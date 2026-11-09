use crate::manifest::ServerManifest;
use anyhow::{bail, Context, Result};
use colored::*;
use std::path::{Path, PathBuf};
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;

pub struct AetherRunner {
    instance_dir: PathBuf,
}

impl AetherRunner {
    pub fn new<P: AsRef<Path>>(instance_dir: P) -> Self {
        Self {
            instance_dir: instance_dir.as_ref().to_path_buf(),
        }
    }

    /// Détecte le binaire Java dans le PATH système et vérifie sa version
    pub async fn detect_java() -> Result<String> {
        let output = Command::new("java")
            .arg("-version")
            .output()
            .await
            .context("La commande 'java' est introuvable dans le PATH système. Veuillez installer Java 21+.")?;

        let version_str = String::from_utf8_lossy(&output.stderr);
        let first_line = version_str.lines().next().unwrap_or("inconnue");

        println!("{} Java détecté : {}", "☕".yellow(), first_line.cyan());
        Ok("java".to_string())
    }

    /// Exécute l'instance Minecraft supervisée
    pub async fn run(&self, manifest: &ServerManifest) -> Result<()> {
        Self::detect_java().await?;
        let jar_path = self.instance_dir.join(&manifest.core.target_jar);

        if !jar_path.exists() {
            bail!(
                "Le fichier JAR du serveur est introuvable : {}\nVeuillez exécuter la commande 'install' au préalable.",
                jar_path.display()
            );
        }

        println!(
            "{}",
            format!(
                "🚀 Lancement de Minecraft [{}] avec {} de RAM (Aikar Flags G1GC)...",
                manifest.core.r#type.to_uppercase(),
                manifest.runtime.heap_max
            )
            .bold()
            .green()
        );

        // Invocation directe du binaire java validé sans passer par un interpréteur shell
        let mut cmd = Command::new("java");
        cmd.current_dir(&self.instance_dir);

        // Ajout des flags JVM Aikar filtrés contre les injections de commandes (CWE-78 / CWE-88)
        let forbidden_prefixes = [
            "-agentlib",
            "-javaagent",
            "-agentpath",
            "-XX:OnOutOfMemoryError",
            "-XX:OnError",
            "-Djava.system.class.loader",
        ];
        for flag in &manifest.runtime.jvm_flags {
            if flag.starts_with('-')
                && !flag.chars().any(|c| ";|&`$><\r\n".contains(c))
                && !forbidden_prefixes.iter().any(|p| flag.starts_with(p))
            {
                cmd.arg(flag);
            }
        }

        // Arguments serveur
        cmd.arg("-jar");
        cmd.arg(&manifest.core.target_jar);
        cmd.arg("nogui");

        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());

        let mut child = cmd.spawn().context("Échec du spawn du processus Java Minecraft")?;
        let pid = child.id().unwrap_or(0);
        println!("📌 Processus supervisé démarré (PID: {})", pid);

        // Capture asynchrone des flux stdout et stderr
        let stdout = child.stdout.take().context("Impossible de capturer stdout")?;
        let stderr = child.stderr.take().context("Impossible de capturer stderr")?;

        let stdout_handle = tokio::spawn(async move {
            let mut reader = BufReader::new(stdout).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                if line.contains("WARN") {
                    println!("{} {}", "[MC-WARN]".yellow(), line);
                } else if line.contains("ERROR") {
                    println!("{} {}", "[MC-ERR]".red().bold(), line);
                } else if line.contains("Done (") {
                    println!("{} {}", "✨ [MC-READY]".green().bold(), line.green());
                } else {
                    println!("{} {}", "[MC]".blue(), line);
                }
            }
        });

        let stderr_handle = tokio::spawn(async move {
            let mut reader = BufReader::new(stderr).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                eprintln!("{} {}", "[MC-STDERR]".red(), line);
            }
        });

        // Attente de l'arrêt du processus
        let status = child.wait().await?;
        let _ = tokio::join!(stdout_handle, stderr_handle);

        println!(
            "{}",
            format!("🛑 Serveur Minecraft arrêté avec le code : {:?}", status.code())
                .bold()
                .yellow()
        );

        Ok(())
    }
}
