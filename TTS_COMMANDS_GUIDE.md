# 🗣️ Guía de Voz y Comandos - Kiro Asistente

## 🎉 Nuevas Funcionalidades Implementadas

### 1. Síntesis de Voz con Amazon Polly (TTS)
Kiro ahora puede **hablar** usando Amazon Polly con voz en español de México (Mia).

### 2. Procesador de Comandos Inteligente
Kiro entiende y responde a múltiples tipos de comandos con personalización para Daniel.

---

## 🎤 Comandos Disponibles

### 👤 Identidad
**Pregunta:** "¿Cómo te llamas?" / "¿Quién eres?" / "¿Cuál es tu nombre?"

**Respuesta:** "Soy Kiro, tu asistente inteligente desarrollado en el TESE."

---

### 💬 Estado
**Pregunta:** "¿Cómo estás?" / "¿Qué tal?" / "¿Cómo te va?"

**Respuesta:** "Bien, gracias por preguntar. ¿En qué puedo ayudarte, Daniel?"

---

### ⏰ Hora
**Pregunta:** "¿Qué hora es?" / "Dime la hora" / "¿Cuál es la hora?"

**Respuesta:** "Son las 3 y 45 minutos de la tarde, Daniel."
- Formato natural en español
- Incluye periodo del día (mañana/tarde/noche)
- Maneja casos especiales (en punto, y cuarto, y media)

---

### 📅 Fecha
**Pregunta:** "¿Qué día es hoy?" / "¿Qué fecha es?" / "¿A cuántos estamos?"

**Respuesta:** "Hoy es martes 24 de diciembre de 2024, Daniel."
- Día de la semana en español
- Fecha completa con mes en español

---

### 😄 Chistes
**Pregunta:** "Cuéntame un chiste" / "Dime algo gracioso" / "Hazme reír"

**Respuesta:** Kiro cuenta uno de 8 chistes aleatorios, incluyendo:
- "¿Por qué los programadores prefieren el modo oscuro? Porque la luz atrae a los bugs."
- "¿Qué le dice un bit al otro? Nos vemos en el bus."
- Y más...

---

### 👋 Saludo
**Pregunta:** "Hola" / "Buenos días" / "Buenas tardes"

**Respuesta:** "¡Hola, Daniel! ¿En qué puedo ayudarte?"

---

### 👋 Despedida
**Pregunta:** "Adiós" / "Hasta luego" / "Gracias"

**Respuesta:** "Hasta luego, Daniel. ¡Que tengas un excelente día!"

---

### ❓ Capacidades
**Pregunta:** "¿Qué puedes hacer?" / "¿Qué sabes hacer?" / "Ayuda"

**Respuesta:** Lista de todas las funciones disponibles.

---

### ❌ Comando No Reconocido
**Pregunta:** Cualquier cosa que Kiro no entienda

**Respuesta:** "Lo siento, Daniel, aún no tengo programada esa función, pero puedo ayudarte con la hora, la fecha, o contarte un chiste."

---

## 🎨 Interfaz Visual Mejorada

### Colores en Consola

```
🟢 VERDE    = Wake word detectado
🟡 AMARILLO = Procesando / Transcripción parcial
🔵 CYAN     = Transcripción del comando
🤖 CYAN     = Respuesta de Kiro
🔊 VERDE    = Confirmación de voz hablada
🔴 ROJO     = Errores
```

### Ejemplo de Salida

```
======================================================================
🎤 WAKE WORD DETECTADO: 'ASISTENTE' (confianza: 95%)
======================================================================

⏳ Escuchando comando...
  ⏳ qué hora es...

======================================================================
💬 COMANDO TRANSCRITO: "qué hora es"
  Confianza: 92%
  Duración: 1.8s
  Idioma: es-ES
======================================================================

⏳ Procesando comando...

──────────────────────────────────────────────────────────────────────
🤖 KIRO RESPONDE:
  Son las 3 y 45 minutos de la tarde, Daniel.
──────────────────────────────────────────────────────────────────────
  🔊 Respuesta hablada con Amazon Polly
──────────────────────────────────────────────────────────────────────
```

---

## 🔧 Configuración de Voz

### Voces Disponibles en Español

Edita `config.json` para cambiar la voz:

```json
"polly": {
    "voice_id": "Mia",      // Español de México (Neural)
    "output_format": "mp3",
    "sample_rate": "22050"
}
```

**Opciones de voces:**
- **Mia** - Español de México (Neural) - ✅ Recomendada
- **Lucia** - Español de España (Neural)
- **Enrique** - Español de España (Standard)
- **Lupe** - Español de Estados Unidos (Neural)

---

## 💾 Sistema de Cache

### Funcionamiento
- Las respuestas se guardan en `cache/` como archivos MP3
- Respuestas repetidas se cargan del cache (más rápido, sin costo AWS)
- Cache automático para reducir latencia y costos

### Estadísticas
Al iniciar el sistema, verás:
```
ℹ Cache de voz: 0 solicitudes, 0.0% hit rate
```

Después de usar:
```
ℹ Cache de voz: 10 solicitudes, 60.0% hit rate
```

### Limpiar Cache
```python
# En el código
response_generator.clear_cache()
```

---

