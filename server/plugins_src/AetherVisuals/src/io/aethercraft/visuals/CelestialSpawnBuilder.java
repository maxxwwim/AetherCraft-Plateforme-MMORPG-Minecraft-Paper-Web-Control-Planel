package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.block.Block;

public class CelestialSpawnBuilder {

    public static void buildSpawn(World world) {
        if (world == null) return;

        int cx = 0;
        int cy = 120;
        int cz = 0;
        int radius = AGORA_RADIUS;

        // 1. Île Flottante de l'Agora agrandie (Cône inversé : Or / Sang / Vert Hacker)
        for (int x = -radius; x <= radius; x++) {
            for (int z = -radius; z <= radius; z++) {
                double dist = Math.sqrt(x * x + z * z);
                if (dist <= radius) {
                    int depth = (int) Math.max(1, (radius - dist) * 0.75);

                    Material surf = agoraSurface(x, z, dist, radius);
                    world.getBlockAt(cx + x, cy, cz + z).setType(surf);

                    // Sous-sol & roche céleste
                    for (int d = 1; d <= depth; d++) {
                        Material sub = (d == 1) ? (dist > 19 ? Material.POLISHED_BLACKSTONE : Material.POLISHED_DIORITE) : Material.CALCITE;
                        if (dist > 19 && d > 1) sub = Material.BLACKSTONE;
                        if (d > 6) sub = Material.DEEPSLATE;
                        world.getBlockAt(cx + x, cy - d, cz + z).setType(sub);
                    }

                    // Nettoyer l'espace aérien
                    for (int h = 1; h <= 25; h++) {
                        world.getBlockAt(cx + x, cy + h, cz + z).setType(Material.AIR);
                    }
                }
            }
        }

        // 1b. Décors de l'extension : piliers, lacs et jardins hackers
        buildAgoraDecor(world, cx, cy, cz);

        // 2. Balise & Stèle Centrale
        buildCentralBeacon(world, cx, cy, 0);

        // 3. Trône du Champion (Nord : Z = -15)
        buildChampionAltar(world, cx, cy, -15);

        // 4. Portail des Donjons Instanciés (Sud : Z = 15)
        buildDungeonPortal(world, cx, cy, 15);

        // 5. Marché des Minerais (Ouest : X = -15)
        buildMarketStalls(world, cx - 15, cy, 0);

        // 6. Sanctuaire des Animaux (Est : X = 15)
        buildPetSanctuary(world, cx + 15, cy, 0);

        // 7. Banque Privée d'Éther (Nord-Ouest : X = -10, Z = -10)
        buildBankVault(world, -10, cy, -10);

        // 8. Portail du OneBlock Céleste (Sud-Ouest : X = -12, Z = 12)
        buildOneBlockPortal(world, -12, cy, 12);

        // Configurer le spawn officiel
        world.setSpawnLocation(cx, cy + 1, 0);
    }

    public static final int AGORA_RADIUS = 40;

    /** Surface par anneaux : cœur quartz poli, puis Pierre Noire polie, Vert Hacker, Sang, rebord Sang. */
    private static Material agoraSurface(int x, int z, double dist, int radius) {
        if (dist <= 18) {
            if (dist < 4) return Material.SMOOTH_QUARTZ;
            if ((Math.abs(x) == 8 || Math.abs(z) == 8) && dist < 17) return Material.SEA_LANTERN;
            return Material.SMOOTH_QUARTZ;
        }
        if (dist <= 20) return Material.POLISHED_BLACKSTONE;
        boolean checker = ((x + z) & 1) == 0;
        Material dark = checker ? Material.POLISHED_BLACKSTONE_BRICKS : Material.BLACKSTONE;
        // Allées en croix : ligne centrale bordée de sang
        if (dist <= radius - 2) {
            if (x == 0 || z == 0) return Material.POLISHED_BLACKSTONE;
            if (Math.abs(x) == 1 || Math.abs(z) == 1) return Material.RED_NETHER_BRICKS;
        }
        if (dist > radius - 2) return checker ? Material.POLISHED_BLACKSTONE : Material.RED_NETHER_BRICKS;
        if (dist >= 24 && dist <= 26) return (((x + z) % 3 + 3) % 3 == 0) ? Material.VERDANT_FROGLIGHT : Material.GREEN_CONCRETE;
        if (dist >= 30 && dist <= 32) return (((x + z) % 3 + 3) % 3 == 0) ? Material.REDSTONE_BLOCK : Material.RED_NETHER_BRICKS;
        if (dist >= 35 && dist <= 36) return Material.POLISHED_BLACKSTONE;
        return dark;
    }

