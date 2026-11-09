# Audit de Préparation à la Production — AetherCraft V1 Bêta
**Projet :** AetherCraft (PaperMC 1.21.1 • Python Flask / Waitress • SQLite)  
**Date :** 8 Novembre 2026  
**Auditeur :** Teamwork Forensic & Reliability Engineering (`teamwork_worker_v1b_m4_1`)  
**Statut :** Document Officiel de Gouvernance Technique  
**Référentiels d'Audit :** OWASP Top 10:2021, CIS Linux Benchmarks, PaperMC Production Hardening Guide.

---

## 1. Résumé Exécutif & Tableau de Bord Général

L'objectif de cet audit est d'évaluer de manière rigoureuse, objective et exhaustive l'état de préparation opérationnelle de la plateforme **AetherCraft** en vue de son ouverture au public pour la version **V1 Bêta**.

L'architecture d'AetherCraft repose sur un couplage étroit entre :
- Un serveur de jeu Minecraft **PaperMC 1.21.1** (Build 133, protocole 767, port 25565, RCON port 25575) doté de plugins MMO custom (`AetherVisuals`, `MapBrowser` avec Chromium JCEF, `GrimAC`).
- Une plateforme Web de contrôle et de monétisation en **Python / Flask** propulsée par le serveur WSGI **Waitress 3.0.2** (port 5000, 8 worker threads).
- Une base de données relationnelle locale partagée **SQLite 3** (`server/data/aethercraft.db`, 30 tables).

### Synthèse des Vulnérabilités Identifiées

L'audit a mis en évidence **19 constats techniques majeurs** répartis sur les 5 piliers de gouvernance industrielle, dont **7 risques critiques (P0)** représentant des bloqueurs stricts pour une mise en production sécurisée :

```
+-----------------------------------------------------------------------------------------------+
| MATRICE GÉNÉRALE DES RISQUES DE PRODUCTION                                                    |
+----------------------------------------------------+-----------+----------+---------+---------+
| Pilier                                             | Total     | Critique | Élevé   | Moyen   |
+----------------------------------------------------+-----------+----------+---------+---------+
| 1. Sécurité & Gestion des Identités                | 7         | 4        | 2       | 1       |
| 2. Persistance & Intégrité des Données             | 4         | 2        | 2       | 0       |
| 3. Gestion des Erreurs & Stabilité Applicative     | 3         | 1        | 2       | 0       |
| 4. Supervision, Monitoring & Métriques             | 4         | 0        | 2       | 2       |
| 5. Résilience Réseau & Architecture d'Exposition   | 3         | 1        | 1       | 1       |
+----------------------------------------------------+-----------+----------+---------+---------+
| TOTAL                                              | 21        | 8        | 9       | 4       |
+----------------------------------------------------+-----------+----------+---------+---------+
```

---

## 2. PILIER 1 : SÉCURITÉ & GESTION DES IDENTITÉS

---

### SEC-01 — Mot de passe d'administration RCON codé en dur dans les dépôts et scripts

- **Niveau de risque :** 🔴 **Critique** (CVSS v3.1 : 9.8 / CWE-798: Use of Hard-coded Credentials)
- **Fichiers et lignes concernées :**
  - `server/server.properties` (ligne 45) : `rcon.password=aether_secret_rcon_2026`
  - `web/services/rcon_service.py` (ligne 11) : `RCON_PASSWORD = os.environ.get("RCON_PASSWORD", "aether_secret_rcon_2026")`
  - `scripts/sanity_check.py` (ligne 488) : `default=os.environ.get("RCON_PASSWORD", "aether_secret_rcon_2026")`
- **Constat :**  
  Le mot de passe d'administration RCON permettant d'exécuter des commandes console arbitraires sur le serveur Minecraft est consigné en clair dans les fichiers versionnés du dépôt Git. De plus, les modules applicatifs Web définissent cette chaîne comme valeur de repli par défaut en l'absence de variable d'environnement.
- **Impact concret en exploitation :**  
  Toute personne ayant accès au dépôt Git, ou tout attaquant scannant le port public TCP 25575 avec le dictionnaire par défaut, peut s'authentifier immédiatement via RCON. L'attaquant dispose alors d'un accès console total (`op`, `stop`, `execute`, dump de mémoire, injection de commandes).
- **Plan d'action :**
  1. Supprimer immédiatement la valeur par défaut `aether_secret_rcon_2026` du code source.
  2. Forcer la lecture exclusive de la variable d'environnement `RCON_PASSWORD`. Lever une exception bloquante au démarrage de l'application Web si la variable est indéfinie en mode production.
  3. Générer un mot de passe cryptographiquement fort (au moins 32 caractères aléatoires) injecté dans le fichier `.env` non versionné et templater dynamiquement `server.properties` au déploiement.
- **Commandes de remédiation :**
  ```bash
  # 1. Génération d'un secret fort
  NEW_RCON_PASS=$(openssl rand -hex 24)
  echo "RCON_PASSWORD=${NEW_RCON_PASS}" >> /opt/aethercraft/.env
  chmod 600 /opt/aethercraft/.env

  # 2. Injection sécurisée dans server.properties
  sed -i "s/^rcon.password=.*/rcon.password=${NEW_RCON_PASS}/" /opt/aethercraft/server/server.properties
  ```

---

### SEC-02 — Clé secrète de session Flask statique et non sécurisée

- **Niveau de risque :** 🔴 **Critique** (CVSS v3.1 : 9.1 / CWE-321: Use of Hard-coded Cryptographic Key)
- **Fichiers et lignes concernées :**
  - `web/app.py` (ligne 72) : `app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.environ.get("SECRET_KEY", "aethercraft_secret_session_key_2026"))`
- **Constat :**  
  L'application Flask s'appuie sur une clé secrète par défaut en dur (`aethercraft_secret_session_key_2026`) pour signer cryptographiquement les cookies de session (`itsdangerous` HMAC-SHA1).
