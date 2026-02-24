# Integración con AWS Transcribe

Este documento describe la implementación de la integración con AWS Transcribe para transcripción de voz a texto en tiempo real.

## Descripción General

La integración con AWS Transcribe permite al asistente de voz convertir audio capturado del micrófono en texto en tiempo real mediante streaming. Esta funcionalidad es fundamental para:

- Detección de palabras de activación (wake words)
- Captura de comandos de voz del usuario
- Transcripción continua con baja latencia

## Arquitectura

### Componentes Principales

```
┌─────────────────┐
│  AudioManager   │ ──> Captura audio del micrófono
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│  CommandTranscriber     │ ──> Coordina captura y transcripción
└────────┬────────────────┘
         │
         v
┌──────────────────────────────────┐
│ TranscribeStreamingClientWrapper │ ──> Cliente de AWS Transcribe
└────────┬─────────────────────────┘
         │
         v
┌─────────────────────┐
│  AWS Transcribe     │ ──> Servicio de AWS
└─────────────────────┘
```

### Flujo de Datos

1. **AudioManager** captura audio continuamente del micrófono en chunks de 1024 bytes
2. **CommandTranscriber** obtiene chunks de audio y los envía al stream
3. **TranscribeStreamingClientWrapper** mantiene conexión persistente con AWS Transcribe
4. AWS Transcribe procesa el audio y retorna transcripciones parciales y finales
5. **TranscribeStreamHandler** procesa las transcripciones y notifica mediante callbacks
6. **CommandTranscriber** detecta silencio y finaliza la captura del comando

## Módulos Implementados

### 1. transcribe_client.py

Cliente de AWS Transcribe con soporte para streaming en tiempo real.

**Clases principales:**

#### TranscribeStreamingClientWrapper

Cliente principal para interactuar con AWS Transcribe.

```python
client = TranscribeStreamingClientWrapper(
    region="us-east-1",
    language_code="es-ES",
    sample_rate=16000,
    vocabulary_name="voice-assistant-vocab",  # Opcional
    enable_language_identification=False,     # Opcional
    language_options=["es-ES", "es-MX"]      # Opcional
)
```

**Características:**
- Conexión de streaming persistente
- Soporte para vocabulario personalizado
- Detección automática de idioma (opcional)
- Manejo de errores y reconexión
- Validación de credenciales AWS

**Métodos principales:**

```python
# Iniciar stream de transcripción
await client.start_stream(
    audio_stream=audio_generator(),
    on_transcription=callback_transcription,
    on_error=callback_error
)

# Detener stream
await client.stop_stream()

# Verificar si hay stream activo
is_active = client.is_streaming()

# Transcribir un chunk único (sin streaming continuo)
result = await client.transcribe_audio_chunk(audio_data)
```

#### TranscribeStreamHandler

Handler para procesar eventos del stream de AWS Transcribe.

**Características:**
- Procesa transcripciones parciales y finales
- Calcula confianza promedio de la transcripción
- Detecta silencio basado en tiempo sin transcripciones
- Notifica mediante callbacks asíncronos o síncronos

#### TranscriptionResult

Dataclass que representa el resultado de una transcripción.

```python
@dataclass
class TranscriptionResult:
    text: str                          # Texto transcrito
    is_partial: bool                   # True si es transcripción parcial
    confidence: float                  # Confianza (0.0 - 1.0)
    language_code: Optional[str]       # Código de idioma detectado
    timestamp: Optional[float]         # Timestamp del evento
```

### 2. command_transcriber.py

Módulo que integra AudioManager con AWS Transcribe para capturar y transcribir comandos completos.

**Clases principales:**

#### CommandTranscriber

Transcriptor de comandos de voz con detección automática de finalización.

```python
transcriber = CommandTranscriber(
    audio_manager=audio_manager,
    transcribe_client=transcribe_client,
    silence_threshold=1.5,      # Segundos de silencio para finalizar
    max_command_duration=10.0   # Duración máxima del comando
)
```

**Características:**
- Captura de comandos completos con inicio y fin automático
- Detección de silencio para finalizar captura
- Timeout de duración máxima
- Callbacks para transcripciones parciales y finales
- Manejo de errores robusto

**Métodos principales:**