    private static void buildAgoraDecor(World world, int cx, int cy, int cz) {
        // 8 piliers monumentaux sur l'anneau r=28 (alternance Vert Hacker / Or)
        for (int k = 0; k < 8; k++) {
            double a = Math.toRadians(k * 45 + 22.5);
            int px = cx + (int) Math.round(Math.cos(a) * 28);
            int pz = cz + (int) Math.round(Math.sin(a) * 28);
            for (int h = 1; h <= 9; h++) {
                Material m = (h % 3 == 0) ? Material.GOLD_BLOCK : Material.RED_NETHER_BRICKS;
                world.getBlockAt(px, cy + h, pz).setType(m);
            }
            world.getBlockAt(px, cy + 10, pz).setType((k % 2 == 0) ? Material.VERDANT_FROGLIGHT : Material.SHROOMLIGHT);
            for (int dx = -1; dx <= 1; dx++) for (int dz = -1; dz <= 1; dz++) {
                if (dx != 0 || dz != 0) world.getBlockAt(px + dx, cy + 1, pz + dz).setType(Material.POLISHED_BLACKSTONE_BRICK_SLAB);
            }
        }
        // 4 lacs sur les diagonales (eau sur fond émeraude, margelle d'or)
        int[][] lakes = {{24, 24}, {-24, 24}, {24, -24}, {-24, -24}};
        for (int[] l : lakes) {
            for (int x = -6; x <= 6; x++) for (int z = -6; z <= 6; z++) {
                double d = Math.sqrt(x * x + z * z);
                int bx = cx + l[0] + x, bz = cz + l[1] + z;
                if (d <= 4.5) {
                    world.getBlockAt(bx, cy - 1, bz).setType(Material.EMERALD_BLOCK);
                    world.getBlockAt(bx, cy, bz).setType(Material.WATER);
                } else if (d <= 5.7) {
                    world.getBlockAt(bx, cy, bz).setType(Material.GOLD_BLOCK);
                }
            }
        }
        // 4 jardins hackers (mousse, azalées, lumières vertes)
        int[][] gardens = {{32, 10}, {-32, 10}, {10, 32}, {-10, -32}};
        for (int[] g : gardens) {
            for (int x = -4; x <= 4; x++) for (int z = -4; z <= 4; z++) {
                double d = Math.sqrt(x * x + z * z);
                int bx = cx + g[0] + x, bz = cz + g[1] + z;
                if (Math.sqrt((double) (bx - cx) * (bx - cx) + (double) (bz - cz) * (bz - cz)) > AGORA_RADIUS - 3) continue;
                if (d <= 4) {
                    world.getBlockAt(bx, cy, bz).setType(Material.MOSS_BLOCK);
                    if (d > 0 && ((x + z) & 1) == 0 && d <= 3) world.getBlockAt(bx, cy + 1, bz).setType(Material.MOSS_CARPET);
                }
            }
            world.getBlockAt(cx + g[0], cy + 1, cz + g[1]).setType(Material.FLOWERING_AZALEA);
            world.getBlockAt(cx + g[0] + 2, cy + 1, cz + g[1]).setType(Material.AZALEA);
            world.getBlockAt(cx + g[0] - 2, cy + 1, cz + g[1]).setType(Material.AZALEA);
            world.getBlockAt(cx + g[0], cy, cz + g[1] + 3).setType(Material.VERDANT_FROGLIGHT);
        }
    }

