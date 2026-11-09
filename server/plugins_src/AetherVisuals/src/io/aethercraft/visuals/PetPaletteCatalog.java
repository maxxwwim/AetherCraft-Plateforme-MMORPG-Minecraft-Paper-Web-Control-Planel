package io.aethercraft.visuals;

import io.aethercraft.visuals.PetRenderer.VoxelPetRig;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Particle;
import org.bukkit.World;
import org.bukkit.entity.Player;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;

/**
 * Palettes de matériaux 3D et auras élémentaires des familiers célestes.
 */
public final class PetPaletteCatalog {

    private PetPaletteCatalog() {}

    public static class PetPalette {
        public final String displayName;
        public final Material torsoMat;
        public final Material chestMat;
        public final Material headMat;
        public final Material snoutMat;
        public final Material hornMat;
        public final Material legMat;
        public final Material wingMat;
        public final Material tailMat;
        public final float scaleMultiplier;
        public final double hoverHeight;

        public PetPalette(String displayName, Material torsoMat, Material chestMat, Material headMat,
                          Material snoutMat, Material hornMat, Material legMat, Material wingMat,
                          Material tailMat, float scaleMultiplier, double hoverHeight) {
            this.displayName = displayName;
            this.torsoMat = torsoMat;
            this.chestMat = chestMat;
            this.headMat = headMat;
            this.snoutMat = snoutMat;
            this.hornMat = hornMat;
            this.legMat = legMat;
            this.wingMat = wingMat;
            this.tailMat = tailMat;
            this.scaleMultiplier = scaleMultiplier;
            this.hoverHeight = hoverHeight;
        }
    }

    public static PetPalette getPalette(String type) {
        return switch (type) {
            case "dragon" -> new PetPalette(
                    "§d§l🐉 DRAGONEAU DE L'AETHER",
                    Material.CRYING_OBSIDIAN, Material.AMETHYST_BLOCK, Material.PURPUR_BLOCK,
                    Material.GOLD_BLOCK, Material.END_ROD, Material.OBSIDIAN,
                    Material.MAGENTA_STAINED_GLASS, Material.AMETHYST_CLUSTER, 1.15f, 1.35);
            case "capybara" -> new PetPalette(
                    "§a§l🌿 CAPYBARA IMPÉRIAL CÉLESTE",
                    Material.STRIPPED_SPRUCE_WOOD, Material.MOSS_BLOCK, Material.STRIPPED_DARK_OAK_WOOD,
                    Material.MUD_BRICKS, Material.PINK_TULIP, Material.DARK_OAK_PLANKS,
                    Material.LILY_PAD, Material.GOLD_BLOCK, 1.20f, 0.45);
            case "fox" -> new PetPalette(
                    "§6§l🦊 KITSUNE ASTRAL À 9 QUEUES",
                    Material.ORANGE_CONCRETE, Material.WHITE_WOOL, Material.RED_SANDSTONE,
                    Material.SNOW_BLOCK, Material.GOLD_BLOCK, Material.BLACK_CONCRETE,
                    Material.SEA_LANTERN, Material.SHROOMLIGHT, 1.12f, 0.65);
            case "goat" -> new PetPalette(
                    "§b§l🐐 BÉLIER ROYAL DES NUAGES",
                    Material.QUARTZ_BRICKS, Material.GOLD_BLOCK, Material.SNOW_BLOCK,
                    Material.CHISELED_QUARTZ_BLOCK, Material.RAW_GOLD_BLOCK, Material.POLISHED_BASALT,
                    Material.DIAMOND_BLOCK, Material.WHITE_WOOL, 1.18f, 0.60);
            case "phoenix" -> new PetPalette(
                    "§c§l🦅 PHÉNIX D'OR PRIMORDIAL",
                    Material.MAGMA_BLOCK, Material.GOLD_BLOCK, Material.SHROOMLIGHT,
                    Material.RESPAWN_ANCHOR, Material.YELLOW_STAINED_GLASS, Material.RED_NETHER_BRICKS,
                    Material.ORANGE_STAINED_GLASS, Material.GLOWSTONE, 1.22f, 1.65);
            default -> new PetPalette(
                    "§e§l🦁 GRIFFON ASTRAL SOUVERAIN",
                    Material.GOLD_BLOCK, Material.QUARTZ_BLOCK, Material.SNOW_BLOCK,
                    Material.HONEYCOMB_BLOCK, Material.DIAMOND_BLOCK, Material.STRIPPED_OAK_WOOD,
                    Material.WHITE_STAINED_GLASS, Material.GLOWSTONE, 1.20f, 1.40);
        };
    }

    public static void applyPetBuffsAndParticles(Player p, VoxelPetRig rig, String type, long tick) {
        if (rig.torso == null || !rig.torso.isValid()) return;
        Location loc = rig.torso.getLocation();
        World w = p.getWorld();

        switch (type) {
            case "dragon" -> {
                if (tick % 4 == 0) {
                    w.spawnParticle(Particle.DRAGON_BREATH, loc, 2, 0.18, 0.18, 0.18, 0.01);
                    w.spawnParticle(Particle.END_ROD, loc.clone().add(0, 0.2, 0), 1, 0.1, 0.1, 0.1, 0.01);
                }
                if (tick % 40 == 0) p.addPotionEffect(new PotionEffect(PotionEffectType.HASTE, 60, 0, false, false));
            }
            case "capybara" -> {
                if (tick % 10 == 0) w.spawnParticle(Particle.HEART, loc.clone().add(0, 0.55, 0), 1, 0.15, 0.1, 0.15, 0);
                if (tick % 40 == 0) p.addPotionEffect(new PotionEffect(PotionEffectType.REGENERATION, 60, 0, false, false));
            }
            case "fox" -> {
                if (tick % 4 == 0) w.spawnParticle(Particle.SOUL_FIRE_FLAME, loc, 2, 0.15, 0.12, 0.15, 0.01);
                if (tick % 40 == 0) p.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 60, 0, false, false));
            }
            case "goat" -> {
                if (tick % 4 == 0) w.spawnParticle(Particle.CLOUD, loc.clone().add(0, -0.25, 0), 2, 0.15, 0.05, 0.15, 0.01);
                p.setFallDistance(0);
                if (tick % 40 == 0) p.addPotionEffect(new PotionEffect(PotionEffectType.JUMP_BOOST, 60, 1, false, false));
            }
            case "phoenix" -> {
                if (tick % 4 == 0) {
                    w.spawnParticle(Particle.FLAME, loc, 3, 0.22, 0.18, 0.22, 0.02);
                    w.spawnParticle(Particle.LAVA, loc, 1, 0.1, 0.1, 0.1, 0);
                }
                if (tick % 40 == 0) p.addPotionEffect(new PotionEffect(PotionEffectType.FIRE_RESISTANCE, 60, 0, false, false));
            }
            default -> {
                if (tick % 4 == 0) w.spawnParticle(Particle.WAX_ON, loc, 2, 0.2, 0.2, 0.2, 0.01);
                if (tick % 40 == 0) p.addPotionEffect(new PotionEffect(PotionEffectType.STRENGTH, 60, 0, false, false));
            }
        }
    }
}
