"""
TTSEngine — Motor de síntesis de voz offline con pyttsx3.

Cada llamada a speak() lanza un hilo daemon separado para no bloquear
el Main Thread de la GUI. pyttsx3.init() se llama dentro del hilo
para evitar conflictos con el event loop de tkinter en Windows.

Cuando la reproducción termina, llama on_done() via root.after(0, on_done)
para que el callback se ejecute en el Main Thread (thread-safe).
"""

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import pyttsx3
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _PYTTSX3_AVAILABLE = False


class TTSEngine:
    """
    Wrapper thread-safe de pyttsx3.

    Uso:
        tts = TTSEngine(root_widget=window)
        tts.speak("Hola, son las 14:32.", on_done=lambda: print("listo"))
    """

    def __init__(self, root_widget=None) -> None:
        """
        Args:
            root_widget: Widget raíz de tkinter (MainWindow).
                         Se usa para llamar on_done() en el Main Thread
                         via root_widget.after(0, on_done).
        """
        self._root       = root_widget
        self._stop_event = threading.Event()
        self._lock       = threading.Lock()   # Solo un hilo TTS a la vez
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def speak(self, text: str, on_done: Optional[Callable[[], None]] = None) -> None:
        """
        Sintetiza y reproduce text en un hilo daemon.
        Si pyttsx3 no puede inicializarse, llama on_done() igualmente
        para no dejar el avatar en SPEAKING indefinidamente.

        Args:
            text:    Texto a sintetizar.
            on_done: Callback invocado en el Main Thread al terminar.
        """
        if not text or not text.strip():
            if on_done:
                self._call_on_done(on_done)
            return

        # Cancelar hilo anterior si sigue activo (no bloquear)
        self._stop_event.set()

        def _run():
            with self._lock:
                self._stop_event.clear()
                self._do_speak(text, on_done)

        self._thread = threading.Thread(target=_run, daemon=True, name="TTSThread")
        self._thread.start()

    def stop(self) -> None:
        """Señaliza al hilo activo que debe detenerse."""
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _do_speak(self, text: str, on_done: Optional[Callable[[], None]]) -> None:
        """Ejecuta la síntesis dentro del hilo daemon."""
        if not _PYTTSX3_AVAILABLE:
            logger.error("TTSEngine: pyttsx3 no está instalado. Ejecuta: pip install pyttsx3")
            self._call_on_done(on_done)
            return

        engine = None
        try:
            # init() dentro del hilo — evita conflictos con tkinter en Windows
            engine = pyttsx3.init()

            # Configuración básica de voz
            engine.setProperty("rate", 160)    # Palabras por minuto
            engine.setProperty("volume", 0.9)  # 0.0 – 1.0

            # Intentar seleccionar voz en español si está disponible
            voices = engine.getProperty("voices")
            for v in voices:
                if "spanish" in v.name.lower() or "es" in (v.id or "").lower():
                    engine.setProperty("voice", v.id)
                    break

            if self._stop_event.is_set():
                return   # Cancelado antes de empezar

            engine.say(text)
            engine.runAndWait()
            logger.info("TTSEngine: reproducción completada.")

        except Exception as exc:
            logger.error("TTSEngine: error en pyttsx3: %s", exc)
        finally:
            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass
            self._call_on_done(on_done)

    def _call_on_done(self, on_done: Optional[Callable[[], None]]) -> None:
        """
        Llama on_done() en el Main Thread via root.after(0, ...).
        Si no hay root disponible, lo llama directamente (tests, etc.).
        """
        if on_done is None:
            return
        if self._root is not None:
            try:
                self._root.after(0, on_done)
                return
            except Exception:
                pass
        # Fallback: llamar directamente (puede no ser thread-safe en tkinter)
        try:
            on_done()
        except Exception as exc:
            logger.warning("TTSEngine: error en on_done callback: %s", exc)
