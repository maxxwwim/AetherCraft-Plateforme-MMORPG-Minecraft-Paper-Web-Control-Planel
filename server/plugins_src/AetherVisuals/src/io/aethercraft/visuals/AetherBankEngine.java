package io.aethercraft.visuals;

import org.bukkit.*;
import org.bukkit.block.Block;
import org.bukkit.entity.Display;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.entity.TextDisplay;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryCloseEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.util.io.BukkitObjectInputStream;
import org.bukkit.util.io.BukkitObjectOutputStream;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Banque Privée d'Aether (Style Dofus : Coffre Personnel 36 slots, Tri automatique,
 * Transferts rapides de ressources/équipements & Guichet financier de Kamas/Pièces ⛃).
 */
public class AetherBankEngine implements Listener {

    public static final String BANK_TITLE_PREFIX = ChatColor.DARK_GRAY + "[" + ChatColor.GOLD + "" + ChatColor.BOLD + "🏦 BANQUE DOFUS" + ChatColor.DARK_GRAY + "] ";
    public static final int BANK_VAULT_X = -10, BANK_VAULT_Y = 121, BANK_VAULT_Z = -10;
    private static final int VAULT_SLOTS = 36;

    private final AetherVisualsPlugin plugin;
    private final Set<UUID> Transitioning = ConcurrentHashMap.newKeySet();

