package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;

public class AetherCommandExecutor implements CommandExecutor {

    private final AetherVisualsPlugin plugin;
    private final CosmeticsEngine cosmeticsEngine;
    private final BoosterEngine boosterEngine;
    private final CrateEngine crateEngine;
    private final AetherMenuGUI menuGUI;
    private final AetherMarketGUI marketGUI;
    private final AetherOresGUI oresGUI;
    private AetherShopGUI shopGUI;
    private PortalTeleportEngine portalEngine;
    private AetherMMOInterfaceEngine mmoEngine;
    private AetherHoloUIEngine holoEngine;
    private DungeonWaveEngine dungeonWaveEngine;
    private RandomSpawnEngine randomSpawnEngine;
    private AetherWebDisplayManager webDisplayManager;
    private AetherVisualScoreboardManager scoreboardManager;

    public AetherCommandExecutor(AetherVisualsPlugin plugin, CosmeticsEngine cosmeticsEngine, BoosterEngine boosterEngine, CrateEngine crateEngine, AetherMenuGUI menuGUI, AetherMarketGUI marketGUI, AetherOresGUI oresGUI) {
        this.plugin = plugin;
        this.cosmeticsEngine = cosmeticsEngine;
        this.boosterEngine = boosterEngine;
        this.crateEngine = crateEngine;
        this.menuGUI = menuGUI;
        this.marketGUI = marketGUI;
        this.oresGUI = oresGUI;
    }

    public void setShopGUI(AetherShopGUI g) { this.shopGUI = g; }
    public void setPortalEngine(PortalTeleportEngine e) { this.portalEngine = e; }
    public void setMmoEngine(AetherMMOInterfaceEngine e) { this.mmoEngine = e; }
    public void setHoloEngine(AetherHoloUIEngine e) { this.holoEngine = e; }
    public void setDungeonWaveEngine(DungeonWaveEngine e) { this.dungeonWaveEngine = e; }
    public void setRandomSpawnEngine(RandomSpawnEngine e) { this.randomSpawnEngine = e; }
    public void setWebDisplayManager(AetherWebDisplayManager m) { this.webDisplayManager = m; }
    public void setScoreboardManager(AetherVisualScoreboardManager m) { this.scoreboardManager = m; }

