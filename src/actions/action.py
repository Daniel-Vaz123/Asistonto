"""
Action Base - Interfaz base para acciones del sistema

Define la interfaz abstracta que todas las acciones deben implementar,
siguiendo el patrón Command para extensibilidad.

Requisitos implementados:
- 8.1: Interfaz base Action con execute()
- 8.2: ActionResult para resultados estructurados
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging


logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """
    Resultado de la ejecución de una acción.
    
    Attributes:
        success: Si la acción se ejecutó exitosamente
        message: Mensaje descriptivo del resultado
        error: Mensaje de error (solo si success=False)
        data: Datos adicionales opcionales
    """
    success: bool
    message: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class Action(ABC):
    """
    Interfaz base abstracta para todas las acciones del sistema.
    
    Todas las acciones concretas deben heredar de esta clase e implementar
    los métodos abstractos.
    
    Patrón: Command Pattern para extensibilidad y desacoplamiento
    """
    
    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> ActionResult:
        """
        Ejecuta la acción con los parámetros proporcionados.
        
        Args:
            parameters: Diccionario con parámetros de la acción
            
        Returns:
            ActionResult con el resultado de la ejecución
            
        Raises:
            Exception: Si ocurre un error durante la ejecución
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Obtiene el nombre descriptivo de la acción.
        
        Returns:
            Nombre de la acción (ej: "YouTube Player", "App Launcher")
        """
        pass
    
    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Valida que los parámetros sean correctos antes de ejecutar.
        
        Args:
            parameters: Diccionario con parámetros a validar
            
        Returns:
            True si los parámetros son válidos, False en caso contrario
        """
        pass
    
    def _log_execution(self, parameters: Dict[str, Any], result: ActionResult) -> None:
        """
        Registra la ejecución de la acción en los logs.
        
        Args:
            parameters: Parámetros usados
            result: Resultado de la ejecución
        """
        if result.success:
            logger.info(
                f"{self.get_name()} ejecutado exitosamente: {result.message} "
                f"(params: {parameters})"
            )
        else:
            logger.error(
                f"{self.get_name()} falló: {result.error} "
                f"(params: {parameters})"
            )


# TODO: Agregar soporte para acciones asíncronas
# TODO: Implementar sistema de permisos por acción
# TODO: Agregar métricas de tiempo de ejecución
# TODO: Implementar retry logic para acciones fallidas
