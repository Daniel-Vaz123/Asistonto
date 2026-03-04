# Kiro - Asistente de Voz Inteligente

Asistente de voz en español desarrollado como proyecto del **TESE** (Tecnológico de Estudios Superiores de Ecatepec) para la materia **Fundamentos de Software**.

Kiro escucha continuamente el micrófono, detecta la palabra de activación **"Asistente"** y responde comandos por voz y texto. Funciona de manera similar a Alexa: siempre está escuchando y cuando detecta la palabra clave, captura el comando del usuario, lo procesa y responde con voz sintetizada.

---

## ¿Qué hace?

1. **Escucha continua**: captura audio del micrófono en tiempo real usando PyAudio.
2. **Transcripción en la nube**: convierte la voz a texto con **AWS Transcribe** (streaming en tiempo real).
3. **Detección de wake word**: identifica cuando el usuario dice "Asistente" (con tolerancia a errores de pronunciación mediante coincidencia difusa).
4. **Clasificación inteligente de comandos**: usa **Smart LLM Router** con DeepSeek para clasificar intenciones (conversacional, notas, YouTube, apps, web).
5. **Notas en Supabase**: las notas del usuario se guardan y buscan solo en la base de datos (tabla `user_notes`), no en archivos locales.
6. **Cache vectorial en Supabase**: almacena preguntas/respuestas con pgvector para reducir llamadas a DeepSeek (umbral de similitud 0.97).
7. **Respuestas inteligentes con IA**: para preguntas generales, consulta **DeepSeek** con contexto de notas o búsqueda web.
8. **Síntesis de voz**: convierte la respuesta a audio con **Amazon Polly** y la reproduce por el altavoz (sin bloquear el event loop).
9. **Vuelve a escuchar**: tras responder, limpia el buffer de audio y regresa al modo de espera en ~1–2 segundos.

---

## Arquitectura y Flujo

```
┌─────────────┐    ┌────────────┐    ┌──────────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│  Micrófono  │───▸│  PyAudio   │───▸│  AWS Transcribe      │───▸│  SmartLLMRouter      │───▸│  Amazon Polly   │
│  (entrada)  │    │  captura   │    │  (streaming STT)     │    │  DeepSeek + JSON     │    │  (TTS salida)   │
└─────────────┘    │  continua  │    │  español             │    │  clasificación       │    │  voz hablada    │
                   └────────────┘    └──────────────────────┘    └──────────────────────┘    └─────────────────┘
                                                                        │
                                                                        ├─▸ LocalKnowledgeReader (RAG)
                                                                        │   └─▸ Notas en Supabase (user_notes)
                                                                        │
                                                                        ├─▸ VectorStore (Supabase)
                                                                        │   └─▸ Cache Q&A con embeddings
                                                                        │
                                                                        └─▸ ActionRouter
                                                                            └─▸ YouTube, Apps, Web, Notas
```

### Flujo detallado

1. `AudioManager` captura audio continuamente desde el micrófono en un hilo separado.
2. `WakeWordDetector` envía el audio a **AWS Transcribe** (streaming) y detecta la palabra **"Asistente"** (o variación).
3. Al detectarla, pasa a modo comando: `CommandTranscriber` captura el comando hasta **2 segundos de silencio** o hasta **60 segundos** de habla continua.
4. `SmartLLMRouter` clasifica el comando con DeepSeek (timeout 3 s, fallback conversacional).
5. `CommandProcessor` procesa según el intent:
   - **Conversational**: Cache vectorial (Supabase) → si no hay hit (similitud ≥ 0.97), consulta DeepSeek → guarda en cache.
   - **File (crear nota)**: Guarda en Supabase (`user_notes`), no en archivos locales.
   - **File (leer nota)**: Busca en Supabase con LocalKnowledgeReader → inyecta contexto en DeepSeek.
   - **YouTube/App/Web**: ActionRouter ejecuta la acción.
6. `ResponseGenerator` sintetiza con **Amazon Polly** y reproduce en un executor (no bloquea el event loop).
7. Auto-Mute evita que el micrófono transcriba la voz del asistente; al terminar se limpia el buffer de audio y se vuelve a escuchar.

---

## Tecnologías y Bibliotecas

### Bibliotecas principales

