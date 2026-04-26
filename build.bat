@echo off
setlocal
title RenKill Build

echo.
echo ===============================================
echo   RenKill - Windows Build Script
echo   made with love - Cloud
echo ===============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

echo [OK] Python detected:
python --version
echo.

echo [*] Installing build dependencies...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
)

python -m pip install pyinstaller==6.19.0 psutil
if errorlevel 1 (
    echo [ERROR] Failed to install build dependencies.
    pause
    exit /b 1
)
echo.

echo [*] Verifying source files...
python -m py_compile renkill.py
if errorlevel 1 (
    echo [ERROR] renkill.py failed to compile.
    pause
    exit /b 1
)

python -m py_compile renengine_hunter.py
if errorlevel 1 (
    echo [ERROR] renengine_hunter.py failed to compile.
    pause
    exit /b 1
)

python -m py_compile reninspect.py
if errorlevel 1 (
    echo [ERROR] reninspect.py failed to compile.
    pause
    exit /b 1
)
echo.

echo [*] Building RenKill.exe...
python -m PyInstaller --clean -y RenKill.spec

if errorlevel 1 (
    echo [ERROR] Build failed. Check the output above.
    pause
    exit /b 1
)

if exist dist\RenKill\RenKill.exe (
    echo.
    echo [OK] Build complete.
    echo [OK] Output folder: dist\RenKill
    echo [OK] Launch file: dist\RenKill\RenKill.exe
) else (
    echo [ERROR] dist\RenKill\RenKill.exe was not produced.
    pause
    exit /b 1
)

echo.
echo [*] Cleaning transient build folders...
if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__
echo [OK] Clean.
echo.

pause
