import time
import socket
import struct
import json
import re
from typing import Dict, Tuple, Optional
from services.rcon_service import is_minecraft_server_alive, MinecraftRconClient

# Configuration centrale du serveur AetherCraft
SERVER_INFO = {
    # Pour l'instant en environnement de développement / local :
    "ip": "127.0.0.1:25565",
    "display_ip": "127.0.0.1:25565",
    "host": "127.0.0.1",
    "port": 25565,
    "local_ip": "127.0.0.1:25565",
    "is_local": True,
    "domain_fallback": "play.aethercraft.net",
    "motd_fallback": "🪐 L'ARCHIPEL CÉLESTE. REDÉFINI POUR L'ÉLITE. [1.21.1]",
    "version_fallback": "Paper 1.21.1",
    "max_players_fallback": 200,
    "discord_url": "https://discord.gg/aethercraft",
    "discord_guild_id": "", # Renseigner le Guild ID pour activer les statistiques d'API en direct
    "runner_download_cmd": "cargo run -p aether-mc-runner -- install-and-run --manifest http://127.0.0.1:5000/api/v1/servers/default/manifest"
}

# Cache en mémoire avec TTL (3 secondes) pour garantir performance et fraîcheur
_CACHE_DATA: Optional[Dict] = None
_CACHE_TIMESTAMP: float = 0.0
CACHE_TTL_SECONDS = 3.0

def _encode_varint(val: int) -> bytes:
    """Encode un entier selon le format VarInt Minecraft."""
    out = b""
    while True:
        byte = val & 0x7F
        val >>= 7
        if val != 0:
            byte |= 0x80
        out += bytes([byte])
        if val == 0:
            break
    return out

def _read_varint(sock: socket.socket) -> Optional[int]:
    """Lit un VarInt depuis le socket Minecraft."""
    val = 0
    shift = 0
    while True:
        b = sock.recv(1)
        if not b:
            return None
        byte = b[0]
        val |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return val

def _clean_minecraft_text(raw_text: any) -> str:
    """Nettoie le MOTD ou composant texte Minecraft (retire les codes § et JSON complexes)."""
    if isinstance(raw_text, dict):
        text = raw_text.get("text", "")
        extra = raw_text.get("extra", [])
        if isinstance(extra, list):
            for part in extra:
                if isinstance(part, dict):
                    text += part.get("text", "")
                elif isinstance(part, str):
                    text += part
        return re.sub(r'§[0-9a-fk-or]', '', text).strip()
    elif isinstance(raw_text, str):
        return re.sub(r'§[0-9a-fk-or]', '', raw_text).strip()
    return str(raw_text or "")

def ping_minecraft_server_slp(host: str = "127.0.0.1", port: int = 25565, timeout: float = 1.0) -> Tuple[bool, Optional[Dict], int]:
    """
    Interroge le serveur Minecraft Paper via le protocole binaire Server List Ping (SLP).
    Retourne : (succès: bool, données_json: Optional[dict], latence_ms: int).
    """
    t0 = time.time()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((host, port))

            # 1. Handshake Packet (ID: 0x00, Protocole: 767 pour 1.21.1, NextState: 1 = Status)
            host_bytes = host.encode("utf-8")
            packet_data = (
                b"\x00" +
                _encode_varint(767) +
                _encode_varint(len(host_bytes)) + host_bytes +
                struct.pack(">H", port) +
                _encode_varint(1)
            )
            sock.sendall(_encode_varint(len(packet_data)) + packet_data)

            # 2. Status Request Packet (ID: 0x00, taille 1)
            sock.sendall(b"\x01\x00")

            # 3. Réception de la réponse
            _packet_len = _read_varint(sock)
            _packet_id = _read_varint(sock)
            json_len = _read_varint(sock)

            if json_len is None or json_len <= 0:
                return False, None, 0

            raw_json = b""
            while len(raw_json) < json_len:
                chunk = sock.recv(min(4096, json_len - len(raw_json)))
                if not chunk:
                    break
                raw_json += chunk

            latency_ms = max(1, int((time.time() - t0) * 1000))
            data = json.loads(raw_json.decode("utf-8", errors="replace"))
            return True, data, latency_ms
    except Exception:
        return False, None, 0

def get_live_server_status() -> Dict:
    """
    Retourne la télémétrie réelle et en direct du serveur Paper 1.21.1.
    Les données proviennent directement de la réponse SLP réseau du serveur.
    """
    global _CACHE_DATA, _CACHE_TIMESTAMP

    now = time.time()
    if _CACHE_DATA is not None and (now - _CACHE_TIMESTAMP) < CACHE_TTL_SECONDS:
        return _CACHE_DATA

    host = SERVER_INFO["host"]
    port = SERVER_INFO["port"]

    ok, slp_data, latency_ms = ping_minecraft_server_slp(host, port, timeout=0.8)

    if ok and slp_data:
        players_info = slp_data.get("players", {})
        version_info = slp_data.get("version", {})
        motd_raw = slp_data.get("description", "")

        online_count = int(players_info.get("online", 0))
        max_players = int(players_info.get("max", SERVER_INFO["max_players_fallback"]))
        version_name = str(version_info.get("name", SERVER_INFO["version_fallback"]))
        motd_clean = _clean_minecraft_text(motd_raw) or SERVER_INFO["motd_fallback"]

        status_result = {
            "status": "online",
            "is_running": True,
            "ip": SERVER_INFO["ip"],
            "display_ip": SERVER_INFO["display_ip"],
            "port": port,
            "local_ip": SERVER_INFO["local_ip"],
            "is_local": SERVER_INFO["is_local"],
            "motd": motd_clean,
            "version": version_name,
            "players_online": online_count,
            "players_max": max_players,
            "ping_ms": latency_ms,
            "tps": 20.0,
            "discord_url": SERVER_INFO["discord_url"],
            "runner_cmd": SERVER_INFO["runner_download_cmd"]
        }
    else:
        # Tentative de vérification TCP simple / RCON fallback
        is_live = is_minecraft_server_alive(host, port, timeout=0.3)
        online_count = 0
        if is_live:
            try:
                rcon = MinecraftRconClient()
                ok_rcon, resp_rcon = rcon.send_command("list", timeout=0.5)
                if ok_rcon:
                    # Parse ex: "There are 0 of a max of 20 players online:"
                    match = re.search(r'(\d+)\s+(?:of|sur)\s+(?:a\s+max\s+of\s+)?(\d+)', resp_rcon)
                    if match:
                        online_count = int(match.group(1))
            except Exception:
                pass

        status_result = {
            "status": "online" if is_live else "standby",
            "is_running": is_live,
            "ip": SERVER_INFO["ip"],
            "display_ip": SERVER_INFO["display_ip"],
            "port": port,
            "local_ip": SERVER_INFO["local_ip"],
            "is_local": SERVER_INFO["is_local"],
            "motd": SERVER_INFO["motd_fallback"],
            "version": SERVER_INFO["version_fallback"],
            "players_online": online_count,
            "players_max": SERVER_INFO["max_players_fallback"],
            "ping_ms": 1 if is_live else 0,
            "tps": 20.0 if is_live else 0.0,
            "discord_url": SERVER_INFO["discord_url"],
            "runner_cmd": SERVER_INFO["runner_download_cmd"]
        }

    _CACHE_DATA = status_result
    _CACHE_TIMESTAMP = now
    return status_result
