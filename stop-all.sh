#!/usr/bin/env bash
# ==============================================================================
# AetherCraft - Arrêt Propre des Services Linux
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}[*] Arrêt propre d'AetherCraft...${NC}"

# 1. Arrêt via tmux si actif
if command -v tmux >/dev/null 2>&1; then
    if tmux has-session -t aether-mc 2>/dev/null; then
        echo -e "${YELLOW}[*] Envoi de la commande 'stop' à Minecraft dans tmux...${NC}"
        tmux send-keys -t aether-mc "stop" Enter
        sleep 5
        tmux kill-session -t aether-mc 2>/dev/null || true
    fi
    if tmux has-session -t aether-web 2>/dev/null; then
        tmux kill-session -t aether-web 2>/dev/null || true
    fi
fi

# 2. Arrêt des PID nohup si présents
if [ -f ".mc.pid" ]; then
    kill -15 "$(cat .mc.pid)" 2>/dev/null || true
    rm -f .mc.pid
fi
if [ -f ".web.pid" ]; then
    kill -15 "$(cat .web.pid)" 2>/dev/null || true
    rm -f .web.pid
fi

echo -e "${GREEN}[OK] Tous les services AetherCraft sont arrêtés.${NC}"
