package io.aethercraft.visuals;

import org.bukkit.ChatColor;
import org.bukkit.Location;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerQuitEvent;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Ambiance de l'Agora : petales de cerisier, fontaine, lucioles nocturnes, brume sous l'ile,
 * sons de bassin / carillon et titres d'entree dans chaque zone.
 */
public class SpawnAtmosphere implements Listener {

    private static final class Zone {
        final String name;
        final String sub;
        final double x;
        final double z;
        final double r;

        Zone(String name, String sub, double x, double z, double r) {
            this.name = name;
            this.sub = sub;
            this.x = x;
            this.z = z;
            this.r = r;
        }
    }

    // L'ordre compte : la premiere zone qui contient le joueur l'emporte.
    private static final Zone[] ZONES = {
        new Zone("Stèle des Terres Sauvages", "Téléportation aléatoire", 12.5, 0.5, 2.5),
        new Zone("Sanctuaire des Animaux", "Compagnons voxel", 15.5, 0.5, 4.5),
        new Zone("Banque d'Éther", "Coffre privé", -9.5, -9.5, 4.0),
        new Zone("Marché des Minerais", "Troc & hôtel des ventes", -14.5, 0.5, 5.0),
        new Zone("Autel des Quêtes", "Le Champion de l'Éther", 0.5, -14.5, 5.5),
        new Zone("Portail des Donjons", "Cinq vagues, un Titan", 0.5, 15.5, 5.5),
        new Zone("Jardin des Cerisiers", "Pétales & quiétude", SpawnGardenBuilder.CHERRY[0] + 0.5, SpawnGardenBuilder.CHERRY[1] + 0.5, 5.5),
        new Zone("Bassin Céleste", "Poissons & axolotls", SpawnGardenBuilder.POND[0] + 0.5, SpawnGardenBuilder.POND[1] + 0.5, 5.5),
        new Zone("Prairie des Lucioles", "Fleurs & pergola", SpawnGardenBuilder.MEADOW[0] + 0.5, SpawnGardenBuilder.MEADOW[1] + 0.5, 5.5),
        new Zone("Agora Céleste", "Le cœur du spawn", 0.5, 0.5, 7.0)
    };

    private static final long TITLE_COOLDOWN_MS = 2500L;

    private final Map<UUID, Integer> lastZone = new HashMap<>();
    private final Map<UUID, Long> lastTitle = new HashMap<>();

    public static boolean playersNearby(World w, double range) {
        for (Player p : w.getPlayers()) {
            Location l = p.getLocation();
            if (l.getY() > 90 && Math.hypot(l.getX() - 0.5, l.getZ() - 0.5) < range) return true;
        }
        return false;
    }

    public void tick(long tick, World w) {
        if (w == null || !playersNearby(w, 70)) return;
        boolean night = w.getTime() >= 12500 && w.getTime() <= 23500;
        petals(w);
        fountain(w, tick);
        if (night) fireflies(w, tick);
        if (tick % 8 == 0) mist(w);
        if (tick % 10 == 0) zones(w);
        if (tick % 200 == 0) sounds(w, tick);
    }

    private void petals(World w) {
        int cx = SpawnGardenBuilder.CHERRY[0], cz = SpawnGardenBuilder.CHERRY[1];
        w.spawnParticle(Particle.CHERRY_LEAVES, cx - 1.5, 127.0, cz - 1.5, 1, 1.6, 0.4, 1.6, 0);
        w.spawnParticle(Particle.CHERRY_LEAVES, cx + 3.5, 126.0, cz + 1.5, 1, 1.4, 0.4, 1.4, 0);
    }

    private void fountain(World w, long tick) {
        double fx = SpawnGardenBuilder.POND[0] + 0.5, fz = SpawnGardenBuilder.POND[1] + 0.5;
        w.spawnParticle(Particle.FALLING_WATER, fx, 124.3, fz, 5, 0.25, 0.05, 0.25, 0);
        w.spawnParticle(Particle.SPLASH, fx, 120.95, fz, 3, 1.2, 0.0, 1.2, 0);
        if (tick % 6 == 0) {
            w.spawnParticle(Particle.BUBBLE_POP, fx, 121.1, fz, 2, 1.5, 0.0, 1.5, 0);
        }
    }

