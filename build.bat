@echo off
title Build AutoBiometrik REST API Service EXE
echo ============================================================
echo Memulai Build AutoBiometrik Service dengan PyInstaller...
echo ============================================================

pip install -r requirements.txt

pyinstaller --noconsole --onefile --name "AutoBiometrikService" main.py

echo.
if exist "dist\AutoBiometrikService.exe" (
    echo ============================================================
    echo SUCCESS: Build berhasil!
    echo File EXE dapat ditemukan di folder: dist\AutoBiometrikService.exe
    echo.
    echo Jangan lupa untuk meletakkan config.json di folder yang sama
    echo dengan AutoBiometrikService.exe di komputer client.
    echo ============================================================
) else (
    echo ============================================================
    echo ERROR: Build gagal. Silakan periksa log di atas.
    echo ============================================================
)
echo.
pause
