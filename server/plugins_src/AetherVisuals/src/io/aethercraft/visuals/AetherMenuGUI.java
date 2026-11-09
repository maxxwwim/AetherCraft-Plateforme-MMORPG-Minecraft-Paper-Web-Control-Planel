package io.aethercraft.visuals;

import org.bukkit.*;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.inventory.meta.SkullMeta;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Interface Graphique In-Game (Menu GUI) stylisée Voxel Cube Émeraude & Veines de Sang Primordial.
 */
public class AetherMenuGUI implements Listener {

    public static final String MENU_TITLE = ChatColor.DARK_GRAY + "[" + ChatColor.GREEN + "" + ChatColor.BOLD + "AETHER" + ChatColor.DARK_GRAY + " • " + ChatColor.RED + "" + ChatColor.BOLD + "PRIMORDIAL" + ChatColor.DARK_GRAY + "]";

    private final AetherVisualsPlugin plugin;
    private final ChatQuizEngine quizEngine;
    private AetherMarketGUI marketGUI;
    private AetherOresGUI oresGUI;
    private PortalTeleportEngine portalEngine;
    private AetherShopGUI shopGUI;

    public AetherMenuGUI(AetherVisualsPlugin plugin, ChatQuizEngine quizEngine) {
        this.plugin = plugin;
        this.quizEngine = quizEngine;
    }

    public void setMarketEngines(AetherMarketGUI marketGUI, AetherOresGUI oresGUI) {
        this.marketGUI = marketGUI;
        this.oresGUI = oresGUI;
    }

    public void setPortalEngine(PortalTeleportEngine portalEngine) {
        this.portalEngine = portalEngine;
    }

    public void setShopGUI(AetherShopGUI shopGUI) {
        this.shopGUI = shopGUI;
    }

    public void openMenu(Player player) {
        if (plugin.getHoloEngine() != null) {
            plugin.getHoloEngine().openHoloUI(player, AetherHoloUIEngine.HoloMode.COCKPIT, null);
            return;
        }
        Inventory inv = Bukkit.createInventory(null, 54, MENU_TITLE);
        ItemStack obsidienne = createGlassPane(Material.BLACK_STAINED_GLASS_PANE, ChatColor.DARK_GRAY + "✦ Obsidienne d'Aether ✦");
        ItemStack emeraude = createGlassPane(Material.LIME_STAINED_GLASS_PANE, ChatColor.GREEN + "✦ Mousse Émeraude Primordiale ✦");
        ItemStack sang = createGlassPane(Material.RED_STAINED_GLASS_PANE, ChatColor.RED + "✦ Veine de Sang Primordial ✦");

        int[] borders = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 18, 26, 27, 35, 36, 44, 45, 46, 47, 48, 50, 51, 52, 53};
        for (int i = 0; i < borders.length; i++) {
            inv.setItem(borders[i], (i % 3 == 0) ? emeraude : (i % 3 == 1) ? sang : obsidienne);
        }

        inv.setItem(11, createMenuItem(Material.ENDER_CHEST,
                ChatColor.GOLD + "" + ChatColor.BOLD + "🤝 HÔTEL DES VENTES" + ChatColor.YELLOW + " (L'Encan d'Éther)",
                ChatColor.DARK_GRAY + "Commerce & Troc entre Joueurs", "",
                ChatColor.WHITE + "Achetez et vendez vos reliques, armes enchantées,",
                ChatColor.WHITE + "minerais sacrés et familiers en toute sécurité.", "",
                ChatColor.YELLOW + "✦ " + ChatColor.WHITE + "Annonces synchronisées en direct sur le site web",
                ChatColor.YELLOW + "✦ " + ChatColor.WHITE + "Monnaie acceptée : " + ChatColor.GOLD + "Aether Coins ⛁", "",
                ChatColor.GREEN + "▶ Clic-gauche pour ouvrir l'Hôtel des Ventes (/ah)"));