    private boolean checkAdmin(CommandSender sender) { return AetherAdminCommandHelper.checkAdmin(sender); }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        return switch (command.getName().toLowerCase()) {
            case "cosmetics" -> AetherAdminCommandHelper.handleCosmetics(sender, args, cosmeticsEngine);
            case "pet" -> AetherAdminCommandHelper.handlePet(sender, args, cosmeticsEngine);
            case "aura" -> AetherAdminCommandHelper.handleAura(sender, args, cosmeticsEngine);
            case "booster" -> AetherAdminCommandHelper.handleBooster(sender, args, boosterEngine);
            case "crate" -> AetherAdminCommandHelper.handleCrate(sender, args, crateEngine);
            case "store" -> handleStore(sender, args);
            case "shop", "boutique", "magasin" -> handleShop(sender, args);
            case "spawn", "agora" -> handleSpawn(sender);
            case "survie", "survival", "regensurvie" -> handleSurvie(sender, args);
            case "back", "retour" -> handleBack(sender);
            case "rtp", "wild", "aleatoire" -> handleRtp(sender);
            case "dungeon", "dungeons", "donjon" -> handleDungeon(sender, args);
            case "oneblock", "ob", "island", "ile" -> handleOneBlock(sender, args);
            case "buildspawn" -> AetherAdminCommandHelper.handleBuildSpawn(sender);
            case "aethertest" -> AetherAdminCommandHelper.handleAetherTest(sender, cosmeticsEngine, boosterEngine);
            case "menu", "aether", "hub" -> handleMenu(sender, args);
            case "phone", "tel", "smartphone", "iphone", "aetherphone" -> handleMenu(sender, args);
            case "profil" -> handleMenu(sender, new String[]{"profil"});
            case "bourse" -> handleMarket(sender, new String[]{"bourse"});
            case "marche", "ah", "market" -> handleMarket(sender, args);
            case "banque", "bank", "vault" -> handleBank(sender);
            case "webdisplay", "ecran", "screen", "webshop" -> handleWebDisplay(sender, args);
            case "top", "baltop", "classement", "classements" -> handleTop(sender, command.getName().toLowerCase(), args);
            default -> false;
        };
    }

    private boolean handleTop(CommandSender sender, String cmdName, String[] args) {
        String sub = (args != null && args.length > 0) ? args[0].toLowerCase() : "";
        if ("baltop".equals(cmdName) || "fortune".equals(sub) || "money".equals(sub) || "solde".equals(sub) || "coins".equals(sub) || sub.isEmpty()) {
            displayLeaderboard(sender, "Fortune (Solde ⛃)", "fortune");
        } else if ("temps".equals(sub) || "playtime".equals(sub) || "heures".equals(sub) || "hours".equals(sub) || "time".equals(sub)) {
            displayLeaderboard(sender, "Temps de Jeu (Heures)", "playtime");
        } else if ("kills".equals(sub) || "pvp".equals(sub) || "frags".equals(sub) || "combat".equals(sub)) {
            displayLeaderboard(sender, "Frags / Kills", "kills");
        } else {
            sender.sendMessage(ChatColor.GOLD + "✦ " + ChatColor.YELLOW + "Classements AetherCraft :");
            sender.sendMessage(ChatColor.AQUA + "  ➤ /top fortune " + ChatColor.GRAY + "- Top 5 joueurs les plus riches");
            sender.sendMessage(ChatColor.AQUA + "  ➤ /top temps " + ChatColor.GRAY + "- Top 5 joueurs par temps de jeu");
            sender.sendMessage(ChatColor.AQUA + "  ➤ /top kills " + ChatColor.GRAY + "- Top 5 joueurs par frags PvP/PvE");
        }
        return true;
    }

    private void displayLeaderboard(CommandSender sender, String title, String category) {
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            java.util.List<AetherVisualScoreboardManager.LeaderboardEntry> list;
            String unit;
            if ("playtime".equals(category)) {
                list = AetherVisualScoreboardManager.getTopPlaytime(5);
                unit = "h de jeu";
            } else if ("kills".equals(category)) {
                list = AetherVisualScoreboardManager.getTopKills(5);
                unit = "frags";
            } else {
                list = AetherVisualScoreboardManager.getTopFortune(5);
                unit = "⛃";
            }

            Bukkit.getScheduler().runTask(plugin, () -> {
                sender.sendMessage(ChatColor.GOLD + "✦ " + ChatColor.BOLD + "CLASSEMENT — TOP " + title.toUpperCase() + ChatColor.GOLD + " ✦");
                if (list.isEmpty()) {
                    sender.sendMessage(ChatColor.GRAY + "  Aucun joueur classé pour le moment.");
                } else {
                    for (int i = 0; i < list.size(); i++) {
                        AetherVisualScoreboardManager.LeaderboardEntry e = list.get(i);
                        String medal = switch (i) {
                            case 0 -> ChatColor.YELLOW + "" + ChatColor.BOLD + "#1 ";
                            case 1 -> ChatColor.WHITE + "" + ChatColor.BOLD + "#2 ";
                            case 2 -> ChatColor.GOLD + "" + ChatColor.BOLD + "#3 ";
                            default -> ChatColor.GRAY + "#" + (i + 1) + " ";
                        };
                        String valStr;
                        if ("playtime".equals(category) || "kills".equals(category)) {
                            valStr = ((int) e.value) + " " + unit;
                        } else {
                            long balInt = Math.round(e.value);
                            valStr = ((e.value == balInt) ? String.valueOf(balInt) : String.format("%.2f", e.value)) + " " + unit;
                        }
                        sender.sendMessage(medal + e.getFormattedPrefix() + " " + ChatColor.WHITE + e.username + ChatColor.DARK_GRAY + " » " + ChatColor.GOLD + valStr);
                    }
                }
                sender.sendMessage(ChatColor.GOLD + "✦ --------------------------------- ✦");
            });
        });
    }

    private boolean handleBank(CommandSender sender) {
        if (!(sender instanceof Player p)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut ouvrir sa banque privée.");
            return true;
        }
        if (plugin.getBankEngine() != null) plugin.getBankEngine().openBank(p);
        return true;
    }

    private boolean handleShop(CommandSender sender, String[] args) {
        if (!(sender instanceof Player p)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut ouvrir la boutique.");
            return true;
        }
        if (args != null && args.length > 0 && ("clear".equalsIgnoreCase(args[0]) || "purge".equalsIgnoreCase(args[0]))) {
            if (webDisplayManager != null) webDisplayManager.closeWebDisplay(p, true);
            AetherHoloUIEngine.purgeAllWebDisplayEntities();
            p.sendMessage(ChatColor.GREEN + "✦ [WebDisplay] Tous les écrans et mobiliers éphémères ont été purgés.");
            return true;
        }
        if (args != null && args.length > 0 && ("web".equalsIgnoreCase(args[0]) || "uhd".equalsIgnoreCase(args[0]) || "html".equalsIgnoreCase(args[0]))) {
            return handleWebDisplay(sender, new String[]{"shop"});
        }
        String cat = (args != null && args.length > 0) ? args[0].toLowerCase() : "all";
        if (holoEngine != null) {
            holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.SHOP, cat);
            if (webDisplayManager != null) webDisplayManager.sendWebDisplayNotice(p, "shop");
            return true;
        }
        p.sendMessage(ChatColor.GOLD + "✦ Boutique AetherCraft : " + ChatColor.AQUA + "http://127.0.0.1:5000/boutique");
        return true;
    }

    private boolean handleWebDisplay(CommandSender sender, String[] args) {
        if (!(sender instanceof Player p)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut déployer l'écran WebDisplay UHD.");
            return true;
        }
        if (args != null && args.length > 0 && ("clear".equalsIgnoreCase(args[0]) || "close".equalsIgnoreCase(args[0]))) {
            if (webDisplayManager != null) webDisplayManager.closeWebDisplay(p, true);
            return true;
        }
        String mode = (args != null && args.length > 0) ? args[0] : "shop";
        if (webDisplayManager != null) {
            webDisplayManager.openOrToggleWebDisplay(p, mode);
        }
        return true;
    }

    private boolean handleRtp(CommandSender sender) {
        if (!(sender instanceof Player p)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut exécuter le rituel RTP.");
            return true;
        }
        if (randomSpawnEngine != null) randomSpawnEngine.startRtpRitual(p);
        return true;
    }

    private boolean handleDungeon(CommandSender sender, String[] args) {
        if (!(sender instanceof Player p)) { sender.sendMessage(ChatColor.RED + "Seul un joueur peut entrer dans le donjon."); return true; }
        if (args != null && args.length > 0) {
            String sub = args[0].toLowerCase();
            if (sub.equals("leave") || sub.equals("quit") || sub.equals("quitter")) {
                if (dungeonWaveEngine != null) dungeonWaveEngine.leaveDungeon(p);
                return true;
            }
            if (sub.equals("reset") && checkAdmin(sender) && dungeonWaveEngine != null) {
                dungeonWaveEngine.resetDungeon();
                sender.sendMessage(ChatColor.GREEN + "✦ Donjon réinitialisé avec succès !");
                return true;
            }
            if (sub.equals("build") && checkAdmin(sender) && dungeonWaveEngine != null) {
                dungeonWaveEngine.buildArena(p.getWorld());
                sender.sendMessage(ChatColor.GREEN + "✦ Arène Céleste du Donjon rebâtie à (" + DungeonWaveEngine.ARENA_X + ", " + DungeonWaveEngine.ARENA_Y + ", " + DungeonWaveEngine.ARENA_Z + ") !");
                return true;
            }
        }
        if (plugin.getSpawnProtectionEngine() != null && plugin.getSpawnProtectionEngine().isProtectedZone(p.getLocation())) {
            p.sendMessage(ChatColor.RED + "⚔️ Impossible de lancer /donjon depuis le spawn d'arrivée ! Éloignez-vous de la zone protégée.");
            p.playSound(p.getLocation(), org.bukkit.Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
            return true;
        }
        if (dungeonWaveEngine != null) dungeonWaveEngine.joinDungeon(p);
        return true;
    }

    private boolean handleOneBlock(CommandSender sender, String[] args) {
        if (plugin.getOneBlockEngine() != null) {
            return plugin.getOneBlockEngine().onCommand(sender, null, "oneblock", args);
        }
        sender.sendMessage(ChatColor.RED + "Moteur OneBlock indisponible.");
        return true;
    }

    private boolean handleSpawn(CommandSender sender) {
        if (!(sender instanceof Player p)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut se téléporter au spawn.");
            return true;
        }
        if (dungeonWaveEngine != null && dungeonWaveEngine.isInDungeon(p)) {
            dungeonWaveEngine.ejectPlayerToSpawn(p);
        }
        if (portalEngine != null) {
            portalEngine.teleportToHub(p);
        } else {
            org.bukkit.World mainWorld = org.bukkit.Bukkit.getWorld("world");
            if (mainWorld == null && !org.bukkit.Bukkit.getWorlds().isEmpty()) mainWorld = org.bukkit.Bukkit.getWorlds().get(0);
            org.bukkit.Location agoraLoc = new org.bukkit.Location(mainWorld, 0.5, 121.0, 1.5, 0f, 0f);
            p.teleport(agoraLoc);
            p.playSound(agoraLoc, org.bukkit.Sound.BLOCK_PORTAL_TRAVEL, 0.6f, 1.5f);
            p.sendTitle(ChatColor.AQUA + "🪐 Agora", ChatColor.GRAY + "Archipel Céleste", 5, 25, 10);
        }
        p.sendMessage(ChatColor.GOLD + "🪐 Téléporté à l'Agora Céleste !");
        return true;
    }

    private boolean handleSurvie(CommandSender sender, String[] args) {
        if (!(sender instanceof Player p)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut se téléporter en survie.");
            return true;
        }
        boolean forceSpawn = false;
        if (args != null && args.length >= 1) {
            if (args[0].equalsIgnoreCase("reset") || args[0].equalsIgnoreCase("clear")) {
                if (plugin.getPlayerLocationEngine() != null) {
                    plugin.getPlayerLocationEngine().deleteSurvivalLocationAsync(p.getUniqueId());
                    p.sendMessage(ChatColor.YELLOW + "✦ Votre position de reprise en survie a été réinitialisée.");
                }
                forceSpawn = true;
            } else if (args[0].equalsIgnoreCase("regen") || args[0].equalsIgnoreCase("build")) {
                if (checkAdmin(sender)) {
                    CelestialSpawnBuilder.buildSurvivalSpawn(p.getWorld(), PortalTeleportEngine.PORTAL2_X, PortalTeleportEngine.PORTAL2_Z);
                    p.sendMessage(ChatColor.GREEN + "✦ Esplanade du Spawn Survie & Portail régénérés sur terre ferme à (640, 864) !");
                }
            } else if (args[0].equalsIgnoreCase("spawn") || args[0].equalsIgnoreCase("hub") || args[0].equalsIgnoreCase("esplanade")) {
                forceSpawn = true;
            }
        }
        if (portalEngine != null) portalEngine.teleportToSurvival(p, forceSpawn);
        else p.sendMessage(ChatColor.GREEN + "Téléportation au monde survie...");
        return true;
    }

    private boolean handleBack(CommandSender sender) {
        if (!(sender instanceof Player)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut exécuter la commande /back.");
            return true;
        }
        if (plugin.getPlayerLocationEngine() != null) {
            return plugin.getPlayerLocationEngine().onCommand(sender, null, "back", new String[0]);
        }
        return true;
    }

    private boolean handleMarket(CommandSender sender, String[] args) {
        if (!(sender instanceof Player p)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut utiliser le marché.");
            return true;
        }
        if (args.length >= 2 && (args[0].equalsIgnoreCase("sell") || args[0].equalsIgnoreCase("vendre"))) {
            try {
                double price = Double.parseDouble(args[1]);
                if (holoEngine != null) {
                    AetherHoloTransactions.TxResult res = holoEngine.getTxService().sellHeldItem(p, price);
                    p.sendMessage(res.message);
                    holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.MARKET, null);
                    return true;
                }
            } catch (NumberFormatException e) {
                p.sendMessage(ChatColor.RED + "Usage : /marche sell <prix_en_coins>");
                return true;
            }
        }
        if (args.length >= 1 && (args[0].equalsIgnoreCase("ores") || args[0].equalsIgnoreCase("bourse") || args[0].equalsIgnoreCase("minerais"))) {
            if (holoEngine != null) holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.ORES, null);
            return true;
        }
        if (holoEngine != null) holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.MARKET, null);
        return true;
    }

    private boolean handleMenu(CommandSender sender, String[] args) {
        if (!(sender instanceof Player p)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut ouvrir le menu Aether.");
            return true;
        }
        if (args != null && args.length > 0 && ("web".equalsIgnoreCase(args[0]) || "uhd".equalsIgnoreCase(args[0]) || "html".equalsIgnoreCase(args[0]))) {
            if (webDisplayManager != null) webDisplayManager.openOrToggleWebDisplay(p, "cockpit");
            return true;
        }
        if (holoEngine != null) {
            if (args != null && args.length > 0) {
                String sub = args[0].toLowerCase();
                if (sub.contains("prof") || sub.contains("ach")) { holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.PROFILE, "achievements"); return true; }
                if (sub.contains("quet") || sub.contains("quest")) { holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.PROFILE, "quests"); return true; }
                if (sub.contains("shop") || sub.contains("bout")) { holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.SHOP, "all"); return true; }
                if (sub.contains("hdv") || sub.contains("ah") || sub.contains("marche")) { holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.MARKET, null); return true; }
                if (sub.contains("bourse") || sub.contains("ore")) { holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.ORES, null); return true; }
                if (sub.contains("top") || sub.contains("class") || sub.contains("rank")) { holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.LEADERBOARD, null); return true; }
                if (sub.contains("pet") || sub.contains("anim")) { holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.PETS, null); return true; }
            }
            holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.COCKPIT, null);
        }
        if (webDisplayManager != null) webDisplayManager.sendWebDisplayNotice(p, "cockpit");
        return true;
    }

    private boolean handleStore(CommandSender sender, String[] args) {
        if (args.length == 0 || !(sender.isOp() || sender.hasPermission("aether.admin"))) {
            return handleShop(sender, args);
        }
        if (!checkAdmin(sender)) return true;
        if (args.length >= 3 && args[0].equalsIgnoreCase("give")) {
            Player target = Bukkit.getPlayer(args[1]);
            String itemId = args[2].toLowerCase();
            int amount = 1;
            if (args.length >= 4) {
                try { amount = Integer.parseInt(args[3]); } catch (Exception ignored) {}
            }
            ItemStack item = CustomItemFactory.createItemById(itemId, amount);
            if (target == null) {
                plugin.addPendingDelivery(args[1], item);
                sender.sendMessage(ChatColor.YELLOW + "Joueur " + args[1] + " hors-ligne : item '" + itemId + "' en file d'attente !");
                return true;
            }
            target.getInventory().addItem(item);
            target.sendMessage(ChatColor.GOLD + "🛍️ Reçu l'article boutique : " + item.getItemMeta().getDisplayName());
            sender.sendMessage(ChatColor.GREEN + "Item '" + itemId + "' (x" + amount + ") donné à " + target.getName() + " !");
            return true;
        }
        sender.sendMessage(ChatColor.GOLD + "Usage: /store give <joueur> <item_id> [quantité]");
        return true;
    }
}
