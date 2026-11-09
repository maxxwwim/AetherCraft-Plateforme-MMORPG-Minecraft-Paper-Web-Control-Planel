package io.aethercraft.visuals;

import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.Color;
import org.bukkit.FireworkEffect;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.entity.Firework;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.inventory.meta.FireworkMeta;
import org.bukkit.plugin.Plugin;
import org.bukkit.scheduler.BukkitRunnable;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class CrateEngine implements Listener {

    private final Plugin plugin;
    private final Random random = new Random();
    private final Particle.DustOptions purpleDust = new Particle.DustOptions(Color.fromRGB(192, 132, 252), 1.4f);
    private final Particle.DustOptions cyanDust = new Particle.DustOptions(Color.fromRGB(56, 189, 248), 1.4f);
    private final Particle.DustOptions goldDust = new Particle.DustOptions(Color.fromRGB(245, 158, 11), 1.5f);

    public CrateEngine(Plugin plugin) {
        this.plugin = plugin;
    }

    public boolean consumeKey(Player player, boolean isOmega) {
        int targetCmd = isOmega ? 2002 : 2001;
        ItemStack[] contents = player.getInventory().getContents();
        for (int i = 0; i < contents.length; i++) {
            ItemStack item = contents[i];
            if (item != null && item.hasItemMeta() && item.getItemMeta().hasCustomModelData()) {
                if (item.getItemMeta().getCustomModelData() == targetCmd) {
                    if (item.getAmount() <= 1) {
                        player.getInventory().setItem(i, null);
                    } else {
                        item.setAmount(item.getAmount() - 1);
                        player.getInventory().setItem(i, item);
                    }
                    return true;
                }
            }
        }
        return false;
    }

    public void startOpeningAnimation(Player player, String crateType) {
        startOpeningAnimation(player, crateType, false);
    }

    public void startOpeningAnimation(Player player, String crateType, boolean bypassKey) {
        boolean isOmega = crateType.equalsIgnoreCase("omega");
        if (!bypassKey) {
            if (!consumeKey(player, isOmega)) {
                player.sendMessage(ChatColor.RED + "❌ Vous n'avez pas de clé " + 
                    (isOmega ? "Oméga" : "Céleste") + " requise dans votre inventaire !");
                player.playSound(player.getLocation(), Sound.ENTITY_VILLAGER_NO, 1.0f, 1.0f);
                return;
            }
        }

        Location center = player.getLocation().add(player.getLocation().getDirection().setY(0).normalize().multiply(1.5));

        player.sendMessage(ChatColor.GOLD + "✦ " + ChatColor.LIGHT_PURPLE + "Ouverture de la " + 
            (isOmega ? ChatColor.RED + "Caisse Oméga" : ChatColor.LIGHT_PURPLE + "Caisse Céleste") + ChatColor.GRAY + " en cours...");

        new BukkitRunnable() {
            int tick = 0;
            final int maxTicks = 50; // 2.5 secondes

            @Override
            public void run() {
                if (!player.isOnline()) {
                    cancel();
                    return;
                }

                // 1. Vortex particulaire en spirale montante
                double progress = (double) tick / maxTicks;
                double height = progress * 2.8;
                double radius = 1.2 * (1.0 - (progress * 0.4));
                double theta = tick * 0.4;

                double x1 = radius * Math.cos(theta);
                double z1 = radius * Math.sin(theta);
                double x2 = radius * Math.cos(theta + Math.PI);
                double z2 = radius * Math.sin(theta + Math.PI);

                Location p1 = center.clone().add(x1, height, z1);
                Location p2 = center.clone().add(x2, height, z2);

                if (isOmega) {
                    player.getWorld().spawnParticle(Particle.DUST, p1, 2, 0, 0, 0, 0, goldDust);
                    player.getWorld().spawnParticle(Particle.FLAME, p2, 1, 0, 0, 0, 0.02);
                } else {
                    player.getWorld().spawnParticle(Particle.DUST, p1, 2, 0, 0, 0, 0, purpleDust);
                    player.getWorld().spawnParticle(Particle.DUST, p2, 2, 0, 0, 0, 0, cyanDust);
                }

                if (tick % 3 == 0) {
                    player.getWorld().spawnParticle(Particle.END_ROD, center.clone().add(0, height, 0), 1, 0.05, 0.05, 0.05, 0.01);
                    float pitch = 0.6f + (float) (progress * 1.2);
                    player.playSound(center, Sound.BLOCK_NOTE_BLOCK_CHIME, 0.7f, pitch);
                }

                tick++;

                // 2. Finalisation : Explosion & Attribution du Butin
                if (tick >= maxTicks) {
                    cancel();
                    deliverReward(player, isOmega, center);
                }
            }
        }.runTaskTimer(plugin, 0L, 1L);
    }

    private void deliverReward(Player player, boolean isOmega, Location loc) {
        // Tirage du butin
        String rewardName;
        ItemStack rewardItem;

        if (isOmega) {
            int roll = random.nextInt(3);
            if (roll == 0) {
                rewardName = "Fragment d'Aetherite Légendaire";
                rewardItem = new ItemStack(Material.NETHERITE_INGOT, 2);
            } else if (roll == 1) {
                rewardName = "Ailes Quantiques Stellaires";
                rewardItem = CustomItemFactory.createQuantumWingsItem();
            } else {
                rewardName = "Pioche Runique Fortune III";
                rewardItem = new ItemStack(Material.DIAMOND_PICKAXE);
            }
        } else {
            int roll = random.nextInt(4);
            if (roll == 0) {
                rewardName = "Lot de 16x Diamants Célestes";
                rewardItem = new ItemStack(Material.DIAMOND, 16);
            } else if (roll == 1) {
                rewardName = "Booster de Minage x2 (2h)";
                rewardItem = CustomItemFactory.createMiningBoosterItem();
            } else if (roll == 2) {
                rewardName = "Épée Stellaire Tranchant IV";
                rewardItem = new ItemStack(Material.DIAMOND_SWORD);
            } else {
                rewardName = "Pomme d'Or Enchantée d'Aether";
                rewardItem = new ItemStack(Material.ENCHANTED_GOLDEN_APPLE, 2);
            }
        }

        // Donner l'item au joueur
        player.getInventory().addItem(rewardItem);

        // Feu d'artifice spectaculaire
        Firework fw = player.getWorld().spawn(loc.clone().add(0, 1.5, 0), Firework.class);
        FireworkMeta fwm = fw.getFireworkMeta();
        fwm.setPower(1);
        fwm.addEffect(FireworkEffect.builder()
            .with(FireworkEffect.Type.BALL_LARGE)
            .withColor(isOmega ? Color.RED : Color.FUCHSIA, Color.YELLOW)
            .withFade(Color.WHITE)
            .flicker(true)
            .trail(true)
            .build());
        fw.setFireworkMeta(fwm);

        // Sons de victoire
        player.playSound(player.getLocation(), Sound.UI_TOAST_CHALLENGE_COMPLETE, 1.0f, 1.0f);

        // Titre à l'écran
        player.sendTitle(
            (isOmega ? ChatColor.RED + "★ BUTIN OMÉGA ★" : ChatColor.LIGHT_PURPLE + "★ BUTIN CÉLESTE ★"),
            ChatColor.GOLD + rewardName,
            10, 60, 20
        );

        // Annonce globale sur le serveur
        Bukkit.broadcastMessage(
            ChatColor.GOLD + "⭐ " + ChatColor.WHITE + "Le joueur " + ChatColor.AQUA + player.getName() + 
            ChatColor.WHITE + " a ouvert une " + (isOmega ? ChatColor.RED + "Caisse Oméga" : ChatColor.LIGHT_PURPLE + "Caisse Céleste") +
            ChatColor.WHITE + " et a obtenu : " + ChatColor.GREEN + rewardName + ChatColor.WHITE + " !"
        );
    }

    /**
     * Ouvre l'interface interactive du Réceptacle Astral sans nécessiter de bloc posé.
     * Le joueur clique pour insérer sa clé et déclencher le vortex stellaire.
     */
    public void openKeyInsertionGUI(Player player, boolean isOmega) {
        String title = isOmega ? 
            ChatColor.DARK_RED + "✦ RÉCEPTACLE OMÉGA — INSÉRER CLÉ ✦" : 
            ChatColor.DARK_PURPLE + "✦ RÉCEPTACLE CÉLESTE — INSÉRER CLÉ ✦";
        Inventory inv = Bukkit.createInventory(null, 27, title);

        ItemStack border = new ItemStack(Material.GRAY_STAINED_GLASS_PANE);
        ItemMeta bm = border.getItemMeta();
        bm.setDisplayName(ChatColor.DARK_GRAY + "✦ Sanctuaire Stellaire ✦");
        border.setItemMeta(bm);

        for (int i = 0; i < 27; i++) {
            inv.setItem(i, border);
        }

        // Info item (Slot 11)
        ItemStack info = new ItemStack(Material.BOOK);
        ItemMeta im = info.getItemMeta();
        im.setDisplayName(ChatColor.GOLD + "✦ CONSIGNES DU RÉCEPTACLE ✦");
        List<String> lore = new ArrayList<>();
        lore.add(ChatColor.GRAY + "Pour activer la Loot Box, cliquez sur le bouton");
        lore.add(ChatColor.GRAY + "central pour y engager votre " + (isOmega ? "Clé Oméga" : "Clé Céleste") + ".");
        lore.add(ChatColor.DARK_GRAY + "Zéro mobilier requis au Spawn.");
        im.setLore(lore);
        info.setItemMeta(im);
        inv.setItem(11, info);

        // Insertion receptacle (Slot 13)
        ItemStack slotKey = new ItemStack(isOmega ? Material.TRIPWIRE_HOOK : Material.NETHER_STAR);
        ItemMeta km = slotKey.getItemMeta();
        km.setDisplayName((isOmega ? ChatColor.RED : ChatColor.LIGHT_PURPLE) + "" + ChatColor.BOLD + "📥 INSÉRER LA CLÉ & JOUER LA LOOT BOX");
        List<String> klore = new ArrayList<>();
        klore.add(ChatColor.YELLOW + "▶ Cliquez ici pour engager la clé dans la stèle astrale");
        klore.add(ChatColor.GRAY + "Coût : " + ChatColor.WHITE + "1x " + (isOmega ? "Clé Oméga Légendaire" : "Clé Céleste"));
        klore.add(ChatColor.GREEN + "⚡ Déclenche le vortex de particules et le tirage du butin !");
        km.setLore(klore);
        slotKey.setItemMeta(km);
        inv.setItem(13, slotKey);

        // Cancel / Exit button (Slot 15)
        ItemStack cancel = new ItemStack(Material.BARRIER);
        ItemMeta cm = cancel.getItemMeta();
        cm.setDisplayName(ChatColor.RED + "✖ Annuler & Conserver ma Clé");
        cancel.setItemMeta(cm);
        inv.setItem(15, cancel);

        player.openInventory(inv);
        player.playSound(player.getLocation(), Sound.BLOCK_RESPAWN_ANCHOR_CHARGE, 0.8f, 1.3f);
    }

    @EventHandler
    public void onInventoryClick(InventoryClickEvent event) {
        if (!(event.getWhoClicked() instanceof Player)) return;
        String title = event.getView().getTitle();
        if (title.contains("✦ RÉCEPTACLE")) {
            event.setCancelled(true);
            Player player = (Player) event.getWhoClicked();
            int slot = event.getRawSlot();

            boolean isOmega = title.contains("OMÉGA");

            if (slot == 13) {
                // Le joueur confirme l'insertion de la clé
                player.closeInventory();
                startOpeningAnimation(player, isOmega ? "omega" : "celestial", false);
            } else if (slot == 15) {
                player.closeInventory();
                player.playSound(player.getLocation(), Sound.UI_BUTTON_CLICK, 0.8f, 1.0f);
                player.sendMessage(ChatColor.YELLOW + "✦ Insertion de clé annulée.");
            }
        }
    }
}
