package io.aethercraft.visuals;

import org.bukkit.ChatColor;
import org.bukkit.Location;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;

import java.sql.Connection;
import java.sql.PreparedStatement;

public class StoreItemInteractListener implements Listener {

    private final AetherVisualsPlugin plugin;
    private final CosmeticsEngine cosmeticsEngine;
    private final BoosterEngine boosterEngine;
    private final CrateEngine crateEngine;

    public StoreItemInteractListener(AetherVisualsPlugin plugin, CosmeticsEngine cosmeticsEngine, BoosterEngine boosterEngine, CrateEngine crateEngine) {
        this.plugin = plugin;
        this.cosmeticsEngine = cosmeticsEngine;
        this.boosterEngine = boosterEngine;
        this.crateEngine = crateEngine;
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onMagotBlockPlace(BlockPlaceEvent event) {
        ItemStack item = event.getItemInHand();
        if (item != null && item.hasItemMeta() && item.getItemMeta().hasCustomModelData()) {
            int cmd = item.getItemMeta().getCustomModelData();
            if (PetItemFactory.getBullionCoinValue(cmd) > 0) {
                // Ne pas annuler la pose quand l'objet est posé via ou géré par HabboBullionBlockEngine
                return;
            }
        }
    }

    @EventHandler
    public void onPlayerInteract(PlayerInteractEvent event) {
        Action action = event.getAction();
        if (action != Action.RIGHT_CLICK_AIR && action != Action.RIGHT_CLICK_BLOCK) return;

        ItemStack item = event.getItem();
        if (item == null || !item.hasItemMeta()) return;
        ItemMeta meta = item.getItemMeta();
        if (!meta.hasCustomModelData()) return;

        int modelData = meta.getCustomModelData();
        Player p = event.getPlayer();
        Location loc = p.getLocation();

        // Conversion instantanée d'un Magot / Lingot Habbo en Pièces (⛃) en l'air
        // Sur un bloc (RIGHT_CLICK_BLOCK), HabboBullionBlockEngine gère la pose du mobilier
        int bullionCoins = PetItemFactory.getBullionCoinValue(modelData);
        if (bullionCoins > 0) {
            if (action == Action.RIGHT_CLICK_AIR) {
                event.setCancelled(true);
                redeemHabboBullion(p, item, bullionCoins);
            }
            return;
        }

        switch (modelData) {
            case 1001 -> {
                cosmeticsEngine.setAura(p.getUniqueId(), "vip");
                p.playSound(loc, Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.2f);
                p.spawnParticle(Particle.HAPPY_VILLAGER, loc.add(0, 1.5, 0), 20, 0.4, 0.4, 0.4, 0.1);
                p.sendMessage(ChatColor.GOLD + "👑 " + ChatColor.YELLOW + "Couronne VIP activée ! Préfixe [VIP] & aura émeraude déployés.");
                event.setCancelled(true);
            }
            case 1002 -> {
                cosmeticsEngine.setAura(p.getUniqueId(), "aether");
                p.playSound(loc, Sound.BLOCK_BEACON_ACTIVATE, 1.0f, 1.5f);
                p.spawnParticle(Particle.SOUL_FIRE_FLAME, loc.add(0, 1.5, 0), 25, 0.5, 0.5, 0.5, 0.05);
                p.sendMessage(ChatColor.AQUA + "🪐 " + ChatColor.DARK_AQUA + "Sceau Céleste d'Aether actif ! Halo cosmique et orbite stellaire.");
                event.setCancelled(true);
            }
            case 1003 -> {
                cosmeticsEngine.setAura(p.getUniqueId(), "titan");
                p.playSound(loc, Sound.ENTITY_BLAZE_SHOOT, 1.0f, 0.8f);
                p.spawnParticle(Particle.FLAME, loc.add(0, 1.5, 0), 30, 0.6, 0.6, 0.6, 0.08);
                p.sendMessage(ChatColor.GOLD + "⚡ " + ChatColor.RED + "Cimier Flamboyant du Titan déchaîné ! Double hélice de feu et XP x2.");
                event.setCancelled(true);
            }
            case 1004 -> {
                cosmeticsEngine.setAura(p.getUniqueId(), "champion");
                p.playSound(loc, Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 0.9f);
                p.playSound(loc, Sound.ITEM_TRIDENT_THUNDER, 0.8f, 1.4f);
                p.spawnParticle(Particle.REVERSE_PORTAL, loc.add(0, 1.8, 0), 35, 0.5, 0.8, 0.5, 0.1);
                p.spawnParticle(Particle.END_ROD, loc, 20, 0.4, 0.4, 0.4, 0.05);
                p.sendMessage(ChatColor.LIGHT_PURPLE + "👑 " + ChatColor.GOLD + "DIADÈME DU CHAMPION DU ROYAUME : " + ChatColor.WHITE + "Couronne de lumière et sceau astral sous vos pas !");
                event.setCancelled(true);
            }
            case 2001 -> {
                p.playSound(loc, Sound.BLOCK_ENCHANTMENT_TABLE_USE, 1.0f, 1.2f);
                p.spawnParticle(Particle.ENCHANT, loc.clone().add(0, 1.0, 0), 15, 0.3, 0.3, 0.3, 0.1);
                crateEngine.openKeyInsertionGUI(p, false);
                event.setCancelled(true);
            }
            case 2002 -> {
                p.playSound(loc, Sound.BLOCK_RESPAWN_ANCHOR_CHARGE, 1.0f, 1.0f);
                p.spawnParticle(Particle.CRIT, loc.clone().add(0, 1.0, 0), 20, 0.4, 0.4, 0.4, 0.15);
                crateEngine.openKeyInsertionGUI(p, true);
                event.setCancelled(true);
            }
            case 2003 -> {
                p.playSound(loc, Sound.BLOCK_PORTAL_TRAVEL, 0.8f, 1.4f);
                p.spawnParticle(Particle.PORTAL, loc.add(0, 1.0, 0), 40, 0.6, 0.6, 0.6, 0.2);
                p.sendMessage(ChatColor.AQUA + "🎫 " + ChatColor.WHITE + "Pass Donjon Céleste validé ! Présentez-vous devant le portail des donjons instanciés de l'Agora.");
                event.setCancelled(true);
            }
            case 3001 -> {
                cosmeticsEngine.toggleWings(p.getUniqueId());
                boolean hasWings = cosmeticsEngine.hasWings(p.getUniqueId());
                p.playSound(loc, Sound.ENTITY_ENDER_DRAGON_FLAP, 1.0f, 1.2f);
                p.spawnParticle(Particle.FIREWORK, loc.add(0, 1.0, 0), 15, 0.3, 0.3, 0.3, 0.05);
                p.sendMessage(ChatColor.BLUE + "🪽 " + ChatColor.WHITE + "Ailes Quantiques Stellaires : " + (hasWings ? ChatColor.GREEN + "ACTIVÉES" : ChatColor.RED + "DÉSACTIVÉES"));
                event.setCancelled(true);
            }
            case 3002 -> { togglePet(p, "dragon", ChatColor.DARK_PURPLE + "🐉 Mini Dragon de l'Aether invoqué ! (+15% vitesse minage)", Particle.DRAGON_BREATH); event.setCancelled(true); }
            case 3003 -> { togglePet(p, "capybara", ChatColor.GREEN + "🐾 Capybara Céleste invoqué ! (Régénération I & Sérénité)", Particle.HAPPY_VILLAGER); event.setCancelled(true); }
            case 3004 -> { togglePet(p, "fox", ChatColor.GOLD + "🦊 Renard Astral invoqué ! (+10% pièces d'or & 3 queues comètes)", Particle.SOUL_FIRE_FLAME); event.setCancelled(true); }
            case 3005 -> { togglePet(p, "goat", ChatColor.AQUA + "🐐 Bélier des Nuages invoqué ! (Saut II & Immunité chutes)", Particle.CLOUD); event.setCancelled(true); }
            case 3006 -> { togglePet(p, "phoenix", ChatColor.RED + "🦅 Phénix d'Or Primordial invoqué ! (Seconde Chance & Résist Feu)", Particle.FLAME); event.setCancelled(true); }
            case 3007 -> {
                cosmeticsEngine.setAura(p.getUniqueId(), "champion");
                p.playSound(loc, Sound.BLOCK_BEACON_POWER_SELECT, 1.0f, 1.1f);
                p.spawnParticle(Particle.END_ROD, loc.add(0, 1.0, 0), 30, 0.5, 0.5, 0.5, 0.05);
                p.sendMessage(ChatColor.LIGHT_PURPLE + "✨ " + ChatColor.WHITE + "Aura du Champion Primordial déployée avec succès !");
                event.setCancelled(true);
            }
            case 4001 -> {
                boosterEngine.addMiningBooster(p.getUniqueId(), 7200);
                p.playSound(loc, Sound.ENTITY_PLAYER_LEVELUP, 1.0f, 1.0f);
                p.spawnParticle(Particle.CRIT, loc.add(0, 1.2, 0), 30, 0.5, 0.5, 0.5, 0.1);
                p.sendMessage(ChatColor.GOLD + "⛏️ " + ChatColor.YELLOW + "Booster de Minage Céleste x2 activé pour les 2 prochaines heures !");
                event.setCancelled(true);
            }
            default -> {}
        }
    }

    private void redeemHabboBullion(Player p, ItemStack item, int unitCoins) {
        int qty = p.isSneaking() ? item.getAmount() : 1;
        long totalGain = (long) qty * unitCoins;
        String itemName = (item.getItemMeta() != null && item.getItemMeta().hasDisplayName())
                ? item.getItemMeta().getDisplayName() : "Magot Habbo";

        try (Connection c = AetherDatabase.getConnection();
             PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?)")) {
            ps.setDouble(1, totalGain);
            ps.setString(2, p.getName());
            ps.executeUpdate();
        } catch (Exception e) {
            p.sendMessage("§cErreur SQLite lors de la conversion du magot : " + e.getMessage());
            return;
        }

        if (plugin.getScoreboardManager() != null) {
            plugin.getScoreboardManager().refreshPlayer(p);
        }

        int rem = item.getAmount() - qty;
        if (rem <= 0) {
            p.getInventory().setItemInMainHand(null);
        } else {
            item.setAmount(rem);
        }
        p.playSound(p.getLocation(), Sound.ENTITY_EXPERIENCE_ORB_PICKUP, 1.0f, 1.35f);
        p.playSound(p.getLocation(), Sound.BLOCK_CHAIN_PLACE, 0.85f, 1.6f);
        p.spawnParticle(Particle.TOTEM_OF_UNDYING, p.getLocation().add(0, 1.2, 0), 22, 0.35, 0.45, 0.35, 0.08);
        p.sendMessage("§6§l[🪙 MAGOT HABBO CONVERTI] §aVous avez encaissé §f" + qty + "x " + itemName
                + " §apour §6§l+" + totalGain + " ⛃ Pièces §adans votre bourse !");
    }

