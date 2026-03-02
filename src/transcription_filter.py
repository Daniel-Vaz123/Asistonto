"""
Transcription Filter - Filtrado y validación de transcripciones

Este módulo implementa un filtro para validar transcripciones de Vosk
antes de enviarlas al procesador de comandos.

Características:
- Remoción de wake words
- Validación de longitud mínima (palabras y caracteres)
- Logging de transcripciones rechazadas
- Prevención de envío de ruido a DeepSeek
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


class TranscriptionFilter:
    """
    Filtra y valida transcripciones de voz.
    
    Remueve wake words y valida que las transcripciones cumplan
    criterios mínimos de calidad antes de procesarlas.
    
    Attributes:
        wake_words: Lista de wake words a remover
        min_words: Mínimo de palabras requeridas
        min_chars: Mínimo de caracteres requeridos
    """
    
    def __init__(
        self,
        wake_words: List[str],
        min_words: int = 2,
        min_chars: int = 4
    ):
        """
        Inicializa el filtro de transcripciones.
        
        Args:
            wake_words: Lista de wake words a remover (ej: ["asistente", "kiro"])
            min_words: Mínimo de palabras requeridas (default: 2)
            min_chars: Mínimo de caracteres requeridos (default: 4)
        """
        self.wake_words = [w.lower() for w in wake_words]
        self.min_words = min_words
        self.min_chars = min_chars
        
        logger.info(
            f"TranscriptionFilter inicializado: "
            f"wake_words={wake_words}, min_words={min_words}, min_chars={min_chars}"
        )
    
    def filter(self, transcription: Optional[str]) -> Optional[str]:
        """
        Filtra y valida una transcripción.
        
        Proceso:
        1. Verificar que no sea None o vacío
        2. Remover wake words
        3. Limpiar espacios extras
        4. Validar criterios mínimos
        5. Loggear si se rechaza
        
        Args:
            transcription: Texto transcrito por Vosk
            
        Returns:
            Texto limpio si es válido, None si se rechaza
        """
        # Validar input
        if not transcription or not transcription.strip():
            logger.debug("Empty or None transcription received")
            return None
        
        # Remover wake words
        cleaned_text = self._remove_wake_words(transcription)
        
        # Limpiar espacios extras
        cleaned_text = " ".join(cleaned_text.split())
        
        # Validar criterios
        if not self._validate(cleaned_text):
            word_count = self._count_words(cleaned_text)
            char_count = len(cleaned_text)
            
            logger.debug(
                f"Transcription rejected: '{transcription}' -> '{cleaned_text}' "
                f"(words={word_count}, chars={char_count})"
            )
            return None
        
        logger.debug(f"Transcription accepted: '{cleaned_text}'")
        return cleaned_text
    
    def _remove_wake_words(self, text: str) -> str:
        """
        Remueve wake words del texto (case-insensitive).
        
        Args:
            text: Texto original
            
        Returns:
            Texto sin wake words
        """
        result = text
        for wake_word in self.wake_words:
            # Usar regex con word boundaries para evitar remover partes de palabras
            pattern = r'\b' + re.escape(wake_word) + r'\b'
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        return result
    
    def _count_words(self, text: str) -> int:
        """
        Cuenta palabras en el texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Número de palabras
        """
        return len(text.split())
    
    def _validate(self, text: str) -> bool:
        """
        Valida que el texto cumpla criterios mínimos.
        
        Args:
            text: Texto limpio (sin wake words)
            
        Returns:
            True si es válido, False si se rechaza
        """
        word_count = self._count_words(text)
        char_count = len(text.strip())
        
        # Debe cumplir AMBOS criterios
        return word_count >= self.min_words and char_count >= self.min_chars
