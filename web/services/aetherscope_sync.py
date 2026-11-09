"""
Service de synchronisation AetherScope MCP & conformité LocalGuard.
Assure l'interfaçage sécurisé entre AetherCraft et le moteur local AetherScope (127.0.0.1:3030).

Fonctionnalités :
- Sonde de santé (Health Check Probe : GET /api/health)
- Télémétrie du graphe architectural & version (GET /api/graph/version, GET /api/graph)
- Métadonnées et découverte des projets (GET /api/projects)
- Respect strict des contraintes LocalGuard (Host, Origin locale, Sec-Fetch-Site anti-CSRF)
- Synchronisation d'état opérationnel (Joueurs connectés, Alertes de sécurité Anti-Cheat, Statut TPS)
- Gestion des erreurs non-bloquante avec repli gracieux et journalisation
"""

import os
import json
import time
import socket
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List, Tuple

# Configuration du logger
logger = logging.getLogger("aetherscope_sync")

# Configuration par défaut
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3030
DEFAULT_TIMEOUT_SECONDS = 2.0
USER_AGENT = "AetherCraft-Sync/1.0"


def is_localguard_compliant(
    host: Optional[str],
    origin: Optional[str] = None,
    sec_fetch_site: Optional[str] = None,
    port: int = DEFAULT_PORT
) -> bool:
    """
    Vérifie la conformité d'une requête vis-à-vis des règles du middleware Rust LocalGuard.
    (crates/desktop-shell/src/local_guard.rs)
    
    Règles de conformité :
    1. Host obligatoire, strictement égal à l'une des adresses de bouclage sur le port cible :
       '127.0.0.1:<port>', 'localhost:<port>', '[::1]:<port>' (anti DNS-rebinding).
    2. Origin (si fourni) : doit débuter par 'http://' suivi de l'une des autorités locales (anti-CSRF).
    3. Sec-Fetch-Site (si fourni) : doit être 'same-origin' ou 'none' (rejet de 'cross-site' / 'same-site').
    """
    if not host:
        return False

    authorities = [
        f"127.0.0.1:{port}".lower(),
        f"localhost:{port}".lower(),
        f"[::1]:{port}".lower(),
    ]

    host_clean = host.strip().lower()
    if host_clean not in authorities:
        return False

    if origin is not None:
        origin_clean = origin.strip().lower()
        expected_origins = [f"http://{a}" for a in authorities]
        if origin_clean not in expected_origins:
            return False

    if sec_fetch_site is not None:
        site_clean = sec_fetch_site.strip().lower()
        if site_clean not in ("same-origin", "none"):
            return False

    return True


def build_localguard_headers(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, str]:
    """
    Génère les en-têtes HTTP strictement conformes à LocalGuard pour sécuriser
    toutes les requêtes vers le serveur AetherScope local.
    """
    authority = f"{host}:{port}"
    return {
        "Host": authority,
        "Origin": f"http://{authority}",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }


