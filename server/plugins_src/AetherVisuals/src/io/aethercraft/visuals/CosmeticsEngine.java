package io.aethercraft.visuals;

import org.bukkit.Color;
import org.bukkit.Location;
import org.bukkit.Particle;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.util.Vector;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

public class CosmeticsEngine {

    private final Set<UUID> activeWings = new HashSet<>();
    private final Map<UUID, String> activePets = new HashMap<>();
    private final Map<UUID, String> activeAuras = new HashMap<>();
    private final PetRenderer petRenderer = new PetRenderer();

    // Couleurs DUST
    private final Particle.DustOptions cyanDust = new Particle.DustOptions(Color.fromRGB(56, 189, 248), 1.2f);
    private final Particle.DustOptions indigoDust = new Particle.DustOptions(Color.fromRGB(99, 102, 241), 1.0f);
    private final Particle.DustOptions purpleDust = new Particle.DustOptions(Color.fromRGB(168, 85, 247), 1.3f);
    private final Particle.DustOptions goldDust = new Particle.DustOptions(Color.fromRGB(245, 158, 11), 1.3f);
    private final Particle.DustOptions emeraldDust = new Particle.DustOptions(Color.fromRGB(16, 185, 129), 1.2f);
    private final Particle.DustOptions fireDust = new Particle.DustOptions(Color.fromRGB(234, 88, 12), 1.3f);
    private final Particle.DustOptions capyBrown = new Particle.DustOptions(Color.fromRGB(120, 53, 15), 1.4f);
    private final Particle.DustOptions lotusPink = new Particle.DustOptions(Color.fromRGB(244, 114, 182), 1.2f);
    private final Particle.DustOptions foxOrange = new Particle.DustOptions(Color.fromRGB(249, 115, 22), 1.3f);
    private final Particle.DustOptions whiteWool = new Particle.DustOptions(Color.fromRGB(255, 255, 255), 1.4f);

    public void toggleWings(UUID uuid) {
        if (activeWings.contains(uuid)) activeWings.remove(uuid);
        else activeWings.add(uuid);
    }

    public void setWings(UUID uuid, boolean enabled) {
        if (enabled) activeWings.add(uuid);
        else activeWings.remove(uuid);
    }

    public boolean hasWings(UUID uuid) {
        return activeWings.contains(uuid);
    }

    public void setPet(UUID uuid, String petType) {
        if (petType == null || petType.equalsIgnoreCase("clear") || petType.equalsIgnoreCase("none")) {
            activePets.remove(uuid);
            petRenderer.removePet(uuid);
        } else {
            activePets.put(uuid, petType.toLowerCase());
        }
    }

    public String getPet(UUID uuid) {
        return activePets.get(uuid);
    }

    public boolean hasPet(UUID uuid) {
        return activePets.containsKey(uuid);
    }

    public void setAura(UUID uuid, String aura) {
        if (aura == null || aura.equalsIgnoreCase("clear") || aura.equalsIgnoreCase("none")) {
            activeAuras.remove(uuid);
        } else {
            activeAuras.put(uuid, aura.toLowerCase());
        }
    }

    public String getAura(UUID uuid) {
        return activeAuras.get(uuid);
    }

    public void clearAll(UUID uuid) {
        activeWings.remove(uuid);
        activePets.remove(uuid);
        activeAuras.remove(uuid);
        petRenderer.removePet(uuid);
    }

    public void clearAllEntities() {
        petRenderer.clearAll();
    }

    // ========================================================
    // MOTEUR D'ANIMATION PARTICULAIRE (Appelé chaque tick)
    // ========================================================

    public void tickPlayer(Player player, long tick) {
        UUID uuid = player.getUniqueId();

        if (activeWings.contains(uuid)) {
            renderWings(player, tick);
        }

        String petType = activePets.get(uuid);
        if (petType != null) {
            renderPetCompanion(player, petType, tick);
        }

        String aura = activeAuras.get(uuid);
        if (aura != null) {
            renderAura(player, aura, tick);
        }
    }

