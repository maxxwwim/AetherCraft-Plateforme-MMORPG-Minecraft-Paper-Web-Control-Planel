package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Color;
import org.bukkit.FireworkEffect;
import org.bukkit.Location;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.entity.EntityType;
import org.bukkit.entity.Firework;
import org.bukkit.entity.Hoglin;
import org.bukkit.entity.IronGolem;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.entity.PolarBear;
import org.bukkit.entity.Ravager;
import org.bukkit.entity.Skeleton;
import org.bukkit.entity.SmallFireball;
import org.bukkit.entity.Vindicator;
import org.bukkit.entity.Witch;
import org.bukkit.entity.WitherSkeleton;
import org.bukkit.entity.Zombie;
import org.bukkit.inventory.meta.FireworkMeta;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.util.Vector;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.util.Random;
import java.util.Set;
import java.util.UUID;

/**
 * Système de compétences magiques, ciblage et récompenses SQLite du donjon.
 */
public class DungeonMobSpellCaster {

    private static final Random random = new Random();

    public static void triggerMobSpells(AetherVisualsPlugin plugin, DungeonWaveEngine engine,
                                        LivingEntity mob, Player target,
                                        Set<UUID> playersInDungeon, Set<LivingEntity> activeMonsters,
                                        Runnable onTitanReinforcements) {
        double distSq = mob.getLocation().distanceSquared(target.getLocation());
        double dist = Math.sqrt(distSq);

        if (mob instanceof IronGolem) {
            triggerTitanSpells(plugin, engine, mob, target, dist, playersInDungeon, onTitanReinforcements);
            return;
        }
        if ((mob instanceof Skeleton || mob instanceof Witch || mob instanceof WitherSkeleton) && dist >= 4.0 && dist <= 24.0 && random.nextDouble() < 0.35) {
            castFireball(mob, target);
        }
        if ((mob instanceof Zombie || mob instanceof Vindicator) && mob.getHealth() <= 10.0 && !mob.hasPotionEffect(PotionEffectType.RESISTANCE) && random.nextDouble() < 0.40) {
            applyArcaneShield(mob);
        }
        if (mob instanceof Ravager || mob instanceof PolarBear || mob instanceof Hoglin) {
            if (dist <= 6.0 && random.nextDouble() < 0.30) castGroundSlam(mob, playersInDungeon);
            else if (dist <= 12.0 && random.nextDouble() < 0.20) castBeastRoar(mob, activeMonsters);
        }
        if (mob instanceof Vindicator && random.nextDouble() < 0.15) {
            castAstralLightning(plugin, engine, mob, target);
        }
    }

    private static void triggerTitanSpells(AetherVisualsPlugin plugin, DungeonWaveEngine engine,
                                           LivingEntity mob, Player target, double dist,
                                           Set<UUID> playersInDungeon, Runnable onTitanReinforcements) {
        if (mob.getHealth() < 125.0) onTitanReinforcements.run();
        if (random.nextDouble() < 0.35) castFireball(mob, target);
        if (dist <= 7.0 && random.nextDouble() < 0.40) castGroundSlam(mob, playersInDungeon);
        if (random.nextDouble() < 0.20) castAstralLightning(plugin, engine, mob, target);
        if (mob.getHealth() < 80.0 && !mob.hasPotionEffect(PotionEffectType.RESISTANCE) && random.nextDouble() < 0.30) {
            applyArcaneShield(mob);
        }
    }

    private static void applyArcaneShield(LivingEntity mob) {
        mob.addPotionEffect(new PotionEffect(PotionEffectType.RESISTANCE, 20 * 4, 2));
        mob.addPotionEffect(new PotionEffect(PotionEffectType.GLOWING, 20 * 4, 0));
        Location loc = mob.getLocation().add(0, 1.0, 0);
        mob.getWorld().spawnParticle(Particle.TOTEM_OF_UNDYING, loc, 25, 0.4, 0.7, 0.4, 0.1);
        mob.getWorld().playSound(loc, Sound.ITEM_SHIELD_BLOCK, 1.0f, 0.8f);
    }

    private static void castFireball(LivingEntity mob, Player target) {
        Location eye = mob.getEyeLocation();
        Vector dir = target.getEyeLocation().toVector().subtract(eye.toVector()).normalize();
        SmallFireball fb = mob.getWorld().spawn(eye.add(dir.clone().multiply(1.2)), SmallFireball.class);
        fb.setShooter(mob);
        fb.setDirection(dir.multiply(0.8));
        mob.getWorld().spawnParticle(Particle.FLAME, eye, 10, 0.2, 0.2, 0.2, 0.05);
        mob.getWorld().playSound(eye, Sound.ENTITY_BLAZE_SHOOT, 0.9f, 1.2f);
    }

