package io.aethercraft.visuals;

import net.md_5.bungee.api.ChatMessageType;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.*;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.*;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.player.PlayerArmorStandManipulateEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.inventory.EntityEquipment;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.util.Transformation;
import org.bukkit.util.Vector;
import org.joml.AxisAngle4f;
import org.joml.Vector3f;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

public class SpawnAmbianceEngine implements Listener {

    public enum SpawnMode {
        SANCTUARY("🌟 Sanctuaire Astral", Particle.END_ROD, Particle.PORTAL, Sound.BLOCK_AMETHYST_BLOCK_CHIME, Material.AMETHYST_BLOCK),
        FESTIVAL("🎉 Festival Céleste", Particle.FIREWORK, Particle.HAPPY_VILLAGER, Sound.ENTITY_FIREWORK_ROCKET_TWINKLE, Material.GOLD_BLOCK),
        CYBER("⚡ Cyber Éther", Particle.ELECTRIC_SPARK, Particle.SOUL_FIRE_FLAME, Sound.BLOCK_BEACON_AMBIENT, Material.SEA_LANTERN),
        AURORA("🌙 Aurore Boréale", Particle.GLOW, Particle.WAX_OFF, Sound.BLOCK_AMETHYST_CLUSTER_STEP, Material.DIAMOND_BLOCK),
        TRAINING("⚔️ Dojo d'Entraînement", Particle.CRIT, Particle.FLAME, Sound.BLOCK_ANVIL_LAND, Material.NETHERITE_BLOCK);

        public final String label;
        public final Particle primary;
        public final Particle secondary;
        public final Sound sound;
        public final Material crystalMat;

        SpawnMode(String label, Particle primary, Particle secondary, Sound sound, Material crystalMat) {
            this.label = label;
            this.primary = primary;
            this.secondary = secondary;
            this.sound = sound;
            this.crystalMat = crystalMat;
        }
    }

    private final AetherVisualsPlugin plugin;
    private final SpawnProtectionEngine protection;
    private SpawnMode currentMode = SpawnMode.SANCTUARY;
    private BlockDisplay centralCrystal;
    private TextDisplay centralHologram;
    private ArmorStand dpsDummy;
    private final Map<UUID, Long> jumpCooldowns = new ConcurrentHashMap<>();

    public SpawnAmbianceEngine(AetherVisualsPlugin plugin, SpawnProtectionEngine protection) {
        this.plugin = plugin;
        this.protection = protection;
    }

    public SpawnMode getCurrentMode() {
        return currentMode;
    }

    public void setMode(SpawnMode mode, CommandSender sender) {
        this.currentMode = mode;
        World w = Bukkit.getWorld("world");
        if (w != null) {
            initSpawnProps(w);
            for (Player p : w.getPlayers()) {
                if (protection.isInSpawn1(p.getLocation())) {
                    p.playSound(p.getLocation(), mode.sound, 1.0f, 1.2f);
                    p.sendTitle(ChatColor.AQUA + "✦ MODE SPAWN ✦", ChatColor.GOLD + mode.label, 10, 45, 15);
                }
            }
        }
        if (sender != null) {
            sender.sendMessage(ChatColor.GREEN + "✦ Mode du Spawn Safe basculé sur : " + ChatColor.GOLD + mode.label);
        }
    }

    public void cycleMode(CommandSender sender) {
        SpawnMode[] vals = SpawnMode.values();
        SpawnMode next = vals[(currentMode.ordinal() + 1) % vals.length];
        setMode(next, sender);
    }

    public void initSpawnProps(World w) {
        if (w == null) return;
        clearEntities();
        cleanupOrphanTaggedEntities(w);
        spawnCentralCrystal(w);
        spawnDpsDummy(w);
    }

    private void cleanupOrphanTaggedEntities(World w) {
        Location center = new Location(w, 0.5, 122.0, 0.5);
        for (Entity e : w.getNearbyEntities(center, 25, 20, 25)) {
            if (e.getScoreboardTags().contains("aether_spawn_prop") || e.getScoreboardTags().contains("aether_dps_dummy")) {
                e.remove();
            }
        }
    }

    private void spawnCentralCrystal(World w) {
        Location crystalLoc = new Location(w, 0.5, 124.2, 0.5);
        centralCrystal = w.spawn(crystalLoc, BlockDisplay.class, bd -> {
            bd.setBlock(Bukkit.createBlockData(currentMode.crystalMat));
            bd.setBrightness(new Display.Brightness(15, 15));
            bd.setGlowing(true);
            bd.addScoreboardTag("aether_spawn_prop");
        });
        Location holoLoc = new Location(w, 0.5, 126.0, 0.5);
        centralHologram = w.spawn(holoLoc, TextDisplay.class, td -> {
            td.setBillboard(Display.Billboard.CENTER);
            td.setBrightness(new Display.Brightness(15, 15));
            td.setBackgroundColor(Color.fromARGB(160, 12, 16, 36));
            td.setText(buildHologramText(w));
            td.addScoreboardTag("aether_spawn_prop");
        });
    }

