package io.aethercraft.visuals;

import io.aethercraft.visuals.AetherMMOShopCatalog.ShopCard;
import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.ClickType;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.SkullMeta;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

import static io.aethercraft.visuals.AetherMMOShopCatalog.*;

/**
 * Moteur d'Interface Graphique Intégrale MMORPG (AetherMMOInterfaceEngine).
 */
public class AetherMMOInterfaceEngine implements Listener {

    public static final String COCKPIT_TITLE = ChatColor.DARK_GRAY + "✦ " + ChatColor.GOLD + ChatColor.BOLD + "AETHERCRAFT" + ChatColor.DARK_GRAY + " • " + ChatColor.AQUA + ChatColor.BOLD + "COCKPIT MMORPG" + ChatColor.DARK_GRAY + " ✦";
    public static final String SHOP_TITLE = ChatColor.DARK_GRAY + "✦ " + ChatColor.GOLD + ChatColor.BOLD + "BOUTIQUE CÉLESTE MMORPG" + ChatColor.DARK_GRAY + " ✦";

    private final AetherVisualsPlugin plugin;
    private final Map<UUID, String> activeShopCategory = new ConcurrentHashMap<>();

    private PortalTeleportEngine portalEngine;
    private RandomSpawnEngine randomSpawnEngine;
    private DungeonWaveEngine dungeonWaveEngine;
    private AetherOresGUI oresGUI;
    private AetherMarketGUI marketGUI;

