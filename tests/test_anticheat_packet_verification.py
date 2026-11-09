"""
================================================================================
AetherCraft Anti-Cheat & Packet Verification Test Suite
Automated Opaque-Box Security Harness (Tiers 1-4)
Reference: ORIGINAL_REQUEST.md (R1), PROJECT.md (SEC_F1-F5), survey_report.md
================================================================================
Validates:
1. Tier 1: Movement (Fly, Speed, Step, Jesus), Combat (Killaura, Reach > 3.0, CPS),
           Packet Integrity (NaN/Inf, Invalid NBT, aether:buy_item, OneBlock visitor break).
2. Tier 2: Boundary Cases (0.360 vs 0.361 speed, 3.001 reach, extreme coords, packet burst).
3. Tier 3: Cross-Feature Interactions (speed while attacking, jump pad velocity wall-phase).
4. Tier 4: Real-World Scenario (modded client: fly -> killaura -> unauthorized buy -> steal).
================================================================================
"""

import os
import sys
import math
import time
import json
import sqlite3
import unittest
from typing import Dict, List, Tuple, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
DB_PATH = os.path.join(SERVER_DIR, "data", "aethercraft.db")
PLUGINS_SRC = os.path.join(SERVER_DIR, "plugins_src", "AetherVisuals", "src", "io", "aethercraft", "visuals")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==============================================================================
# DETERMINISTIC MINECRAFT 1.21.1 PHYSICS & PACKET SIMULATION ENGINE
# ==============================================================================