    private static void castGroundSlam(LivingEntity mob, Set<UUID> playersInDungeon) {
        Location loc = mob.getLocation();
        mob.getWorld().spawnParticle(Particle.EXPLOSION, loc, 3, 0.5, 0.2, 0.5, 0.1);
        mob.getWorld().playSound(loc, Sound.ENTITY_RAVAGER_ATTACK, 1.2f, 0.7f);
        for (UUID uid : playersInDungeon) {
            Player p = Bukkit.getPlayer(uid);
            if (p != null && p.isValid() && p.getLocation().distanceSquared(loc) <= 36.0) {
                Vector kb = p.getLocation().toVector().subtract(loc.toVector()).normalize().multiply(0.9).setY(0.4);
                p.setVelocity(kb);
                p.damage(4.0, mob);
                p.playSound(p.getLocation(), Sound.ENTITY_PLAYER_HURT, 0.8f, 1.0f);
            }
        }
    }

    private static void castAstralLightning(AetherVisualsPlugin plugin, DungeonWaveEngine engine, LivingEntity mob, Player target) {
        Location targetLoc = target.getLocation();
        target.getWorld().spawnParticle(Particle.ELECTRIC_SPARK, targetLoc, 20, 0.4, 0.1, 0.4, 0.1);
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (engine.getState() == DungeonWaveEngine.DungeonState.IN_WAVE && target.isValid() && !target.isDead()) {
                targetLoc.getWorld().strikeLightningEffect(targetLoc);
                target.damage(4.0, mob);
                target.sendMessage(ChatColor.RED + "⚡ Un éclair astral vous frappe de plein fouet !");
            }
        }, 15L);
    }

    private static void castBeastRoar(LivingEntity mob, Set<LivingEntity> activeMonsters) {
        Location loc = mob.getLocation();
        mob.getWorld().playSound(loc, Sound.ENTITY_WOLF_GROWL, 1.3f, 0.6f);
        mob.getWorld().spawnParticle(Particle.ANGRY_VILLAGER, loc.add(0, 1.2, 0), 8, 0.4, 0.4, 0.4, 0.05);
        synchronized (activeMonsters) {
            for (LivingEntity ally : activeMonsters) {
                if (ally.isValid() && ally.getLocation().distanceSquared(loc) <= 64.0) {
                    ally.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 20 * 6, 1));
                    ally.addPotionEffect(new PotionEffect(PotionEffectType.STRENGTH, 20 * 6, 0));
                }
            }
        }
    }

    public static Player getNearestDungeonPlayer(Location loc, Set<UUID> playersInDungeon) {
        Player nearest = null;
        double minDistanceSq = Double.MAX_VALUE;
        for (UUID uid : playersInDungeon) {
            Player p = Bukkit.getPlayer(uid);
            if (p != null && p.isValid() && !p.isDead() && p.getWorld().equals(loc.getWorld())) {
                double dSq = p.getLocation().distanceSquared(loc);
                if (dSq < minDistanceSq) { minDistanceSq = dSq; nearest = p; }
            }
        }
        return nearest;
    }

    public static void rewardDungeonVictory(World world, Set<UUID> playersInDungeon) {
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement("UPDATE community_goals SET current_amount = current_amount + 50 WHERE id = 's4_celestial_tree'")) {
            ps.executeUpdate();
        } catch (Throwable ignored) {}

        for (UUID uid : playersInDungeon) {
            Player p = Bukkit.getPlayer(uid);
            if (p == null) continue;
            try (Connection conn = AetherDatabase.getConnection();
                 PreparedStatement ps = conn.prepareStatement("UPDATE players SET balance = balance + 350 WHERE LOWER(username) = LOWER(?)")) {
                ps.setString(1, p.getName());
                ps.executeUpdate();
            } catch (Throwable ignored) {}

            p.getInventory().addItem(CustomItemFactory.createCelestialKey(1));
            p.sendMessage(ChatColor.GREEN + "✦ RÉCOMPENSES DU DONJON : +350 Coins, +1 Clé Céleste, +50 Minerais Arbre !");

            Firework fw = (Firework) world.spawnEntity(p.getLocation(), EntityType.FIREWORK_ROCKET);
            FireworkMeta fwm = fw.getFireworkMeta();
            fwm.addEffect(FireworkEffect.builder().withColor(Color.YELLOW, Color.GREEN, Color.TEAL).withFade(Color.WHITE).with(FireworkEffect.Type.BALL_LARGE).build());
            fwm.setPower(1);
            fw.setFireworkMeta(fwm);
        }
    }
}
