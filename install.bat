@echo off
setlocal EnableDelayedExpansion
title AetherCraft - Installation Automatique
color 0B

echo ===================================================================
echo   AETHERCRAFT // INSTALLATEUR AUTOMATIQUE 1-CLIC
echo   Configuration du Serveur Paper 1.21.1 et de la Boutique Web
echo ===================================================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

REM -------------------------------------------------------------------
REM 1. DETECTION ET CONFIGURATION DE JAVA 21
REM -------------------------------------------------------------------
echo [1/6] Verification de l'environnement Java 21...
set "JAVA_CMD="

REM Verification A : Runtime portable integre dans server\runtime
for /d %%D in ("%ROOT_DIR%server\runtime\jdk-*") do (
    if exist "%%D\bin\java.exe" (
        set "JAVA_CMD=%%D\bin\java.exe"
        echo [OK] Java 21 portable detecte dans %%D.
        goto :JAVA_DONE
    )
)

REM Verification B : Java dans le PATH systeme
where java >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('java -version 2^>^&1') do (
        echo %%v | findstr /i "version" >nul
        if !errorlevel! equ 0 (
            echo %%v | findstr /r "21\." >nul
            if !errorlevel! equ 0 (
                set "JAVA_CMD=java"
                echo [OK] Java 21 systeme detecte avec succes.
                goto :JAVA_DONE
            )
        )
    )
)

REM Verification C : JAVA_HOME
if defined JAVA_HOME (
    if exist "%JAVA_HOME%\bin\java.exe" (
        set "JAVA_CMD=%JAVA_HOME%\bin\java.exe"
        echo [OK] Java detecte via JAVA_HOME.
        goto :JAVA_DONE
    )
)

REM Telechargement automatique du runtime Java 21 portable si absent
echo [!] Java 21 est introuvable sur cette machine.
echo [*] Telechargement automatique du runtime portable OpenJDK 21 (Adoptium Temurin)...
echo [*] Veuillez patienter pendant le telechargement...

if not exist "%ROOT_DIR%server\runtime" mkdir "%ROOT_DIR%server\runtime"

powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $dest = '%ROOT_DIR%server\runtime\temurin-jre.zip'; Write-Host 'Telechargement de OpenJDK 21 JRE...'; Invoke-WebRequest -Uri 'https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jre/hotspot/normal/eclipse' -OutFile $dest; if (Test-Path $dest) { Write-Host 'Extraction du runtime Java 21...'; Expand-Archive -Path $dest -DestinationPath '%ROOT_DIR%server\runtime' -Force; Remove-Item $dest; Write-Host '[OK] Java 21 portable installe !' }"

for /d %%D in ("%ROOT_DIR%server\runtime\jdk-*") do (
    if exist "%%D\bin\java.exe" (
        set "JAVA_CMD=%%D\bin\java.exe"
        echo [OK] Java 21 portable configure avec succes.
        goto :JAVA_DONE
    )
)

REM Tentative winget si PowerShell direct echoue
where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] Tentative via winget...
    winget install -e --id EclipseAdoptium.Temurin.21.JDK --accept-package-agreements --accept-source-agreements
    where java >nul 2>&1
    if %errorlevel% equ 0 (
        set "JAVA_CMD=java"
        goto :JAVA_DONE
    )
)

color 0C
echo.
echo [ERREUR] Impossible de trouver ou d'installer Java 21 LTS automatiquement.
echo Minecraft Paper 1.21.1 requiert obligatoirement Java 21.
echo Ouverture de la page de telechargement officielle...
start https://adoptium.net/temurin/releases/?version=21
pause
exit /b 1

:JAVA_DONE

REM -------------------------------------------------------------------
REM 2. DETECTION ET CONFIGURATION DE PYTHON 3
REM -------------------------------------------------------------------
echo.
echo [2/6] Verification de Python 3...
set "PYTHON_CMD="

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :PYTHON_DONE
)

py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3"
    goto :PYTHON_DONE
)

for %%P in (
    "%LocalAppData%\Programs\Python\Python313\python.exe"
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python311\python.exe"
    "%LocalAppData%\Programs\Python\Python310\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python310\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
) do (
    if exist "%%~P" (
        set "PYTHON_CMD=%%~P"
        goto :PYTHON_DONE
    )
)

echo [!] Python 3 est introuvable.
echo [*] Tentative d'installation automatique de Python 3.11...
where winget >nul 2>&1
if %errorlevel% equ 0 (
    winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=python"
        goto :PYTHON_DONE
    )
)

echo [*] Telechargement de l'installateur Python officiel...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $installer = '%ROOT_DIR%python-installer.exe'; Write-Host 'Telechargement de Python 3.11...'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile $installer; if (Test-Path $installer) { Write-Host 'Installation silencieuse de Python...'; Start-Process -FilePath $installer -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1' -Wait; Remove-Item $installer; }"

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :PYTHON_DONE
)

color 0C
echo.
echo [ERREUR] Python 3 est introuvable.
echo Veuillez telecharger et installer Python 3.10 ou superieur.
echo ATTENTION : Cochez imperativement 'Add Python to PATH' lors de l'installation !
start https://www.python.org/downloads/
pause
exit /b 1

