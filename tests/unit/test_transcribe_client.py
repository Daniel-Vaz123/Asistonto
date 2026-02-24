"""
Pruebas unitarias para TranscribeStreamingClientWrapper

Estas pruebas verifican la funcionalidad básica del cliente de AWS Transcribe
sin hacer llamadas reales a AWS (usando mocks).
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from src.transcribe_client import (
    TranscribeStreamingClientWrapper,
    TranscriptionResult,
    TranscribeStreamHandler
)


class TestTranscribeStreamingClientWrapper:
    """Pruebas para TranscribeStreamingClientWrapper"""
    
    @pytest.fixture
    def mock_boto_session(self):
        """Mock de boto3 session con credenciales"""
        with patch('boto3.Session') as mock_session:
            mock_credentials = Mock()
            mock_credentials.access_key = 'test_key'
            mock_credentials.secret_key = 'test_secret'
            mock_session.return_value.get_credentials.return_value = mock_credentials
            yield mock_session
    
    def test_initialization(self, mock_boto_session):
        """Prueba la inicialización del cliente"""
        client = TranscribeStreamingClientWrapper(
            region="us-east-1",
            language_code="es-ES",
            sample_rate=16000
        )
        
        assert client.region == "us-east-1"
        assert client.language_code == "es-ES"
        assert client.sample_rate == 16000
        assert not client.is_streaming()
    
    def test_initialization_with_vocabulary(self, mock_boto_session):
        """Prueba inicialización con vocabulario personalizado"""
        client = TranscribeStreamingClientWrapper(
            region="us-east-1",
            language_code="es-ES",
            sample_rate=16000,
            vocabulary_name="test-vocab"
        )
        
        assert client.vocabulary_name == "test-vocab"
    
    def test_initialization_with_language_identification(self, mock_boto_session):
        """Prueba inicialización con detección de idioma"""
        client = TranscribeStreamingClientWrapper(
            region="us-east-1",
            language_code="es-ES",
            sample_rate=16000,
            enable_language_identification=True,
            language_options=["es-ES", "es-MX", "en-US"]
        )
        
        assert client.enable_language_identification is True
        assert "es-ES" in client.language_options
        assert "es-MX" in client.language_options
        assert "en-US" in client.language_options
    
    def test_validate_aws_credentials_missing(self):
        """Prueba validación cuando faltan credenciales"""
        with patch('boto3.Session') as mock_session:
            mock_session.return_value.get_credentials.return_value = None
            
            with pytest.raises(ValueError, match="Credenciales de AWS no configuradas"):
                TranscribeStreamingClientWrapper()
    
    def test_is_streaming_initially_false(self, mock_boto_session):
        """Prueba que is_streaming es False inicialmente"""
        client = TranscribeStreamingClientWrapper()
        assert not client.is_streaming()
    
    @pytest.mark.asyncio
    async def test_stop_stream_when_not_streaming(self, mock_boto_session):
        """Prueba detener stream cuando no hay stream activo"""
        client = TranscribeStreamingClientWrapper()
        
        # No debería lanzar excepción
        await client.stop_stream()
        assert not client.is_streaming()


class TestTranscriptionResult:
    """Pruebas para TranscriptionResult"""
    
    def test_transcription_result_creation(self):
        """Prueba creación de TranscriptionResult"""
        result = TranscriptionResult(
            text="hola mundo",
            is_partial=False,
            confidence=0.95,
            language_code="es-ES",
            timestamp=123.45
        )
        
        assert result.text == "hola mundo"
        assert result.is_partial is False
        assert result.confidence == 0.95
        assert result.language_code == "es-ES"
        assert result.timestamp == 123.45
    
    def test_transcription_result_partial(self):
        """Prueba TranscriptionResult parcial"""
        result = TranscriptionResult(
            text="hola",
            is_partial=True,
            confidence=0.8
        )
        
        assert result.text == "hola"
        assert result.is_partial is True
        assert result.confidence == 0.8
        assert result.language_code is None
        assert result.timestamp is None


class TestTranscribeStreamHandler:
    """Pruebas para TranscribeStreamHandler"""
    
    @pytest.fixture
    def mock_transcript_stream(self):
        """Mock del stream de transcripción"""
        return Mock()
    
    def test_handler_initialization(self, mock_transcript_stream):
        """Prueba inicialización del handler"""
        on_transcription = Mock()
        on_error = Mock()
        
        handler = TranscribeStreamHandler(
            mock_transcript_stream,
            on_transcription=on_transcription,
            on_error=on_error
        )
        
        assert handler.on_transcription == on_transcription
        assert handler.on_error == on_error
        assert handler.silence_threshold == 1.5
    
    @pytest.mark.asyncio
    async def test_handle_transcript_event_with_results(self, mock_transcript_stream):
        """Prueba manejo de evento con transcripción"""
        on_transcription = Mock()
        handler = TranscribeStreamHandler(
            mock_transcript_stream,
            on_transcription=on_transcription
        )
        
        # Crear mock de evento de transcripción
        mock_event = Mock()
        mock_result = Mock()
        mock_result.is_partial = False
        mock_alternative = Mock()
        mock_alternative.transcript = "hola mundo"
        mock_alternative.items = []
        mock_result.alternatives = [mock_alternative]
        mock_event.transcript.results = [mock_result]
        
        # Procesar evento
        await handler.handle_transcript_event(mock_event)
        
        # Verificar que se llamó al callback
        assert on_transcription.called
        call_args = on_transcription.call_args[0][0]
        assert isinstance(call_args, TranscriptionResult)
        assert call_args.text == "hola mundo"
        assert call_args.is_partial is False
    
    @pytest.mark.asyncio
    async def test_handle_transcript_event_empty_results(self, mock_transcript_stream):
        """Prueba manejo de evento sin resultados"""
        on_transcription = Mock()
        handler = TranscribeStreamHandler(
            mock_transcript_stream,
            on_transcription=on_transcription
        )
        
        # Crear mock de evento sin resultados
        mock_event = Mock()
        mock_event.transcript.results = []
        
        # Procesar evento
        await handler.handle_transcript_event(mock_event)
        
        # No debería llamar al callback
        assert not on_transcription.called


# Pruebas de integración (requieren credenciales AWS reales)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcribe_real_audio():
    """
    Prueba de integración con AWS Transcribe real.
    
    NOTA: Esta prueba requiere credenciales AWS válidas y hace
    llamadas reales a AWS Transcribe (puede generar costos).
    
    Para ejecutar: pytest -m integration
    """
    pytest.skip("Prueba de integración deshabilitada por defecto")
    
    # TODO: Implementar prueba de integración real cuando sea necesario
    # client = TranscribeStreamingClientWrapper(
    #     region="us-east-1",
    #     language_code="es-ES",
    #     sample_rate=16000
    # )
    # 
    # # Generar audio de prueba
    # async def audio_generator():
    #     # Generar audio sintético o cargar archivo de prueba
    #     pass
    # 
    # results = []
    # def on_transcription(result):
    #     results.append(result)
    # 
    # await client.start_stream(audio_generator(), on_transcription=on_transcription)
    # 
    # assert len(results) > 0
