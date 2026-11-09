@echo off
title AetherCraft 1.21.1 Server - Aikar Flags G1GC
echo ===================================================================
echo   AETHERCRAFT // INSTANCE MINECRAFT 1.21.1
echo   Optimisation Aikar G1GC
echo ===================================================================

set "JAVA_BIN=java"
if exist "%~dp0runtime\jdk-21.0.13+9-jre\bin\java.exe" (
    set "JAVA_BIN=%~dp0runtime\jdk-21.0.13+9-jre\bin\java.exe"
    echo [OK] Java 21 LTS integre detecte.
)

echo [*] Lancement de server.jar avec flags Aikar...
cd /d "%~dp0"
"%JAVA_BIN%" -Xms2G -Xmx3G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 -Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true -jar server.jar --nogui

echo [*] Serveur arrete.
pause
