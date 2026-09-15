#!/usr/bin/env python3
"""Generates a Java Edition Minecraft world (Anvil format) containing a castle."""
import os
import time

import anvil
from nbt import nbt

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WORLD_NAME = "Castle World"
DATA_VERSION = 1976  # 18w06a (1.13) — old "flattened" pre-1.18 chunk format anvil-parser2 targets

CX, CZ = 150, 150   # world-space centre of the castle
GY = 63              # y of top grass block (ground surface)
GROUND = GY + 1      # 64, first air/walkable layer

TERRAIN_HALF = 72    # flat grassy clearing extends this far from centre

# Blocks
B = lambda name, **props: anvil.Block("minecraft", name, properties=props or None)
BEDROCK = B("bedrock")
STONE = B("stone")
DIRT = B("dirt")
GRASS = B("grass_block")
WATER = B("water")
AIR = B("air")
STONE_BRICK = B("stone_bricks")
MOSSY_BRICK = B("mossy_stone_bricks")
CRACKED_BRICK = B("cracked_stone_bricks")
CHISELED_BRICK = B("chiseled_stone_bricks")
COBBLE = B("cobblestone")
WALL = B("stone_brick_wall")
OAK_PLANKS = B("oak_planks")
OAK_LOG = lambda axis="y": B("oak_log", axis=axis)
OAK_FENCE = B("oak_fence")
GLASS_PANE = B("glass_pane")
TORCH = B("torch")
WALL_TORCH = lambda facing: B("wall_torch", facing=facing)
LANTERN = B("lantern", hanging="false")
IRON_BARS = B("iron_bars")
GRAVEL = B("gravel")
SPRUCE_STAIRS = lambda facing, half="bottom": B("spruce_stairs", facing=facing, half=half)
STONE_BRICK_STAIRS = lambda facing, half="bottom": B("stone_brick_stairs", facing=facing, half=half)
STONE_BRICK_SLAB = lambda typ="bottom": B("stone_brick_slab", type=typ)
LADDER = lambda facing: B("ladder", facing=facing)
RED_BANNER = B("red_banner")
GOLD_BLOCK = B("gold_block")
OAK_DOOR = lambda facing, half="lower", hinge="left": B("oak_door", facing=facing, half=half, hinge=hinge)


def w(x, z):
    """local castle coords -> world coords"""
    return CX + x, CZ + z


def fill(region, block, x1, y1, z1, x2, y2, z2):
    wx1, wz1 = w(x1, z1)
    wx2, wz2 = w(x2, z2)
    region.fill(block, wx1, y1, wz1, wx2, y2, wz2, ignore_outside=True)


def setb(region, block, x, y, z):
    wx, wz = w(x, z)
    region.set_if_inside(block, wx, y, wz)


def hollow_box(region, block, x1, y1, z1, x2, y2, z2, thickness=1):
    """Walls of a box, floor+ceiling solid, interior hollow."""
    fill(region, block, x1, y1, z1, x2, y1, z2)  # floor
    fill(region, block, x1, y2, z1, x2, y2, z2)  # ceiling
    fill(region, block, x1, y1, z1, x2, y2, z1 + thickness - 1)  # -z wall
    fill(region, block, x1, y1, z2 - thickness + 1, x2, y2, z2)  # +z wall
    fill(region, block, x1, y1, z1, x1 + thickness - 1, y2, z2)  # -x wall
    fill(region, block, x2 - thickness + 1, y1, z1, x2, y2, z2)  # +x wall


def crenellate(region, block, x1, z1, x2, z2, y, axis):
    """Place alternating merlons along a straight edge at height y."""
    if axis == "x":
        for x in range(x1, x2 + 1, 2):
            setb(region, block, x, y, z1)
    else:
        for z in range(z1, z2 + 1, 2):
            setb(region, block, x1, y, z)


