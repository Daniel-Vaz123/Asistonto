# 🎤 Asistente de Voz - MVP Instrucciones de Uso

## ✅ Archivos Implementados

Los siguientes archivos están completamente implementados y listos para usar:

1. **`src/wake_word_detector.py`** - Detector de palabra de activación "Asistente"
2. **`src/main.py`** - Script principal con interfaz CLI colorida
3. **`src/audio_manager.py`** - Gestor de audio (ya existente)
4. **`src/transcribe_client.py`** - Cliente de AWS Transcribe (ya existente)
5. **`src/command_transcriber.py`** - Transcriptor de comandos (ya existente)

## 🚀 Cómo Ejecutar el MVP

### 1. Configurar Credenciales AWS

Edita el archivo `.env` y agrega tus credenciales:

```bash
# TODO: Ingresa tus credenciales de AWS aquí
AWS_ACCESS_KEY_ID=tu_access_key_id_aqui
AWS_SECRET_ACCESS_KEY=tu_secret_access_key_aqui
AWS_DEFAULT_REGION=us-east-1

# Configuración opcional
VOICE_ASSISTANT_LOG_LEVEL=INFO
VOICE_ASSISTANT_CONFIG_PATH=config.json
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Ejecutar el Asistente

```bash
python src/main.py
```

## 🎨 Interfaz de Consola con Colores

El sistema usa códigos ANSI para mostrar una interfaz visual atractiva:

- **🟢 VERDE** - Wake word detectado ("Asistente")
- **🟡 AMARILLO** - Procesando audio / transcripción parcial
- **🔵 CYAN** - Texto transcrito final
- **🔴 ROJO** - Errores
- **⚪ BLANCO** - Información general

### Ejemplo de Salida:

```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     █████╗ ███████╗██╗███████╗████████╗███████╗███╗   ██╗████████╗║
║    ██╔══██╗██╔════╝██║██╔════╝╚══██╔══╝██╔════╝████╗  ██║╚══██╔══╝║
║    ███████║███████╗██║███████╗   ██║   █████╗  ██╔██╗ ██║   ██║   ║
║    ██╔══██║╚════██║██║╚════██║   ██║   ██╔══╝  ██║╚██╗██║   ██║   ║
║    ██║  ██║███████║██║███████║   ██║   ███████╗██║ ╚████║   ██║   ║
║    ╚═╝  ╚═╝╚══════╝╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝   ╚═╝   ║
║                                                                   ║
║              🎤 Asistente de Voz para Raspberry Pi 🎤             ║
║                                                                   ║
║                    Powered by AWS Transcribe                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

✓ Credenciales de AWS validadas
✓ Configuración cargada exitosamente
⏳ Inicializando componentes del sistema...
✓ Micrófono calibrado - Nivel de ruido: 245.32
✓ Sistema inicializado correctamente

======================================================================
🎤 SISTEMA LISTO - Di 'ASISTENTE' para activar
======================================================================

🎤 WAKE WORD DETECTADO: 'ASISTENTE' (confianza: 95%)

⏳ Escuchando comando...
  ⏳ qué hora es...

======================================================================
💬 COMANDO TRANSCRITO: "qué hora es"
  Confianza: 92%
  Duración: 1.8s
  Idioma: es-ES