class AetherScopeClient:
    """
    Client HTTP résilient pour l'interface AetherScope MCP locale (Axum REST API sur 127.0.0.1:3030).
    Fournit un mode dégradé non-bloquant en cas d'indisponibilité temporaire du serveur AetherScope.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        custom_logger: Optional[logging.Logger] = None,
    ):
        self.host = host or os.environ.get("AETHERSCOPE_HOST", DEFAULT_HOST)
        self.port = int(port or os.environ.get("AETHERSCOPE_PORT", str(DEFAULT_PORT)))
        self.base_url = f"http://{self.host}:{self.port}"
        self.timeout = timeout
        self.log = custom_logger or logger

    def _get_headers(self, has_payload: bool = False) -> Dict[str, str]:
        headers = build_localguard_headers(self.host, self.port)
        if has_payload:
            headers["Content-Type"] = "application/json; charset=utf-8"
        return headers

    def send_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Envoie une requête HTTP conforme LocalGuard au serveur AetherScope local.
        Ne lève jamais d'exception non gérée vers l'appelant.
        """
        req_timeout = timeout if timeout is not None else self.timeout
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        url = f"{self.base_url}{endpoint}"

        data_bytes = None
        has_payload = False
        if payload is not None:
            has_payload = True
            try:
                data_bytes = json.dumps(payload).encode("utf-8")
            except Exception as e:
                self.log.error(f"[AetherScope] Erreur de sérialisation JSON: {e}")
                return {
                    "success": False,
                    "status_code": None,
                    "data": None,
                    "error": f"JSON serialization error: {e}",
                    "is_offline": False,
                }

        headers = self._get_headers(has_payload=has_payload)
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())

        try:
            with urllib.request.urlopen(req, timeout=req_timeout) as resp:
                status_code = resp.status
                raw_body = resp.read().decode("utf-8")
                try:
                    data = json.loads(raw_body) if raw_body else {}
                except json.JSONDecodeError:
                    data = raw_body

                return {
                    "success": 200 <= status_code < 300,
                    "status_code": status_code,
                    "data": data,
                    "error": None,
                    "is_offline": False,
                }

        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
            self.log.warning(f"[AetherScope] Rejet HTTP {e.code} sur {endpoint}: {err_msg}")
            return {
                "success": False,
                "status_code": e.code,
                "data": None,
                "error": f"HTTP {e.code}: {err_msg}",
                "is_offline": False,
            }

        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as e:
            self.log.debug(f"[AetherScope] Serveur non joignable sur {url} ({e})")
            return {
                "success": False,
                "status_code": None,
                "data": None,
                "error": str(e),
                "is_offline": True,
            }

        except Exception as e:
            self.log.error(f"[AetherScope] Erreur inattendue lors de la requête sur {url}: {e}")
            return {
                "success": False,
                "status_code": None,
                "data": None,
                "error": f"Unexpected error: {e}",
                "is_offline": False,
            }

    # =========================================================================
    # 1. Sondes de Santé & Version
    # =========================================================================

    def check_health(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Sonde de disponibilité du moteur AetherScope (GET /api/health).
        Retourne le statut en ligne et les informations de version.
        """
        res = self.send_request("GET", "/api/health", timeout=timeout)
        if res["success"] and isinstance(res["data"], dict):
            status = res["data"].get("status", "unknown")
            engine = res["data"].get("engine", "unknown")
            return {
                "online": status == "ok",
                "status": status,
                "engine": engine,
                "status_code": res["status_code"],
                "raw": res["data"],
            }
        return {
            "online": False,
            "status": "offline",
            "engine": None,
            "error": res["error"],
            "status_code": res["status_code"],
        }

    def is_alive(self, timeout: Optional[float] = 1.0) -> bool:
        """Indicateur booléen rapide de disponibilité du serveur AetherScope."""
        return self.check_health(timeout=timeout).get("online", False)

    def get_graph_version(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Récupère le compteur atomique de version du graphe architectural (GET /api/graph/version).
        """
        res = self.send_request("GET", "/api/graph/version", timeout=timeout)
        if res["success"] and isinstance(res["data"], dict):
            return {
                "success": True,
                "version": res["data"].get("version"),
                "online": True,
            }
        return {
            "success": False,
            "version": None,
            "online": False,
            "error": res["error"],
        }

    def get_graph_summary(self, timeout: Optional[float] = 3.0) -> Dict[str, Any]:
        """
        Récupère un résumé synthétique du graphe architectural AST (GET /api/graph).
        Compte le nombre de nœuds, relations et violations sans saturer la mémoire.
        """
        res = self.send_request("GET", "/api/graph", timeout=timeout)
        if res["success"] and isinstance(res["data"], dict):
            graph = res["data"]
            nodes = graph.get("nodes", [])
            edges = graph.get("edges", [])
            metadata = graph.get("metadata", {})
            return {
                "success": True,
                "online": True,
                "nodes_count": len(nodes),
                "edges_count": len(edges),
                "metadata": metadata,
            }
        return {
            "success": False,
            "online": False,
            "nodes_count": 0,
            "edges_count": 0,
            "error": res["error"],
        }

    # =========================================================================
    # 2. Métadonnées de Projets
    # =========================================================================

    def get_projects(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Récupère la liste des projets découverts par AetherScope (GET /api/projects).
        """
        res = self.send_request("GET", "/api/projects", timeout=timeout)
        if res["success"] and isinstance(res["data"], dict):
            return {
                "success": True,
                "online": True,
                "projects": res["data"].get("projects", []),
                "default_project": res["data"].get("default_project"),
            }
        return {
            "success": False,
            "online": False,
            "projects": [],
            "default_project": None,
            "error": res["error"],
        }

    def get_project_metadata(self, project_name: str = "aethercraft") -> Optional[Dict[str, Any]]:
        """
        Recherche les métadonnées d'un projet spécifique par son nom dans le registre AetherScope.
        """
        res = self.get_projects()
        if not res.get("success"):
            return None
        target = project_name.lower()
        for p in res.get("projects", []):
            if p.get("name", "").lower() == target:
                return p
        return None

    # =========================================================================
    # 3. Synchronisation d'État & Télémétrie Opérationnelle
    # =========================================================================

    def publish_telemetry(
        self,
        target: str,
        action: str,
        details: str,
        timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Émet un événement de télémétrie spatiale vers le Cockpit AetherScope (POST /api/ai/telemetry).
        Aligne la caméra WebGL et met à jour le HUD en temps réel.
        """
        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        payload = {
            "target": str(target),
            "action": str(action),
            "details": str(details),
            "timestamp": ts,
        }
        res = self.send_request("POST", "/api/ai/telemetry", payload=payload)
        return {
            "success": res["success"],
            "online": not res.get("is_offline", False),
            "is_offline": res.get("is_offline", False),
            "error": res.get("error"),
        }

    def send_cockpit_chat(
        self,
        text: str,
        sender: str = "AetherCraft-Security",
        target_symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Émet un message dans la console de chat Copilot d'AetherScope (POST /api/ai/chat).
        Permet d'afficher des alertes de sécurité directement dans le cockpit spatial.
        """
        payload = {
            "text": str(text),
            "sender": str(sender),
            "target_symbol": target_symbol,
        }
        res = self.send_request("POST", "/api/ai/chat", payload=payload)
        return {
            "success": res["success"],
            "online": not res.get("is_offline", False),
            "is_offline": res.get("is_offline", False),
            "error": res.get("error"),
        }

    def publish_security_alert(
        self,
        player: str,
        violation_type: str,
        details: str,
        severity: str = "HIGH"
    ) -> Dict[str, Any]:
        """
        Publie une alerte de sécurité Anti-Cheat à AetherScope.
        Met à jour à la fois le flux de télémétrie spatiale (cible: AntiCheatEngine)
        et le HUD de notification de chat.
        """
        telemetry_details = (
            f"Alerte de securite: Joueur '{player}' signale pour {violation_type}. "
            f"Details: {details} [Severite: {severity}]"
        )
        t_res = self.publish_telemetry(
            target="AntiCheatEngine",
            action=f"Violation:{violation_type}",
            details=telemetry_details,
        )

        chat_text = (
            f"🛡️ [ANTI-CHEAT] Alerte {severity}: Joueur '{player}' intercepté pour {violation_type}. "
            f"{details}"
        )
        c_res = self.send_cockpit_chat(
            text=chat_text,
            sender="AetherAntiCheat",
            target_symbol="AntiCheatEngine",
        )

        return {
            "success": t_res.get("success", False) or c_res.get("success", False),
            "telemetry": t_res,
            "chat": c_res,
        }

    def sync_player_count(
        self,
        count: int,
        player_names: Optional[List[str]] = None,
        max_players: int = 200
    ) -> Dict[str, Any]:
        """
        Synchronise le nombre de joueurs actifs et la liste des connectés avec AetherScope.
        """
        names_str = ", ".join(player_names) if player_names else "aucun"
        details = f"Joueurs connectes: {count}/{max_players} ({names_str})"
        return self.publish_telemetry(
            target="PlayerTracker",
            action="PlayerCountSync",
            details=details,
        )

    def sync_tps_status(
        self,
        tps: float,
        cpu_load: Optional[float] = None,
        memory_usage_mb: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Synchronise la métrique TPS et les indicateurs de performance Paper avec AetherScope.
        """
        extra_info = []
        if cpu_load is not None:
            extra_info.append(f"CPU: {cpu_load:.1f}%")
        if memory_usage_mb is not None:
            extra_info.append(f"RAM: {memory_usage_mb:.1f} MB")
        extra_str = f" ({', '.join(extra_info)})" if extra_info else ""
        details = f"Paper Server TPS: {tps:.2f}{extra_str}"

        return self.publish_telemetry(
            target="PaperEngine",
            action="TpsSync",
            details=details,
        )

    def sync_operational_state(
        self,
        player_count: int,
        tps: float,
        security_alerts_count: int = 0,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synchronisation groupée de l'état opérationnel global d'AetherCraft vers AetherScope.
        """
        tps_res = self.sync_tps_status(tps=tps)
        player_res = self.sync_player_count(count=player_count)
        
        return {
            "success": tps_res.get("success", False) and player_res.get("success", False),
            "tps_sync": tps_res,
            "player_sync": player_res,
            "security_alerts_count": security_alerts_count,
        }


# =============================================================================
# Instance Singleton par défaut et Fonctions Raccourcies
# =============================================================================

default_client = AetherScopeClient()

def check_health(timeout: Optional[float] = None) -> Dict[str, Any]:
    return default_client.check_health(timeout=timeout)

def is_alive(timeout: Optional[float] = 1.0) -> bool:
    return default_client.is_alive(timeout=timeout)

def get_graph_version(timeout: Optional[float] = None) -> Dict[str, Any]:
    return default_client.get_graph_version(timeout=timeout)

def get_graph_summary(timeout: Optional[float] = 3.0) -> Dict[str, Any]:
    return default_client.get_graph_summary(timeout=timeout)

def get_projects(timeout: Optional[float] = None) -> Dict[str, Any]:
    return default_client.get_projects(timeout=timeout)

def get_project_metadata(project_name: str = "aethercraft") -> Optional[Dict[str, Any]]:
    return default_client.get_project_metadata(project_name=project_name)

def publish_telemetry(target: str, action: str, details: str, timestamp: Optional[int] = None) -> Dict[str, Any]:
    return default_client.publish_telemetry(target=target, action=action, details=details, timestamp=timestamp)

def publish_security_alert(player: str, violation_type: str, details: str, severity: str = "HIGH") -> Dict[str, Any]:
    return default_client.publish_security_alert(player=player, violation_type=violation_type, details=details, severity=severity)

def sync_player_count(count: int, player_names: Optional[List[str]] = None, max_players: int = 200) -> Dict[str, Any]:
    return default_client.sync_player_count(count=count, player_names=player_names, max_players=max_players)

def sync_tps_status(tps: float, cpu_load: Optional[float] = None, memory_usage_mb: Optional[float] = None) -> Dict[str, Any]:
    return default_client.sync_tps_status(tps=tps, cpu_load=cpu_load, memory_usage_mb=memory_usage_mb)

def sync_operational_state(player_count: int, tps: float, security_alerts_count: int = 0, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return default_client.sync_operational_state(player_count=player_count, tps=tps, security_alerts_count=security_alerts_count, extra=extra)

def send_cockpit_chat(text: str, sender: str = "AetherCraft-Security", target_symbol: Optional[str] = None) -> Dict[str, Any]:
    return default_client.send_cockpit_chat(text=text, sender=sender, target_symbol=target_symbol)
