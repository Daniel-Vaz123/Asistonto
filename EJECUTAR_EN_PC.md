# Ejecutar el asistente en tu PC (Windows)

Guía para usar el asistente tipo Alexa en tu computadora: detectar audio del micrófono y responder por voz.

## Requisitos en tu PC

1. **Python 3.12 o 3.13** (PyAudio tiene wheels precompilados; con 3.14 no instala sin compilador).
2. **Credenciales AWS** en un archivo `.env` (ya lo tienes).
3. **Micrófono** (el de la laptop o uno USB).
4. **Conexión a Internet** (Transcribe y Polly son en la nube).

---

## ✅ Entorno listo con Python 3.12

En este proyecto ya está creado un **entorno virtual** (`.venv`) con **Python 3.12** y todas las dependencias instaladas, incluida PyAudio.

### Cómo ejecutar el asistente (cada vez)

1. Abre terminal en la carpeta del proyecto **Asistonto**.

2. **Activa el entorno virtual:**
   - **PowerShell:** `.\.venv\Scripts\Activate.ps1`
   - **CMD:** `.\.venv\Scripts\activate.bat`
   - **Git Bash / Bash:** `source .venv/Scripts/activate`

3. Ejecuta (como módulo para que encuentre el paquete `src`):
   ```bash
   python -m src.main
   ```

Verás `(.venv)` en el prompt cuando el entorno esté activo. Para salir del asistente: **Ctrl+C**.

---

## 1. Variables de entorno (.env)

En la raíz del proyecto (`Asistonto`), el archivo `.env` debe tener al menos:

```env
AWS_ACCESS_KEY_ID=tu_key
AWS_SECRET_ACCESS_KEY=tu_secret
AWS_DEFAULT_REGION=us-east-1
```

Opcional para personalizar:

```env
VOICE_ASSISTANT_USER_NAME=TuNombre
VOICE_ASSISTANT_LOG_LEVEL=INFO
```

No hace falta poner `VOICE_ASSISTANT_CONFIG_PATH` en PC; por defecto se usa `config.json` en la carpeta del proyecto.

---

## Modo gratuito (sin AWS): Vosk + pyttsx3

Si no quieres usar AWS (o aún no tienes la cuenta validada), el proyecto puede funcionar **en modo local**:

- **Vosk**: reconoce la voz (wake word y comandos) en tu PC, sin internet.
- **pyttsx3**: hace hablar al asistente con las voces de Windows.

### Pasos para usar el modo gratuito

1. En **config.json** debe estar:
   - `"voice_mode": "local"`
   - `"local": { "vosk_model_path": "model/vosk-model-small-es-0.42" }`  
   (ya viene así por defecto en el proyecto.)

2. Instala dependencias del modo local (con el venv activado):
   ```bash
   pip install vosk pyttsx3
   ```

