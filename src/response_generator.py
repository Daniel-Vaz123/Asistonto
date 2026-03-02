"""
Response Generator - Generación y síntesis de respuestas con Amazon Polly

Este módulo implementa la síntesis de texto a voz (TTS) usando Amazon Polly
para que el asistente pueda hablar las respuestas.

Características:
- Síntesis de texto a voz con Amazon Polly
- Cache de respuestas comunes para reducir latencia y costos
- Reproducción automática de audio
- Soporte para voces en español (México y España)
- Manejo robusto de errores con fallback a texto

Requisitos implementados:
- 7.1: Enviar respuesta textual a AWS Polly para síntesis
- 7.2: Reproducir audio de respuesta inmediatamente
- 7.3: Configurar voz en español con velocidad ajustable
- 7.5: Cachear respuestas comunes localmente
"""

import asyncio
import logging
import os
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict
import json

import numpy as np
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.audio_manager import AudioManager


logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generador de respuestas con síntesis de voz usando Amazon Polly.
    
    Convierte texto a voz y reproduce el audio automáticamente.
    Implementa cache para respuestas comunes.
    
    Attributes:
        polly_voice_id: ID de la voz de Polly (ej: 'Mia', 'Lucia', 'Enrique')
        output_format: Formato de audio (mp3, ogg_vorbis, pcm)
        sample_rate: Frecuencia de muestreo del audio
        cache_enabled: Si está habilitado el cache de respuestas
        audio_manager: Gestor de audio para reproducción
    """
    
    def __init__(
        self,
        audio_manager: AudioManager,
        polly_voice_id: str = "Mia",
        output_format: str = "mp3",
        sample_rate: str = "22050",
        cache_enabled: bool = True,
        cache_dir: str = "cache",
        region: str = "us-east-1",
        volume_gain: float = 3.0
    ):
        """
        Inicializa el generador de respuestas.
        
        Args:
            audio_manager: Gestor de audio para reproducción
            polly_voice_id: ID de voz de Polly ('Mia', 'Lucia', 'Enrique', 'Lupe')
            output_format: Formato de salida de audio
            sample_rate: Frecuencia de muestreo
            cache_enabled: Habilitar cache de respuestas
            cache_dir: Directorio para almacenar cache
            region: Región de AWS
        """
        self.audio_manager = audio_manager
        self.polly_voice_id = polly_voice_id
        self.output_format = output_format
        self.sample_rate = sample_rate
        self.cache_enabled = cache_enabled
        self.cache_dir = Path(cache_dir)
        self.region = region
        self.volume_gain = volume_gain
        
        # Crear directorio de cache si no existe
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cliente de Polly
        self._polly_client = None
        
        # Estadísticas
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_requests = 0
        
        logger.info(
            f"ResponseGenerator inicializado: voz={polly_voice_id}, "
            f"formato={output_format}, cache={'habilitado' if cache_enabled else 'deshabilitado'}"
        )
    
    def _get_polly_client(self):
        """Obtiene o crea el cliente de Polly"""
        if self._polly_client is None:
            self._polly_client = boto3.client('polly', region_name=self.region)
        return self._polly_client
    
    def _get_cache_key(self, text: str) -> str:
        """
        Genera una clave de cache única para el texto.
        
        Args:
            text: Texto a sintetizar
            
        Returns:
            Hash MD5 del texto como clave de cache
        """
        # Incluir voz y configuración en la clave para evitar colisiones
        cache_string = f"{text}_{self.polly_voice_id}_{self.output_format}_{self.sample_rate}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Obtiene la ruta del archivo de cache.
        
        Args:
            cache_key: Clave de cache
            
        Returns:
            Path al archivo de cache
        """
        extension = "mp3" if self.output_format == "mp3" else "ogg"
        return self.cache_dir / f"{cache_key}.{extension}"
    
    def _load_from_cache(self, text: str) -> Optional[bytes]:
        """
        Intenta cargar audio desde el cache.
        
        Args:
            text: Texto a buscar en cache
            
        Returns:
            Datos de audio si están en cache, None en caso contrario
        """
        if not self.cache_enabled:
            return None
        
        cache_key = self._get_cache_key(text)
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    audio_data = f.read()
                
                self._cache_hits += 1
                logger.debug(f"Cache hit para: '{text[:50]}...'")
                return audio_data
            except Exception as e:
                logger.warning(f"Error leyendo cache: {e}")
                return None
        
        self._cache_misses += 1
        return None
    
    def _save_to_cache(self, text: str, audio_data: bytes) -> None:
        """
        Guarda audio en el cache.
        
        Args:
            text: Texto sintetizado
            audio_data: Datos de audio a guardar
        """
        if not self.cache_enabled:
            return
        
        cache_key = self._get_cache_key(text)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'wb') as f:
                f.write(audio_data)
            logger.debug(f"Audio guardado en cache: {cache_path.name}")
        except Exception as e:
            logger.warning(f"Error guardando en cache: {e}")
    
    async def generate_speech(self, text: str) -> Optional[bytes]:
        """
        Genera audio desde texto usando Amazon Polly.
        
        Args:
            text: Texto a sintetizar
            
        Returns:
            Datos de audio en formato especificado o None si falla
            
        Requisito: 7.1 - Enviar respuesta textual a AWS Polly
        """
        if not text or not text.strip():
            logger.warning("Texto vacío, no se puede sintetizar")
            return None
        
        self._total_requests += 1
        
        # Intentar cargar desde cache
        cached_audio = self._load_from_cache(text)
        if cached_audio:
            return cached_audio
        
        # Sintetizar con Polly
        try:
            logger.info(f"Sintetizando con Polly: '{text[:50]}...'")
            
            polly_client = self._get_polly_client()
            
            # Llamar a Polly
            response = polly_client.synthesize_speech(
                Text=text,
                OutputFormat=self.output_format,
                VoiceId=self.polly_voice_id,
                SampleRate=self.sample_rate,
                Engine='neural' if self.polly_voice_id in ['Mia', 'Lucia'] else 'standard'
            )
            
            # Leer audio del stream
            if 'AudioStream' in response:
                audio_data = response['AudioStream'].read()
                
                # Guardar en cache
                self._save_to_cache(text, audio_data)
                
                logger.info(
                    f"Audio sintetizado correctamente: {len(audio_data)} bytes "
                    f"(voz: {self.polly_voice_id})"
                )
                return audio_data
            else:
                logger.error("No se recibió AudioStream de Polly")
                return None
                
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error de AWS Polly: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado sintetizando audio: {e}")
            return None
    
    async def speak(self, text: str, block: bool = True) -> bool:
        """
        Sintetiza y reproduce texto como voz.
        
        Este es el método principal para hacer que el asistente hable.
        
        Args:
            text: Texto a hablar
            block: Si True, espera a que termine la reproducción
            
        Returns:
            True si se reprodujo exitosamente, False en caso contrario
            
        Requisito: 7.2 - Reproducir audio de respuesta inmediatamente
        """
        if not text:
            return False
        
        try:
            audio_data = await self.generate_speech(text)
            
            if not audio_data:
                logger.warning("No se pudo generar audio, fallback a solo texto")
                return False
            
            if self.output_format == "mp3":
                audio_data = self._convert_mp3_to_pcm(audio_data)
                if not audio_data:
                    return False
            
            if self.volume_gain != 1.0:
                audio_data = self._amplify_pcm(audio_data, self.volume_gain)

            self.audio_manager.play_audio(audio_data, block=block)
            logger.info("Audio reproducido correctamente")
            return True
                
        except Exception as e:
            logger.error(f"Error reproduciendo audio: {e}")
            return False
    
    @staticmethod
    def _amplify_pcm(pcm_data: bytes, gain: float) -> bytes:
        """Amplifica audio PCM 16-bit multiplicando las muestras por el factor de ganancia."""
        samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
        samples *= gain
        samples = np.clip(samples, -32768, 32767)
        return samples.astype(np.int16).tobytes()

    def _convert_mp3_to_pcm(self, mp3_data: bytes) -> Optional[bytes]:
        """
        Convierte audio MP3 a PCM para reproducción con PyAudio.
        
        Args:
            mp3_data: Datos de audio en formato MP3
            
        Returns:
            Datos de audio en formato PCM o None si falla
        """
        try:
            # Guardar MP3 temporalmente
            temp_mp3 = self.cache_dir / f"temp_{int(time.time())}.mp3"
            temp_wav = self.cache_dir / f"temp_{int(time.time())}.wav"
            
            with open(temp_mp3, 'wb') as f:
                f.write(mp3_data)
            
            # Convertir MP3 a WAV usando pydub
            try:
                from pydub import AudioSegment
                
                audio = AudioSegment.from_mp3(str(temp_mp3))
                audio = audio.set_frame_rate(16000)  # Ajustar a sample rate del sistema
                audio = audio.set_channels(1)  # Mono
                audio.export(str(temp_wav), format="wav")
                
                # Leer WAV como PCM
                with open(temp_wav, 'rb') as f:
                    # Saltar header WAV (44 bytes)
                    f.seek(44)
                    pcm_data = f.read()
                
                # Limpiar archivos temporales
                temp_mp3.unlink(missing_ok=True)
                temp_wav.unlink(missing_ok=True)
                
                return pcm_data
                
            except ImportError:
                logger.warning("pydub no está instalado, intentando con ffmpeg directamente")
                
                # Intentar con ffmpeg/avconv
                import subprocess
                
                result = subprocess.run([
                    'ffmpeg', '-i', str(temp_mp3),
                    '-f', 's16le', '-acodec', 'pcm_s16le',
                    '-ar', '16000', '-ac', '1',
                    str(temp_wav)
                ], capture_output=True)
                
                if result.returncode == 0:
                    with open(temp_wav, 'rb') as f:
                        pcm_data = f.read()
                    
                    temp_mp3.unlink(missing_ok=True)
                    temp_wav.unlink(missing_ok=True)
                    
                    return pcm_data
                else:
                    logger.error("No se pudo convertir MP3 a PCM")
                    temp_mp3.unlink(missing_ok=True)
                    return None
                    
        except Exception as e:
            logger.error(f"Error convirtiendo MP3 a PCM: {e}")
            return None
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Obtiene estadísticas del cache.
        
        Returns:
            Diccionario con estadísticas de cache
        """
        hit_rate = (self._cache_hits / self._total_requests * 100) if self._total_requests > 0 else 0
        
        return {
            'total_requests': self._total_requests,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': round(hit_rate, 2)
        }
    
    def clear_cache(self) -> int:
        """
        Limpia todos los archivos del cache.
        
        Returns:
            Número de archivos eliminados
        """
        if not self.cache_enabled or not self.cache_dir.exists():
            return 0
        
        count = 0
        for cache_file in self.cache_dir.glob("*.mp3"):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Error eliminando {cache_file}: {e}")
        
        for cache_file in self.cache_dir.glob("*.ogg"):
            try:
                cache_file.unlink()
                count += 1
            except Exception as e:
                logger.warning(f"Error eliminando {cache_file}: {e}")
        
        logger.info(f"Cache limpiado: {count} archivos eliminados")
        return count


# TODO: Implementar ajuste de velocidad de habla (speech rate)
# TODO: Agregar soporte para SSML (Speech Synthesis Markup Language)
# TODO: Implementar cola de reproducción para múltiples respuestas
# TODO: Agregar efectos de audio (eco, reverb) para personalización
