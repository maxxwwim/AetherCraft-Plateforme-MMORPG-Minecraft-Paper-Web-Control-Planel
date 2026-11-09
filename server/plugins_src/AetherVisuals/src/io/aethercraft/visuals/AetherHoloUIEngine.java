package io.aethercraft.visuals;

import io.aethercraft.visuals.AetherHoloDataService.*;
import io.aethercraft.visuals.AetherPhoneCanvasRenderer.CardEntry;
import net.md_5.bungee.api.ChatMessageType;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.*;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.inventory.*;
import org.bukkit.event.player.*;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.MapMeta;
import org.bukkit.map.MapCanvas;
import org.bukkit.map.MapRenderer;
import org.bukkit.map.MapView;
import org.bukkit.scheduler.BukkitTask;

import java.awt.image.BufferedImage;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Moteur Smartphone GTA HD sur l'Écran du Joueur (Tenue 2 Mains Centrée, Pointeur Magnétique Sans Dérive & Molette).
 */
public class AetherHoloUIEngine implements Listener {

    private static final long INACTIVITY_TIMEOUT_MS = 3L * 60L * 1000L;

    public enum HoloMode { COCKPIT, SHOP, MARKET, ORES, PROFILE, LEADERBOARD, PETS }
    public enum ProfileSubTab { OVERVIEW_AND_ACHIEVEMENTS, QUESTS }

    private final AetherVisualsPlugin plugin;
    private final AetherHoloDataService dataService;
    private final AetherHoloTransactions txService;
    private final Map<UUID, HoloSession> sessions = new ConcurrentHashMap<>();
    private BukkitTask watchLoop;

