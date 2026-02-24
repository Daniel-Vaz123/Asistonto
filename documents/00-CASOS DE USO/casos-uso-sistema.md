# Casos de Uso - Actor: Sistema

## CU-S01: Inicializar Servicios AWS

**Actor Principal:** Sistema  
**Precondiciones:** Raspberry Pi está encendida y tiene conectividad de red  
**Postcondiciones:** Todos los servicios AWS están conectados y operativos  

**Flujo Principal:**
1. El sistema carga configuración desde archivo JSON local
2. Valida credenciales AWS (Access Key, Secret Key, Region)
3. Establece conexión con AWS Transcribe para streaming
4. Configura cliente AWS Polly con voz en español
5. Inicializa conexión con Amazon Lex
6. Conecta con AWS IoT Core para dispositivos domóticos
7. Verifica acceso a DynamoDB para sincronización
8. Registra estado de inicialización exitosa

**Flujos Alternativos:**
- 2a. Credenciales AWS inválidas
  - 2a1. Registra error en SQLite local
  - 2a2. Termina inicialización con código de error
- 3a-7a. Falla conexión con algún servicio AWS
  - 3a1. Registra el servicio no disponible
  - 3a2. Continúa con servicios disponibles
  - 3a3. Marca sistema en modo degradado

---

## CU-S02: Calibrar Micrófono

**Actor Principal:** Sistema  
**Precondiciones:** Hardware de audio está conectado  
**Postcondiciones:** Micrófono está calibrado para captura óptima  

**Flujo Principal:**
1. El sistema detecta dispositivos de audio disponibles
2. Selecciona el micrófono configurado por defecto
3. Realiza prueba de captura de 5 segundos
4. Analiza niveles de ruido de fondo
5. Ajusta ganancia y sensibilidad automáticamente
6. Configura filtros de ruido si es necesario
7. Almacena configuración de audio en archivo local
8. Confirma calibración exitosa

**Flujos Alternativos:**
- 1a. No se detecta micrófono
  - 1a1. Registra error crítico
  - 1a2. Termina inicialización
- 4a. Niveles de ruido muy altos
  - 4a1. Ajusta configuración para ambiente ruidoso
  - 4a2. Registra advertencia sobre calidad de audio

---

## CU-S03: Procesar Stream de Audio Continuo

**Actor Principal:** Sistema  
**Precondiciones:** Micrófono calibrado y AWS Transcribe conectado  
**Postcondiciones:** Audio se procesa continuamente para detección de wake word  

**Flujo Principal:**
1. El sistema inicia captura continua de audio
2. Envía stream de audio a AWS Transcribe en tiempo real
3. Recibe transcripciones parciales continuamente
4. Analiza cada transcripción parcial para wake word
5. Mantiene buffer circular de últimos 10 segundos de audio
6. Registra estadísticas de calidad de audio cada minuto
7. Continúa procesamiento hasta comando de parada

**Flujos Alternativos:**
- 2a. Conexión con AWS Transcribe se pierde
  - 2a1. Intenta reconectar automáticamente
  - 2a2. Si falla, registra error y pausa procesamiento
- 4a. Detección de wake word con baja confianza
  - 4a1. Requiere confirmación adicional
  - 4a2. Continúa escuchando si no se confirma

---

## CU-S04: Gestionar Sesión de Comando

**Actor Principal:** Sistema  
**Precondiciones:** Wake word detectado exitosamente  
**Postcondiciones:** Comando del usuario procesado y respondido  

**Flujo Principal:**
1. El sistema crea nueva sesión con ID único y timestamp
2. Reproduce sonido de confirmación de activación
3. Cambia AWS Transcribe a modo de comando (mayor precisión)
4. Captura comando completo hasta detección de silencio
5. Envía transcripción final a Amazon Lex
6. Procesa respuesta de Lex y ejecuta acción correspondiente
7. Genera respuesta textual para el usuario
8. Convierte respuesta a audio con AWS Polly
9. Reproduce respuesta al usuario
10. Cierra sesión y retorna a escucha continua

**Flujos Alternativos:**
- 4a. Usuario no habla después de activación
  - 4a1. Espera 10 segundos máximo
  - 4a2. Reproduce mensaje "¿En qué puedo ayudarte?"
  - 4a3. Si sigue sin respuesta, cierra sesión
- 5a. Amazon Lex no reconoce intención
  - 5a1. Solicita al usuario reformular el comando
  - 5a2. Da ejemplos de comandos válidos

---

## CU-S05: Sincronizar Datos con DynamoDB

**Actor Principal:** Sistema  
**Precondiciones:** Datos locales modificados y conexión a AWS disponible  
**Postcondiciones:** Datos locales y en la nube están sincronizados  

**Flujo Principal:**
1. El sistema identifica cambios en SQLite local desde última sincronización
2. Prepara lote de cambios para envío a DynamoDB
3. Envía datos modificados usando AWS SDK
4. Recibe confirmación de escritura exitosa
5. Actualiza timestamp de última sincronización local
6. Marca registros como sincronizados en SQLite
7. Registra estadísticas de sincronización

**Flujos Alternativos:**
- 3a. Falla conexión con DynamoDB
  - 3a1. Programa reintento automático en 5 minutos
  - 3a2. Mantiene datos localmente hasta reconexión
