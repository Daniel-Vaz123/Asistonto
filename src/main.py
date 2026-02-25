"""
Punto de entrada principal del Asistente de Voz para Raspberry Pi

Este script orquesta todos los componentes del sistema para crear
un asistente de voz funcional con detección de wake word y transcripción
en tiempo real usando AWS Transcribe.

Flujo del MVP:
1. Captura de audio continua desde el micrófono
2. Detección de wake word "Asistente" 
3. Streaming a AWS Transcribe
4. Salida de texto transcrito en consola con colores

Autor: VoiceAssistantBot Team
Plataforma: Raspberry Pi 4
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Importar componentes del sistema
from src.audio_manager import AudioManager
from src.transcribe_client import TranscribeStreamingClientWrapper
from src.wake_word_detector import WakeWordDetector, WakeWordDetection
from src.command_transcriber import CommandTranscriber, CommandTranscription
from src.response_generator import ResponseGenerator
from src.command_processor import CommandProcessor

# Cargar variables de entorno
load_dotenv()

# Configurar logging
log_level = os.getenv('VOICE_ASSISTANT_LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/voice_assistant.log'),
        logging.StreamHandler(sys.stdout)
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
║              🎤 Asistente de Voz para Raspberry Pi 🎤             ║
║                                                                   ║
║                    Powered by AWS Transcribe                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
{Colors.RESET}
{Colors.BRIGHT_WHITE}Versión: 1.0.0 MVP
Plataforma: Raspberry Pi 4
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
        self._is_running = False
        
    async def initialize(self):
        """Inicializa todos los componentes del sistema"""
        print_status("Inicializando componentes del sistema...", "processing")
        
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
        
        # 2. Calibrar micrófono
        print_status("Calibrando micrófono (mantén silencio)...", "processing")
        try:
            calibration = self.audio_manager.calibrate_microphone(duration=2.0)
            print_status(
                f"Micrófono calibrado - Nivel de ruido: {calibration['noise_level']:.2f}",
                "success"
            )
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
            region=self.config['aws']['region']
        )
        
        # 4. Inicializar CommandProcessor
        print_status("Inicializando procesador de comandos...", "info")
        self.command_processor = CommandProcessor(
            response_generator=self.response_generator,
            user_name="Daniel"  # Personalización para Daniel
        )
        
        # 5. Inicializar cliente de AWS Transcribe
        print_status("Inicializando cliente de AWS Transcribe...", "info")
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
            confidence_threshold=0.7
        )
        
        # Registrar callback para wake word detectado
        self.wake_word_detector.on_wake_word_detected(self._on_wake_word_detected)
        
        # 7. Inicializar CommandTranscriber
        print_status("Inicializando transcriptor de comandos...", "info")
        self.command_transcriber = CommandTranscriber(
            audio_manager=self.audio_manager,
            transcribe_client=self.transcribe_client,
            silence_threshold=1.5,
            max_command_duration=10.0
        )
        
        # Configurar callbacks para transcripción
        self.command_transcriber.set_callbacks(
            on_partial=self._on_partial_transcription,
            on_final=self._on_final_transcription,
            on_error=self._on_transcription_error
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
        
        print_status("Iniciando detección de wake words...", "processing")
        print()
        print(f"{Colors.BRIGHT_WHITE}{'='*70}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}🎤 SISTEMA LISTO - Di '{self.config['wake_words'][0].upper()}' para activar{Colors.RESET}")
        print(f"{Colors.BRIGHT_WHITE}{'='*70}{Colors.RESET}")
        print()
        
        # Iniciar detección de wake words (esto corre indefinidamente)
        await self.wake_word_detector.start_detection()
    
    async def stop(self):
        """Detiene el asistente de voz"""
        self._is_running = False
        
        print_status("Deteniendo sistema...", "processing")
        
        if self.wake_word_detector:
            await self.wake_word_detector.stop_detection()
        
        if self.audio_manager:
            self.audio_manager.stop_continuous_capture()
            self.audio_manager.cleanup()
        
        print_status("Sistema detenido correctamente", "success")
    
    def _on_wake_word_detected(self, detection: WakeWordDetection):
        """
        Callback cuando se detecta un wake word.
        
        Args:
            detection: Información de la detección
        """
        print_status(
            f"WAKE WORD DETECTADO: '{detection.wake_word.upper()}' "
            f"(confianza: {detection.confidence:.0%})",
            "wake_word"
        )
        
        # Capturar comando después del wake word
        print_status("Escuchando comando...", "processing")
        asyncio.create_task(self._capture_command())
    
    async def _capture_command(self):
        """Captura y transcribe un comando después del wake word"""
        try:
            # Capturar comando
            result = await self.command_transcriber.capture_command()
            
            if result:
                # Comando transcrito exitosamente
                print()
                print(f"{Colors.BRIGHT_WHITE}{'='*70}{Colors.RESET}")
                print_status(
                    f"COMANDO TRANSCRITO: \"{result.text}\"",
                    "transcription"
                )
                print(f"{Colors.BRIGHT_WHITE}  Confianza: {result.confidence:.0%}{Colors.RESET}")
                print(f"{Colors.BRIGHT_WHITE}  Duración: {result.duration:.1f}s{Colors.RESET}")
                print(f"{Colors.BRIGHT_WHITE}  Idioma: {result.language_code or 'es-ES'}{Colors.RESET}")
                print(f"{Colors.BRIGHT_WHITE}{'='*70}{Colors.RESET}")
                print()
                
                # Procesar comando con el CommandProcessor
                print_status("Procesando comando...", "processing")
                command_result = await self.command_processor.process_command(
                    result.text,
                    speak=True  # Hablar la respuesta
                )
                
                if command_result['success']:
                    # Mostrar respuesta en consola con formato elegante tipo banner
                    print()
                    print(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}╔{'═'*68}╗{Colors.RESET}")
                    print(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}║{' '*68}║{Colors.RESET}")
                    print(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}║  🤖 KIRO RESPONDE:{' '*50}║{Colors.RESET}")
                    print(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}║{' '*68}║{Colors.RESET}")
                    
                    # Dividir respuesta en líneas si es muy larga
                    response_text = command_result['response_text']
                    max_width = 64
                    words = response_text.split()
                    lines = []
                    current_line = ""
                    
                    for word in words:
                        if len(current_line) + len(word) + 1 <= max_width:
                            current_line += (word + " ")
                        else:
                            lines.append(current_line.strip())
                            current_line = word + " "
                    if current_line:
                        lines.append(current_line.strip())
                    
                    # Imprimir cada línea centrada en el banner
                    for line in lines:
                        padding = (64 - len(line)) // 2
                        print(f"{Colors.BRIGHT_WHITE}║  {' '*padding}{line}{' '*(64-len(line)-padding)}  ║{Colors.RESET}")
                    
                    print(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}║{' '*68}║{Colors.RESET}")
                    
                    if command_result['spoken']:
                        print(f"{Colors.BRIGHT_GREEN}║  🔊 Respuesta hablada con Amazon Polly (Voz: Mia){' '*20}║{Colors.RESET}")
                    else:
                        print(f"{Colors.BRIGHT_YELLOW}║  ⚠ Solo texto (error en síntesis de voz){' '*27}║{Colors.RESET}")
                    
                    print(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}║{' '*68}║{Colors.RESET}")
                    print(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}╚{'═'*68}╝{Colors.RESET}")
                    print()
                else:
                    print_status("Error procesando comando", "error")
                
                # Volver a escuchar wake word
                print_status(
                    f"Esperando wake word '{self.config['wake_words'][0]}'...",
                    "info"
                )
            else:
                print_status("No se pudo transcribir el comando", "warning")
                print_status(
                    f"Esperando wake word '{self.config['wake_words'][0]}'...",
                    "info"
                )
                
        except Exception as e:
            print_status(f"Error capturando comando: {e}", "error")
            logger.error(f"Error en _capture_command: {e}", exc_info=True)
    
    def _on_partial_transcription(self, text: str):
        """
        Callback para transcripciones parciales.
        
        Args:
            text: Texto transcrito parcialmente
        """
        # Mostrar transcripción parcial en tiempo real
        print(f"{Colors.YELLOW}  ⏳ {text}...{Colors.RESET}", end='\r')
    
    def _on_final_transcription(self, transcription: CommandTranscription):
        """
        Callback para transcripción final.
        
        Args:
            transcription: Resultado de transcripción completo
        """
        # Limpiar línea de transcripción parcial
        print(" " * 100, end='\r')
    
    def _on_transcription_error(self, error: Exception):
        """
        Callback para errores de transcripción.
        
        Args:
            error: Excepción ocurrida
        """
        print_status(f"Error de transcripción: {error}", "error")


async def main():
    """Función principal del asistente de voz"""
    # Imprimir banner
    print_banner()
    
    print_status("Iniciando Asistente de Voz para Raspberry Pi", "info")
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

