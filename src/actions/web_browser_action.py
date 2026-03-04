"""
Web Browser Action - Navegación a sitios web

Implementa la acción de abrir sitios web en el navegador predeterminado.

Requisitos implementados:
- 5.1: Mapear nombres a URLs
- 5.2: Abrir URL en navegador
- 5.3: Construir URL si no está en mapeo
- 5.4: Confirmar apertura
"""

import logging
import webbrowser
from typing import Dict, Any

from src.actions.action import Action, ActionResult


logger = logging.getLogger(__name__)


class WebBrowserAction(Action):
    """
    Acción para abrir sitios web en el navegador predeterminado.
    
    Usa webbrowser.open() para abrir URLs.
    """
    
    # Mapeo de nombres comunes a URLs
    URL_MAPPING = {
        'google': 'https://www.google.com',
        'facebook': 'https://www.facebook.com',
        'twitter': 'https://www.twitter.com',
        'instagram': 'https://www.instagram.com',
        'youtube': 'https://www.youtube.com',
        'gmail': 'https://mail.google.com',
        'github': 'https://www.github.com',
        'stackoverflow': 'https://stackoverflow.com',
        'reddit': 'https://www.reddit.com',
        'wikipedia': 'https://www.wikipedia.org',
        'amazon': 'https://www.amazon.com',
        'netflix': 'https://www.netflix.com',
        'spotify': 'https://open.spotify.com',
        'linkedin': 'https://www.linkedin.com',
        'whatsapp': 'https://web.whatsapp.com',
    }
    
    def __init__(self):
        """Inicializa la acción de navegación web."""
        logger.info("WebBrowserAction inicializado")
    
    def get_name(self) -> str:
        """Retorna el nombre de la acción."""
        return "Web Browser"
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Valida que el parámetro 'website' esté presente y no vacío.
        
        Args:
            parameters: Debe contener 'website' con el nombre del sitio
            
        Returns:
            True si es válido, False en caso contrario
        """
        if not parameters:
            logger.warning("Parámetros vacíos para WebBrowserAction")
            return False
        
        website = parameters.get('website', '').strip()
        if not website:
            logger.warning("website vacío para WebBrowserAction")
            return False
        
        return True
    
    def execute(self, parameters: Dict[str, Any]) -> ActionResult:
        """
        Ejecuta la apertura del sitio web.
        
        Args:
            parameters: Debe contener 'website' con el nombre del sitio
            
        Returns:
            ActionResult con el resultado de la ejecución
            
        Requisito: 5.2 - Abrir URL en navegador
        """
        # Validar parámetros
        if not self.validate_parameters(parameters):
            result = ActionResult(
                success=False,
                message="Parámetros inválidos",
                error="El parámetro 'website' es requerido y no puede estar vacío"
            )
            self._log_execution(parameters, result)
            return result
        
        website = parameters['website'].strip().lower()
        
        try:
            # Obtener URL del mapeo o construir una
            if website in self.URL_MAPPING:
                url = self.URL_MAPPING[website]
                logger.info(f"Usando URL mapeada: {website} -> {url}")
            else:
                # Construir URL si no está en el mapeo
                # Requisito: 5.3 - Construir URL si no está en mapeo
                if not website.startswith('http'):
                    url = f"https://www.{website}.com"
                else:
                    url = website
                logger.info(f"Construyendo URL: {website} -> {url}")
            
            logger.info(f"Abriendo sitio web: {url}")
            
            # Abrir URL en navegador predeterminado
            webbrowser.open(url)
            
            result = ActionResult(
                success=True,
                message=f"Abriendo {website}",
                data={'website': website, 'url': url}
            )
            
            self._log_execution(parameters, result)
            return result
            
        except Exception as e:
            error_msg = f"Error al abrir sitio web: {str(e)}"
            logger.error(error_msg)
            
            result = ActionResult(
                success=False,
                message="Error al abrir sitio web",
                error=error_msg
            )
            
            self._log_execution(parameters, result)
            return result


# TODO: Agregar soporte para abrir en navegador específico
# TODO: Implementar validación de URLs
# TODO: Agregar soporte para parámetros de búsqueda
# TODO: Implementar historial de sitios visitados