======================================================================
```

## 🔧 Configuración

### Archivo `config.json`

Puedes modificar la configuración en `config.json`:

```json
{
    "aws": {
        "region": "us-east-1",
        "transcribe": {
            "language_code": "es-ES",  // Cambia a "es-MX" si prefieres
            "sample_rate": 16000,
            "vocabulary_name": "voice-assistant-vocab"
        }
    },
    "audio": {
        "sample_rate": 16000,
        "chunk_size": 1024,  // Optimizado para baja latencia
        "channels": 1
    },
    "wake_words": ["asistente", "alexa", "hola asistente"]
}
```

### Cambiar Wake Words

Edita la lista `wake_words` en `config.json` para usar diferentes palabras de activación:

```json
"wake_words": ["asistente", "hola", "oye"]
```

## 📋 Flujo del Sistema

1. **Inicio**: El sistema inicia y calibra el micrófono
2. **Escucha Continua**: AudioManager captura audio continuamente
3. **Detección de Wake Word**: WakeWordDetector envía audio a AWS Transcribe y busca "Asistente"
4. **Wake Word Detectado**: Se muestra en VERDE y se activa la captura de comando
5. **Captura de Comando**: CommandTranscriber captura el comando completo
6. **Transcripción**: Se muestra en CYAN el texto transcrito
7. **Vuelta a Escucha**: El sistema vuelve a esperar el wake word

## 🐛 Troubleshooting

### Error: "Credenciales de AWS no configuradas"

**Solución**: Edita el archivo `.env` y agrega tus credenciales de AWS.

### Error: "No se pudo capturar audio"

**Solución**: 
- Verifica que el micrófono esté conectado
- Ejecuta `python -c "import pyaudio; p = pyaudio.PyAudio(); print(p.get_device_count())"` para listar dispositivos
- Ajusta `input_device_index` en `config.json` si es necesario

### Error: "BotoCoreError: Could not connect"

**Solución**:
- Verifica tu conexión a internet
- Verifica que la región AWS sea correcta en `.env`
- Verifica que tus credenciales AWS tengan permisos para Transcribe

### El sistema no detecta el wake word

**Solución**:
- Habla más claro y fuerte
- Reduce el ruido de fondo
- Ajusta `confidence_threshold` en el código (línea 287 de `main.py`)

## 💰 Costos de AWS

⚠️ **IMPORTANTE**: AWS Transcribe cobra por tiempo de uso.

- **Tier Gratuito**: 60 minutos/mes durante los primeros 12 meses
- **Después**: $0.024 USD por minuto de audio transcrito

**Estimación para el MVP**:
- El sistema transcribe continuamente mientras busca el wake word
- ~$1.44 USD por hora de uso continuo
- Recomendación: Usa solo cuando necesites probar

## 🎯 Próximos Pasos

Este MVP implementa el núcleo básico. Para extenderlo:

1. **Integrar Amazon Lex** - Procesar intenciones de los comandos
2. **Integrar AWS Polly** - Respuestas habladas
3. **Agregar Session Manager** - Mantener contexto de conversación
4. **Implementar IoT Control** - Controlar dispositivos del hogar
5. **Agregar Base de Datos** - Recordatorios y configuración persistente

## 📝 Notas Técnicas

### Arquitectura del MVP

```
┌─────────────────┐
│  AudioManager   │ ──> Captura audio del micrófono
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│  WakeWordDetector       │ ──> Detecta "Asistente"
└────────┬────────────────┘
         │
         v
┌──────────────────────────────────┐
│ TranscribeStreamingClientWrapper │ ──> AWS Transcribe
└────────┬─────────────────────────┘
         │
         v
┌─────────────────────────┐
│  CommandTranscriber     │ ──> Captura comando completo
└─────────────────────────┘
```

### Optimizaciones Implementadas

- **Chunk Size**: 1024 bytes para baja latencia
- **Sample Rate**: 16000 Hz (óptimo para voz)
- **Buffer Circular**: Mantiene últimos 10 segundos de audio
- **Detección de Silencio**: 1.5 segundos para finalizar comando
- **Filtrado de Duplicados**: Ventana de 3 segundos para evitar detecciones repetidas

## 🤝 Soporte

Si encuentras problemas:

1. Revisa los logs en `logs/voice_assistant.log`
2. Verifica que todas las dependencias estén instaladas
3. Asegúrate de tener Python 3.9+
4. Verifica que PyAudio esté instalado correctamente (puede requerir `portaudio` en el sistema)

## 📄 Licencia

Este proyecto es parte del VoiceAssistantBot para Raspberry Pi.

---

**¡Disfruta tu asistente de voz! 🎤🤖**
