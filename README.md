# Kiro - Asistente de Voz Inteligente

Asistente de voz en español desarrollado como proyecto del **TESE** (Tecnológico de Estudios Superiores de Ecatepec) para la materia **Fundamentos de Software**.

Kiro escucha continuamente el micrófono, detecta la palabra de activación **"Asistente"** y responde comandos por voz y texto. Funciona de manera similar a Alexa: siempre está escuchando y cuando detecta la palabra clave, captura el comando del usuario, lo procesa y responde con voz sintetizada.

---

## ¿Qué hace?

1. **Escucha continua**: captura audio del micrófono en tiempo real usando PyAudio.
2. **Transcripción local**: convierte la voz a texto de forma offline usando Vosk (no requiere internet para esta parte).
3. **Detección de wake word**: identifica cuando el usuario dice "Asistente" (con tolerancia a errores de pronunciación mediante coincidencia difusa).
4. **Clasificación inteligente de comandos**: usa **Smart LLM Router** con DeepSeek para clasificar intenciones con lenguaje natural (conversacional, notas, YouTube, apps, web).
5. **Sistema RAG local**: indexa y busca en notas personales (.md) usando **LocalKnowledgeReader** con búsqueda TF-IDF.
6. **Cache vectorial**: almacena preguntas/respuestas en **Supabase** (pgvector) para reducir llamadas a DeepSeek y ahorrar créditos.
7. **Respuestas inteligentes con IA**: para preguntas generales, consulta la API de **DeepSeek** (modelo `deepseek-chat`) con contexto de notas o búsqueda web.
8. **Síntesis de voz**: convierte la respuesta de texto a audio usando **Amazon Polly** y la reproduce por el altavoz.
9. **Vuelve a escuchar**: tras responder, regresa automáticamente al modo de espera.

---

## Arquitectura y Flujo

```
┌─────────────┐    ┌────────────┐    ┌──────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│  Micrófono  │───▸│  PyAudio   │───▸│   Vosk (STT)     │───▸│  SmartLLMRouter      │───▸│  Amazon Polly   │
│  (entrada)  │    │  captura   │    │  transcripción   │    │  DeepSeek + JSON     │    │  (TTS salida)   │
└─────────────┘    │  continua  │    │  local offline   │    │  clasificación       │    │  voz hablada    │
                   └────────────┘    └──────────────────┘    └──────────────────────┘    └─────────────────┘
                                                                        │
                                                                        ├─▸ LocalKnowledgeReader (RAG)
                                                                        │   └─▸ TF-IDF search en notas .md
                                                                        │
                                                                        ├─▸ VectorStore (Supabase)
                                                                        │   └─▸ Cache Q&A con embeddings
                                                                        │
                                                                        └─▸ ActionRouter
                                                                            └─▸ YouTube, Apps, Web, Notas
```

### Flujo detallado (Fase 4)

1. `AudioManager` captura audio continuamente desde el micrófono en un hilo separado.
2. `WakeWordDetector` alimenta el audio a `VoskTranscribeStreamingWrapper`, que transcribe en tiempo real.
3. Cuando detecta la palabra **"Asistente"** (o variación), pasa a modo comando.
4. `CommandTranscriber` captura el comando del usuario y lo transcribe con Vosk.
5. `SmartLLMRouter` clasifica el comando usando **DeepSeek** con few-shot prompting:
   - Retorna JSON estructurado: `{intent, parameters, confidence}`
   - Soporta: conversational, file (notas), youtube, app, web
   - Timeout de 3 segundos con fallback a conversational
6. `CommandProcessor` procesa según el intent:
   - **Conversational**: Busca en cache vectorial (Supabase) → si no hay hit, consulta DeepSeek → guarda respuesta en cache
   - **File (crear nota)**: Guarda en `data/notas.md` → re-indexa LocalKnowledgeReader
   - **File (leer nota)**: Busca con LocalKnowledgeReader (TF-IDF) → inyecta contexto en DeepSeek → responde
   - **YouTube/App/Web**: Ejecuta acción del sistema con ActionRouter
7. `ResponseGenerator` envía la respuesta de texto a **Amazon Polly**, que la convierte a audio.
8. `AudioManager` reproduce el audio por el altavoz con **Auto-Mute** (silencia micrófono durante reproducción).
9. El sistema vuelve a escuchar.

