package io.aethercraft.visuals;

import net.md_5.bungee.api.ChatMessageType;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.*;
import org.bukkit.entity.*;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.*;
import org.bukkit.event.entity.*;
import org.bukkit.event.hanging.HangingBreakByEntityEvent;
import org.bukkit.event.hanging.HangingPlaceEvent;
import org.bukkit.event.player.*;
import org.bukkit.inventory.ItemStack;

import java.util.Iterator;

public class SpawnProtectionEngine implements Listener {

    public static final int SPAWN1_CENTER_X = 0, SPAWN1_CENTER_Y = 120, SPAWN1_CENTER_Z = 0, SPAWN1_RADIUS = 44;
    public static final int SPAWN2_CENTER_X = 640, SPAWN2_CENTER_Z = 864, SPAWN2_HALF_SIZE = 6;

    private final AetherVisualsPlugin plugin;

    public SpawnProtectionEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
    }

    public boolean isInSpawn1(Location loc) {
        if (loc == null || loc.getWorld() == null) return false;
        if (!loc.getWorld().getName().equalsIgnoreCase("world") || loc.getY() < 110) return false;
        double dx = loc.getX() - SPAWN1_CENTER_X, dz = loc.getZ() - SPAWN1_CENTER_Z;
        return (dx * dx + dz * dz) <= (SPAWN1_RADIUS * SPAWN1_RADIUS);
    }

    public boolean isInSpawn2(Location loc) {
        if (loc == null || loc.getWorld() == null) return false;
        if (!loc.getWorld().getName().equalsIgnoreCase("world") || loc.getY() >= 110) return false;
        int groundY = CelestialSpawnBuilder.getSafeGroundY(loc.getWorld(), SPAWN2_CENTER_X, SPAWN2_CENTER_Z);
        if (Math.abs(loc.getBlockY() - groundY) > 8) return false;
        return Math.abs(loc.getX() - SPAWN2_CENTER_X) <= SPAWN2_HALF_SIZE
                && Math.abs(loc.getZ() - SPAWN2_CENTER_Z) <= SPAWN2_HALF_SIZE;
    }

    public boolean isProtectedZone(Location loc) {
        return isInSpawn1(loc) || isInSpawn2(loc);
    }

    private boolean canBypass(Player player) {
        // Spawn 100% incassable : aucun contournement (même OP / créatif)
        return false;
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onBucketEmpty(PlayerBucketEmptyEvent event) {
        if (isProtectedZone(event.getBlock().getLocation())) event.setCancelled(true);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onBucketFill(PlayerBucketFillEvent event) {
        if (isProtectedZone(event.getBlock().getLocation())) event.setCancelled(true);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onEntityChangeBlock(EntityChangeBlockEvent event) {
        if (isProtectedZone(event.getBlock().getLocation())) event.setCancelled(true);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onPistonExtend(BlockPistonExtendEvent event) {
        for (org.bukkit.block.Block b : event.getBlocks()) {
            if (isProtectedZone(b.getLocation())) { event.setCancelled(true); return; }
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onPistonRetract(BlockPistonRetractEvent event) {
        for (org.bukkit.block.Block b : event.getBlocks()) {
            if (isProtectedZone(b.getLocation())) { event.setCancelled(true); return; }
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onFluidFlow(BlockFromToEvent event) {
        if (isProtectedZone(event.getToBlock().getLocation())) event.setCancelled(true);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onTrample(PlayerInteractEvent event) {
        if (event.getAction() == Action.PHYSICAL && event.getClickedBlock() != null
                && isProtectedZone(event.getClickedBlock().getLocation())
                && event.getClickedBlock().getType() == Material.FARMLAND) {
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onBlockBreak(BlockBreakEvent event) {
        Player player = event.getPlayer();
        Location loc = event.getBlock().getLocation();
        if (isInSpawn1(loc) && !canBypass(player)) {
            event.setCancelled(true);
            player.sendMessage(ChatColor.RED + "🛡️ L'Agora Céleste (Spawn 1) est un sanctuaire indestructible !");
        } else if (isInSpawn2(loc) && !canBypass(player)) {
            event.setCancelled(true);
            player.sendMessage(ChatColor.RED + "🛡️ Esplanade du Portail Survie protégée ! Éloignez-vous de quelques pas pour miner.");
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onBlockPlace(BlockPlaceEvent event) {
        Player player = event.getPlayer();
        Location loc = event.getBlock().getLocation();
        if (isInSpawn1(loc) && !canBypass(player)) {
            event.setCancelled(true);
            player.sendMessage(ChatColor.RED + "🛡️ Impossible de poser des blocs dans l'Agora Céleste (Spawn 1) !");
        } else if (isInSpawn2(loc) && !canBypass(player)) {
            event.setCancelled(true);
            player.sendMessage(ChatColor.RED + "🛡️ Esplanade du Portail Survie protégée ! Éloignez-vous de quelques pas pour bâtir.");
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onArmorStandManipulate(PlayerArmorStandManipulateEvent event) {
        Player p = event.getPlayer();
        if (isProtectedZone(event.getRightClicked().getLocation()) && !p.isOp()) {
            event.setCancelled(true);
            p.sendMessage(ChatColor.RED + "🛡️ Les armures et équipements du Spawn sont verrouillés (Réservé aux OP) !");
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onInteractAtEntity(PlayerInteractAtEntityEvent event) {
        Player p = event.getPlayer();
        Entity clicked = event.getRightClicked();
        if ((clicked instanceof ArmorStand || clicked instanceof ItemFrame) && isProtectedZone(clicked.getLocation()) && !p.isOp()) {
            event.setCancelled(true);
            p.sendMessage(ChatColor.RED + "🛡️ Les armures et équipements du Spawn sont verrouillés (Réservé aux OP) !");
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onInteractEntity(PlayerInteractEntityEvent event) {
        Player p = event.getPlayer();
        Entity clicked = event.getRightClicked();
        if ((clicked instanceof ArmorStand || clicked instanceof ItemFrame) && isProtectedZone(clicked.getLocation()) && !p.isOp()) {
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onHangingBreakByEntity(HangingBreakByEntityEvent event) {
        Player p = resolvePlayerAttacker(event.getRemover());
        if (isProtectedZone(event.getEntity().getLocation()) && !canBypass(p)) {
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onPlayerInteractSpawn(PlayerInteractEvent event) {
        Player player = event.getPlayer();
        Location loc = event.getClickedBlock() != null ? event.getClickedBlock().getLocation() : player.getLocation();
        if (!isProtectedZone(loc) || canBypass(player)) return;
        ItemStack item = event.getItem();
        if (isCrateKey(item)) return;
        if (item != null && isForbiddenSpawnPlaceable(item.getType()) && event.getAction() == Action.RIGHT_CLICK_BLOCK) {
            event.setCancelled(true);
            player.sendMessage(ChatColor.RED + "🛡️ Sanctuaire Spawn : Pose de mobilier & caisses interdite ! Utilisez uniquement vos clés.");
        }
    }

    private boolean isCrateKey(ItemStack item) {
        if (item != null && item.hasItemMeta() && item.getItemMeta().hasCustomModelData()) {
            int cmd = item.getItemMeta().getCustomModelData();
            return cmd == 2001 || cmd == 2002;
        }
        return false;
    }

    private boolean isForbiddenSpawnPlaceable(Material t) {
        String n = t.name();
        return t.isBlock() || t == Material.ARMOR_STAND || t == Material.ITEM_FRAME || t == Material.GLOW_ITEM_FRAME
                || t == Material.PAINTING || t == Material.END_CRYSTAL || n.contains("CHEST")
                || n.contains("SHULKER_BOX") || n.contains("BARREL") || n.contains("BANNER") || n.contains("BED") || n.contains("SIGN");
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onHangingPlace(HangingPlaceEvent event) {
        Player player = event.getPlayer();
        if (isProtectedZone(event.getEntity().getLocation()) && !canBypass(player)) {
            event.setCancelled(true);
            if (player != null) player.sendMessage(ChatColor.RED + "🛡️ Pose de décorations/cadres interdite dans le sanctuaire du Spawn !");
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onEntityPlace(EntityPlaceEvent event) {
        Player player = event.getPlayer();
        if (isProtectedZone(event.getEntity().getLocation()) && !canBypass(player)) {
            event.setCancelled(true);
            if (player != null) player.sendMessage(ChatColor.RED + "🛡️ Pose d'entités/mobilier interdite dans le sanctuaire du Spawn !");
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onEntityExplode(EntityExplodeEvent event) {
        Iterator<org.bukkit.block.Block> it = event.blockList().iterator();
        while (it.hasNext()) if (isProtectedZone(it.next().getLocation())) it.remove();
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onBlockExplode(BlockExplodeEvent event) {
        Iterator<org.bukkit.block.Block> it = event.blockList().iterator();
        while (it.hasNext()) if (isProtectedZone(it.next().getLocation())) it.remove();
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onBlockBurn(BlockBurnEvent event) {
        if (isProtectedZone(event.getBlock().getLocation())) event.setCancelled(true);
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onEntityDamage(EntityDamageEvent event) {
        Entity e = event.getEntity();
        if (e instanceof Player && isInSpawn1(e.getLocation())) {
            event.setCancelled(true);
        } else if ((e instanceof ArmorStand || e instanceof Hanging) && isProtectedZone(e.getLocation())) {
            if (!e.getScoreboardTags().contains("aether_dps_dummy")) event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onPvPDamage(EntityDamageByEntityEvent event) {
        Entity victim = event.getEntity();
        Player attacker = resolvePlayerAttacker(event.getDamager());
        if (victim instanceof Player && attacker != null && isProtectedZone(victim.getLocation())) {
            event.setCancelled(true);
            attacker.sendMessage(ChatColor.YELLOW + "🛡️ Combat désactivé dans la zone sécurisée !");
        } else if ((victim instanceof ArmorStand || victim instanceof Hanging) && isProtectedZone(victim.getLocation())) {
            if (!victim.getScoreboardTags().contains("aether_dps_dummy") && !canBypass(attacker)) {
                event.setCancelled(true);
            }
        }
    }

    private Player resolvePlayerAttacker(Entity damager) {
        if (damager instanceof Player p) return p;
        if (damager instanceof Projectile proj && proj.getShooter() instanceof Player p) return p;
        return null;
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onFoodChange(FoodLevelChangeEvent event) {
        if (event.getEntity() instanceof Player p && isProtectedZone(p.getLocation())) {
            event.setCancelled(true);
            p.setFoodLevel(20);
            p.setSaturation(20f);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onCreatureSpawn(CreatureSpawnEvent event) {
        if (event.getEntity() instanceof Monster && isProtectedZone(event.getLocation())) event.setCancelled(true);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPlayerMove(PlayerMoveEvent event) {
        Location from = event.getFrom(), to = event.getTo();
        if (to == null) return;
        Player player = event.getPlayer();
        checkVoidFallRescue(player, to);
        if (from.getBlockX() != to.getBlockX() || from.getBlockZ() != to.getBlockZ()) {
            handleZoneBoundaryNotification(player, from, to);
        }
    }

    private void checkVoidFallRescue(Player player, Location loc) {
        if (!loc.getWorld().getName().equalsIgnoreCase("world")) return;
        double dx = loc.getX() - SPAWN1_CENTER_X, dz = loc.getZ() - SPAWN1_CENTER_Z;
        if ((dx * dx + dz * dz) <= 50 * 50 && loc.getY() < 75) {
            Location safe = new Location(loc.getWorld(), 0.5, 121.0, 0.5, 0f, 0f);
            player.teleport(safe);
            player.setFallDistance(0f);
            player.playSound(safe, Sound.ENTITY_ENDERMAN_TELEPORT, 1.0f, 1.2f);
            player.sendMessage(ChatColor.AQUA + "☁ Sauvetage Céleste : Les vents d'Éther vous ramènent à l'Agora !");
        }
    }

    private void handleZoneBoundaryNotification(Player player, Location from, Location to) {
        boolean wasIn = isInSpawn2(from), nowIn = isInSpawn2(to);
        if (wasIn && !nowIn && !isInSpawn1(to)) {
            sendActionBar(player, ChatColor.RED + "⚔️ Zone Sécurisée quittée — Bienvenue dans le Monde Survie Sauvage !");
        } else if (!wasIn && nowIn && !isInSpawn1(to)) {
            sendActionBar(player, ChatColor.GREEN + "🛡️ Esplanade Sécurisée du Portail Survie.");
        }
    }

    private void sendActionBar(Player player, String message) {
        try {
            player.spigot().sendMessage(ChatMessageType.ACTION_BAR, TextComponent.fromLegacy(message));
        } catch (Throwable ignored) {
            player.sendMessage(message);
        }
    }
}
