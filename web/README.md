# 🌐 AetherCraft — Portail Web & Control Plane

> **Couche :** Application / Web UI  
> **Framework :** Python 3.14 + Flask + HTMX + TailwindCSS  
> **Port d'écoute :** `5000` (`http://127.0.0.1:5000`)  

---

## 📂 Structure du Répertoire

- `app.py` : Contrôleur Flask principal gérant les routes publiques et API.
- `requirements.txt` : Dépendances Python nécessaires (`Flask`, `requests`).
- `services/` :
  - `database.py` : Adaptateur SQLite (`server/data/aethercraft.db`) gérant les tables `players`, `ranks`, `store_orders` et `rcon_queue`.
  - `rcon_service.py` : Client RCON Source natif pour l'exécution des commandes en jeu (`25575`) avec basculement automatique sur file d'attente persistante si hors-ligne.
  - `store_service.py` : Catalogue d'articles boutique (grades, clés, cosmétiques) et traitement du panier d'achat.
  - `player_service.py` : Classements compétitifs (richesse, temps de jeu) et profils joueurs connectés à l'API mc-heads.
  - `server_status_service.py` : Surveillance live de l'état réseau (socket ping 25565 et métriques TPS).
  - `manifest_generator.py` : Spécification des manifestes JSON de déploiement pour le runner Rust.
- `templates/` : Vues Jinja2 (vitrine `index.html`, boutique `shop.html`, classements `players.html`, dashboard `dashboard.html`).
- `static/` : Feuilles de style, effets de défilement et ressources médias.

---

## 🚀 Démarrage du Serveur Web

```bash
cd web
python -m flask --app app run --port 5000 --debug
```
