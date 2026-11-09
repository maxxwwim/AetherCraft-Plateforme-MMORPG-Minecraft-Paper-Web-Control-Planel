package io.aethercraft.visuals;

import org.bukkit.ChatColor;
import org.bukkit.Material;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

/**
 * Fabrique des Familiers Célestes et des Magots / Lingots / Blocs d'Argent convertibles (Style Habbo Hotel).
 */
public class PetItemFactory {

    public static ItemStack createCapybaraPetItem() {
        return makePet(ChatColor.GREEN + "" + ChatColor.BOLD + "🐾 Capybara Céleste", "Gardien de la Sérénité",
                ChatColor.GREEN + "✦ " + ChatColor.WHITE + "Aura Apaisement : " + ChatColor.AQUA + "Régénération I de groupe",
                ChatColor.GREEN + "✦ " + ChatColor.WHITE + "Repousse les monstres nocturnes", 3003);
    }

    public static ItemStack createFoxPetItem() {
        return makePet(ChatColor.GOLD + "" + ChatColor.BOLD + "🦊 Renard Astral", "Kitsune Lunaire",
                ChatColor.GOLD + "✦ " + ChatColor.WHITE + "Aura Prospérité : " + ChatColor.YELLOW + "+10% Pièces d'or troc",
                ChatColor.GOLD + "✦ " + ChatColor.WHITE + "3 Queues de comètes scintillantes", 3004);
    }

    public static ItemStack createGoatPetItem() {
        return makePet(ChatColor.AQUA + "" + ChatColor.BOLD + "🐐 Bélier des Nuages", "Compagnon Aérien des Cieux",
                ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Aura Saut : " + ChatColor.GREEN + "Saut II & No Fall Damage",
                ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Nuages vaporeux sous les sabots", 3005);
    }

    public static ItemStack createPhoenixPetItem() {
        return makePet(ChatColor.RED + "" + ChatColor.BOLD + "🦅 Phénix d'Or Primordial", "Oiseau de Renaissance",
                ChatColor.RED + "✦ " + ChatColor.WHITE + "Aura Renaissance : " + ChatColor.GOLD + "Seconde Chance & Résist Feu",
                ChatColor.RED + "✦ " + ChatColor.WHITE + "Ailes solaires incandescentes d'étincelles", 3006);
    }

    public static ItemStack createGriffinPetItem() {
        return makePet(ChatColor.GOLD + "" + ChatColor.BOLD + "🦁 Griffon Astral", "Souverain des Cieux",
                ChatColor.GOLD + "✦ " + ChatColor.WHITE + "Aura Force : " + ChatColor.YELLOW + "Force I & Vitesse d'attaque",
                ChatColor.GOLD + "✦ " + ChatColor.WHITE + "4 Pattes griffues et ailes de cristal 3D", 3008);
    }

    private static ItemStack makePet(String name, String sub, String l1, String l2, int cmd) {
        ItemStack item = new ItemStack(Material.HEART_OF_THE_SEA);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(name);
            meta.setLore(Arrays.asList(ChatColor.DARK_GRAY + sub, "", l1, l2, "", ChatColor.GOLD + "⭐ " + ChatColor.ITALIC + "Boutique Officielle AetherCraft"));
            meta.setCustomModelData(cmd);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createPetItemByType(String type) {
        if (type == null) return CustomItemFactory.createDragonPetItem();
        return switch (type.toLowerCase(Locale.ROOT)) {
            case "capybara" -> createCapybaraPetItem();
            case "fox" -> createFoxPetItem();
            case "goat" -> createGoatPetItem();
            case "phoenix" -> createPhoenixPetItem();
            case "griffin" -> createGriffinPetItem();
            default -> CustomItemFactory.createDragonPetItem();
        };
    }

    /**
     * Crée un Magot / Lingot / Bloc d'Argent Habbo Hotel convertible à 100% en Pièces (⛃).
     */
    public static ItemStack createHabboBullionItem(String itemId, int amount) {
        String id = itemId == null ? "magot_lingot_or" : itemId.toLowerCase(Locale.ROOT);
        int qty = Math.max(1, amount);
        return switch (id) {
            case "magot_piece_bronze" -> makeBullion(Material.COPPER_INGOT, qty, 6001, 10,
                    "§6§l🪙 Pièce de Bronze §8[§e10 ⛃§8]", "Monnaie Physique Convertible (Habbo)");
            case "magot_piece_argent" -> makeBullion(Material.IRON_INGOT, qty, 6002, 50,
                    "§f§l🪙 Pièce d'Argent Royale §8[§e50 ⛃§8]", "Monnaie Physique Convertible (Habbo)");
            case "magot_sac_pieces" -> makeBullion(Material.RAW_GOLD_BLOCK, qty, 6003, 100,
                    "§e§l💰 Sac de Pièces d'Or §8[§6100 ⛃§8]", "Bloc d'Argent Convertible (Habbo)");
            case "magot_bloc_or" -> makeBullion(Material.GOLD_BLOCK, qty, 6005, 500,
                    "§6§l🟨 Bloc d'Or Impérial §8[§6500 ⛃§8]", "Bloc d'Argent Haute Valeur (Habbo)");
            case "magot_bloc_emeraude" -> makeBullion(Material.EMERALD_BLOCK, qty, 6006, 1000,
                    "§a§l🟩 Magot Bloc d'Émeraude §8[§21 000 ⛃§8]", "Magot Suprême Convertible (Habbo)");
            case "magot_bloc_diamant" -> makeBullion(Material.DIAMOND_BLOCK, qty, 6007, 2500,
                    "§b§l🔷 Magot Bloc de Diamant §8[§32 500 ⛃§8]", "Bloc Précieux Convertible (Habbo)");
            case "magot_trophee_or", "trophee_or", "trophee_champion" -> makeBullion(Material.BEACON, qty, 6008, 5000,
                    "§6§l🏆 Trophée d'Or de Champion §8[§e5 000 ⛃§8]", "Mobilier d'Honneur Convertible (Habbo)");
            case "magot_trone_royal", "trone_royal", "mobilier_trone_habbo" -> makeBullion(Material.GILDED_BLACKSTONE, qty, 6009, 10000,
                    "§5§l👑 Trône Royal Céleste §8[§d10 000 ⛃§8]", "Mobilier Royal Suprême (Habbo)");
            case "bloc_aether", "aether_block" -> makeBullion(Material.SEA_LANTERN, qty, 6010, 1500,
                    "§b§l🌌 Bloc Céleste d'Aether §8[§31 500 ⛃§8]", "Bloc Stellaire Posable & Convertible (Aether)");
            case "minerai_aether", "aether_ore" -> makeBullion(Material.ANCIENT_DEBRIS, qty, 6011, 750,
                    "§3§l☄️ Minerai d'Aether du Nether §8[§b750 ⛃§8]", "Filon Minéral du Nether Convertible (Aether)");
            default -> makeBullion(Material.GOLD_INGOT, qty, 6004, 250,
                    "§6§l🧈 Lingot d'Or Habbo §8[§6250 ⛃§8]", "Lingot d'Or Convertible (Habbo)");
        };
    }

    private static ItemStack makeBullion(Material mat, int qty, int cmd, int coinsValue, String title, String sub) {
        ItemStack item = new ItemStack(mat, qty);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(title);
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + sub);
            lore.add("");
            lore.add("§e✦ §fValeur garantie : §6§l" + coinsValue + " ⛃ Pièces");
            lore.add("§e✦ §fStockable en §b/banque §fou échangeable entre joueurs");
            lore.add("");
            lore.add("§a▶ Clic-Droit en main : §fConvertir en §6+" + coinsValue + " ⛃ Pièces");
            lore.add("§b▶ Sneak + Clic-Droit : §fConvertir toute la pile");
            lore.add("§e▶ Poser au sol : §fMobilier 3D d'Archipel");
            meta.setLore(lore);
            meta.setCustomModelData(cmd);
            meta.addItemFlags(ItemFlag.HIDE_ENCHANTS, ItemFlag.HIDE_ATTRIBUTES);
            item.setItemMeta(meta);
            item.addUnsafeEnchantment(Enchantment.LUCK_OF_THE_SEA, 1);
        }
        return item;
    }

