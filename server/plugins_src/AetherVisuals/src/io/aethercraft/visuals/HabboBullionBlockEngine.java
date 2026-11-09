package io.aethercraft.visuals;

import org.bukkit.*;
import org.bukkit.block.Block;
import org.bukkit.block.BlockFace;
import org.bukkit.entity.*;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.block.BlockExplodeEvent;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityExplodeEvent;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.persistence.PersistentDataContainer;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.util.Transformation;
import org.joml.AxisAngle4f;
import org.joml.Vector3f;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.util.UUID;

/**
 * Moteur des Magots / Lingots / Blocs d'Argent Habbo Hotel posables et convertibles.
 * Pose un ItemDisplay + TextDisplay + Interaction cliquable / ramassable / convertible.
 */
public class HabboBullionBlockEngine implements Listener {

    public static final String TAG_BULLION = "AETHER_HABBO_BULLION";

    private final AetherVisualsPlugin plugin;
    private final NamespacedKey keyBullion;
    private final NamespacedKey keyCmd;
    private final NamespacedKey keyValue;
    private final NamespacedKey keyName;
    private final NamespacedKey keyOwner;
    private final NamespacedKey keyLinkedItem;
    private final NamespacedKey keyLinkedText;
    private final NamespacedKey keyLinkedInter;

