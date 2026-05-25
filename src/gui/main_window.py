"""
MainWindow — Ventana principal de Asistonto GUI Fase 1.

Layout de dos columnas:
  - Izquierda (300 px): AvatarWidget + label de estado + botón "Escuchar"
  - Derecha  (580 px): ChatLogWidget

Comunicación con hilos secundarios via queue.Queue + polling each 50 ms.
"""

import queue
import signal
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import customtkinter as ctk

from src.gui import theme
from src.gui.avatar_widget import AvatarState, AvatarWidget
from src.gui.chat_log_widget import ChatLogWidget


# ---------------------------------------------------------------------------
# Protocolo de eventos (hilo → GUI)
# ---------------------------------------------------------------------------

class EventType(Enum):
    TRANSCRIPTION = "transcription"   # str: texto reconocido por STT
    WAKE_WORD     = "wake_word"       # str: wake word detectado
    STATE_CHANGE  = "state_change"    # AvatarState: nuevo estado solicitado
    ERROR         = "error"           # str: mensaje de error
    TTS_DONE      = "tts_done"        # None: TTS terminó de hablar


@dataclass
class GUIEvent:
    """Evento tipado que viaja de hilos secundarios al Main Thread via queue."""
    type:      EventType
    payload:   Any   = None
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------

class MainWindow(ctk.CTk):
    """
    Ventana principal de Asistonto.

    Parámetros:
        event_queue       — queue.Queue compartida con hilos de audio/TTS
        on_listen_pressed — callback invocado cuando el usuario pulsa "Escuchar"
        on_close          — callback invocado antes de destruir la ventana
    """

    def __init__(
        self,
        event_queue: queue.Queue,
        on_listen_pressed: Optional[Callable[[], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ):
        super().__init__()

        self._event_queue      = event_queue
        self._on_listen_pressed = on_listen_pressed
        self._on_close_cb      = on_close

        # ---- Configuración de la ventana ----
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(theme.WINDOW_TITLE)
        self.minsize(theme.WINDOW_MIN_WIDTH, theme.WINDOW_MIN_HEIGHT)
        self.geometry(f"{theme.WINDOW_MIN_WIDTH}x{theme.WINDOW_MIN_HEIGHT}")
        self.configure(fg_color=theme.BG_PRIMARY)

        # Interceptar cierre de ventana
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---- Construir layout ----
        self._build_layout()

        # ---- Arrancar polling de la queue ----
        self.after(theme.ANIM_POLL_INTERVAL_MS, self._poll_queue)

    # ------------------------------------------------------------------
    # Construcción del layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        """Crea las dos columnas y sus widgets."""
        self.grid_columnconfigure(0, weight=0, minsize=theme.LEFT_PANEL_WIDTH)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- Columna izquierda ----
        left = ctk.CTkFrame(self, fg_color=theme.BG_SECONDARY, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_rowconfigure(0, weight=1)   # Avatar se expande
        left.grid_rowconfigure(1, weight=0)   # Estado fijo
        left.grid_rowconfigure(2, weight=0)   # Botón fijo
        left.grid_columnconfigure(0, weight=1)

        # Título de la app
        title_lbl = ctk.CTkLabel(
            left,
            text="Asistonto",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_XL, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        title_lbl.grid(row=0, column=0, pady=(16, 4), sticky="n")

        # Avatar widget
        self._avatar = AvatarWidget(left)
        self._avatar.grid(row=0, column=0, pady=(40, 8), sticky="n")

        # Label de estado
        self._state_label = ctk.CTkLabel(
            left,
            text=theme.STATE_LABELS["IDLE"],
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_LG),
            text_color=theme.AVATAR_COLORS["IDLE"],
        )
        self._state_label.grid(row=1, column=0, pady=(0, 16))

        # Botón "Escuchar"
        self._listen_btn = ctk.CTkButton(
            left,
            text="🎤  Escuchar",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_MD, weight="bold"),
            fg_color=theme.BG_TERTIARY,
            hover_color=theme.ACCENT_CYAN,
            text_color=theme.TEXT_PRIMARY,
            corner_radius=24,
            height=44,
            command=self._on_listen_button,
        )
        self._listen_btn.grid(row=2, column=0, padx=24, pady=(0, 24), sticky="ew")

        # ---- Columna derecha ----
        self._chat_log = ChatLogWidget(self)
        self._chat_log.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)

        # Mensaje de bienvenida
        self._chat_log.add_system_message(
            "Asistonto iniciado. Di la palabra clave o pulsa 'Escuchar'."
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_avatar_state(self, state: AvatarState) -> None:
        """
        Cambia el estado del avatar y actualiza el label de estado.
        Sincronizado: label y animación cambian en el mismo frame.
        """
        self._avatar.set_state(state)
        label_text = theme.STATE_LABELS[state.value]
        color      = theme.AVATAR_COLORS[state.value]
        self._state_label.configure(text=label_text, text_color=color)

        # Habilitar/deshabilitar botón según estado
        if state in (AvatarState.LISTENING, AvatarState.PROCESSING, AvatarState.SPEAKING):
            self._listen_btn.configure(state="disabled")
        else:
            self._listen_btn.configure(state="normal")

    @property
    def chat_log(self) -> ChatLogWidget:
        return self._chat_log

    @property
    def avatar(self) -> AvatarWidget:
        return self._avatar

    # ------------------------------------------------------------------
    # Polling de la queue (Main Thread)
    # ------------------------------------------------------------------

    def _poll_queue(self) -> None:
        """
        Consume todos los GUIEvent disponibles en event_queue.
        Se reprograma cada ANIM_POLL_INTERVAL_MS ms.
        Nunca bloquea — usa get_nowait().
        """
        try:
            while True:
                event: GUIEvent = self._event_queue.get_nowait()
                self._dispatch_event(event)
        except queue.Empty:
            pass
        finally:
            self.after(theme.ANIM_POLL_INTERVAL_MS, self._poll_queue)

    def _dispatch_event(self, event: GUIEvent) -> None:
        """Despacha un GUIEvent al handler correspondiente."""
        if event.type == EventType.STATE_CHANGE and isinstance(event.payload, AvatarState):
            self.set_avatar_state(event.payload)

        elif event.type == EventType.TRANSCRIPTION and event.payload:
            self._chat_log.add_user_message(str(event.payload))

        elif event.type == EventType.WAKE_WORD:
            self.set_avatar_state(AvatarState.LISTENING)

        elif event.type == EventType.ERROR and event.payload:
            self._chat_log.add_error_message(str(event.payload))
            self.set_avatar_state(AvatarState.IDLE)

        elif event.type == EventType.TTS_DONE:
            self.set_avatar_state(AvatarState.IDLE)

    # ------------------------------------------------------------------
    # Handlers de botón y cierre
    # ------------------------------------------------------------------

    def _on_listen_button(self) -> None:
        """Fuerza el modo escucha sin necesidad de wake word."""
        self.set_avatar_state(AvatarState.LISTENING)
        if self._on_listen_pressed:
            self._on_listen_pressed()

    def _on_close(self) -> None:
        """
        Intercepta el cierre de ventana (botón X).
        Llama al callback de cierre limpio antes de destruir.
        Garantiza que la ventana se cierra incluso si el callback falla.
        """
        try:
            if self._on_close_cb:
                self._on_close_cb()
        except Exception:
            pass
        finally:
            self.destroy()
