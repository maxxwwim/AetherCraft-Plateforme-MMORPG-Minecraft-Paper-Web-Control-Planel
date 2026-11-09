package io.aethercraft.visuals;

import io.aethercraft.visuals.AetherShopGUI.ShopArticle;
import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.inventory.ItemStack;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.util.ArrayList;
import java.util.List;

/**
 * Catalogue des articles de la boutique AetherShopGUI et mise à jour SQLite des grades.
 */
public class AetherShopCatalog {

    public static List<ShopArticle> getAllArticles(AetherVisualsPlugin plugin) {
        List<ShopArticle> list = new ArrayList<>();

        // Magots, Lingots & Blocs d'Argent convertibles (Style Habbo Hotel - 100% Pièces ⛃)
        list.add(new ShopArticle("magot_piece_bronze", "magots", "§6§l🪙 Pièce de Bronze §8[§e10 ⛃§8]", 10.0,
                PetItemFactory.createHabboBullionItem("magot_piece_bronze", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("magot_piece_bronze", 1))));
        list.add(new ShopArticle("magot_piece_argent", "magots", "§f§l🪙 Pièce d'Argent §8[§e50 ⛃§8]", 50.0,
                PetItemFactory.createHabboBullionItem("magot_piece_argent", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("magot_piece_argent", 1))));
        list.add(new ShopArticle("magot_sac_pieces", "magots", "§e§l💰 Sac de Pièces §8[§6100 ⛃§8]", 100.0,
                PetItemFactory.createHabboBullionItem("magot_sac_pieces", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("magot_sac_pieces", 1))));
        list.add(new ShopArticle("magot_lingot_or", "magots", "§6§l🧈 Lingot d'Or Habbo §8[§6250 ⛃§8]", 250.0,
                PetItemFactory.createHabboBullionItem("magot_lingot_or", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("magot_lingot_or", 1))));
        list.add(new ShopArticle("magot_bloc_or", "magots", "§6§l🟨 Bloc d'Or Impérial §8[§6500 ⛃§8]", 500.0,
                PetItemFactory.createHabboBullionItem("magot_bloc_or", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("magot_bloc_or", 1))));
        list.add(new ShopArticle("magot_bloc_emeraude", "magots", "§a§l🟩 Magot Émeraude §8[§21 000 ⛃§8]", 1000.0,
                PetItemFactory.createHabboBullionItem("magot_bloc_emeraude", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("magot_bloc_emeraude", 1))));
        list.add(new ShopArticle("magot_bloc_diamant", "magots", "§b§l🔷 Magot Diamant §8[§32 500 ⛃§8]", 2500.0,
                PetItemFactory.createHabboBullionItem("magot_bloc_diamant", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("magot_bloc_diamant", 1))));
        list.add(new ShopArticle("magot_trophee_or", "magots", "§6§l🏆 Trophée d'Or Champion §8[§e5 000 ⛃§8]", 5000.0,
                PetItemFactory.createHabboBullionItem("magot_trophee_or", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("magot_trophee_or", 1))));
        list.add(new ShopArticle("magot_trone_royal", "magots", "§5§l👑 Trône Royal Céleste §8[§d10 000 ⛃§8]", 10000.0,
                PetItemFactory.createHabboBullionItem("magot_trone_royal", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("magot_trone_royal", 1))));
        list.add(new ShopArticle("bloc_aether", "magots", "§b§l🌌 Bloc Céleste Aether §8[§31 500 ⛃§8]", 1500.0,
                PetItemFactory.createHabboBullionItem("bloc_aether", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("bloc_aether", 1))));
        list.add(new ShopArticle("minerai_aether", "magots", "§3§l☄️ Minerai Aether Nether §8[§b750 ⛃§8]", 750.0,
                PetItemFactory.createHabboBullionItem("minerai_aether", 1),
                (p, pl) -> p.getInventory().addItem(PetItemFactory.createHabboBullionItem("minerai_aether", 1))));

        list.add(new ShopArticle("rank_vip", "ranks", ChatColor.GOLD + "" + ChatColor.BOLD + "👑 Grade VIP", 500.0,
                CustomItemFactory.createVipCrown(),
                (p, pl) -> {
                    Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "lp user " + p.getName() + " parent add vip");
                    updatePlayerRankDB(pl, p.getName(), "VIP");
                    p.getInventory().addItem(CustomItemFactory.createVipCrown());
                    Bukkit.broadcastMessage(ChatColor.GOLD + "★ " + ChatColor.WHITE + p.getName() + ChatColor.YELLOW + " a débloqué le grade " + ChatColor.GREEN + "[VIP]" + ChatColor.YELLOW + " dans la Boutique !");
                }));

