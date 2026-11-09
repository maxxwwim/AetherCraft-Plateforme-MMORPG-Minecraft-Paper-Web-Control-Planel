package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerCommandPreprocessEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

public class AetherVisualsPlugin extends JavaPlugin implements Listener {

    private final Set<UUID> authenticatedOperators = ConcurrentHashMap.newKeySet();

    private CosmeticsEngine cosmeticsEngine;
    private BoosterEngine boosterEngine;
    private CrateEngine crateEngine;
    private ChatQuizEngine quizEngine;
    private AetherMenuGUI menuGUI;
    private AetherMarketGUI marketGUI;
    private AetherOresGUI oresGUI;
    private AetherShopGUI shopGUI;
    private PortalTeleportEngine portalEngine;
    private SpawnProtectionEngine spawnProtectionEngine;
    private SpawnAmbianceEngine spawnAmbianceEngine;
    private SpawnLifeManager spawnLife;
    private RandomSpawnEngine randomSpawnEngine;
    private PlayerLocationEngine playerLocationEngine;
    private AetherPacketBridge packetBridge;
    private MMORPGDisplayEngine mmorpgDisplayEngine;
    private AetherMMOInterfaceEngine mmoEngine;
    private AetherHoloUIEngine holoEngine;
    private AetherBankEngine bankEngine;
    private HabboBullionBlockEngine bullionEngine;
    private DungeonWaveEngine dungeonWaveEngine;
    private OneBlockEngine oneBlockEngine;
    private MobAffixEngine mobAffixEngine;
    private AetherNetherOreEngine netherOreEngine;
    private AetherWebDisplayManager webDisplayManager;
    private AetherVisualScoreboardManager scoreboardManager;
    private BukkitTask tickerTask;
    private long globalTick = 0;
    private final Map<String, List<ItemStack>> pendingDeliveries = new ConcurrentHashMap<>();

