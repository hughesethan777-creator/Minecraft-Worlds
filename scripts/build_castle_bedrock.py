#!/usr/bin/env python3
"""Generates a Bedrock Edition Minecraft world (LevelDB format) containing a castle.

Same castle layout as build_castle.py (the Java Anvil version), rebuilt on
Amulet-Core's LevelDB format wrapper. Blocks are described using their Java
Edition identifiers and set via World.set_version_block(), which uses
PyMCTranslate to convert them into the equivalent Bedrock blocks -- there's
no need to know Bedrock's own (quite different) block id/property scheme.
"""
import os
import shutil
import time
import zipfile

from amulet.api.block import Block
from amulet.api.level import World
from amulet.level.formats.leveldb_world import LevelDBFormat
from amulet import StringTag

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WORLD_NAME = "Castle World"
PLATFORM = "bedrock"
BEDROCK_VERSION = (1, 21, 110)
JAVA_VERSION_TAG = ("java", (1, 20, 4))
BEDROCK_VERSION_TAG = (PLATFORM, BEDROCK_VERSION)
DIMENSION = "minecraft:overworld"

CX, CZ = 0, 0        # world-space centre of the castle
GY = 63              # y of top grass block (ground surface)
GROUND = GY + 1      # 64, first air/walkable layer

TERRAIN_HALF = 72    # flat grassy clearing extends this far from centre

# Blocks (Java Edition ids/properties -- translated to Bedrock automatically)
B = lambda name, **props: Block("minecraft", name, properties={k: StringTag(v) for k, v in props.items()} or None)
BEDROCK_BLOCK = B("bedrock")
STONE = B("stone")
DIRT = B("dirt")
GRASS = B("grass_block")
WATER = B("water")
AIR = B("air")
STONE_BRICK = B("stone_bricks")
MOSSY_BRICK = B("mossy_stone_bricks")
CHISELED_BRICK = B("chiseled_stone_bricks")
WALL = B("stone_brick_wall")
OAK_PLANKS = B("oak_planks")
OAK_FENCE = B("oak_fence")
GLASS_PANE = B("glass_pane")
TORCH = B("torch")
WALL_TORCH = lambda facing: B("wall_torch", facing=facing)
GRAVEL = B("gravel")
LADDER = lambda facing: B("ladder", facing=facing)
RED_BANNER = B("red_banner")


def w(x, z):
    """local castle coords -> world coords"""
    return CX + x, CZ + z


def fill(world, block, x1, y1, z1, x2, y2, z2):
    wx1, wz1 = w(x1, z1)
    wx2, wz2 = w(x2, z2)
    for x in range(min(wx1, wx2), max(wx1, wx2) + 1):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for z in range(min(wz1, wz2), max(wz1, wz2) + 1):
                world.set_version_block(x, y, z, DIMENSION, JAVA_VERSION_TAG, block)


def setb(world, block, x, y, z):
    wx, wz = w(x, z)
    world.set_version_block(wx, y, wz, DIMENSION, JAVA_VERSION_TAG, block)


def hollow_box(world, block, x1, y1, z1, x2, y2, z2, thickness=1):
    """Walls of a box, floor+ceiling solid, interior hollow."""
    fill(world, block, x1, y1, z1, x2, y1, z2)  # floor
    fill(world, block, x1, y2, z1, x2, y2, z2)  # ceiling
    fill(world, block, x1, y1, z1, x2, y2, z1 + thickness - 1)  # -z wall
    fill(world, block, x1, y1, z2 - thickness + 1, x2, y2, z2)  # +z wall
    fill(world, block, x1, y1, z1, x1 + thickness - 1, y2, z2)  # -x wall
    fill(world, block, x2 - thickness + 1, y1, z1, x2, y2, z2)  # +x wall


def tower(world, cx, cz, radius, y0, top, wall_thick=2, roof=True, torch_top=True):
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
                fill(world, STONE_BRICK, x, y0, z, x, top, z)
            else:
                setb(world, STONE_BRICK, x, y0 - 1, z)  # floor
    # crenellations ring at top
    for dz in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            d2 = dx * dx + dz * dz
            if r2_in <= d2 <= r2_out and (dx + dz) % 2 == 0:
                setb(world, WALL, cx + dx, top + 1, cz + dz)
    # window slits, punched straight through the wall thickness on all 4 sides
    for wy in (y0 + 3, y0 + 7, y0 + 11):
        if wy >= top - 1:
            continue
        for r in range(radius - wall_thick - 1, radius + 1):
            setb(world, AIR, cx + r, wy, cz)
            setb(world, AIR, cx + r, wy + 1, cz)
            setb(world, AIR, cx - r, wy, cz)
            setb(world, AIR, cx - r, wy + 1, cz)
            setb(world, AIR, cx, wy, cz + r)
            setb(world, AIR, cx, wy + 1, cz + r)
            setb(world, AIR, cx, wy, cz - r)
            setb(world, AIR, cx, wy + 1, cz - r)
    if roof:
        rr = radius - 1
        ry = top + 2
        while rr >= 0:
            r2 = rr * rr
            for dz in range(-rr, rr + 1):
                for dx in range(-rr, rr + 1):
                    if dx * dx + dz * dz <= r2:
                        setb(world, MOSSY_BRICK, cx + dx, ry, cz + dz)
            rr -= 1
            ry += 1
        if torch_top:
            setb(world, OAK_FENCE, cx, ry, cz)
            setb(world, TORCH, cx, ry + 1, cz)


