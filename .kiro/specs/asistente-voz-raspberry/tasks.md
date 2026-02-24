# Plan de Implementación: Asistente de Voz para Raspberry Pi

## Resumen

Este plan de implementación desglosa el desarrollo del asistente de voz en tareas incrementales y manejables. Cada tarea construye sobre las anteriores, asegurando que el sistema se desarrolle de forma iterativa con validación continua.

**Lenguaje de Implementación:** Python 3.9+  
**Plataforma:** Raspberry Pi Zero 2W  
**Servicios Cloud:** AWS (Transcribe, Polly, Lex, Lambda, IoT Core, DynamoDB)

## Tareas

- [x] 1. Configuración inicial del proyecto y estructura
  - Crear estructura de directorios del proyecto
  - Configurar entorno virtual de Python
  - Crear archivo requirements.txt con dependencias
  - Configurar archivo de configuración config.json
  - Crear archivo .env.example para variables de entorno
  - Inicializar repositorio Git con .gitignore apropiado
  - _Requisitos: 9.1_

- [x] 2. Implementar Audio Manager
  - [x] 2.1 Crear clase AudioManager con captura básica de audio
    - Implementar inicialización de PyAudio
    - Configurar parámetros de audio (sample rate, channels, chunk size)
    - Implementar captura continua con buffer circular
    - _Requisitos: 1.1, 9.2_
  
  - [x] 2.2 Implementar calibración automática de micrófono
    - Detectar dispositivos de audio disponibles
    - Analizar niveles de ruido de fondo
    - Ajustar ganancia y sensibilidad automáticamente
    - _Requisitos: 9.2_
  
  - [x] 2.3 Implementar reproducción de audio
    - Configurar dispositivo de salida de audio
    - Implementar método play_audio() para reproducir bytes de audio
    - Gestionar cola de reproducción para múltiples audios
    - _Requisitos: 7.2_
  
  - [ ]* 2.4 Escribir pruebas unitarias para AudioManager
    - Probar inicialización con diferentes configuraciones
    - Probar captura de audio con mock de PyAudio
    - Probar reproducción de audio
    - _Requisitos: 1.1, 9.2_

- [x] 3. Implementar integración con AWS Transcribe
  - [x] 3.1 Crear cliente de AWS Transcribe con streaming
    - Configurar boto3 para AWS Transcribe
    - Implementar conexión de streaming persistente
    - Manejar autenticación con credenciales AWS
    - _Requisitos: 1.2, 2.1_
  
  - [x] 3.2 Implementar envío de audio a Transcribe en tiempo real
    - Convertir chunks de audio al formato requerido
    - Enviar audio continuamente al stream de Transcribe
    - Recibir transcripciones parciales y finales
    - _Requisitos: 2.1, 2.2_
  
  - [ ]* 3.3 Escribir prueba de propiedad para captura completa de comando
    - **Propiedad 2: Captura Completa de Comando**
    - **Valida: Requisitos 2.1, 2.2, 2.3**

- [x] 4. Implementar Wake Word Detector
  - [x] 4.1 Crear clase WakeWordDetector
    - Implementar detección de wake word usando transcripciones de Transcribe
    - Configurar umbral de confianza para detección
    - Implementar sistema de callbacks para wake word detectado
    - _Requisitos: 1.3, 1.4_
  
  - [x] 4.2 Implementar filtrado de falsos positivos
    - Validar contexto de la detección
    - Implementar ventana de tiempo para confirmación
    - _Requisitos: 1.3_
  
  - [ ]* 4.3 Escribir prueba de propiedad para detección de wake word
    - **Propiedad 1: Detección de Wake Word Inicia Sesión**
    - **Valida: Requisitos 1.3, 1.4**

- [ ] 5. Checkpoint - Verificar captura y transcripción de audio
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