        list.add(new ShopArticle("rank_aether", "ranks", ChatColor.AQUA + "" + ChatColor.BOLD + "🪐 Grade AETHER", 1200.0,
                CustomItemFactory.createAetherSeal(),
                (p, pl) -> {
                    Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "lp user " + p.getName() + " parent add aether");
                    updatePlayerRankDB(pl, p.getName(), "AETHER");
                    p.getInventory().addItem(CustomItemFactory.createAetherSeal());
                    Bukkit.broadcastMessage(ChatColor.AQUA + "✦ " + ChatColor.WHITE + p.getName() + ChatColor.AQUA + " a rejoint le rang suprême " + ChatColor.AQUA + "[AETHER]" + ChatColor.AQUA + " !");
                }));

        list.add(new ShopArticle("rank_titan", "ranks", ChatColor.GOLD + "" + ChatColor.BOLD + "⚡ Grade TITAN", 2500.0,
                CustomItemFactory.createTitanCrest(),
                (p, pl) -> {
                    Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "lp user " + p.getName() + " parent add titan");
                    updatePlayerRankDB(pl, p.getName(), "TITAN");
                    p.getInventory().addItem(CustomItemFactory.createTitanCrest());
                    Bukkit.broadcastMessage(ChatColor.GOLD + "⚡ " + ChatColor.WHITE + p.getName() + ChatColor.GOLD + " a atteint le rang légendaire " + ChatColor.GOLD + "[TITAN]" + ChatColor.GOLD + " !");
                }));

        list.add(new ShopArticle("rank_champion", "ranks", ChatColor.LIGHT_PURPLE + "" + ChatColor.BOLD + "🏆 Grade CHAMPION", 5000.0,
                CustomItemFactory.createChampionRelic(),
                (p, pl) -> {
                    Bukkit.dispatchCommand(Bukkit.getConsoleSender(), "lp user " + p.getName() + " parent add champion");
                    updatePlayerRankDB(pl, p.getName(), "CHAMPION");
                    p.getInventory().addItem(CustomItemFactory.createChampionRelic());
                    Bukkit.broadcastMessage(ChatColor.LIGHT_PURPLE + "🏆 " + ChatColor.GOLD + "PROCLAMATION ROYALE : " + ChatColor.WHITE + p.getName() + ChatColor.LIGHT_PURPLE + " est sacré CHAMPION du Royaume !");
                }));

        list.add(new ShopArticle("key_celestial_5", "keys", ChatColor.LIGHT_PURPLE + "" + ChatColor.BOLD + "🗝️ Clés Célestes (x5)", 350.0,
                CustomItemFactory.createCelestialKey(5),
                (p, pl) -> p.getInventory().addItem(CustomItemFactory.createCelestialKey(5))));

        list.add(new ShopArticle("key_omega_12", "keys", ChatColor.RED + "" + ChatColor.BOLD + "💎 Clés Oméga Suprêmes (x12)", 800.0,
                CustomItemFactory.createOmegaKey(12),
                (p, pl) -> p.getInventory().addItem(CustomItemFactory.createOmegaKey(12))));

        list.add(new ShopArticle("wings_quantum", "cosmetics", ChatColor.AQUA + "" + ChatColor.BOLD + "🪽 Ailes Quantiques d'Archipel", 1500.0,
                CustomItemFactory.createQuantumWingsItem(),
                (p, pl) -> {
                    pl.getCosmeticsEngine().setWings(p.getUniqueId(), true);
                    p.getInventory().addItem(CustomItemFactory.createQuantumWingsItem());
                }));

        list.add(new ShopArticle("aura_champion", "cosmetics", ChatColor.GOLD + "" + ChatColor.BOLD + "✨ Aura Rayonnante Divine", 900.0,
                CustomItemFactory.createChampionAuraItem(),
                (p, pl) -> {
                    pl.getCosmeticsEngine().setAura(p.getUniqueId(), "champion");
                    p.getInventory().addItem(CustomItemFactory.createChampionAuraItem());
                }));

        list.add(new ShopArticle("pet_dragon", "pets", ChatColor.LIGHT_PURPLE + "" + ChatColor.BOLD + "🐉 Dragoneau Céleste", 1800.0,
                CustomItemFactory.createDragonPetItem(),
                (p, pl) -> {
                    pl.getCosmeticsEngine().setPet(p.getUniqueId(), "dragon");
                    p.getInventory().addItem(CustomItemFactory.createDragonPetItem());
                }));

        list.add(new ShopArticle("pet_capybara", "pets", ChatColor.GOLD + "" + ChatColor.BOLD + "🦦 Capybara Zen de Sérénité", 1400.0,
                CustomItemFactory.createCapybaraPetItem(),
                (p, pl) -> {
                    pl.getCosmeticsEngine().setPet(p.getUniqueId(), "capybara");
                    p.getInventory().addItem(CustomItemFactory.createCapybaraPetItem());
                }));

        list.add(new ShopArticle("pet_fox", "pets", ChatColor.GOLD + "" + ChatColor.BOLD + "🦊 Renard Cosmique", 1400.0,
                CustomItemFactory.createFoxPetItem(),
                (p, pl) -> {
                    pl.getCosmeticsEngine().setPet(p.getUniqueId(), "fox");
                    p.getInventory().addItem(CustomItemFactory.createFoxPetItem());
                }));

        list.add(new ShopArticle("pet_goat", "pets", ChatColor.WHITE + "" + ChatColor.BOLD + "🐐 Bélier des Cimes Éthérées", 1600.0,
                CustomItemFactory.createGoatPetItem(),
                (p, pl) -> {
                    pl.getCosmeticsEngine().setPet(p.getUniqueId(), "goat");
                    p.getInventory().addItem(CustomItemFactory.createGoatPetItem());
                }));

        list.add(new ShopArticle("pet_phoenix", "pets", ChatColor.RED + "" + ChatColor.BOLD + "🔥 Phénix Immortel Flamboyant", 2200.0,
                CustomItemFactory.createPhoenixPetItem(),
                (p, pl) -> {
                    pl.getCosmeticsEngine().setPet(p.getUniqueId(), "phoenix");
                    p.getInventory().addItem(CustomItemFactory.createPhoenixPetItem());
                }));

        list.add(new ShopArticle("pet_griffin", "pets", ChatColor.GOLD + "" + ChatColor.BOLD + "🦁 Griffon Astral Souverain", 2400.0,
                CustomItemFactory.createGriffinPetItem(),
                (p, pl) -> {
                    pl.getCosmeticsEngine().setPet(p.getUniqueId(), "griffin");
                    p.getInventory().addItem(CustomItemFactory.createGriffinPetItem());
                }));

        list.add(new ShopArticle("booster_mining", "boosters", ChatColor.GREEN + "" + ChatColor.BOLD + "⛏️ Booster Minage x2 (1 Heure)", 400.0,
                CustomItemFactory.createMiningBoosterItem(),
                (p, pl) -> {
                    pl.getBoosterEngine().addMiningBooster(p.getUniqueId(), 3600);
                    p.getInventory().addItem(CustomItemFactory.createMiningBoosterItem());
                }));

        list.add(new ShopArticle("dungeon_pass_3", "boosters", ChatColor.RED + "" + ChatColor.BOLD + "🎫 Pass Donjon Céleste (x3)", 300.0,
                CustomItemFactory.createDungeonPass(3),
                (p, pl) -> p.getInventory().addItem(CustomItemFactory.createDungeonPass(3))));

        return list;
    }

    public static List<ShopArticle> getArticlesForCategory(AetherVisualsPlugin plugin, String cat) {
        List<ShopArticle> all = getAllArticles(plugin);
        if (cat == null || cat.equals("all")) return all;
        List<ShopArticle> filtered = new ArrayList<>();
        for (ShopArticle a : all) {
            if (a.category.equalsIgnoreCase(cat)) filtered.add(a);
        }
        return filtered;
    }

    public static ShopArticle findArticleByItem(AetherVisualsPlugin plugin, ItemStack item) {
        if (item == null || !item.hasItemMeta() || item.getItemMeta().getDisplayName() == null) return null;
        int itemCmd = item.getItemMeta().hasCustomModelData() ? item.getItemMeta().getCustomModelData() : -1;
        String name = ChatColor.stripColor(item.getItemMeta().getDisplayName());

        for (ShopArticle a : getAllArticles(plugin)) {
            if (itemCmd > 0 && a.baseIcon != null && a.baseIcon.hasItemMeta() && a.baseIcon.getItemMeta().hasCustomModelData()) {
                if (a.baseIcon.getItemMeta().getCustomModelData() == itemCmd) {
                    return a;
                }
            }
            String artName = ChatColor.stripColor(a.displayName);
            if (name.equalsIgnoreCase(artName) || name.contains(artName) || artName.contains(name)) {
                return a;
            }
        }
        return null;
    }

    public static void updatePlayerRankDB(AetherVisualsPlugin plugin, String username, String rank) {
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = AetherDatabase.getConnection();
                 PreparedStatement ps = conn.prepareStatement("UPDATE players SET rank = ? WHERE LOWER(username) = LOWER(?);")) {
                ps.setString(1, rank);
                ps.setString(2, username);
                ps.executeUpdate();
            } catch (Exception e) {
                plugin.getLogger().warning("Erreur mise à jour rank: " + e.getMessage());
            }
        });
    }
}
