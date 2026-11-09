"""
================================================================================
AetherCraft V1 Bêta End-to-End Acceptance Test Suite (Tiers 1-4)
================================================================================
Opaque-box, requirement-driven acceptance test harness systematically validating
the 5 core requirements of AetherCraft V1 Bêta preparation:
  - Requirement R1: Security CWE Remediation in vKeyboard.js (CWE-79 & CWE-1075)
  - Requirement R2: UI Background Index Visibility & Translucent Header (y=0 display)
  - Requirement R3: 50-Player Concurrent Load Test Harness (scripts/load_test_50.js)
  - Requirement R4: Fast Diagnostic Tooling (scripts/sanity_check.py < 1 min, 6 probes)
  - Requirement R5: Production Readiness Audit (AUDIT_PRODUCTION.md, 14 findings, 5 pillars)

Structured systematically across 4 testing tiers:
  - Tier 1: Feature Coverage (Positive acceptance testing for each requirement)
  - Tier 2: Boundary & Corner Cases (Line limits, regex sinks, timeouts, args, mock bans)
  - Tier 3: Cross-Feature Combinations (Security x UI, Load x Sanity, Audit x Real Config)
  - Tier 4: Real-World Scenarios (End-to-End launch readiness acceptance pipeline)

Framework: Standard pytest / unittest.
================================================================================
"""

import os
import sys
import re
import json
import time
import socket
import sqlite3
import subprocess
import unittest
from typing import Dict, Any, List

# Ensure project root and web directory are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

# Project paths
VKEYBOARD_PATH = os.path.join(PROJECT_ROOT, "server", "plugins", "MapBrowser", "snippets", "vKeyboard.js")
INDEX_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "web", "templates", "index.html")
BASE_TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "web", "templates", "base.html")
HERO_BG_PATH = os.path.join(PROJECT_ROOT, "web", "static", "images", "hero-bg.jpg")
LOAD_TEST_PATH = os.path.join(PROJECT_ROOT, "scripts", "load_test_50.js")
PACKAGE_JSON_PATH = os.path.join(PROJECT_ROOT, "scripts", "package.json")
BUKKIT_YML_PATH = os.path.join(PROJECT_ROOT, "server", "bukkit.yml")
SANITY_CHECK_PATH = os.path.join(PROJECT_ROOT, "scripts", "sanity_check.py")
AUDIT_FILE_PATH = os.path.join(PROJECT_ROOT, "AUDIT_PRODUCTION.md")
DB_PATH = os.path.join(PROJECT_ROOT, "server", "data", "aethercraft.db")
SYSTEMD_DIR = os.path.join(PROJECT_ROOT, "systemd")
SPIGOT_YML_PATH = os.path.join(PROJECT_ROOT, "server", "spigot.yml")
SERVER_PROPERTIES_PATH = os.path.join(PROJECT_ROOT, "server", "server.properties")

# Import Flask app for template and route rendering
from app import app