    public AetherHoloUIEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
        this.dataService = new AetherHoloDataService(plugin);
        this.txService = new AetherHoloTransactions(plugin, dataService);
        startWatchLoop();
    }

    public AetherHoloDataService getDataService() { return dataService; }
    public AetherHoloTransactions getTxService() { return txService; }

    public static class HoloSession {
        public final UUID playerUuid;
        public HoloMode mode;
        public ProfileSubTab profileSubTab = ProfileSubTab.OVERVIEW_AND_ACHIEVEMENTS;
        public String shopCategory = "all", statusBanner = "";
        public String leaderboardCategory = "oneblock", petsSubFilter = "familiers";
        public int selectedIndex = 0, dockIndex = 0, phoneSlot = 0, cursorX = 33, cursorY = 49;
        public float anchorYaw = 0f, anchorPitch = 40f;
        public boolean active = true, dirty = true, dockFocused = false;
        public long lastActivityMillis = System.currentTimeMillis(), lastClickMillis = 0, lastModeSwitchMillis = 0;
        public ItemStack savedHandItem, savedOffHandItem;
        public MapView mapView;
        public BufferedImage latestFrame;

        // --- Écran holographique 2x2 cartes (256x256) & pointeur laser ---
        public PhoneTiles tiles;
        public final List<org.bukkit.entity.ItemFrame> frames = new ArrayList<>();
        public final List<org.bukkit.block.Block> barriers = new ArrayList<>();
        public boolean wheelMode = false, needsPush = false;
        public float wheelYaw, wheelPitch;
        public long lastHudMillis = 0;
        public Location anchorLoc;
        public int axis, sd, cb, yb, sgnR, rxCoord;
        public double plane;
        public PlayerProfileData profile;
        public List<ShopItemData> shopItems = Collections.emptyList();
        public List<MarketListingData> marketItems = Collections.emptyList();
        public List<OreData> oreItems = Collections.emptyList();
        public List<AchievementData> achievements = Collections.emptyList();
        public List<QuestData> quests = Collections.emptyList();
        public List<ShopItemData> animalItems = Collections.emptyList();
        public List<AetherVisualScoreboardManager.LeaderboardEntry> leaderboardEntries = Collections.emptyList();

        public HoloSession(UUID playerUuid, HoloMode mode) {
            this.playerUuid = playerUuid;
            this.mode = mode;
            this.dockIndex = mode.ordinal();
        }
        public void touchActivity() { this.lastActivityMillis = System.currentTimeMillis(); }
    }

    /** Quatre cartes persistantes par joueur (réutilisées entre sessions pour ne pas gonfler les fichiers map_N.dat). */
    public static class PhoneTiles {
        public final UUID owner;
        public final MapView[] views = new MapView[4];
        public final BufferedImage[] img = new BufferedImage[4];
        public final boolean[] dirty = new boolean[4];
        public final int[] hash = new int[4];
        public PhoneTiles(UUID owner) { this.owner = owner; Arrays.fill(hash, Integer.MIN_VALUE); }
    }

    private final Map<UUID, PhoneTiles> tileCache = new ConcurrentHashMap<>();
    private java.io.File barrierFile() { return new java.io.File(plugin.getDataFolder(), "phone_barriers.txt"); }

    private PhoneTiles getTiles(Player p) {
        return tileCache.computeIfAbsent(p.getUniqueId(), id -> {
            PhoneTiles t = new PhoneTiles(id);
            for (int k = 0; k < 4; k++) {
                final int idx = k;
                MapView view = Bukkit.createMap(p.getWorld());
                for (MapRenderer r : new ArrayList<>(view.getRenderers())) view.removeRenderer(r);
                view.setTrackingPosition(false);
                view.setUnlimitedTracking(false);
                view.addRenderer(new MapRenderer(true) {
                    @Override
                    public void render(MapView mv, MapCanvas canvas, Player viewer) {
                        if (!viewer.getUniqueId().equals(t.owner) || !t.dirty[idx] || t.img[idx] == null) return;
                        t.dirty[idx] = false;
                        canvas.drawImage(0, 0, t.img[idx]);
                    }
                });
                t.views[k] = view;
            }
            return t;
        });
    }

    public void openHoloUI(Player p, HoloMode mode, String subFilter) {
        p.closeInventory();
        closeSession(p.getUniqueId(), false);
        HoloSession s = new HoloSession(p.getUniqueId(), mode);
        if (subFilter != null && !subFilter.isEmpty()) {
            if (mode == HoloMode.SHOP) s.shopCategory = subFilter.toLowerCase(Locale.ROOT);
            if (mode == HoloMode.PROFILE && subFilter.equalsIgnoreCase("quests")) s.profileSubTab = ProfileSubTab.QUESTS;
            if (mode == HoloMode.LEADERBOARD) s.leaderboardCategory = subFilter.toLowerCase(Locale.ROOT);
            if (mode == HoloMode.PETS) s.petsSubFilter = subFilter.toLowerCase(Locale.ROOT);
        }
        reloadSessionData(p, s);
        s.tiles = getTiles(p);
        Arrays.fill(s.tiles.hash, Integer.MIN_VALUE);
        sessions.put(p.getUniqueId(), s);
        if (!buildScreen(p, s)) {
            closeSession(p.getUniqueId(), false);
            p.sendMessage("§c📱 Pas assez de place devant vous : l'écran holographique demande 2x2 blocs libres à ~2 blocs de distance.");
            return;
        }
        s.anchorLoc = p.getLocation().clone();
        aimPointer(p, s, p.getEyeLocation());
        pushPhoneFrame(p, s);
        // Second envoi une fois les cadres visibles côté client (garantit l'affichage initial)
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (sessions.get(p.getUniqueId()) == s) { Arrays.fill(s.tiles.hash, Integer.MIN_VALUE); pushPhoneFrame(p, s); }
        }, 6L);
        p.playSound(p.getLocation(), Sound.BLOCK_NOTE_BLOCK_CHIME, 0.85f, 1.6f);
        p.sendMessage("§b§l📱 [IPHONE 2026 — AETHER-OS] §7Écran holographique 256x256 : §eVisez §7avec la souris (laser) • §aClic G §7Ouvrir/Action • §bClic D §7‹ Accueil • §eMolette §7Naviguer • §d[F] §7Catégorie • §c[Sneak] §7Ranger.");
    }

    /** Construit l'écran 2x2 : cadres invisibles (visibles uniquement du joueur) adossés à des barrières temporaires. */
    private boolean buildScreen(Player p, HoloSession s) {
        World w = p.getWorld();
        Location eye = p.getEyeLocation();
        org.bukkit.block.BlockFace face = p.getFacing();
        int dx = face.getModX(), dz = face.getModZ();
        if (dx == 0 && dz == 0) return false;
        int rx = -dz, rz = dx;
        s.axis = (dx != 0) ? 0 : 1;
        s.sd = (dx != 0) ? dx : dz;
        s.rxCoord = (rx != 0) ? 0 : 1; // axe horizontal (0=x, 1=z) le long duquel va la droite du joueur
        s.sgnR = (rx != 0) ? rx : rz;
        double eyeAlong = (s.axis == 0) ? eye.getX() : eye.getZ();
        double eyeRight = (s.rxCoord == 0) ? eye.getX() : eye.getZ();
        int fb = (int) Math.floor(eyeAlong) + 2 * s.sd;
        s.cb = (int) Math.round(eyeRight);
        s.yb = (int) Math.round(eye.getY());
        s.plane = (s.sd > 0) ? fb + 1 - 0.0625 : fb + 0.0625;

        org.bukkit.block.Block[] front = new org.bukkit.block.Block[4];
        org.bukkit.block.Block[] back = new org.bukkit.block.Block[4];
        for (int k = 0; k < 4; k++) {
            int col = k % 2, row = k / 2;
            int rightIdx = (s.sgnR > 0) ? s.cb - 1 + col : s.cb - col;
            int y = s.yb - row;
            front[k] = (s.axis == 0) ? w.getBlockAt(fb, y, rightIdx) : w.getBlockAt(rightIdx, y, fb);
            back[k] = (s.axis == 0) ? w.getBlockAt(fb + s.sd, y, rightIdx) : w.getBlockAt(rightIdx, y, fb + s.sd);
            if (!front[k].getType().isAir()) return false;
            Material bm = back[k].getType();
            if (!bm.isAir() && !bm.isSolid()) return false;
        }
        try {
            for (int k = 0; k < 4; k++) {
                if (back[k].getType().isAir()) {
                    back[k].setType(Material.BARRIER, false);
                    s.barriers.add(back[k]);
                }
            }
            persistBarriers();
            org.bukkit.block.BlockFace facing = face.getOppositeFace();
            for (int k = 0; k < 4; k++) {
                ItemStack mapItem = new ItemStack(Material.FILLED_MAP, 1);
                MapMeta meta = (MapMeta) mapItem.getItemMeta();
                meta.setMapView(s.tiles.views[k]);
                mapItem.setItemMeta(meta);
                Location at = front[k].getLocation();
                org.bukkit.entity.ItemFrame fr = w.spawn(at, org.bukkit.entity.ItemFrame.class, f -> {
                    f.setVisibleByDefault(false);
                    f.setPersistent(false);
                    f.setFacingDirection(facing, true);
                    f.setItem(mapItem, false);
                    f.setVisible(false);
                    f.setFixed(true);
                    f.setInvulnerable(true);
                    f.setSilent(true);
                    f.addScoreboardTag("AETHER_PHONE_SCREEN");
                });
                s.frames.add(fr);
                p.showEntity(plugin, fr);
            }
        } catch (Throwable t) {
            plugin.getLogger().warning("Écran phone indisponible : " + t.getMessage());
            teardownScreen(s);
            return false;
        }
        return true;
    }

    private void teardownScreen(HoloSession s) {
        for (org.bukkit.entity.ItemFrame f : s.frames) { try { f.remove(); } catch (Throwable ignored) {} }
        s.frames.clear();
        for (org.bukkit.block.Block b : s.barriers) { if (b.getType() == Material.BARRIER) b.setType(Material.AIR, false); }
        s.barriers.clear();
        persistBarriers();
    }

    private void persistBarriers() {
        try {
            java.io.File f = barrierFile();
            f.getParentFile().mkdirs();
            StringBuilder sb = new StringBuilder();
            for (HoloSession hs : sessions.values()) {
                for (org.bukkit.block.Block b : hs.barriers) {
                    sb.append(b.getWorld().getName()).append(';').append(b.getX()).append(';').append(b.getY()).append(';').append(b.getZ()).append('\n');
                }
            }
            java.nio.file.Files.writeString(f.toPath(), sb.toString());
        } catch (Exception ignored) {}
    }

    /** Nettoie les barrières orphelines laissées par un crash serveur. */
    private void cleanupOrphanBarriers() {
        try {
            java.io.File f = barrierFile();
            if (!f.exists()) return;
            for (String line : java.nio.file.Files.readAllLines(f.toPath())) {
                String[] parts = line.split(";");
                if (parts.length != 4) continue;
                World w = Bukkit.getWorld(parts[0]);
                if (w == null) continue;
                org.bukkit.block.Block b = w.getBlockAt(Integer.parseInt(parts[1]), Integer.parseInt(parts[2]), Integer.parseInt(parts[3]));
                if (b.getType() == Material.BARRIER) b.setType(Material.AIR, false);
            }
            java.nio.file.Files.writeString(f.toPath(), "");
        } catch (Exception ignored) {}
    }

    /** Laser : intersection du regard avec le plan de l'écran -> curseur logique 0..127. */
    private boolean aimPointer(Player p, HoloSession s, Location eye) {
        org.bukkit.util.Vector l = eye.getDirection();
        double ld = (s.axis == 0) ? l.getX() : l.getZ();
        if (ld * s.sd < 0.05) return false;
        double od = (s.axis == 0) ? eye.getX() : eye.getZ();
        double t = (s.plane - od) / ld;
        if (t <= 0) return false;
        double hy = eye.getY() + l.getY() * t;
        double hr = (s.rxCoord == 0) ? (eye.getX() + l.getX() * t) : (eye.getZ() + l.getZ() * t);
        double a = s.sgnR * (hr - s.cb);
        double fx = (a + 1.0) / 2.0;
        double fy = ((s.yb + 1) - hy) / 2.0;
        if (fx < -0.15 || fx > 1.15 || fy < -0.15 || fy > 1.15) return false;
        fx = Math.max(0, Math.min(1, fx));
        fy = Math.max(0, Math.min(1, fy));
        return AetherPhoneCanvasRenderer.updatePointer(s, fx * AetherPhoneCanvasRenderer.SIZE, fy * AetherPhoneCanvasRenderer.SIZE);
    }

    public void pushPhoneFrame(Player p, HoloSession s) {
        if (p == null || !p.isOnline() || s.tiles == null) return;
        s.needsPush = false;
        BufferedImage full = AetherPhoneCanvasRenderer.renderSmartphoneImage(s);
        int n = AetherPhoneCanvasRenderer.SIZE;
        int[] px = new int[n * n];
        for (int k = 0; k < 4; k++) {
            full.getRGB((k % 2) * n, (k / 2) * n, n, n, px, 0, n);
            int h = Arrays.hashCode(px);
            if (h == s.tiles.hash[k]) continue; // tuile inchangée : rien à envoyer
            BufferedImage tile = new BufferedImage(n, n, BufferedImage.TYPE_INT_ARGB);
            tile.setRGB(0, 0, n, n, px, 0, n);
            s.tiles.img[k] = tile;
            s.tiles.hash[k] = h;
            s.tiles.dirty[k] = true;
            p.sendMap(s.tiles.views[k]);
        }
        long now = System.currentTimeMillis();
        if (now - s.lastHudMillis > 1500L) { s.lastHudMillis = now; sendHudPrompt(p, s); }
    }

    private void sendHudPrompt(Player p, HoloSession s) {
        List<CardEntry> cards = AetherPhoneCanvasRenderer.buildCards(s);
        String selTitle = (s.selectedIndex >= 0 && s.selectedIndex < cards.size()) ? cards.get(s.selectedIndex).title() : s.mode.name();
        String msg = (s.mode == HoloMode.COCKPIT)
                ? "§b📱 iPhone 2026 §8| §6§l[App: " + selTitle + "] §8| §aClicG: Ouvrir §8| §eMolette: Naviguer §8| §c[Sneak]: Ranger"
                : "§b📱 " + s.mode.name() + " §8| §6§l[" + selTitle + "] §8| §aClicG: Action §8| §bClicD: ‹ Accueil §8| §c[Sneak]: Ranger";
        try { p.spigot().sendMessage(ChatMessageType.ACTION_BAR, TextComponent.fromLegacy(msg)); } catch (Throwable ignored) {}
    }

    public void closeSession(UUID uuid, boolean sound) {
        HoloSession old = sessions.remove(uuid);
        if (old == null) return;
        old.active = false;
        teardownScreen(old);
        Player p = Bukkit.getPlayer(uuid);
        if (p != null) {
            if (sound && p.isOnline()) {
                p.playSound(p.getLocation(), Sound.ITEM_ARMOR_EQUIP_IRON, 0.7f, 1.3f);
                try { p.spigot().sendMessage(ChatMessageType.ACTION_BAR, TextComponent.fromLegacy("§7📱 AetherPhone rangé dans votre poche.")); } catch (Throwable ignored) {}
            }
        }
    }

    public void closeAll() {
        for (UUID id : new ArrayList<>(sessions.keySet())) closeSession(id, false);
        if (watchLoop != null) watchLoop.cancel();
        purgeAllWebDisplayEntities();
    }

    public static void purgeAllWebDisplayEntities() {
        for (World w : Bukkit.getWorlds()) {
            for (Entity e : w.getEntities()) {
                if (e.getScoreboardTags().contains("AETHER_WEBDISPLAY") || e.getScoreboardTags().stream().anyMatch(t -> t.startsWith("AETHER_SESSION_"))) {
                    try { e.remove(); } catch (Exception ignored) {}
                }
            }
        }
    }

    public void reloadSessionData(Player p, HoloSession s) {
        s.profile = dataService.loadPlayerProfile(p.getName());
        s.shopItems = dataService.loadShopItems(p.getName(), s.shopCategory);
        s.marketItems = dataService.loadActiveMarketListings();
        s.oreItems = dataService.loadOresMarket();
        s.achievements = dataService.loadAchievements(p.getName());
        s.quests = dataService.loadQuests(p.getName());
        s.animalItems = dataService.loadAnimalShopItems(p.getName(), s.petsSubFilter);
        s.leaderboardEntries = dataService.loadLeaderboard(s.leaderboardCategory);
    }

    private int watchTick = 0;

    private void startWatchLoop() {
        Bukkit.getScheduler().runTaskLater(plugin, this::cleanupOrphanBarriers, 20L);
        this.watchLoop = Bukkit.getScheduler().runTaskTimer(plugin, () -> {
            watchTick++;
            long now = System.currentTimeMillis();
            for (Map.Entry<UUID, HoloSession> entry : new ArrayList<>(sessions.entrySet())) {
                Player p = Bukkit.getPlayer(entry.getKey());
                HoloSession s = entry.getValue();
                if (p == null || !p.isOnline() || now - s.lastActivityMillis > INACTIVITY_TIMEOUT_MS) {
                    closeSession(entry.getKey(), false); continue;
                }
                if (s.needsPush || watchTick % 2 == 0) pushPhoneFrame(p, s);
            }
        }, 2L, 2L);
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onMagneticPointerMove(PlayerMoveEvent e) {
        Player p = e.getPlayer();
        HoloSession s = sessions.get(p.getUniqueId());
        if (s == null || e.getTo() == null) return;
        Location to = e.getTo();
        if (s.anchorLoc != null && (to.getWorld() != s.anchorLoc.getWorld() || to.distanceSquared(s.anchorLoc) > 16.0)) {
            closeSession(p.getUniqueId(), true);
            return;
        }
        if (s.wheelMode) {
            float dy = Math.abs(to.getYaw() - s.wheelYaw); if (dy > 180f) dy = 360f - dy;
            float dp = Math.abs(to.getPitch() - s.wheelPitch);
            if (dy < 3f && dp < 3f) return; // navigation molette : on ignore les micro-mouvements de souris
        }
        Location eye = to.clone().add(0, p.getEyeHeight(), 0);
        boolean wasWheel = s.wheelMode;
        s.wheelMode = false;
        if (aimPointer(p, s, eye)) {
            s.needsPush = true;
            p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.2f, 1.9f);
        } else {
            s.wheelMode = wasWheel;
        }
    }

    public static boolean isPhoneItem(ItemStack item) {
        if (item == null || !item.hasItemMeta()) return false;
        org.bukkit.inventory.meta.ItemMeta meta = item.getItemMeta();
        if (meta == null) return false;
        if (meta.isUnbreakable()) return true;
        if (meta.hasCustomModelData() && meta.getCustomModelData() == 5001) return true;
        if (meta.hasDisplayName() && meta.getDisplayName().contains("AetherPhone")) return true;
        try {
            org.bukkit.persistence.PersistentDataContainer pdc = meta.getPersistentDataContainer();
            org.bukkit.NamespacedKey key = new org.bukkit.NamespacedKey("aethercraft", "aether_phone_unbreakable");
            if (pdc.has(key, org.bukkit.persistence.PersistentDataType.BYTE) || pdc.has(key, org.bukkit.persistence.PersistentDataType.STRING)) {
                return true;
            }
        } catch (Throwable ignored) {}
        return false;
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void onPlayerItemDamage(PlayerItemDamageEvent event) {
        if (sessions.containsKey(event.getPlayer().getUniqueId())) {
            event.setCancelled(true);
            return;
        }
        ItemStack item = event.getItem();
        if (item != null && item.hasItemMeta()) {
            org.bukkit.inventory.meta.ItemMeta meta = item.getItemMeta();
            if (meta != null) {
                if (meta.isUnbreakable() || (meta.hasCustomModelData() && meta.getCustomModelData() == 5001)) {
                    event.setCancelled(true);
                    return;
                }
            }
            if (isPhoneItem(item)) {
                event.setCancelled(true);
                return;
            }
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = false)
    public void onBlockDamageWhilePhoneOpen(org.bukkit.event.block.BlockDamageEvent e) {
        if (sessions.containsKey(e.getPlayer().getUniqueId())) {
            e.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = false)
    public void onBlockActionWhilePhoneOpen(org.bukkit.event.block.BlockBreakEvent e) {
        if (sessions.containsKey(e.getPlayer().getUniqueId())) {
            e.setCancelled(true);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST)
    public void onArmSwing(org.bukkit.event.player.PlayerAnimationEvent e) {
        Player p = e.getPlayer();
        HoloSession s = sessions.get(p.getUniqueId());
        if (s == null) return;
        if (e.getAnimationType() == org.bukkit.event.player.PlayerAnimationType.ARM_SWING) {
            long now = System.currentTimeMillis();
            if (now - s.lastClickMillis < 220L || now - s.lastModeSwitchMillis < 220L) return;
            s.lastClickMillis = now;
            aimPointer(p, s, p.getEyeLocation());
            p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.75f, 1.5f);
            AetherPhoneCanvasRenderer.handleLeftClick(this, p, s);
        }
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = false)
    public void onPhoneClick(PlayerInteractEvent e) {
        Player p = e.getPlayer();
        HoloSession s = sessions.get(p.getUniqueId());
        if (s == null) return;
        e.setCancelled(true);
        if (e.getHand() == org.bukkit.inventory.EquipmentSlot.OFF_HAND) return;

        Action act = e.getAction();
        if (act != Action.RIGHT_CLICK_AIR && act != Action.RIGHT_CLICK_BLOCK) {
            // Clics gauches gérés exclusivement par onArmSwing pour éviter toute double exécution
            return;
        }

        long now = System.currentTimeMillis();
        if (now - s.lastClickMillis < 220L || now - s.lastModeSwitchMillis < 220L) return;
        s.lastClickMillis = now;
        aimPointer(p, s, p.getEyeLocation());
        AetherPhoneCanvasRenderer.handleRightClickCycleMode(this, p, s);
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void onEntityClickWhilePhoneOpen(PlayerInteractEntityEvent e) {
        HoloSession s = sessions.get(e.getPlayer().getUniqueId());
        if (s != null) { e.setCancelled(true); AetherPhoneCanvasRenderer.handleRightClickCycleMode(this, e.getPlayer(), s); }
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void onEntityHitWhilePhoneOpen(EntityDamageByEntityEvent e) {
        if (e.getDamager() instanceof Player p && sessions.containsKey(p.getUniqueId())) {
            e.setCancelled(true);
            AetherPhoneCanvasRenderer.handleLeftClick(this, p, sessions.get(p.getUniqueId()));
        }
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void onHotbarScroll(PlayerItemHeldEvent e) {
        Player p = e.getPlayer();
        HoloSession s = sessions.get(p.getUniqueId());
        if (s == null) return;
        e.setCancelled(true);
        int newSlot = e.getNewSlot();
        int totalCards = Math.max(1, AetherPhoneCanvasRenderer.buildCards(s).size());
        if (newSlot >= 0 && newSlot < totalCards) {
            s.dockFocused = false;
            s.selectedIndex = newSlot;
            s.wheelMode = true;
            s.wheelYaw = p.getLocation().getYaw();
            s.wheelPitch = p.getLocation().getPitch();
            AetherPhoneCanvasRenderer.snapCursorToSelectedCard(s);
            p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.35f, 1.8f);
            pushPhoneFrame(p, s);
            return;
        }
        int d = ((e.getNewSlot() - e.getPreviousSlot()) % 9 + 9) % 9;
        int delta = (d == 0) ? 0 : (d <= 4 ? 1 : -1);
        if (delta == 0) return;
        s.touchActivity();
        AetherPhoneCanvasRenderer.stepSelection(s, delta);
        s.wheelYaw = p.getLocation().getYaw();
        s.wheelPitch = p.getLocation().getPitch();
        p.playSound(p.getLocation(), Sound.UI_BUTTON_CLICK, 0.35f, 1.8f);
        pushPhoneFrame(p, s);
    }

    @EventHandler(priority = EventPriority.LOWEST) public void onSwapHand(PlayerSwapHandItemsEvent e) { HoloSession s = sessions.get(e.getPlayer().getUniqueId()); if (s != null) { e.setCancelled(true); AetherPhoneCanvasRenderer.cycleSubFilter(this, e.getPlayer(), s); } }
    @EventHandler(priority = EventPriority.LOWEST) public void onDropPhone(PlayerDropItemEvent e) { if (sessions.containsKey(e.getPlayer().getUniqueId())) { e.setCancelled(true); closeSession(e.getPlayer().getUniqueId(), true); } }
    @EventHandler(priority = EventPriority.LOWEST) public void onInventoryClick(InventoryClickEvent e) { if (e.getWhoClicked() instanceof Player p && sessions.containsKey(p.getUniqueId())) e.setCancelled(true); }
    @EventHandler(priority = EventPriority.LOWEST) public void onInventoryClose(InventoryCloseEvent e) { if (sessions.containsKey(e.getPlayer().getUniqueId())) closeSession(e.getPlayer().getUniqueId(), true); }
    @EventHandler(priority = EventPriority.LOWEST) public void onInventoryOpen(org.bukkit.event.inventory.InventoryOpenEvent e) { if (sessions.containsKey(e.getPlayer().getUniqueId())) closeSession(e.getPlayer().getUniqueId(), false); }
    @EventHandler public void onSneakClose(PlayerToggleSneakEvent e) { if (e.isSneaking() && sessions.containsKey(e.getPlayer().getUniqueId())) closeSession(e.getPlayer().getUniqueId(), true); }
    @EventHandler public void onWorldChange(PlayerChangedWorldEvent e) { closeSession(e.getPlayer().getUniqueId(), false); }
    @EventHandler public void onPlayerDeath(PlayerDeathEvent e) { closeSession(e.getEntity().getUniqueId(), false); }
    @EventHandler public void onQuit(PlayerQuitEvent e) { closeSession(e.getPlayer().getUniqueId(), false); }
}
