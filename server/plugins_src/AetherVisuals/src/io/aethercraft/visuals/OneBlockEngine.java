package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Color;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.WorldCreator;
import org.bukkit.generator.ChunkGenerator;
import org.bukkit.block.Block;
import org.bukkit.block.Chest;
import org.bukkit.block.Sign;
import org.bukkit.block.sign.Side;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.entity.ArmorStand;
import org.bukkit.entity.Display;
import org.bukkit.entity.Entity;
import org.bukkit.entity.EntityType;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Monster;
import org.bukkit.entity.Player;
import org.bukkit.entity.TextDisplay;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerInteractAtEntityEvent;
import org.bukkit.event.server.PluginDisableEvent;
import org.bukkit.event.world.ChunkLoadEvent;
import org.bukkit.event.world.ChunkUnloadEvent;
import org.bukkit.event.world.WorldUnloadEvent;
import org.bukkit.scheduler.BukkitTask;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerRespawnEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Moteur Intelligent d'Îles Personnelles OneBlock (OneBlock Engine).
 * Gère la grille d'îles individuelles, le minage infini par phases évolutives,
 * la protection territoriale et la future coopération multi-joueurs.
 */
public class OneBlockEngine implements Listener, CommandExecutor {

    public static final int BASE_X = 10000;
    public static final int BASE_Y = 120;
    public static final int BASE_Z = 10000;
    public static final int ISLAND_SPACING = 1000;
    public static final int ISLAND_RADIUS = 350;
    public static final String TAG_LOCKED_CHUNK_MARKER = "aether_locked_chunk_marker";

    public static final int[][] SURROUNDING_CHUNK_OFFSETS = {
            {0, 1},   // Tier 2 - Sud
            {1, 0},   // Tier 3 - Est
            {-1, 0},  // Tier 4 - Ouest
            {1, -1},  // Tier 5 - NE
            {-1, -1}, // Tier 6 - NW
            {1, 1},   // Tier 7 - SE
            {-1, 1},  // Tier 8 - SW
            {0, 2},   // Tier 9 - Grand Sud
            {0, -2}   // Tier 10 - Grand Nord
    };

    public static class IslandData {
        public final UUID ownerUuid;
        public final String ownerName;
        public final int islandId;
        public final int x;
        public final int y;
        public final int z;
        public int phase;
        public int blocksBroken;
        public int level;
        public int unlockedChunks = 1;
        public int treasuresFound = 0;
        public int monstersKilled = 0;
        public boolean isGenerated = false;
        public final List<String> trustedMembers = Collections.synchronizedList(new ArrayList<>());

        public IslandData(UUID ownerUuid, String ownerName, int islandId, int x, int y, int z, int phase, int blocksBroken, int level, int unlockedChunks, int treasuresFound, int monstersKilled) {
            this.ownerUuid = ownerUuid;
            this.ownerName = ownerName;
            this.islandId = islandId;
            this.x = x;
            this.y = y;
            this.z = z;
            this.phase = phase;
            this.blocksBroken = blocksBroken;
            this.level = level;
            this.unlockedChunks = Math.max(1, unlockedChunks);
            this.treasuresFound = Math.max(0, treasuresFound);
            this.monstersKilled = Math.max(0, monstersKilled);
        }

        public Location getBlockLocation(World world) {
            return new Location(world, x, y, z);
        }

        public Location getSpawnLocation(World world) {
            return new Location(world, x + 0.5, y + 0.1, z - 9.0, 0f, 0f);
        }

        public boolean isMember(UUID uuid) {
            if (uuid == null) return false;
            if (ownerUuid != null && ownerUuid.equals(uuid)) return true;
            Player p = Bukkit.getPlayer(uuid);
            if (p != null && trustedMembers.contains(p.getName().toLowerCase(java.util.Locale.ROOT))) return true;
            return false;
        }

        public boolean isMember(String name) {
            if (name == null) return false;
            if (ownerName != null && ownerName.equalsIgnoreCase(name)) return true;
            return trustedMembers.contains(name.toLowerCase(java.util.Locale.ROOT));
        }
    }

    private final AetherVisualsPlugin plugin;
    private final Map<UUID, IslandData> islandsByPlayer = new ConcurrentHashMap<>();
    private final Map<Integer, IslandData> islandsById = new ConcurrentHashMap<>();
    private final Map<Integer, Map<String, Entity>> islandLockedMarkers = new ConcurrentHashMap<>();
    private BukkitTask proximityTask;
    private final Particle.DustOptions redDustOptions = new Particle.DustOptions(Color.RED, 1.2f);
    private final Random random = new Random();
    private int nextIslandId = 1;

