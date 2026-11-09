package io.aethercraft.visuals;

import net.md_5.bungee.api.ChatMessageType;
import net.md_5.bungee.api.chat.ClickEvent;
import net.md_5.bungee.api.chat.ComponentBuilder;
import net.md_5.bungee.api.chat.HoverEvent;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerToggleSneakEvent;
import org.bukkit.plugin.Plugin;
import org.bukkit.util.Vector;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Gestionnaire d'Écran WebDisplay UHD (MapBrowser JCEF / Écran HTML 16:9 Interactif).
 * Déploie face au joueur un véritable écran Chromium connecté à la Boutique, l'HDV et la Bourse.
 */
public class AetherWebDisplayManager implements Listener {

    private final AetherVisualsPlugin plugin;
    private final Map<UUID, Integer> activeDisplayIds = new ConcurrentHashMap<>();
    private static final String BASE_URL = "http://127.0.0.1:5000/webdisplay";

    public AetherWebDisplayManager(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
    }

    public boolean openOrToggleWebDisplay(Player p, String mode) {
        if (activeDisplayIds.containsKey(p.getUniqueId())) {
            closeWebDisplay(p, true);
            return false;
        }

        String safeMode = (mode != null && !mode.isEmpty()) ? mode.toLowerCase() : "cockpit";
        long ts = System.currentTimeMillis() / 1000L;
        String token = generateAuthToken(p.getName(), ts);
        String targetUrl = BASE_URL + "?player=" + p.getName() + "&mode=" + safeMode + "&ts=" + ts + "&token=" + token + "&phone=1";

        boolean spawnedMapBrowser = spawnMapBrowserScreen(p, targetUrl);
        sendWebDisplayPrompts(p, targetUrl, spawnedMapBrowser);
        p.playSound(p.getLocation(), Sound.BLOCK_BEACON_ACTIVATE, 0.85f, 1.4f);
        return true;
    }