- [ ] 6. Implementar Session Manager
  - [ ] 6.1 Crear clase SessionManager para gestión de sesiones
    - Implementar creación de sesiones con ID único
    - Mantener registro de sesiones activas
    - Implementar cierre de sesiones
    - _Requisitos: 11.1, 11.3_
  
  - [ ] 6.2 Implementar limpieza automática de sesiones expiradas
    - Verificar timeout de sesiones (30 segundos)
    - Limpiar contexto de sesiones expiradas
    - Programar tarea periódica de limpieza
    - _Requisitos: 11.4_
  
  - [ ] 6.3 Implementar mantenimiento de historial de conversación
    - Almacenar comandos y respuestas durante sesión activa
    - Proporcionar acceso al historial para contexto
    - _Requisitos: 11.2_
  
  - [ ]* 6.4 Escribir pruebas de propiedad para gestión de sesiones
    - **Propiedad 15: Mantenimiento de Historial de Sesión**
    - **Propiedad 16: Timeout de Sesiones Inactivas**
    - **Valida: Requisitos 11.2, 11.4**

- [ ] 7. Implementar integración con Amazon Lex
  - [ ] 7.1 Crear cliente de Amazon Lex
    - Configurar boto3 para Amazon Lex
    - Implementar método para enviar texto a Lex
    - Parsear respuesta de Lex (intención, entidades, confianza)
    - _Requisitos: 3.1_
  
  - [ ] 7.2 Implementar manejo de intenciones con baja confianza
    - Detectar cuando confianza < 0.8
    - Generar solicitud de aclaración al usuario
    - _Requisitos: 3.3_
  
  - [ ]* 7.3 Escribir prueba de propiedad para procesamiento de intenciones
    - **Propiedad 3: Procesamiento de Intención con Alta Confianza**
    - **Valida: Requisitos 3.1, 3.4**
  
  - [ ]* 7.4 Escribir prueba unitaria para caso edge de baja confianza
    - Probar que se solicita aclaración cuando confianza < 0.8
    - _Requisitos: 3.3_

- [ ] 8. Implementar Command Processor
  - [ ] 8.1 Crear clase CommandProcessor
    - Integrar con Amazon Lex para extracción de intenciones
    - Implementar routing de intenciones a handlers específicos
    - Manejar respuestas y errores
    - _Requisitos: 3.1, 3.4_
  
  - [ ] 8.2 Implementar handlers para intenciones básicas
    - Handler para ConsultarHora (retorna hora actual)
    - Handler para ConsultarClima (placeholder)
    - Handler para ConsultarNoticias (placeholder)
    - _Requisitos: 4.1, 4.2, 4.3_
  
  - [ ]* 8.3 Escribir pruebas unitarias para handlers de intenciones
    - Probar handler de hora con diferentes zonas horarias
    - Probar manejo de intenciones no reconocidas
    - _Requisitos: 4.1_

- [ ] 9. Implementar integración con AWS Polly
  - [ ] 9.1 Crear clase ResponseGenerator con AWS Polly
    - Configurar boto3 para AWS Polly
    - Implementar síntesis de texto a voz
    - Configurar voz en español (Lupe o Mia)
    - _Requisitos: 7.1_
  
  - [ ] 9.2 Implementar cache de respuestas comunes
    - Crear sistema de cache en memoria y disco
    - Implementar lógica de cache hit/miss
    - Configurar TTL para entradas de cache
    - _Requisitos: 7.5_
  
  - [ ] 9.3 Integrar reproducción de respuestas con AudioManager
    - Conectar audio sintetizado con AudioManager.play_audio()
    - Implementar retorno a modo de escucha después de reproducción
    - _Requisitos: 7.2, 7.4_
  
  - [ ]* 9.4 Escribir pruebas de propiedad para respuestas de voz
    - **Propiedad 10: Flujo Completo de Respuesta de Voz**
    - **Propiedad 11: Cache de Respuestas Comunes**
    - **Valida: Requisitos 7.1, 7.2, 7.4, 7.5**

- [ ] 10. Checkpoint - Verificar flujo completo de comando básico
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

- [ ] 11. Implementar Data Manager con SQLite
  - [ ] 11.1 Crear esquema de base de datos SQLite
    - Crear tablas: reminders, configuration, logs, iot_devices
    - Implementar índices para consultas eficientes
    - Crear script de inicialización de BD
    - _Requisitos: 6.2, 8.4_
  
  - [ ] 11.2 Crear clase DataManager con operaciones CRUD
    - Implementar save_reminder(), get_reminder(), delete_reminder()
    - Implementar get_pending_reminders()
    - Implementar operaciones de configuración
    - Implementar logging de errores
    - _Requisitos: 6.2, 6.5, 8.4_
  
  - [ ]* 11.3 Escribir prueba de propiedad para round-trip de recordatorios
    - **Propiedad 7: Round-Trip de Recordatorios**
    - **Valida: Requisitos 6.1, 6.2, 6.4**
  
  - [ ]* 11.4 Escribir prueba de propiedad para operaciones CRUD
    - **Propiedad 9: Operaciones CRUD de Recordatorios**
    - **Valida: Requisitos 6.5**

