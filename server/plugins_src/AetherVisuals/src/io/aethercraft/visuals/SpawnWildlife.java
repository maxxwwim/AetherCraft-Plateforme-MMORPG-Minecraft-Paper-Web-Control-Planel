package io.aethercraft.visuals;

import org.bukkit.DyeColor;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.entity.Axolotl;
import org.bukkit.entity.Cat;
import org.bukkit.entity.Entity;
import org.bukkit.entity.EntityType;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Parrot;
import org.bukkit.entity.Rabbit;
import org.bukkit.entity.TropicalFish;
import org.bukkit.event.entity.CreatureSpawnEvent;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.function.Consumer;

/**
 * Faune ambiante de l'Agora : perroquets, abeilles, allays, chats, lapins, poissons tropicaux, axolotls.
 * Toutes les creatures sont invulnerables, non persistantes, taguees et ramenees a leur point d'attache
 * si elles s'eloignent de l'ile.
 */
public class SpawnWildlife {

    public static final String TAG = "aether_spawn_life";
    private static final double MAX_RADIUS = 19.0;
    private static final double MIN_Y = 117.0;
    private static final double MAX_Y = 150.0;

    private static final class Slot {
        final EntityType type;
        final Location home;
        final Consumer<Entity> init;
        Entity ref;

        Slot(EntityType type, Location home, Consumer<Entity> init) {
            this.type = type;
            this.home = home;
            this.init = init;
        }
    }

    private final List<Slot> slots = new ArrayList<>();
    private final Random rnd = new Random();

    public void populate(World w) {
        clear();
        addParrots(w);
        addGardenFauna(w);
        addPondFauna(w);
        for (Slot s : slots) {
            spawnSlot(w, s);
        }
    }

    private void addParrots(World w) {
        Parrot.Variant[] variants = Parrot.Variant.values();
        for (int i = 0; i < 4; i++) {
            final Parrot.Variant v = variants[i % variants.length];
            double a = Math.PI / 2 * i;
            add(w, EntityType.PARROT, 0.5 + 6 * Math.cos(a), 125.0, 0.5 + 6 * Math.sin(a), e -> ((Parrot) e).setVariant(v));
        }
    }

    private void addGardenFauna(World w) {
        double cx = SpawnGardenBuilder.CHERRY[0] + 0.5, cz = SpawnGardenBuilder.CHERRY[1] + 0.5;
        double mx = SpawnGardenBuilder.MEADOW[0] + 0.5, mz = SpawnGardenBuilder.MEADOW[1] + 0.5;
        for (int i = 0; i < 3; i++) {
            add(w, EntityType.BEE, cx - 1 + i, 123.0, cz + 1, e -> { });
        }
        add(w, EntityType.ALLAY, mx, 123.5, mz - 1, e -> { });
        add(w, EntityType.ALLAY, mx, 123.5, mz + 1, e -> { });
        add(w, EntityType.RABBIT, cx, 121.0, cz + 2, e -> ((Rabbit) e).setRabbitType(Rabbit.Type.BROWN));
        add(w, EntityType.RABBIT, cx + 1, 121.0, cz, e -> ((Rabbit) e).setRabbitType(Rabbit.Type.WHITE));
        add(w, EntityType.RABBIT, mx + 3, 121.0, mz, e -> ((Rabbit) e).setRabbitType(Rabbit.Type.GOLD));
        add(w, EntityType.RABBIT, mx - 3, 121.0, mz + 1, e -> ((Rabbit) e).setRabbitType(Rabbit.Type.BLACK_AND_WHITE));
        add(w, EntityType.CAT, cx - 1, 121.5, cz + 3, e -> sit((Cat) e, Cat.Type.CALICO));
        add(w, EntityType.CAT, mx - 1, 121.5, mz, e -> sit((Cat) e, Cat.Type.TABBY));
    }

    private void addPondFauna(World w) {
        double px = SpawnGardenBuilder.POND[0] + 0.5, pz = SpawnGardenBuilder.POND[1] + 0.5;
        TropicalFish.Pattern[] patterns = TropicalFish.Pattern.values();
        DyeColor[] colors = DyeColor.values();
        for (int i = 0; i < 5; i++) {
            double a = Math.toRadians(72 * i);
            add(w, EntityType.TROPICAL_FISH, px + 2 * Math.cos(a), 119.5, pz + 2 * Math.sin(a), e -> {
                TropicalFish f = (TropicalFish) e;
                f.setPattern(patterns[rnd.nextInt(patterns.length)]);
                f.setBodyColor(colors[rnd.nextInt(colors.length)]);
                f.setPatternColor(colors[rnd.nextInt(colors.length)]);
            });
        }
        Axolotl.Variant[] variants = Axolotl.Variant.values();
        for (int i = 0; i < 2; i++) {
            final Axolotl.Variant v = variants[rnd.nextInt(variants.length)];
            add(w, EntityType.AXOLOTL, px - 2.5 + 5 * i, 119.3, pz + (i == 0 ? 0.5 : -0.5), e -> ((Axolotl) e).setVariant(v));
        }
    }

    private static void sit(Cat cat, Cat.Type type) {
        cat.setCatType(type);
        cat.setAI(false);
        cat.setSitting(true);
    }

    private void add(World w, EntityType type, double x, double y, double z, Consumer<Entity> init) {
        slots.add(new Slot(type, new Location(w, x, y, z), init));
    }

    private void spawnSlot(World w, Slot s) {
        if (!w.isChunkLoaded(s.home.getBlockX() >> 4, s.home.getBlockZ() >> 4)) return;
        Entity e = w.spawnEntity(s.home, s.type, CreatureSpawnEvent.SpawnReason.CUSTOM);
        e.addScoreboardTag(TAG);
        e.setInvulnerable(true);
        e.setPersistent(false);
        if (e instanceof LivingEntity le) {
            le.setRemoveWhenFarAway(false);
            le.setCanPickupItems(false);
        }
        s.init.accept(e);
        s.ref = e;
    }

    public void tick(long tick, World w) {
        if (w == null || tick % 20 != 0 || !SpawnAtmosphere.playersNearby(w, 64)) return;
        boolean revive = tick % 600 == 0;
        for (Slot s : slots) {
            if (s.ref == null || !s.ref.isValid()) {
                if (revive) spawnSlot(w, s);
                continue;
            }
            Location l = s.ref.getLocation();
            double dx = l.getX() - 0.5, dz = l.getZ() - 0.5;
            if (dx * dx + dz * dz > MAX_RADIUS * MAX_RADIUS || l.getY() < MIN_Y || l.getY() > MAX_Y) {
                s.ref.teleport(s.home);
            }
        }
    }

    public void clear() {
        for (Slot s : slots) {
            if (s.ref != null && s.ref.isValid()) {
                s.ref.remove();
            }
        }
        slots.clear();
    }
}
