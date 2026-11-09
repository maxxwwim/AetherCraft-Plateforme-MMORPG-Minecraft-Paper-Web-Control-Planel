# 🕹️ AetherCraft — Module Serveur Minecraft (PaperMC Engine)

> **Couche :** Infrastructure / Game Engine  
> **Version cible :** Minecraft 1.21.1 (PaperMC Build 133)  
> **Compatibilité Clients :** 1.8.x jusqu'à 1.21.x (via ViaVersion)  
> **Ports d'écoute :** `25565` (Jeu TCP), `25575` (RCON TCP)  

---

## 📂 Structure du Répertoire

- `server.jar` / `paper-1.21.1-133.jar` : Binaire haute performance PaperMC officiel vérifié par empreinte SHA-256 (`39bd8c00...`).
- `eula.txt` : Acceptation formelle du CLUF Mojang (`eula=true`).
- `server.properties` : Paramètres réseau, RCON, compression réseau et visibilité optimisés pour un TPS constant de 20.0.
- `run-aikar.bat` : Script de démarrage avec allocation de 4 Go de mémoire heap et drapeaux de garbage collector G1GC (Aikar Flags).
- `plugins/` :
  - `LuckPerms-Bukkit-5.5.71.jar` : Gestion fine des rangs, permissions et préfixes.
  - `Chunky-Bukkit-1.4.40.jar` : Prégénération asynchrone des chunks pour éliminer le lag d'exploration.
  - `ViaVersion-5.12.3.jar` : Rétro-compatibilité multi-versions pour maximiser l'accessibilité des joueurs.
- `data/` :
  - `aethercraft.db` : Base de données SQLite locale assurant la synchronisation des données joueurs et la file d'attente RCON.

---

## 🚀 Démarrage Manuel & Supervision

```cmd
:: Lancement direct avec Garbage Collection optimisé
run-aikar.bat
```

Ou via le superviseur Rust :
```cmd
cargo run -p aether-mc-runner -- run --instance ./server
```
