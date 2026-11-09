package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Color;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.entity.Display;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.entity.TextDisplay;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockPhysicsEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerPortalEvent;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.util.Vector;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

public class PortalTeleportEngine implements Listener {

    public static final int PORTAL1_X = 0;
    public static final int PORTAL1_Y = 120;
    public static final int PORTAL1_Z = 15;

    public static final int PORTAL2_X = 640;
    public static final int PORTAL2_Z = 864;

    public static final int PORTAL_ONEBLOCK_X = -12;
    public static final int PORTAL_ONEBLOCK_Y = 120;
    public static final int PORTAL_ONEBLOCK_Z = 12;

    private static final long COOLDOWN_MS = 1500;
    private final AetherVisualsPlugin plugin;
    private final Map<UUID, Long> lastTeleportMap = new ConcurrentHashMap<>();

    public PortalTeleportEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
    }

    public boolean isInsidePortalOneBlock(Location loc) {
        if (loc == null || loc.getWorld() == null) return false;
        int bx = loc.getBlockX();
        int by = loc.getBlockY();
        int bz = loc.getBlockZ();
        boolean inFrame = (bz == PORTAL_ONEBLOCK_Z && Math.abs(bx - PORTAL_ONEBLOCK_X) <= 1 && by >= PORTAL_ONEBLOCK_Y + 1 && by <= PORTAL_ONEBLOCK_Y + 4);
        Material feetMat = loc.getBlock().getType();
        boolean touches = (feetMat == Material.NETHER_PORTAL || feetMat == Material.END_PORTAL);
        return inFrame || (touches && Math.abs(bx - PORTAL_ONEBLOCK_X) <= 2 && Math.abs(bz - PORTAL_ONEBLOCK_Z) <= 1);
    }

    public boolean isNearPortalOneBlock(Location loc) {
        if (loc == null || loc.getWorld() == null) return false;
        return Math.abs(loc.getBlockX() - PORTAL_ONEBLOCK_X) <= 2
                && Math.abs(loc.getBlockZ() - PORTAL_ONEBLOCK_Z) <= 2
                && Math.abs(loc.getBlockY() - PORTAL_ONEBLOCK_Y) <= 5;
    }

    public boolean isInsidePortal1(Location loc) {
        if (loc == null || loc.getWorld() == null) return false;
        int bx = loc.getBlockX();
        int by = loc.getBlockY();
        int bz = loc.getBlockZ();

        boolean inFrame = (bz == PORTAL1_Z && Math.abs(bx - PORTAL1_X) <= 1 && by >= PORTAL1_Y + 1 && by <= PORTAL1_Y + 4);
        Material feetMat = loc.getBlock().getType();
        Material eyeMat = loc.clone().add(0, 1, 0).getBlock().getType();
        boolean touches = (feetMat == Material.NETHER_PORTAL || feetMat == Material.END_PORTAL ||
                           eyeMat == Material.NETHER_PORTAL || eyeMat == Material.END_PORTAL);

        return inFrame || (touches && Math.abs(bx - PORTAL1_X) <= 2 && Math.abs(bz - PORTAL1_Z) <= 1);
    }

    public boolean isNearPortal1(Location loc) {
        if (loc == null || loc.getWorld() == null) return false;
        return Math.abs(loc.getBlockX() - PORTAL1_X) <= 2
                && Math.abs(loc.getBlockZ() - PORTAL1_Z) <= 2
                && Math.abs(loc.getBlockY() - PORTAL1_Y) <= 5;
    }

    public boolean isInsidePortal2(Location loc) {
        if (loc == null || loc.getWorld() == null) return false;
        int bx = loc.getBlockX();
        int by = loc.getBlockY();
        int bz = loc.getBlockZ();
        int baseY = getSpawn2GroundY(loc.getWorld());

        boolean inFrame = (bz == PORTAL2_Z && Math.abs(bx - PORTAL2_X) <= 1 && by >= baseY + 1 && by <= baseY + 4);
        Material feetMat = loc.getBlock().getType();
        Material eyeMat = loc.clone().add(0, 1, 0).getBlock().getType();
        boolean touches = (feetMat == Material.NETHER_PORTAL || feetMat == Material.END_PORTAL ||
                           eyeMat == Material.NETHER_PORTAL || eyeMat == Material.END_PORTAL);

        return inFrame || (touches && Math.abs(bx - PORTAL2_X) <= 2 && Math.abs(bz - PORTAL2_Z) <= 1);
    }

    public boolean isNearPortal2(Location loc) {
        if (loc == null || loc.getWorld() == null) return false;
        int baseY = getSpawn2GroundY(loc.getWorld());
        return Math.abs(loc.getBlockX() - PORTAL2_X) <= 2
                && Math.abs(loc.getBlockZ() - PORTAL2_Z) <= 2
                && Math.abs(loc.getBlockY() - baseY) <= 5;
    }

    public int getSpawn2GroundY(World world) {
        if (world == null) return 66;
        return CelestialSpawnBuilder.getSafeGroundY(world, PORTAL2_X, PORTAL2_Z);
    }

    public Location getSpawn2Arrival(World world) {
        int y = getSpawn2GroundY(world);
        return new Location(world, PORTAL2_X + 0.5, y + 1.0, PORTAL2_Z + 4.5, 180f, 0f);
    }

    public Location getSpawn1Arrival(World world) {
        return new Location(world, 0.5, 121.0, 1.5, 0f, 0f);
    }

    public World getHubWorld() {
        World w = Bukkit.getWorld("world");
        if (w == null && !Bukkit.getWorlds().isEmpty()) {
            w = Bukkit.getWorlds().get(0);
        }
        return w;
    }

    public boolean isOneBlockReturnPortalArea(Location loc) {
        if (loc == null || loc.getWorld() == null || plugin.getOneBlockEngine() == null) return false;
        if (!loc.getWorld().getName().equalsIgnoreCase("world_oneblock")) return false;
        OneBlockEngine.IslandData island = plugin.getOneBlockEngine().getIslandAt(loc);
        if (island == null) return false;
        return Math.abs(loc.getBlockX() - island.x) <= 2 && Math.abs(loc.getBlockZ() - (island.z - 12)) <= 2 && Math.abs(loc.getBlockY() - island.y) <= 4;
    }

    private boolean canTeleport(UUID uuid) {
        long now = System.currentTimeMillis();
        Long last = lastTeleportMap.get(uuid);
        return (last == null || (now - last) >= COOLDOWN_MS);
    }

    public static boolean isUnsafeLocation(Location loc) {
        if (loc == null || loc.getWorld() == null) return true;
        Block feet = loc.getBlock();
        Block head = feet.getRelative(0, 1, 0);
        Block below = feet.getRelative(0, -1, 0);
        if (feet.getType().isSolid() || head.getType().isSolid()) return true;
        if (feet.isLiquid() || head.isLiquid()) return true;
        return !below.getType().isSolid();
    }

    public void teleportToSurvival(Player player) {
        teleportToSurvival(player, false);
    }

    public void teleportToSurvival(Player player, boolean forceSpawnPad) {
        World world = getHubWorld();
        if (world == null) {
            player.sendMessage(ChatColor.RED + "Erreur : Monde Survie introuvable.");
            return;
        }

        // 1. Régénération automatique du portail retour (Portal 2) s'il est cassé
        int baseY = getSpawn2GroundY(world);
        Block portalBlock = world.getBlockAt(PORTAL2_X, baseY + 1, PORTAL2_Z);
        if (portalBlock.getType() != Material.NETHER_PORTAL) {
            CelestialSpawnBuilder.regenerateSurvivalPortalSafely(world, PORTAL2_X, PORTAL2_Z);
        }

        Location savedLoc = (plugin.getPlayerLocationEngine() != null && !forceSpawnPad)
                ? plugin.getPlayerLocationEngine().getLastSurvivalLocation(player.getUniqueId()) : null;

        // 2. Si le portail ou point de survie du joueur est cassé/obstrué, régénérer ailleurs
        if (savedLoc != null && isUnsafeLocation(savedLoc)) {
            player.sendMessage(ChatColor.YELLOW + "⚠️ Votre ancien point de survie était obstrué ou le portail était brisé : redirection vers le portail régénéré !");
            savedLoc = null;
        }

        Location target = (savedLoc != null && savedLoc.getWorld() != null) ? savedLoc : getSpawn2Arrival(world);
        lastTeleportMap.put(player.getUniqueId(), System.currentTimeMillis());

        boolean isResuming = (savedLoc != null && savedLoc.getWorld() != null);

        world.getChunkAtAsync(target).thenAccept(chunk -> {
            Bukkit.getScheduler().runTask(plugin, () -> {
                player.setVelocity(new Vector(0, 0, 0));
                player.setFallDistance(0.0f);
                player.teleport(target, org.bukkit.event.player.PlayerTeleportEvent.TeleportCause.PLUGIN);
                player.playSound(target, Sound.BLOCK_PORTAL_TRAVEL, 0.8f, 1.2f);
                player.playSound(target, Sound.ENTITY_PLAYER_TELEPORT, 1.0f, 1.0f);
                player.spawnParticle(Particle.PORTAL, target.clone().add(0, 1, 0), 40, 0.5, 0.8, 0.5, 0.1);

                player.addPotionEffect(new PotionEffect(PotionEffectType.REGENERATION, 20 * 15, 1, false, false, true));
                player.addPotionEffect(new PotionEffect(PotionEffectType.RESISTANCE, 20 * 15, 1, false, false, true));
                player.addPotionEffect(new PotionEffect(PotionEffectType.SATURATION, 20 * 15, 0, false, false, true));

                if (isResuming) {
                    player.sendTitle(ChatColor.GREEN + "🌲 MONDE SURVIE",
                            ChatColor.YELLOW + "Reprise à votre dernière position connue !", 10, 50, 15);
                    player.sendMessage(ChatColor.GREEN + "✦ Vous avez repris exactement là où vous étiez en survie.");
                    player.sendMessage(ChatColor.GRAY + "Astuce : pour rejoindre l'esplanade du portail : /survie spawn");
                } else {
                    player.sendTitle(ChatColor.GREEN + "🌲 MONDE SURVIE",
                            ChatColor.YELLOW + "Plaines Primordiales (X=640, Z=864) • Régénération Active !", 10, 60, 20);
                    player.sendMessage(ChatColor.DARK_AQUA + "================================================");
                    player.sendMessage(ChatColor.GOLD + "✦ BIENVENUE EN SURVIE PRIMORDIALE !");
                    player.sendMessage(ChatColor.GREEN + "• Sol 100% terrestre (Plaines verdoyantes : X=640, Z=864)");
                    player.sendMessage(ChatColor.AQUA + "• Protection & Régénération actives pendant 15 secondes");
                    player.sendMessage(ChatColor.YELLOW + "• Pour retourner à l'Agora, reprenez le portail ou tapez /spawn !");
                    player.sendMessage(ChatColor.DARK_AQUA + "================================================");
                }
            });
        });
    }

    public void teleportToHub(Player player) {
        World world = getHubWorld();
        if (world == null) {
            player.sendMessage(ChatColor.RED + "Erreur : Monde Agora introuvable.");
            return;
        }
        // Vérifier l'intégrité du Portail 1 à l'Agora, régénérer si cassé
        Block p1 = world.getBlockAt(PORTAL1_X, PORTAL1_Y + 1, PORTAL1_Z);
        if (p1.getType() != Material.NETHER_PORTAL) {
            CelestialSpawnBuilder.buildDungeonPortal(world, PORTAL1_X, PORTAL1_Y, PORTAL1_Z);
        }
        Location target = getSpawn1Arrival(world);
        lastTeleportMap.put(player.getUniqueId(), System.currentTimeMillis());

        world.getChunkAtAsync(target).thenAccept(chunk -> {
            Bukkit.getScheduler().runTask(plugin, () -> {
                player.setVelocity(new Vector(0, 0, 0));
                player.setFallDistance(0.0f);
                player.teleport(target, org.bukkit.event.player.PlayerTeleportEvent.TeleportCause.PLUGIN);
                player.playSound(target, Sound.BLOCK_PORTAL_TRAVEL, 0.8f, 1.2f);
                player.playSound(target, Sound.ENTITY_PLAYER_TELEPORT, 1.0f, 1.0f);
                player.spawnParticle(Particle.REVERSE_PORTAL, target.clone().add(0, 1, 0), 40, 0.5, 0.8, 0.5, 0.1);

                player.sendTitle(ChatColor.AQUA + "🪐 AGORA CÉLESTE",
                        ChatColor.GOLD + "Spawn Principal de l'Archipel (Y=120)", 10, 60, 20);
                player.sendMessage(ChatColor.AQUA + "✦ Vous avez franchi le portail retour vers l'Agora Céleste !");
            });
        });
    }

    public static void spawnPortalHolograms(World w) {
        if (w == null) return;
        Location h1 = new Location(w, PORTAL1_X + 0.5, PORTAL1_Y + 5.5, PORTAL1_Z + 0.5);
        for (Entity e : w.getNearbyEntities(h1, 3, 3, 3)) {
            if (e.getScoreboardTags().contains("aether_portal_holo")) e.remove();
        }
        w.spawn(h1, TextDisplay.class, td -> {
            td.setBillboard(Display.Billboard.CENTER);
            td.setBrightness(new Display.Brightness(15, 15));
            td.setBackgroundColor(Color.fromARGB(180, 10, 35, 20));
            td.setText("§a§l🌲 VORTEX VERS LE MONDE SURVIE\n§fPlaines Primordiales (X=640, Z=864)\n§e✨ Entrez dans le portail ou tapez §f/survie");
            td.addScoreboardTag("aether_portal_holo");
            td.addScoreboardTag("aether_spawn_prop");
        });

        int y2 = CelestialSpawnBuilder.getSafeGroundY(w, PORTAL2_X, PORTAL2_Z);
        Location h2 = new Location(w, PORTAL2_X + 0.5, y2 + 5.5, PORTAL2_Z + 0.5);
        for (Entity e : w.getNearbyEntities(h2, 3, 3, 3)) {
            if (e.getScoreboardTags().contains("aether_portal2_holo")) e.remove();
        }
        w.spawn(h2, TextDisplay.class, td -> {
            td.setBillboard(Display.Billboard.CENTER);
            td.setBrightness(new Display.Brightness(15, 15));
            td.setBackgroundColor(Color.fromARGB(180, 15, 25, 45));
            td.setText("§b§l🪐 PORTAIL RETOUR VERS L'AGORA\n§fArchipel Céleste & Boutiques (Y=120)\n§e✨ Entrez pour regagner la cité ou tapez §f/spawn");
            td.addScoreboardTag("aether_portal2_holo");
            td.addScoreboardTag("aether_spawn_prop");
        });
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onPlayerPortal(PlayerPortalEvent event) {
        Player player = event.getPlayer();
        Location from = event.getFrom();
        if (isInsidePortal1(from) || isNearPortal1(from)) {
            event.setCancelled(true);
            if (canTeleport(player.getUniqueId())) teleportToSurvival(player);
        } else if (isInsidePortalOneBlock(from) || isNearPortalOneBlock(from)) {
            event.setCancelled(true);
            if (canTeleport(player.getUniqueId()) && plugin.getOneBlockEngine() != null) {
                lastTeleportMap.put(player.getUniqueId(), System.currentTimeMillis());
                plugin.getOneBlockEngine().teleportToIsland(player);
            }
        } else if (isInsidePortal2(from) || isNearPortal2(from)) {
            event.setCancelled(true);
            if (canTeleport(player.getUniqueId())) teleportToHub(player);
        } else if (from.getWorld() != null && (from.getWorld().getName().equalsIgnoreCase("world") || from.getWorld().getName().equalsIgnoreCase("world_oneblock"))) {
            // Portail de joueur dans le monde survie ou OneBlock : retour sécurisé vers l'Agora
            event.setCancelled(true);
            if (canTeleport(player.getUniqueId())) {
                teleportToHub(player);
                if (plugin.getOneBlockEngine() != null && plugin.getOneBlockEngine().isOneBlockZone(from)) {
                    player.sendMessage(ChatColor.AQUA + "✦ Portail OneBlock emprunté : retour sécurisé vers l'Agora Céleste !");
                } else {
                    player.sendMessage(ChatColor.AQUA + "✦ Portail de joueur emprunté : téléportation sécurisée vers l'Agora Céleste !");
                }
            }
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onPlayerMove(PlayerMoveEvent event) {
        Location to = event.getTo();
        if (to == null) return;
        Player player = event.getPlayer();
        UUID uuid = player.getUniqueId();

        boolean touchesPortal = to.getBlock().getType() == Material.NETHER_PORTAL ||
                                to.clone().add(0, 1, 0).getBlock().getType() == Material.NETHER_PORTAL;

        if ((isInsidePortal1(to) || isNearPortal1(to) && touchesPortal) && canTeleport(uuid)) {
            teleportToSurvival(player);
        } else if ((isInsidePortalOneBlock(to) || isNearPortalOneBlock(to) && touchesPortal) && canTeleport(uuid)) {
            if (plugin.getOneBlockEngine() != null) {
                lastTeleportMap.put(uuid, System.currentTimeMillis());
                plugin.getOneBlockEngine().teleportToIsland(player);
            }
        } else if ((isInsidePortal2(to) || isNearPortal2(to) && touchesPortal) && canTeleport(uuid)) {
            teleportToHub(player);
        } else if ((touchesPortal || isOneBlockReturnPortalArea(to)) && canTeleport(uuid) && to.getWorld() != null && (to.getWorld().getName().equalsIgnoreCase("world") || to.getWorld().getName().equalsIgnoreCase("world_oneblock"))) {
            // Portail nether de joueur franchi en survie ou OneBlock
            teleportToHub(player);
            if (plugin.getOneBlockEngine() != null && plugin.getOneBlockEngine().isOneBlockZone(to)) {
                player.sendMessage(ChatColor.AQUA + "✦ Portail OneBlock emprunté : retour sécurisé vers l'Agora Céleste !");
            } else {
                player.sendMessage(ChatColor.AQUA + "✦ Portail de joueur franchi : téléportation vers l'Agora Céleste !");
            }
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onBlockPhysics(BlockPhysicsEvent event) {
        if (event.getChangedType() == Material.NETHER_PORTAL) {
            Location loc = event.getBlock().getLocation();
            if (isNearPortal1(loc) || isNearPortal2(loc) || isNearPortalOneBlock(loc) ||
                (plugin.getOneBlockEngine() != null && plugin.getOneBlockEngine().isOneBlockZone(loc))) {
                event.setCancelled(true);
            }
        }
    }
}
