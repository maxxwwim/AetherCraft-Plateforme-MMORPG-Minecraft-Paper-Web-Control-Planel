package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.boss.BarColor;
import org.bukkit.boss.BarStyle;
import org.bukkit.boss.BossBar;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Mob;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.scheduler.BukkitTask;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Moteur d'Expédition Donjon par Vagues Évolutives (Dungeon Wave Engine).
 */
public class DungeonWaveEngine implements Listener {

    public static final int ARENA_X = 2000;
    public static final int ARENA_Y = 280; // Haut dans la stratosphère céleste (sous la limite Y=320)
    public static final int ARENA_Z = 2000;

    public enum DungeonState { IDLE, STARTING, IN_WAVE, WAVE_CLEARED, VICTORY }

    private final AetherVisualsPlugin plugin;
    private final Set<UUID> playersInDungeon = ConcurrentHashMap.newKeySet();
    private final Set<LivingEntity> activeMonsters = Collections.synchronizedSet(new HashSet<>());
    private final Map<UUID, Location> launchLocations = new ConcurrentHashMap<>();

    private DungeonState state = DungeonState.IDLE;
    private int currentWave = 0;
    private int totalWaveMonsters = 0;
    private final BossBar bossBar;
    private BukkitTask waveCountdownTask;
    private BukkitTask mobSpellTickerTask;
    private boolean titanReinforcementsSpawned = false;

