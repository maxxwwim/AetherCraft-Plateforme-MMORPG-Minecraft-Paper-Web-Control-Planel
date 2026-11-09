package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;

/**
 * Délégué des commandes administratives, cosmétiques, familiers, boosters et caisses.
 */
public final class AetherAdminCommandHelper {

    private AetherAdminCommandHelper() {}

    public static boolean checkAdmin(CommandSender sender) {
        if (!(sender instanceof Player) || sender.isOp() || sender.hasPermission("aether.admin")) {
            return true;
        }
        sender.sendMessage(ChatColor.RED + "❌ Accès refusé : permission 'aether.admin' ou OP requise.");
        return false;
    }

    public static boolean handleCosmetics(CommandSender sender, String[] args, CosmeticsEngine cosmeticsEngine) {
        if (args.length == 0) {
            sender.sendMessage(ChatColor.GOLD + "✦ " + ChatColor.YELLOW + "Usage: /cosmetics <wings|pet|clear|unlock> [joueur]");
            return true;
        }
        String sub = args[0].toLowerCase();
        if (sub.equals("unlock")) {
            if (!checkAdmin(sender)) return true;
            if (args.length < 3) {
                sender.sendMessage(ChatColor.YELLOW + "Usage: /cosmetics unlock <joueur> <wings|dragon>");
                return true;
            }
            Player target = Bukkit.getPlayer(args[1]);
            if (target == null) {
                sender.sendMessage(ChatColor.RED + "Joueur introuvable: " + args[1]);
                return true;
            }
            if (args[2].toLowerCase().contains("wings")) {
                cosmeticsEngine.setWings(target.getUniqueId(), true);
                target.getInventory().addItem(CustomItemFactory.createQuantumWingsItem());
                target.sendMessage(ChatColor.GREEN + "✨ Ailes Quantiques Débloquées !");
            } else {
                cosmeticsEngine.setPet(target.getUniqueId(), "dragon");
                target.getInventory().addItem(CustomItemFactory.createDragonPetItem());
                target.sendMessage(ChatColor.DARK_PURPLE + "🐉 Mini Dragon Débloqué !");
            }
            return true;
        }

        Player target = (sender instanceof Player) ? (Player) sender : null;
        if (args.length >= 2) {
            if (!checkAdmin(sender)) return true;
            target = Bukkit.getPlayer(args[1]);
        }
        if (target == null) {
            sender.sendMessage(ChatColor.RED + "Spécifiez un joueur connecté.");
            return true;
        }
        if (sub.equals("wings")) {
            cosmeticsEngine.toggleWings(target.getUniqueId());
            boolean has = cosmeticsEngine.hasWings(target.getUniqueId());
            target.sendMessage(ChatColor.AQUA + "Ailes Quantiques : " + (has ? ChatColor.GREEN + "ACTIVÉES" : ChatColor.RED + "DÉSACTIVÉES"));
        } else if (sub.equals("pet") || sub.equals("dragon")) {
            boolean has = cosmeticsEngine.hasPet(target.getUniqueId());
            cosmeticsEngine.setPet(target.getUniqueId(), has ? null : "dragon");
            target.sendMessage(ChatColor.LIGHT_PURPLE + "Mini Dragon : " + (!has ? ChatColor.GREEN + "ACTIVÉ" : ChatColor.RED + "DÉSACTIVÉ"));
        } else if (sub.equals("clear")) {
            cosmeticsEngine.clearAll(target.getUniqueId());
            target.sendMessage(ChatColor.GRAY + "Tous vos cosmétiques ont été désactivés.");
        }
        return true;
    }

    public static boolean handlePet(CommandSender sender, String[] args, CosmeticsEngine cosmeticsEngine) {
        if (args.length == 0) {
            sender.sendMessage(ChatColor.GOLD + "✦ " + ChatColor.YELLOW + "Usage: /pet <dragon|capybara|fox|goat|phoenix|clear> [joueur]");
            return true;
        }
        Player target = (sender instanceof Player) ? (Player) sender : null;
        if (args.length >= 2) {
            if (!checkAdmin(sender)) return true;
            target = Bukkit.getPlayer(args[1]);
        }
        if (target == null) {
            sender.sendMessage(ChatColor.RED + "Joueur introuvable.");
            return true;
        }
        String petType = args[0].toLowerCase();
        if (petType.equals("clear") || petType.equals("none")) {
            cosmeticsEngine.setPet(target.getUniqueId(), null);
            target.sendMessage(ChatColor.GRAY + "Votre familier céleste a été rengainé.");
        } else {
            cosmeticsEngine.setPet(target.getUniqueId(), petType);
            target.sendMessage(ChatColor.GOLD + "🐾 " + ChatColor.YELLOW + "Familier Céleste " + ChatColor.GREEN + petType.toUpperCase() + ChatColor.YELLOW + " invoqué !");
        }
        return true;
    }

    public static boolean handleAura(CommandSender sender, String[] args, CosmeticsEngine cosmeticsEngine) {
        if (args.length == 0) {
            sender.sendMessage(ChatColor.GOLD + "✦ " + ChatColor.YELLOW + "Usage: /aura <vip|aether|titan|champion|clear> [joueur]");
            return true;
        }
        Player target = (sender instanceof Player) ? (Player) sender : null;
        if (args.length >= 2) {
            if (!checkAdmin(sender)) return true;
            target = Bukkit.getPlayer(args[1]);
        }
        if (target == null) {
            sender.sendMessage(ChatColor.RED + "Joueur introuvable.");
            return true;
        }
        String auraType = args[0].toLowerCase();
        cosmeticsEngine.setAura(target.getUniqueId(), auraType);
        target.sendMessage(ChatColor.GOLD + "Aura particulaire définie sur: " + ChatColor.AQUA + auraType.toUpperCase());
        return true;
    }

