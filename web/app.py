import os
import uuid
import re
import hmac
import hashlib
import time
import math
import datetime
from markupsafe import escape
from flask import Flask, render_template, request, jsonify, session, abort, redirect, url_for, flash, Response
from services.security_middleware import rate_limit, validate_username
from services.block_renderer import render_isometric_block_png
from services.manifest_generator import build_server_manifest
from services.store_service import (
    get_store_items,
    get_item_by_id,
    process_checkout,
    process_points_checkout,
    execute_item_delivery,
    ORDERS_HISTORY
)
from services.player_service import get_leaderboards, get_player_profile
from services.server_status_service import get_live_server_status
from services.discord_service import get_discord_status
from services.auth_service import (
    register_user,
    authenticate_user,
    get_current_user,
    login_required,
    admin_required,
    api_auth_required,
    admin_api_required
)
from services.rcon_service import execute_server_command
from services.database import (
    get_db_connection,
    db_get_user_by_username,
    db_get_top_player,
    db_get_leaderboards,
    db_get_recent_orders,
    db_get_player_by_username,
    db_update_player_balance,
    db_add_player_balance,
    db_get_ores_market,
    db_get_community_goal,
    db_contribute_to_community_goal,
    db_get_market_listings,
    db_get_mystic_pets,
    db_get_reward_status,
    db_claim_30min_reward,
    db_get_user_unlocked_items,
    db_has_user_unlocked_item,
    db_get_quests,
    db_get_user_quests,
    db_claim_quest,
    db_get_all_achievements,
    db_get_user_achievements,
    db_unlock_achievement,
    db_get_all_dungeons,
    db_can_enter_dungeon,
    db_enter_dungeon,
    db_get_user_dungeon_history,
    db_get_recent_quiz_winners,
    db_buy_market_listing,
    db_create_market_listing,
    db_get_user_keys,
    db_open_crate,
    db_get_recent_crate_openings
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.environ.get("SECRET_KEY", "aethercraft_secret_session_key_2026"))

# Cache en mémoire des manifests générés
MANIFEST_STORE = {}

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text).strip('_')
    return text or "server"

@app.context_processor
def inject_global_status():
    """Injecte le statut du serveur, l'utilisateur (avec solde de Pièces ⛃ synchronisé) et l'objectif communautaire."""
    user = get_current_user()
    reward_status = None
    if user:
        reward_status = db_get_reward_status(user["id"])
        player = db_get_player_by_username(user["minecraft_username"])
        if player:
            user["balance"] = player["balance"]
            user["shop_points"] = int(player["balance"])
        else:
            user["balance"] = float(user.get("shop_points", 1000))
    return {
        "server_status": get_live_server_status(),
        "discord_status": get_discord_status(),
        "current_user": user,
        "community_goal": db_get_community_goal(),
        "reward_status": reward_status
    }

# ========================================================
# 1. AUTHENTIFICATION & COMPTE UTILISATEUR
# ========================================================

@app.route("/inscription", methods=["GET", "POST"])
@rate_limit(max_requests=5, window_seconds=60, tier="auth")
def register():
    if get_current_user():
        return redirect(url_for("my_account"))
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        minecraft_username = request.form.get("minecraft_username", "")
        ok, msg, user = register_user(email, password, minecraft_username)
        if ok:
            session["user_id"] = user["id"]
            flash(msg, "success")
            return redirect(url_for("my_account"))
        else:
            flash(msg, "danger")
    return render_template("register.html")

@app.route("/connexion", methods=["GET", "POST"])
@rate_limit(max_requests=5, window_seconds=60, tier="auth")
def login():
    if get_current_user():
        return redirect(url_for("my_account"))
    if request.method == "POST":
        identifier = request.form.get("identifier", "")
        password = request.form.get("password", "")
        ok, msg, user = authenticate_user(identifier, password)
        if ok:
            session["user_id"] = user["id"]
            next_url = request.args.get("next") or url_for("my_account")
            return redirect(next_url)
        else:
            flash(msg, "danger")
    return render_template("login.html")

@app.route("/deconnexion")
def logout():
    session.pop("user_id", None)
    flash("Vous avez été déconnecté avec succès.", "info")
    return redirect(url_for("index"))

@app.route("/mon-compte")
@login_required
def my_account():
    user = get_current_user()
    player_stats = db_get_player_by_username(user["minecraft_username"])
    all_orders = db_get_recent_orders(50)
    user_orders = [o for o in all_orders if o["username"].lower() == user["minecraft_username"].lower()]
    unlocked_items = db_get_user_unlocked_items(user["id"])
    quests = db_get_user_quests(user["id"])
    achievements = db_get_user_achievements(user["id"])
    dungeons = db_get_all_dungeons()
    for d in dungeons:
        can_enter, reason = db_can_enter_dungeon(user["id"], d["id"])
        d["can_enter"] = can_enter
        d["access_reason"] = reason
    dungeon_history = db_get_user_dungeon_history(user["id"])
    return render_template(
        "account.html",
        player_stats=player_stats,
        orders=user_orders,
        unlocked_items=unlocked_items,
        quests=quests,
        achievements=achievements,
        dungeons=dungeons,
        dungeon_history=dungeon_history
    )

