package io.aethercraft.visuals;

import org.bukkit.ChatColor;
import org.bukkit.Color;
import org.bukkit.DyeColor;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.entity.EntityType;
import org.bukkit.entity.Hoglin;
import org.bukkit.entity.IronGolem;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.PolarBear;
import org.bukkit.entity.Ravager;
import org.bukkit.entity.Skeleton;
import org.bukkit.entity.Spider;
import org.bukkit.entity.Vindicator;
import org.bukkit.entity.Witch;
import org.bukkit.entity.WitherSkeleton;
import org.bukkit.entity.Wolf;
import org.bukkit.entity.Zombie;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.LeatherArmorMeta;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;

import java.util.Random;
import java.util.Set;
import java.util.function.Consumer;

import static io.aethercraft.visuals.DungeonWaveEngine.*;

/**
 * Constructeur d'arène et générateur de vagues de monstres pour DungeonWaveEngine.
 */
public class DungeonWaveSpawner {

    private static final Random random = new Random();

    public static void buildArena(AetherVisualsPlugin plugin, World world) {
        if (world == null) return;
        int radius = 15;
        for (int x = -radius; x <= radius; x++) {
            for (int z = -radius; z <= radius; z++) {
                int bx = ARENA_X + x;
                int bz = ARENA_Z + z;
                world.getBlockAt(bx, ARENA_Y, bz).setType((Math.abs(x) == radius || Math.abs(z) == radius) ? Material.CRYING_OBSIDIAN : Material.POLISHED_BASALT);
                if (x * x + z * z <= 16) {
                    world.getBlockAt(bx, ARENA_Y, bz).setType(Material.AMETHYST_BLOCK);
                }
                for (int y = 1; y <= 9; y++) {
                    world.getBlockAt(bx, ARENA_Y + y, bz).setType(Material.AIR);
                }
                if (Math.abs(x) == radius || Math.abs(z) == radius) {
                    for (int y = 1; y <= 6; y++) {
                        world.getBlockAt(bx, ARENA_Y + y, bz).setType(y == 6 ? Material.SEA_LANTERN : Material.DEEPSLATE_BRICKS);
                    }
                }
            }
        }
        int[] cornerOffsets = {-12, 12};
        for (int cx : cornerOffsets) {
            for (int cz : cornerOffsets) {
                int px = ARENA_X + cx;
                int pz = ARENA_Z + cz;
                for (int y = 1; y <= 4; y++) {
                    world.getBlockAt(px, ARENA_Y + y, pz).setType(Material.CHISELED_DEEPSLATE);
                }
                world.getBlockAt(px, ARENA_Y + 5, pz).setType(Material.SOUL_CAMPFIRE);
            }
        }
        plugin.getLogger().info("✦ Arène du Sanctuaire de l'Aetherite prête à (" + ARENA_X + ", " + ARENA_Y + ", " + ARENA_Z + ") !");
    }