    // 1. AILES QUANTIQUES STELLAIRES (Battement & Envergure 3D)
    private void renderWings(Player player, long tick) {
        Location loc = player.getLocation();
        double yawRad = Math.toRadians(-loc.getYaw() - 90);
        double flap = Math.sin(tick * 0.25) * 0.35;

        double[][] wingMatrix = {
            {0.2, 0.2}, {0.4, 0.4}, {0.6, 0.7}, {0.8, 1.0}, {1.0, 1.3}, {1.3, 1.5},
            {0.4, 0.1}, {0.7, 0.3}, {1.0, 0.5}, {1.3, 0.8}, {1.5, 1.1},
            {0.5, -0.1}, {0.8, 0.0}, {1.1, 0.1}, {1.4, 0.3},
            {0.6, -0.3}, {0.9, -0.2}, {1.2, -0.1}
        };

        Vector backDir = loc.getDirection().setY(0).normalize().multiply(-0.25);
        Location centerBack = loc.clone().add(0, 1.0, 0).add(backDir);

        for (double[] pt : wingMatrix) {
            double rx = pt[0];
            double ry = pt[1];

            double zFlap = rx * Math.sin(flap);
            double xFlap = rx * Math.cos(flap);

            Vector rightVec = rotateAroundY(new Vector(xFlap, ry, zFlap), yawRad);
            Location rightLoc = centerBack.clone().add(rightVec);
            player.getWorld().spawnParticle(Particle.DUST, rightLoc, 1, 0, 0, 0, 0, cyanDust);

            Vector leftVec = rotateAroundY(new Vector(-xFlap, ry, zFlap), yawRad);
            Location leftLoc = centerBack.clone().add(leftVec);
            player.getWorld().spawnParticle(Particle.DUST, leftLoc, 1, 0, 0, 0, 0, indigoDust);

            if (rx >= 1.2 && (tick % 4 == 0)) {
                player.getWorld().spawnParticle(Particle.END_ROD, rightLoc, 1, 0, 0, 0, 0.01);
                player.getWorld().spawnParticle(Particle.END_ROD, leftLoc, 1, 0, 0, 0, 0.01);
            }
        }
    }

    // 2. MOTEUR DES 5 FAMILIERS CÉLESTES (Animations & Auras de Groupe)
    private void renderPetCompanion(Player player, String petType, long tick) {
        petRenderer.renderPetCompanion(player, petType, tick);
    }

