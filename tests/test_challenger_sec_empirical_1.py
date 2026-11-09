"""
================================================================================
AetherCraft Adversarial Empirical Security & Stress Harness
Test Suite: test_challenger_sec_empirical_1.py
Author: teamwork_challenger_sec_1
Target Project: C:\\Users\\1234\\Desktop\\Projets\\aethercraft

Validates and stress-tests:
1. Packet Attack Simulation:
   - Micro-speed threshold bypass (0.3601 - 25.0 blocks/tick) and ice speed bounds.
   - Micro-hover fly (dy = 0.000001), step height (> 0.60), and waterwalk/Jesus.
   - Combat reach micro-boundary (3.0001 - 50.0 blocks), KillAura impossible angles, CPS flood.
   - Malformed packets: NaN coordinates, Infinity coordinates, world limits (> 30M blocks), NBT depth.
   - In-game packet bridge unauthorized purchases & OneBlock generator theft.
2. Web Exploit Simulation:
   - Forged HMAC tokens, bit-flipped tokens, expired/future timestamps, player mismatch.
   - Player spoofing on /api/webdisplay/action (web session & game token spoofing).
   - Schema & action injection attacks (unknown actions, malformed strings, XSS/SQL tokens).
   - Quest coin minting replay containment (enforce 1/day progression limit, HTTP 429).
   - RCON command injections with diverse CRLF and separator encodings (\\r\\n, \\n, \\r, \\x00, ;).
   - Block icon path traversal fuzzing (..%2f..%2f, null bytes, backslashes, double url-encoding).
3. Concurrent Rate Limiting Stress:
   - Multi-threaded flood against /connexion (Auth tier: max 5 req/min -> HTTP 429).
   - Multi-threaded flood against /api/webdisplay/action (Mutation tier: max 30 req/min -> HTTP 429).
   - Client IP isolation & thread-safety verification under high concurrency.
4. AetherScope LocalGuard & DNS Rebinding Simulation:
   - Foreign Host header rejection (anti-DNS rebinding).
   - Malicious Origin and cross-site Sec-Fetch-Site rejection (anti-CSRF).
   - Graceful degradation under network unavailability.
5. Legitimate Golden Path Verification:
   - Normal movement, jump pad velocity, legitimate combat hit, valid auth action, valid PNG render.
================================================================================
"""

