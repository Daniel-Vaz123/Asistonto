"""
Cliente de transcripción local con Vosk (sin nube, sin facturación).

Misma interfaz que los clientes AWS/Google: start_stream + stop_stream.
Funciona offline; solo necesitas descargar el modelo de idioma una vez.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Callable, AsyncIterator

from src.transcribe_client import TranscriptionResult

logger = logging.getLogger(__name__)

try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    # Silenciar mensajes LOG de Kaldi (Decoding params, Loading i-vector, etc.)
    SetLogLevel(-1)
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    Model = None
    KaldiRecognizer = None
    SetLogLevel = None


class VoskTranscribeStreamingWrapper:
    """
    Cliente de transcripción con Vosk (local, gratis).
    Compatible con la interfaz de TranscribeStreamingClientWrapper.
    """

    def __init__(
        self,
        model_path: str = "model",
        sample_rate: int = 16000,
        buffer_ms: float = 300,
    ):
        if not VOSK_AVAILABLE:
            raise RuntimeError(
                "vosk no está instalado. Ejecuta: pip install vosk"
            )
        path = Path(model_path)
        if not path.is_dir():
            raise FileNotFoundError(
                f"Modelo Vosk no encontrado en {model_path}. "
                "Ejecuta: python scripts/download_vosk_model.py"
            )
        self.model_path = str(path)
        self.sample_rate = sample_rate
        # Vosk necesita bloques de ~100–400 ms para dar resultados; chunks de 32 ms no bastan
        self._buffer_size = int(sample_rate * 2 * (buffer_ms / 1000.0))  # 16-bit = 2 bytes/sample
        self._model: Optional[Model] = None
        self._is_streaming = False
        self._sender_task: Optional[asyncio.Task] = None
        self._recognizer = None
        logger.info(
            "Cliente Vosk inicializado: model=%s, sample_rate=%s Hz, buffer=%s ms",
            model_path,
            sample_rate,
            buffer_ms,
        )

    def _get_model(self):
        if self._model is None:
            self._model = Model(self.model_path)
        return self._model

    async def start_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        on_transcription: Optional[Callable[[TranscriptionResult], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        if self._is_streaming:
            raise RuntimeError("Ya hay un stream de transcripción activo")

        self._is_streaming = True
        model = self._get_model()
        rec = KaldiRecognizer(model, self.sample_rate)
        rec.SetWords(True)
        buffer = bytearray()

        def emit_partial():
            try:
                raw = rec.PartialResult()
                if not raw:
                    return
                partial = json.loads(raw)
                text = (partial.get("partial") or "").strip()
                if text and on_transcription:
                    on_transcription(TranscriptionResult(
                        text=text,
                        is_partial=True,
                        confidence=0.5,
                        language_code=None,
                        timestamp=None,
                    ))
            except (json.JSONDecodeError, KeyError):
                pass

        def emit_result():
            try:
                raw = rec.Result()
                if not raw:
                    return None
                res = json.loads(raw)
                text = (res.get("text") or "").strip()
                if text and on_transcription:
                    on_transcription(TranscriptionResult(
                        text=text,
                        is_partial=False,
                        confidence=0.9,
                        language_code=None,
                        timestamp=None,
                    ))
                return text
            except (json.JSONDecodeError, KeyError):
                return None

        try:
            async for chunk in audio_stream:
                if not self._is_streaming or not chunk:
                    break
                buffer.extend(chunk)
                while len(buffer) >= self._buffer_size:
                    block = bytes(buffer[:self._buffer_size])
                    del buffer[:self._buffer_size]
                    if rec.AcceptWaveform(block):
                        emit_result()
                    else:
                        emit_partial()
            # Flush resto del buffer
            if buffer and on_transcription:
                if rec.AcceptWaveform(bytes(buffer)):
                    emit_result()
                else:
                    emit_partial()
            # Último resultado pendiente
            try:
                raw = rec.FinalResult()
                if raw:
                    res = json.loads(raw)
                    text = (res.get("text") or "").strip()
                    if text and on_transcription:
                        on_transcription(TranscriptionResult(
                            text=text,
                            is_partial=False,
                            confidence=0.9,
                            language_code=None,
                            timestamp=None,
                        ))
            except (json.JSONDecodeError, KeyError):
                pass
        except Exception as e:
            logger.exception("Error en Vosk: %s", e)
            if on_error:
                if asyncio.iscoroutinefunction(on_error):
                    await on_error(e)
                else:
                    on_error(e)
        finally:
            self._is_streaming = False
            logger.info("Stream Vosk finalizado")

    async def stop_stream(self) -> None:
        self._is_streaming = False

    def is_streaming(self) -> bool:
        return self._is_streaming