# ========================================================
# 2. VITRINE & ACCUEIL JOUEURS
# ========================================================

@app.route("/")
def index():
    """Page d'accueil vitrine du serveur."""
    top_player = db_get_top_player()
    return render_template("index.html", top_player=top_player)

# ========================================================
# 3. MARCHÉ, BOURSE DES MINERAIS & ANIMAUX CÉLESTES
# ========================================================

@app.route("/marche")
def market():
    """Bourse des minerais et hôtel des ventes joueur à joueur."""
    ores = db_get_ores_market()
    listings = db_get_market_listings()
    player_stats = None
    user = get_current_user()
    if user:
        player_stats = db_get_player_by_username(user["minecraft_username"])
    return render_template("market.html", ores=ores, listings=listings, player_stats=player_stats)

@app.route("/animaux")
def companions():
    """Sanctuaire des animaux célestes et familiers coopératifs."""
    user = get_current_user()
    pets = db_get_mystic_pets()
    unlocked_pet_ids = [u["item_id"] for u in db_get_user_unlocked_items(user["id"])] if user else []
    return render_template("companions.html", pets=pets, unlocked_pet_ids=unlocked_pet_ids)

@app.route("/api/minecraft/block-icon/<path:material>.png")
@rate_limit(max_requests=60, window_seconds=60, tier="read")
def api_minecraft_block_icon(material: str):
    """Génère et sert le vrai bloc 3D isométrique du jeu Minecraft 1.21.1."""
    clean_mat = os.path.basename(material).replace(".png", "")
    clean_mat = re.sub(r"[^a-zA-Z0-9_]", "", clean_mat).lower()
    if not clean_mat:
        clean_mat = "diamond_block"
    png_bytes = render_isometric_block_png(clean_mat)
    return Response(png_bytes, mimetype="image/png", headers={"Cache-Control": "public, max-age=3600"})