| Biblioteca | Versión mínima | Función en el proyecto |
|---|---|---|
| **boto3** / **botocore** | `>=1.28.0` / `>=1.31.0` | **Amazon Polly (TTS)** y **AWS Transcribe (STT)**. Síntesis de voz y transcripción de voz a texto en tiempo real. |
| **amazon-transcribe** | (ver requirements.txt) | Cliente de streaming para AWS Transcribe. |
| **openai** | `>=1.0.0` | Cliente para la API de **DeepSeek** (clasificación de intenciones y respuestas inteligentes). |
| **pyaudio** | `>=0.2.13` | Captura y reproducción de audio (micrófono y altavoz). |
| **numpy** | `>=1.24.0` | Procesamiento de señales de audio (RMS, calibración). |
| **python-dotenv** | `>=1.0.0` | Variables de entorno (AWS, DeepSeek, Supabase). |
| **sentence-transformers** | `>=2.2.0` | Embeddings para cache vectorial (modelo `all-MiniLM-L6-v2`). |
| **supabase** | `>=2.0.0` | Cache Q&A (pgvector) y notas de usuario (tabla `user_notes`). |
| **chromadb** | `>=0.4.0` | Opcional: cache vectorial local (por defecto se usa Supabase). |

### Resumen por función

| Función | Tecnología |
|---|---|
| Reconocimiento de voz (STT) | **AWS Transcribe** — streaming, español (es-ES) |
| Clasificación de intenciones | **SmartLLMRouter** — DeepSeek, JSON estructurado |
| Notas del usuario | **Supabase** — tabla `user_notes` (lectura/escritura) |
| Cache vectorial Q&A | **VectorStore** — Supabase (pgvector), similitud ≥ 0.97 |
| Respuestas inteligentes | **DeepSeek** — vía `openai` apuntando a `api.deepseek.com` |
| Síntesis de voz (TTS) | **Amazon Polly** — voz "Mia", español |
| Captura de audio | **PyAudio** — buffer circular, Auto-Mute durante reproducción |

---

## Estructura del Proyecto

```
Asistonto/
├── src/
│   ├── main.py                      # Punto de entrada, orquesta componentes
│   ├── audio_manager.py             # Captura continua y reproducción con Auto-Mute
│   ├── transcribe_client.py         # Cliente AWS Transcribe (streaming)
│   ├── wake_word_detector.py        # Detección "Asistente"
│   ├── command_transcriber.py       # Captura de comando (silencio 2s, máx 60s)
│   ├── command_processor.py         # Smart Router, RAG, cache, acciones
│   ├── smart_llm_router.py          # Clasificación con DeepSeek
│   ├── local_knowledge_reader.py    # RAG sobre notas (Supabase o .md)
│   ├── vector_store.py              # Cache Q&A (Supabase / ChromaDB)
│   ├── notes_db.py                  # Guardado y búsqueda de notas en Supabase
│   ├── intent_classifier.py         # Clasificador regex (fallback)
│   ├── action_router.py             # YouTube, Apps, Web, Notas
│   ├── response_generator.py        # Amazon Polly + reproducción en executor
│   ├── query_router.py              # ¿Requiere búsqueda web?
│   ├── web_search.py                # DuckDuckGo
│   ├── feedback_preventer.py        # Auto-Mute durante TTS
│   ├── rich_ui_manager.py           # Paneles de estado en consola
│   └── actions/
│       ├── file_writer_action.py    # Crear notas → Supabase (user_notes)
│       ├── youtube_action.py        # Reproducir YouTube
│       ├── app_launcher_action.py   # Abrir aplicaciones
│       └── web_browser_action.py    # Abrir sitios web
│
├── scripts/
│   ├── check_supabase_vector.py     # Verificar Supabase (cache + notas)
│   └── test_supabase_insert.py      # Probar inserción en Supabase
│
├── data/                            # Opcional (solo .gitkeep si todo está en Supabase)
├── logs/                            # Logs del sistema
├── cache/                           # Cache de audio de Amazon Polly
├── docs/
│   └── SUPABASE_VECTOR_SETUP.md     # Configuración Supabase (qa_cache + user_notes)
│
├── config.json                      # Configuración (aws, wake_words, features)
├── .env                             # Credenciales (no se sube a git)
├── .env.example                     # Plantilla de credenciales
├── requirements.txt
├── README.md
└── MIGRACION_AWS.md                 # Referencia: migración desde Vosk (ya no usado)
```

### Módulos principales

