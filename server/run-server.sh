#!/usr/bin/env bash
# ==============================================================================
# AetherCraft - Lanceur Serveur Minecraft Paper 1.21.1 (Optimisé Linux)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Mémoire allouée par défaut (ajustable via la variable SERVER_RAM, ex: SERVER_RAM=10G ./run-server.sh)
RAM_MIN="${SERVER_RAM_MIN:-4G}"
RAM_MAX="${SERVER_RAM:-10G}"

echo "==================================================================="
echo "  AETHERCRAFT // PAPER 1.21.1 (Linux x64)"
echo "  Allocation RAM : ${RAM_MIN} (min) / ${RAM_MAX} (max)"
echo "==================================================================="

exec java \
  -Xms"${RAM_MIN}" \
  -Xmx"${RAM_MAX}" \
  -XX:+UseG1GC \
  -XX:+ParallelRefProcEnabled \
  -XX:MaxGCPauseMillis=200 \
  -XX:+UnlockExperimentalVMOptions \
  -XX:+DisableExplicitGC \
  -XX:+AlwaysPreTouch \
  -XX:G1NewSizePercent=30 \
  -XX:G1MaxNewSizePercent=40 \
  -XX:G1ReservePercent=20 \
  -XX:G1HeapWastePercent=5 \
  -XX:G1MixedGCCountTarget=4 \
  -XX:InitiatingHeapOccupancyPercent=15 \
  -XX:G1MixedGCLiveThresholdPercent=90 \
  -XX:G1RSetUpdatingPauseTimePercent=5 \
  -XX:SurvivorRatio=32 \
  -XX:+PerfDisableSharedMem \
  -XX:MaxTenuringThreshold=1 \
  -Dusing.aikars.flags=https://mcflags.emc.gs \
  -Daikars.new.flags=true \
  -jar server.jar --nogui
