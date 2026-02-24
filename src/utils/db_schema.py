"""
Esquema de base de datos SQLite para el asistente de voz
"""

# Schema SQL para la base de datos local
SCHEMA_SQL = """
-- Tabla de recordatorios
CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    scheduled_time DATETIME NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced_at DATETIME,
    user_id TEXT
);

-- Índice para búsquedas por tiempo programado
CREATE INDEX IF NOT EXISTS idx_reminders_scheduled_time 
ON reminders(scheduled_time);

-- Índice para búsquedas por estado
CREATE INDEX IF NOT EXISTS idx_reminders_status 
ON reminders(status);

-- Tabla de configuración
CREATE TABLE IF NOT EXISTS configuration (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de logs
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    component TEXT NOT NULL,
    message TEXT NOT NULL,
    session_id TEXT,
    error_details TEXT
);

-- Índice para búsquedas por timestamp
CREATE INDEX IF NOT EXISTS idx_logs_timestamp 
ON logs(timestamp);

-- Índice para búsquedas por componente
CREATE INDEX IF NOT EXISTS idx_logs_component 
ON logs(component);

-- Tabla de dispositivos IoT
CREATE TABLE IF NOT EXISTS iot_devices (
    device_id TEXT PRIMARY KEY,
    device_name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    last_status TEXT,
    last_seen DATETIME,
    is_online BOOLEAN DEFAULT FALSE
);

-- Tabla de sesiones (para historial)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME,
    status TEXT NOT NULL,
    context TEXT
);

-- Índice para búsquedas por fecha de creación
CREATE INDEX IF NOT EXISTS idx_sessions_created_at 
ON sessions(created_at);
"""


async def initialize_database(db_path: str) -> None:
    """
    Inicializa la base de datos SQLite con el esquema definido
    
    Args:
        db_path: Ruta al archivo de base de datos
    """
    import aiosqlite
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.executescript(SCHEMA_SQL)
            await db.commit()
            logger.info(f"Base de datos inicializada: {db_path}")
    except Exception as e:
        logger.error(f"Error al inicializar base de datos: {e}")
        raise
