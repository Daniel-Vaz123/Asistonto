"""
OfflineCommandHandler — Manejador de comandos locales para Asistonto Fase 1.

Procesa texto mediante patrones regex compilados y retorna una respuesta
string sin necesidad de internet ni APIs externas.

Comandos soportados:
  - Hora actual   : "qué hora es", "dime la hora", "hora actual"
  - Chiste        : "cuéntame un chiste", "dime un chiste"
  - Abrir app     : "abre la calculadora", "abre el bloc de notas", etc.

Retorna None si el texto no coincide con ningún patrón conocido.
Nunca lanza excepciones — todos los errores se convierten en strings descriptivos.
"""

import logging
import random
import re
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OfflineCommandHandler:
    """
    Manejador de comandos offline.

    Uso:
        handler = OfflineCommandHandler()
        response = handler.handle("qué hora es")
        # → "Son las 14:32:05."
        response = handler.handle("cuéntame un chiste")
        # → "¿Por qué los pájaros vuelan hacia el sur?..."
        response = handler.handle("abre la calculadora")
        # → "Abriendo la calculadora..."
        response = handler.handle("texto desconocido")
        # → None
    """

    # ------------------------------------------------------------------
    # Patrones compilados
    # ------------------------------------------------------------------

    _HORA_PATTERN = re.compile(
        r'\b(qu[eé]\s+hora\s+(es|son)|dime\s+la\s+hora|hora\s+actual|'
        r'qu[eé]\s+horas?\s+son|a\s+qu[eé]\s+hora)\b',
        re.IGNORECASE,
    )

    _CHISTE_PATTERN = re.compile(
        r'\b(cu[eé]ntame|dime|s[eé]|cuenta)\s+(un\s+)?chiste\b',
        re.IGNORECASE,
    )

    _APP_PATTERN = re.compile(
        r'\babre\s+(la\s+|el\s+|los\s+|las\s+)?'
        r'(calculadora|bloc\s+de\s+notas?|notepad|explorador\s+de\s+archivos?|'
        r'explorador|paint|chrome|google\s+chrome|firefox|edge|'
        r'administrador\s+de\s+tareas?|task\s+manager)\b',
        re.IGNORECASE,
    )

    # ------------------------------------------------------------------
    # Datos estáticos
    # ------------------------------------------------------------------

    _CHISTES: List[str] = [
        "¿Por qué los pájaros vuelan hacia el sur en invierno? "
        "¡Porque caminar sería demasiado lejos!",

        "¿Qué le dijo el cero al ocho? "
        "¡Bonito cinturón!",

        "¿Por qué el libro de matemáticas estaba triste? "
        "Porque tenía demasiados problemas.",

        "¿Qué hace una abeja en el gimnasio? "
        "¡Zum-ba!",

        "¿Cómo se llama el campeón de buceo de Japón? "
        "Tokofondo.",

        "¿Qué le dice un jardinero a otro? "
        "¡Que te peta la albahaca!",

        "¿Por qué el espantapájaros ganó un premio? "
        "Porque era sobresaliente en su campo.",
    ]

    # Mapa nombre normalizado → binario del sistema
    _APP_MAP: Dict[str, str] = {
        "calculadora":                "calc.exe",
        "bloc de notas":              "notepad.exe",
        "bloc de nota":               "notepad.exe",
        "notepad":                    "notepad.exe",
        "explorador de archivos":     "explorer.exe",
        "explorador de archivo":      "explorer.exe",
        "explorador":                 "explorer.exe",
        "paint":                      "mspaint.exe",
        "chrome":                     "chrome.exe",
        "google chrome":              "chrome.exe",
        "firefox":                    "firefox.exe",
        "edge":                       "msedge.exe",
        "administrador de tareas":    "taskmgr.exe",
        "administrador de tarea":     "taskmgr.exe",
        "task manager":               "taskmgr.exe",
    }

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def handle(self, text: str) -> Optional[str]:
        """
        Procesa el texto y retorna una respuesta string, o None si no reconoce el comando.

        Nunca lanza excepciones.
        """
        if not text or not text.strip():
            return None

        try:
            text_clean = text.strip()

            if self._HORA_PATTERN.search(text_clean):
                return self._handle_hora()

            if self._CHISTE_PATTERN.search(text_clean):
                return self._handle_chiste()

            match = self._APP_PATTERN.search(text_clean)
            if match:
                # Extraer el nombre de la app del grupo capturado
                app_raw = match.group(2).lower().strip()
                return self._handle_app(app_raw)

            return None   # Comando no reconocido

        except Exception as exc:
            logger.error("OfflineCommandHandler.handle() error inesperado: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Handlers individuales
    # ------------------------------------------------------------------

    def _handle_hora(self) -> str:
        """Retorna la hora actual del sistema."""
        now = datetime.now()
        hora_str = now.strftime("%H:%M:%S")
        return f"Son las {hora_str}."

    def _handle_chiste(self) -> str:
        """Retorna un chiste aleatorio de la lista estática."""
        return random.choice(self._CHISTES)

    def _handle_app(self, app_raw: str) -> str:
        """
        Abre la aplicación nativa correspondiente.
        Verifica existencia con shutil.which() antes de ejecutar.
        """
        # Normalizar: colapsar espacios múltiples
        app_key = re.sub(r'\s+', ' ', app_raw).strip()

        binary = self._APP_MAP.get(app_key)
        if binary is None:
            # Intentar coincidencia parcial
            for key, bin_name in self._APP_MAP.items():
                if key in app_key or app_key in key:
                    binary = bin_name
                    break

        if binary is None:
            return f"No conozco la aplicación '{app_raw}'."

        # En Windows los binarios del sistema están en PATH o en System32
        found = shutil.which(binary)
        if found is None and sys.platform == "win32":
            # Intentar ruta directa en System32
            import os
            system32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
            candidate = os.path.join(system32, binary)
            if os.path.isfile(candidate):
                found = candidate

        if found is None:
            logger.warning("OfflineCommandHandler: binario '%s' no encontrado.", binary)
            return f"No encontré '{binary}' en el sistema."

        try:
            subprocess.Popen([found], shell=False)
            app_display = app_key.capitalize()
            logger.info("OfflineCommandHandler: abriendo '%s' (%s).", app_display, found)
            return f"Abriendo {app_display}."
        except Exception as exc:
            logger.error("OfflineCommandHandler: error al abrir '%s': %s", binary, exc)
            return f"No pude abrir '{app_key}': {exc}"
