package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.entity.Entity;
import org.bukkit.plugin.PluginManager;

/**
 * Chef d'orchestre du "Spawn Vivant" : jardins, faune, PNJ guides et ambiance de l'Agora Celeste.
 */
public class SpawnLifeManager {

    private final AetherVisualsPlugin plugin;
    private final SpawnWildlife wildlife = new SpawnWildlife();
    private final SpawnNpcGuides npcs = new SpawnNpcGuides();
    private final SpawnAtmosphere atmosphere = new SpawnAtmosphere();
    private World world;

    public SpawnLifeManager(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
    }

    public void register() {
        PluginManager pm = Bukkit.getPluginManager();
        pm.registerEvents(npcs, plugin);
        pm.registerEvents(atmosphere, plugin);
    }

    /** Construit (ou reconstruit) tout le spawn vivant. Idempotent. */
    public void build(World w) {
        if (w == null) return;
        this.world = w;
        sweepOrphans(w);
        SpawnGardenBuilder.buildAll(w);
        wildlife.populate(w);
        npcs.populate(w);
    }

    public void tick(long tick) {
        if (world == null) return;
        wildlife.tick(tick, world);
        npcs.tick(tick, world);
        atmosphere.tick(tick, world);
    }

    public void shutdown() {
        wildlife.clear();
        npcs.clear();
    }

    private void sweepOrphans(World w) {
        Location center = new Location(w, 0.5, 121.0, 0.5);
        for (Entity e : w.getNearbyEntities(center, 30, 40, 30)) {
            if (e.getScoreboardTags().contains(SpawnWildlife.TAG) || e.getScoreboardTags().contains(SpawnNpcGuides.TAG)) {
                e.remove();
            }
        }
    }
}
