@echo off
title Build AutoBiometrik EXE
echo ============================================================
echo Memulai Build AutoBiometrik dengan PyInstaller...
echo ============================================================

pip install pyinstaller

pyinstaller --noconsole --onefile --name "AutoBiometrik" main.py

echo.
if exist "dist\AutoBiometrik.exe" (
    echo ============================================================
    echo SUCCESS: Build berhasil!
    echo File EXE dapat ditemukan di folder: dist\AutoBiometrik.exe
    echo ============================================================
) else (
    echo ============================================================
    echo ERROR: Build gagal. Silakan periksa log di atas.
    echo ============================================================
)
echo.
pause
