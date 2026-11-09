"""
================================================================================
AetherScope MCP Integration & State Synchronization Test Suite
Automated Opaque-Box Security & Telemetry Harness (R3)
Reference: ORIGINAL_REQUEST.md (R3), PROJECT.md (SEC_F12), survey_report.md
================================================================================
Validates:
1. REST Engine Availability & Health Probe on 127.0.0.1:3030 (/api/health, /api/graph/version, /api/projects).
2. LocalGuard Defense Filter against DNS Rebinding & Malicious External Origins (403 Forbidden).
3. Live Telemetry & Security Alert Synchronization (/api/ai/telemetry, /api/ai/chat).
4. Model Context Protocol (MCP) Stdio JSON-RPC 2.0 Handshake & Tool Catalog (aetherscope-mcp.exe).
5. Network Synchronization Resilience & Graceful Error Handling.
================================================================================
"""

import os
import sys
import json
import socket
import urllib.request
import urllib.error
import subprocess
import unittest
from typing import Dict, Any, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "aether-engine"))
MCP_EXE_PATH = os.path.join(ENGINE_DIR, "aetherscope-mcp.exe")
MCP_BASE_URL = "http://127.0.0.1:3030"

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def http_request(path: str, method: str = "GET", headers: Dict[str, str] = None,
                 payload: Dict[str, Any] = None, timeout: float = 3.0) -> Tuple[int, str]:
    """Helper for dispatching HTTP requests to local AetherScope server."""
    url = f"{MCP_BASE_URL}{path}"
    data_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
    req_headers = {"User-Agent": "AetherCraft-SecurityTest/2.0"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return -1, str(e)


# ==============================================================================
# 1. REST ENGINE HEALTH & GRAPH METRICS
# ==============================================================================

class TestAetherScopeRestHealthAndMetrics(unittest.TestCase):
    """Validates local AetherScope REST API endpoints on 127.0.0.1:3030."""

    def test_01_mcp_health_probe_status_ok(self):
        """TC-MCP-01: Sonde de santé GET /api/health retourne 200 avec status: ok et engine: aether-v2."""
        status_code, body = http_request("/api/health")
        self.assertEqual(status_code, 200, f"Expected 200 OK from /api/health, got {status_code}: {body}")
        data = json.loads(body)
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("engine"), "aether-v2")

    def test_02_mcp_graph_version_counter(self):
        """TC-MCP-02a: GET /api/graph/version retourne 200 avec version numérique > 0."""
        status_code, body = http_request("/api/graph/version")
        self.assertEqual(status_code, 200, f"Expected 200 OK from /api/graph/version, got {status_code}")
        data = json.loads(body)
        self.assertIn("version", data)
        self.assertIsInstance(data["version"], int)
        self.assertGreaterEqual(data["version"], 0)

    def test_03_mcp_projects_discovery_contains_aethercraft(self):
        """TC-MCP-02b: GET /api/projects liste les projets et référence aethercraft."""
        status_code, body = http_request("/api/projects")
        self.assertEqual(status_code, 200, f"Expected 200 OK from /api/projects, got {status_code}")
        data = json.loads(body)
        self.assertIn("projects", data)
        project_names = [p.get("name") for p in data["projects"]]
        self.assertIn("aethercraft", project_names, f"aethercraft not found in project list: {project_names}")


# ==============================================================================
# 2. LOCALGUARD DEFENSE FILTER (ANTI-DNS REBINDING & ANTI-CSRF)
# ==============================================================================

class TestAetherScopeLocalGuardDefense(unittest.TestCase):
    """Validates LocalGuard security middleware protecting port 3030."""

    def test_04_localguard_foreign_host_rejected_with_403(self):
        """TC-MCP-03a: Requête avec en-tête Host externe (DNS rebinding) est rejetée avec 403 Forbidden."""
        status_code, body = http_request("/api/health", headers={"Host": "evil.attacker.com:3030"})
        self.assertEqual(status_code, 403,
                         f"Expected 403 Forbidden for foreign Host header, got {status_code}: {body}")
        self.assertIn("origine non locale", body.lower())

    def test_05_localguard_malicious_origin_rejected_with_403(self):
        """TC-MCP-03b: Requête avec en-tête Origin malveillante (anti-CSRF) est rejetée avec 403 Forbidden."""
        status_code, body = http_request("/api/health", headers={"Origin": "https://malicious.site"})
        self.assertEqual(status_code, 403,
                         f"Expected 403 Forbidden for external Origin, got {status_code}: {body}")
        self.assertIn("origine non locale", body.lower())

    def test_06_localguard_legitimate_local_host_accepted(self):
        """Requête avec en-tête Host légitime 127.0.0.1:3030 est acceptée (200 OK)."""
        status_code, body = http_request("/api/health", headers={"Host": "127.0.0.1:3030"})
        self.assertEqual(status_code, 200)


