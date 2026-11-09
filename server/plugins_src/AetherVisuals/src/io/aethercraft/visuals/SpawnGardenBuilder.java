package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.block.BlockFace;
import org.bukkit.block.data.type.Lantern;
import org.bukkit.block.data.type.Leaves;
import org.bukkit.block.data.type.Stairs;

import java.util.Random;

/**
 * Construit les trois jardins de l'Agora Celeste (Cerisiers, Bassin, Prairie) et les lampadaires.
 * Placement strictement non destructif (blocs d'air uniquement, sauf le sol des jardins) et idempotent.
 */
public final class SpawnGardenBuilder {

    public static final int FLOOR_Y = 120;
    public static final int[] CHERRY = {9, -9};
    public static final int[] POND = {9, 9};
    public static final int[] MEADOW = {-9, 9};
    public static final double GARDEN_R = 4.5;
    public static final double POND_R = 3.5;

    private static final Material[] FLOWERS = {
        Material.POPPY, Material.DANDELION, Material.BLUE_ORCHID, Material.ALLIUM, Material.AZURE_BLUET,
        Material.RED_TULIP, Material.ORANGE_TULIP, Material.WHITE_TULIP, Material.PINK_TULIP,
        Material.OXEYE_DAISY, Material.CORNFLOWER, Material.LILY_OF_THE_VALLEY,
        Material.SHORT_GRASS, Material.SHORT_GRASS, Material.FERN, Material.AZALEA, Material.FLOWERING_AZALEA
    };
    private static final int WILD_FLOWERS = 12;

    private interface Cell {
        void at(int x, int z, int dx, int dz, double d);
    }

    private SpawnGardenBuilder() { }

    public static void buildAll(World w) {
        if (w == null || w.getBlockAt(0, FLOOR_Y, 0).getType() == Material.AIR) return;
        buildCherryGarden(w, CHERRY[0], CHERRY[1]);
        buildPond(w, POND[0], POND[1]);
        buildMeadow(w, MEADOW[0], MEADOW[1]);
        buildLampposts(w);
    }

    // ------------------------------------------------------------------ Jardin des Cerisiers

    private static void buildCherryGarden(World w, int cx, int cz) {
        Random rnd = new Random(cx * 1000L + cz);
        paintGrass(w, cx, cz, rnd);
        cherryTree(w, cx - 2, cz - 2, 5);
        cherryTree(w, cx + 3, cz + 1, 4);
        stairs(w, cx - 1, FLOOR_Y + 1, cz + 3, Material.CHERRY_STAIRS, BlockFace.SOUTH);
        stairs(w, cx, FLOOR_Y + 1, cz + 3, Material.CHERRY_STAIRS, BlockFace.SOUTH);
        post(w, cx + 2, cz + 3, Material.CHERRY_FENCE, 2);
        disc(cx, cz, GARDEN_R, (x, z, dx, dz, d) -> {
            int roll = rnd.nextInt(100);
            if (!plantable(w.getBlockAt(x, FLOOR_Y, z))) return;
            if (roll < 28) {
                put(w, x, FLOOR_Y + 1, z, Material.PINK_PETALS);
            } else if (roll < 55) {
                put(w, x, FLOOR_Y + 1, z, Material.SHORT_GRASS);
            } else if (roll < 60) {
                put(w, x, FLOOR_Y + 1, z, Material.FERN);
            }
        });
    }

    private static void cherryTree(World w, int x, int z, int height) {
        if (!plantable(w.getBlockAt(x, FLOOR_Y, z))) return;
        for (int h = 1; h <= height; h++) {
            put(w, x, FLOOR_Y + h, z, Material.CHERRY_LOG);
        }
        int top = FLOOR_Y + height;
        for (int dy = -1; dy <= 2; dy++) {
            int r = dy <= 0 ? 2 : 1;
            for (int dx = -r; dx <= r; dx++) {
                for (int dz = -r; dz <= r; dz++) {
                    if (dx * dx + dz * dz <= r * r + 1) {
                        leaf(w, x + dx, top + dy, z + dz);
                    }
                }
            }
        }
    }