    @EventHandler(priority = EventPriority.HIGH)
    public void onPlayerDeath(org.bukkit.event.entity.PlayerDeathEvent event) {
        Player player = event.getEntity();
        if (player == null) return;

        // Règle de gameplay : Perte à la mort uniquement sur les blocs de construction de bâtiments.
        // La banque (solde virtuel) et les pièces/lingots ("pièces solides", magots, monnaie) ne sont JAMAIS perdus.
        // Aucune pénalité de réparation ni dégradation de durabilité sur les lingots/pièces portés.
        // Les items non-blocs tombent au sol et sont ramassables par le joueur lui-même ou n'importe quel autre joueur.
        java.util.List<ItemStack> drops = event.getDrops();
        if (drops != null && !drops.isEmpty()) {
            drops.removeIf(item -> item != null && item.getType().isBlock() && !PetItemFactory.isBullionCoin(item));
        }
    }

    private void togglePet(Player p, String type, String msg, Particle particle) {
        Location loc = p.getLocation();
        if (cosmeticsEngine.hasPet(p.getUniqueId())) {
            cosmeticsEngine.setPet(p.getUniqueId(), null);
            p.playSound(loc, Sound.ENTITY_ITEM_PICKUP, 1.0f, 0.8f);
            p.sendMessage(ChatColor.GRAY + "Familier céleste rengainé.");
        } else {
            cosmeticsEngine.setPet(p.getUniqueId(), type);
            p.playSound(loc, Sound.ENTITY_PLAYER_LEVELUP, 1.0f, 1.3f);
            p.spawnParticle(particle, loc.add(0, 1.2, 0), 25, 0.4, 0.4, 0.4, 0.08);
            p.sendMessage(msg);
        }
    }
}
