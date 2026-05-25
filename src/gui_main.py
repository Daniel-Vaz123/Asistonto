"""
gui_main.py — Punto de entrada de Asistonto GUI Fase 1 (Offline).

Uso:
    python -m src.gui_main
    python src/gui_main.py

Arquitectura de hilos:
    Main Thread  → GUI (CustomTkinter mainloop)
    STTThread    → Vosk KaldiRecognizer + detección de wake words
    TTSThread    → pyttsx3 (lanzado por llamada, hilo daemon)

Comunicación entre hilos:
    STTThread → event_queue (queue.Queue) → Main Thread (polling cada 50 ms)
    TTSThread → root.after(0, on_done)    → Main Thread
"""

import json
import logging
import queue
import signal
import sys
import threading
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging (antes de cualquier otro import para capturar errores de arranque)
# ---------------------------------------------------------------------------

Path("logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("logs/voice_assistant.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("gui_main")

# ---------------------------------------------------------------------------
# Imports del proyecto
# ---------------------------------------------------------------------------

from src.audio_manager import AudioManager                          # noqa: E402
from src.gui.avatar_widget import AvatarState                       # noqa: E402
from src.gui.main_window import EventType, GUIEvent, MainWindow     # noqa: E402
from src.gui import theme                                           # noqa: E402
from src.offline.stt_local import STTEngine                         # noqa: E402
from src.offline.tts_local import TTSEngine                         # noqa: E402
from src.offline.offline_command_handler import OfflineCommandHandler  # noqa: E402


# ---------------------------------------------------------------------------
# ResourceManager
# ---------------------------------------------------------------------------

class ResourceManager:
    """
    Cierre limpio y atómico de todos los recursos.

    Garantías:
    - Idempotente: shutdown() puede llamarse N veces; solo la primera actúa.
    - Timeout: espera máximo 5 s al Audio Thread antes de continuar.
    - Cobertura: botón X, SIGTERM, SIGINT, excepción no capturada.
    """

    _SHUTDOWN_TIMEOUT_S = 5.0

    def __init__(self) -> None:
        self._shutdown_event  = threading.Event()
        self._window: Optional[MainWindow] = None
        self._audio_manager: Optional[AudioManager] = None
        self._stt_engine:    Optional[STTEngine]    = None
        self._tts_engine:    Optional[TTSEngine]    = None

    def register_window(self, window: MainWindow) -> None:
        self._window = window

    def register_components(
        self,
        audio_manager: Optional[AudioManager] = None,
        stt_engine:    Optional[STTEngine]    = None,
        tts_engine:    Optional[TTSEngine]    = None,
    ) -> None:
        self._audio_manager = audio_manager
        self._stt_engine    = stt_engine
        self._tts_engine    = tts_engine

    def shutdown(self) -> None:
        """Cierre limpio. Idempotente."""
        if self._shutdown_event.is_set():
            return
        self._shutdown_event.set()
        logger.info("ResourceManager: iniciando cierre limpio...")

        # 1. Detener STT (señaliza el hilo de audio)
        if self._stt_engine is not None:
            try:
                self._stt_engine.stop()
                logger.info("ResourceManager: STTEngine detenido.")
            except Exception as exc:
                logger.warning("ResourceManager: error al detener STTEngine: %s", exc)

        # 2. Detener captura de audio + liberar PyAudio (atómico con try/finally)
        if self._audio_manager is not None:
            try:
                self._audio_manager.stop_continuous_capture()
                capture_thread = getattr(self._audio_manager, "_capture_thread", None)
                if capture_thread and capture_thread.is_alive():
                    capture_thread.join(timeout=self._SHUTDOWN_TIMEOUT_S)
                    if capture_thread.is_alive():
                        logger.warning(
                            "ResourceManager: Audio Thread no terminó en %s s.",
                            self._SHUTDOWN_TIMEOUT_S,
                        )
            except Exception as exc:
                logger.warning("ResourceManager: error al detener AudioManager: %s", exc)
            finally:
                try:
                    self._audio_manager.cleanup()
                    logger.info("ResourceManager: AudioManager liberado (PyAudio cerrado).")
                except Exception as exc:
                    logger.warning("ResourceManager: error en AudioManager.cleanup(): %s", exc)

        # 3. Detener TTS
        if self._tts_engine is not None:
            try:
                self._tts_engine.stop()
                logger.info("ResourceManager: TTSEngine detenido.")
            except Exception as exc:
                logger.warning("ResourceManager: error al detener TTSEngine: %s", exc)

        logger.info("ResourceManager: todos los recursos liberados correctamente.")

        # 4. Destruir ventana desde el Main Thread
        if self._window is not None:
            try:
                self._window.after(0, self._window.destroy)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Orquestador principal
# ---------------------------------------------------------------------------

class VoiceAssistantGUI:
    """
    Orquestador de Asistonto GUI Fase 1.

    Conecta MainWindow ↔ AudioManager ↔ STTEngine ↔ TTSEngine ↔ OfflineCommandHandler.
    """

    def __init__(self) -> None:
        self._event_queue:     queue.Queue              = queue.Queue(maxsize=500)
        self._resource_manager: ResourceManager         = ResourceManager()
        self._window:          Optional[MainWindow]     = None
        self._audio_manager:   Optional[AudioManager]   = None
        self._stt_engine:      Optional[STTEngine]      = None
        self._tts_engine:      Optional[TTSEngine]      = None
        self._command_handler: Optional[OfflineCommandHandler] = None
        self._stt_available    = False   # False si el modelo Vosk no existe

    # ------------------------------------------------------------------
    # Arranque
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Punto de entrada principal.
        1. Carga config.json
        2. Registra signal handlers
        3. Inicializa componentes
        4. Crea la ventana y arranca el mainloop
        """
        config = self._load_config()
        logger.info(
            "Configuración cargada: sample_rate=%s, wake_words=%s",
            config.get("audio", {}).get("sample_rate"),
            config.get("wake_words"),
        )

        self._register_signal_handlers()

        # ---- Componentes de lógica ----
        audio_cfg = config.get("audio", {})
        self._audio_manager = AudioManager(
            sample_rate=audio_cfg.get("sample_rate", 16000),
            chunk_size=audio_cfg.get("chunk_size", 4000),
            channels=audio_cfg.get("channels", 1),
            input_device_index=audio_cfg.get("input_device_index"),
            output_device_index=audio_cfg.get("output_device_index"),
        )
        self._command_handler = OfflineCommandHandler()

        # ---- Ventana principal ----
        self._window = MainWindow(
            event_queue=self._event_queue,
            on_listen_pressed=self._on_listen_pressed,
            on_close=self._resource_manager.shutdown,
        )

        # ---- TTS (necesita root para after()) ----
        self._tts_engine = TTSEngine(root_widget=self._window)

        # ---- STT ----
        vosk_path = Path(config.get("vosk_model_path", "models/vosk-model-small-es-0.42"))
        if vosk_path.exists():
            self._stt_engine = STTEngine(
                model_path=str(vosk_path),
                audio_manager=self._audio_manager,
                wake_words=config.get("wake_words", ["asistente"]),
                event_queue=self._event_queue,
            )
            self._stt_available = True
        else:
            self._stt_available = False

        # ---- Registrar componentes en ResourceManager ----
        self._resource_manager.register_window(self._window)
        self._resource_manager.register_components(
            audio_manager=self._audio_manager,
            stt_engine=self._stt_engine,
            tts_engine=self._tts_engine,
        )

        # ---- Mensajes de bienvenida en el chat ----
        self._window.chat_log.add_system_message(
            f"Wake words: {', '.join(config.get('wake_words', []))}"
        )

        if self._stt_available:
            self._window.chat_log.add_system_message(
                f"Modelo Vosk cargado: {vosk_path}"
            )
            # Arrancar captura de audio y STT
            self._audio_manager.start_continuous_capture()
            self._stt_engine.start()
            logger.info("AudioManager y STTEngine iniciados.")
        else:
            self._window.chat_log.add_error_message(
                f"Modelo Vosk no encontrado en '{vosk_path}'. "
                "STT deshabilitado. Descárgalo con: python scripts/download_vosk_model.py"
            )
            logger.warning("Modelo Vosk no encontrado: %s — STT deshabilitado.", vosk_path)

        # ---- Conectar el dispatcher de eventos de la ventana ----
        # Sobreescribir _dispatch_event para incluir lógica de comandos
        self._window._dispatch_event = self._dispatch_gui_event  # type: ignore[method-assign]

        # Avatar arranca en IDLE
        self._window.set_avatar_state(AvatarState.IDLE)

        logger.info("Asistonto GUI iniciado. Abriendo ventana...")
        self._window.mainloop()
        logger.info("Ventana cerrada. Sesión terminada.")

    # ------------------------------------------------------------------
    # Dispatcher de eventos (reemplaza el de MainWindow)
    # ------------------------------------------------------------------

    def _dispatch_gui_event(self, event: GUIEvent) -> None:
        """
        Procesa cada GUIEvent en el Main Thread.
        Llamado por MainWindow._poll_queue() cada 50 ms.
        """
        if event.type == EventType.WAKE_WORD:
            # Wake word detectado → avatar LISTENING
            logger.info("Evento WAKE_WORD recibido: '%s'.", event.payload)
            self._window.set_avatar_state(AvatarState.LISTENING)

        elif event.type == EventType.TRANSCRIPTION:
            # Transcripción final → mostrar en chat + procesar comando
            text = str(event.payload or "").strip()
            if text:
                logger.info("Evento TRANSCRIPTION: '%s'.", text)
                self._window.chat_log.add_user_message(text)
                self._window.set_avatar_state(AvatarState.PROCESSING)
                self._process_command(text)

        elif event.type == EventType.STATE_CHANGE and isinstance(event.payload, AvatarState):
            self._window.set_avatar_state(event.payload)

        elif event.type == EventType.ERROR and event.payload:
            self._window.chat_log.add_error_message(str(event.payload))
            self._window.set_avatar_state(AvatarState.IDLE)

        elif event.type == EventType.TTS_DONE:
            self._window.set_avatar_state(AvatarState.IDLE)

    # ------------------------------------------------------------------
    # Procesamiento de comandos
    # ------------------------------------------------------------------

    def _process_command(self, text: str) -> None:
        """
        Clasifica el texto con OfflineCommandHandler y responde.
        Siempre termina con una respuesta en el chat y TTS.
        """
        response = self._command_handler.handle(text)

        if response is None:
            response = (
                "Lo siento, no entendí ese comando. "
                "Puedo decirte la hora, contarte un chiste o abrir aplicaciones."
            )

        logger.info("Respuesta generada: '%s'.", response)
        self._window.chat_log.add_assistant_message(response)
        self._window.set_avatar_state(AvatarState.SPEAKING)

        # TTS en hilo daemon — on_done vuelve al Main Thread via after(0)
        self._tts_engine.speak(response, on_done=self._on_tts_done)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_listen_pressed(self) -> None:
        """
        Botón 'Escuchar' presionado — activa modo escucha sin wake word.
        """
        logger.info("Botón 'Escuchar' presionado.")
        self._window.set_avatar_state(AvatarState.LISTENING)

        if self._stt_available and self._stt_engine:
            # Activar modo comando directamente en el STTEngine
            self._stt_engine.trigger_listen()
        else:
            # STT no disponible — informar al usuario
            self._window.chat_log.add_error_message(
                "STT no disponible. Descarga el modelo Vosk para usar el micrófono."
            )
            self._window.set_avatar_state(AvatarState.IDLE)

    def _on_tts_done(self) -> None:
        """Callback: TTS terminó → Avatar vuelve a IDLE."""
        logger.info("TTS completado — Avatar → IDLE.")
        self._event_queue.put_nowait(GUIEvent(type=EventType.TTS_DONE))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_config(config_path: str = "config.json") -> dict:
        """Carga config.json. Si falla, retorna defaults mínimos."""
        _defaults = {
            "audio": {"sample_rate": 16000, "chunk_size": 4000, "channels": 1},
            "wake_words": ["asistente"],
            "vosk_model_path": "models/vosk-model-small-es-0.42",
        }
        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("config.json no encontrado — usando defaults.")
            return _defaults
        except json.JSONDecodeError as exc:
            logger.error("config.json malformado: %s — usando defaults.", exc)
            return _defaults

    def _register_signal_handlers(self) -> None:
        """Registra SIGTERM e SIGINT para cierre limpio."""
        def _handler(signum, frame):
            logger.info("Señal %s recibida — iniciando cierre limpio.", signum)
            self._resource_manager.shutdown()

        try:
            signal.signal(signal.SIGTERM, _handler)
            signal.signal(signal.SIGINT,  _handler)
        except (OSError, ValueError) as exc:
            logger.warning("No se pudieron registrar signal handlers: %s", exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = VoiceAssistantGUI()
    app.run()


if __name__ == "__main__":
    main()
