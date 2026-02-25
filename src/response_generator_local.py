"""
Generador de respuestas con pyttsx3 (modo gratuito / local)

Texto a voz usando las voces del sistema (Windows), sin AWS Polly.
"""

import asyncio
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class LocalResponseGenerator:
    """
    Generador de respuestas con pyttsx3 (offline, gratuito).
    
    Compatible con la interfaz de ResponseGenerator:
    - speak(text, block=True) -> bool
    - get_cache_stats() -> dict
    """

    def __init__(self, rate: int = 150, volume: float = 1.0):
        """
        Args:
            rate: Velocidad del habla (palabras por minuto aproximado)
            volume: Volumen 0.0 a 1.0
        """
        self.rate = rate
        self.volume = volume
        self._engine = None
        self._total_requests = 0
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("LocalResponseGenerator (pyttsx3) inicializado")

    def _get_engine(self):
        """Inicializa el motor pyttsx3 una sola vez."""
        if self._engine is None:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)
            # Preferir voz en español si está disponible
            voices = self._engine.getProperty("voices")
            for v in voices:
                if "es" in (v.id or "").lower() or "spanish" in (v.name or "").lower():
                    self._engine.setProperty("voice", v.id)
                    logger.info(f"Voz en español seleccionada: {v.name}")
                    break
        return self._engine

    async def speak(self, text: str, block: bool = True) -> bool:
        """
        Sintetiza y reproduce el texto con la voz del sistema.
        """
        if not text or not text.strip():
            return False
        self._total_requests += 1
        self._cache_misses += 1  # pyttsx3 no cachea por texto

        try:
            engine = self._get_engine()
            # pyttsx3 es síncrono; ejecutamos en thread para no bloquear el event loop
            def _say():
                engine.say(text)
                engine.runAndWait()

            if block:
                await asyncio.to_thread(_say)
            else:
                asyncio.create_task(asyncio.to_thread(_say))
            logger.debug(f"Texto hablado con pyttsx3: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Error en pyttsx3: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, int]:
        """Estadísticas compatibles con ResponseGenerator (cache no aplica en local)."""
        return {
            "total_requests": self._total_requests,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": 0.0,
        }