    public OneBlockEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
        loadIslandsFromDatabase();
        Bukkit.getScheduler().runTask(plugin, this::getOneBlockWorld);
        startAutosaveTimer();
        startProximityVisualTask();
    }

    private void loadIslandsFromDatabase() {
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = AetherDatabase.getConnection();
                 Statement stmt = conn.createStatement()) {
                stmt.execute("CREATE TABLE IF NOT EXISTS player_oneblock (" +
                        "uuid TEXT PRIMARY KEY, " +
                        "username TEXT NOT NULL, " +
                        "island_id INTEGER NOT NULL UNIQUE, " +
                        "island_x REAL NOT NULL, " +
                        "island_y REAL NOT NULL, " +
                        "island_z REAL NOT NULL, " +
                        "phase INTEGER NOT NULL DEFAULT 1, " +
                        "blocks_broken INTEGER NOT NULL DEFAULT 0, " +
                        "level INTEGER NOT NULL DEFAULT 1, " +
                        "unlocked_chunks INTEGER NOT NULL DEFAULT 1, " +
                        "treasures_found INTEGER NOT NULL DEFAULT 0, " +
                        "monsters_killed INTEGER NOT NULL DEFAULT 0, " +
                        "trusted_members TEXT DEFAULT '[]', " +
                        "created_at TEXT NOT NULL" +
                        ")");

                // Migrations défensives pour colonnes additionnelles
                try { stmt.execute("ALTER TABLE player_oneblock ADD COLUMN unlocked_chunks INTEGER NOT NULL DEFAULT 1"); } catch (Throwable ignored) {}
                try { stmt.execute("ALTER TABLE player_oneblock ADD COLUMN treasures_found INTEGER NOT NULL DEFAULT 0"); } catch (Throwable ignored) {}
                try { stmt.execute("ALTER TABLE player_oneblock ADD COLUMN monsters_killed INTEGER NOT NULL DEFAULT 0"); } catch (Throwable ignored) {}

                try (ResultSet rs = stmt.executeQuery("SELECT uuid, username, island_id, island_x, island_y, island_z, phase, blocks_broken, level, unlocked_chunks, treasures_found, monsters_killed, trusted_members FROM player_oneblock")) {
                    int maxId = 0;
                    while (rs.next()) {
                        UUID uid = UUID.fromString(rs.getString("uuid"));
                        String name = rs.getString("username");
                        int id = rs.getInt("island_id");
                        int x = rs.getInt("island_x");
                        int y = rs.getInt("island_y");
                        int z = rs.getInt("island_z");
                        int phase = rs.getInt("phase");
                        int broken = rs.getInt("blocks_broken");
                        int lvl = rs.getInt("level");
                        int chunks = rs.getInt("unlocked_chunks");
                        int treasures = rs.getInt("treasures_found");
                        int kills = rs.getInt("monsters_killed");

                        IslandData data = new IslandData(uid, name, id, x, y, z, phase, broken, lvl, chunks, treasures, kills);
                        data.isGenerated = true;
                        islandsByPlayer.put(uid, data);
                        islandsById.put(id, data);
                        if (id > maxId) maxId = id;
                    }
                    this.nextIslandId = maxId + 1;
                    plugin.getLogger().info("✦ " + islandsByPlayer.size() + " île(s) OneBlock chargée(s) depuis SQLite !");
                }
            } catch (Throwable t) {
                plugin.getLogger().warning("Erreur chargement OneBlock: " + t.getMessage());
            }
        });
    }

    public IslandData getOrGenerateIsland(Player player) {
        UUID uid = player.getUniqueId();
        IslandData existing = islandsByPlayer.get(uid);
        if (existing != null) return existing;

        int newId = nextIslandId++;
        int ix = BASE_X + (newId * ISLAND_SPACING);
        int iy = BASE_Y;
        int iz = BASE_Z;

        IslandData island = new IslandData(uid, player.getName(), newId, ix, iy, iz, 1, 0, 1, 1, 0, 0);
        islandsByPlayer.put(uid, island);
        islandsById.put(newId, island);

        // Sauvegarde asynchrone dans SQLite
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = AetherDatabase.getConnection();
                 PreparedStatement ps = conn.prepareStatement(
                         "INSERT INTO player_oneblock (uuid, username, island_id, island_x, island_y, island_z, phase, blocks_broken, level, unlocked_chunks, treasures_found, monsters_killed, trusted_members, created_at) " +
                                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 0, '[]', datetime('now')) " +
                                 "ON CONFLICT(uuid) DO UPDATE SET username=excluded.username")) {
                ps.setString(1, uid.toString());
                ps.setString(2, player.getName());
                ps.setInt(3, newId);
                ps.setDouble(4, ix);
                ps.setDouble(5, iy);
                ps.setDouble(6, iz);
                ps.setInt(7, 1);
                ps.setInt(8, 0);
                ps.setInt(9, 1);
                ps.executeUpdate();
            } catch (Throwable t) {
                plugin.getLogger().warning("Erreur sauvegarde création OneBlock: " + t.getMessage());
            }
        });

        return island;
    }

    public void buildIslandStructure(World world, IslandData island) {
        if (world == null) return;
        int ix = island.x;
        int iy = island.y;
        int iz = island.z;

        // 0. Dégager l'espace aérien de l'archipel OneBlock UNIQUEMENT si l'île est toute nouvelle et jamais générée
        boolean islandExists = island.blocksBroken > 0 || island.isGenerated || isIslandInDatabase(island.ownerUuid);
        if (!islandExists) {
            for (int x = ix - 5; x <= ix + 5; x++) {
                for (int z = iz - 15; z <= iz + 5; z++) {
                    for (int y = iy; y <= iy + 8; y++) {
                        world.getBlockAt(x, y, z).setType(Material.AIR);
                    }
                }
            }
        }
        island.isGenerated = true;

        // ==========================================
        // 1. PLATEFORME DU PORTAIL RETOUR (AGORA)
        // ==========================================
        // Spacieuse plateforme sécurisée centrée en z = iz - 10 (de z = iz - 13 à iz - 7, x = ix - 3 à ix + 3)
        for (int dx = -3; dx <= 3; dx++) {
            for (int dz = -13; dz <= -7; dz++) {
                int z = iz + dz;
                boolean isEdge = (Math.abs(dx) == 3 || dz == -13 || (dz == -7 && Math.abs(dx) > 1));
                boolean isCorner = (Math.abs(dx) == 3 && (dz == -13 || dz == -7));

                // Sol à iy - 1
                Material floorMat = isCorner ? Material.SEA_LANTERN
                        : (isEdge ? Material.POLISHED_BLACKSTONE_BRICKS : Material.STONE_BRICKS);
                world.getBlockAt(ix + dx, iy - 1, z).setType(floorMat);

                // Sous-sol & profondeur sécurisée
                world.getBlockAt(ix + dx, iy - 2, z).setType(Material.COBBLESTONE);
                if (Math.abs(dx) <= 2 && dz >= -12 && dz <= -8) {
                    world.getBlockAt(ix + dx, iy - 3, z).setType(Material.DEEPSLATE);
                }

                // Murets de sécurité périphérique anti-chute dans le vide
                if (isEdge && dz != -12) {
                    world.getBlockAt(ix + dx, iy, z).setType(Material.STONE_BRICK_WALL);
                    if (isCorner) {
                        world.getBlockAt(ix + dx, iy + 1, z).setType(Material.LANTERN);
                    }
                }
            }
        }

        // Construction du Grand Portail Retour à l'Agora (à z = iz - 12)
        buildReturnPortal(world, ix, iy, iz - 12);

        // ==========================================
        // 2. PASSERELLE DE LIAISON (PONT CÉLESTE)
        // ==========================================
        // Reliant la plateforme du portail (z = iz - 7) à la plateforme OneBlock (z = iz - 3)
        for (int dz = -6; dz <= -4; dz++) {
            int z = iz + dz;
            // Sol
            world.getBlockAt(ix, iy - 1, z).setType(Material.POLISHED_ANDESITE);
            world.getBlockAt(ix - 1, iy - 1, z).setType(Material.STONE_BRICKS);
            world.getBlockAt(ix + 1, iy - 1, z).setType(Material.STONE_BRICKS);

            // Sous-sol
            world.getBlockAt(ix, iy - 2, z).setType(Material.COBBLESTONE);
            world.getBlockAt(ix - 1, iy - 2, z).setType(Material.COBBLESTONE);
            world.getBlockAt(ix + 1, iy - 2, z).setType(Material.COBBLESTONE);

            // Garde-corps de sécurité latéraux
            world.getBlockAt(ix - 1, iy, z).setType(Material.STONE_BRICK_WALL);
            world.getBlockAt(ix + 1, iy, z).setType(Material.STONE_BRICK_WALL);

            if (dz == -5) {
                world.getBlockAt(ix - 1, iy + 1, z).setType(Material.LANTERN);
                world.getBlockAt(ix + 1, iy + 1, z).setType(Material.LANTERN);
            }
        }

        // ==========================================
        // 3. PLATEFORME ONEBLOCK CENTRALE (ARÈNE DE MINAGE)
        // ==========================================
        // Centrée en (ix, iz), rayon 3 (7x7 arrondi)
        for (int dx = -3; dx <= 3; dx++) {
            for (int dz = -3; dz <= 3; dz++) {
                int z = iz + dz;
                int distSq = dx * dx + dz * dz;
                if (distSq <= 10) {
                    // Sol à iy - 1
                    Material surf;
                    if (dx == 0 && dz == 0) {
                        surf = Material.BEDROCK; // Ancre éternelle incassable sous le OneBlock
                    } else if (Math.abs(dx) <= 1 && Math.abs(dz) <= 1) {
                        if (Math.abs(dx) == 1 && Math.abs(dz) == 1) {
                            surf = Material.SEA_LANTERN; // 4 coins illuminés pour le piédestal central
                        } else {
                            surf = Material.POLISHED_BLACKSTONE_BRICKS; // Socle noble autour
                        }
                    } else {
                        surf = Material.GRASS_BLOCK; // Sol d'herbe céleste pour marcher sans danger
                    }
                    world.getBlockAt(ix + dx, iy - 1, z).setType(surf);

                    // Sous-sol céleste (cône inversé)
                    world.getBlockAt(ix + dx, iy - 2, z).setType(Material.DIRT);
                    if (distSq <= 6) world.getBlockAt(ix + dx, iy - 3, z).setType(Material.COBBLESTONE);
                    if (distSq <= 3) world.getBlockAt(ix + dx, iy - 4, z).setType(Material.DEEPSLATE);
                    if (dx == 0 && dz == 0) world.getBlockAt(ix, iy - 5, z).setType(Material.BEDROCK);

                    // Murets de sécurité périphérique
                    if (distSq >= 8 && (dz > -3 || Math.abs(dx) > 1)) {
                        world.getBlockAt(ix + dx, iy, z).setType(Material.STONE_BRICK_WALL);
                    }
                }
            }
        }

        // ==========================================
        // 4. LE BLOC CENTRAL ONEBLOCK & MISE EN AVANT
        // ==========================================
        Material currentBlock = (island.blocksBroken > 0) ? getNextBlockForSubPhase(computeSubPhase(island.blocksBroken)) : Material.GRASS_BLOCK;
        world.getBlockAt(ix, iy, iz).setType(currentBlock);

        // Décoration du piédestal : 4 dalles élégantes sur les lanternes autour du bloc
        world.getBlockAt(ix + 1, iy, iz + 1).setType(Material.POLISHED_BLACKSTONE_SLAB);
        world.getBlockAt(ix - 1, iy, iz + 1).setType(Material.POLISHED_BLACKSTONE_SLAB);
        world.getBlockAt(ix + 1, iy, iz - 1).setType(Material.POLISHED_BLACKSTONE_SLAB);
        world.getBlockAt(ix - 1, iy, iz - 1).setType(Material.POLISHED_BLACKSTONE_SLAB);

        // Coffre bonus de bienvenue
        Block chestBlock = world.getBlockAt(ix + 2, iy, iz);
        if (chestBlock.getType() != Material.CHEST) {
            chestBlock.setType(Material.CHEST);
            if (chestBlock.getState() instanceof Chest chest) {
                Inventory inv = chest.getInventory();
                inv.addItem(new ItemStack(Material.OAK_SAPLING, 4));
                inv.addItem(new ItemStack(Material.WATER_BUCKET, 1));
                inv.addItem(new ItemStack(Material.LAVA_BUCKET, 1));
                inv.addItem(new ItemStack(Material.BREAD, 32));
                inv.addItem(new ItemStack(Material.BONE_MEAL, 8));
                inv.addItem(new ItemStack(Material.TORCH, 8));

                ItemStack book = new ItemStack(Material.BOOK);
                ItemMeta m = book.getItemMeta();
                if (m != null) {
                    m.setDisplayName(ChatColor.GOLD + "✦ Guide de l'Aventurier OneBlock");
                    book.setItemMeta(m);
                }
                inv.addItem(book);
            }
        }

        // Panneau informatif d'accueil
        Block signBlock = world.getBlockAt(ix - 2, iy, iz);
        signBlock.setType(Material.OAK_SIGN);
        if (signBlock.getState() instanceof Sign sign) {
            sign.getSide(Side.FRONT).setLine(0, ChatColor.GOLD + "★ ONEBLOCK ★");
            sign.getSide(Side.FRONT).setLine(1, ChatColor.AQUA + island.ownerName);
            sign.getSide(Side.FRONT).setLine(2, ChatColor.GREEN + "Phase " + island.phase);
            sign.getSide(Side.FRONT).setLine(3, ChatColor.YELLOW + "/ob info");
            sign.update();
        }

        // Création / Mise à jour des Hologrammes TextDisplay
        updateIslandHolograms(world, island);

        // Particules de bénédiction
        world.spawnParticle(Particle.HAPPY_VILLAGER, new Location(world, ix + 0.5, iy + 1.2, iz + 0.5), 25, 0.4, 0.4, 0.4, 0.1);
    }

    private void buildReturnPortal(World world, int cx, int cy, int cz) {
        // Cadre en obsidienne, obsidienne pleureuse et améthyste (5x6, centré en cx)
        for (int x = -2; x <= 2; x++) {
            for (int y = -1; y <= 4; y++) {
                if (x == -2 || x == 2 || y == -1 || y == 4) {
                    Material mat;
                    if (y == -1) mat = Material.CRYING_OBSIDIAN;
                    else if (y == 4 && x == 0) mat = Material.RESPAWN_ANCHOR;
                    else if ((x == -2 || x == 2) && (y == 1 || y == 2)) mat = Material.AMETHYST_BLOCK;
                    else mat = Material.OBSIDIAN;

                    world.getBlockAt(cx + x, cy + y, cz).setType(mat);
                } else {
                    world.getBlockAt(cx + x, cy + y, cz).setType(Material.AIR);
                }
            }
        }

        // Remplir l'intérieur avec nether_portal via l'API directe Paper (instantané et infaillible)
        for (int px = cx - 1; px <= cx + 1; px++) {
            for (int py = cy; py <= cy + 3; py++) {
                try {
                    org.bukkit.block.data.Orientable portalData = (org.bukkit.block.data.Orientable) Bukkit.createBlockData(Material.NETHER_PORTAL);
                    portalData.setAxis(org.bukkit.Axis.X);
                    world.getBlockAt(px, py, cz).setBlockData(portalData, false);
                } catch (Throwable t) {
                    world.getBlockAt(px, py, cz).setType(Material.NETHER_PORTAL, false);
                }
            }
        }

        // Lanternes décoratives au sommet des piliers
        world.getBlockAt(cx - 2, cy + 5, cz).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx + 2, cy + 5, cz).setType(Material.SEA_LANTERN);
    }

    public void updateIslandHolograms(World world, IslandData island) {
        if (world == null) return;
        // 1. Hologramme du Portail Retour
        Location hPortal = new Location(world, island.x + 0.5, island.y + 4.8, island.z - 12 + 0.5);
        for (Entity e : world.getNearbyEntities(hPortal, 3, 3, 3)) {
            if (e.getScoreboardTags().contains("aether_oneblock_portal_holo")) e.remove();
        }
        world.spawn(hPortal, TextDisplay.class, td -> {
            td.setBillboard(Display.Billboard.CENTER);
            td.setBrightness(new Display.Brightness(15, 15));
            td.setBackgroundColor(Color.fromARGB(180, 20, 35, 60));
            td.setText("§b§l🪐 PORTAIL RETOUR AGORA\n§fArchipel Céleste & Spawn (Y=120)\n§e✨ Entrez dans le portail pour regagner le Hub");
            td.addScoreboardTag("aether_oneblock_portal_holo");
        });

        // 2. Hologramme au-dessus du Bloc Central
        updateBlockHologram(world, island);

        // 3. Hologrammes / Marqueurs 3D des Chunks Verrouillés
        updateLockedChunkMarkers(world, island);
    }

    public void updateBlockHologram(World world, IslandData island) {
        if (world == null) return;
        Location hBlock = new Location(world, island.x + 0.5, island.y + 1.85, island.z + 0.5);
        String subPhaseDisplay = getSubPhaseDisplay(island.blocksBroken);
        int nextGoal = getNextGoalBlocks(island.blocksBroken);
        int nextChunk = getNextPalierBlocks(island.blocksBroken);
        int remaining = Math.max(1, nextGoal - island.blocksBroken);
        String goalText = (nextGoal == nextChunk)
                ? String.format("§e✦ Prochain Chunk dans §b%d §eblocs ! ✦", remaining)
                : String.format("§6✦ Demi-palier dans §b%d §6blocs ! ✦", remaining);

        String text = String.format("§6§l⛏ BLOC CENTRAL ONEBLOCK ⛏\n§e%s\n§f✦ §b%d/1000 blocs §f• §a%d Chunks §f✦\n%s",
                subPhaseDisplay, island.blocksBroken, island.unlockedChunks, goalText);

        boolean updated = false;
        for (Entity e : world.getNearbyEntities(hBlock, 2.5, 2.5, 2.5)) {
            if (e instanceof TextDisplay td && e.getScoreboardTags().contains("aether_oneblock_block_holo")) {
                td.setText(text);
                updated = true;
                break;
            }
        }
        if (!updated) {
            world.spawn(hBlock, TextDisplay.class, td -> {
                td.setBillboard(Display.Billboard.CENTER);
                td.setBrightness(new Display.Brightness(15, 15));
                td.setBackgroundColor(Color.fromARGB(180, 45, 15, 60));
                td.setText(text);
                td.addScoreboardTag("aether_oneblock_block_holo");
            });
        }
    }

    public World getOneBlockWorld() {
        World w = Bukkit.getWorld("world_oneblock");
        if (w == null) {
            WorldCreator wc = new WorldCreator("world_oneblock");
            wc.environment(World.Environment.NORMAL);
            wc.generator(new ChunkGenerator() {
                @Override public boolean shouldGenerateNoise() { return false; }
                @Override public boolean shouldGenerateSurface() { return false; }
                @Override public boolean shouldGenerateBedrock() { return false; }
                @Override public boolean shouldGenerateCaves() { return false; }
                @Override public boolean shouldGenerateDecorations() { return false; }
                @Override public boolean shouldGenerateMobs() { return false; }
                @Override public boolean shouldGenerateStructures() { return false; }
            });
            w = Bukkit.createWorld(wc);
        }
        if (w != null) {
            w.setAutoSave(true);
        }
        return (w != null) ? w : Bukkit.getWorld("world");
    }

    public void teleportToIsland(Player player) {
        final World w = getOneBlockWorld();
        if (w == null) {
            player.sendMessage(ChatColor.RED + "✦ Erreur : Monde OneBlock indisponible.");
            return;
        }
        IslandData island = getOrGenerateIsland(player);
        Location spawnLoc = island.getSpawnLocation(w);

        int chunkX = island.x >> 4;
        int chunkZ = island.z >> 4;
        int portalChunkZ = (island.z - 9) >> 4;

        // Pré-charger le chunk de spawn et le chunk du portail (chunk 624 et chunk 625)
        java.util.concurrent.CompletableFuture.allOf(
                w.getChunkAtAsync(chunkX, chunkZ, true),
                w.getChunkAtAsync(chunkX, portalChunkZ, true)
        ).whenComplete((v, err) -> {
            Bukkit.getScheduler().runTask(plugin, () -> {
                if (!player.isOnline()) return;
                Block portalFloor = w.getBlockAt(island.x, island.y - 1, island.z - 9);
                Block central = w.getBlockAt(island.x, island.y, island.z);
                if (portalFloor.getType() == Material.AIR || central.getType() == Material.AIR) {
                    buildIslandStructure(w, island);
                } else {
                    updateIslandHolograms(w, island);
                }
                player.teleportAsync(spawnLoc).thenAccept(success -> {
                    player.playSound(spawnLoc, Sound.BLOCK_AMETHYST_BLOCK_CHIME, 1.0f, 1.2f);
                    player.sendTitle(ChatColor.LIGHT_PURPLE + "🌌 VOTRE ONEBLOCK",
                            ChatColor.GOLD + "Niveau " + island.level + " • " + getSubPhaseDisplay(island.blocksBroken), 5, 40, 10);
                    player.sendMessage(ChatColor.AQUA + "✦ Bienvenue sur votre île OneBlock isolée dans le vide ! Cassez le bloc central pour progresser.");
                    player.sendMessage(ChatColor.GRAY + "Pour retourner au Spawn : empruntez le portail derrière vous ou tapez /spawn");
                });
            });
        });
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onBlockBreak(BlockBreakEvent event) {
        Block b = event.getBlock();
        Player p = event.getPlayer();
        World w = b.getWorld();

        IslandData island = getIslandAt(b.getLocation());
        if (island == null) return;

        // Est-ce le bloc OneBlock central ?
        if (b.getX() == island.x && b.getY() == island.y && b.getZ() == island.z) {
            // Vérification stricte de propriété / co-op
            boolean isOwnerOrMember = (island.ownerUuid != null && island.ownerUuid.equals(p.getUniqueId()))
                    || island.isMember(p.getUniqueId())
                    || (p.getName() != null && island.trustedMembers.contains(p.getName().toLowerCase(java.util.Locale.ROOT)))
                    || p.isOp()
                    || p.hasPermission("aether.admin");

            if (!isOwnerOrMember) {
                event.setCancelled(true);
                p.sendMessage(ChatColor.RED + "🛡️ Seul le propriétaire (" + island.ownerName + ") ou ses membres peuvent miner ce générateur OneBlock !");
                p.playSound(p.getLocation(), Sound.BLOCK_CHEST_LOCKED, 0.8f, 1.2f);
                return;
            }

            event.setCancelled(true); // Empêche la destruction vanilla et la chute dans le vide

            // 1. Récupérer les drops du bloc cassé et les donner au joueur
            Material currentMat = b.getType();
            ItemStack drop = getDropForMaterial(currentMat);
            if (drop != null) {
                Map<Integer, ItemStack> overflow = p.getInventory().addItem(drop);
                if (!overflow.isEmpty()) {
                    for (ItemStack item : overflow.values()) {
                        w.dropItemNaturally(p.getLocation(), item);
                    }
                }
            }

            // 2. Progression & Statistiques
            int oldBroken = island.blocksBroken;
            island.blocksBroken++;
            island.phase = computePhase(island.blocksBroken);
            island.level = (island.blocksBroken / 50) + 1;

            int oldSubPhase = computeSubPhase(oldBroken);
            int newSubPhase = computeSubPhase(island.blocksBroken);

            // Détection de déblocage de chunk (tous les 100 blocs jusqu'à 1k, puis tous les 250)
            int newChunks = computeUnlockedChunks(island.blocksBroken);
            boolean newChunkUnlocked = (newChunks > island.unlockedChunks);
            if (newChunkUnlocked) {
                island.unlockedChunks = newChunks;
                generateUnlockedChunkIsland(w, island, island.unlockedChunks);
                updateLockedChunkMarkers(w, island);
                p.playSound(p.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.0f);
                p.playSound(p.getLocation(), Sound.ENTITY_PLAYER_LEVELUP, 1.0f, 1.2f);
                p.sendTitle(ChatColor.GOLD + "✦ CHUNK DÉBLOQUÉ ! ✦",
                        ChatColor.AQUA + "Chunk #" + island.unlockedChunks + " accessible • " + getSubPhaseDisplay(island.blocksBroken), 10, 60, 20);
                p.sendMessage(ChatColor.GOLD + "★ [PALIER CHUNK] Félicitations ! Votre territoire s'agrandit : " + ChatColor.GREEN + "Chunk #" + island.unlockedChunks + " débloqué !");
                spawnPalierBoss(w, island, island.unlockedChunks - 1, p);
            } else if (newSubPhase > oldSubPhase) {
                // Détection de demi-palier (tous les 50 blocs entre deux chunks)
                triggerDemiPalierReward(p, island, w, newSubPhase);
            }

            // 3. Choix du bloc suivant
            Material nextMat = getNextBlockForSubPhase(newSubPhase);
            b.setType(nextMat);

            // 4. Feedback sonore, particules & mise à jour de l'hologramme
            p.playSound(b.getLocation(), Sound.BLOCK_NOTE_BLOCK_PLING, 0.8f, 1.5f);
            w.spawnParticle(Particle.HAPPY_VILLAGER, b.getLocation().clone().add(0.5, 0.6, 0.5), 12, 0.25, 0.25, 0.25, 0.05);
            updateBlockHologram(w, island);

            // 5. Événements spéciaux : Trésors, Pièges, Monstres ou Faune
            if (!newChunkUnlocked && newSubPhase == oldSubPhase) {
                int roll = random.nextInt(100);
                if (roll < 4) {
                    triggerLuckyGift(p, island, w, b.getLocation());
                } else if (roll < 7) {
                    triggerSneakyTrap(p, island, w, b.getLocation());
                } else if (roll < 10) {
                    spawnRandomMonster(w, island, p);
                } else if (roll < 13) {
                    spawnFriendlyCreature(w, island);
                }
            }

            // Sauvegarde asynchrone périodique (tous les 10 blocs)
            if (island.blocksBroken % 10 == 0) {
                saveIslandProgressAsync(island);
            }
            return;
        }

        // Protection du portail retour vers l'Agora
        if (b.getZ() <= island.z - 10 && Math.abs(b.getX() - island.x) <= 3) {
            event.setCancelled(true);
            p.sendMessage(ChatColor.YELLOW + "🛡️ Le Portail de retour vers l'Agora est protégé !");
            return;
        }

        // Protection de l'ancre bedrock sous le OneBlock
        if (b.getX() == island.x && b.getY() < island.y && b.getZ() == island.z) {
            event.setCancelled(true);
            return;
        }

        // Protection de l'île contre les intrus et vérification du territoire débloqué
        if (!isAllowedToBuild(p, island, b.getLocation())) {
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onBlockPlace(BlockPlaceEvent event) {
        Block b = event.getBlock();
        Player p = event.getPlayer();
        IslandData island = getIslandAt(b.getLocation());
        if (island != null && !isAllowedToBuild(p, island, b.getLocation())) {
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onPlayerInteract(org.bukkit.event.player.PlayerInteractEvent event) {
        Block b = event.getClickedBlock();
        if (b == null) return;
        Player p = event.getPlayer();
        IslandData island = getIslandAt(b.getLocation());
        if (island != null && !isAllowedToBuild(p, island, b.getLocation())) {
            event.setCancelled(true);
            p.sendMessage(ChatColor.RED + "🚫 Vous n'avez pas la permission d'interagir sur l'île de " + island.ownerName + " !");
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onEntityDamage(org.bukkit.event.entity.EntityDamageByEntityEvent event) {
        if (!(event.getDamager() instanceof Player p)) return;
        if (event.getEntity() instanceof org.bukkit.entity.Animals || event.getEntity() instanceof org.bukkit.entity.Villager) {
            IslandData island = getIslandAt(event.getEntity().getLocation());
            if (island != null && !isAllowedToBuild(p, island, event.getEntity().getLocation())) {
                event.setCancelled(true);
                p.sendMessage(ChatColor.RED + "🚫 Vous ne pouvez pas attaquer les animaux sur l'île de " + island.ownerName + " !");
            }
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onEntityDeath(EntityDeathEvent event) {
        LivingEntity entity = event.getEntity();
        if (entity instanceof Monster) {
            IslandData island = getIslandAt(entity.getLocation());
            if (island != null) {
                island.monstersKilled++;
                if (entity.getScoreboardTags().contains("aether_oneblock_boss")) {
                    Player killer = entity.getKiller();
                    String killerName = (killer != null) ? killer.getName() : island.ownerName;
                    Bukkit.broadcastMessage(ChatColor.GOLD + "★ [ONEBLOCK] " + ChatColor.AQUA + killerName + ChatColor.YELLOW + " a terrassé le " + ChatColor.RED + entity.getCustomName() + ChatColor.YELLOW + " !");
                    entity.getWorld().spawnParticle(Particle.TOTEM_OF_UNDYING, entity.getLocation(), 40, 0.5, 1.0, 0.5, 0.1);
                    entity.getWorld().playSound(entity.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.2f);
                }
            }
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onPlayerRespawn(PlayerRespawnEvent event) {
        Player player = event.getPlayer();
        Location deathLoc = player.getLocation();
        IslandData island = islandsByPlayer.get(player.getUniqueId());
        if (island != null) {
            World obWorld = getOneBlockWorld();
            if (player.getWorld().equals(obWorld) || (deathLoc.getWorld() != null && deathLoc.getWorld().equals(obWorld)) || isOneBlockZone(deathLoc)) {
                event.setRespawnLocation(island.getSpawnLocation(obWorld));
                player.sendMessage(ChatColor.AQUA + "✦ Réapparition sur votre île OneBlock ! Attention au vide !");
            }
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onPlayerVoidDeath(org.bukkit.event.entity.PlayerDeathEvent event) {
        Player player = event.getEntity();
        if (player.getWorld().getName().equals("world_oneblock") || isOneBlockZone(player.getLocation())) {
            if (player.getLastDamageCause() != null && player.getLastDamageCause().getCause() == EntityDamageEvent.DamageCause.VOID) {
                event.setDeathMessage(ChatColor.RED + "☠ " + ChatColor.AQUA + player.getName() + ChatColor.GRAY + " a sombré dans l'abîme du vide de son OneBlock !");
            }
        }
    }

    public boolean isAllowedToBuild(Player player, IslandData island) {
        return isAllowedToBuild(player, island, null);
    }

    public boolean isAllowedToBuild(Player player, IslandData island, Location loc) {
        if (player.isOp() || player.hasPermission("aether.admin")) return true;
        if (!island.ownerUuid.equals(player.getUniqueId()) && !island.trustedMembers.contains(player.getName().toLowerCase())) {
            player.sendMessage(ChatColor.RED + "🛡️ Cette île OneBlock appartient à " + island.ownerName + " !");
            return false;
        }
        if (loc != null && !isLocationInUnlockedChunk(island, loc)) {
            int nextPalier = getNextPalierBlocks(island.blocksBroken);
            player.sendMessage(ChatColor.RED + "🔒 Ce chunk est encore verrouillé ! Prochain déblocage à " + nextPalier + " blocs minés (/ob stats).");
            player.playSound(player.getLocation(), Sound.BLOCK_CHEST_LOCKED, 0.8f, 1.2f);
            return false;
        }
        return true;
    }

    public boolean isLocationInUnlockedChunk(IslandData island, Location loc) {
        int relX = (loc.getBlockX() >> 4) - (island.x >> 4);
        int relZ = (loc.getBlockZ() >> 4) - (island.z >> 4);

        // Les deux chunks initiaux (central et portail) sont toujours débloqués
        if (relX == 0 && (relZ == 0 || relZ == -1)) return true;

        int unlocked = island.unlockedChunks;
        if (unlocked >= 2 && relX == 0 && relZ == 1) return true;   // Sud
        if (unlocked >= 3 && relX == 1 && relZ == 0) return true;   // Est
        if (unlocked >= 4 && relX == -1 && relZ == 0) return true;  // Ouest
        if (unlocked >= 5 && relX == 1 && relZ == -1) return true;  // NE
        if (unlocked >= 6 && relX == -1 && relZ == -1) return true; // NW
        if (unlocked >= 7 && relX == 1 && relZ == 1) return true;   // SE
        if (unlocked >= 8 && relX == -1 && relZ == 1) return true;  // SW
        if (unlocked >= 9 && relX == 0 && relZ == 2) return true;   // Grand Sud
        if (unlocked >= 10 && relX == 0 && relZ == -2) return true; // Grand Nord
        if (unlocked >= 11 && Math.abs(relX) <= 1 && Math.abs(relZ) <= 1) return true; // 3x3 complet
        if (unlocked >= 12 && Math.abs(relX) <= 2 && Math.abs(relZ) <= 2) return true; // 5x5 complet
        return unlocked >= 15;
    }

    public static int getRequiredTierForChunk(int relX, int relZ) {
        int tier = 15;
        if (relX == 0 && (relZ == 0 || relZ == -1)) tier = 1;
        else if (relX == 0 && relZ == 1) tier = 2;   // Sud
        else if (relX == 1 && relZ == 0) tier = 3;   // Est
        else if (relX == -1 && relZ == 0) tier = 4;  // Ouest
        else if (relX == 1 && relZ == -1) tier = 5;  // NE
        else if (relX == -1 && relZ == -1) tier = 6; // NW
        else if (relX == 1 && relZ == 1) tier = 7;   // SE
        else if (relX == -1 && relZ == 1) tier = 8;  // SW
        else if (relX == 0 && relZ == 2) tier = 9;   // Grand Sud
        else if (relX == 0 && relZ == -2) tier = 10; // Grand Nord
        else if (Math.abs(relX) <= 1 && Math.abs(relZ) <= 1) tier = 11; // 3x3 complet
        else if (Math.abs(relX) <= 2 && Math.abs(relZ) <= 2) tier = 12; // 5x5 complet
        return tier;
    }

    public boolean isChunkUnlocked(IslandData island, int relX, int relZ) {
        if (island == null) return false;
        return island.unlockedChunks >= getRequiredTierForChunk(relX, relZ);
    }

    public static final int[] EXPONENTIAL_THRESHOLDS = {
        0, 10, 21, 34, 50, 68, 89, 113, 140, 171, 206, 246, 292, 345, 405, 474, 553, 643, 747, 865, 1000
    };

    public static final int[] CHUNK_THRESHOLDS = {
        0, 21, 50, 89, 140, 206, 292, 405, 553, 747, 1000
    };

    public static int computeUnlockedChunks(int broken) {
        if (broken <= 0) return 1;
        if (broken < 1000) {
            int c = 1;
            for (int i = 1; i < CHUNK_THRESHOLDS.length; i++) {
                if (broken >= CHUNK_THRESHOLDS[i]) {
                    c = i + 1;
                }
            }
            return c;
        }
        return 11 + ((broken - 1000) / 250);
    }

    public static int getNextPalierBlocks(int broken) {
        if (broken < 1000) {
            for (int i = 1; i < CHUNK_THRESHOLDS.length; i++) {
                if (CHUNK_THRESHOLDS[i] > broken) {
                    return CHUNK_THRESHOLDS[i];
                }
            }
            return 1000;
        }
        return 1000 + (((broken - 1000) / 250) + 1) * 250;
    }

    public static int getNextGoalBlocks(int broken) {
        if (broken < 1000) {
            for (int i = 1; i < EXPONENTIAL_THRESHOLDS.length; i++) {
                if (EXPONENTIAL_THRESHOLDS[i] > broken) {
                    return EXPONENTIAL_THRESHOLDS[i];
                }
            }
            return 1000;
        }
        return 1000 + (((broken - 1000) / 250) + 1) * 250;
    }

    public static int computeSubPhase(int broken) {
        if (broken >= 1000) return 21;
        for (int i = 1; i < EXPONENTIAL_THRESHOLDS.length; i++) {
            if (broken < EXPONENTIAL_THRESHOLDS[i]) {
                return i;
            }
        }
        return 21;
    }

    public void generateUnlockedChunkIsland(World world, IslandData island, int chunkNumber) {
        int[][] offsets = {
                {0, 0},   // 1. Central
                {0, 1},   // 2. Sud
                {1, 0},   // 3. Est
                {-1, 0},  // 4. Ouest
                {1, -1},  // 5. NE
                {-1, -1}, // 6. NW
                {1, 1},   // 7. SE
                {-1, 1},  // 8. SW
                {0, 2},   // 9. Grand Sud
                {0, -2}   // 10/11. Grand Nord (Palier 1K)
        };
        int idx = Math.min(chunkNumber - 1, offsets.length - 1);
        int relX = offsets[idx][0];
        int relZ = offsets[idx][1];

        int cx = ((island.x >> 4) + relX) * 16 + 8;
        int cz = ((island.z >> 4) + relZ) * 16 + 8;
        int cy = island.y - 1;

        // Préchargement asynchrone du chunk débloqué
        world.getChunkAtAsync(cx >> 4, cz >> 4).thenAccept(chunk -> {
            Bukkit.getScheduler().runTask(plugin, () -> {
                // Générer un mini-îlot thématique flottant (rayon 2 à 3 blocs)
                for (int dx = -2; dx <= 2; dx++) {
                    for (int dz = -2; dz <= 2; dz++) {
                        if (dx * dx + dz * dz <= 5) {
                            Material surf = (chunkNumber >= 10) ? Material.GOLD_BLOCK : (chunkNumber % 2 == 0 ? Material.STONE_BRICKS : Material.MOSSY_STONE_BRICKS);
                            world.getBlockAt(cx + dx, cy, cz + dz).setType(surf);
                            world.getBlockAt(cx + dx, cy - 1, cz + dz).setType(Material.COBBLESTONE);
                            if (dx == 0 && dz == 0) world.getBlockAt(cx, cy - 2, cz).setType(Material.DEEPSLATE);
                        }
                    }
                }
                // Décoration centrale de l'îlot débloqué
                if (chunkNumber >= 10) {
                    world.getBlockAt(cx, cy + 1, cz).setType(Material.BEACON);
                    world.getBlockAt(cx, cy, cz).setType(Material.NETHERITE_BLOCK);
                    world.getBlockAt(cx - 1, cy + 1, cz).setType(Material.SEA_LANTERN);
                    world.getBlockAt(cx + 1, cy + 1, cz).setType(Material.SEA_LANTERN);
                } else if (chunkNumber == 2) {
                    world.getBlockAt(cx, cy + 1, cz).setType(Material.CHEST);
                    world.getBlockAt(cx + 1, cy + 1, cz).setType(Material.LANTERN);
                } else if (chunkNumber == 3) {
                    world.getBlockAt(cx, cy + 1, cz).setType(Material.AMETHYST_CLUSTER);
                } else if (chunkNumber == 4) {
                    world.getBlockAt(cx, cy + 1, cz).setType(Material.BLUE_ICE);
                } else if (chunkNumber == 5) {
                    world.getBlockAt(cx, cy + 1, cz).setType(Material.FLOWERING_AZALEA);
                } else if (chunkNumber == 6) {
                    world.getBlockAt(cx, cy + 1, cz).setType(Material.SCULK_CATALYST);
                } else if (chunkNumber == 7) {
                    world.getBlockAt(cx, cy + 1, cz).setType(Material.MAGMA_BLOCK);
                } else if (chunkNumber == 8) {
                    world.getBlockAt(cx, cy + 1, cz).setType(Material.GILDED_BLACKSTONE);
                } else {
                    world.getBlockAt(cx, cy + 1, cz).setType(Material.PURPUR_PILLAR);
                }
                world.spawnParticle(Particle.TOTEM_OF_UNDYING, new Location(world, cx + 0.5, cy + 2.0, cz + 0.5), 40, 0.5, 0.5, 0.5, 0.1);
            });
        });
    }

    public void spawnPalierBoss(World world, IslandData island, int palier, Player player) {
        Location spawnLoc = new Location(world, island.x + 0.5, island.y + 1.0, island.z + 0.5);
        world.playSound(spawnLoc, Sound.ENTITY_WITHER_SPAWN, 0.7f, 1.0f);
        world.spawnParticle(Particle.FLAME, spawnLoc, 30, 0.4, 0.6, 0.4, 0.05);

        EntityType type;
        String bossName;

        switch (palier) {
            case 1 -> { type = EntityType.ZOMBIE; bossName = "§e§l✦ Gardien des Cavernes (Chunk #2) ✦"; }
            case 2 -> { type = EntityType.HUSK; bossName = "§6§l✦ Momie des Dunes (Chunk #3) ✦"; }
            case 3 -> { type = EntityType.STRAY; bossName = "§b§l✦ Vagabond des Glaces (Chunk #4) ✦"; }
            case 4 -> { type = EntityType.SPIDER; bossName = "§c§l✦ Terreur Sylvestre (Chunk #5) ✦"; }
            case 5 -> { type = EntityType.WITHER_SKELETON; bossName = "§8§l✦ Spectre des Abîmes (Chunk #6) ✦"; }
            case 6 -> { type = EntityType.BLAZE; bossName = "§4§l✦ Seigneur des Flammes (Chunk #7) ✦"; }
            case 7 -> { type = EntityType.PIGLIN_BRUTE; bossName = "§c§l✦ Tyran du Bastion (Chunk #8) ✦"; }
            case 8 -> { type = EntityType.ENDERMAN; bossName = "§d§l✦ Héraut du Vide (Chunk #9) ✦"; }
            case 9 -> { type = EntityType.EVOKER; bossName = "§5§l✦ Évocateur Céleste (Chunk #10) ✦"; }
            default -> { type = EntityType.WITHER_SKELETON; bossName = "§4§l★ L'AVATAR D'AETHER (1K) ★"; }
        }

        Entity e = world.spawnEntity(spawnLoc, type);
        if (e instanceof LivingEntity le) {
            le.setCustomName(bossName);
            le.setCustomNameVisible(true);
            le.addScoreboardTag("aether_oneblock_boss");
            le.addPotionEffect(new PotionEffect(PotionEffectType.RESISTANCE, 20 * 60, (palier >= 10 ? 2 : 1)));
            le.addPotionEffect(new PotionEffect(PotionEffectType.FIRE_RESISTANCE, 20 * 120, 0));
            if (plugin.getMobAffixEngine() != null) {
                plugin.getMobAffixEngine().applyBossAffixes(le, palier);
            }
        }
        player.sendTitle(ChatColor.RED + "⚔ MINI-BOSS DU PALIER !", ChatColor.GOLD + bossName, 10, 50, 15);
    }

    public void triggerDemiPalierReward(Player p, IslandData island, World w, int subPhase) {
        island.treasuresFound++;
        p.playSound(p.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.2f);
        p.playSound(p.getLocation(), Sound.BLOCK_BEACON_POWER_SELECT, 1.0f, 1.4f);
        String subName = getSubPhaseName(subPhase);
        int major = (subPhase + 1) / 2;
        p.sendTitle(ChatColor.GOLD + "✦ DEMI-PALIER ATTEINT ! ✦",
                ChatColor.YELLOW + "Phase " + major + ".5 : " + subName, 10, 60, 20);
        p.sendMessage(ChatColor.GOLD + "★ [DEMI-PALIER] Vous entrez dans la sous-zone : " + ChatColor.AQUA + subName + ChatColor.GOLD + " ! De nouveaux blocs et minerais sont disponibles.");

        ItemStack[] bonusItems;
        switch (subPhase) {
            case 2 -> { // Verger (50)
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.BIRCH_SAPLING, 2),
                        new ItemStack(Material.HONEY_BOTTLE, 2),
                        new ItemStack(Material.MOSS_BLOCK, 4),
                        new ItemStack(Material.GOLDEN_APPLE, 1)
                };
            }
            case 4 -> { // Géode & Filon (150)
                ItemStack pickaxe = new ItemStack(Material.IRON_PICKAXE);
                ItemMeta meta = pickaxe.getItemMeta();
                if (meta != null) {
                    meta.setDisplayName(ChatColor.AQUA + "✦ Pioche du Mineur de Géode");
                    meta.addEnchant(Enchantment.EFFICIENCY, 2, true);
                    pickaxe.setItemMeta(meta);
                }
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.AMETHYST_SHARD, 4),
                        new ItemStack(Material.RAW_IRON, 8),
                        pickaxe
                };
            }
            case 6 -> { // Oasis & Temples (250)
                Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
                    try (Connection c = AetherDatabase.getConnection();
                         PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance + 500 WHERE LOWER(username) = LOWER(?)")) {
                        ps.setDouble(1, 500.0);
                        ps.setString(2, p.getName());
                        ps.executeUpdate();
                    } catch (Throwable ignored) {}
                });
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.RAW_GOLD, 8),
                        new ItemStack(Material.CHISELED_SANDSTONE, 8),
                        new ItemStack(Material.ACACIA_SAPLING, 2)
                };
                p.sendMessage(ChatColor.GOLD + "💰 +500 Aether Coins de prime de découverte !");
            }
            case 8 -> { // Banquise & Pics (350)
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.BLUE_ICE, 4),
                        new ItemStack(Material.IRON_INGOT, 8),
                        CustomItemFactory.createCelestialKey(1)
                };
            }
            case 10 -> { // Mangrove & Marais (450)
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.SLIME_BALL, 8),
                        new ItemStack(Material.PACKED_MUD, 16),
                        new ItemStack(Material.DIAMOND, 2),
                        new ItemStack(Material.DIAMOND_PICKAXE, 1)
                };
            }
            case 12 -> { // Cité Antique (550)
                Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
                    try (Connection c = AetherDatabase.getConnection();
                         PreparedStatement ps = c.prepareStatement("UPDATE users SET shop_points = shop_points + 1 WHERE LOWER(minecraft_username) = LOWER(?)")) {
                        ps.setString(1, p.getName());
                        ps.executeUpdate();
                    } catch (Throwable ignored) {}
                });
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.ECHO_SHARD, 2),
                        new ItemStack(Material.SCULK_CATALYST, 1),
                        new ItemStack(Material.DIAMOND, 3)
                };
                p.sendMessage(ChatColor.LIGHT_PURPLE + "⭐ +1 Jeton Boutique Play-to-Earn débloqué !");
            }
            case 14 -> { // Forêts Carmélites (650)
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.SHROOMLIGHT, 8),
                        new ItemStack(Material.CRIMSON_STEM, 8),
                        new ItemStack(Material.WARPED_STEM, 8),
                        CustomItemFactory.createOmegaKey(1)
                };
            }
            case 16 -> { // Forges Royales & Bastion (750)
                if (plugin.getBoosterEngine() != null) {
                    plugin.getBoosterEngine().addMiningBooster(p.getUniqueId(), 60);
                }
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.ANCIENT_DEBRIS, 1),
                        new ItemStack(Material.GOLD_BLOCK, 2)
                };
                p.sendMessage(ChatColor.GOLD + "⚡ Surtension de Minage x2 activée pendant 60 secondes !");
            }
            case 18 -> { // Cité Flottante de l'End (850)
                Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
                    try (Connection c = AetherDatabase.getConnection();
                         PreparedStatement ps = c.prepareStatement("UPDATE users SET shop_points = shop_points + 1 WHERE LOWER(minecraft_username) = LOWER(?)")) {
                        ps.setString(1, p.getName());
                        ps.executeUpdate();
                    } catch (Throwable ignored) {}
                });
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.END_ROD, 4),
                        new ItemStack(Material.PURPUR_BLOCK, 16),
                        new ItemStack(Material.DIAMOND, 4)
                };
                p.sendMessage(ChatColor.LIGHT_PURPLE + "⭐ +1 Jeton Boutique Play-to-Earn débloqué !");
            }
            case 20 -> { // Sanctuaire de l'Infini (950)
                Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
                    try (Connection c = AetherDatabase.getConnection();
                         PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance + 2500 WHERE LOWER(username) = LOWER(?)")) {
                        ps.setDouble(1, 2500.0);
                        ps.setString(2, p.getName());
                        ps.executeUpdate();
                    } catch (Throwable ignored) {}
                });
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.NETHER_STAR, 1),
                        new ItemStack(Material.ENCHANTED_GOLDEN_APPLE, 1),
                        new ItemStack(Material.NETHERITE_INGOT, 1)
                };
                p.sendMessage(ChatColor.GOLD + "💰 +2 500 Aether Coins & Relique de l'Infini débloqués !");
            }
            default -> {
                bonusItems = new ItemStack[]{
                        new ItemStack(Material.GOLDEN_APPLE, 1),
                        new ItemStack(Material.DIAMOND, 2)
                };
            }
        }

        for (ItemStack item : bonusItems) {
            if (item != null) {
                Map<Integer, ItemStack> overflow = p.getInventory().addItem(item);
                for (ItemStack rem : overflow.values()) {
                    w.dropItemNaturally(p.getLocation(), rem);
                }
            }
        }
        w.spawnParticle(Particle.TOTEM_OF_UNDYING, p.getLocation().add(0, 1, 0), 30, 0.4, 0.6, 0.4, 0.1);
    }

    public void triggerLuckyGift(Player p, IslandData island, World w, Location loc) {
        island.treasuresFound++;
        w.spawnParticle(Particle.TOTEM_OF_UNDYING, loc.clone().add(0.5, 1.0, 0.5), 25, 0.3, 0.5, 0.3, 0.1);
        p.playSound(p.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 0.9f, 1.3f);

        int type = random.nextInt(5);
        switch (type) {
            case 0 -> {
                int coins = 50 + random.nextInt(201);
                Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
                    try (Connection c = AetherDatabase.getConnection();
                         PreparedStatement ps = c.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?)")) {
                        ps.setDouble(1, coins);
                        ps.setString(2, p.getName());
                        ps.executeUpdate();
                    } catch (Throwable ignored) {}
                });
                p.sendMessage(ChatColor.GOLD + "🎁 " + ChatColor.YELLOW + "TRÉSOR CÉLESTE : " + ChatColor.GREEN + "+" + coins + " Aether Coins ⛁ " + ChatColor.YELLOW + "crédités sur votre compte !");
            }
            case 1 -> {
                Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
                    try (Connection c = AetherDatabase.getConnection();
                         PreparedStatement ps = c.prepareStatement("UPDATE users SET shop_points = shop_points + 1 WHERE LOWER(minecraft_username) = LOWER(?)")) {
                        ps.setString(1, p.getName());
                        ps.executeUpdate();
                    } catch (Throwable ignored) {}
                });
                p.sendMessage(ChatColor.LIGHT_PURPLE + "🎁 " + ChatColor.YELLOW + "TRÉSOR CÉLESTE : " + ChatColor.GOLD + "+1 Jeton Boutique ⭐ " + ChatColor.YELLOW + "Play-to-Earn débloqué !");
            }
            case 2 -> {
                ItemStack key = CustomItemFactory.createCelestialKey(1);
                p.getInventory().addItem(key);
                p.sendMessage(ChatColor.LIGHT_PURPLE + "🎁 " + ChatColor.YELLOW + "TRÉSOR CÉLESTE : " + ChatColor.GOLD + "Clé de Caisse Céleste 🗝️ " + ChatColor.YELLOW + "obtenue ! (/crate)");
            }
            case 3 -> {
                if (plugin.getBoosterEngine() != null) {
                    plugin.getBoosterEngine().addMiningBooster(p.getUniqueId(), 60);
                }
                p.addPotionEffect(new PotionEffect(PotionEffectType.HASTE, 20 * 60, 1));
                p.sendMessage(ChatColor.GOLD + "⚡ " + ChatColor.YELLOW + "SURTENSION TEMPORAIRE : " + ChatColor.GREEN + "Minage x2 & Célérité activés pendant 60 secondes !");
            }
            default -> {
                p.getInventory().addItem(new ItemStack(Material.GOLDEN_APPLE, 1), new ItemStack(Material.DIAMOND, 2));
                p.sendMessage(ChatColor.AQUA + "🎁 " + ChatColor.YELLOW + "TRÉSOR CÉLESTE : " + ChatColor.AQUA + "1x Pomme Dorée & 2x Diamants trouvés !");
            }
        }
    }

    public void triggerSneakyTrap(Player p, IslandData island, World w, Location loc) {
        int trap = random.nextInt(5);
        switch (trap) {
            case 0 -> { // Coup de Foudre
                w.strikeLightningEffect(loc);
                p.setVelocity(p.getLocation().getDirection().multiply(-0.5).setY(0.2));
                p.playSound(loc, Sound.ENTITY_LIGHTNING_BOLT_THUNDER, 0.8f, 1.2f);
                p.sendMessage(ChatColor.YELLOW + "⚡ " + ChatColor.GOLD + "COUP DE FOUDRE CÉLESTE ! " + ChatColor.GRAY + "L'orage s'abat sur votre OneBlock !");
            }
            case 1 -> { // Fausse TNT / Sifflement Creeper
                p.playSound(loc, Sound.ENTITY_CREEPER_PRIMED, 1.0f, 1.0f);
                w.spawnParticle(Particle.EXPLOSION, loc.clone().add(0.5, 0.5, 0.5), 1);
                p.sendMessage(ChatColor.RED + "💣 " + ChatColor.YELLOW + "ATTENTION ! " + ChatColor.GRAY + "Un souffle explosif secoue la plateforme !");
            }
            case 2 -> { // Toile d'araignée & Argentiers
                loc.getBlock().setType(Material.COBWEB);
                w.spawnEntity(loc.clone().add(0.5, 0.5, 0.5), EntityType.SILVERFISH);
                w.spawnEntity(loc.clone().add(0.5, 0.5, 0.5), EntityType.SILVERFISH);
                p.playSound(loc, Sound.ENTITY_SILVERFISH_AMBIENT, 1.0f, 1.0f);
                p.sendMessage(ChatColor.GRAY + "🕸️ " + ChatColor.WHITE + "Une toile collante et des argentiers jaillissent du bloc !");
            }
            case 3 -> { // Malédiction de Sorcière
                p.playSound(loc, Sound.ENTITY_WITCH_CELEBRATE, 1.0f, 1.0f);
                p.addPotionEffect(new PotionEffect(PotionEffectType.LEVITATION, 20 * 3, 0));
                p.sendMessage(ChatColor.DARK_PURPLE + "👁️ " + ChatColor.LIGHT_PURPLE + "MALÉDICTION CÉLESTE : " + ChatColor.GRAY + "Une force mystique vous fait léviter !");
            }
            default -> { // Lave temporaire qui se solidifie
                loc.getBlock().setType(Material.LAVA);
                p.playSound(loc, Sound.ITEM_BUCKET_EMPTY_LAVA, 1.0f, 1.0f);
                p.sendMessage(ChatColor.GOLD + "🔥 " + ChatColor.RED + "MAGMA INSTABLE ! " + ChatColor.GRAY + "Le bloc s'est liquéfié temporairement !");
                Bukkit.getScheduler().runTaskLater(plugin, () -> {
                    if (loc.getBlock().getType() == Material.LAVA) {
                        loc.getBlock().setType(Material.OBSIDIAN);
                        p.playSound(loc, Sound.BLOCK_LAVA_EXTINGUISH, 1.0f, 1.0f);
                    }
                }, 30L);
            }
        }
    }

    public void spawnRandomMonster(World w, IslandData island, Player p) {
        Location spawnLoc = new Location(w, island.x + 0.5, island.y + 1.0, island.z + 0.5);
        EntityType[] pool;
        if (island.phase <= 3) {
            pool = new EntityType[]{EntityType.ZOMBIE, EntityType.SKELETON, EntityType.SPIDER};
        } else if (island.phase <= 6) {
            pool = new EntityType[]{EntityType.SLIME, EntityType.CAVE_SPIDER, EntityType.WITCH, EntityType.PILLAGER};
        } else {
            pool = new EntityType[]{EntityType.PIGLIN, EntityType.PIGLIN_BRUTE, EntityType.BLAZE, EntityType.ENDERMITE};
        }
        EntityType choice = pool[random.nextInt(pool.length)];
        Entity e = w.spawnEntity(spawnLoc, choice);
        if (e instanceof LivingEntity le) {
            if (plugin.getMobAffixEngine() != null) {
                plugin.getMobAffixEngine().applyProceduralAffixes(le, island.phase);
            } else {
                le.setCustomName(ChatColor.RED + "⚔ Intrus du OneBlock");
                le.setCustomNameVisible(true);
            }
        }
        w.spawnParticle(Particle.SMOKE, spawnLoc, 15, 0.3, 0.4, 0.3, 0.05);
        p.playSound(spawnLoc, Sound.ENTITY_ZOMBIE_AMBIENT, 0.8f, 1.1f);
        p.sendMessage(ChatColor.RED + "⚔ " + ChatColor.YELLOW + "Un monstre hostile a émergé du bloc miné !");
    }

    public IslandData getIslandAt(Location loc) {
        if (loc == null || loc.getWorld() == null) return null;
        World obWorld = getOneBlockWorld();
        if (!loc.getWorld().equals(obWorld) && !loc.getWorld().getName().equals("world_oneblock") && !loc.getWorld().getName().equals("world")) return null;
        for (IslandData island : islandsById.values()) {
            if (Math.abs(loc.getBlockX() - island.x) <= ISLAND_RADIUS &&
                Math.abs(loc.getBlockZ() - island.z) <= ISLAND_RADIUS) {
                return island;
            }
        }
        return null;
    }

    public boolean isOneBlockZone(Location loc) {
        if (loc == null || loc.getWorld() == null) return false;
        if (loc.getWorld().getName().equals("world_oneblock")) return true;
        return getIslandAt(loc) != null;
    }

    private int computePhase(int broken) {
        int calculated = 1 + (broken / 100);
        return Math.min(10, calculated);
    }

    public String getSubPhaseDisplay(int broken) {
        int sub = computeSubPhase(broken);
        if (sub >= 21) {
            return "Apogée 1K+ : " + getSubPhaseName(sub);
        }
        int major = (sub + 1) / 2;
        String decimal = (sub % 2 == 0) ? ".5" : ".0";
        return "Phase " + major + decimal + " : " + getSubPhaseName(sub);
    }

    public String getSubPhaseName(int subPhase) {
        return switch (subPhase) {
            case 1 -> "Plaines Célestes & Sylve";
            case 2 -> "Verger Fleuri & Bosquet";
            case 3 -> "Cavernes des Profondeurs";
            case 4 -> "Géode & Filon Profond";
            case 5 -> "Dunes & Désert Aride";
            case 6 -> "Oasis & Cités Ensevelies";
            case 7 -> "Toundra Boréale & Neiges";
            case 8 -> "Pics Givrés & Glace Bleue";
            case 9 -> "Jungle Sauvage & Marais";
            case 10 -> "Mangrove Tropicale & Racines";
            case 11 -> "Abîmes Obscurs & Sculk";
            case 12 -> "Cité Antique & Hurleurs";
            case 13 -> "Brasier Infernal du Nether";
            case 14 -> "Forêts Carmélite & Bizarre";
            case 15 -> "Citadelle des Bastions & Or";
            case 16 -> "Forges Royales & Trésorerie";
            case 17 -> "Faille du Vide & Îles de l'End";
            case 18 -> "Cité Flottante de l'End";
            case 19 -> "Éther Primordial & Gemmes Stellaires";
            case 20 -> "Sanctuaire de l'Infini & Reliques";
            default -> "Apogée Céleste Suprême (1K+)";
        };
    }

    public String getPhaseName(int phase) {
        return switch (phase) {
            case 1 -> "Plaines & Sylve Céleste";
            case 2 -> "Cavernes des Profondeurs";
            case 3 -> "Dunes & Cités Oubliées";
            case 4 -> "Toundra & Glaces Éternelles";
            case 5 -> "Jungle Tropicale & Marais";
            case 6 -> "Abîmes Obscurs & Sculk";
            case 7 -> "Brasier Infernal du Nether";
            case 8 -> "Citadelle des Bastions & Or";
            case 9 -> "Faille du Vide & Cités de l'End";
            case 10 -> "Éther Primordial (Apogée 1K)";
            default -> "Transcendance Cosmique";
        };
    }

    public Material getNextBlockForSubPhase(int subPhase) {
        int r = random.nextInt(100);
        return switch (subPhase) {
            case 1 -> { // Phase 1.0 (0-49)
                if (r < 35) yield Material.GRASS_BLOCK;
                if (r < 55) yield Material.DIRT;
                if (r < 75) yield Material.OAK_LOG;
                if (r < 88) yield Material.CLAY;
                yield Material.OAK_PLANKS;
            }
            case 2 -> { // Phase 1.5 - Verger & Bosquet (50-99)
                if (r < 30) yield Material.BIRCH_LOG;
                if (r < 55) yield Material.MOSS_BLOCK;
                if (r < 70) yield Material.FLOWERING_AZALEA;
                if (r < 82) yield Material.PUMPKIN;
                if (r < 92) yield Material.MELON;
                yield Material.BEEHIVE;
            }
            case 3 -> { // Phase 2.0 (100-149)
                if (r < 35) yield Material.STONE;
                if (r < 55) yield Material.COAL_ORE;
                if (r < 75) yield Material.COPPER_ORE;
                if (r < 90) yield Material.IRON_ORE;
                yield Material.COBBLESTONE;
            }
            case 4 -> { // Phase 2.5 - Géode & Filon Profond (150-199)
                if (r < 30) yield Material.DEEPSLATE;
                if (r < 55) yield Material.AMETHYST_BLOCK;
                if (r < 75) yield Material.DEEPSLATE_IRON_ORE;
                if (r < 88) yield Material.LAPIS_ORE;
                yield Material.REDSTONE_ORE;
            }
            case 5 -> { // Phase 3.0 (200-249)
                if (r < 35) yield Material.SAND;
                if (r < 55) yield Material.SANDSTONE;
                if (r < 75) yield Material.TERRACOTTA;
                if (r < 88) yield Material.CHISELED_SANDSTONE;
                yield Material.CACTUS;
            }
            case 6 -> { // Phase 3.5 - Oasis & Cités Ensevelies (250-299)
                if (r < 30) yield Material.RED_SAND;
                if (r < 55) yield Material.RED_SANDSTONE;
                if (r < 75) yield Material.GOLD_ORE;
                if (r < 88) yield Material.RAW_GOLD_BLOCK;
                yield Material.SMOOTH_SANDSTONE;
            }
            case 7 -> { // Phase 4.0 (300-349)
                if (r < 35) yield Material.SNOW_BLOCK;
                if (r < 55) yield Material.PACKED_ICE;
                if (r < 75) yield Material.SPRUCE_LOG;
                if (r < 90) yield Material.CLAY;
                yield Material.SPRUCE_PLANKS;
            }
            case 8 -> { // Phase 4.5 - Pics Givrés & Glace Bleue (350-399)
                if (r < 30) yield Material.BLUE_ICE;
                if (r < 55) yield Material.CALCITE;
                if (r < 75) yield Material.DIORITE;
                if (r < 88) yield Material.IRON_BLOCK;
                yield Material.EMERALD_ORE;
            }
            case 9 -> { // Phase 5.0 (400-449)
                if (r < 30) yield Material.JUNGLE_LOG;
                if (r < 55) yield Material.BAMBOO_BLOCK;
                if (r < 75) yield Material.MELON;
                if (r < 88) yield Material.MUD;
                yield Material.DIAMOND_ORE;
            }
            case 10 -> { // Phase 5.5 - Mangrove Tropicale (450-499)
                if (r < 30) yield Material.MANGROVE_LOG;
                if (r < 55) yield Material.PACKED_MUD;
                if (r < 75) yield Material.MUD_BRICKS;
                if (r < 88) yield Material.SLIME_BLOCK;
                yield Material.DIAMOND_ORE;
            }
            case 11 -> { // Phase 6.0 (500-549)
                if (r < 35) yield Material.SCULK;
                if (r < 55) yield Material.SCULK_VEIN;
                if (r < 75) yield Material.AMETHYST_BLOCK;
                if (r < 90) yield Material.DEEPSLATE_DIAMOND_ORE;
                yield Material.DEEPSLATE_REDSTONE_ORE;
            }
            case 12 -> { // Phase 6.5 - Cité Antique & Hurleurs (550-599)
                if (r < 30) yield Material.SCULK_CATALYST;
                if (r < 55) yield Material.SCULK_SHRIEKER;
                if (r < 75) yield Material.POLISHED_DEEPSLATE;
                if (r < 90) yield Material.DEEPSLATE_DIAMOND_ORE;
                yield Material.ECHO_SHARD;
            }
            case 13 -> { // Phase 7.0 (600-649)
                if (r < 35) yield Material.NETHERRACK;
                if (r < 55) yield Material.NETHER_QUARTZ_ORE;
                if (r < 75) yield Material.SOUL_SAND;
                if (r < 88) yield Material.BASALT;
                yield Material.NETHER_BRICKS;
            }
            case 14 -> { // Phase 7.5 - Forêts Carmélite & Bizarre (650-699)
                if (r < 30) yield Material.CRIMSON_STEM;
                if (r < 55) yield Material.WARPED_STEM;
                if (r < 70) yield Material.CRIMSON_NYLIUM;
                if (r < 82) yield Material.WARPED_NYLIUM;
                if (r < 92) yield Material.SHROOMLIGHT;
                yield Material.NETHER_GOLD_ORE;
            }
            case 15 -> { // Phase 8.0 (700-749)
                if (r < 35) yield Material.BLACKSTONE;
                if (r < 55) yield Material.POLISHED_BLACKSTONE;
                if (r < 75) yield Material.GILDED_BLACKSTONE;
                if (r < 90) yield Material.GOLD_BLOCK;
                yield Material.CRYING_OBSIDIAN;
            }
            case 16 -> { // Phase 8.5 - Forges Royales & Trésorerie (750-799)
                if (r < 30) yield Material.POLISHED_BLACKSTONE_BRICKS;
                if (r < 55) yield Material.RAW_GOLD_BLOCK;
                if (r < 75) yield Material.ANCIENT_DEBRIS;
                if (r < 90) yield Material.NETHERITE_SCRAP;
                yield Material.GOLD_BLOCK;
            }
            case 17 -> { // Phase 9.0 (800-849)
                if (r < 35) yield Material.END_STONE;
                if (r < 55) yield Material.END_STONE_BRICKS;
                if (r < 75) yield Material.PURPUR_BLOCK;
                if (r < 90) yield Material.OBSIDIAN;
                yield Material.DIAMOND_BLOCK;
            }
            case 18 -> { // Phase 9.5 - Cité Flottante de l'End (850-899)
                if (r < 30) yield Material.PURPUR_PILLAR;
                if (r < 55) yield Material.PURPUR_BLOCK;
                if (r < 75) yield Material.END_ROD;
                if (r < 90) yield Material.DIAMOND_BLOCK;
                yield Material.NETHERITE_SCRAP;
            }
            case 19 -> { // Phase 10.0 (900-949)
                if (r < 30) yield Material.PRISMARINE;
                if (r < 55) yield Material.DARK_PRISMARINE;
                if (r < 75) yield Material.SEA_LANTERN;
                if (r < 90) yield Material.EMERALD_BLOCK;
                yield Material.DIAMOND_BLOCK;
            }
            case 20 -> { // Phase 10.5 - Sanctuaire de l'Infini (950-999)
                if (r < 30) yield Material.CRYING_OBSIDIAN;
                if (r < 55) yield Material.DIAMOND_BLOCK;
                if (r < 75) yield Material.EMERALD_BLOCK;
                if (r < 90) yield Material.ANCIENT_DEBRIS;
                yield Material.BEACON;
            }
            default -> { // Apogée Suprême (1000+)
                if (r < 25) yield Material.DIAMOND_BLOCK;
                if (r < 50) yield Material.EMERALD_BLOCK;
                if (r < 70) yield Material.ANCIENT_DEBRIS;
                if (r < 85) yield Material.NETHERITE_BLOCK;
                if (r < 95) yield Material.NETHER_STAR;
                yield Material.BEACON;
            }
        };
    }

    private Material getNextBlockForPhase(int phase) {
        return getNextBlockForSubPhase(phase * 2 - 1);
    }

    private ItemStack getDropForMaterial(Material mat) {
        return switch (mat) {
            case GRASS_BLOCK, DIRT -> new ItemStack(Material.DIRT);
            case STONE -> new ItemStack(Material.COBBLESTONE);
            case COAL_ORE, DEEPSLATE_COAL_ORE -> new ItemStack(Material.COAL, 1 + random.nextInt(2));
            case IRON_ORE, RAW_IRON_BLOCK, DEEPSLATE_IRON_ORE -> new ItemStack(Material.RAW_IRON);
            case COPPER_ORE, RAW_COPPER_BLOCK, DEEPSLATE_COPPER_ORE -> new ItemStack(Material.RAW_COPPER, 2 + random.nextInt(3));
            case GOLD_ORE, DEEPSLATE_GOLD_ORE -> new ItemStack(Material.RAW_GOLD);
            case DIAMOND_ORE, DEEPSLATE_DIAMOND_ORE -> new ItemStack(Material.DIAMOND);
            case EMERALD_ORE, DEEPSLATE_EMERALD_ORE -> new ItemStack(Material.EMERALD);
            case LAPIS_ORE, DEEPSLATE_LAPIS_ORE -> new ItemStack(Material.LAPIS_LAZULI, 3 + random.nextInt(4));
            case REDSTONE_ORE, DEEPSLATE_REDSTONE_ORE -> new ItemStack(Material.REDSTONE, 4 + random.nextInt(2));
            case NETHER_GOLD_ORE -> new ItemStack(Material.GOLD_NUGGET, 4 + random.nextInt(5));
            case NETHER_QUARTZ_ORE -> new ItemStack(Material.QUARTZ, 2);
            case SNOW_BLOCK -> new ItemStack(Material.SNOWBALL, 4);
            case ANCIENT_DEBRIS -> new ItemStack(Material.ANCIENT_DEBRIS);
            case ECHO_SHARD -> new ItemStack(Material.ECHO_SHARD);
            case NETHERITE_SCRAP -> new ItemStack(Material.NETHERITE_SCRAP);
            case NETHER_STAR -> new ItemStack(Material.NETHER_STAR);
            case BEACON -> new ItemStack(Material.BEACON);
            case SLIME_BLOCK -> new ItemStack(Material.SLIME_BALL, 4);
            case MELON -> new ItemStack(Material.MELON_SLICE, 4 + random.nextInt(4));
            case MUD -> new ItemStack(Material.MUD);
            case SCULK -> new ItemStack(Material.SCULK);
            case SCULK_CATALYST -> new ItemStack(Material.SCULK_CATALYST);
            case SCULK_SHRIEKER -> new ItemStack(Material.SCULK_SHRIEKER);
            case GILDED_BLACKSTONE -> new ItemStack(Material.GILDED_BLACKSTONE);
            case BLUE_ICE -> new ItemStack(Material.BLUE_ICE);
            case PACKED_ICE -> new ItemStack(Material.PACKED_ICE);
            case RAW_GOLD_BLOCK -> new ItemStack(Material.RAW_GOLD, 9);
            case AMETHYST_CLUSTER -> new ItemStack(Material.AMETHYST_SHARD, 4);
            default -> new ItemStack(mat);
        };
    }

    private void spawnFriendlyCreature(World world, IslandData island) {
        EntityType[] pool = {EntityType.COW, EntityType.SHEEP, EntityType.PIG, EntityType.CHICKEN};
        EntityType choice = pool[random.nextInt(pool.length)];
        Location loc = new Location(world, island.x + 0.5, island.y + 1.0, island.z + 0.5);
        world.spawnEntity(loc, choice);
        world.spawnParticle(Particle.HEART, loc.clone().add(0, 0.5, 0), 10, 0.4, 0.4, 0.4, 0.1);
        world.playSound(loc, Sound.ENTITY_CHICKEN_EGG, 1.0f, 1.0f);
    }

    private void saveIslandProgressAsync(IslandData island) {
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = AetherDatabase.getConnection();
                 PreparedStatement ps = conn.prepareStatement(
                         "UPDATE player_oneblock SET phase = ?, blocks_broken = ?, level = ?, unlocked_chunks = ?, treasures_found = ?, monsters_killed = ? WHERE uuid = ?")) {
                ps.setInt(1, island.phase);
                ps.setInt(2, island.blocksBroken);
                ps.setInt(3, island.level);
                ps.setInt(4, island.unlockedChunks);
                ps.setInt(5, island.treasuresFound);
                ps.setInt(6, island.monstersKilled);
                ps.setString(7, island.ownerUuid.toString());
                ps.executeUpdate();
            } catch (Throwable ignored) {}
        });
    }

    public void saveAllSynchronously() {
        saveAllSynchronouslyInternal();
        World w = Bukkit.getWorld("world_oneblock");
        if (w != null) {
            try {
                w.save();
            } catch (Throwable t) {
                plugin.getLogger().warning("Erreur world_oneblock.save(): " + t.getMessage());
            }
        }
        if (!plugin.isEnabled()) {
            cleanupAllLockedChunkMarkers();
        }
    }

    private void saveAllSynchronouslyInternal() {
        if (islandsByPlayer.isEmpty()) return;
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                     "UPDATE player_oneblock SET phase = ?, blocks_broken = ?, level = ?, unlocked_chunks = ?, treasures_found = ?, monsters_killed = ? WHERE uuid = ?")) {
            for (IslandData island : islandsByPlayer.values()) {
                ps.setInt(1, island.phase);
                ps.setInt(2, island.blocksBroken);
                ps.setInt(3, island.level);
                ps.setInt(4, island.unlockedChunks);
                ps.setInt(5, island.treasuresFound);
                ps.setInt(6, island.monstersKilled);
                ps.setString(7, island.ownerUuid.toString());
                ps.addBatch();
            }
            ps.executeBatch();
            plugin.getLogger().info("✦ Sauvegarde synchrone OneBlock terminée (" + islandsByPlayer.size() + " îles).");
        } catch (Throwable t) {
            plugin.getLogger().warning("Erreur saveAllSynchronouslyInternal: " + t.getMessage());
        }
    }

    public void saveIslandSynchronously(IslandData island) {
        if (island == null) return;
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                     "UPDATE player_oneblock SET phase = ?, blocks_broken = ?, level = ?, unlocked_chunks = ?, treasures_found = ?, monsters_killed = ? WHERE uuid = ?")) {
            ps.setInt(1, island.phase);
            ps.setInt(2, island.blocksBroken);
            ps.setInt(3, island.level);
            ps.setInt(4, island.unlockedChunks);
            ps.setInt(5, island.treasuresFound);
            ps.setInt(6, island.monstersKilled);
            ps.setString(7, island.ownerUuid.toString());
            ps.executeUpdate();
        } catch (Throwable t) {
            plugin.getLogger().warning("Erreur saveIslandSynchronously: " + t.getMessage());
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onPlayerQuit(PlayerQuitEvent e) {
        Player p = e.getPlayer();
        IslandData island = islandsByPlayer.get(p.getUniqueId());
        if (island != null) {
            saveIslandSynchronously(island);
        }
    }

    private void startAutosaveTimer() {
        Bukkit.getScheduler().runTaskTimerAsynchronously(plugin, () -> {
            try {
                saveAllSynchronouslyInternal();
            } catch (Throwable t) {
                plugin.getLogger().warning("Erreur autosave asynchrone OneBlock: " + t.getMessage());
            }
            Bukkit.getScheduler().runTask(plugin, () -> {
                World w = Bukkit.getWorld("world_oneblock");
                if (w != null) {
                    try {
                        w.save();
                    } catch (Throwable t) {
                        plugin.getLogger().warning("Erreur w.save() autosave: " + t.getMessage());
                    }
                }
            });
        }, 1200L, 1200L);
    }

    // =========================================================================
    // FEATURE F18: Indicateurs Visuels de Chunks Verrouillés (OneBlock Option 1)
    // =========================================================================

    private void startProximityVisualTask() {
        this.proximityTask = Bukkit.getScheduler().runTaskTimer(plugin, this::tickLockedChunkVisuals, 20L, 10L);
    }

    public void tickLockedChunkVisuals() {
        World obWorld = Bukkit.getWorld("world_oneblock");
        if (obWorld == null) return;

        for (Player player : obWorld.getPlayers()) {
            if (!player.isOnline()) continue;
            Location pLoc = player.getLocation();
            IslandData island = getIslandAt(pLoc);
            if (island == null) {
                island = islandsByPlayer.get(player.getUniqueId());
            }
            if (island == null) continue;

            Map<String, Entity> markers = islandLockedMarkers.get(island.islandId);
            if (markers == null || markers.isEmpty()) {
                updateLockedChunkMarkers(obWorld, island);
            }

            tickProximityParticlesForPlayer(player, obWorld, island);
        }
    }

    private void tickProximityParticlesForPlayer(Player player, World world, IslandData island) {
        Location pLoc = player.getLocation();
        double px = pLoc.getX();
        double py = pLoc.getY();
        double pz = pLoc.getZ();

        if (Math.abs(py - island.y) > 25.0) return;

        int baseChunkX = island.x >> 4;
        int baseChunkZ = island.z >> 4;

        for (int[] offset : SURROUNDING_CHUNK_OFFSETS) {
            int relX = offset[0];
            int relZ = offset[1];
            int requiredTier = getRequiredTierForChunk(relX, relZ);

            // Cesser l'émission si le chunk est déjà débloqué
            if (island.unlockedChunks >= requiredTier) continue;

            int chunkX = baseChunkX + relX;
            int chunkZ = baseChunkZ + relZ;

            int minX = chunkX * 16;
            int maxX = minX + 16;
            int minZ = chunkZ * 16;
            int maxZ = minZ + 16;

            double dx = 0;
            if (px < minX) dx = minX - px;
            else if (px > maxX) dx = px - maxX;

            double dz = 0;
            if (pz < minZ) dz = minZ - pz;
            else if (pz > maxZ) dz = pz - maxZ;

            double dist = Math.sqrt(dx * dx + dz * dz);

            // Détection de proximité entre 8 et 10 blocs
            if (dist <= 10.0) {
                emitChunkBoundaryParticles(world, minX, maxX, minZ, maxZ, island.y, py);
            }
        }
    }

    private void emitChunkBoundaryParticles(World world, int minX, int maxX, int minZ, int maxZ, int islandY, double playerY) {
        double y1 = islandY + 0.2;
        double y2 = islandY + 1.2;

        // Bords Nord & Sud
        for (int x = minX; x <= maxX; x += 2) {
            spawnBorderParticle(world, x, y1, minZ, redDustOptions);
            spawnBorderParticle(world, x, y2, minZ, redDustOptions);
            spawnBorderParticle(world, x, y1, maxZ, redDustOptions);
            spawnBorderParticle(world, x, y2, maxZ, redDustOptions);
        }

        // Bords Ouest & Est
        for (int z = minZ; z <= maxZ; z += 2) {
            spawnBorderParticle(world, minX, y1, z, redDustOptions);
            spawnBorderParticle(world, minX, y2, z, redDustOptions);
            spawnBorderParticle(world, maxX, y1, z, redDustOptions);
            spawnBorderParticle(world, maxX, y2, z, redDustOptions);
        }
    }

    private void spawnBorderParticle(World world, double x, double y, double z, Particle.DustOptions dust) {
        try {
            world.spawnParticle(Particle.DUST, x, y, z, 1, 0, 0, 0, 0, dust);
        } catch (Throwable t) {
            try {
                world.spawnParticle(Particle.FLAME, x, y, z, 1, 0, 0, 0, 0.01);
            } catch (Throwable ignored) {}
        }
    }

    public void updateLockedChunkMarkers(World world, IslandData island) {
        if (world == null || island == null) return;
        int baseChunkX = island.x >> 4;
        int baseChunkZ = island.z >> 4;

        Map<String, Entity> islandMarkers = islandLockedMarkers.computeIfAbsent(island.islandId, k -> new ConcurrentHashMap<>());

        for (int[] offset : SURROUNDING_CHUNK_OFFSETS) {
            int relX = offset[0];
            int relZ = offset[1];
            int targetChunkX = baseChunkX + relX;
            int targetChunkZ = baseChunkZ + relZ;
            String chunkKey = targetChunkX + "_" + targetChunkZ;
            int requiredTier = getRequiredTierForChunk(relX, relZ);

            if (island.unlockedChunks >= requiredTier) {
                // Auto-Dismissal dès le déblocage du palier requis
                Entity marker = islandMarkers.remove(chunkKey);
                if (marker != null && marker.isValid()) {
                    marker.remove();
                }
                Location cLoc = new Location(world, targetChunkX * 16 + 8.0, island.y + 1.5, targetChunkZ * 16 + 8.0);
                if (world.isChunkLoaded(targetChunkX, targetChunkZ)) {
                    for (Entity e : world.getNearbyEntities(cLoc, 4.0, 4.0, 4.0)) {
                        if (e.getScoreboardTags().contains(TAG_LOCKED_CHUNK_MARKER)) {
                            e.remove();
                        }
                    }
                }
            } else {
                // Chunk verrouillé : maintien ou création de l'hologramme 3D
                spawnOrUpdateLockedMarker(world, island, targetChunkX, targetChunkZ, requiredTier, islandMarkers);
            }
        }
    }

    private void spawnOrUpdateLockedMarker(World world, IslandData island, int chunkX, int chunkZ, int requiredTier, Map<String, Entity> islandMarkers) {
        String chunkKey = chunkX + "_" + chunkZ;
        String markerText = ChatColor.RED + "🔒 Chunk Verrouillé" + "\n" + ChatColor.YELLOW + "Palier " + requiredTier + " Requis";
        double mx = chunkX * 16 + 8.0;
        double my = island.y + 1.5;
        double mz = chunkZ * 16 + 8.0;
        Location markerLoc = new Location(world, mx, my, mz);

        if (!world.isChunkLoaded(chunkX, chunkZ)) {
            world.getChunkAtAsync(chunkX, chunkZ).thenAccept(chunk -> {
                Bukkit.getScheduler().runTask(plugin, () -> {
                    spawnOrUpdateLockedMarker(world, island, chunkX, chunkZ, requiredTier, islandMarkers);
                });
            });
            return;
        }

        Entity existing = islandMarkers.get(chunkKey);
        if (existing != null && existing.isValid() && !existing.isDead()) {
            existing.setCustomName(markerText);
            if (existing instanceof TextDisplay td) {
                td.setText(markerText);
            }
            return;
        }

        for (Entity e : world.getNearbyEntities(markerLoc, 3.0, 3.0, 3.0)) {
            if (e.getScoreboardTags().contains(TAG_LOCKED_CHUNK_MARKER)) {
                e.setCustomName(markerText);
                if (e instanceof TextDisplay td) {
                    td.setText(markerText);
                }
                islandMarkers.put(chunkKey, e);
                return;
            }
        }

        try {
            TextDisplay td = world.spawn(markerLoc, TextDisplay.class, display -> {
                display.setBillboard(Display.Billboard.CENTER);
                display.setBrightness(new Display.Brightness(15, 15));
                display.setBackgroundColor(Color.fromARGB(180, 80, 20, 20));
                display.setText(markerText);
                display.setCustomName(markerText);
                display.setCustomNameVisible(true);
                display.addScoreboardTag(TAG_LOCKED_CHUNK_MARKER);
                display.setPersistent(false);
            });
            islandMarkers.put(chunkKey, td);
        } catch (Throwable t) {
            try {
                ArmorStand as = world.spawn(markerLoc, ArmorStand.class, stand -> {
                    stand.setVisible(false);
                    stand.setGravity(false);
                    stand.setMarker(true);
                    stand.setCustomName(markerText);
                    stand.setCustomNameVisible(true);
                    stand.addScoreboardTag(TAG_LOCKED_CHUNK_MARKER);
                    stand.setPersistent(false);
                });
                islandMarkers.put(chunkKey, as);
            } catch (Throwable ignored) {}
        }
    }

    public void cleanupAllLockedChunkMarkers() {
        if (proximityTask != null) {
            proximityTask.cancel();
            proximityTask = null;
        }

        for (Map<String, Entity> map : islandLockedMarkers.values()) {
            for (Entity e : map.values()) {
                if (e != null && e.isValid()) {
                    e.remove();
                }
            }
            map.clear();
        }
        islandLockedMarkers.clear();

        World obWorld = Bukkit.getWorld("world_oneblock");
        if (obWorld != null) {
            for (Entity e : obWorld.getEntities()) {
                if (e.getScoreboardTags().contains(TAG_LOCKED_CHUNK_MARKER)) {
                    e.remove();
                }
            }
        }
    }

    public Map<String, Entity> getLockedChunkMarkers(int islandId) {
        Map<String, Entity> markers = islandLockedMarkers.get(islandId);
        return (markers != null) ? Collections.unmodifiableMap(markers) : Collections.emptyMap();
    }

    @EventHandler(priority = EventPriority.NORMAL)
    public void onMarkerInteract(PlayerInteractAtEntityEvent event) {
        Entity entity = event.getRightClicked();
        if (entity != null && entity.getScoreboardTags().contains(TAG_LOCKED_CHUNK_MARKER)) {
            Player player = event.getPlayer();
            player.playSound(player.getLocation(), Sound.BLOCK_CHEST_LOCKED, 0.9f, 1.2f);
            player.sendMessage(ChatColor.RED + "🔒 Ce chunk est verrouillé ! Continuez de miner pour le débloquer.");
            event.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onPluginDisable(PluginDisableEvent event) {
        if (event.getPlugin().equals(plugin)) {
            cleanupAllLockedChunkMarkers();
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onChunkUnload(ChunkUnloadEvent event) {
        if (event.getWorld() == null || !event.getWorld().getName().equals("world_oneblock")) return;
        for (Entity e : event.getChunk().getEntities()) {
            if (e.getScoreboardTags().contains(TAG_LOCKED_CHUNK_MARKER)) {
                e.remove();
            }
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onWorldUnload(WorldUnloadEvent event) {
        if (event.getWorld() != null && event.getWorld().getName().equals("world_oneblock")) {
            cleanupAllLockedChunkMarkers();
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onChunkLoad(ChunkLoadEvent event) {
        if (event.getWorld() == null || !event.getWorld().getName().equals("world_oneblock")) return;
        Block centerBlock = event.getChunk().getBlock(8, BASE_Y, 8);
        IslandData island = getIslandAt(centerBlock.getLocation());
        if (island != null) {
            int relX = event.getChunk().getX() - (island.x >> 4);
            int relZ = event.getChunk().getZ() - (island.z >> 4);
            int requiredTier = getRequiredTierForChunk(relX, relZ);
            if (island.unlockedChunks < requiredTier) {
                Map<String, Entity> islandMarkers = islandLockedMarkers.computeIfAbsent(island.islandId, k -> new ConcurrentHashMap<>());
                spawnOrUpdateLockedMarker(event.getWorld(), island, event.getChunk().getX(), event.getChunk().getZ(), requiredTier, islandMarkers);
            }
        }
    }

    public boolean isIslandInDatabase(UUID uuid) {
        if (uuid == null) return false;
        try (Connection conn = AetherDatabase.getConnection();
             PreparedStatement ps = conn.prepareStatement("SELECT 1 FROM player_oneblock WHERE uuid = ?")) {
            ps.setString(1, uuid.toString());
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next();
            }
        } catch (Throwable ignored) {
            return false;
        }
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur peut utiliser les commandes OneBlock.");
            return true;
        }

        if (args.length == 0 || args[0].equalsIgnoreCase("home") || args[0].equalsIgnoreCase("go")) {
            teleportToIsland(player);
            return true;
        }

        if (args[0].equalsIgnoreCase("rebuild") || args[0].equalsIgnoreCase("reset") || args[0].equalsIgnoreCase("fix")) {
            IslandData island = islandsByPlayer.get(player.getUniqueId());
            if (island == null) {
                teleportToIsland(player);
                return true;
            }
            World w = getOneBlockWorld();
            buildIslandStructure(w, island);
            player.teleport(island.getSpawnLocation(w));
            player.playSound(player.getLocation(), Sound.BLOCK_AMETHYST_BLOCK_CHIME, 1.0f, 1.4f);
            player.sendMessage(ChatColor.GREEN + "✦ Votre île OneBlock isolée dans le vide a été restaurée avec succès !");
            return true;
        }

        if (args[0].equalsIgnoreCase("spawn") || args[0].equalsIgnoreCase("hub")) {
            if (plugin.getPortalEngine() != null) {
                plugin.getPortalEngine().teleportToHub(player);
                return true;
            }
            World mainWorld = Bukkit.getWorld("world");
            if (mainWorld == null && !Bukkit.getWorlds().isEmpty()) mainWorld = Bukkit.getWorlds().get(0);
            Location agora = new Location(mainWorld, 0.5, 121.0, 1.5, 0f, 0f);
            player.teleport(agora);
            player.sendMessage(ChatColor.GOLD + "🪐 Téléporté à l'Agora Céleste !");
            return true;
        }

        if (args[0].equalsIgnoreCase("info") || args[0].equalsIgnoreCase("stats")) {
            IslandData island = islandsByPlayer.get(player.getUniqueId());
            if (island == null) {
                player.sendMessage(ChatColor.YELLOW + "✦ Vous n'avez pas encore d'île. Tapez /ob pour en créer une !");
                return true;
            }
            int nextGoal = getNextGoalBlocks(island.blocksBroken);
            int nextChunk = getNextPalierBlocks(island.blocksBroken);
            int remaining = Math.max(0, nextGoal - island.blocksBroken);
            String goalDesc = (nextGoal == nextChunk)
                    ? ("Palier Chunk #" + (island.unlockedChunks + 1))
                    : "Demi-palier Récompense & Sous-zone";

            player.sendMessage(ChatColor.DARK_AQUA + "========================================");
            player.sendMessage(ChatColor.GOLD + "✦ VOTRE DOMAINE ONEBLOCK (#" + island.islandId + ")");
            player.sendMessage(ChatColor.AQUA + "• Sous-Zone Actuelle : " + ChatColor.YELLOW + getSubPhaseDisplay(island.blocksBroken));
            player.sendMessage(ChatColor.GREEN + "• Progression Blocs : " + ChatColor.WHITE + island.blocksBroken + " / 1000 blocs (Courbe Exponentielle)");
            player.sendMessage(ChatColor.LIGHT_PURPLE + "• Chunks débloqués : " + ChatColor.WHITE + island.unlockedChunks + " Chunks (Territoire étendu)");
            player.sendMessage(ChatColor.YELLOW + "• Prochain Objectif : " + ChatColor.WHITE + "dans " + remaining + " bloc(s) (" + goalDesc + ")");
            player.sendMessage(ChatColor.GOLD + "• Trésors & Cadeaux découverts : " + ChatColor.WHITE + island.treasuresFound + " 🎁");
            player.sendMessage(ChatColor.RED + "• Monstres & Boss vaincus : " + ChatColor.WHITE + island.monstersKilled + " ⚔️");
            player.sendMessage(ChatColor.GRAY + "• Membres invités : " + ChatColor.WHITE + (island.trustedMembers.isEmpty() ? "Aucun (Solo)" : String.join(", ", island.trustedMembers)));
            player.sendMessage(ChatColor.DARK_AQUA + "========================================");
            return true;
        }

        if (args[0].equalsIgnoreCase("invite") || args[0].equalsIgnoreCase("trust")) {
            if (args.length < 2) {
                player.sendMessage(ChatColor.RED + "Utilisation : /ob invite <joueur>");
                return true;
            }
            IslandData island = islandsByPlayer.get(player.getUniqueId());
            if (island == null) {
                player.sendMessage(ChatColor.RED + "Créez d'abord votre île avec /ob !");
                return true;
            }
            String target = args[1].toLowerCase();
            if (island.trustedMembers.contains(target)) {
                player.sendMessage(ChatColor.YELLOW + target + " est déjà invité sur votre île !");
            } else {
                island.trustedMembers.add(target);
                player.sendMessage(ChatColor.GREEN + "✦ " + target + " a été invité sur votre île OneBlock !");
            }
            return true;
        }

        player.sendMessage(ChatColor.GOLD + "✦ Commandes OneBlock : /ob, /ob spawn, /ob info, /ob rebuild, /ob invite <joueur>");
        return true;
    }
}
