import os
import socket
import struct
import datetime
import re
from typing import Tuple, Optional
from services.database import get_db_connection

RCON_HOST = os.environ.get("RCON_HOST", "127.0.0.1")
RCON_PORT = int(os.environ.get("RCON_PORT", "25575"))
RCON_PASSWORD = os.environ.get("RCON_PASSWORD", "aether_secret_rcon_2026")

# Types de paquets RCON Source / Minecraft
SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0

class MinecraftRconClient:
    """Client RCON officiel implémentant le protocole binaire Minecraft."""
    def __init__(self, host: str = RCON_HOST, port: int = RCON_PORT, password: str = RCON_PASSWORD):
        self.host = host
        self.port = port
        self.password = password

    def send_command(self, command: str, timeout: float = 0.25) -> Tuple[bool, str]:
        """
        Envoie une commande au serveur Minecraft via RCON.
        Retourne (Succès: bool, Réponse: str).
        """
        # Défense stricte contre l'injection de commandes arbitraires (CWE-78, CWE-88)
        if any(c in command for c in ("\r", "\n", "\x00", ";")):
            return False, "Rejet de commande : injection de saut de ligne ou séparateur détecté."

        if not is_minecraft_server_alive(self.host, self.port, timeout=0.1):
            return False, "Serveur Minecraft ou RCON non actif"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect((self.host, self.port))

                # 1. Authentification
                auth_pkt = self._encode_packet(1, SERVERDATA_AUTH, self.password)
                sock.sendall(auth_pkt)

                resp_id, resp_type, _ = self._read_packet(sock)
                if resp_id == -1:
                    return False, "Échec d'authentification RCON (mot de passe invalide)"

                # 2. Exécution de la commande
                cmd_pkt = self._encode_packet(2, SERVERDATA_EXECCOMMAND, command)
                sock.sendall(cmd_pkt)

                _, _, body = self._read_packet(sock)
                return True, body.strip()

        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            # Serveur hors-ligne ou port non joignable
            return False, f"Serveur injoignable ({e})"

    def _encode_packet(self, request_id: int, packet_type: int, body: str) -> bytes:
        payload = body.encode("utf-8") + b"\x00\x00"
        length = len(payload) + 8  # 4 bytes id + 4 bytes type
        return struct.pack("<iii", length, request_id, packet_type) + payload

    def _read_packet(self, sock: socket.socket) -> Tuple[int, int, str]:
        header = sock.recv(12)
        if len(header) < 12:
            return -1, -1, ""
        length, req_id, pkt_type = struct.unpack("<iii", header)
        remaining = length - 8
        body_bytes = b""
        while len(body_bytes) < remaining:
            chunk = sock.recv(min(4096, remaining - len(body_bytes)))
            if not chunk:
                break
            body_bytes += chunk
        # Découpe les 2 null bytes de fin
        body = body_bytes[:-2].decode("utf-8", errors="replace") if len(body_bytes) >= 2 else ""
        return req_id, pkt_type, body


rcon_client = MinecraftRconClient()

def execute_server_command(command: str, target_player: Optional[str] = None) -> Tuple[bool, str]:
    """
    Exécute une commande RCON en direct si le serveur tourne,
    sinon l'enregistre dans la file d'attente SQLite pour exécution différée.
    Valide strictement les entrées contre toute tentative d'injection.
    """
    # 1. Rejet absolu des injections de sauts de lignes et délimiteurs de commande
    if any(c in command for c in ("\r", "\n", "\x00", ";")):
        return False, "Rejet de commande : injection de saut de ligne ou séparateur détecté."

    # 2. Validation stricte du pseudo joueur cible si spécifié
    if target_player:
        clean_player = str(target_player).strip()
        if not re.match(r"^[a-zA-Z0-9_]{3,16}$", clean_player):
            return False, f"Rejet de commande : pseudo joueur invalide ({clean_player})."

    # 3. Whitelist des modèles de commande autorisés
    allowed_prefixes = (
        "broadcast ",
        "title ",
        "playsound ",
        "whitelist ",
        "op ",
        "lp user ",
        "aura ",
        "pet ",
        "store give ",
        "crate ",
        "booster give ",
        "cosmetics ",
        "teleport ",
        "execute as ",
        "give ",
        "say ",
        "msg ",
        "tell ",
    )
    cmd_clean = command.strip()
    if cmd_clean != "list" and not any(cmd_clean.startswith(prefix) for prefix in allowed_prefixes):
        return False, f"Rejet de commande : modèle de commande non autorisé."

    # Contrôle additionnel sur 'execute as'
    if cmd_clean.startswith("execute as "):
        parts = cmd_clean.split()
        if len(parts) >= 5 and parts[3] == "run":
            u_target = parts[2]
            if not re.match(r"^[a-zA-Z0-9_]{3,16}$", u_target):
                return False, f"Rejet de commande : nom de joueur invalide dans execute as ({u_target})."
            subcmd = " ".join(parts[4:])
            allowed_subcmds = {"spawn", "survie", "dungeon", "rtp", "banque", "pet", "cosmetics", "webdisplay close"}
            if subcmd not in allowed_subcmds:
                return False, f"Rejet de commande : sous-commande non autorisée ({subcmd})."
        else:
            return False, "Rejet de commande : format execute as invalide (attendu: execute as <joueur> run <sous-commande>)."

    success, response = rcon_client.send_command(command)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Enregistrement dans rcon_queue (SQLite)
    status = "EXECUTED" if success else "PENDING"
    executed_at = now if success else None

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO rcon_queue (command, target_player, status, created_at, executed_at)
                VALUES (?, ?, ?, ?, ?);
            """, (command, target_player, status, now, executed_at))
            conn.commit()
    except Exception as e:
        print(f"[WARN] Erreur persistance queue RCON : {e}")

    return success, response

def is_minecraft_server_alive(host: str = "127.0.0.1", port: int = 25565, timeout: float = 0.5) -> bool:
    """Vérifie si le socket Minecraft écoute sur le port cible."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return True
    except OSError:
        return False