    public HabboBullionBlockEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
        this.keyBullion = new NamespacedKey(plugin, "habbo_bullion");
        this.keyCmd = new NamespacedKey(plugin, "bullion_cmd");
        this.keyValue = new NamespacedKey(plugin, "bullion_value");
        this.keyName = new NamespacedKey(plugin, "bullion_name");
        this.keyOwner = new NamespacedKey(plugin, "bullion_owner");
        this.keyLinkedItem = new NamespacedKey(plugin, "bullion_item_uuid");
        this.keyLinkedText = new NamespacedKey(plugin, "bullion_text_uuid");
        this.keyLinkedInter = new NamespacedKey(plugin, "bullion_inter_uuid");
    }

    @EventHandler(priority = EventPriority.HIGH)
    public void onBullionPlace(PlayerInteractEvent event) {
        if (event.getAction() != Action.RIGHT_CLICK_BLOCK) return;
        if (event.getHand() != EquipmentSlot.HAND) return;

        ItemStack item = event.getItem();
        if (item == null || !item.hasItemMeta() || !item.getItemMeta().hasCustomModelData()) return;

        int cmd = item.getItemMeta().getCustomModelData();
        int coinsValue = PetItemFactory.getBullionCoinValue(cmd);
        if (coinsValue <= 0) return;

        event.setCancelled(true);
        Player p = event.getPlayer();
        Block clicked = event.getClickedBlock();
        if (clicked == null) return;

        BlockFace face = event.getBlockFace();
        Block target = clicked.getRelative(face);
        if (!target.isPassable() && target.getType() != Material.AIR) {
            p.sendMessage("§cEmplacement encombré, impossible de poser ce magot ici.");
            return;
        }

        World w = target.getWorld();

        if (plugin.getSpawnProtectionEngine() != null && plugin.getSpawnProtectionEngine().isProtectedZone(target.getLocation())) {
            p.sendMessage("§cImpossible de poser du mobilier dans la zone protégée du spawn !");
            return;
        }

        OneBlockEngine ob = plugin.getOneBlockEngine();
        if (ob != null && (w.getName().equals("world_oneblock") || w.equals(ob.getOneBlockWorld()))) {
            OneBlockEngine.IslandData island = ob.getIslandAt(target.getLocation());
            if (island != null && !ob.isAllowedToBuild(p, island, target.getLocation())) {
                return;
            }
        }

        String displayName = item.getItemMeta().hasDisplayName() ? item.getItemMeta().getDisplayName() : "Magot Habbo";
        Location center = target.getLocation().add(0.5, 0.05, 0.5);
        float yaw = Math.round(p.getLocation().getYaw() / 45f) * 45f;
        center.setYaw(yaw);

        ItemDisplay itemDisp = w.spawn(center, ItemDisplay.class, d -> {
            ItemStack single = item.clone();
            single.setAmount(1);
            d.setItemStack(single);
            d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.GROUND);
            d.setTransformation(new Transformation(
                    new Vector3f(0f, 0.04f, 0f),
                    new AxisAngle4f(0f, 0f, 1f, 0f),
                    new Vector3f(1.15f, 1.15f, 1.15f),
                    new AxisAngle4f(0f, 0f, 1f, 0f)
            ));
            Color glowColor = switch (cmd) {
                case 6006 -> Color.fromRGB(46, 204, 113); // Emerald
                case 6007 -> Color.fromRGB(0, 210, 255);  // Diamond
                case 6008 -> Color.fromRGB(255, 215, 0);  // Trophy Gold
                case 6009 -> Color.fromRGB(155, 89, 182); // Throne Purple
                case 6010 -> Color.fromRGB(0, 255, 230);  // Aether Cyan
                case 6011 -> Color.fromRGB(230, 126, 34); // Nether Flame
                default -> Color.fromRGB(255, 215, 0);
            };
            d.setGlowing(true);
            d.setGlowColorOverride(glowColor);
            d.setBrightness(new Display.Brightness(15, 15));
            d.addScoreboardTag(TAG_BULLION);
        });

        TextDisplay textDisp = w.spawn(center.clone().add(0, 0.58, 0), TextDisplay.class, t -> {
            t.setText("§6§l" + displayName + "\n§e✦ §fValeur : §6§l" + coinsValue + " ⛃ Pièces\n§7• Clic-G: §fRamasser §8| §a• Clic-D: §6Encaisser");
            t.setBillboard(Display.Billboard.CENTER);
            t.setBackgroundColor(Color.fromARGB(170, 18, 24, 38));
            t.setShadowed(true);
            t.setBrightness(new Display.Brightness(15, 15));
            t.addScoreboardTag(TAG_BULLION);
        });

        Interaction inter = w.spawn(center, Interaction.class, i -> {
            i.setInteractionWidth(0.85f);
            i.setInteractionHeight(0.70f);
            i.setResponsive(true);
            i.addScoreboardTag(TAG_BULLION);
        });

        tagBullionEntity(itemDisp, cmd, coinsValue, displayName, p.getUniqueId(), itemDisp.getUniqueId(), textDisp.getUniqueId(), inter.getUniqueId());
        tagBullionEntity(textDisp, cmd, coinsValue, displayName, p.getUniqueId(), itemDisp.getUniqueId(), textDisp.getUniqueId(), inter.getUniqueId());
        tagBullionEntity(inter, cmd, coinsValue, displayName, p.getUniqueId(), itemDisp.getUniqueId(), textDisp.getUniqueId(), inter.getUniqueId());

        if (item.getAmount() <= 1) {
            p.getInventory().setItemInMainHand(null);
        } else {
            item.setAmount(item.getAmount() - 1);
        }

        w.playSound(center, Sound.BLOCK_ANVIL_PLACE, 0.65f, 1.6f);
        w.playSound(center, Sound.BLOCK_CHAIN_PLACE, 0.85f, 1.35f);
        w.spawnParticle(Particle.WAX_OFF, center.clone().add(0, 0.25, 0), 16, 0.25, 0.25, 0.25, 0.05);
        p.sendMessage("§6§l[🪙 HABBO MOBILIER] §aMagot §f" + displayName + " §aposé au sol ! §7(Clic-G: Ramasser • Clic-D: Encaisser)");
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void onBullionHit(EntityDamageByEntityEvent event) {
        if (!(event.getDamager() instanceof Player p)) return;
        Entity target = event.getEntity();
        PersistentDataContainer pdc = target.getPersistentDataContainer();
        if (!pdc.has(keyBullion, PersistentDataType.STRING)) return;

        event.setCancelled(true);
        int cmd = pdc.getOrDefault(keyCmd, PersistentDataType.INTEGER, 6004);
        String name = pdc.getOrDefault(keyName, PersistentDataType.STRING, "Magot Habbo");
        String bullionId = getBullionIdFromCmd(cmd);

        ItemStack refund = PetItemFactory.createHabboBullionItem(bullionId, 1);
        Location dropLoc = target.getLocation();
        target.getWorld().dropItemNaturally(dropLoc, refund);

        p.playSound(p.getLocation(), Sound.ENTITY_ITEM_PICKUP, 1.0f, 1.2f);
        p.spawnParticle(Particle.CLOUD, target.getLocation().add(0, 0.3, 0), 12, 0.2, 0.2, 0.2, 0.05);
        p.sendMessage("§e[🪙 HABBO MOBILIER] §7Vous avez décroché §f" + name + " §7(butin au sol).");
        destroyBullionCluster(target);
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void onBullionInteract(PlayerInteractEntityEvent event) {
        Entity target = event.getRightClicked();
        PersistentDataContainer pdc = target.getPersistentDataContainer();
        if (!pdc.has(keyBullion, PersistentDataType.STRING)) return;

        event.setCancelled(true);
        Player p = event.getPlayer();
        int value = pdc.getOrDefault(keyValue, PersistentDataType.INTEGER, 0);
        String name = pdc.getOrDefault(keyName, PersistentDataType.STRING, "Magot Habbo");

        if (value > 0) {
            try (Connection c = AetherDatabase.getConnection();
                 PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username)=LOWER(?)")) {
                ps.setDouble(1, value);
                ps.setString(2, p.getName());
                ps.executeUpdate();
            } catch (Exception ex) {
                p.sendMessage("§cErreur base de données lors de l'encaissement : " + ex.getMessage());
                return;
            }

            if (plugin.getScoreboardManager() != null) {
                plugin.getScoreboardManager().refreshPlayer(p);
            }

            Location loc = target.getLocation();
            loc.getWorld().playSound(loc, Sound.ENTITY_PLAYER_LEVELUP, 1.0f, 1.3f);
            loc.getWorld().playSound(loc, Sound.BLOCK_AMETHYST_BLOCK_CHIME, 1.0f, 1.6f);
            loc.getWorld().spawnParticle(Particle.TOTEM_OF_UNDYING, loc.clone().add(0, 0.5, 0), 24, 0.35, 0.45, 0.35, 0.08);
            loc.getWorld().spawnParticle(Particle.HAPPY_VILLAGER, loc.clone().add(0, 0.4, 0), 14, 0.3, 0.3, 0.3, 0.05);

            p.sendMessage("§6§l[🪙 ENCAISSEMENT HABBO] §aVous avez encaissé ce mobilier §f" + name + " §apour §6§l+" + value + " ⛃ Pièces §a!");
        }

        destroyBullionCluster(target);
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onEntityExplode(EntityExplodeEvent event) {
        handleExplosion(event.getLocation(), 4.5);
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onBlockExplode(BlockExplodeEvent event) {
        handleExplosion(event.getBlock().getLocation(), 4.5);
    }

    private void handleExplosion(Location center, double radius) {
        if (center == null || center.getWorld() == null) return;
        World world = center.getWorld();
        double searchRadius = Math.max(5.0, radius);
        for (Entity entity : world.getNearbyEntities(center, searchRadius, searchRadius, searchRadius)) {
            if (!entity.isValid()) continue;
            PersistentDataContainer pdc = entity.getPersistentDataContainer();
            if (!pdc.has(keyBullion, PersistentDataType.STRING)) continue;

            int cmd = pdc.getOrDefault(keyCmd, PersistentDataType.INTEGER, 6004);
            String bullionId = getBullionIdFromCmd(cmd);
            ItemStack refund = PetItemFactory.createHabboBullionItem(bullionId, 1);
            Location loc = entity.getLocation();

            destroyBullionCluster(entity);
            world.dropItemNaturally(loc, refund);
            world.spawnParticle(Particle.EXPLOSION, loc, 1);
        }
    }

    @EventHandler(priority = EventPriority.HIGH)
    public void onPlayerDeath(PlayerDeathEvent event) {
        Player player = event.getEntity();
        if (player == null) return;

        // Règle de gameplay : Perte à la mort uniquement sur les blocs de construction de bâtiments.
        // La banque (solde virtuel) et les pièces/lingots ("pièces solides", magots, monnaie) ne sont JAMAIS perdus.
        // Aucune pénalité de réparation ni dégradation de durabilité sur les lingots/pièces portés.
        // Les items restants tombent au sol et sont ramassables par le joueur lui-même ou n'importe quel autre joueur.
        java.util.List<ItemStack> drops = event.getDrops();
        if (drops != null && !drops.isEmpty()) {
            drops.removeIf(item -> item != null && item.getType().isBlock() && !PetItemFactory.isBullionCoin(item));
        }
    }

    private void tagBullionEntity(Entity e, int cmd, int value, String name, UUID owner, UUID itemUuid, UUID textUuid, UUID interUuid) {
        PersistentDataContainer pdc = e.getPersistentDataContainer();
        pdc.set(keyBullion, PersistentDataType.STRING, "true");
        pdc.set(keyCmd, PersistentDataType.INTEGER, cmd);
        pdc.set(keyValue, PersistentDataType.INTEGER, value);
        pdc.set(keyName, PersistentDataType.STRING, name);
        pdc.set(keyOwner, PersistentDataType.STRING, owner.toString());
        pdc.set(keyLinkedItem, PersistentDataType.STRING, itemUuid.toString());
        pdc.set(keyLinkedText, PersistentDataType.STRING, textUuid.toString());
        pdc.set(keyLinkedInter, PersistentDataType.STRING, interUuid.toString());
    }

    private void destroyBullionCluster(Entity source) {
        PersistentDataContainer pdc = source.getPersistentDataContainer();
        String itemUuidStr = pdc.get(keyLinkedItem, PersistentDataType.STRING);
        String textUuidStr = pdc.get(keyLinkedText, PersistentDataType.STRING);
        String interUuidStr = pdc.get(keyLinkedInter, PersistentDataType.STRING);

        removeEntityByUuidString(source.getWorld(), itemUuidStr);
        removeEntityByUuidString(source.getWorld(), textUuidStr);
        removeEntityByUuidString(source.getWorld(), interUuidStr);
        source.remove();
    }

    private void removeEntityByUuidString(World w, String uuidStr) {
        if (uuidStr == null || uuidStr.isEmpty()) return;
        try {
            Entity e = Bukkit.getEntity(UUID.fromString(uuidStr));
            if (e != null && e.isValid()) e.remove();
        } catch (Exception ignored) {}
    }

    public static String getBullionIdFromCmd(int cmd) {
        return switch (cmd) {
            case 6001 -> "magot_piece_bronze";
            case 6002 -> "magot_piece_argent";
            case 6003 -> "magot_sac_pieces";
            case 6005 -> "magot_bloc_or";
            case 6006 -> "magot_bloc_emeraude";
            case 6007 -> "magot_bloc_diamant";
            case 6008 -> "magot_trophee_or";
            case 6009 -> "magot_trone_royal";
            case 6010 -> "bloc_aether";
            case 6011 -> "minerai_aether";
            default -> "magot_lingot_or";
        };
    }
}
