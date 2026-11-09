use crate::manifest::ServerManifest;
use anyhow::{bail, Context, Result};
use colored::*;
use futures_util::StreamExt;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use tokio::fs::{self, File};
use tokio::io::AsyncWriteExt;

pub struct AetherInstaller {
    client: reqwest::Client,
    instance_dir: PathBuf,
}

impl AetherInstaller {
    pub fn new<P: AsRef<Path>>(instance_dir: P) -> Self {
        Self {
            client: reqwest::Client::builder()
                .user_agent("Aether-MC-Runner/1.0")
                .build()
                .unwrap_or_default(),
            instance_dir: instance_dir.as_ref().to_path_buf(),
        }
    }

    /// Télécharge un fichier par chunks et vérifie optionnellement son checksum SHA-256
    pub async fn download_file(
        &self,
        url: &str,
        dest_path: &Path,
        expected_sha256: &str,
        label: &str,
    ) -> Result<()> {
        if let Some(parent) = dest_path.parent() {
            fs::create_dir_all(parent).await?;
        }

        println!(
            "{} Téléchargement de {} (depuis {})...",
            "⬇️".cyan(),
            label.bold(),
            url
        );

        let resp = self
            .client
            .get(url)
            .send()
            .await
            .context(format!("Erreur réseau pour {url}"))?
            .error_for_status()
            .context(format!("Code HTTP d'erreur pour {url}"))?;

        let _total_size = resp.content_length();
        let mut stream = resp.bytes_stream();
        let mut file = File::create(dest_path).await?;
        let mut hasher = Sha256::new();
        let mut downloaded: u64 = 0;

        while let Some(chunk_result) = stream.next().await {
            let chunk = chunk_result.context("Erreur de lecture du flux réseau")?;
            hasher.update(&chunk);
            file.write_all(&chunk).await?;
            downloaded += chunk.len() as u64;
        }

        file.flush().await?;

        // Validation cryptographique
        let computed_hash = format!("{:x}", hasher.finalize());
        if !expected_sha256.is_empty() {
            if !computed_hash.eq_ignore_ascii_case(expected_sha256) {
                fs::remove_file(dest_path).await.ok();
                bail!(
                    "Échec d'intégrité pour {} !\nAttendu: {}\nObtenu:  {}",
                    label,
                    expected_sha256,
                    computed_hash
                );
            }
            println!(
                "{} Intégrité SHA-256 vérifiée avec succès ({:.2} Mo)",
                "🔒".green(),
                downloaded as f64 / (1024.0 * 1024.0)
            );
        } else {
            let size_mb = downloaded as f64 / (1024.0 * 1024.0);
            println!(
                "{} Fichier reçu avec succès ({:.2} Mo) [Hash: {}...]",
                "✅".green(),
                size_mb,
                &computed_hash[..8]
            );
        }

        Ok(())
    }

    /// Exécute l'installation complète à partir du manifest
    pub async fn install(&self, manifest: &ServerManifest) -> Result<()> {
        println!(
            "{}",
            format!(
                "🪐 Début de l'installation de l'instance '{}' (ID: {})",
                manifest.name, manifest.server_id
            )
            .bold()
            .cyan()
        );

        fs::create_dir_all(&self.instance_dir).await?;

        // Sécurité anti-traversal (CWE-22)
        if manifest.core.target_jar.contains("..") || manifest.core.target_jar.starts_with('/') || manifest.core.target_jar.starts_with('\\') {
            bail!("Nom de fichier cible illégal pour target_jar : {}", manifest.core.target_jar);
        }

        // 1. Téléchargement du Core Server Jar (Paper, Purpur, etc.)
        let core_jar_path = self.instance_dir.join(&manifest.core.target_jar);
        self.download_file(
            &manifest.core.download_url,
            &core_jar_path,
            &manifest.core.sha256,
            &format!("Core {} ({})", manifest.core.r#type, manifest.core.target_jar),
        )
        .await?;

        // 2. Téléchargement des plugins / mods
        for artifact in &manifest.plugins_and_mods {
            if artifact.name.contains("..")
                || artifact.target_dir.contains("..")
                || artifact.target_dir.starts_with('/')
                || artifact.target_dir.starts_with('\\')
                || artifact.name.starts_with('/')
                || artifact.name.starts_with('\\')
                || artifact.target_dir.contains(':')
                || artifact.name.contains(':')
            {
                bail!(
                    "Chemin d'artéfact interdit (traversal CWE-22) : {} / {}",
                    artifact.target_dir,
                    artifact.name
                );
            }
            let target_path = self
                .instance_dir
                .join(&artifact.target_dir)
                .join(&artifact.name);
            self.download_file(
                &artifact.download_url,
                &target_path,
                &artifact.sha256,
                &format!("Plugin/Mod {}", artifact.name),
            )
            .await?;
        }

        // 3. Écriture des fichiers de configuration
        for (rel_path, content) in &manifest.configs {
            if rel_path.contains("..") || rel_path.starts_with('/') || rel_path.starts_with('\\') {
                bail!("Chemin de configuration interdit (traversal CWE-22) : {}", rel_path);
            }
            let config_path = self.instance_dir.join(rel_path);
            if let Some(parent) = config_path.parent() {
                fs::create_dir_all(parent).await?;
            }
            fs::write(&config_path, content).await?;
            println!("📝 Configuration écrite : {}", rel_path.yellow());
        }

        // 4. Sauvegarde du manifest pour référence future du runner
        let manifest_dest = self.instance_dir.join(".aether-manifest.json");
        let serialized = serde_json::to_string_pretty(manifest)?;
        fs::write(&manifest_dest, serialized).await?;

        println!(
            "{}",
            format!("🎉 Installation de '{}' terminée avec succès dans : {}", manifest.name, self.instance_dir.display())
                .bold()
                .green()
        );

        Ok(())
    }
}