    public static int getBullionCoinValue(int customModelData) {
        return switch (customModelData) {
            case 6001 -> 10;
            case 6002 -> 50;
            case 6003 -> 100;
            case 6004 -> 250;
            case 6005 -> 500;
            case 6006 -> 1000;
            case 6007 -> 2500;
            case 6008 -> 5000;
            case 6009 -> 10000;
            case 6010 -> 1500;
            case 6011 -> 750;
            default -> 0;
        };
    }

    /**
     * Vérifie si un itemstack correspond à un Magot / Lingot / Pièce de monnaie Habbo (CustomModelData 6001 à 6006).
     */
    public static boolean isBullionCoin(ItemStack item) {
        if (item == null || !item.hasItemMeta()) return false;
        ItemMeta meta = item.getItemMeta();
        if (!meta.hasCustomModelData()) return false;
        return getBullionCoinValue(meta.getCustomModelData()) > 0;
    }

    /**
     * Vérifie si un itemstack est une pièce "solide" physique non sous forme de bloc (ex: Pièce Bronze, Pièce Argent, Lingot d'Or).
     */
    public static boolean isSolidCoin(ItemStack item) {
        if (item == null || !item.hasItemMeta()) return false;
        ItemMeta meta = item.getItemMeta();
        if (!meta.hasCustomModelData()) return false;
        int cmd = meta.getCustomModelData();
        return cmd == 6001 || cmd == 6002 || cmd == 6004;
    }
}
