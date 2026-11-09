@echo off
setlocal enabledelayedexpansion
title AetherCraft - Demarrage Global (Web, Serveur Minecraft & Client)
color 0E

echo ===================================================================
echo   AETHERCRAFT // DEMARRAGE COMPLET (SERVEUR, WEB ET CLIENT)
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

REM 2. Detection de Python 3
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
start "AetherCraft Web Platform [Port 5000]" cmd.exe /k "cd /d ""%ROOT_DIR%web"" && ""!PYTHON_CMD!"" app.py"

echo [2/4] Lancement du serveur Minecraft Paper 1.21.1 (Port 25565)...
start "AetherCraft Minecraft Server [Port 25565]" cmd.exe /k "cd /d ""%ROOT_DIR%server"" && run-server.bat"

echo [3/4] Ouverture du Dashboard & Boutique dans votre navigateur...
timeout /t 3 > nul
start http://127.0.0.1:5000

echo [4/4] Lancement du Client Minecraft (1.21.1)...
set "CLIENT_MODS_DIR=%ROOT_DIR%client-mods\neoforge"
set "FANCY_CFG_DIR=%ROOT_DIR%client-mods\fancymenu_config"
set "MC_DIR=%APPDATA%\.minecraft"
set "MC_MODS_DIR=%MC_DIR%\mods"
set "MC_FANCY_DIR=%MC_DIR%\config\fancymenu"

if exist "%MC_DIR%" (
    if exist "%CLIENT_MODS_DIR%" (
        echo [*] Synchronisation des mods client...
        if not exist "%MC_MODS_DIR%" mkdir "%MC_MODS_DIR%"
        copy /y "%CLIENT_MODS_DIR%\*.jar" "%MC_MODS_DIR%\" >nul 2>&1
    )
    if exist "%FANCY_CFG_DIR%" (
        echo [*] Synchronisation des menus FancyMenu...
        if not exist "%MC_FANCY_DIR%" mkdir "%MC_FANCY_DIR%"
        xcopy /s /e /y "%FANCY_CFG_DIR%\*" "%MC_FANCY_DIR%\" >nul 2>&1
    )
)

REM Detection et demarrage du launcher Minecraft
set "LAUNCHER_FOUND=0"
if exist "C:\XboxGames\Minecraft Launcher\Content\Minecraft.exe" (
    echo [OK] Launcher detecte : C:\XboxGames\Minecraft Launcher\Content\Minecraft.exe
    start "" "C:\XboxGames\Minecraft Launcher\Content\Minecraft.exe"
    set "LAUNCHER_FOUND=1"
)
if "!LAUNCHER_FOUND!"=="0" if exist "%LOCALAPPDATA%\Programs\Minecraft Launcher\MinecraftLauncher.exe" (
    echo [OK] Launcher detecte : %LOCALAPPDATA%\Programs\Minecraft Launcher\MinecraftLauncher.exe
    start "" "%LOCALAPPDATA%\Programs\Minecraft Launcher\MinecraftLauncher.exe"
    set "LAUNCHER_FOUND=1"
)
if "!LAUNCHER_FOUND!"=="0" if exist "%ProgramFiles(x86)%\Minecraft Launcher\MinecraftLauncher.exe" (
    echo [OK] Launcher detecte : %ProgramFiles(x86)%\Minecraft Launcher\MinecraftLauncher.exe
    start "" "%ProgramFiles(x86)%\Minecraft Launcher\MinecraftLauncher.exe"
    set "LAUNCHER_FOUND=1"
)
if "!LAUNCHER_FOUND!"=="0" if exist "%LOCALAPPDATA%\Programs\Modrinth App\Modrinth App.exe" (
    echo [OK] Launcher Modrinth detecte
    start "" "%LOCALAPPDATA%\Programs\Modrinth App\Modrinth App.exe"
    set "LAUNCHER_FOUND=1"
)
if "!LAUNCHER_FOUND!"=="0" (
    start minecraft: >nul 2>&1
    if !errorlevel! equ 0 set "LAUNCHER_FOUND=1"
)

color 0A
echo.
echo ===================================================================
echo   TOUS LES SERVICES AETHERCRAFT SONT EN COURS D'EXECUTION !
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