    // 3. AURAS DE RANGS (VIP, AETHER, TITAN)
    private void renderAura(Player player, String type, long tick) {
        Location loc = player.getLocation();

        switch (type.toLowerCase()) {
            case "vip": {
                double radius = 0.85;
                int points = 12;
                double offset = (tick * 0.1) % (2 * Math.PI);

                for (int i = 0; i < points; i++) {
                    double theta = offset + (i * (2 * Math.PI / points));
                    double x = radius * Math.cos(theta);
                    double z = radius * Math.sin(theta);
                    Location pLoc = loc.clone().add(x, 0.1, z);

                    if (i % 2 == 0) {
                        player.getWorld().spawnParticle(Particle.DUST, pLoc, 1, 0, 0, 0, 0, emeraldDust);
                    } else {
                        player.getWorld().spawnParticle(Particle.DUST, pLoc, 1, 0, 0, 0, 0, goldDust);
                    }
                }
                break;
            }

            case "aether": {
                Location head = loc.clone().add(0, 2.15, 0);
                double haloRadius = 0.45;
                int haloPoints = 10;
                double angleOffset = (tick * 0.08) % (2 * Math.PI);

                for (int i = 0; i < haloPoints; i++) {
                    double theta = (i * (2 * Math.PI / haloPoints));
                    double hx = haloRadius * Math.cos(theta);
                    double hz = haloRadius * Math.sin(theta);
                    double hy = 0.08 * Math.sin(theta);
                    player.getWorld().spawnParticle(Particle.DUST, head.clone().add(hx, hy, hz), 1, 0, 0, 0, 0, cyanDust);
                }

                double sx = 0.65 * Math.cos(-angleOffset * 1.5);
                double sz = 0.65 * Math.sin(-angleOffset * 1.5);
                player.getWorld().spawnParticle(Particle.END_ROD, head.clone().add(sx, 0.05, sz), 1, 0, 0, 0, 0, 0.01);
                break;
            }

            case "titan": {
                double helixRadius = 0.8;
                double height = 2.0;
                double progress = (tick % 40) / 40.0;

                double currentY = progress * height;
                double theta1 = (progress * 4 * Math.PI);
                double theta2 = theta1 + Math.PI;

                double x1 = helixRadius * Math.cos(theta1);
                double z1 = helixRadius * Math.sin(theta1);
                double x2 = helixRadius * Math.cos(theta2);
                double z2 = helixRadius * Math.sin(theta2);

                player.getWorld().spawnParticle(Particle.FLAME, loc.clone().add(x1, currentY, z1), 1, 0, 0, 0, 0.01);
                player.getWorld().spawnParticle(Particle.DUST, loc.clone().add(x2, currentY, z2), 1, 0, 0, 0, 0, fireDust);

                if (tick % 10 == 0) {
                    player.getWorld().spawnParticle(Particle.LAVA, loc.clone().add(0, 0.2, 0), 1, 0.2, 0.1, 0.2, 0);
                }
                break;
            }

            case "champion": {
                // Aura du Champion du Royaume : Halo Astral & Sceau Stellaire Royal
                double crownRadius = 0.55;
                int crownPoints = 8;
                double angleOffset = (tick * 0.05) % (2 * Math.PI);
                Location head = loc.clone().add(0, 2.25, 0);

                Particle.DustOptions purpleDust = new Particle.DustOptions(org.bukkit.Color.fromRGB(168, 85, 247), 1.2f);
                for (int i = 0; i < crownPoints; i++) {
                    double theta = angleOffset + (i * (2 * Math.PI / crownPoints));
                    double cx = crownRadius * Math.cos(theta);
                    double cz = crownRadius * Math.sin(theta);
                    double cy = 0.08 * Math.sin((tick * 0.1) + i);
                    player.getWorld().spawnParticle(Particle.DUST, head.clone().add(cx, cy, cz), 1, 0, 0, 0, 0, purpleDust);
                    if (i % 2 == 0) {
                        player.getWorld().spawnParticle(Particle.DUST, head.clone().add(cx, cy + 0.1, cz), 1, 0, 0, 0, 0, goldDust);
                    }
                }

                // Sceau stellaire circulaire au sol
                double groundRadius = 1.05 + (0.12 * Math.sin(tick * 0.1));
                int groundPoints = 14;
                for (int i = 0; i < groundPoints; i++) {
                    double theta = -angleOffset + (i * (2 * Math.PI / groundPoints));
                    double gx = groundRadius * Math.cos(theta);
                    double gz = groundRadius * Math.sin(theta);
                    player.getWorld().spawnParticle(Particle.END_ROD, loc.clone().add(gx, 0.05, gz), 1, 0, 0, 0, 0, 0.005);
                }

                if (tick % 8 == 0) {
                    player.getWorld().spawnParticle(Particle.FIREWORK, loc.clone().add(0, 1.2, 0), 1, 0.3, 0.5, 0.3, 0.02);
                }
                break;
            }
        }
    }

    private Vector rotateAroundY(Vector v, double angle) {
        double cos = Math.cos(angle);
        double sin = Math.sin(angle);
        double x = v.getX() * cos + v.getZ() * sin;
        double z = -v.getX() * sin + v.getZ() * cos;
        return new Vector(x, v.getY(), z);
    }
}
