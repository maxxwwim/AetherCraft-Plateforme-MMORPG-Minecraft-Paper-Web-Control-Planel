package io.aethercraft.visuals;

import org.bukkit.*;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.entity.*;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.LeatherArmorMeta;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.scheduler.BukkitTask;
import org.bukkit.util.Vector;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Moteur Procédural d'Affixes Aléatoires pour Monstres (OneBlock & Donjons).
 * Génère dynamiquement des Rangs (X1, X2, X3 Titan), Éléments primaires,
 * et Mutations de combat avec auras de particules et Bestiaire SQLite.
 */
public class MobAffixEngine implements Listener {

    public enum MobElement {
        NONE("Neutre", ChatColor.GRAY, null, null, Color.GRAY),
        FIRE("Igné", ChatColor.GOLD, Particle.FLAME, Sound.ITEM_FIRECHARGE_USE, Color.RED),
        ICE("Cryo", ChatColor.AQUA, Particle.SNOWFLAKE, Sound.BLOCK_GLASS_BREAK, Color.TEAL),
        LIGHTNING("Fulgurant", ChatColor.YELLOW, Particle.ELECTRIC_SPARK, Sound.ENTITY_LIGHTNING_BOLT_THUNDER, Color.YELLOW),
        TOXIC("Pestilentiel", ChatColor.GREEN, Particle.SPORE_BLOSSOM_AIR, Sound.ENTITY_SLIME_SQUISH, Color.LIME),
        VOID("Cosmique", ChatColor.DARK_PURPLE, Particle.PORTAL, Sound.ENTITY_ENDERMAN_TELEPORT, Color.PURPLE);

        private final String displayName;
        private final ChatColor color;
        private final Particle particle;
        private final Sound sound;
        private final Color armorColor;

        MobElement(String displayName, ChatColor color, Particle particle, Sound sound, Color armorColor) {
            this.displayName = displayName;
            this.color = color;
            this.particle = particle;
            this.sound = sound;
            this.armorColor = armorColor;
        }

        public String getDisplayName() { return displayName; }
        public ChatColor getColor() { return color; }
        public Particle getParticle() { return particle; }
        public Sound getSound() { return sound; }
        public Color getArmorColor() { return armorColor; }
    }

    public enum MobMutation {
        VAMPIRIC("Vampirique", ChatColor.RED),
        CARAPACE("Carapace", ChatColor.DARK_GRAY),
        SWIFT("Vif", ChatColor.WHITE),
        VOLATILE("Volatil", ChatColor.DARK_RED),
        MAGNETIC("Magnétique", ChatColor.LIGHT_PURPLE),
        LOOTER("Pillard", ChatColor.GOLD);

        private final String displayName;
        private final ChatColor color;

        MobMutation(String displayName, ChatColor color) {
            this.displayName = displayName;
            this.color = color;
        }

        public String getDisplayName() { return displayName; }
        public ChatColor getColor() { return color; }
    }

    public enum AffixTier {
        NORMAL(0, "", ChatColor.GRAY, 1.0, 1.0),
        ELITE(1, "§a§l[X1]", ChatColor.GREEN, 1.3, 1.15),
        CHAMPION(2, "§9§l[X2]", ChatColor.BLUE, 1.8, 1.35),
        TITAN(3, "§d§l[X3 TITAN]", ChatColor.LIGHT_PURPLE, 2.2, 1.6);

        private final int level;
        private final String badge;
        private final ChatColor color;
        private final double healthMultiplier;
        private final double damageMultiplier;

        AffixTier(int level, String badge, ChatColor color, double healthMultiplier, double damageMultiplier) {
            this.level = level;
            this.badge = badge;
            this.color = color;
            this.healthMultiplier = healthMultiplier;
            this.damageMultiplier = damageMultiplier;
        }

