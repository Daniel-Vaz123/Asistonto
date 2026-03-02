# ============================================================
# Data Models - Modelos de datos del sistema
# ============================================================
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class CommandResult:
    """Resultado del procesamiento de un comando de voz. (EN USO)"""
    success: bool
    response_text: str
    intent: Optional[str] = None
    entities: Optional[Dict] = None
    error: Optional[str] = None


# ============================================================
# MODELOS PARA FUTURA IMPLEMENTACIÓN
# Los siguientes modelos están definidos pero aún no se usan
# en el flujo principal. Se activarán al implementar:
#   - session_manager.py (Session)
#   - data_manager.py (Reminder)
#   - iot_controller.py (IoTDevice)
# ============================================================

@dataclass
class Reminder:
    """Recordatorio programado. (FUTURA IMPLEMENTACIÓN — data_manager.py)"""
    id: str
    content: str
    scheduled_time: datetime
    status: str = "pending"
    created_at: Optional[datetime] = None
    user_id: Optional[str] = None


@dataclass
class Session:
    """Sesión de conversación con contexto. (FUTURA IMPLEMENTACIÓN — session_manager.py)"""
    id: str
    created_at: datetime
    last_activity: datetime
    status: str
    context: Dict[str, Any]


@dataclass
class IoTDevice:
    """Dispositivo IoT controlable por voz. (FUTURA IMPLEMENTACIÓN — iot_controller.py)"""
    device_id: str
    device_name: str
    device_type: str
    last_status: Dict[str, Any]
    last_seen: datetime
    is_online: bool
