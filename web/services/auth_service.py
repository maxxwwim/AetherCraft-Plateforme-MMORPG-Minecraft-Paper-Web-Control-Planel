import os
import hashlib
import secrets
import re
from functools import wraps
from typing import Optional, Dict, Any, Tuple
from flask import session, redirect, url_for, request, flash, jsonify
from services.database import (
    db_create_user,
    db_get_user_by_email,
    db_get_user_by_username,
    db_get_user_by_id,
    db_update_user_last_login,
    db_upsert_player
)
from services.rcon_service import execute_server_command

PBKDF2_ITERATIONS = 600_000

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hache un mot de passe avec PBKDF2-HMAC-SHA256 et salt cryptographique de 16 octets."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS
    )
    return key.hex(), salt

def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Vérification en temps constant contre les attaques temporelles."""
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS
    )
    return secrets.compare_digest(key.hex(), expected_hash)

def validate_minecraft_username(username: str) -> bool:
    """Format officiel Minecraft Java Edition : 3 à 16 caractères alphanumériques et underscores."""
    return bool(re.match(r"^[a-zA-Z0-9_]{3,16}$", username))

def sync_to_whitelist_json(username: str):
    """Ajoute le joueur au fichier server/whitelist.json immédiatement sur le disque."""
    try:
        import json, uuid as _uuid
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        candidates = [
            os.path.join(root_dir, "server", "whitelist.json"),
            os.path.join("server", "whitelist.json"),
            os.path.join("..", "server", "whitelist.json"),
        ]

        md5 = bytearray(hashlib.md5(f"OfflinePlayer:{username}".encode("utf-8")).digest())
        md5[6] &= 0x0f
        md5[6] |= 0x30
        md5[8] &= 0x3f
        md5[8] |= 0x80
        player_uuid = str(_uuid.UUID(bytes=bytes(md5)))

        for target in candidates:
            if os.path.exists(os.path.dirname(target)):
                entries = []
                if os.path.exists(target):
                    try:
                        with open(target, "r", encoding="utf-8") as f:
                            entries = json.load(f)
                    except Exception:
                        entries = []

                if not any(e.get("name", "").lower() == username.lower() for e in entries):
                    entries.append({"uuid": player_uuid, "name": username})
                    with open(target, "w", encoding="utf-8") as f:
                        json.dump(entries, f, indent=2)
                break
    except Exception as e:
        print(f"[!] Erreur sync_to_whitelist_json: {e}")

def register_user(email: str, password: str, minecraft_username: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Inscrit un nouvel utilisateur, crée son profil joueur,
    et l'inscrit automatiquement sur la whitelist du serveur Minecraft via RCON.
    """
    email = email.strip().lower()
    minecraft_username = minecraft_username.strip()

    if not email or "@" not in email:
        return False, "Adresse email invalide.", None

    if len(password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères.", None

    if not validate_minecraft_username(minecraft_username):
        return False, "Le pseudo Minecraft est invalide (3 à 16 caractères alphanumériques).", None

    if db_get_user_by_email(email):
        return False, "Un compte existe déjà avec cette adresse email.", None

    if db_get_user_by_username(minecraft_username):
        return False, "Ce pseudo Minecraft est déjà lié à un compte AetherCraft.", None

    # Hachage sécurisé
    pwd_hash, salt = hash_password(password)

    user = db_create_user(email, pwd_hash, salt, minecraft_username)
    if not user:
        return False, "Erreur lors de la création du compte en base de données.", None

    # Synchronisation de la table players (stats, rank, balance)
    initial_rank = "CREATEUR" if minecraft_username.strip().lower() == "hactheglitchis" else "JOUEUR"
    db_upsert_player(minecraft_username, rank=initial_rank)

    # Inscription directe dans whitelist.json sur disque
    sync_to_whitelist_json(minecraft_username)

    # Auto-Whitelist RCON immédiate ou mise en queue
    execute_server_command(f"whitelist add {minecraft_username}", target_player=minecraft_username)
    execute_server_command("whitelist reload")
    if minecraft_username.strip().lower() == "hactheglitchis":
        execute_server_command(f"op {minecraft_username}")
        execute_server_command(f"lp user {minecraft_username} parent set admin")
        execute_server_command(f"lp user {minecraft_username} permission set aether.admin true")
        execute_server_command(
            f"broadcast §6✦ §eBienvenue au Fondateur & Administrateur §b{minecraft_username} §e(10,000 Pièces & Privilèges Activés) !"
        )
    else:
        execute_server_command(
            f"broadcast §e✨ §fBienvenue sur AetherCraft à §b{minecraft_username} §f(Nouveau joueur Whitelisté) !"
        )

    return True, "Compte créé avec succès et pseudo ajouté à la whitelist !", user

def authenticate_user(identifier: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    """Authentifie un utilisateur via son email ou son pseudo Minecraft."""
    identifier = identifier.strip()
    if "@" in identifier:
        user = db_get_user_by_email(identifier)
    else:
        user = db_get_user_by_username(identifier)

    if not user:
        return False, "Identifiant ou mot de passe incorrect.", None

    if not verify_password(password, user["salt"], user["password_hash"]):
        return False, "Identifiant ou mot de passe incorrect.", None

    # Mise à jour date dernière connexion
    db_update_user_last_login(user["id"])
    return True, "Connexion réussie.", user

def get_current_user() -> Optional[Dict[str, Any]]:
    """Récupère l'utilisateur connecté en session avec données de skin NPC."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = db_get_user_by_id(user_id)
    if not user:
        return None

    # Enrichissement avec texture skin Minecraft 3D
    mc_user = user["minecraft_username"]
    return {
        **user,
        "avatar_url": f"https://mc-heads.net/avatar/{mc_user}/96",
        "body_url": f"https://mc-heads.net/body/{mc_user}/right",
        "head_url": f"https://mc-heads.net/head/{mc_user}"
    }

def login_required(f):
    """Décorateur pour restreindre les routes aux utilisateurs connectés."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({
                    "error": "Unauthorized",
                    "code": 401,
                    "message": "Authentification requise pour cette ressource API."
                }), 401
            flash("Vous devez être connecté pour accéder à cette page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Décorateur pour restreindre les routes aux administrateurs (Espace Créateur)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({
                    "error": "Unauthorized",
                    "code": 401,
                    "message": "Authentification requise pour cette ressource API."
                }), 401
            flash("Accès réservé aux administrateurs. Veuillez vous connecter.", "warning")
            return redirect(url_for("login", next=request.url))
        user = get_current_user()
        if not user or not user.get("is_admin"):
            if request.path.startswith("/api/"):
                return jsonify({
                    "error": "Forbidden",
                    "code": 403,
                    "message": "Privilèges administrateur requis."
                }), 403
            flash("Accès refusé : vous devez posséder les privilèges Administrateur / Créateur.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

def api_auth_required(f):
    """Décorateur dédié aux endpoints API JSON garantissant un retour HTTP 401 systématique."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id") and not session.get("game_auth"):
            return jsonify({
                "error": "Unauthorized",
                "code": 401,
                "message": "Authentification requise pour cette ressource API."
            }), 401
        return f(*args, **kwargs)
    return decorated

def admin_api_required(f):
    """Décorateur dédié aux endpoints API administrateur garantissant HTTP 401 ou 403 systématique."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({
                "error": "Unauthorized",
                "code": 401,
                "message": "Authentification requise pour cette ressource API."
            }), 401
        user = get_current_user()
        if not user or not user.get("is_admin"):
            return jsonify({
                "error": "Forbidden",
                "code": 403,
                "message": "Privilèges administrateur requis."
            }), 403
        return f(*args, **kwargs)
    return decorated
