package io.aethercraft.visuals;

import org.bukkit.*;
import org.bukkit.block.Block;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerRespawnEvent;
import org.bukkit.event.player.PlayerTeleportEvent;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.scheduler.BukkitRunnable;

import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Moteur Path RTP & Rituel de Téléportation Aléatoire Sécurisé.
 */
public class RandomSpawnEngine implements Listener, CommandExecutor {

    private final AetherVisualsPlugin plugin;
    private final Random random = new Random();

    public static final int MIN_RADIUS = 500;
    public static final int MAX_RADIUS = 2500;
    public static final long COOLDOWN_MILLIS = 45 * 1000L;

    private final Map<UUID, Long> cooldowns = new ConcurrentHashMap<>();
    private final Set<UUID> castingRituals = ConcurrentHashMap.newKeySet();
    private final Set<String> spawnedPlayers = ConcurrentHashMap.newKeySet();

    public static final int STELE_AGORA_X = 12;
    public static final int STELE_AGORA_Y = 120;
    public static final int STELE_AGORA_Z = 0;

    public RandomSpawnEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onPlayerSpawnLocation(org.spigotmc.event.player.PlayerSpawnLocationEvent event) {
        Player player = event.getPlayer();
        if (player.hasPlayedBefore() || (plugin.getPlayerLocationEngine() != null
                && plugin.getPlayerLocationEngine().hasSavedSurvivalLocation(player.getUniqueId()))) {
            return;
        }
        World world = Bukkit.getWorld("world");
        if (world != null) {
            event.setSpawnLocation(new Location(world, 0.5, 121.0, 0.5, 0f, 0f));
        }
    }

    @EventHandler(priority = EventPriority.HIGH)
    public void onPlayerJoin(PlayerJoinEvent event) {}

