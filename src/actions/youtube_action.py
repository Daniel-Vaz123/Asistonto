"""
YouTube Action - Reproducción de videos de YouTube

Implementa la acción de reproducir videos de YouTube usando pywhatkit.

Requisitos implementados:
- 3.2: Ejecutar búsqueda y reproducción en YouTube
- 3.3: Confirmar reproducción al usuario
- 3.4: Manejar errores de red o API
"""

import logging
from typing import Dict, Any

from src.actions.action import Action, ActionResult


logger = logging.getLogger(__name__)


class YouTubeAction(Action):
    """
    Acción para reproducir videos de YouTube.
    
    Usa pywhatkit.playonyt() para abrir YouTube en el navegador
    y reproducir el video buscado.
    """
    
    def __init__(self):
        """Inicializa la acción de YouTube."""
        logger.info("YouTubeAction inicializado")
    
    def get_name(self) -> str:
        """Retorna el nombre de la acción."""
        return "YouTube Player"
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Valida que el parámetro 'query' esté presente y no vacío.
        
        Args:
            parameters: Debe contener 'query' con el término de búsqueda
            
        Returns:
            True si es válido, False en caso contrario
        """
        if not parameters:
            logger.warning("Parámetros vacíos para YouTubeAction")
            return False
        
        query = parameters.get('query', '').strip()
        if not query:
            logger.warning("Query vacío para YouTubeAction")
            return False
        
        return True
    
    def execute(self, parameters: Dict[str, Any]) -> ActionResult:
        """
        Ejecuta la reproducción de video en YouTube.
        
        Args:
            parameters: Debe contener 'query' con el término de búsqueda
            
        Returns:
            ActionResult con el resultado de la ejecución
            
        Requisito: 3.2 - Ejecutar búsqueda y reproducción
        """
        # Validar parámetros
        if not self.validate_parameters(parameters):
            result = ActionResult(
                success=False,
                message="Parámetros inválidos",
                error="El parámetro 'query' es requerido y no puede estar vacío"
            )
            self._log_execution(parameters, result)
            return result
        
        query = parameters['query'].strip()
        
        try:
            # Importar pywhatkit aquí para evitar error si no está instalado
            import pywhatkit as kit
            
            logger.info(f"Reproduciendo en YouTube: '{query}'")
            
            # Reproducir video en YouTube
            # pywhatkit abre el navegador automáticamente
            kit.playonyt(query)
            
            result = ActionResult(
                success=True,
                message=f"Reproduciendo '{query}' en YouTube",
                data={'query': query}
            )
            
            self._log_execution(parameters, result)
            return result
            
        except ImportError:
            error_msg = "pywhatkit no está instalado. Ejecuta: pip install pywhatkit"
            logger.error(error_msg)
            
            result = ActionResult(
                success=False,
                message="Error de dependencia",
                error=error_msg
            )
            
            self._log_execution(parameters, result)
            return result
            
        except Exception as e:
            error_msg = f"Error al reproducir video: {str(e)}"
            logger.error(error_msg)
            
            result = ActionResult(
                success=False,
                message="Error al reproducir video",
                error=error_msg
            )
            
            self._log_execution(parameters, result)
            return result


# TODO: Agregar soporte para reproducir playlist
# TODO: Implementar búsqueda avanzada con filtros
# TODO: Agregar opción de reproducir en ventana específica
# TODO: Implementar cache de búsquedas recientes
