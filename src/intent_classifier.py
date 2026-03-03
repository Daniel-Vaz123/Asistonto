"""
Intent Classifier - Clasificación de comandos en intenciones

Este módulo implementa la clasificación de comandos de voz en dos categorías:
- CONVERSATIONAL: Preguntas, conversación general (procesadas por DeepSeek)
- ACTION: Acciones del sistema (YouTube, Apps, Web, Files)

Usa patrones regex para detectar intenciones de acción y extrae parámetros.

Requisitos implementados:
- 2.1: Clasificar comandos en conversational vs action
- 2.2: Detectar patrones de YouTube
- 2.3: Detectar patrones de aplicaciones
- 2.4: Detectar patrones de navegación web
- 3.1: Extraer query de búsqueda de YouTube
- 4.1: Extraer nombre de aplicación
- 5.1: Extraer nombre de sitio web
- 6.1: Extraer contenido de nota
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Tipo de intención del comando."""
    CONVERSATIONAL = "conversational"  # Pregunta o conversación general
    ACTION = "action"  # Acción del sistema


class ActionType(Enum):
    """Tipo de acción del sistema."""
    YOUTUBE = "youtube"  # Reproducir video de YouTube
    APP = "app"  # Abrir aplicación
    WEB = "web"  # Abrir sitio web
    FILE = "file"  # Crear/escribir nota


