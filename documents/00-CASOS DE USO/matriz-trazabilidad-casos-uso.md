# Matriz de Trazabilidad - Casos de Uso vs Requisitos

## Resumen de Casos de Uso Creados

### Casos de Uso de Usuario (10)
- CU-U01: Activar Asistente con Wake Word
- CU-U02: Solicitar Información del Clima  
- CU-U03: Controlar Luces del Hogar
- CU-U04: Crear Recordatorio
- CU-U05: Solicitar Noticias
- CU-U06: Ajustar Temperatura
- CU-U07: Cancelar Recordatorio
- CU-U08: Consultar Hora Actual
- CU-U09: Listar Recordatorios Pendientes
- CU-U10: Solicitar Ayuda del Sistema

### Casos de Uso del Sistema (10)
- CU-S01: Inicializar Servicios AWS
- CU-S02: Calibrar Micrófono
- CU-S03: Procesar Stream de Audio Continuo
- CU-S04: Gestionar Sesión de Comando
- CU-S05: Sincronizar Datos con DynamoDB
- CU-S06: Monitorear Estado de Dispositivos IoT
- CU-S07: Ejecutar Recordatorios Programados
- CU-S08: Gestionar Logs y Diagnósticos
- CU-S09: Manejar Modo Degradado
- CU-S10: Realizar Backup y Recuperación

### Casos de Uso de Servicios en la Nube (10)
- CU-C01: AWS Transcribe - Procesar Stream de Audio
- CU-C02: AWS Polly - Sintetizar Respuesta de Voz
- CU-C03: Amazon Lex - Procesar Intención de Usuario
- CU-C04: AWS Lambda - Ejecutar Lógica de Negocio
- CU-C05: AWS IoT Core - Gestionar Dispositivos Domóticos
- CU-C06: DynamoDB - Sincronizar Datos de Usuario
- CU-C07: Alexa Skills Kit - Obtener Información Contextual
- CU-C08: AWS KMS - Cifrar Datos Sensibles
- CU-C09: CloudWatch - Monitorear Sistema
- CU-C10: S3 - Almacenar Backups y Archivos

## Matriz de Trazabilidad

| Requisito | Casos de Uso Relacionados | Cobertura |
|-----------|---------------------------|-----------|
| **Req 1: Detección Wake Word** | CU-U01, CU-S03, CU-C01 | ✅ Completa |
| **Req 2: Captura y Transcripción** | CU-S04, CU-C01, CU-C02 | ✅ Completa |
| **Req 3: Procesamiento Intenciones** | CU-S04, CU-C03, CU-C04 | ✅ Completa |
| **Req 4: Información Contextual** | CU-U02, CU-U05, CU-U08, CU-C07 | ✅ Completa |
| **Req 5: Control Domótico** | CU-U03, CU-U06, CU-S06, CU-C05 | ✅ Completa |
| **Req 6: Recordatorios y Alarmas** | CU-U04, CU-U07, CU-U09, CU-S07, CU-S05, CU-C06 | ✅ Completa |
| **Req 7: Síntesis de Voz** | CU-S04, CU-C02 | ✅ Completa |
| **Req 8: Manejo de Errores** | CU-S09, CU-S08, CU-C09 | ✅ Completa |
| **Req 9: Inicialización** | CU-S01, CU-S02 | ✅ Completa |
| **Req 10: Privacidad y Seguridad** | CU-C08, CU-S08, CU-S10, CU-C10 | ✅ Completa |
| **Req 11: Gestión de Sesiones** | CU-S04, CU-S08 | ✅ Completa |
| **Req 12: Detección de Idioma** | CU-C01, CU-C02, CU-C03 | ✅ Completa |

## Análisis de Cobertura

### ✅ Fortalezas de la Cobertura
- **100% de los requisitos** tienen casos de uso asociados
- **Flujos principales y alternativos** bien definidos para cada caso
- **Integración entre actores** claramente especificada
- **Manejo de errores** cubierto en múltiples niveles
- **Escalabilidad** considerada en casos de servicios en la nube

### 📋 Casos de Uso Adicionales Identificados
Los siguientes casos de uso fueron agregados para completar la funcionalidad del sistema:

1. **CU-U10: Solicitar Ayuda** - Mejora la usabilidad del sistema
2. **CU-S08: Gestionar Logs** - Esencial para mantenimiento y debugging
3. **CU-S09: Modo Degradado** - Garantiza operación continua
4. **CU-S10: Backup y Recuperación** - Protege datos del usuario
5. **CU-C09: CloudWatch** - Monitoreo proactivo del sistema
6. **CU-C10: S3 para Backups** - Almacenamiento seguro y durable

### 🎯 Alcance del Proyecto
Los 30 casos de uso definidos cubren:

**Funcionalidades Core (70%)**
- Detección de wake word y procesamiento de voz
- Control domótico básico (luces, temperatura)
- Información contextual (clima, noticias, hora)
- Gestión de recordatorios y alarmas

**Funcionalidades de Soporte (20%)**
- Inicialización y configuración
- Manejo de errores y recuperación
- Sincronización de datos
- Monitoreo y logs

**Funcionalidades Avanzadas (10%)**
- Modo degradado
- Backup automático
- Seguridad y cifrado
- Detección de idioma

## Recomendaciones para Implementación

### Fase 1 - MVP (Casos de Uso Críticos)
- CU-U01, CU-S03, CU-C01: Wake word y transcripción
- CU-S04, CU-C03, CU-C04: Procesamiento de comandos
- CU-U08, CU-C02: Respuestas básicas
- CU-S01, CU-S02: Inicialización

### Fase 2 - Funcionalidades Principales
- CU-U02, CU-U05, CU-C07: Información contextual
- CU-U04, CU-U07, CU-U09, CU-S07: Recordatorios
- CU-S05, CU-C06: Sincronización de datos

### Fase 3 - Control Domótico
- CU-U03, CU-U06, CU-S06, CU-C05: Control IoT
- CU-C09: Monitoreo avanzado

### Fase 4 - Robustez y Seguridad
- CU-S09: Modo degradado
- CU-C08: Cifrado
- CU-S10, CU-C10: Backup y recuperación