    private static void leaf(World w, int x, int y, int z) {
        Block b = w.getBlockAt(x, y, z);
        if (b.getType() != Material.AIR) return;
        Leaves data = (Leaves) Bukkit.createBlockData(Material.CHERRY_LEAVES);
        data.setPersistent(true);
        b.setBlockData(data, false);
    }

    // ------------------------------------------------------------------ Bassin Celeste

    private static void buildPond(World w, int cx, int cz) {
        Random rnd = new Random(cx * 1000L + cz);
        paintGrass(w, cx, cz, rnd);
        post(w, cx + 4, cz, Material.STONE_BRICK_WALL, 2);
        post(w, cx - 4, cz, Material.STONE_BRICK_WALL, 2);
        post(w, cx, cz + 4, Material.STONE_BRICK_WALL, 2);
        post(w, cx, cz - 4, Material.STONE_BRICK_WALL, 2);
        disc(cx, cz, POND_R + 1.2, (x, z, dx, dz, d) -> {
            if (d <= POND_R) {
                carve(w, x, z, d, rnd.nextInt(100));
            } else {
                buildRim(w, x, z, dx, dz);
            }
        });
        for (int y = FLOOR_Y - 1; y <= FLOOR_Y + 2; y++) {
            w.getBlockAt(cx, y, cz).setType(Material.QUARTZ_PILLAR, false);
        }
        w.getBlockAt(cx, FLOOR_Y + 3, cz).setType(Material.SEA_LANTERN, false);
        disc(cx, cz, GARDEN_R, (x, z, dx, dz, d) -> {
            int roll = rnd.nextInt(100);
            int pick = rnd.nextInt(WILD_FLOWERS);
            if (d <= POND_R + 1.2 || !plantable(w.getBlockAt(x, FLOOR_Y, z))) return;
            if (roll < 30) {
                put(w, x, FLOOR_Y + 1, z, Material.SHORT_GRASS);
            } else if (roll < 40) {
                put(w, x, FLOOR_Y + 1, z, FLOWERS[pick]);
            }
        });
    }

    private static void carve(World w, int x, int z, double d, int roll) {
        Block top = w.getBlockAt(x, FLOOR_Y, z);
        Block mid = w.getBlockAt(x, FLOOR_Y - 1, z);
        Block low = w.getBlockAt(x, FLOOR_Y - 2, z);
        if (top.getType() == Material.WATER) return;
        // On ne creuse que si le bassin est entierement contenu (aucune fuite d'eau dans le vide).
        if (!(top.getType().isSolid() && mid.getType().isSolid() && low.getType().isSolid())) return;
        top.setType(Material.WATER, false);
        mid.setType(Material.WATER, false);
        if (d <= 1.6) {
            low.setType(Material.SEA_LANTERN, false);
        } else if (roll < 22) {
            mid.setType(Material.SEAGRASS, false);
        } else if (roll < 40) {
            put(w, x, FLOOR_Y + 1, z, Material.LILY_PAD);
        }
    }

    private static void buildRim(World w, int x, int z, int dx, int dz) {
        Block floor = w.getBlockAt(x, FLOOR_Y, z);
        if (plantable(floor) || floor.getType() == Material.SMOOTH_QUARTZ) {
            floor.setType(Material.POLISHED_ANDESITE, false);
        }
        boolean gapTowardCenter = dx < 0 && dz < 0 && Math.abs(dx - dz) <= 2;
        if (!gapTowardCenter) {
            put(w, x, FLOOR_Y + 1, z, Material.STONE_BRICK_SLAB);
        }
    }

    // ------------------------------------------------------------------ Prairie des Lucioles

    private static void buildMeadow(World w, int cx, int cz) {
        Random rnd = new Random(cx * 1000L + cz);
        paintGrass(w, cx, cz, rnd);
        pergola(w, cx, cz);
        disc(cx, cz, GARDEN_R, (x, z, dx, dz, d) -> {
            int roll = rnd.nextInt(100);
            int pick = rnd.nextInt(FLOWERS.length);
            if (plantable(w.getBlockAt(x, FLOOR_Y, z)) && roll < 70) {
                put(w, x, FLOOR_Y + 1, z, FLOWERS[pick]);
            }
        });
    }