---

## Tecnologías y Bibliotecas

### Bibliotecas principales

| Biblioteca | Versión mínima | Función en el proyecto |
|---|---|---|
| **vosk** | `>=0.3.45` | **Transcripción de voz a texto (STT)**. Motor de reconocimiento de voz offline. Usa un modelo de idioma español descargado localmente para convertir el audio del micrófono a texto sin necesidad de internet. |
| **openai** | `>=1.0.0` | **Cliente para la API de DeepSeek**. Se usa la biblioteca `openai` (compatible con la API de OpenAI) apuntando al endpoint de DeepSeek (`https://api.deepseek.com`) con el modelo `deepseek-chat`. Responde preguntas generales y clasifica intenciones con JSON estructurado. |
| **boto3** / **botocore** | `>=1.28.0` / `>=1.31.0` | **Síntesis de voz (TTS) con Amazon Polly**. Convierte las respuestas de texto del asistente a audio hablado usando la voz neural "Mia" en español. También se usa para posible integración futura con AWS Transcribe. |
| **pyaudio** | `>=0.2.13` | **Captura y reproducción de audio**. Maneja el micrófono (entrada) y el altavoz (salida) en tiempo real. Usa un buffer circular para captura continua. |
| **numpy** | `>=1.24.0` | **Procesamiento de señales de audio**. Se usa para calcular niveles de ruido (RMS), calibrar el micrófono y verificar que el nivel de audio sea adecuado. |
| **python-dotenv** | `>=1.0.0` | **Gestión de variables de entorno**. Carga las credenciales de AWS, DeepSeek, Supabase y Hugging Face desde el archivo `.env`. |
| **aiohttp** | `>=3.8.0` | **Soporte HTTP asíncrono**. Dependencia para operaciones asíncronas de red. |
| **sentence-transformers** | `>=2.2.0` | **Generación de embeddings**. Modelo `all-MiniLM-L6-v2` (70% más rápido que multilingüe) para cache vectorial en Supabase. |
| **supabase** | `>=2.0.0` | **Base de datos vectorial**. Cliente de Supabase para cache de Q&A con pgvector (búsqueda por similitud coseno). |
| **chromadb** | `>=0.4.0` | **Base de datos vectorial local** (alternativa a Supabase). Almacenamiento persistente de embeddings en disco. |

### Resumen por función

| Función | Tecnología |
|---|---|
| Reconocimiento de voz (STT) | **Vosk** — offline, modelo en español `vosk-model-small-es-0.42` |
| Clasificación de intenciones | **SmartLLMRouter** — DeepSeek con few-shot prompting, JSON estructurado |
| Sistema RAG local | **LocalKnowledgeReader** — TF-IDF search en archivos .md, inyección de contexto |
| Cache vectorial | **VectorStore** — Supabase (pgvector) o ChromaDB, embeddings con `all-MiniLM-L6-v2` |
| Respuestas inteligentes (IA) | **DeepSeek** — vía biblioteca `openai` apuntando a `api.deepseek.com` |
| Síntesis de voz (TTS) | **Amazon Polly** — voz neural "Mia", idioma español (vía `boto3`) |
| Captura de audio | **PyAudio** — micrófono en tiempo real, buffer circular, Auto-Mute |
| Procesamiento de comandos | **Python** — regex, `SequenceMatcher` para coincidencia difusa |
| Programación asíncrona | **asyncio** + **ThreadingManager** — orquestación de componentes en tiempo real con timeouts |

---

## Estructura del Proyecto