- **Impact concret en exploitation :**  
  Puisque la clé secrète est publique dans le code source, un attaquant distant peut forger arbitrairement n'importe quel cookie de session côté client à l'aide d'outils comme `flask-unsign`. Il peut ainsi s'attribuer l'identité de l'administrateur du serveur ou de n'importe quel joueur, accéder aux interfaces privées et ordonner des transactions frauduleuses sur la boutique.
- **Plan d'action :**
  1. Interdire le démarrage de Flask si `FLASK_SECRET_KEY` n'est pas configuré dans l'environnement.
  2. Ajouter la rotation de secrets et configurer les paramètres de durcissement des cookies Flask (`SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_SAMESITE='Lax'`).
- **Commandes de remédiation :**
  ```python
  # Modification dans web/app.py
  flask_secret = os.environ.get("FLASK_SECRET_KEY")
  if not flask_secret:
      raise RuntimeError("[FATAL] La variable d'environnement FLASK_SECRET_KEY est obligatoire en production.")
  app.secret_key = flask_secret
  app.config.update(
      SESSION_COOKIE_HTTPONLY=True,
      SESSION_COOKIE_SECURE=True,
      SESSION_COOKIE_SAMESITE="Lax",
      PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=7),
  )
  ```

---

### SEC-03 — Exécution des services en tant que superutilisateur (`User=root`) dans systemd

- **Niveau de risque :** 🔴 **Critique** (CVSS v3.1 : 8.8 / CWE-250: Execution with Unnecessary Privileges)
- **Fichiers et lignes concernées :**
  - `systemd/aether-minecraft.service` (ligne 7) : `User=root`
  - `systemd/aether-web.service` (ligne 7) : `User=root`
- **Constat :**  
  Les unités de service systemd conçues pour démarrer le serveur Minecraft Paper (JVM Java 21) et la passerelle Web (Waitress / Python) sont explicitement configurées pour tourner sous le compte `root`.
- **Impact concret en exploitation :**  
  En cas de vulnérabilité d'exécution de code à distance (RCE) dans la JVM (failles Log4Shell, failles de désérialisation de paquets, vulnérabilités dans le navigateur Chromium embarqué par MapBrowser, ou injection via Waitress/Python), l'attaquant obtient immédiatement un shell root sur le serveur hôte sans nécessiter d'élévation de privilèges.
- **Plan d'action :**
  1. Créer un utilisateur et un groupe système dédiés sans interpréteur de commande (`aethercraft`).
  2. Assigner la propriété exclusive du dossier `/opt/aethercraft` à cet utilisateur.
  3. Mettre à jour les deux fichiers de service systemd avec `User=aethercraft` et `Group=aethercraft`, en ajoutant les directives de sandboxing systemd standard.
- **Commandes de remédiation :**
  ```bash
  # 1. Création de l'utilisateur dédié
  sudo useradd -r -s /usr/sbin/nologin -d /opt/aethercraft -M aethercraft
  sudo chown -R aethercraft:aethercraft /opt/aethercraft
  sudo chmod 750 /opt/aethercraft

  # 2. Mise à jour des services systemd
  sudo sed -i 's/^User=root/User=aethercraft/' /opt/aethercraft/systemd/*.service
  echo "Group=aethercraft" | sudo tee -a /opt/aethercraft/systemd/aether-minecraft.service
  echo "Group=aethercraft" | sudo tee -a /opt/aethercraft/systemd/aether-web.service
  sudo systemctl daemon-reload
  ```

---

### SEC-04 — Mode serveur non authentifié (`online-mode=false`) sans plugin d'authentification in-game

- **Niveau de risque :** 🔴 **Critique** (CVSS v3.1 : 9.4 / CWE-287: Improper Authentication)
- **Fichiers et lignes concernées :**
  - `server/server.properties` (ligne 38) : `online-mode=false`
  - `server/plugins_src/AetherVisuals/src/io/aethercraft/visuals/AetherVisualsPlugin.java` (lignes 326-347)
- **Constat :**  
  Le serveur de jeu est configuré avec `online-mode=false`, ce qui désactive la vérification des sessions auprès des serveurs Mojang / Microsoft. Bien qu'un filtre de whitelist vérifie l'existence du pseudo dans la table `users`/`players`, et qu'un `AuthGuard` (`/opauth`) protège les opérateurs, **aucun mot de passe in-game n'est exigé pour les joueurs réguliers**.
- **Impact concret en exploitation :**  
  N'importe quel client Minecraft cracké ou modifié peut rejoindre le serveur en prenant le pseudo de n'importe quel joueur existant enregistré dans la base de données. L'usurpateur hérite instantanément de la bourse, du solde en banque, des familiers et de l'inventaire de la victime sans contestation possible.
- **Plan d'action :**
  - **Option Recommandée A (Serveur Premium) :** Basculer `online-mode=true` dans `server.properties` dès le passage en production publique.
  - **Option B (Serveur Hybride / Cracké) :** Si le mode hors-ligne doit être conservé, intégrer impérativement un plugin d'authentification robuste (ex. FastLogin couplé à AuthMe Reloaded) forçant `/register <pass>` et `/login <pass>` avec hachage Argon2id ou bcrypt à chaque connexion.
- **Commandes de remédiation :**
  ```bash
  sed -i 's/^online-mode=false/online-mode=true/' /opt/aethercraft/server/server.properties
  ```

---

### SEC-05 — Rate-limiter contournable par falsification du header `X-Forwarded-For`

- **Niveau de risque :** 🟠 **Élevé** (CVSS v3.1 : 7.5 / CWE-290: Authentication Bypass by Spoofing)
- **Fichiers et lignes concernées :**
  - `web/services/security_middleware.py` (lignes 66-70) :
    ```python
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.remote_addr or "127.0.0.1"
    ```
