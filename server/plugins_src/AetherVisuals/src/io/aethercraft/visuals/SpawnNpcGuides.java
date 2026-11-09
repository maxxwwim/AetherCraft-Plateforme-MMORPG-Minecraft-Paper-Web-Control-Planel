package io.aethercraft.visuals;

import org.bukkit.ChatColor;
import org.bukkit.Location;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.entity.Entity;
import org.bukkit.entity.EntityType;
import org.bukkit.entity.Player;
import org.bukkit.entity.Villager;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.CreatureSpawnEvent;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.inventory.EquipmentSlot;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * PNJ guides de l'Agora : un villageois fige, invulnerable et silencieux par station.
 * Il suit du regard le joueur le plus proche et dialogue au clic droit (le menu d'echange est desactive).
 */
public class SpawnNpcGuides implements Listener {

    public static final String TAG = "aether_spawn_npc";
    private static final double LOOK_RANGE = 7.0;
    private static final long CLICK_COOLDOWN_MS = 1200L;

    private static final class Npc {
        final String name;
        final Villager.Profession job;
        final double x;
        final double z;
        final float homeYaw;
        final String[] lines;
        Villager ref;
        float lastYaw;

        Npc(String name, Villager.Profession job, double x, double z, float homeYaw, String... lines) {
            this.name = name;
            this.job = job;
            this.x = x;
            this.z = z;
            this.homeYaw = homeYaw;
            this.lines = lines;
            this.lastYaw = homeYaw;
        }
    }

    private final AetherVisualsPlugin plugin;
    private final List<Npc> npcs = new ArrayList<>();
    private final Map<UUID, Long> lastClick = new HashMap<>();

    private static AetherVisualsPlugin resolvePlugin() {
        try {
            return AetherVisualsPlugin.getPlugin(AetherVisualsPlugin.class);
        } catch (Throwable t) {
            try {
                return (AetherVisualsPlugin) org.bukkit.Bukkit.getPluginManager().getPlugin("AetherVisuals");
            } catch (Throwable ignored) {
                return null;
            }
        }
    }

    public SpawnNpcGuides() {
        this(resolvePlugin());
    }

    public SpawnNpcGuides(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
        npcs.add(new Npc("Gardienne de l'Agora", Villager.Profession.LIBRARIAN, 3.5, 3.5, 135f,
            "%g %p ! Bienvenue sur l'Agora Céleste.",
            "Ouvre ton /menu pour tout retrouver : profil, boutique, quêtes.",
            "Les pads lumineux autour de la balise te propulsent dans les airs, essaie !",
            "Un quiz éclair surgit régulièrement : réponds vite dans le chat pour gagner des jetons."));
        npcs.add(new Npc("Maître des Quêtes", Villager.Profession.CLERIC, 4.5, -13.5, 45f,
            "%g ! L'autel du Champion veille sur les plus braves.",
            "/quests : tes quêtes du jour et leurs récompenses en Pièces.",
            "/succes : la liste de tes succès débloqués."));
        npcs.add(new Npc("Guide du Portail Survie", Villager.Profession.WEAPONSMITH, 4.5, 13.5, 135f,
            "%g %p ! Le vortex au sud mène directement au Monde Survie.",
            "Franchis le portail ou tape /survie pour explorer les terres vierges.",
            "Pour affronter le Sanctuaire des Donjons, tape plutôt /donjon."));
        npcs.add(new Npc("Gardien des Âmes", Villager.Profession.CLERIC, -4.5, 13.5, 225f,
            "%g %p. Je purifie les liens d'ancrage et réinitialise ton point de spawn survie.",
            "Un simple clic sur moi efface ton lit et ta position de reprise en survie.",
            "Tes inventaires et ta progression restent totalement intacts !"));
        npcs.add(new Npc("Marchande des Minerais", Villager.Profession.TOOLSMITH, -12.5, -1.5, -90f,
            "%g ! Mes étals sont ouverts à tous.",
            "/marche ou /ah : hôtel des ventes et troc entre joueurs."));
        npcs.add(new Npc("Banquier d'Éther", Villager.Profession.CARTOGRAPHER, -10.5, -7.5, 0f,
            "%g %p ! Bienvenue au Guichet de la Banque d'Aether (Style Dofus).",
            "Ici, vos Kamas (⛃) et ressources sont en sécurité absolue.",
            "Accès gratuit et coffre personnel illimité garanti !"));
        npcs.add(new Npc("Éleveuse du Sanctuaire", Villager.Profession.SHEPHERD, 14.5, 4.5, 180f,
            "Les compagnons voxel adorent les cerisiers du sanctuaire.",
            "/pet : gère tes compagnons. /cosmetics : ailes et auras."));
        npcs.add(new Npc("Guide des Terres Sauvages", Villager.Profession.LEATHERWORKER, 10.5, -2.5, -90f,
            "La stèle à l'est te téléporte au hasard en survie : /rtp.",
            "/survie t'emmène à l'esplanade survie. Reviens avec /spawn ou /agora."));
    }

    public void populate(World w) {
        clear();
        for (Npc n : npcs) {
            spawn(w, n);
        }
    }

    private void spawn(World w, Npc n) {
        if (!w.isChunkLoaded((int) n.x >> 4, (int) n.z >> 4)) return;
        Location loc = new Location(w, n.x, 121.0, n.z, n.homeYaw, 0f);
        Villager v = (Villager) w.spawnEntity(loc, EntityType.VILLAGER, CreatureSpawnEvent.SpawnReason.CUSTOM);
        v.setAI(false);
        v.setSilent(true);
        v.setInvulnerable(true);
        v.setPersistent(false);
        v.setRemoveWhenFarAway(false);
        v.setCollidable(false);
        v.setProfession(n.job);
        v.setVillagerType(Villager.Type.PLAINS);
        v.setVillagerLevel(5);
        v.setCustomName(ChatColor.GOLD + "✦ " + ChatColor.YELLOW + n.name);
        v.setCustomNameVisible(true);
        v.addScoreboardTag(TAG);
        v.setRotation(n.homeYaw, 0f);
        n.ref = v;
        n.lastYaw = n.homeYaw;
    }

    public void tick(long tick, World w) {
        if (w == null || tick % 4 != 0 || !SpawnAtmosphere.playersNearby(w, 64)) return;
        boolean revive = tick % 600 == 0;
        for (Npc n : npcs) {
            if (n.ref == null || !n.ref.isValid()) {
                if (revive) spawn(w, n);
                continue;
            }
            faceNearestPlayer(n);
        }
    }

    private void faceNearestPlayer(Npc n) {
        Location base = n.ref.getLocation();
        Player best = null;
        double bestD = LOOK_RANGE * LOOK_RANGE;
        for (Player p : base.getWorld().getPlayers()) {
            double d = p.getLocation().distanceSquared(base);
            if (d < bestD) {
                bestD = d;
                best = p;
            }
        }
        float yaw = n.homeYaw;
        float pitch = 0f;
        if (best != null) {
            Location eye = best.getEyeLocation();
            double dx = eye.getX() - base.getX();
            double dz = eye.getZ() - base.getZ();
            double dy = eye.getY() - (base.getY() + 1.62);
            yaw = (float) Math.toDegrees(Math.atan2(-dx, dz));
            pitch = (float) -Math.toDegrees(Math.atan2(dy, Math.sqrt(dx * dx + dz * dz)));
        }
        if (best != null || n.lastYaw != yaw) {
            n.ref.setRotation(yaw, pitch);
            n.lastYaw = yaw;
        }
    }

    @EventHandler(priority = EventPriority.HIGH)
    public void onInteract(PlayerInteractEntityEvent event) {
        Entity clicked = event.getRightClicked();
        if (!clicked.getScoreboardTags().contains(TAG)) return;
        event.setCancelled(true);
        if (event.getHand() != EquipmentSlot.HAND) return;
        Player p = event.getPlayer();
        long now = System.currentTimeMillis();
        Long last = lastClick.get(p.getUniqueId());
        if (last != null && now - last < CLICK_COOLDOWN_MS) return;
        for (Npc n : npcs) {
            if (n.ref != null && n.ref.getUniqueId().equals(clicked.getUniqueId())) {
                lastClick.put(p.getUniqueId(), now);
                speak(p, n);
                if (n.name.contains("Gardien des Âmes")) {
                    handleSpawnResetNpc(p, n);
                } else if (n.name.contains("Banquier")) {
                    AetherVisualsPlugin pl = this.plugin != null ? this.plugin : resolvePlugin();
                    if (pl != null && pl.getBankEngine() != null) {
                        pl.getBankEngine().openBank(p);
                    }
                }
                return;
            }
        }
    }

    private void handleSpawnResetNpc(Player p, Npc n) {
        p.setBedSpawnLocation(null, true);
        AetherVisualsPlugin pl = this.plugin != null ? this.plugin : resolvePlugin();
        if (pl != null && pl.getPlayerLocationEngine() != null) {
            pl.getPlayerLocationEngine().deleteSurvivalLocationAsync(p.getUniqueId());
        }
        Location at = (n.ref != null) ? n.ref.getLocation() : p.getLocation();
        p.playSound(at, Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.0f);
        p.spawnParticle(Particle.TOTEM_OF_UNDYING, at.clone().add(0, 1.2, 0), 35, 0.5, 0.5, 0.5, 0.1);
        p.sendMessage(ChatColor.GOLD + "✦ " + ChatColor.YELLOW + "Votre point de spawn et votre reprise en survie ont été réinitialisés avec succès !");
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        lastClick.remove(event.getPlayer().getUniqueId());
    }

    private void speak(Player p, Npc n) {
        long t = p.getWorld().getTime();
        String greet = t < 12000 ? "Bonjour" : "Bonsoir";
        String bar = ChatColor.DARK_GRAY + "━━━━━━━━━━━━━━━━━━━━━━";
        p.sendMessage(bar);
        p.sendMessage(ChatColor.GOLD + "✦ " + n.name + ChatColor.GRAY + " dit :");
        for (String line : n.lines) {
            p.sendMessage(ChatColor.WHITE + " " + line.replace("%g", greet).replace("%p", p.getName()));
        }
        p.sendMessage(bar);
        Location at = n.ref.getLocation();
        p.playSound(at, Sound.ENTITY_VILLAGER_YES, 0.9f, 1.1f);
        p.spawnParticle(Particle.HAPPY_VILLAGER, at.clone().add(0, 2.2, 0), 6, 0.3, 0.2, 0.3, 0);
    }

    public void clear() {
        for (Npc n : npcs) {
            if (n.ref != null && n.ref.isValid()) {
                n.ref.remove();
            }
            n.ref = null;
        }
    }
}
