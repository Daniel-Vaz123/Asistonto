"""
Command Transcriber

Este módulo integra AudioManager con AWS Transcribe para capturar y transcribir
comandos de voz en tiempo real.

Características:
- Captura de audio continua desde AudioManager
- Envío de audio en tiempo real a AWS Transcribe
- Recepción de transcripciones parciales y finales
- Detección de silencio para finalizar captura
- Manejo de sesiones de comando
"""

import asyncio
import logging
from typing import Optional, Callable, List
from dataclasses import dataclass
import time

from src.audio_manager import AudioManager
from src.transcribe_client import (
    TranscribeStreamingClientWrapper,
    TranscriptionResult
)


logger = logging.getLogger(__name__)


@dataclass
class CommandTranscription:
    """Resultado de transcripción de un comando completo"""
    text: str
    confidence: float
    duration: float
    language_code: Optional[str] = None
    partial_transcriptions: List[str] = None
    
    def __post_init__(self):
        if self.partial_transcriptions is None:
            self.partial_transcriptions = []


class CommandTranscriber:
    """
    Transcriptor de comandos de voz usando AWS Transcribe.
    
    Integra AudioManager con AWS Transcribe para capturar audio
    continuamente y transcribirlo en tiempo real.
    
    Attributes:
        audio_manager: Gestor de audio para captura
        transcribe_client: Cliente de AWS Transcribe
        silence_threshold: Segundos de silencio para finalizar captura
        max_command_duration: Duración máxima de comando en segundos
    """
    
    def __init__(
        self,
        audio_manager: AudioManager,
        transcribe_client: TranscribeStreamingClientWrapper,
        silence_threshold: float = 1.5,
        max_command_duration: float = 10.0
    ):
        """
        Inicializa el transcriptor de comandos.
        
        Args:
            audio_manager: Gestor de audio
            transcribe_client: Cliente de AWS Transcribe
            silence_threshold: Segundos de silencio para finalizar
            max_command_duration: Duración máxima de comando
        """
        self.audio_manager = audio_manager
        self.transcribe_client = transcribe_client
        self.silence_threshold = silence_threshold
        self.max_command_duration = max_command_duration
        
        # Estado interno
        self._is_capturing = False
        self._current_transcription: Optional[str] = None
        self._partial_transcriptions: List[str] = []
        self._last_transcription_time: Optional[float] = None
        self._capture_start_time: Optional[float] = None
        self._final_transcription: Optional[TranscriptionResult] = None
        self._transcription_confidence: float = 0.0
        
        # Callbacks
        self._on_partial_transcription: Optional[Callable[[str], None]] = None
        self._on_final_transcription: Optional[Callable[[CommandTranscription], None]] = None
        self._on_error: Optional[Callable[[Exception], None]] = None
        
        logger.info(
            f"CommandTranscriber inicializado: "
            f"silence_threshold={silence_threshold}s, "
            f"max_duration={max_command_duration}s"
        )
    
    def set_callbacks(
        self,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[CommandTranscription], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ) -> None:
        """
        Configura callbacks para eventos de transcripción.
        
        Args:
            on_partial: Callback para transcripciones parciales
            on_final: Callback para transcripción final
            on_error: Callback para errores
        """
        self._on_partial_transcription = on_partial
        self._on_final_transcription = on_final
        self._on_error = on_error
    
    async def capture_command(self) -> Optional[CommandTranscription]:
        """
        Captura y transcribe un comando de voz completo.
        
        Captura audio continuamente hasta que:
        - Se detecta silencio por silence_threshold segundos
        - Se alcanza max_command_duration
        - Ocurre un error
        
        Returns:
            Transcripción del comando o None si no hay transcripción
        """
        if self._is_capturing:
            logger.warning("Ya hay una captura de comando en progreso")
            return None
        
        try:
            self._is_capturing = True
            self._current_transcription = None
            self._partial_transcriptions = []
            self._last_transcription_time = None
            self._capture_start_time = time.time()
            self._final_transcription = None
            self._transcription_confidence = 0.0
            
            logger.info("Iniciando captura de comando")
            
            # Asegurar que AudioManager está capturando
            if not self.audio_manager.is_capturing():
                self.audio_manager.start_continuous_capture()
            
            # Crear generador de audio asíncrono
            audio_stream = self._create_audio_stream()
            
            # Iniciar streaming a AWS Transcribe
            await self.transcribe_client.start_stream(
                audio_stream=audio_stream,
                on_transcription=self._handle_transcription,
                on_error=self._handle_error
            )
            
            # Construir resultado final
            if self._final_transcription:
                duration = time.time() - self._capture_start_time
                
                result = CommandTranscription(
                    text=self._final_transcription.text,
                    confidence=self._transcription_confidence,
                    duration=duration,
                    language_code=self._final_transcription.language_code,
                    partial_transcriptions=self._partial_transcriptions.copy()
                )
                
                logger.info(
                    f"Comando capturado: '{result.text}' "
                    f"(confianza: {result.confidence:.2f}, duración: {duration:.2f}s)"
                )
                
                # Notificar callback
                if self._on_final_transcription:
                    if asyncio.iscoroutinefunction(self._on_final_transcription):
                        await self._on_final_transcription(result)
                    else:
                        self._on_final_transcription(result)
                
                return result
            else:
                logger.warning("No se obtuvo transcripción final del comando")
                return None
                
        except Exception as e:
            logger.error(f"Error capturando comando: {e}")
            if self._on_error:
                if asyncio.iscoroutinefunction(self._on_error):
                    await self._on_error(e)
                else:
                    self._on_error(e)
            return None
        finally:
            self._is_capturing = False
    
    async def _create_audio_stream(self):
        """
        Crea un generador asíncrono de chunks de audio.
        
        Yields:
            Chunks de audio en formato PCM
        """
        try:
            while self._is_capturing:
                # Verificar timeout de duración máxima
                if time.time() - self._capture_start_time > self.max_command_duration:
                    logger.info(
                        f"Duración máxima de comando alcanzada "
                        f"({self.max_command_duration}s)"
                    )
                    break
                
                # Verificar timeout de silencio
                if (self._last_transcription_time is not None and
                    time.time() - self._last_transcription_time > self.silence_threshold):
                    logger.info(
                        f"Silencio detectado por {self.silence_threshold}s, "
                        f"finalizando captura"
                    )
                    break
                
                # Obtener chunk de audio del AudioManager
                audio_chunk = self.audio_manager.get_audio_chunk(timeout=0.1)
                
                if audio_chunk:
                    # Convertir a formato requerido por AWS Transcribe (PCM)
                    # El audio ya viene en formato PCM desde AudioManager
                    yield audio_chunk
                else:
                    # No hay audio disponible, esperar un poco
                    await asyncio.sleep(0.01)
                    
        except Exception as e:
            logger.error(f"Error en stream de audio: {e}")
            raise
    
    def _handle_transcription(self, transcription: TranscriptionResult) -> None:
        """
        Maneja transcripciones recibidas de AWS Transcribe.
        
        Args:
            transcription: Resultado de transcripción
        """
        try:
            # Actualizar tiempo de última transcripción
            self._last_transcription_time = time.time()
            
            if transcription.is_partial:
                # Transcripción parcial
                self._current_transcription = transcription.text
                self._partial_transcriptions.append(transcription.text)
                
                logger.debug(f"Transcripción parcial: '{transcription.text}'")
                
                # Notificar callback
                if self._on_partial_transcription:
                    if asyncio.iscoroutinefunction(self._on_partial_transcription):
                        asyncio.create_task(
                            self._on_partial_transcription(transcription.text)
                        )
                    else:
                        self._on_partial_transcription(transcription.text)
            else:
                # Transcripción final
                self._final_transcription = transcription
                self._transcription_confidence = transcription.confidence
                
                logger.info(
                    f"Transcripción final: '{transcription.text}' "
                    f"(confianza: {transcription.confidence:.2f})"
                )
                
        except Exception as e:
            logger.error(f"Error manejando transcripción: {e}")
            if self._on_error:
                if asyncio.iscoroutinefunction(self._on_error):
                    asyncio.create_task(self._on_error(e))
                else:
                    self._on_error(e)
    
    def _handle_error(self, error: Exception) -> None:
        """
        Maneja errores de AWS Transcribe.
        
        Args:
            error: Excepción ocurrida
        """
        logger.error(f"Error de AWS Transcribe: {error}")
        
        if self._on_error:
            if asyncio.iscoroutinefunction(self._on_error):
                asyncio.create_task(self._on_error(error))
            else:
                self._on_error(error)
    
    def is_capturing(self) -> bool:
        """
        Verifica si hay una captura en progreso.
        
        Returns:
            True si hay captura activa, False en caso contrario
        """
        return self._is_capturing
    
    def get_current_transcription(self) -> Optional[str]:
        """
        Obtiene la transcripción parcial actual.
        
        Returns:
            Texto de transcripción parcial o None
        """
        return self._current_transcription
    
    async def stop_capture(self) -> None:
        """
        Detiene la captura de comando en progreso.
        """
        if not self._is_capturing:
            logger.warning("No hay captura activa para detener")
            return
        
        logger.info("Deteniendo captura de comando")
        self._is_capturing = False
        
        # Detener stream de Transcribe
        await self.transcribe_client.stop_stream()


# TODO: Implementar función auxiliar para convertir formato de audio si es necesario
def convert_audio_format(
    audio_data: bytes,
    source_format: str = "pcm",
    target_format: str = "pcm"
) -> bytes:
    """
    Convierte audio entre diferentes formatos.
    
    Args:
        audio_data: Datos de audio
        source_format: Formato de origen
        target_format: Formato de destino
        
    Returns:
        Audio convertido
    """
    # Por ahora, AudioManager ya proporciona PCM que es lo que necesita Transcribe
    # Esta función es un placeholder para futuras conversiones si son necesarias
    return audio_data