        public int getLevel() { return level; }
        public String getBadge() { return badge; }
        public ChatColor getColor() { return color; }
        public double getHealthMultiplier() { return healthMultiplier; }
        public double getDamageMultiplier() { return damageMultiplier; }
    }

    public static class AffixedMobData {
        public final UUID entityUuid;
        public final AffixTier tier;
        public final MobElement element;
        public final Set<MobMutation> mutations;
        public final String originalName;
        public final long spawnedAt;

        public AffixedMobData(UUID entityUuid, AffixTier tier, MobElement element, Set<MobMutation> mutations, String originalName) {
            this.entityUuid = entityUuid;
            this.tier = tier;
            this.element = element;
            this.mutations = mutations;
            this.originalName = originalName;
            this.spawnedAt = System.currentTimeMillis();
        }
    }

    private final AetherVisualsPlugin plugin;
    private final Map<UUID, AffixedMobData> activeMobs = new ConcurrentHashMap<>();
    private final Random random = new Random();
    private BukkitTask auraTask;

    public MobAffixEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
        initDatabaseTable();
        startAuraTicker();
    }

    private void initDatabaseTable() {
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = AetherDatabase.getConnection();
                 var stmt = conn.createStatement()) {
                stmt.execute("CREATE TABLE IF NOT EXISTS player_bestiary (" +
                        "id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                        "user_id INTEGER NOT NULL, " +
                        "username TEXT NOT NULL, " +
                        "entity_type TEXT NOT NULL, " +
                        "element TEXT NOT NULL, " +
                        "affix_tier INTEGER NOT NULL, " +
                        "kills_count INTEGER NOT NULL DEFAULT 1, " +
                        "first_killed_at TEXT NOT NULL, " +
                        "last_killed_at TEXT NOT NULL, " +
                        "UNIQUE(user_id, entity_type, element, affix_tier))");
            } catch (Throwable t) {
                plugin.getLogger().warning("Erreur init player_bestiary: " + t.getMessage());
            }
        });
    }

    public void stop() {
        if (auraTask != null) {
            auraTask.cancel();
            auraTask = null;
        }
        activeMobs.clear();
    }

    private void startAuraTicker() {
        auraTask = Bukkit.getScheduler().runTaskTimer(plugin, () -> {
            if (activeMobs.isEmpty()) return;
            Iterator<Map.Entry<UUID, AffixedMobData>> it = activeMobs.entrySet().iterator();
            while (it.hasNext()) {
                Map.Entry<UUID, AffixedMobData> entry = it.next();
                Entity entity = Bukkit.getEntity(entry.getKey());
                if (!(entity instanceof LivingEntity le) || !entity.isValid() || entity.isDead()) {
                    it.remove();
                    continue;
                }

                AffixedMobData data = entry.getValue();
                Location loc = le.getLocation().add(0, 0.9, 0);

                // Aura particulaire selon l'élément
                if (data.element != MobElement.NONE && data.element.getParticle() != null) {
                    le.getWorld().spawnParticle(data.element.getParticle(), loc, (data.tier == AffixTier.TITAN ? 6 : 3), 0.35, 0.45, 0.35, 0.02);
                }

                // Mutation Magnétique : attire légèrement les joueurs proches
                if (data.mutations.contains(MobMutation.MAGNETIC) && random.nextInt(4) == 0) {
                    for (Player p : le.getWorld().getPlayers()) {
                        if (p.getLocation().distanceSquared(le.getLocation()) <= 49.0) { // rayon 7 blocs
                            Vector pull = le.getLocation().toVector().subtract(p.getLocation().toVector()).normalize().multiply(0.22);
                            pull.setY(0.08);
                            p.setVelocity(p.getVelocity().add(pull));
                            p.spawnParticle(Particle.PORTAL, p.getLocation().add(0, 1, 0), 5, 0.2, 0.2, 0.2, 0.05);
                        }
                    }
                }
            }
        }, 12L, 12L);
    }

    public boolean isAffixed(LivingEntity entity) {
        return entity != null && (activeMobs.containsKey(entity.getUniqueId()) || entity.getScoreboardTags().contains("aether_affixed_mob"));
    }

    /**
     * Applique un profil procédural d'affixes à un monstre selon le palier (phase OneBlock ou vague Donjon).
     */
    public AffixedMobData applyProceduralAffixes(LivingEntity mob, int levelContext) {
        if (mob == null || !mob.isValid()) return null;

        // Tirage du Rang (AffixTier)
        AffixTier tier = rollTier(levelContext, mob);
        if (tier == AffixTier.NORMAL) return null;

        MobElement element = MobElement.NONE;
        Set<MobMutation> mutations = new HashSet<>();

        MobElement[] elements = new MobElement[]{MobElement.FIRE, MobElement.ICE, MobElement.LIGHTNING, MobElement.TOXIC, MobElement.VOID};
        MobMutation[] allMutations = MobMutation.values();

        switch (tier) {
            case ELITE -> { // 1 Affixe : 50% Élément OU 50% Mutation
                if (random.nextBoolean()) {
                    element = elements[random.nextInt(elements.length)];
                } else {
                    mutations.add(allMutations[random.nextInt(allMutations.length)]);
                }
            }
            case CHAMPION -> { // 2 Affixes : 1 Élément + 1 Mutation
                element = elements[random.nextInt(elements.length)];
                mutations.add(allMutations[random.nextInt(allMutations.length)]);
            }
            case TITAN -> { // 3 Affixes : 1 Élément + 2 Mutations distinctes
                element = elements[random.nextInt(elements.length)];
                List<MobMutation> mutList = new ArrayList<>(Arrays.asList(allMutations));
                Collections.shuffle(mutList, random);
                mutations.add(mutList.get(0));
                mutations.add(mutList.get(1));
            }
            default -> {}
        }

        // Multiplicateurs de Santé & Dégâts
        AttributeInstance maxHpAttr = mob.getAttribute(Attribute.GENERIC_MAX_HEALTH);
        if (maxHpAttr != null) {
            double newHp = Math.round(maxHpAttr.getBaseValue() * tier.getHealthMultiplier());
            maxHpAttr.setBaseValue(newHp);
            mob.setHealth(newHp);
        }

        if (mutations.contains(MobMutation.SWIFT) || element == MobElement.LIGHTNING) {
            AttributeInstance speedAttr = mob.getAttribute(Attribute.GENERIC_MOVEMENT_SPEED);
            if (speedAttr != null) {
                speedAttr.setBaseValue(speedAttr.getBaseValue() * 1.35);
            }
        }

        // Équipement Visuel Céleste
        equipEntityCosmetics(mob, tier, element);

        // Scoreboard Tags pour persistance
        mob.addScoreboardTag("aether_affixed_mob");
        mob.addScoreboardTag("aether_tier_" + tier.name());
        mob.addScoreboardTag("aether_elem_" + element.name());
        for (MobMutation m : mutations) {
            mob.addScoreboardTag("aether_mut_" + m.name());
        }

        // Formatage du Nom Stylisé
        String baseName = mob.getCustomName() != null ? mob.getCustomName() : formatEntityTypeName(mob.getType());
        StringBuilder sb = new StringBuilder();
        sb.append(tier.getBadge()).append(" ").append(ChatColor.WHITE).append(baseName);
        if (element != MobElement.NONE) {
            sb.append(" ").append(element.getColor()).append("[").append(element.getDisplayName()).append("]");
        }
        for (MobMutation m : mutations) {
            sb.append(" ").append(m.getColor()).append("[").append(m.getDisplayName()).append("]");
        }

        mob.setCustomName(sb.toString());
        mob.setCustomNameVisible(true);

        AffixedMobData data = new AffixedMobData(mob.getUniqueId(), tier, element, mutations, baseName);
        activeMobs.put(mob.getUniqueId(), data);
        return data;
    }

    /**
     * Applique des affixes garantis de haute puissance pour les Mini-Boss de palier OneBlock.
     */
    public AffixedMobData applyBossAffixes(LivingEntity mob, int palier) {
        if (mob == null || !mob.isValid()) return null;
        AffixTier tier = (palier >= 8 || random.nextBoolean()) ? AffixTier.TITAN : AffixTier.CHAMPION;

        MobElement[] elements = new MobElement[]{MobElement.FIRE, MobElement.ICE, MobElement.LIGHTNING, MobElement.TOXIC, MobElement.VOID};
        MobElement element = elements[palier % elements.length];

        Set<MobMutation> mutations = new HashSet<>();
        List<MobMutation> mutList = new ArrayList<>(Arrays.asList(MobMutation.values()));
        Collections.shuffle(mutList, random);
        mutations.add(mutList.get(0));
        if (tier == AffixTier.TITAN) mutations.add(mutList.get(1));

        AttributeInstance maxHpAttr = mob.getAttribute(Attribute.GENERIC_MAX_HEALTH);
        if (maxHpAttr != null) {
            double newHp = Math.round(maxHpAttr.getBaseValue() * tier.getHealthMultiplier() * 1.5);
            maxHpAttr.setBaseValue(newHp);
            mob.setHealth(newHp);
        }

        equipEntityCosmetics(mob, tier, element);

        mob.addScoreboardTag("aether_affixed_mob");
        mob.addScoreboardTag("aether_tier_" + tier.name());
        mob.addScoreboardTag("aether_elem_" + element.name());
        for (MobMutation m : mutations) mob.addScoreboardTag("aether_mut_" + m.name());

        String baseName = mob.getCustomName() != null ? mob.getCustomName() : "Boss de Palier";
        StringBuilder sb = new StringBuilder();
        sb.append(tier.getBadge()).append(" ").append(baseName);
        sb.append(" ").append(element.getColor()).append("[").append(element.getDisplayName()).append("]");
        for (MobMutation m : mutations) sb.append(" ").append(m.getColor()).append("[").append(m.getDisplayName()).append("]");

        mob.setCustomName(sb.toString());
        mob.setCustomNameVisible(true);

        AffixedMobData data = new AffixedMobData(mob.getUniqueId(), tier, element, mutations, baseName);
        activeMobs.put(mob.getUniqueId(), data);
        return data;
    }

    private AffixTier rollTier(int levelContext, LivingEntity mob) {
        if (mob.getScoreboardTags().contains("aether_oneblock_boss") || mob instanceof IronGolem) {
            return random.nextBoolean() ? AffixTier.TITAN : AffixTier.CHAMPION;
        }

        int roll = random.nextInt(100);
        if (levelContext <= 2) {
            if (roll < 55) return AffixTier.NORMAL;
            if (roll < 90) return AffixTier.ELITE;
            return AffixTier.CHAMPION;
        } else if (levelContext <= 5) {
            if (roll < 35) return AffixTier.NORMAL;
            if (roll < 75) return AffixTier.ELITE;
            if (roll < 96) return AffixTier.CHAMPION;
            return AffixTier.TITAN;
        } else if (levelContext <= 8) {
            if (roll < 15) return AffixTier.NORMAL;
            if (roll < 60) return AffixTier.ELITE;
            if (roll < 88) return AffixTier.CHAMPION;
            return AffixTier.TITAN;
        } else {
            if (roll < 10) return AffixTier.NORMAL;
            if (roll < 45) return AffixTier.ELITE;
            if (roll < 80) return AffixTier.CHAMPION;
            return AffixTier.TITAN;
        }
    }

    private void equipEntityCosmetics(LivingEntity mob, AffixTier tier, MobElement element) {
        if (mob.getEquipment() == null) return;
        Color c = (element != MobElement.NONE) ? element.getArmorColor() : Color.GRAY;

        // Casque teinté de l'élément
        ItemStack helm = new ItemStack(Material.LEATHER_HELMET);
        if (helm.getItemMeta() instanceof LeatherArmorMeta meta) {
            meta.setColor(c);
            helm.setItemMeta(meta);
        }
        mob.getEquipment().setHelmet(helm);

        if (tier == AffixTier.CHAMPION) {
            mob.getEquipment().setChestplate(new ItemStack(Material.CHAINMAIL_CHESTPLATE));
            mob.getEquipment().setBoots(new ItemStack(Material.IRON_BOOTS));
        } else if (tier == AffixTier.TITAN) {
            mob.getEquipment().setChestplate(new ItemStack(Material.DIAMOND_CHESTPLATE));
            mob.getEquipment().setLeggings(new ItemStack(Material.NETHERITE_LEGGINGS));
            mob.getEquipment().setBoots(new ItemStack(Material.DIAMOND_BOOTS));
        }
    }

    private String formatEntityTypeName(EntityType type) {
        return switch (type) {
            case ZOMBIE -> "Zombie";
            case SKELETON -> "Squelette";
            case SPIDER -> "Araignée";
            case CAVE_SPIDER -> "Araignée Bleue";
            case WITCH -> "Sorcière";
            case PILLAGER -> "Pillard";
            case VINDICATOR -> "Inquisiteur";
            case PIGLIN -> "Piglin";
            case PIGLIN_BRUTE -> "Piglin Brute";
            case BLAZE -> "Blaze";
            case ENDERMAN -> "Enderman";
            case WITHER_SKELETON -> "Wither Squelette";
            case STRAY -> "Vagabond";
            case DROWNED -> "Noyé";
            case EVOKER -> "Évokateur";
            case RAVAGER -> "Ravageur";
            case IRON_GOLEM -> "Titan de Pierre";
            default -> "Créature";
        };
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onEntityDamageByEntity(EntityDamageByEntityEvent event) {
        // Cas 1 : Monstre Affixé frappe un Joueur
        if (event.getDamager() instanceof LivingEntity damager && event.getEntity() instanceof Player target) {
            AffixedMobData data = activeMobs.get(damager.getUniqueId());
            if (data != null) {
                // Effets élémentaires
                switch (data.element) {
                    case FIRE -> target.setFireTicks(20 * 4);
                    case ICE -> {
                        target.addPotionEffect(new PotionEffect(PotionEffectType.SLOWNESS, 20 * 3, 1));
                        target.playSound(target.getLocation(), Sound.BLOCK_GLASS_BREAK, 0.8f, 1.3f);
                    }
                    case LIGHTNING -> {
                        target.getWorld().strikeLightningEffect(target.getLocation());
                        target.setVelocity(target.getVelocity().add(new Vector(0, 0.35, 0)));
                    }
                    case TOXIC -> target.addPotionEffect(new PotionEffect(PotionEffectType.POISON, 20 * 4, 1));
                    case VOID -> {
                        target.addPotionEffect(new PotionEffect(PotionEffectType.BLINDNESS, 20 * 2, 0));
                        target.playSound(target.getLocation(), Sound.ENTITY_ENDERMAN_TELEPORT, 1.0f, 1.2f);
                    }
                    default -> {}
                }

                // Mutation Vampirique : se soigne de 30% des dégâts infligés
                if (data.mutations.contains(MobMutation.VAMPIRIC)) {
                    AttributeInstance maxHpAttr = damager.getAttribute(Attribute.GENERIC_MAX_HEALTH);
                    double maxHp = maxHpAttr != null ? maxHpAttr.getValue() : 20.0;
                    double heal = event.getFinalDamage() * 0.35;
                    damager.setHealth(Math.min(maxHp, damager.getHealth() + heal));
                    damager.getWorld().spawnParticle(Particle.HEART, damager.getLocation().add(0, 1.5, 0), 3, 0.2, 0.2, 0.2, 0.05);
                }
            }
        }

        // Cas 2 : Joueur frappe un Monstre Affixé
        if (event.getEntity() instanceof LivingEntity victim && event.getDamager() instanceof Player attacker) {
            AffixedMobData data = activeMobs.get(victim.getUniqueId());
            if (data != null) {
                // Mutation Carapace : réduit les dégâts de 40%
                if (data.mutations.contains(MobMutation.CARAPACE)) {
                    event.setDamage(event.getDamage() * 0.60);
                    victim.getWorld().spawnParticle(Particle.CRIT, victim.getLocation().add(0, 1, 0), 8, 0.3, 0.3, 0.3, 0.1);
                    attacker.playSound(victim.getLocation(), Sound.ITEM_SHIELD_BLOCK, 0.8f, 1.2f);
                }
            }
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onEntityDeath(EntityDeathEvent event) {
        LivingEntity entity = event.getEntity();
        AffixedMobData data = activeMobs.remove(entity.getUniqueId());
        if (data == null) return;

        Player killer = entity.getKiller();
        Location loc = entity.getLocation();

        // Mutation Volatile : explosion d'énergie à la mort
        if (data.mutations.contains(MobMutation.VOLATILE)) {
            loc.getWorld().spawnParticle(Particle.EXPLOSION, loc.add(0, 0.8, 0), 2, 0.2, 0.2, 0.2, 0.05);
            loc.getWorld().playSound(loc, Sound.ENTITY_GENERIC_EXPLODE, 1.0f, 1.2f);
            for (Player p : loc.getWorld().getPlayers()) {
                if (p.getLocation().distanceSquared(loc) <= 16.0) {
                    p.damage(3.5, entity);
                    p.setVelocity(p.getLocation().toVector().subtract(loc.toVector()).normalize().multiply(0.4).setY(0.2));
                }
            }
        }

        // Si tué par un joueur : calcul des récompenses et enregistrement Bestiaire
        if (killer != null) {
            boolean isLooter = data.mutations.contains(MobMutation.LOOTER);
            int baseCoins = switch (data.tier) {
                case ELITE -> 20 + random.nextInt(21);        // 20-40 ⛃
                case CHAMPION -> 60 + random.nextInt(41);    // 60-100 ⛃
                case TITAN -> 200 + random.nextInt(151);     // 200-350 ⛃
                default -> 5;
            };
            if (isLooter) baseCoins *= 3;

            int pointsGain = switch (data.tier) {
                case CHAMPION -> 1;
                case TITAN -> 3;
                default -> 0;
            };

            // Drop chance de Clé Céleste pour les Titans
            if (data.tier == AffixTier.TITAN && random.nextInt(4) == 0) {
                killer.getInventory().addItem(CustomItemFactory.createCelestialKey(1));
                killer.sendMessage(ChatColor.LIGHT_PURPLE + "🗝️ " + ChatColor.GOLD + "Loot Mythique : Clé de Caisse Céleste trouvée sur le Titan !");
            }

            final int finalCoins = baseCoins;
            final int finalPoints = pointsGain;
            final String killedTypeName = entity.getType().name();
            final String elemName = data.element.name();
            final int tierLvl = data.tier.getLevel();

            // Enregistrement asynchrone SQLite & vérification des Succès Bestiaire
            Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
                recordKillAndCheckAchievements(killer, killedTypeName, elemName, tierLvl, finalCoins, finalPoints);
            });

            // Feedback joueur
            killer.playSound(killer.getLocation(), Sound.ENTITY_EXPERIENCE_ORB_PICKUP, 0.9f, 1.3f);
            killer.sendMessage(data.tier.getColor() + "✔ " + ChatColor.YELLOW + "[BESTIAIRE] Monstre terrassé : " +
                    data.tier.getBadge() + " " + ChatColor.WHITE + data.originalName +
                    ChatColor.GOLD + " (+" + finalCoins + " ⛃" + (finalPoints > 0 ? " & +" + finalPoints + " 💎" : "") + ") !");
        }
    }

    private void recordKillAndCheckAchievements(Player player, String entityType, String element, int tierLevel, int coins, int points) {
        String now = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        try (Connection conn = AetherDatabase.getConnection()) {
            conn.setAutoCommit(false);
            try {
                // 1. Récupérer l'ID utilisateur web du joueur
                int userId = 1;
                try (PreparedStatement ps = conn.prepareStatement("SELECT id FROM users WHERE LOWER(minecraft_username) = LOWER(?)")) {
                    ps.setString(1, player.getName());
                    try (ResultSet rs = ps.executeQuery()) {
                        if (rs.next()) userId = rs.getInt("id");
                    }
                }

                // 2. Créditer les Coins
                try (PreparedStatement ps = conn.prepareStatement("UPDATE players SET balance = balance + ? WHERE LOWER(username) = LOWER(?)")) {
                    ps.setDouble(1, coins);
                    ps.setString(2, player.getName());
                    ps.executeUpdate();
                }

                // 3. Créditer les Points Boutique si applicable
                if (points > 0) {
                    try (PreparedStatement ps = conn.prepareStatement("UPDATE users SET shop_points = shop_points + ? WHERE id = ?")) {
                        ps.setInt(1, points);
                        ps.setInt(2, userId);
                        ps.executeUpdate();
                    }
                }

                // 4. Mettre à jour la table player_bestiary
                try (PreparedStatement ps = conn.prepareStatement(
                        "INSERT INTO player_bestiary (user_id, username, entity_type, element, affix_tier, kills_count, first_killed_at, last_killed_at) " +
                                "VALUES (?, ?, ?, ?, ?, 1, ?, ?) " +
                                "ON CONFLICT(user_id, entity_type, element, affix_tier) DO UPDATE SET kills_count = kills_count + 1, last_killed_at = ?")) {
                    ps.setInt(1, userId);
                    ps.setString(2, player.getName());
                    ps.setString(3, entityType);
                    ps.setString(4, element);
                    ps.setInt(5, tierLevel);
                    ps.setString(6, now);
                    ps.setString(7, now);
                    ps.setString(8, now);
                    ps.executeUpdate();
                }

                // 5. Vérifier les Succès du Bestiaire
                checkAndUnlockBestiaryAchievements(conn, userId, player, tierLevel);

                conn.commit();
            } catch (Throwable ex) {
                conn.rollback();
                throw ex;
            }
        } catch (Throwable t) {
            plugin.getLogger().warning("Erreur SQL Bestiaire: " + t.getMessage());
        }
    }

    private void checkAndUnlockBestiaryAchievements(Connection conn, int userId, Player player, int lastTier) throws Exception {
        String now = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));

        // Succès 1 : ach_bestiary_x1_first (premier kill X1+)
        if (lastTier >= 1) {
            unlockSingleAchievement(conn, userId, player, "ach_bestiary_x1_first", "Premier Chasseur", "Initié Chasseur", 20, now);
        }

        // Succès 2 : ach_bestiary_x1_elements (les 5 éléments battus au rang X1+)
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT COUNT(DISTINCT element) as cnt FROM player_bestiary WHERE user_id = ? AND affix_tier >= 1 AND element != 'NONE'")) {
            ps.setInt(1, userId);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next() && rs.getInt("cnt") >= 5) {
                    unlockSingleAchievement(conn, userId, player, "ach_bestiary_x1_elements", "Maître des Éléments X1", "Élémentaliste", 50, now);
                }
            }
        }

        // Succès 3 : ach_bestiary_x2_slayer (20 kills de rang X2+)
        if (lastTier >= 2) {
            try (PreparedStatement ps = conn.prepareStatement(
                    "SELECT SUM(kills_count) as total_x2 FROM player_bestiary WHERE user_id = ? AND affix_tier >= 2")) {
                ps.setInt(1, userId);
                try (ResultSet rs = ps.executeQuery()) {
                    if (rs.next() && rs.getInt("total_x2") >= 20) {
                        unlockSingleAchievement(conn, userId, player, "ach_bestiary_x2_slayer", "Chasseur de Champions", "Traqueur de Champions", 80, now);
                    }
                }
            }
        }

        // Succès 4 : ach_bestiary_x2_species (au moins 8 espèces différentes en X2+)
        try (PreparedStatement ps = conn.prepareStatement(
                "SELECT COUNT(DISTINCT entity_type) as species_cnt FROM player_bestiary WHERE user_id = ? AND affix_tier >= 2")) {
            ps.setInt(1, userId);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next() && rs.getInt("species_cnt") >= 8) {
                    unlockSingleAchievement(conn, userId, player, "ach_bestiary_x2_species", "Grand Bestiaire X2", "Zoologiste Céleste", 100, now);
                }
            }
        }

        // Succès 5 : ach_bestiary_x3_titan (premier Titan X3 battu)
        if (lastTier >= 3) {
            unlockSingleAchievement(conn, userId, player, "ach_bestiary_x3_titan", "Tombeur de Mythes", "Tueur de Titans", 150, now);

            // Succès 6 : ach_bestiary_x3_pantheon (les 5 éléments vaincus en Rang X3)
            try (PreparedStatement ps = conn.prepareStatement(
                    "SELECT COUNT(DISTINCT element) as elem_x3 FROM player_bestiary WHERE user_id = ? AND affix_tier >= 3 AND element != 'NONE'")) {
                ps.setInt(1, userId);
                try (ResultSet rs = ps.executeQuery()) {
                    if (rs.next() && rs.getInt("elem_x3") >= 5) {
                        unlockSingleAchievement(conn, userId, player, "ach_bestiary_x3_pantheon", "Fléau Primordial X3", "Fléau Primordial", 300, now);
                    }
                }
            }
        }
    }

    private void unlockSingleAchievement(Connection conn, int userId, Player player, String achId, String achTitle, String titleReward, int points, String now) throws Exception {
        try (PreparedStatement check = conn.prepareStatement("SELECT id FROM user_achievements WHERE user_id = ? AND achievement_id = ?")) {
            check.setInt(1, userId);
            check.setString(2, achId);
            try (ResultSet rs = check.executeQuery()) {
                if (rs.next()) return; // Déjà débloqué
            }
        }

        try (PreparedStatement insert = conn.prepareStatement("INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)")) {
            insert.setInt(1, userId);
            insert.setString(2, achId);
            insert.setString(3, now);
            insert.executeUpdate();
        }

        try (PreparedStatement up = conn.prepareStatement("UPDATE users SET shop_points = shop_points + ? WHERE id = ?")) {
            up.setInt(1, points);
            up.setInt(2, userId);
            up.executeUpdate();
        }

        Bukkit.getScheduler().runTask(plugin, () -> {
            player.playSound(player.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.0f);
            player.sendTitle(ChatColor.GOLD + "★ SUCCÈS BESTIAIRE DÉBLOQUÉ ! ★", ChatColor.YELLOW + achTitle + " (+" + points + " 💎)", 10, 60, 20);
            Bukkit.broadcastMessage(ChatColor.GOLD + "★ [BESTIAIRE] " + ChatColor.AQUA + player.getName() +
                    ChatColor.YELLOW + " a débloqué le succès : " + ChatColor.LIGHT_PURPLE + achTitle +
                    ChatColor.GOLD + " (Titre : " + ChatColor.WHITE + "[" + titleReward + "]" + ChatColor.GOLD + ") !");
        });
    }
}
