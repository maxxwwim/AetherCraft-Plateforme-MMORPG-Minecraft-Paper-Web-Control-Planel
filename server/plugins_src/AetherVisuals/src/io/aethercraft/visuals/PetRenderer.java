package io.aethercraft.visuals;

import io.aethercraft.visuals.PetPaletteCatalog.PetPalette;
import org.bukkit.*;
import org.bukkit.entity.*;
import org.bukkit.util.Transformation;
import org.joml.AxisAngle4f;
import org.joml.Vector3f;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Moteur de Rendu 3D Volumétrique Multi-Blocs des Familiers Célestes (Paper 1.21.1).
 */
public class PetRenderer {

    public static class VoxelPetRig {
        public final String petType;
        public final World world;
        public BlockDisplay torso;
        public BlockDisplay chest;
        public BlockDisplay head;
        public BlockDisplay snout;
        public BlockDisplay hornLeft;
        public BlockDisplay hornRight;
        public BlockDisplay legFL;
        public BlockDisplay legFR;
        public BlockDisplay legBL;
        public BlockDisplay legBR;
        public BlockDisplay wingLeft;
        public BlockDisplay wingRight;
        public BlockDisplay tail;
        public TextDisplay nameTag;

        public VoxelPetRig(String petType, World world) {
            this.petType = petType;
            this.world = world;
        }

        public boolean isValid(World currentWorld) {
            return world.equals(currentWorld) && torso != null && torso.isValid() && head != null && head.isValid();
        }

        public List<Entity> allParts() {
            return Arrays.asList(torso, chest, head, snout, hornLeft, hornRight,
                    legFL, legFR, legBL, legBR, wingLeft, wingRight, tail, nameTag);
        }

        public void destroy() {
            for (Entity e : allParts()) {
                if (e != null && e.isValid()) {
                    e.remove();
                }
            }
        }
    }

    private final Map<UUID, VoxelPetRig> activeRigs = new ConcurrentHashMap<>();

    public void removePet(UUID playerUuid) {
        VoxelPetRig rig = activeRigs.remove(playerUuid);
        if (rig != null) {
            rig.destroy();
        }
    }

    public void clearAll() {
        for (UUID id : new ArrayList<>(activeRigs.keySet())) {
            removePet(id);
        }
    }

    public void renderPetCompanion(Player player, String petType, long tick) {
        if (petType == null || !player.isOnline()) {
            removePet(player.getUniqueId());
            return;
        }

        String normalized = petType.toLowerCase(Locale.ROOT);
        UUID uuid = player.getUniqueId();
        VoxelPetRig rig = activeRigs.get(uuid);

        if (rig == null || !rig.petType.equals(normalized) || !rig.isValid(player.getWorld())) {
            removePet(uuid);
            rig = spawnVoxelPetRig(player, normalized);
            activeRigs.put(uuid, rig);
        }

        animateRig(player, rig, normalized, tick);
        PetPaletteCatalog.applyPetBuffsAndParticles(player, rig, normalized, tick);
    }

    private VoxelPetRig spawnVoxelPetRig(Player p, String type) {
        World w = p.getWorld();
        PetPalette pal = PetPaletteCatalog.getPalette(type);
        Location base = computePetAnchor(p, pal.hoverHeight, 0);
        VoxelPetRig rig = new VoxelPetRig(type, w);

        rig.torso = spawnPart(w, base, pal.torsoMat);
        rig.chest = spawnPart(w, base, pal.chestMat);
        rig.head = spawnPart(w, base, pal.headMat);
        rig.snout = spawnPart(w, base, pal.snoutMat);
        rig.hornLeft = spawnPart(w, base, pal.hornMat);
        rig.hornRight = spawnPart(w, base, pal.hornMat);
        rig.legFL = spawnPart(w, base, pal.legMat);
        rig.legFR = spawnPart(w, base, pal.legMat);
        rig.legBL = spawnPart(w, base, pal.legMat);
        rig.legBR = spawnPart(w, base, pal.legMat);
        rig.wingLeft = spawnPart(w, base, pal.wingMat);
        rig.wingRight = spawnPart(w, base, pal.wingMat);
        rig.tail = spawnPart(w, base, pal.tailMat);

        rig.nameTag = w.spawn(base.clone().add(0, 0.95, 0), TextDisplay.class, td -> {
            td.setText(pal.displayName);
            td.setBillboard(Display.Billboard.CENTER);
            td.setBackgroundColor(Color.fromARGB(165, 15, 23, 42));
            td.setShadowed(true);
            td.setBrightness(new Display.Brightness(15, 15));
            td.setTransformation(new Transformation(
                    new Vector3f(0, 0, 0),
                    new AxisAngle4f(0, 0, 1, 0),
                    new Vector3f(0.68f, 0.68f, 0.68f),
                    new AxisAngle4f(0, 0, 1, 0)
            ));
        });

        return rig;
    }

