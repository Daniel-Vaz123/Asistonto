"""
AvatarWidget — Orbe 2D animado con 4 estados para Asistonto GUI Fase 1.

Cada estado tiene su propio loop de animación ejecutado via canvas.after().
Las transiciones son idempotentes: set_state(s) cuando ya está en s no hace nada.
"""

import math
import tkinter as tk
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import customtkinter as ctk

from src.gui import theme


class AvatarState(Enum):
    """Los cuatro estados posibles del avatar. Invariante: exactamente uno activo."""
    IDLE       = "IDLE"
    LISTENING  = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING   = "SPEAKING"


@dataclass
class AnimationState:
    """Estado interno de la animación activa."""
    after_id:  Optional[str] = None   # ID del after() pendiente para cancelación
    phase:     float          = 0.0   # Progreso del ciclo 0.0 → 1.0
    direction: int            = 1     # +1 o -1 para animaciones oscilantes
    angle:     float          = 0.0   # Ángulo actual para spinner (grados)


class AvatarWidget(ctk.CTkFrame):
    """
    Orbe 2D animado en Canvas de tkinter.

    Uso:
        widget = AvatarWidget(parent)
        widget.set_state(AvatarState.LISTENING)
    """

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=theme.BG_SECONDARY,
            corner_radius=16,
            **kwargs,
        )

        self._current_state: AvatarState = AvatarState.IDLE
        self._anim = AnimationState()

        size = theme.AVATAR_CANVAS_SIZE
        self._canvas = tk.Canvas(
            self,
            width=size,
            height=size,
            bg=theme.BG_SECONDARY,
            highlightthickness=0,
        )
        self._canvas.pack(padx=10, pady=10)

        self._cx = size // 2   # Centro X del canvas
        self._cy = size // 2   # Centro Y del canvas
        self._base_r = theme.AVATAR_ORB_RADIUS

        # Arrancar en IDLE
        self._start_animation(AvatarState.IDLE)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_state(self, state: AvatarState) -> None:
        """
        Transiciona al estado dado.
        Idempotente: si state == self._current_state, retorna sin efectos.
        Completa la transición en < 200 ms.
        """
        if state == self._current_state:
            return
        self._cancel_animation()
        self._current_state = state
        self._anim = AnimationState()   # Reset de fase/ángulo
        self._start_animation(state)

    @property
    def current_state(self) -> AvatarState:
        return self._current_state

    # ------------------------------------------------------------------
    # Control de animación
    # ------------------------------------------------------------------

    def _cancel_animation(self) -> None:
        """Cancela el after() pendiente del loop actual."""
        if self._anim.after_id is not None:
            try:
                self._canvas.after_cancel(self._anim.after_id)
            except Exception:
                pass
            self._anim.after_id = None

    def _start_animation(self, state: AvatarState) -> None:
        """Despacha al loop de animación correspondiente al estado."""
        dispatch = {
            AvatarState.IDLE:       self._animate_idle,
            AvatarState.LISTENING:  self._animate_listening,
            AvatarState.PROCESSING: self._animate_processing,
            AvatarState.SPEAKING:   self._animate_speaking,
        }
        dispatch[state]()

    # ------------------------------------------------------------------
    # Loops de animación — cada uno se reprograma a sí mismo
    # ------------------------------------------------------------------

    def _animate_idle(self) -> None:
        """Respiración suave: escala 0.8 → 1.0, ciclo 3000 ms."""
        if self._current_state != AvatarState.IDLE:
            return

        cycle_ms   = theme.ANIM_IDLE_CYCLE_MS
        step_ms    = 30
        step_phase = step_ms / cycle_ms

        self._anim.phase += step_phase * self._anim.direction
        if self._anim.phase >= 1.0:
            self._anim.phase = 1.0
            self._anim.direction = -1
        elif self._anim.phase <= 0.0:
            self._anim.phase = 0.0
            self._anim.direction = 1

        # Escala 0.8 → 1.0
        scale = 0.8 + 0.2 * self._anim.phase
        r = int(self._base_r * scale)
        color = theme.AVATAR_COLORS["IDLE"]
        glow  = theme.AVATAR_GLOW_COLORS["IDLE"]

        self._draw_orb(r, color, glow, alpha_rings=False)
        self._anim.after_id = self._canvas.after(step_ms, self._animate_idle)

    def _animate_listening(self) -> None:
        """Pulso rápido: escala 0.9 → 1.1, ciclo 800 ms."""
        if self._current_state != AvatarState.LISTENING:
            return

        cycle_ms   = theme.ANIM_LISTENING_CYCLE_MS
        step_ms    = 20
        step_phase = step_ms / cycle_ms

        self._anim.phase += step_phase * self._anim.direction
        if self._anim.phase >= 1.0:
            self._anim.phase = 1.0
            self._anim.direction = -1
        elif self._anim.phase <= 0.0:
            self._anim.phase = 0.0
            self._anim.direction = 1

        # Escala 0.9 → 1.1
        scale = 0.9 + 0.2 * self._anim.phase
        r = int(self._base_r * scale)
        color = theme.AVATAR_COLORS["LISTENING"]
        glow  = theme.AVATAR_GLOW_COLORS["LISTENING"]

        self._draw_orb(r, color, glow, alpha_rings=True)
        self._anim.after_id = self._canvas.after(step_ms, self._animate_listening)

    def _animate_processing(self) -> None:
        """Spinner: arco rotatorio, ciclo 1000 ms."""
        if self._current_state != AvatarState.PROCESSING:
            return

        step_ms    = 16   # ~60 fps
        degrees_per_step = 360 / (theme.ANIM_PROCESSING_CYCLE_MS / step_ms)

        self._anim.angle = (self._anim.angle + degrees_per_step) % 360

        color = theme.AVATAR_COLORS["PROCESSING"]
        glow  = theme.AVATAR_GLOW_COLORS["PROCESSING"]
        r     = self._base_r

        self._canvas.delete("all")
        # Orbe base tenue
        self._canvas.create_oval(
            self._cx - r, self._cy - r,
            self._cx + r, self._cy + r,
            fill=theme.BG_TERTIARY, outline=color, width=2,
        )
        # Arco giratorio
        start_angle = self._anim.angle
        self._canvas.create_arc(
            self._cx - r - 12, self._cy - r - 12,
            self._cx + r + 12, self._cy + r + 12,
            start=start_angle, extent=270,
            style=tk.ARC, outline=color, width=4,
        )
        # Punto en la punta del arco
        tip_rad = math.radians(start_angle)
        tip_x = self._cx + (r + 12) * math.cos(tip_rad)
        tip_y = self._cy - (r + 12) * math.sin(tip_rad)
        self._canvas.create_oval(
            tip_x - 5, tip_y - 5, tip_x + 5, tip_y + 5,
            fill=glow, outline="",
        )

        self._anim.after_id = self._canvas.after(step_ms, self._animate_processing)

    def _animate_speaking(self) -> None:
        """Ondas concéntricas expansivas, ciclo 400 ms."""
        if self._current_state != AvatarState.SPEAKING:
            return

        step_ms    = 20
        step_phase = step_ms / theme.ANIM_SPEAKING_CYCLE_MS

        self._anim.phase = (self._anim.phase + step_phase) % 1.0

        color = theme.AVATAR_COLORS["SPEAKING"]
        glow  = theme.AVATAR_GLOW_COLORS["SPEAKING"]
        r     = self._base_r

        self._canvas.delete("all")

        # Ondas concéntricas (3 anillos desfasados)
        for i in range(3):
            wave_phase = (self._anim.phase + i / 3) % 1.0
            wave_r = int(r + wave_phase * 40)
            alpha_factor = 1.0 - wave_phase   # Desvanece al expandirse
            ring_color = self._interpolate_alpha(color, theme.BG_SECONDARY, alpha_factor)
            self._canvas.create_oval(
                self._cx - wave_r, self._cy - wave_r,
                self._cx + wave_r, self._cy + wave_r,
                outline=ring_color, width=2, fill="",
            )

        # Orbe central
        self._canvas.create_oval(
            self._cx - r, self._cy - r,
            self._cx + r, self._cy + r,
            fill=color, outline=glow, width=2,
        )

        self._anim.after_id = self._canvas.after(step_ms, self._animate_speaking)

    # ------------------------------------------------------------------
    # Helpers de dibujo
    # ------------------------------------------------------------------

    def _draw_orb(self, r: int, color: str, glow: str, alpha_rings: bool) -> None:
        """Dibuja el orbe principal con halo opcional."""
        self._canvas.delete("all")

        if alpha_rings:
            # Halo exterior tenue
            halo_r = r + 15
            self._canvas.create_oval(
                self._cx - halo_r, self._cy - halo_r,
                self._cx + halo_r, self._cy + halo_r,
                outline=glow, width=1, fill="",
            )

        # Orbe principal
        self._canvas.create_oval(
            self._cx - r, self._cy - r,
            self._cx + r, self._cy + r,
            fill=color, outline=glow, width=2,
        )

        # Reflejo interior (punto de luz)
        highlight_r = max(4, r // 5)
        hx = self._cx - r // 3
        hy = self._cy - r // 3
        self._canvas.create_oval(
            hx - highlight_r, hy - highlight_r,
            hx + highlight_r, hy + highlight_r,
            fill="#ffffff", outline="",
        )

    @staticmethod
    def _interpolate_alpha(hex_color: str, bg_color: str, factor: float) -> str:
        """
        Interpola entre hex_color y bg_color según factor (0.0=bg, 1.0=color).
        Usado para simular transparencia en Canvas (que no soporta alpha real).
        """
        def parse(h: str):
            h = h.lstrip("#")
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

        r1, g1, b1 = parse(hex_color)
        r2, g2, b2 = parse(bg_color)
        f = max(0.0, min(1.0, factor))
        r = int(r1 * f + r2 * (1 - f))
        g = int(g1 * f + g2 * (1 - f))
        b = int(b1 * f + b2 * (1 - f))
        return f"#{r:02x}{g:02x}{b:02x}"
