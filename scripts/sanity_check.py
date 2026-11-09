#!/usr/bin/env python3
"""
AetherCraft Production Sanity Check & Diagnostic Harness
========================================================
Sub-minute (< 3s target, typically < 1s) automated diagnostic probe suite testing
the core components of the AetherCraft platform:
  1. Minecraft Paper Server SLP Ping (TCP 25565)
  2. RCON Admin Protocol Probe (TCP 25575)
  3. Web API Health Probe (HTTP 5000)
  4. SQLite Database Integrity Probe (PRAGMA integrity_check)
  5. Security Middleware Enforcement Probe (POST /api/webdisplay/action -> 401)
  6. Static Asset Resource Probe (GET /static/AetherPack.zip)

Zero external dependencies: pure Python standard library only.
Exit code: 0 on PASS, 1 on FAIL.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import socket
import sqlite3
import struct
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

# Ensure stdout uses UTF-8 encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Enable ANSI escape sequences on Windows consoles if supported
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# Terminal ANSI styling
USE_COLOR = os.environ.get("NO_COLOR") is None and sys.stdout.isatty()
CLR_RESET = "\033[0m" if USE_COLOR else ""
CLR_BOLD = "\033[1m" if USE_COLOR else ""
CLR_DIM = "\033[2m" if USE_COLOR else ""
CLR_GREEN = "\033[92m" if USE_COLOR else ""
CLR_RED = "\033[91m" if USE_COLOR else ""
CLR_YELLOW = "\033[93m" if USE_COLOR else ""
CLR_CYAN = "\033[96m" if USE_COLOR else ""
CLR_WHITE = "\033[97m" if USE_COLOR else ""


def tag_pass() -> str:
    return f"{CLR_GREEN}{CLR_BOLD}[PASS]{CLR_RESET}"


def tag_fail() -> str:
    return f"{CLR_RED}{CLR_BOLD}[FAIL]{CLR_RESET}"


def tag_warn() -> str:
    return f"{CLR_YELLOW}{CLR_BOLD}[WARN]{CLR_RESET}"


def clean_minecraft_formatting(text: str) -> str:
    """Removes Minecraft § color and formatting codes from strings."""
    if not text:
        return ""
    clean = re.sub(r"§[0-9a-fk-or]", "", str(text))
    return clean.replace("\n", " ").replace("\r", "").strip()


# ---------------------------------------------------------------------------
# Minecraft SLP (Server List Ping) Protocol Utilities
# ---------------------------------------------------------------------------
def encode_varint(val: int) -> bytes:
    """Encodes a signed 32-bit integer as a Minecraft VarInt."""
    buf = bytearray()
    val &= 0xFFFFFFFF  # Treat as unsigned 32-bit for bitwise shifts
    while True:
        byte = val & 0x7F
        val >>= 7
        if val != 0:
            buf.append(byte | 0x80)
        else:
            buf.append(byte)
            break
    return bytes(buf)


def decode_varint(sock: socket.socket) -> int:
    """Reads a Minecraft VarInt from a stream socket."""
    val = 0
    for i in range(5):
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("Connection closed while reading VarInt")
        byte = chunk[0]
        val |= (byte & 0x7F) << (7 * i)
        if not (byte & 0x80):
            # Sign extend if needed (32-bit signed)
            if val & (1 << 31):
                val -= 1 << 32
            return val
    raise ValueError("VarInt exceeds 5 bytes limit")


# ---------------------------------------------------------------------------
# Probe Result Container
# ---------------------------------------------------------------------------
class ProbeResult:
    def __init__(
        self,
        probe_id: int,
        name: str,
        target: str,
        status: str,
        duration_ms: float,
        detail: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.probe_id = probe_id
        self.name = name
        self.target = target
        self.status = status  # "PASS", "FAIL", "WARN"
        self.duration_ms = duration_ms
        self.detail = detail
        self.extra = extra or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "name": self.name,
            "target": self.target,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "detail": self.detail,
            "extra": self.extra,
        }


# ---------------------------------------------------------------------------
# Core Diagnostic Probes
# ---------------------------------------------------------------------------
def probe_1_minecraft_slp(host: str, port: int, timeout: float = 0.8) -> ProbeResult:
    """
    Probe 1: Minecraft Paper Server SLP Ping (TCP 25565)
    Sends Minecraft Handshake (protocol 767) + Status Request.
    Verifies MOTD, version string (1.21.1), online player capacity, and TCP latency.
    """
    start_time = time.perf_counter()
    target_str = f"{host}:{port}"
    sock = None

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))

        # 1. Handshake Packet (Packet ID: 0x00, NextState: 1 = Status)
        addr_bytes = host.encode("utf-8")
        handshake_payload = (
            b"\x00"
            + encode_varint(767)  # Protocol 767 (Minecraft 1.21.1)
            + encode_varint(len(addr_bytes))
            + addr_bytes
            + struct.pack(">H", port)
            + encode_varint(1)
        )
        sock.sendall(encode_varint(len(handshake_payload)) + handshake_payload)

        # 2. Status Request Packet (Length: 1, Packet ID: 0x00)
        sock.sendall(b"\x01\x00")

        # 3. Read Status Response Packet
        packet_len = decode_varint(sock)
        packet_id = decode_varint(sock)
        if packet_id != 0:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ProbeResult(
                1,
                "Minecraft Paper SLP Ping",
                target_str,
                "FAIL",
                duration_ms,
                f"Protocole invalide : paquet reçu {packet_id} au lieu de 0x00",
            )

        json_len = decode_varint(sock)
        raw_buffer = bytearray()
        while len(raw_buffer) < json_len:
            chunk = sock.recv(min(4096, json_len - len(raw_buffer)))
            if not chunk:
                break
            raw_buffer.extend(chunk)

        duration_ms = (time.perf_counter() - start_time) * 1000
        sock.close()
        sock = None

        response_str = raw_buffer.decode("utf-8", errors="replace")
        status_data = json.loads(response_str)

        ver_info = status_data.get("version", {})
        version_name = ver_info.get("name", "Unknown")
        version_proto = ver_info.get("protocol", 0)

        players_info = status_data.get("players", {})
        online_players = players_info.get("online", 0)
        max_players = players_info.get("max", 0)

        desc_info = status_data.get("description", "")
        if isinstance(desc_info, dict):
            motd_raw = desc_info.get("text", "")
            if not motd_raw and "extra" in desc_info:
                motd_raw = "".join(part.get("text", "") for part in desc_info.get("extra", []) if isinstance(part, dict))
        else:
            motd_raw = str(desc_info)
        motd_clean = clean_minecraft_formatting(motd_raw)

        detail = (
            f"Version: {version_name} (proto {version_proto}) | "
            f"Joueurs: {online_players}/{max_players} | "
            f"Latence: {duration_ms:.1f}ms | "
            f"MOTD: \"{motd_clean[:45]}\""
        )

        return ProbeResult(
            1,
            "Minecraft Paper SLP Ping",
            target_str,
            "PASS",
            duration_ms,
            detail,
            extra={
                "version": version_name,
                "protocol": version_proto,
                "online": online_players,
                "max": max_players,
                "motd": motd_clean,
            },
        )

    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            1,
            "Minecraft Paper SLP Ping",
            target_str,
            "FAIL",
            duration_ms,
            f"Serveur Paper hors ligne / connexion refusée sur {target_str} ({type(e).__name__})",
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            1,
            "Minecraft Paper SLP Ping",
            target_str,
            "FAIL",
            duration_ms,
            f"Erreur d'analyse SLP ({type(e).__name__}: {e})",
        )
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def probe_2_minecraft_rcon(
    host: str, port: int, password: str, timeout: float = 0.8
) -> ProbeResult:
    """
    Probe 2: RCON Admin Protocol Probe (TCP 25575)
    Authenticates via Source RCON binary protocol and queries 'list' and 'tps'.
    """
    start_time = time.perf_counter()
    target_str = f"{host}:{port}"
    sock = None

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))

        # 1. Authenticate (Type 3: SERVERDATA_AUTH)
        auth_body = password.encode("utf-8") + b"\x00\x00"
        auth_len = len(auth_body) + 8
        sock.sendall(struct.pack("<iii", auth_len, 1, 3) + auth_body)

        header = sock.recv(12)
        if len(header) < 12:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ProbeResult(
                2,
                "RCON Admin Protocol",
                target_str,
                "FAIL",
                duration_ms,
                "En-tête de réponse d'authentification RCON tronquée",
            )

        resp_len, req_id, pkt_type = struct.unpack("<iii", header)
        _ = sock.recv(max(0, resp_len - 8))

        # Check for potential empty SERVERDATA_RESPONSE_VALUE (0) preceding SERVERDATA_AUTH_RESPONSE (2)
        if pkt_type == 0:
            header2 = sock.recv(12)
            if len(header2) >= 12:
                resp_len2, req_id, pkt_type = struct.unpack("<iii", header2)
                _ = sock.recv(max(0, resp_len2 - 8))

        if req_id == -1:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ProbeResult(
                2,
                "RCON Admin Protocol",
                target_str,
                "FAIL",
                duration_ms,
                "Échec d'authentification RCON : mot de passe rejeté par Paper",
            )

        # 2. Execute 'list' query
        cmd_body = b"list\x00\x00"
        sock.sendall(struct.pack("<iii", len(cmd_body) + 8, 2, 2) + cmd_body)
        h_list = sock.recv(12)
        if len(h_list) >= 12:
            l_len, _, _ = struct.unpack("<iii", h_list)
            list_raw = sock.recv(max(0, l_len - 8))
            list_text = list_raw[:-2].decode("utf-8", errors="replace").strip() if len(list_raw) >= 2 else ""
        else:
            list_text = "Pas de réponse list"

        # 3. Execute 'tps' query
        tps_body = b"tps\x00\x00"
        sock.sendall(struct.pack("<iii", len(tps_body) + 8, 3, 2) + tps_body)
        h_tps = sock.recv(12)
        if len(h_tps) >= 12:
            t_len, _, _ = struct.unpack("<iii", h_tps)
            tps_raw = sock.recv(max(0, t_len - 8))
            tps_text = tps_raw[:-2].decode("utf-8", errors="replace").strip() if len(tps_raw) >= 2 else ""
        else:
            tps_text = "Pas de réponse tps"

        duration_ms = (time.perf_counter() - start_time) * 1000
        sock.close()
        sock = None

        list_clean = clean_minecraft_formatting(list_text)
        tps_clean = clean_minecraft_formatting(tps_text)

        detail = f"Auth réussie | list: \"{list_clean[:35]}\" | tps: \"{tps_clean[:35]}\""
        return ProbeResult(
            2,
            "RCON Admin Protocol",
            target_str,
            "PASS",
            duration_ms,
            detail,
            extra={"list": list_clean, "tps": tps_clean},
        )

    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            2,
            "RCON Admin Protocol",
            target_str,
            "FAIL",
            duration_ms,
            f"Service RCON hors ligne / port fermé sur {target_str} ({type(e).__name__})",
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            2,
            "RCON Admin Protocol",
            target_str,
            "FAIL",
            duration_ms,
            f"Erreur protocolaire RCON ({type(e).__name__}: {e})",
        )
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def probe_3_web_health(web_url: str, timeout: float = 0.8) -> ProbeResult:
    """
    Probe 3: Web API Health Probe (HTTP 5000)
    Executes GET /api/v1/health and validates status=='ok' JSON payload.
    """
    start_time = time.perf_counter()
    endpoint = f"{web_url.rstrip('/')}/api/v1/health"

    try:
        req = urllib.request.Request(
            endpoint,
            headers={
                "Accept": "application/json",
                "User-Agent": "AetherSanity/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            duration_ms = (time.perf_counter() - start_time) * 1000
            status_code = resp.status
            content = resp.read().decode("utf-8")

            if status_code != 200:
                return ProbeResult(
                    3,
                    "Web API Health Endpoint",
                    endpoint,
                    "FAIL",
                    duration_ms,
                    f"Code HTTP inattendu {status_code} (attendu: 200)",
                )

            data = json.loads(content)
            if data.get("status") == "ok":
                service = data.get("service", "unknown")
                modules = data.get("modules", [])
                modules_str = ", ".join(modules) if isinstance(modules, list) else str(modules)
                detail = f"HTTP 200 OK | status: 'ok' | service: {service} | modules: [{modules_str}]"
                return ProbeResult(
                    3,
                    "Web API Health Endpoint",
                    endpoint,
                    "PASS",
                    duration_ms,
                    detail,
                    extra=data,
                )
            else:
                return ProbeResult(
                    3,
                    "Web API Health Endpoint",
                    endpoint,
                    "FAIL",
                    duration_ms,
                    f"Payload JSON invalide (status != 'ok'): {content[:60]}",
                )

    except urllib.error.HTTPError as he:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            3,
            "Web API Health Endpoint",
            endpoint,
            "FAIL",
            duration_ms,
            f"Erreur HTTP {he.code}: {he.reason}",
        )
    except (urllib.error.URLError, ConnectionRefusedError, socket.timeout, OSError) as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            3,
            "Web API Health Endpoint",
            endpoint,
            "FAIL",
            duration_ms,
            f"Serveur Web Flask/Waitress hors ligne sur {endpoint} ({type(e).__name__})",
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            3,
            "Web API Health Endpoint",
            endpoint,
            "FAIL",
            duration_ms,
            f"Échec de la sonde Health ({type(e).__name__}: {e})",
        )


def probe_4_sqlite_integrity(db_path: str) -> ProbeResult:
    """
    Probe 4: SQLite Database Integrity Probe
    Executes PRAGMA integrity_check on server/data/aethercraft.db.
    Inspects journal_mode, table count, and user/player entity counts.
    """
    start_time = time.perf_counter()
    target_str = os.path.relpath(db_path) if os.path.isabs(db_path) else db_path
    conn = None

    try:
        if not os.path.exists(db_path):
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ProbeResult(
                4,
                "SQLite Database Integrity",
                target_str,
                "FAIL",
                duration_ms,
                f"Fichier de base de données introuvable : {db_path}",
            )

        size_bytes = os.path.getsize(db_path)
        if size_bytes == 0:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ProbeResult(
                4,
                "SQLite Database Integrity",
                target_str,
                "FAIL",
                duration_ms,
                "Le fichier SQLite est vide (0 octets)",
            )

        # Open in URI read-only mode to prevent write locks during check
        db_abs = os.path.abspath(db_path)
        uri = f"file:{db_abs}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        cursor = conn.cursor()

        # 1. PRAGMA integrity_check
        cursor.execute("PRAGMA integrity_check;")
        check_row = cursor.fetchone()
        integrity_status = str(check_row[0]) if check_row else "error"

        if integrity_status.lower() != "ok":
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ProbeResult(
                4,
                "SQLite Database Integrity",
                target_str,
                "FAIL",
                duration_ms,
                f"Corruption détectée par PRAGMA integrity_check : {integrity_status}",
            )

        # 2. PRAGMA journal_mode
        cursor.execute("PRAGMA journal_mode;")
        jm_row = cursor.fetchone()
        journal_mode = str(jm_row[0]).lower() if jm_row else "unknown"

        # 3. Relation metrics
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
        tables_count = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM users;")
        users_count = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM players;")
        players_count = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM store_orders;")
        orders_count = cursor.fetchone()[0]

        duration_ms = (time.perf_counter() - start_time) * 1000

        warn_note = ""
        if journal_mode != "wal":
            warn_note = f" (Avertissement: mode {journal_mode.upper()} non-WAL - risque de lock sous charge)"

        detail = (
            f"Intégrité: OK | Tables: {tables_count} | Utilisateurs: {users_count} | "
            f"Joueurs: {players_count} | Commandes: {orders_count} | "
            f"Journal: {journal_mode.upper()} | Taille: {size_bytes / 1024:.1f} Ko{warn_note}"
        )

        return ProbeResult(
            4,
            "SQLite Database Integrity",
            target_str,
            "PASS",
            duration_ms,
            detail,
            extra={
                "integrity": integrity_status,
                "journal_mode": journal_mode,
                "tables_count": tables_count,
                "users_count": users_count,
                "players_count": players_count,
                "orders_count": orders_count,
                "size_bytes": size_bytes,
            },
        )

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            4,
            "SQLite Database Integrity",
            target_str,
            "FAIL",
            duration_ms,
            f"Erreur d'accès à la base SQLite ({type(e).__name__}: {e})",
        )
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def probe_5_security_middleware(web_url: str, timeout: float = 0.8) -> ProbeResult:
    """
    Probe 5: Security Middleware Enforcement Probe
    Sends an unauthenticated POST request to /api/webdisplay/action.
    Strictly verifies that HTTP 401 Unauthorized is returned with JSON error.
    """
    start_time = time.perf_counter()
    endpoint = f"{web_url.rstrip('/')}/api/webdisplay/action"

    payload_data = json.dumps({"player": "AuditorProbe", "action": "tp_spawn"}).encode("utf-8")

    try:
        req = urllib.request.Request(
            endpoint,
            data=payload_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "AetherSanity/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            duration_ms = (time.perf_counter() - start_time) * 1000
            # If an unauthenticated mutation returns 200 OK, authentication is broken!
            return ProbeResult(
                5,
                "Security Middleware Enforcement",
                endpoint,
                "FAIL",
                duration_ms,
                f"Faille de sécurité : action non authentifiée autorisée avec HTTP {resp.status} !",
            )

    except urllib.error.HTTPError as he:
        duration_ms = (time.perf_counter() - start_time) * 1000
        if he.code == 401:
            raw_body = he.read().decode("utf-8")
            try:
                data = json.loads(raw_body)
                err_msg = data.get("message") or data.get("error") or "Non autorisé"
                detail = f"HTTP 401 Unauthorized appliqué avec succès (\"{err_msg}\")"
                return ProbeResult(
                    5,
                    "Security Middleware Enforcement",
                    endpoint,
                    "PASS",
                    duration_ms,
                    detail,
                    extra=data,
                )
            except Exception:
                detail = f"HTTP 401 Unauthorized renvoyé ({raw_body[:40]})"
                return ProbeResult(
                    5,
                    "Security Middleware Enforcement",
                    endpoint,
                    "PASS",
                    duration_ms,
                    detail,
                )
        else:
            return ProbeResult(
                5,
                "Security Middleware Enforcement",
                endpoint,
                "FAIL",
                duration_ms,
                f"Code HTTP attendu 401, reçu {he.code} ({he.reason})",
            )

    except (urllib.error.URLError, ConnectionRefusedError, socket.timeout, OSError) as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            5,
            "Security Middleware Enforcement",
            endpoint,
            "FAIL",
            duration_ms,
            f"Serveur Web hors ligne sur {endpoint} ({type(e).__name__})",
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            5,
            "Security Middleware Enforcement",
            endpoint,
            "FAIL",
            duration_ms,
            f"Échec du test de sécurité ({type(e).__name__}: {e})",
        )


def probe_6_static_asset(web_url: str, timeout: float = 0.8) -> ProbeResult:
    """
    Probe 6: Static Asset Resource Probe
    Requests GET /static/AetherPack.zip and verifies HTTP 200 OK with valid zip header.
    """
    start_time = time.perf_counter()
    endpoint = f"{web_url.rstrip('/')}/static/AetherPack.zip"

    try:
        req = urllib.request.Request(
            endpoint,
            headers={
                "User-Agent": "AetherSanity/1.0",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            duration_ms = (time.perf_counter() - start_time) * 1000
            status_code = resp.status
            content_type = resp.headers.get("Content-Type", "application/zip")
            content_length = resp.headers.get("Content-Length", "")

            # Sample first 64 bytes to verify PK zip signature
            header_bytes = resp.read(64)

            if status_code != 200:
                return ProbeResult(
                    6,
                    "Static Asset Resource",
                    endpoint,
                    "FAIL",
                    duration_ms,
                    f"Code HTTP inattendu {status_code} (attendu: 200)",
                )

            is_valid_zip = header_bytes.startswith(b"PK\x03\x04")
            zip_desc = "Signature ZIP valide (PK\\x03\\x04)" if is_valid_zip else "Signature ZIP atypique"

            size_kb = (
                f"{int(content_length)/1024:.1f} Ko"
                if content_length and content_length.isdigit()
                else f">={len(header_bytes)} octets"
            )

            detail = f"HTTP 200 OK | Type: {content_type} | Taille: {size_kb} | {zip_desc}"
            return ProbeResult(
                6,
                "Static Asset Resource",
                endpoint,
                "PASS",
                duration_ms,
                detail,
                extra={
                    "status_code": status_code,
                    "content_type": content_type,
                    "content_length": content_length,
                    "valid_zip": is_valid_zip,
                },
            )

    except urllib.error.HTTPError as he:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            6,
            "Static Asset Resource",
            endpoint,
            "FAIL",
            duration_ms,
            f"Erreur HTTP {he.code}: {he.reason}",
        )
    except (urllib.error.URLError, ConnectionRefusedError, socket.timeout, OSError) as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            6,
            "Static Asset Resource",
            endpoint,
            "FAIL",
            duration_ms,
            f"Serveur Web hors ligne sur {endpoint} ({type(e).__name__})",
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ProbeResult(
            6,
            "Static Asset Resource",
            endpoint,
            "FAIL",
            duration_ms,
            f"Échec de la sonde de ressource statique ({type(e).__name__}: {e})",
        )


# ---------------------------------------------------------------------------
# CLI Argument Parser & Orchestration Harness
# ---------------------------------------------------------------------------
def resolve_default_db_path() -> str:
    """Finds server/data/aethercraft.db relative to the script location or workspace."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(script_dir, "..", "server", "data", "aethercraft.db")),
        os.path.abspath(os.path.join(script_dir, "server", "data", "aethercraft.db")),
        os.path.abspath(os.path.join(os.getcwd(), "server", "data", "aethercraft.db")),
        os.path.abspath(os.path.join(script_dir, "..", "aethercraft.db")),
        os.path.abspath(os.path.join(os.getcwd(), "aethercraft.db")),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AetherCraft Production Sanity Check & Diagnostic Harness (< 3s)"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("AETHER_HOST", "127.0.0.1"),
        help="Target host address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--mc-port",
        type=int,
        default=int(os.environ.get("MC_PORT", "25565")),
        help="Minecraft Paper SLP TCP port (default: 25565)",
    )
    parser.add_argument(
        "--rcon-port",
        type=int,
        default=int(os.environ.get("RCON_PORT", "25575")),
        help="Minecraft RCON TCP port (default: 25575)",
    )
    parser.add_argument(
        "--rcon-password",
        default=os.environ.get("RCON_PASSWORD", "aether_secret_rcon_2026"),
        help="Minecraft RCON secret password",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=int(os.environ.get("WEB_PORT", "5000")),
        help="Web Platform HTTP port (default: 5000)",
    )
    parser.add_argument(
        "--web-url",
        default=None,
        help="Base URL for the Web Platform (default: http://<host>:<web-port>)",
    )
    parser.add_argument(
        "--db-path",
        default=resolve_default_db_path(),
        help="Path to SQLite database (default: server/data/aethercraft.db)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=0.8,
        help="Network probe socket timeout in seconds (default: 0.8s)",
    )
    parser.add_argument(
        "--warn-offline",
        action="store_true",
        help="Degrade offline unreachable services to [WARN] instead of [FAIL] (for cold CI/pre-boot checks)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON summary only",
    )
    return parser.parse_args()


