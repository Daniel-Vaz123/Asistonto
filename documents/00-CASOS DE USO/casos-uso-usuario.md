# Casos de Uso - Actor: Usuario

## CU-U01: Activar Asistente con Wake Word

**Actor Principal:** Usuario  
**Precondiciones:** El sistema está ejecutándose y escuchando continuamente  
**Postcondiciones:** El asistente está activo y listo para recibir comandos  

**Flujo Principal:**
1. El usuario dice la palabra de activación ("Alexa", "Asistente", etc.)
2. El sistema detecta el wake word mediante AWS Transcribe
3. El sistema reproduce un sonido de confirmación
4. El sistema inicia una sesión de comando activa
5. El sistema espera el comando del usuario

**Flujos Alternativos:**
- 2a. El wake word no es detectado correctamente
  - 2a1. El sistema continúa escuchando sin activarse
- 3a. Falla la reproducción del sonido de confirmación
  - 3a1. El sistema continúa con la sesión pero registra el error

---

## CU-U02: Solicitar Información del Clima

**Actor Principal:** Usuario  
**Precondiciones:** El asistente está activo después del wake word  
**Postcondiciones:** El usuario recibe información meteorológica actualizada  

**Flujo Principal:**
1. El usuario dice "¿Cómo está el clima hoy?"
2. El sistema transcribe el comando usando AWS Transcribe
3. Amazon Lex identifica la intención "ConsultarClima"
4. AWS Lambda invoca Alexa Skills Kit para obtener datos meteorológicos
5. El sistema sintetiza la respuesta usando AWS Polly
6. El sistema reproduce la información del clima
7. La sesión se cierra automáticamente

**Flujos Alternativos:**
- 4a. El servicio de clima no está disponible
  - 4a1. El sistema informa al usuario sobre la indisponibilidad
  - 4a2. Sugiere intentar más tarde
- 2a. La transcripción es incorrecta
  - 2a1. Amazon Lex no reconoce la intención
  - 2a2. El sistema solicita aclaración al usuario

---

## CU-U03: Controlar Luces del Hogar

**Actor Principal:** Usuario  
**Precondiciones:** El asistente está activo y hay dispositivos IoT configurados  
**Postcondiciones:** Las luces cambian de estado según el comando  

**Flujo Principal:**
1. El usuario dice "Enciende las luces de la sala"
2. El sistema transcribe el comando
3. Amazon Lex identifica intención "ControlDispositivo" con entidad "luces_sala"
4. AWS Lambda consulta el estado actual en AWS IoT Core
5. AWS Lambda envía comando MQTT para encender las luces
6. El dispositivo IoT confirma la ejecución
7. El sistema confirma verbalmente la acción realizada

**Flujos Alternativos:**
- 6a. El dispositivo no responde en 5 segundos
  - 6a1. El sistema informa al usuario sobre el fallo
  - 6a2. Sugiere verificar la conectividad del dispositivo
- 3a. La entidad no es reconocida
  - 3a1. El sistema pregunta cuál dispositivo específico controlar

---

## CU-U04: Crear Recordatorio

**Actor Principal:** Usuario  
**Precondiciones:** El asistente está activo  
**Postcondiciones:** El recordatorio queda programado en el sistema  

**Flujo Principal:**
1. El usuario dice "Recuérdame llamar al doctor mañana a las 3 PM"
2. El sistema transcribe el comando
3. Amazon Lex extrae intención "CrearRecordatorio" con entidades de tiempo y contenido
4. AWS Lambda procesa la información temporal
5. El recordatorio se almacena en SQLite local
6. Se sincroniza con DynamoDB en la nube
7. El sistema confirma la creación del recordatorio

**Flujos Alternativos:**
- 3a. La fecha/hora no es clara
  - 3a1. El sistema solicita aclaración sobre el momento
- 6a. Falla la sincronización con DynamoDB
  - 6a1. El recordatorio se mantiene solo localmente
  - 6a2. Se reintenta la sincronización más tarde

---

## CU-U05: Solicitar Noticias

**Actor Principal:** Usuario  
**Precondiciones:** El asistente está activo y hay conexión a internet  
**Postcondiciones:** El usuario recibe un resumen de noticias actuales  

**Flujo Principal:**
1. El usuario dice "¿Cuáles son las noticias de hoy?"
2. El sistema transcribe el comando
3. Amazon Lex identifica intención "ConsultarNoticias"
4. AWS Lambda invoca Alexa Skills Kit para obtener titulares
5. El sistema selecciona los 3 titulares más relevantes
6. AWS Polly sintetiza el resumen de noticias
7. El sistema reproduce las noticias