        inv.setItem(13, createMenuItem(Material.EMERALD_BLOCK,
                ChatColor.GREEN + "" + ChatColor.BOLD + "⛏️ BOURSE DES MINERAIS" + ChatColor.DARK_GREEN + " (Admin Shop)",
                ChatColor.DARK_GRAY + "Le Grand Comptoir de l'Agora Céleste", "",
                ChatColor.WHITE + "Rachat garanti 24/7 par les marchands PNJ de l'Agora.",
                ChatColor.WHITE + "Revendez vos filons de Charbon, Cuivre, Fer,",
                ChatColor.WHITE + "Diamant, Netherite et fragments d'Aetherite.", "",
                ChatColor.GREEN + "✦ " + ChatColor.WHITE + "Cours dynamique fluctuant selon l'offre et la demande",
                ChatColor.GREEN + "✦ " + ChatColor.WHITE + "Rachat instantané en " + ChatColor.GOLD + "Coins", "",
                ChatColor.GREEN + "▶ Clic-gauche pour accéder à la Bourse (/marche)"));

        inv.setItem(15, createMenuItem(Material.DRAGON_HEAD,
                ChatColor.LIGHT_PURPLE + "" + ChatColor.BOLD + "🐾 SANCTUAIRE DES COMPAGNONS",
                ChatColor.DARK_GRAY + "Faune Mystique & Auras de Guilde", "",
                ChatColor.WHITE + "Vos animaux célestes confèrent des " + ChatColor.LIGHT_PURPLE + "Auras de Groupe",
                ChatColor.WHITE + "permanentes à vous et à vos compagnons d'exploration.", "",
                ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Dragoneau d'Éther, Capybara Céleste, Phénix Doré",
                ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Rendu particulaire fluide à 10 FPS (100% sans mod)", "",
                ChatColor.GREEN + "▶ Clic-gauche pour invoquer votre familier (/pet)"));

        String quizStatus = (quizEngine != null && quizEngine.isQuestionActive())
                ? ChatColor.GREEN + "● Question active dans le chat !"
                : ChatColor.GRAY + "● Prochaine énigme dans quelques minutes...";
        inv.setItem(20, createMenuItem(Material.ENCHANTED_BOOK,
                ChatColor.YELLOW + "" + ChatColor.BOLD + "❓ LE SPHINX CÉLESTE" + ChatColor.GOLD + " (Chat Trivia Quiz)",
                ChatColor.DARK_GRAY + "Épreuves Royales & Culture Minecraft", "",
                ChatColor.WHITE + "Une énigme est posée dans le chat toutes les 30 à 60 minutes.",
                ChatColor.WHITE + "Le premier joueur à donner la bonne réponse remporte :",
                ChatColor.GOLD + "  ⭐ +5 Jetons Boutique " + ChatColor.GRAY + "(crédités en base web)", "",
                ChatColor.YELLOW + "Statut Actuel : " + quizStatus, "",
                ChatColor.GREEN + "▶ Clic-gauche pour afficher l'énigme en cours (/quiz)"));

        inv.setItem(22, createMenuItem(Material.NETHER_STAR,
                ChatColor.AQUA + "" + ChatColor.BOLD + "👑 BOUTIQUE & TRÉSORERIE CÉLESTE",
                ChatColor.DARK_GRAY + "Double Devise (€ et Jetons Play-to-Earn)", "",
                ChatColor.WHITE + "Débloquez grades, cosmétiques, clés et coffres sans payer !",
                ChatColor.WHITE + "Coffre de fidélité gratuit toutes les 30 minutes :",
                ChatColor.GOLD + "  🎁 +2 Jetons Boutique " + ChatColor.GRAY + "à chaque cycle sur le site", "",
                ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Grades VIP, Aether, Titan avec préfixes et auras",
                ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Site web : " + ChatColor.UNDERLINE + "http://127.0.0.1:5000/boutique", "",
                ChatColor.GREEN + "▶ Clic-gauche pour voir les offres (/store)"));

        inv.setItem(24, createMenuItem(Material.NETHERITE_SWORD,
                ChatColor.RED + "" + ChatColor.BOLD + "⚔️ DONJONS INSTANCIÉS",
                ChatColor.DARK_GRAY + "Expéditions & Boss de l'Archipel", "",
                ChatColor.WHITE + "Plongez dans les 3 donjons primordiaux :",
                ChatColor.RED + "  ✦ " + ChatColor.WHITE + "Sanctuaire de l'Aetherite " + ChatColor.GRAY + "(Difficulté Normale)",
                ChatColor.RED + "  ✦ " + ChatColor.WHITE + "Citadelle du Titan " + ChatColor.GRAY + "(Difficulté Épique)",
                ChatColor.RED + "  ✦ " + ChatColor.WHITE + "Faille du Dragon Ancien " + ChatColor.GRAY + "(Difficulté Mythique)", "",
                ChatColor.GREEN + "▶ Clic-gauche pour entrer en donjon (/dungeon)"));

