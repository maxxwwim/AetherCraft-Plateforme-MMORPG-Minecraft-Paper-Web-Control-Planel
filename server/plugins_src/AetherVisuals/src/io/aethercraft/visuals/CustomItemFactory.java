package io.aethercraft.visuals;

import org.bukkit.ChatColor;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;
import java.util.ArrayList;
import java.util.List;

public class CustomItemFactory {

    public static ItemStack createVipCrown() {
        ItemStack item = new ItemStack(Material.GOLDEN_HELMET);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.GOLD + "" + ChatColor.BOLD + "👑 Couronne Royale VIP");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Artefact de Prestige");
            lore.add("");
            lore.add(ChatColor.YELLOW + "✦ " + ChatColor.WHITE + "Préfixe " + ChatColor.GREEN + "[VIP]" + ChatColor.WHITE + " dans le chat");
            lore.add(ChatColor.YELLOW + "✦ " + ChatColor.WHITE + "Aura d'émeraudes & or tournoyante");
            lore.add(ChatColor.YELLOW + "✦ " + ChatColor.WHITE + "Commandes " + ChatColor.AQUA + "/fly" + ChatColor.WHITE + " et " + ChatColor.AQUA + "/feed");
            lore.add("");
            lore.add(ChatColor.GOLD + "⭐ " + ChatColor.ITALIC + "Boutique Officielle AetherCraft");
            meta.setLore(lore);
            meta.setCustomModelData(1001);
            meta.setUnbreakable(true);
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES, ItemFlag.HIDE_UNBREAKABLE);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createAetherSeal() {
        ItemStack item = new ItemStack(Material.NETHER_STAR);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.AQUA + "" + ChatColor.BOLD + "🪐 Sceau Céleste d'Aether");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Artefact Stellaire des Héros");
            lore.add("");
            lore.add(ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Préfixe " + ChatColor.AQUA + "[AETHER]" + ChatColor.WHITE + " animé");
            lore.add(ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Halo cosmique et orbite d'étoiles");
            lore.add(ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Commandes " + ChatColor.GREEN + "/fly" + ChatColor.WHITE + " et " + ChatColor.GREEN + "/workbench");
            lore.add("");
            lore.add(ChatColor.AQUA + "⭐ " + ChatColor.ITALIC + "Boutique Officielle AetherCraft");
            meta.setLore(lore);
            meta.setCustomModelData(1002);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createTitanCrest() {
        ItemStack item = new ItemStack(Material.MAGMA_CREAM);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.GOLD + "" + ChatColor.BOLD + "⚡ Cimier Flamboyant du Titan");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Puissance Primordiale");
            lore.add("");
            lore.add(ChatColor.GOLD + "✦ " + ChatColor.WHITE + "Préfixe " + ChatColor.GOLD + "[TITAN]" + ChatColor.WHITE + " incandescent");
            lore.add(ChatColor.GOLD + "✦ " + ChatColor.WHITE + "Double hélice de flammes et de lave");
            lore.add(ChatColor.GOLD + "✦ " + ChatColor.WHITE + "Multiplicateur XP x2 permanent");
            lore.add("");
            lore.add(ChatColor.GOLD + "⭐ " + ChatColor.ITALIC + "Boutique Officielle AetherCraft");
            meta.setLore(lore);
            meta.setCustomModelData(1003);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createCelestialKey(int amount) {
        ItemStack item = new ItemStack(Material.TRIPWIRE_HOOK, amount);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.LIGHT_PURPLE + "" + ChatColor.BOLD + "🗝️ Clé de la Caisse Céleste");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Clé Magique Runique");
            lore.add("");
            lore.add(ChatColor.GRAY + "Permet d'ouvrir la " + ChatColor.LIGHT_PURPLE + "Caisse des Étoiles" + ChatColor.GRAY + " au Spawn.");
            lore.add(ChatColor.GRAY + "Tentez de remporter des artéfacts légendaires !");
            lore.add("");
            lore.add(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Clic-droit sur la caisse pour l'ouvrir");
            meta.setLore(lore);
            meta.setCustomModelData(2001);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createOmegaKey(int amount) {
        ItemStack item = new ItemStack(Material.TRIPWIRE_HOOK, amount);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.RED + "" + ChatColor.BOLD + "💎 Clé Oméga Suprême");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Clé Maîtresse Antique");
            lore.add("");
            lore.add(ChatColor.GRAY + "Garantit un butin d'élite ou spawner mythique");
            lore.add(ChatColor.GRAY + "dans la " + ChatColor.RED + "Caisse Oméga" + ChatColor.GRAY + " au Spawn.");
            lore.add("");
            lore.add(ChatColor.RED + "✦ " + ChatColor.WHITE + "Drop Mythique Garanti");
            meta.setLore(lore);
            meta.setCustomModelData(2002);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createQuantumWingsItem() {
        ItemStack item = new ItemStack(Material.FEATHER);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.BLUE + "" + ChatColor.BOLD + "🪽 Ailes Quantiques Stellaires");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Cosmétique Animé 3D");
            lore.add("");
            lore.add(ChatColor.BLUE + "✦ " + ChatColor.WHITE + "Déploie des ailes luminescentes dans votre dos");
            lore.add(ChatColor.BLUE + "✦ " + ChatColor.WHITE + "Battement sinusoïdal et traînée d'étoiles");
            lore.add(ChatColor.BLUE + "✦ " + ChatColor.WHITE + "Activable via " + ChatColor.YELLOW + "/cosmetics wings");
            meta.setLore(lore);
            meta.setCustomModelData(3001);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createDragonPetItem() {
        ItemStack item = new ItemStack(Material.HEART_OF_THE_SEA);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.DARK_PURPLE + "" + ChatColor.BOLD + "🐉 Mini Dragon de l'Aether");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Compagnon Fidèle Animé");
            lore.add("");
            lore.add(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Aura Flamme : " + ChatColor.GOLD + "+15% Minage partagé");
            lore.add(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Vole fidèlement en orbite autour de vous");
            lore.add("");
            lore.add(ChatColor.GOLD + "⭐ " + ChatColor.ITALIC + "Boutique Officielle AetherCraft");
            meta.setLore(lore);
            meta.setCustomModelData(3002);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createCapybaraPetItem() {
        return PetItemFactory.createCapybaraPetItem();
    }

    public static ItemStack createFoxPetItem() {
        return PetItemFactory.createFoxPetItem();
    }

    public static ItemStack createGoatPetItem() {
        return PetItemFactory.createGoatPetItem();
    }

    public static ItemStack createPhoenixPetItem() {
        return PetItemFactory.createPhoenixPetItem();
    }

    public static ItemStack createGriffinPetItem() {
        return PetItemFactory.createGriffinPetItem();
    }

    public static ItemStack createAetherBlockItem(int amount) {
        return PetItemFactory.createHabboBullionItem("bloc_aether", amount);
    }

    public static ItemStack createAetherOreItem(int amount) {
        return PetItemFactory.createHabboBullionItem("minerai_aether", amount);
    }

    public static ItemStack createDiamondBullionBlock(int amount) {
        return PetItemFactory.createHabboBullionItem("magot_bloc_diamant", amount);
    }

    public static ItemStack createHabboTrophyItem(int amount) {
        return PetItemFactory.createHabboBullionItem("magot_trophee_or", amount);
    }

    public static ItemStack createHabboThroneItem(int amount) {
        return PetItemFactory.createHabboBullionItem("magot_trone_royal", amount);
    }

    public static ItemStack createPetItemByType(String type) {
        return PetItemFactory.createPetItemByType(type);
    }

    public static ItemStack createChampionRelic() {
        ItemStack item = new ItemStack(Material.AMETHYST_SHARD);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.LIGHT_PURPLE + "" + ChatColor.BOLD + "👑 Diadème du Champion du Royaume");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Titre Suprême de l'Archipel Céleste");
            lore.add("");
            lore.add(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Préfixe " + ChatColor.LIGHT_PURPLE + "[CHAMPION]" + ChatColor.WHITE + " violet scintillant");
            lore.add(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Aura Royale : Couronne astrale & Sceau céleste");
            lore.add(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Accès illimité aux donjons instanciés");
            lore.add(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Bonus 500k pièces d'or & Ailes Quantiques");
            lore.add("");
            lore.add(ChatColor.GOLD + "⭐ " + ChatColor.ITALIC + "Boutique Officielle AetherCraft (Prestige #1)");
            meta.setLore(lore);
            meta.setCustomModelData(1004);
            meta.addItemFlags(ItemFlag.HIDE_ENCHANTS, ItemFlag.HIDE_ATTRIBUTES);
            item.setItemMeta(meta);
            item.addUnsafeEnchantment(org.bukkit.enchantments.Enchantment.LUCK_OF_THE_SEA, 1);
        }
        return item;
    }

    public static ItemStack createDungeonPass(int amount) {
        ItemStack item = new ItemStack(Material.RECOVERY_COMPASS, amount);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.AQUA + "" + ChatColor.BOLD + "🎫 Pass des Donjons Célestes");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Jeton d'Expédition Instanciée");
            lore.add("");
            lore.add(ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Accès aux donjons instanciés sans mod");
            lore.add(ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Affrontez les Boss mythiques de l'Archipel");
            lore.add(ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Butins : Fragments d'Aetherite & Reliques");
            lore.add("");
            lore.add(ChatColor.GOLD + "✦ " + ChatColor.YELLOW + "Clic-droit au Portail des Donjons pour consommer");
            meta.setLore(lore);
            meta.setCustomModelData(2003);
            meta.addItemFlags(ItemFlag.HIDE_ENCHANTS, ItemFlag.HIDE_ATTRIBUTES);
            item.setItemMeta(meta);
            item.addUnsafeEnchantment(org.bukkit.enchantments.Enchantment.LUCK_OF_THE_SEA, 1);
        }
        return item;
    }

    public static ItemStack createChampionAuraItem() {
        ItemStack item = new ItemStack(Material.ECHO_SHARD);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.DARK_PURPLE + "" + ChatColor.BOLD + "✨ Sceau de l'Aura du Champion");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Artefact Cosmétique Royal");
            lore.add("");
            lore.add(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Couronne de lumière & Sceau au sol");
            lore.add(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Visible par tous les joueurs à 20 TPS");
            lore.add(ChatColor.LIGHT_PURPLE + "✦ " + ChatColor.WHITE + "Clic-droit pour activer / désactiver");
            lore.add("");
            lore.add(ChatColor.GOLD + "⭐ " + ChatColor.ITALIC + "Boutique Officielle AetherCraft");
            meta.setLore(lore);
            meta.setCustomModelData(3007);
            meta.addItemFlags(ItemFlag.HIDE_ENCHANTS, ItemFlag.HIDE_ATTRIBUTES);
            item.setItemMeta(meta);
            item.addUnsafeEnchantment(org.bukkit.enchantments.Enchantment.LUCK_OF_THE_SEA, 1);
        }
        return item;
    }

    public static ItemStack createItemById(String itemId, int amount) {
        if (itemId == null) return createVipCrown();
        int qty = Math.max(1, amount);
        switch (itemId.toLowerCase()) {
            case "rank_vip": return createVipCrown();
            case "rank_aether": return createAetherSeal();
            case "rank_titan": return createTitanCrest();
            case "rank_champion": return createChampionRelic();
            case "key_mystic_bundle": return createCelestialKey(qty <= 1 ? 5 : qty);
            case "key_omega_bundle": return createOmegaKey(qty <= 1 ? 12 : qty);
            case "dungeon_pass_bundle": return createDungeonPass(qty <= 1 ? 3 : qty);
            case "cosmetic_wings": return createQuantumWingsItem();
            case "aura_champion": return createChampionAuraItem();
            case "booster_mining": return createMiningBoosterItem();
            case "pet_dragon": return createDragonPetItem();
            case "pet_capybara": return createCapybaraPetItem();
            case "pet_fox": return createFoxPetItem();
            case "pet_goat": return createGoatPetItem();
            case "pet_phoenix": return createPhoenixPetItem();
            case "pet_griffin": return createGriffinPetItem();
            case "magot_bloc_diamant": return createDiamondBullionBlock(qty);
            case "magot_trophee_or":
            case "trophee_or":
            case "trophee_champion": return createHabboTrophyItem(qty);
            case "magot_trone_royal":
            case "trone_royal":
            case "mobilier_trone_habbo": return createHabboThroneItem(qty);
            case "bloc_aether":
            case "aether_block": return createAetherBlockItem(qty);
            case "minerai_aether":
            case "aether_ore": return createAetherOreItem(qty);
            case "animal_cow": return createAnimalEggItem(Material.COW_SPAWN_EGG, "Couple de Vaches", "Élevage & Production Lait/Cuir", qty <= 1 ? 2 : qty);
            case "animal_sheep": return createAnimalEggItem(Material.SHEEP_SPAWN_EGG, "Couple de Moutons", "Production Laine Colorée", qty <= 1 ? 2 : qty);
            case "animal_pig": return createAnimalEggItem(Material.PIG_SPAWN_EGG, "Couple de Cochons", "Élevage & Viande OneBlock", qty <= 1 ? 2 : qty);
            case "animal_chicken": return createAnimalEggItem(Material.CHICKEN_SPAWN_EGG, "Couple de Poules", "Production Œufs & Plumes", qty <= 1 ? 2 : qty);
            case "animal_wolf": return createAnimalEggItem(Material.WOLF_SPAWN_EGG, "Loup Domestique", "Fidèle Gardien & Chasseur", qty <= 1 ? 1 : qty);
            case "animal_horse": return createAnimalEggItem(Material.HORSE_SPAWN_EGG, "Cheval Pur-Sang", "Monture Rapide Céleste", qty <= 1 ? 1 : qty);
            case "animal_bee": return createAnimalEggItem(Material.BEE_SPAWN_EGG, "Essaim d'Abeilles", "Pollinisation & Ruche", qty <= 1 ? 2 : qty);
            case "phone":
            case "aether_phone":
            case "aetherphone":
            case "smartphone":
                return createAetherPhoneItem();
            default:
                String low = itemId.toLowerCase();
                if (low.startsWith("magot_") || low.startsWith("lingot_") || low.contains("bloc")
                        || low.contains("aether") || low.contains("ore") || low.contains("trophee")
                        || low.contains("trone") || low.contains("furniture")) {
                    return PetItemFactory.createHabboBullionItem(itemId, qty);
                }
                if (low.startsWith("pet_")) {
                    return createPetItemByType(low.substring(4));
                }
                return createVipCrown();
        }
    }

    public static ItemStack createMiningBoosterItem() {
        ItemStack item = new ItemStack(Material.GOLDEN_PICKAXE);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.GOLD + "" + ChatColor.BOLD + "⛏️ Booster de Minage x2");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Consommable d'Énergie");
            lore.add("");
            lore.add(ChatColor.YELLOW + "✦ " + ChatColor.WHITE + "Double tous vos drops de minerais");
            lore.add(ChatColor.YELLOW + "✦ " + ChatColor.WHITE + "Particules dorées et son de résonance au minage");
            lore.add(ChatColor.YELLOW + "✦ " + ChatColor.WHITE + "Durée active : " + ChatColor.GOLD + "2 Heures");
            meta.setLore(lore);
            meta.setCustomModelData(4001);
            meta.setUnbreakable(true);
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES, ItemFlag.HIDE_UNBREAKABLE);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createAnimalEggItem(Material eggMat, String name, String subtitle, int qty) {
        ItemStack item = new ItemStack(eggMat, Math.max(1, qty));
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.GREEN + "" + ChatColor.BOLD + "🐾 " + name);
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + subtitle);
            lore.add("");
            lore.add(ChatColor.YELLOW + "✦ " + ChatColor.WHITE + "Faune & Élevage OneBlock");
            lore.add(ChatColor.YELLOW + "✦ " + ChatColor.WHITE + "Faites un Clic Droit au sol pour faire apparaître");
            lore.add("");
            lore.add(ChatColor.GOLD + "⭐ " + ChatColor.ITALIC + "AetherCraft Animalerie");
            meta.setLore(lore);
            item.setItemMeta(meta);
        }
        return item;
    }

    public static ItemStack createAetherPhoneItem() {
        ItemStack item = new ItemStack(Material.WARPED_FUNGUS_ON_A_STICK);
        ItemMeta meta = item.getItemMeta();
        if (meta != null) {
            meta.setDisplayName(ChatColor.GOLD + "" + ChatColor.BOLD + "📱 AetherPhone Ultra");
            List<String> lore = new ArrayList<>();
            lore.add(ChatColor.DARK_GRAY + "Interface Holographique Personnelle");
            lore.add("");
            lore.add(ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Résolution 16/9 Haute Définition");
            lore.add(ChatColor.AQUA + "✦ " + ChatColor.WHITE + "Accès Banque, Boutique, Bourse & Profil");
            lore.add(ChatColor.AQUA + "✦ " + ChatColor.GREEN + "Incassable & Éternel");
            lore.add("");
            lore.add(ChatColor.GOLD + "⭐ " + ChatColor.ITALIC + "AetherCraft Technologie");
            meta.setLore(lore);
            meta.setCustomModelData(5001);
            meta.setUnbreakable(true);
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES, ItemFlag.HIDE_UNBREAKABLE);

            NamespacedKey key = new NamespacedKey("aethercraft", "aether_phone_unbreakable");
            meta.getPersistentDataContainer().set(key, PersistentDataType.BYTE, (byte) 1);
            item.setItemMeta(meta);
        }
        return item;
    }
}