    public static String generateAuthToken(String username, long ts) {
        try {
            String envKey = System.getenv("AETHER_AUTH_KEY");
            String key = (envKey != null && !envKey.trim().isEmpty()) ? envKey.trim() : "aethercraft_session_hmac_2026";
            String data = username.toLowerCase() + ":" + ts;
            javax.crypto.Mac mac = javax.crypto.Mac.getInstance("HmacSHA256");
            mac.init(new javax.crypto.spec.SecretKeySpec(key.getBytes(java.nio.charset.StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] bytes = mac.doFinal(data.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder(bytes.length * 2);
            for (byte b : bytes) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            return "fallback";
        }
    }

    private boolean spawnMapBrowserScreen(Player p, String targetUrl) {
        try {
            Plugin mb = Bukkit.getPluginManager().getPlugin("MapBrowser");
            if (mb == null || !mb.isEnabled()) return false;

            Field dsField = mb.getClass().getDeclaredField("displayService");
            dsField.setAccessible(true);
            Object displayService = dsField.get(mb);
            if (displayService == null) return false;

            Location eyeLoc = p.getEyeLocation().clone();
            Vector dir = eyeLoc.getDirection().setY(0).normalize();
            Location screenLoc = eyeLoc.add(dir.multiply(2.2));

            Method createMethod = displayService.getClass().getMethod(
                    "createAndInitializeDisplay",
                    Player.class, String.class, Location.class, int.class, int.class
            );

            // Timeout strict de 250ms pour ne JAMAIS figer le thread serveur principal de Paper
            java.util.concurrent.Future<Object> future = java.util.concurrent.CompletableFuture.supplyAsync(() -> {
                try {
                    return createMethod.invoke(displayService, p, targetUrl, screenLoc, 16, 9);
                } catch (Throwable t) {
                    return null;
                }
            });

            Object displayObj = future.get(250, java.util.concurrent.TimeUnit.MILLISECONDS);
            if (displayObj != null) {
                Method getIdMethod = displayObj.getClass().getMethod("getId");
                int id = (int) getIdMethod.invoke(displayObj);
                activeDisplayIds.put(p.getUniqueId(), id);
                return true;
            }
        } catch (Throwable ignored) {}
        return false;
    }

    public void sendWebDisplayNotice(Player p, String mode) {
        String safeMode = (mode != null && !mode.isEmpty()) ? mode.toLowerCase() : "cockpit";
        long ts = System.currentTimeMillis() / 1000L;
        String token = generateAuthToken(p.getName(), ts);
        String targetUrl = BASE_URL + "?player=" + p.getName() + "&mode=" + safeMode + "&ts=" + ts + "&token=" + token + "&phone=1";

        TextComponent msg = new TextComponent("§b§l🖥️ [AETHER WEBDISPLAY UHD] §7Version Web 16:9 : ");
        TextComponent link = new TextComponent("§e§nCliquez ici pour ouvrir l'écran interactif");
        link.setClickEvent(new ClickEvent(ClickEvent.Action.OPEN_URL, targetUrl));
        link.setHoverEvent(new HoverEvent(HoverEvent.Action.SHOW_TEXT,
                new ComponentBuilder("§aOuvrir le Menu UHD 16:9 interactif avec navigation Clavier / Souris").create()));
        msg.addExtra(link);
        p.spigot().sendMessage(msg);
    }

    public void closeWebDisplay(Player p, boolean sound) {
        Integer id = activeDisplayIds.remove(p.getUniqueId());
        if (id != null) {
            removeMapBrowserDisplay(id);
            if (sound) p.playSound(p.getLocation(), Sound.BLOCK_BEACON_DEACTIVATE, 0.75f, 1.6f);
            p.sendMessage("§7✦ Écran WebDisplay refermé.");
        }
    }

    private void removeMapBrowserDisplay(int id) {
        try {
            Plugin mb = Bukkit.getPluginManager().getPlugin("MapBrowser");
            if (mb == null || !mb.isEnabled()) return;
            Field dsField = mb.getClass().getDeclaredField("displayService");
            dsField.setAccessible(true);
            Object displayService = dsField.get(mb);
            if (displayService != null) {
                Method removeMethod = displayService.getClass().getMethod("removeDisplay", int.class);
                removeMethod.invoke(displayService, id);
            }
        } catch (Throwable ignored) {}
    }

    private void sendWebDisplayPrompts(Player p, String url, boolean hasScreen3D) {
        if (hasScreen3D) {
            p.spigot().sendMessage(ChatMessageType.ACTION_BAR,
                    TextComponent.fromLegacy("§b🖥️ Écran WebDisplay UHD Actif §8| §aRegardez & Clic 1-touch §8| §c[Sneak]: Fermer"));
        } else {
            p.spigot().sendMessage(ChatMessageType.ACTION_BAR,
                    TextComponent.fromLegacy("§b🖥️ Interface WebDisplay UHD Prête §8| §eConsultez le Chat"));
        }

        TextComponent msg = new TextComponent("§b§l🖥️ [AETHER WEBDISPLAY UHD] §7Cliquez pour ouvrir l'interface HTML : ");
        TextComponent link = new TextComponent("§e§n" + url);
        link.setClickEvent(new ClickEvent(ClickEvent.Action.OPEN_URL, url));
        link.setHoverEvent(new HoverEvent(HoverEvent.Action.SHOW_TEXT,
                new ComponentBuilder("§aOuvrir la Boutique UHD 16:9 dans votre navigateur ou mod WebDisplays").create()));
        msg.addExtra(link);
        p.spigot().sendMessage(msg);
    }

    public void closeAll() {
        for (UUID uuid : activeDisplayIds.keySet()) {
            Player p = Bukkit.getPlayer(uuid);
            if (p != null) closeWebDisplay(p, false);
        }
        activeDisplayIds.clear();
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onPlayerSneak(PlayerToggleSneakEvent e) {
        if (e.isSneaking() && activeDisplayIds.containsKey(e.getPlayer().getUniqueId())) {
            closeWebDisplay(e.getPlayer(), true);
        }
    }

    @EventHandler
    public void onPlayerQuit(PlayerQuitEvent e) {
        closeWebDisplay(e.getPlayer(), false);
    }
}
