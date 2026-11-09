from typing import Dict, List, Optional
import re
from services.database import (
    db_get_all_players,
    db_get_player_by_username,
    db_get_leaderboards,
    db_record_playtime_and_reward
)
from services.rcon_service import execute_server_command

def get_leaderboards(limit: int = 5) -> Dict[str, List[Dict]]:
    """Classements des meilleurs joueurs par richesse, temps de jeu et frags depuis SQLite."""
    return db_get_leaderboards(limit)

def get_player_profile(username: str) -> Optional[Dict]:
    """Retourne la fiche du joueur depuis SQLite ou None si introuvable."""
    p = db_get_player_by_username(username)
    if not p:
        return None

    # Couleurs de badge par rang
    badge_colors = {
        "TITAN": "amber",
        "AETHER": "sky",
        "VIP": "emerald",
        "CREATEUR": "rose",
        "JOUEUR": "slate"
    }

    return {
        **p,
        "rank_color": badge_colors.get(p.get("rank"), "slate"),
        "avatar_url": f"https://mc-heads.net/avatar/{p['username']}/96",
        "body_url": f"https://mc-heads.net/body/{p['username']}/right"
    }

def parse_online_players_from_rcon() -> List[str]:
    """Interroge la commande /list du serveur Minecraft et extrait les pseudos connectés."""
    ok, resp = execute_server_command("list")
    if not ok or not resp:
        return []

    # Ex: "There are 2 of a max of 20 players online: Notch, AetherKnight"
    if ":" in resp:
        names_part = resp.split(":", 1)[1].strip()
        if not names_part:
            return []
        players = [name.strip() for name in names_part.split(",") if name.strip()]
        return players
    return []

def sync_online_players_playtime(minutes_elapsed: int = 5) -> List[Dict]:
    """
    Scrutateur d'activité in-game : synchronise le temps de jeu effectif sur le serveur Minecraft.
    Tous les cycles de 30 minutes de jeu actif, crédite +5 points boutique et alerte le joueur en jeu !
    """
    online_players = parse_online_players_from_rcon()
    results = []
    for username in online_players:
        reward = db_record_playtime_and_reward(username, minutes_elapsed=minutes_elapsed)
        if reward and reward.get("points_granted", 0) > 0:
            pts = reward["points_granted"]
            # Alertes RCON sonores et visuelles in-game
            execute_server_command(
                f"title {username} title {{\"text\":\"§6⭐ +{pts} ⛃ PIÈCES !\",\"bold\":true}}"
            )
            execute_server_command(
                f"title {username} subtitle {{\"text\":\"§a30 minutes de jeu accomplies ! Utilisez vos pièces sur le site ou en jeu.\"}}"
            )
            execute_server_command(f"playsound minecraft:ui.toast.challenge_complete master {username}")
            results.append(reward)
    return results
