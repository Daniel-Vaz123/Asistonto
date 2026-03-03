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
    used_web_search: bool = False
    spoken: bool = False
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

# Phase 2: Web Search, Rich UI & Threading Models

from enum import Enum


class SystemState(Enum):
    """
    Estados posibles del sistema.
    
    El sistema siempre está en exactamente uno de estos estados.
    """
    ESCUCHANDO = "Escuchando"      # Esperando wake word
    PROCESANDO = "Pensando"        # Procesando comando o llamando DeepSeek (texto en UI)
    BUSCANDO = "Buscando en Web"   # Ejecutando búsqueda en internet
    HABLANDO = "Hablando"          # Sintetizando y reproduciendo respuesta


@dataclass
class SearchResult:
    """Resultado individual de búsqueda web"""
    title: str
    body: str
    url: Optional[str] = None
    
    def to_text(self) -> str:
        """Convierte resultado a texto plano"""
        return f"{self.title}. {self.body}"


@dataclass
class StateTransition:
    """Registro de transición de estado para debugging"""
    from_state: SystemState
    to_state: SystemState
    timestamp: datetime
    trigger: str  # Qué causó la transición