3. Descarga el modelo de voz en español (solo una vez). Desde la carpeta **Asistonto**:
   ```bash
   python scripts/download_vosk_model.py
   ```
   Se creará la carpeta `model/vosk-model-small-es-0.42`. Si la descarga falla, descarga a mano desde [Vosk models](https://alphacephei.com/vosk/models) el modelo **vosk-model-small-es-0.42**, descomprímelo y colócalo en `model/vosk-model-small-es-0.42`.

4. Ejecuta igual que siempre:
   ```bash
   python -m src.main
   ```
   No necesitas `.env` con claves AWS en modo local.

**Si la transcripción es incorrecta** (por ejemplo dice "para todo" en vez de "zapato"): el modelo **pequeño** es rápido pero menos preciso. Para mejor precisión usa el **modelo grande**:
   ```bash
   python scripts/download_vosk_model.py --big
   ```
   (Descarga ~1.4 GB; tarda unos minutos.) Luego en **config.json** → `local` → cambia a:
   ```json
   "vosk_model_path": "model/vosk-model-es-0.42"
   ```

Para volver a usar AWS más adelante, cambia en **config.json** a `"voice_mode": "aws"` y configura de nuevo el `.env`.

---

## 2. Si necesitas reinstalar dependencias

Si en el futuro creas otro venv o cambias de máquina, desde la carpeta **Asistonto** con el venv activado:

```bash
pip install -r requirements.txt
```

Con **Python 3.12 o 3.13** todas las dependencias (incluida PyAudio) se instalan sin compilador. Con Python 3.14 PyAudio no tiene wheel y falla; usa el venv de 3.12 que ya está en el proyecto.

### Reproducción de respuestas (MP3 → audio)

Las respuestas de Amazon Polly vienen en MP3. Para convertirlas a audio se usa **pydub**. Opcionalmente instala **ffmpeg** para que pydub soporte MP3 sin problemas:

- Descarga: https://ffmpeg.org/download.html (Windows) o con Chocolatey: `choco install ffmpeg`.
- Añade la carpeta `bin` de ffmpeg al PATH.

Si no tienes ffmpeg, pydub puede dar error al convertir MP3; en ese caso conviene tener ffmpeg instalado.

## 3. Ejecutar el asistente

Siempre desde la **carpeta Asistonto** (raíz del proyecto):

```bash
cd Asistonto
python src/main.py
```

O desde la raíz del repo:

```bash
python Asistonto/src/main.py
```

pero asegúrate de que el directorio de trabajo sea **Asistonto** (donde están `config.json` y `.env`), o define en `.env`:

```env
VOICE_ASSISTANT_CONFIG_PATH=C:\ruta\completa\a\Asistonto\config.json
```

## 4. Uso (tipo Alexa)

1. Al arrancar verás el banner y “SISTEMA LISTO”.
2. Di una **palabra de activación**: **"Asistente"**, **"Alexa"** o **"Hola asistente"**.
3. Cuando aparezca en verde “WAKE WORD DETECTADO”, di tu comando en español, por ejemplo:
   - “¿Qué hora es?”
   - “¿Qué día es hoy?”
   - “¿Cómo te llamas?”
   - “Cuéntame un chiste”
   - “Hola” / “¿Qué tal?”
4. El asistente transcribe, procesa el comando y **responde por voz** (Amazon Polly) y en pantalla.

Para salir: **Ctrl+C**.

## 5. Config.json y vocabulario AWS (opcional)

Si al iniciar obtienes un error de AWS sobre **vocabulario** (vocabulary), es que en la nube no tienes creado el vocabulario personalizado. Para usar solo el idioma por defecto:

- En `config.json`, dentro de `aws.transcribe`, pon `"vocabulary_name": null` o borra la línea `"vocabulary_name": "voice-assistant-vocab"`.

Así Transcribe usará solo el idioma configurado (`es-ES`) sin vocabulario personalizado.

## 6. Configuración opcional (config.json)

- **user_name**: nombre que usa el asistente para dirigirse a ti (también se puede usar `VOICE_ASSISTANT_USER_NAME` en `.env`).
- **wake_words**: palabras/frases de activación (por defecto: `"asistente"`, `"alexa"`, `"hola asistente"`).
- **audio**: `input_device_index` / `output_device_index`: si tienes varios micrófonos o altavoces, puedes poner el índice del dispositivo (ver logs al iniciar o listar dispositivos con un script de prueba).

## 7. Problemas frecuentes en PC

| Problema | Qué hacer |
|----------|-----------|
| `pip: command not found` | Usa `python -m pip install ...`. |
| Error al instalar PyAudio | Instala C++ Build Tools o usa una rueda precompilada (ver arriba). |
| “Credenciales no configuradas” | Revisa `.env` en la carpeta Asistonto y que tenga `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`. |
| No escucha / no reproduce | Comprueba que PyAudio esté instalado y que el micrófono/altavoz por defecto sean los correctos en Windows. |
| Error al convertir MP3 | Instala ffmpeg y añádelo al PATH para que pydub pueda procesar MP3. |

Con esto puedes ejecutar el proyecto en tu computadora, con detección de audio y respuestas habladas como un asistente tipo Alexa.
