@echo off
chcp 65001 >nul 2>&1
echo ============================================================
echo   Kiro - Asistente de Voz Inteligente
echo   Script de instalacion automatica (Windows)
echo ============================================================
echo.

:: Verificar Python
echo [1/5] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado o no esta en el PATH.
    echo Descargalo desde https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

:: Crear entorno virtual
echo [2/5] Creando entorno virtual (.venv)...
if not exist .venv (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo Entorno virtual creado.
) else (
    echo Entorno virtual ya existe, omitiendo...
)
echo.

:: Activar entorno e instalar dependencias
echo [3/5] Instalando dependencias...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: No se pudieron instalar las dependencias.
    pause
    exit /b 1
)
echo.

:: Descargar modelo Vosk
echo [4/5] Descargando modelo de voz Vosk (español)...
if not exist "model\vosk-model-small-es-0.42" (
    python scripts\download_vosk_model.py
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo descargar el modelo Vosk.
        pause
        exit /b 1
    )
) else (
    echo Modelo Vosk ya existe, omitiendo...
)
echo.

:: Crear directorios y archivo .env
echo [5/5] Verificando estructura del proyecto...
if not exist logs mkdir logs
if not exist cache mkdir cache
if not exist data mkdir data
if not exist .env (
    echo # Credenciales AWS (necesarias para Amazon Polly – voz de respuesta)> .env
    echo AWS_ACCESS_KEY_ID=tu_access_key_aqui>> .env
    echo AWS_SECRET_ACCESS_KEY=tu_secret_key_aqui>> .env
    echo AWS_DEFAULT_REGION=us-east-1>> .env
    echo DEEPSEEK_API_KEY=tu_api_key_aqui>> .env
    echo.
    echo IMPORTANTE: Se creo el archivo .env con valores de ejemplo.
    echo Editalo con tus credenciales reales antes de ejecutar.
)
echo.

echo ============================================================
echo   Instalacion completada
echo ============================================================
echo.
echo Para ejecutar el asistente:
echo   1. Edita .env con tus credenciales (AWS + DeepSeek)
echo   2. Abre Git Bash o CMD en esta carpeta
echo   3. Activa el entorno:
echo      CMD:      .venv\Scripts\activate.bat
echo      Git Bash: source .venv/Scripts/activate
echo   4. Ejecuta: python -m src.main
echo.
pause
