mod installer;
mod manifest;
mod runner;

use anyhow::Result;
use clap::{Parser, Subcommand};
use colored::*;
use installer::AetherInstaller;
use manifest::ServerManifest;
use runner::AetherRunner;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(
    name = "aether-mc-runner",
    about = "🪐 Runner & Installer de Serveurs Minecraft Haute Performance Aether",
    version = "1.0.0"
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Télécharge et installe les composants spécifiés dans le manifest
    Install {
        /// Chemin local ou URL HTTP(S) vers le manifest JSON
        #[arg(short, long)]
        manifest: String,

        /// Répertoire cible de l'instance (par défaut: ./instances/<server_id>)
        #[arg(short, long)]
        dir: Option<PathBuf>,
    },

    /// Lance une instance Minecraft préalablement installée
    Run {
        /// Répertoire de l'instance contenant le fichier .aether-manifest.json
        #[arg(short, long)]
        dir: PathBuf,
    },

    /// Installe puis démarre immédiatement le serveur
    InstallAndRun {
        /// Chemin local ou URL HTTP(S) vers le manifest JSON
        #[arg(short, long)]
        manifest: String,

        /// Répertoire cible de l'instance
        #[arg(short, long)]
        dir: Option<PathBuf>,
    },

    /// Vérifie les prérequis de l'environnement (Java 21, connectivité, etc.)
    Doctor,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    println!(
        "{}",
        "🪐 AETHER MINECRAFT RUNNER & INSTALLER (Rust Tokio)"
            .bold()
            .cyan()
    );

    match cli.command {
        Commands::Install { manifest, dir } => {
            let m = ServerManifest::load(&manifest).await?;
            let target_dir = dir.unwrap_or_else(|| PathBuf::from("instances").join(&m.server_id));
            let installer = AetherInstaller::new(&target_dir);
            installer.install(&m).await?;
        }

        Commands::Run { dir } => {
            let manifest_path = dir.join(".aether-manifest.json");
            if !manifest_path.exists() {
                anyhow::bail!(
                    "Fichier .aether-manifest.json introuvable dans {}",
                    dir.display()
                );
            }
            let raw = tokio::fs::read_to_string(&manifest_path).await?;
            let m: ServerManifest = serde_json::from_str(&raw)?;
            let runner = AetherRunner::new(&dir);
            runner.run(&m).await?;
        }

        Commands::InstallAndRun { manifest, dir } => {
            let m = ServerManifest::load(&manifest).await?;
            let target_dir = dir.unwrap_or_else(|| PathBuf::from("instances").join(&m.server_id));
            let installer = AetherInstaller::new(&target_dir);
            installer.install(&m).await?;

            let runner = AetherRunner::new(&target_dir);
            runner.run(&m).await?;
        }

        Commands::Doctor => {
            println!("{}", "🩺 Diagnostic des prérequis Aether...".bold());

            // 1. Détection Java
            match AetherRunner::detect_java().await {
                Ok(_) => println!("  {} Runtime Java opérationnel", "✅".green()),
                Err(e) => println!("  {} Attention : {}", "⚠️".yellow(), e),
            }

            // 2. Test connectivité PaperMC Fill v3 API
            let client = reqwest::Client::builder()
                .user_agent("AetherCraft-Runner/1.0.0 (contact@aethercraft.net)")
                .timeout(std::time::Duration::from_secs(5))
                .build()?;
            match client.get("https://fill.papermc.io/v3/projects/paper").send().await {
                Ok(res) if res.status().is_success() => {
                    println!("  {} Connectivité PaperMC Fill v3 API : OK", "✅".green())
                }
                _ => println!("  {} Connectivité PaperMC Fill v3 API : Erreur ou hors-ligne", "⚠️".yellow()),
            }

            println!("{}", "Diagnostic terminé !".bold());
        }
    }

    Ok(())
}
