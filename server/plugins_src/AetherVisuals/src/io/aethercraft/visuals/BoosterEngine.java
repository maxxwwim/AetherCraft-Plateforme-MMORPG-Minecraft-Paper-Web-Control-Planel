package io.aethercraft.visuals;

import org.bukkit.ChatColor;
import org.bukkit.Color;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.block.Block;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.inventory.ItemStack;

import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public class BoosterEngine implements Listener {

    // UUID -> Expiration timestamp in milliseconds
    private final Map<UUID, Long> miningBoosters = new HashMap<>();
    private final Particle.DustOptions goldSpark = new Particle.DustOptions(Color.fromRGB(254, 240, 138), 1.5f);

    public void addMiningBooster(UUID uuid, int seconds) {
        long current = System.currentTimeMillis();
        long existing = miningBoosters.getOrDefault(uuid, current);
        long start = Math.max(current, existing);
        miningBoosters.put(uuid, start + (seconds * 1000L));
    }

    public boolean hasActiveMiningBooster(UUID uuid) {
        Long expire = miningBoosters.get(uuid);
        return expire != null && expire > System.currentTimeMillis();
    }

    public int getRemainingSeconds(UUID uuid) {
        Long expire = miningBoosters.get(uuid);
        if (expire == null) return 0;
        long diff = expire - System.currentTimeMillis();
        return diff > 0 ? (int)(diff / 1000L) : 0;
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onOreBreak(BlockBreakEvent event) {
        Player player = event.getPlayer();
        if (!hasActiveMiningBooster(player.getUniqueId())) return;

        Block block = event.getBlock();
        String name = block.getType().name();

        boolean isOre = name.endsWith("_ORE") || name.equals("ANCIENT_DEBRIS") || name.endsWith("_BLOCK_RAW");
        if (!isOre) return;

        // Doubler les drops naturels
        Collection<ItemStack> naturalDrops = block.getDrops(player.getInventory().getItemInMainHand(), player);
        Location dropLoc = block.getLocation().add(0.5, 0.5, 0.5);

        for (ItemStack drop : naturalDrops) {
            ItemStack extra = drop.clone();
            block.getWorld().dropItemNaturally(dropLoc, extra);
        }

        // Effets visuels & sonores du booster
        block.getWorld().spawnParticle(Particle.WAX_ON, dropLoc, 8, 0.3, 0.3, 0.3, 0.1);
        block.getWorld().spawnParticle(Particle.DUST, dropLoc, 6, 0.2, 0.2, 0.2, 0, goldSpark);
        player.playSound(dropLoc, Sound.BLOCK_AMETHYST_BLOCK_RESONATE, 0.8f, 1.4f);

        // Actionbar indicatif
        int rem = getRemainingSeconds(player.getUniqueId());
        int mins = rem / 60;
        player.sendActionBar(ChatColor.GOLD + "⛏️ " + ChatColor.YELLOW + "Drop x2 !" + ChatColor.GRAY + " (Booster actif: " + mins + "m)");
    }
}