    private static void pergola(World w, int cx, int cz) {
        for (int dx = -1; dx <= 1; dx++) {
            for (int dz = -1; dz <= 1; dz++) {
                Block f = w.getBlockAt(cx + dx, FLOOR_Y, cz + dz);
                if (plantable(f) || f.getType() == Material.SMOOTH_QUARTZ) {
                    f.setType(Material.SPRUCE_PLANKS, false);
                }
            }
        }
        for (int sx = -2; sx <= 2; sx += 4) {
            for (int sz = -2; sz <= 2; sz += 4) {
                for (int h = 1; h <= 3; h++) {
                    put(w, cx + sx, FLOOR_Y + h, cz + sz, Material.OAK_FENCE);
                }
            }
        }
        for (int dx = -2; dx <= 2; dx++) {
            for (int dz = -2; dz <= 2; dz++) {
                if (Math.abs(dx) == 2 || Math.abs(dz) == 2 || dx == 0 || dz == 0) {
                    put(w, cx + dx, FLOOR_Y + 4, cz + dz, Material.OAK_SLAB);
                }
            }
        }
        stairs(w, cx - 1, FLOOR_Y + 1, cz, Material.OAK_STAIRS, BlockFace.WEST);
        stairs(w, cx + 1, FLOOR_Y + 1, cz, Material.OAK_STAIRS, BlockFace.EAST);
        put(w, cx, FLOOR_Y + 1, cz, Material.POTTED_AZALEA_BUSH);
        lantern(w, cx, FLOOR_Y + 3, cz - 1, true);
        lantern(w, cx, FLOOR_Y + 3, cz + 1, true);
    }

    // ------------------------------------------------------------------ Lampadaires

    private static void buildLampposts(World w) {
        for (int k = 0; k < 8; k++) {
            double angle = Math.toRadians(22.5 + 45.0 * k);
            int x = (int) Math.round(8 * Math.cos(angle));
            int z = (int) Math.round(8 * Math.sin(angle));
            if (w.getBlockAt(x, FLOOR_Y, z).getType() != Material.AIR) {
                post(w, x, z, Material.STONE_BRICK_WALL, 3);
            }
        }
    }

    // ------------------------------------------------------------------ Utilitaires

    private static void disc(int cx, int cz, double r, Cell cell) {
        int n = (int) Math.ceil(r);
        for (int dx = -n; dx <= n; dx++) {
            for (int dz = -n; dz <= n; dz++) {
                double d = Math.sqrt(dx * dx + dz * dz);
                if (d <= r) {
                    cell.at(cx + dx, cz + dz, dx, dz, d);
                }
            }
        }
    }

    private static void paintGrass(World w, int cx, int cz, Random rnd) {
        disc(cx, cz, GARDEN_R, (x, z, dx, dz, d) -> {
            boolean moss = rnd.nextInt(100) < 12;
            Block floor = w.getBlockAt(x, FLOOR_Y, z);
            if (floor.getType() == Material.SMOOTH_QUARTZ) {
                floor.setType(moss ? Material.MOSS_BLOCK : Material.GRASS_BLOCK, false);
            }
        });
    }

    private static boolean plantable(Block floor) {
        Material m = floor.getType();
        return m == Material.GRASS_BLOCK || m == Material.MOSS_BLOCK;
    }

    private static boolean put(World w, int x, int y, int z, Material m) {
        Block b = w.getBlockAt(x, y, z);
        if (b.getType() != Material.AIR) return false;
        b.setType(m, false);
        return true;
    }

    private static void post(World w, int x, int z, Material m, int height) {
        for (int i = 1; i <= height; i++) {
            put(w, x, FLOOR_Y + i, z, m);
        }
        lantern(w, x, FLOOR_Y + height + 1, z, false);
    }

    private static void stairs(World w, int x, int y, int z, Material m, BlockFace back) {
        Block b = w.getBlockAt(x, y, z);
        if (b.getType() != Material.AIR) return;
        Stairs data = (Stairs) Bukkit.createBlockData(m);
        data.setFacing(back);
        b.setBlockData(data, false);
    }

    private static void lantern(World w, int x, int y, int z, boolean hanging) {
        Block b = w.getBlockAt(x, y, z);
        if (b.getType() != Material.AIR) return;
        Lantern data = (Lantern) Bukkit.createBlockData(Material.LANTERN);
        data.setHanging(hanging);
        b.setBlockData(data, false);
    }
}