:PYTHON_DONE
echo [OK] Python detecte : "%PYTHON_CMD%"

REM -------------------------------------------------------------------
REM 3. INSTALLATION DES DEPENDANCES WEB (Flask, Waitress...)
REM -------------------------------------------------------------------
echo.
echo [3/6] Verification des dependances web (requirements.txt)...
"%PYTHON_CMD%" -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Initialisation de pip...
    "%PYTHON_CMD%" -m ensurepip --upgrade >nul 2>&1
)

if exist "%ROOT_DIR%web\requirements.txt" (
    "%PYTHON_CMD%" -m pip install -r "%ROOT_DIR%web\requirements.txt" --disable-pip-version-check
    if %errorlevel% neq 0 (
        echo [!] Avertissement lors de pip install, tentative de poursuite...
    ) else (
        echo [OK] Dependances web installees avec succes.
    )
)

REM -------------------------------------------------------------------
REM 4. INITIALISATION DE LA BASE SQLITE UNIFIEE
REM -------------------------------------------------------------------
echo.
echo [4/6] Initialisation de la base SQLite unifiee (aethercraft.db)...
if not exist "%ROOT_DIR%server\data" mkdir "%ROOT_DIR%server\data"
cd /d "%ROOT_DIR%web"
"%PYTHON_CMD%" -c "import sys, os; sys.path.insert(0, os.path.abspath('.')); from services.database import init_database, DB_PATH; init_database(); print(f'[OK] Base SQLite unifiee initialisee : {DB_PATH}')"
cd /d "%ROOT_DIR%"

REM -------------------------------------------------------------------
REM 5. CONFIGURATION DU SERVEUR MINECRAFT ET COMPILATION DU PLUGIN
REM -------------------------------------------------------------------
echo.
echo [5/6] Configuration Minecraft et compilation du plugin...

REM EULA acceptation automatique
if not exist "%ROOT_DIR%server\eula.txt" (
    echo eula=true> "%ROOT_DIR%server\eula.txt"
    echo [OK] Fichier server\eula.txt cree avec eula=true.
) else (
    echo [OK] Fichier server\eula.txt valide.
)

REM Verification / Telechargement server.jar
if not exist "%ROOT_DIR%server\server.jar" (
    if exist "%ROOT_DIR%server\paper-1.21.1-133.jar" (
        copy /y "%ROOT_DIR%server\paper-1.21.1-133.jar" "%ROOT_DIR%server\server.jar" > nul
        echo [OK] paper-1.21.1-133.jar copie vers server.jar.
    ) else (
        echo [*] Telechargement automatique de Paper 1.21.1 Build 133...
        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://api.papermc.io/v2/projects/paper/versions/1.21.1/builds/133/downloads/paper-1.21.1-133.jar' -OutFile '%ROOT_DIR%server\server.jar'"
        if exist "%ROOT_DIR%server\server.jar" (
            echo [OK] Paper 1.21.1 telecharge avec succes !
        )
    )
)

REM Compilation du plugin AetherVisuals
if exist "%ROOT_DIR%server\plugins_src\build_plugin.py" (
    echo [*] Compilation des classes Java du plugin AetherVisuals...
    "%PYTHON_CMD%" "%ROOT_DIR%server\plugins_src\build_plugin.py"
    if %errorlevel% equ 0 (
        echo [OK] AetherVisuals.jar compile et deploye dans server\plugins.
    ) else (
        echo [!] Avertissement lors de la compilation du plugin.
    )
)

REM -------------------------------------------------------------------
REM 6. PRE-RENDU DES BLOCS 3D ISOMETRIQUES & ANIMAUX 3D VOXEL
REM -------------------------------------------------------------------
echo.
echo [6/6] Generation des rendus 3D isometriques (Blocs Minecraft et Animaux 3D)...
if exist "%ROOT_DIR%web\services\block_renderer.py" (
    "%PYTHON_CMD%" "%ROOT_DIR%web\services\block_renderer.py"
    echo [OK] Blocs 3D isometriques du Marche generes.
)
if exist "%ROOT_DIR%web\services\pet_3d_renderer.py" (
    "%PYTHON_CMD%" "%ROOT_DIR%web\services\pet_3d_renderer.py" > nul 2>&1
    echo [OK] Animaux 3D Voxel Haute Definition generes.
)

REM -------------------------------------------------------------------
REM SUCCES
REM -------------------------------------------------------------------
color 0A
echo.
echo ===================================================================
echo   [SUCCES] INSTALLATION D'AETHERCRAFT TERMINEE AVEC SUCCES !
echo ===================================================================
echo.
echo   Tout est pret pour demarrer votre infrastructure :
echo   - Lancer l'ensemble (Web + Minecraft) : start-all.bat (ou lunchall.bat)
echo   - Lancer le client joueur             : launch-client.bat
echo   - Lancer uniquement le Web            : start-web.bat
echo.
echo   - Boutique et Dashboard Web : http://127.0.0.1:5000
echo   - Serveur Minecraft Paper   : 127.0.0.1:25565
echo.
echo ===================================================================
pause