def build(world):
    print("Terrain...")
    fill(world, BEDROCK_BLOCK, -TERRAIN_HALF, 0, -TERRAIN_HALF, TERRAIN_HALF, 0, TERRAIN_HALF)
    fill(world, STONE, -TERRAIN_HALF, 1, -TERRAIN_HALF, TERRAIN_HALF, 58, TERRAIN_HALF)
    fill(world, DIRT, -TERRAIN_HALF, 59, -TERRAIN_HALF, TERRAIN_HALF, 62, TERRAIN_HALF)
    fill(world, GRASS, -TERRAIN_HALF, GY, -TERRAIN_HALF, TERRAIN_HALF, GY, TERRAIN_HALF)

    print("Moat...")
    for z in range(-48, 49):
        for x in range(-48, 49):
            d = max(abs(x), abs(z))
            if 42 <= d <= 47:
                if -3 <= x <= 3 and z >= 38:
                    continue  # leave gap for bridge on south approach
                fill(world, WATER, x, 59, z, x, 63, z)

    print("Bridge...")
    fill(world, OAK_PLANKS, -3, GROUND, 38, 3, GROUND, 48)
    fill(world, OAK_FENCE, -3, GROUND + 1, 38, -3, GROUND + 1, 48)
    fill(world, OAK_FENCE, 3, GROUND + 1, 38, 3, GROUND + 1, 48)
    for z in range(38, 49, 4):
        setb(world, TORCH, -3, GROUND + 2, z)
        setb(world, TORCH, 3, GROUND + 2, z)
    fill(world, GRAVEL, -4, GY, 48, 4, GY, 60)

    print("Curtain walls...")
    WBOT, WTOP = GROUND, GROUND + 10
    fill(world, STONE_BRICK, -26, WBOT, -33, 26, WTOP, -31)
    fill(world, STONE_BRICK, -26, WBOT, 31, 26, WTOP, 33)
    fill(world, STONE_BRICK, -33, WBOT, -26, -31, WTOP, 26)
    fill(world, STONE_BRICK, 31, WBOT, -26, 33, WTOP, 26)
    fill(world, AIR, -25, WBOT, -32, 25, WTOP - 1, -32)
    fill(world, AIR, -25, WBOT, 32, 25, WTOP - 1, 32)
    fill(world, AIR, -32, WBOT, -25, -32, WTOP - 1, 25)
    fill(world, AIR, 32, WBOT, -25, 32, WTOP - 1, 25)
    for x in range(-26, 27, 2):
        setb(world, WALL, x, WTOP + 1, -33)
        setb(world, WALL, x, WTOP + 1, 33)
    for z in range(-26, 27, 2):
        setb(world, WALL, -33, WTOP + 1, z)
        setb(world, WALL, 33, WTOP + 1, z)
    for coord in range(-20, 21, 8):
        for wy in (WBOT + 3, WBOT + 6):
            setb(world, AIR, coord, wy, -33)
            setb(world, AIR, coord, wy, 33)
            setb(world, AIR, -33, wy, coord)
            setb(world, AIR, 33, wy, coord)

    print("Corner towers...")
    for tx in (-32, 32):
        for tz in (-32, 32):
            tower(world, tx, tz, 7, GROUND, GROUND + 20)

    print("Gatehouse...")
    GBOT, GTOP = GROUND, GROUND + 20
    fill(world, STONE_BRICK, -9, GBOT, 30, -5, GTOP, 39)
    fill(world, STONE_BRICK, 5, GBOT, 30, 9, GTOP, 39)
    fill(world, AIR, -8, GBOT, 31, -6, GTOP - 3, 38)
    fill(world, AIR, 6, GBOT, 31, 8, GTOP - 3, 38)
    fill(world, STONE_BRICK, -9, GTOP - 2, 30, 9, GTOP - 2, 39)
    for x in (-9, -5, 5, 9):
        for z in range(30, 40, 2):
            setb(world, WALL, x, GTOP + 1, z)
    fill(world, AIR, -3, GROUND, 27, 3, GROUND + 5, 40)
    fill(world, STONE_BRICK, -4, GROUND + 6, 27, 4, GROUND + 6, 40)
    fill(world, CHISELED_BRICK, -4, GROUND, 27, -4, GROUND + 5, 27)
    fill(world, CHISELED_BRICK, 4, GROUND, 27, 4, GROUND + 5, 27)
    setb(world, WALL_TORCH("east"), -4, GROUND + 3, 33)
    setb(world, WALL_TORCH("west"), 4, GROUND + 3, 33)

    print("Courtyard path...")
    fill(world, STONE_BRICK, -2, GY, 9, 2, GY, 27)
    fill(world, GRAVEL, -3, GY, 9, -3, GY, 27)
    fill(world, GRAVEL, 3, GY, 9, 3, GY, 27)
    for z in range(10, 26, 6):
        setb(world, TORCH, -3, GROUND, z)
        setb(world, TORCH, 3, GROUND, z)

    print("Keep...")
    hollow_box(world, STONE_BRICK, -8, GROUND, -8, 8, GROUND + 32, 8, thickness=2)
    for fy in (GROUND + 10, GROUND + 20):
        fill(world, OAK_PLANKS, -6, fy, -6, 6, fy, 6)
        fill(world, AIR, -1, fy, -1, 1, fy, 1)
    fill(world, LADDER("north"), 2, GROUND + 1, 7, 2, GROUND + 31, 7)
    fill(world, AIR, -1, GROUND, 7, 1, GROUND + 3, 9)
    setb(world, TORCH, -2, GROUND + 2, 8)
    setb(world, TORCH, 2, GROUND + 2, 8)
    for fy in (GROUND + 5, GROUND + 15, GROUND + 25):
        fill(world, AIR, -7, fy, -3, -7, fy + 1, 3)
        fill(world, GLASS_PANE, -8, fy, -3, -8, fy + 1, 3)
        fill(world, AIR, 7, fy, -3, 7, fy + 1, 3)
        fill(world, GLASS_PANE, 8, fy, -3, 8, fy + 1, 3)
        fill(world, AIR, -3, fy, -7, 3, fy + 1, -7)
        fill(world, GLASS_PANE, -3, fy, -8, 3, fy + 1, -8)
        fill(world, AIR, -3, fy, 7, 3, fy + 1, 7)
        fill(world, GLASS_PANE, -3, fy, 8, 3, fy + 1, 8)
    top = GROUND + 32
    for x in range(-8, 9, 2):
        setb(world, WALL, x, top + 1, -8)
        setb(world, WALL, x, top + 1, 8)
    for z in range(-8, 9, 2):
        setb(world, WALL, -8, top + 1, z)
        setb(world, WALL, 8, top + 1, z)
    rr = 8
    ry = top + 1
    while rr >= 0:
        fill(world, MOSSY_BRICK, -rr, ry, -rr, rr, ry, rr)
        rr -= 1
        ry += 1
    setb(world, OAK_FENCE, 0, ry, 0)
    setb(world, RED_BANNER, 0, ry + 1, 0)


