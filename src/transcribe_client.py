"""
AWS Transcribe Streaming Client

ESTADO: No se usa actualmente — el sistema usa Vosk (transcribe_client_vosk.py).

FUTURA IMPLEMENTACIÓN:
  - Para activar AWS Transcribe como alternativa en la nube, cambiar
    en config.json: "transcribe_provider": "aws"
  - Requiere: pip install amazon-transcribe
  - Requiere: suscripción activa a AWS Transcribe en la cuenta AWS.
  - Ver MIGRACION_AWS.md para instrucciones detalladas.

Características:
- Conexión de streaming persistente con AWS Transcribe
- Soporte para español (es-ES/es-MX) con detección automática
- Manejo de transcripciones parciales y finales
- Detección de silencio para finalizar captura
- Optimizado para baja latencia en tiempo real
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, AsyncIterator
from dataclasses import dataclass
import json
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent, TranscriptResultStream


logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Resultado de transcripción de AWS Transcribe"""
    text: str
    is_partial: bool
    confidence: float
    language_code: Optional[str] = None
    timestamp: Optional[float] = None


class TranscribeStreamHandler(TranscriptResultStreamHandler):
    """
    Handler personalizado para procesar eventos del stream de AWS Transcribe.
    
    Procesa transcripciones parciales y finales, detecta silencio,
    y notifica mediante callbacks.
    """
    
    def __init__(
        self,
        transcript_result_stream: TranscriptResultStream,
        on_transcription: Optional[Callable[[TranscriptionResult], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        super().__init__(transcript_result_stream)
        self.on_transcription = on_transcription
        self.on_error = on_error
        self.last_transcript_time = None
        self.silence_threshold = 1.5  # segundos de silencio para considerar fin
        
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """
        Procesa eventos de transcripción del stream.
        
        Args:
            transcript_event: Evento de transcripción de AWS Transcribe
        """
        try:
            results = transcript_event.transcript.results
            
            for result in results:
                if not result.alternatives:
                    continue
                    
                # Obtener la mejor alternativa
                alternative = result.alternatives[0]
                transcript_text = alternative.transcript
                
                if not transcript_text:
                    continue
                
                # Calcular confianza promedio
                confidence = 0.0
                if alternative.items:
                    confidences = [
                        item.confidence for item in alternative.items
                        if item.confidence is not None
                    ]
                    if confidences:
                        confidence = sum(confidences) / len(confidences)
                
                # Crear resultado de transcripción
                transcription = TranscriptionResult(
                    text=transcript_text,
                    is_partial=result.is_partial,
                    confidence=confidence,
                    language_code=getattr(result, 'language_code', None),
                    timestamp=asyncio.get_event_loop().time()
                )
                
                # Actualizar tiempo de última transcripción
                self.last_transcript_time = transcription.timestamp
                
                # Notificar callback
                if self.on_transcription:
                    if asyncio.iscoroutinefunction(self.on_transcription):
                        await self.on_transcription(transcription)
                    else:
                        self.on_transcription(transcription)
                
                logger.debug(
                    f"Transcripción {'parcial' if result.is_partial else 'final'}: "
                    f"'{transcript_text}' (confianza: {confidence:.2f})"
                )
                
        except Exception as e:
            logger.error(f"Error procesando evento de transcripción: {e}")
            if self.on_error:
                if asyncio.iscoroutinefunction(self.on_error):
                    await self.on_error(e)
                else:
                    self.on_error(e)


class TranscribeStreamingClientWrapper:
    """
    Cliente de AWS Transcribe con soporte para streaming en tiempo real.
    
    Gestiona la conexión persistente con AWS Transcribe, envía audio
    continuamente, y recibe transcripciones parciales y finales.
    
    Attributes:
        region: Región de AWS
        language_code: Código de idioma (es-ES, es-MX, etc.)
        sample_rate: Frecuencia de muestreo del audio (16000 Hz)
        vocabulary_name: Nombre del vocabulario personalizado (opcional)
    """
    
    def __init__(
        self,
        region: str = "us-east-1",
        language_code: str = "es-ES",
        sample_rate: int = 16000,
        vocabulary_name: Optional[str] = None,
        enable_language_identification: bool = False,
        language_options: Optional[list] = None
    ):
        """
        Inicializa el cliente de AWS Transcribe.
        
        Args:
            region: Región de AWS
            language_code: Código de idioma principal
            sample_rate: Frecuencia de muestreo del audio
            vocabulary_name: Nombre del vocabulario personalizado
            enable_language_identification: Habilitar detección automática de idioma
            language_options: Lista de idiomas para detección automática
        """
        self.region = region
        self.language_code = language_code
        self.sample_rate = sample_rate
        self.vocabulary_name = vocabulary_name
        self.enable_language_identification = enable_language_identification
        self.language_options = language_options or ["es-ES", "es-MX", "en-US"]
        
        self._client: Optional[TranscribeStreamingClient] = None
        self._stream_handler: Optional[TranscribeStreamHandler] = None
        self._is_streaming = False
        self._stream_task: Optional[asyncio.Task] = None
        
        # Validar credenciales AWS
        self._validate_aws_credentials()
        
        logger.info(
            f"Cliente de AWS Transcribe inicializado: "
            f"región={region}, idioma={language_code}, "
            f"sample_rate={sample_rate}Hz"
        )
    
    def _validate_aws_credentials(self) -> None:
        """
        Valida que las credenciales de AWS estén configuradas.
        
        Raises:
            ValueError: Si las credenciales no están configuradas
        """
        # TODO: Implementar validación de credenciales AWS
        # Verificar que AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY estén configuradas
        # o que exista un perfil de AWS configurado
        
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if credentials is None:
                raise ValueError(
                    "Credenciales de AWS no configuradas. "
                    "Configure AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY "
                    "o use un perfil de AWS."
                )
            
            logger.debug("Credenciales de AWS validadas correctamente")
            
        except Exception as e:
            logger.error(f"Error validando credenciales de AWS: {e}")
            raise
    
    async def start_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        on_transcription: Optional[Callable[[TranscriptionResult], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ) -> None:
        """
        Inicia el streaming de audio a AWS Transcribe.
        
        Args:
            audio_stream: Iterador asíncrono que genera chunks de audio
            on_transcription: Callback para transcripciones recibidas
            on_error: Callback para errores
            
        Raises:
            BotoCoreError: Si hay error de conexión con AWS
        """
        if self._is_streaming:
            # En lugar de fallar, detenemos el stream anterior y abrimos uno nuevo.
            logger.warning(
                "Se intentó iniciar un nuevo stream de transcripción mientras otro seguía activo; "
                "deteniendo el stream anterior."
            )
            await self.stop_stream()
        
        try:
            # Crear cliente de Transcribe
            self._client = TranscribeStreamingClient(region=self.region)
            
            # Configurar parámetros del stream
            stream_params = {
                "language_code": self.language_code,
                "media_sample_rate_hz": self.sample_rate,
                "media_encoding": "pcm",
            }
            
            # Agregar vocabulario personalizado si está configurado
            if self.vocabulary_name:
                stream_params["vocabulary_name"] = self.vocabulary_name
            
            # Habilitar detección de idioma si está configurado
            if self.enable_language_identification:
                stream_params["identify_language"] = True
                stream_params["language_options"] = ",".join(self.language_options)
                # Remover language_code cuando se usa identificación de idioma
                del stream_params["language_code"]
            
            logger.info(f"Iniciando stream de AWS Transcribe con parámetros: {stream_params}")
            
            # Iniciar stream
            stream = await self._client.start_stream_transcription(**stream_params)
            
            # Crear handler para procesar transcripciones
            self._stream_handler = TranscribeStreamHandler(
                stream.output_stream,
                on_transcription=on_transcription,
                on_error=on_error
            )
            
            self._is_streaming = True
            
            send_task = asyncio.create_task(
                self._send_audio_stream(stream, audio_stream)
            )
            receive_task = asyncio.create_task(
                self._stream_handler.handle_events()
            )
            
            # Esperar a que terminen; timeout evita que se cuelgue si AWS no cierra el stream
            done, pending = await asyncio.wait(
                [send_task, receive_task],
                timeout=None,
                return_when=asyncio.FIRST_EXCEPTION,
            )
            # Si send terminó (audio_stream agotado), dar un momento al receive para procesar últimos eventos
            if send_task in done and receive_task in pending:
                try:
                    await asyncio.wait_for(receive_task, timeout=3.0)
                except asyncio.TimeoutError:
                    receive_task.cancel()
                    logger.debug("Receive task cancelado tras timeout post-send")
            for t in pending:
                if not t.done():
                    t.cancel()
            
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error de AWS al iniciar stream: {e}")
            if on_error:
                if asyncio.iscoroutinefunction(on_error):
                    await on_error(e)
                else:
                    on_error(e)
            raise
        except Exception as e:
            logger.error(f"Error inesperado al iniciar stream: {e}")
            if on_error:
                if asyncio.iscoroutinefunction(on_error):
                    await on_error(e)
                else:
                    on_error(e)
            raise
        finally:
            self._is_streaming = False
            logger.info("Stream de AWS Transcribe finalizado")
    
    async def _send_audio_stream(
        self,
        stream,
        audio_stream: AsyncIterator[bytes]
    ) -> None:
        """
        Envía chunks de audio al stream de AWS Transcribe.
        
        Args:
            stream: Stream de AWS Transcribe
            audio_stream: Iterador asíncrono de chunks de audio
        """
        try:
            async for audio_chunk in audio_stream:
                if not self._is_streaming:
                    break
                await stream.input_stream.send_audio_event(audio_chunk=audio_chunk)
                await asyncio.sleep(0.01)
            
            try:
                await asyncio.wait_for(
                    stream.input_stream.end_stream(), timeout=2.0
                )
            except asyncio.TimeoutError:
                logger.warning("end_stream() tardó más de 2 s; continuando sin esperar")
            logger.debug("Stream de audio finalizado")
            
        except Exception as e:
            logger.error(f"Error enviando audio al stream: {e}")
            raise
    
    async def stop_stream(self) -> None:
        """
        Detiene el stream de transcripción activo.
        """
        if not self._is_streaming:
            logger.warning("No hay stream activo para detener")
            return
        
        self._is_streaming = False
        
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stream de AWS Transcribe detenido")
    
    def is_streaming(self) -> bool:
        """
        Verifica si hay un stream activo.
        
        Returns:
            True si hay un stream activo, False en caso contrario
        """
        return self._is_streaming
    
    async def transcribe_audio_chunk(
        self,
        audio_data: bytes,
        timeout: float = 5.0
    ) -> Optional[TranscriptionResult]:
        """
        Transcribe un chunk de audio único (sin streaming continuo).
        
        Útil para transcripciones puntuales sin mantener un stream persistente.
        
        Args:
            audio_data: Datos de audio en formato PCM
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            Resultado de transcripción o None si no hay transcripción
        """
        result = None
        
        async def audio_generator():
            yield audio_data
        
        def on_transcription(transcription: TranscriptionResult):
            nonlocal result
            if not transcription.is_partial:
                result = transcription
        
        try:
            await asyncio.wait_for(
                self.start_stream(audio_generator(), on_transcription=on_transcription),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout transcribiendo audio después de {timeout}s")
        
        return result
    
    def __del__(self):
        """Limpieza al destruir el objeto"""
        if self._is_streaming:
            logger.warning("Cliente destruido con stream activo")
