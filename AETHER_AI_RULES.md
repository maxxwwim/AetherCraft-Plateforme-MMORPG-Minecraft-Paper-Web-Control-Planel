# 🪐 AETHERSCOPE V2 — DIRECTIVES SYSTÈME COPILOTE IA (COMMANDES MCP COMBINÉES & GOUVERNANCE)

> **Projet :** `aethercraft`  
> **Racine :** `C:\Users\1234\Desktop\Projets\aethercraft`  
> **Stack Détectée :** 🦀 Pure Rust (Cargo Workspace Hexagonal)  
> **Architecture Active :** Cargo Workspace : `crates/domain` (100% pur), `crates/server-axum`, `crates/client-ui`, `crates/db-adapter`  
> **Serveur Local AetherScope :** `http://127.0.0.1:3030`  

Tu opères en binôme direct avec le développeur et le moteur d'intelligence architecturale **AetherScope V2**.
Le graphe 3D WebGL 2 tourne en continu sur le port `3030` et audite chaque modification du codebase en temps réel (< 50 ms).

---

## ⚡ 1. WORKFLOW MCP COMBINÉ EN 3 APPELS (ZÉRO COMMANDES REDONDANTES)
Les commandes MCP d'AetherScope ont été **fusionnées et réduites à 8 outils combinés** pour minimiser les appels d'outils :

1. **Au Démarrage / Diagnostic Global (1 seul appel 4-en-1) :**
   - Exécute **`aetherscope_get_graph_summary({"path": ".", "rescan": false, "include_tasks": true})`**
   - *(Combine le résumé du graphe 3D + les violations SAST/CWE actives + la liste des tâches en cours + un rescan optionnel).*
   - Annonce l'état en 1 ligne : `🪐 [AETHER_STATUS : Nœuds=<N>, Flux=<F>, Sécurité=<OK | X violations>, Tâches=<T actives>]`

2. **Avant de Lire / Modifier un Symbole ou Fichier (1 seul appel 3-en-1) :**
   - Exécute **`aetherscope_get_active_target({"symbol_id": "<symbole_ou_fichier>", "action": "Analyse", "details": "<objectif>", "trace_direction": "both"})`**
   - *(Combine automatiquement : (1) Téléportation de la caméra 3D WebGL & badge HUD, (2) Chargement du contrat EARS + Handshake XML + tâches liées, et (3) Traçage complet des flux amont/aval).*