        inv.setItem(31, createPlayerProfileHead(player));
        inv.setItem(38, createMenuItem(Material.BEACON,
                ChatColor.AQUA + "" + ChatColor.BOLD + "🪐 TÉLÉPORTATION AGORA CÉLESTE",
                ChatColor.DARK_GRAY + "Spawn de l'Archipel (Y=120)", "",
                ChatColor.WHITE + "Rejoignez instantanément la place centrale de l'Agora,",
                ChatColor.WHITE + "les caisses célestes et les comptoirs marchands.", "",
                ChatColor.AQUA + "Coordonnées : X=0, Y=121, Z=0 (Archipel)", "",
                ChatColor.GREEN + "▶ Clic pour se téléporter immédiatement"));

        inv.setItem(40, createMenuItem(Material.GRASS_BLOCK,
                ChatColor.GREEN + "" + ChatColor.BOLD + "🌲 PORTAIL MONDE SURVIE",
                ChatColor.DARK_GRAY + "Spawn Survie (Zone Protégée 300x300)", "",
                ChatColor.WHITE + "Téléportez-vous directement dans le Monde Ouvert.",
                ChatColor.WHITE + "Zone sécurisée sur 300x300 blocs, puis survie sauvage !", "",
                ChatColor.GREEN + "Coordonnées : X=640, Z=864 (Plaines Terrestres)", "",
                ChatColor.GREEN + "▶ Clic pour se téléporter au Spawn Survie (/survie)"));

        inv.setItem(42, createMenuItem(Material.PURPUR_BLOCK,
                ChatColor.LIGHT_PURPLE + "" + ChatColor.BOLD + "🌌 ÎLE ONEBLOCK PERSONNELLE",
                ChatColor.DARK_GRAY + "Votre Monde OneBlock Infini", "",
                ChatColor.WHITE + "Générez et développez votre île céleste unique.",
                ChatColor.WHITE + "Minage infini du bloc central évolutif (6 phases) !", "",
                ChatColor.LIGHT_PURPLE + "✦ Protection automatique & anti-chute d'items",
                ChatColor.LIGHT_PURPLE + "✦ Invitez vos amis avec /ob invite <joueur>", "",
                ChatColor.GREEN + "▶ Clic pour rejoindre votre OneBlock (/ob)"));

        inv.setItem(49, createMenuItem(Material.BARRIER,
                ChatColor.RED + "" + ChatColor.BOLD + "✖ FERMER LE MENU",
                ChatColor.GRAY + "Retourner dans le jeu"));