## 🚀 Cómo Usar

### 1. Ejecutar el Sistema
```bash
python src/main.py
```

### 2. Activar con Wake Word
Di: **"Asistente"**

### 3. Dar Comando
Ejemplos:
- "¿Qué hora es?"
- "¿Cómo te llamas?"
- "Cuéntame un chiste"
- "¿Qué día es hoy?"

### 4. Escuchar Respuesta
Kiro responderá:
- 📝 En texto (consola)
- 🔊 En voz (Amazon Polly)

---

## 🎯 Arquitectura Técnica

```
Usuario dice "Asistente"
    ↓
WakeWordDetector detecta wake word
    ↓
CommandTranscriber captura comando
    ↓
CommandProcessor analiza intención
    ↓
ResponseGenerator sintetiza respuesta
    ↓
Amazon Polly genera audio
    ↓
AudioManager reproduce audio
    ↓
Usuario escucha respuesta
```

---

## 📊 Matriz de Intenciones

| Intención    | Patrones                          | Tipo      |
|--------------|-----------------------------------|-----------|
| identidad    | nombre, quién eres                | Estática  |
| estado       | cómo estás, qué tal               | Estática  |
| hora         | qué hora, hora es                 | Dinámica  |
| fecha        | qué día, fecha                    | Dinámica  |
| chiste       | chiste, algo gracioso             | Dinámica  |
| saludo       | hola, buenos días                 | Estática  |
| despedida    | adiós, gracias                    | Estática  |
| capacidades  | qué puedes hacer, ayuda           | Estática  |

---

## 🔍 Personalización

### Cambiar Nombre de Usuario

Edita `src/main.py` línea ~235:
```python
self.command_processor = CommandProcessor(
    response_generator=self.response_generator,
    user_name="TuNombre"  # Cambia aquí
)
```

### Agregar Nuevos Comandos

Edita `src/command_processor.py`:

```python
# Agregar nueva intención
'nuevo_comando': {
    'patterns': [
        r'\b(palabra clave|otra palabra)\b'
    ],
    'responses': [
        'Respuesta para {user}.'
    ]
}
```

### Agregar Chistes

Edita `src/command_processor.py` línea ~80:
```python
JOKES = [
    'Tu nuevo chiste aquí...',
    # Agregar más chistes
]
```

---

## 💰 Costos de AWS

### Amazon Polly
- **Tier Gratuito**: 5 millones de caracteres/mes (primeros 12 meses)
- **Después**: $4.00 USD por 1 millón de caracteres
- **Voces Neural**: $16.00 USD por 1 millón de caracteres

### Estimación
- Respuesta promedio: ~50 caracteres
- 1000 respuestas: ~$0.08 USD (Neural)
- Con cache 60%: ~$0.03 USD

### Reducir Costos
1. ✅ Cache habilitado (automático)
2. ✅ Respuestas cortas y concisas
3. ✅ Reutilizar respuestas comunes

---

## 🐛 Troubleshooting

### "No se pudo hablar la respuesta"
**Causa:** Error de Amazon Polly o conversión de audio

**Solución:**
1. Verifica credenciales AWS en `.env`
2. Verifica permisos IAM para Polly
3. Instala dependencias de audio:
   ```bash
   pip install pydub
   # O instala ffmpeg en el sistema
   ```

### "Error convirtiendo MP3 a PCM"
**Causa:** Falta pydub o ffmpeg

**Solución:**
```bash
# Opción 1: Instalar pydub
pip install pydub

# Opción 2: Instalar ffmpeg
# Windows: Descargar de ffmpeg.org
# Linux: sudo apt-get install ffmpeg
# Mac: brew install ffmpeg
```

### Respuesta solo en texto
**Causa:** Polly funciona pero reproducción falla

**Solución:**
- Verifica que el altavoz esté conectado
- Revisa logs en `logs/voice_assistant.log`

---

## 📝 Logs y Debugging

### Ver Logs
```bash
tail -f logs/voice_assistant.log
```

### Nivel de Log
Edita `.env`:
```bash
VOICE_ASSISTANT_LOG_LEVEL=DEBUG  # INFO, WARNING, ERROR
```

---

## ✅ Checklist de Funcionalidades

- [x] Síntesis de voz con Amazon Polly
- [x] Voz en español de México (Mia)
- [x] Cache de respuestas
- [x] Procesador de comandos con intenciones
- [x] Comando: Identidad
- [x] Comando: Estado
- [x] Comando: Hora (formato natural)
- [x] Comando: Fecha (formato natural)
- [x] Comando: Chistes (8 chistes)
- [x] Comando: Saludo
- [x] Comando: Despedida
- [x] Comando: Capacidades
- [x] Fallback para comandos no reconocidos
- [x] Personalización para Daniel
- [x] Interfaz visual mejorada
- [x] Manejo robusto de errores

---

## 🎓 Próximos Pasos

1. **Integrar Amazon Lex** - NLU más avanzado
2. **Agregar más comandos** - Clima, noticias, etc.
3. **Control IoT** - Luces, termostato
4. **Recordatorios** - Gestión de tareas
5. **Contexto de conversación** - Seguimiento de diálogo

---

**¡Kiro ahora puede hablar! 🎤🤖**
