# Migracion de Vosk a AWS Transcribe

Guia para reemplazar Vosk (transcripcion local) por AWS Transcribe (transcripcion en la nube) cuando tu cuenta de AWS tenga habilitado el servicio.

---

## Por que migrar

| Aspecto | Vosk (actual) | AWS Transcribe |
|---|---|---|
| Precision | Buena (modelo pequeno) | Muy alta |
| Frases largas | Limitado | Excelente |
| Internet | No necesita | Requiere conexion |
| Costo | Gratis | 60 min/mes gratis, despues ~0.024 USD/min |
| Latencia | Baja (local) | Baja (streaming) |

AWS Transcribe ofrece mejor reconocimiento, especialmente en frases largas y vocabulario variado.

---

## Requisitos previos

1. **Cuenta AWS activa** con metodo de pago verificado.
2. **Amazon Transcribe habilitado** en tu cuenta (si da error SubscriptionRequiredException, contacta soporte AWS).
3. Credenciales en .env (ya las tienes para Polly):

       AWS_ACCESS_KEY_ID=tu_key
       AWS_SECRET_ACCESS_KEY=tu_secret
       AWS_DEFAULT_REGION=us-east-1

---

## Pasos para migrar

### 1. Instalar dependencia de AWS Transcribe

    pip install amazon-transcribe>=0.6.0

### 2. Cambiar config.json

Cambia el campo transcribe_provider de vosk a aws:

    {
        "transcribe_provider": "aws",
        ...
    }

El bloque aws.transcribe ya existe en config.json con la configuracion necesaria:

    "aws": {
        "transcribe": {
            "language_code": "es-ES",
            "sample_rate": 16000,
            "vocabulary_name": "voice-assistant-vocab"
        }
    }

Si no usas vocabulario personalizado, pon vocabulary_name como null o quitalo.

### 3. Ejecutar

    python -m src.main

El sistema usara AWS Transcribe para wake word y comandos, y Amazon Polly para las respuestas (igual que antes).

---

## Como funciona internamente

El archivo src/main.py ya tiene la logica para elegir proveedor:

    transcribe_provider = config.get("transcribe_provider", "vosk")

    if transcribe_provider == "vosk":
        # Usa VoskTranscribeStreamingWrapper
    else:
        # Usa TranscribeStreamingClientWrapper (AWS)

Ambos clientes tienen la misma interfaz (start_stream, stop_stream), asi que el resto del codigo (wake_word_detector, command_transcriber) funciona igual sin cambios.

---

## Archivos involucrados

| Archivo | Funcion |
|---|---|
| src/transcribe_client.py | Cliente de AWS Transcribe (ya existe) |
| src/transcribe_client_vosk.py | Cliente de Vosk (se deja de usar) |
| config.json | Cambiar transcribe_provider a aws |

---

## Volver a Vosk

Si quieres volver a Vosk, solo cambia en config.json:

    "transcribe_provider": "vosk"

No hace falta tocar codigo. El modelo Vosk sigue en la carpeta model/.

---

## Solucion de problemas

### Error: SubscriptionRequiredException

Tu cuenta AWS no tiene habilitado Transcribe. Opciones:

1. Entra a la consola de AWS Transcribe y haz una transcripcion de prueba para activar el servicio.
2. Prueba otra region (us-east-2, eu-west-1).
3. Contacta soporte AWS (Account and billing) y pide que activen Amazon Transcribe.

### Error: Credenciales no configuradas

Verifica que .env tenga AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY y AWS_DEFAULT_REGION.

### La transcripcion es peor que con Vosk

Poco probable, pero si pasa: revisa que language_code sea es-ES (o es-MX) y que el sample_rate coincida con el del microfono (16000).