```python
# Configurar callbacks
transcriber.set_callbacks(
    on_partial=lambda text: print(f"Parcial: {text}"),
    on_final=lambda result: print(f"Final: {result.text}"),
    on_error=lambda error: print(f"Error: {error}")
)

# Capturar y transcribir comando
result = await transcriber.capture_command()

# Verificar si hay captura activa
is_active = transcriber.is_capturing()

# Obtener transcripción parcial actual
current = transcriber.get_current_transcription()

# Detener captura manualmente
await transcriber.stop_capture()
```

#### CommandTranscription

Dataclass que representa el resultado de un comando transcrito completo.

```python
@dataclass
class CommandTranscription:
    text: str                              # Texto final del comando
    confidence: float                      # Confianza promedio
    duration: float                        # Duración de la captura
    language_code: Optional[str]           # Idioma detectado
    partial_transcriptions: List[str]      # Historial de parciales
```

## Configuración

### Archivo config.json

```json
{
    "aws": {
        "region": "us-east-1",
        "transcribe": {
            "language_code": "es-ES",
            "sample_rate": 16000,
            "vocabulary_name": "voice-assistant-vocab"
        }
    },
    "audio": {
        "sample_rate": 16000,
        "chunk_size": 1024,
        "channels": 1
    }
}
```

### Variables de Entorno (.env)

```bash
# Credenciales AWS (requeridas)
AWS_ACCESS_KEY_ID=tu_access_key_id
AWS_SECRET_ACCESS_KEY=tu_secret_access_key
AWS_DEFAULT_REGION=us-east-1

# Configuración opcional
VOICE_ASSISTANT_LOG_LEVEL=INFO
```

### Permisos IAM Requeridos

El usuario o rol de AWS debe tener los siguientes permisos:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "transcribe:StartStreamTranscription"
            ],
            "Resource": "*"
        }
    ]
}
```

## Uso

### Ejemplo Básico

```python
import asyncio
from src.audio_manager import AudioManager
from src.transcribe_client import TranscribeStreamingClientWrapper
from src.command_transcriber import CommandTranscriber

async def main():
    # Inicializar componentes
    audio_manager = AudioManager(sample_rate=16000, chunk_size=1024)
    audio_manager.calibrate_microphone()
    
    transcribe_client = TranscribeStreamingClientWrapper(
        region="us-east-1",
        language_code="es-ES",
        sample_rate=16000
    )
    
    command_transcriber = CommandTranscriber(
        audio_manager=audio_manager,
        transcribe_client=transcribe_client
    )
    
    # Iniciar captura de audio
    audio_manager.start_continuous_capture()
    
    # Capturar comando
    print("¡Habla ahora!")
    result = await command_transcriber.capture_command()
    
    if result:
        print(f"Comando: {result.text}")
        print(f"Confianza: {result.confidence:.2%}")
    
    # Cleanup
    audio_manager.stop_continuous_capture()
    audio_manager.cleanup()

asyncio.run(main())
```

### Ejemplo con Callbacks

```python
def on_partial(text: str):
    """Callback para transcripciones parciales"""
    print(f"[PARCIAL] {text}")

def on_final(transcription: CommandTranscription):
    """Callback para transcripción final"""
    print(f"[FINAL] {transcription.text}")
    print(f"  Confianza: {transcription.confidence:.2%}")
    print(f"  Duración: {transcription.duration:.2f}s")

def on_error(error: Exception):
    """Callback para errores"""
    print(f"[ERROR] {error}")

# Configurar callbacks
command_transcriber.set_callbacks(
    on_partial=on_partial,
    on_final=on_final,
    on_error=on_error
)

# Capturar comando
result = await command_transcriber.capture_command()
```

### Ejemplo con Detección de Idioma

```python
# Habilitar detección automática de idioma
transcribe_client = TranscribeStreamingClientWrapper(
    region="us-east-1",
    language_code="es-ES",  # Idioma por defecto
    sample_rate=16000,
    enable_language_identification=True,
    language_options=["es-ES", "es-MX", "en-US"]
)

