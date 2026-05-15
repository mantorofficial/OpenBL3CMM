@echo off
REM ============================================
REM  OpenBL3CMM 1.0 - Build to EXE
REM  Run this from the source folder
REM ============================================

echo === OpenBL3CMM EXE Builder ===
echo.

REM Check Python
python --version 2>nul
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install PySide6 pyyaml pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Building EXE...
echo.

REM Wipe stale build artifacts so old .pyc files can't poison the build
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

REM Build with spec file (preferred), fall back to CLI flags
if exist OpenBL3CMM.spec (
    echo Using OpenBL3CMM.spec...
    python -m PyInstaller --clean --noconfirm OpenBL3CMM.spec
) else (
    echo No spec file found, building directly...
    python -m PyInstaller ^
        --name "OpenBL3CMM" ^
        --onefile ^
        --windowed ^
        --noconfirm ^
        --clean ^
        --icon "openbl3cmm.ico" ^
        --add-data "models.py;." ^
        --add-data "parser.py;." ^
        --add-data "exporter.py;." ^
        --add-data "commands.py;." ^
        --add-data "blimp.py;." ^
        --add-data "blmod.py;." ^
        --add-data "object_explorer.py;." ^
        --add-data "hotfix_highlighter.py;." ^
        --add-data "generate_datapack.py;." ^
        --add-data "openbl3cmm.ico;." ^
        --hidden-import "models" ^
        --hidden-import "parser" ^
        --hidden-import "exporter" ^
        --hidden-import "commands" ^
        --hidden-import "blimp" ^
        --hidden-import "blmod" ^
        --hidden-import "object_explorer" ^
        --hidden-import "hotfix_highlighter" ^
        --hidden-import "generate_datapack" ^
        --hidden-import "yaml" ^
        main.py
)

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo  BUILD SUCCESSFUL!
echo  EXE is at: dist\OpenBL3CMM.exe
echo ============================================
echo.
pause