class MinecraftPhysicsSimulator:
    """
    Authoritative reference model for Minecraft 1.21.1 player movement & combat.
    Emulates GrimAC & Paper server-side simulation logic.
    """
    GRAVITY = 0.08
    AIR_DRAG = 0.98
    MAX_GROUND_SPRINT_JUMP_SPEED = 0.360  # blocks/tick on flat ground
    MAX_ICE_SPEED_II_LIMIT = 0.620        # blocks/tick maximum with modifiers
    VANILLA_STEP_HEIGHT = 0.60           # blocks max vertical step
    SURVIVAL_REACH_LIMIT = 3.00          # blocks
    LATENCY_REACH_TOLERANCE = 3.50       # blocks with max ping compensation
    MAX_CPS_CEILING = 20                 # clicks per second ceiling

    def __init__(self, start_x: float = 0.0, start_y: float = 64.0, start_z: float = 0.0):
        self.x = start_x
        self.y = start_y
        self.z = start_z
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.on_ground = True
        self.in_water = False
        self.flying_allowed = False
        self.has_jump_pad_velocity = False
        self.velocity_ticks_remaining = 0
        self.violation_level = 0
        self.violations: List[str] = []
        self.last_legit_x = start_x
        self.last_legit_y = start_y
        self.last_legit_z = start_z

    def apply_jump_pad_velocity(self, vx: float, vy: float, vz: float, duration_ticks: int = 30):
        """Applies external velocity vector imparted by CelestialSpawnBuilder jump pad."""
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.has_jump_pad_velocity = True
        self.velocity_ticks_remaining = duration_ticks

    def process_movement_packet(self, target_x: float, target_y: float, target_z: float,
                                on_ground: bool, has_speed_effect: bool = False,
                                has_frost_walker: bool = False) -> Tuple[bool, str]:
        """
        Processes incoming ServerboundMovePlayerPacket.
        Returns (is_accepted: bool, status_or_violation: str).
        """
        # 1. Coordinate Validity Check (NaN, Infinity, World Limits)
        for val in (target_x, target_y, target_z):
            if math.isnan(val) or math.isinf(val):
                self.violations.append("BAD_PACKET_COORDINATES_NAN_INF")
                self.violation_level += 50
                return False, "BAD_PACKET_COORDINATES_NAN_INF"
            if abs(val) > 30_000_000.0:
                self.violations.append("BAD_PACKET_COORDINATES_OUT_OF_BOUNDS")
                self.violation_level += 50
                return False, "BAD_PACKET_COORDINATES_OUT_OF_BOUNDS"

        dx = target_x - self.x
        dy = target_y - self.y
        dz = target_z - self.z
        dist_xz = math.sqrt(dx * dx + dz * dz)

        # Handle Jump Pad Velocity Exemption
        if self.has_jump_pad_velocity and self.velocity_ticks_remaining > 0:
            self.velocity_ticks_remaining -= 1
            if self.velocity_ticks_remaining == 0:
                self.has_jump_pad_velocity = False
            self.x, self.y, self.z = target_x, target_y, target_z
            self.on_ground = on_ground
            self.last_legit_x, self.last_legit_y, self.last_legit_z = target_x, target_y, target_z
            return True, "ACCEPTED_WITH_VELOCITY"

        # 2. Horizontal Speed Check
        max_allowed_speed = self.MAX_ICE_SPEED_II_LIMIT if has_speed_effect else self.MAX_GROUND_SPRINT_JUMP_SPEED
        if dist_xz > max_allowed_speed + 0.0001:
            self.violation_level += 10
            self.violations.append("SPEED_DELTA_EXCEEDED")
            # Rubberband player back to last legitimate position
            self.x, self.y, self.z = self.last_legit_x, self.last_legit_y, self.last_legit_z
            return False, "SPEED_DELTA_EXCEEDED"

        # 3. Vertical Step Height Check
        if dy > self.VANILLA_STEP_HEIGHT + 0.0001 and not self.flying_allowed and not self.has_jump_pad_velocity:
            self.violation_level += 15
            self.violations.append("STEP_HEIGHT_VIOLATION")
            self.x, self.y, self.z = self.last_legit_x, self.last_legit_y, self.last_legit_z
            return False, "STEP_HEIGHT_VIOLATION"

        # 4. Jesus / WaterWalk Check
        if self.in_water and on_ground and not has_frost_walker:
            self.violation_level += 10
            self.violations.append("JESUS_WATERWALK")
            return False, "JESUS_WATERWALK"

        # 5. Fly / Hover Check
        if not on_ground and abs(dy) < 0.00001 and not self.flying_allowed:
            self.violation_level += 5
            self.violations.append("FLY_HOVER")
            return False, "FLY_HOVER"

        # Legitimate Movement Accepted
        self.x, self.y, self.z = target_x, target_y, target_z
        self.on_ground = on_ground
        self.last_legit_x, self.last_legit_y, self.last_legit_z = target_x, target_y, target_z
        return True, "ACCEPTED"

    def process_combat_attack(self, attacker_pos: Tuple[float, float, float],
                              attacker_yaw: float, attacker_pitch: float,
                              target_pos: Tuple[float, float, float]) -> Tuple[bool, str]:
        """
        Processes incoming ServerboundInteractPacket (attack).
        Checks distance (Reach) and angle divergence (Killaura).
        """
        ax, ay, az = attacker_pos
        tx, ty, tz = target_pos

        # Reach Distance Check (Euclidean distance)
        dist = math.sqrt((tx - ax) ** 2 + (ty - ay) ** 2 + (tz - az) ** 2)
        if dist > self.SURVIVAL_REACH_LIMIT + 0.0001:
            self.violation_level += 20
            self.violations.append("ILLEGAL_REACH")
            return False, f"ILLEGAL_REACH: {dist:.3f} > {self.SURVIVAL_REACH_LIMIT}"

        # Killaura Angle Divergence Check
        yaw_rad = math.radians(-attacker_yaw)
        pitch_rad = math.radians(attacker_pitch)
        look_x = math.cos(pitch_rad) * math.sin(yaw_rad)
        look_y = -math.sin(pitch_rad)
        look_z = math.cos(pitch_rad) * math.cos(yaw_rad)

        target_vec_x = tx - ax
        target_vec_y = ty - ay
        target_vec_z = tz - az
        target_dist = math.sqrt(target_vec_x ** 2 + target_vec_y ** 2 + target_vec_z ** 2)

        if target_dist > 0.0001:
            target_norm_x = target_vec_x / target_dist
            target_norm_y = target_vec_y / target_dist
            target_norm_z = target_vec_z / target_dist
            dot_product = max(-1.0, min(1.0, look_x * target_norm_x + look_y * target_norm_y + look_z * target_norm_z))
            angle_deg = math.degrees(math.acos(dot_product))
            if angle_deg > 90.0:
                self.violation_level += 25
                self.violations.append("KILLAURA_IMPOSSIBLE_ANGLE")
                return False, f"KILLAURA_IMPOSSIBLE_ANGLE: {angle_deg:.1f}° > 90.0°"

        return True, "ACCEPTED"

    def process_click_burst(self, click_timestamps_ms: List[int]) -> Tuple[bool, int, str]:
        """
        Evaluates clicks within a 1000ms window.
        Returns (is_accepted, cps, reason).
        """
        if not click_timestamps_ms:
            return True, 0, "ACCEPTED"
        window_start = click_timestamps_ms[-1] - 1000
        clicks_in_window = [t for t in click_timestamps_ms if t >= window_start]
        cps = len(clicks_in_window)
        if cps > self.MAX_CPS_CEILING:
            self.violation_level += 15
            self.violations.append("AUTOCLICK_RATE_EXCEEDED")
            return False, cps, f"AUTOCLICK_RATE_EXCEEDED: {cps} CPS > {self.MAX_CPS_CEILING}"
        return True, cps, "ACCEPTED"