@app.route("/api/community/contribute", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def contribute_community():
    """Permet aux joueurs de contribuer des minerais à la jauge mondiale avec calcul % donation et paliers anti-cheat."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized", "code": 401, "message": "Authentification requise."}), 401
    mc_user = user["minecraft_username"]
    try:
        raw_amount = request.form.get("amount", "10")
        raw_price = request.form.get("ore_price", "10.0")
        amount = int(raw_amount)
        ore_price = float(raw_price)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Paramètres numériques invalides."}), 400

    if amount <= 0 or amount > 100000:
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Montant invalide (doit être compris entre 1 et 100000)."}), 400
    if ore_price <= 0.0 or math.isnan(ore_price) or math.isinf(ore_price) or ore_price > 1000000.0:
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Prix de minerai invalide."}), 400

    updated_goal = db_contribute_to_community_goal("s4_celestial_tree", amount, username=mc_user, ore_price=ore_price)
    return jsonify({"status": "ok", "goal": updated_goal})

@app.route("/api/market/buy", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def api_market_buy():
    """Achat direct d'un objet de l'Hôtel des Ventes avec synchronisation RCON."""
    user = get_current_user()
    listing_id = request.form.get("listing_id", "").strip()
    if not listing_id or not re.match(r"^[a-zA-Z0-9_\-]{1,64}$", listing_id):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "ID d'annonce manquant ou invalide."}), 400

    ok, msg, listing = db_buy_market_listing(user["id"], listing_id)
    if ok:
        mc_buyer = user["minecraft_username"]
        seller = listing.get("seller_username", "Inconnu")
        item_name = listing.get("item_name", "Objet")
        price = listing.get("price_coins", 0)

        safe_item_name = re.sub(r"[\r\n\x00;]", "", item_name)[:48]
        # Retransmission RCON en direct sur le serveur
        execute_server_command(
            f"broadcast §8[§6★ ENCAN D'ÉTHER ★§8] §e{mc_buyer} §fa acheté §b{safe_item_name} §fà §a{seller} §fpour §6{int(price)} ⛁ Coins §f(via le Site Web) !"
        )
        execute_server_command(
            f"title {mc_buyer} title {{\"text\":\"Achat Encan Réussi !\",\"color\":\"gold\",\"bold\":true}}"
        )
        return jsonify({"status": "ok", "message": msg, "listing": listing})
    else:
        return jsonify({"status": "error", "message": msg}), 400

@app.route("/api/market/sell", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def api_market_sell():
    """Mise en vente d'un objet sur l'Hôtel des Ventes depuis le site web."""
    user = get_current_user()
    item_name = request.form.get("item_name", "").strip()
    material_id = request.form.get("material_id", "").strip()
    try:
        quantity = int(request.form.get("quantity", 1))
        price = float(request.form.get("price", 100.0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Quantité ou prix invalide."}), 400

    if not item_name or len(item_name) < 2 or len(item_name) > 64:
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Nom d'objet invalide (2 à 64 caractères requis)."}), 400
    if any(c in item_name for c in ("\r", "\n", "\x00", ";", "|", "$", "`", "<", ">")):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Nom d'objet contient des caractères interdits."}), 400
    if quantity < 1 or quantity > 64:
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "La quantité doit être comprise entre 1 et 64."}), 400
    if price <= 0.0 or price > 10_000_000.0 or math.isnan(price) or math.isinf(price):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Prix invalide."}), 400
    if material_id and not re.match(r"^[a-zA-Z0-9_]{2,32}$", material_id):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Identifiant de matériau invalide."}), 400

    ok, msg, list_id = db_create_market_listing(user["id"], item_name, quantity, price, material_id=material_id)
    if ok:
        mc_user = user["minecraft_username"]
        safe_item_name = re.sub(r"[\r\n\x00;]", "", item_name)[:48]
        execute_server_command(
            f"broadcast §8[§6★ ENCAN D'ÉTHER ★§8] §e{mc_user} §fa mis en vente §b{safe_item_name} (x{quantity}) §fpour §6{int(price)} ⛁ Coins §f! (via le Site Web)"
        )
        return jsonify({"status": "ok", "message": msg, "listing_id": list_id})
    else:
        return jsonify({"status": "error", "message": msg}), 400

# ========================================================
# 4. BOUTIQUE EN LIGNE (ACCESSIBLE SI CONNECTÉ)
# ========================================================

@app.route("/boutique")
@login_required
def shop():
    user = get_current_user()
    cat = request.args.get("cat", "all")
    items = get_store_items(cat)
    cart = session.get("cart", [])
    cart_total = sum(i["price"] for i in cart)
    unlocked_item_ids = [u["item_id"] for u in db_get_user_unlocked_items(user["id"])] if user else []
    return render_template("shop.html", items=items, current_cat=cat, cart=cart, cart_total=cart_total, unlocked_item_ids=unlocked_item_ids)

@app.route("/api/store/cart/add", methods=["POST"])
def add_to_cart():
    item_id = request.form.get("item_id")
    item = get_item_by_id(item_id)
    cart = session.get("cart", [])
    if item:
        cart.append(item)
        session["cart"] = cart
    cart_total = sum(i["price"] for i in cart)
    return render_template("partials/cart.html", cart=cart, cart_total=cart_total)

@app.route("/api/store/cart/remove", methods=["POST"])
def remove_from_cart():
    item_id = request.form.get("item_id")
    cart = session.get("cart", [])
    for idx, item in enumerate(cart):
        if item["id"] == item_id:
            cart.pop(idx)
            break
    session["cart"] = cart
    cart_total = sum(i["price"] for i in cart)
    return render_template("partials/cart.html", cart=cart, cart_total=cart_total)

@app.route("/api/store/cart/clear", methods=["POST"])
def clear_cart():
    session["cart"] = []
    return render_template("partials/cart.html", cart=[], cart_total=0.0)

@app.route("/api/store/checkout", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def checkout():
    user = get_current_user()
    username = user["minecraft_username"] if user else request.form.get("username", "Steve").strip()
    cart = session.get("cart", [])
    if not cart:
        return render_template("partials/cart.html", cart=[], cart_total=0.0)
    
    order = process_checkout(username, cart)
    session["cart"] = []  # Vide le panier après validation
    return render_template("partials/cart.html", cart=[], cart_total=0.0, order_success=order)

@app.route("/api/store/reward-status")
@login_required
def store_reward_status():
    """Retourne l'état du compte à rebours 30 minutes et le solde de points."""
    user = get_current_user()
    status = db_get_reward_status(user["id"])
    return jsonify({"status": "ok", **status})

@app.route("/api/store/claim-reward", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def store_claim_reward():
    """Permet au joueur de réclamer son coffre de fidélité toutes les 30 minutes en Pièces (⛃)."""
    user = get_current_user()
    ok, msg, pts_gain, new_balance, rem = db_claim_30min_reward(user["id"])
    if ok:
        mc_user = user["minecraft_username"]
        # Retransmission RCON en direct sur le serveur Minecraft
        execute_server_command(
            f"broadcast §e🎁 §b{mc_user} §fa récupéré son coffre de fidélité 30min §6(+{pts_gain} ⛃ Pièces) §f!"
        )
        execute_server_command(
            f"title {mc_user} title {{\"text\":\"+{pts_gain} ⛃ Pièces !\",\"color\":\"gold\",\"bold\":true}}"
        )
        execute_server_command(f"playsound minecraft:entity.player.levelup master {mc_user}")
        return jsonify({
            "status": "ok",
            "message": msg,
            "points_gained": pts_gain,
            "new_balance": new_balance,
            "seconds_remaining": rem,
            "can_claim": False
        })
    else:
        return jsonify({
            "status": "error",
            "message": msg,
            "points_gained": 0,
            "new_balance": new_balance,
            "seconds_remaining": rem,
            "can_claim": False
        }), 400

@app.route("/api/quiz/winners")
@rate_limit(max_requests=60, window_seconds=60, tier="read")
def api_quiz_winners():
    """Retourne la liste des récents gagnants du Trivia Quiz in-game avec leurs gains."""
    winners = db_get_recent_quiz_winners(limit=10)
    return jsonify({
        "status": "ok",
        "winners": winners
    })

@app.route("/api/store/buy-points", methods=["POST"])
@app.route("/api/store/buy-coins", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def store_buy_with_points():
    """Achat direct en 1-clic avec les Pièces (⛃) accumulées."""
    user = get_current_user()
    item_id = request.form.get("item_id", "").strip()
    if not item_id or not re.match(r"^[a-zA-Z0-9_]{2,64}$", item_id):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Identifiant d'article manquant ou non conforme."}), 400

    ok, msg, order = process_points_checkout(user["id"], item_id)
    if ok:
        return jsonify({
            "status": "ok",
            "message": msg,
            "order": order,
            "new_balance": order["new_balance"]
        })
    else:
        return jsonify({
            "status": "error",
            "message": msg
        }), 400

@app.route("/api/auras/toggle", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def toggle_aura():
    """Active ou désactive une aura particulaire avec contrôle strict de déblocage en base."""
    user = get_current_user()
    aura_type = request.form.get("aura_type", "").strip().lower()
    if not aura_type or not re.match(r"^[a-zA-Z0-9_]{2,32}$", aura_type):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Type d'aura requis et conforme."}), 400

    username = user["minecraft_username"]

    # Désactivation
    if aura_type in ["clear", "none", "off"]:
        execute_server_command(f"aura clear {username}", target_player=username)
        return jsonify({"status": "ok", "message": "Aura particulaire désactivée avec succès."})

    # Contrôle strict : Seules les auras débloquées peuvent être activées
    aura_item_id = f"aura_{aura_type}" if not aura_type.startswith("aura_") else aura_type
    has_unlocked = db_has_user_unlocked_item(user["id"], aura_item_id)

    # Autorisation par grade du joueur
    player = db_get_player_by_username(username)
    if player and player.get("rank", "").lower() == aura_type.replace("aura_", ""):
        has_unlocked = True

    if not has_unlocked:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "code": 403,
            "message": f"🔒 Accès refusé : l'Aura {aura_type.upper()} n'est pas débloquée sur votre compte. Obtenez-la dans la boutique !"
        }), 403

    # Activation RCON en jeu
    short_aura = aura_type.replace("aura_", "")
    ok, resp = execute_server_command(f"aura {short_aura} {username}", target_player=username)
    execute_server_command(f"title {username} actionbar {{\"text\":\"✦ Aura {short_aura.upper()} Activée !\",\"color\":\"gold\"}}", target_player=username)

    return jsonify({
        "status": "ok",
        "message": f"✨ Aura {short_aura.upper()} activée en jeu sur votre personnage !",
        "aura": short_aura
    })

@app.route("/api/pets/summon", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def summon_pet():
    """Invoque un familier céleste débloqué sur le personnage du joueur connecté."""
    user = get_current_user()
    pet_type = request.form.get("pet_type", "").strip().lower()
    if not pet_type or not re.match(r"^[a-zA-Z0-9_]{2,32}$", pet_type):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Type de familier requis et conforme."}), 400

    username = user["minecraft_username"]

    if pet_type in ["clear", "none", "off"]:
        execute_server_command(f"pet clear {username}", target_player=username)
        return jsonify({"status": "ok", "message": "Familier céleste rengainé."})

    pet_item_id = f"pet_{pet_type}" if not pet_type.startswith("pet_") else pet_type
    if not db_has_user_unlocked_item(user["id"], pet_item_id):
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "code": 403,
            "message": f"🔒 Familier {pet_type.upper()} non débloqué. Rendez-vous dans la boutique pour l'adopter !"
        }), 403

    short_pet = pet_type.replace("pet_", "")
    execute_server_command(f"pet {short_pet} {username}", target_player=username)
    execute_server_command(f"title {username} actionbar {{\"text\":\"🐾 {short_pet.upper()} Invoqué !\",\"color\":\"gold\"}}", target_player=username)

    return jsonify({
        "status": "ok",
        "message": f"🐾 Familier {short_pet.upper()} invoqué avec succès à vos côtés en jeu !",
        "pet": short_pet
    })

# ========================================================
# 3. JOUEURS & CLASSEMENTS
# ========================================================

@app.route("/joueurs")
def players():
    leaderboards = db_get_leaderboards(5)
    user = get_current_user()
    default_player = None
    if user and user.get("minecraft_username"):
        default_player = get_player_profile(user["minecraft_username"])
    elif leaderboards.get("top_rich") and len(leaderboards["top_rich"]) > 0:
        default_player = get_player_profile(leaderboards["top_rich"][0]["username"])
    return render_template("players.html", leaderboards=leaderboards, player=default_player)

@app.route("/api/players/search", methods=["POST"])
@rate_limit(max_requests=60, window_seconds=60, tier="read")
def search_player():
    username = request.form.get("username", "").strip()
    if not username:
        username = "Steve"
    player = get_player_profile(username)
    if not player:
        return """
        <div class="glass-panel border border-white/10 rounded-3xl p-6 shadow-2xl relative text-center py-12">
          <div class="text-4xl mb-3">🔍</div>
          <h3 class="text-lg font-gaming font-bold text-white">Joueur introuvable</h3>
          <p class="text-xs text-slate-400 mt-1">Aucun joueur enregistré sous ce pseudo dans l'archipel.</p>
        </div>
        """
    return render_template("partials/player_card.html", player=player)

# ========================================================
# 4. COCKPIT CRÉATEUR & ADMINISTRATION (RÉSERVÉ ADMINS)
# ========================================================

@app.route("/admin")
@admin_required
def admin_cockpit():
    return render_template("admin.html", orders=db_get_recent_orders(50))

@app.route("/api/v1/servers/generate", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@admin_required
def generate_server():
    name = request.form.get("name", "Serveur Minecraft").strip()
    core_type = request.form.get("core_type", "paper").strip().lower()
    mc_version = request.form.get("mc_version", "1.21.1").strip()
    try:
        ram_gb = int(request.form.get("ram_gb", 4))
        port = int(request.form.get("port", 25565))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Paramètres numériques RAM ou Port invalides."}), 400

    difficulty = request.form.get("difficulty", "normal").strip().lower()
    plugins = request.form.getlist("plugins")

    if not name or len(name) > 64:
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Nom de serveur invalide."}), 400
    if core_type not in ("paper", "purpur", "spigot", "fabric"):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Type de core serveur non supporté."}), 400
    if not re.match(r"^[0-9\.]+$", mc_version):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Version Minecraft non valide."}), 400
    if ram_gb < 1 or ram_gb > 128:
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "RAM allouée doit être comprise entre 1 et 128 Go."}), 400
    if port < 1024 or port > 65535:
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Port d'écoute doit être compris entre 1024 et 65535."}), 400

    server_id = f"srv_{slugify(name)}_{str(uuid.uuid4())[:6]}"

    # Construction du Manifest
    manifest = build_server_manifest(
        server_id=server_id,
        name=name,
        core_type=core_type,
        mc_version=mc_version,
        ram_gb=ram_gb,
        plugins=plugins,
        port=port,
        difficulty=difficulty
    )
    MANIFEST_STORE[server_id] = manifest

    manifest_url = f"http://127.0.0.1:5000/api/v1/servers/{server_id}/manifest"
    cli_cmd = f"cargo run -p aether-mc-runner -- install-and-run --manifest {manifest_url}"
    safe_name = escape(manifest['name'])

    html = f"""
    <div class="w-full text-left space-y-4 animate-fade-in bg-obsidian-950 p-5 rounded-2xl border border-amber-500/40 shadow-xl">
      <div class="flex items-center justify-between border-b border-white/10 pb-3">
        <div>
          <span class="text-[10px] uppercase tracking-wider text-amber-400 font-bold font-gaming">Manifest Prêt Pour Déploiement</span>
          <h3 class="text-base font-bold text-white font-gaming">{safe_name}</h3>
        </div>
        <span class="px-2.5 py-1 text-xs rounded-full bg-amber-950 text-amber-300 border border-amber-800 font-mono">
          {manifest['core']['type'].upper()} {manifest['core']['mc_version']} (Build {manifest['core']['build']})
        </span>
      </div>

      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="bg-black/50 p-2.5 rounded-xl border border-white/5">
          <span class="text-slate-400 block text-[10px] font-gaming">RAM & Garbage Collector</span>
          <span class="text-white font-semibold">{manifest['runtime']['heap_max']} (Aikar Flags G1GC)</span>
        </div>
        <div class="bg-black/50 p-2.5 rounded-xl border border-white/5">
          <span class="text-slate-400 block text-[10px] font-gaming">Plugins Injectés</span>
          <span class="text-white font-semibold">{len(manifest['plugins_and_mods'])} plugin(s)</span>
        </div>
      </div>

      <div class="space-y-1">
        <label class="text-[11px] font-semibold text-slate-300 font-gaming">URL du Manifest JSON :</label>
        <div class="flex items-center gap-2">
          <input type="text" readonly value="{manifest_url}" 
                 class="w-full text-xs bg-black/60 border border-white/10 rounded-xl p-2.5 font-mono text-amber-300">
          <a href="{manifest_url}" target="_blank" 
             class="px-3.5 py-2.5 bg-white/10 hover:bg-white/20 text-xs rounded-xl text-slate-200 border border-white/10 transition font-gaming font-bold">
            Consulter
          </a>
        </div>
      </div>

      <div class="space-y-1 pt-1">
        <label class="text-[11px] font-semibold text-slate-300 font-gaming">🚀 Commande d'Exécution Client Rust :</label>
        <div class="relative bg-black/70 p-3 rounded-xl border border-white/10 font-mono text-xs text-emerald-400 break-all select-all">
          {cli_cmd}
        </div>
      </div>
    </div>
    """
    return html

