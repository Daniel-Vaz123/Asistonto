"""
App Launcher Action - Lanzamiento de aplicaciones del sistema

Implementa la acción de abrir aplicaciones del sistema operativo.

Requisitos implementados:
- 4.1: Detectar sistema operativo
- 4.2: Mapear nombres de apps a comandos
- 4.3: Ejecutar comando de lanzamiento
- 4.4: Validar app en whitelist
- 4.5: Manejar app no instalada
- 4.6: Confirmar lanzamiento
"""

import logging
import platform
import subprocess
from typing import Dict, Any

from src.actions.action import Action, ActionResult


logger = logging.getLogger(__name__)


class AppLauncherAction(Action):
    """
    Acción para lanzar aplicaciones del sistema operativo.
    
    Soporta Windows, macOS y Linux con mapeo de comandos por OS.
    """
    
    # Mapeo de nombres de apps a comandos por sistema operativo
    APP_COMMANDS = {
        'Windows': {
            'spotify': 'spotify',
            'notepad': 'notepad',
            'bloc de notas': 'notepad',
            'calculadora': 'calc',
            'calculator': 'calc',
            'chrome': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            'google chrome': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            'firefox': r'C:\Program Files\Mozilla Firefox\firefox.exe',
            'edge': 'msedge',
            'word': 'winword',
            'excel': 'excel',
            'powerpoint': 'powerpnt',
            'paint': 'mspaint',
            'explorador': 'explorer',
            'explorer': 'explorer',
        },
        'Darwin': {  # macOS
            'spotify': 'open -a Spotify',
            'notepad': 'open -a TextEdit',
            'calculadora': 'open -a Calculator',
            'calculator': 'open -a Calculator',
            'chrome': 'open -a "Google Chrome"',
            'google chrome': 'open -a "Google Chrome"',
            'firefox': 'open -a Firefox',
            'safari': 'open -a Safari',
        },
        'Linux': {
            'spotify': 'spotify',
            'notepad': 'gedit',
            'calculadora': 'gnome-calculator',
            'calculator': 'gnome-calculator',
            'chrome': 'google-chrome',
            'google chrome': 'google-chrome',
            'firefox': 'firefox',
        }
    }
    
    def __init__(self):
        """Inicializa la acción de lanzamiento de apps."""
        self.os_name = platform.system()
        logger.info(f"AppLauncherAction inicializado para {self.os_name}")
    
    def get_name(self) -> str:
        """Retorna el nombre de la acción."""
        return "App Launcher"
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Valida que el parámetro 'app_name' esté presente y en whitelist.
        
        Args:
            parameters: Debe contener 'app_name' con el nombre de la app
            
        Returns:
            True si es válido, False en caso contrario
            
        Requisito: 4.4 - Validar app en whitelist
        """
        if not parameters:
            logger.warning("Parámetros vacíos para AppLauncherAction")
            return False
        
        app_name = parameters.get('app_name', '').strip().lower()
        if not app_name:
            logger.warning("app_name vacío para AppLauncherAction")
            return False
        
        # Verificar que la app esté en el mapeo del OS actual
        os_apps = self.APP_COMMANDS.get(self.os_name, {})
        if app_name not in os_apps:
            logger.warning(f"App '{app_name}' no está en whitelist para {self.os_name}")
            return False
        
        return True
    
    def execute(self, parameters: Dict[str, Any]) -> ActionResult:
        """
        Ejecuta el lanzamiento de la aplicación.
        
        Args:
            parameters: Debe contener 'app_name' con el nombre de la app
            
        Returns:
            ActionResult con el resultado de la ejecución
            
        Requisito: 4.3 - Ejecutar comando de lanzamiento
        """
        # Validar parámetros
        if not self.validate_parameters(parameters):
            result = ActionResult(
                success=False,
                message="Parámetros inválidos",
                error=f"La aplicación no está configurada para {self.os_name}"
            )
            self._log_execution(parameters, result)
            return result
        
        app_name = parameters['app_name'].strip().lower()
        
        try:
            # Obtener comando para el OS actual
            os_apps = self.APP_COMMANDS.get(self.os_name, {})
            command = os_apps[app_name]
            
            logger.info(f"Lanzando aplicación: {app_name} (comando: {command})")
            
            # Ejecutar comando
            if self.os_name == 'Darwin':  # macOS usa shell para 'open -a'
                subprocess.Popen(command, shell=True)
            else:
                subprocess.Popen(command)
            
            result = ActionResult(
                success=True,
                message=f"Abriendo {app_name}",
                data={'app_name': app_name, 'command': command}
            )
            
            self._log_execution(parameters, result)
            return result
            
        except FileNotFoundError:
            error_msg = f"La aplicación '{app_name}' no está instalada en el sistema"
            logger.error(error_msg)
            
            result = ActionResult(
                success=False,
                message="Aplicación no encontrada",
                error=error_msg
            )
            
            self._log_execution(parameters, result)
            return result
            
        except Exception as e:
            error_msg = f"Error al lanzar aplicación: {str(e)}"
            logger.error(error_msg)
            
            result = ActionResult(
                success=False,
                message="Error al lanzar aplicación",
                error=error_msg
            )
            
            self._log_execution(parameters, result)
            return result


# TODO: Agregar detección automática de apps instaladas
# TODO: Implementar búsqueda de ejecutables en PATH
# TODO: Agregar soporte para parámetros de línea de comandos
# TODO: Implementar verificación de permisos antes de ejecutar
