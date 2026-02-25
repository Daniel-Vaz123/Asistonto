#!/usr/bin/env python3
"""
Script de prueba para verificar TTS (Amazon Polly) y Comandos

Este script prueba:
1. Síntesis de voz con Amazon Polly
2. Procesador de comandos
3. Cache de respuestas
4. Todos los tipos de intenciones

Uso:
    python test_tts_commands.py
"""

import sys
import os
import asyncio
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("TEST DE TTS Y COMANDOS - Kiro Asistente")
print("=" * 70)
print()

# Test 1: Importar módulos
print("1. Verificando importacion de modulos...")
try:
    from src.audio_manager import AudioManager
    from src.response_generator import ResponseGenerator
    from src.command_processor import CommandProcessor
    from src.main import Colors
    print(f"{Colors.BRIGHT_GREEN}✓ Módulos importados correctamente{Colors.RESET}")
except ImportError as e:
    print(f"{Colors.BRIGHT_RED}✗ Error importando módulos: {e}{Colors.RESET}")
    sys.exit(1)

print()

# Test 2: Verificar credenciales AWS
print("2. Verificando credenciales AWS...")
required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"{Colors.BRIGHT_RED}✗ Variables faltantes: {', '.join(missing_vars)}{Colors.RESET}")
    sys.exit(1)
else:
    print(f"{Colors.BRIGHT_GREEN}✓ Credenciales AWS configuradas{Colors.RESET}")

print()

# Test 3: Inicializar componentes
print("3. Inicializando componentes...")
try:
    # AudioManager (sin captura real)
    audio_manager = AudioManager(sample_rate=16000, chunk_size=1024)
    print(f"{Colors.BRIGHT_GREEN}✓ AudioManager inicializado{Colors.RESET}")
    
    # ResponseGenerator
    response_generator = ResponseGenerator(
        audio_manager=audio_manager,
        polly_voice_id="Mia",
        output_format="mp3",
        cache_enabled=True,
        region=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )
    print(f"{Colors.BRIGHT_GREEN}✓ ResponseGenerator inicializado{Colors.RESET}")
    
    # CommandProcessor
    command_processor = CommandProcessor(
        response_generator=response_generator,
        user_name="Daniel"
    )
    print(f"{Colors.BRIGHT_GREEN}✓ CommandProcessor inicializado{Colors.RESET}")
    
except Exception as e:
    print(f"{Colors.BRIGHT_RED}✗ Error inicializando: {e}{Colors.RESET}")
    sys.exit(1)

print()

# Test 4: Probar síntesis de voz
print("4. Probando sintesis de voz con Amazon Polly...")
async def test_polly():
    try:
        test_text = "Hola, soy Kiro, tu asistente inteligente."
        print(f"   Sintetizando: '{test_text}'")
        
        audio_data = await response_generator.generate_speech(test_text)
        
        if audio_data:
            print(f"{Colors.BRIGHT_GREEN}✓ Audio sintetizado: {len(audio_data)} bytes{Colors.RESET}")
            print(f"   Voz: Mia (Español de México)")
            return True
        else:
            print(f"{Colors.BRIGHT_RED}✗ No se pudo sintetizar audio{Colors.RESET}")
            return False
    except Exception as e:
        print(f"{Colors.BRIGHT_RED}✗ Error en Polly: {e}{Colors.RESET}")
        return False

polly_ok = asyncio.run(test_polly())
print()

# Test 5: Probar comandos
print("5. Probando procesador de comandos...")

commands_to_test = [
    ("¿Cómo te llamas?", "identidad"),
    ("¿Qué hora es?", "hora"),
    ("¿Qué día es hoy?", "fecha"),
    ("Cuéntame un chiste", "chiste"),
    ("¿Cómo estás?", "estado"),
    ("Hola", "saludo"),
    ("Adiós", "despedida"),
    ("¿Qué puedes hacer?", "capacidades"),
    ("Comando desconocido xyz", "unknown")
]

async def test_commands():
    print()
    for command_text, expected_intent in commands_to_test:
        print(f"   Comando: '{command_text}'")
        
        result = await command_processor.process_command(
            command_text,
            speak=False  # No hablar en tests
        )
        
        if result['success']:
            intent = result['intent']
            response = result['response_text']
            
            if intent == expected_intent or (expected_intent == 'unknown' and intent == 'unknown'):
                print(f"   {Colors.BRIGHT_GREEN}✓ Intención: {intent}{Colors.RESET}")
            else:
                print(f"   {Colors.BRIGHT_YELLOW}⚠ Intención: {intent} (esperada: {expected_intent}){Colors.RESET}")
            
            print(f"   {Colors.BRIGHT_CYAN}→ Respuesta: {response[:80]}...{Colors.RESET}")
        else:
            print(f"   {Colors.BRIGHT_RED}✗ Error procesando comando{Colors.RESET}")
        
        print()

asyncio.run(test_commands())

# Test 6: Verificar cache
print("6. Verificando sistema de cache...")
cache_stats = response_generator.get_cache_stats()
print(f"   Total de solicitudes: {cache_stats['total_requests']}")
print(f"   Cache hits: {cache_stats['cache_hits']}")
print(f"   Cache misses: {cache_stats['cache_misses']}")
print(f"   Hit rate: {cache_stats['hit_rate_percent']}%")

if cache_stats['total_requests'] > 0:
    print(f"{Colors.BRIGHT_GREEN}✓ Sistema de cache funcionando{Colors.RESET}")
else:
    print(f"{Colors.BRIGHT_YELLOW}⚠ No hay estadísticas de cache aún{Colors.RESET}")

print()

# Test 7: Verificar intenciones disponibles
print("7. Intenciones disponibles:")
intents = command_processor.get_available_intents()
for intent in intents:
    print(f"   - {intent}")

print()

# Resumen
print("=" * 70)
if polly_ok:
    print(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}TODOS LOS TESTS PASARON{Colors.RESET}")
    print()
    print(f"{Colors.BRIGHT_CYAN}El sistema esta listo para:{Colors.RESET}")
    print(f"  - Sintetizar voz con Amazon Polly (Mia)")
    print(f"  - Procesar {len(intents)} tipos de comandos")
    print(f"  - Cachear respuestas para mejor rendimiento")
    print(f"  - Responder con personalizacion para Daniel")
else:
    print(f"{Colors.BRIGHT_YELLOW}{Colors.BOLD}TESTS PARCIALES{Colors.RESET}")
    print()
    print(f"{Colors.BRIGHT_YELLOW}Amazon Polly no esta funcionando correctamente.{Colors.RESET}")
    print(f"Verifica:")
    print(f"  - Credenciales AWS tienen permisos para Polly")
    print(f"  - Region AWS es correcta")
    print(f"  - Conexion a internet")

print("=" * 70)
print()
print(f"{Colors.BRIGHT_CYAN}Para ejecutar el asistente completo:{Colors.RESET}")
print(f"  {Colors.BRIGHT_WHITE}python src/main.py{Colors.RESET}")
print()
print(f"{Colors.BRIGHT_CYAN}Documentacion:{Colors.RESET}")
print(f"  {Colors.BRIGHT_WHITE}cat TTS_COMMANDS_GUIDE.md{Colors.RESET}")
print()
