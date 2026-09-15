# Minecraft Worlds

## Castle World

A Java Edition (Anvil format) world save featuring a stone-brick castle:
a moat with a causeway bridge, a gatehouse, four corner towers, crenellated
curtain walls, and a tall central keep with windows, floors, and a
stepped roof.

### How to play it

1. Copy the `CastleWorld/` folder into your Minecraft `saves` directory:
   - Windows: `%appdata%\.minecraft\saves\`
   - macOS: `~/Library/Application Support/minecraft/saves/`
   - Linux: `~/.minecraft/saves/`
2. Launch Minecraft Java Edition and select **Castle World** from the
   world list. The client will silently upgrade the old world format on
   first load — that's expected.
3. You'll spawn in creative mode on the bridge, facing the gate.

### Regenerating / customizing it

The world was generated procedurally with `scripts/build_castle.py`
using the [`anvil-parser2`](https://pypi.org/project/anvil-parser2/)
library (raw `.mca` region files + a hand-built `level.dat`, no running
Minecraft instance required). To rebuild or tweak the layout:

```
pip install -r scripts/requirements.txt
python3 scripts/build_castle.py CastleWorld
```

Edit the constants and the `build()` function in `build_castle.py` to
change the castle's size, position, or add more detail.