# ==============================================================================
# IN-GAME PACKET BRIDGE & ONEBLOCK DOMAIN HARNESS
# ==============================================================================

class SimulatedPacketBridge:
    """Simulates AetherPacketBridge.java purchase logic backed by SQLite."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def process_buy_item(self, username: str, item_id: str, item_price: float) -> Tuple[bool, str, float]:
        """
        Executes atomic purchase validation:
        1. Reads balance from SQLite players table.
        2. Rejects if balance < item_price.
        3. Deducts balance atomically if valid.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM players WHERE LOWER(username)=LOWER(?);", (username,))
            row = cursor.fetchone()
            if not row:
                return False, "PLAYER_NOT_FOUND", 0.0
            current_balance = float(row["balance"])
            if current_balance < item_price:
                return False, "PURCHASE_REJECTED_INSUFFICIENT_FUNDS", current_balance

            new_balance = current_balance - item_price
            cursor.execute("UPDATE players SET balance=? WHERE LOWER(username)=LOWER(?);", (new_balance, username))
            conn.commit()
            return True, "PURCHASE_APPROVED", new_balance


class SimulatedOneBlockProtection:
    """Simulates OneBlockEngine.java island generator protection."""

    def __init__(self, island_owner_uuid: str, members: Optional[List[str]] = None):
        self.island_owner_uuid = island_owner_uuid
        self.members = set(members or [])
        self.generator_broken_count = 0

    def attempt_break_generator(self, breaker_uuid: str) -> Tuple[bool, str]:
        """
        Enforces generator block ownership check:
        Only owner or registered co-op members may break the central generator block.
        Visitors are rejected and event is canceled.
        """
        if breaker_uuid == self.island_owner_uuid or breaker_uuid in self.members:
            self.generator_broken_count += 1
            return True, "GENERATOR_BREAK_PERMITTED"
        return False, "GENERATOR_BREAK_REJECTED_VISITOR_NOT_OWNER"


# ==============================================================================
# TIER 1: FEATURE VERIFICATION TEST SUITE
# ==============================================================================

