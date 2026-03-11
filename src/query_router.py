"""
Enrutador de consultas para detectar necesidad de búsqueda web.

Este módulo analiza las consultas del usuario para determinar si requieren
información en tiempo real de internet.
"""

import re
from typing import List


class QueryRouter:
    """Enrutador de consultas para detectar necesidad de búsqueda web"""
    
    # Patrones que indican necesidad de búsqueda web
    WEB_SEARCH_PATTERNS = [
        r'\bbusca en internet\b',
        r'\bnoticias\b',
        r'\bclima (actual|de)\b',
        r'\bprecio de\b',
        r'\bcuánto cuesta\b',
        r'\b(hoy|ahora|actual)\b',
    ]
    
    def __init__(self):
        """Inicializa el router compilando los patrones de búsqueda"""
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.WEB_SEARCH_PATTERNS
        ]
    
    def requires_web_search(self, query: str) -> bool:
        """
        Determina si una consulta requiere búsqueda en internet.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            True si requiere búsqueda web, False en caso contrario
        """
        query_lower = query.lower().strip()
        
        # Verificar cada patrón
        for pattern in self.compiled_patterns:
            if pattern.search(query_lower):
                return True
        
        return False