    public DungeonWaveEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
        this.bossBar = Bukkit.createBossBar(ChatColor.GOLD + "⚔️ SANCTUAIRE DE L'AETHERITE", BarColor.GREEN, BarStyle.SEGMENTED_6);
        this.bossBar.setVisible(false);
    }

    public Location getArenaSpawn(World world) {
        return new Location(world, ARENA_X + 0.5, ARENA_Y + 1.0, ARENA_Z - 10.5, 0f, 0f);
    }

    public Location getAgoraReturn(World world) {
        return new Location(world, 0.5, 121.0, 1.5, 0f, 0f);
    }

    public void buildArena(World world) {
        DungeonWaveSpawner.buildArena(plugin, world);
    }

    public boolean hasDungeonBypass(Player player) {
        if (player.isOp()) return true;
        if (player.hasPermission("aether.dungeon.unlimited")) return true;
        if (player.hasPermission("aether.vip") || player.hasPermission("aether.champion")) return true;
        try (java.sql.Connection conn = AetherDatabase.getConnection();
             java.sql.PreparedStatement ps = conn.prepareStatement("SELECT rank FROM players WHERE LOWER(username) = LOWER(?)")) {
            ps.setString(1, player.getName());
            try (java.sql.ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    String r = rs.getString("rank");
                    if (r != null) {
                        String rUp = r.toUpperCase();
                        if (rUp.equals("VIP") || rUp.equals("CHAMPION") || rUp.equals("CREATEUR")) {
                            return true;
                        }
                    }
                }
            }
        } catch (Throwable ignored) {}
        return false;
    }

    public static boolean isDungeonKey(ItemStack item) {
        if (item == null || item.getType() == Material.AIR) return false;
        if (item.hasItemMeta()) {
            ItemMeta meta = item.getItemMeta();
            if (meta.hasCustomModelData() && meta.getCustomModelData() == 2003) return true;
            if (meta.hasDisplayName()) {
                String name = ChatColor.stripColor(meta.getDisplayName());
                if (name.contains("Pass des Donjons") || name.contains("Clé de Donjon") || name.contains("Cle de Donjon") || name.contains("DungeonPass")) {
                    return true;
                }
            }
        }
        return false;
    }

    public static boolean consumeDungeonKey(Player player) {
        for (int i = 0; i < player.getInventory().getSize(); i++) {
            ItemStack item = player.getInventory().getItem(i);
            if (isDungeonKey(item)) {
                if (item.getAmount() > 1) {
                    item.setAmount(item.getAmount() - 1);
                } else {
                    player.getInventory().setItem(i, null);
                }
                player.updateInventory();
                return true;
            }
        }
        return false;
    }

    public boolean joinDungeon(Player player) {
        if (plugin.getSpawnProtectionEngine() != null && plugin.getSpawnProtectionEngine().isProtectedZone(player.getLocation())) {
            player.sendMessage(ChatColor.RED + "⚔️ Impossible de lancer le donjon depuis le spawn d'arrivée ! Éloignez-vous de la zone protégée.");
            player.playSound(player.getLocation(), Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
            return false;
        }

        // Contrôle d'accès par Clé de Donjon (CustomModelData 2003 / Pass des Donjons) ou Bypass VIP/Champion (F15)
        if (!hasDungeonBypass(player)) {
            if (!consumeDungeonKey(player)) {
                player.sendMessage("§cVous devez posséder une Clé de Donjon (disponible en boutique) pour entrer !");
                player.playSound(player.getLocation(), Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
                return false;
            }
            player.sendMessage(ChatColor.GREEN + "🎫 Une Clé de Donjon a été consommée pour votre accès à l'arène.");
        } else {
            player.sendMessage(ChatColor.GOLD + "👑 Accès Donjon VIP / Privilégié (clé non consommée).");
        }

        World world = player.getWorld();

        // 1. Sauvegarde de la position de lancement pour le re-tp en cas de victoire ou défaite
        launchLocations.put(player.getUniqueId(), player.getLocation().clone());

        // 2. Préchargement des chunks de l'arène céleste pour éviter tout freeze ou chute
        int chunkX = ARENA_X >> 4;
        int chunkZ = ARENA_Z >> 4;
        for (int cx = chunkX - 1; cx <= chunkX + 1; cx++) {
            for (int cz = chunkZ - 1; cz <= chunkZ + 1; cz++) {
                if (!world.isChunkLoaded(cx, cz)) {
                    world.loadChunk(cx, cz, true);
                }
            }
        }

        // 3. Construction garantie de l'arène céleste dans le ciel si absente
        if (world.getBlockAt(ARENA_X, ARENA_Y, ARENA_Z).getType() != org.bukkit.Material.AMETHYST_BLOCK) {
            buildArena(world);
        }

        Location spawnLoc = getArenaSpawn(world);
        playersInDungeon.add(player.getUniqueId());
        bossBar.addPlayer(player);
        bossBar.setVisible(true);

        player.teleport(spawnLoc);
        player.playSound(spawnLoc, Sound.BLOCK_PORTAL_TRAVEL, 0.7f, 1.2f);
        player.sendTitle(ChatColor.DARK_RED + "⚔️ SANCTUAIRE DE L'AETHERITE", ChatColor.GOLD + "Arène Céleste ! 5 Vagues d'ennemis vous attendent.", 10, 60, 20);
        player.sendMessage(ChatColor.GOLD + "✦ BIENVENUE DANS L'ARÈNE CÉLESTE DU DONJON ! (/dungeon leave pour quitter)");

        if (state == DungeonState.IDLE) {
            state = DungeonState.STARTING;
            currentWave = 0;
            broadcastToDungeon(ChatColor.AQUA + "✦ Le rituel d'éveil a commencé... Début de la Vague 1 dans 5 secondes !");
            scheduleNextWave(world, 5);
        }
        return true;
    }

    public boolean leaveDungeon(Player player) {
        if (!playersInDungeon.remove(player.getUniqueId())) {
            player.sendMessage(ChatColor.RED + "Vous n'êtes pas dans le donjon.");
            return false;
        }
        bossBar.removePlayer(player);
        Location returnLoc = launchLocations.remove(player.getUniqueId());
        if (returnLoc == null || returnLoc.getWorld() == null) {
            returnLoc = getAgoraReturn(player.getWorld());
        }
        player.teleport(returnLoc);
        player.sendMessage(ChatColor.YELLOW + "✦ Vous avez quitté le Sanctuaire et retrouvé votre position d'origine.");
        if (playersInDungeon.isEmpty()) resetDungeon();
        return true;
    }

    public boolean isInDungeon(Player player) {
        return player != null && playersInDungeon.contains(player.getUniqueId());
    }

    public void ejectPlayerToSpawn(Player player) {
        if (player == null) return;
        playersInDungeon.remove(player.getUniqueId());
        launchLocations.remove(player.getUniqueId());
        bossBar.removePlayer(player);
        if (playersInDungeon.isEmpty()) resetDungeon();
    }

    private void scheduleNextWave(World world, int secondsDelay) {
        if (waveCountdownTask != null) waveCountdownTask.cancel();
        stopSpellTicker();
        state = DungeonState.WAVE_CLEARED;

        waveCountdownTask = Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (playersInDungeon.isEmpty()) { resetDungeon(); return; }
            currentWave++;
            if (currentWave <= 5) spawnWave(world, currentWave);
            else handleVictory(world);
        }, secondsDelay * 20L);
    }

    private void spawnWave(World world, int wave) {
        state = DungeonState.IN_WAVE;
        activeMonsters.clear();

        switch (wave) {
            case 1 -> {
                DungeonWaveSpawner.spawnWave1(world, activeMonsters, this::setInitialTarget);
                bossBar.setTitle(ChatColor.GREEN + "⚔️ VAGUE 1/5 : Rôdeurs & Meute Spectrale (" + activeMonsters.size() + " restants)");
                bossBar.setColor(BarColor.GREEN);
                broadcastTitle(ChatColor.GREEN + "⚔️ VAGUE 1 / 5", ChatColor.YELLOW + "Rôdeurs & Loups Spectraux à l'assaut...", Sound.ENTITY_ZOMBIE_AMBIENT);
            }
            case 2 -> {
                DungeonWaveSpawner.spawnWave2(world, activeMonsters, this::setInitialTarget);
                bossBar.setTitle(ChatColor.AQUA + "⚔️ VAGUE 2/5 : Garde d'Obsidienne & Sangliers (" + activeMonsters.size() + " restants)");
                bossBar.setColor(BarColor.BLUE);
                broadcastTitle(ChatColor.AQUA + "⚔️ VAGUE 2 / 5", ChatColor.YELLOW + "La Garde d'Obsidienne & les Sangliers chargent !", Sound.ENTITY_SKELETON_AMBIENT);
            }
            case 3 -> {
                DungeonWaveSpawner.spawnWave3(world, activeMonsters, this::setInitialTarget);
                bossBar.setTitle(ChatColor.GOLD + "🔥 VAGUE 3/5 : Berserkers & Molosses Ardents (" + activeMonsters.size() + " restants)");
                bossBar.setColor(BarColor.YELLOW);
                broadcastTitle(ChatColor.GOLD + "🔥 VAGUE 3 / 5", ChatColor.RED + "Le Brasier primordial déferle !", Sound.ENTITY_BLAZE_SHOOT);
            }
            case 4 -> {
                DungeonWaveSpawner.spawnWave4(world, activeMonsters, this::setInitialTarget);
                bossBar.setTitle(ChatColor.RED + "⚡ VAGUE 4/5 : Inquisition, Ours & Ravageur (" + activeMonsters.size() + " restants)");
                bossBar.setColor(BarColor.RED);
                broadcastTitle(ChatColor.RED + "⚡ VAGUE 4 / 5", ChatColor.DARK_RED + "Les Inquisiteurs & Bêtes Colossales attaquent !", Sound.ENTITY_VINDICATOR_CELEBRATE);
            }
            case 5 -> {
                titanReinforcementsSpawned = false;
                DungeonWaveSpawner.spawnBossTitan(world, activeMonsters, this::setInitialTarget);
                bossBar.setTitle(ChatColor.DARK_PURPLE + "💀 VAGUE FINALE : LE TITAN DE L'ÉTHER [BOSS]");
                bossBar.setColor(BarColor.PURPLE);
                broadcastTitle(ChatColor.DARK_PURPLE + "💀 VAGUE FINALE : LE TITAN", ChatColor.GOLD + "Terrassez le Titan pour libérer l'Archipel !", Sound.ENTITY_ENDER_DRAGON_GROWL);
            }
        }

        // Application des affixes procéduraux aléatoires (X1, X2, X3) aux monstres de donjon
        if (plugin.getMobAffixEngine() != null) {
            for (LivingEntity m : new ArrayList<>(activeMonsters)) {
                plugin.getMobAffixEngine().applyProceduralAffixes(m, wave * 2);
            }
        }

        totalWaveMonsters = activeMonsters.size();
        bossBar.setProgress(1.0);
        stopSpellTicker();
        mobSpellTickerTask = Bukkit.getScheduler().runTaskTimer(plugin, this::tickMobSpells, 30L, 40L);
    }

    private void setInitialTarget(LivingEntity entity) {
        if (entity instanceof Mob mob) {
            Player nearest = DungeonMobSpellCaster.getNearestDungeonPlayer(mob.getLocation(), playersInDungeon);
            if (nearest != null) mob.setTarget(nearest);
        }
    }

    private void stopSpellTicker() {
        if (mobSpellTickerTask != null) { mobSpellTickerTask.cancel(); mobSpellTickerTask = null; }
    }

    private void tickMobSpells() {
        if (state != DungeonState.IN_WAVE || playersInDungeon.isEmpty()) return;
        List<LivingEntity> mobs;
        synchronized (activeMonsters) { mobs = new ArrayList<>(activeMonsters); }
        for (LivingEntity mob : mobs) {
            if (mob == null || !mob.isValid() || mob.isDead()) { activeMonsters.remove(mob); continue; }
            Player target = DungeonMobSpellCaster.getNearestDungeonPlayer(mob.getLocation(), playersInDungeon);
            if (target == null) continue;
            if (mob instanceof Mob m && (m.getTarget() == null || !playersInDungeon.contains(m.getTarget().getUniqueId()))) {
                m.setTarget(target);
            }
            DungeonMobSpellCaster.triggerMobSpells(plugin, this, mob, target, playersInDungeon, activeMonsters, () -> {
                if (!titanReinforcementsSpawned) {
                    titanReinforcementsSpawned = true;
                    broadcastToDungeon(ChatColor.DARK_RED + "💀 LE TITAN RUGIT ET INVOQUE SA MEUTE TERRESTRE PRIMORDIALE !");
                    DungeonWaveSpawner.spawnTitanReinforcements(mob.getWorld(), mob.getLocation(), activeMonsters, this::setInitialTarget);
                    if (plugin.getMobAffixEngine() != null) {
                        for (LivingEntity m : new ArrayList<>(activeMonsters)) {
                            if (!plugin.getMobAffixEngine().isAffixed(m)) {
                                plugin.getMobAffixEngine().applyProceduralAffixes(m, 10);
                            }
                        }
                    }
                    totalWaveMonsters += 4;
                    bossBar.setTitle(ChatColor.DARK_PURPLE + "💀 TITAN DE L'ÉTHER & RENFORTS (" + activeMonsters.size() + " cibles)");
                }
            });
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onEntityDeath(EntityDeathEvent event) {
        LivingEntity entity = event.getEntity();
        if (!activeMonsters.remove(entity)) return;

        int remaining = activeMonsters.size();
        if (totalWaveMonsters > 0) bossBar.setProgress(Math.max(0.0, (double) remaining / (double) totalWaveMonsters));
        bossBar.setTitle(currentWave < 5
                ? ChatColor.YELLOW + "⚔️ VAGUE " + currentWave + "/5 (" + remaining + " créatures restantes)"
                : ChatColor.DARK_PURPLE + "💀 TITAN DE L'ÉTHER - PV: " + remaining + " Cibles");

        if (remaining == 0) {
            if (currentWave < 5) {
                broadcastTitle(ChatColor.GREEN + "✦ VAGUE " + currentWave + " NETTOYÉE ! ✦", ChatColor.YELLOW + "Prochaine vague dans 5 secondes...", Sound.ENTITY_PLAYER_LEVELUP);
                for (UUID uid : playersInDungeon) {
                    Player p = Bukkit.getPlayer(uid);
                    if (p != null) {
                        p.addPotionEffect(new PotionEffect(PotionEffectType.REGENERATION, 20 * 6, 1));
                        p.addPotionEffect(new PotionEffect(PotionEffectType.ABSORPTION, 20 * 60, 0));
                    }
                }
                scheduleNextWave(entity.getWorld(), 5);
            } else {
                handleVictory(entity.getWorld());
            }
        }
    }

    private void handleVictory(World world) {
        stopSpellTicker();
        state = DungeonState.VICTORY;
        bossBar.setTitle(ChatColor.GOLD + "👑 VICTOIRE ÉPIQUE : LE TITAN EST VAINCU !");
        bossBar.setColor(BarColor.YELLOW);
        bossBar.setProgress(1.0);

        broadcastTitle(ChatColor.GOLD + "👑 VICTOIRE LÉGENDAIRE !", ChatColor.YELLOW + "Le Sanctuaire a été purifié ! (+50 Minerais Célestes)", Sound.UI_TOAST_CHALLENGE_COMPLETE);
        DungeonMobSpellCaster.rewardDungeonVictory(world, playersInDungeon);
        Bukkit.broadcastMessage(ChatColor.GOLD + "⚔️ [DONJON D'ÉTHER] L'escouade héroïque a triomphé du Titan Primordial (+50 Minerais Célestes) !");

        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            for (UUID uid : new ArrayList<>(playersInDungeon)) {
                Player p = Bukkit.getPlayer(uid);
                if (p != null && p.isOnline()) {
                    Location returnLoc = launchLocations.remove(uid);
                    if (returnLoc == null || returnLoc.getWorld() == null) {
                        returnLoc = getAgoraReturn(world);
                    }
                    p.teleport(returnLoc);
                    p.sendMessage(ChatColor.GREEN + "✦ Téléportation retour à votre position de lancement effectuée !");
                }
            }
            resetDungeon();
        }, 10 * 20L);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onPlayerQuit(PlayerQuitEvent event) {
        Player player = event.getPlayer();
        if (playersInDungeon.contains(player.getUniqueId())) {
            Location returnLoc = launchLocations.remove(player.getUniqueId());
            if (returnLoc != null && returnLoc.getWorld() != null) {
                player.teleport(returnLoc);
            }
            leaveDungeon(player);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onPlayerDeath(PlayerDeathEvent event) {
        Player player = event.getEntity();
        if (playersInDungeon.remove(player.getUniqueId())) {
            bossBar.removePlayer(player);
            player.sendMessage(ChatColor.RED + "💀 Vous avez succombé dans le Sanctuaire de l'Aetherite...");
            if (playersInDungeon.isEmpty()) resetDungeon();
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onPlayerRespawn(org.bukkit.event.player.PlayerRespawnEvent event) {
        Player player = event.getPlayer();
        Location launchLoc = launchLocations.remove(player.getUniqueId());
        if (launchLoc != null && launchLoc.getWorld() != null) {
            event.setRespawnLocation(launchLoc);
            player.sendMessage(ChatColor.YELLOW + "✦ Réapparition à votre position de lancement de donjon.");
        }
    }

    public void resetDungeon() {
        stopSpellTicker();
        titanReinforcementsSpawned = false;
        if (waveCountdownTask != null) { waveCountdownTask.cancel(); waveCountdownTask = null; }
        for (LivingEntity entity : activeMonsters) { if (entity.isValid()) entity.remove(); }
        activeMonsters.clear();
        playersInDungeon.clear();
        bossBar.removeAll();
        bossBar.setVisible(false);
        state = DungeonState.IDLE;
        currentWave = 0;
    }

    private void broadcastToDungeon(String msg) {
        for (UUID uid : playersInDungeon) {
            Player p = Bukkit.getPlayer(uid);
            if (p != null) p.sendMessage(msg);
        }
    }

    private void broadcastTitle(String title, String subtitle, Sound sound) {
        for (UUID uid : playersInDungeon) {
            Player p = Bukkit.getPlayer(uid);
            if (p != null) {
                p.sendTitle(title, subtitle, 10, 50, 15);
                if (sound != null) p.playSound(p.getLocation(), sound, 1.0f, 1.0f);
            }
        }
    }

    public DungeonState getState() { return state; }
    public int getCurrentWave() { return currentWave; }
}
