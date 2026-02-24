# Documento de Requisitos: Asistente de Voz para Raspberry Pi

## Introducción

Este documento especifica los requisitos para un asistente de voz inteligente que se ejecuta en una Raspberry Pi Zero 2W. El sistema captura audio continuamente, detecta una palabra de activación, procesa comandos de voz mediante servicios cognitivos en la nube, y proporciona respuestas habladas. El asistente puede responder preguntas, proporcionar información contextual, controlar dispositivos domóticos, y gestionar recordatorios.

## Glosario

- **Sistema**: El asistente de voz completo ejecutándose en Raspberry Pi
- **Wake_Word**: Palabra o frase de activación que inicia la escucha activa
- **AWS_Transcribe**: Servicio de AWS para conversión de voz a texto en tiempo real
- **AWS_Polly**: Servicio de AWS para síntesis de texto a voz
- **Amazon_Lex**: Servicio de AWS para procesamiento de lenguaje natural e intenciones
- **AWS_Lambda**: Funciones serverless para lógica de negocio personalizada
- **AWS_IoT_Core**: Plataforma de AWS para comunicación con dispositivos IoT
- **Alexa_Skills_Kit**: Framework de Amazon para funcionalidades de información contextual
- **DynamoDB**: Base de datos NoSQL de AWS para almacenamiento en la nube
- **SQLite_Local**: Base de datos local en la Raspberry Pi para almacenamiento offline
- **Audio_Buffer**: Buffer circular que almacena audio continuo
- **Comando_Voz**: Instrucción hablada por el usuario después del wake word
- **Intención**: Acción o información que el usuario desea obtener
- **Sesión**: Período de interacción activa entre wake word y respuesta completa
- **Dispositivo_Domótico**: Aparato del hogar controlable (luces, termostato, etc.)

## Requisitos

### Requisito 1: Detección de Palabra de Activación

**Historia de Usuario:** Como usuario, quiero activar el asistente con una palabra clave, para que el sistema solo procese comandos cuando lo necesito.

#### Criterios de Aceptación

1. THE Sistema SHALL escuchar audio continuamente desde el micrófono
2. WHEN el Sistema inicia, THE Sistema SHALL establecer una conexión de streaming con AWS_Transcribe
3. WHEN AWS_Transcribe detecta el wake word en el stream de audio, THE Sistema SHALL iniciar una sesión de comando
4. WHEN se detecta el wake word, THE Sistema SHALL proporcionar retroalimentación audible inmediata
5. THE Sistema SHALL usar AWS_Transcribe con vocabulario personalizado para mejorar precisión del wake word

### Requisito 2: Captura y Transcripción de Comandos

**Historia de Usuario:** Como usuario, quiero hablar comandos naturalmente después de la palabra de activación, para que el sistema entienda mis instrucciones.

#### Criterios de Aceptación

1. WHEN una sesión de comando está activa, THE Sistema SHALL continuar usando AWS_Transcribe para capturar el comando completo
2. WHEN el usuario termina de hablar (silencio detectado por AWS_Transcribe), THE Sistema SHALL finalizar la captura
3. WHEN AWS_Transcribe retorna la transcripción final, THE Sistema SHALL almacenar el texto para procesamiento
4. THE Sistema SHALL configurar AWS_Transcribe para español como idioma primario con detección automática
5. IF la transcripción falla o está vacía, THEN THE Sistema SHALL usar AWS_Polly para solicitar al usuario que repita el comando

### Requisito 3: Procesamiento de Intenciones

**Historia de Usuario:** Como usuario, quiero que el asistente entienda diferentes tipos de solicitudes, para que pueda realizar múltiples tareas.

#### Criterios de Aceptación