- [ ] 12. Implementar sincronización con DynamoDB
  - [ ] 12.1 Crear cliente de DynamoDB
    - Configurar boto3 para DynamoDB
    - Implementar operaciones de lectura/escritura
    - Manejar errores de conexión y throttling
    - _Requisitos: 6.2_
  
  - [ ] 12.2 Implementar lógica de sincronización bidireccional
    - Detectar cambios locales desde última sincronización
    - Enviar cambios a DynamoDB en lotes
    - Manejar conflictos de sincronización
    - Implementar reintentos con backoff exponencial
    - _Requisitos: 6.2_
  
  - [ ] 12.3 Implementar sincronización periódica en background
    - Crear tarea asíncrona para sincronización cada 5 minutos
    - Manejar modo offline cuando DynamoDB no está disponible
    - _Requisitos: 6.2_
  
  - [ ]* 12.4 Escribir pruebas unitarias para sincronización
    - Probar sincronización exitosa
    - Probar manejo de errores de red
    - Probar modo offline
    - _Requisitos: 6.2_

- [ ] 13. Implementar gestión de recordatorios
  - [ ] 13.1 Implementar handler de intención CrearRecordatorio
    - Extraer contenido y tiempo del comando usando Lex
    - Validar fecha/hora del recordatorio
    - Almacenar recordatorio en SQLite
    - Confirmar creación al usuario
    - _Requisitos: 6.1, 6.2_
  
  - [ ] 13.2 Implementar sistema de ejecución de recordatorios
    - Crear tarea periódica que verifica recordatorios pendientes
    - Ejecutar recordatorios cuando llega su tiempo
    - Generar alerta audible con AWS Polly
    - Marcar recordatorio como ejecutado
    - _Requisitos: 6.3_
  
  - [ ] 13.3 Implementar handlers para listar y cancelar recordatorios
    - Handler para ListarRecordatorios
    - Handler para CancelarRecordatorio
    - _Requisitos: 6.5_
  
  - [ ]* 13.4 Escribir prueba de propiedad para ejecución de recordatorios
    - **Propiedad 8: Ejecución de Recordatorios en Tiempo Programado**
    - **Valida: Requisitos 6.3**

- [ ] 14. Implementar integración con Alexa Skills Kit
  - [ ] 14.1 Crear cliente para Alexa Skills Kit
    - Configurar acceso a Alexa Skills Kit vía AWS Lambda
    - Implementar obtención de información del clima
    - Implementar obtención de noticias
    - _Requisitos: 4.2, 4.3_
  
  - [ ] 14.2 Implementar inclusión de ubicación en consultas de clima
    - Obtener ubicación del usuario desde configuración
    - Incluir ubicación en solicitudes a Alexa Skills Kit
    - _Requisitos: 4.4_
  
  - [ ]* 14.3 Escribir prueba de propiedad para inclusión de ubicación
    - **Propiedad 4: Inclusión de Ubicación en Consultas de Clima**
    - **Valida: Requisitos 4.4**
  
  - [ ]* 14.4 Escribir pruebas unitarias para información contextual
    - Probar obtención de clima con ubicación
    - Probar obtención de noticias
    - Probar manejo de servicios no disponibles
    - _Requisitos: 4.2, 4.3, 4.5_

- [ ] 15. Checkpoint - Verificar recordatorios e información contextual
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

