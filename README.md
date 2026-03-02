# Kiro - Asistente de Voz Inteligente

Asistente de voz en español desarrollado como proyecto del **TESE** (Tecnológico de Estudios Superiores de Ecatepec) para la materia **Fundamentos de Software**.

Kiro escucha continuamente el micrófono, detecta la palabra de activación **"Asistente"** y responde comandos por voz y texto. Funciona de manera similar a Alexa: siempre está escuchando y cuando detecta la palabra clave, captura el comando del usuario, lo procesa y responde con voz sintetizada.

---

## ¿Qué hace?

1. **Escucha continua**: captura audio del micrófono en tiempo real usando PyAudio.
2. **Transcripción local**: convierte la voz a texto de forma offline usando Vosk (no requiere internet para esta parte).
3. **Detección de wake word**: identifica cuando el usuario dice "Asistente" (con tolerancia a errores de pronunciación mediante coincidencia difusa).
4. **Procesamiento de comandos**: analiza la intención del usuario (hora, fecha, chistes, saludos, etc.) usando regex y coincidencia difusa.
5. **Respuestas inteligentes con IA**: para preguntas generales que no coinciden con un comando predefinido, consulta la API de **DeepSeek** (modelo `deepseek-chat`) a través de la biblioteca `openai`.
6. **Síntesis de voz**: convierte la respuesta de texto a audio usando **Amazon Polly** y la reproduce por el altavoz.
7. **Vuelve a escuchar**: tras responder, regresa automáticamente al modo de espera.

---

## Arquitectura y Flujo

```
┌─────────────┐    ┌────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Micrófono  │───▸│  PyAudio   │───▸│   Vosk (STT)     │───▸│ CommandProcessor │───▸│  Amazon Polly   │
│  (entrada)  │    │  captura   │    │  transcripción   │    │ regex + DeepSeek │    │  (TTS salida)   │
└─────────────┘    │  continua  │    │  local offline   │    │  genera respuesta│    │  voz hablada    │
                   └────────────┘    └──────────────────┘    └──────────────────┘    └─────────────────┘
```

### Flujo detallado

1. `AudioManager` captura audio continuamente desde el micrófono en un hilo separado.
2. `WakeWordDetector` alimenta el audio a `VoskTranscribeStreamingWrapper`, que transcribe en tiempo real.
3. Cuando detecta la palabra **"Asistente"** (o variación), pasa a modo comando.
4. `CommandTranscriber` captura el comando del usuario y lo transcribe con Vosk.
5. `CommandProcessor` identifica la intención:
   - Si coincide con un comando predefinido (hora, fecha, chiste, etc.), genera la respuesta directamente.
   - Si no coincide, consulta a **DeepSeek** como fallback inteligente.
6. `ResponseGenerator` envía la respuesta de texto a **Amazon Polly**, que la convierte a audio.
7. `AudioManager` reproduce el audio por el altavoz.
8. El sistema vuelve a escuchar.

---

## Tecnologías y Bibliotecas

### Bibliotecas principales

| Biblioteca | Versión mínima | Función en el proyecto |
|---|---|---|
| **vosk** | `>=0.3.45` | **Transcripción de voz a texto (STT)**. Motor de reconocimiento de voz offline. Usa un modelo de idioma español descargado localmente para convertir el audio del micrófono a texto sin necesidad de internet. |
| **openai** | `>=1.0.0` | **Cliente para la API de DeepSeek**. Se usa la biblioteca `openai` (compatible con la API de OpenAI) apuntando al endpoint de DeepSeek (`https://api.deepseek.com`) con el modelo `deepseek-chat`. Responde preguntas generales cuando el comando no coincide con una intención predefinida. |
| **boto3** / **botocore** | `>=1.28.0` / `>=1.31.0` | **Síntesis de voz (TTS) con Amazon Polly**. Convierte las respuestas de texto del asistente a audio hablado usando la voz neural "Mia" en español. También se usa para posible integración futura con AWS Transcribe. |
| **pyaudio** | `>=0.2.13` | **Captura y reproducción de audio**. Maneja el micrófono (entrada) y el altavoz (salida) en tiempo real. Usa un buffer circular para captura continua. |
| **numpy** | `>=1.24.0` | **Procesamiento de señales de audio**. Se usa para calcular niveles de ruido (RMS), calibrar el micrófono y verificar que el nivel de audio sea adecuado. |
| **python-dotenv** | `>=1.0.0` | **Gestión de variables de entorno**. Carga las credenciales de AWS y la API key de DeepSeek desde el archivo `.env`. |
| **aiohttp** | `>=3.8.0` | **Soporte HTTP asíncrono**. Dependencia para operaciones asíncronas de red. |