    private String buildHologramText(World w) {
        long count = w.getPlayers().stream().filter(p -> protection.isInSpawn1(p.getLocation())).count();
        return ChatColor.GOLD + "✦ " + ChatColor.AQUA + ChatColor.BOLD + "AGORA CÉLESTE" + ChatColor.GOLD + " ✦\n"
                + ChatColor.GRAY + "Mode : " + ChatColor.YELLOW + currentMode.label + "\n"
                + ChatColor.GRAY + "Présents au Sanctuaire : " + ChatColor.GREEN + count;
    }

    private void spawnDpsDummy(World w) {
        Location loc = new Location(w, 6.5, 121.0, -6.5, 45f, 0f);
        dpsDummy = w.spawn(loc, ArmorStand.class, as -> {
            as.setCustomName(ChatColor.RED + "⚔️ " + ChatColor.GOLD + "Golem Astral [Test DPS]");
            as.setCustomNameVisible(true);
            as.setGravity(false);
            as.setBasePlate(true);
            as.setArms(true);
            as.addScoreboardTag("aether_dps_dummy");
            EntityEquipment eq = as.getEquipment();
            if (eq != null) {
                eq.setHelmet(new ItemStack(Material.AMETHYST_CLUSTER));
                eq.setChestplate(new ItemStack(Material.NETHERITE_CHESTPLATE));
                eq.setLeggings(new ItemStack(Material.NETHERITE_LEGGINGS));
                eq.setBoots(new ItemStack(Material.NETHERITE_BOOTS));
                eq.setItemInMainHand(new ItemStack(Material.NETHERITE_SWORD));
            }
            for (EquipmentSlot slot : EquipmentSlot.values()) {
                for (ArmorStand.LockType lt : ArmorStand.LockType.values()) {
                    as.addEquipmentLock(slot, lt);
                }
            }
        });
    }

    public void tickAmbiance(long tick) {
        World w = Bukkit.getWorld("world");
        if (w == null) return;
        animateCrystal(w, tick);
        renderModeParticles(w, tick);
        if (tick % 40 == 0) {
            applySpawnBuffs(w);
        }
    }

    private void animateCrystal(World w, long tick) {
        if (centralCrystal == null || !centralCrystal.isValid()) return;
        float angle = (float) ((tick * 0.06) % (Math.PI * 2));
        float bob = (float) (Math.sin(tick * 0.08) * 0.30);
        Transformation tr = new Transformation(
                new Vector3f(-0.45f, bob, -0.45f),
                new AxisAngle4f(angle, 0.3f, 1.0f, 0.2f),
                new Vector3f(0.9f, 0.9f, 0.9f),
                new AxisAngle4f(0f, 0f, 1f, 0f)
        );
        centralCrystal.setTransformation(tr);
        if (tick % 20 == 0 && centralHologram != null && centralHologram.isValid()) {
            centralHologram.setText(buildHologramText(w));
        }
    }

    private void renderModeParticles(World w, long tick) {
        double angle = (tick * 0.12) % (Math.PI * 2);
        double rx = Math.cos(angle) * 2.8;
        double rz = Math.sin(angle) * 2.8;
        Location ringLoc = new Location(w, 0.5 + rx, 122.2 + Math.sin(tick * 0.1) * 0.5, 0.5 + rz);
        w.spawnParticle(currentMode.primary, ringLoc, 2, 0.05, 0.05, 0.05, 0.01);
        w.spawnParticle(currentMode.secondary, new Location(w, 0.5 - rx, 122.5, 0.5 - rz), 2, 0.1, 0.1, 0.1, 0.02);

        if (currentMode == SpawnMode.AURORA && tick % 4 == 0) {
            for (int i = -12; i <= 12; i += 4) {
                double zOff = Math.sin((tick * 0.05) + (i * 0.3)) * 5.0;
                w.spawnParticle(Particle.GLOW, new Location(w, i, 131.5, zOff), 3, 0.6, 0.3, 0.6, 0.01);
            }
        } else if (currentMode == SpawnMode.FESTIVAL && tick % 20 == 0) {
            w.spawnParticle(Particle.FIREWORK, new Location(w, 0.5, 128.0, 0.5), 18, 4.0, 2.0, 4.0, 0.08);
        }
    }