- 4a. Error de escritura en DynamoDB
  - 4a1. Analiza tipo de error (permisos, límites, etc.)
  - 4a2. Reintenta con backoff exponencial

---

## CU-S06: Monitorear Estado de Dispositivos IoT

**Actor Principal:** Sistema  
**Precondiciones:** AWS IoT Core conectado y dispositivos registrados  
**Postcondiciones:** Estado actual de dispositivos actualizado  

**Flujo Principal:**
1. El sistema suscribe a topics MQTT de estado de dispositivos
2. Recibe mensajes de estado periódicos de cada dispositivo
3. Actualiza base de datos local con estados actuales
4. Detecta dispositivos que no reportan en tiempo esperado
5. Marca dispositivos no responsivos como "offline"
6. Registra cambios de estado con timestamp
7. Mantiene historial de disponibilidad de dispositivos

**Flujos Alternativos:**
- 4a. Dispositivo reporta error o falla
  - 4a1. Registra el error específico
  - 4a2. Marca dispositivo como "error"
  - 4a3. Notifica al usuario si es crítico
- 2a. Pérdida de conexión MQTT
  - 2a1. Intenta reconectar automáticamente
  - 2a2. Marca todos los dispositivos como "desconocido"

---

## CU-S07: Ejecutar Recordatorios Programados

**Actor Principal:** Sistema  
**Precondiciones:** Existen recordatorios programados en SQLite  
**Postcondiciones:** Recordatorios vencidos son ejecutados  

**Flujo Principal:**
1. El sistema verifica recordatorios cada 30 segundos
2. Identifica recordatorios cuyo tiempo ha llegado
3. Para cada recordatorio vencido:
   - Genera mensaje de alerta personalizado
   - Convierte mensaje a audio con AWS Polly
   - Reproduce alerta sonora seguida del mensaje
   - Marca recordatorio como "ejecutado"
4. Actualiza estado en SQLite local
5. Sincroniza cambios con DynamoDB

**Flujos Alternativos:**
- 3a. AWS Polly no disponible para síntesis
  - 3a1. Reproduce alerta sonora genérica
  - 3a2. Registra falla de síntesis
- 3b. Usuario no está presente (no hay respuesta)
  - 3b1. Repite alerta cada 2 minutos hasta 3 veces
  - 3b2. Después marca como "no atendido"

---

## CU-S08: Gestionar Logs y Diagnósticos

**Actor Principal:** Sistema  
**Precondiciones:** Sistema en operación  
**Postcondiciones:** Logs actualizados y diagnósticos disponibles  

**Flujo Principal:**
1. El sistema registra eventos en SQLite con niveles (INFO, WARN, ERROR)
2. Incluye timestamp, componente, mensaje y contexto
3. Rota logs automáticamente cuando superan 10MB
4. Mantiene últimos 7 días de logs localmente
5. Opcionalmente sincroniza logs críticos con DynamoDB
6. Genera reportes de diagnóstico semanales
7. Limpia logs antiguos automáticamente

**Flujos Alternativos:**
- 2a. SQLite no disponible para escritura
  - 2a1. Almacena logs temporalmente en memoria
  - 2a2. Intenta escribir cuando SQLite esté disponible
- 5a. Usuario ha deshabilitado sincronización de logs
  - 5a1. Mantiene logs solo localmente
  - 5a2. Respeta configuración de privacidad

---

## CU-S09: Manejar Modo Degradado

**Actor Principal:** Sistema  
**Precondiciones:** Uno o más servicios AWS no disponibles  
**Postcondiciones:** Sistema opera con funcionalidad limitada  

**Flujo Principal:**
1. El sistema detecta falla de servicio AWS crítico
2. Evalúa qué funcionalidades pueden continuar operando
3. Notifica al usuario sobre limitaciones actuales
4. Desactiva funciones que requieren servicios no disponibles
5. Mantiene funciones básicas usando recursos locales
6. Monitorea disponibilidad de servicios cada 2 minutos
7. Restaura funcionalidad completa cuando servicios vuelven

**Flujos Alternativos:**
- 5a. Todos los servicios AWS fallan
  - 5a1. Opera solo con funciones básicas locales
  - 5a2. Informa al usuario sobre modo offline
- 6a. Servicios parcialmente restaurados
  - 6a1. Habilita funciones según servicios disponibles
  - 6a2. Informa al usuario sobre funciones restauradas

---

## CU-S10: Realizar Backup y Recuperación

**Actor Principal:** Sistema  
**Precondiciones:** Datos críticos almacenados localmente  
**Postcondiciones:** Backup creado y datos protegidos  

**Flujo Principal:**
1. El sistema programa backup automático diario a las 3:00 AM
2. Crea copia de seguridad de SQLite local
3. Comprime archivos de configuración y logs críticos
4. Opcionalmente sube backup a S3 si está configurado
5. Verifica integridad del backup creado
6. Mantiene últimos 7 backups locales
7. Elimina backups más antiguos automáticamente

**Flujos Alternativos:**
- 4a. S3 no disponible para backup
  - 4a1. Mantiene backup solo localmente
  - 4a2. Registra advertencia sobre backup limitado
- 5a. Backup corrupto detectado
  - 5a1. Elimina backup defectuoso
  - 5a2. Reintenta proceso de backup
  - 5a3. Notifica al usuario si persiste el problema