```
Asistonto/
├── src/                             # Código fuente principal
│   ├── __init__.py                  # Paquete Python (versión 0.1.0)
│   ├── main.py                      # Punto de entrada — orquesta todos los componentes
│   ├── audio_manager.py             # Captura continua de audio (micrófono) y reproducción (altavoz) con Auto-Mute
│   ├── transcribe_client_vosk.py    # Cliente de transcripción con Vosk (EN USO — local, offline)
│   ├── transcribe_client.py         # Cliente de AWS Transcribe (FUTURA IMPLEMENTACIÓN)
│   ├── wake_word_detector.py        # Detección de la palabra de activación ("Asistente")
│   ├── command_transcriber.py       # Captura y transcripción de comandos de voz
│   ├── command_processor.py         # Procesamiento de comandos con Smart Router + RAG + cache vectorial
│   ├── smart_llm_router.py          # Clasificación inteligente con DeepSeek (JSON estructurado, few-shot)
│   ├── local_knowledge_reader.py    # Sistema RAG local (indexa .md, búsqueda TF-IDF, inyección de contexto)
│   ├── vector_store.py              # Cache vectorial Q&A (Supabase/ChromaDB, embeddings all-MiniLM-L6-v2)
│   ├── intent_classifier.py         # Clasificador de intenciones basado en regex (fallback de Smart Router)
│   ├── action_router.py             # Enrutador de acciones del sistema (YouTube, Apps, Web, Notas)
│   ├── response_generator.py        # Síntesis de voz con Amazon Polly + cache de respuestas
│   ├── query_router.py              # Determina si una pregunta requiere búsqueda web
│   ├── web_search.py                # Módulo de búsqueda web (DuckDuckGo)
│   ├── threading_manager.py         # Gestor de threads con timeouts para operaciones pesadas
│   ├── rich_ui_manager.py           # Interfaz de consola con Rich (paneles de estado)
│   ├── feedback_preventer.py        # Auto-Mute: silencia micrófono durante reproducción de voz
│   ├── models.py                    # Modelos de datos (CommandResult, SystemState, etc.)
│   ├── session_manager.py           # Gestión de sesiones (FUTURA IMPLEMENTACIÓN)
│   ├── iot_controller.py            # Control de dispositivos IoT (FUTURA IMPLEMENTACIÓN)
│   ├── data_manager.py              # Gestión de datos con SQLite (FUTURA IMPLEMENTACIÓN)
│   └── actions/                     # Acciones del sistema (Phase 3)
│       ├── action.py                # Clase base para acciones
│       ├── youtube_action.py        # Reproducir videos de YouTube
│       ├── app_launcher_action.py   # Abrir aplicaciones del sistema
│       ├── web_browser_action.py    # Abrir sitios web
│       └── file_writer_action.py    # Crear y guardar notas en data/notas.md
│
├── scripts/
│   ├── download_vosk_model.py       # Descarga automática del modelo Vosk en español
│   ├── check_supabase_vector.py     # Verificar conexión y configuración de Supabase
│   └── test_supabase_insert.py      # Probar inserción de embeddings en Supabase
│
├── model/                           # Modelo Vosk de idioma español (no se sube a git)
│   └── vosk-model-small-es-0.42/    # Modelo descargado (~50 MB)
│
├── data/                            # Datos del usuario (notas, conocimiento local)
│   ├── notas.md                     # Notas personales del usuario (indexadas por RAG)
│   └── chroma_db/                   # Base de datos vectorial local (ChromaDB)
│
├── logs/                            # Archivos de log del sistema
├── cache/                           # Cache de respuestas de Amazon Polly
├── documents/                       # Documentación del proyecto (casos de uso, acuerdos)
│   └── 00-CASOS DE USO/             # Casos de uso del sistema
│
├── docs/
│   └── SUPABASE_VECTOR_SETUP.md     # Guía de configuración de Supabase para cache vectorial
│
├── setup.bat                        # Script de instalación automática (Windows)
├── setup.sh                         # Script de instalación automática (Linux/Mac/Git Bash)
├── config.json                      # Configuración general del sistema
├── .env                             # Credenciales AWS + DeepSeek + Supabase + HF (no se sube a git)
├── .env.example                     # Plantilla de credenciales
├── requirements.txt                 # Dependencias Python
├── README.md                        # Documentación principal
├── MIGRACION_AWS.md                 # Guía para migrar de Vosk a AWS Transcribe
└── .gitignore                       # Archivos excluidos del repositorio
```

### Descripción de cada módulo (Fase 4)