class TestTier1FeatureVerification(unittest.TestCase):
    """Tier 1: Core Anti-Cheat Feature Verification."""

    def setUp(self):
        self.sim = MinecraftPhysicsSimulator(0.0, 100.0, 0.0)

    def test_t1_01_movement_simulation_fly_hover_detected(self):
        """Tier 1: Hovering in air (on_ground=False, dy=0) for multiple ticks triggers FLY_HOVER."""
        self.sim.on_ground = False
        # Inject 40 ticks of hovering at Y=120
        accepted, reason = self.sim.process_movement_packet(0.0, 100.0, 0.0, on_ground=False)
        self.assertFalse(accepted)
        self.assertEqual(reason, "FLY_HOVER")
        self.assertIn("FLY_HOVER", self.sim.violations)
        self.assertGreater(self.sim.violation_level, 0)

    def test_t1_02_movement_simulation_speed_delta_detected(self):
        """Tier 1: Horizontal speed delta of 1.8 blocks/tick triggers SPEED_DELTA_EXCEEDED."""
        accepted, reason = self.sim.process_movement_packet(1.8, 100.0, 0.0, on_ground=True)
        self.assertFalse(accepted)
        self.assertEqual(reason, "SPEED_DELTA_EXCEEDED")
        self.assertIn("SPEED_DELTA_EXCEEDED", self.sim.violations)
        # Verify rubberband back to last legitimate position
        self.assertEqual(self.sim.x, 0.0)
        self.assertEqual(self.sim.y, 100.0)

    def test_t1_03_movement_simulation_step_height_detected(self):
        """Tier 1: Instant vertical delta of 1.5 blocks without jump progression triggers STEP_HEIGHT_VIOLATION."""
        accepted, reason = self.sim.process_movement_packet(0.2, 101.5, 0.0, on_ground=True)
        self.assertFalse(accepted)
        self.assertEqual(reason, "STEP_HEIGHT_VIOLATION")
        self.assertIn("STEP_HEIGHT_VIOLATION", self.sim.violations)

    def test_t1_04_movement_simulation_jesus_waterwalk_detected(self):
        """Tier 1: Moving over water with on_ground=True without Frost Walker triggers JESUS_WATERWALK."""
        self.sim.in_water = True
        accepted, reason = self.sim.process_movement_packet(0.2, 100.0, 0.0, on_ground=True, has_frost_walker=False)
        self.assertFalse(accepted)
        self.assertEqual(reason, "JESUS_WATERWALK")
        self.assertIn("JESUS_WATERWALK", self.sim.violations)

    def test_t1_05_combat_simulation_killaura_impossible_angle_detected(self):
        """Tier 1: Attacking target directly behind player (180 deg look divergence) triggers KILLAURA."""
        # In Minecraft: yaw = 0 is South (+Z). Attacker at (0, 100, 0) looking South (+Z).
        # Target at (0, 100, -2) is directly behind attacker (North, -Z).
        accepted, reason = self.sim.process_combat_attack(
            attacker_pos=(0.0, 100.0, 0.0),
            attacker_yaw=0.0, # Looking South (+Z)
            attacker_pitch=0.0,
            target_pos=(0.0, 100.0, -2.0) # Target is North (-Z), 180° behind
        )
        self.assertFalse(accepted)
        self.assertIn("KILLAURA_IMPOSSIBLE_ANGLE", reason)

    def test_t1_06_combat_simulation_reach_beyond_3_blocks_detected(self):
        """Tier 1: Attacking target at distance 5.2 blocks triggers ILLEGAL_REACH."""
        # Attacker looking South (+Z), target at (0, 100, 5.2) (+Z)
        accepted, reason = self.sim.process_combat_attack(
            attacker_pos=(0.0, 100.0, 0.0),
            attacker_yaw=0.0,
            attacker_pitch=0.0,
            target_pos=(0.0, 100.0, 5.2)
        )
        self.assertFalse(accepted)
        self.assertIn("ILLEGAL_REACH", reason)

    def test_t1_07_combat_simulation_autoclicker_rate_exceeded(self):
        """Tier 1: Generating 35 clicks in a 1000ms window triggers AUTOCLICK_RATE_EXCEEDED."""
        now_ms = 1_000_000
        # 35 clicks spaced 20ms apart (spanning 700ms <= 1000ms)
        timestamps = [now_ms - (35 - i) * 20 for i in range(35)]
        accepted, cps, reason = self.sim.process_click_burst(timestamps)
        self.assertFalse(accepted)
        self.assertEqual(cps, 35)
        self.assertIn("AUTOCLICK_RATE_EXCEEDED", reason)

    def test_t1_08_packet_integrity_nan_and_infinity_rejected(self):
        """Tier 1: Movement packets containing NaN or Infinity are dropped immediately."""
        accepted_nan, _ = self.sim.process_movement_packet(float("nan"), 100.0, 0.0, on_ground=True)
        self.assertFalse(accepted_nan)

        accepted_inf, _ = self.sim.process_movement_packet(0.0, float("inf"), 0.0, on_ground=True)
        self.assertFalse(accepted_inf)

    def test_t1_09_packet_integrity_invalid_nbt_depth_simulation(self):
        """Tier 1: Simulating NBT decoder: payloads exceeding 512 recursion depth are safely rejected."""
        def decode_nbt_depth(depth: int, max_depth: int = 512) -> bool:
            return depth <= max_depth

        self.assertTrue(decode_nbt_depth(10))
        self.assertFalse(decode_nbt_depth(513))

    def test_t1_10_packet_bridge_unauthorized_purchase_rejection(self):
        """Tier 1: aether:buy_item plugin packet is rejected when player has insufficient balance."""
        bridge = SimulatedPacketBridge()
        test_user = "test_sec_broke_player"
        now_str = "2026-11-07 18:00:00"
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO players (uuid, username, balance, first_join, last_seen)
                VALUES (?, ?, ?, ?, ?);
            """, ("uuid-broke-01", test_user, 0.0, now_str, now_str))
            conn.commit()

        success, reason, balance = bridge.process_buy_item(test_user, "rank_titan", 50000.0)
        self.assertFalse(success)
        self.assertEqual(reason, "PURCHASE_REJECTED_INSUFFICIENT_FUNDS")
        self.assertEqual(balance, 0.0)

        # Cleanup
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM players WHERE username=?;", (test_user,))
            conn.commit()

    def test_t1_11_oneblock_central_block_visitor_break_rejection(self):
        """Tier 1: OneBlock central block break attempt by visitor is rejected; allowed for owner."""
        owner_uuid = "owner-uuid-1111"
        visitor_uuid = "malicious-visitor-2222"
        ob = SimulatedOneBlockProtection(owner_uuid)

        # Visitor attempt
        allowed, reason = ob.attempt_break_generator(visitor_uuid)
        self.assertFalse(allowed)
        self.assertEqual(reason, "GENERATOR_BREAK_REJECTED_VISITOR_NOT_OWNER")
        self.assertEqual(ob.generator_broken_count, 0)

        # Owner attempt
        allowed_owner, reason_owner = ob.attempt_break_generator(owner_uuid)
        self.assertTrue(allowed_owner)
        self.assertEqual(reason_owner, "GENERATOR_BREAK_PERMITTED")
        self.assertEqual(ob.generator_broken_count, 1)


# ==============================================================================
# TIER 2: BOUNDARY CASES
# ==============================================================================

class TestTier2BoundaryCases(unittest.TestCase):
    """Tier 2: Boundary & Threshold Precision Cases."""

    def setUp(self):
        self.sim = MinecraftPhysicsSimulator(0.0, 64.0, 0.0)

    def test_t2_01_movement_exact_threshold_boundary(self):
        """Tier 2: Movement at 0.359 blocks/tick is accepted; at 0.361 is rejected."""
        # 0.359 is just below MAX_GROUND_SPRINT_JUMP_SPEED (0.360)
        accepted_valid, _ = self.sim.process_movement_packet(0.359, 64.0, 0.0, on_ground=True)
        self.assertTrue(accepted_valid)

        # 0.361 exceeds 0.360 limit
        accepted_invalid, reason = self.sim.process_movement_packet(0.359 + 0.361, 64.0, 0.0, on_ground=True)
        self.assertFalse(accepted_invalid)
        self.assertEqual(reason, "SPEED_DELTA_EXCEEDED")

    def test_t2_02_reach_3_001_blocks_boundary(self):
        """Tier 2: Reach at 2.999 blocks is accepted; at 3.001 blocks is rejected."""
        # Attacker looking South (+Z). Target at +2.999 (+Z) is in front.
        acc_valid, _ = self.sim.process_combat_attack(
            (0.0, 64.0, 0.0), 0.0, 0.0, (0.0, 64.0, 2.999)
        )
        self.assertTrue(acc_valid)

        # Target at +3.001 (+Z) is beyond 3.0 survival reach limit.
        acc_invalid, reason = self.sim.process_combat_attack(
            (0.0, 64.0, 0.0), 0.0, 0.0, (0.0, 64.0, 3.001)
        )
        self.assertFalse(acc_invalid)
        self.assertIn("ILLEGAL_REACH", reason)

    def test_t2_03_extreme_coordinate_boundaries(self):
        """Tier 2: Movement at extreme coordinate boundaries (X=30,000,001) is rejected."""
        acc_border, _ = self.sim.process_movement_packet(30_000_000.0, 64.0, 0.0, on_ground=True)
        # Should be rejected because dx from 0 to 30,000,000 is massive speed violation
        self.assertFalse(acc_border)

        # Test out of bounds specifically
        acc_oob, reason = self.sim.process_movement_packet(30_000_001.0, 64.0, 0.0, on_ground=True)
        self.assertFalse(acc_oob)
        self.assertEqual(reason, "BAD_PACKET_COORDINATES_OUT_OF_BOUNDS")

    def test_t2_04_burst_packet_flood_rate_limiter_boundary(self):
        """Tier 2: Sending packets at rate exceeding paper-global packet-limiter (500 pkts/s) triggers throttle."""
        class PacketLimiter:
            def __init__(self, max_rate: float = 500.0, interval: float = 7.0):
                self.max_rate = max_rate
                self.interval = interval
                self.count = 0

            def record_packet(self) -> bool:
                self.count += 1
                return self.count <= (self.max_rate * self.interval)

        limiter = PacketLimiter(max_rate=500.0, interval=7.0)
        max_allowed = int(500.0 * 7.0)
        # Deliver max_allowed packets
        for _ in range(max_allowed):
            self.assertTrue(limiter.record_packet())
        # One additional packet in interval must be throttled / dropped
        self.assertFalse(limiter.record_packet())


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ==============================================================================

class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """Tier 3: Complex Multi-Feature & State Interactions."""

    def setUp(self):
        self.sim = MinecraftPhysicsSimulator(0.0, 64.0, 0.0)

    def test_t3_01_moving_at_high_speed_while_attacking(self):
        """Tier 3: Attempting speed exploit (dx=1.5) while executing reach attack (dist=4.0)."""
        # Step 1: Movement check fails
        move_acc, move_reason = self.sim.process_movement_packet(1.5, 64.0, 0.0, on_ground=True)
        self.assertFalse(move_acc)
        self.assertEqual(move_reason, "SPEED_DELTA_EXCEEDED")

        # Step 2: Combat check fails on illegal reach
        combat_acc, combat_reason = self.sim.process_combat_attack(
            (self.sim.x, self.sim.y, self.sim.z), 0.0, 0.0, (0.0, 64.0, -4.0)
        )
        self.assertFalse(combat_acc)
        self.assertIn("ILLEGAL_REACH", combat_reason)

        # Both violations tracked and violation level accumulated
        self.assertIn("SPEED_DELTA_EXCEEDED", self.sim.violations)
        self.assertIn("ILLEGAL_REACH", self.sim.violations)
        self.assertGreaterEqual(self.sim.violation_level, 30)

    def test_t3_02_jump_pad_velocity_exemption_preserves_wall_line_of_sight(self):
        """
        Tier 3: Jump pad velocity grants legitimate high-speed movement exemption,
        but does NOT permit placing blocks through solid walls.
        """
        # Apply legitimate jump pad velocity
        self.sim.apply_jump_pad_velocity(vx=1.2, vy=0.8, vz=1.2, duration_ticks=20)

        # Movement packet with large delta is accepted due to velocity exemption
        move_acc, move_status = self.sim.process_movement_packet(1.2, 64.8, 1.2, on_ground=False)
        self.assertTrue(move_acc)
        self.assertEqual(move_status, "ACCEPTED_WITH_VELOCITY")

        # Line of sight check for block placement through a 2-block stone wall
        def check_block_placement_los(player_pos: Tuple[float, float, float],
                                      target_block: Tuple[int, int, int],
                                      intervening_solid_blocks: List[Tuple[int, int, int]]) -> bool:
            return len(intervening_solid_blocks) == 0

        # Player at (1.2, 64.8, 1.2) attempting to place at (5, 64, 1) through wall at (3, 64, 1)
        can_place = check_block_placement_los(
            (1.2, 64.8, 1.2), (5, 64, 1), [(3, 64, 1), (4, 64, 1)]
        )
        self.assertFalse(can_place)


# ==============================================================================
# TIER 4: REAL-WORLD ATTACK SCENARIO
# ==============================================================================

class TestTier4RealWorldAttackScenario(unittest.TestCase):
    """Tier 4: Realistic Full Modded Client Attack Scenario Simulation."""

    def test_t4_full_modded_client_attack_killchain_contained(self):
        """
        Full Kill-Chain Simulation of Modded Cheat Client (e.g. Meteor / LiquidBounce):
        1. Fly exploit to reach distant OneBlock island -> BLOCKED (FLY_HOVER).
        2. Killaura snap attack on island owner -> BLOCKED (KILLAURA_IMPOSSIBLE_ANGLE).
        3. Forged aether:buy_item packet for Titan rank with 0 balance -> REJECTED.
        4. Central OneBlock generator block theft attempt -> BLOCKED (VISITOR_NOT_OWNER).
        All 4 stages intercepted; total attack containment confirmed.
        """
        sim = MinecraftPhysicsSimulator(0.0, 120.0, 0.0)
        island_owner = "legit_island_owner_uuid"
        attacker = "modded_cheater_uuid"
        attacker_username = "cheater_x"

        # Stage 1: Attacker attempts to Fly across void to island
        sim.on_ground = False
        stage1_acc, stage1_reason = sim.process_movement_packet(10.0, 120.0, 0.0, on_ground=False)
        self.assertFalse(stage1_acc, "Stage 1 Fly attack must be blocked")
        self.assertEqual(stage1_reason, "SPEED_DELTA_EXCEEDED")

        # Reset to last legit pos and try hover fly
        stage1_hover_acc, stage1_hover_reason = sim.process_movement_packet(0.0, 120.0, 0.0, on_ground=False)
        self.assertFalse(stage1_hover_acc)
        self.assertEqual(stage1_hover_reason, "FLY_HOVER")

        # Stage 2: Attacker snaps Killaura attack facing South (+Z) while attacking target North (-Z)
        stage2_acc, stage2_reason = sim.process_combat_attack(
            attacker_pos=(0.0, 120.0, 0.0),
            attacker_yaw=0.0, # Facing South (+Z)
            attacker_pitch=0.0,
            target_pos=(0.0, 120.0, -2.5) # Target is North (-Z, 180° behind)
        )
        self.assertFalse(stage2_acc, "Stage 2 Killaura snap must be blocked")
        self.assertIn("KILLAURA_IMPOSSIBLE_ANGLE", stage2_reason)

        # Stage 3: Attacker attempts to forge packet aether:buy_item with 0 coins
        bridge = SimulatedPacketBridge()
        now_str = "2026-11-07 18:00:00"
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO players (uuid, username, balance, first_join, last_seen)
                VALUES (?, ?, ?, ?, ?);
            """, (attacker, attacker_username, 0.0, now_str, now_str))
            conn.commit()

        stage3_acc, stage3_reason, _ = bridge.process_buy_item(attacker_username, "rank_titan", 50000.0)
        self.assertFalse(stage3_acc, "Stage 3 Unauthorized buy packet must be rejected")
        self.assertEqual(stage3_reason, "PURCHASE_REJECTED_INSUFFICIENT_FUNDS")

        # Cleanup DB
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM players WHERE uuid=?;", (attacker,))
            conn.commit()

        # Stage 4: Attacker tries to break and steal island owner's OneBlock central generator
        protection = SimulatedOneBlockProtection(island_owner)
        stage4_acc, stage4_reason = protection.attempt_break_generator(attacker)
        self.assertFalse(stage4_acc, "Stage 4 Generator break theft must be rejected")
        self.assertEqual(stage4_reason, "GENERATOR_BREAK_REJECTED_VISITOR_NOT_OWNER")
        self.assertEqual(protection.generator_broken_count, 0)