import os
import sys
import re
import math
import time
import hmac
import hashlib
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import unittest
from typing import Dict, List, Tuple, Optional, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
DB_PATH = os.path.join(SERVER_DIR, "data", "aethercraft.db")
PLUGINS_SRC = os.path.join(SERVER_DIR, "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from app import app, verify_game_auth_token
from services.database import get_db_connection, init_database
from services.rcon_service import execute_server_command
from services.block_renderer import normalize_material_key, render_isometric_block_png, CACHE_3D_DIR
from services.security_middleware import rate_limiter, validate_username, validate_rcon_command_safety
from services.aetherscope_sync import is_localguard_compliant, build_localguard_headers, AetherScopeClient


# ==============================================================================
# 1. PACKET ATTACK SIMULATION HARNESS
# ==============================================================================

class EmpiricalPhysicsAntiCheatEngine:
    """
    Deterministic empirical model of Paper 1.21.1 / GrimAC simulation engine.
    Applies exact server-side movement bounds, combat checks, and coordinate assertions.
    """
    MAX_GROUND_SPEED = 0.360       # blocks/tick
    MAX_ICE_SPEED = 0.620          # blocks/tick with Speed II
    VANILLA_STEP_HEIGHT = 0.60    # blocks
    SURVIVAL_REACH = 3.00         # blocks
    MAX_CPS = 20                  # clicks/second
    WORLD_BORDER_LIMIT = 30000000.0

    def __init__(self, x: float = 0.0, y: float = 64.0, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z
        self.last_legit_x = x
        self.last_legit_y = y
        self.last_legit_z = z
        self.on_ground = True
        self.in_water = False
        self.flying_allowed = False
        self.has_jump_pad_velocity = False
        self.velocity_ticks = 0
        self.violations: List[str] = []

    def set_jump_pad_velocity(self, ticks: int = 30):
        self.has_jump_pad_velocity = True
        self.velocity_ticks = ticks

    def process_movement(self, target_x: float, target_y: float, target_z: float,
                         on_ground: bool, has_speed_effect: bool = False,
                         has_frost_walker: bool = False) -> Tuple[bool, str]:
        # 1. NaN and Infinity assertions
        for val in (target_x, target_y, target_z):
            if math.isnan(val) or math.isinf(val):
                self.violations.append("BAD_PACKET_COORDINATES_NAN_INF")
                return False, "BAD_PACKET_COORDINATES_NAN_INF"
            if abs(val) > self.WORLD_BORDER_LIMIT:
                self.violations.append("BAD_PACKET_COORDINATES_OUT_OF_BOUNDS")
                return False, "BAD_PACKET_COORDINATES_OUT_OF_BOUNDS"

        dx = target_x - self.x
        dy = target_y - self.y
        dz = target_z - self.z
        dist_xz = math.sqrt(dx * dx + dz * dz)

        # 2. Jump pad velocity exemption
        if self.has_jump_pad_velocity and self.velocity_ticks > 0:
            self.velocity_ticks -= 1
            if self.velocity_ticks == 0:
                self.has_jump_pad_velocity = False
            self.x, self.y, self.z = target_x, target_y, target_z
            self.on_ground = on_ground
            self.last_legit_x, self.last_legit_y, self.last_legit_z = target_x, target_y, target_z
            return True, "ACCEPTED_WITH_VELOCITY"

        # 3. Horizontal Speed delta
        max_speed = self.MAX_ICE_SPEED if has_speed_effect else self.MAX_GROUND_SPEED
        if dist_xz > max_speed + 0.00001:
            self.violations.append("SPEED_DELTA_EXCEEDED")
            # Rubberband
            self.x, self.y, self.z = self.last_legit_x, self.last_legit_y, self.last_legit_z
            return False, "SPEED_DELTA_EXCEEDED"

        # 4. Vertical Step Height
        if dy > self.VANILLA_STEP_HEIGHT + 0.00001 and not self.flying_allowed:
            self.violations.append("STEP_HEIGHT_VIOLATION")
            self.x, self.y, self.z = self.last_legit_x, self.last_legit_y, self.last_legit_z
            return False, "STEP_HEIGHT_VIOLATION"

        # 5. Jesus / WaterWalk
        if self.in_water and on_ground and not has_frost_walker:
            self.violations.append("JESUS_WATERWALK")
            return False, "JESUS_WATERWALK"

        # 6. Fly / Hover (dy nearly 0 while mid-air)
        if not on_ground and abs(dy) < 0.0001 and not self.flying_allowed:
            self.violations.append("FLY_HOVER")
            return False, "FLY_HOVER"

        # Accepted
        self.x, self.y, self.z = target_x, target_y, target_z
        self.on_ground = on_ground
        self.last_legit_x, self.last_legit_y, self.last_legit_z = target_x, target_y, target_z
        return True, "ACCEPTED"

    def process_attack(self, attacker_pos: Tuple[float, float, float],
                       attacker_yaw: float,
                       target_pos: Tuple[float, float, float]) -> Tuple[bool, str]:
        dx = target_pos[0] - attacker_pos[0]
        dy = target_pos[1] - attacker_pos[1]
        dz = target_pos[2] - attacker_pos[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        # Reach assertion
        if dist > self.SURVIVAL_REACH + 0.00001:
            self.violations.append("REACH_LIMIT_EXCEEDED")
            return False, f"REACH_LIMIT_EXCEEDED: {dist:.4f} > {self.SURVIVAL_REACH}"

        # KillAura angle assertion
        yaw_rad = math.radians(attacker_yaw)
        look_dx = -math.sin(yaw_rad)
        look_dz = math.cos(yaw_rad)

        t_xz = math.sqrt(dx * dx + dz * dz)
        if t_xz > 0.0001:
            norm_dx = dx / t_xz
            norm_dz = dz / t_xz
            dot = look_dx * norm_dx + look_dz * norm_dz
            dot = max(-1.0, min(1.0, dot))
            angle_deg = math.degrees(math.acos(dot))
            if angle_deg > 90.0:
                self.violations.append("KILLAURA_IMPOSSIBLE_ANGLE")
                return False, f"KILLAURA_IMPOSSIBLE_ANGLE: {angle_deg:.2f}° divergence"

        return True, "ACCEPTED"


class TestChallengerPacketAttacks(unittest.TestCase):
    """Adversarial stress harness for Minecraft network packets and in-game security contracts."""

    def setUp(self):
        self.engine = EmpiricalPhysicsAntiCheatEngine(x=0.0, y=64.0, z=0.0)

    def test_packet_speed_bypass_fuzzing(self):
        """Attacks speed thresholds with fine-grained deltas (0.3601 up to 25.0 blocks/tick)."""
        attack_deltas = [0.3601, 0.3605, 0.361, 0.370, 0.400, 0.500, 1.0, 5.0, 25.0]
        for delta in attack_deltas:
            acc, reason = self.engine.process_movement(delta, 64.0, 0.0, on_ground=True)
            self.assertFalse(acc, f"Delta {delta} should be rejected")
            self.assertEqual(reason, "SPEED_DELTA_EXCEEDED")
            # Verify coordinates were rubberbanded to last legitimate position (0.0, 64.0, 0.0)
            self.assertEqual((self.engine.x, self.engine.y, self.engine.z), (0.0, 64.0, 0.0))

        # Legitimate speed below threshold (0.359) must be accepted
        acc_legit, _ = self.engine.process_movement(0.359, 64.0, 0.0, on_ground=True)
        self.assertTrue(acc_legit)
        self.assertEqual(self.engine.x, 0.359)

        # Ice speed boundary with speed effect: 0.6201 rejected, 0.619 accepted
        acc_ice_bad, _ = self.engine.process_movement(0.359 + 0.6201, 64.0, 0.0, on_ground=True, has_speed_effect=True)
        self.assertFalse(acc_ice_bad)
        acc_ice_ok, _ = self.engine.process_movement(0.359 + 0.619, 64.0, 0.0, on_ground=True, has_speed_effect=True)
        self.assertTrue(acc_ice_ok)

    def test_packet_fly_and_hover_attacks(self):
        """Attacks flight/hover checks with micro-elevations and step violations."""
        # 1. Hover in mid-air (dy = 0, on_ground = False)
        acc, reason = self.engine.process_movement(0.0, 64.0, 0.0, on_ground=False)
        self.assertFalse(acc)
        self.assertEqual(reason, "FLY_HOVER")

        # 2. Micro-hover
        acc_micro, reason_micro = self.engine.process_movement(0.0, 64.000001, 0.0, on_ground=False)
        self.assertFalse(acc_micro)
        self.assertEqual(reason_micro, "FLY_HOVER")

        # 3. Vertical Step violation (> 0.60)
        acc_step, reason_step = self.engine.process_movement(0.0, 64.61, 0.0, on_ground=True)
        self.assertFalse(acc_step)
        self.assertEqual(reason_step, "STEP_HEIGHT_VIOLATION")

        # 4. WaterWalk / Jesus without Frost Walker
        self.engine.in_water = True
        acc_jesus, reason_jesus = self.engine.process_movement(0.0, 64.0, 0.0, on_ground=True, has_frost_walker=False)
        self.assertFalse(acc_jesus)
        self.assertEqual(reason_jesus, "JESUS_WATERWALK")

    def test_packet_reach_and_killaura_attacks(self):
        """Attacks combat interact packets beyond 3.0 blocks reach and impossible angles."""
        # 1. Reach boundary fuzzing
        reach_distances = [3.0001, 3.001, 3.01, 3.05, 3.5, 4.0, 6.0, 50.0]
        for dist in reach_distances:
            acc, reason = self.engine.process_attack(
                attacker_pos=(0.0, 64.0, 0.0),
                attacker_yaw=0.0,  # Looking south (+Z)
                target_pos=(0.0, 64.0, dist)
            )
            self.assertFalse(acc, f"Reach {dist} should be rejected")
            self.assertIn("REACH_LIMIT_EXCEEDED", reason)

        # Legitimate reach at 2.999 blocks must pass
        acc_legit, _ = self.engine.process_attack(
            attacker_pos=(0.0, 64.0, 0.0),
            attacker_yaw=0.0,
            target_pos=(0.0, 64.0, 2.999)
        )
        self.assertTrue(acc_legit)

        # 2. KillAura snap angle attack (attacking behind while facing forward)
        acc_ka, reason_ka = self.engine.process_attack(
            attacker_pos=(0.0, 64.0, 0.0),
            attacker_yaw=0.0,  # Looking south (+Z)
            target_pos=(0.0, 64.0, -2.5)  # Target is north (-Z, 180° divergence)
        )
        self.assertFalse(acc_ka)
        self.assertIn("KILLAURA_IMPOSSIBLE_ANGLE", reason_ka)

    def test_packet_malformed_coordinates_nan_inf(self):
        """Attacks movement decoder with NaN, Infinity, and out-of-world boundary coordinates."""
        nan_payloads = [
            (float("nan"), 64.0, 0.0),
            (0.0, float("nan"), 0.0),
            (0.0, 64.0, float("nan")),
            (float("nan"), float("nan"), float("nan")),
            (float("inf"), 64.0, 0.0),
            (-float("inf"), 64.0, 0.0),
            (0.0, -float("inf"), 0.0)
        ]
        for x, y, z in nan_payloads:
            acc, reason = self.engine.process_movement(x, y, z, on_ground=True)
            self.assertFalse(acc)
            self.assertEqual(reason, "BAD_PACKET_COORDINATES_NAN_INF")

        # World border overflows (> 30,000,000 blocks)
        oob_payloads = [
            (30000001.0, 64.0, 0.0),
            (-30000001.0, 64.0, 0.0),
            (0.0, 64.0, 30000001.0),
            (1e20, 64.0, 0.0)
        ]
        for x, y, z in oob_payloads:
            acc, reason = self.engine.process_movement(x, y, z, on_ground=True)
            self.assertFalse(acc)
            self.assertEqual(reason, "BAD_PACKET_COORDINATES_OUT_OF_BOUNDS")

    def test_packet_malformed_nbt_depth_simulation(self):
        """Simulates deeply nested NBT payloads and verifies containment without recursion crash."""
        def craft_recursive_nbt(depth: int) -> dict:
            root = {"type": "compound", "name": "root", "value": {}}
            curr = root["value"]
            for i in range(depth):
                child = {"type": "compound", "name": f"nest_{i}", "value": {}}
                curr["child"] = child
                curr = child["value"]
            return root

        deep_payload = craft_recursive_nbt(600)

        # Simulation of GrimAC / Paper NBT parser depth limit (max 512 tags)
        def validate_nbt_depth(tag: dict, max_depth: int = 512) -> bool:
            stack = [(tag, 0)]
            while stack:
                node, depth = stack.pop()
                if depth > max_depth:
                    return False
                if isinstance(node, dict) and "value" in node and isinstance(node["value"], dict):
                    for v in node["value"].values():
                        stack.append((v, depth + 1))
            return True

        self.assertFalse(validate_nbt_depth(deep_payload), "Payload exceeding 512 nesting level must be rejected")
        normal_payload = craft_recursive_nbt(32)
        self.assertTrue(validate_nbt_depth(normal_payload))


# ==============================================================================
# 2. WEB EXPLOIT SIMULATION HARNESS
# ==============================================================================

class TestChallengerWebExploitSimulation(unittest.TestCase):
    """Adversarial stress harness targeting web endpoints, RCON injection, and path traversal."""

    def setUp(self):
        init_database()
        app.config["TESTING"] = True
        app.config["RATELIMIT_ENABLED"] = True
        rate_limiter.reset()
        self.client = app.test_client()

    def tearDown(self):
        rate_limiter.reset()

    def test_webdisplay_forged_and_tampered_hmac_tokens(self):
        """Fuzzes HMAC authentication on /api/webdisplay/action with tampered tokens and timestamps."""
        auth_key = os.environ.get("AETHER_AUTH_KEY", "aethercraft_session_hmac_2026")
        username = "validplayer"
        now = int(time.time())
        valid_token = hmac.new(auth_key.encode("utf-8"), f"{username.lower()}:{now}".encode("utf-8"), hashlib.sha256).hexdigest()

        # 1. Unauthenticated request without token -> 401
        res = self.client.post("/api/webdisplay/action", json={"player": username, "action": "tp_spawn"})
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.get_json().get("code"), 401)

        # 2. Arbitrary forged token string -> 401
        res_forged = self.client.post("/api/webdisplay/action", json={
            "player": username, "action": "tp_spawn", "token": "deadbeef1234567890abcdef", "ts": str(now)
        })
        self.assertEqual(res_forged.status_code, 401)

        # 3. Bit-flipped token (1 char altered) -> 401
        bit_flipped = ("0" if valid_token[0] != "0" else "1") + valid_token[1:]
        res_bitflip = self.client.post("/api/webdisplay/action", json={
            "player": username, "action": "tp_spawn", "token": bit_flipped, "ts": str(now)
        })
        self.assertEqual(res_bitflip.status_code, 401)

        # 4. Expired timestamp (> 3600s in past) -> 401
        expired_ts = str(now - 3601)
        expired_token = hmac.new(auth_key.encode("utf-8"), f"{username.lower()}:{expired_ts}".encode("utf-8"), hashlib.sha256).hexdigest()
        res_expired = self.client.post("/api/webdisplay/action", json={
            "player": username, "action": "tp_spawn", "token": expired_token, "ts": expired_ts
        })
        self.assertEqual(res_expired.status_code, 401)

        # 5. Future timestamp (> 3600s in future) -> 401
        future_ts = str(now + 3601)
        future_token = hmac.new(auth_key.encode("utf-8"), f"{username.lower()}:{future_ts}".encode("utf-8"), hashlib.sha256).hexdigest()
        res_future = self.client.post("/api/webdisplay/action", json={
            "player": username, "action": "tp_spawn", "token": future_token, "ts": future_ts
        })
        self.assertEqual(res_future.status_code, 401)

        # 6. Wrong secret key HMAC -> 401
        wrong_token = hmac.new(b"wrong_secret_attacker_key", f"{username.lower()}:{now}".encode("utf-8"), hashlib.sha256).hexdigest()
        res_wrong = self.client.post("/api/webdisplay/action", json={
            "player": username, "action": "tp_spawn", "token": wrong_token, "ts": str(now)
        })
        self.assertEqual(res_wrong.status_code, 401)

    def test_webdisplay_player_spoofing_attempts(self):
        """Simulates authenticated user attempting actions on behalf of another player (must return 403)."""
        auth_key = os.environ.get("AETHER_AUTH_KEY", "aethercraft_session_hmac_2026")
        now = int(time.time())
        attacker = "attacker"
        victim = "victim"
        attacker_token = hmac.new(auth_key.encode("utf-8"), f"{attacker}:{now}".encode("utf-8"), hashlib.sha256).hexdigest()

        # Attacker provides their own valid token but requests action on victim
        res_token_spoof = self.client.post("/api/webdisplay/action", json={
            "player": victim,
            "action": "tp_spawn",
            "token": attacker_token,
            "ts": str(now)
        })
        self.assertEqual(res_token_spoof.status_code, 401)  # Token doesn't validate for victim

        # Web session logged in as Alice attempts action as Bob
        with self.client.session_transaction() as sess:
            sess["user_id"] = 999
            sess["minecraft_username"] = "Alice"
            sess["game_auth"] = "alice"

        res_session_spoof = self.client.post("/api/webdisplay/action", json={
            "player": "Bob",
            "action": "tp_spawn"
        })
        self.assertEqual(res_session_spoof.status_code, 403)
        self.assertEqual(res_session_spoof.get_json().get("code"), 403)
        self.assertIn("Interdiction", res_session_spoof.get_json().get("message", ""))

    def test_webdisplay_schema_injection_and_unauthorized_actions(self):
        """Fuzzes /api/webdisplay/action with unknown actions, payload injections, and bad formats (must return 400)."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 100
            sess["minecraft_username"] = "LegitUser"
            sess["game_auth"] = "legituser"

        malicious_actions = [
            "op_me", "give_all", "<script>alert(1)</script>", "rm_rf",
            "tp_void", "__proto__", "eval(1)", "select * from users",
            "execute;op hacker", "tp_spawn\nstop"
        ]
        for bad_action in malicious_actions:
            res = self.client.post("/api/webdisplay/action", json={
                "player": "LegitUser",
                "action": bad_action
            })
            self.assertEqual(res.status_code, 400, f"Action '{bad_action}' must return 400")
            self.assertEqual(res.get_json().get("code"), 400)

        # Malformed username
        res_bad_user = self.client.post("/api/webdisplay/action", json={
            "player": "Bad User With Spaces!",
            "action": "tp_spawn"
        })
        self.assertEqual(res_bad_user.status_code, 400)

        # Malformed target (path traversal or shell injection in target)
        res_bad_target = self.client.post("/api/webdisplay/action", json={
            "player": "LegitUser",
            "action": "tp_spawn",
            "target": "../../etc/shadow"
        })
        self.assertEqual(res_bad_target.status_code, 400)

    def test_webdisplay_quest_coin_minting_replay_contained(self):
        """
        Verifies that an authenticated player cannot mint unlimited coins via repeated claim_quest calls.
        DISCOVERED DEFECT: web/app.py:950 calls `get_db_connection()` which is not imported in web/app.py!
        This causes an unhandled NameError: name 'get_db_connection' is not defined (500 crash).
        """
        with self.client.session_transaction() as sess:
            sess["user_id"] = 200
            sess["minecraft_username"] = "QuestHunter"
            sess["game_auth"] = "questhunter"

        # Clear prior claims for test idempotency
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS player_daily_quest_claims (username TEXT PRIMARY KEY, last_claimed_date TEXT NOT NULL, claimed_at TEXT NOT NULL);")
            c.execute("DELETE FROM player_daily_quest_claims WHERE LOWER(username) = LOWER(?);", ("QuestHunter",))
            conn.commit()

        # 1st claim of the day -> succeeds (+500 coins)
        res1 = self.client.post("/api/webdisplay/action", json={
            "player": "QuestHunter",
            "action": "claim_quest"
        })
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.get_json().get("status"), "ok")

        # 2nd immediate claim on the same UTC day -> rejected with HTTP 429
        res2 = self.client.post("/api/webdisplay/action", json={
            "player": "QuestHunter",
            "action": "claim_quest"
        })
        self.assertEqual(res2.status_code, 429)
        self.assertEqual(res2.get_json().get("code"), 429)
        self.assertIn("déjà réclamée", res2.get_json().get("message", ""))

        # 3rd claim on the same UTC day -> still rejected with HTTP 429
        res3 = self.client.post("/api/webdisplay/action", json={
            "player": "QuestHunter",
            "action": "claim_quest"
        })
        self.assertEqual(res3.status_code, 429)

    def test_rcon_command_injection_encodings(self):
        """Fuzzes RCON sanitizer with CRLF (\\r\\n, \\n, \\r), null bytes (\\x00), semicolons, and subcommands."""
        injection_payloads = [
            "broadcast Hello\r\nop Attacker",
            "broadcast Hello\nop Attacker",
            "broadcast Hello\rop Attacker",
            "broadcast Hello\x00op Attacker",
            "broadcast Hello; op Attacker",
            "say Test;\n;\r\x00op Pwned",
            "give Alice diamond 1\nstop",
            "lp user Alice parent add admin\rdeop Bob"
        ]
        for inj in injection_payloads:
            safe, msg = validate_rcon_command_safety(inj)
            self.assertFalse(safe, f"Injection '{repr(inj)}' should be flagged unsafe")
            # Also test execute_server_command directly
            success, response = execute_server_command(inj)
            self.assertFalse(success, f"RCON execution should fail on '{repr(inj)}'")
            self.assertIn("Rejet de commande", response)

        # Injected username in 'execute as' with separators
        bad_users = [
            "execute as Alice;op Bob run spawn",
            "execute as Alice\nstop run spawn",
            "execute as Alice\r\nop Bob run spawn",
            "execute as Alice\x00stop run spawn"
        ]
        for bad_u in bad_users:
            safe, _ = validate_rcon_command_safety(bad_u)
            self.assertFalse(safe, f"Username injection with separator '{bad_u}' must be rejected")
            success, _ = execute_server_command(bad_u)
            self.assertFalse(success)

        # Whitelist non-compliant commands
        disallowed_commands = ["pwn", "help", "save-all", "restart", "reload", "stop", "eval 1"]
        for dis in disallowed_commands:
            safe, _ = validate_rcon_command_safety(dis)
            self.assertFalse(safe, f"Command '{dis}' not in whitelist must be rejected")

        # Legitimate commands MUST pass validation
        legit_commands = [
            "broadcast Welcome to Aethercraft!",
            "execute as Alice run spawn",
            "execute as Bob run survie",
            "say Serveur actif",
            "list"
        ]
        for legit in legit_commands:
            safe, _ = validate_rcon_command_safety(legit)
            self.assertTrue(safe, f"Legitimate command '{legit}' must be accepted")

    def test_rcon_execute_as_subcommand_defense_in_depth(self):
        """
        Adversarial probe: tests whether execute as subcommand validation enforces whitelist.
        DISCOVERED DEFECT: In security_middleware.py:139 and rcon_service.py:129,
        the code checks `parts[2] == 'run'`, but `parts` is ['execute', 'as', '<player>', 'run', ...].
        Therefore parts[2] is the player username, skipping subcommand validation entirely!
        """
        unauthorized_subcmds = [
            "execute as Alice run op Attacker",
            "execute as Alice run stop",
            "execute as Alice run deop Alice",
            "execute as Alice run ban Bob",
            "execute as Alice run gamemode creative",
            "execute as Alice run whitelist off"
        ]
        for subcmd in unauthorized_subcmds:
            safe, _ = validate_rcon_command_safety(subcmd)
            self.assertFalse(safe, f"Subcommand '{subcmd}' must be rejected by subcommand validator")
            success, _ = execute_server_command(subcmd)
            self.assertFalse(success, f"execute_server_command must reject unauthorized subcommand '{subcmd}'")

    def test_block_icon_path_traversal_fuzzing(self):
        """Fuzzes block icon renderer with path traversal, URL-encoded patterns, null bytes, and long paths."""
        traversal_attempts = [
            "../../../../etc/passwd",
            "..%2f..%2fetc/passwd",
            "..%5c..%5cwindows/win.ini",
            "....//....//....//etc/shadow",
            "diamond_block\x00cmd.exe",
            "diamond_block%00.png",
            "..%252f..%252fsecret",
            "/etc/passwd",
            "C:\\Windows\\System32\\cmd.exe",
            "..\\..\\windows\\system32",
            "a" * 500 + "/../../secret"
        ]

        for payload in traversal_attempts:
            # 1. normalize_material_key must never return path characters
            clean_key = normalize_material_key(payload)
            self.assertNotIn("..", clean_key, f"Traversal dots in {clean_key}")
            self.assertNotIn("/", clean_key, f"Slash in {clean_key}")
            self.assertNotIn("\\", clean_key, f"Backslash in {clean_key}")
            self.assertNotIn("\x00", clean_key, f"Null byte in {clean_key}")
            self.assertTrue(bool(re.match(r"^[a-z0-9_]+$", clean_key)), f"Key {clean_key} contains invalid chars")

            # 2. Cache path must remain strictly within CACHE_3D_DIR
            resolved_cache_file = os.path.abspath(os.path.join(CACHE_3D_DIR, f"{clean_key}.png"))
            self.assertTrue(
                resolved_cache_file.startswith(os.path.abspath(CACHE_3D_DIR)),
                f"Resolved cache file {resolved_cache_file} escaped {CACHE_3D_DIR}"
            )

            # 3. HTTP endpoint call must not leak or raise 500
            url = f"/api/minecraft/block-icon/{payload}.png"
            res = self.client.get(url, follow_redirects=True, headers={"X-Forwarded-For": "198.51.100.99"})
            # Must return 200 with valid image/png (fallback to diamond_block) or 400/404, never 500
            self.assertIn(res.status_code, (200, 400, 404), f"Unexpected status {res.status_code} for {payload}")
            if res.status_code == 200:
                self.assertEqual(res.mimetype, "image/png")
                self.assertTrue(res.data.startswith(b"\x89PNG\r\n\x1a\n"), "Must be valid PNG magic header")


# ==============================================================================
# 3. CONCURRENT RATE LIMITING STRESS HARNESS
# ==============================================================================

class TestChallengerRateLimitingStressConcurrent(unittest.TestCase):
    """Stress-tests thread-safe sliding window rate limiting under concurrent flood."""

    def setUp(self):
        init_database()
        app.config["TESTING"] = True
        app.config["RATELIMIT_ENABLED"] = True
        rate_limiter.reset()

    def tearDown(self):
        rate_limiter.reset()

    def test_concurrent_auth_flood_rate_limiting_enforcement(self):
        """
        Floods /connexion (Auth tier: max 5 requests / min) with 25 concurrent threads from a single IP.
        Empirically verifies that exactly 5 succeed and exactly 20 receive HTTP 429 Too Many Requests.
        """
        ip = "198.51.100.10"
        num_threads = 25

        def make_auth_request():
            with app.test_client() as c:
                res = c.get("/connexion", headers={"X-Forwarded-For": ip})
                return res.status_code, res.get_json(silent=True)

        results = []
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_auth_request) for _ in range(num_threads)]
            for f in as_completed(futures):
                results.append(f.result())

        status_codes = [r[0] for r in results]
        count_200 = status_codes.count(200)
        count_429 = status_codes.count(429)

        self.assertEqual(len(results), num_threads)
        self.assertEqual(count_200, 5, f"Expected exactly 5 allowed requests, got {count_200}")
        self.assertEqual(count_429, 20, f"Expected exactly 20 rate-limited (429) requests, got {count_429}")

        # Check structure of 429 response
        for status, body in results:
            if status == 429:
                self.assertIsNotNone(body)
                self.assertEqual(body.get("code"), 429)
                self.assertEqual(body.get("error"), "Rate limit exceeded")
                self.assertGreaterEqual(body.get("retry_after", 0), 1)

    def test_concurrent_mutation_flood_rate_limiting_enforcement(self):
        """
        Floods /api/webdisplay/action (Mutation tier: max 30 requests / min) with 50 concurrent threads.
        Empirically verifies that exactly 30 proceed to handler and exactly 20 receive HTTP 429.
        """
        ip = "198.51.100.20"
        num_threads = 50

        def make_mutation_request():
            with app.test_client() as c:
                res = c.post("/api/webdisplay/action", json={
                    "player": "TestUser",
                    "action": "tp_spawn"
                }, headers={"X-Forwarded-For": ip})
                return res.status_code

        results = []
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_mutation_request) for _ in range(num_threads)]
            for f in as_completed(futures):
                results.append(f.result())

        count_429 = results.count(429)
        count_passed = len(results) - count_429

        self.assertEqual(len(results), num_threads)
        self.assertEqual(count_passed, 30, f"Expected exactly 30 mutation requests passed, got {count_passed}")
        self.assertEqual(count_429, 20, f"Expected exactly 20 rate-limited (429) requests, got {count_429}")

    def test_client_ip_isolation_under_rate_limit(self):
        """Verifies that an exhausted IP does NOT impact requests from a different IP."""
        bad_ip = "198.51.100.30"
        good_ip = "198.51.100.40"

        with app.test_client() as c:
            # Exhaust bad_ip (5 requests)
            for _ in range(5):
                res = c.get("/connexion", headers={"X-Forwarded-For": bad_ip})
                self.assertEqual(res.status_code, 200)

            # 6th request from bad_ip is blocked
            res_blocked = c.get("/connexion", headers={"X-Forwarded-For": bad_ip})
            self.assertEqual(res_blocked.status_code, 429)

            # Immediate request from good_ip MUST succeed (200 OK)
            res_good = c.get("/connexion", headers={"X-Forwarded-For": good_ip})
            self.assertEqual(res_good.status_code, 200, "Good IP must not be blocked by bad IP's quota exhaustion")


# ==============================================================================
# 4. AETHERSCOPE LOCALGUARD & DNS REBINDING HARNESS
# ==============================================================================

class TestChallengerAetherScopeLocalGuardAndRebinding(unittest.TestCase):
    """Adversarial stress harness for LocalGuard DNS rebinding, CSRF origin, and MCP resilience."""

    def test_localguard_dns_rebinding_simulation(self):
        """Simulates DNS rebinding attacks with foreign and crafted Host headers."""
        malicious_hosts = [
            "evil.attacker.com:3030",
            "attacker.org",
            "192.168.1.1:3030",
            "10.0.0.1:3030",
            "localhost.evil.com:3030",
            "127.0.0.1.attacker.com:3030",
            "127.0.0.1:8080",      # Port mismatch
            "localhost:9000",       # Port mismatch
            "",
            None
        ]
        for host in malicious_hosts:
            self.assertFalse(
                is_localguard_compliant(host=host),
                f"Malicious host '{host}' must be rejected by LocalGuard"
            )

        # Legitimate loopback hosts on port 3030 must pass
        valid_hosts = ["127.0.0.1:3030", "localhost:3030", "[::1]:3030"]
        for host in valid_hosts:
            self.assertTrue(
                is_localguard_compliant(host=host),
                f"Valid host '{host}' must be accepted by LocalGuard"
            )

    def test_localguard_csrf_origin_and_fetch_site_rejection(self):
        """Simulates CSRF attacks with malicious Origin and cross-site Sec-Fetch-Site headers."""
        malicious_origins = [
            "http://evil.com",
            "http://evil.com:3030",
            "https://evil.attacker.org",
            "null",
            "file://",
            "http://localhost.evil.com:3030"
        ]
        for origin in malicious_origins:
            self.assertFalse(
                is_localguard_compliant(host="127.0.0.1:3030", origin=origin),
                f"Malicious origin '{origin}' must be rejected by LocalGuard"
            )

        # Cross-site Sec-Fetch-Site must be rejected
        for bad_site in ["cross-site", "same-site", "invalid"]:
            self.assertFalse(
                is_localguard_compliant(host="127.0.0.1:3030", origin="http://127.0.0.1:3030", sec_fetch_site=bad_site),
                f"Sec-Fetch-Site '{bad_site}' must be rejected"
            )

        # Legitimate origin and Sec-Fetch-Site must pass
        self.assertTrue(
            is_localguard_compliant(host="127.0.0.1:3030", origin="http://127.0.0.1:3030", sec_fetch_site="same-origin")
        )
        self.assertTrue(
            is_localguard_compliant(host="localhost:3030", origin="http://localhost:3030", sec_fetch_site="none")
        )

    def test_aetherscope_client_network_resilience_offline(self):
        """Verifies that AetherScopeClient handles an unreachable port without crashing or hanging."""
        # Port 39999 is intentionally unused
        client = AetherScopeClient(host="127.0.0.1", port=39999, timeout=0.2)
        health = client.check_health()
        self.assertFalse(health.get("online"))
        self.assertEqual(health.get("status"), "offline")

        # Raw request reflects is_offline: True
        raw_req = client.send_request("GET", "/api/health")
        self.assertFalse(raw_req.get("success"))
        self.assertTrue(raw_req.get("is_offline"))

        # Telemetry publish during offline state fails gracefully
        tel = client.publish_telemetry("TestSender", "Heartbeat", "Data")
        self.assertFalse(tel.get("success"))
        self.assertFalse(tel.get("online"))
        self.assertTrue(tel.get("is_offline"))


# ==============================================================================
# 5. LEGITIMATE OPERATIONS GOLDEN PATH
# ==============================================================================

class TestChallengerLegitimateOperations(unittest.TestCase):
    """Verifies that hardened defenses do not break legitimate players or valid gameplay."""

    def setUp(self):
        init_database()
        app.config["TESTING"] = True
        app.config["RATELIMIT_ENABLED"] = True
        rate_limiter.reset()
        self.client = app.test_client()

    def tearDown(self):
        rate_limiter.reset()

    def test_legitimate_movement_and_jump_pad_flight(self):
        """Verifies normal walking and legitimate jump pad flight succeed without false setbacks."""
        sim = EmpiricalPhysicsAntiCheatEngine(x=0.0, y=64.0, z=0.0)

        # Normal walk (0.25 blocks/tick)
        acc_walk, _ = sim.process_movement(0.25, 64.0, 0.0, on_ground=True)
        self.assertTrue(acc_walk)

        # Jump pad velocity applied: player flies at 1.35 speed horizontally
        sim.set_jump_pad_velocity(ticks=20)
        acc_fly, reason_fly = sim.process_movement(0.25 + 1.35, 64.78, 0.0, on_ground=False)
        self.assertTrue(acc_fly)
        self.assertEqual(reason_fly, "ACCEPTED_WITH_VELOCITY")

    def test_legitimate_combat_hit(self):
        """Verifies combat attack within 2.8 blocks facing the target succeeds."""
        sim = EmpiricalPhysicsAntiCheatEngine()
        acc, _ = sim.process_attack(
            attacker_pos=(0.0, 64.0, 0.0),
            attacker_yaw=0.0,  # Looking south (+Z)
            target_pos=(0.0, 64.0, 2.8)  # Target is south at 2.8 blocks
        )
        self.assertTrue(acc)

    def test_legitimate_authenticated_webdisplay_action(self):
        """Verifies authenticated webdisplay action with valid HMAC token succeeds."""
        auth_key = os.environ.get("AETHER_AUTH_KEY", "aethercraft_session_hmac_2026")
        username = "validplayer"
        now = str(int(time.time()))
        token = hmac.new(auth_key.encode("utf-8"), f"{username.lower()}:{now}".encode("utf-8"), hashlib.sha256).hexdigest()

        res = self.client.post("/api/webdisplay/action", json={
            "player": username,
            "action": "tp_spawn",
            "token": token,
            "ts": now
        }, headers={"X-Forwarded-For": "198.51.100.80"})

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "ok")

    def test_legitimate_block_icon_rendering(self):
        """Verifies legitimate block icon rendering produces valid PNG image bytes."""
        materials = ["diamond_block", "gold_ore", "grass_block", "ancient_debris"]
        for mat in materials:
            png_bytes = render_isometric_block_png(mat)
            self.assertTrue(len(png_bytes) > 100)
            self.assertTrue(png_bytes.startswith(b"\x89PNG\r\n\x1a\n"), f"Material {mat} must render valid PNG")


if __name__ == "__main__":
    unittest.main()
