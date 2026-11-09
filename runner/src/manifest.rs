use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerManifest {
    #[serde(default = "default_version")]
    pub version: String,
    pub server_id: String,
    pub name: String,
    pub runtime: RuntimeConfig,
    pub core: CoreConfig,
    #[serde(default)]
    pub plugins_and_mods: Vec<ArtifactConfig>,
    #[serde(default)]
    pub configs: HashMap<String, String>,
}

fn default_version() -> String {
    "1.0".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuntimeConfig {
    pub java_major_version: u32,
    #[serde(default = "default_vendor")]
    pub vendor: String,
    #[serde(default = "default_heap")]
    pub heap_min: String,
    #[serde(default = "default_heap")]
    pub heap_max: String,
    #[serde(default)]
    pub jvm_flags: Vec<String>,
}

fn default_vendor() -> String {
    "adoptium".to_string()
}

fn default_heap() -> String {
    "4G".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoreConfig {
    pub r#type: String,
    pub mc_version: String,
    #[serde(default)]
    pub build: u64,
    #[serde(default = "default_target_jar")]
    pub target_jar: String,
    pub download_url: String,
    #[serde(default)]
    pub sha256: String,
}

fn default_target_jar() -> String {
    "server.jar".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactConfig {
    pub name: String,
    pub target_dir: String,
    pub download_url: String,
    #[serde(default)]
    pub sha256: String,
}

impl ServerManifest {
    /// Charge un manifest soit depuis un chemin de fichier local, soit depuis une URL HTTP(S)
    pub async fn load(source: &str) -> Result<Self> {
        if source.starts_with("http://") || source.starts_with("https://") {
            let client = reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(10))
                .build()?;
            let resp = client
                .get(source)
                .send()
                .await
                .context(format!("Impossible de contacter le serveur manifest: {source}"))?
                .error_for_status()
                .context("Le serveur de manifest a retourné une erreur HTTP")?;
            let text = resp.text().await?;
            let manifest: Self = serde_json::from_str(&text)
                .context("Erreur de parsing JSON du manifest distant")?;
            Ok(manifest)
        } else {
            let path = Path::new(source);
            let raw = tokio::fs::read_to_string(path)
                .await
                .context(format!("Impossible de lire le fichier manifest local: {source}"))?;
            let manifest: Self = serde_json::from_str(&raw)
                .context("Erreur de parsing JSON du manifest local")?;
            Ok(manifest)
        }
    }
}
