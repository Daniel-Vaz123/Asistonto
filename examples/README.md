# Ejemplos de Uso - Asistente de Voz

Este directorio contiene scripts de ejemplo para probar y demostrar las diferentes funcionalidades del asistente de voz.

## Requisitos Previos

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar credenciales de AWS:**
   
   Crea un archivo `.env` en la raíz del proyecto con tus credenciales:
   ```bash
   AWS_ACCESS_KEY_ID=tu_access_key
   AWS_SECRET_ACCESS_KEY=tu_secret_key
   AWS_DEFAULT_REGION=us-east-1
   ```

3. **Verificar configuración:**
   
   Asegúrate de que el archivo `config.json` esté configurado correctamente.

## Ejemplos Disponibles

### 1. test_transcribe_integration.py

Prueba la integración con AWS Transcribe para transcripción de voz a texto en tiempo real.

**Características:**
- Captura de audio desde el micrófono
- Transcripción en tiempo real usando AWS Transcribe
- Detección automática de silencio
- Soporte para español (es-ES)

**Uso:**
```bash
python examples/test_transcribe_integration.py
```

**Opciones:**
1. **Prueba básica:** Captura y transcribe un solo comando
2. **Múltiples comandos:** Captura y transcribe 3 comandos consecutivos

**Ejemplo de salida:**
```
=== Prueba de Integración con AWS Transcribe ===
Inicializando AudioManager...
Calibrando micrófono...
Calibración completada: {'noise_level': 0.02, 'recommended_threshold': 0.05}
Inicializando cliente de AWS Transcribe...
¡Habla ahora! Di un comando en español...

[PARCIAL] qué hora
[PARCIAL] qué hora es
[FINAL] ¿Qué hora es?
  Confianza: 0.95
  Duración: 2.3s
  Idioma: es-ES
```

## Notas Importantes

### Configuración de Audio

- **Sample Rate:** 16000 Hz (requerido por AWS Transcribe)
- **Channels:** 1 (mono)
- **Chunk Size:** 1024 bytes

### Configuración de AWS Transcribe

- **Idioma:** es-ES (español de España) o es-MX (español de México)
- **Detección de silencio:** 1.5 segundos
- **Duración máxima de comando:** 10 segundos

### Costos de AWS

⚠️ **IMPORTANTE:** AWS Transcribe cobra por tiempo de uso. Consulta la [página de precios de AWS Transcribe](https://aws.amazon.com/transcribe/pricing/) para más información.

- Nivel gratuito: 60 minutos/mes durante los primeros 12 meses
- Después: ~$0.024 por minuto de audio

### Solución de Problemas

**Error: "No audio input device found"**
- Verifica que tu micrófono esté conectado
- En Linux/Raspberry Pi, instala: `sudo apt-get install portaudio19-dev`

**Error: "AWS credentials not configured"**
- Verifica que el archivo `.env` exista y contenga las credenciales correctas
- Alternativamente, configura AWS CLI: `aws configure`

**Error: "Connection timeout"**
- Verifica tu conexión a internet
- Verifica que la región de AWS esté configurada correctamente

**Transcripción vacía o incorrecta**
- Habla más cerca del micrófono
- Reduce el ruido de fondo
- Calibra el micrófono antes de usar

## Próximos Pasos

Después de probar estos ejemplos, puedes:

1. Integrar con el detector de wake word (Task 4)
2. Agregar procesamiento de intenciones con Amazon Lex (Task 7)
3. Implementar respuestas de voz con AWS Polly (Task 9)

## Soporte

Para reportar problemas o hacer preguntas, consulta la documentación principal del proyecto.
