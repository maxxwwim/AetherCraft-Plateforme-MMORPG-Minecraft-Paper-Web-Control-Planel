import time
import json
import urllib.request
from typing import Dict, Optional

# Configuration Discord AetherCraft
# Note : Pour lier votre vrai serveur Discord et afficher les membres en direct :
# 1. Activez le "Widget du serveur" dans les paramètres de votre serveur Discord
# 2. Renseignez ici l'ID de votre serveur Discord dans DISCORD_GUILD_ID
DISCORD_INVITE_URL = "https://discord.gg/aethercraft"
DISCORD_GUILD_ID = ""  # Ex: "1098765432109876543"

_DISCORD_CACHE: Optional[Dict] = None
_DISCORD_CACHE_TIME: float = 0.0
DISCORD_CACHE_TTL = 60.0  # 60 secondes pour respecter les rate limits de l'API Discord

def get_discord_status() -> Dict:
    """
    Récupère en direct les statistiques du serveur Discord via l'API officielle Widget.
    Si le Guild ID est configuré, interroge https://discord.com/api/guilds/{id}/widget.json
    Sinon, retourne les métriques officielles configurées prêtes à l'emploi.
    """
    global _DISCORD_CACHE, _DISCORD_CACHE_TIME

    now = time.time()
    if _DISCORD_CACHE is not None and (now - _DISCORD_CACHE_TIME) < DISCORD_CACHE_TTL:
        return _DISCORD_CACHE

    invite_url = DISCORD_INVITE_URL
    guild_id = DISCORD_GUILD_ID.strip()

    if guild_id:
        try:
            req = urllib.request.Request(
                f"https://discord.com/api/guilds/{guild_id}/widget.json",
                headers={"User-Agent": "AetherCraft-Web/2.4 (compatible; DiscordBot/1.0)"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                
                presence_count = int(data.get("presence_count", 0))
                server_name = data.get("name", "AetherCraft Communauté")
                instant_invite = data.get("instant_invite") or invite_url
                members_sample = data.get("members", [])

                result = {
                    "is_live_api": True,
                    "is_configured": True,
                    "name": server_name,
                    "invite_url": instant_invite,
                    "presence_online": presence_count,
                    "members_sample_count": len(members_sample),
                    "channels_count": len(data.get("channels", []))
                }
                _DISCORD_CACHE = result
                _DISCORD_CACHE_TIME = now
                return result
        except Exception:
            pass

    # Configuration par défaut / En attente de l'ID du serveur
    result = {
        "is_live_api": False,
        "is_configured": bool(guild_id),
        "name": "AetherCraft Communauté",
        "invite_url": invite_url,
        "presence_online": 0, # Mettre 0 ou dynamique
        "members_sample_count": 0,
        "channels_count": 0
    }
    _DISCORD_CACHE = result
    _DISCORD_CACHE_TIME = now
    return result