| Módulo | Estado | Descripción |
|---|---|---|
| `main.py` | EN USO | Clase `VoiceAssistantMVP` que inicializa y conecta todos los componentes. Configura callbacks, maneja el flujo principal y la interfaz de consola. |
| `audio_manager.py` | EN USO | Gestiona PyAudio: captura continua en un hilo separado con buffer circular, calibración del micrófono, reproducción de audio con Auto-Mute. |
| `transcribe_client_vosk.py` | EN USO | Transcripción local con Vosk. Procesa audio en bloques de ~500ms y emite resultados parciales y finales. |
| `wake_word_detector.py` | EN USO | Detecta la palabra "Asistente" usando coincidencia exacta y difusa. Soporta comandos inline ("Asistente qué hora es"). |
| `command_transcriber.py` | EN USO | Captura un comando de voz completo. Detecta silencio para finalizar (timeout máx. 10s). |
| `smart_llm_router.py` | EN USO | Clasificador inteligente con DeepSeek. Retorna JSON estructurado con intent, parameters y confidence. Timeout de 3s con fallback. |
| `local_knowledge_reader.py` | EN USO | Sistema RAG local. Indexa archivos .md en data/, busca con TF-IDF, formatea contexto para inyección en DeepSeek. |
| `vector_store.py` | EN USO | Cache vectorial Q&A. Supabase (pgvector) o ChromaDB. Embeddings con all-MiniLM-L6-v2. Reduce llamadas a DeepSeek. |
| `command_processor.py` | EN USO | Orquesta Smart Router, RAG, cache vectorial, web search y acciones. Procesa comandos con threading y timeouts. |
| `intent_classifier.py` | FALLBACK | Clasificador basado en regex. Usado como fallback si Smart Router falla. |
| `action_router.py` | EN USO | Enruta y ejecuta acciones del sistema (YouTube, Apps, Web, Notas). |
| `response_generator.py` | EN USO | Amazon Polly (voz "Mia") para TTS + cache local de respuestas repetidas. |
| `query_router.py` | EN USO | Determina si una pregunta requiere búsqueda web (keywords, patrones). |
| `web_search.py` | EN USO | Búsqueda web con DuckDuckGo. Extrae snippets relevantes para contexto. |
| `threading_manager.py` | EN USO | Gestor de threads con timeouts. Ejecuta operaciones pesadas (embeddings, Supabase, búsqueda) sin bloquear. |
| `rich_ui_manager.py` | EN USO | Interfaz de consola con Rich. Paneles de estado (Escuchando, Procesando, Buscando, Hablando). |
| `feedback_preventer.py` | EN USO | Auto-Mute: silencia micrófono durante reproducción de voz para evitar retroalimentación. |
| `models.py` | PARCIAL | `CommandResult`, `SystemState` en uso. `Reminder`, `Session`, `IoTDevice` definidos para futura implementación. |
| `actions/*.py` | EN USO | Acciones del sistema: YouTube, Apps, Web, Notas. Ejecutadas por ActionRouter. |
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
# AWS (Amazon Polly para TTS)
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_DEFAULT_REGION=us-east-1

# DeepSeek (clasificación de intenciones + respuestas inteligentes)
DEEPSEEK_API_KEY=tu_api_key_de_deepseek

# Hugging Face (embeddings para cache vectorial)
HF_TOKEN=tu_hugging_face_token

