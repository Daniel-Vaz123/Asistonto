"""
Script de ejemplo para probar la integración con AWS Transcribe

Este script demuestra cómo usar los módulos TranscribeStreamingClientWrapper
y CommandTranscriber para capturar y transcribir comandos de voz.

Uso:
    python examples/test_transcribe_integration.py
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio_manager import AudioManager
from src.transcribe_client import TranscribeStreamingClientWrapper
from src.command_transcriber import CommandTranscriber, CommandTranscription
from dotenv import load_dotenv
import json

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def load_config():
    """Carga la configuración del sistema"""
    config_path = Path(__file__).parent.parent / 'config.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def test_basic_transcription():
    """
    Prueba básica de transcripción de un comando de voz.
    
    Captura audio del micrófono y lo transcribe usando AWS Transcribe.
    """
    logger.info("=== Prueba de Integración con AWS Transcribe ===")
    
    # Cargar configuración
    config = load_config()
    audio_config = config['audio']
    transcribe_config = config['aws']['transcribe']
    
    # Inicializar AudioManager
    logger.info("Inicializando AudioManager...")
    audio_manager = AudioManager(
        sample_rate=audio_config['sample_rate'],
        chunk_size=audio_config['chunk_size'],
        channels=audio_config['channels']
    )
    
    # Calibrar micrófono
    logger.info("Calibrando micrófono...")
    calibration = audio_manager.calibrate_microphone(duration=2.0)
    logger.info(f"Calibración completada: {calibration}")
    
    # Inicializar cliente de AWS Transcribe
    logger.info("Inicializando cliente de AWS Transcribe...")
    transcribe_client = TranscribeStreamingClientWrapper(
        region=config['aws']['region'],
        language_code=transcribe_config['language_code'],
        sample_rate=transcribe_config['sample_rate'],
        vocabulary_name=transcribe_config.get('vocabulary_name')
    )
    
    # Inicializar CommandTranscriber
    logger.info("Inicializando CommandTranscriber...")
    command_transcriber = CommandTranscriber(
        audio_manager=audio_manager,
        transcribe_client=transcribe_client,
        silence_threshold=1.5,
        max_command_duration=10.0
    )
    
    # Configurar callbacks
    def on_partial(text: str):
        logger.info(f"[PARCIAL] {text}")
    
    def on_final(transcription: CommandTranscription):
        logger.info(f"[FINAL] {transcription.text}")
        logger.info(f"  Confianza: {transcription.confidence:.2f}")
        logger.info(f"  Duración: {transcription.duration:.2f}s")
        logger.info(f"  Idioma: {transcription.language_code}")
    
    def on_error(error: Exception):
        logger.error(f"[ERROR] {error}")
    
    command_transcriber.set_callbacks(
        on_partial=on_partial,
        on_final=on_final,
        on_error=on_error
    )
    
    try:
        # Iniciar captura continua de audio
        logger.info("Iniciando captura de audio...")
        audio_manager.start_continuous_capture()
        
        # Capturar y transcribir comando
        logger.info("\n" + "="*60)
        logger.info("¡Habla ahora! Di un comando en español...")
        logger.info("El sistema detectará automáticamente cuando termines de hablar")
        logger.info("="*60 + "\n")
        
        result = await command_transcriber.capture_command()
        
        if result:
            logger.info("\n" + "="*60)
            logger.info("RESULTADO FINAL:")
            logger.info(f"  Texto: {result.text}")
            logger.info(f"  Confianza: {result.confidence:.2%}")
            logger.info(f"  Duración: {result.duration:.2f}s")
            logger.info(f"  Idioma: {result.language_code}")
            logger.info(f"  Transcripciones parciales: {len(result.partial_transcriptions)}")
            logger.info("="*60)
        else:
            logger.warning("No se obtuvo transcripción del comando")
        
    except KeyboardInterrupt:
        logger.info("\nPrueba interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error durante la prueba: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Limpiando recursos...")
        audio_manager.stop_continuous_capture()
        audio_manager.cleanup()
        logger.info("Prueba finalizada")


async def test_multiple_commands():
    """
    Prueba de captura de múltiples comandos consecutivos.
    """
    logger.info("=== Prueba de Múltiples Comandos ===")
    
    config = load_config()
    audio_config = config['audio']
    transcribe_config = config['aws']['transcribe']
    
    # Inicializar componentes
    audio_manager = AudioManager(
        sample_rate=audio_config['sample_rate'],
        chunk_size=audio_config['chunk_size'],
        channels=audio_config['channels']
    )
    
    audio_manager.calibrate_microphone(duration=2.0)
    
    transcribe_client = TranscribeStreamingClientWrapper(
        region=config['aws']['region'],
        language_code=transcribe_config['language_code'],
        sample_rate=transcribe_config['sample_rate']
    )
    
    command_transcriber = CommandTranscriber(
        audio_manager=audio_manager,
        transcribe_client=transcribe_client
    )
    
    try:
        audio_manager.start_continuous_capture()
        
        # Capturar 3 comandos
        for i in range(3):
            logger.info(f"\n{'='*60}")
            logger.info(f"Comando {i+1}/3 - ¡Habla ahora!")
            logger.info(f"{'='*60}\n")
            
            result = await command_transcriber.capture_command()
            
            if result:
                logger.info(f"✓ Comando {i+1}: '{result.text}' (confianza: {result.confidence:.2%})")
            else:
                logger.warning(f"✗ Comando {i+1}: No se obtuvo transcripción")
            
            # Pausa entre comandos
            if i < 2:
                logger.info("Esperando 2 segundos antes del siguiente comando...")
                await asyncio.sleep(2)
        
        logger.info("\n" + "="*60)
        logger.info("Prueba de múltiples comandos completada")
        logger.info("="*60)
        
    except KeyboardInterrupt:
        logger.info("\nPrueba interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error durante la prueba: {e}", exc_info=True)
    finally:
        audio_manager.stop_continuous_capture()
        audio_manager.cleanup()


def main():
    """Función principal"""
    # Verificar credenciales AWS
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Variables de entorno faltantes: {', '.join(missing_vars)}")
        logger.error("Por favor configura el archivo .env con tus credenciales de AWS")
        sys.exit(1)
    
    # Menú de opciones
    print("\n" + "="*60)
    print("Pruebas de Integración con AWS Transcribe")
    print("="*60)
    print("1. Prueba básica (un comando)")
    print("2. Prueba de múltiples comandos (3 comandos)")
    print("0. Salir")
    print("="*60)
    
    choice = input("\nSelecciona una opción: ").strip()
    
    if choice == "1":
        asyncio.run(test_basic_transcription())
    elif choice == "2":
        asyncio.run(test_multiple_commands())
    elif choice == "0":
        logger.info("Saliendo...")
    else:
        logger.error("Opción inválida")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nPrograma interrumpido por el usuario")
        sys.exit(0)