    private void fireflies(World w, long tick) {
        for (int i = 0; i < 18; i++) {
            if ((tick / 2 + i) % 3 == 0) continue; // scintillement
            int[] c = (i % 3 == 0) ? SpawnGardenBuilder.CHERRY : (i % 3 == 1) ? SpawnGardenBuilder.POND : SpawnGardenBuilder.MEADOW;
            double phase = i * 1.7;
            double x = c[0] + 0.5 + 4.2 * Math.sin(tick * 0.011 * (1 + (i % 4) * 0.3) + phase);
            double z = c[1] + 0.5 + 4.2 * Math.cos(tick * 0.009 * (1 + (i % 3) * 0.4) + phase * 1.3);
            double y = 122.3 + 1.1 * (1 + Math.sin(tick * 0.03 + i));
            w.spawnParticle(Particle.WAX_ON, x, y, z, 1, 0, 0, 0, 0);
        }
    }

    private void mist(World w) {
        ThreadLocalRandom r = ThreadLocalRandom.current();
        double angle = r.nextDouble() * Math.PI * 2;
        double radius = 9 + r.nextDouble() * 10;
        double depth = Math.max(1, (20 - radius) * 0.75);
        w.spawnParticle(Particle.CLOUD, 0.5 + radius * Math.cos(angle), 120 - depth - 0.3, 0.5 + radius * Math.sin(angle),
            2, 0.5, 0.15, 0.5, 0.004);
    }

    private void zones(World w) {
        long now = System.currentTimeMillis();
        for (Player p : w.getPlayers()) {
            Location l = p.getLocation();
            int idx = Math.abs(l.getY() - 121) <= 8 ? zoneAt(l.getX(), l.getZ()) : -1;
            Integer prev = lastZone.put(p.getUniqueId(), idx);
            if (idx < 0 || (prev != null && prev == idx)) continue;
            Long last = lastTitle.get(p.getUniqueId());
            if (last != null && now - last < TITLE_COOLDOWN_MS) continue;
            lastTitle.put(p.getUniqueId(), now);
            Zone z = ZONES[idx];
            p.sendTitle(ChatColor.GOLD + z.name, ChatColor.GRAY + z.sub, 8, 28, 10);
        }
    }

    private int zoneAt(double x, double z) {
        for (int i = 0; i < ZONES.length; i++) {
            double dx = x - ZONES[i].x, dz = z - ZONES[i].z;
            if (dx * dx + dz * dz <= ZONES[i].r * ZONES[i].r) return i;
        }
        return -1;
    }

    private void sounds(World w, long tick) {
        Location pond = new Location(w, SpawnGardenBuilder.POND[0] + 0.5, 121, SpawnGardenBuilder.POND[1] + 0.5);
        Location meadow = new Location(w, SpawnGardenBuilder.MEADOW[0] + 0.5, 122, SpawnGardenBuilder.MEADOW[1] + 0.5);
        for (Player p : w.getPlayers()) {
            Location l = p.getLocation();
            if (l.getWorld() != w) continue;
            if (l.distanceSquared(pond) < 144) {
                p.playSound(pond, Sound.BLOCK_WATER_AMBIENT, 0.5f, 1.0f);
            }
            if (tick % 400 == 0 && l.distanceSquared(meadow) < 196) {
                float pitch = 1.2f + (float) ThreadLocalRandom.current().nextDouble(0.8);
                p.playSound(meadow, Sound.BLOCK_AMETHYST_BLOCK_CHIME, 0.35f, pitch);
            }
        }
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        lastZone.remove(event.getPlayer().getUniqueId());
        lastTitle.remove(event.getPlayer().getUniqueId());
    }
}