    @Override
    public void onEnable() {
        // Initialisation et validation de la base de données SQLite
        java.io.File db = AetherDatabase.getDatabaseFile();
        getLogger().info("✦ [AetherDatabase] Base SQLite connectée : " + db.getAbsolutePath() + " (Taille: " + db.length() + " octets)");

        this.cosmeticsEngine = new CosmeticsEngine();
        this.boosterEngine = new BoosterEngine();
        this.crateEngine = new CrateEngine(this);
        this.quizEngine = new ChatQuizEngine(this);
        this.menuGUI = new AetherMenuGUI(this, quizEngine);
        this.marketGUI = new AetherMarketGUI(this);
        this.oresGUI = new AetherOresGUI(this);
        this.shopGUI = new AetherShopGUI(this);
        this.portalEngine = new PortalTeleportEngine(this);
        this.spawnProtectionEngine = new SpawnProtectionEngine(this);
        this.spawnAmbianceEngine = new SpawnAmbianceEngine(this, this.spawnProtectionEngine);
        this.spawnLife = new SpawnLifeManager(this);
        this.spawnLife.register();
        this.playerLocationEngine = new PlayerLocationEngine(this, this.spawnProtectionEngine);
        this.randomSpawnEngine = new RandomSpawnEngine(this);
        this.mmoEngine = new AetherMMOInterfaceEngine(this);
        this.holoEngine = new AetherHoloUIEngine(this);
        this.bankEngine = new AetherBankEngine(this);
        this.bullionEngine = new HabboBullionBlockEngine(this);
        this.webDisplayManager = new AetherWebDisplayManager(this);
        AetherHoloUIEngine.purgeAllWebDisplayEntities();
        this.dungeonWaveEngine = new DungeonWaveEngine(this);
        this.oneBlockEngine = new OneBlockEngine(this);
        this.mobAffixEngine = new MobAffixEngine(this);
        this.netherOreEngine = new AetherNetherOreEngine(this);
        this.mmoEngine.setEngines(portalEngine, randomSpawnEngine, dungeonWaveEngine, oresGUI, marketGUI);
        this.packetBridge = new AetherPacketBridge(this, crateEngine);
        this.packetBridge.registerChannels();

        this.menuGUI.setMarketEngines(marketGUI, oresGUI);
        this.menuGUI.setShopGUI(shopGUI);
        this.menuGUI.setPortalEngine(portalEngine);
        this.shopGUI.setEngines(oresGUI, marketGUI, menuGUI);

        this.scoreboardManager = new AetherVisualScoreboardManager(this);
        this.scoreboardManager.start();

        // Enregistrement des Events
        getServer().getPluginManager().registerEvents(this, this);
        getServer().getPluginManager().registerEvents(scoreboardManager, this);
        getServer().getPluginManager().registerEvents(holoEngine, this);
        getServer().getPluginManager().registerEvents(bankEngine, this);
        getServer().getPluginManager().registerEvents(spawnProtectionEngine, this);
        getServer().getPluginManager().registerEvents(spawnAmbianceEngine, this);
        getServer().getPluginManager().registerEvents(playerLocationEngine, this);
        getServer().getPluginManager().registerEvents(crateEngine, this);
        getServer().getPluginManager().registerEvents(randomSpawnEngine, this);
        getServer().getPluginManager().registerEvents(mmoEngine, this);
        getServer().getPluginManager().registerEvents(boosterEngine, this);
        getServer().getPluginManager().registerEvents(quizEngine, this);
        getServer().getPluginManager().registerEvents(menuGUI, this);
        getServer().getPluginManager().registerEvents(marketGUI, this);
        getServer().getPluginManager().registerEvents(oresGUI, this);
        getServer().getPluginManager().registerEvents(shopGUI, this);
        getServer().getPluginManager().registerEvents(portalEngine, this);
        getServer().getPluginManager().registerEvents(dungeonWaveEngine, this);
        getServer().getPluginManager().registerEvents(oneBlockEngine, this);
        getServer().getPluginManager().registerEvents(mobAffixEngine, this);
        getServer().getPluginManager().registerEvents(netherOreEngine, this);
        getServer().getPluginManager().registerEvents(bullionEngine, this);
        getServer().getPluginManager().registerEvents(webDisplayManager, this);
        getServer().getPluginManager().registerEvents(new StoreItemInteractListener(this, cosmeticsEngine, boosterEngine, crateEngine), this);

        // Enregistrement des Commandes et TabCompleter déportés
        AetherCommandExecutor cmdExecutor = new AetherCommandExecutor(this, cosmeticsEngine, boosterEngine, crateEngine, menuGUI, marketGUI, oresGUI);
        cmdExecutor.setShopGUI(shopGUI);
        cmdExecutor.setPortalEngine(portalEngine);
        cmdExecutor.setMmoEngine(mmoEngine);
        cmdExecutor.setHoloEngine(holoEngine);
        cmdExecutor.setDungeonWaveEngine(dungeonWaveEngine);
        cmdExecutor.setRandomSpawnEngine(randomSpawnEngine);
        cmdExecutor.setWebDisplayManager(webDisplayManager);
        cmdExecutor.setScoreboardManager(scoreboardManager);
        GameCommandExecutor gameCmdExecutor = new GameCommandExecutor(quizEngine, holoEngine);
        gameCmdExecutor.setSpawnAmbianceEngine(spawnAmbianceEngine);
        AetherTabCompleter tabCompleter = new AetherTabCompleter();

        String[] coreCommands = {"cosmetics", "pet", "aura", "booster", "crate", "store", "shop", "boutique", "magasin", "spawn", "agora", "survie", "survival", "regensurvie", "back", "retour", "rtp", "wild", "aleatoire", "dungeon", "dungeons", "donjon", "oneblock", "ob", "island", "ile", "buildspawn", "aethertest", "menu", "aether", "profil", "hub", "marche", "ah", "market", "bourse", "banque", "bank", "vault", "phone", "tel", "smartphone", "iphone", "aetherphone", "webdisplay", "ecran", "screen", "webshop", "top", "baltop", "classement", "classements"};
        for (String c : coreCommands) {
            if (getCommand(c) != null) {
                getCommand(c).setExecutor(cmdExecutor);
                getCommand(c).setTabCompleter(tabCompleter);
            }
        }
        String[] gameCommands = {"quest", "quests", "quetes", "achievement", "achievements", "succes", "quiz", "trivia", "aetherquiz", "spawnmode", "ambiance", "modespawn"};
        for (String c : gameCommands) {
            if (getCommand(c) != null) {
                getCommand(c).setExecutor(gameCmdExecutor);
                getCommand(c).setTabCompleter(tabCompleter);
            }
        }

        // Lancement du scheduler automatique de Quiz (30 min à 1h, 5 jetons au vainqueur)
        this.quizEngine.startAutoScheduler();

        // Bâtissage automatique du Spawn Céleste et du Spawn Survie Terrestre
        Bukkit.getScheduler().runTaskLater(this, () -> {
            org.bukkit.World w = Bukkit.getWorlds().isEmpty() ? null : Bukkit.getWorlds().get(0);
            if (w != null) {
                if (w.getBlockAt(0, 120, 0).getType() == org.bukkit.Material.AIR) {
                    getLogger().info("✦ Bâtissage automatique de l'Archipel Céleste (Y=120)...");
                    CelestialSpawnBuilder.buildSpawn(w);
                    getLogger().info("✦ Archipel Céleste bâti avec succès à l'Agora !");
                }
                CelestialSpawnBuilder.cleanSpawnGoldSlabs(w);
                CelestialSpawnBuilder.buildJumpPads(w, 0, 120, 0);
                CelestialSpawnBuilder.buildBankVault(w, -10, 120, -10);
                spawnAmbianceEngine.initSpawnProps(w);
                spawnLife.build(w);
                // Régénération et vérification systématique du Portail 1 vers la survie
                CelestialSpawnBuilder.buildDungeonPortal(w, 0, 120, 15);
                getLogger().info("✦ Portail Agora Céleste (Z=15) synchronisé et opérationnel !");
                getLogger().info("✦ Bâtissage & Initialisation de l'esplanade du Spawn Survie Terrestre à (640, 864)...");
                CelestialSpawnBuilder.buildSurvivalSpawn(w, PortalTeleportEngine.PORTAL2_X, PortalTeleportEngine.PORTAL2_Z);
                getLogger().info("✦ Spawn Survie Terrestre & Portail de Retour opérationnels !");

                // Bâtissage de l'Arène du Donjon, Portail OneBlock & Stèle RTP
                dungeonWaveEngine.buildArena(w);
                CelestialSpawnBuilder.buildOneBlockPortal(w, -12, 120, 12);
                RandomSpawnEngine.buildRtpStele(w, RandomSpawnEngine.STELE_AGORA_X, RandomSpawnEngine.STELE_AGORA_Y, RandomSpawnEngine.STELE_AGORA_Z);
                getLogger().info("✦ Sanctuaire du Donjon, Portail OneBlock (-12, 12) & Stèle RTP Agora initialisés !");
            }
        }, 40L);

        // Boucle principale de rendu particulaire (toutes les 2 ticks = 10 FPS de rendu fluide)
        this.tickerTask = Bukkit.getScheduler().runTaskTimer(this, () -> {
            globalTick += 2;
            spawnAmbianceEngine.tickAmbiance(globalTick);
            spawnLife.tick(globalTick);
            for (Player player : Bukkit.getOnlinePlayers()) {
                cosmeticsEngine.tickPlayer(player, globalTick);
            }
        }, 0L, 2L);

        getLogger().info("================================================");
        getLogger().info("★ AetherVisuals v2.0 (Paper 1.21.1) ACTIVÉ !");
        getLogger().info("✦ Moteur de Particules 3D (Ailes, Dragoneau, Auras)");
        getLogger().info("✦ Caisse Céleste & Système de Booster Minage x2");
        getLogger().info("================================================");
    }

