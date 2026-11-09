package io.aethercraft.visuals;

import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class AetherTabCompleter implements TabCompleter {

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        String cmd = command.getName().toLowerCase();
        List<String> list = new ArrayList<>();
        boolean isAdmin = !sender.hasPermission("aether.admin") && !sender.isOp();
        if (cmd.equals("cosmetics") && args.length == 1) {
            list.addAll(Arrays.asList("wings", "pet", "clear"));
            if (!isAdmin) list.add("unlock");
        } else if (cmd.equals("pet") && args.length == 1) {
            list.addAll(Arrays.asList("dragon", "capybara", "fox", "goat", "phoenix", "clear"));
        } else if (cmd.equals("aura") && args.length == 1) {
            list.addAll(Arrays.asList("vip", "aether", "titan", "champion", "clear"));
        } else if (cmd.equals("crate") && args.length == 1) {
            list.add("open");
            if (!isAdmin) list.add("give");
        } else if ((cmd.equals("webdisplay") || cmd.equals("ecran") || cmd.equals("screen")) && args.length == 1) {
            list.addAll(Arrays.asList("shop", "market", "ores", "profile", "cockpit", "close"));
        } else if ((cmd.equals("shop") || cmd.equals("boutique") || cmd.equals("store")) && args.length == 1) {
            list.addAll(Arrays.asList("ores", "ah", "menu", "web"));
            if (!isAdmin) list.add("give");
        } else if (cmd.equals("marche") && args.length == 1) {
            list.addAll(Arrays.asList("sell", "ores", "bourse"));
        } else if ((cmd.equals("survie") || cmd.equals("survival")) && args.length == 1) {
            list.add("regen");
        } else if ((cmd.equals("spawnmode") || cmd.equals("ambiance") || cmd.equals("modespawn")) && args.length == 1) {
            list.addAll(Arrays.asList("sanctuary", "festival", "cyber", "aurora", "training", "cycle", "status"));
        } else if ((cmd.equals("top") || cmd.equals("baltop") || cmd.equals("classement") || cmd.equals("classements")) && args.length == 1) {
            list.addAll(Arrays.asList("oneblock", "fortune", "temps", "kills", "playtime", "pvp"));
        } else if ((cmd.equals("menu") || cmd.equals("phone")) && args.length == 1) {
            list.addAll(Arrays.asList("shop", "animaux", "top", "hdv", "bourse", "profil"));
        } else if ((cmd.equals("oneblock") || cmd.equals("ob") || cmd.equals("island") || cmd.equals("ile")) && args.length == 1) {
            list.addAll(Arrays.asList("home", "spawn", "info", "invite", "rebuild", "stats"));
        }
        return list;
    }
}