**Flujos Alternativos:**
- 4a. El servicio de noticias no está disponible
  - 4a1. El sistema informa sobre la indisponibilidad
- 5a. No hay noticias disponibles
  - 5a1. El sistema informa que no hay actualizaciones

---

## CU-U06: Ajustar Temperatura

**Actor Principal:** Usuario  
**Precondiciones:** El asistente está activo y hay termostato conectado  
**Postcondiciones:** La temperatura del hogar se ajusta según el comando  

**Flujo Principal:**
1. El usuario dice "Sube la temperatura a 22 grados"
2. El sistema transcribe el comando
3. Amazon Lex identifica intención "AjustarTemperatura" con valor "22"
4. AWS Lambda valida que el valor esté en rango permitido (16-30°C)
5. Se envía comando MQTT al termostato vía AWS IoT Core
6. El termostato confirma el cambio
7. El sistema confirma verbalmente el ajuste

**Flujos Alternativos:**
- 4a. La temperatura está fuera del rango
  - 4a1. El sistema informa el rango válido
  - 4a2. Solicita una temperatura dentro del rango
- 6a. El termostato no responde
  - 6a1. El sistema informa sobre el problema de conectividad

---

## CU-U07: Cancelar Recordatorio

**Actor Principal:** Usuario  
**Precondiciones:** El asistente está activo y existen recordatorios  
**Postcondiciones:** El recordatorio especificado es eliminado  

**Flujo Principal:**
1. El usuario dice "Cancela mi recordatorio de llamar al doctor"
2. El sistema transcribe el comando
3. Amazon Lex identifica intención "CancelarRecordatorio"
4. AWS Lambda busca recordatorios que coincidan con la descripción
5. Si encuentra una coincidencia única, la elimina de SQLite
6. Se sincroniza la eliminación con DynamoDB
7. El sistema confirma la cancelación

**Flujos Alternativos:**
- 4a. Se encuentran múltiples coincidencias
  - 4a1. El sistema lista las opciones disponibles
  - 4a2. Solicita al usuario especificar cuál cancelar
- 4b. No se encuentra ningún recordatorio
  - 4b1. El sistema informa que no hay recordatorios que coincidan

---

## CU-U08: Consultar Hora Actual

**Actor Principal:** Usuario  
**Precondiciones:** El asistente está activo  
**Postcondiciones:** El usuario recibe la hora actual  

**Flujo Principal:**
1. El usuario dice "¿Qué hora es?"
2. El sistema transcribe el comando
3. Amazon Lex identifica intención "ConsultarHora"
4. AWS Lambda obtiene la hora local del sistema
5. AWS Polly sintetiza la respuesta con la hora
6. El sistema reproduce la hora actual

**Flujos Alternativos:**
- 4a. Error al obtener la hora del sistema
  - 4a1. El sistema informa sobre el error técnico

---

## CU-U09: Listar Recordatorios Pendientes

**Actor Principal:** Usuario  
**Precondiciones:** El asistente está activo  
**Postcondiciones:** El usuario escucha todos sus recordatorios pendientes  

**Flujo Principal:**
1. El usuario dice "¿Cuáles son mis recordatorios?"
2. El sistema transcribe el comando
3. Amazon Lex identifica intención "ListarRecordatorios"
4. AWS Lambda consulta SQLite local para recordatorios pendientes
5. Se ordenan los recordatorios por fecha/hora
6. AWS Polly sintetiza la lista completa
7. El sistema reproduce todos los recordatorios

**Flujos Alternativos:**
- 4a. No hay recordatorios pendientes
  - 4a1. El sistema informa que no hay recordatorios programados
- 6a. Hay más de 10 recordatorios
  - 6a1. El sistema pregunta si quiere escuchar todos o solo los próximos

---

## CU-U10: Solicitar Ayuda del Sistema

**Actor Principal:** Usuario  
**Precondiciones:** El asistente está activo  
**Postcondiciones:** El usuario recibe información sobre comandos disponibles  

**Flujo Principal:**
1. El usuario dice "¿Qué puedes hacer?" o "Ayuda"
2. El sistema transcribe el comando
3. Amazon Lex identifica intención "SolicitudAyuda"
4. AWS Lambda prepara lista de funcionalidades disponibles
5. AWS Polly sintetiza la respuesta con ejemplos de comandos
6. El sistema reproduce la guía de ayuda

**Flujos Alternativos:**
- 5a. El usuario solicita ayuda específica sobre una función
  - 5a1. El sistema proporciona ayuda detallada sobre esa función