    public static void spawnWave1(World world, Set<LivingEntity> activeMonsters, Consumer<LivingEntity> targeter) {
        for (int i = 0; i < 4; i++) {
            Zombie z = (Zombie) world.spawnEntity(getRandomSpawnPoint(world), EntityType.ZOMBIE);
            z.setCustomName(ChatColor.DARK_AQUA + "Rôdeur de l'Ombre");
            z.setCustomNameVisible(true);
            equipLeather(z, Color.NAVY);
            z.getEquipment().setItemInMainHand(new ItemStack(Material.IRON_SWORD));
            targeter.accept(z);
            activeMonsters.add(z);
        }
        for (int i = 0; i < 3; i++) {
            Wolf w = (Wolf) world.spawnEntity(getRandomSpawnPoint(world), EntityType.WOLF);
            w.setCustomName(ChatColor.DARK_PURPLE + "Loup Spectral de l'Ombre");
            w.setCustomNameVisible(true);
            w.setAngry(true);
            w.setCollarColor(DyeColor.PURPLE);
            w.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 20 * 180, 0));
            targeter.accept(w);
            activeMonsters.add(w);
        }
        // Créature 1.21 : Bourbier (Bogged) / Rôdeur des Marais
        for (int i = 0; i < 2; i++) {
            try {
                LivingEntity bogged = (LivingEntity) world.spawnEntity(getRandomSpawnPoint(world), EntityType.BOGGED);
                bogged.setCustomName(ChatColor.DARK_GREEN + "Bourbier Putride [Bogged 1.21]");
                bogged.setCustomNameVisible(true);
                targeter.accept(bogged);
                activeMonsters.add(bogged);
            } catch (Throwable t) {
                Skeleton st = (Skeleton) world.spawnEntity(getRandomSpawnPoint(world), EntityType.STRAY);
                st.setCustomName(ChatColor.AQUA + "Archer Givré [Stray]");
                st.setCustomNameVisible(true);
                targeter.accept(st);
                activeMonsters.add(st);
            }
        }
    }

    public static void spawnWave2(World world, Set<LivingEntity> activeMonsters, Consumer<LivingEntity> targeter) {
        for (int i = 0; i < 3; i++) {
            Skeleton s = (Skeleton) world.spawnEntity(getRandomSpawnPoint(world), EntityType.SKELETON);
            s.setCustomName(ChatColor.BLUE + "Archer Cristallin");
            s.setCustomNameVisible(true);
            s.getEquipment().setChestplate(new ItemStack(Material.CHAINMAIL_CHESTPLATE));
            s.getEquipment().setItemInMainHand(new ItemStack(Material.BOW));
            targeter.accept(s);
            activeMonsters.add(s);
        }
        for (int i = 0; i < 2; i++) {
            Zombie z = (Zombie) world.spawnEntity(getRandomSpawnPoint(world), EntityType.ZOMBIE);
            z.setCustomName(ChatColor.DARK_GREEN + "Garde Cuirassé");
            z.setCustomNameVisible(true);
            z.getEquipment().setHelmet(new ItemStack(Material.IRON_HELMET));
            z.getEquipment().setItemInMainHand(new ItemStack(Material.IRON_AXE));
            targeter.accept(z);
            activeMonsters.add(z);
        }
        for (int i = 0; i < 2; i++) {
            Hoglin h = (Hoglin) world.spawnEntity(getRandomSpawnPoint(world), EntityType.HOGLIN);
            h.setCustomName(ChatColor.GOLD + "Sanglier Primordial de Guerre");
            h.setCustomNameVisible(true);
            h.setImmuneToZombification(true);
            h.setIsAbleToBeHunted(false);
            targeter.accept(h);
            activeMonsters.add(h);
        }
        // Créature diversifiée : Vagabond des Glaces (Stray)
        for (int i = 0; i < 2; i++) {
            org.bukkit.entity.Stray stray = (org.bukkit.entity.Stray) world.spawnEntity(getRandomSpawnPoint(world), EntityType.STRAY);
            stray.setCustomName(ChatColor.AQUA + "Vagabond Glacial Astral [Stray]");
            stray.setCustomNameVisible(true);
            targeter.accept(stray);
            activeMonsters.add(stray);
        }
    }

    public static void spawnWave3(World world, Set<LivingEntity> activeMonsters, Consumer<LivingEntity> targeter) {
        for (int i = 0; i < 3; i++) {
            WitherSkeleton ws = (WitherSkeleton) world.spawnEntity(getRandomSpawnPoint(world), EntityType.WITHER_SKELETON);
            ws.setCustomName(ChatColor.RED + "Berserker du Brasier");
            ws.setCustomNameVisible(true);
            ws.getEquipment().setItemInMainHand(new ItemStack(Material.GOLDEN_SWORD));
            targeter.accept(ws);
            activeMonsters.add(ws);
        }
        for (int i = 0; i < 2; i++) {
            Spider sp = (Spider) world.spawnEntity(getRandomSpawnPoint(world), EntityType.SPIDER);
            sp.setCustomName(ChatColor.GOLD + "Tisseuse Astrale");
            sp.setCustomNameVisible(true);
            sp.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 20 * 180, 1));
            targeter.accept(sp);
            activeMonsters.add(sp);
        }
        for (int i = 0; i < 3; i++) {
            Wolf w = (Wolf) world.spawnEntity(getRandomSpawnPoint(world), EntityType.WOLF);
            w.setCustomName(ChatColor.RED + "Molosse Ardent de l'Abîme");
            w.setCustomNameVisible(true);
            w.setAngry(true);
            w.setCollarColor(DyeColor.RED);
            w.addPotionEffect(new PotionEffect(PotionEffectType.FIRE_RESISTANCE, 20 * 300, 0));
            w.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 20 * 180, 1));
            targeter.accept(w);
            activeMonsters.add(w);
        }
        // Créature aquatique hostile : Noyé Astral (Drowned avec Trident)
        for (int i = 0; i < 2; i++) {
            org.bukkit.entity.Drowned drowned = (org.bukkit.entity.Drowned) world.spawnEntity(getRandomSpawnPoint(world), EntityType.DROWNED);
            drowned.setCustomName(ChatColor.DARK_AQUA + "Noyé Foudroyant des Cieux [Drowned]");
            drowned.setCustomNameVisible(true);
            drowned.getEquipment().setItemInMainHand(new ItemStack(Material.TRIDENT));
            targeter.accept(drowned);
            activeMonsters.add(drowned);
        }
    }

    public static void spawnWave4(World world, Set<LivingEntity> activeMonsters, Consumer<LivingEntity> targeter) {
        for (int i = 0; i < 2; i++) {
            Vindicator v = (Vindicator) world.spawnEntity(getRandomSpawnPoint(world), EntityType.VINDICATOR);
            v.setCustomName(ChatColor.GOLD + "Inquisiteur Stellaire");
            v.setCustomNameVisible(true);
            v.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 20 * 180, 0));
            targeter.accept(v);
            activeMonsters.add(v);
        }
        for (int i = 0; i < 2; i++) {
            Witch w = (Witch) world.spawnEntity(getRandomSpawnPoint(world), EntityType.WITCH);
            w.setCustomName(ChatColor.LIGHT_PURPLE + "Sorcière de l'Abîme");
            w.setCustomNameVisible(true);
            targeter.accept(w);
            activeMonsters.add(w);
        }
        for (int i = 0; i < 2; i++) {
            PolarBear bear = (PolarBear) world.spawnEntity(getRandomSpawnPoint(world), EntityType.POLAR_BEAR);
            bear.setCustomName(ChatColor.AQUA + "Ours Céleste Furieux");
            bear.setCustomNameVisible(true);
            bear.addPotionEffect(new PotionEffect(PotionEffectType.STRENGTH, 20 * 180, 0));
            bear.addPotionEffect(new PotionEffect(PotionEffectType.RESISTANCE, 20 * 180, 0));
            targeter.accept(bear);
            activeMonsters.add(bear);
        }
        // Créature magique avancée : Évokateur Astral (Evoker)
        org.bukkit.entity.Evoker evoker = (org.bukkit.entity.Evoker) world.spawnEntity(getRandomSpawnPoint(world), EntityType.EVOKER);
        evoker.setCustomName(ChatColor.DARK_PURPLE + "Évokateur Stellaire Runique [Evoker]");
        evoker.setCustomNameVisible(true);
        targeter.accept(evoker);
        activeMonsters.add(evoker);

        Ravager r = (Ravager) world.spawnEntity(getRandomSpawnPoint(world), EntityType.RAVAGER);
        r.setCustomName(ChatColor.DARK_RED + "Ravageur Tellurique d'Assaut");
        r.setCustomNameVisible(true);
        targeter.accept(r);
        activeMonsters.add(r);
    }

    public static void spawnBossTitan(World world, Set<LivingEntity> activeMonsters, Consumer<LivingEntity> targeter) {
        Location bossLoc = new Location(world, ARENA_X + 0.5, ARENA_Y + 1.0, ARENA_Z + 6.5);
        IronGolem titan = (IronGolem) world.spawnEntity(bossLoc, EntityType.IRON_GOLEM);
        titan.setCustomName(ChatColor.RED + "" + ChatColor.BOLD + "💀 LE TITAN DE L'ÉTHER [BOSS]");
        titan.setCustomNameVisible(true);

        AttributeInstance healthAttr = titan.getAttribute(Attribute.GENERIC_MAX_HEALTH);
        if (healthAttr != null) {
            healthAttr.setBaseValue(90.0);
            titan.setHealth(90.0);
        }
        titan.addPotionEffect(new PotionEffect(PotionEffectType.RESISTANCE, 20 * 300, 1));
        titan.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 20 * 300, 0));
        targeter.accept(titan);
        activeMonsters.add(titan);

        world.playSound(bossLoc, Sound.ENTITY_WITHER_SPAWN, 1.0f, 0.8f);
        world.spawnParticle(Particle.EXPLOSION, bossLoc, 10);
    }

    public static void spawnTitanReinforcements(World world, Location center, Set<LivingEntity> activeMonsters, Consumer<LivingEntity> targeter) {
        world.playSound(center, Sound.ENTITY_WITHER_AMBIENT, 1.2f, 0.7f);
        for (int i = 0; i < 2; i++) {
            PolarBear bear = (PolarBear) world.spawnEntity(getRandomSpawnPoint(world), EntityType.POLAR_BEAR);
            bear.setCustomName(ChatColor.AQUA + "Garde Polaire du Titan");
            bear.setCustomNameVisible(true);
            targeter.accept(bear);
            activeMonsters.add(bear);
        }
        for (int i = 0; i < 2; i++) {
            Wolf w = (Wolf) world.spawnEntity(getRandomSpawnPoint(world), EntityType.WOLF);
            w.setCustomName(ChatColor.DARK_PURPLE + "Traqueur Astral du Titan");
            w.setCustomNameVisible(true);
            w.setAngry(true);
            targeter.accept(w);
            activeMonsters.add(w);
        }
    }

    public static Location getRandomSpawnPoint(World world) {
        int ox = (random.nextBoolean() ? 1 : -1) * (6 + random.nextInt(6));
        int oz = (random.nextBoolean() ? 1 : -1) * (6 + random.nextInt(6));
        return new Location(world, ARENA_X + ox + 0.5, ARENA_Y + 1.0, ARENA_Z + oz + 0.5);
    }

    private static void equipLeather(LivingEntity entity, Color color) {
        ItemStack helm = new ItemStack(Material.LEATHER_HELMET);
        LeatherArmorMeta m = (LeatherArmorMeta) helm.getItemMeta();
        if (m != null) {
            m.setColor(color);
            helm.setItemMeta(m);
        }
        entity.getEquipment().setHelmet(helm);
    }
}
