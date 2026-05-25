"""
STTEngine — Motor de reconocimiento de voz offline con Vosk.

Corre en un hilo daemon separado del Main Thread de la GUI.
Comunica resultados al Main Thread exclusivamente via queue.Queue.

Flujo:
    AudioManager.get_audio_chunk() → Vosk KaldiRecognizer
    → transcripción parcial/final → GUIEvent en event_queue
    → detección de wake words (fuzzy, umbral 0.70)
    → GUIEvent(WAKE_WORD) en event_queue
"""

import json
import logging
import queue
import threading
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

try:
    from vosk import KaldiRecognizer, Model, SetLogLevel
    SetLogLevel(-1)   # Silenciar logs de Kaldi
    _VOSK_AVAILABLE = True
except ImportError:
    _VOSK_AVAILABLE = False
    Model = None
    KaldiRecognizer = None


class STTEngine:
    """
    Motor STT offline basado en Vosk.

    Uso:
        engine = STTEngine(
            model_path="models/vosk-model-small-es-0.42",
            audio_manager=audio_mgr,
            wake_words=["asistente", "alexa"],
            event_queue=gui_queue,
        )
        engine.start()
        # ... más tarde ...
        engine.stop()
    """

    def __init__(
        self,
        model_path: str,
        audio_manager,
        wake_words: List[str],
        event_queue: queue.Queue,
        fuzzy_threshold: float = 0.70,
    ) -> None:
        self._model_path     = model_path
        self._audio_manager  = audio_manager
        self._wake_words     = [w.lower() for w in wake_words]
        self._event_queue    = event_queue
        self._fuzzy_threshold = fuzzy_threshold

        self._stop_event  = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Estado de escucha: True = capturando comando tras wake word
        self._listening_for_command = False

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Lanza el loop STT en un hilo daemon."""
        if self._thread and self._thread.is_alive():
            logger.warning("STTEngine ya está corriendo.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._stt_loop,
            daemon=True,
            name="STTThread",
        )
        self._thread.start()
        logger.info("STTEngine iniciado (modelo: %s).", self._model_path)

    def stop(self) -> None:
        """
        Señaliza el hilo para que termine.
        El hilo termina en ≤ 5 s (timeout de get_audio_chunk = 1 s × 5 iteraciones).
        """
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("STTEngine: hilo no terminó en 5 s.")
        logger.info("STTEngine detenido.")

    def trigger_listen(self) -> None:
        """
        Activa el modo 'escuchando comando' desde el botón manual.
        Equivalente a haber detectado un wake word.
        """
        self._listening_for_command = True
        logger.info("STTEngine: modo escucha activado manualmente.")

    # ------------------------------------------------------------------
    # Loop principal (hilo daemon)
    # ------------------------------------------------------------------

    def _stt_loop(self) -> None:
        """Loop de captura y reconocimiento. Corre en STTThread."""
        # Importar aquí para evitar errores si vosk no está instalado
        if not _VOSK_AVAILABLE:
            self._put_error("Vosk no está instalado. Ejecuta: pip install vosk")
            return

        model_path = Path(self._model_path)
        if not model_path.is_dir():
            self._put_error(
                f"Modelo Vosk no encontrado en '{self._model_path}'. "
                "Descárgalo con: python scripts/download_vosk_model.py"
            )
            return

        try:
            model = Model(str(model_path))
            sample_rate = self._audio_manager.sample_rate
            rec = KaldiRecognizer(model, sample_rate)
            rec.SetWords(True)
        except Exception as exc:
            self._put_error(f"Error inicializando Vosk: {exc}")
            return

        logger.info("STTEngine: KaldiRecognizer listo (sample_rate=%s Hz).", sample_rate)

        # Buffer acumulador — Vosk necesita bloques de ~300 ms para resultados útiles
        buffer = bytearray()
        buffer_target = int(sample_rate * 2 * 0.3)   # 300 ms en bytes (16-bit mono)

        while not self._stop_event.is_set():
            chunk = self._audio_manager.get_audio_chunk(timeout=1.0)
            if chunk is None:
                continue

            buffer.extend(chunk)

            # Procesar cuando el buffer alcanza el tamaño objetivo
            while len(buffer) >= buffer_target:
                block = bytes(buffer[:buffer_target])
                del buffer[:buffer_target]

                try:
                    if rec.AcceptWaveform(block):
                        # Resultado final
                        raw = rec.Result()
                        text = self._parse_text(raw)
                        if text:
                            self._handle_text(text, is_partial=False)
                    else:
                        # Resultado parcial
                        raw = rec.PartialResult()
                        text = self._parse_partial(raw)
                        if text:
                            self._handle_text(text, is_partial=True)
                except Exception as exc:
                    logger.error("STTEngine: error en AcceptWaveform: %s", exc)

        # Flush del buffer restante al detener
        if buffer:
            try:
                rec.AcceptWaveform(bytes(buffer))
                raw = rec.FinalResult()
                text = self._parse_text(raw)
                if text:
                    self._handle_text(text, is_partial=False)
            except Exception:
                pass

        logger.info("STTEngine: loop finalizado.")

    # ------------------------------------------------------------------
    # Procesamiento de texto
    # ------------------------------------------------------------------

    def _handle_text(self, text: str, is_partial: bool) -> None:
        """Decide si el texto es un wake word o un comando y notifica a la GUI."""
        text_lower = text.lower().strip()

        if not self._listening_for_command:
            # Modo detección de wake word
            detected = self._check_wake_word(text_lower)
            if detected:
                logger.info("STTEngine: wake word detectado — '%s'.", detected)
                self._listening_for_command = True
                self._put_event("wake_word", detected)
        else:
            # Modo captura de comando — solo resultados finales
            if not is_partial and text_lower:
                logger.info("STTEngine: comando capturado — '%s'.", text)
                self._listening_for_command = False
                self._put_event("transcription", text)

    def _check_wake_word(self, text: str) -> Optional[str]:
        """
        Detecta wake words en el texto.
        Primero coincidencia exacta, luego fuzzy con SequenceMatcher (umbral 0.70).
        """
        words = text.split()
        for wake_word in self._wake_words:
            # Exacto (palabra o frase)
            if wake_word in words or (' ' in wake_word and wake_word in text):
                return wake_word
            # Fuzzy por palabra
            for w in words:
                ratio = SequenceMatcher(None, wake_word, w).ratio()
                if ratio >= self._fuzzy_threshold:
                    logger.debug(
                        "STTEngine: fuzzy match '%s' ≈ '%s' (%.0f%%).",
                        w, wake_word, ratio * 100,
                    )
                    return wake_word
        return None

    # ------------------------------------------------------------------
    # Helpers de queue
    # ------------------------------------------------------------------

    def _put_event(self, event_type: str, payload) -> None:
        """Pone un evento en la queue de la GUI (thread-safe, no bloqueante)."""
        # Importación local para evitar dependencia circular
        from src.gui.main_window import EventType, GUIEvent
        from src.gui.avatar_widget import AvatarState

        type_map = {
            "transcription": EventType.TRANSCRIPTION,
            "wake_word":     EventType.WAKE_WORD,
            "error":         EventType.ERROR,
        }
        evt_type = type_map.get(event_type, EventType.ERROR)
        try:
            self._event_queue.put_nowait(GUIEvent(type=evt_type, payload=payload))
        except queue.Full:
            # Descartar el evento más antiguo y reintentar
            try:
                self._event_queue.get_nowait()
                self._event_queue.put_nowait(GUIEvent(type=evt_type, payload=payload))
            except Exception:
                pass

    def _put_error(self, message: str) -> None:
        self._put_event("error", message)
        logger.error("STTEngine: %s", message)

    # ------------------------------------------------------------------
    # Parsers de JSON de Vosk
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_text(raw: str) -> str:
        try:
            return (json.loads(raw).get("text") or "").strip()
        except (json.JSONDecodeError, AttributeError):
            return ""

    @staticmethod
    def _parse_partial(raw: str) -> str:
        try:
            return (json.loads(raw).get("partial") or "").strip()
        except (json.JSONDecodeError, AttributeError):
            return ""