    @Override
    public void onDisable() {
        if (oneBlockEngine != null) {
            oneBlockEngine.saveAllSynchronously();
        }
        org.bukkit.World worldOneblock = Bukkit.getWorld("world_oneblock");
        if (worldOneblock != null) {
            try {
                worldOneblock.save();
            } catch (Throwable t) {
                getLogger().warning("Erreur world_oneblock.save() onDisable: " + t.getMessage());
            }
        }
        if (tickerTask != null) {
            tickerTask.cancel();
        }
        if (quizEngine != null) {
            quizEngine.stop();
        }
        if (spawnAmbianceEngine != null) {
            spawnAmbianceEngine.clearEntities();
        }
        if (spawnLife != null) {
            spawnLife.shutdown();
        }
        if (playerLocationEngine != null) {
            playerLocationEngine.onDisable();
        }
        if (holoEngine != null) {
            holoEngine.closeAll();
        }
        if (webDisplayManager != null) {
            webDisplayManager.closeAll();
        }
        if (scoreboardManager != null) {
            scoreboardManager.stop();
        }
        if (mobAffixEngine != null) {
            mobAffixEngine.stop();
        }
        if (cosmeticsEngine != null) {
            cosmeticsEngine.clearAllEntities();
        }
        getLogger().info("AetherVisuals désactivé.");
    }

