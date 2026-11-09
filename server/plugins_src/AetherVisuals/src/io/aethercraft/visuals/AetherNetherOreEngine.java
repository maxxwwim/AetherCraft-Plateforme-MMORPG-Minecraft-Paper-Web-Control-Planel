package io.aethercraft.visuals;

import org.bukkit.ChatColor;
import org.bukkit.Chunk;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.world.ChunkLoadEvent;
import org.bukkit.inventory.ItemStack;
import org.bukkit.persistence.PersistentDataContainer;
import org.bukkit.persistence.PersistentDataType;

import java.util.Random;

/**
 * Générateur et Moteur de Découverte des Minerais / Blocs d'Aether dans le Nether (F20).
 * Génère des filons rares d'Aether Ore exclusivement dans la dimension Nether (world_nether).
 */
public class AetherNetherOreEngine implements Listener {

    private final AetherVisualsPlugin plugin;
    private final NamespacedKey keyChunkProcessed;
    private final Random random = new Random();

    public AetherNetherOreEngine(AetherVisualsPlugin plugin) {
        this.plugin = plugin;
        this.keyChunkProcessed = new NamespacedKey(plugin, "aether_nether_ore_gen");
    }

    public boolean isNetherWorld(World world) {
        if (world == null) return false;
        return world.getEnvironment() == World.Environment.NETHER || world.getName().equalsIgnoreCase("world_nether") || world.getName().toLowerCase().contains("nether");
    }

    @EventHandler(priority = EventPriority.NORMAL)
    public void onChunkLoad(ChunkLoadEvent event) {
        World world = event.getWorld();
        if (!isNetherWorld(world)) return;

        Chunk chunk = event.getChunk();
        PersistentDataContainer pdc = chunk.getPersistentDataContainer();
        if (pdc.has(keyChunkProcessed, PersistentDataType.BYTE)) {
            return;
        }
        pdc.set(keyChunkProcessed, PersistentDataType.BYTE, (byte) 1);

        // Chance rare par chunk (65% d'avoir au moins un filon)
        if (random.nextDouble() > 0.65) return;

        int veins = 1 + (random.nextDouble() < 0.25 ? 1 : 0);
        for (int v = 0; v < veins; v++) {
            generateVein(chunk);
        }
    }

    public void generateVein(Chunk chunk) {
        int startX = random.nextInt(16);
        int startZ = random.nextInt(16);
        int startY = 15 + random.nextInt(81); // Entre Y=15 et Y=95

        int veinSize = 1 + random.nextInt(3); // 1 à 3 blocs

        for (int i = 0; i < veinSize; i++) {
            int bx = Math.max(0, Math.min(15, startX + (i == 1 ? (random.nextBoolean() ? 1 : -1) : 0)));
            int bz = Math.max(0, Math.min(15, startZ + (i == 2 ? (random.nextBoolean() ? 1 : -1) : 0)));
            int by = Math.max(15, Math.min(95, startY + (random.nextInt(3) - 1)));

            Block b = chunk.getBlock(bx, by, bz);
            if (b.getType() == Material.NETHERRACK) {
                b.setType(Material.ANCIENT_DEBRIS, false);
            }
        }
    }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onOreBreak(BlockBreakEvent event) {
        Block block = event.getBlock();
        World world = block.getWorld();
        if (!isNetherWorld(world)) return;

        if (block.getType() == Material.ANCIENT_DEBRIS) {
            Player player = event.getPlayer();
            event.setDropItems(false);
            ItemStack aetherOre = PetItemFactory.createHabboBullionItem("minerai_aether", 1);
            world.dropItemNaturally(block.getLocation(), aetherOre);

            Location loc = block.getLocation().add(0.5, 0.5, 0.5);
            world.spawnParticle(Particle.PORTAL, loc, 25, 0.4, 0.4, 0.4, 0.1);
            world.spawnParticle(Particle.SOUL_FIRE_FLAME, loc, 15, 0.3, 0.3, 0.3, 0.05);
            world.playSound(loc, Sound.BLOCK_AMETHYST_BLOCK_CHIME, 1.0f, 1.5f);
            world.playSound(loc, Sound.BLOCK_RESPAWN_ANCHOR_CHARGE, 0.8f, 1.8f);

            player.sendMessage(ChatColor.DARK_AQUA + "☄️ " + ChatColor.AQUA + "" + ChatColor.BOLD + "DÉCOUVERTE D'AETHER ! " +
                    ChatColor.YELLOW + "Vous avez extrait un " + ChatColor.GOLD + "Minerai d'Aether du Nether" +
                    ChatColor.YELLOW + " convertible en Boutique ou Banque (" + ChatColor.GOLD + "+750 ⛃" + ChatColor.YELLOW + ") !");
        }
    }
}
