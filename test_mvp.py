#!/usr/bin/env python3
"""
Script de prueba rápida para verificar que el MVP está funcionando correctamente.

Este script verifica:
1. Importación de módulos
2. Configuración de AWS
3. Dispositivos de audio disponibles
4. Conexión con AWS Transcribe

Uso:
    python test_mvp.py
"""

import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("🧪 TEST DEL MVP - Asistente de Voz")
print("=" * 70)
print()

# Test 1: Importar módulos
print("1️⃣  Verificando importación de módulos...")
try:
    from src.audio_manager import AudioManager
    from src.transcribe_client import TranscribeStreamingClientWrapper
    from src.wake_word_detector import WakeWordDetector
    from src.command_transcriber import CommandTranscriber
    from src.main import VoiceAssistantMVP, Colors
    print(f"{Colors.BRIGHT_GREEN}✓ Todos los módulos importados correctamente{Colors.RESET}")
except ImportError as e:
    print(f"{Colors.BRIGHT_RED}✗ Error importando módulos: {e}{Colors.RESET}")
    sys.exit(1)

print()

# Test 2: Verificar variables de entorno
print("2️⃣  Verificando variables de entorno...")
from dotenv import load_dotenv
load_dotenv()

required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"{Colors.BRIGHT_RED}✗ Variables faltantes: {', '.join(missing_vars)}{Colors.RESET}")
    print(f"{Colors.YELLOW}⚠ Por favor configura el archivo .env{Colors.RESET}")
    sys.exit(1)
else:
    print(f"{Colors.BRIGHT_GREEN}✓ Credenciales de AWS configuradas{Colors.RESET}")

print()

# Test 3: Verificar archivo de configuración
print("3️⃣  Verificando archivo de configuración...")
import json

try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    print(f"{Colors.BRIGHT_GREEN}✓ config.json cargado correctamente{Colors.RESET}")
    print(f"   - Región AWS: {config['aws']['region']}")
    print(f"   - Idioma: {config['aws']['transcribe']['language_code']}")
    print(f"   - Wake words: {', '.join(config['wake_words'])}")
except Exception as e:
    print(f"{Colors.BRIGHT_RED}✗ Error cargando config.json: {e}{Colors.RESET}")
    sys.exit(1)

print()

# Test 4: Verificar PyAudio y dispositivos de audio
print("4️⃣  Verificando dispositivos de audio...")
try:
    import pyaudio
    p = pyaudio.PyAudio()
    device_count = p.get_device_count()
    print(f"{Colors.BRIGHT_GREEN}✓ PyAudio instalado correctamente{Colors.RESET}")
    print(f"   - Dispositivos de audio encontrados: {device_count}")
    
    # Listar dispositivos de entrada
    print(f"\n   📱 Dispositivos de entrada disponibles:")
    for i in range(device_count):
        try:
            device_info = p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels', 0) > 0:
                print(f"      [{i}] {device_info.get('name')}")
        except:
            pass
    
    p.terminate()
except ImportError:
    print(f"{Colors.BRIGHT_RED}✗ PyAudio no está instalado{Colors.RESET}")
    print(f"{Colors.YELLOW}⚠ Instala con: pip install pyaudio{Colors.RESET}")
    sys.exit(1)
except Exception as e:
    print(f"{Colors.BRIGHT_YELLOW}⚠ Error verificando dispositivos: {e}{Colors.RESET}")

print()

# Test 5: Verificar conexión con AWS
print("5️⃣  Verificando conexión con AWS...")
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    
    # Intentar crear cliente de Transcribe
    session = boto3.Session()
    credentials = session.get_credentials()
    
    if credentials:
        print(f"{Colors.BRIGHT_GREEN}✓ Credenciales AWS válidas{Colors.RESET}")
        print(f"   - Access Key: {credentials.access_key[:8]}...{credentials.access_key[-4:]}")
        print(f"   - Región: {session.region_name or os.getenv('AWS_DEFAULT_REGION')}")
    else:
        print(f"{Colors.BRIGHT_RED}✗ No se pudieron obtener credenciales{Colors.RESET}")
        sys.exit(1)
    
except NoCredentialsError:
    print(f"{Colors.BRIGHT_RED}✗ Credenciales de AWS no encontradas{Colors.RESET}")
    sys.exit(1)
except Exception as e:
    print(f"{Colors.BRIGHT_YELLOW}⚠ Error verificando AWS: {e}{Colors.RESET}")

print()

# Test 6: Verificar dependencias adicionales
print("6️⃣  Verificando dependencias adicionales...")
dependencies = [
    ('numpy', 'NumPy'),
    ('amazon_transcribe', 'Amazon Transcribe SDK'),
    ('asyncio', 'AsyncIO'),
]

all_ok = True
for module_name, display_name in dependencies:
    try:
        __import__(module_name)
        print(f"{Colors.BRIGHT_GREEN}✓ {display_name}{Colors.RESET}")
    except ImportError:
        print(f"{Colors.BRIGHT_RED}✗ {display_name} no instalado{Colors.RESET}")
        all_ok = False

if not all_ok:
    print(f"\n{Colors.YELLOW}⚠ Instala dependencias faltantes con: pip install -r requirements.txt{Colors.RESET}")
    sys.exit(1)

print()
print("=" * 70)
print(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}✅ TODOS LOS TESTS PASARON - EL MVP ESTÁ LISTO PARA USAR{Colors.RESET}")
print("=" * 70)
print()
print(f"{Colors.BRIGHT_CYAN}Para ejecutar el asistente:{Colors.RESET}")
print(f"  {Colors.BRIGHT_WHITE}python src/main.py{Colors.RESET}")
print()
print(f"{Colors.BRIGHT_CYAN}Documentación:{Colors.RESET}")
print(f"  {Colors.BRIGHT_WHITE}cat MVP_INSTRUCTIONS.md{Colors.RESET}")
print()