def set_level_dat_fields(fmt):
    from amulet import IntTag, LongTag, ByteTag, StringTag as S

    c = fmt.root_tag.compound
    c["LevelName"] = S(WORLD_NAME)
    c["GameType"] = IntTag(1)  # creative
    c["Difficulty"] = IntTag(2)  # normal
    c["SpawnX"] = IntTag(CX)
    c["SpawnY"] = IntTag(GROUND + 1)
    c["SpawnZ"] = IntTag(CZ + 44)
    c["RandomSeed"] = LongTag(8391137216498)
    c["Time"] = LongTag(6000)
    c["commandsEnabled"] = ByteTag(1)
    c["ForceGameType"] = ByteTag(0)


def make_mcworld(world_dir, mcworld_path):
    if os.path.exists(mcworld_path):
        os.remove(mcworld_path)
    with zipfile.ZipFile(mcworld_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(world_dir):
            for name in files:
                full = os.path.join(root, name)
                arc = os.path.relpath(full, world_dir)
                zf.write(full, arc)


if __name__ == "__main__":
    import sys
    out_dir = sys.argv[1]
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)

    fmt = LevelDBFormat(out_dir)
    fmt.create_and_open(PLATFORM, BEDROCK_VERSION, overwrite=True)
    set_level_dat_fields(fmt)
    fmt.save()
    fmt.close()

    world = World(out_dir, fmt)
    t0 = time.time()
    build(world)
    print(f"Built in {time.time() - t0:.1f}s, saving...")
    world.save()
    world.close()

    mcworld_path = out_dir.rstrip("/\\") + ".mcworld"
    make_mcworld(out_dir, mcworld_path)
    print("World written to", out_dir)
    print("Importable package:", mcworld_path)
