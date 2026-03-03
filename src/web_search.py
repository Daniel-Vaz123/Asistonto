"""
Módulo de búsqueda en internet usando DuckDuckGo.

Este módulo proporciona capacidades de búsqueda web para el asistente de voz,
permitiendo responder preguntas sobre información en tiempo real.
"""

import logging
import warnings
from typing import Optional

logger = logging.getLogger(__name__)


class WebSearchModule:
    """Módulo de búsqueda en internet usando DuckDuckGo"""
    
    def __init__(self, max_results: int = 3, timeout: int = 30):
        """
        Inicializa el módulo de búsqueda web.
        
        Args:
            max_results: Número máximo de resultados a recuperar (default: 3)
            timeout: Timeout en segundos para búsquedas (default: 30)
        
        Raises:
            ImportError: Si duckduckgo-search no está instalado
        """
        self.max_results = max_results
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Verificar que duckduckgo-search está instalado (silenciar aviso de renombre a ddgs)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                from duckduckgo_search import DDGS
            self.ddgs = DDGS()
        except ImportError:
            raise ImportError(
                "duckduckgo-search no está instalado. "
                "Instala con: pip install duckduckgo-search>=4.0.0"
            )
    
    def search(self, query: str) -> str:
        """
        Busca en internet y retorna texto concatenado.
        
        Args:
            query: Consulta de búsqueda
            
        Returns:
            Texto concatenado de los resultados o string vacío si falla
        """
        try:
            # Sanitizar query antes de buscar
            sanitized_query = self._sanitize_query(query)
            self.logger.info(f"Buscando en web: '{sanitized_query}'")
            
            # Ejecutar búsqueda
            results = self.ddgs.text(sanitized_query, max_results=self.max_results)
            
            # Extraer texto de cada resultado
            extracted_texts = []
            for result in results:
                text = self._extract_text(result)
                if text:
                    extracted_texts.append(text)
            
            # Concatenar y sanitizar resultados
            combined_text = " ".join(extracted_texts)
            sanitized_results = self._sanitize_search_results(combined_text)
            
            if sanitized_results:
                self.logger.info(f"Web search exitoso: {len(sanitized_results)} caracteres")
            else:
                self.logger.warning("Web search no retornó resultados")
            
            return sanitized_results
            
        except TimeoutError:
            self.logger.error("Timeout en búsqueda web")
            return ""
        except ConnectionError:
            self.logger.error("Error de conexión en búsqueda web")
            return ""
        except Exception as e:
            self.logger.error(f"Error en búsqueda web: {e}", exc_info=True)
            return ""
    
    def _extract_text(self, result: dict) -> str:
        """
        Extrae texto de un resultado individual.
        
        Args:
            result: Diccionario con resultado de búsqueda
            
        Returns:
            Texto extraído o string vacío si falla
        """
        try:
            title = result.get('title', '')
            body = result.get('body', '')
            return f"{title}. {body}"
        except Exception:
            return ""
    
    def _sanitize_query(self, query: str) -> str:
        """
        Sanitiza query antes de búsqueda.
        
        Args:
            query: Query original
            
        Returns:
            Query sanitizada
        """
        import re
        # Remover caracteres especiales peligrosos
        query = re.sub(r'[<>"\'%;()&+]', '', query)
        # Limitar longitud
        query = query[:200]
        return query
    
    def _sanitize_search_results(self, text: str) -> str:
        """
        Sanitiza resultados antes de retornar.
        
        Args:
            text: Texto de resultados
            
        Returns:
            Texto sanitizado
        """
        import re
        # Remover HTML tags si los hay
        text = re.sub(r'<[^>]+>', '', text)
        # Limitar longitud total
        text = text[:2000]
        return text
