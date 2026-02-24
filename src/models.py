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
    error: Optional[str] = None

@dataclass
class IoTDevice:
    device_id: str
    device_name: str
    device_type: str
    last_status: Dict[str, Any]
    last_seen: datetime
    is_online: bool