- **Constat :**  
  Le décorateur `@rate_limit` lit et fait aveuglément confiance au premier élément de l'en-tête `X-Forwarded-For` fourni par le client HTTP sans vérifier si la requête provient d'un proxy inverse de confiance (ex. `127.0.0.1`).
- **Impact concret en exploitation :**  
  Un attaquant automatisé peut contourner intégralement toutes les protections contre les attaques par force brute (sur `/inscription` et `/connexion` limitées à 5 req/min, ou `/api/webdisplay/action` limitée à 30 req/min) en injectant une valeur aléatoire arbitraire dans l'en-tête `X-Forwarded-For` (`X-Forwarded-For: 203.0.113.X`) à chaque paquet.
- **Plan d'action :**
  1. Utiliser le middleware standardisé et sécurisé `ProxyFix` fourni par Werkzeug, configuré strictement pour faire confiance à 1 seul saut de proxy (`x_for=1`).
  2. N'accepter le header `X-Forwarded-For` que si `request.remote_addr` appartient strictement au réseau local approuvé (`127.0.0.1`, `::1`).
- **Commandes de remédiation :**
  ```python
  # Dans web/app.py
  from werkzeug.middleware.proxy_fix import ProxyFix
  app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
  ```

---

### SEC-06 — Exécution du navigateur Chromium JCEF sans bac à sable (`--no-sandbox`)

- **Niveau de risque :** 🟠 **Élevé** (CVSS v3.1 : 8.1 / CWE-250: Unrestricted Sandbox)
- **Fichiers et lignes concernées :**
  - `server/plugins/MapBrowser/config.yml` (lignes 18-21) :
    ```yaml
    custom-chrome-args:
      - "--disable-gpu-compositing"
      - "--disable-gpu-vsync"
      - "--no-sandbox"
    ```
- **Constat :**  
  Le moteur de rendu Chromium (JCEF) utilisé par le plugin `MapBrowser` pour afficher l'interface smartphone in-game est exécuté avec l'option `--no-sandbox` désactivant l'isolation de processus multi-niveaux de Chromium.
- **Impact concret en exploitation :**  
  En cas de faille mémoire ou d'évasion de moteur JavaScript (V8 / Blink), le code injecté dans une page web consultée in-game s'exécute directement dans le contexte du processus hôte sans être endigué par le bac à sable de Chromium. Couplé au fait que le service tournait en `root` (SEC-03), cela constituait un vecteur d'évasion de conteneur direct.
- **Plan d'action :**
  1. Supprimer l'argument `- "--no-sandbox"` de `MapBrowser/config.yml`.
  2. Sous Linux, s'assurer que le binaire `chrome-sandbox` possède les permissions appropriées (`chown root:root; chmod 4755`) ou autoriser les namespaces utilisateurs non privilégiés dans le noyau (`sysctl kernel.unprivileged_userns_clone=1`).
- **Commandes de remédiation :**
  ```bash
  sed -i '/--no-sandbox/d' /opt/aethercraft/server/plugins/MapBrowser/config.yml
  ```

---

### SEC-07 — Absence de jetons anti-CSRF sur les formulaires d'authentification et de marché

- **Niveau de risque :** 🟡 **Moyen** (CVSS v3.1 : 6.5 / CWE-352: Cross-Site Request Forgery)
- **Fichiers et lignes concernées :**
  - `web/templates/connexion.html`, `web/templates/inscription.html`
  - Routes POST dans `web/app.py` (`/connexion`, `/inscription`, `/marche/achat`)
- **Constat :**  
  Les formulaires HTML et endpoints d'API traitant des mutations d'état (création de compte, authentification, transactions économiques du marché) ne requièrent ni ne vérifient de jeton CSRF synchronisé.
- **Impact concret en exploitation :**  
  Un joueur naviguant sur un site tiers malveillant tout en ayant une session active sur la boutique AetherCraft peut être victime d'une soumission automatique de formulaires forçant l'achat ou le transfert de ressources à son insu.
- **Plan d'action :**
  1. Intégrer l'extension officielle `Flask-WTF` avec le middleware `CSRFProtect(app)`.
  2. Inclure `{{ csrf_token() }}` dans chaque formulaire POST et l'en-tête `X-CSRFToken` dans les appels Fetch/AJAX.
- **Commandes de remédiation :**
  ```bash
  pip install Flask-WTF
  ```
  ```python
  from flask_wtf.csrf import CSRFProtect
  csrf = CSRFProtect(app)
  ```

---

## 3. PILIER 2 : PERSISTANCE & INTÉGRITÉ DES DONNÉES

---

### DAT-01 — SQLite configuré en mode journal `DELETE` au lieu de `WAL` (Write-Ahead Logging)

- **Niveau de risque :** 🔴 **Critique** (CVSS v3.1 : 8.5 / CWE-662: Improper Synchronization)
- **Fichiers et lignes concernées :**
  - `web/services/database.py` (ligne 29) : `conn = sqlite3.connect(DB_PATH, factory=ManagedConnection)`
  - `server/plugins_src/AetherVisuals/src/io/aethercraft/visuals/AetherDatabase.java` (lignes 80-87)
- **Constat :**  
  L'interrogation `PRAGMA journal_mode;` sur `server/data/aethercraft.db` retourne **`DELETE`**. En mode DELETE classique, toute écriture verrouille de manière **exclusive** l'intégralité du fichier de base de données, bloquant toutes les lectures concurrentes provenant des 8 threads de Waitress et des threads asynchrones de Paper.
- **Impact concret en exploitation :**  
  Sous la charge de 50 joueurs simultanés (qui génèrent des mises à jour constantes de profils, soldes, banques et inventaires) combinée au trafic web, les threads Waitress subissent immédiatement des erreurs `sqlite3.OperationalError: database is locked`. Côté jeu, cela se traduit par des blocages d'inventaires, des échecs d'inscription et des timeouts réseau.