@dataclass
class Intent:
    """
    Representa una intención clasificada con sus parámetros.
    
    Attributes:
        intent_type: Tipo de intención (conversational o action)
        action_type: Tipo de acción (solo si intent_type es ACTION)
        parameters: Parámetros extraídos del comando
        confidence: Nivel de confianza de la clasificación (0.0-1.0)
    """
    intent_type: IntentType
    action_type: Optional[ActionType] = None
    parameters: Dict[str, Any] = None
    confidence: float = 1.0
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class IntentClassifier:
    """
    Clasificador de intenciones usando patrones regex.
    
    Analiza comandos de voz y los clasifica en intenciones conversacionales
    o de acción, extrayendo parámetros relevantes.
    """
    
    # Patrones para YouTube
    YOUTUBE_PATTERNS = [
        r'\b(pon|reproduce|abre|busca|muestra|quiero ver)\s+(en\s+)?youtube\s+(.+)',
        r'\b(pon|reproduce|abre|busca|muestra)\s+(.+)\s+en\s+youtube\b',
        r'\b(video|videos)\s+de\s+(.+)\s+en\s+youtube\b',
        r'\byoutube\s+(.+)',
    ]
    
    # Patrones para aplicaciones
    APP_PATTERNS = [
        r'\b(abre|inicia|ejecuta|lanza)\s+(la\s+)?(aplicación|app|programa)\s+(.+)',
        r'\b(abre|inicia|ejecuta|lanza)\s+(.+)',
    ]
    
    # Nombres de aplicaciones conocidas (whitelist)
    KNOWN_APPS = [
        'spotify', 'notepad', 'bloc de notas', 'calculadora', 'calculator',
        'chrome', 'google chrome', 'firefox', 'edge', 'word', 'excel',
        'powerpoint', 'paint', 'explorador', 'explorer'
    ]
    
    # Patrones para navegación web
    WEB_PATTERNS = [
        r'\b(abre|ve a|navega a|busca en)\s+(la\s+página|el\s+sitio|la\s+web)?\s*(.+)',
        r'\b(google|facebook|twitter|instagram|gmail|youtube)\b',
    ]
    
    # Sitios web conocidos
    KNOWN_WEBSITES = [
        'google', 'facebook', 'twitter', 'instagram', 'gmail', 'youtube',
        'github', 'stackoverflow', 'reddit', 'wikipedia', 'amazon'
    ]
    
    # Patrones para notas/archivos
    FILE_PATTERNS = [
        r'\b(toma\s+nota|anota|escribe|guarda|crea\s+nota)\s*:?\s*(.+)',
        r'\b(nota|apunta)\s+(.+)',
    ]
    
    def __init__(self):
        """Inicializa el clasificador compilando patrones regex."""
        # Compilar patrones para eficiencia
        self._youtube_patterns = [re.compile(p, re.IGNORECASE) for p in self.YOUTUBE_PATTERNS]
        self._app_patterns = [re.compile(p, re.IGNORECASE) for p in self.APP_PATTERNS]
        self._web_patterns = [re.compile(p, re.IGNORECASE) for p in self.WEB_PATTERNS]
        self._file_patterns = [re.compile(p, re.IGNORECASE) for p in self.FILE_PATTERNS]
        
        logger.info("IntentClassifier inicializado con patrones compilados")
    
    def classify(self, command: str) -> Intent:
        """
        Clasifica un comando en una intención.
        
        Orden de prioridad:
        1. YouTube (más específico)
        2. File/Notas (más específico)
        3. App (medio específico)
        4. Web (menos específico)
        5. Conversational (default)
        
        Args:
            command: Comando de voz a clasificar
            
        Returns:
            Intent con tipo, acción y parámetros
            
        Requisito: 2.1 - Clasificar comandos
        """
        if not command or not command.strip():
            return Intent(intent_type=IntentType.CONVERSATIONAL)
        
        command = command.strip()
        
        # 1. Intentar YouTube (prioridad alta)
        youtube_query = self._extract_youtube_query(command)
        if youtube_query:
            logger.info(f"Clasificado como YouTube: query='{youtube_query}'")
            return Intent(
                intent_type=IntentType.ACTION,
                action_type=ActionType.YOUTUBE,
                parameters={'query': youtube_query},
                confidence=0.95
            )
        
        # 2. Intentar File/Notas (prioridad alta)
        note_content = self._extract_note_content(command)
        if note_content:
            logger.info(f"Clasificado como File: content='{note_content[:50]}...'")
            return Intent(
                intent_type=IntentType.ACTION,
                action_type=ActionType.FILE,
                parameters={'content': note_content},
                confidence=0.95
            )
        
        # 3. Intentar App (prioridad media)
        app_name = self._extract_app_name(command)
        if app_name:
            logger.info(f"Clasificado como App: app='{app_name}'")
            return Intent(
                intent_type=IntentType.ACTION,
                action_type=ActionType.APP,
                parameters={'app_name': app_name},
                confidence=0.85
            )
        
        # 4. Intentar Web (prioridad baja)
        website = self._extract_website(command)
        if website:
            logger.info(f"Clasificado como Web: website='{website}'")
            return Intent(
                intent_type=IntentType.ACTION,
                action_type=ActionType.WEB,
                parameters={'website': website},
                confidence=0.80
            )
        
        # 5. Default: Conversational
        logger.info("Clasificado como Conversational (default)")
        return Intent(
            intent_type=IntentType.CONVERSATIONAL,
            confidence=0.70
        )
    
    def _extract_youtube_query(self, command: str) -> Optional[str]:
        """
        Extrae query de búsqueda de YouTube.
        
        Args:
            command: Comando de voz
            
        Returns:
            Query de búsqueda o None
            
        Requisito: 3.1 - Extraer query de YouTube
        """
        for pattern in self._youtube_patterns:
            match = pattern.search(command)
            if match:
                # Extraer el último grupo capturado (el query)
                groups = match.groups()
                query = groups[-1].strip()
                
                # Limpiar palabras comunes
                query = re.sub(r'\b(en|de|la|el|los|las)\b', '', query, flags=re.IGNORECASE)
                query = query.strip()
                
                if query and len(query) > 2:
                    return query
        
        return None
    
    def _extract_app_name(self, command: str) -> Optional[str]:
        """
        Extrae nombre de aplicación.
        
        Args:
            command: Comando de voz
            
        Returns:
            Nombre de aplicación o None
            
        Requisito: 4.1 - Extraer nombre de aplicación
        """
        command_lower = command.lower()
        
        # Primero verificar si menciona una app conocida
        for app in self.KNOWN_APPS:
            if app in command_lower:
                return app
        
        # Luego intentar extraer con patrones
        for pattern in self._app_patterns:
            match = pattern.search(command)
            if match:
                # Extraer el último grupo capturado
                groups = match.groups()
                app_name = groups[-1].strip().lower()
                
                # Verificar si está en la whitelist
                if app_name in self.KNOWN_APPS:
                    return app_name
        
        return None
    
    def _extract_website(self, command: str) -> Optional[str]:
        """
        Extrae nombre de sitio web.
        
        Args:
            command: Comando de voz
            
        Returns:
            Nombre de sitio web o None
            
        Requisito: 5.1 - Extraer nombre de sitio web
        """
        command_lower = command.lower()
        
        # Primero verificar si menciona un sitio conocido
        for website in self.KNOWN_WEBSITES:
            if website in command_lower:
                return website
        
        # Luego intentar extraer con patrones
        for pattern in self._web_patterns:
            match = pattern.search(command)
            if match:
                # Extraer el último grupo capturado
                groups = match.groups()
                website = groups[-1].strip().lower()
                
                # Limpiar palabras comunes
                website = re.sub(r'\b(punto|com|www|http|https)\b', '', website, flags=re.IGNORECASE)
                website = website.strip()
                
                if website and len(website) > 2:
                    return website
        
        return None
    
    def _extract_note_content(self, command: str) -> Optional[str]:
        """
        Extrae contenido de nota.
        
        Args:
            command: Comando de voz
            
        Returns:
            Contenido de nota o None
            
        Requisito: 6.1 - Extraer contenido de nota
        """
        for pattern in self._file_patterns:
            match = pattern.search(command)
            if match:
                # Extraer el último grupo capturado
                groups = match.groups()
                content = groups[-1].strip()
                
                if content and len(content) > 3:
                    return content
        
        return None


# TODO: Implementar machine learning para mejorar clasificación
# TODO: Agregar soporte para comandos compuestos
# TODO: Implementar contexto de conversación para desambiguación
# TODO: Agregar métricas de confianza más sofisticadas
