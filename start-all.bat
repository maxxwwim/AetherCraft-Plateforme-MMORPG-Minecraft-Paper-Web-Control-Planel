@echo off
setlocal EnableDelayedExpansion
title AetherCraft - Lanceur Global (Web & Minecraft)
color 0E

echo ===================================================================
echo   AETHERCRAFT // DEMARRAGE COMPLET (SERVEUR ET WEB)
echo ===================================================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

REM 1. Verification rapide des prerequis
if not exist "%ROOT_DIR%server\server.jar" (
    echo [!] server\server.jar est introuvable.
    echo Execution automatique de l'installation prealable...
    call "%ROOT_DIR%install.bat"
)

REM 2. Detection de Python
set "PYTHON_CMD=python"
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=py -3"
    ) else (
        if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python313\python.exe"
        if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
        if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
        if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
    )
)

echo [1/4] Lancement de la plateforme Web Waitress (Port 5000)...
start "AetherCraft Web Platform [Port 5000]" cmd.exe /k "cd /d ""%ROOT_DIR%web"" && ""%PYTHON_CMD%"" app.py"

echo [2/4] Lancement du serveur Minecraft Paper 1.21.1 (Port 25565)...
start "AetherCraft Minecraft Server [Port 25565]" cmd.exe /k "cd /d ""%ROOT_DIR%server"" && run-server.bat"

echo [3/4] Ouverture du Dashboard & Boutique dans votre navigateur...
timeout /t 3 > nul
start http://127.0.0.1:5000

echo [4/4] Lancement du Client Minecraft (NeoForge 1.21.1)...
if exist "%ROOT_DIR%launch-client.bat" (
    call "%ROOT_DIR%launch-client.bat"
)

color 0A
echo.
echo ===================================================================
echo   LES SERVICES AETHERCRAFT SONT EN COURS D'EXECUTION !
echo ===================================================================
echo.
echo   - Boutique & Dashboard Web : http://127.0.0.1:5000
echo   - Connexion Minecraft       : 127.0.0.1:25565 (ou localhost)
echo   - Console RCON Securisee    : 127.0.0.1:25575
echo.
echo   Commandes In-Game (Interfaces Holographiques 3D & MMORPG) :
echo   - /menu         : Cockpit 3D, Profil Joueur, Succes, Quetes
echo   - /shop         : Boutique Royale 3D liee en direct a SQLite
echo   - /marche       : Hotel des Ventes P2P 3D et Bourse des Minerais
echo   - /banque       : Coffre-fort personnel et Livret d'Epargne
echo   - /rtp          : Teleportation aleatoire securisee sur terre
echo   - /oneblock     : Generation de votre ile OneBlock infinie
echo ===================================================================
echo   Laissez cette fenetre ouverte ou fermez-la a tout moment.
echo   Les serveurs continuent de tourner dans leurs fenetres dediees.
echo ===================================================================
pause