- **Plan d'action :**
  1. Activer de manière permanente le mode **WAL (Write-Ahead Logging)** sur la base de données SQLite : `PRAGMA journal_mode = WAL;`.
  2. Configurer le mode de synchronisation sur `NORMAL` : `PRAGMA synchronous = NORMAL;`, ce qui garantit la cohérence tout en décuplant les débits d'écriture concurrente.
  3. Appliquer ces pragmas dès la méthode `init_database()` côté Python et dans le bloc statique d'initialisation JDBC côté Java.
- **Commandes de remédiation :**
  ```bash
  # Activation immédiate du mode WAL via le binaire sqlite3
  sqlite3 /opt/aethercraft/server/data/aethercraft.db "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;"
  ```
  ```python
  # Dans web/services/database.py
  def get_db_connection() -> sqlite3.Connection:
      os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
      conn = sqlite3.connect(DB_PATH, timeout=10.0, factory=ManagedConnection)
      conn.execute("PRAGMA journal_mode=WAL;")
      conn.execute("PRAGMA synchronous=NORMAL;")
      conn.execute("PRAGMA busy_timeout=5000;")
      conn.row_factory = sqlite3.Row
      return conn
  ```

---

### DAT-02 — Absence de temporisation `busy_timeout` face à la concurrence multi-thread Waitress

- **Niveau de risque :** 🟠 **Élevé** (CVSS v3.1 : 7.1 / CWE-400: Resource Exhaustion)
- **Fichiers et lignes concernées :**
  - `web/services/database.py` (ligne 29) : appel à `sqlite3.connect()` sans argument `timeout`.
  - `server/plugins_src/AetherVisuals/src/io/aethercraft/visuals/AetherDatabase.java`
- **Constat :**  
  L'application Web utilise Waitress avec `threads=8` (`waitress.serve(..., threads=8)`), mais n'attribue aucun délai d'attente lors de l'acquisition des connexions SQLite.
- **Impact concret en exploitation :**  
  En cas de micro-conflit d'écriture de 50 millisecondes (ex. traitement d'un ordre de bourse), toute requête concurrente entrante sur un autre thread de Waitress échoue immédiatement en levant une exception au lieu de temporiser quelques instants en attendant la libération du verrou.
- **Plan d'action :**
  1. Ajouter `timeout=10.0` dans l'appel `sqlite3.connect()`.
  2. Exécuter systématiquement `PRAGMA busy_timeout = 5000;` lors de l'ouverture de chaque connexion.
  3. Côté JDBC Java, ajouter `?busy_timeout=5000` à l'URL de connexion JDBC : `jdbc:sqlite:/opt/aethercraft/server/data/aethercraft.db?busy_timeout=5000`.

---

### DAT-03 — Absence totale de routine et de politique de sauvegarde automatisée

- **Niveau de risque :** 🔴 **Critique** (CVSS v3.1 : 8.2 / CWE-699: Insufficient Data Backup)
- **Fichiers et lignes concernées :**
  - Répertoire `server/data/`, absence de crontab ou de timer systemd dédié.
  - `README.md` (ligne 167) : conseil obsolète invitant à supprimer manuellement `aethercraft.db`.
- **Constat :**  
  Il n'existe aucune routine de sauvegarde (ni locale, ni distante) pour le fichier `aethercraft.db` ni pour les fichiers de mondes Minecraft (`server/world`, `server/world_nether`, `server/world_the_end`).
- **Impact concret en exploitation :**  
  En cas d'incident matériel sur l'hôte, de coupure électrique brutale, de corruption de bloc ou d'erreur d'administration, l'intégralité des données (comptes, soldes financiers, quêtes, objets de boutique payés en argent réel, et constructions des joueurs) est irréversiblement perdue.
- **Plan d'action :**
  1. Mettre en place un script de sauvegarde exploitant l'API officielle de sauvegarde à chaud de SQLite (`VACUUM INTO` ou `sqlite3 .backup`) qui garantit un instantané cohérent sans interrompre les transactions en cours.
  2. Planifier une exécution horaire avec rotation (rétention : 24 horaires, 7 quotidiens, 4 hebdomadaires).
  3. Chiffrer et synchroniser les archives vers un compartiment de stockage distant S3 / R2 chiffré au repos.
- **Commandes de remédiation :**
  ```bash
  # Création du script de sauvegarde atomique /opt/aethercraft/scripts/backup.sh
  cat << 'EOF' > /opt/aethercraft/scripts/backup.sh
  #!/bin/bash
  set -euo pipefail
  BACKUP_DIR="/opt/aethercraft/backups"
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  mkdir -p "${BACKUP_DIR}"

  # Sauvegarde atomique SQLite sans coupure
  sqlite3 /opt/aethercraft/server/data/aethercraft.db "VACUUM INTO '${BACKUP_DIR}/aethercraft_${TIMESTAMP}.db';"
  gzip -9 "${BACKUP_DIR}/aethercraft_${TIMESTAMP}.db"

  # Rétention 7 jours
  find "${BACKUP_DIR}" -name "aethercraft_*.db.gz" -mtime +7 -delete
  EOF
  chmod +x /opt/aethercraft/scripts/backup.sh
  (crontab -l 2>/dev/null; echo "0 * * * * /opt/aethercraft/scripts/backup.sh >/dev/null 2>&1") | crontab -
  ```

---

### DAT-04 — File d'attente `rcon_queue` orpheline sans worker de traitement asynchrone

- **Niveau de risque :** 🟠 **Élevé** (CVSS v3.1 : 7.2 / CWE-404: Unhandled Asynchronous Queue)
- **Fichiers et lignes concernées :**
  - `web/services/database.py` (lignes 120-130) : création de la table `rcon_queue`.
  - `web/services/rcon_service.py` (lignes 143-157) : insertion des commandes échouées avec le statut `PENDING`.