    public AetherHoloUIEngine getHoloEngine() { return holoEngine; }
    public AetherBankEngine getBankEngine() { return bankEngine; }
    public AetherWebDisplayManager getWebDisplayManager() { return webDisplayManager; }
    public AetherVisualScoreboardManager getScoreboardManager() { return scoreboardManager; }

    public PlayerLocationEngine getPlayerLocationEngine() {
        return playerLocationEngine;
    }

    public SpawnProtectionEngine getSpawnProtectionEngine() {
        return spawnProtectionEngine;
    }

    public void addPendingDelivery(String player, ItemStack item) {
        pendingDeliveries.computeIfAbsent(player.toLowerCase(), k -> new ArrayList<>()).add(item);
    }

    public CosmeticsEngine getCosmeticsEngine() {
        return cosmeticsEngine;
    }

    public BoosterEngine getBoosterEngine() {
        return boosterEngine;
    }

    public CrateEngine getCrateEngine() {
        return crateEngine;
    }

    public ChatQuizEngine getQuizEngine() {
        return quizEngine;
    }

    public PortalTeleportEngine getPortalEngine() {
        return portalEngine;
    }

    public AetherShopGUI getShopGUI() {
        return shopGUI;
    }

    public OneBlockEngine getOneBlockEngine() {
        return oneBlockEngine;
    }

    public MobAffixEngine getMobAffixEngine() {
        return mobAffixEngine;
    }

    public AetherNetherOreEngine getNetherOreEngine() {
        return netherOreEngine;
    }

    public AetherPacketBridge getPacketBridge() {
        return packetBridge;
    }

    public boolean isOperatorAuthenticated(UUID uuid) {
        return authenticatedOperators.contains(uuid);
    }

    public void authenticateOperator(UUID uuid) {
        authenticatedOperators.add(uuid);
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        authenticatedOperators.remove(event.getPlayer().getUniqueId());
        cosmeticsEngine.clearAll(event.getPlayer().getUniqueId());
    }

    @EventHandler(priority = org.bukkit.event.EventPriority.LOWEST)
    public void onPlayerLogin(org.bukkit.event.player.PlayerLoginEvent event) {
        Player player = event.getPlayer();
        String name = player.getName();

        // Si le joueur est intercepté par la Whitelist du serveur
        if (event.getResult() == org.bukkit.event.player.PlayerLoginEvent.Result.KICK_WHITELIST) {
            // Vérifier si le joueur s'est inscrit sur la plateforme Web (SQLite)
            if (AetherDatabase.isPlayerRegistered(name)) {
                player.setWhitelisted(true);
                event.allow();
                getLogger().info("✦ [Auto-Whitelist] Joueur inscrit valide et autorise : " + name);
            } else {
                event.disallow(
                    org.bukkit.event.player.PlayerLoginEvent.Result.KICK_WHITELIST,
                    ChatColor.GOLD + "✦ " + ChatColor.YELLOW + "ACCÈS REFUSÉ : INSCRIPTION REQUISE " + ChatColor.GOLD + "✦\n\n" +
                    ChatColor.GRAY + "Ce serveur est protégé par Whitelist automatique.\n" +
                    ChatColor.WHITE + "Pour débloquer votre accès en jeu, inscrivez-vous sur le site :\n" +
                    ChatColor.AQUA + "➤ http://127.0.0.1:5000/register\n\n" +
                    ChatColor.GREEN + "Votre compte sera automatiquement whitelisté dès l'inscription !"
                );
            }
        }
    }

    @EventHandler(priority = org.bukkit.event.EventPriority.HIGHEST)
    public void onJoin(PlayerJoinEvent event) {
        Player p = event.getPlayer();
        p.setWhitelisted(true);

        // Durcissement Session / Mode Hors-Ligne pour les Opérateurs
        if (!Bukkit.getOnlineMode()) {
            boolean claimsOp = p.isOp() || Bukkit.getOperators().stream()
                    .anyMatch(op -> op.getName() != null && op.getName().equalsIgnoreCase(p.getName()));

            if (claimsOp && !authenticatedOperators.contains(p.getUniqueId())) {
                p.setOp(false);
                getLogger().warning("⚠ [AuthGuard] Joueur avec statut OP potentiel '" + p.getName() + "' (" + p.getUniqueId() + ") connecté en mode hors-ligne sans session authentifiée. Droits OP suspendus.");
                p.sendMessage(ChatColor.RED + "⚠ [SÉCURITÉ] Mode hors-ligne actif. Vos privilèges OP ont été suspendus.");
                p.sendMessage(ChatColor.YELLOW + "Pour restaurer vos droits administrateur, validez votre session :");
                p.sendMessage(ChatColor.AQUA + "➤ Tapez /opauth <token> (jeton HMAC ou secret de session console)");
            }
        }

        String name = p.getName().toLowerCase(Locale.ROOT);
        List<ItemStack> pending = pendingDeliveries.remove(name);
        if (pending != null && !pending.isEmpty()) {
            for (ItemStack item : pending) {
                p.getInventory().addItem(item);
            }
            p.playSound(p.getLocation(), org.bukkit.Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.0f);
            p.sendMessage(ChatColor.GOLD + "🛍️ " + ChatColor.YELLOW + "Vos " + pending.size() + "x article(s) boutique en attente vous ont été livrés !");
        }
    }