# Supabase (cache vectorial Q&A con pgvector)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_KEY=tu_service_role_key
```

- **AWS**: Las credenciales de AWS se usan para **Amazon Polly** (síntesis de voz).
- **DeepSeek**: La API key de DeepSeek se usa para **clasificación de intenciones** (Smart Router) y **respuestas inteligentes** a preguntas generales.
- **Hugging Face**: Token para descargar modelos de embeddings (`all-MiniLM-L6-v2`) usado en el cache vectorial.
- **Supabase**: URL y service role key para el cache vectorial Q&A (reduce llamadas a DeepSeek). Ver `docs/SUPABASE_VECTOR_SETUP.md` para configuración.

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
| **Crear nota** | "Anota que mañana tengo clase", "Guarda que el proyecto va al 80%", "Recuérdame comprar leche" |
| **Leer notas** | "¿Qué notas tengo sobre el proyecto?", "Revisa mis apuntes", "Busca en mis notas sobre la reunión" |
| **YouTube** | "Pon música relajante en YouTube", "Reproduce videos de Python" |
| **Abrir app** | "Abre Chrome", "Inicia Spotify" |
| **Búsqueda web** | "Busca en Google sobre Python", "Ve a Facebook" |
| **Pregunta general** | Cualquier otra pregunta → se envía a DeepSeek (con cache vectorial) |

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
| `features.web_search_enabled` | Habilitar búsqueda web con DuckDuckGo |
| `features.smart_router_enabled` | Habilitar Smart LLM Router (clasificación con DeepSeek) |
| `features.local_rag_enabled` | Habilitar sistema RAG local (búsqueda en notas) |
| `features.vector_cache_enabled` | Habilitar cache vectorial Q&A (Supabase/ChromaDB) |
| `features.vector_cache_backend` | Backend del cache vectorial: `supabase` o `chroma` |

---

## Fase 4: Smart Router + Local RAG + Cache Vectorial

### Smart LLM Router

El **Smart LLM Router** reemplaza el clasificador basado en regex con clasificación inteligente usando DeepSeek:

- **Few-shot prompting**: Incluye 8+ ejemplos de cada tipo de intent para mejorar precisión
- **JSON estructurado**: Retorna `{intent, parameters, confidence}` para procesamiento consistente
- **Timeout de 3 segundos**: Si DeepSeek tarda mucho, usa fallback conversational
- **Confidence threshold**: Solo acepta clasificaciones con confidence >= 0.7
- **Tolerancia a errores**: Entiende variaciones naturales ("apunta por ahí que...", "recuérdame que...")

Intents soportados:
- `conversational`: Preguntas generales
- `file`: Crear/leer notas (con parámetros `content` o `query` + `action: read`)
- `youtube`: Reproducir videos
- `app`: Abrir aplicaciones
- `web`: Búsqueda web o abrir sitios

### Local RAG (LocalKnowledgeReader)

Sistema de **Retrieval-Augmented Generation** local para notas del usuario:

- **Indexación automática**: Escanea archivos .md en `data/` al iniciar
- **Búsqueda TF-IDF**: Rankea notas por relevancia usando frecuencia de términos
- **Inyección de contexto**: Formatea notas relevantes y las inyecta en el system prompt de DeepSeek
- **Límite de tokens**: Trunca contexto a 2000 tokens para no exceder límites de API
- **Re-indexación**: Detecta cambios en archivos y re-indexa automáticamente
- **Fallback de dos niveles**: Si no encuentra resultados con query específico, reintenta con comando completo

Flujo de lectura de notas:
1. Usuario: "¿Qué notas tengo sobre el proyecto?"
2. Smart Router clasifica como `file` con `action: read` y `query: proyecto`
3. LocalKnowledgeReader busca en notas con TF-IDF
4. Formatea top 3 notas más relevantes
5. Inyecta contexto en system prompt de DeepSeek
6. DeepSeek responde basándose en las notas del usuario

### Cache Vectorial (VectorStore)

Sistema de cache Q&A con embeddings para **reducir llamadas a DeepSeek** y ahorrar créditos:

- **Backend Supabase**: PostgreSQL + pgvector para búsqueda por similitud coseno
- **Backend ChromaDB**: Alternativa local con almacenamiento en disco
- **Modelo de embeddings**: `all-MiniLM-L6-v2` (70% más rápido que multilingüe, 384 dimensiones)
- **Umbral de similitud**: 0.88 (solo usa cache si pregunta es muy similar)
- **Threading optimizado**: Búsqueda en cache con timeout de 3s, guardado en background (fire-and-forget)
- **Límite de entradas**: 2000 respuestas cacheadas (eviction automática de las más antiguas)

Flujo con cache vectorial:
1. Usuario hace pregunta conversacional
2. Busca en cache vectorial (3s timeout)
3. Si hay hit (similitud >= 0.88): retorna respuesta cacheada (ahorro de créditos)
4. Si no hay hit: consulta DeepSeek → guarda respuesta en cache (background)

### Threading y Optimizaciones

Todas las operaciones pesadas se ejecutan en threads separados con timeouts:

- **Embeddings**: Generación de vectores en background (no bloquea main thread)
- **Supabase**: Búsqueda y guardado con timeouts (3s búsqueda, 5s guardado)
- **Búsqueda de notas**: LocalKnowledgeReader con timeout de 5s
- **Web search**: DuckDuckGo con timeout de 30s
- **DeepSeek**: Clasificación y respuestas con timeout de 60s

Esto evita que el sistema se congele en "Pensando..." si alguna operación tarda mucho.

---

## Autores

Proyecto desarrollado para **Fundamentos de Software** — TESE (Tecnológico de Estudios Superiores de Ecatepec).
