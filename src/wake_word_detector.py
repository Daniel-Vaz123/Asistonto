"""
Wake Word Detector - Detección de palabra de activación

Este módulo implementa la detección de palabras de activación (wake words)
usando AWS Transcribe en tiempo real mediante streaming.

Características:
- Detección continua de wake words configurables
- Streaming asíncrono con AWS Transcribe
- Filtrado de falsos positivos
- Callbacks para notificación de detección
- Soporte para español (es-ES/es-MX)

Requisitos implementados:
- 1.2: Establecer conexión de streaming con AWS Transcribe
- 1.3: Detectar wake word en el stream de audio
- 1.4: Proporcionar retroalimentación cuando se detecta wake word
"""

import asyncio
import logging
import time
from typing import List, Optional, Callable
from dataclasses import dataclass

from src.audio_manager import AudioManager
from src.transcribe_client import (
    TranscribeStreamingClientWrapper,
    TranscriptionResult
)


logger = logging.getLogger(__name__)


@dataclass
class WakeWordDetection:
    """Resultado de detección de wake word"""
    wake_word: str
    confidence: float
    timestamp: float
    full_transcription: str


class WakeWordDetector:
    """
    Detector de palabras de activación usando AWS Transcribe.
    
    Escucha continuamente el audio y detecta cuando se pronuncia
    una palabra de activación configurada.
    
    Attributes:
        wake_words: Lista de palabras de activación a detectar
        confidence_threshold: Umbral mínimo de confianza (0.0-1.0)
        audio_manager: Gestor de audio para captura
        transcribe_client: Cliente de AWS Transcribe
    """
    
    def __init__(
        self,
        wake_words: List[str],
        audio_manager: AudioManager,
        transcribe_client: TranscribeStreamingClientWrapper,
        confidence_threshold: float = 0.7,
        detection_window: float = 3.0
    ):
        """
        Inicializa el detector de wake words.
        
        Args:
            wake_words: Lista de palabras de activación (ej: ["asistente", "alexa"])
            audio_manager: Gestor de audio
            transcribe_client: Cliente de AWS Transcribe
            confidence_threshold: Umbral mínimo de confianza para detección
            detection_window: Ventana de tiempo para validar detección (segundos)
        """
        # Normalizar wake words a minúsculas para comparación case-insensitive
        self.wake_words = [word.lower() for word in wake_words]
        self.audio_manager = audio_manager
        self.transcribe_client = transcribe_client
        self.confidence_threshold = confidence_threshold
        self.detection_window = detection_window
        
        # Estado interno
        self._is_detecting = False
        self._detection_callback: Optional[Callable[[WakeWordDetection], None]] = None
        self._last_detection_time: Optional[float] = None
        self._recent_transcriptions: List[str] = []
        
        logger.info(
            f"WakeWordDetector inicializado: wake_words={wake_words}, "
            f"threshold={confidence_threshold}"
        )
    
    def on_wake_word_detected(self, callback: Callable[[WakeWordDetection], None]) -> None:
        """
        Registra un callback para cuando se detecte un wake word.
        
        Args:
            callback: Función a llamar cuando se detecte wake word
        """
        self._detection_callback = callback
        logger.debug("Callback de detección registrado")
    
    async def start_detection(self) -> None:
        """
        Inicia la detección continua de wake words.
        
        Este método mantiene un stream persistente con AWS Transcribe
        y analiza las transcripciones en busca de wake words.
        
        Requisito: 1.2, 1.3 - Establecer conexión y detectar wake word
        """
        if self._is_detecting:
            logger.warning("La detección ya está en progreso")
            return
        
        self._is_detecting = True
        logger.info("Iniciando detección de wake words...")
        
        # Asegurar que AudioManager está capturando
        if not self.audio_manager.is_capturing():
            self.audio_manager.start_continuous_capture()
            # Dar tiempo para que el buffer se llene
            await asyncio.sleep(0.5)
        
        try:
            while self._is_detecting:
                try:
                    # Crear generador de audio asíncrono
                    audio_stream = self._create_audio_stream()
                    
                    # Iniciar streaming a AWS Transcribe
                    await self.transcribe_client.start_stream(
                        audio_stream=audio_stream,
                        on_transcription=self._handle_transcription,
                        on_error=self._handle_error
                    )
                    
                except Exception as e:
                    logger.error(f"Error en stream de detección: {e}")
                    
                    if self._is_detecting:
                        # Reintentar después de un breve delay
                        logger.info("Reintentando conexión en 2 segundos...")
                        await asyncio.sleep(2)
                    else:
                        break
        
        finally:
            self._is_detecting = False
            logger.info("Detección de wake words detenida")
    
    async def stop_detection(self) -> None:
        """Detiene la detección de wake words."""
        if not self._is_detecting:
            logger.warning("La detección no está activa")
            return
        
        logger.info("Deteniendo detección de wake words...")
        self._is_detecting = False
        
        # Detener stream de Transcribe
        await self.transcribe_client.stop_stream()
    
    async def _create_audio_stream(self):
        """
        Crea un generador asíncrono de chunks de audio.
        
        Yields:
            Chunks de audio en formato PCM
        """
        try:
            while self._is_detecting:
                # Obtener chunk de audio del AudioManager
                audio_chunk = self.audio_manager.get_audio_chunk(timeout=0.1)
                
                if audio_chunk:
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
        
        Analiza el texto transcrito en busca de wake words.
        
        Args:
            transcription: Resultado de transcripción
        """
        try:
            # Normalizar texto a minúsculas para comparación
            text_lower = transcription.text.lower().strip()
            
            if not text_lower:
                return
            
            # Agregar a transcripciones recientes
            self._recent_transcriptions.append(text_lower)
            
            # Mantener solo las últimas 10 transcripciones
            if len(self._recent_transcriptions) > 10:
                self._recent_transcriptions.pop(0)
            
            # Buscar wake words en la transcripción
            detected_word = self._check_for_wake_word(text_lower)
            
            if detected_word:
                # Verificar que no sea una detección duplicada reciente
                current_time = time.time()
                
                if (self._last_detection_time is None or 
                    current_time - self._last_detection_time > self.detection_window):
                    
                    # Wake word detectado!
                    detection = WakeWordDetection(
                        wake_word=detected_word,
                        confidence=transcription.confidence,
                        timestamp=current_time,
                        full_transcription=transcription.text
                    )
                    
                    self._last_detection_time = current_time
                    
                    logger.info(
                        f"🎤 Wake word detectado: '{detected_word}' "
                        f"(confianza: {transcription.confidence:.2f})"
                    )
                    
                    # Notificar callback
                    if self._detection_callback:
                        if asyncio.iscoroutinefunction(self._detection_callback):
                            asyncio.create_task(self._detection_callback(detection))
                        else:
                            self._detection_callback(detection)
                else:
                    logger.debug(
                        f"Wake word detectado pero ignorado (muy reciente): '{detected_word}'"
                    )
            
            # Log de transcripciones para debugging
            if transcription.is_partial:
                logger.debug(f"Transcripción parcial: '{transcription.text}'")
            else:
                logger.debug(f"Transcripción final: '{transcription.text}'")
                
        except Exception as e:
            logger.error(f"Error manejando transcripción: {e}")
    
    def _check_for_wake_word(self, text: str) -> Optional[str]:
        """
        Verifica si el texto contiene algún wake word.
        
        Args:
            text: Texto transcrito (ya en minúsculas)
        
        Returns:
            Wake word detectado o None si no se encontró ninguno
        """
        # Buscar cada wake word en el texto
        for wake_word in self.wake_words:
            # Buscar palabra completa (no como substring)
            # Ej: "asistente" debe coincidir en "hola asistente" pero no en "asistentes"
            words_in_text = text.split()
            
            # Verificar coincidencia exacta de palabra
            if wake_word in words_in_text:
                return wake_word
            
            # También verificar si el wake word es una frase multi-palabra
            if ' ' in wake_word and wake_word in text:
                return wake_word
        
        return None
    
    def _handle_error(self, error: Exception) -> None:
        """
        Maneja errores de AWS Transcribe.
        
        Args:
            error: Excepción ocurrida
        """
        logger.error(f"Error de AWS Transcribe: {error}")
    
    def is_detecting(self) -> bool:
        """
        Verifica si la detección está activa.
        
        Returns:
            True si está detectando, False en caso contrario
        """
        return self._is_detecting
    
    def get_recent_transcriptions(self) -> List[str]:
        """
        Obtiene las transcripciones recientes.
        
        Returns:
            Lista de transcripciones recientes
        """
        return self._recent_transcriptions.copy()


# TODO: Implementar filtrado avanzado de falsos positivos usando contexto
# TODO: Agregar soporte para wake words con variaciones fonéticas
# TODO: Implementar detección local de wake word para reducir costos de AWS
# TODO: Agregar métricas de precisión y recall de detección
