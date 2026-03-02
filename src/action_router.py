"""
Action Router - Enrutamiento y ejecución de acciones del sistema

Implementa el sistema de enrutamiento de acciones usando el patrón Strategy/Command.
Registra acciones disponibles y las ejecuta según el intent clasificado.

Requisitos implementados:
- 2.6: Enrutar intent a acción correspondiente
- 8.1: ActionRegistry para gestión de acciones
- 8.2: Registro y obtención de acciones
- 8.3: Validación y ejecución con manejo de excepciones
- 9.1: Manejo robusto de errores
- 9.4: Logging de ejecución
"""

import logging
from typing import Dict, Optional

from src.intent_classifier import Intent, IntentType, ActionType
from src.actions.action import Action, ActionResult
from src.actions.youtube_action import YouTubeAction
from src.actions.app_launcher_action import AppLauncherAction
from src.actions.web_browser_action import WebBrowserAction
from src.actions.file_writer_action import FileWriterAction


logger = logging.getLogger(__name__)


class ActionRegistry:
    """
    Registro de acciones disponibles.
    
    Permite registrar, obtener y listar acciones de forma dinámica.
    """
    
    def __init__(self):
        """Inicializa el registro vacío."""
        self._actions: Dict[ActionType, Action] = {}
        logger.info("ActionRegistry inicializado")
    
    def register(self, action_type: ActionType, action: Action) -> None:
        """
        Registra una acción en el registry.
        
        Args:
            action_type: Tipo de acción
            action: Instancia de la acción
            
        Requisito: 8.2 - Registro de acciones
        """
        self._actions[action_type] = action
        logger.info(f"Acción registrada: {action_type.value} -> {action.get_name()}")
    
    def get_action(self, action_type: ActionType) -> Optional[Action]:
        """
        Obtiene una acción del registry.
        
        Args:
            action_type: Tipo de acción a obtener
            
        Returns:
            Instancia de la acción o None si no está registrada
            
        Requisito: 8.2 - Obtención de acciones
        """
        return self._actions.get(action_type)
    
    def list_actions(self) -> Dict[ActionType, str]:
        """
        Lista todas las acciones registradas.
        
        Returns:
            Diccionario con action_type -> nombre de acción
        """
        return {
            action_type: action.get_name()
            for action_type, action in self._actions.items()
        }


class ActionRouter:
    """
    Enrutador de acciones usando patrón Strategy.
    
    Recibe intents clasificados y ejecuta la acción correspondiente.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Inicializa el router con acciones por defecto.
        
        Args:
            data_dir: Directorio para FileWriterAction
        """
        self.registry = ActionRegistry()
        self.data_dir = data_dir
        
        # Registrar acciones por defecto
        self._register_default_actions()
        
        logger.info("ActionRouter inicializado con acciones por defecto")
    
    def _register_default_actions(self) -> None:
        """
        Registra las acciones estándar del sistema.
        
        Requisito: 8.1 - Registro de acciones estándar
        """
        self.registry.register(ActionType.YOUTUBE, YouTubeAction())
        self.registry.register(ActionType.APP, AppLauncherAction())
        self.registry.register(ActionType.WEB, WebBrowserAction())
        self.registry.register(ActionType.FILE, FileWriterAction(data_dir=self.data_dir))
        
        logger.info("Acciones por defecto registradas")
    
    def route_and_execute(self, intent: Intent) -> ActionResult:
        """
        Enruta y ejecuta la acción correspondiente al intent.
        
        Args:
            intent: Intent clasificado con tipo y parámetros
            
        Returns:
            ActionResult con el resultado de la ejecución
            
        Requisito: 2.6 - Enrutar intent a acción
        Requisito: 8.3 - Validación y ejecución
        Requisito: 9.1 - Manejo de errores
        Requisito: 9.4 - Logging
        """
        # Validar que sea un intent de acción
        if intent.intent_type != IntentType.ACTION:
            error_msg = f"Intent type inválido: {intent.intent_type.value} (esperado: ACTION)"
            logger.error(error_msg)
            return ActionResult(
                success=False,
                message="Error de enrutamiento",
                error=error_msg
            )
        
        # Validar que tenga action_type
        if not intent.action_type:
            error_msg = "Intent de acción sin action_type"
            logger.error(error_msg)
            return ActionResult(
                success=False,
                message="Error de enrutamiento",
                error=error_msg
            )
        
        # Obtener acción del registry
        action = self.registry.get_action(intent.action_type)
        
        if not action:
            error_msg = f"Acción no registrada: {intent.action_type.value}"
            logger.error(error_msg)
            return ActionResult(
                success=False,
                message="Acción no disponible",
                error=error_msg
            )
        
        try:
            # Validar parámetros
            if not action.validate_parameters(intent.parameters):
                error_msg = f"Parámetros inválidos para {action.get_name()}"
                logger.error(error_msg)
                return ActionResult(
                    success=False,
                    message="Parámetros inválidos",
                    error=error_msg
                )
            
            # Ejecutar acción
            logger.info(
                f"Ejecutando acción: {action.get_name()} "
                f"(params: {intent.parameters})"
            )
            
            result = action.execute(intent.parameters)
            
            # Log resultado
            if result.success:
                logger.info(f"Acción exitosa: {result.message}")
            else:
                logger.error(f"Acción fallida: {result.error}")
            
            return result
            
        except Exception as e:
            error_msg = f"Excepción durante ejecución de {action.get_name()}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return ActionResult(
                success=False,
                message="Error inesperado",
                error=error_msg
            )
    
    def register_action(self, action_type: ActionType, action: Action) -> None:
        """
        Registra una acción personalizada.
        
        Permite extensibilidad del sistema con nuevas acciones.
        
        Args:
            action_type: Tipo de acción
            action: Instancia de la acción
            
        Requisito: 8.1 - Extensibilidad
        """
        self.registry.register(action_type, action)
        logger.info(f"Acción personalizada registrada: {action_type.value}")
    
    def list_available_actions(self) -> Dict[ActionType, str]:
        """
        Lista todas las acciones disponibles.
        
        Returns:
            Diccionario con action_type -> nombre de acción
        """
        return self.registry.list_actions()


# TODO: Agregar soporte para acciones asíncronas
# TODO: Implementar cola de acciones pendientes
# TODO: Agregar métricas de uso por acción
# TODO: Implementar sistema de permisos por acción