def tower(region, cx, cz, radius, y0, top, wall_thick=2, roof=True, torch_top=True):
    """Cylindrical tower: hollow shaft, crenellations, tiered conical roof."""
    r2_out = radius * radius
    r2_in = (radius - wall_thick) * (radius - wall_thick)
    for dz in range(-radius - 1, radius + 2):
        for dx in range(-radius - 1, radius + 2):
            d2 = dx * dx + dz * dz
            if d2 > r2_out:
                continue
            x, z = cx + dx, cz + dz
            if d2 >= r2_in:
                fill(region, STONE_BRICK, x, y0, z, x, top, z)
            else:
                setb(region, STONE_BRICK, x, y0 - 1, z)  # floor
    # crenellations ring at top
    for dz in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            d2 = dx * dx + dz * dz
            if r2_in <= d2 <= r2_out and (dx + dz) % 2 == 0:
                setb(region, WALL, cx + dx, top + 1, cz + dz)
    # window slits, punched straight through the wall thickness on all 4 sides
    for wy in (y0 + 3, y0 + 7, y0 + 11):
        if wy >= top - 1:
            continue
        for r in range(radius - wall_thick - 1, radius + 1):
            setb(region, AIR, cx + r, wy, cz)
            setb(region, AIR, cx + r, wy + 1, cz)
            setb(region, AIR, cx - r, wy, cz)
            setb(region, AIR, cx - r, wy + 1, cz)
            setb(region, AIR, cx, wy, cz + r)
            setb(region, AIR, cx, wy + 1, cz + r)
            setb(region, AIR, cx, wy, cz - r)
            setb(region, AIR, cx, wy + 1, cz - r)
    if roof:
        rr = radius - 1
        ry = top + 2
        while rr >= 0:
            r2 = rr * rr
            for dz in range(-rr, rr + 1):
                for dx in range(-rr, rr + 1):
                    if dx * dx + dz * dz <= r2:
                        setb(region, MOSSY_BRICK, cx + dx, ry, cz + dz)
            rr -= 1
            ry += 1
        if torch_top:
            setb(region, OAK_FENCE, cx, ry, cz)
            setb(region, TORCH, cx, ry + 1, cz)