    public static void buildBankVault(World world, int bx, int cy, int bz) {
        if (world == null) return;
        // Sol de guichet Dofus (Pierre noire polie et bordure dorée)
        for (int x = -2; x <= 2; x++) {
            for (int z = -2; z <= 2; z++) {
                world.getBlockAt(bx + x, cy, bz + z).setType((Math.abs(x) == 2 || Math.abs(z) == 2) ? Material.GOLD_BLOCK : Material.POLISHED_BLACKSTONE_BRICKS);
            }
        }
        // Comptoir de banque en chêne sombre
        world.getBlockAt(bx - 1, cy + 1, bz - 1).setType(Material.DARK_OAK_STAIRS);
        world.getBlockAt(bx, cy + 1, bz - 1).setType(Material.DARK_OAK_STAIRS);
        world.getBlockAt(bx + 1, cy + 1, bz - 1).setType(Material.DARK_OAK_STAIRS);

        // Guichet de coffre-fort cliquable au comptoir
        world.getBlockAt(bx, cy + 1, bz).setType(Material.ENDER_CHEST);

        // Grille de sécurité en barreaux de fer
        world.getBlockAt(bx - 1, cy + 1, bz + 1).setType(Material.IRON_BARS);
        world.getBlockAt(bx + 1, cy + 1, bz + 1).setType(Material.IRON_BARS);
        world.getBlockAt(bx - 1, cy + 2, bz + 1).setType(Material.IRON_BARS);
        world.getBlockAt(bx + 1, cy + 2, bz + 1).setType(Material.IRON_BARS);

        // Réserve de Kamas et Lingots visible en arrière-guichet
        world.getBlockAt(bx, cy + 1, bz + 2).setType(Material.GOLD_BLOCK);
        world.getBlockAt(bx - 1, cy + 1, bz + 2).setType(Material.RAW_GOLD_BLOCK);
        world.getBlockAt(bx + 1, cy + 1, bz + 2).setType(Material.EMERALD_BLOCK);

        // Lanternes marines célestes
        world.getBlockAt(bx - 2, cy + 1, bz - 2).setType(Material.SEA_LANTERN);
        world.getBlockAt(bx + 2, cy + 1, bz - 2).setType(Material.SEA_LANTERN);

        AetherBankEngine.spawnBankHologram(world);
    }

