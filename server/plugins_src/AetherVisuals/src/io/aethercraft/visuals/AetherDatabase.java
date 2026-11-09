package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.logging.Level;

/**
 * Gestionnaire centralisé et résilient de la base de données SQLite partagée.
 * Résout automatiquement et proprement le chemin de aethercraft.db
 * quel que soit le point de départ du serveur (dossier server/, racine du projet, etc.).
 */
public class AetherDatabase {

    private static File resolvedDbFile = null;

    /**
     * Localise de façon robuste le fichier aethercraft.db.
     * Crée le dossier parent si nécessaire pour éviter toute SQLException.
     */
    public static synchronized File getDatabaseFile() {
        if (resolvedDbFile != null && resolvedDbFile.exists() && resolvedDbFile.length() > 0) {
            return resolvedDbFile;
        }

        // 1. Vérification d'une variable d'environnement explicite si fournie
        String envPath = System.getenv("AETHER_DB_PATH");
        if (envPath != null && !envPath.trim().isEmpty()) {
            File f = new File(envPath);
            if (f.exists() && f.length() > 0) {
                resolvedDbFile = f.getAbsoluteFile();
                return resolvedDbFile;
            }
        }

        // 2. Liste ordonnée de chemins relatifs candidats
        File[] candidates = new File[] {
            new File("data/aethercraft.db"),                 // Cas nominal: working dir = server/
            new File("server/data/aethercraft.db"),          // Cas nominal: working dir = racine
            new File("../server/data/aethercraft.db"),       // Cas nominal: working dir = sous-dossier
            new File("data/aethercraft.db.bak")
        };

        for (File candidate : candidates) {
            if (candidate.exists() && candidate.isFile() && candidate.length() > 0) {
                resolvedDbFile = candidate.getAbsoluteFile();
                return resolvedDbFile;
            }
        }

        // 3. Si aucun fichier existant n'est trouvé, créer proprement l'emplacement standard
        File defaultFile = new File("data/aethercraft.db");
        if (!defaultFile.exists()) {
            // Si on est à la racine, préférer server/data/aethercraft.db
            File serverDir = new File("server");
            if (serverDir.exists() && serverDir.isDirectory()) {
                defaultFile = new File("server/data/aethercraft.db");
            }
        }

        File parent = defaultFile.getParentFile();
        if (parent != null && !parent.exists()) {
            parent.mkdirs();
        }

        resolvedDbFile = defaultFile.getAbsoluteFile();
        return resolvedDbFile;
    }

    /**
     * Ouvre une connexion JDBC SQLite vers la base de données avec chemin normalisé.
     * Utilise des slashes '/' pour éviter les erreurs d'encodage de chemins Windows (\Users -> \U).
     */
    public static Connection getConnection() throws SQLException {
        File file = getDatabaseFile();
        File parent = file.getParentFile();
        if (parent != null && !parent.exists()) {
            parent.mkdirs();
        }
        String normalizedPath = file.getAbsolutePath().replace('\\', '/');
        String url = "jdbc:sqlite:" + normalizedPath;
        return DriverManager.getConnection(url);
    }

    /**
     * Vérifie si un joueur s'est inscrit sur le site web (table users ou players).
     * Permet à l'auto-whitelist d'autoriser immédiatement les joueurs inscrits.
     */
    public static boolean isPlayerRegistered(String username) {
        if (username == null || username.trim().isEmpty()) return false;
        String trimmed = username.trim();

        // 1. Vérification dans la table des utilisateurs web
        String sqlUsers = "SELECT 1 FROM users WHERE LOWER(minecraft_username) = LOWER(?) LIMIT 1";
        try (Connection conn = getConnection();
             java.sql.PreparedStatement ps = conn.prepareStatement(sqlUsers)) {
            ps.setString(1, trimmed);
            try (java.sql.ResultSet rs = ps.executeQuery()) {
                if (rs.next()) return true;
            }
        } catch (SQLException ignored) {}

        // 2. Vérification dans la table des joueurs synchronisés
        String sqlPlayers = "SELECT 1 FROM players WHERE LOWER(username) = LOWER(?) LIMIT 1";
        try (Connection conn = getConnection();
             java.sql.PreparedStatement ps = conn.prepareStatement(sqlPlayers)) {
            ps.setString(1, trimmed);
            try (java.sql.ResultSet rs = ps.executeQuery()) {
                return rs.next();
            }
        } catch (SQLException ignored) {}

        return false;
    }
}