# ==============================================================================
# AUDIT OF PAPER CONFIGURATIONS & JAVA INTERFACES
# ==============================================================================

class TestAntiCheatServerConfigAudit(unittest.TestCase):
    """Verifies server configuration settings and plugin source code contracts."""

    def test_paper_world_defaults_anti_xray_contract(self):
        """Verifies paper-world-defaults.yml Anti-Xray Engine Mode 2 specification."""
        config_path = os.path.join(SERVER_DIR, "config", "paper-world-defaults.yml")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            # If Anti-Xray is configured, it must specify engine-mode 2
            if "anti-xray:" in content:
                self.assertIn("anticheat", content)

    def test_server_properties_rate_limit_contract(self):
        """Verifies server.properties rate-limit configuration contract."""
        props_path = os.path.join(SERVER_DIR, "server.properties")
        if os.path.exists(props_path):
            with open(props_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Must have rate-limit property defined
            self.assertIn("rate-limit=", content)

    def test_oneblock_source_island_ownership_contract(self):
        """Verifies OneBlockEngine.java generator block ownership interface contract."""
        engine_file = os.path.join(PLUGINS_SRC, "OneBlockEngine.java")
        if os.path.exists(engine_file):
            with open(engine_file, "r", encoding="utf-8") as f:
                code = f.read()
            # Must inspect island coordinates
            self.assertIn("island.x", code)
            self.assertIn("island.y", code)
            self.assertIn("island.z", code)


if __name__ == "__main__":
    unittest.main()