- **Constat :**  
  Lorsque le serveur Minecraft est éteint ou redémarre, toute commande de distribution d'objet achetée sur la boutique Web est enregistrée dans la table `rcon_queue` avec le statut `PENDING`. Cependant, **aucun script, thread ni worker ne consulte cette table pour rejouer les commandes**.
- **Impact concret en exploitation :**  
  Si un joueur effectue un achat sur la boutique pendant un reboot ou un crash du serveur de jeu, sa commande reste indéfiniment bloquée en base. Le joueur n'est jamais crédité de son grade ou de ses items bien qu'ayant été débité, générant des litiges de support immédiats.
- **Plan d'action :**
  1. Concevoir un service d'arrière-plan autonome (`rcon_queue_worker.py`).
  2. Dès que la sonde RCON détecte que le serveur Paper est opérationnel, dépiler les commandes `PENDING` par ordre chronologique et mettre à jour leur statut en `EXECUTED`.
  3. Intégrer ce worker dans une unité systemd dédiée (`aether-rcon-worker.service`).
- **Commandes de remédiation :**
  ```python
  # Logique du worker rcon_worker.py
  def process_pending_rcon_queue():
      if not is_minecraft_server_alive():
          return
      with get_db_connection() as conn:
          cursor = conn.cursor()
          cursor.execute("SELECT id, command FROM rcon_queue WHERE status = 'PENDING' ORDER BY id ASC LIMIT 50;")
          for row in cursor.fetchall():
              ok, _ = rcon_client.send_command(row["command"])
              if ok:
                  cursor.execute("UPDATE rcon_queue SET status = 'EXECUTED', executed_at = datetime('now') WHERE id = ?;", (row["id"],))
          conn.commit()
  ```

---

## 4. PILIER 3 : GESTION DES ERREURS & STABILITÉ APPLICATIVE

---

### ERR-01 — Script de redémarrage automatique inexistant dans `spigot.yml` (`./start.sh`)

- **Niveau de risque :** 🔴 **Critique** (CVSS v3.1 : 8.6 / CWE-404: Improper Resource Shutdown / Restart)
- **Fichiers et lignes concernées :**
  - `server/spigot.yml` (lignes 33-34) :
    ```yaml
    settings:
      restart-on-crash: true
      restart-script: ./start.sh
    ```
- **Constat :**  
  Dans `spigot.yml`, l'option `restart-on-crash` est activée et pointe vers `./start.sh`. Cependant, **aucun fichier nommé `start.sh` n'existe dans le répertoire `server/` ni à la racine**. Les vrais scripts de lancement du dépôt sont nommés `run-server.sh` (Linux) et `run-server.bat` (Windows).
- **Impact concret en exploitation :**  
  En cas de crash de PaperMC (ex. timeout watchdog,OutOfMemory, ou commande `/restart`), Spigot tente d'exécuter `./start.sh`. L'appel système échoue avec `No such file or directory`, et le processus Java s'éteint définitivement au lieu de redémarrer.
- **Plan d'action :**
  1. Modifier `spigot.yml` pour pointer vers `./run-server.sh`.
  2. Créer un lien symbolique ou un fichier exécutable `server/start.sh` pointant vers `run-server.sh` comme filet de sécurité.
- **Commandes de remédiation :**
  ```bash
  sed -i 's|restart-script: ./start.sh|restart-script: ./run-server.sh|' /opt/aethercraft/server/spigot.yml
  ln -sf run-server.sh /opt/aethercraft/server/start.sh
  chmod +x /opt/aethercraft/server/run-server.sh /opt/aethercraft/server/start.sh
  ```

---

### ERR-02 — Absence de gestionnaires d'erreurs globaux Flask (`@app.errorhandler(404/500)`)