        player.openInventory(inv);
        player.playSound(player.getLocation(), Sound.BLOCK_NOTE_BLOCK_PLING, 1.0f, 1.8f);
    }

    private ItemStack createGlassPane(Material mat, String name) {
        ItemStack item = new ItemStack(mat);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(name);
            item.setItemMeta(meta);
        }
        return item;
    }

    private ItemStack createMenuItem(Material mat, String title, String... loreLines) {
        ItemStack item = new ItemStack(mat);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(title);
            meta.setLore(Arrays.asList(loreLines));
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES, ItemFlag.HIDE_ENCHANTS);
            item.setItemMeta(meta);
        }
        return item;
    }

    private ItemStack createPlayerProfileHead(Player player) {
        ItemStack head = new ItemStack(Material.PLAYER_HEAD);
        SkullMeta meta = (SkullMeta) head.getItemMeta();
        if (meta != null) {
            meta.setOwningPlayer(player);
            meta.setDisplayName(ChatColor.GREEN + "" + ChatColor.BOLD + "📜 GRIMOIRE DE " + player.getName().toUpperCase());
            double balance = 1000.0;
            int shopPoints = 10;
            String rank = "JOUEUR";
            try (Connection conn = AetherDatabase.getConnection()) {
                try (PreparedStatement ps = conn.prepareStatement("SELECT balance, rank FROM players WHERE LOWER(username) = LOWER(?);")) {
                    ps.setString(1, player.getName());
                    try (ResultSet rs = ps.executeQuery()) {
                        if (rs.next()) {
                            balance = rs.getDouble("balance");
                            rank = rs.getString("rank");
                        }
                    }
                }
                try (PreparedStatement ps = conn.prepareStatement("SELECT shop_points FROM users WHERE LOWER(minecraft_username) = LOWER(?);")) {
                    ps.setString(1, player.getName());
                    try (ResultSet rs = ps.executeQuery()) {
                        if (rs.next()) shopPoints = rs.getInt("shop_points");
                    }
                }
            } catch (Exception ignored) {}

            List<String> lore = new ArrayList<>(Arrays.asList(
                    ChatColor.DARK_GRAY + "Profil & Statistiques Primordiales", "",
                    ChatColor.WHITE + "✦ Rang Actuel : " + ChatColor.GOLD + "[" + rank + "]",
                    ChatColor.WHITE + "✦ Solde In-Game : " + ChatColor.YELLOW + String.format("%.0f", balance) + " ⛁ Aether Coins",
                    ChatColor.WHITE + "✦ Solde Boutique : " + ChatColor.GOLD + shopPoints + " ⭐ Jetons",
                    ChatColor.WHITE + "✦ Niveau d'Expérience : " + ChatColor.GREEN + player.getLevel() + " Lvl", "",
                    ChatColor.DARK_GRAY + "Connecté à l'écosystème web AetherCraft"));
            meta.setLore(lore);
            head.setItemMeta(meta);
        }
        return head;
    }

    @EventHandler
    public void onInventoryClick(InventoryClickEvent event) {
        if (event.getView() == null || !MENU_TITLE.equals(event.getView().getTitle())) return;
        event.setCancelled(true);
        if (!(event.getWhoClicked() instanceof Player player)) return;

        switch (event.getRawSlot()) {
            case 11 -> {
                player.closeInventory();
                if (marketGUI != null) marketGUI.openMarket(player);
                else player.performCommand("ah");
            }
            case 13 -> {
                player.closeInventory();
                if (oresGUI != null) oresGUI.openOresShop(player);
                else player.sendMessage(ChatColor.DARK_GREEN + "  ▶ http://127.0.0.1:5000/marche");
            }
            case 15 -> {
                player.closeInventory();
                player.playSound(player.getLocation(), Sound.ENTITY_ALLAY_AMBIENT_WITHOUT_ITEM, 1.0f, 1.3f);
                player.sendMessage(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Sanctuaire des Compagnons Célestes :");
                player.sendMessage(ChatColor.GRAY + "Usage: /pet <dragon|capybara|fox|goat|phoenix>");
            }
            case 20 -> {
                player.closeInventory();
                player.playSound(player.getLocation(), Sound.BLOCK_ENCHANTMENT_TABLE_USE, 1.0f, 1.2f);
                if (quizEngine != null && quizEngine.isQuestionActive() && quizEngine.getActiveQuestion() != null) {
                    player.sendMessage(ChatColor.GOLD + "★ Énigme active du Sphinx : " + ChatColor.WHITE + quizEngine.getActiveQuestion().getQuestion());
                    player.sendMessage(ChatColor.YELLOW + "Tapez votre réponse directement dans le chat pour gagner 5 Jetons !");
                } else {
                    player.sendMessage(ChatColor.GOLD + "★ Le Sphinx médite... Une énigme sera posée très bientôt dans le chat !");
                }
            }
            case 22 -> {
                player.closeInventory();
                if (shopGUI != null) shopGUI.openShop(player);
                else {
                    player.playSound(player.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 0.8f, 1.5f);
                    player.sendMessage(ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Visitez la Boutique Céleste pour dépenser vos Jetons : " + ChatColor.UNDERLINE + "http://127.0.0.1:5000/boutique");
                }
            }
            case 24 -> {
                player.closeInventory();
                player.playSound(player.getLocation(), Sound.ENTITY_ENDER_DRAGON_GROWL, 0.7f, 1.2f);
                player.sendMessage(ChatColor.RED + "⚔️ " + ChatColor.WHITE + "Préparation d'expédition de Donjon Céleste...");
                player.performCommand("dungeon start aetherite");
            }
            case 38 -> {
                player.closeInventory();
                if (portalEngine != null) {
                    portalEngine.teleportToHub(player);
                } else {
                    player.performCommand("spawn");
                }
            }
            case 40 -> {
                player.closeInventory();
                if (portalEngine != null) portalEngine.teleportToSurvival(player);
                else player.performCommand("survie");
            }
            case 42 -> {
                player.closeInventory();
                player.performCommand("ob");
            }
            case 49 -> {
                player.closeInventory();
                player.playSound(player.getLocation(), Sound.UI_BUTTON_CLICK, 1.0f, 1.0f);
            }
            default -> {}
        }
    }
}
