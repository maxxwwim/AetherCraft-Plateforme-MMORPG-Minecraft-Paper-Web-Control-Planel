@echo off
setlocal enabledelayedexpansion
title AetherCraft - Lanceur Client Minecraft 1.21.1
color 0B

echo ===================================================================
echo   AETHERCRAFT // LANCEUR DU CLIENT MINECRAFT (1.21.1)
echo ===================================================================
echo.

set "ROOT_DIR=%~dp0"
set "CLIENT_MODS_DIR=%ROOT_DIR%client-mods\neoforge"
set "FANCY_CFG_DIR=%ROOT_DIR%client-mods\fancymenu_config"
set "MC_DIR=%APPDATA%\.minecraft"
set "MC_MODS_DIR=%MC_DIR%\mods"
set "MC_FANCY_DIR=%MC_DIR%\config\fancymenu"

REM 1. Synchronisation des mods client et configs si presents
if exist "%MC_DIR%" (
    if exist "%CLIENT_MODS_DIR%" (
        echo [*] Verification et synchronisation des mods client (FancyMenu, Konkrete, Melody)...
        if not exist "%MC_MODS_DIR%" mkdir "%MC_MODS_DIR%"
        copy /y "%CLIENT_MODS_DIR%\*.jar" "%MC_MODS_DIR%\" >nul 2>&1
        echo [OK] Mods installes dans .minecraft\mods !
    )
    
    if exist "%FANCY_CFG_DIR%" (
        echo [*] Synchronisation des menus MMORPG (assets, fonds d'ecran, boutons)...
        if not exist "%MC_FANCY_DIR%" mkdir "%MC_FANCY_DIR%"
        xcopy /s /e /y "%FANCY_CFG_DIR%\*" "%MC_FANCY_DIR%\" >nul 2>&1
        echo [OK] Menus MMORPG configures dans .minecraft\config\fancymenu !
    )
)

echo.
echo [*] Recherche et lancement du Launcher Minecraft...

REM Verification 1 : Launcher officiel Xbox / Windows Store
if exist "C:\XboxGames\Minecraft Launcher\Content\Minecraft.exe" (
    echo [OK] Launcher detecte : C:\XboxGames\Minecraft Launcher\Content\Minecraft.exe
    start "" "C:\XboxGames\Minecraft Launcher\Content\Minecraft.exe"
    goto :launched
)

REM Verification 2 : Launcher officiel LocalAppData
if exist "%LOCALAPPDATA%\Programs\Minecraft Launcher\MinecraftLauncher.exe" (
    echo [OK] Launcher detecte : %LOCALAPPDATA%\Programs\Minecraft Launcher\MinecraftLauncher.exe
    start "" "%LOCALAPPDATA%\Programs\Minecraft Launcher\MinecraftLauncher.exe"
    goto :launched
)

REM Verification 3 : Launcher officiel Program Files (x86)
if exist "%ProgramFiles(x86)%\Minecraft Launcher\MinecraftLauncher.exe" (
    echo [OK] Launcher detecte : %ProgramFiles(x86)%\Minecraft Launcher\MinecraftLauncher.exe
    start "" "%ProgramFiles(x86)%\Minecraft Launcher\MinecraftLauncher.exe"
    goto :launched
)

REM Verification 4 : Modrinth App
if exist "%LOCALAPPDATA%\Programs\Modrinth App\Modrinth App.exe" (
    echo [OK] Modrinth App detectee, lancement...
    start "" "%LOCALAPPDATA%\Programs\Modrinth App\Modrinth App.exe"
    goto :launched
)

REM Verification 5 : Protocole systeme Windows
echo [*] Tentative via le protocole systeme URI "minecraft:"...
start minecraft:
if %errorlevel% equ 0 goto :launched

echo [!] Aucun launcher automatique trouve. Veuillez ouvrir votre launcher Minecraft manuellement.
pause
exit /b 1

:launched
echo.
echo ===================================================================
echo   [OK] LE CLIENT MINECRAFT A ETE DEMARRE AVEC SUCCES !
echo ===================================================================
echo.
echo   Consignes de jeu :
echo   1. Choisissez le profil "1.21.1" (ou NeoForge 21.1.265 si modde).
echo   2. Cliquez sur "Jouer".
echo   3. Dans Multijoueur, connectez-vous a : 127.0.0.1:25565
echo      (ou l'adresse IP de votre serveur dedie).
echo   4. Les menus MMORPG, boutique et HDV sont integres directement in-game !
echo ===================================================================
timeout /t 5 >nul
exit /b 0
