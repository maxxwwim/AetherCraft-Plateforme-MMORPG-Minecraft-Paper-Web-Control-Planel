import requests
from typing import Dict, Any, Optional

PAPER_API_V3 = "https://fill.papermc.io/v3"
USER_AGENT = "AetherCraft-Platform/1.0.0 (contact@aethercraft.net)"

def get_paper_build_info(version: str = "1.21.1") -> Dict[str, Any]:
    """
    Récupère le dernier build PaperMC pour la version spécifiée via la nouvelle API Fill v3 officielle.
    En cas d'échec réseau, renvoie le build vérifié 133.
    """
    try:
        url = f"{PAPER_API_V3}/projects/paper/versions/{version}"
        headers = {"User-Agent": USER_AGENT}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            builds = data.get("builds", [])
            if builds:
                latest_build = max(builds)
                build_url = f"{PAPER_API_V3}/projects/paper/versions/{version}/builds/{latest_build}"
                b_res = requests.get(build_url, headers=headers, timeout=5)
                if b_res.status_code == 200:
                    b_data = b_res.json()
                    dl_info = b_data.get("downloads", {}).get("server:default", {})
                    if dl_info:
                        dl_url = dl_info.get("url", "")
                        sha256 = dl_info.get("checksums", {}).get("sha256", "")
                        return {
                            "build": latest_build,
                            "download_url": dl_url,
                            "target_jar": "paper-server.jar",
                            "sha256": sha256
                        }
    except Exception as e:
        print(f"[WARN] PaperMC Fill v3 API non joignable ({e}), utilisation du fallback")

    # Fallback vérifié officiel PaperMC 1.21.1 Build 133
    return {
        "build": 133,
        "download_url": "https://fill-data.papermc.io/v1/objects/39bd8c00b9e18de91dcabd3cc3dcfa5328685a53b7187a2f63280c22e2d287b9/paper-1.21.1-133.jar",
        "target_jar": "paper-server.jar",
        "sha256": "39bd8c00b9e18de91dcabd3cc3dcfa5328685a53b7187a2f63280c22e2d287b9"
    }

def get_purpur_build_info(version: str = "1.21.1") -> Dict[str, Any]:
    """Récupère les informations de téléchargement de PurpurMC."""
    return {
        "build": 2300,
        "download_url": f"https://api.purpurmc.org/v2/purpur/{version}/latest/download",
        "target_jar": "purpur-server.jar",
        "sha256": ""
    }

def get_plugin_presets(plugin_keys: list[str]) -> list[Dict[str, str]]:
    """Catalogue de plugins pré-vérifiés et optimisés pour serveur Aether."""
    CATALOG = {
        "chunky": {
            "name": "Chunky-1.4.28.jar",
            "target_dir": "plugins",
            "download_url": "https://cdn.modrinth.com/data/fALzjamp/versions/R1Kxvd8Z/Chunky-1.4.28.jar",
            "sha256": ""
        },
        "luckperms": {
            "name": "LuckPerms-Bukkit-5.4.140.jar",
            "target_dir": "plugins",
            "download_url": "https://download.luckperms.net/1556/bukkit/loader/LuckPerms-Bukkit-5.4.140.jar",
            "sha256": ""
        },
        "spark": {
            "name": "spark-bukkit.jar",
            "target_dir": "plugins",
            "download_url": "https://sparkcdn.lucko.me/download/bukkit",
            "sha256": ""
        }
    }
    plugins = []
    for key in plugin_keys:
        k = key.lower().strip()
        if k in CATALOG:
            plugins.append(CATALOG[k])
    return plugins