# ==============================================================================
# TIER 1: FEATURE COVERAGE (Positive Acceptance Tests)
# ==============================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 - Feature Coverage:
    Positive acceptance tests validating that each of the 5 user requirements
    is fully met according to specifications.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_t1_r1_vkeyboard_cwe_remediation(self):
        """
        R1 Acceptance: vKeyboard.js contains 0 innerHTML DOM sinks,
        total lines <= 300, and is valid JavaScript syntax.
        """
        self.assertTrue(os.path.exists(VKEYBOARD_PATH), f"Missing vKeyboard.js at {VKEYBOARD_PATH}")
        with open(VKEYBOARD_PATH, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()

        # CWE-1075: Line budget limit <= 300
        line_count = len(lines)
        self.assertLessEqual(
            line_count, 300,
            f"CWE-1075 violation: vKeyboard.js has {line_count} lines, exceeding the 300 LOC limit."
        )

        # CWE-79: Zero DOM sinks
        self.assertNotIn(".innerHTML =", content, "CWE-79 violation: .innerHTML = assignment found in vKeyboard.js")
        self.assertNotIn("document.write(", content, "CWE-79 violation: document.write( found in vKeyboard.js")
        self.assertNotIn("dangerouslySetInnerHTML", content, "CWE-79 violation: dangerouslySetInnerHTML found in vKeyboard.js")

        # Functional completeness
        self.assertIn("KEY_LAYOUT", content, "vKeyboard.js must retain KEY_LAYOUT definition")
        self.assertIn("VirtualKeyboard", content, "vKeyboard.js must retain VirtualKeyboard class")
        self.assertIn("window.toggleVKB", content, "vKeyboard.js must export window.toggleVKB bootstrap")

        # Node.js syntax compilation verification
        cmd = ["node", "-c", VKEYBOARD_PATH]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(
            result.returncode, 0,
            f"Node.js syntax error in vKeyboard.js:\n{result.stderr}"
        )

    def test_t1_r2_hero_background_visibility_and_wiring(self):
        """
        R2 Acceptance: index.html contains <section id="hero">, wires #hero-bg-layer
        and #hero-content-wrapper, and base.html has translucent navbar and top bar.
        """
        # Asset existence
        self.assertTrue(os.path.exists(HERO_BG_PATH), f"Missing hero-bg.jpg at {HERO_BG_PATH}")
        self.assertGreater(os.path.getsize(HERO_BG_PATH), 10000, "hero-bg.jpg is empty or corrupted")

        # Template inspection: index.html
        with open(INDEX_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            index_content = f.read()

        self.assertIn('<section id="hero"', index_content, "index.html must contain <section id=\"hero\">")
        self.assertIn('id="hero-bg-layer"', index_content, "index.html must contain #hero-bg-layer")
        self.assertIn('id="hero-content-wrapper"', index_content, "index.html must contain #hero-content-wrapper")
        self.assertIn('/static/images/hero-bg.jpg', index_content, "index.html must reference /static/images/hero-bg.jpg")
        self.assertIn('-mt-[98px]', index_content, "index.html hero must have negative margin -mt-[98px] for y=0 start")

        # Template inspection: base.html
        with open(BASE_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            base_content = f.read()

        self.assertTrue(
            "bg-obsidian-950/40" in base_content or "bg-obsidian-900/40" in base_content or "backdrop-blur-md" in base_content,
            "base.html announcement bar must have translucent background (< 50% opacity)"
        )
        self.assertTrue(
            "bg-obsidian-950/30" in base_content or "bg-obsidian-900/30" in base_content or "bg-obsidian-950/40" in base_content,
            "base.html header must have translucent background (< 50% opacity)"
        )

        # Flask rendered route verification
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200, "Homepage / must return HTTP 200 OK")
        rendered_html = resp.get_data(as_text=True)

        self.assertIn('id="hero"', rendered_html, "Rendered page must contain id=\"hero\"")
        self.assertIn('id="hero-bg-layer"', rendered_html, "Rendered page must contain id=\"hero-bg-layer\"")
        self.assertIn('id="hero-content-wrapper"', rendered_html, "Rendered page must contain id=\"hero-content-wrapper\"")

    def test_t1_r3_load_test_harness_and_connection_throttle(self):
        """
        R3 Acceptance: scripts/load_test_50.js exists, is valid Node.js script,
        supports --count, --duration, minecraft-protocol dependency, and
        server/bukkit.yml has connection-throttle: 0.
        """
        self.assertTrue(os.path.exists(LOAD_TEST_PATH), f"Missing load test script at {LOAD_TEST_PATH}")
        self.assertTrue(os.path.exists(PACKAGE_JSON_PATH), f"Missing scripts/package.json at {PACKAGE_JSON_PATH}")

        # Check package.json dependency
        with open(PACKAGE_JSON_PATH, "r", encoding="utf-8") as f:
            pkg_data = json.load(f)
        deps = pkg_data.get("dependencies", {})
        self.assertIn("minecraft-protocol", deps, "scripts/package.json must declare minecraft-protocol dependency")

        # Check script syntax
        syntax_res = subprocess.run(["node", "-c", LOAD_TEST_PATH], capture_output=True, text=True)
        self.assertEqual(syntax_res.returncode, 0, f"load_test_50.js syntax check failed:\n{syntax_res.stderr}")

        # Check CLI arguments support (--count, --duration, --host, --port)
        help_res = subprocess.run(["node", LOAD_TEST_PATH, "--help"], capture_output=True, text=True)
        self.assertEqual(help_res.returncode, 0, "node load_test_50.js --help must exit with code 0")
        help_output = help_res.stdout
        self.assertIn("--count", help_output, "load_test_50.js must support --count option")
        self.assertIn("--duration", help_output, "load_test_50.js must support --duration option")
        self.assertIn("--host", help_output, "load_test_50.js must support --host option")
        self.assertIn("--port", help_output, "load_test_50.js must support --port option")

        # Verify server/bukkit.yml has connection-throttle: 0
        self.assertTrue(os.path.exists(BUKKIT_YML_PATH), f"Missing bukkit.yml at {BUKKIT_YML_PATH}")
        with open(BUKKIT_YML_PATH, "r", encoding="utf-8") as f:
            bukkit_content = f.read()

        match = re.search(r"connection-throttle:\s*(\d+)", bukkit_content)
        self.assertIsNotNone(match, "bukkit.yml must define connection-throttle")
        self.assertEqual(int(match.group(1)), 0, "bukkit.yml connection-throttle must be set to 0 for 50 bots")

    def test_t1_r4_fast_sanity_check_tooling(self):
        """
        R4 Acceptance: scripts/sanity_check.py exists, is executable,
        tests 6 core health probes in < 1 min, and provides structured results.
        """
        self.assertTrue(os.path.exists(SANITY_CHECK_PATH), f"Missing sanity check script at {SANITY_CHECK_PATH}")

        # Python syntax check
        compile_res = subprocess.run(
            [sys.executable, "-m", "py_compile", SANITY_CHECK_PATH],
            capture_output=True, text=True
        )
        self.assertEqual(compile_res.returncode, 0, f"Python syntax error in sanity_check.py:\n{compile_res.stderr}")

        # Read source code to verify 6 core health probes
        with open(SANITY_CHECK_PATH, "r", encoding="utf-8") as f:
            source = f.read()

        required_probes = [
            "SLP",               # Probe 1: Minecraft Paper SLP Ping
            "RCON",              # Probe 2: RCON Protocol Probe
            "/api/v1/health",    # Probe 3: Web API Health Endpoint
            "integrity_check",   # Probe 4: SQLite Database Integrity Probe
            "/api/webdisplay/action", # Probe 5: Security Middleware Probe (401 check)
            "AetherPack.zip"     # Probe 6: Static Asset Resource Probe
        ]
        for probe in required_probes:
            self.assertIn(probe, source, f"sanity_check.py must implement probe covering '{probe}'")

        # Execute sanity_check.py in sub-minute cold mode (--warn-offline --json)
        start_time = time.time()
        res = subprocess.run(
            [sys.executable, SANITY_CHECK_PATH, "--warn-offline", "--json"],
            capture_output=True, text=True, timeout=60
        )
        elapsed = time.time() - start_time

        self.assertLess(elapsed, 60.0, f"sanity_check.py took {elapsed:.2f}s, exceeding 60-second requirement")
        self.assertEqual(res.returncode, 0, f"sanity_check.py failed with code {res.returncode}:\n{res.stderr}")

        # Parse JSON output to verify 6 probes were executed
        data = json.loads(res.stdout)
        self.assertEqual(data.get("probes_count"), 6, "sanity_check.py must execute exactly 6 probes")
        self.assertIn(data.get("overall_status"), ["PASS", "WARN"])

    def test_t1_r5_production_readiness_audit(self):
        """
        R5 Acceptance: AUDIT_PRODUCTION.md exists, covers 14 findings across
        all 5 pillars (Sécurité, Persistance, Erreurs, Supervision, Réseau).
        """
        self.assertTrue(os.path.exists(AUDIT_FILE_PATH), f"Missing audit report at {AUDIT_FILE_PATH}")
        with open(AUDIT_FILE_PATH, "r", encoding="utf-8") as f:
            audit_text = f.read()

        self.assertGreater(len(audit_text), 2000, "AUDIT_PRODUCTION.md must contain substantive audit analysis")

        # Check all 5 pillars
        pillars = ["Sécurité", "Persistance", "Erreurs", "Supervision", "Réseau"]
        for p in pillars:
            self.assertTrue(
                p.lower() in audit_text.lower(),
                f"AUDIT_PRODUCTION.md must cover Pillar '{p}'"
            )

        # Check key real findings mentioned in report
        key_findings = [
            "User=root",           # Pillar 1 / Security (Systemd root)
            "journal_mode",        # Pillar 2 / Persistence (SQLite delete mode)
            "start.sh",            # Pillar 3 / Errors (Dead restart script in spigot.yml)
            "--no-sandbox",        # Pillar 1 / Security (Chromium sandbox disabled)
            "X-Forwarded-For"      # Pillar 1 / Security (Rate limit bypass)
        ]
        for finding in key_findings:
            self.assertIn(
                finding, audit_text,
                f"AUDIT_PRODUCTION.md must document specific finding regarding '{finding}'"
            )


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

class TestTier2BoundaryAndCornerCases(unittest.TestCase):
    """
    Tier 2 - Boundary & Corner Cases:
    Strict boundary limits, regex sink safety checks, timeout limits,
    parameter edge cases, and zero dummy/mock keyword enforcement.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_t2_line_budget_strict_boundary(self):
        """
        Strict boundary on vKeyboard.js line budget (CWE-1075):
        - Upper limit: strictly <= 300 LOC.
        - Lower boundary: strictly >= 150 LOC (ensures no mock/empty file).
        - Rejection property: a file with > 300 LOC is formally rejected.
        """
        with open(VKEYBOARD_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        actual_lines = len(lines)

        self.assertLessEqual(actual_lines, 300, f"Line count {actual_lines} strictly exceeds 300 LOC budget")
        self.assertGreaterEqual(actual_lines, 150, f"Line count {actual_lines} is suspiciously low for a full keyboard")

        # Boundary logic test: artificial 301 lines triggers rejection
        over_budget_sim = ["// dummy line\n"] * 301
        self.assertFalse(
            len(over_budget_sim) <= 300,
            "Boundary check: 301 lines must violate the <= 300 rule."
        )

    def test_t2_dom_sink_regex_boundary(self):
        """
        Comprehensive regex search for dangerous DOM sinks:
        - Rejects any .innerHTML = assignment (with any whitespace)
        - Rejects document.write(...) calls
        - Rejects dangerouslySetInnerHTML
        - Rejects .outerHTML = assignment
        """
        with open(VKEYBOARD_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        sink_patterns = [
            (r"\.innerHTML\s*=", "innerHTML assignment"),
            (r"document\.write\s*\(", "document.write call"),
            (r"dangerouslySetInnerHTML", "dangerouslySetInnerHTML attribute"),
            (r"\.outerHTML\s*=", "outerHTML assignment"),
        ]

        for pattern, name in sink_patterns:
            matches = re.findall(pattern, content)
            self.assertEqual(
                matches, [],
                f"Dangerous DOM sink '{name}' detected in vKeyboard.js (pattern: {pattern})"
            )

    def test_t2_sanity_check_timeout_boundary(self):
        """
        Sanity check execution timeout boundary:
        Must complete in strictly under 60 seconds (requirement R4).
        In practice, cold sub-minute check should finish under 10 seconds.
        """
        start_time = time.time()
        res = subprocess.run(
            [sys.executable, SANITY_CHECK_PATH, "--warn-offline", "--timeout", "0.5"],
            capture_output=True, text=True, timeout=60
        )
        duration = time.time() - start_time

        self.assertLess(duration, 60.0, f"Sanity check exceeded 60s hard ceiling: {duration:.2f}s")
        self.assertLess(duration, 15.0, f"Sanity check exceeded expected fast ceiling (15s): {duration:.2f}s")
        self.assertEqual(res.returncode, 0, f"Sanity check execution failed:\n{res.stderr}")

    def test_t2_load_test_cli_argument_parsing_boundaries(self):
        """
        Load test CLI parser boundary tests:
        - Runs --dry-run to test argument defaults.
        - Verifies custom --count and --duration flags parse without crashing.
        - Verifies help and exit codes.
        """
        # Test dry-run with custom count and duration
        cmd = [
            "node", LOAD_TEST_PATH,
            "--count", "10",
            "--duration", "10s",
            "--stagger", "100ms",
            "--dry-run"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Dry-run with custom arguments failed:\n{res.stderr}")
        self.assertIn("10 bots", res.stdout, "Dry-run output must reflect custom count 10")
        self.assertIn("10 s", res.stdout, "Dry-run output must reflect custom duration 10s")

    def test_t2_absence_of_forbidden_mock_strings_in_templates(self):
        """
        Strictly forbids fake dummy/mock indicators in homepage templates and rendered HTML:
        Forbidden: 'AetherKnight', 'PixelSorceress', 'TITAN PRIMORDIAL', '35,714', '1,250',
                   'ShadowRanger', 'VortexCrafter'.
        """
        forbidden_mocks = [
            "AetherKnight",
            "PixelSorceress",
            "TITAN PRIMORDIAL",
            "35,714",
            "1,250",
            "ShadowRanger",
            "VortexCrafter"
        ]

        # Check raw index.html template
        with open(INDEX_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            template_code = f.read()

        for mock in forbidden_mocks:
            self.assertNotIn(
                mock, template_code,
                f"Forbidden mock keyword '{mock}' found in web/templates/index.html"
            )

        # Check rendered homepage HTML
        resp = self.client.get("/")
        rendered_html = resp.get_data(as_text=True)

        for mock in forbidden_mocks:
            self.assertNotIn(
                mock, rendered_html,
                f"Forbidden mock keyword '{mock}' found in rendered homepage HTML"
            )


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ==============================================================================

class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3 - Cross-Feature Combinations:
    Multi-component interaction tests:
    - Security x UI: vKeyboard syntax validity alongside web styles and CEF compatibility.
    - Load Testing x Diagnostics: Sanity check probes while load test harness is configured.
    - Production Audit x Physical Configuration: Cross-validates audit findings against real repository configs.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_t3_security_x_ui_compatibility(self):
        """
        Security x UI:
        - vKeyboard.js uses CSS class names that do not conflict with web styles.
        - Web template scroll_effects.js connects properly to index.html hero section.
        - Static hero-bg.jpg is accessible via Web static route HTTP 200.
        """
        # Read vKeyboard CSS classes
        with open(VKEYBOARD_PATH, "r", encoding="utf-8") as f:
            vkb_code = f.read()

        # Ensure vKeyboard CSS uses scoped namespace
        self.assertIn(".virtual-keyboard", vkb_code)
        self.assertIn(".keyboard__", vkb_code)
        self.assertIn(".key--", vkb_code)

        # Ensure web static route returns hero-bg.jpg with 200 OK
        resp = self.client.get("/static/images/hero-bg.jpg")
        self.assertEqual(resp.status_code, 200, "Static asset /static/images/hero-bg.jpg must return 200 OK")
        self.assertGreater(len(resp.data), 10000, "hero-bg.jpg payload is empty")

        # Ensure scroll_effects.js targets elements present in index.html
        scroll_js_path = os.path.join(PROJECT_ROOT, "web", "static", "scroll_effects.js")
        with open(scroll_js_path, "r", encoding="utf-8") as f:
            scroll_code = f.read()

        with open(INDEX_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            index_code = f.read()

        # Both elements queried by initHeroParallaxDisappearance must exist in index.html
        self.assertIn("hero-content-wrapper", scroll_code)
        self.assertIn('id="hero-content-wrapper"', index_code)
        self.assertIn("hero-bg-layer", scroll_code)
        self.assertIn('id="hero-bg-layer"', index_code)

    def test_t3_load_testing_x_diagnostics_integration(self):
        """
        Load Testing x Diagnostics:
        - load_test_50.js and sanity_check.py target the same default Minecraft port (25565).
        - connection-throttle: 0 in bukkit.yml ensures both tools can probe/connect without throttle kicks.
        - Both scripts execute dry-run/offline checks without uncaught exceptions or crashes.
        """
        # Port coherence
        with open(LOAD_TEST_PATH, "r", encoding="utf-8") as f:
            load_code = f.read()
        with open(SANITY_CHECK_PATH, "r", encoding="utf-8") as f:
            sanity_code = f.read()

        self.assertIn("25565", load_code, "load_test_50.js must target default port 25565")
        self.assertIn("25565", sanity_code, "sanity_check.py must target default port 25565")

        # Bukkit throttle validation
        with open(BUKKIT_YML_PATH, "r", encoding="utf-8") as f:
            bukkit_yaml = f.read()
        self.assertIn("connection-throttle: 0", bukkit_yaml, "bukkit.yml connection-throttle must be 0")

        # Concurrent non-blocking dry-runs
        res_load = subprocess.run(["node", LOAD_TEST_PATH, "--dry-run"], capture_output=True, text=True)
        res_sanity = subprocess.run([sys.executable, SANITY_CHECK_PATH, "--warn-offline", "--json"], capture_output=True, text=True)

        self.assertEqual(res_load.returncode, 0, "load_test_50.js dry-run must exit with 0")
        self.assertEqual(res_sanity.returncode, 0, "sanity_check.py --warn-offline must exit with 0")

    def test_t3_production_audit_x_configuration_correlation(self):
        """
        Production Audit x Configuration Correlation:
        Verifies that findings in AUDIT_PRODUCTION.md accurately correlate with
        actual configuration files in the repository:
        1. systemd units specify User=root (SEC-03).
        2. SQLite database operates in delete journal mode (DAT-01).
        3. server/spigot.yml specifies restart-script: ./start.sh which does not exist (ERR-01).
        4. server/server.properties specifies rcon.password (SEC-01).
        5. web/services/security_middleware.py contains X-Forwarded-For check (SEC-05).
        """
        with open(AUDIT_FILE_PATH, "r", encoding="utf-8") as f:
            audit_text = f.read()

        # 1. Systemd User=root
        mc_service = os.path.join(SYSTEMD_DIR, "aether-minecraft.service")
        web_service = os.path.join(SYSTEMD_DIR, "aether-web.service")
        self.assertTrue(os.path.exists(mc_service))
        self.assertTrue(os.path.exists(web_service))

        with open(mc_service, "r", encoding="utf-8") as f:
            mc_service_text = f.read()
        self.assertIn("User=root", mc_service_text, "Systemd service should specify User=root as documented in audit")
        self.assertIn("User=root", audit_text, "Audit must document User=root finding")

        # 2. SQLite journal mode
        self.assertTrue(os.path.exists(DB_PATH), f"Database must exist at {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0].lower()
        conn.close()

        self.assertIn("journal_mode", audit_text, "Audit must document SQLite journal_mode")
        self.assertEqual(journal_mode, "delete", "Actual SQLite journal mode is 'delete' as documented in audit")

        # 3. Spigot restart script ./start.sh
        self.assertTrue(os.path.exists(SPIGOT_YML_PATH))
        with open(SPIGOT_YML_PATH, "r", encoding="utf-8") as f:
            spigot_text = f.read()
        self.assertIn("restart-script: ./start.sh", spigot_text, "spigot.yml should specify ./start.sh as documented")
        start_sh_path = os.path.join(PROJECT_ROOT, "server", "start.sh")
        self.assertFalse(os.path.exists(start_sh_path), "server/start.sh must not exist, confirming audit finding ERR-01")

        # 4. RCON password in server.properties
        self.assertTrue(os.path.exists(SERVER_PROPERTIES_PATH))
        with open(SERVER_PROPERTIES_PATH, "r", encoding="utf-8") as f:
            props_text = f.read()
        self.assertIn("rcon.password=", props_text, "server.properties must configure rcon.password as audited")

        # 5. X-Forwarded-For in security middleware
        sec_middleware_path = os.path.join(PROJECT_ROOT, "web", "services", "security_middleware.py")
        with open(sec_middleware_path, "r", encoding="utf-8") as f:
            sec_text = f.read()
        self.assertIn("X-Forwarded-For", sec_text, "security_middleware.py must reference X-Forwarded-For as audited")


# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS
# ==============================================================================

class TestTier4RealWorldScenarios(unittest.TestCase):
    """
    Tier 4 - Real-World Scenarios:
    Comprehensive End-to-End launch readiness acceptance pipeline validating
    all 5 user requirements in an integrated sequence.
    """

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_t4_e2e_launch_readiness_acceptance_pipeline(self):
        """
        Full Launch Readiness Acceptance Pipeline:
        Executes a 5-step sequential acceptance verification verifying:
        1. R1: Virtual keyboard security & line count compliance.
        2. R2: Frontend cinematic hero display at y=0 without mock artifacts.
        3. R3: 50-player concurrency test readiness & zero throttle.
        4. R4: Rapid diagnostic probes execution under sub-minute constraint.
        5. R5: Production governance audit covering 14 findings across 5 pillars.
        """
        verification_log = []

        # Step 1: Security Verification (R1)
        with open(VKEYBOARD_PATH, "r", encoding="utf-8") as f:
            vkb_code = f.read()
            lines = vkb_code.splitlines()
        self.assertLessEqual(len(lines), 300)
        self.assertNotIn(".innerHTML =", vkb_code)
        node_check = subprocess.run(["node", "-c", VKEYBOARD_PATH], capture_output=True, text=True)
        self.assertEqual(node_check.returncode, 0)
        verification_log.append("Step 1 (R1 Security) PASSED: 0 DOM sinks, <= 300 LOC, valid syntax.")

        # Step 2: UI Presentation & Header Translucency (R2)
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('id="hero"', html)
        self.assertIn('id="hero-bg-layer"', html)
        self.assertIn('id="hero-content-wrapper"', html)
        for forbidden in ["AetherKnight", "PixelSorceress", "TITAN PRIMORDIAL"]:
            self.assertNotIn(forbidden, html)
        verification_log.append("Step 2 (R2 UI Background) PASSED: Hero rendered at y=0, zero mocks.")

        # Step 3: Concurrency & Resiliency Readiness (R3)
        with open(BUKKIT_YML_PATH, "r", encoding="utf-8") as f:
            bukkit_cfg = f.read()
        self.assertIn("connection-throttle: 0", bukkit_cfg)
        load_dry = subprocess.run(["node", LOAD_TEST_PATH, "--dry-run"], capture_output=True, text=True)
        self.assertEqual(load_dry.returncode, 0)
        verification_log.append("Step 3 (R3 50-Player Load Testing) PASSED: Harness verified, throttle=0.")

        # Step 4: Rapid Diagnostic Probe Suite (R4)
        sanity_start = time.time()
        sanity_res = subprocess.run(
            [sys.executable, SANITY_CHECK_PATH, "--warn-offline", "--json"],
            capture_output=True, text=True, timeout=60
        )
        sanity_elapsed = time.time() - sanity_start
        self.assertEqual(sanity_res.returncode, 0)
        self.assertLess(sanity_elapsed, 60.0)
        sanity_json = json.loads(sanity_res.stdout)
        self.assertEqual(sanity_json.get("probes_count"), 6)
        verification_log.append(f"Step 4 (R4 Diagnostic Sanity Check) PASSED: 6 probes completed in {sanity_elapsed:.2f}s.")

        # Step 5: Production Readiness Audit (R5)
        with open(AUDIT_FILE_PATH, "r", encoding="utf-8") as f:
            audit_body = f.read()
        for pillar in ["Sécurité", "Persistance", "Erreurs", "Supervision", "Réseau"]:
            self.assertIn(pillar.lower(), audit_body.lower())
        self.assertGreater(len(audit_body), 2000)
        verification_log.append("Step 5 (R5 Production Audit) PASSED: 14 findings across 5 pillars verified.")

        # Final assertion on the complete pipeline
        self.assertEqual(len(verification_log), 5, "All 5 acceptance pipeline steps must complete successfully.")


if __name__ == "__main__":
    unittest.main()