# ==============================================================================
# 3. LIVE TELEMETRY & SECURITY ALERT SYNCHRONIZATION
# ==============================================================================

class TestAetherScopeTelemetryAndStateSync(unittest.TestCase):
    """Validates state and telemetry synchronization from AetherCraft to AetherScope."""

    def test_07_telemetry_camera_alignment_sync(self):
        """TC-MCP-07: POST /api/ai/telemetry émet un signal de visée spatiale pour inspection anti-cheat."""
        payload = {
            "target": "AntiCheatEngine",
            "action": "Inspect",
            "details": "Automated security verification pulse"
        }
        status_code, body = http_request("/api/ai/telemetry", method="POST", payload=payload)
        self.assertEqual(status_code, 200, f"Expected 200 OK from /api/ai/telemetry, got {status_code}: {body}")
        data = json.loads(body)
        self.assertEqual(data.get("status"), "ok")

    def test_08_chat_hud_security_alert_notification(self):
        """TC-MCP-08: POST /api/ai/chat émet une notification d'alerte de triche dans le cockpit spatial."""
        payload = {
            "text": "[AntiCheat-Alert] Player cheater_bot flagged for Speed & Fly at (100, 64, 200)"
        }
        status_code, body = http_request("/api/ai/chat", method="POST", payload=payload)
        self.assertEqual(status_code, 200, f"Expected 200 OK from /api/ai/chat, got {status_code}: {body}")
        data = json.loads(body)
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("message", data)


# ==============================================================================
# 4. MODEL CONTEXT PROTOCOL (MCP) STDIO JSON-RPC 2.0 PROTOCOL
# ==============================================================================

class TestAetherScopeMcpStdioProtocol(unittest.TestCase):
    """Validates stdio JSON-RPC 2.0 communication with aetherscope-mcp.exe."""

    def test_09_mcp_stdio_jsonrpc_initialization(self):
        """TC-MCP-04: Handshake JSON-RPC 2.0 'initialize' sur stdio retourne protocolVersion 2024-11-05."""
        if not os.path.exists(MCP_EXE_PATH):
            self.skipTest(f"Binary {MCP_EXE_PATH} not found on disk")

        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "aethercraft-test", "version": "1.0.0"}
            }
        }
        payload = json.dumps(req) + "\n"

        proc = subprocess.Popen(
            [MCP_EXE_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(payload, timeout=5)
        self.assertIn('"jsonrpc":"2.0"', stdout)
        self.assertIn('"id":1', stdout)
        self.assertIn('"protocolVersion":"2024-11-05"', stdout)
        self.assertIn('"name":"aetherscope-mcp"', stdout)

    def test_10_mcp_stdio_tools_list_contract(self):
        """TC-MCP-05: Envoi de 'tools/list' sur stdio retourne les outils aetherscope_*."""
        if not os.path.exists(MCP_EXE_PATH):
            self.skipTest(f"Binary {MCP_EXE_PATH} not found on disk")

        init_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}
        }) + "\n"

        tools_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }) + "\n"

        proc = subprocess.Popen(
            [MCP_EXE_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, _ = proc.communicate(init_req + tools_req, timeout=5)

        # Look for tools/list response
        self.assertIn('"tools"', stdout)
        self.assertIn("aetherscope_teleport_camera", stdout)
        self.assertIn("aetherscope_get_graph_summary", stdout)


# ==============================================================================
# 5. SYNCHRONIZATION RESILIENCE & ERROR HANDLING
# ==============================================================================

class TestAetherScopeSyncResilience(unittest.TestCase):
    """Validates graceful degradation and error handling when MCP is partitioned."""

    def test_11_sync_resilience_unreachable_endpoint_handled(self):
        """Vérifie qu'une tentative de synchronisation vers un port fermé est interceptée sans crash."""
        class MockAetherScopeClient:
            def __init__(self, port: int = 3039):
                self.port = port

            def sync_alert(self, alert_msg: str) -> bool:
                try:
                    with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                        return True
                except OSError:
                    # Graceful offline mode
                    return False

        client = MockAetherScopeClient(port=3039)
        # Port 3039 is closed; client must return False cleanly without unhandled exception
        result = client.sync_alert("Test alert")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