# El idioma detectado estará en result.language_code
result = await command_transcriber.capture_command()
print(f"Idioma detectado: {result.language_code}")
```

## Optimizaciones

### Baja Latencia

Para optimizar la latencia en streaming:

1. **Chunk Size:** Usar chunks pequeños (1024 bytes) para envío rápido
2. **Sample Rate:** 16000 Hz es el óptimo para voz (balance calidad/velocidad)
3. **Región AWS:** Usar región más cercana geográficamente
4. **Conexión Persistente:** Reutilizar conexión de streaming cuando sea posible

### Detección de Silencio

El sistema detecta automáticamente cuando el usuario termina de hablar:

```python
# Configurar umbral de silencio (segundos sin transcripción)
command_transcriber = CommandTranscriber(
    audio_manager=audio_manager,
    transcribe_client=transcribe_client,
    silence_threshold=1.5  # 1.5 segundos de silencio
)
```

**Recomendaciones:**
- `1.0s` - Muy rápido, puede cortar comandos largos
- `1.5s` - Balance óptimo (recomendado)
- `2.0s` - Más tolerante, pero más lento

### Vocabulario Personalizado

Para mejorar precisión con términos específicos:

1. Crear vocabulario en AWS Transcribe Console
2. Agregar términos específicos del dominio
3. Configurar en el cliente:

```python
transcribe_client = TranscribeStreamingClientWrapper(
    region="us-east-1",
    language_code="es-ES",
    sample_rate=16000,
    vocabulary_name="voice-assistant-vocab"
)
```

## Manejo de Errores

### Errores Comunes

#### 1. Credenciales no configuradas

```
ValueError: Credenciales de AWS no configuradas
```

**Solución:** Configurar variables de entorno AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY

#### 2. Error de conexión

```
BotoCoreError: Could not connect to the endpoint URL
```

**Solución:** Verificar conectividad a internet y región AWS correcta

#### 3. Timeout de transcripción

```
asyncio.TimeoutError
```

**Solución:** Aumentar max_command_duration o verificar calidad del audio

#### 4. Audio vacío

```
No se obtuvo transcripción del comando
```

**Solución:** Verificar que el micrófono esté funcionando y calibrado

### Estrategia de Reintentos

El sistema implementa manejo robusto de errores:

```python
try:
    result = await command_transcriber.capture_command()
except Exception as e:
    logger.error(f"Error capturando comando: {e}")
    # Implementar lógica de reintento si es necesario
```

## Pruebas

### Ejecutar Pruebas Unitarias

```bash
# Todas las pruebas
pytest tests/unit/test_transcribe_client.py

# Con cobertura
pytest tests/unit/test_transcribe_client.py --cov=src.transcribe_client

# Verbose
pytest tests/unit/test_transcribe_client.py -v
```

### Ejecutar Ejemplo de Integración

```bash
python examples/test_transcribe_integration.py
```

## Costos de AWS

⚠️ **IMPORTANTE:** AWS Transcribe cobra por tiempo de uso.

**Precios (región us-east-1):**
- Nivel gratuito: 60 minutos/mes durante los primeros 12 meses
- Después: $0.024 USD por minuto de audio transcrito

**Estimación de costos:**
- 1 comando de 5 segundos: ~$0.002 USD
- 100 comandos/día: ~$0.20 USD/día
- 1000 comandos/día: ~$2.00 USD/día

**Recomendaciones para reducir costos:**
- Usar detección de wake word local antes de activar Transcribe
- Implementar timeout agresivo para comandos
- Cachear respuestas comunes
- Considerar alternativas locales para desarrollo/testing

## Próximos Pasos

1. **Integrar con Wake Word Detector** (Task 4)
   - Usar Transcribe solo después de detectar wake word
   - Reducir costos y latencia

2. **Integrar con Command Processor** (Task 8)
   - Enviar transcripciones a Amazon Lex
   - Extraer intenciones y entidades

3. **Implementar Cache** (Task 23)
   - Cachear transcripciones comunes
   - Reducir llamadas a AWS

4. **Agregar Métricas** (Task 24)
   - Monitorear latencia de transcripción
   - Rastrear precisión y confianza

## Referencias

- [AWS Transcribe Documentation](https://docs.aws.amazon.com/transcribe/)
- [AWS Transcribe Streaming](https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html)
- [amazon-transcribe Python Library](https://github.com/awslabs/amazon-transcribe-streaming-sdk)
- [AWS Transcribe Pricing](https://aws.amazon.com/transcribe/pricing/)

## Soporte

Para reportar problemas o hacer preguntas sobre la integración con AWS Transcribe, consulta la documentación principal del proyecto o abre un issue en el repositorio.
