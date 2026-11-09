package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.AsyncPlayerChatEvent;
import org.bukkit.scheduler.BukkitTask;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.text.Normalizer;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Moteur de Quiz Trivia Céleste interactif pour AetherCraft.
 */
public class ChatQuizEngine implements Listener {

    public static class QuizQuestion {
        private final String question;
        private final String displayAnswer;
        private final List<String> variants;

        public QuizQuestion(String question, String displayAnswer, String... variants) {
            this.question = question;
            this.displayAnswer = displayAnswer;
            this.variants = new ArrayList<>();
            for (String v : variants) {
                this.variants.add(normalize(v));
            }
            this.variants.add(normalize(displayAnswer));
        }

        public String getQuestion() { return question; }
        public String getDisplayAnswer() { return displayAnswer; }
        public List<String> getVariants() { return variants; }
    }

    private final AetherVisualsPlugin plugin;
    private final List<QuizQuestion> questionPool = new ArrayList<>();
    private final List<QuizQuestion> recentQuestions = new ArrayList<>();

    private QuizQuestion activeQuestion = null;
    private boolean isQuestionActive = false;
    private BukkitTask scheduledTask = null;
    private BukkitTask timeoutTask = null;

    public ChatQuizEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
        initQuestions();
    }

    private void initQuestions() {
        ChatQuizCatalog.populateQuestions(questionPool);
    }

    public void startAutoScheduler() {
        scheduleNextQuestion(1200L);
    }

    private void scheduleNextQuestion(long delayTicks) {
        if (scheduledTask != null) scheduledTask.cancel();
        scheduledTask = Bukkit.getScheduler().runTaskLater(plugin, () -> {
            triggerQuizQuestion();
            long nextDelay = ThreadLocalRandom.current().nextLong(36000L, 72001L);
            scheduleNextQuestion(nextDelay);
        }, delayTicks);
    }

    public synchronized boolean triggerQuizQuestion() {
        if (questionPool.isEmpty()) initQuestions();
        List<QuizQuestion> candidates = new ArrayList<>(questionPool);
        candidates.removeAll(recentQuestions);
        if (candidates.isEmpty()) {
            recentQuestions.clear();
            candidates.addAll(questionPool);
        }

        QuizQuestion q = candidates.get(ThreadLocalRandom.current().nextInt(candidates.size()));
        activeQuestion = q;
        isQuestionActive = true;
        recentQuestions.add(q);
        if (recentQuestions.size() > 10) recentQuestions.remove(0);

        broadcastQuizAnnouncement(q);
        if (timeoutTask != null) timeoutTask.cancel();
        timeoutTask = Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (isQuestionActive && activeQuestion == q) {
                isQuestionActive = false;
                Bukkit.broadcastMessage("§8[§6★ AETHER TRIVIA ★§8] §cTemps écoulé ! §7Personne n'a trouvé la bonne réponse : §e" + q.getDisplayAnswer());
                activeQuestion = null;
            }
        }, 1800L);
        return true;
    }

    private void broadcastQuizAnnouncement(QuizQuestion q) {
        Bukkit.broadcastMessage("§8§m--------------------------------------------------");
        Bukkit.broadcastMessage(" §6★ §lAETHER TRIVIA QUIZ §r§e— QUESTION DU SPHINX");
        Bukkit.broadcastMessage(" §f" + q.getQuestion());
        Bukkit.broadcastMessage(" §7Répondez directement dans le chat !");
        Bukkit.broadcastMessage(" §6🎁 Premier joueur correct : §a+5 Jetons Boutique §7(Site)");
        Bukkit.broadcastMessage("§8§m--------------------------------------------------");
        for (Player p : Bukkit.getOnlinePlayers()) {
            p.playSound(p.getLocation(), Sound.BLOCK_NOTE_BLOCK_CHIME, 1.0f, 1.5f);
        }
    }

    @EventHandler(priority = EventPriority.LOW)
    public void onPlayerChat(AsyncPlayerChatEvent event) {
        if (!isQuestionActive || activeQuestion == null) return;
        Player player = event.getPlayer();
        String message = event.getMessage();

        if (isCorrectAnswer(message, activeQuestion)) {
            synchronized (this) {
                if (!isQuestionActive) return;
                isQuestionActive = false;
                QuizQuestion answered = activeQuestion;
                activeQuestion = null;
                if (timeoutTask != null) timeoutTask.cancel();

                Bukkit.getScheduler().runTask(plugin, () -> {
                    Bukkit.broadcastMessage("§8§m--------------------------------------------------");
                    Bukkit.broadcastMessage(" §6★ §lAETHER TRIVIA QUIZ §r§e— BONNE RÉPONSE !");
                    Bukkit.broadcastMessage(" §a✦ Félicitations à §e" + player.getName() + " §aqu'a trouvé en premier !");
                    Bukkit.broadcastMessage(" §fRéponse attendue : §b" + answered.getDisplayAnswer());
                    Bukkit.broadcastMessage(" §6🎁 Gain : §e+5 Jetons Boutique §aajoutés à son compte web !");
                    Bukkit.broadcastMessage("§8§m--------------------------------------------------");
                    player.sendTitle("§6★ BRAVO ! ★", "§e+5 Jetons Boutique §7(Aether Quiz)", 10, 60, 20);
                    player.playSound(player.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.0f);
                    player.playSound(player.getLocation(), Sound.ENTITY_PLAYER_LEVELUP, 1.0f, 1.2f);
                });
                creditQuizReward(player.getName(), answered.getQuestion(), answered.getDisplayAnswer());
            }
        }
    }

    private boolean isCorrectAnswer(String input, QuizQuestion q) {
        if (input == null || input.trim().isEmpty()) return false;
        String normalizedInput = normalize(input);
        Set<String> wordSet = new HashSet<>(Arrays.asList(normalizedInput.split(" ")));
        for (String variant : q.getVariants()) {
            if (normalizedInput.equals(variant) || wordSet.contains(variant)) return true;
            if (variant.length() >= 4 && normalizedInput.contains(variant)) return true;
        }
        return false;
    }

    private void creditQuizReward(String username, String question, String answer) {
        Bukkit.getScheduler().runTaskAsynchronously(plugin, () -> {
            try (Connection conn = AetherDatabase.getConnection()) {
                try (Statement st = conn.createStatement()) {
                    st.executeUpdate("CREATE TABLE IF NOT EXISTS quiz_winners (" +
                            "id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, question TEXT NOT NULL, " +
                            "answer TEXT NOT NULL, points INTEGER NOT NULL DEFAULT 5, won_at TEXT NOT NULL);");
                }
                int updatedRows;
                try (PreparedStatement ps = conn.prepareStatement(
                        "UPDATE users SET shop_points = shop_points + 5 WHERE LOWER(minecraft_username) = LOWER(?);")) {
                    ps.setString(1, username);
                    updatedRows = ps.executeUpdate();
                }
                try (PreparedStatement ps = conn.prepareStatement(
                        "INSERT INTO quiz_winners (username, question, answer, points, won_at) VALUES (?, ?, ?, 5, datetime('now'));")) {
                    ps.setString(1, username);
                    ps.setString(2, question);
                    ps.setString(3, answer);
                    ps.executeUpdate();
                }
                plugin.getLogger().info("[Quiz] 5 jetons attribués avec succès à " + username + " (comptes mis à jour: " + updatedRows + ")");
            } catch (Exception e) {
                plugin.getLogger().warning("[Quiz] Impossible de mettre à jour SQLite (" + e.getMessage() + ")");
            }
        });
    }

    public static String normalize(String str) {
        if (str == null) return "";
        String nfd = Normalizer.normalize(str, Normalizer.Form.NFD);
        String noAccents = nfd.replaceAll("\\p{M}", "");
        return noAccents.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9 ]", " ").trim().replaceAll("\\s+", " ");
    }

    public boolean isQuestionActive() { return isQuestionActive; }
    public QuizQuestion getActiveQuestion() { return activeQuestion; }

    public void stop() {
        if (scheduledTask != null) scheduledTask.cancel();
        if (timeoutTask != null) timeoutTask.cancel();
        isQuestionActive = false;
        activeQuestion = null;
    }
}
