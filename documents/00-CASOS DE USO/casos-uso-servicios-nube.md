# Casos de Uso - Actor: Servicios en la Nube (AWS)

## CU-C01: AWS Transcribe - Procesar Stream de Audio

**Actor Principal:** AWS Transcribe  
**Precondiciones:** Stream de audio recibido desde Raspberry Pi  
**Postcondiciones:** Transcripción de texto retornada al sistema  

**Flujo Principal:**
1. AWS Transcribe recibe stream de audio en tiempo real
2. Aplica modelo de reconocimiento de voz para español
3. Procesa audio usando algoritmos de deep learning
4. Detecta pausas y segmenta el habla automáticamente
5. Genera transcripciones parciales durante el procesamiento
6. Aplica corrección contextual y gramática
7. Retorna transcripción final con nivel de confianza
8. Incluye timestamps para sincronización

**Flujos Alternativos:**
- 2a. Audio de baja calidad detectado
  - 2a1. Aplica filtros de mejora de audio
  - 2a2. Reduce confianza en transcripción
- 4a. Múltiples hablantes detectados
  - 4a1. Intenta separar voces si es posible
  - 4a2. Marca transcripción como "múltiples hablantes"
- 7a. Confianza muy baja en transcripción
  - 7a1. Marca resultado como "incierto"
  - 7a2. Sugiere repetir comando

---

## CU-C02: AWS Polly - Sintetizar Respuesta de Voz

**Actor Principal:** AWS Polly  
**Precondiciones:** Texto de respuesta recibido del sistema  
**Postcondiciones:** Audio sintetizado retornado al sistema  

**Flujo Principal:**
1. AWS Polly recibe texto para síntesis
2. Selecciona voz neural en español (Lupe o Mia)
3. Analiza texto para pronunciación correcta
4. Aplica reglas de prosodia y entonación
5. Genera audio usando síntesis neural
6. Optimiza calidad para reproducción en altavoces pequeños
7. Retorna archivo de audio en formato MP3/PCM
8. Incluye metadatos de duración y calidad

**Flujos Alternativos:**
- 3a. Texto contiene palabras no reconocidas
  - 3a1. Aplica reglas fonéticas por defecto
  - 3a2. Marca palabras problemáticas en metadatos
- 5a. Texto muy largo (>3000 caracteres)
  - 5a1. Segmenta texto en partes manejables
  - 5a2. Genera múltiples archivos de audio
- 6a. Configuración de voz no disponible
  - 6a1. Usa voz alternativa disponible
  - 6a2. Notifica cambio de voz al sistema

---

## CU-C03: Amazon Lex - Procesar Intención de Usuario

**Actor Principal:** Amazon Lex  
**Precondiciones:** Transcripción de texto recibida del sistema  
**Postcondiciones:** Intención y entidades extraídas retornadas  

**Flujo Principal:**
1. Amazon Lex recibe texto transcrito
2. Aplica modelo de NLU entrenado para el dominio
3. Identifica intención principal del usuario
4. Extrae entidades relevantes (fechas, números, nombres)
5. Calcula nivel de confianza para la intención
6. Determina si se necesita información adicional
7. Retorna intención, entidades y nivel de confianza
8. Incluye sugerencias para aclaración si es necesario

**Flujos Alternativos:**
- 3a. Múltiples intenciones posibles detectadas
  - 3a1. Retorna intención con mayor confianza
  - 3a2. Incluye intenciones alternativas en respuesta
- 4a. Entidades ambiguas o incompletas
  - 4a1. Marca entidades como "requiere aclaración"
  - 4a2. Sugiere preguntas específicas para completar
- 5a. Confianza muy baja en todas las intenciones
  - 5a1. Retorna intención "NoEntendido"
  - 5a2. Sugiere reformular el comando

---

## CU-C04: AWS Lambda - Ejecutar Lógica de Negocio