    public static boolean handleBooster(CommandSender sender, String[] args, BoosterEngine boosterEngine) {
        if (!checkAdmin(sender)) return true;
        if (args.length >= 4 && args[0].equalsIgnoreCase("give")) {
            Player target = Bukkit.getPlayer(args[1]);
            if (target == null) {
                sender.sendMessage(ChatColor.RED + "Joueur introuvable: " + args[1]);
                return true;
            }
            int seconds = 7200;
            try { seconds = Integer.parseInt(args[3]); } catch (NumberFormatException ignored) {}
            boosterEngine.addMiningBooster(target.getUniqueId(), seconds);
            target.getInventory().addItem(CustomItemFactory.createMiningBoosterItem());
            target.sendMessage(ChatColor.GOLD + "⛏️ " + ChatColor.YELLOW + "Booster de Minage x2 activé (" + (seconds / 60) + " min) !");
            return true;
        }
        sender.sendMessage(ChatColor.GOLD + "Usage: /booster give <joueur> mining_2x <secondes>");
        return true;
    }

    public static boolean handleCrate(CommandSender sender, String[] args, CrateEngine crateEngine) {
        if (args.length < 2) {
            sender.sendMessage(ChatColor.GOLD + "Usage: /crate <give|open> <joueur> [celestial|omega] [quantité]");
            return true;
        }
        String action = args[0].toLowerCase();
        if (action.equals("give")) {
            if (!checkAdmin(sender)) return true;
            Player target = Bukkit.getPlayer(args[1]);
            if (target == null) {
                sender.sendMessage(ChatColor.RED + "Joueur introuvable: " + args[1]);
                return true;
            }
            String type = (args.length >= 3) ? args[2].toLowerCase() : "celestial";
            int count = 1;
            if (args.length >= 4) {
                try { count = Integer.parseInt(args[3]); } catch (Exception ignored) {}
            }
            ItemStack keys = type.contains("omega") ? CustomItemFactory.createOmegaKey(count) : CustomItemFactory.createCelestialKey(count);
            target.getInventory().addItem(keys);
            target.sendMessage(ChatColor.LIGHT_PURPLE + "🗝️ Reçu " + count + "x Clé(s) " + type.toUpperCase() + " !");
            return true;
        } else if (action.equals("open")) {
            Player target = Bukkit.getPlayer(args[1]);
            if (target == null) {
                sender.sendMessage(ChatColor.RED + "Joueur introuvable: " + args[1]);
                return true;
            }
            boolean isSelf = (sender instanceof Player) && ((Player) sender).getUniqueId().equals(target.getUniqueId());
            boolean bypass = (!isSelf || checkAdmin(sender));
            String type = (args.length >= 3) ? args[2].toLowerCase() : "celestial";
            crateEngine.startOpeningAnimation(target, type, bypass);
            return true;
        }
        return true;
    }

    public static boolean handleBuildSpawn(CommandSender sender) {
        if (!checkAdmin(sender)) return true;
        org.bukkit.World w = Bukkit.getWorlds().isEmpty() ? null : Bukkit.getWorlds().get(0);
        if (w != null) {
            CelestialSpawnBuilder.buildSpawn(w);
            CelestialSpawnBuilder.buildSurvivalSpawn(w, PortalTeleportEngine.PORTAL2_X, PortalTeleportEngine.PORTAL2_Z);
            sender.sendMessage(ChatColor.GOLD + "🪐 Spawns Céleste (Agora Y=120) et Survie Terrestre (640, 864) reconstruits avec succès !");
        } else {
            sender.sendMessage(ChatColor.RED + "Monde introuvable.");
        }
        return true;
    }

    public static boolean handleAetherTest(CommandSender sender, CosmeticsEngine cosmeticsEngine, BoosterEngine boosterEngine) {
        if (!checkAdmin(sender)) return true;
        if (!(sender instanceof Player p)) {
            sender.sendMessage("Commande réservée aux joueurs.");
            return true;
        }
        p.getInventory().addItem(
                CustomItemFactory.createVipCrown(), CustomItemFactory.createAetherSeal(),
                CustomItemFactory.createTitanCrest(), CustomItemFactory.createChampionRelic(),
                CustomItemFactory.createCelestialKey(5), CustomItemFactory.createOmegaKey(3),
                CustomItemFactory.createDungeonPass(3), CustomItemFactory.createQuantumWingsItem(),
                CustomItemFactory.createChampionAuraItem(), CustomItemFactory.createDragonPetItem(),
                CustomItemFactory.createMiningBoosterItem());
        cosmeticsEngine.setWings(p.getUniqueId(), true);
        cosmeticsEngine.setPet(p.getUniqueId(), "dragon");
        cosmeticsEngine.setAura(p.getUniqueId(), "champion");
        boosterEngine.addMiningBooster(p.getUniqueId(), 3600);
        p.sendMessage(ChatColor.GREEN + "★ Pack Test Admin attribué !");
        return true;
    }
}