def build(region):
    print("Terrain...")
    fill(region, BEDROCK, -TERRAIN_HALF, 0, -TERRAIN_HALF, TERRAIN_HALF, 0, TERRAIN_HALF)
    fill(region, STONE, -TERRAIN_HALF, 1, -TERRAIN_HALF, TERRAIN_HALF, 58, TERRAIN_HALF)
    fill(region, DIRT, -TERRAIN_HALF, 59, -TERRAIN_HALF, TERRAIN_HALF, 62, TERRAIN_HALF)
    fill(region, GRASS, -TERRAIN_HALF, GY, -TERRAIN_HALF, TERRAIN_HALF, GY, TERRAIN_HALF)
    region.fill_biome(anvil.Biome("plains"), *w(-TERRAIN_HALF, -TERRAIN_HALF), *w(TERRAIN_HALF, TERRAIN_HALF))

    print("Moat...")
    for z in range(-48, 49):
        for x in range(-48, 49):
            d = max(abs(x), abs(z))
            if 42 <= d <= 47:
                if -3 <= x <= 3 and z >= 38:
                    continue  # leave gap for bridge on south approach
                fill(region, AIR, x, 59, z, x, 63, z)
                fill(region, WATER, x, 59, z, x, 63, z)

    print("Bridge...")
    fill(region, OAK_PLANKS, -3, GROUND, 38, 3, GROUND, 48)
    fill(region, OAK_FENCE, -3, GROUND + 1, 38, -3, GROUND + 1, 48)
    fill(region, OAK_FENCE, 3, GROUND + 1, 38, 3, GROUND + 1, 48)
    for z in range(38, 49, 4):
        setb(region, TORCH, -3, GROUND + 2, z)
        setb(region, TORCH, 3, GROUND + 2, z)
    fill(region, GRAVEL, -4, GY, 48, 4, GY, 60)

    print("Curtain walls...")
    WBOT, WTOP = GROUND, GROUND + 10
    # north / south walls
    fill(region, STONE_BRICK, -26, WBOT, -33, 26, WTOP, -31)
    fill(region, STONE_BRICK, -26, WBOT, 31, 26, WTOP, 33)
    # east / west walls
    fill(region, STONE_BRICK, -33, WBOT, -26, -31, WTOP, 26)
    fill(region, STONE_BRICK, 31, WBOT, -26, 33, WTOP, 26)
    # wall walkway (hollow behind battlement, thin walkway on top)
    fill(region, AIR, -25, WBOT, -32, 25, WTOP - 1, -32)
    fill(region, AIR, -25, WBOT, 32, 25, WTOP - 1, 32)
    fill(region, AIR, -32, WBOT, -25, -32, WTOP - 1, 25)
    fill(region, AIR, 32, WBOT, -25, 32, WTOP - 1, 25)
    for x in range(-26, 27, 2):
        setb(region, WALL, x, WTOP + 1, -33)
        setb(region, WALL, x, WTOP + 1, 33)
    for z in range(-26, 27, 2):
        setb(region, WALL, -33, WTOP + 1, z)
        setb(region, WALL, 33, WTOP + 1, z)
    # arrow slits punched through the outer skin (the middle layer is
    # already hollow walkway, so only the outward-facing stone needs clearing)
    for coord in range(-20, 21, 8):
        for wy in (WBOT + 3, WBOT + 6):
            setb(region, AIR, coord, wy, -33)
            setb(region, AIR, coord, wy, 33)
            setb(region, AIR, -33, wy, coord)
            setb(region, AIR, 33, wy, coord)

    print("Corner towers...")
    for tx in (-32, 32):
        for tz in (-32, 32):
            tower(region, tx, tz, 7, GROUND, GROUND + 20)

    print("Gatehouse...")
    GBOT, GTOP = GROUND, GROUND + 20
    fill(region, STONE_BRICK, -9, GBOT, 30, -5, GTOP, 39)
    fill(region, STONE_BRICK, 5, GBOT, 30, 9, GTOP, 39)
    fill(region, AIR, -8, GBOT, 31, -6, GTOP - 3, 38)
    fill(region, AIR, 6, GBOT, 31, 8, GTOP - 3, 38)
    fill(region, STONE_BRICK, -9, GTOP - 2, 30, 9, GTOP - 2, 39)  # lintel joining towers
    for x in (-9, -5, 5, 9):
        for z in range(30, 40, 2):
            setb(region, WALL, x, GTOP + 1, z)
    # gate opening through curtain wall + towers, with an arch
    fill(region, AIR, -3, GROUND, 27, 3, GROUND + 5, 40)
    fill(region, STONE_BRICK, -4, GROUND + 6, 27, 4, GROUND + 6, 40)
    fill(region, CHISELED_BRICK, -4, GROUND, 27, -4, GROUND + 5, 27)
    fill(region, CHISELED_BRICK, 4, GROUND, 27, 4, GROUND + 5, 27)
    setb(region, WALL_TORCH("east"), -4, GROUND + 3, 33)
    setb(region, WALL_TORCH("west"), 4, GROUND + 3, 33)

    print("Courtyard path...")
    fill(region, STONE_BRICK, -2, GY, 9, 2, GY, 27)
    fill(region, GRAVEL, -3, GY, 9, -3, GY, 27)
    fill(region, GRAVEL, 3, GY, 9, 3, GY, 27)
    for z in range(10, 26, 6):
        setb(region, TORCH, -3, GROUND, z)
        setb(region, TORCH, 3, GROUND, z)

    print("Keep...")
    hollow_box(region, STONE_BRICK, -8, GROUND, -8, 8, GROUND + 32, 8, thickness=2)
    # floors
    for fy in (GROUND + 10, GROUND + 20):
        fill(region, OAK_PLANKS, -6, fy, -6, 6, fy, 6)
        fill(region, AIR, -1, fy, -1, 1, fy, 1)  # hatch for ladder
    fill(region, LADDER("north"), 2, GROUND + 1, 7, 2, GROUND + 31, 7)
    # entrance on the +z face, toward the gate/courtyard (punch through both wall layers)
    fill(region, AIR, -1, GROUND, 7, 1, GROUND + 3, 9)
    setb(region, TORCH, -2, GROUND + 2, 8)
    setb(region, TORCH, 2, GROUND + 2, 8)
    # windows: clear the inner skin, glass pane on the outer skin
    for fy in (GROUND + 5, GROUND + 15, GROUND + 25):
        fill(region, AIR, -7, fy, -3, -7, fy + 1, 3)
        fill(region, GLASS_PANE, -8, fy, -3, -8, fy + 1, 3)
        fill(region, AIR, 7, fy, -3, 7, fy + 1, 3)
        fill(region, GLASS_PANE, 8, fy, -3, 8, fy + 1, 3)
        fill(region, AIR, -3, fy, -7, 3, fy + 1, -7)
        fill(region, GLASS_PANE, -3, fy, -8, 3, fy + 1, -8)
        fill(region, AIR, -3, fy, 7, 3, fy + 1, 7)
        fill(region, GLASS_PANE, -3, fy, 8, 3, fy + 1, 8)
    # crenellations + roof
    top = GROUND + 32
    for x in range(-8, 9, 2):
        setb(region, WALL, x, top + 1, -8)
        setb(region, WALL, x, top + 1, 8)
    for z in range(-8, 9, 2):
        setb(region, WALL, -8, top + 1, z)
        setb(region, WALL, 8, top + 1, z)
    rr = 8
    ry = top + 1
    while rr >= 0:
        fill(region, MOSSY_BRICK, -rr, ry, -rr, rr, ry, rr)
        rr -= 1
        ry += 1
    setb(region, OAK_FENCE, 0, ry, 0)
    setb(region, RED_BANNER, 0, ry + 1, 0)

    return region


