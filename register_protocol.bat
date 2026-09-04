@echo off
title Registrasi Protocol AutoBiometrik BPJS
echo ============================================================
echo Mendaftarkan Protocol fingerbpjs:// dan fristabpjs:// ...
echo ============================================================

set EXE_PATH=%~dp0AutoBiometrik.exe

if not exist "%EXE_PATH%" (
    echo.
    echo ERROR: File AutoBiometrik.exe tidak ditemukan di folder ini!
    echo Harap letakkan register_protocol.bat di folder yang sama dengan AutoBiometrik.exe
    echo.
    pause
    exit /b 1
)

:: Escape backslashes for registry
set ESCAPED_PATH=%EXE_PATH:\=\\%

reg add "HKCU\Software\Classes\fingerbpjs" /ve /t REG_SZ /d "URL:Finger BPJS Protocol" /f >nul
reg add "HKCU\Software\Classes\fingerbpjs" /v "URL Protocol" /t REG_SZ /d "" /f >nul
reg add "HKCU\Software\Classes\fingerbpjs\shell\open\command" /ve /t REG_SZ /d "\"%EXE_PATH%\" \"%%1\"" /f >nul

reg add "HKCU\Software\Classes\fristabpjs" /ve /t REG_SZ /d "URL:Frista BPJS Protocol" /f >nul
reg add "HKCU\Software\Classes\fristabpjs" /v "URL Protocol" /t REG_SZ /d "" /f >nul
reg add "HKCU\Software\Classes\fristabpjs\shell\open\command" /ve /t REG_SZ /d "\"%EXE_PATH%\" \"%%1\"" /f >nul

echo.
echo SUCCESS: Protocol fingerbpjs:// dan fristabpjs:// telah berhasil didaftarkan!
echo Path EXE: %EXE_PATH%
echo.
pause