1. WHEN una transcripción es recibida, THE Sistema SHALL enviar el texto a Amazon_Lex para extracción de intenciones
2. THE Amazon_Lex SHALL estar configurado con al menos 5 intenciones: preguntas generales, información contextual, control domótico, recordatorios, y configuración
3. WHEN Amazon_Lex retorna una intención con baja confianza, THE Sistema SHALL solicitar aclaraciones al usuario
4. WHEN una intención es reconocida con alta confianza, THE Sistema SHALL invocar la AWS_Lambda correspondiente
5. IF Amazon_Lex no puede determinar la intención, THEN THE Sistema SHALL usar AWS_Polly para informar al usuario y solicitar reformular el comando

### Requisito 4: Información Contextual

**Historia de Usuario:** Como usuario, quiero solicitar información del clima, noticias y hora, para mantenerme informado sin usar otros dispositivos.

#### Criterios de Aceptación

1. WHEN el usuario solicita la hora actual, THE AWS_Lambda SHALL proporcionar la hora local con precisión de minutos
2. WHEN el usuario solicita información del clima, THE Sistema SHALL usar Alexa_Skills_Kit para obtener datos meteorológicos
3. WHEN el usuario solicita noticias, THE Sistema SHALL usar Alexa_Skills_Kit para obtener titulares recientes
4. THE Alexa_Skills_Kit SHALL incluir la ubicación del usuario en solicitudes de clima cuando sea relevante
5. WHEN los servicios de Alexa_Skills_Kit no están disponibles, THE Sistema SHALL usar AWS_Polly para informar al usuario del problema

### Requisito 5: Control de Dispositivos Domóticos

**Historia de Usuario:** Como usuario, quiero controlar dispositivos del hogar con comandos de voz, para automatizar mi entorno sin interacción manual.

#### Criterios de Aceptación

1. WHEN el usuario solicita encender o apagar luces, THE AWS_Lambda SHALL publicar comandos a AWS_IoT_Core
2. WHEN el usuario solicita ajustar temperatura, THE AWS_Lambda SHALL enviar mensajes MQTT al termostato vía AWS_IoT_Core
3. WHEN un comando de control es ejecutado, THE Sistema SHALL usar AWS_Polly para confirmar la acción verbalmente
4. IF un Dispositivo_Domótico no responde en 5 segundos, THEN THE Sistema SHALL informar al usuario del fallo
5. THE Sistema SHALL consultar AWS_IoT_Core para mantener un registro actualizado de dispositivos disponibles y sus estados

### Requisito 6: Gestión de Recordatorios y Alarmas

**Historia de Usuario:** Como usuario, quiero configurar recordatorios y alarmas por voz, para organizar mis actividades sin usar otros dispositivos.

#### Criterios de Aceptación

1. WHEN el usuario solicita crear un recordatorio, THE AWS_Lambda SHALL extraer el contenido y tiempo del comando usando Amazon_Lex
2. WHEN un recordatorio es creado, THE Sistema SHALL almacenarlo en SQLite_Local y sincronizarlo con DynamoDB
3. WHEN llega el momento del recordatorio, THE Sistema SHALL usar AWS_Polly para reproducir una alerta audible y el mensaje
4. WHEN el usuario solicita crear una alarma, THE Sistema SHALL almacenarla en SQLite_Local con sincronización a DynamoDB
5. THE Sistema SHALL permitir al usuario listar, modificar y cancelar recordatorios consultando SQLite_Local primero

### Requisito 7: Síntesis y Reproducción de Respuestas

**Historia de Usuario:** Como usuario, quiero recibir respuestas habladas del asistente, para interactuar completamente por voz.

#### Criterios de Aceptación

1. WHEN el Sistema genera una respuesta textual, THE Sistema SHALL enviarla a AWS_Polly para síntesis de voz
2. WHEN AWS_Polly retorna el audio de respuesta, THE Sistema SHALL reproducirlo inmediatamente
3. THE Sistema SHALL configurar AWS_Polly con voz en español (Lupe o Mia) y velocidad ajustable
4. WHEN la reproducción finaliza, THE Sistema SHALL retornar al modo de escucha continua con AWS_Transcribe
5. THE Sistema SHALL cachear respuestas comunes localmente para reducir latencia y costos de AWS_Polly

### Requisito 8: Manejo de Errores y Recuperación

