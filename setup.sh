#!/bin/bash
# ============================================================
#   Kiro - Asistente de Voz Inteligente
#   Script de instalación automática (Linux / Mac / Git Bash)
# ============================================================

set -e

echo "============================================================"
echo "  Kiro - Asistente de Voz Inteligente"
echo "  Script de instalación automática"
echo "============================================================"
echo ""

# Detectar comando de Python
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "ERROR: Python no está instalado."
    echo "Descárgalo desde https://www.python.org/downloads/"
    exit 1
fi

# 1. Verificar Python
echo "[1/5] Verificando Python..."
$PY --version
echo ""

# 2. Crear entorno virtual
echo "[2/5] Creando entorno virtual (.venv)..."
if [ ! -d ".venv" ]; then
    $PY -m venv .venv
    echo "Entorno virtual creado."
else
    echo "Entorno virtual ya existe, omitiendo..."
fi
echo ""

# 3. Activar e instalar dependencias
echo "[3/5] Instalando dependencias..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
fi

$PY -m pip install --upgrade pip > /dev/null 2>&1
$PY -m pip install -r requirements.txt
echo ""

# 4. Descargar modelo Vosk
echo "[4/5] Descargando modelo de voz Vosk (español)..."
if [ ! -d "model/vosk-model-small-es-0.42" ]; then
    $PY scripts/download_vosk_model.py
else
    echo "Modelo Vosk ya existe, omitiendo..."
fi
echo ""

# 5. Crear directorios y .env
echo "[5/5] Verificando estructura del proyecto..."
mkdir -p logs cache data

if [ ! -f ".env" ]; then
    cat > .env << 'ENVEOF'
# Credenciales AWS (necesarias para Amazon Polly – voz de respuesta)
AWS_ACCESS_KEY_ID=tu_access_key_aqui
AWS_SECRET_ACCESS_KEY=tu_secret_key_aqui
AWS_DEFAULT_REGION=us-east-1
DEEPSEEK_API_KEY=tu_api_key_aqui
ENVEOF
    echo ""
    echo "IMPORTANTE: Se creó el archivo .env con valores de ejemplo."
    echo "Edítalo con tus credenciales reales antes de ejecutar."
fi
echo ""

echo "============================================================"
echo "  Instalación completada"
echo "============================================================"
echo ""
echo "Para ejecutar el asistente:"
echo "  1. Edita .env con tus credenciales (AWS + DeepSeek)"
echo "  2. Activa el entorno: source .venv/bin/activate"
echo "     (Git Bash Windows: source .venv/Scripts/activate)"
echo "  3. Ejecuta: python -m src.main"
echo ""