    private void applySpawnBuffs(World w) {
        int speedAmp = (currentMode == SpawnMode.FESTIVAL || currentMode == SpawnMode.CYBER) ? 1 : 0;
        for (Player p : w.getPlayers()) {
            if (protection.isInSpawn1(p.getLocation())) {
                p.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 65, speedAmp, true, false, false));
                p.addPotionEffect(new PotionEffect(PotionEffectType.JUMP_BOOST, 65, 0, true, false, false));
            }
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onJumpPadStep(PlayerMoveEvent event) {
        Location to = event.getTo();
        if (to == null || !protection.isInSpawn1(to)) return;
        Material plate = to.getBlock().getType();
        if (plate != Material.POLISHED_BLACKSTONE_PRESSURE_PLATE && plate != Material.LIGHT_WEIGHTED_PRESSURE_PLATE && plate != Material.HEAVY_WEIGHTED_PRESSURE_PLATE) return;

        Player p = event.getPlayer();
        long now = System.currentTimeMillis();
        if (now - jumpCooldowns.getOrDefault(p.getUniqueId(), 0L) < 900L) return;
        jumpCooldowns.put(p.getUniqueId(), now);

        launchPlayerFromPad(p, to);
    }

    private void launchPlayerFromPad(Player p, Location padLoc) {
        Vector dir = p.getLocation().getDirection().setY(0).normalize();
        String dest = "Envol Céleste";
        if (padLoc.getBlockZ() >= 4) { dir = new Vector(0, 0, 1); dest = "Portail Survie & Donjons"; }
        else if (padLoc.getBlockZ() <= -4) { dir = new Vector(0, 0, -1); dest = "Trône du Champion"; }
        else if (padLoc.getBlockX() <= -4) { dir = new Vector(-1, 0, 0); dest = "Marché & Bourse"; }
        else if (padLoc.getBlockX() >= 4) { dir = new Vector(1, 0, 0); dest = "Sanctuaire des Familiers"; }

        p.setVelocity(dir.multiply(1.35).setY(0.78));
        p.playSound(padLoc, Sound.ENTITY_ENDER_DRAGON_FLAP, 1.0f, 1.35f);
        p.getWorld().spawnParticle(Particle.CLOUD, padLoc.clone().add(0, 0.2, 0), 18, 0.3, 0.1, 0.3, 0.08);
        p.spigot().sendMessage(ChatMessageType.ACTION_BAR, TextComponent.fromLegacy(
                ChatColor.AQUA + "🚀 Propulsion Astrale ➤ " + ChatColor.GOLD + dest));
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void onDummyDamage(EntityDamageByEntityEvent event) {
        Entity victim = event.getEntity();
        if (!victim.getScoreboardTags().contains("aether_dps_dummy")) return;
        event.setCancelled(true);
        if (!(event.getDamager() instanceof Player p)) return;

        double dmg = Math.max(1.0, event.getFinalDamage());
        boolean crit = p.getFallDistance() > 0.1f;
        if (crit) dmg *= 1.5;

        victim.getWorld().playSound(victim.getLocation(), Sound.BLOCK_AMETHYST_BLOCK_BREAK, 1.0f, crit ? 1.5f : 1.1f);
        victim.getWorld().spawnParticle(crit ? Particle.CRIT : Particle.ENCHANTED_HIT,
                victim.getLocation().add(0, 1.3, 0), 15, 0.25, 0.3, 0.25, 0.15);
        spawnDamageIndicator(victim.getLocation().add(0, 2.0, 0), dmg, crit);
        p.spigot().sendMessage(ChatMessageType.ACTION_BAR, TextComponent.fromLegacy(
                ChatColor.RED + "⚔️ Frappe Astrale : " + ChatColor.GOLD + String.format("%.1f", dmg) + " DMG"
                        + (crit ? ChatColor.LIGHT_PURPLE + " [CRITIQUE !]" : "")));
    }

    private void spawnDamageIndicator(Location loc, double dmg, boolean crit) {
        Location jitter = loc.clone().add((Math.random() - 0.5) * 0.7, 0, (Math.random() - 0.5) * 0.7);
        TextDisplay indicator = loc.getWorld().spawn(jitter, TextDisplay.class, td -> {
            td.setBillboard(Display.Billboard.CENTER);
            td.setBrightness(new Display.Brightness(15, 15));
            td.setText((crit ? ChatColor.LIGHT_PURPLE + "✧ " : ChatColor.RED + "")
                    + String.format("-%.1f ❤", dmg) + (crit ? " CRIT!" : ""));
        });
        Bukkit.getScheduler().runTaskLater(plugin, indicator::remove, 16L);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onDummyArmorManipulate(PlayerArmorStandManipulateEvent event) {
        if (!event.getPlayer().isOp() && (event.getRightClicked().getScoreboardTags().contains("aether_dps_dummy")
                || protection.isInSpawn1(event.getRightClicked().getLocation())
                || protection.isInSpawn2(event.getRightClicked().getLocation()))) {
            event.setCancelled(true);
            event.getPlayer().sendMessage(ChatColor.RED + "🛡️ Équipement du Sanctuaire verrouillé (Réservé aux OP) !");
        }
    }

    public void clearEntities() {
        if (centralCrystal != null) { centralCrystal.remove(); centralCrystal = null; }
        if (centralHologram != null) { centralHologram.remove(); centralHologram = null; }
        if (dpsDummy != null) { dpsDummy.remove(); dpsDummy = null; }
    }
}