### Resumen por función

| Función | Tecnología |
|---|---|
| Reconocimiento de voz (STT) | **Vosk** — offline, modelo en español `vosk-model-small-es-0.42` |
| Respuestas inteligentes (IA) | **DeepSeek** — vía biblioteca `openai` apuntando a `api.deepseek.com` |
| Síntesis de voz (TTS) | **Amazon Polly** — voz neural "Mia", idioma español (vía `boto3`) |
| Captura de audio | **PyAudio** — micrófono en tiempo real, buffer circular |
| Procesamiento de comandos | **Python** — regex, `SequenceMatcher` para coincidencia difusa |
| Programación asíncrona | **asyncio** — orquestación de componentes en tiempo real |

---

## Estructura del Proyecto

```
Asistonto/
├── src/                             # Código fuente principal
│   ├── __init__.py                  # Paquete Python (versión 0.1.0)
│   ├── main.py                      # Punto de entrada — orquesta todos los componentes
│   ├── audio_manager.py             # Captura continua de audio (micrófono) y reproducción (altavoz)
│   ├── transcribe_client_vosk.py    # Cliente de transcripción con Vosk (EN USO — local, offline)
│   ├── transcribe_client.py         # Cliente de AWS Transcribe (FUTURA IMPLEMENTACIÓN)
│   ├── wake_word_detector.py        # Detección de la palabra de activación ("Asistente")
│   ├── command_transcriber.py       # Captura y transcripción de comandos de voz
│   ├── command_processor.py         # Procesamiento de intenciones + fallback con DeepSeek
│   ├── response_generator.py        # Síntesis de voz con Amazon Polly + cache de respuestas
│   ├── models.py                    # Modelos de datos (CommandResult en uso; Reminder, Session, IoTDevice futuros)
│   ├── session_manager.py           # Gestión de sesiones (FUTURA IMPLEMENTACIÓN)
│   ├── iot_controller.py            # Control de dispositivos IoT (FUTURA IMPLEMENTACIÓN)
│   ├── data_manager.py              # Gestión de datos con SQLite (FUTURA IMPLEMENTACIÓN)
│   └── utils/
│       ├── config_loader.py         # Cargador y validador de configuración
│       └── db_schema.py             # Esquema SQLite (FUTURA IMPLEMENTACIÓN)
│
├── scripts/
│   └── download_vosk_model.py       # Descarga automática del modelo Vosk en español
│
├── model/                           # Modelo Vosk de idioma español (no se sube a git)
│   └── vosk-model-small-es-0.42/    # Modelo descargado (~50 MB)
│
├── logs/                            # Archivos de log del sistema
├── cache/                           # Cache de respuestas de Amazon Polly
├── documents/                       # Documentación del proyecto (casos de uso, acuerdos)
│
├── setup.bat                        # Script de instalación automática (Windows)
├── setup.sh                         # Script de instalación automática (Linux/Mac/Git Bash)
├── config.json                      # Configuración general del sistema
├── .env                             # Credenciales AWS + API key DeepSeek (no se sube a git)
├── .env.example                     # Plantilla de credenciales
├── requirements.txt                 # Dependencias Python
├── README.md                        # Documentación principal
├── MIGRACION_AWS.md                 # Guía para migrar de Vosk a AWS Transcribe
└── .gitignore                       # Archivos excluidos del repositorio
```

### Descripción de cada módulo

