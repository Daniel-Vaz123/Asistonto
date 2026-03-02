"""
Punto de entrada principal del Asistente de Voz "Kiro".

Orquesta los componentes: captura de audio (PyAudio), detección de wake word,
transcripción con Vosk (offline), procesamiento de comandos (regex + DeepSeek),
y respuesta hablada con Amazon Polly.

Flujo: captura continua → wake word → comando por voz → procesamiento → respuesta hablada.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from src.audio_manager import AudioManager
from src.wake_word_detector import WakeWordDetector, WakeWordDetection
from src.command_transcriber import CommandTranscriber, CommandTranscription
from src.response_generator import ResponseGenerator
from src.command_processor import CommandProcessor
from src.feedback_preventer import FeedbackPreventer

# Cargar variables de entorno
load_dotenv()


def verify_phase2_dependencies():
    """Verifica que las dependencias de Fase 2 estén instaladas"""
    try:
        import duckduckgo_search
    except ImportError:
        print("ERROR: duckduckgo-search no está instalado")
        print("Instala con: pip install duckduckgo-search>=4.0.0")
        sys.exit(1)
    
    try:
        import rich
    except ImportError:
        print("ERROR: rich no está instalado")
        print("Instala con: pip install rich>=13.0.0")
        sys.exit(1)
    
    print("✓ Dependencias de Fase 2 verificadas")


# Verificar dependencias al inicio
verify_phase2_dependencies()

# Asegurar que existe la carpeta de logs (para ejecución en PC o Raspberry)
Path('logs').mkdir(parents=True, exist_ok=True)

# Configurar logging
log_level = os.getenv('VOICE_ASSISTANT_LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/voice_assistant.log'),
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# CÓDIGOS ANSI PARA COLORES EN CONSOLA
# ============================================================================

class Colors:
    """Códigos ANSI para colores en terminal"""
    # Colores básicos
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Colores de texto
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Colores brillantes
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Colores de fondo
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'


def print_banner():
    """Imprime el banner ASCII de inicio del sistema"""
    banner = f"""
{Colors.BRIGHT_CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     █████╗ ███████╗██╗███████╗████████╗███████╗███╗   ██╗████████╗║
║    ██╔══██╗██╔════╝██║██╔════╝╚══██╔══╝██╔════╝████╗  ██║╚══██╔══╝║
║    ███████║███████╗██║███████╗   ██║   █████╗  ██╔██╗ ██║   ██║   ║
║    ██╔══██║╚════██║██║╚════██║   ██║   ██╔══╝  ██║╚██╗██║   ██║   ║
║    ██║  ██║███████║██║███████║   ██║   ███████╗██║ ╚████║   ██║   ║
║    ╚═╝  ╚═╝╚══════╝╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝   ╚═╝   ║
║                                                                   ║
║              🎤 Asistente de Voz (estilo Alexa) 🎤               ║
║                                                                   ║
║                    Powered by AWS Transcribe                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
{Colors.RESET}
{Colors.BRIGHT_WHITE}Versión: 1.0.0 MVP
Plataforma: PC / Raspberry Pi
Idioma: Español (es-MX / es-ES)
{Colors.RESET}
"""
    print(banner)


def print_status(message: str, status: str = "info"):
    """
    Imprime un mensaje de estado con color.
    
    Args:
        message: Mensaje a imprimir
        status: Tipo de estado (info, success, warning, error, processing, wake_word, transcription)
    """
    timestamp = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
    
    if status == "success":
        print(f"{Colors.BRIGHT_GREEN}✓ {message}{Colors.RESET}")
    elif status == "error":
        print(f"{Colors.BRIGHT_RED}✗ {message}{Colors.RESET}")
    elif status == "warning":
        print(f"{Colors.BRIGHT_YELLOW}⚠ {message}{Colors.RESET}")
    elif status == "processing":
        print(f"{Colors.YELLOW}⏳ {message}{Colors.RESET}")
    elif status == "wake_word":
        print(f"\n{Colors.BRIGHT_GREEN}{Colors.BOLD}🎤 {message}{Colors.RESET}\n")
    elif status == "transcription":
        print(f"{Colors.BRIGHT_CYAN}💬 {message}{Colors.RESET}")
    else:
        print(f"{Colors.BRIGHT_WHITE}ℹ {message}{Colors.RESET}")


def load_config(config_path: str = 'config.json') -> dict:
    """Carga la configuración desde el archivo JSON"""
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            print_status(f"Archivo de configuración no encontrado: {config_path}", "error")
            sys.exit(1)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print_status("Configuración cargada exitosamente", "success")
        return config
    except Exception as e:
        print_status(f"Error al cargar configuración: {e}", "error")
        sys.exit(1)


def validate_aws_credentials() -> bool:
    """Valida que las credenciales de AWS estén configuradas"""
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print_status(f"Variables de entorno faltantes: {', '.join(missing_vars)}", "error")
        print_status("Por favor configura el archivo .env con tus credenciales de AWS", "warning")
        print_status("Ejemplo: AWS_ACCESS_KEY_ID=tu_access_key", "info")
        return False
    
    print_status("Credenciales de AWS validadas", "success")
    return True


class VoiceAssistantMVP:
    """
    Clase principal del MVP del Asistente de Voz.
    
    Orquesta todos los componentes del sistema para proporcionar
    funcionalidad básica de detección de wake word y transcripción.
    """
    
    def __init__(self, config: dict):
        """
        Inicializa el asistente de voz.
        
        Args:
            config: Diccionario de configuración del sistema
        """
        self.config = config
        self.audio_manager: Optional[AudioManager] = None
        self.transcribe_client: Optional[TranscribeStreamingClientWrapper] = None
        self.wake_word_detector: Optional[WakeWordDetector] = None
        self.command_transcriber: Optional[CommandTranscriber] = None
        self.response_generator: Optional[ResponseGenerator] = None
        self.command_processor: Optional[CommandProcessor] = None
        self.feedback_preventer: Optional[FeedbackPreventer] = None  # Phase 3: Auto-Mute
        self._is_running = False
        
    async def initialize(self):
        """Inicializa todos los componentes del sistema"""
        print_status("Inicializando componentes del sistema...", "processing")
        
        # Phase 2: Mostrar banner de RichUI
        from src.rich_ui_manager import RichUIManager
        from src.models import SystemState
        ui_manager = RichUIManager()
        ui_manager.show_banner()
        
        # Phase 3: Inicializar FeedbackPreventer (Auto-Mute)
        print_status("Inicializando prevención de feedback...", "info")
        self.feedback_preventer = FeedbackPreventer()
        
        # 1. Inicializar AudioManager
        print_status("Inicializando AudioManager...", "info")
        audio_config = self.config['audio']
        self.audio_manager = AudioManager(
            sample_rate=audio_config['sample_rate'],
            chunk_size=audio_config['chunk_size'],
            channels=audio_config['channels'],
            input_device_index=audio_config.get('input_device_index'),
            output_device_index=audio_config.get('output_device_index')
        )
        
        # 2. Calibrar micrófono y verificar dispositivo
        print_status("Calibrando micrófono (mantén silencio)...", "processing")
        try:
            calibration = self.audio_manager.calibrate_microphone(duration=2.0)
            dev_info = calibration.get("device_info", {})
            mic_name = dev_info.get("name", "Desconocido")
            print_status(
                f"Micrófono calibrado - Nivel de ruido: {calibration['noise_level']:.2f}",
                "success"
            )
            print_status(f"Dispositivo de entrada: {mic_name}", "info")
            # Listar dispositivos de entrada por si hay que cambiar en config.json (audio.input_device_index)
            try:
                devices = self.audio_manager.list_audio_devices()
                inputs = [d for d in devices if (d.get("max_input_channels") or 0) >= 1]
                if len(inputs) > 1:
                    print_status("Otros micrófonos disponibles (config.json → audio.input_device_index):", "info")
                    for d in inputs[:5]:
                        print(f"    [{d['index']}] {d.get('name', '?')}")
            except Exception:
                pass
        except Exception as e:
            print_status(f"Error al calibrar micrófono: {e}", "error")
            raise
        
        # 3. Inicializar ResponseGenerator (Amazon Polly)
        print_status("Inicializando generador de respuestas (Amazon Polly)...", "info")
        polly_config = self.config['aws']['polly']
        self.response_generator = ResponseGenerator(
            audio_manager=self.audio_manager,
            polly_voice_id=polly_config['voice_id'],
            output_format=polly_config['output_format'],
            sample_rate=polly_config['sample_rate'],
            cache_enabled=self.config['features']['voice_cache_enabled'],
            region=self.config['aws']['region'],
            feedback_preventer=self.feedback_preventer,  # Phase 3: Pasar FeedbackPreventer
            volume_gain=float(polly_config.get('volume_gain', 3.0)),
        )
        
        # 4. Inicializar CommandProcessor
        print_status("Inicializando procesador de comandos...", "info")
        user_name = self.config.get('user_name') or os.getenv('VOICE_ASSISTANT_USER_NAME', 'Usuario')
        self.command_processor = CommandProcessor(
            response_generator=self.response_generator,
            user_name=user_name,
            web_search_enabled=True  # Phase 2: Habilitar búsqueda web
        )
        
        # 5. Inicializar cliente de transcripción (AWS, Google o Vosk local)
        transcribe_provider = (self.config.get("transcribe_provider") or "vosk").lower()
        if transcribe_provider == "vosk":
            print_status("Inicializando transcripción local (Vosk)...", "info")
            from src.transcribe_client_vosk import VoskTranscribeStreamingWrapper
            vosk_cfg = self.config.get("vosk") or {}
            self.transcribe_client = VoskTranscribeStreamingWrapper(
                model_path=vosk_cfg.get("model_path", "model/vosk-model-small-es-0.42"),
                sample_rate=int(vosk_cfg.get("sample_rate", 16000)),
                buffer_ms=float(vosk_cfg.get("buffer_ms", 300)),
            )
        else:
            # FUTURA IMPLEMENTACIÓN — AWS Transcribe (ver MIGRACION_AWS.md)
            print_status("Inicializando cliente de AWS Transcribe...", "info")
            from src.transcribe_client import TranscribeStreamingClientWrapper
            transcribe_config = self.config['aws']['transcribe']
            self.transcribe_client = TranscribeStreamingClientWrapper(
                region=self.config['aws']['region'],
                language_code=transcribe_config['language_code'],
                sample_rate=transcribe_config['sample_rate'],
                vocabulary_name=transcribe_config.get('vocabulary_name')
            )
        
        # 6. Inicializar WakeWordDetector
        print_status("Inicializando detector de wake words...", "info")
        wake_words = self.config['wake_words']
        self.wake_word_detector = WakeWordDetector(
            wake_words=wake_words,
            audio_manager=self.audio_manager,
            transcribe_client=self.transcribe_client,
            confidence_threshold=0.7,
            feedback_preventer=self.feedback_preventer  # Phase 3: Pasar FeedbackPreventer
        )
        
        # Registrar callbacks
        self.wake_word_detector.on_wake_word_detected(self._on_wake_word_detected)
        self.wake_word_detector.on_hearing(self._on_hearing)
        
        # 7. Inicializar CommandTranscriber
        print_status("Inicializando transcriptor de comandos...", "info")
        self.command_transcriber = CommandTranscriber(
            audio_manager=self.audio_manager,
            transcribe_client=self.transcribe_client,
            silence_threshold=1.5,
            max_command_duration=10.0,
            feedback_preventer=self.feedback_preventer  # Phase 3: Pasar FeedbackPreventer
        )
        
        # Configurar callbacks para transcripción
        self.command_transcriber.set_callbacks(
            on_partial=self._on_partial_transcription,
            on_final=self._on_final_transcription,
            on_error=self._on_transcription_error
        )
        
        # 8. Inicializar TranscriptionFilter
        print_status("Inicializando filtro de transcripciones...", "info")
        from src.transcription_filter import TranscriptionFilter
        wake_words = self.config['wake_words']
        self.transcription_filter = TranscriptionFilter(
            wake_words=wake_words,
            min_words=2,
            min_chars=4
        )
        
        print_status("Sistema inicializado correctamente", "success")
        
        # Mostrar estadísticas de cache
        cache_stats = self.response_generator.get_cache_stats()
        print_status(
            f"Cache de voz: {cache_stats['total_requests']} solicitudes, "
            f"{cache_stats['hit_rate_percent']}% hit rate",
            "info"
        )
    
    async def start(self):
        """Inicia el asistente de voz"""
        self._is_running = True
        
        print_status("Iniciando captura de audio...", "processing")
        self.audio_manager.start_continuous_capture()
        await asyncio.sleep(0.5)  # Dar tiempo para que el buffer se llene
        # Comprobar que el micrófono capta (ayuda a detectar si no hay voz)
        try:
            chunks = self.audio_manager.get_audio_buffer(num_chunks=32)
            if chunks:
                import numpy as np
                raw = b"".join(chunks)
                arr = np.frombuffer(raw, dtype=np.int16)
                rms = float(np.sqrt(np.mean(arr.astype(np.float32) ** 2)))
                if rms < 200:
                    print_status("Nivel de micrófono bajo. Sube el volumen del mic en Windows o acércate.", "warning")
                else:
                    print_status(f"Nivel de micrófono OK (RMS ≈ {rms:.0f})", "info")
            else:
                print_status("No se recibió audio. Comprueba el dispositivo de entrada.", "warning")
        except Exception as e:
            logger.debug("Comprobación de micrófono omitida: %s", e)
        print()
        ww = self.config['wake_words'][0].upper()
        print(f"{Colors.BRIGHT_WHITE}  {'='*60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}  🎤 SISTEMA LISTO — Di '{ww}' para activarme{Colors.RESET}")
        print(f"{Colors.BRIGHT_BLACK}     Verás lo que escucho en gris. Cuando diga '{ww}'{Colors.RESET}")
        print(f"{Colors.BRIGHT_BLACK}     pasaré a modo comando y responderé.{Colors.RESET}")
        print(f"{Colors.BRIGHT_WHITE}  {'='*60}{Colors.RESET}")
        print()
        
        # Iniciar detección de wake words (esto corre indefinidamente)
        await self.wake_word_detector.start_detection()
    
    async def stop(self):
        """Detiene el asistente de voz"""
        self._is_running = False
        
        print_status("Deteniendo sistema...", "processing")
        
        if self.wake_word_detector:
            await self.wake_word_detector.stop_detection()
        
        # Phase 2: Cleanup de threading
        if self.command_processor and hasattr(self.command_processor, 'threading_manager'):
            self.command_processor.threading_manager.shutdown()
        
        if self.audio_manager:
            self.audio_manager.stop_continuous_capture()
            self.audio_manager.cleanup()
        
        print_status("Sistema detenido correctamente", "success")
    
    # ------------------------------------------------------------------
    # Callbacks: flujo tipo Alexa
    # ------------------------------------------------------------------

    def _on_hearing(self, text: str, is_partial: bool):
        """Muestra en consola lo que se escucha mientras espera el wake word."""
        if is_partial:
            label = f"{Colors.BRIGHT_BLACK}  🎤 {text}{Colors.RESET}"
            print(f"\r{label}", end="", flush=True)
        else:
            ww_hint = self.config['wake_words'][0]
            label = f"{Colors.YELLOW}  > {text}  {Colors.BRIGHT_BLACK}(di '{ww_hint}' para activar){Colors.RESET}"
            print(f"\r{label}")

    def _on_wake_word_detected(self, detection: WakeWordDetection):
        """Wake word detectado → escuchar comando → responder → volver a escuchar."""
        print("\r" + " " * 80, end="\r")
        print()
        print(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}  ✦  WAKE WORD: '{detection.wake_word.upper()}' detectado{Colors.RESET}")

        if detection.inline_command:
            # El usuario dijo "asistente qué hora es" de corrido → procesar directamente
            print(f"{Colors.BRIGHT_CYAN}  ➤  Comando detectado en la misma frase{Colors.RESET}")
            print()
            return asyncio.create_task(self._process_inline_command(detection.inline_command))
        else:
            # Solo dijo "asistente" → escuchar comando aparte
            print(f"{Colors.BRIGHT_CYAN}  ➤  Te escucho, di tu comando...{Colors.RESET}")
            print()
            return asyncio.create_task(self._capture_command())

    async def _process_inline_command(self, command_text: str):
            """Procesa un comando que vino pegado al wake word (ej. 'asistente qué hora es')."""
            try:
                # Aplicar filtro de transcripción también a comandos inline
                filtered_text = self.transcription_filter.filter(command_text)

                if filtered_text is None:
                    # Comando inline rechazado por el filtro
                    logger.debug("Inline command rejected by filter, returning to listening state")
                    print()
                    print(f"{Colors.BRIGHT_BLACK}  {'─'*60}{Colors.RESET}")
                    ww = self.config['wake_words'][0].upper()
                    print(f"{Colors.BRIGHT_GREEN}  🎤 Escuchando... di '{ww}' para activarme{Colors.RESET}")
                    print()
                    return

                # Mostrar texto filtrado (sin wake word)
                print(f"{Colors.BRIGHT_WHITE}  💬 Tú dijiste: \"{filtered_text}\"{Colors.RESET}")
                print()

                # Procesar comando con texto filtrado
                command_result = await self.command_processor.process_command(filtered_text, speak=True)

                if command_result['success']:
                    print(f"{Colors.BRIGHT_CYAN}  🤖 Kiro: {command_result['response_text']}{Colors.RESET}")
                    if command_result.get('spoken'):
                        print(f"{Colors.BRIGHT_BLACK}     (hablado con Polly){Colors.RESET}")
                else:
                    print(f"{Colors.BRIGHT_RED}  ✗ No pude procesar el comando.{Colors.RESET}")
            except Exception as e:
                print_status(f"Error procesando comando: {e}", "error")
                logger.error("Error en _process_inline_command: %s", e, exc_info=True)
            print()
            print(f"{Colors.BRIGHT_BLACK}  {'─'*60}{Colors.RESET}")
            ww = self.config['wake_words'][0].upper()
            print(f"{Colors.BRIGHT_GREEN}  🎤 Escuchando... di '{ww}' para activarme{Colors.RESET}")
            print()



    async def _capture_command(self):
        """Captura comando, lo procesa y responde."""
        try:
            result = await self.command_transcriber.capture_command()

            # Limpiar línea parcial
            print("\r" + " " * 80, end="\r")

            if result and result.text.strip():
                # Aplicar filtro de transcripción
                filtered_text = self.transcription_filter.filter(result.text)
                
                if filtered_text is None:
                    # Transcripción rechazada, volver a escuchar silenciosamente
                    logger.debug("Transcription rejected by filter, returning to listening state")
                    print()
                    print(f"{Colors.BRIGHT_BLACK}  {'─'*60}{Colors.RESET}")
                    ww = self.config['wake_words'][0].upper()
                    print(f"{Colors.BRIGHT_GREEN}  🎤 Escuchando... di '{ww}' para activarme{Colors.RESET}")
                    print()
                    return
                
                # Mostrar texto filtrado (sin wake word)
                print(f"{Colors.BRIGHT_WHITE}  💬 Tú dijiste: \"{filtered_text}\"{Colors.RESET}")
                print()

                command_result = await self.command_processor.process_command(
                    filtered_text, speak=True
                )

                if command_result['success']:
                    response = command_result['response_text']
                    print(f"{Colors.BRIGHT_CYAN}  🤖 Kiro: {response}{Colors.RESET}")
                    if command_result.get('spoken'):
                        print(f"{Colors.BRIGHT_BLACK}     (hablado con Polly){Colors.RESET}")
                    else:
                        print(f"{Colors.BRIGHT_YELLOW}     (solo texto){Colors.RESET}")
                else:
                    print(f"{Colors.BRIGHT_RED}  ✗ No pude procesar el comando.{Colors.RESET}")
            else:
                print(f"{Colors.BRIGHT_YELLOW}  ⚠ No escuché ningún comando.{Colors.RESET}")

            # Separador y volver a escuchar
            print()
            print(f"{Colors.BRIGHT_BLACK}  {'─'*60}{Colors.RESET}")
            ww = self.config['wake_words'][0].upper()
            print(f"{Colors.BRIGHT_GREEN}  🎤 Escuchando... di '{ww}' para activarme{Colors.RESET}")
            print()

        except Exception as e:
            print_status(f"Error capturando comando: {e}", "error")
            logger.error("Error en _capture_command: %s", e, exc_info=True)

    def _on_partial_transcription(self, text: str):
        """Muestra transcripción parcial del comando en tiempo real."""
        print(f"\r{Colors.YELLOW}  ⏳ {text}...{Colors.RESET}", end="", flush=True)

    def _on_final_transcription(self, transcription: CommandTranscription):
        """Limpia la línea parcial."""
        print("\r" + " " * 80, end="\r")

    def _on_transcription_error(self, error: Exception):
        """Error de transcripción."""
        print_status(f"Error de transcripción: {error}", "error")


async def main():
    """Función principal del asistente de voz"""
    # Imprimir banner
    print_banner()
    
    print_status("Iniciando Asistente de Voz", "info")
    print()
    
    # Validar credenciales
    if not validate_aws_credentials():
        sys.exit(1)
    
    # Cargar configuración
    config_path = os.getenv('VOICE_ASSISTANT_CONFIG_PATH', 'config.json')
    config = load_config(config_path)
    
    # Crear instancia del asistente
    assistant = VoiceAssistantMVP(config)
    
    try:
        # Inicializar componentes
        await assistant.initialize()
        
        print()
        print_status("¡Sistema listo para usar!", "success")
        print()
        
        # Iniciar asistente
        await assistant.start()
        
    except KeyboardInterrupt:
        print()
        print_status("Deteniendo asistente de voz...", "warning")
    except Exception as e:
        print_status(f"Error en el sistema: {e}", "error")
        logger.error(f"Error fatal: {e}", exc_info=True)
    finally:
        # Cleanup de recursos
        await assistant.stop()
        print()
        print_status("¡Hasta luego! 👋", "info")
        print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print(f"{Colors.BRIGHT_YELLOW}Programa interrumpido por el usuario{Colors.RESET}")
        sys.exit(0)