def build_level_dat(path, seed):
    root = nbt.NBTFile()
    root.name = ""
    data = nbt.TAG_Compound(name="Data")

    def tag(cls, name, value):
        t = cls(name=name, value=value)
        data.tags.append(t)

    tag(nbt.TAG_Int, "version", 19133)
    tag(nbt.TAG_Int, "DataVersion", DATA_VERSION)
    ver = nbt.TAG_Compound(name="Version")
    ver.tags.append(nbt.TAG_Int(name="Id", value=DATA_VERSION))
    ver.tags.append(nbt.TAG_String(name="Name", value="1.13"))
    ver.tags.append(nbt.TAG_Byte(name="Snapshot", value=0))
    data.tags.append(ver)

    tag(nbt.TAG_Byte, "initialized", 1)
    tag(nbt.TAG_String, "LevelName", WORLD_NAME)
    tag(nbt.TAG_String, "generatorName", "default")
    tag(nbt.TAG_Int, "generatorVersion", 1)
    tag(nbt.TAG_String, "generatorOptions", "")
    tag(nbt.TAG_Long, "RandomSeed", seed)
    tag(nbt.TAG_Byte, "MapFeatures", 1)
    tag(nbt.TAG_Byte, "mapFeatures", 1)
    tag(nbt.TAG_Long, "LastPlayed", int(time.time() * 1000))
    tag(nbt.TAG_Long, "SizeOnDisk", 0)
    tag(nbt.TAG_Byte, "allowCommands", 1)
    tag(nbt.TAG_Byte, "hardcore", 0)
    tag(nbt.TAG_Int, "GameType", 1)  # creative
    tag(nbt.TAG_Int, "Difficulty", 2)
    tag(nbt.TAG_Byte, "DifficultyLocked", 0)
    tag(nbt.TAG_Int, "SpawnX", CX)
    tag(nbt.TAG_Int, "SpawnY", GROUND + 1)
    tag(nbt.TAG_Int, "SpawnZ", CZ + 44)
    tag(nbt.TAG_Float, "SpawnAngle", 180.0)
    tag(nbt.TAG_Long, "Time", 6000)
    tag(nbt.TAG_Long, "DayTime", 6000)
    tag(nbt.TAG_Byte, "raining", 0)
    tag(nbt.TAG_Int, "rainTime", 0)
    tag(nbt.TAG_Byte, "thundering", 0)
    tag(nbt.TAG_Int, "thunderTime", 0)
    tag(nbt.TAG_Int, "clearWeatherTime", 0)
    tag(nbt.TAG_Byte, "WasModded", 0)
    tag(nbt.TAG_Int, "BorderCenterX", 0)
    tag(nbt.TAG_Int, "BorderCenterZ", 0)
    tag(nbt.TAG_Double, "BorderSize", 60000000.0)

    dp = nbt.TAG_Compound(name="DataPacks")
    enabled = nbt.TAG_List(name="Enabled", type=nbt.TAG_String)
    enabled.tags.append(nbt.TAG_String(value="vanilla"))
    disabled = nbt.TAG_List(name="Disabled", type=nbt.TAG_String)
    dp.tags.append(enabled)
    dp.tags.append(disabled)
    data.tags.append(dp)

    root.tags.append(data)
    root.write_file(path)


if __name__ == "__main__":
    import sys
    out_dir = sys.argv[1]
    os.makedirs(os.path.join(out_dir, "region"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "playerdata"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "stats"), exist_ok=True)

    region = anvil.EmptyRegion(0, 0)
    build(region)

    # Force lighting recompute on first load by marking chunks not-yet-lit,
    # since EmptySection.save() never writes BlockLight/SkyLight data.
    class Wrapped:
        def __init__(self, nbt_data):
            self._nbt_data = nbt_data
        def save(self):
            return self._nbt_data

    for i, chunk in enumerate(region.chunks):
        if chunk is None:
            continue
        nbt_data = chunk.save()
        level = next(t for t in nbt_data.tags if t.name == "Level")
        for t in level.tags:
            if t.name == "isLightOn":
                t.value = 0
        region.chunks[i] = Wrapped(nbt_data)

    region.save(os.path.join(out_dir, "region", "r.0.0.mca"))
    build_level_dat(os.path.join(out_dir, "level.dat"), seed=8391137216498)
    print("World written to", out_dir)