    private static void buildCentralBeacon(World world, int cx, int cy, int cz) {
        for (int x = -2; x <= 2; x++) {
            for (int z = -2; z <= 2; z++) {
                world.getBlockAt(cx + x, cy, cz + z).setType(Material.NETHERITE_BLOCK);
            }
        }
        world.getBlockAt(cx, cy + 1, cz).setType(Material.BEACON);
        world.getBlockAt(cx - 2, cy + 1, cz - 2).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx + 2, cy + 1, cz - 2).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx - 2, cy + 1, cz + 2).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx + 2, cy + 1, cz + 2).setType(Material.SEA_LANTERN);
        buildJumpPads(world, cx, cy, cz);
    }

    public static void buildJumpPads(World world, int cx, int cy, int cz) {
        if (world == null) return;
        int[][] offsets = {{0, 5}, {0, -5}, {-5, 0}, {5, 0}};
        for (int[] off : offsets) {
            world.getBlockAt(cx + off[0], cy, cz + off[1]).setType(Material.SEA_LANTERN);
            world.getBlockAt(cx + off[0], cy + 1, cz + off[1]).setType(Material.POLISHED_BLACKSTONE_PRESSURE_PLATE);
        }
    }

    /**
     * Nettoie les anciennes dalles de pression en or au sol du spawn céleste et remplace
     * tout bloc d'or du sol d'agora par du quartz poli ou de la pierre noire polie (F12).
     */
    public static void cleanSpawnGoldSlabs(World world) {
        if (world == null) return;
        int cx = 0;
        int cy = 120;
        int cz = 0;
        int radius = AGORA_RADIUS + 5;
        for (int x = -radius; x <= radius; x++) {
            for (int z = -radius; z <= radius; z++) {
                double dist = Math.sqrt(x * x + z * z);
                if (dist <= radius) {
                    for (int y = cy; y <= cy + 2; y++) {
                        Block b = world.getBlockAt(cx + x, y, cz + z);
                        if (b.getType().name().equals("LIGHT_WEIGHTED_PRESSURE_PLATE")) {
                            b.setType(Material.POLISHED_BLACKSTONE_PRESSURE_PLATE);
                        } else if (y == cy && b.getType() == Material.GOLD_BLOCK) {
                            b.setType(Material.SMOOTH_QUARTZ);
                        }
                    }
                }
            }
        }
    }

    private static void buildChampionAltar(World world, int cx, int cy, int cz) {
        for (int x = -3; x <= 3; x++) {
            for (int z = -3; z <= 3; z++) {
                world.getBlockAt(cx + x, cy + 1, cz + z).setType(Material.PURPUR_BLOCK);
            }
        }
        world.getBlockAt(cx, cy + 2, cz).setType(Material.CRYING_OBSIDIAN);
        world.getBlockAt(cx, cy + 3, cz).setType(Material.BEACON);
        world.getBlockAt(cx, cy + 4, cz).setType(Material.PURPLE_STAINED_GLASS);
        world.getBlockAt(cx - 1, cy + 2, cz).setType(Material.AMETHYST_CLUSTER);
        world.getBlockAt(cx + 1, cy + 2, cz).setType(Material.AMETHYST_CLUSTER);
    }

    public static void buildDungeonPortal(World world, int cx, int cy, int cz) {
        if (world == null) return;
        // Cadre de portail imposant 5x6
        for (int x = -2; x <= 2; x++) {
            for (int y = 0; y <= 5; y++) {
                if (x == -2 || x == 2 || y == 0 || y == 5) {
                    world.getBlockAt(cx + x, cy + y, cz).setType(Material.OBSIDIAN);
                } else {
                    world.getBlockAt(cx + x, cy + y, cz).setType(Material.AIR);
                }
            }
        }
        Bukkit.dispatchCommand(Bukkit.getConsoleSender(), 
            String.format("fill %d %d %d %d %d %d minecraft:nether_portal[axis=x]", cx - 1, cy + 1, cz, cx + 1, cy + 4, cz));
        world.getBlockAt(cx - 3, cy + 1, cz).setType(Material.CRYING_OBSIDIAN);
        world.getBlockAt(cx - 3, cy + 2, cz).setType(Material.CRYING_OBSIDIAN);
        world.getBlockAt(cx + 3, cy + 1, cz).setType(Material.CRYING_OBSIDIAN);
        world.getBlockAt(cx + 3, cy + 2, cz).setType(Material.CRYING_OBSIDIAN);
        world.getBlockAt(cx - 2, cy + 6, cz).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx + 2, cy + 6, cz).setType(Material.SEA_LANTERN);
        PortalTeleportEngine.spawnPortalHolograms(world);
    }

    public static void buildOneBlockPortal(World world, int cx, int cy, int cz) {
        if (world == null) return;
        for (int x = -2; x <= 2; x++) {
            for (int y = 0; y <= 5; y++) {
                if (x == -2 || x == 2 || y == 0 || y == 5) {
                    world.getBlockAt(cx + x, cy + y, cz).setType((x == 0 && y == 5) ? Material.RESPAWN_ANCHOR : Material.CRYING_OBSIDIAN);
                } else {
                    world.getBlockAt(cx + x, cy + y, cz).setType(Material.AIR);
                }
            }
        }
        Bukkit.dispatchCommand(Bukkit.getConsoleSender(), 
            String.format("fill %d %d %d %d %d %d minecraft:nether_portal[axis=x]", cx - 1, cy + 1, cz, cx + 1, cy + 4, cz));
        world.getBlockAt(cx - 3, cy + 1, cz).setType(Material.AMETHYST_BLOCK);
        world.getBlockAt(cx - 3, cy + 2, cz).setType(Material.AMETHYST_BLOCK);
        world.getBlockAt(cx + 3, cy + 1, cz).setType(Material.AMETHYST_BLOCK);
        world.getBlockAt(cx + 3, cy + 2, cz).setType(Material.AMETHYST_BLOCK);
        world.getBlockAt(cx - 2, cy + 6, cz).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx + 2, cy + 6, cz).setType(Material.SEA_LANTERN);

        Location h = new Location(world, cx + 0.5, cy + 5.5, cz + 0.5);
        for (org.bukkit.entity.Entity e : world.getNearbyEntities(h, 3, 3, 3)) {
            if (e.getScoreboardTags().contains("aether_oneblock_portal_holo")) e.remove();
        }
        world.spawn(h, org.bukkit.entity.TextDisplay.class, td -> {
            td.setBillboard(org.bukkit.entity.Display.Billboard.CENTER);
            td.setBrightness(new org.bukkit.entity.Display.Brightness(15, 15));
            td.setBackgroundColor(org.bukkit.Color.fromARGB(180, 45, 15, 60));
            td.setText("§d§l🌌 VORTEX DU ONEBLOCK CÉLESTE\n§fVotre Île Personnelle & Évolutive\n§e✨ Entrez pour créer ou rejoindre votre île !");
            td.addScoreboardTag("aether_oneblock_portal_holo");
            td.addScoreboardTag("aether_spawn_prop");
        });
    }

    private static void buildMarketStalls(World world, int cx, int cy, int cz) {
        for (int z = -3; z <= 3; z++) {
            world.getBlockAt(cx, cy + 1, cz + z).setType(Material.BARREL);
            world.getBlockAt(cx, cy + 2, cz + z).setType((z % 2 == 0) ? Material.YELLOW_CARPET : Material.ORANGE_CARPET);
        }
        world.getBlockAt(cx - 1, cy + 1, cz).setType(Material.CHEST);
        world.getBlockAt(cx, cy + 3, cz).setType(Material.LANTERN);
    }

    private static void buildPetSanctuary(World world, int cx, int cy, int cz) {
        for (int x = -3; x <= 3; x++) {
            for (int z = -3; z <= 3; z++) {
                double d = Math.sqrt(x * x + z * z);
                if (d <= 3) {
                    world.getBlockAt(cx + x, cy + 1, cz + z).setType(Material.MOSS_BLOCK);
                }
            }
        }
        world.getBlockAt(cx, cy + 1, cz).setType(Material.WATER);
        world.getBlockAt(cx - 2, cy + 2, cz - 2).setType(Material.CHERRY_LEAVES);
        world.getBlockAt(cx + 2, cy + 2, cz - 2).setType(Material.CHERRY_LEAVES);
        world.getBlockAt(cx - 2, cy + 2, cz + 2).setType(Material.CHERRY_LEAVES);
        world.getBlockAt(cx + 2, cy + 2, cz + 2).setType(Material.CHERRY_LEAVES);
    }

    public static int getSafeGroundY(World world, int cx, int cz) {
        if (world == null) return 66;
        for (int y = 120; y >= 50; y--) {
            Material mat = world.getBlockAt(cx, y, cz).getType();
            if (mat == Material.GRASS_BLOCK || mat == Material.DIRT || mat == Material.STONE ||
                mat == Material.SAND || mat == Material.SMOOTH_QUARTZ || mat == Material.DEEPSLATE ||
                mat == Material.DEEPSLATE_TILES || mat == Material.OBSIDIAN || mat == Material.GRANITE ||
                mat == Material.ANDESITE || mat == Material.DIORITE || mat == Material.COARSE_DIRT || mat == Material.PODZOL) {
                return y;
            }
        }
        return 66;
    }

    public static Location buildSurvivalSpawn(World world, int cx, int cz) {
        if (world == null) return null;

        int cy = getSafeGroundY(world, cx, cz);

        int radius = 5;
        // 1. Esplanade de quartz poli et prismarine sur terre ferme
        for (int x = -radius; x <= radius; x++) {
            for (int z = -radius; z <= radius; z++) {
                world.getBlockAt(cx + x, cy - 1, cz + z).setType(Material.DEEPSLATE_TILES);
                world.getBlockAt(cx + x, cy, cz + z).setType(Material.SMOOTH_QUARTZ);
                for (int h = 1; h <= 7; h++) {
                    world.getBlockAt(cx + x, cy + h, cz + z).setType(Material.AIR);
                }
            }
        }

        // 2. Bordures de protection & Lanternes Célestes
        for (int x = -radius; x <= radius; x++) {
            world.getBlockAt(cx + x, cy, cz - radius).setType(Material.PRISMARINE_BRICKS);
            world.getBlockAt(cx + x, cy, cz + radius).setType(Material.PRISMARINE_BRICKS);
        }
        for (int z = -radius; z <= radius; z++) {
            world.getBlockAt(cx - radius, cy, cz + z).setType(Material.PRISMARINE_BRICKS);
            world.getBlockAt(cx + radius, cy, cz + z).setType(Material.PRISMARINE_BRICKS);
        }
        world.getBlockAt(cx - radius, cy + 1, cz - radius).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx + radius, cy + 1, cz - radius).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx - radius, cy + 1, cz + radius).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx + radius, cy + 1, cz + radius).setType(Material.SEA_LANTERN);

        // 3. Cadre de Portail Retour vers l'Agora (Obsidienne & Nether Portal de plain-pied)
        for (int x = -2; x <= 2; x++) {
            for (int y = 0; y <= 5; y++) {
                if (x == -2 || x == 2 || y == 0 || y == 5) {
                    world.getBlockAt(cx + x, cy + y, cz).setType(Material.OBSIDIAN);
                }
            }
        }
        Bukkit.dispatchCommand(Bukkit.getConsoleSender(), 
            String.format("fill %d %d %d %d %d %d minecraft:nether_portal[axis=x]", cx - 1, cy + 1, cz, cx + 1, cy + 4, cz));
        world.getBlockAt(cx - 3, cy + 1, cz).setType(Material.CRYING_OBSIDIAN);
        world.getBlockAt(cx - 3, cy + 2, cz).setType(Material.CRYING_OBSIDIAN);
        world.getBlockAt(cx + 3, cy + 1, cz).setType(Material.CRYING_OBSIDIAN);
        world.getBlockAt(cx + 3, cy + 2, cz).setType(Material.CRYING_OBSIDIAN);
        world.getBlockAt(cx - 2, cy + 6, cz).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx + 2, cy + 6, cz).setType(Material.SEA_LANTERN);

        PortalTeleportEngine.spawnPortalHolograms(world);
        return new Location(world, cx + 0.5, cy + 1.0, cz + 3.5, 180f, 0f);
    }

    public static Location regenerateSurvivalPortalSafely(World world, int originX, int originZ) {
        if (world == null) return null;
        int targetX = originX;
        int targetZ = originZ;
        int cy = getSafeGroundY(world, targetX, targetZ);
        Block block = world.getBlockAt(targetX, cy + 1, targetZ);

        if (block.getType() != Material.NETHER_PORTAL) {
            int[][] offsets = {{0, 0}, {20, 10}, {-20, -15}, {15, -25}, {-25, 20}, {35, 0}, {-35, 0}};
            for (int[] off : offsets) {
                int candX = originX + off[0];
                int candZ = originZ + off[1];
                int candY = getSafeGroundY(world, candX, candZ);
                Material under = world.getBlockAt(candX, candY, candZ).getType();
                if (under != Material.LAVA && under != Material.WATER && candY >= 55 && candY <= 120) {
                    targetX = candX;
                    targetZ = candZ;
                    break;
                }
            }
        }
        return buildSurvivalSpawn(world, targetX, targetZ);
    }
}