- [ ] 16. Implementar IoT Controller para dispositivos domóticos
  - [ ] 16.1 Crear clase IoTController con AWS IoT Core
    - Configurar conexión MQTT con AWS IoT Core
    - Implementar autenticación con certificados X.509
    - Implementar publicación de mensajes a topics
    - Implementar suscripción a topics de estado
    - _Requisitos: 5.1, 5.2_
  
  - [ ] 16.2 Implementar envío de comandos a dispositivos
    - Implementar send_device_command() para luces
    - Implementar send_device_command() para termostato
    - Implementar timeout de 5 segundos para respuestas
    - Generar confirmación verbal de acciones
    - _Requisitos: 5.1, 5.2, 5.3, 5.4_
  
  - [ ] 16.3 Implementar monitoreo de estado de dispositivos
    - Suscribirse a topics de estado de dispositivos
    - Actualizar base de datos local con estados
    - Detectar dispositivos offline
    - _Requisitos: 5.5_
  
  - [ ]* 16.4 Escribir pruebas de propiedad para control IoT
    - **Propiedad 5: Comandos IoT Publicados a AWS IoT Core**
    - **Propiedad 6: Consulta de Estado de Dispositivos IoT**
    - **Valida: Requisitos 5.1, 5.2, 5.3, 5.5**
  
  - [ ]* 16.5 Escribir prueba unitaria para timeout de dispositivos
    - Probar que se informa al usuario cuando dispositivo no responde
    - _Requisitos: 5.4_

- [ ] 17. Implementar handlers de intenciones para control domótico
  - [ ] 17.1 Implementar handler para ControlLuces
    - Extraer dispositivo y acción (encender/apagar) de entidades Lex
    - Invocar IoTController para enviar comando
    - Manejar respuesta y confirmar al usuario
    - _Requisitos: 5.1, 5.3_
  
  - [ ] 17.2 Implementar handler para AjustarTemperatura
    - Extraer temperatura deseada de entidades Lex
    - Validar rango de temperatura (16-30°C)
    - Invocar IoTController para ajustar termostato
    - _Requisitos: 5.2, 5.3_
  
  - [ ]* 17.3 Escribir pruebas unitarias para handlers IoT
    - Probar control de luces con diferentes dispositivos
    - Probar ajuste de temperatura con validación de rango
    - _Requisitos: 5.1, 5.2_

- [ ] 18. Implementar manejo de errores y modo degradado
  - [ ] 18.1 Crear clase ErrorHandler
    - Implementar categorización de errores
    - Implementar logging de errores en SQLite
    - Implementar generación de mensajes de error para usuario
    - _Requisitos: 8.1, 8.2, 8.4_
  
  - [ ] 18.2 Implementar reintentos con backoff exponencial
    - Crear función retry_with_backoff()
    - Aplicar a llamadas a servicios AWS
    - Configurar máximo de 3 reintentos
    - _Requisitos: 8.1_
  
  - [ ] 18.3 Implementar DegradedModeManager
    - Detectar servicios AWS no disponibles
    - Activar modo degradado cuando sea necesario
    - Proporcionar funcionalidad limitada usando recursos locales
    - Monitorear disponibilidad de servicios para restauración
    - _Requisitos: 8.5_
  
  - [ ] 18.4 Implementar finalización de sesión en errores
    - Asegurar que errores durante sesión cierren la sesión
    - Retornar al modo de escucha continua
    - _Requisitos: 8.3_
  
  - [ ]* 18.5 Escribir prueba de propiedad para manejo de errores
    - **Propiedad 12: Finalización de Sesión en Error**
    - **Valida: Requisitos 8.3, 8.4**
  
  - [ ]* 18.6 Escribir pruebas unitarias para casos edge de errores
    - Probar reintentos con fallas de red
    - Probar modo degradado cuando AWS no disponible
    - Probar manejo de micrófono no disponible
    - _Requisitos: 8.1, 8.2, 8.5_

- [ ] 19. Implementar detección de idioma y sincronización
  - [ ] 19.1 Configurar AWS Transcribe con detección automática de idioma
    - Habilitar detección de idioma en configuración de Transcribe
    - Soportar español e inglés
    - _Requisitos: 12.1, 12.3_
  
  - [ ] 19.2 Implementar sincronización de idioma entre servicios
    - Detectar idioma de transcripción
    - Configurar AWS Polly con mismo idioma
    - Configurar Amazon Lex con modelo de idioma correspondiente
    - Implementar fallback a español si detección falla
    - _Requisitos: 12.2, 12.4, 12.5_
  
  - [ ]* 19.3 Escribir prueba de propiedad para sincronización de idioma
    - **Propiedad 17: Sincronización de Idioma entre Servicios**
    - **Valida: Requisitos 12.2, 12.4**
  
  - [ ]* 19.4 Escribir prueba unitaria para fallback de idioma
    - Probar que se usa español cuando detección falla
    - _Requisitos: 12.5_

