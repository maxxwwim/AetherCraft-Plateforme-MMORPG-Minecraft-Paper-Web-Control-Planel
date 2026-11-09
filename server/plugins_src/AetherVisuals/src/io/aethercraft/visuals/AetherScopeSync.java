package io.aethercraft.visuals;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Consumer;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.bukkit.Bukkit;

/**
 * Passerelle asynchrone de synchronisation entre le serveur Paper 1.21.x et l'agent AetherScope MCP.
 * Émet la télémétrie opérationnelle (TPS, nombre de joueurs, alertes de triche) vers http://127.0.0.1:3030.
 * Conforme aux contraintes LocalGuard (Host, Origin locale, Sec-Fetch-Site anti-CSRF).
 */
public class AetherScopeSync {

    private static final String DEFAULT_HOST = "127.0.0.1";
    private static final int DEFAULT_PORT = 3030;
    private static final String BASE_URL = "http://" + DEFAULT_HOST + ":" + DEFAULT_PORT;
    private static final Duration TIMEOUT = Duration.ofSeconds(2);

    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "AetherScope-Sync-Thread");
        t.setDaemon(true);
        return t;
    });

    private static final HttpClient HTTP_CLIENT = HttpClient.newBuilder()
            .executor(EXECUTOR)
            .connectTimeout(TIMEOUT)
            .build();

    private static Logger getLogger() {
        try {
            if (Bukkit.getServer() != null) {
                return Bukkit.getLogger();
            }
        } catch (Throwable ignored) {
        }
        return Logger.getLogger("AetherScopeSync");
    }

    /**
     * Vérifie la conformité LocalGuard pour une autorité locale donnée.
     */
    public static boolean isLocalGuardCompliant(String host, String origin) {
        if (host == null) return false;
        String h = host.trim().toLowerCase();
        boolean hostOk = h.equals("127.0.0.1:" + DEFAULT_PORT) ||
                         h.equals("localhost:" + DEFAULT_PORT) ||
                         h.equals("[::1]:" + DEFAULT_PORT);
        if (!hostOk) return false;

        if (origin != null) {
            String o = origin.trim().toLowerCase();
            return o.equals("http://127.0.0.1:" + DEFAULT_PORT) ||
                   o.equals("http://localhost:" + DEFAULT_PORT) ||
                   o.equals("http://[::1]:" + DEFAULT_PORT);
        }
        return true;
    }

    /**
     * Envoie une requête POST JSON asynchrone avec les en-têtes requis par LocalGuard.
     */
    private static CompletableFuture<String> postJsonAsync(String endpoint, String jsonPayload) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                String authority = DEFAULT_HOST + ":" + DEFAULT_PORT;
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(BASE_URL + endpoint))
                        .timeout(TIMEOUT)
                        .header("Host", authority)
                        .header("Origin", "http://" + authority)
                        .header("Sec-Fetch-Site", "same-origin")
                        .header("User-Agent", "AetherCraft-Java-Sync/1.0")
                        .header("Content-Type", "application/json; charset=utf-8")
                        .header("Accept", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(jsonPayload))
                        .build();

                HttpResponse<String> response = HTTP_CLIENT.send(request, HttpResponse.BodyHandlers.ofString());
                if (response.statusCode() >= 200 && response.statusCode() < 300) {
                    return response.body();
                } else {
                    getLogger().log(Level.FINE, "[AetherScope] Réponse HTTP inattendue " + response.statusCode() + " sur " + endpoint);
                    return null;
                }
            } catch (Exception e) {
                // Échec silencieux / dégradé gracieux : n'interrompt jamais l'exécution du serveur Paper
                getLogger().log(Level.FINE, "[AetherScope] Serveur MCP non joignable sur " + endpoint + ": " + e.getMessage());
                return null;
            }
        }, EXECUTOR);
    }

    /**
     * Émet un événement de télémétrie spatiale vers AetherScope (POST /api/ai/telemetry).
     */
    public static CompletableFuture<Boolean> sendTelemetryAsync(String target, String action, String details) {
        long now = System.currentTimeMillis();
        String escapedDetails = details.replace("\"", "\\\"");
        String payload = String.format(
                "{\"target\":\"%s\",\"action\":\"%s\",\"details\":\"%s\",\"timestamp\":%d}",
                target, action, escapedDetails, now
        );
        return postJsonAsync("/api/ai/telemetry", payload)
                .thenApply(res -> res != null);
    }

    /**
     * Émet une alerte de sécurité Anti-Cheat vers la télémétrie spatiale et le HUD chat AetherScope.
     */
    public static void sendSecurityAlertAsync(String player, String violationType, String details) {
        sendTelemetryAsync(
                "AntiCheatEngine",
                "Violation:" + violationType,
                "Alerte joueur '" + player + "' pour " + violationType + ": " + details
        );

        String chatPayload = String.format(
                "{\"text\":\"[ANTI-CHEAT] Alerte: Joueur '%s' flag pour %s: %s\",\"sender\":\"AetherAntiCheat\",\"target_symbol\":\"AntiCheatEngine\"}",
                player, violationType, details.replace("\"", "\\\"")
        );
        postJsonAsync("/api/ai/chat", chatPayload);
    }

    /**
     * Synchronise les métriques de performance (TPS et joueurs actifs) vers AetherScope.
     */
    public static void sendTpsStatusAsync(double tps, int activePlayers) {
        String details = String.format("Paper Server TPS: %.2f | Joueurs: %d", tps, activePlayers);
        sendTelemetryAsync("PaperEngine", "TpsSync", details);
    }

    /**
     * Sonde de disponibilité asynchrone (GET /api/health).
     */
    public static void checkHealthAsync(Consumer<Boolean> callback) {
        CompletableFuture.runAsync(() -> {
            try {
                String authority = DEFAULT_HOST + ":" + DEFAULT_PORT;
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(BASE_URL + "/api/health"))
                        .timeout(TIMEOUT)
                        .header("Host", authority)
                        .header("Origin", "http://" + authority)
                        .header("User-Agent", "AetherCraft-Java-Sync/1.0")
                        .header("Accept", "application/json")
                        .GET()
                        .build();

                HttpResponse<String> response = HTTP_CLIENT.send(request, HttpResponse.BodyHandlers.ofString());
                boolean ok = response.statusCode() == 200 && response.body().contains("\"status\":\"ok\"");
                if (callback != null) {
                    callback.accept(ok);
                }
            } catch (Exception e) {
                if (callback != null) {
                    callback.accept(false);
                }
            }
        }, EXECUTOR);
    }
}