| Módulo | Descripción |
|---|---|
| `transcribe_client.py` | AWS Transcribe streaming. Si ya hay un stream activo, se detiene y se abre uno nuevo (evita error "stream activo"). |
| `command_transcriber.py` | Captura comando hasta 2 s de silencio o 60 s máx. |
| `vector_store.py` | Cache Q&A en Supabase; similitud mínima 0.97 para reutilizar respuesta. |
| `notes_db.py` | Guardar/buscar notas en tabla `user_notes` (Supabase). |
| `response_generator.py` | Polly + reproducción en `run_in_executor` para no bloquear el event loop en respuestas largas. |
| `wake_word_detector.py` | Tras cada comando, limpia buffer de audio y resetea ventana de detección para escuchar de nuevo. |

---

## Requisitos

- **Python 3.12 o 3.13**
- **Micrófono**
- **Conexión a Internet** (AWS Transcribe, Polly, DeepSeek, Supabase)
- **Cuenta AWS** (Polly + Transcribe)
- **API Key de DeepSeek**
- **Proyecto Supabase** (tablas `qa_cache` y `user_notes`). Ver `docs/SUPABASE_VECTOR_SETUP.md`.

---

## Instalación

### Opción A: Script automático

**Windows:**
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
source .venv/Scripts/activate   # Windows Git Bash
# .venv\Scripts\activate        # Windows CMD
pip install -r requirements.txt
```

### Configurar `.env`

```env
# AWS (Polly + Transcribe)
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_DEFAULT_REGION=us-east-1

# DeepSeek
DEEPSEEK_API_KEY=tu_api_key

# Supabase (cache Q&A + notas)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_KEY=tu_service_role_key
```

- **AWS**: Polly (TTS) y Transcribe (STT).
- **DeepSeek**: Smart Router y respuestas conversacionales.
- **Supabase**: Cache vectorial y notas. Ver `docs/SUPABASE_VECTOR_SETUP.md`.

### Ejecutar

```bash
python -m src.main
```

Para ocultar warnings en consola:

```bash
python -W ignore -m src.main
```

---

## Uso

- Di **"Asistente"** para activar.
- Di tu comando o pregunta (puedes hablar hasta ~60 segundos; se cierra con 2 segundos de silencio).
- Kiro responde por texto y por voz.
- Vuelve a escuchar automáticamente.
- `Ctrl+C` para salir.

### Comandos de ejemplo

| Intención | Ejemplos |
|---|---|
| Hora / Fecha | "¿Qué hora es?", "¿Qué día es hoy?" (solo preguntas sobre hoy) |
| Crear nota | "Anota que mañana tengo clase", "Guarda que el proyecto va al 80%" |
| Leer notas | "¿Qué notas tengo sobre el proyecto?", "Revisa mis apuntes" |
| YouTube / App / Web | "Pon música en YouTube", "Abre Chrome" |
| Pregunta general | Cualquier otra pregunta → DeepSeek (con cache y/o búsqueda web) |

---

## Configuración (`config.json`)

| Campo | Descripción |
|---|---|
| `aws.transcribe.language_code` | Idioma para AWS Transcribe (ej. `es-ES`) |
| `aws.polly.voice_id` | Voz de Polly (`Mia`, `Lucia`, etc.) |
| `wake_words` | Palabras de activación (ej. `["asistente"]`) |
| `user_name` | Nombre del usuario en respuestas |
| `features.vector_cache_backend` | `supabase` (por defecto) o `chroma` |
| `features.notes_backend` | `supabase` (por defecto) — notas solo en BD |
| `features.voice_cache_enabled` | Cache de audio de Polly |
| `features.vector_cache_enabled` | Cache Q&A en Supabase |

---

## Cache vectorial y notas (Supabase)

- **Cache Q&A**: Preguntas y respuestas se guardan en Supabase (pgvector). Solo se reutiliza una respuesta si la nueva pregunta tiene similitud **≥ 0.97** con una guardada (evita respuestas incorrectas por preguntas parecidas).
- **Notas**: Se guardan en la tabla `user_notes` (crear nota por voz). La búsqueda para "leer notas" se hace contra esa tabla.
- No se usa almacenamiento local obligatorio: ni ChromaDB ni archivos `data/*.md` son necesarios si `vector_cache_backend` y `notes_backend` son `supabase`.

---

## Autores

Proyecto desarrollado para **Fundamentos de Software** — TESE (Tecnológico de Estudios Superiores de Ecatepec).
