@echo off
title AetherCraft Minecraft Server
echo ===================================================================
echo   AETHERCRAFT // MINECRAFT PAPER 1.21.1
echo ===================================================================

set "JAVA_BIN=java"
for /d %%D in ("%~dp0runtime\jdk-*") do (
    if exist "%%D\bin\java.exe" (
        set "JAVA_BIN=%%D\bin\java.exe"
        echo [OK] Runtime Java 21 portable detecte dans %%D.
    )
)

cd /d "%~dp0"
"%JAVA_BIN%" -Xms2G -Xmx3G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 -Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true -jar server.jar --nogui
pause
