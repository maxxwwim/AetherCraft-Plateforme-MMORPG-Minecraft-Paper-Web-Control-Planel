#!/usr/bin/env bash
# ==============================================================================
# AetherCraft - Lanceur Global Linux (Serveur Minecraft + Web Platform)
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}===================================================================${NC}"
echo -e "${GREEN}   AETHERCRAFT // DEMARRAGE GLOBAL LINUX${NC}"
echo -e "${BLUE}===================================================================${NC}"

# 1. Verification de l'installation prealable
if [ ! -f "server/server.jar" ] || [ ! -d "web/venv" ]; then
    echo -e "${YELLOW}[!] Prerequis manquants. Execution de ./install.sh...${NC}"
    ./install.sh
fi

# Detecter le binaire Python pour le Web
if [ -f "web/venv/bin/python" ]; then
    PYTHON_BIN="web/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

# 2. Utilisation preferentielle de tmux ou screen pour garder la console accessible
if command -v tmux >/dev/null 2>&1; then
    echo -e "${CYAN}[1/2] Demarrage du Web Panel dans la session tmux 'aether-web'...${NC}"
    tmux kill-session -t aether-web 2>/dev/null || true
    tmux new-session -d -s aether-web "bash -c 'cd \"$SCRIPT_DIR/web\" && \"$PYTHON_BIN\" -u app.py; exec bash'"

    echo -e "${CYAN}[2/2] Demarrage du serveur Minecraft dans la session tmux 'aether-mc'...${NC}"
    tmux kill-session -t aether-mc 2>/dev/null || true
    tmux new-session -d -s aether-mc "bash -c 'cd \"$SCRIPT_DIR/server\" && ./run-server.sh; exec bash'"

    echo -e "\n${GREEN}===================================================================${NC}"
    echo -e "${GREEN}   LES DEUX SERVICES TOURNENT EN ARRIERE-PLAN DANS TMUX !${NC}"
    echo -e "${GREEN}===================================================================${NC}"
    echo -e "Commandes pour voir la console en direct :"
    echo -e "  - Voir la console Minecraft : ${YELLOW}tmux attach -t aether-mc${NC}"
    echo -e "    ${CYAN}(Pour quitter sans fermer le serveur : Ctrl+B puis appuyez sur D)${NC}"
    echo -e "  - Voir les logs du Web       : ${YELLOW}tmux attach -t aether-web${NC}"
    echo -e "  - Arreter les deux services : ${YELLOW}./stop-all.sh${NC}"

elif command -v screen >/dev/null 2>&1; then
    echo -e "${CYAN}[1/2] Demarrage du Web Panel dans screen 'aether-web'...${NC}"
    screen -dmS aether-web bash -c "cd \"$SCRIPT_DIR/web\" && \"$PYTHON_BIN\" -u app.py"

    echo -e "${CYAN}[2/2] Demarrage du serveur Minecraft dans screen 'aether-mc'...${NC}"
    screen -dmS aether-mc bash -c "cd \"$SCRIPT_DIR/server\" && ./run-server.sh"

    echo -e "\n${GREEN}===================================================================${NC}"
    echo -e "${GREEN}   LES DEUX SERVICES TOURNENT EN ARRIERE-PLAN DANS SCREEN !${NC}"
    echo -e "${GREEN}===================================================================${NC}"
    echo -e "  - Voir la console Minecraft : ${YELLOW}screen -r aether-mc${NC}"
    echo -e "    ${CYAN}(Pour detacher sans fermer : Ctrl+A puis D)${NC}"
    echo -e "  - Arreter les deux services : ${YELLOW}./stop-all.sh${NC}"

else
    echo -e "${YELLOW}[*] tmux/screen non detectes. Lancement en arriere-plan avec redirection des logs...${NC}"
    mkdir -p logs
    nohup "$PYTHON_BIN" -u web/app.py > logs/web.log 2>&1 &
    echo $! > .web.pid
    echo -e "${GREEN}[OK] Web demarre (PID: $(cat .web.pid), logs: logs/web.log)${NC}"

    cd server
    nohup ./run-server.sh > ../logs/minecraft.log 2>&1 &
    echo $! > ../.mc.pid
    cd ..
    echo -e "${GREEN}[OK] Minecraft demarre (PID: $(cat .mc.pid), logs: logs/minecraft.log)${NC}"
fi

echo -e "\n${BLUE}===================================================================${NC}"
echo -e "  - Web Dashboard & Boutique : ${YELLOW}http://127.0.0.1:5000${NC}"
echo -e "  - Serveur Minecraft Paper : ${YELLOW}127.0.0.1:25565${NC}"
echo -e "  - Console RCON Securisee   : ${YELLOW}127.0.0.1:25575${NC}"
echo -e "${BLUE}===================================================================${NC}\n"
