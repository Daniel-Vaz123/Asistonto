"""
Cliente de transcripción con Vosk (modo gratuito / offline)

Permite usar el asistente sin AWS: reconocimiento de voz local con Vosk.
Misma interfaz que TranscribeStreamingClientWrapper para poder intercambiarlo.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Callable, AsyncIterator

from src.transcribe_client import TranscriptionResult

logger = logging.getLogger(__name__)


class VoskTranscribeStreamingWrapper:
    """
    Cliente de transcripción con Vosk (offline, gratuito).
    
    Compatible con la interfaz de TranscribeStreamingClientWrapper:
    - start_stream(audio_stream, on_transcription, on_error)
    - stop_stream()
    - is_streaming()
    """

    def __init__(
        self,
        model_path: str,
        sample_rate: int = 16000,
    ):
        """
        Args:
            model_path: Ruta a la carpeta del modelo Vosk (ej. model/vosk-model-small-es-0.42)
            sample_rate: Frecuencia de muestreo del audio (16000 Hz)
        """
        self.model_path = Path(model_path)
        self.sample_rate = sample_rate
        self._model = None
        self._recognizer = None
        self._is_streaming = False
        self._stream_task: Optional[asyncio.Task] = None
        self._cancel_stream = False

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Modelo Vosk no encontrado en {self.model_path}. "
                "Descarga un modelo español desde https://alphacephei.com/vosk/models "
                "y descomprímelo en esa ruta (ej. vosk-model-small-es-0.42)."
            )
        logger.info(f"VoskTranscribeStreamingWrapper: modelo en {self.model_path}, sample_rate={sample_rate}")

    def _ensure_model(self):
        """Carga el modelo Vosk si aún no está cargado."""
        if self._model is None:
            from vosk import Model
            self._model = Model(str(self.model_path))
            logger.info("Modelo Vosk cargado correctamente")

    async def start_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        on_transcription: Optional[Callable[[TranscriptionResult], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """
        Inicia el streaming de audio y transcribe con Vosk.
        
        Compatible con la interfaz de AWS Transcribe.
        """
        if self._is_streaming:
            raise RuntimeError("Ya hay un stream de transcripción activo")

        self._is_streaming = True
        self._cancel_stream = False

        async def _run():
            try:
                self._ensure_model()
                from vosk import KaldiRecognizer
                rec = KaldiRecognizer(self._model, self.sample_rate)
                rec.SetWords(True)

                async for audio_chunk in audio_stream:
                    if self._cancel_stream:
                        break
                    if not audio_chunk:
                        await asyncio.sleep(0.01)
                        continue
                    # Vosk espera bytes PCM 16-bit mono
                    if rec.AcceptWaveform(audio_chunk):
                        result = json.loads(rec.Result())
                        text = (result.get("text") or "").strip()
                        if text and on_transcription:
                            tr = TranscriptionResult(
                                text=text,
                                is_partial=False,
                                confidence=0.95,
                                language_code="es",
                            )
                            if asyncio.iscoroutinefunction(on_transcription):
                                await on_transcription(tr)
                            else:
                                on_transcription(tr)
                    else:
                        partial = json.loads(rec.PartialResult())
                        text = (partial.get("partial") or "").strip()
                        if text and on_transcription:
                            tr = TranscriptionResult(
                                text=text,
                                is_partial=True,
                                confidence=0.8,
                                language_code="es",
                            )
                            if asyncio.iscoroutinefunction(on_transcription):
                                await on_transcription(tr)
                            else:
                                on_transcription(tr)
                    await asyncio.sleep(0.01)

                # Resultado final pendiente
                final = json.loads(rec.FinalResult())
                text = (final.get("text") or "").strip()
                if text and on_transcription:
                    tr = TranscriptionResult(
                        text=text,
                        is_partial=False,
                        confidence=0.95,
                        language_code="es",
                    )
                    if asyncio.iscoroutinefunction(on_transcription):
                        await on_transcription(tr)
                    else:
                        on_transcription(tr)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error en stream Vosk: {e}")
                if on_error:
                    if asyncio.iscoroutinefunction(on_error):
                        await on_error(e)
                    else:
                        on_error(e)
            finally:
                self._is_streaming = False
                logger.info("Stream de Vosk finalizado")

        self._stream_task = asyncio.create_task(_run())
        await self._stream_task

    async def stop_stream(self) -> None:
        """Detiene el stream de transcripción."""
        if not self._is_streaming:
            return
        self._cancel_stream = True
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
        self._is_streaming = False
        logger.info("Stream de Vosk detenido")

    def is_streaming(self) -> bool:
        return self._is_streaming