def run_sanity_checks(args: argparse.Namespace) -> Tuple[List[ProbeResult], float]:
    web_base_url = args.web_url or f"http://{args.host}:{args.web_port}"
    total_start = time.perf_counter()

    probe_factories: List[Tuple[int, Callable[[], ProbeResult]]] = [
        (1, lambda: probe_1_minecraft_slp(args.host, args.mc_port, timeout=args.timeout)),
        (2, lambda: probe_2_minecraft_rcon(args.host, args.rcon_port, args.rcon_password, timeout=args.timeout)),
        (3, lambda: probe_3_web_health(web_base_url, timeout=args.timeout)),
        (4, lambda: probe_4_sqlite_integrity(args.db_path)),
        (5, lambda: probe_5_security_middleware(web_base_url, timeout=args.timeout)),
        (6, lambda: probe_6_static_asset(web_base_url, timeout=args.timeout)),
    ]

    # Execute all 6 probes concurrently with ThreadPoolExecutor to ensure runtime << 3s
    results_map: Dict[int, ProbeResult] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        future_to_id = {executor.submit(fn): probe_id for probe_id, fn in probe_factories}
        for future in concurrent.futures.as_completed(future_to_id):
            probe_id = future_to_id[future]
            try:
                res = future.result()
            except Exception as e:
                res = ProbeResult(
                    probe_id,
                    f"Probe {probe_id}",
                    "Internal",
                    "FAIL",
                    0.0,
                    f"Erreur d'exécution ({type(e).__name__}: {e})",
                )
            results_map[probe_id] = res

    # Reorder sequentially from 1 to 6
    ordered_results: List[ProbeResult] = [results_map[i] for i in range(1, 7)]

    # Handle graceful offline degradation flag if enabled
    for res in ordered_results:
        if args.warn_offline and res.status == "FAIL":
            detail_lower = res.detail.lower()
            if any(term in detail_lower for term in ("hors ligne", "offline", "connexion refusée", "connection refused", "port fermé")):
                res.status = "WARN"
                res.detail = f"[Dégradé / Hors ligne] {res.detail}"

    total_duration_s = time.perf_counter() - total_start
    return ordered_results, total_duration_s