| Módulo | Estado | Descripción |
|---|---|---|
| `main.py` | EN USO | Clase `VoiceAssistantMVP` que inicializa y conecta todos los componentes. Configura callbacks, maneja el flujo principal y la interfaz de consola. |
| `audio_manager.py` | EN USO | Gestiona PyAudio: captura continua en un hilo separado con buffer circular, calibración del micrófono, reproducción de audio. |
| `transcribe_client_vosk.py` | EN USO | Transcripción local con Vosk. Procesa audio en bloques de ~500ms y emite resultados parciales y finales. |
| `wake_word_detector.py` | EN USO | Detecta la palabra "Asistente" usando coincidencia exacta y difusa. Soporta comandos inline ("Asistente qué hora es"). |
| `command_transcriber.py` | EN USO | Captura un comando de voz completo. Detecta silencio para finalizar (timeout máx. 10s). |
| `command_processor.py` | EN USO | Matriz de intenciones (regex) + fallback inteligente con DeepSeek para preguntas generales. |
| `response_generator.py` | EN USO | Amazon Polly (voz "Mia") para TTS + cache local de respuestas repetidas. |
| `models.py` | PARCIAL | `CommandResult` en uso. `Reminder`, `Session`, `IoTDevice` definidos para futura implementación. |
| `transcribe_client.py` | FUTURO | AWS Transcribe como alternativa en la nube. Ver `MIGRACION_AWS.md`. |
| `session_manager.py` | FUTURO | Gestión de sesiones de conversación con contexto persistente. |
| `iot_controller.py` | FUTURO | Control de dispositivos IoT con AWS IoT Core. |
| `data_manager.py` | FUTURO | Base de datos SQLite local + sincronización con DynamoDB. |

---

## Requisitos

- **Python 3.12 o 3.13** (PyAudio tiene wheels precompilados para estas versiones).
- **Micrófono** (el de la laptop, USB o headset).
- **Conexión a Internet** (solo para Amazon Polly y DeepSeek; Vosk funciona offline).
- **Cuenta AWS** con credenciales para Amazon Polly (tier gratuito).
- **API Key de DeepSeek** para preguntas generales con IA.

---

## Instalación

### Opción A: Script automático (recomendado)

El script crea el entorno virtual, instala dependencias y descarga el modelo Vosk automáticamente.

**Windows (doble clic o CMD):**
```
setup.bat
```

**Linux / Mac / Git Bash:**
```bash
chmod +x setup.sh
./setup.sh
```

### Opción B: Manual

```bash
cd Asistonto
python -m venv .venv
source .venv/Scripts/activate   # Git Bash en Windows
pip install -r requirements.txt
python scripts/download_vosk_model.py
```

### Configurar credenciales en `.env`

Después de la instalación, edita el archivo `.env` con tus credenciales reales:

```env
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_DEFAULT_REGION=us-east-1
DEEPSEEK_API_KEY=tu_api_key_de_deepseek
```

- Las credenciales de AWS se usan para **Amazon Polly** (síntesis de voz).
- La API key de DeepSeek se usa para **respuestas inteligentes** a preguntas generales.

### Ejecutar

```bash
python -m src.main
```

---

## Uso

- En gris aparece lo que el micrófono capta en tiempo real.
- Di **"Asistente"** y el sistema se activa.
- Di tu comando (ej. "¿qué hora es?").
- Kiro responde por texto en la consola y por voz en el altavoz.
- Vuelve a escuchar automáticamente.
- `Ctrl+C` para salir.

### Comandos predefinidos

| Intención | Ejemplos |
|---|---|
| Identidad | "¿Cómo te llamas?", "¿Quién eres?" |
| Estado | "¿Cómo estás?", "¿Qué tal?" |
| Hora | "¿Qué hora es?", "Dime la hora" |
| Fecha | "¿Qué día es hoy?", "¿Qué fecha es?" |
| Chiste | "Cuéntame un chiste", "Dime algo gracioso" |
| Saludo | "Hola", "Buenos días" |
| Despedida | "Adiós", "Gracias" |
| Capacidades | "¿Qué puedes hacer?", "Ayuda" |
| **Pregunta general** | Cualquier otra pregunta → se envía a DeepSeek |

---

## Configuración (`config.json`)

| Campo | Descripción |
|---|---|
| `transcribe_provider` | `vosk` (local, offline) o `aws` (nube) |
| `vosk.model_path` | Ruta al modelo de idioma descargado |
| `vosk.buffer_ms` | Buffer de audio en milisegundos (300–500) |
| `audio.chunk_size` | Frames por bloque de audio (4000 = 250 ms) |
| `wake_words` | Lista de palabras de activación (ej. `["asistente"]`) |
| `user_name` | Nombre del usuario para personalización de respuestas |
| `aws.polly.voice_id` | Voz de Amazon Polly (`Mia`, `Lucia`, `Enrique`) |
| `features.voice_cache_enabled` | Habilitar cache de audio para respuestas repetidas |

---

## Autores

Proyecto desarrollado para **Fundamentos de Software** — TESE (Tecnológico de Estudios Superiores de Ecatepec).