3. **Après Chaque Modification de Code (1 seul appel 4-en-1) :**
   - Exécute **`aetherscope_verify_patch({"files_modified": ["<chemin_fichier>"], "task_id": "<task_id_optionnel>", "status": "done", "progress": 100, "chat_message": "<résumé_court>"})`**
   - *(Combine : (1) Le Pare-Feu Temps Réel < 50ms SAST 150+ CWE & contrats EARS/BLAKE3, (2) Téléportation caméra sur l'état validé ou la ligne en faute, (3) Mise à jour/clôture automatique de la tâche, et (4) Publication du compte-rendu dans le Chat Copilot AetherScope).*
   - Si le verdict est `[PATCH_REJECTED]`, corrige immédiatement les violations signalées et relance `aetherscope_verify_patch`.

---

## 🛠️ 2. RÉFÉRENTIEL DES 8 COMMANDES MCP COMBINÉES (`aetherscope_*`)
Spécifie toujours les paramètres exacts lors de tes appels MCP :

1. **`aetherscope_get_graph_summary(path?, rescan?, include_tasks?, severity?)`** *(4-en-1)*
   - Vue globale de l'architecture, dossiers, violations CWE filtrables par `severity` (`"critical"`, `"high"`, `"all"`), tâches actives (`include_tasks: true` par défaut) et réanalyse AST (`rescan: true` remplace `scan_project`).
2. **`aetherscope_get_active_target(symbol_id, action?, details?, trace_direction?, max_depth?, path?)`** *(3-en-1)*
   - Aligne la caméra 3D (`action`: `"Inspection"` | `"Analyse"` | `"Refactoring"` | `"Correction CVE"`), extrait le contrat EARS & Handshake XML, et trace le flux MVC amont/aval (`trace_direction`: `"both"` par défaut, `"upstream"`, `"downstream"`, ou `"none"`).
3. **`aetherscope_search_symbols(query?, layer?, kind?, stereotype?, has_violation?, cwe_id?, severity?, file_pattern?, limit?, path?)`** *(2-en-1)*
   - Combine la recherche multi-critères dans l'AST (`layer`: `"ui"` | `"action"` | `"domain"` | `"database"`, `kind`, `stereotype`) ET l'audit détaillé des violations SAST/CWE (`cwe_id`, `severity`, `file_pattern`) avec patrons de remédiation.
4. **`aetherscope_manage_tasks(action, task_id?, title?, kind?, target_symbol?, target_file?, priority?, status?, progress?, progress_note?, initial_readme?, full_readme?, status_filter?)`** *(3-en-1)*
   - Gère tout le cycle de vie des tâches dans `.aether/tasks/` via `action`:
     - `"list"` : liste les tâches (`status_filter`: `"active"` | `"all"` | `"done"`).
     - `"create"` : crée une tâche (`title`, `kind`: `"function"` | `"security_fix"` | `"arch_refactor"` | `"research"` | `"test"`, `target_symbol`, `priority`) et téléporte la caméra 3D.
     - `"update"` : met à jour une tâche (`task_id`, `status`: `"in_progress"` | `"done"` | `"blocked"`, `progress`: `0..100`, `progress_note`).
5. **`aetherscope_verify_patch(files_modified, task_id?, status?, progress?, progress_note?, chat_message?)`** *(4-en-1)*
   - Pare-Feu IA Temps Réel (< 50 ms) : vérifie les fichiers modifiés (`files_modified: ["..."]`), valide les 150+ règles CWE, l'atteignabilité Source-to-Sink et les contrats `README.md` (imports interdits, max lignes, BLAKE3). Si `[PATCH_APPROVED]`, met à jour `task_id` et envoie `chat_message` dans le HUD.
6. **`aetherscope_chat(action?, text?, thought?, target_symbol?)`** *(2-en-1)*
   - `action: "send"` (défaut si `text` fourni) : affiche un debrief Markdown dans le Chat Copilot d'AetherScope et centre la caméra sur `target_symbol`.
   - `action: "history"` : récupère l'historique des échanges du cockpit.
7. **`aetherscope_manage_plugins(action, target_path?, plugins_dir?, path?, plugin_name?, rule_id?, cwe_id?, name?, severity?, description?, remediation?, file_extensions?, ...)`** *(4-en-1)*
   - Gère les plugins déclaratifs YAML dans `.aether/plugins/` via `action`: `"list"` (inventaire), `"test"` (exécution des tests unitaires embarqués), `"scan"` (audit sur `target_path`), ou `"upsert"` (création/mise à jour certifiée d'une règle CWE).
8. **`aetherscope_teleport_camera(target, action, details)`**
   - Déplacement rapide de la caméra 3D WebGL et mise à jour du fil d'Ariane stellaire sans recharger le contrat complet.

*(Note : les anciens noms d'outils unitaires restent supportés en alias rétrocompatibles par le serveur MCP, mais privilégie toujours les 8 commandes combinées ci-dessus).*

---

## 🔒 3. ZERO-SHELL PROTOCOLE DE GOUVERNANCE & CONTRATS EARS
1. **Avant d'écrire ou modifier du code :**
   - Exécute `aetherscope_get_active_target` sur le symbole/fichier visé (ou lis `.aether/ACTIVE_TARGET.md` et le `README.md` du dossier).
   - Ne modifie JAMAIS un `README.md` pour contourner une règle : son empreinte cryptographique BLAKE3 est scellée dans `aether.lock.toml`.
2. **Après chaque modification :**
   - Passe systématiquement par `aetherscope_verify_patch(files_modified: [...])` pour certifier `0 violation` avant de conclure.

---

## 🏛️ 4. INVARIANTS PAR COUCHE & SÉPARATION STRICTE
- `contracts/` : Traits Rust (`RepositoryPort`), DTOs partagés Serde et schémas RPC stricts
- `client/` : Rendu graphique, formulaires («Form»), état réactif. Ne doit JAMAIS importer `server/domain` ni `data-nodes`.
- `server/domain/` : **100% pur, déterministe, zéro I/O**. Interdiction formelle de requêtes SQL brutes, d'accès réseau ou de variables d'environnement (`process.env` / `std::env::var`).
- `server/application/` : Orchestration des cas d'usage reliant le domaine aux interfaces de persistance.
- `server/api/` : Contrôleurs d'entrée (REST / WebSocket) validant tout payload via `contracts/`.
- `data-nodes/` : Adaptateurs de persistance (PostgreSQL / SQLite / Redis) isolables en microservices.

---

## ⚡ 5. CONSIGNES DE RÉPONSE OPTIMISÉE
- **Concision & Densité :** Réponse technique, chirurgicale et directe. Zéro bavardage inutile.
- **Diffs Chirurgicaux :** Ne réécris jamais un fichier complet si seules quelques lignes changent.
- **Règle d'Atomicité (< 35 lignes) :** Découpe le code en fonctions atomiques pures de moins de 35 lignes maximum (particulièrement dans `domain/`).
- **Preuve de Lecture [AETHER_ACK] :** Démarre tes propositions techniques par :
  `[AETHER_ACK: cible=<symbole>, couche=<layer>, mcp=aetherscope_get_active_target->aetherscope_verify_patch]`