**Actor Principal:** AWS Lambda  
**Precondiciones:** Intención y entidades recibidas de Amazon Lex  
**Postcondiciones:** Acción ejecutada y respuesta generada  

**Flujo Principal:**
1. AWS Lambda recibe evento con intención y entidades
2. Valida parámetros de entrada y permisos
3. Ejecuta lógica específica según la intención
4. Interactúa con otros servicios AWS según sea necesario
5. Procesa resultados y maneja errores
6. Genera respuesta estructurada para el usuario
7. Registra métricas de ejecución y logs
8. Retorna respuesta al sistema llamador

**Flujos Alternativos:**
- 2a. Parámetros inválidos o faltantes
  - 2a1. Retorna error de validación
  - 2a2. Especifica qué parámetros son requeridos
- 4a. Servicio externo no disponible
  - 4a1. Implementa lógica de fallback
  - 4a2. Retorna respuesta con funcionalidad limitada
- 5a. Timeout en procesamiento
  - 5a1. Retorna respuesta parcial si es posible
  - 5a2. Registra error para análisis posterior

---

## CU-C05: AWS IoT Core - Gestionar Dispositivos Domóticos

**Actor Principal:** AWS IoT Core  
**Precondiciones:** Comando de control recibido de AWS Lambda  
**Postcondiciones:** Comando enviado a dispositivo y estado actualizado  

**Flujo Principal:**
1. AWS IoT Core recibe comando para dispositivo específico
2. Valida que el dispositivo esté registrado y activo
3. Verifica permisos para el comando solicitado
4. Publica mensaje MQTT al topic del dispositivo
5. Espera confirmación del dispositivo (ACK)
6. Actualiza shadow del dispositivo con nuevo estado
7. Retorna confirmación de ejecución exitosa
8. Registra evento en logs de IoT

**Flujos Alternativos:**
- 2a. Dispositivo no registrado o inactivo
  - 2a1. Retorna error "dispositivo no disponible"
  - 2a2. Sugiere verificar configuración
- 5a. Dispositivo no responde en tiempo límite
  - 5a1. Marca dispositivo como "no responsivo"
  - 5a2. Retorna error de timeout
- 6a. Error al actualizar device shadow
  - 6a1. Reintenta actualización una vez
  - 6a2. Registra inconsistencia de estado

---

## CU-C06: DynamoDB - Sincronizar Datos de Usuario

**Actor Principal:** DynamoDB  
**Precondiciones:** Datos de sincronización recibidos del sistema  
**Postcondiciones:** Datos almacenados y disponibles para consulta  

**Flujo Principal:**
1. DynamoDB recibe operación de escritura/lectura
2. Valida formato y estructura de los datos
3. Verifica capacidad de lectura/escritura disponible
4. Ejecuta operación en la tabla correspondiente
5. Aplica índices secundarios si es necesario
6. Retorna confirmación de operación exitosa
7. Actualiza métricas de uso y rendimiento
8. Mantiene consistencia eventual entre réplicas

**Flujos Alternativos:**
- 3a. Capacidad de escritura excedida
  - 3a1. Aplica throttling automático
  - 3a2. Reintenta operación con backoff
- 4a. Datos no cumplen esquema esperado
  - 4a1. Retorna error de validación
  - 4a2. Especifica campos problemáticos
- 8a. Falla en replicación entre regiones
  - 8a1. Registra inconsistencia temporal
  - 8a2. Programa reconciliación automática

---

## CU-C07: Alexa Skills Kit - Obtener Información Contextual

**Actor Principal:** Alexa Skills Kit  
**Precondiciones:** Solicitud de información recibida de AWS Lambda  
**Postcondiciones:** Información contextual retornada al sistema  

**Flujo Principal:**
1. Alexa Skills Kit recibe solicitud de información
2. Identifica tipo de información requerida (clima, noticias, etc.)
3. Consulta APIs externas correspondientes
4. Procesa y filtra información relevante
5. Formatea respuesta en lenguaje natural
6. Aplica personalización según perfil del usuario
7. Retorna información estructurada
8. Registra uso para análisis y mejoras

