# Data Models - Modelos de datos del sistema
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class Reminder:
    id: str
    content: str
    scheduled_time: datetime
    status: str = "pending"
    created_at: Optional[datetime] = None
    user_id: Optional[str] = None

@dataclass
class Session:
    id: str
    created_at: datetime
    last_activity: datetime
    status: str
    context: Dict[str, Any]

@dataclass
class CommandResult:
    success: bool
    response_text: str
    intent: Optional[str] = None
    entities: Optional[Dict] = None
    used_web_search: bool = False
    spoken: bool = False
    error: Optional[str] = None

@dataclass
class IoTDevice:
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
    PROCESANDO = "Procesando"      # Procesando comando o llamando DeepSeek
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