    public AetherBankEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
        ensureSchema();
    }

    private void ensureSchema() {
        try (Connection c = AetherDatabase.getConnection(); Statement st = c.createStatement()) {
            st.executeUpdate("CREATE TABLE IF NOT EXISTS player_bank_accounts ("
                    + "username TEXT PRIMARY KEY, bank_coins REAL DEFAULT 0.0, updated_at TEXT)");
            st.executeUpdate("CREATE TABLE IF NOT EXISTS player_bank_items ("
                    + "username TEXT, slot INTEGER, item_b64 TEXT, PRIMARY KEY (username, slot))");
        } catch (Exception e) {
            plugin.getLogger().warning("[AetherBank] Erreur init SQLite: " + e.getMessage());
        }
    }

    public static void spawnBankHologram(World w) {
        if (w == null) return;
        Location center = new Location(w, BANK_VAULT_X + 0.5, BANK_VAULT_Y + 2.7, BANK_VAULT_Z + 0.5);
        for (Entity e : w.getNearbyEntities(center, 4, 4, 4)) {
            if (e.getScoreboardTags().contains("aether_bank_holo")) e.remove();
        }
        w.spawn(center, TextDisplay.class, td -> {
            td.setBillboard(Display.Billboard.CENTER);
            td.setBrightness(new Display.Brightness(15, 15));
            td.setBackgroundColor(Color.fromARGB(185, 12, 20, 36));
            td.setText("§6§l🏦 BANQUE D'AETHER §e✦ STYLE DOFUS\n§7Guichet du Maître Banquier & Coffre-Fort Personnel\n§a🔒 100% Sécurisé §8• §eKamas (⛃) & Inventaire Illimité\n§e▶ Clic Droit sur le Guichet ou §f/banque");
            td.addScoreboardTag("aether_bank_holo");
            td.addScoreboardTag("aether_spawn_prop");
        });
    }

    public double[] getBalances(String username) {
        double wallet = 1000.0, bank = 0.0;
        try (Connection c = AetherDatabase.getConnection()) {
            try (PreparedStatement ps = c.prepareStatement("SELECT balance FROM players WHERE LOWER(username)=LOWER(?)")) {
                ps.setString(1, username);
                try (ResultSet rs = ps.executeQuery()) { if (rs.next()) wallet = rs.getDouble(1); }
            }
            try (PreparedStatement ps = c.prepareStatement("SELECT bank_coins FROM player_bank_accounts WHERE LOWER(username)=LOWER(?)")) {
                ps.setString(1, username);
                try (ResultSet rs = ps.executeQuery()) {
                    if (rs.next()) bank = rs.getDouble(1);
                    else {
                        try (PreparedStatement ins = c.prepareStatement("INSERT OR IGNORE INTO player_bank_accounts (username, bank_coins, updated_at) VALUES (?, 0.0, datetime('now'))")) {
                            ins.setString(1, username); ins.executeUpdate();
                        }
                    }
                }
            }
        } catch (Exception ignored) {}
        return new double[]{wallet, bank};
    }

    public void openBank(Player p) {
        if (plugin.getHoloEngine() != null) plugin.getHoloEngine().closeSession(p.getUniqueId(), false);
        double[] bal = getBalances(p.getName());
        String title = BANK_TITLE_PREFIX + ChatColor.AQUA + p.getName();
        Inventory inv = Bukkit.createInventory(p, 54, title);

        // 1. Charger les 36 emplacements de coffre privé (Style Dofus)
        Map<Integer, ItemStack> items = loadVaultItems(p.getName());
        for (Map.Entry<Integer, ItemStack> entry : items.entrySet()) {
            int sl = entry.getKey();
            if (sl >= 0 && sl < VAULT_SLOTS) inv.setItem(sl, entry.getValue());
        }

        // 2. Barre d'outils et de tri Dofus (Slots 36..44)
        inv.setItem(36, makeBtn(Material.CHEST, "§6§l📦 COFFRE DOFUS",
                "§7Vos objets et reliques en sécurité",
                "§eEmplacements : §f" + items.size() + " / " + VAULT_SLOTS + " slots",
                "§a🔒 Accès strictement personnel"));

        inv.setItem(37, makeBtn(Material.AMETHYST_SHARD, "§b§l⚡ TRIER LE COFFRE (Style Dofus)",
                "§7Regroupe et réorganise automatiquement",
                "§7tous les objets de votre coffre",
                "§e▶ Clic gauche pour trier"));

        inv.setItem(38, makeBtn(Material.RAW_GOLD, "§e§l📥 DÉPOSER LES RESSOURCES (Dofus)",
                "§7Transfère automatiquement tous les",
                "§7minerais, lingots, blocs & récoltes",
                "§7de votre inventaire vers la banque",
                "§a▶ Clic pour vider vos ressources"));

        inv.setItem(39, makeBtn(Material.HOPPER, "§a§l📥 TOUT DÉPOSER EN BANQUE",
                "§7Transfère tous les objets possibles",
                "§7de votre sac vers votre coffre",
                "§7(conserve votre équipement et téléphone)",
                "§e▶ Clic pour tout déposer"));

        inv.setItem(40, makeBtn(Material.ENDER_CHEST, "§6§l🏦 COMPTE BANCAIRE DOFUS",
                "§7Titulaire : §f" + p.getName() + " §8(§a🔒 Privé§8)",
                "§7Kamas en Poche : §e" + (int) bal[0] + " ⛃",
                "§7Kamas en Banque : §6§l" + (int) bal[1] + " ⛃",
                "§7Objets en Coffre : §b" + items.size() + " / " + VAULT_SLOTS + " slots",
                "§a✔ Coût d'ouverture : Gratuit (0 ⛃ Kamas)"));

        inv.setItem(41, makeBtn(Material.DISPENSER, "§c§l📤 TOUT RÉCUPÉRER",
                "§7Transfère les objets de la banque",
                "§7vers votre inventaire personnel",
                "§e▶ Clic pour tout récupérer"));

        inv.setItem(42, makeBtn(Material.RAW_GOLD_BLOCK, "§6§l🧈 Frapper 1x Lingot Habbo (250 ⛃)",
                "§7Convertit 250 ⛃ en Lingot physique",
                "§a▶ Clic pour forger un Lingot"));

        inv.setItem(43, makeBtn(Material.RECOVERY_COMPASS, "§b§l📱 Ouvrir AetherPhone (16/9)",
                "§7Basculer sur le HUD du Téléphone"));

        inv.setItem(44, makeBtn(Material.BARRIER, "§c§l❌ Fermer la Banque",
                "§7Sauvegarder et quitter le guichet"));

        // 3. Guichet financier de Kamas (Slots 45..53)
        inv.setItem(45, makeBtn(Material.GOLD_NUGGET, "§a📥 Déposer +100 ⛃", "§7Kamas poche ➔ Coffre"));
        inv.setItem(46, makeBtn(Material.GOLD_INGOT, "§a📥 Déposer +1 000 ⛃", "§7Kamas poche ➔ Coffre"));
        inv.setItem(47, makeBtn(Material.GOLD_BLOCK, "§a📥 Déposer +10 000 ⛃", "§7Kamas poche ➔ Coffre"));
        inv.setItem(48, makeBtn(Material.NETHER_STAR, "§a§l📥 TOUT DÉPOSER (Kamas)",
                "§7Sécuriser 100% de vos Kamas en banque",
                "§eEn poche : §6" + (int) bal[0] + " ⛃"));

        inv.setItem(49, makeBtn(Material.SUNFLOWER, "§e§l⚖️ GUICHET DES KAMAS",
                "§7Gestion de votre fortune financière",
                "§7En Poche : §e" + (int) bal[0] + " ⛃",
                "§7En Banque : §6§l" + (int) bal[1] + " ⛃"));

        inv.setItem(50, makeBtn(Material.BEACON, "§e§l📤 TOUT RETIRER (Kamas)",
                "§7Récupérer 100% de vos Kamas en poche",
                "§6En banque : §e" + (int) bal[1] + " ⛃"));

        inv.setItem(51, makeBtn(Material.IRON_BLOCK, "§e📤 Retirer -10 000 ⛃", "§7Coffre ➔ Kamas poche"));
        inv.setItem(52, makeBtn(Material.IRON_INGOT, "§e📤 Retirer -1 000 ⛃", "§7Coffre ➔ Kamas poche"));
        inv.setItem(53, makeBtn(Material.IRON_NUGGET, "§e📤 Retirer -100 ⛃", "§7Coffre ➔ Kamas poche"));

        p.openInventory(inv);
        p.playSound(p.getLocation(), Sound.BLOCK_CHEST_OPEN, 0.85f, 1.15f);
        p.playSound(p.getLocation(), Sound.ITEM_ARMOR_EQUIP_GOLD, 0.7f, 1.25f);
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void onBankVaultInteract(PlayerInteractEvent e) {
        if (e.getAction() != Action.RIGHT_CLICK_BLOCK || e.getClickedBlock() == null) return;
        Block b = e.getClickedBlock();
        if ((b.getType() == Material.ENDER_CHEST || b.getType() == Material.BARREL || b.getType() == Material.CHEST) 
                && b.getWorld().getName().equalsIgnoreCase("world") && b.getY() >= 110
                && Math.abs(b.getX() - BANK_VAULT_X) <= 3 && Math.abs(b.getZ() - BANK_VAULT_Z) <= 3) {
            e.setCancelled(true);
            openBank(e.getPlayer());
        }
    }

    @EventHandler
    public void onBankInventoryClick(InventoryClickEvent e) {
        if (!(e.getWhoClicked() instanceof Player p)) return;
        if (!e.getView().getTitle().contains("BANQUE")) return;

        int raw = e.getRawSlot();
        if (raw >= 36 && raw < 54) {
            e.setCancelled(true);
            if (raw == 37) sortVault(p, e.getInventory());
            else if (raw == 38) depositResources(p, e.getInventory());
            else if (raw == 39) depositAllItems(p, e.getInventory());
            else if (raw == 41) retrieveAllItems(p, e.getInventory());
            else if (raw == 42) mintBullion(p, e.getInventory());
            else if (raw == 43) {
                p.closeInventory();
                if (plugin.getHoloEngine() != null) plugin.getHoloEngine().openHoloUI(p, AetherHoloUIEngine.HoloMode.COCKPIT, null);
            } else if (raw == 44) {
                p.closeInventory();
            } else if (raw == 45) transferCoins(p, e.getInventory(), 100, true);
            else if (raw == 46) transferCoins(p, e.getInventory(), 1000, true);
            else if (raw == 47) transferCoins(p, e.getInventory(), 10000, true);
            else if (raw == 48) transferCoins(p, e.getInventory(), Double.MAX_VALUE, true);
            else if (raw == 50) transferCoins(p, e.getInventory(), Double.MAX_VALUE, false);
            else if (raw == 51) transferCoins(p, e.getInventory(), 10000, false);
            else if (raw == 52) transferCoins(p, e.getInventory(), 1000, false);
            else if (raw == 53) transferCoins(p, e.getInventory(), 100, false);
        }
    }

    @EventHandler
    public void onBankClose(InventoryCloseEvent e) {
        if (!(e.getPlayer() instanceof Player p)) return;
        if (!e.getView().getTitle().contains("BANQUE")) return;
        if (Transitioning.remove(p.getUniqueId())) return;
        saveVaultItems(p.getName(), e.getInventory());
        p.playSound(p.getLocation(), Sound.BLOCK_CHEST_CLOSE, 0.75f, 1.25f);
    }

    public static boolean isResource(ItemStack item) {
        if (item == null || item.getType() == Material.AIR) return false;
        Material m = item.getType();
        String name = m.name();

        if (name.contains("SWORD") || name.contains("AXE") || name.contains("PICKAXE")
                || name.contains("SHOVEL") || name.contains("HOE") || name.contains("BOW")
                || name.contains("CROSSBOW") || name.contains("TRIDENT") || name.contains("MACE")
                || name.contains("SHIELD") || name.contains("HELMET") || name.contains("CHESTPLATE")
                || name.contains("LEGGINGS") || name.contains("BOOTS") || name.contains("ELYTRA")
                || name.contains("POTION") || name.contains("GOLDEN_APPLE")) {
            return false;
        }
        if (item.hasItemMeta() && item.getItemMeta().hasCustomModelData()) {
            int cmd = item.getItemMeta().getCustomModelData();
            if (cmd == 9999 || (cmd >= 1000 && cmd < 2000)) return false;
        }

        if (m.isBlock()) return true;
        return name.contains("ORE") || name.contains("INGOT") || name.contains("RAW_")
                || name.contains("NUGGET") || name.contains("LOG") || name.contains("WOOD")
                || name.contains("DIAMOND") || name.contains("EMERALD") || name.contains("COAL")
                || name.contains("QUARTZ") || name.contains("AMETHYST") || name.contains("DEBRIS")
                || name.contains("LEATHER") || name.contains("FEATHER") || name.contains("STRING")
                || name.contains("BONE") || name.contains("SLIME") || name.contains("WHEAT")
                || name.contains("CARROT") || name.contains("POTATO") || name.contains("SEEDS")
                || name.contains("REDSTONE") || name.contains("LAPIS") || name.contains("FLINT")
                || name.contains("CLAY") || name.contains("BRICK") || name.contains("PAPER")
                || name.contains("SUGAR") || name.contains("GUNPOWDER") || name.contains("ROTTEN_FLESH")
                || name.contains("SPIDER_EYE") || name.contains("ENDER_PEARL") || name.contains("BLAZE")
                || name.contains("MAGOT") || PetItemFactory.isBullionCoin(item);
    }

    private void depositResources(Player p, Inventory inv) {
        saveVaultItems(p.getName(), inv);
        int transferred = 0;
        ItemStack[] pContents = p.getInventory().getStorageContents();
        for (int i = 0; i < pContents.length; i++) {
            ItemStack stack = pContents[i];
            if (stack == null || stack.getType() == Material.AIR) continue;
            if (!isResource(stack)) continue;

            for (int v = 0; v < VAULT_SLOTS; v++) {
                ItemStack vStack = inv.getItem(v);
                if (vStack != null && vStack.isSimilar(stack)) {
                    int space = vStack.getMaxStackSize() - vStack.getAmount();
                    if (space > 0) {
                        int toMove = Math.min(space, stack.getAmount());
                        vStack.setAmount(vStack.getAmount() + toMove);
                        stack.setAmount(stack.getAmount() - toMove);
                        transferred += toMove;
                        if (stack.getAmount() <= 0) {
                            pContents[i] = null;
                            break;
                        }
                    }
                }
            }
            if (stack.getAmount() > 0) {
                for (int v = 0; v < VAULT_SLOTS; v++) {
                    if (inv.getItem(v) == null || inv.getItem(v).getType() == Material.AIR) {
                        inv.setItem(v, stack.clone());
                        transferred += stack.getAmount();
                        pContents[i] = null;
                        break;
                    }
                }
            }
        }
        p.getInventory().setStorageContents(pContents);
        saveVaultItems(p.getName(), inv);
        if (transferred > 0) {
            p.playSound(p.getLocation(), Sound.ITEM_ARMOR_EQUIP_GOLD, 0.9f, 1.3f);
            p.playSound(p.getLocation(), Sound.ENTITY_EXPERIENCE_ORB_PICKUP, 0.8f, 1.5f);
            p.sendMessage("§6§l[🏦 BANQUE DOFUS] §aDépôt rapide terminé : §f" + transferred + " ressources §atransférées dans votre coffre !");
        } else {
            p.playSound(p.getLocation(), Sound.ENTITY_VILLAGER_NO, 0.8f, 1.0f);
            p.sendMessage("§e[Banque Dofus] Aucune ressource à déposer ou coffre plein !");
        }
        Transitioning.add(p.getUniqueId());
        openBank(p);
    }

    private void depositAllItems(Player p, Inventory inv) {
        saveVaultItems(p.getName(), inv);
        int transferred = 0;
        ItemStack[] pContents = p.getInventory().getStorageContents();
        for (int i = 0; i < pContents.length; i++) {
            ItemStack stack = pContents[i];
            if (stack == null || stack.getType() == Material.AIR) continue;
            if (stack.hasItemMeta() && stack.getItemMeta().hasCustomModelData() && stack.getItemMeta().getCustomModelData() == 9999) {
                continue;
            }

            for (int v = 0; v < VAULT_SLOTS; v++) {
                ItemStack vStack = inv.getItem(v);
                if (vStack != null && vStack.isSimilar(stack)) {
                    int space = vStack.getMaxStackSize() - vStack.getAmount();
                    if (space > 0) {
                        int toMove = Math.min(space, stack.getAmount());
                        vStack.setAmount(vStack.getAmount() + toMove);
                        stack.setAmount(stack.getAmount() - toMove);
                        transferred += toMove;
                        if (stack.getAmount() <= 0) {
                            pContents[i] = null;
                            break;
                        }
                    }
                }
            }
            if (stack.getAmount() > 0) {
                for (int v = 0; v < VAULT_SLOTS; v++) {
                    if (inv.getItem(v) == null || inv.getItem(v).getType() == Material.AIR) {
                        inv.setItem(v, stack.clone());
                        transferred += stack.getAmount();
                        pContents[i] = null;
                        break;
                    }
                }
            }
        }
        p.getInventory().setStorageContents(pContents);
        saveVaultItems(p.getName(), inv);
        if (transferred > 0) {
            p.playSound(p.getLocation(), Sound.ITEM_ARMOR_EQUIP_CHAIN, 0.9f, 1.2f);
            p.sendMessage("§6§l[🏦 BANQUE DOFUS] §aTout déposé : §f" + transferred + " objets §atransférés dans votre coffre !");
        } else {
            p.playSound(p.getLocation(), Sound.ENTITY_VILLAGER_NO, 0.8f, 1.0f);
            p.sendMessage("§e[Banque Dofus] Rien à déposer ou coffre plein !");
        }
        Transitioning.add(p.getUniqueId());
        openBank(p);
    }

    private void retrieveAllItems(Player p, Inventory inv) {
        saveVaultItems(p.getName(), inv);
        int retrieved = 0;
        for (int v = 0; v < VAULT_SLOTS; v++) {
            ItemStack vStack = inv.getItem(v);
            if (vStack == null || vStack.getType() == Material.AIR) continue;
            HashMap<Integer, ItemStack> leftover = p.getInventory().addItem(vStack);
            if (leftover.isEmpty()) {
                retrieved += vStack.getAmount();
                inv.setItem(v, null);
            } else {
                ItemStack rem = leftover.values().iterator().next();
                retrieved += (vStack.getAmount() - rem.getAmount());
                inv.setItem(v, rem);
                break;
            }
        }
        saveVaultItems(p.getName(), inv);
        if (retrieved > 0) {
            p.playSound(p.getLocation(), Sound.ENTITY_ITEM_PICKUP, 0.9f, 1.2f);
            p.sendMessage("§6§l[🏦 BANQUE DOFUS] §aObjets récupérés : §f" + retrieved + " objets §atransférés dans votre sac !");
        } else {
            p.playSound(p.getLocation(), Sound.ENTITY_VILLAGER_NO, 0.8f, 1.0f);
            p.sendMessage("§e[Banque Dofus] Votre inventaire est plein ou le coffre est vide !");
        }
        Transitioning.add(p.getUniqueId());
        openBank(p);
    }

    private void sortVault(Player p, Inventory inv) {
        saveVaultItems(p.getName(), inv);
        List<ItemStack> items = new ArrayList<>();
        for (int i = 0; i < VAULT_SLOTS; i++) {
            ItemStack it = inv.getItem(i);
            if (it != null && it.getType() != Material.AIR) {
                items.add(it.clone());
                inv.setItem(i, null);
            }
        }
        if (items.isEmpty()) {
            p.playSound(p.getLocation(), Sound.ENTITY_VILLAGER_NO, 0.8f, 1.0f);
            p.sendMessage("§e[Banque Dofus] Le coffre est déjà vide !");
            return;
        }

        List<ItemStack> merged = new ArrayList<>();
        for (ItemStack it : items) {
            boolean combined = false;
            for (ItemStack m : merged) {
                if (m.isSimilar(it)) {
                    int space = m.getMaxStackSize() - m.getAmount();
                    if (space > 0) {
                        int add = Math.min(space, it.getAmount());
                        m.setAmount(m.getAmount() + add);
                        it.setAmount(it.getAmount() - add);
                        if (it.getAmount() <= 0) {
                            combined = true;
                            break;
                        }
                    }
                }
            }
            if (!combined && it.getAmount() > 0) {
                merged.add(it);
            }
        }

        merged.sort((a, b) -> {
            boolean aRes = isResource(a);
            boolean bRes = isResource(b);
            if (aRes != bRes) return aRes ? -1 : 1;
            return a.getType().name().compareToIgnoreCase(b.getType().name());
        });

        for (int i = 0; i < Math.min(VAULT_SLOTS, merged.size()); i++) {
            inv.setItem(i, merged.get(i));
        }
        saveVaultItems(p.getName(), inv);
        p.playSound(p.getLocation(), Sound.ITEM_BUNDLE_DROP_CONTENTS, 0.9f, 1.4f);
        p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.8f, 1.3f);
        p.sendMessage("§6§l[🏦 BANQUE DOFUS] §aCoffre trié et réorganisé avec succès !");
        Transitioning.add(p.getUniqueId());
        openBank(p);
    }

    private void mintBullion(Player p, Inventory inv) {
        saveVaultItems(p.getName(), inv);
        double[] bal = getBalances(p.getName());
        double cost = 250.0;
        if (bal[0] < cost && bal[1] < cost) {
            p.playSound(p.getLocation(), Sound.ENTITY_VILLAGER_NO, 0.8f, 1.0f);
            p.sendMessage("§c⚠ [Banque Dofus] Il vous faut au moins 250 ⛃ Kamas pour frapper un Lingot d'Or !");
            return;
        }

        boolean fromWallet = bal[0] >= cost;
        try (Connection c = AetherDatabase.getConnection()) {
            c.setAutoCommit(false);
            try {
                if (fromWallet) {
                    try (PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance - ? WHERE LOWER(username)=LOWER(?)")) {
                        ps.setDouble(1, cost); ps.setString(2, p.getName()); ps.executeUpdate();
                    }
                } else {
                    try (PreparedStatement ps = c.prepareStatement("UPDATE player_bank_accounts SET bank_coins = bank_coins - ? WHERE LOWER(username)=LOWER(?)")) {
                        ps.setDouble(1, cost); ps.setString(2, p.getName()); ps.executeUpdate();
                    }
                }
                c.commit();
            } catch (Exception ex) { c.rollback(); throw ex; }
        } catch (Exception ex) {
            p.sendMessage("§cErreur SQLite Banque : " + ex.getMessage());
            return;
        }

        ItemStack bullion = PetItemFactory.createHabboBullionItem("magot_lingot_or", 1);
        HashMap<Integer, ItemStack> leftover = p.getInventory().addItem(bullion);
        if (!leftover.isEmpty()) {
            p.getWorld().dropItemNaturally(p.getLocation(), leftover.get(0));
        }
        p.playSound(p.getLocation(), Sound.BLOCK_ANVIL_USE, 0.8f, 1.3f);
        p.playSound(p.getLocation(), Sound.ENTITY_PLAYER_LEVELUP, 0.7f, 1.5f);
        p.sendMessage("§6§l[🏦 BANQUE DOFUS] §aLingot d'Or Habbo (250 ⛃ Kamas) forgé et ajouté à votre inventaire !");
        Transitioning.add(p.getUniqueId());
        openBank(p);
    }

    private void transferCoins(Player p, Inventory inv, double amount, boolean deposit) {
        saveVaultItems(p.getName(), inv);
        double[] bal = getBalances(p.getName());
        double wallet = bal[0], bank = bal[1];
        double delta = deposit ? Math.min(wallet, amount) : Math.min(bank, amount);

        if (delta < 1.0) {
            p.playSound(p.getLocation(), Sound.ENTITY_VILLAGER_NO, 0.8f, 1.0f);
            p.sendMessage("§c⚠ [Banque Dofus] Solde insuffisant pour cette opération !");
            return;
        }
        try (Connection c = AetherDatabase.getConnection()) {
            c.setAutoCommit(false);
            try {
                double wDiff = deposit ? -delta : delta;
                double bDiff = deposit ? delta : -delta;
                try (PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?)")) {
                    ps.setDouble(1, wDiff); ps.setString(2, p.getName()); ps.executeUpdate();
                }
                try (PreparedStatement ps = c.prepareStatement(
                        "INSERT INTO player_bank_accounts (username, bank_coins, updated_at) VALUES (?, ?, datetime('now')) "
                        + "ON CONFLICT(username) DO UPDATE SET bank_coins = bank_coins + ?, updated_at = datetime('now')")) {
                    ps.setString(1, p.getName()); ps.setDouble(2, Math.max(0, bDiff)); ps.setDouble(3, bDiff); ps.executeUpdate();
                }
                c.commit();
            } catch (Exception ex) { c.rollback(); throw ex; }
        } catch (Exception ex) {
            p.sendMessage("§cErreur SQLite Banque : " + ex.getMessage());
            return;
        }
        p.playSound(p.getLocation(), Sound.ENTITY_EXPERIENCE_ORB_PICKUP, 0.95f, 1.4f);
        p.sendMessage("§6§l[🏦 BANQUE DOFUS] §a" + (deposit ? "Dépôt" : "Retrait") + " de §e" + (int) delta + " ⛃ Kamas §aeffectué avec succès !");
        Transitioning.add(p.getUniqueId());
        openBank(p);
    }

    private Map<Integer, ItemStack> loadVaultItems(String username) {
        Map<Integer, ItemStack> map = new HashMap<>();
        try (Connection c = AetherDatabase.getConnection();
             PreparedStatement ps = c.prepareStatement("SELECT slot, item_b64 FROM player_bank_items WHERE LOWER(username)=LOWER(?)")) {
            ps.setString(1, username);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    ItemStack it = fromBase64(rs.getString("item_b64"));
                    if (it != null) map.put(rs.getInt("slot"), it);
                }
            }
        } catch (Exception ignored) {}
        return map;
    }

    private void saveVaultItems(String username, Inventory inv) {
        try (Connection c = AetherDatabase.getConnection()) {
            c.setAutoCommit(false);
            try (PreparedStatement del = c.prepareStatement("DELETE FROM player_bank_items WHERE LOWER(username)=LOWER(?)")) {
                del.setString(1, username); del.executeUpdate();
            }
            try (PreparedStatement ins = c.prepareStatement("INSERT INTO player_bank_items (username, slot, item_b64) VALUES (?, ?, ?)")) {
                for (int i = 0; i < VAULT_SLOTS; i++) {
                    ItemStack it = inv.getItem(i);
                    if (it != null && it.getType() != Material.AIR) {
                        String b64 = toBase64(it);
                        if (b64 != null) {
                            ins.setString(1, username); ins.setInt(2, i); ins.setString(3, b64);
                            ins.addBatch();
                        }
                    }
                }
                ins.executeBatch();
            }
            c.commit();
        } catch (Exception e) {
            plugin.getLogger().warning("[AetherBank] Erreur sauvegarde coffre: " + e.getMessage());
        }
    }

    private static String toBase64(ItemStack item) {
        try (ByteArrayOutputStream bos = new ByteArrayOutputStream(); BukkitObjectOutputStream out = new BukkitObjectOutputStream(bos)) {
            out.writeObject(item);
            return Base64.getEncoder().encodeToString(bos.toByteArray());
        } catch (Exception e) { return null; }
    }

    private static ItemStack fromBase64(String b64) {
        if (b64 == null || b64.isEmpty()) return null;
        try (ByteArrayInputStream bis = new ByteArrayInputStream(Base64.getDecoder().decode(b64)); BukkitObjectInputStream in = new BukkitObjectInputStream(bis)) {
            return (ItemStack) in.readObject();
        } catch (Exception e) { return null; }
    }

    private static ItemStack makeBtn(Material mat, String name, String... lore) {
        ItemStack it = new ItemStack(mat);
        ItemMeta m = it.getItemMeta();
        if (m != null) { m.setDisplayName(name); if (lore.length > 0) m.setLore(Arrays.asList(lore)); it.setItemMeta(m); }
        return it;
    }
}
