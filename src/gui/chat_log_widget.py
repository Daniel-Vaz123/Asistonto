"""
ChatLogWidget — Panel de historial de conversación para Asistonto GUI Fase 1.

Muestra mensajes de usuario y asistente con timestamps HH:MM:SS,
diferenciación visual por color y auto-scroll al mensaje más reciente.
"""

import tkinter as tk
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from src.gui import theme


class ChatLogWidget(ctk.CTkFrame):
    """
    Panel de chat con scroll automático.

    Uso:
        log = ChatLogWidget(parent)
        log.add_user_message("qué hora es")
        log.add_assistant_message("Son las 14:32:05")
        log.add_error_message("Modelo Vosk no encontrado")
    """

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=theme.BG_SECONDARY,
            corner_radius=12,
            **kwargs,
        )

        # Título del panel
        self._title_label = ctk.CTkLabel(
            self,
            text="Conversación",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_MD, weight="bold"),
            text_color=theme.TEXT_SECONDARY,
        )
        self._title_label.pack(anchor="w", padx=16, pady=(12, 4))

        # Separador
        sep = ctk.CTkFrame(self, height=1, fg_color=theme.BORDER_COLOR)
        sep.pack(fill="x", padx=16, pady=(0, 8))

        # Textbox principal
        self._textbox = ctk.CTkTextbox(
            self,
            fg_color=theme.BG_PRIMARY,
            text_color=theme.TEXT_PRIMARY,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=theme.FONT_SIZE_SM),
            corner_radius=8,
            wrap="word",
            state="disabled",   # Solo lectura — se habilita temporalmente para insertar
            scrollbar_button_color=theme.BG_TERTIARY,
            scrollbar_button_hover_color=theme.BORDER_COLOR,
        )
        self._textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Configurar tags de color
        self._textbox._textbox.tag_configure(
            "user",
            foreground=theme.CHAT_USER_COLOR,
            justify="right",
        )
        self._textbox._textbox.tag_configure(
            "assistant",
            foreground=theme.CHAT_ASSISTANT_COLOR,
            justify="left",
        )
        self._textbox._textbox.tag_configure(
            "error",
            foreground=theme.CHAT_ERROR_COLOR,
            justify="left",
        )
        self._textbox._textbox.tag_configure(
            "timestamp",
            foreground=theme.CHAT_TIMESTAMP_COLOR,
        )

        self._message_count = 0

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def add_user_message(self, text: str) -> None:
        """
        Inserta mensaje del usuario.
        Formato: [HH:MM:SS] Tú: <text>
        Color: ACCENT_CYAN, alineación derecha.
        """
        ts = self._timestamp()
        self._append(f"[{ts}] Tú: {text}\n", tag="user")

    def add_assistant_message(self, text: str) -> None:
        """
        Inserta mensaje del asistente.
        Formato: [HH:MM:SS] Asistonto: <text>
        Color: ACCENT_GREEN, alineación izquierda.
        """
        ts = self._timestamp()
        self._append(f"[{ts}] Asistonto: {text}\n", tag="assistant")

    def add_error_message(self, text: str) -> None:
        """
        Inserta mensaje de error.
        Color: TEXT_ERROR (#ef4444), alineación izquierda.
        """
        ts = self._timestamp()
        self._append(f"[{ts}] ⚠ {text}\n", tag="error")

    def add_system_message(self, text: str) -> None:
        """Inserta mensaje del sistema (info, sin timestamp de usuario)."""
        ts = self._timestamp()
        self._append(f"[{ts}] — {text}\n", tag="timestamp")

    @property
    def message_count(self) -> int:
        """Número de mensajes insertados en la sesión."""
        return self._message_count

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _append(self, text: str, tag: str) -> None:
        """
        Inserta texto con el tag dado y hace scroll al final.
        Habilita el textbox temporalmente para escritura.
        """
        tb = self._textbox._textbox
        tb.configure(state="normal")
        tb.insert("end", text, tag)
        tb.configure(state="disabled")
        tb.see("end")   # Auto-scroll — dentro de 100 ms por el event loop
        self._message_count += 1

    @staticmethod
    def _timestamp() -> str:
        """Retorna timestamp en formato HH:MM:SS."""
        return datetime.now().strftime("%H:%M:%S")
