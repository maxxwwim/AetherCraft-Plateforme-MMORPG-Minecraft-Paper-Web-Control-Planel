# ⚙️ AetherCraft — Spécifications & Configurations Déclaratives

> **Couche :** Contracts & Declarative Configs  
> **Format :** JSON Strict (Schéma Manifest Aether v1.0)  

---

## 📂 Contenu du Répertoire

- `aether-manifest.json` : Contrat déclaratif complet d'une instance serveur Minecraft :
  - `core` : Moteur de jeu (`paper`, version `1.21.1`, URL de téléchargement officielle et empreinte de contrôle SHA-256).
  - `runtime` : Version Java requise (Java 21 LTS), allocations de tas mémoire (`heap_min`, `heap_max`) et drapeaux JVM G1GC Aikar.
  - `plugins_and_mods` : Liste des extensions obligatoires à télécharger et déployer dans `plugins/`.
  - `configuration_files` : Fichiers statiques générés automatiquement (`eula.txt`, `server.properties`).
