@echo off
cd /d "%~dp0"

echo ========================================
echo   MemoPet Build
echo ========================================

if exist "build" rmdir /s /q "build" 2>nul
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "MemoPet.spec" del /f /q "MemoPet.spec" 2>nul

echo [1/2] Building...

python -m PyInstaller --onefile --noconsole --name MemoPet --add-data "widget_icon.png;." --hidden-import customtkinter --hidden-import PIL --hidden-import PIL.ImageTk --hidden-import PIL.ImageDraw --hidden-import PIL.ImageFilter --hidden-import numpy --collect-all customtkinter --distpath "dist" --workpath "build" --specpath "." "memo.py"

if %ERRORLEVEL% neq 0 (
    echo [FAIL] Build failed!
    pause
    exit /b 1
)

echo [2/2] Cleaning up...
rmdir /s /q "build" 2>nul
del /f /q "MemoPet.spec" 2>nul

echo.
echo ========================================
echo   Done: dist\MemoPet.exe
echo ========================================
pause
