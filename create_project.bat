@echo off
setlocal

set /p PROJECT_NAME=Nom du projet: 

if "%PROJECT_NAME%"=="" (
    echo Erreur: le nom du projet est obligatoire.
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo [INFO] Generation du projet "%PROJECT_NAME%"...
python generator.py --project-name "%PROJECT_NAME%"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERREUR] La generation a echoue ^(code %EXIT_CODE%^).
    exit /b %EXIT_CODE%
)

echo.
echo [OK] Generation terminee.
exit /b 0