@app.route("/api/v1/servers/<server_id>/manifest", methods=["GET"])
def get_manifest(server_id):
    manifest = MANIFEST_STORE.get(server_id)
    if not manifest:
        manifest = build_server_manifest(
            server_id=server_id,
            name=f"Instance {server_id}",
            core_type="paper",
            mc_version="1.21.1",
            ram_gb=4
        )
        MANIFEST_STORE[server_id] = manifest
    return jsonify(manifest)

@app.route("/api/v1/server/ping", methods=["GET"])
def server_ping():
    return jsonify(get_live_server_status())

@app.route("/favicon.ico")
def favicon():
    return "", 204

@app.route("/api/quests/claim", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def api_claim_quest():
    user = get_current_user()
    data = request.get_json(silent=True) or request.form or {}
    quest_id = data.get("quest_id", "").strip() if isinstance(data, dict) else ""
    if not quest_id or not re.match(r"^[a-zA-Z0-9_]{2,64}$", quest_id):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "ID de quête manquant ou non conforme."}), 400
    res = db_claim_quest(user["id"], quest_id)
    return jsonify(res)

@app.route("/api/dungeons/enter", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def api_enter_dungeon():
    user = get_current_user()
    data = request.get_json(silent=True) or request.form or {}
    dungeon_id = data.get("dungeon_id", "").strip() if isinstance(data, dict) else ""
    if not dungeon_id or not re.match(r"^[a-zA-Z0-9_]{2,64}$", dungeon_id):
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "ID de donjon manquant ou non conforme."}), 400
    res = db_enter_dungeon(user["id"], dungeon_id)
    return jsonify(res)

