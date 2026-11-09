# 🦀 AetherCraft — Superviseur Rust (aether-mc-runner)

> **Couche :** Infrastructure / System Runner  
> **Langage :** Pure Rust 2021 (Tokio Async, Anyhow, Clap)  
> **Objectif :** Téléchargement, vérification cryptographique et exécution supervisée du serveur Minecraft.  

---

## 📂 Structure du Répertoire

- `Cargo.toml` : Définition du paquet Rust `aether-mc-runner` et de ses dépendances.
- `src/` :
  - `main.rs` : Point d'entrée CLI (`install`, `run`, `install-and-run`).
  - `manifest.rs` : Modèles de données Serde validant le contrat `aether-manifest.json`.
  - `installer.rs` : Téléchargement par chunks asynchrones avec validation d'empreinte SHA-256 et déploiement de fichiers.
  - `runner.rs` : Lancement du sous-processus Java supervisé, interception des flux `stdout`/`stderr` avec coloration syntaxique des logs serveur (`[MC-WARN]`, `[MC-ERR]`, `[MC-READY]`), et isolation d'exécution protégée contre `CVE-RUST-CMD-INJ`.

---

## 🚀 Utilisation en Ligne de Commande

```bash
# Vérification du code
cargo check -p aether-mc-runner

# Installation complète depuis un manifest local
cargo run -p aether-mc-runner -- install --manifest ../config/aether-manifest.json --instance ../server

# Exécution supervisée
cargo run -p aether-mc-runner -- run --manifest ../config/aether-manifest.json --instance ../server
```