    @EventHandler(priority = EventPriority.HIGH)
    public void onPlayerRespawn(PlayerRespawnEvent event) {
        if (event.isBedSpawn() || event.isAnchorSpawn()) return;
        World world = Bukkit.getWorld("world");
        if (world == null && !Bukkit.getWorlds().isEmpty()) {
            world = Bukkit.getWorlds().get(0);
        }
        if (world != null) {
            Location safeLoc = allocateSafeSurvivalSpawn(world);
            if (safeLoc != null) {
                event.setRespawnLocation(safeLoc);
            }
        }

        Player player = event.getPlayer();
        if (player.getBedSpawnLocation() != null || player.hasPlayedBefore()) {
            Bukkit.getScheduler().runTaskLater(plugin, () -> {
                if (player.isOnline()) {
                    player.sendMessage(ChatColor.GOLD + "✦ " + ChatColor.YELLOW + "Votre point de spawn ou lit était détruit/inaccessible : réapparition sur une zone sécurisée !");
                    player.playSound(player.getLocation(), Sound.BLOCK_NOTE_BLOCK_BELL, 0.8f, 1.2f);
                }
            }, 5L);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onPlayerTeleport(PlayerTeleportEvent event) {
        Location to = event.getTo();
        if (to == null || to.getWorld() == null) return;
        if (!to.getWorld().getName().equalsIgnoreCase("world")) return;

        // Prévention du sur-empilement si téléporté vers le point d'arrivée fixe de l'esplanade (640.5, y, 864.5 ou 868.5)
        if (Math.abs(to.getX() - 640.5) < 0.6 && (Math.abs(to.getZ() - 864.5) < 0.6 || Math.abs(to.getZ() - 868.5) < 0.6)) {
            Location safe = allocateSafeSurvivalSpawn(to.getWorld());
            if (safe != null) {
                event.setTo(safe);
            }
        }
    }

    public static Location allocateSafeSurvivalSpawn(World world) {
        if (world == null) {
            world = Bukkit.getWorld("world");
            if (world == null && !Bukkit.getWorlds().isEmpty()) {
                world = Bukkit.getWorlds().get(0);
            }
        }
        if (world == null) return null;

        int cx = PortalTeleportEngine.PORTAL2_X; // 640
        int cz = PortalTeleportEngine.PORTAL2_Z; // 864
        int groundY = CelestialSpawnBuilder.getSafeGroundY(world, cx, cz);

        Random rnd = new Random();
        Location fallback = null;

        // Tente de trouver une coordonnée sûre sur l'esplanade sans sur-empilement (dx, dz != 0)
        for (int attempt = 0; attempt < 30; attempt++) {
            int ox = rnd.nextInt(7) - 3; // -3 à +3
            int oz = rnd.nextInt(7) - 3; // -3 à +3
            if (ox == 0 && oz == 0) continue; // Jamais sur le point exact central (640.5, 72.0, 864.5)

            int targetX = cx + ox;
            int targetZ = cz + oz;
            int y = CelestialSpawnBuilder.getSafeGroundY(world, targetX, targetZ);

            Block ground = world.getBlockAt(targetX, y, targetZ);
            Block head1 = world.getBlockAt(targetX, y + 1, targetZ);
            Block head2 = world.getBlockAt(targetX, y + 2, targetZ);

            if (ground.getType().isSolid() && head1.isPassable() && head2.isPassable()
                    && !head1.isLiquid() && !head2.isLiquid()) {
                Location candidate = new Location(world, targetX + 0.5, y + 1.0, targetZ + 0.5, 180f, 0f);
                if (fallback == null) fallback = candidate;

                // Anti-stacking : aucun joueur à moins de 0.8 blocs
                if (world.getNearbyEntities(candidate, 0.8, 1.5, 0.8).isEmpty()) {
                    return candidate;
                }
            }
        }

        if (fallback != null) return fallback;
        return new Location(world, cx + 1.5, groundY + 1.0, cz + 1.5, 180f, 0f);
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage(ChatColor.RED + "Seul un joueur en jeu peut exécuter le rituel RTP.");
            return true;
        }
        startRtpRitual(player);
        return true;
    }

    public void startRtpRitual(Player player) {
        UUID uid = player.getUniqueId();
        if (castingRituals.contains(uid)) {
            player.sendMessage(ChatColor.RED + "⚠️ Un rituel de téléportation est déjà en cours d'incantation !");
            return;
        }
        long now = System.currentTimeMillis();
        Long lastTime = cooldowns.get(uid);
        if (lastTime != null && (now - lastTime) < COOLDOWN_MILLIS && !player.isOp()) {
            long remainingSec = (COOLDOWN_MILLIS - (now - lastTime)) / 1000L;
            player.sendMessage(ChatColor.RED + "⏳ Le Vortex d'Éther recharge son énergie... Veuillez attendre " + ChatColor.YELLOW + remainingSec + " secondes.");
            player.playSound(player.getLocation(), Sound.BLOCK_FIRE_EXTINGUISH, 0.7f, 1.5f);
            return;
        }

        castingRituals.add(uid);
        Location startLoc = player.getLocation().clone();
        player.sendTitle(ChatColor.AQUA + "🌀 Vortex", ChatColor.GRAY + "Incantation en cours (3s)", 5, 40, 10);
        player.playSound(startLoc, Sound.BLOCK_PORTAL_TRIGGER, 0.7f, 0.9f);
        player.sendMessage(ChatColor.DARK_AQUA + "✦ " + ChatColor.AQUA + "Canalisation de l'énergie... Restez immobile.");

        new BukkitRunnable() {
            int ticks = 0;
            @Override
            public void run() {
                if (!player.isOnline()) {
                    castingRituals.remove(uid);
                    cancel();
                    return;
                }
                if (player.getLocation().distanceSquared(startLoc) > 1.2) {
                    player.sendMessage(ChatColor.RED + "❌ Incantation brisée !");
                    player.sendTitle(ChatColor.RED + "❌ Annulé", ChatColor.GRAY + "Mouvement détecté", 5, 25, 10);
                    player.playSound(player.getLocation(), Sound.ENTITY_ENDERMAN_TELEPORT, 0.8f, 0.5f);
                    castingRituals.remove(uid);
                    cancel();
                    return;
                }
                double angle = ticks * 0.4;
                double x = Math.cos(angle), z = Math.sin(angle), y = (ticks % 20) * 0.1;
                Location pLoc = player.getLocation().add(0, y, 0);
                player.getWorld().spawnParticle(Particle.PORTAL, pLoc.clone().add(x, 0, z), 5, 0.05, 0.05, 0.05, 0.02);
                player.getWorld().spawnParticle(Particle.REVERSE_PORTAL, pLoc.clone().add(-x, 0, -z), 5, 0.05, 0.05, 0.05, 0.02);
                if (ticks % 10 == 0) {
                    player.playSound(player.getLocation(), Sound.BLOCK_NOTE_BLOCK_CHIME, 0.8f, 1.0f + (ticks * 0.015f));
                }
                ticks += 2;
                if (ticks >= 30) {
                    castingRituals.remove(uid);
                    cooldowns.put(uid, System.currentTimeMillis());
                    cancel();
                    player.sendMessage(ChatColor.GREEN + "⚡ Déchirure de l'espace achevée ! Téléportation vers une contrée vierge...");
                    player.playSound(player.getLocation(), Sound.ENTITY_ILLUSIONER_MIRROR_MOVE, 1.0f, 1.2f);
                    teleportRandomGround(player, 0, "Rituel RTP");
                }
            }
        }.runTaskTimer(plugin, 0L, 2L);
    }

    public void teleportRandomGround(Player player, int attempt, String reason) {
        if (!player.isOnline()) return;
        if (attempt >= 8) {
            player.teleportAsync(new Location(Bukkit.getWorld("world"), 640.5, 72.0, 864.5));
            player.sendMessage(ChatColor.YELLOW + "🌱 Atterrissage de secours au Domaine Terrestre (Spawn Survie).");
            return;
        }
        World world = Bukkit.getWorld("world");
        if (world == null) world = Bukkit.getWorlds().isEmpty() ? null : Bukkit.getWorlds().get(0);
        if (world == null) return;

        double angle = random.nextDouble() * 2 * Math.PI;
        double distance = MIN_RADIUS + (random.nextDouble() * (MAX_RADIUS - MIN_RADIUS));
        int targetX = (int) (Math.cos(angle) * distance);
        int targetZ = (int) (Math.sin(angle) * distance);
        int chunkX = targetX >> 4, chunkZ = targetZ >> 4;
        final World fWorld = world;

        fWorld.getChunkAtAsync(chunkX, chunkZ).thenAccept(chunk -> {
            for (int dx = -1; dx <= 1; dx++) {
                for (int dz = -1; dz <= 1; dz++) {
                    if (dx != 0 || dz != 0) fWorld.getChunkAtAsync(chunkX + dx, chunkZ + dz);
                }
            }
            Bukkit.getScheduler().runTask(plugin, () -> {
                if (!player.isOnline()) return;
                Block validGround = findValidDirtBlockInChunk(chunk, targetX, targetZ);
                if (validGround != null) {
                    completeGroundLanding(player, fWorld, validGround);
                } else {
                    teleportRandomGround(player, attempt + 1, reason);
                }
            });
        });
    }

    private void completeGroundLanding(Player player, World fWorld, Block validGround) {
        Location targetLoc = validGround.getLocation().add(0.5, 1.05, 0.5);
        player.setVelocity(new org.bukkit.util.Vector(0, 0, 0));
        player.setFallDistance(0.0f);
        player.teleport(targetLoc, org.bukkit.event.player.PlayerTeleportEvent.TeleportCause.PLUGIN);
        spawnedPlayers.add(player.getName());
        player.playSound(targetLoc, Sound.ENTITY_PLAYER_TELEPORT, 1.0f, 1.2f);
        player.playSound(targetLoc, Sound.BLOCK_GRASS_STEP, 1.0f, 0.8f);
        fWorld.spawnParticle(Particle.HAPPY_VILLAGER, targetLoc, 35, 0.6, 0.8, 0.6, 0.1);
        fWorld.spawnParticle(Particle.COMPOSTER, targetLoc, 25, 0.5, 0.3, 0.5, 0.05);
        player.addPotionEffect(new PotionEffect(PotionEffectType.RESISTANCE, 20 * 15, 2, false, false, true));
        player.addPotionEffect(new PotionEffect(PotionEffectType.REGENERATION, 20 * 15, 1, false, false, true));
        player.addPotionEffect(new PotionEffect(PotionEffectType.SATURATION, 20 * 15, 0, false, false, true));
        player.sendTitle(ChatColor.GOLD + "✦ Terre Vierge", ChatColor.GRAY + "Position validée", 8, 35, 12);
        player.sendMessage(ChatColor.DARK_GREEN + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        player.sendMessage(ChatColor.GREEN + "🌱 " + ChatColor.WHITE + "Bienvenue en Survie !");
        player.sendMessage(ChatColor.GRAY + "📌 " + ChatColor.AQUA + targetLoc.getBlockX() + ", " + targetLoc.getBlockY() + ", " + targetLoc.getBlockZ()
                + ChatColor.DARK_GRAY + " (" + validGround.getType().name() + ")");
        player.sendMessage(ChatColor.YELLOW + "🛡️ Protection active (15s)");
        player.sendMessage(ChatColor.DARK_GREEN + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    }

    private Block findValidDirtBlockInChunk(Chunk chunk, int preferredX, int preferredZ) {
        World world = chunk.getWorld();
        Block candidate = testDirtAt(world, preferredX, preferredZ);
        if (candidate != null) return candidate;
        int baseBlockX = chunk.getX() << 4, baseBlockZ = chunk.getZ() << 4;
        int[] offsets = {2, 5, 8, 11, 14};
        for (int ox : offsets) {
            for (int oz : offsets) {
                Block b = testDirtAt(world, baseBlockX + ox, baseBlockZ + oz);
                if (b != null) return b;
            }
        }
        return null;
    }

    private Block testDirtAt(World world, int x, int z) {
        int highestY = world.getHighestBlockYAt(x, z, HeightMap.MOTION_BLOCKING_NO_LEAVES);
        if (highestY < 55 || highestY > 140) return null;
        Block ground = world.getBlockAt(x, highestY - 1, z);
        if (isDirtMaterial(ground.getType())) {
            Block head1 = world.getBlockAt(x, highestY, z);
            Block head2 = world.getBlockAt(x, highestY + 1, z);
            if (head1.isPassable() && head2.isPassable() && !head1.isLiquid() && !head2.isLiquid()) {
                return ground;
            }
        }
        return null;
    }

    private boolean isDirtMaterial(Material mat) {
        return mat == Material.GRASS_BLOCK || mat == Material.DIRT || mat == Material.COARSE_DIRT
                || mat == Material.ROOTED_DIRT || mat == Material.PODZOL || mat == Material.MUD
                || mat == Material.MUDDY_MANGROVE_ROOTS;
    }

    public static void buildRtpStele(World world, int cx, int cy, int cz) {
        if (world == null) return;
        world.getBlockAt(cx, cy + 1, cz).setType(Material.CRYING_OBSIDIAN);
        world.getBlockAt(cx, cy + 2, cz).setType(Material.AMETHYST_CLUSTER);
        world.getBlockAt(cx, cy + 3, cz).setType(Material.SEA_LANTERN);
        world.getBlockAt(cx, cy + 1, cz + 1).setType(Material.POLISHED_BLACKSTONE_PRESSURE_PLATE);
        world.getBlockAt(cx, cy + 1, cz - 1).setType(Material.POLISHED_BLACKSTONE_PRESSURE_PLATE);
    }

    @EventHandler
    public void onPlayerInteract(PlayerInteractEvent event) {
        if (event.getAction() != Action.PHYSICAL && event.getAction() != Action.RIGHT_CLICK_BLOCK) return;
        Block clicked = event.getClickedBlock();
        if (clicked == null) return;
        if (Math.abs(clicked.getX() - STELE_AGORA_X) <= 1
                && Math.abs(clicked.getY() - STELE_AGORA_Y) <= 3
                && Math.abs(clicked.getZ() - STELE_AGORA_Z) <= 1) {
            startRtpRitual(event.getPlayer());
        }
    }
}
