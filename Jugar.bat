@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

title Arcane Vision: Duelo de Magos

set "VENV_PY=.venv\Scripts\python.exe"

:: 1. Si el entorno virtual ya existe y tiene las dependencias listas, abrir directo
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import mediapipe, cv2, pygame, numpy" >nul 2>&1
    if not errorlevel 1 goto :launch
)

echo ============================================================
echo   Arcane Vision: Duelo de Magos - Preparando primera ejecucion
echo ============================================================
echo.

:: 2. Buscar uv en PATH o en las rutas habituales de instalacion
set "UV_CMD="
where uv >nul 2>&1
if not errorlevel 1 set "UV_CMD=uv"

if not defined UV_CMD if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV_CMD=%USERPROFILE%\.local\bin\uv.exe"
)
if not defined UV_CMD if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
    set "UV_CMD=%USERPROFILE%\.cargo\bin\uv.exe"
)

:: 3. Si no esta instalado, descargar uv automaticamente (sin permisos de admin)
if not defined UV_CMD (
    echo [1/3] Descargando gestor portable uv...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo.
        echo [ERROR] No se pudo descargar uv. Revisa tu conexion a internet.
        pause
        exit /b 1
    )
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "UV_CMD=%USERPROFILE%\.local\bin\uv.exe"
    ) else if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
        set "UV_CMD=%USERPROFILE%\.cargo\bin\uv.exe"
    ) else (
        set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
        set "UV_CMD=uv"
    )
)

:: 4. Crear entorno virtual aislado con Python 3.14
if not exist "%VENV_PY%" (
    echo [2/3] Creando entorno virtual aislado con Python 3.14...
    "%UV_CMD%" venv --python 3.14 .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] No se pudo crear el entorno virtual con Python 3.14.
        pause
        exit /b 1
    )
)

:: 5. Instalar dependencias del proyecto
echo [3/3] Instalando dependencias ^(solo ocurre la primera vez^)...
"%UV_CMD%" pip install --python "%VENV_PY%" -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Fallo la instalacion de dependencias. Revisa tu conexion a internet.
    pause
    exit /b 1
)

echo.
echo Instalacion completada. Iniciando Arcane Vision...
echo.

:launch
"%VENV_PY%" main.py %*
if errorlevel 1 (
    echo.
    echo El juego termino con un error ^(codigo %errorlevel%^).
    pause
)
endlocal
