@echo off
setlocal enabledelayedexpansion
title RenKill — Build Script

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   RENKILL — BUILD SCRIPT                            ║
echo  ║   CJMXO STUDIOS                                     ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: ─ Check Python ──────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from python.org and add to PATH.
    pause
    exit /b 1
)
echo [OK] Python found:
python --version
echo.

:: ─ Install dependencies ───────────────────────────────────────────────────────
echo [*] Installing dependencies...
echo.

python -m pip install --upgrade pip --quiet
python -m pip install psutil --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install psutil
    pause
    exit /b 1
)
echo [OK] psutil installed

python -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install pyinstaller
    pause
    exit /b 1
)
echo [OK] pyinstaller installed
echo.

:: ─ Compile using python -m PyInstaller (bypasses PATH issue) ──────────────────
echo [*] Compiling RenKill to single EXE (30-60 seconds)...
echo.

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "RenKill" ^
    --hidden-import psutil ^
    --hidden-import winreg ^
    --hidden-import tkinter ^
    --hidden-import tkinter.scrolledtext ^
    --hidden-import tkinter.messagebox ^
    --hidden-import tkinter.filedialog ^
    --collect-all psutil ^
    --noupx ^
    renkill.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check output above for details.
    pause
    exit /b 1
)

:: ─ Move output ────────────────────────────────────────────────────────────────
if exist dist\RenKill.exe (
    copy /y dist\RenKill.exe RenKill.exe >nul
    echo.
    echo  ╔══════════════════════════════════════════════════════╗
    echo  ║   BUILD COMPLETE                                     ║
    echo  ║   Output: RenKill.exe (this folder)                 ║
    echo  ║                                                      ║
    echo  ║   Right-click RenKill.exe → Run as Administrator    ║
    echo  ╚══════════════════════════════════════════════════════╝
    echo.
) else (
    echo [ERROR] RenKill.exe not found after build.
    echo Check PyInstaller output above.
)

:: ─ Cleanup ────────────────────────────────────────────────────────────────────
echo [*] Cleaning build artifacts...
if exist build        rmdir /s /q build
if exist dist         rmdir /s /q dist
if exist __pycache__  rmdir /s /q __pycache__
if exist RenKill.spec del /q RenKill.spec
echo [OK] Clean.
echo.

pause
