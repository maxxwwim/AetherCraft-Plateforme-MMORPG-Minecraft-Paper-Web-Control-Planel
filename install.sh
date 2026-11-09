#!/usr/bin/env bash
# ==============================================================================
# AetherCraft - Script d'installation automatique pour Linux (Ubuntu / Debian / CentOS / Rocky)
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}===================================================================${NC}"
echo -e "${GREEN}   AETHERCRAFT // INSTALLATEUR LINUX AUTOMATIQUE${NC}"
echo -e "${BLUE}===================================================================${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Detection des privileges / gestionnaire de paquets
echo -e "\n${YELLOW}[1/5] Detection de l'environnement Linux et des paquets...${NC}"

install_packages() {
    if command -v apt-get >/dev/null 2>&1; then
        echo -e "${GREEN}[*] Systeme Debian/Ubuntu detecte (apt-get).${NC}"
        sudo apt-get update -y
        sudo apt-get install -y openjdk-21-jre-headless python3 python3-pip python3-venv tmux curl sqlite3
    elif command -v dnf >/dev/null 2>&1; then
        echo -e "${GREEN}[*] Systeme RHEL/CentOS/Rocky detecte (dnf).${NC}"
        sudo dnf install -y java-21-openjdk-headless python3 python3-pip tmux curl sqlite
    else
        echo -e "${YELLOW}[!] Gestionnaire non reconnu. Assurez-vous d'avoir Java 21, Python 3 et tmux installes.${NC}"
    fi
}

if ! command -v java >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
    echo -e "${YELLOW}[*] Installation des dependances systeme necessaires...${NC}"
    install_packages
fi

# 2. Verification Java 21
echo -e "\n${YELLOW}[2/5] Verification de Java 21...${NC}"
JAVA_VERSION=$(java -version 2>&1 | head -n 1 | awk -F '"' '{print $2}' | cut -d'.' -f1)
if [ "$JAVA_VERSION" != "21" ]; then
    echo -e "${RED}[!] Java 21 n'est pas la version par defaut (detecte: $JAVA_VERSION).${NC}"
    echo -e "${YELLOW}[*] Tentative d'installation directe d'OpenJDK 21...${NC}"
    install_packages
fi
echo -e "${GREEN}[OK] Java 21 operationnel : $(java -version 2>&1 | head -n 1)${NC}"

# 3. Configuration de l'environnement Python
echo -e "\n${YELLOW}[3/5] Configuration de l'environnement Python Web (Flask/Waitress)...${NC}"
if [ ! -d "web/venv" ]; then
    echo -e "${YELLOW}[*] Creation du venv Python dans web/venv...${NC}"
    python3 -m venv web/venv
fi

echo -e "${YELLOW}[*] Installation des paquets Python depuis web/requirements.txt...${NC}"
web/venv/bin/pip install --upgrade pip
web/venv/bin/pip install -r web/requirements.txt
echo -e "${GREEN}[OK] Environnement Python pret !${NC}"

# Initialisation de la base SQLite
echo -e "${YELLOW}[*] Initialisation de la base de donnees SQLite unifiee...${NC}"
mkdir -p server/data
web/venv/bin/python -c "import sys, os; sys.path.insert(0, 'web'); from services.database import init_database, DB_PATH; init_database(); print(f'[OK] DB initialisee : {DB_PATH}')"

# 4. Acceptation de l'EULA Minecraft et validation du serveur
echo -e "\n${YELLOW}[4/5] Configuration du serveur Minecraft Paper...${NC}"
mkdir -p server
if [ ! -f "server/server.jar" ]; then
    if [ -f "server/paper-1.21.1-133.jar" ]; then
        cp server/paper-1.21.1-133.jar server/server.jar
        echo -e "${GREEN}[OK] paper-1.21.1-133.jar copie vers server.jar.${NC}"
    else
        echo -e "${YELLOW}[*] Telechargement automatique de Paper 1.21.1 Build 133...${NC}"
        curl -sSLo server/server.jar https://api.papermc.io/v2/projects/paper/versions/1.21.1/builds/133/downloads/paper-1.21.1-133.jar
        echo -e "${GREEN}[OK] Paper 1.21.1 telecharge avec succes.${NC}"
    fi
fi
echo "eula=true" > server/eula.txt
echo -e "${GREEN}[OK] EULA Minecraft acceptee (server/eula.txt).${NC}"

# 5. Droits d'execution sur les scripts
echo -e "\n${YELLOW}[5/5] Attribution des permissions d'execution aux scripts...${NC}"
chmod +x *.sh 2>/dev/null || true
chmod +x server/*.sh 2>/dev/null || true
echo -e "${GREEN}[OK] Scripts executables configures.${NC}"

echo -e "\n${BLUE}===================================================================${NC}"
echo -e "${GREEN}   INSTALLATION TERMINEE AVEC SUCCES SUR LINUX !${NC}"
echo -e "${BLUE}===================================================================${NC}"
echo -e "Pour demarrer le serveur complet :"
echo -e "  ${YELLOW}./lunchall.sh${NC}"
echo -e "\nPour arreter tous les services :"
echo -e "  ${YELLOW}./stop-all.sh${NC}"
echo -e "${BLUE}===================================================================${NC}\n"