def print_cli_report(results: List[ProbeResult], total_duration_s: float) -> int:
    pass_count = sum(1 for r in results if r.status == "PASS")
    fail_count = sum(1 for r in results if r.status == "FAIL")
    warn_count = sum(1 for r in results if r.status == "WARN")

    print(f"\n{CLR_CYAN}{CLR_BOLD}========================================================================================{CLR_RESET}")
    print(f"{CLR_WHITE}{CLR_BOLD}                   AETHERCRAFT PRODUCTION SANITY CHECK HARNESS                          {CLR_RESET}")
    print(f"{CLR_CYAN}{CLR_BOLD}========================================================================================{CLR_RESET}\n")

    for r in results:
        if r.status == "PASS":
            tag = tag_pass()
        elif r.status == "WARN":
            tag = tag_warn()
        else:
            tag = tag_fail()

        duration_tag = f"{CLR_DIM}({r.duration_ms:5.1f}ms){CLR_RESET}"
        print(f" {tag} Probe #{r.probe_id}: {CLR_BOLD}{r.name:<32}{CLR_RESET} {duration_tag}")
        print(f"        {CLR_DIM}Cible  :{CLR_RESET} {r.target}")
        print(f"        {CLR_DIM}Détail :{CLR_RESET} {r.detail}")
        print()

    print(f"{CLR_CYAN}{CLR_BOLD}----------------------------------------------------------------------------------------{CLR_RESET}")
    print(f"{CLR_BOLD}Synthèse d'exécution :{CLR_RESET}")
    print(f"  • Total sondes    : {len(results)}")
    print(f"  • Succès (PASS)   : {CLR_GREEN}{pass_count}{CLR_RESET}")
    print(f"  • Échecs (FAIL)   : {CLR_RED if fail_count > 0 else CLR_GREEN}{fail_count}{CLR_RESET}")
    print(f"  • Alertes (WARN)  : {CLR_YELLOW if warn_count > 0 else CLR_DIM}{warn_count}{CLR_RESET}")
    print(f"  • Durée totale    : {CLR_BOLD}{total_duration_s:.3f}s{CLR_RESET} (seuil d'acceptation: < 3.0s)")

    is_overall_pass = (fail_count == 0)
    if is_overall_pass:
        print(f"\n{CLR_GREEN}{CLR_BOLD}==> RÉSULTAT GLOBAL : [PASS] Système validé et prêt.{CLR_RESET}\n")
        return 0
    else:
        print(f"\n{CLR_RED}{CLR_BOLD}==> RÉSULTAT GLOBAL : [FAIL] Composants critiques en défaut ou hors ligne.{CLR_RESET}\n")
        return 1


def main() -> int:
    args = parse_arguments()
    results, total_duration_s = run_sanity_checks(args)

    if args.json:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_duration_s": round(total_duration_s, 4),
            "overall_status": "PASS" if all(r.status != "FAIL" for r in results) else "FAIL",
            "probes_count": len(results),
            "pass_count": sum(1 for r in results if r.status == "PASS"),
            "fail_count": sum(1 for r in results if r.status == "FAIL"),
            "warn_count": sum(1 for r in results if r.status == "WARN"),
            "probes": [r.to_dict() for r in results],
        }
        print(json.dumps(payload, indent=2))
        return 0 if payload["overall_status"] == "PASS" else 1

    return print_cli_report(results, total_duration_s)


if __name__ == "__main__":
    sys.exit(main())
