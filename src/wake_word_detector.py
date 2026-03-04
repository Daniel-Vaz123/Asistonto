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
from difflib import SequenceMatcher
from typing import List, Optional, Callable
from dataclasses import dataclass, field

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
    inline_command: Optional[str] = None  # Texto después del wake word (ej. "asistente qué hora es" → "qué hora es")


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
        detection_window: float = 3.0,
        feedback_preventer: Optional['FeedbackPreventer'] = None  # Phase 3: Auto-Mute
    ):
        """
        Inicializa el detector de wake words.
        
        Args:
            wake_words: Lista de palabras de activación (ej: ["asistente", "alexa"])
            audio_manager: Gestor de audio
            transcribe_client: Cliente de AWS Transcribe
            confidence_threshold: Umbral mínimo de confianza para detección
            detection_window: Ventana de tiempo para validar detección (segundos)
            feedback_preventer: FeedbackPreventer para auto-mute (Phase 3)
        """
        # Normalizar wake words a minúsculas para comparación case-insensitive
        self.wake_words = [word.lower() for word in wake_words]
        self.audio_manager = audio_manager
        self.transcribe_client = transcribe_client
        self.confidence_threshold = confidence_threshold
        self.detection_window = detection_window
        self.feedback_preventer = feedback_preventer  # Phase 3: Auto-Mute
        
        # Estado interno
        self._is_detecting = False
        self._paused = False
        self._pending_command_task = None
        self._detection_callback: Optional[Callable[[WakeWordDetection], None]] = None
        self._on_hearing_callback: Optional[Callable[[str, bool], None]] = None
        self._last_detection_time: Optional[float] = None
        self._recent_transcriptions: List[str] = []
        self._fuzzy_threshold = 0.70
        
        logger.info(
            f"WakeWordDetector inicializado: wake_words={wake_words}, "
            f"threshold={confidence_threshold}, auto_mute={'enabled' if feedback_preventer else 'disabled'}"
        )
    
    def pause(self) -> None:
        """Pausa el stream de audio para permitir usar el cliente en captura de comando."""
        self._paused = True
        logger.debug("Detección pausada (captura de comando)")

    def on_wake_word_detected(self, callback: Callable[[WakeWordDetection], None]) -> None:
        """Registra callback para detección de wake word."""
        self._detection_callback = callback

    def on_hearing(self, callback: Callable[[str, bool], None]) -> None:
        """Registra callback (text, is_partial) para mostrar lo que se escucha."""
        self._on_hearing_callback = callback

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
                    self._paused = False
                    self._pending_command_task = None

                    # Descartar audio acumulado mientras se procesaba el comando anterior
                    self.audio_manager.clear_buffer()

                    # Crear generador de audio asíncrono
                    audio_stream = self._create_audio_stream()
                    
                    # Iniciar streaming a AWS Transcribe
                    await self.transcribe_client.start_stream(
                        audio_stream=audio_stream,
                        on_transcription=self._handle_transcription,
                        on_error=self._handle_error
                    )
                    
                    # Si se pausó para capturar comando, esperar a que termine
                    if self._pending_command_task is not None:
                        try:
                            await asyncio.shield(self._pending_command_task)
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            logger.error(f"Error en captura de comando: {e}")
                        self._pending_command_task = None
                        # El wake word anterior ya fue procesado; permitir detección inmediata
                        self._last_detection_time = None
                    
                except Exception as e:
                    logger.error(f"Error en stream de detección: {e}")
                    
                    if self._is_detecting:
                        logger.info("Reintentando conexión en 1 segundo...")
                        await asyncio.sleep(1)
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
        
        Phase 3: Integra verificación de FeedbackPreventer para ignorar
        audio mientras Kiro está hablando (auto-mute).
        
        Yields:
            Chunks de audio en formato PCM (solo cuando no está hablando)
            
        Requisito: 1.2 - Ignorar audio mientras Speaking_State es verdadero (Phase 3)
        """
        try:
            while self._is_detecting and not self._paused:
                # Phase 3: Verificar si Kiro está hablando
                if self.feedback_preventer and self.feedback_preventer.is_speaking():
                    # Ignorar audio mientras está hablando
                    await asyncio.sleep(0.01)
                    continue
                
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
        """Analiza transcripciones en busca de wake words y notifica lo que se escucha."""
        try:
            text_lower = transcription.text.lower().strip()
            if not text_lower:
                return

            # Mostrar en consola lo que se escucha
            if self._on_hearing_callback:
                self._on_hearing_callback(transcription.text, transcription.is_partial)

            self._recent_transcriptions.append(text_lower)
            if len(self._recent_transcriptions) > 10:
                self._recent_transcriptions.pop(0)

            detected_word = self._check_for_wake_word(text_lower)

            if detected_word:
                current_time = time.time()
                if (self._last_detection_time is None or
                        current_time - self._last_detection_time > self.detection_window):
                    # Extraer texto después del wake word (ej. "asistente qué hora es" → "qué hora es")
                    inline_cmd = None
                    idx = text_lower.find(detected_word)
                    if idx >= 0:
                        after = text_lower[idx + len(detected_word):].strip()
                        if len(after) > 2:
                            inline_cmd = after
                    detection = WakeWordDetection(
                        wake_word=detected_word,
                        confidence=transcription.confidence,
                        timestamp=current_time,
                        full_transcription=transcription.text,
                        inline_command=inline_cmd,
                    )
                    self._last_detection_time = current_time
                    logger.info("Wake word detectado: '%s'", detected_word)

                    self._paused = True
                    if self._detection_callback:
                        result = self._detection_callback(detection)
                        if result is not None and (asyncio.iscoroutine(result) or isinstance(result, asyncio.Task)):
                            self._pending_command_task = asyncio.ensure_future(result)

        except Exception as e:
            logger.error("Error manejando transcripción: %s", e)
    
    def _check_for_wake_word(self, text: str) -> Optional[str]:
        """Verifica si el texto contiene algún wake word (exacto o aproximado)."""
        words_in_text = text.split()

        for wake_word in self.wake_words:
            # Exacto
            if wake_word in words_in_text:
                return wake_word
            # Frase multi-palabra
            if ' ' in wake_word and wake_word in text:
                return wake_word
            # Coincidencia aproximada (Vosk puede decir "asistentes", "persistente", etc.)
            for w in words_in_text:
                ratio = SequenceMatcher(None, wake_word, w).ratio()
                if ratio >= self._fuzzy_threshold:
                    logger.debug("Fuzzy match: '%s' ≈ '%s' (%.0f%%)", w, wake_word, ratio * 100)
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