    public AetherMMOInterfaceEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
    }

    public void setEngines(PortalTeleportEngine portalEngine, RandomSpawnEngine randomSpawnEngine,
                           DungeonWaveEngine dungeonWaveEngine, AetherOresGUI oresGUI, AetherMarketGUI marketGUI) {
        this.portalEngine = portalEngine;
        this.randomSpawnEngine = randomSpawnEngine;
        this.dungeonWaveEngine = dungeonWaveEngine;
        this.oresGUI = oresGUI;
        this.marketGUI = marketGUI;
    }

    public void openCockpitMenu(Player player) {
        if (plugin.getHoloEngine() != null) {
            plugin.getHoloEngine().openHoloUI(player, AetherHoloUIEngine.HoloMode.COCKPIT, null);
            return;
        }
        Inventory inv = Bukkit.createInventory(null, 54, COCKPIT_TITLE);
        ItemStack filler = createBorderItem();
        for (int i = 0; i < 54; i++) inv.setItem(i, filler);

        int coins = getPlayerCoins(player.getName());
        int points = getPlayerPoints(player.getName());
        int gauge = getCommunityGauge();
        int gaugePct = Math.min(100, (int) Math.round((gauge / 50000.0) * 100.0));
        String progressBar = buildProgressBar(gaugePct);

        ItemStack profile = new ItemStack(Material.PLAYER_HEAD);
        SkullMeta sm = (SkullMeta) profile.getItemMeta();
        if (sm != null) {
            sm.setOwningPlayer(player);
            sm.setDisplayName(ChatColor.GOLD + "" + ChatColor.BOLD + "⚔️ AVENTURIER : " + player.getName());
            Location loc = player.getLocation();
            sm.setLore(Arrays.asList(
                    ChatColor.DARK_GRAY + "────────────────────────────",
                    ChatColor.YELLOW + "⭐ Statut : " + ChatColor.GREEN + "Connecté • Archipel Céleste",
                    ChatColor.YELLOW + "👑 Rang : " + (player.isOp() ? ChatColor.LIGHT_PURPLE + "Administrateur" : ChatColor.GOLD + "Explorateur"),
                    ChatColor.YELLOW + "💰 Solde Or : " + ChatColor.GOLD + coins + " ⛁ Coins",
                    ChatColor.YELLOW + "✪ Jetons d'Éther : " + ChatColor.AQUA + points + " ✪ Points",
                    ChatColor.YELLOW + "📌 Position : " + ChatColor.GRAY + "X=" + loc.getBlockX() + " Y=" + loc.getBlockY() + " Z=" + loc.getBlockZ(),
                    ChatColor.DARK_GRAY + "────────────────────────────"
            ));
            sm.addItemFlags(ItemFlag.HIDE_ATTRIBUTES);
            profile.setItemMeta(sm);
        }
        inv.setItem(4, profile);

        inv.setItem(13, createMMOItem(Material.HEART_OF_THE_SEA, ChatColor.GREEN + "" + ChatColor.BOLD + "🌳 ÉCLOSION DE L'ARBRE DES CIEUX",
                Arrays.asList(ChatColor.DARK_GRAY + "────────────────────────────",
                        ChatColor.YELLOW + "Progression Mondiale : " + ChatColor.GREEN + gaugePct + "%",
                        ChatColor.AQUA + "  " + progressBar, ChatColor.WHITE + "  " + gauge + " / 50 000 Minerais Célestes",
                        ChatColor.DARK_GRAY + "────────────────────────────",
                        ChatColor.GRAY + "Chaque minerai livré au marché ou expédition", ChatColor.GRAY + "de donjon alimente cette jauge partagée !"), 0));

        inv.setItem(20, createMMOItem(Material.BEACON, ChatColor.DARK_AQUA + "" + ChatColor.BOLD + "🪐 AGORA CÉLESTE (Spawn 1)",
                Arrays.asList(ChatColor.GRAY + "Spawn central de l'Archipel (Y=120).", ChatColor.AQUA + "▶ Clic Gauche : Téléportation Agora"), 0));

        inv.setItem(22, createMMOItem(Material.GRASS_BLOCK, ChatColor.GREEN + "" + ChatColor.BOLD + "🌱 MONDE SURVIE TERRESTRE",
                Arrays.asList(ChatColor.GRAY + "Plaines naturelles et liberté totale de minage.",
                        ChatColor.GREEN + "▶ Clic Gauche : Reprendre Survie", ChatColor.GRAY + "▶ Clic Droit : Esplanade Portail (640, 864)"), 0));

        inv.setItem(24, createMMOItem(Material.AMETHYST_CLUSTER, ChatColor.BLUE + "" + ChatColor.BOLD + "🌀 TÉLÉPORTATION ALÉATOIRE (RTP)",
                Arrays.asList(ChatColor.GRAY + "Sol naturel garanti • Protection 15s.", ChatColor.BLUE + "▶ Clic Gauche : Lancer le Rituel RTP"), 0));

        inv.setItem(29, createMMOItem(Material.NETHER_STAR, ChatColor.GOLD + "" + ChatColor.BOLD + "🛍️ LA BOUTIQUE CÉLESTE MMORPG",
                Arrays.asList(ChatColor.GRAY + "Rangs VIP, Ailes 3D, Clés, Boosters et Familiers.", ChatColor.GOLD + "▶ Clic Gauche : Ouvrir la Boutique"), 0));

        inv.setItem(31, createMMOItem(Material.NETHERITE_SWORD, ChatColor.RED + "" + ChatColor.BOLD + "⚔️ LE SANCTUAIRE DE L'AETHERITE",
                Arrays.asList(ChatColor.GRAY + "Expédition instanciée en 5 vagues scalaires.",
                        ChatColor.YELLOW + "Boss : Titan Primordial de l'Éther.", ChatColor.RED + "▶ Clic Gauche : Entrer dans le Donjon"), 0));

        inv.setItem(33, createMMOItem(Material.RAW_GOLD, ChatColor.YELLOW + "" + ChatColor.BOLD + "⚖️ BOURSE DES MINERAIS & AGORA",
                Arrays.asList(ChatColor.GRAY + "Place de commerce et cours en direct des minerais.", ChatColor.YELLOW + "▶ Clic Gauche : Ouvrir la Bourse"), 0));

        inv.setItem(38, createMMOItem(Material.BONE, ChatColor.AQUA + "" + ChatColor.BOLD + "🐾 COMPAGNONS & FAMILIERS 3D",
                Arrays.asList(ChatColor.GRAY + "Invoquez votre Dragoneau, Capybara ou Phénix.", ChatColor.AQUA + "▶ Clic Gauche : Gérer les Familiers"), 0));

        inv.setItem(40, createMMOItem(Material.FEATHER, ChatColor.LIGHT_PURPLE + "" + ChatColor.BOLD + "🪽 COSMÉTIQUES & AURAS PARTICULAIRES",
                Arrays.asList(ChatColor.GRAY + "Activez vos Ailes Quantiques ou Auras de rang.", ChatColor.LIGHT_PURPLE + "▶ Clic Gauche : Gérer les Cosmétiques"), 0));

        inv.setItem(42, createMMOItem(Material.ENDER_PEARL, ChatColor.DARK_PURPLE + "" + ChatColor.BOLD + "🔙 RETOUR DERNIÈRE POSITION (/back)",
                Arrays.asList(ChatColor.GRAY + "Téléportation à votre dernier emplacement.", ChatColor.DARK_PURPLE + "▶ Clic Gauche : Se téléporter"), 0));

        inv.setItem(49, createMMOItem(Material.BARRIER, ChatColor.RED + "" + ChatColor.BOLD + "✖ FERMER LE COCKPIT",
                Collections.singletonList(ChatColor.GRAY + "Quitter le menu"), 0));

        player.playSound(player.getLocation(), Sound.BLOCK_BEACON_ACTIVATE, 0.7f, 1.4f);
        player.playSound(player.getLocation(), Sound.UI_BUTTON_CLICK, 0.8f, 1.2f);
        player.openInventory(inv);
    }

    public void openShopMenu(Player player, String category) {
        if (plugin.getHoloEngine() != null) {
            plugin.getHoloEngine().openHoloUI(player, AetherHoloUIEngine.HoloMode.SHOP, category);
            return;
        }
        if (category == null) category = "all";
        activeShopCategory.put(player.getUniqueId(), category);

        Inventory inv = Bukkit.createInventory(null, 54, SHOP_TITLE);
        ItemStack filler = createBorderItem();
        for (int i = 0; i < 54; i++) inv.setItem(i, filler);

        int points = getPlayerPoints(player.getName());
        inv.setItem(10, createTabItem("🌟 TOUS", category.equals("all")));
        inv.setItem(11, createTabItem("👑 RANGS", category.equals("ranks")));
        inv.setItem(12, createTabItem("🗝️ CLÉS", category.equals("keys")));
        inv.setItem(13, createTabItem("🪽 COSMÉTIQUES", category.equals("cosmetics")));
        inv.setItem(14, createTabItem("🐾 FAMILIERS", category.equals("pets")));
        inv.setItem(15, createTabItem("⚡ BOOSTERS", category.equals("boosters")));

        List<ShopCard> cards = getShopCards(category);
        int[] itemSlots = {19, 20, 21, 22, 23, 24, 25, 28, 29, 30, 31, 32, 33, 34};
        for (int i = 0; i < cards.size() && i < itemSlots.length; i++) {
            inv.setItem(itemSlots[i], createShopCardItem(cards.get(i), points));
        }

        inv.setItem(45, createMMOItem(Material.GOLD_INGOT, ChatColor.YELLOW + "" + ChatColor.BOLD + "VOTRE SOLDE : " + ChatColor.AQUA + points + " ✪ Points",
                Arrays.asList(ChatColor.GRAY + "Gagnez des jetons lors des quiz célestes,", ChatColor.AQUA + "Lien Web : http://127.0.0.1:5000/boutique"), 0));
        inv.setItem(49, createMMOItem(Material.ARROW, ChatColor.GREEN + "" + ChatColor.BOLD + "🔙 RETOUR AU COCKPIT",
                Collections.singletonList(ChatColor.GRAY + "Revenir au menu principal"), 0));
        inv.setItem(53, createMMOItem(Material.BOOK, ChatColor.GOLD + "" + ChatColor.BOLD + "🌐 BOUTIQUE EN LIGNE",
                Arrays.asList(ChatColor.GRAY + "Paiements sécurisés, packs de clés et VIP.", ChatColor.GOLD + "▶ Clic : Afficher le lien dans le chat"), 0));

        player.playSound(player.getLocation(), Sound.ITEM_ARMOR_EQUIP_GOLD, 0.8f, 1.1f);
        player.openInventory(inv);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onInventoryClick(InventoryClickEvent event) {
        if (!(event.getWhoClicked() instanceof Player player)) return;
        String title = event.getView().getTitle();
        if (title.equals(COCKPIT_TITLE)) {
            event.setCancelled(true);
            handleCockpitClick(player, event.getRawSlot(), event.getClick());
        } else if (title.equals(SHOP_TITLE)) {
            event.setCancelled(true);
            handleShopClick(player, event.getRawSlot());
        }
    }

    private void handleCockpitClick(Player player, int slot, ClickType click) {
        player.playSound(player.getLocation(), Sound.UI_BUTTON_CLICK, 0.7f, 1.2f);
        switch (slot) {
            case 20 -> { player.closeInventory(); if (portalEngine != null) portalEngine.teleportToHub(player); }
            case 22 -> { player.closeInventory(); if (portalEngine != null) portalEngine.teleportToSurvival(player, click.isRightClick()); }
            case 24 -> { player.closeInventory(); if (randomSpawnEngine != null) randomSpawnEngine.startRtpRitual(player); }
            case 29 -> openShopMenu(player, "all");
            case 31 -> { player.closeInventory(); if (dungeonWaveEngine != null) dungeonWaveEngine.joinDungeon(player); }
            case 33 -> { player.closeInventory(); if (oresGUI != null) oresGUI.openOresShop(player); }
            case 38 -> { player.closeInventory(); player.performCommand("pet"); }
            case 40 -> { player.closeInventory(); player.performCommand("aura"); }
            case 42 -> { player.closeInventory(); player.performCommand("back"); }
            case 49 -> player.closeInventory();
        }
    }

    private void handleShopClick(Player player, int slot) {
        player.playSound(player.getLocation(), Sound.UI_BUTTON_CLICK, 0.7f, 1.2f);
        if (slot >= 10 && slot <= 15) {
            String[] cats = {"all", "ranks", "keys", "cosmetics", "pets", "boosters"};
            openShopMenu(player, cats[slot - 10]);
            return;
        }
        if (slot == 49) { openCockpitMenu(player); return; }
        if (slot == 53) {
            player.closeInventory();
            player.sendMessage(ChatColor.GOLD + "✦ Boutique Web Officielle : " + ChatColor.AQUA + "http://127.0.0.1:5000/boutique");
            return;
        }
        String category = activeShopCategory.getOrDefault(player.getUniqueId(), "all");
        List<ShopCard> cards = getShopCards(category);
        int[] itemSlots = {19, 20, 21, 22, 23, 24, 25, 28, 29, 30, 31, 32, 33, 34};
        for (int i = 0; i < cards.size() && i < itemSlots.length; i++) {
            if (itemSlots[i] == slot) {
                executePurchase(player, cards.get(i));
                break;
            }
        }
    }

    private void executePurchase(Player player, ShopCard card) {
        int currentPoints = getPlayerPoints(player.getName());
        if (currentPoints < card.pricePoints) {
            player.playSound(player.getLocation(), Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
            player.sendMessage(ChatColor.RED + "❌ Points insuffisants ! Il vous manque " + (card.pricePoints - currentPoints) + " ✪ Points.");
            return;
        }
        if (deductPlayerPoints(player.getName(), card.pricePoints)) {
            player.playSound(player.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.2f);
            player.getWorld().spawnParticle(Particle.HAPPY_VILLAGER, player.getLocation().add(0, 1, 0), 30, 0.5, 0.5, 0.5, 0.1);
            deliverPurchasedItem(plugin, player, card.id);
            player.sendMessage(ChatColor.GREEN + "✦ ACHAT RÉUSSI ! " + card.title + ChatColor.YELLOW + " (-" + card.pricePoints + " ✪)");
            openShopMenu(player, activeShopCategory.getOrDefault(player.getUniqueId(), "all"));
        } else {
            player.sendMessage(ChatColor.RED + "❌ Erreur de transaction SQLite.");
        }
    }
}
