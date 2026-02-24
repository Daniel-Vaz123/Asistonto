"""
Utilidad para cargar y validar configuración del sistema
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Cargador y validador de configuración"""
    
    REQUIRED_AWS_KEYS = [
        'aws.region',
        'aws.transcribe.language_code',
        'aws.polly.voice_id',
        'aws.lex.bot_name',
    ]
    
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
    
    def load(self) -> Dict[str, Any]:
        """Carga la configuración desde el archivo JSON"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        logger.info(f"Configuración cargada desde {self.config_path}")
        return self.config
    
    def validate(self) -> bool:
        """Valida que la configuración tenga todos los campos requeridos"""
        for key_path in self.REQUIRED_AWS_KEYS:
            if not self._get_nested_value(key_path):
                logger.error(f"Clave de configuración faltante: {key_path}")
                return False
        
        logger.info("Configuración validada exitosamente")
        return True
    
    def _get_nested_value(self, key_path: str) -> Any:
        """Obtiene un valor anidado usando notación de punto"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Obtiene un valor de configuración con valor por defecto"""
        value = self._get_nested_value(key_path)
        return value if value is not None else default
