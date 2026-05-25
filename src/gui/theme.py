"""
Theme — Paleta de colores y tipografía para la GUI de Asistonto (Fase 1).

Módulo de constantes puras: sin clases, sin estado, sin efectos secundarios.
Importar directamente: from src.gui.theme import BG_PRIMARY, AVATAR_COLORS, etc.
"""

# ---------------------------------------------------------------------------
# Paleta de colores — Modo oscuro
# ---------------------------------------------------------------------------

BG_PRIMARY    = "#1a1a2e"   # Fondo principal de la ventana
BG_SECONDARY  = "#16213e"   # Fondo de paneles secundarios
BG_TERTIARY   = "#0f3460"   # Fondo de elementos elevados (botones, cards)

ACCENT_CYAN   = "#00d4ff"   # Acento principal — estado LISTENING
ACCENT_PURPLE = "#7c3aed"   # Acento secundario — estado PROCESSING
ACCENT_GREEN  = "#10b981"   # Acento terciario — estado SPEAKING
ACCENT_GRAY   = "#4a5568"   # Acento neutro — estado IDLE

TEXT_PRIMARY   = "#e2e8f0"  # Texto principal
TEXT_SECONDARY = "#94a3b8"  # Texto secundario / timestamps
TEXT_ERROR     = "#ef4444"  # Texto de error

BORDER_COLOR  = "#2d3748"   # Color de bordes y separadores

# ---------------------------------------------------------------------------
# Colores por estado del Avatar
# ---------------------------------------------------------------------------

AVATAR_COLORS: dict = {
    "IDLE":       ACCENT_GRAY,
    "LISTENING":  ACCENT_CYAN,
    "PROCESSING": ACCENT_PURPLE,
    "SPEAKING":   ACCENT_GREEN,
}

# Colores de glow/halo por estado (versión más brillante para el efecto de brillo)
AVATAR_GLOW_COLORS: dict = {
    "IDLE":       "#6b7280",
    "LISTENING":  "#67e8f9",
    "PROCESSING": "#a78bfa",
    "SPEAKING":   "#34d399",
}

# ---------------------------------------------------------------------------
# Etiquetas de estado (normativas — no usar "por ejemplo")
# ---------------------------------------------------------------------------

STATE_LABELS: dict = {
    "IDLE":       "En espera",
    "LISTENING":  "Escuchando...",
    "PROCESSING": "Procesando...",
    "SPEAKING":   "Hablando...",
}

# ---------------------------------------------------------------------------
# Colores de mensajes en el Chat Log
# ---------------------------------------------------------------------------

CHAT_USER_COLOR      = ACCENT_CYAN    # Mensajes del usuario
CHAT_ASSISTANT_COLOR = ACCENT_GREEN   # Mensajes del asistente
CHAT_ERROR_COLOR     = TEXT_ERROR     # Mensajes de error
CHAT_TIMESTAMP_COLOR = TEXT_SECONDARY # Timestamps

# ---------------------------------------------------------------------------
# Tipografía
# ---------------------------------------------------------------------------

FONT_FAMILY = "Segoe UI"   # Windows; fallback automático en otros OS

FONT_SIZE_XS = 9
FONT_SIZE_SM = 11
FONT_SIZE_MD = 13
FONT_SIZE_LG = 16
FONT_SIZE_XL = 20

FONT_BOLD   = (FONT_FAMILY, FONT_SIZE_MD, "bold")
FONT_NORMAL = (FONT_FAMILY, FONT_SIZE_MD)
FONT_SMALL  = (FONT_FAMILY, FONT_SIZE_SM)
FONT_TINY   = (FONT_FAMILY, FONT_SIZE_XS)
FONT_TITLE  = (FONT_FAMILY, FONT_SIZE_XL, "bold")
FONT_STATE  = (FONT_FAMILY, FONT_SIZE_LG)

# ---------------------------------------------------------------------------
# Dimensiones de la ventana
# ---------------------------------------------------------------------------

WINDOW_MIN_WIDTH  = 900
WINDOW_MIN_HEIGHT = 650
WINDOW_TITLE      = "Asistonto — Fase 1 (Offline)"

LEFT_PANEL_WIDTH  = 300   # Columna izquierda: Avatar + controles
RIGHT_PANEL_WIDTH = 580   # Columna derecha: Chat Log

AVATAR_CANVAS_SIZE = 220  # Tamaño del canvas cuadrado del avatar
AVATAR_ORB_RADIUS  = 70   # Radio base del orbe en píxeles

# ---------------------------------------------------------------------------
# Parámetros de animación
# ---------------------------------------------------------------------------

ANIM_IDLE_CYCLE_MS       = 3000   # Ciclo de respiración IDLE (ms)
ANIM_LISTENING_CYCLE_MS  = 800    # Ciclo de pulso LISTENING (ms)
ANIM_PROCESSING_CYCLE_MS = 1000   # Ciclo de spinner PROCESSING (ms)
ANIM_SPEAKING_CYCLE_MS   = 400    # Ciclo de ondas SPEAKING (ms)
ANIM_POLL_INTERVAL_MS    = 50     # Intervalo de polling de la queue (ms)
