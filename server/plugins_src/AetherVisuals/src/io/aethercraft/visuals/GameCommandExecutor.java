package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Location;
import org.bukkit.Sound;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;

public class GameCommandExecutor implements CommandExecutor {

    private final ChatQuizEngine quizEngine;
    private final AetherHoloUIEngine holoEngine;
    private SpawnAmbianceEngine spawnAmbianceEngine;

    public GameCommandExecutor(ChatQuizEngine quizEngine, AetherHoloUIEngine holoEngine) {
        this.quizEngine = quizEngine;
        this.holoEngine = holoEngine;
    }

    public void setSpawnAmbianceEngine(SpawnAmbianceEngine spawnAmbianceEngine) {
        this.spawnAmbianceEngine = spawnAmbianceEngine;
    }

    private boolean checkAdmin(CommandSender sender) {
        if (!(sender instanceof Player) || sender.isOp() || sender.hasPermission("aether.admin")) {
            return true;
        }
        sender.sendMessage(ChatColor.RED + "❌ Accès refusé : permission 'aether.admin' ou OP requise.");
        return false;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        String cmd = command.getName().toLowerCase();
        switch (cmd) {
            case "quest": case "quests": case "quetes": return handleQuest(sender, args);
            case "dungeon": case "dungeons": case "donjon": return handleDungeon(sender, args);
            case "achievement": case "achievements": case "succes": return handleAchievement(sender);
            case "quiz": case "trivia": case "aetherquiz": return handleQuiz(sender, args);
            case "spawnmode": case "ambiance": case "modespawn": return handleSpawnMode(sender, args);
            default: return false;
        }
    }

    private boolean handleSpawnMode(CommandSender sender, String[] args) {
        if (spawnAmbianceEngine == null) return true;
        if (args.length == 0 || args[0].equalsIgnoreCase("status")) {
            sender.sendMessage(ChatColor.GOLD + "✦ Mode Spawn Actif : " + ChatColor.AQUA + spawnAmbianceEngine.getCurrentMode().label);
            sender.sendMessage(ChatColor.GRAY + "Usage : /spawnmode <sanctuary|festival|cyber|aurora|training|cycle>");
            return true;
        }
        String sub = args[0].toLowerCase();
        if (sub.equals("cycle") || sub.equals("next")) {
            spawnAmbianceEngine.cycleMode(sender);
            return true;
        }
        for (SpawnAmbianceEngine.SpawnMode m : SpawnAmbianceEngine.SpawnMode.values()) {
            if (m.name().equalsIgnoreCase(sub)) {
                spawnAmbianceEngine.setMode(m, sender);
                return true;
            }
        }
        sender.sendMessage(ChatColor.RED + "Mode inconnu. Choisissez : sanctuary, festival, cyber, aurora, training, cycle.");
        return true;
    }

    private boolean handleQuest(CommandSender sender, String[] args) {
        if (args.length >= 3 && args[0].equalsIgnoreCase("progress")) {
            if (!checkAdmin(sender)) return true;
            Player target = Bukkit.getPlayer(args[1]);
            String qid = args[2].toLowerCase();
            int amount = 1;
            if (args.length >= 4) {
                try { amount = Integer.parseInt(args[3]); } catch (Exception ignored) {}
            }
            if (target != null) {
                target.playSound(target.getLocation(), Sound.ENTITY_EXPERIENCE_ORB_PICKUP, 1.0f, 1.4f);
                target.sendMessage(ChatColor.GOLD + "✦ " + ChatColor.YELLOW + "Progression Quête Céleste [" + qid + "] : " + ChatColor.GREEN + "+" + amount);
            }
            sender.sendMessage(ChatColor.GREEN + "Progression ajoutée pour " + args[1] + " (" + qid + " +" + amount + ")");
            return true;
        }
        if (sender instanceof Player p && holoEngine != null) {
            holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.PROFILE, "quests");
            return true;
        }
        sender.sendMessage(ChatColor.GOLD + "★ Quêtes Célestes actives sur votre espace joueur.");
        return true;
    }

    private boolean handleDungeon(CommandSender sender, String[] args) {
        if (args.length >= 2 && (args[0].equalsIgnoreCase("start") || args[0].equalsIgnoreCase("enter"))) {
            Player target = (args.length >= 3) ? Bukkit.getPlayer(args[1]) : (sender instanceof Player ? (Player) sender : null);
            String dungId = (args.length >= 3) ? args[2].toLowerCase() : args[1].toLowerCase();
            if (args.length >= 3 && !checkAdmin(sender)) return true;
            if (target == null) {
                sender.sendMessage(ChatColor.RED + "Joueur cible introuvable.");
                return true;
            }
            Location loc = new Location(target.getWorld(), 0.5, 121.0, 15.5);
            target.teleport(loc);
            target.playSound(loc, Sound.ENTITY_ENDER_DRAGON_GROWL, 1.0f, 1.0f);
            target.sendTitle(ChatColor.RED + "⚔️ DONJON INSTANCIÉ", ChatColor.GOLD + dungId.toUpperCase(), 10, 70, 20);
            return true;
        }
        sender.sendMessage(ChatColor.RED + "✦ Donjons Célestes : Sanctuaire de l'Aetherite, Citadelle du Titan, Faille du Dragon.");
        return true;
    }

    private boolean handleAchievement(CommandSender sender) {
        if (sender instanceof Player p && holoEngine != null) {
            holoEngine.openHoloUI(p, AetherHoloUIEngine.HoloMode.PROFILE, "achievements");
            return true;
        }
        sender.sendMessage(ChatColor.GOLD + "🏆 Consultez vos trophées sur votre profil joueur.");
        return true;
    }

    private boolean handleQuiz(CommandSender sender, String[] args) {
        if (args.length >= 1 && (args[0].equalsIgnoreCase("start") || args[0].equalsIgnoreCase("ask") || args[0].equalsIgnoreCase("next"))) {
            if (!checkAdmin(sender)) return true;
            if (quizEngine != null) {
                quizEngine.triggerQuizQuestion();
                sender.sendMessage(ChatColor.GREEN + "✦ Nouvelle question Trivia Aether lancée dans le chat !");
            }
            return true;
        }

        if (args.length >= 1 && args[0].equalsIgnoreCase("stop")) {
            if (!checkAdmin(sender)) return true;
            if (quizEngine != null) {
                quizEngine.stop();
                sender.sendMessage(ChatColor.YELLOW + "✦ Quiz interrompu.");
            }
            return true;
        }

        if (quizEngine != null && quizEngine.isQuestionActive() && quizEngine.getActiveQuestion() != null) {
            sender.sendMessage(ChatColor.GOLD + "★ Quiz en cours : " + ChatColor.WHITE + quizEngine.getActiveQuestion().getQuestion());
            sender.sendMessage(ChatColor.YELLOW + "Répondez directement dans le chat pour gagner 5 Jetons Boutique !");
        } else {
            sender.sendMessage(ChatColor.GOLD + "★ Aether Trivia Quiz :");
            sender.sendMessage(ChatColor.YELLOW + "Une question est posée toutes les 30 à 60 minutes dans le chat.");
            sender.sendMessage(ChatColor.AQUA + "Le premier joueur qui répond correctement remporte 5 Jetons Boutique !");
        }
        return true;
    }
}