    private BlockDisplay spawnPart(World w, Location loc, Material mat) {
        Material safe = (mat != null && mat.isBlock()) ? mat : Material.GOLD_BLOCK;
        return w.spawn(loc, BlockDisplay.class, bd -> {
            bd.setBlock(Bukkit.createBlockData(safe));
            bd.setBrightness(new Display.Brightness(15, 15));
            bd.setInterpolationDuration(2);
            bd.setTeleportDuration(2);
        });
    }

    private Location computePetAnchor(Player p, double hoverHeight, long tick) {
        Location pLoc = p.getLocation();
        double yawRad = Math.toRadians(-pLoc.getYaw() - 48);
        double orbitX = 1.45 * Math.cos(yawRad);
        double orbitZ = 1.45 * Math.sin(yawRad);
        double bobY = hoverHeight + (0.14 * Math.sin(tick * 0.16));
        Location anchor = pLoc.clone().add(orbitX, bobY, orbitZ);
        anchor.setYaw(pLoc.getYaw());
        anchor.setPitch(0f);
        return anchor;
    }

    private void animateRig(Player p, VoxelPetRig rig, String type, long tick) {
        PetPalette pal = PetPaletteCatalog.getPalette(type);
        Location anchor = computePetAnchor(p, pal.hoverHeight, tick);
        float s = pal.scaleMultiplier;

        float walkSwing = (float) (Math.sin(tick * 0.32) * 0.35);
        float wingFlap = (float) (Math.sin(tick * 0.45) * 0.52);
        float tailWag = (float) (Math.cos(tick * 0.28) * 0.32);
        float headNod = (float) (Math.sin(tick * 0.18) * 0.08);

        for (Entity e : rig.allParts()) {
            if (e != null && e.isValid()) {
                if (e.equals(rig.nameTag)) {
                    e.teleport(anchor.clone().add(0, 0.92 * s, 0));
                } else {
                    e.teleport(anchor);
                }
            }
        }

        setBox(rig.torso, 0f, 0f, 0f, 0.46f * s, 0.38f * s, 0.72f * s, 0f, 1f, 0f, 0f);
        setBox(rig.chest, 0f, 0.06f * s, 0.24f * s, 0.50f * s, 0.42f * s, 0.32f * s, 0f, 1f, 0f, 0f);
        setBox(rig.head, 0f, 0.36f * s + headNod, 0.44f * s, 0.40f * s, 0.40f * s, 0.40f * s, headNod, 1f, 0f, 0f);
        setBox(rig.snout, 0f, 0.30f * s + headNod, 0.70f * s, 0.24f * s, 0.20f * s, 0.26f * s, headNod, 1f, 0f, 0f);
        setBox(rig.hornLeft, -0.15f * s, 0.64f * s + headNod, 0.38f * s, 0.11f * s, 0.28f * s, 0.12f * s, -0.2f, 1f, 0f, 0f);
        setBox(rig.hornRight, 0.15f * s, 0.64f * s + headNod, 0.38f * s, 0.11f * s, 0.28f * s, 0.12f * s, -0.2f, 1f, 0f, 0f);

        setBox(rig.legFL, -0.18f * s, -0.34f * s, 0.24f * s, 0.15f * s, 0.36f * s, 0.15f * s, walkSwing, 1f, 0f, 0f);
        setBox(rig.legFR, 0.18f * s, -0.34f * s, 0.24f * s, 0.15f * s, 0.36f * s, 0.15f * s, -walkSwing, 1f, 0f, 0f);
        setBox(rig.legBL, -0.18f * s, -0.34f * s, -0.24f * s, 0.15f * s, 0.36f * s, 0.15f * s, -walkSwing, 1f, 0f, 0f);
        setBox(rig.legBR, 0.18f * s, -0.34f * s, -0.24f * s, 0.15f * s, 0.36f * s, 0.15f * s, walkSwing, 1f, 0f, 0f);

        float wingSpan = (type.equals("dragon") || type.equals("phoenix") || type.equals("griffin")) ? 0.68f * s : 0.28f * s;
        setBox(rig.wingLeft, -0.26f * s - (wingSpan * 0.5f), 0.18f * s, 0.0f, wingSpan, 0.08f * s, 0.48f * s, wingFlap, 0f, 0f, 1f);
        setBox(rig.wingRight, 0.26f * s + (wingSpan * 0.5f), 0.18f * s, 0.0f, wingSpan, 0.08f * s, 0.48f * s, -wingFlap, 0f, 0f, 1f);
        setBox(rig.tail, 0f, 0.12f * s, -0.52f * s, 0.18f * s, 0.18f * s, 0.46f * s, tailWag, 0f, 1f, 0f);
    }

    private void setBox(BlockDisplay bd, float tx, float ty, float tz,
                        float sx, float sy, float sz,
                        float angleRad, float ax, float ay, float az) {
        if (bd == null || !bd.isValid()) return;
        bd.setTransformation(new Transformation(
                new Vector3f(tx - (sx * 0.5f), ty - (sy * 0.5f), tz - (sz * 0.5f)),
                new AxisAngle4f(angleRad, ax, ay, az),
                new Vector3f(sx, sy, sz),
                new AxisAngle4f(0f, 0f, 1f, 0f)
        ));
    }
}