**Historia de Usuario:** Como usuario, quiero que el asistente maneje errores graciosamente, para que el sistema sea confiable incluso con problemas de red.

#### Criterios de Aceptación

1. IF la conexión a AWS_Transcribe, AWS_Polly, o Amazon_Lex falla, THEN THE Sistema SHALL usar AWS_Polly para informar al usuario y reintentar hasta 3 veces
2. IF el micrófono no está disponible, THEN THE Sistema SHALL registrar el error en SQLite_Local y notificar al usuario
3. WHEN ocurre un error durante una sesión, THE Sistema SHALL finalizar la sesión y retornar al modo de escucha
4. THE Sistema SHALL registrar todos los errores en SQLite_Local con timestamp y sincronizar con DynamoDB
5. IF un servicio de AWS no está disponible, THEN THE Sistema SHALL operar en modo degradado usando solo funcionalidades locales

### Requisito 9: Inicialización y Configuración

**Historia de Usuario:** Como administrador del sistema, quiero configurar el asistente fácilmente, para personalizar su comportamiento según mis necesidades.

#### Criterios de Aceptación

1. WHEN el Sistema inicia, THE Sistema SHALL cargar configuración desde un archivo JSON local
2. WHEN el Sistema inicia, THE Sistema SHALL calibrar el micrófono y verificar niveles de audio
3. THE Sistema SHALL validar credenciales de AWS (Access Key, Secret Key, Region) durante la inicialización
4. THE Sistema SHALL verificar conectividad con AWS_Transcribe, AWS_Polly, Amazon_Lex y AWS_IoT_Core antes de iniciar
5. IF la inicialización falla, THEN THE Sistema SHALL registrar el error en SQLite_Local y proporcionar instrucciones de diagnóstico

### Requisito 10: Privacidad y Seguridad

**Historia de Usuario:** Como usuario, quiero que mis datos de voz sean manejados de forma segura, para proteger mi privacidad.

#### Criterios de Aceptación

1. THE Sistema SHALL usar conexiones TLS/SSL para todas las comunicaciones con servicios de AWS
2. THE Sistema SHALL almacenar credenciales de AWS usando variables de entorno o AWS IAM roles
3. THE Sistema SHALL eliminar archivos de audio temporales después de procesamiento exitoso
4. THE Sistema SHALL permitir al usuario deshabilitar el almacenamiento de logs de interacción en DynamoDB
5. THE Sistema SHALL usar AWS KMS para cifrar datos sensibles almacenados en DynamoDB

### Requisito 11: Gestión de Sesiones

**Historia de Usuario:** Como usuario, quiero que el asistente mantenga contexto durante una conversación, para interacciones más naturales.

#### Criterios de Aceptación

1. WHEN una sesión inicia, THE Sistema SHALL crear un contexto de sesión con timestamp
2. WHILE una sesión está activa, THE Sistema SHALL mantener el historial de la conversación
3. WHEN una sesión finaliza (después de respuesta o timeout), THE Sistema SHALL limpiar el contexto
4. THE Sistema SHALL mantener sesiones activas por un máximo de 30 segundos después de la última interacción
5. WHEN el usuario dice "gracias" o "adiós", THE Sistema SHALL finalizar la sesión explícitamente

### Requisito 12: Detección de Idioma

**Historia de Usuario:** Como usuario multilingüe, quiero que el asistente detecte automáticamente mi idioma, para usar el sistema en diferentes lenguas.

#### Criterios de Aceptación

1. WHEN el audio es enviado a AWS_Transcribe, THE Sistema SHALL habilitar detección automática de idioma
2. WHEN AWS_Transcribe detecta el idioma, THE Sistema SHALL configurar AWS_Polly para usar el mismo idioma
3. THE Sistema SHALL soportar al menos español e inglés en AWS_Transcribe y AWS_Polly
4. WHEN el idioma detectado cambia, THE Amazon_Lex SHALL usar el modelo de idioma correspondiente
5. IF el idioma no puede ser detectado con confianza, THEN THE Sistema SHALL usar español como idioma por defecto