- [ ] 20. Checkpoint - Verificar control IoT y manejo de errores
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

- [ ] 21. Implementar seguridad y privacidad
  - [ ] 21.1 Implementar limpieza de archivos de audio temporales
    - Eliminar archivos de audio después de procesamiento exitoso
    - Implementar limpieza automática periódica
    - _Requisitos: 10.3_
  
  - [ ] 21.2 Implementar respeto de configuración de privacidad
    - Leer configuración de privacidad del usuario
    - Deshabilitar sincronización de logs si está configurado
    - Deshabilitar almacenamiento de transcripciones si está configurado
    - _Requisitos: 10.4_
  
  - [ ] 21.3 Configurar cifrado con AWS KMS para DynamoDB
    - Configurar tabla de DynamoDB con cifrado KMS
    - Configurar permisos IAM para acceso a KMS
    - _Requisitos: 10.5_
  
  - [ ]* 21.4 Escribir pruebas de propiedad para privacidad
    - **Propiedad 13: Limpieza de Archivos de Audio Temporales**
    - **Propiedad 14: Respeto de Configuración de Privacidad**
    - **Valida: Requisitos 10.3, 10.4**

- [ ] 22. Implementar sistema de inicialización completo
  - [ ] 22.1 Crear clase VoiceAssistantSystem principal
    - Coordinar inicialización de todos los componentes
    - Implementar método initialize() que valida todo
    - Implementar método run() para loop principal
    - Implementar método shutdown() para cierre gracioso
    - _Requisitos: 9.1, 9.2, 9.3, 9.4_
  
  - [ ] 22.2 Implementar validación de inicialización
    - Cargar y validar configuración desde config.json
    - Validar credenciales AWS
    - Verificar conectividad con todos los servicios AWS
    - Calibrar micrófono
    - _Requisitos: 9.1, 9.2, 9.3, 9.4_
  
  - [ ] 22.3 Implementar manejo de fallos de inicialización
    - Registrar errores en SQLite
    - Proporcionar instrucciones de diagnóstico
    - Terminar graciosamente si inicialización falla
    - _Requisitos: 9.5_
  
  - [ ]* 22.4 Escribir pruebas unitarias para inicialización
    - Probar carga de configuración
    - Probar validación de credenciales
    - Probar calibración de micrófono
    - Probar manejo de fallos de inicialización
    - _Requisitos: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 23. Implementar optimizaciones de rendimiento
  - [ ] 23.1 Implementar cache multinivel
    - Cache en memoria para respuestas frecuentes
    - Cache en disco para persistencia
    - Implementar políticas de evicción (LRU)
    - _Requisitos: 7.5_
  
  - [ ] 23.2 Implementar procesamiento asíncrono
    - Usar asyncio para operaciones I/O
    - Implementar ThreadPoolExecutor para tareas CPU-bound
    - Optimizar paralelización de llamadas AWS
    - _Requisitos: 2.1, 3.1, 7.1_
  
  - [ ] 23.3 Optimizar streaming de audio
    - Reducir latencia en captura y envío
    - Implementar compresión de audio si es necesario
    - Optimizar tamaño de chunks
    - _Requisitos: 1.1, 2.1_

- [ ] 24. Implementar monitoreo y observabilidad
  - [ ] 24.1 Crear clase MetricsCollector
    - Registrar métricas clave (detecciones, comandos, errores)
    - Calcular estadísticas (tiempo de respuesta promedio)
    - Implementar envío de métricas a CloudWatch
    - _Requisitos: 8.4_
  
  - [ ] 24.2 Implementar logging estructurado
    - Configurar structlog para logging
    - Incluir contexto en todos los logs (session_id, intent, etc.)
    - Implementar niveles de log apropiados
    - _Requisitos: 8.4_
  
  - [ ] 24.3 Crear dashboard de monitoreo
    - Configurar CloudWatch dashboard con métricas clave
    - Configurar alarmas para errores críticos
    - _Requisitos: 8.4_

