from typing import Dict, Any, List
from .mc_api import get_paper_build_info, get_purpur_build_info, get_plugin_presets

def generate_aikar_jvm_flags(heap_gb: int) -> List[str]:
    """
    Génère les flags JVM recommandés par Aikar (G1GC tuning) pour serveur Minecraft.
    """
    heap_str = f"{heap_gb}G"
    return [
        f"-Xms{heap_str}",
        f"-Xmx{heap_str}",
        "-XX:+UseG1GC",
        "-XX:+ParallelRefProcEnabled",
        "-XX:MaxGCPauseMillis=200",
        "-XX:+UnlockExperimentalVMOptions",
        "-XX:+DisableExplicitGC",
        "-XX:+AlwaysPreTouch",
        "-XX:G1NewSizePercent=30",
        "-XX:G1MaxNewSizePercent=40",
        "-XX:G1ReservePercent=20",
        "-XX:SurvivorRatio=32",
        "-XX:InitiatingHeapOccupancyPercent=15",
        "-XX:G1MixedGCLiveThresholdPercent=90",
        "-XX:G1RSetUpdatingPauseTimePercent=5",
        "-Dterminal.jline=false",
        "-Dterminal.ansi=true"
    ]

def build_server_manifest(
    server_id: str,
    name: str,
    core_type: str = "paper",
    mc_version: str = "1.21.1",
    ram_gb: int = 4,
    plugins: List[str] = None,
    port: int = 25565,
    motd: str = "§bAetherCraft §7— Serveur Optimisé",
    difficulty: str = "hard"
) -> Dict[str, Any]:
    """
    Génère le dictionnaire complet conforme à la spécification AETHER_MC_MANIFEST_SPEC (v1.0).
    """
    if plugins is None:
        plugins = ["chunky", "spark"]

    # Résolution du core
    if core_type.lower() == "purpur":
        core_info = get_purpur_build_info(mc_version)
    else:
        core_info = get_paper_build_info(mc_version)

    # Résolution des plugins
    plugin_artifacts = get_plugin_presets(plugins)

    # Configuration properties
    server_props = (
        f"server-port={port}\n"
        f"motd={motd}\n"
        f"difficulty={difficulty}\n"
        f"online-mode=true\n"
        f"pvp=true\n"
        f"view-distance=10\n"
        f"simulation-distance=8\n"
        f"max-players=20\n"
        f"enable-command-block=true\n"
    )

    manifest = {
        "$schema": "https://aether.local/schemas/mc-manifest-v1.json",
        "version": "1.0",
        "server_id": server_id,
        "name": name,
        "runtime": {
            "java_major_version": 21,
            "vendor": "adoptium",
            "heap_min": f"{ram_gb}G",
            "heap_max": f"{ram_gb}G",
            "jvm_flags": generate_aikar_jvm_flags(ram_gb)
        },
        "core": {
            "type": core_type,
            "mc_version": mc_version,
            "build": core_info["build"],
            "target_jar": core_info["target_jar"],
            "download_url": core_info["download_url"],
            "sha256": core_info.get("sha256", "")
        },
        "plugins_and_mods": plugin_artifacts,
        "configs": {
            "eula.txt": "eula=true\n",
            "server.properties": server_props
        }
    }

    return manifest