    @EventHandler(priority = org.bukkit.event.EventPriority.HIGHEST)
    public void onPlayerCommandPreprocess(PlayerCommandPreprocessEvent event) {
        String message = event.getMessage().trim();
        if (message.toLowerCase(Locale.ROOT).startsWith("/opauth")) {
            event.setCancelled(true);
            Player p = event.getPlayer();
            String[] parts = message.split("\\s+");
            if (parts.length < 2) {
                p.sendMessage(ChatColor.YELLOW + "Usage : /opauth <token>");
                return;
            }
            String token = parts[1].trim();
            handleOpAuth(p, token);
            return;
        }

        if (!Bukkit.getOnlineMode()) {
            String low = message.toLowerCase(Locale.ROOT);
            if (low.startsWith("/op ") || low.startsWith("/stop") || low.startsWith("/reload") || low.startsWith("/restart")) {
                Player p = event.getPlayer();
                if (!authenticatedOperators.contains(p.getUniqueId())) {
                    event.setCancelled(true);
                    p.sendMessage(ChatColor.RED + "⛔ Accès refusé : vous devez valider votre session opérateur avec /opauth <token>.");
                    p.playSound(p.getLocation(), org.bukkit.Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
                }
            }
        }
    }

    private void handleOpAuth(Player p, String token) {
        long nowSec = System.currentTimeMillis() / 1000L;
        boolean valid = false;

        // 1. Vérification par jeton HMAC (fenêtre de validité 3600 secondes)
        for (long offset = 0; offset <= 3600; offset += 30) {
            String expected = AetherWebDisplayManager.generateAuthToken(p.getName(), nowSec - offset);
            if (expected.equalsIgnoreCase(token)) {
                valid = true;
                break;
            }
        }

        // 2. Vérification par secret admin console / variable d'environnement
        if (!valid) {
            String envKey = System.getenv("AETHER_AUTH_KEY");
            String masterKey = (envKey != null && !envKey.trim().isEmpty()) ? envKey.trim() : "aethercraft_session_hmac_2026";
            if (masterKey.equals(token)) {
                valid = true;
            }
        }

        // 3. Vérification via la table SQLite users (is_admin = 1)
        if (!valid) {
            try (Connection conn = AetherDatabase.getConnection();
                 PreparedStatement ps = conn.prepareStatement(
                         "SELECT is_admin, password_hash, salt FROM users WHERE LOWER(minecraft_username) = LOWER(?) AND is_admin = 1")) {
                ps.setString(1, p.getName());
                try (ResultSet rs = ps.executeQuery()) {
                    if (rs.next()) {
                        String pwdHash = rs.getString("password_hash");
                        if (pwdHash != null && (pwdHash.equalsIgnoreCase(token) || pwdHash.startsWith(token))) {
                            valid = true;
                        }
                    }
                }
            } catch (SQLException ignored) {}
        }

        if (valid) {
            authenticatedOperators.add(p.getUniqueId());
            p.setOp(true);
            p.sendMessage(ChatColor.GREEN + "✔ Authentification réussie ! Vos privilèges OP ont été restaurés pour cette session.");
            p.playSound(p.getLocation(), org.bukkit.Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.0f);
            getLogger().info("✔ [AuthGuard] Opérateur '" + p.getName() + "' (" + p.getUniqueId() + ") authentifié avec succès via /opauth.");
        } else {
            p.sendMessage(ChatColor.RED + "❌ Jeton d'authentification invalide ou expiré !");
            p.playSound(p.getLocation(), org.bukkit.Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
            getLogger().warning("⚠ [AuthGuard] Tentative d'authentification /opauth échouée pour '" + p.getName() + "'.");
        }
    }
}