@app.route("/api/achievements", methods=["GET"])
@rate_limit(max_requests=60, window_seconds=60, tier="read")
@login_required
def api_get_achievements():
    user = get_current_user()
    return jsonify(db_get_user_achievements(user["id"]))

# ========================================================
# CAISSES & PACKS DE CLÉS (RNG & DÉBALLAGE)
# ========================================================

@app.route("/caisses")
def crates_page():
    user = get_current_user()
    keys = {"celestial": 0, "omega": 0}
    if user:
        keys = db_get_user_keys(user["id"])
    recent_openings = db_get_recent_crate_openings(20)
    return render_template("crates.html", user_keys=keys, recent_openings=recent_openings)

@app.route("/api/crates/open", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
@login_required
def api_open_crate():
    user = get_current_user()
    data = request.get_json(silent=True) or request.form or {}
    crate_type = (data.get("crate_type", "celestial") if isinstance(data, dict) else "celestial").strip().lower()
    if crate_type not in ["celestial", "omega"]:
        return jsonify({"error": "Invalid payload schema", "code": 400, "message": "Type de caisse invalide."}), 400
    res = db_open_crate(user["id"], crate_type)
    return jsonify(res)

@app.route("/api/crates/recent", methods=["GET"])
def api_get_recent_crates():
    recent = db_get_recent_crate_openings(20)
    return jsonify({"success": True, "openings": recent})


# ========================================================
# WEBDISPLAY 3D IN-GAME (PANNEAU & ÉCRAN /SHOP & /MENU)
# ========================================================

def verify_game_auth_token(username: str, ts: str, token: str) -> bool:
    if not username or not ts or not token:
        return False
    try:
        ts_val = int(ts)
        now = int(time.time())
        if abs(now - ts_val) > 3600:
            return False
        auth_key = os.environ.get("AETHER_AUTH_KEY", "aethercraft_session_hmac_2026")
        expected = hmac.new(auth_key.encode("utf-8"), f"{username.lower()}:{ts_val}".encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, token)
    except Exception:
        return False


@app.route("/webdisplay")
def webdisplay_panel():
    username = request.args.get("player") or (get_current_user() or {}).get("minecraft_username") or "Explorateur"
    ts = request.args.get("ts") or ""
    token = request.args.get("token") or ""
    is_authenticated = verify_game_auth_token(username, ts, token) or bool(session.get("game_auth") == username.lower())
    if is_authenticated:
        session["game_auth"] = username.lower()
        session["minecraft_username"] = username

    mode = (request.args.get("mode") or "cockpit").lower()
    cat = (request.args.get("cat") or "all").lower()

    pf = db_get_player_by_username(username) or {
        "username": username,
        "rank": "Aventurier",
        "balance": 1000,
        "points": 10
    }
    player_ctx = {
        "username": pf.get("username", username),
        "rank": pf.get("rank", "Aventurier"),
        "coins": pf.get("balance", 1000),
        "points": pf.get("shop_points", pf.get("points", 10)),
        "guild": pf.get("guild", "Aventurier"),
        "is_authenticated": is_authenticated,
        "auth_token": token,
        "auth_ts": ts
    }

    shop_items = get_store_items(cat if cat != "all" else None)
    market_items = db_get_market_listings()[:12]
    ores = db_get_ores_market()
    goal = db_get_community_goal()
    quests = db_get_quests()
    achievements = db_get_all_achievements()[:6]
    dungeons = db_get_all_dungeons()[:4]
    leaderboards = db_get_leaderboards(5)

    return render_template(
        "webdisplay.html",
        player=player_ctx,
        active_mode=mode,
        active_cat=cat,
        shop_items=shop_items[:8],
        market_items=market_items[:8],
        ores=ores[:8],
        goal=goal,
        quests=quests[:6],
        achievements=achievements,
        dungeons=dungeons,
        leaderboards=leaderboards
    )


@app.route("/api/webdisplay/state", methods=["GET"])
@rate_limit(max_requests=60, window_seconds=60, tier="read")
def api_webdisplay_state():
    username = request.args.get("player", "Explorateur")
    mode = (request.args.get("mode") or "cockpit").lower()
    cat = (request.args.get("cat") or "all").lower()
    pf = db_get_player_by_username(username) or {"username": username, "rank": "Aventurier", "balance": 1000, "points": 10}
    return jsonify({
        "status": "ok",
        "url": f"https://aethercraft.local/webdisplay/{mode}?player={username}&phone=1",
        "player": pf,
        "mode": mode,
        "category": cat,
        "goal": db_get_community_goal()
    })


@app.route("/api/webdisplay/action", methods=["POST"])
@rate_limit(max_requests=30, window_seconds=60, tier="mutation")
def api_webdisplay_action():
    """Exécute une action 1-clic depuis le Smartphone WebDisplay (MapBrowser JCEF) uniquement pour le joueur authentifié."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    username = (data.get("player") or "").strip()
    action = (data.get("action") or "").strip().lower()
    target = (data.get("target") or "").strip()

    if not username or not re.match(r"^[a-zA-Z0-9_]{3,16}$", username):
        return jsonify({
            "error": "Invalid payload schema",
            "code": 400,
            "message": "Nom de joueur manquant ou non conforme (3 à 16 caractères alphanumériques)."
        }), 400

    # 1. Dual-context authentication check (session ou API token / HMAC)
    auth_user = None
    curr_user = get_current_user()
    if curr_user:
        auth_user = curr_user["minecraft_username"].lower()
    elif session.get("game_auth"):
        auth_user = str(session.get("game_auth")).lower()
    else:
        # Contrôle du jeton explicite dans la requête (headers ou corps)
        token = data.get("token") or request.headers.get("X-Aether-Token") or request.args.get("token") or ""
        ts = data.get("ts") or request.headers.get("X-Aether-Timestamp") or request.args.get("ts") or ""
        if verify_game_auth_token(username, str(ts), str(token)):
            auth_user = username.lower()
            session["game_auth"] = username.lower()
            session["minecraft_username"] = username

    if not auth_user:
        return jsonify({
            "error": "Unauthorized",
            "code": 401,
            "message": "Authentification requise : session ou jeton HMAC invalide."
        }), 401

    # 2. Protection contre l'usurpation d'identité (player spoofing)
    if auth_user != username.lower():
        return jsonify({
            "error": "Forbidden",
            "code": 403,
            "message": "Interdiction d'exécuter des actions pour un tiers."
        }), 403

    # 3. Validation de l'action et de la cible
    allowed_actions = {
        "tp_spawn", "tp_survie", "tp_dungeon", "tp_rtp",
        "buy_item", "claim_quest", "open_bank", "open_pet",
        "open_cosmetics", "close_display", "contribute_ore"
    }
    if action not in allowed_actions:
        return jsonify({
            "error": "Invalid payload schema",
            "code": 400,
            "message": f"Action '{action}' non reconnue."
        }), 400

    if target and not re.match(r"^[a-zA-Z0-9_\-\.]{1,64}$", target):
        return jsonify({
            "error": "Invalid payload schema",
            "code": 400,
            "message": "Cible d'action non conforme."
        }), 400

    if action in ("tp_spawn", "tp_survie", "tp_dungeon", "tp_rtp"):
        cmd_map = {
            "tp_spawn": f"execute as {username} run spawn",
            "tp_survie": f"execute as {username} run survie",
            "tp_dungeon": f"execute as {username} run dungeon",
            "tp_rtp": f"execute as {username} run rtp",
        }
        execute_server_command(cmd_map[action], target_player=username)
        return jsonify({"status": "ok", "message": f"Téléportation ({action.replace('tp_', '').upper()}) lancée !"})

    if action == "buy_item":
        it = get_item_by_id(target)
        if not it:
            return jsonify({"status": "error", "message": "Article introuvable dans le catalogue."}), 404
        cost = max(1, it.get("price_points", 10)) * 10.0
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE players SET balance = balance - ? WHERE LOWER(username) = LOWER(?) AND balance >= ?;",
                (cost, username, cost)
            )
            if cursor.rowcount == 0:
                pf = db_get_player_by_username(username) or {"balance": 0.0}
                current_bal = float(pf.get("balance", 0.0))
                return jsonify({"status": "error", "message": f"Solde insuffisant : requis {int(cost)} ⛃ (solde actuel : {int(current_bal)} ⛃)"}), 400
            conn.commit()
            cursor.execute("SELECT balance FROM players WHERE LOWER(username) = LOWER(?);", (username,))
            row = cursor.fetchone()
            new_bal = float(row["balance"]) if row else 0.0

        execute_item_delivery(username, target)
        return jsonify({
            "status": "ok",
            "message": f"Achat confirmé : {it['name']} (-{int(cost)} ⛃) !",
            "new_balance": int(new_bal)
        })

    if action == "claim_quest":
        # Vérification d'une quête spécifique via target
        if target and target not in ("daily", "claim_quest"):
            u = db_get_user_by_username(username)
            if not u and curr_user:
                u = curr_user
            if u:
                res = db_claim_quest(u["id"], target)
                if not res.get("success"):
                    err = res.get("error", "Progression insuffisante")
                    status_code = 429 if "déjà réclamée" in str(err) else 400
                    return jsonify({
                        "status": "error",
                        "error": err,
                        "code": status_code,
                        "message": err
                    }), status_code
                pf = db_get_player_by_username(username) or {"balance": 0.0}
                return jsonify({
                    "status": "ok",
                    "message": "Récompense de quête réclamée !",
                    "new_balance": int(pf.get("balance", 0.0))
                })

        # Limite quotidienne stricte en base SQLite pour neutraliser le minting infini
        today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS player_daily_quest_claims (
                    username TEXT PRIMARY KEY,
                    last_claimed_date TEXT NOT NULL,
                    claimed_at TEXT NOT NULL
                );
            """)
            conn.commit()
            c.execute("SELECT last_claimed_date FROM player_daily_quest_claims WHERE LOWER(username) = LOWER(?);", (username,))
            row = c.fetchone()
            if row and row["last_claimed_date"] == today_str:
                return jsonify({
                    "error": "Progression limit reached",
                    "code": 429,
                    "message": "Quête céleste quotidienne déjà réclamée aujourd'hui. Revenez demain !"
                }), 429

            c.execute("""
                INSERT INTO player_daily_quest_claims (username, last_claimed_date, claimed_at)
                VALUES (?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    last_claimed_date = excluded.last_claimed_date,
                    claimed_at = excluded.claimed_at
                WHERE player_daily_quest_claims.last_claimed_date != excluded.last_claimed_date;
            """, (username, today_str, now_ts))
            if c.rowcount == 0:
                return jsonify({
                    "error": "Progression limit reached",
                    "code": 429,
                    "message": "Quête céleste quotidienne déjà réclamée aujourd'hui. Revenez demain !"
                }), 429
            conn.commit()

        db_add_player_balance(username, 500.0)
        execute_server_command(f"title {username} actionbar {{\"text\":\"+500 ⛃ Récompense de Quête Céleste !\",\"color\":\"green\"}}", target_player=username)
        pf = db_get_player_by_username(username) or {"balance": 0.0}
        return jsonify({"status": "ok", "message": "Récompense réclamée (+500 ⛃) !", "new_balance": int(pf.get("balance", 0.0))})

    if action == "open_bank":
        execute_server_command(f"execute as {username} run banque", target_player=username)
        return jsonify({"status": "ok", "message": "Ouverture du coffre de banque..."})

    if action == "open_pet":
        execute_server_command(f"execute as {username} run pet", target_player=username)
        return jsonify({"status": "ok", "message": "Gestionnaire de compagnons ouvert !"})

    if action == "open_cosmetics":
        execute_server_command(f"execute as {username} run cosmetics", target_player=username)
        return jsonify({"status": "ok", "message": "Menu Cosmétiques & Auras ouvert !"})

    if action == "close_display":
        execute_server_command(f"execute as {username} run webdisplay close", target_player=username)
        return jsonify({"status": "ok", "message": "Écran WebDisplay refermé."})

    if action == "contribute_ore":
        updated = db_contribute_to_community_goal("s4_celestial_tree", 5, username=username, ore_price=12.0)
        return jsonify({"status": "ok", "message": "+5 Minerais versés à l'Arbre Céleste !", "goal": updated})

    return jsonify({"status": "ok", "message": f"Action {action} synchronisée ({target})"})


@app.route("/api/v1/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "aether-mc-control-plane", "modules": ["store", "players", "server_creator"]})

if __name__ == "__main__":
    import logging, time
    logging.basicConfig(level=logging.INFO)
    print("[*] Aether Community & Server Platform demarre avec Waitress sur http://0.0.0.0:5000")
    from waitress import serve
    while True:
        try:
            serve(app, host="0.0.0.0", port=5000, threads=8, channel_timeout=120)
        except Exception as e:
            print(f"[ERROR] Waitress exception: {e}, relance dans 1s...")
            time.sleep(1)
