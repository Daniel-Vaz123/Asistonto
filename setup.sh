#!/bin/bash
# Script de configuración inicial para el Asistente de Voz

echo "=== Configuración del Asistente de Voz para Raspberry Pi ==="
echo ""

# Verificar Python 3.9+
echo "Verificando versión de Python..."
python3 --version

if [ $? -ne 0 ]; then
    echo "Error: Python 3 no está instalado"
    exit 1
fi

# Crear entorno virtual
echo ""
echo "Creando entorno virtual..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "Error: No se pudo crear el entorno virtual"
    exit 1
fi

# Activar entorno virtual
echo "Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo ""
echo "Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
echo ""
echo "Instalando dependencias..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: No se pudieron instalar las dependencias"
    exit 1
fi

# Crear archivo .env si no existe
if [ ! -f .env ]; then
    echo ""
    echo "Creando archivo .env desde .env.example..."
    cp .env.example .env
    echo "IMPORTANTE: Edita el archivo .env con tus credenciales de AWS"
fi

# Crear directorios necesarios
echo ""
echo "Verificando estructura de directorios..."
mkdir -p data logs cache

# Inicializar Git si no existe
if [ ! -d .git ]; then
    echo ""
    echo "Inicializando repositorio Git..."
    git init
    echo "Repositorio Git inicializado"
fi

echo ""
echo "=== Configuración completada exitosamente ==="
echo ""
echo "Próximos pasos:"
echo "1. Edita el archivo .env con tus credenciales de AWS"
echo "2. Edita config.json con tu configuración específica"
echo "3. Activa el entorno virtual: source venv/bin/activate"
echo "4. Ejecuta el asistente: python -m src.main"
echo ""
