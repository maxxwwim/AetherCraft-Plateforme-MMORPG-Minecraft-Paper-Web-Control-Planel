"""
Security Middleware & Validation Layer for AetherCraft Web Service.
Provides:
- In-memory thread-safe sliding window rate limiting
- Rate limit decorators with configurable tiers and retry-after headers
- Dual-context authentication helpers
- Strict input sanitization and schema validators
"""
import re
import time
import math
import threading
from functools import wraps
from collections import defaultdict
from typing import Tuple, Dict, Any, Optional, Set
from flask import request, jsonify, current_app


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Maintains per-client timestamp lists and prunes expired entries on each check.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._requests[key]
            valid = [ts for ts in timestamps if ts > cutoff]
            if len(valid) >= max_requests:
                earliest = valid[0]
                retry_after = int(math.ceil(earliest + window_seconds - now))
                self._requests[key] = valid
                return False, max(1, retry_after)
            valid.append(now)
            self._requests[key] = valid
            return True, 0

    def reset(self):
        """Resets all recorded rate limit windows (useful for test isolation)."""
        with self._lock:
            self._requests.clear()


# Global singleton limiter
rate_limiter = SlidingWindowRateLimiter()


def rate_limit(max_requests: int, window_seconds: int = 60, tier: str = "default"):
    """
    Decorator enforcing rate limits per client IP for a specific tier.
    When limit is exceeded, returns HTTP 429 Too Many Requests with JSON error.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Allow tests to bypass rate limiting if explicitly disabled in config
            if current_app.config.get("RATELIMIT_ENABLED") is False:
                return f(*args, **kwargs)

            # Determine client IP address
            forwarded = request.headers.get("X-Forwarded-For", "")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            else:
                client_ip = request.remote_addr or "127.0.0.1"

            key = f"{client_ip}:{tier}"
            allowed, retry_after = rate_limiter.is_allowed(key, max_requests, window_seconds)
            if not allowed:
                return jsonify({
                    "error": "Rate limit exceeded",
                    "code": 429,
                    "message": "Trop de requêtes. Veuillez patienter avant de réessayer.",
                    "retry_after": retry_after
                }), 429

            return f(*args, **kwargs)
        return wrapper
    return decorator


def sanitize_text(val: Optional[str], max_len: int = 64) -> str:
    """Strips newlines, null bytes, formatting escapes, and control characters."""
    if not val:
        return ""
    clean = re.sub(r"[\r\n\x00\x1b;|$`]", "", str(val))
    return clean[:max_len].strip()


def validate_username(username: str) -> bool:
    """Minecraft Java username: 3-16 alphanumeric chars + underscores."""
    return bool(re.match(r"^[a-zA-Z0-9_]{3,16}$", username.strip()))


def validate_rcon_command_safety(command: str) -> Tuple[bool, str]:
    """
    Verifies that an RCON command contains no newlines, carriage returns, null bytes,
    or semicolons, and matches allowed command templates.
    """
    if any(c in command for c in ("\r", "\n", "\x00", ";")):
        return False, "Caractères interdits détectés dans la commande RCON (saut de ligne ou séparateur)."

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
        "list",
        "give ",
        "say ",
        "msg ",
        "tell ",
    )
    cmd_clean = command.strip()
    if cmd_clean == "list":
        return True, ""

    if not any(cmd_clean.startswith(prefix) for prefix in allowed_prefixes):
        return False, f"Modèle de commande RCON non autorisé."

    # If execute as, ensure username and subcommand are safe
    if cmd_clean.startswith("execute as "):
        parts = cmd_clean.split()
        if len(parts) >= 5 and parts[3] == "run":
            target_user = parts[2]
            if not validate_username(target_user):
                return False, "Nom de joueur invalide dans execute as."
            subcmd = " ".join(parts[4:])
            allowed_subcmds = {"spawn", "survie", "dungeon", "rtp", "banque", "pet", "cosmetics", "webdisplay close"}
            if subcmd not in allowed_subcmds:
                return False, f"Sous-commande non autorisée dans execute as: {subcmd}"
        else:
            return False, "Format de commande 'execute as <player> run <subcmd>' invalide."

    return True, ""