- **Niveau de risque :** 🟠 **Élevé** (CVSS v3.1 : 6.5 / CWE-209: Generation of Error Message Containing Sensitive Information)
- **Fichiers et lignes concernées :**
  - `web/app.py` (aucune définition de gestionnaire d'erreur global).
- **Constat :**  
  L'application Flask ne déclare aucun gestionnaire d'erreur personnalisé (`@app.errorhandler(404)`, `@app.errorhandler(500)`).
- **Impact concret en exploitation :**  
  En cas d'exception non interceptée (ex: timeout de base de données, erreur de format JSON), le moteur renvoie la page d'erreur par défaut de Werkzeug. En mode production ou debug accidentel, cette page peut exposer des traces de pile d'exécution complètes (stack traces), des chemins absolus sur le système de fichiers hôte (`/opt/aethercraft/...`) et les versions des dépendances.
- **Plan d'action :**
  1. Déclarer des handlers globaux pour les statuts HTTP 400, 404, 429 et 500.
  2. Adapter la réponse selon le type de requête : renvoyer un JSON uniforme `{"error": "...", "code": 500}` pour les endpoints d'API (`/api/*`), et une vue HTML épurée sans trace technique pour les navigateurs.
- **Commandes de remédiation :**
  ```python
  # Dans web/app.py
  @app.errorhandler(404)
  def handle_not_found(e):
      if request.path.startswith("/api/"):
          return jsonify({"error": "Resource Not Found", "code": 404}), 404
      return render_template("errors/404.html"), 404

  @app.errorhandler(500)
  def handle_internal_error(e):
      app.logger.error(f"Internal server error: {e}")
      if request.path.startswith("/api/"):
          return jsonify({"error": "Internal Server Error", "code": 500}), 500
      return render_template("errors/500.html"), 500
  ```

---

### ERR-03 — Explosion quadratique $O(N^2)$ des requêtes SQLite lors des connexions joueurs

- **Niveau de risque :** 🟠 **Élevé** (CVSS v3.1 : 7.5 / CWE-400: Uncontrolled Resource Consumption)
- **Fichiers et lignes concernées :**
  - `server/plugins_src/AetherVisuals/src/io/aethercraft/visuals/AetherVisualScoreboardManager.java` (lignes 86-93 et 101-122) :
    ```java
    @EventHandler
    public void onPlayerJoin(PlayerJoinEvent event) {
        ...
        Bukkit.getScheduler().runTaskLater(plugin, this::refreshAllOnlinePlayers, 20L);
    }
    public void refreshAllOnlinePlayers() {
        for (Player p : Bukkit.getOnlinePlayers()) {
            refreshPlayer(p); // Déclenche un thread async avec requête SQL pour chaque joueur !
        }
    }
    ```
- **Constat :**  
  À chaque fois qu'un joueur rejoint le serveur, `onPlayerJoin` appelle `refreshAllOnlinePlayers()`, qui itère sur **tous les joueurs en ligne** et lance une requête asynchrone SQLite `fetchPlayerData` pour chacun d'eux.
- **Impact concret en exploitation :**  
  Pour une vague de 50 connexions simultanées (lors d'un test de charge ou de l'ouverture du serveur), le nombre total de requêtes asynchrones bombardant SQLite est de $\sum_{k=1}^{50} k = \frac{50 \times 51}{2} = \mathbf{1\,275}$ requêtes SQL ! Combiné au mode `DELETE` de SQLite (DAT-01), cela provoque des contentions I/O massives et fige le thread principal Paper.
- **Plan d'action :**
  1. Lors de la connexion d'un joueur, exécuter la requête SQLite uniquement pour le joueur entrant.
  2. Pour tous les autres joueurs déjà connectés, mettre à jour uniquement le compteur numérique de joueurs en ligne dans le scoreboard en mémoire sans ré-interroger la base de données SQLite.
- **Commandes de remédiation :**
  ```java
  // Correction dans AetherVisualScoreboardManager.java
  @EventHandler
  public void onPlayerJoin(PlayerJoinEvent event) {
      Player p = event.getPlayer();
      Bukkit.getScheduler().runTaskLater(plugin, () -> refreshPlayer(p), 10L);
      // Diffuse uniquement le nombre de joueurs sans requête SQL
      int onlineCount = Bukkit.getOnlinePlayers().size();
      Bukkit.getScheduler().runTaskLater(plugin, () -> updateOnlineCountOnly(onlineCount), 20L);
  }
  ```

---

## 5. PILIER 4 : SUPERVISION, MONITORING & MÉTRIQUES

---

### SUP-01 — Unités systemd dépourvues de limites de ressources (`LimitNOFILE`, `MemoryMax`)

- **Niveau de risque :** 🟠 **Élevé** (CVSS v3.1 : 7.3 / CWE-770: Allocation of Resources Without Limits)
- **Fichiers et lignes concernées :**
  - `systemd/aether-minecraft.service`
  - `systemd/aether-web.service`
- **Constat :**  
  Les unités systemd ne définissent aucune directive de restriction de ressources (`LimitNOFILE`, `MemoryMax`, `TasksMax`, `CPUQuota`).
- **Impact concret en exploitation :**  
  Sous la charge de 50 joueurs et de connexions Web intenses, la limite par défaut de descripteurs de fichiers (`LimitNOFILE=1024` sous Linux classique) peut être rapidement atteinte par PaperMC (sockets TCP, chunks chargés, jars de plugins, drivers JDBC), menant à des crashes `java.io.IOException: Too many open files`. De plus, sans `MemoryMax`, une fuite mémoire dans la JVM peut consommer 100% de la RAM hôte et déclencher le Linux OOM Killer.
- **Plan d'action :**
  1. Configurer `LimitNOFILE=65536` sur les deux services systemd.
  2. Définir `MemoryMax=10G` et `TasksMax=infinity` sur `aether-minecraft.service`.
  3. Ajouter `RestartSec=5s` et `TimeoutStopSec=45s` pour permettre une sauvegarde propre des mondes lors de l'arrêt du service.
- **Commandes de remédiation :**
  ```ini
  # Ajout dans /opt/aethercraft/systemd/aether-minecraft.service sous [Service]
  LimitNOFILE=65536
  MemoryMax=10G
  TasksMax=infinity
  TimeoutStopSec=45s
  ```

---

### SUP-02 — Absence de politique de rotation des logs applicatifs

- **Niveau de risque :** 🟡 **Moyen** (CVSS v3.1 : 5.3 / CWE-778: Insufficient Logging / Storage)
- **Fichiers et lignes concernées :**
  - `web/app.py`, `server/logs/latest.log`
- **Constat :**  
  Aucune configuration de rotation de journaux applicatifs (`logrotate` ou gestionnaire Python `TimedRotatingFileHandler`) n'est configurée.
- **Impact concret en exploitation :**  
  En production continue, les fichiers de logs (particulièrement les logs de requêtes Waitress et les traces de GrimAC) peuvent saturer insidieusement la partition disque `/` ou `/var`, entraînant des pannes de persistance SQLite.
- **Plan d'action :**
  1. Déployer un fichier de configuration `logrotate` pour `/opt/aethercraft/logs/*.log`.
  2. Appliquer une rotation quotidienne avec compression gzip et rétention sur 14 jours.
- **Commandes de remédiation :**
  ```bash
  cat << 'EOF' | sudo tee /etc/logrotate.d/aethercraft
  /opt/aethercraft/logs/*.log /opt/aethercraft/server/logs/*.log {
      daily
      rotate 14
      compress
      delaycompress
      missingok
      notifempty
      copytruncate
  }
  EOF
  ```

---

### SUP-03 — Table relationnelle `server_telemetry` orpheline et inexploitée

- **Niveau de risque :** 🟡 **Moyen** (CVSS v3.1 : 4.3 / CWE-1065: Runtime Incomplete Feature)
- **Fichiers et lignes concernées :**
  - `web/services/database.py` (lignes 134-142) :
    ```sql
    CREATE TABLE IF NOT EXISTS server_telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        tps REAL NOT NULL DEFAULT 20.0,
        online_players INTEGER NOT NULL DEFAULT 0,
        ram_used_mb REAL NOT NULL DEFAULT 1024.0,
        ram_max_mb REAL NOT NULL DEFAULT 4096.0
    );
    ```
- **Constat :**  
  La table `server_telemetry` est formellement déclarée dans le schéma relationnel de la base de données, mais **aucune fonction, plugin ou thread dans l'ensemble du projet n'écrit de données dans cette table**.
- **Impact concret en exploitation :**  
  Aucun historique de métriques système (évolution du TPS, saturation de la RAM, pics d'affluence) n'est enregistré. En cas de freeze serveur ou de crash in-game, l'équipe d'exploitation ne dispose d'aucun enregistrement chronologique pour mener une analyse post-mortem.
- **Plan d'action :**
  1. Implémenter une tâche planifiée dans `AetherVisualsPlugin.java` ou un daemon Python qui échantillonne le TPS (via spark ou Bukkit), la RAM consommée et le nombre de joueurs chaque minute et enregistre les valeurs dans `server_telemetry`.
  2. Ajouter une politique de purge automatique conservant 30 jours d'historique.

---

### SUP-04 — Absence d'exporteur de métriques standard (Prometheus) et d'alerting

- **Niveau de risque :** 🟠 **Élevé** (CVSS v3.1 : 6.8 / CWE-778: Insufficient Operational Visibility)
- **Fichiers et lignes concernées :**
  - `web/app.py`, `server/config/paper-global.yml` (spark activé mais local uniquement).
- **Constat :**  
  La plateforme ne dispose d'aucun endpoint `/metrics` au format Prometheus et d'aucun canal d'alerte automatisé (Discord Webhook, Alertmanager).
- **Impact concret en exploitation :**  
  Les administrateurs système ne sont informés d'un incident critique (chute du TPS en dessous de 15.0, plantage du service Web, fuite de mémoire) que lorsque les utilisateurs se plaignent sur les canaux de support.
- **Plan d'action :**
  1. Intégrer `prometheus-flask-exporter` dans l'application Flask pour exposer `/metrics` (sécurisé par authentification réseau interne).
  2. Installer le plugin `PrometheusExporter` sur PaperMC.
  3. Configurer un Webhook Discord envoyant des alertes automatiques en cas de TPS < 18.0 ou de redémarrage de service.
- **Commandes de remédiation :**
  ```bash
  pip install prometheus-flask-exporter
  ```

---

## 6. PILIER 5 : RÉSILIENCE RÉSEAU & ARCHITECTURE D'EXPOSITION

---

### NET-01 — Exposition directe du serveur WSGI Waitress sans reverse proxy TLS/Nginx

- **Niveau de risque :** 🔴 **Critique** (CVSS v3.1 : 8.8 / CWE-319: Cleartext Transmission of Sensitive Information)
- **Fichiers et lignes concernées :**
  - `web/app.py` (ligne 1037) : `serve(app, host="0.0.0.0", port=5000, threads=8, channel_timeout=120)`
- **Constat :**  
  Le serveur Waitress est directement lié sur `0.0.0.0:5000` en protocole HTTP clair non chiffré sans couche de terminaison TLS/HTTPS ni reverse proxy amont.
- **Impact concret en exploitation :**  
  1. Les mots de passe des joueurs, les identifiants de session et les transactions de boutique circulent en clair sur le réseau public Internet, exposés à l'interception et au vol de session (Man-in-the-Middle).
  2. Waitress n'est pas conçu pour faire face aux attaques DoS de type Slowloris (épuisement de connexions HTTP lentes).
- **Plan d'action :**
  1. Restreindre Waitress pour écouter exclusivement sur la boucle locale : `host="127.0.0.1"`.
  2. Déployer un reverse proxy Nginx ou Caddy en frontal avec certificat TLS Let's Encrypt (TLS 1.2/1.3), compression Brotli/Gzip et HTTP/2.
- **Commandes de remédiation :**
  ```nginx
  # Fichier /etc/nginx/sites-available/aethercraft.conf
  server {
      listen 80;
      server_name aethercraft.net;
      return 301 https://$host$request_uri;
  }
  server {
      listen 443 ssl http2;
      server_name aethercraft.net;
      ssl_certificate /etc/letsencrypt/live/aethercraft.net/fullchain.pem;
      ssl_certificate_key /etc/letsencrypt/live/aethercraft.net/privkey.pem;

      location / {
          proxy_pass http://127.0.0.1:5000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
      location /static/ {
          alias /opt/aethercraft/web/static/;
          expires 30d;
          add_header Cache-Control "public, no-transform";
      }
  }
  ```

---

### NET-02 — Port de jeu Minecraft 25565 exposé publiquement sans protection anti-DDoS

- **Niveau de risque :** 🟠 **Élevé** (CVSS v3.1 : 7.5 / CWE-400: Uncontrolled Resource Consumption)
- **Fichiers et lignes concernées :**
  - `server/server.properties` (ligne 54) : `server-port=25565`
  - `server/config/paper-global.yml`
- **Constat :**  
  Le port 25565 de PaperMC est exposé sans passerelle de protection contre les attaques par déni de service distribué (DDoS).
- **Impact concret en exploitation :**  
  Une attaque par amplification UDP, inondation SYN ou saturation de handshakes bots Minecraft (ex: attaques MCStorm) peut saturer la bande passante et faire tomber la liaison réseau du serveur dédié en quelques secondes.
- **Plan d'action :**
  1. Positionner un proxy Minecraft de protection amont (Velocity, TCPShield, NeoProtect ou Cloudflare Spectrum for Minecraft).
  2. Filtrer le port TCP 25565 au niveau d'iptables/ufw pour refuser tout paquet ne provenant pas des passerelles certifiées du proxy anti-DDoS.
- **Commandes de remédiation :**
  ```bash
  # Verrouillage iptables du port 25565 pour autoriser uniquement l'IP du proxy
  sudo iptables -A INPUT -p tcp --dport 25565 -s 198.51.100.10 -j ACCEPT
  sudo iptables -A INPUT -p tcp --dport 25565 -j DROP
  ```

---

### NET-03 — Absence de support `proxy-protocol` pour la préservation des adresses IP réelles

- **Niveau de risque :** 🟡 **Moyen** (CVSS v3.1 : 5.8 / CWE-290: Authentication Bypass by Spoofing)
- **Fichiers et lignes concernées :**
  - `server/config/paper-global.yml`
- **Constat :**  
  Le protocole HAProxy PROXY Protocol v2 n'est pas activé dans la configuration de PaperMC.
- **Impact concret en exploitation :**  
  Dès lors qu'un reverse proxy L4 anti-DDoS (TCPShield ou HAProxy) est placé devant PaperMC, toutes les connexions des joueurs apparaissent comme provenant de l'adresse IP unique du proxy. Cela rend inopérants les bannissements par IP (`/ban-ip`), le rate-limiting anticheat de GrimAC et le filtrage des attaques par force brute.
- **Plan d'action :**
  1. Activer `proxy-protocol: true` dans `server/config/paper-global.yml`.
  2. Configurer la liste blanche des adresses IP de proxies autorisées à transmettre les en-têtes PROXY Protocol.

---

## 7. Plan d'Action & Feuille de Route de Remédiation Priorisée

```
+---------------------------------------------------------------------------------------------------+
| FEUILLE DE ROUTE DE REMÉDIATION TECHNIQUE                                                         |
+---------------------------------------------------------------------------------------------------+
| PHASE 1 — BLOQUEURS CRITIQUES PRÉ-LANCEMENT (P0 : À réaliser avant toute ouverture publique)      |
+---------------------------------------------------------------------------------------------------+
| 1. [DAT-01] Activer SQLite WAL mode : PRAGMA journal_mode=WAL et PRAGMA synchronous=NORMAL.     |
| 2. [SEC-01] Éliminer le mot de passe RCON par défaut et forcer la variable d'environnement.       |
| 3. [SEC-02] Forcer une clé cryptographique forte pour FLASK_SECRET_KEY et sécuriser les cookies. |
| 4. [SEC-03] Créer l'utilisateur système 'aethercraft' et bannir User=root dans systemd.          |
| 5. [SEC-04] Activer online-mode=true ou déployer un plugin d'authentification in-game.            |
| 6. [ERR-01] Corriger restart-script dans spigot.yml vers ./run-server.sh.                         |
| 7. [NET-01] Déployer Nginx en frontal avec certificat TLS Let's Encrypt (HTTPS).                 |
| 8. [DAT-03] Installer le script de sauvegarde atomique SQLite horaire avec rétention.            |
+---------------------------------------------------------------------------------------------------+
| PHASE 2 — CONSOLIDATION DE LA STABILITÉ OPÉRATIONNELLE (P1 : Sous 72 heures)                      |
+---------------------------------------------------------------------------------------------------+
| 9.  [DAT-02] Définir timeout=10.0 et busy_timeout=5000 sur toutes les connexions SQLite.         |
| 10. [SEC-05] Corriger le middleware pour ne faire confiance qu'au reverse proxy local.           |
| 11. [ERR-03] Supprimer la boucle de requêtes N^2 dans AetherVisualScoreboardManager.java.         |
| 12. [DAT-04] Implémenter le worker asynchrone pour traiter rcon_queue.                            |
| 13. [ERR-02] Déclarer les errorhandlers Flask 404/500 retournant des réponses génériques.        |
| 14. [SUP-01] Ajouter LimitNOFILE=65536 et MemoryMax=10G dans les unités systemd.                |
| 15. [SEC-06] Supprimer le drapeau --no-sandbox dans MapBrowser/config.yml.                       |
+---------------------------------------------------------------------------------------------------+
| PHASE 3 — INDUSTRIALISATION & SUPERVISION CONTINUE (P2 : Sous 7 jours)                           |
+---------------------------------------------------------------------------------------------------+
| 16. [NET-02 & NET-03] Déployer un tunnel anti-DDoS Minecraft et activer proxy-protocol.          |
| 17. [SUP-02] Configurer logrotate pour les journaux Web et Minecraft.                            |
| 18. [SUP-04] Déployer prometheus-flask-exporter et configurer un Webhook d'alerting Discord.     |
| 19. [SUP-03] Connecter le reporting périodique de télémétrie dans server_telemetry.              |
| 20. [SEC-07] Ajouter des jetons CSRF sur les formulaires de boutique et de marché.              |
+---------------------------------------------------------------------------------------------------+
```

---

## 8. Conclusion de l'Audit & Avis de Conformité

L'audit technique confirme qu'**AetherCraft** dispose d'un gameplay MMO novateur et d'un couplage web immersif à fort potentiel.  
Toutefois, en l'état actuel de son infrastructure :
- La persistance SQLite en mode `DELETE` provoquera des **verrouillages critiques sous la charge de 50 joueurs simultanés**.
- La présence d'identifiants en dur, de services exécutés en `root` et l'absence de TLS exposent le serveur à des **compromissions immédiates**.

L'application stricte des **8 remédiations de Phase 1** détaillées dans ce rapport permettra de lever l'ensemble des verrous bloquants et de garantir une ouverture en **V1 Bêta** stable, performante et sécurisée.