- [ ] 25. Implementar backup y recuperación
  - [ ] 25.1 Crear clase BackupManager
    - Implementar backup diario de SQLite
    - Comprimir archivos de configuración y logs
    - Mantener últimos 7 backups locales
    - _Requisitos: 10.3_
  
  - [ ] 25.2 Implementar backup opcional a S3
    - Configurar upload de backups a S3 si está habilitado
    - Implementar verificación de integridad de backups
    - _Requisitos: 10.3_
  
  - [ ] 25.3 Implementar recuperación desde backup
    - Crear script de restauración desde backup
    - Validar integridad antes de restaurar
    - _Requisitos: 10.3_

- [ ] 26. Checkpoint - Verificar sistema completo
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

- [ ] 27. Crear scripts de instalación y despliegue
  - [ ] 27.1 Crear script install.sh para Raspberry Pi
    - Instalar dependencias del sistema (portaudio, etc.)
    - Instalar dependencias de Python
    - Crear base de datos SQLite inicial
    - Configurar variables de entorno
    - _Requisitos: 9.1_
  
  - [ ] 27.2 Crear servicio systemd
    - Crear archivo voice-assistant.service
    - Configurar auto-inicio en boot
    - Configurar reinicio automático en fallos
    - _Requisitos: 9.1_
  
  - [ ] 27.3 Crear script de configuración inicial
    - Script interactivo para configurar credenciales AWS
    - Configurar ubicación del usuario
    - Configurar dispositivos IoT
    - _Requisitos: 9.1_

- [ ] 28. Crear documentación de usuario
  - [ ] 28.1 Crear README.md con instrucciones de instalación
    - Requisitos de hardware
    - Pasos de instalación
    - Configuración inicial
    - Comandos disponibles
  
  - [ ] 28.2 Crear guía de configuración de AWS
    - Configuración de servicios AWS necesarios
    - Creación de IAM roles y políticas
    - Configuración de Amazon Lex bot
    - Configuración de AWS IoT Core
  
  - [ ] 28.3 Crear guía de troubleshooting
    - Problemas comunes y soluciones
    - Interpretación de logs
    - Comandos de diagnóstico

- [ ] 29. Pruebas de integración end-to-end
  - [ ]* 29.1 Escribir prueba de flujo completo de comando
    - Simular wake word → comando → respuesta
    - Verificar que todos los componentes interactúan correctamente
    - _Requisitos: 1.1, 1.3, 2.1, 3.1, 7.1, 7.2_
  
  - [ ]* 29.2 Escribir prueba de integración con AWS
    - Probar conexión real con servicios AWS (en ambiente de test)
    - Verificar transcripción, síntesis y procesamiento de intenciones
    - _Requisitos: 1.2, 2.1, 3.1, 7.1_
  
  - [ ]* 29.3 Escribir prueba de integración IoT
    - Probar control de dispositivos IoT reales o simulados
    - Verificar publicación y suscripción MQTT
    - _Requisitos: 5.1, 5.2, 5.5_

- [ ] 30. Optimización final y ajustes
  - [ ] 30.1 Realizar pruebas de rendimiento en Raspberry Pi
    - Medir uso de CPU y memoria
    - Medir latencia de respuesta
    - Identificar cuellos de botella
  
  - [ ] 30.2 Optimizar consumo de recursos
    - Ajustar tamaños de buffer
    - Optimizar frecuencia de sincronización
    - Reducir uso de memoria si es necesario
  
  - [ ] 30.3 Ajustar configuración de producción
    - Configurar niveles de log apropiados
    - Ajustar timeouts y reintentos
    - Configurar límites de cache

- [ ] 31. Checkpoint final - Sistema listo para producción
  - Asegurar que todos los tests pasen, preguntar al usuario si surgen dudas.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia los requisitos específicos que implementa para trazabilidad
- Los checkpoints aseguran validación incremental del sistema
- Las pruebas de propiedades validan corrección universal, mientras que las pruebas unitarias validan casos específicos y edge cases
- Se recomienda ejecutar las tareas en orden secuencial para asegurar que las dependencias estén disponibles