**Flujos Alternativos:**
- 3a. API externa no disponible
  - 3a1. Intenta fuente alternativa de información
  - 3a2. Retorna mensaje de servicio no disponible
- 4a. Información no relevante o desactualizada
  - 4a1. Filtra contenido obsoleto
  - 4a2. Marca información como "limitada"
- 6a. Perfil de usuario no disponible
  - 6a1. Usa configuración por defecto
  - 6a2. Retorna información genérica

---

## CU-C08: AWS KMS - Cifrar Datos Sensibles

**Actor Principal:** AWS KMS  
**Precondiciones:** Datos sensibles requieren cifrado  
**Postcondiciones:** Datos cifrados y claves gestionadas  

**Flujo Principal:**
1. AWS KMS recibe solicitud de cifrado/descifrado
2. Valida permisos del solicitante
3. Selecciona clave de cifrado apropiada
4. Ejecuta operación criptográfica solicitada
5. Registra uso de clave para auditoría
6. Retorna datos cifrados/descifrados
7. Actualiza métricas de uso de claves
8. Mantiene rotación automática de claves

**Flujos Alternativos:**
- 2a. Permisos insuficientes para la operación
  - 2a1. Retorna error de autorización
  - 2a2. Registra intento no autorizado
- 3a. Clave de cifrado no disponible
  - 3a1. Crea nueva clave si está autorizado
  - 3a2. Retorna error si no puede crear
- 8a. Falla en rotación de clave
  - 8a1. Mantiene clave actual temporalmente
  - 8a2. Programa reintento de rotación

---

## CU-C09: CloudWatch - Monitorear Sistema

**Actor Principal:** CloudWatch  
**Precondiciones:** Métricas y logs enviados desde servicios AWS  
**Postcondiciones:** Monitoreo activo y alertas configuradas  

**Flujo Principal:**
1. CloudWatch recibe métricas de todos los servicios AWS
2. Almacena métricas con timestamps precisos
3. Aplica agregaciones y estadísticas configuradas
4. Evalúa alarmas y umbrales definidos
5. Genera alertas cuando se superan límites
6. Mantiene dashboards actualizados en tiempo real
7. Retiene datos históricos según configuración
8. Proporciona APIs para consulta de métricas

**Flujos Alternativos:**
- 4a. Umbral de alarma superado
  - 4a1. Envía notificación inmediata
  - 4a2. Ejecuta acciones automáticas si están configuradas
- 5a. Múltiples alarmas simultáneas
  - 5a1. Prioriza alarmas críticas
  - 5a2. Agrupa notificaciones relacionadas
- 7a. Límite de retención alcanzado
  - 7a1. Archiva datos antiguos automáticamente
  - 7a2. Mantiene resúmenes estadísticos

---

## CU-C10: S3 - Almacenar Backups y Archivos

**Actor Principal:** Amazon S3  
**Precondiciones:** Archivos de backup enviados desde el sistema  
**Postcondiciones:** Archivos almacenados de forma segura y durable  

**Flujo Principal:**
1. S3 recibe archivo de backup del sistema
2. Valida integridad del archivo recibido
3. Aplica cifrado en reposo automáticamente
4. Almacena archivo en bucket configurado
5. Replica datos en múltiples zonas de disponibilidad
6. Aplica políticas de lifecycle si están configuradas
7. Retorna confirmación de almacenamiento exitoso
8. Actualiza metadatos y versionado del objeto

**Flujos Alternativos:**
- 2a. Archivo corrupto detectado
  - 2a1. Rechaza upload y notifica error
  - 2a2. Solicita reenvío del archivo
- 4a. Bucket no disponible o lleno
  - 4a1. Retorna error de capacidad
  - 4a2. Sugiere configuración alternativa
- 6a. Política de lifecycle elimina archivo
  - 6a1. Ejecuta eliminación según programación
  - 6a2. Registra acción en logs de auditoría