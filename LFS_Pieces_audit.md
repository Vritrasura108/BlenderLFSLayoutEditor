# LFS Pieces Collection Audit

Audit of the `LFS Pieces` collection structure and object naming in `lyt_editor.blend`.

**Total:** 27 subcollections under `LFS Pieces`

---

## Structural Issues

### Nested duplicate folders
- **`[RAMP]` → `[Ramp]`**: Top-level `RAMP` contains a single child `Ramp` which has the actual objects and 16 height subcollections (`Ramp_025` through `Ramp_400`). Should be flattened.
- **`[Slab]`**: Subcollection names have inconsistent formatting:
  - `[Slab _60]` and `[Slab _66]` have a **space before the number** (should be `Slab_60`, `Slab_66`)
  - Other subcollections (`Slab_00` through `Slab_90`) are fine

### Railing is empty
- `[Railing]` collection is empty (0 objects, 0 subcollections)
- `Railing1` and `Railing2` objects are inside `[Barrier]` collection instead

### Stray object in Kerb
- `[Kerb]` contains `Texte` (type=CURVE) which doesn't belong there

---

## Object Naming Issues

### Slab (subcollections of `[Slab]`)
- **Pattern:** `Slab_{width}_{length}_{pitch}` (expected: pitch = 00, 06, 12, ... 90)
- **Problem:** Most objects use Blender `.NNN` duplicate suffixes instead of proper pitch values
- Only ONE object per subcollection has a correct name (e.g. `Slab_4_2_06`), the rest are like `Slab_16_16_.002`, `Slab_2_8_.002`
- The `.NNN` suffix is a Blender auto-deduplicate artefact from duplicating, NOT a pitch value
- `[Slab_84]` has only 15 objects (missing one)
- `[Slab_00]` has only 15 objects (missing `Slab_2_16_00` or equivalent)

### Ramp (subcollections of `[RAMP]` → `[Ramp]`)
- **Pattern:** `Ramp_{width}_{length}_{height}` (expected: height = 025, 050, ... 400)
- **Same problem as Slab:** Most objects use `.NNN` suffixes. Only `Ramp_4_2_XXX` has the correct height, rest are like `Ramp_16_16_.005`
- Template objects `Ramp` and `Ramp.001` sit at the `[Ramp]` level (not in any height subcollection)
- Some subcollections have 15 objects, some have 16, one has 17 (inconsistent)

### Marker_Distance
- **Pattern:** Should be `Marker_Distance_{value}` (values: 25, 50, 75, 100, 125, 150, 175, 200)
- **Problem:** Named `Marker_Distance`, `Marker_Distance_.001` through `Marker_Distance_.007` - using Blender suffixes instead of distance values
- 8 objects total, all with wrong names

### Kerb
- **Pattern:** Should be `Kerb_{Colour}_{variant}` (e.g. `Kerb_Blue_1`, `Kerb_Blue_2`)
- **Problem:** Named `Kerb_Blue` and `Kerb_Blue_.001` - the `.001` is a Blender suffix, not a variant number
- Same for all 8 colours: each has base + `.001` duplicate
- Exception: `Kerb_Green_2` exists correctly named (but `Kerb_Green_.001` also exists)

### Double-dot duplicates (`..001`)
Several collections have objects with `..001` in the name (double period), which is a Blender renaming artefact:
- **RampWall**: `RampWall_4_200_Blue..001`, `RampWall_4_200_Grey..001`, `RampWall_4_200_Red..001` (also `RampWall_4_200_Red.001`), `RampWall_4_200_Yellow..001`
- **SlabWall**: `SlabWall_4_24_Grey..001`, `SlabWall_4_30_Grey..001`, `SlabWall_4_24_Blue..001`, `SlabWall_4_30_Blue..001`, `SlabWall_4_24_Red..001`, `SlabWall_4_30_Red..001`, `SlabWall_4_24_Yellow..001`, `SlabWall_4_30_Yellow..001`
- **Wall**: `Wall_4_200_Blue..001`, `Wall_4_200_Grey..001`, `Wall_4_200_Red..001`, `Wall_4_200_Yellow..001`

### SlabWall - Missing objects
Each colour should have 64 objects (4 lengths × 16 pitches). Some `length=4` pitches appear missing (42, 48 gaps), replaced by `..001` duplicates of adjacent pitches (24, 30).

### Letter_Board
- Many objects have `.001`/`.002`/`.008` suffixes (Blender duplicates)
- e.g. `Letter_Board_0_Yellow.001`, `Letter_Board_A_Blue.001`, `Letter_Board_M_Red.008`
- These are likely backup copies from manual work

### Paint_Letters / Paint_Arrow
- Some have `.001` suffixes: `Paint_Letters_0_White.001`, `Paint_Arrow_LEFT_White.001`, etc.
- `Paint_Letters_SLASH_Yellow` AND `Paint_Letters_SLASH_Yellow.001` both exist (true duplicate)

---

## Correctly Named Collections (no issues found)

| Collection | Objects | Format |
|---|---|---|
| Armco | 6 | `Armco_{variant}_{condition}` |
| Bale | 1 | `Bale` |
| Banner | 2 | `Banner1`, `Banner2` |
| Barrier | 5 | `BarrierLong`, `BarrierRed`, `BarrierWhite`, `Railing1`, `Railing2` |
| Chalk | 40 | `Chalk{Type}_{Colour}` |
| Cone | 35 | `Cone{Type}_{Colour}` |
| Control | 5 templates + 7 subcollections | Checkpoint/FinishLine/RouteChecker/etc properly named |
| Pillar | 256 | `Pillar_{sizex:03d}_{sizey:03d}_{height:03d}` |
| Post | 7 | `Post_{Colour}` |
| Marquee | 7 | `Marquee_{Colour}` |
| Bin1/Bin2 | 6/7 | `Bin{N}_{Colour}` |
| Sign | 16 | `Sign_Speed_*`, `Sign_Metal_*`, `Chevron_*` |
| Speedhump | 4 | `SpeedHump{size}` |
| Tyre | 48 | `Tyre{Type}_{Colour}` |
| Vehicles | 4 | `SUV`, `Van`, `Truck`, `Ambulance` |
| Wall | 256 (4 colours × 4 lengths × 16 heights) | `Wall_{length}_{height:03d}_{Colour}` |
| RampWall | 256 (4 colours × 4 lengths × 16 heights) | `RampWall_{length}_{height:03d}_{Colour}` |
| ShortSlabWall | 256 (4 colours × 4 sizes × 16 pitches) | `ShortSlabWall_{sizey:03d}_{pitch:02d}_{Colour}` |

---

## Naming Convention Summary

For concrete objects, the established naming pattern (from correctly named collections) is:
- **Sizes** (sizex, sizey): 3-digit zero-padded (`025`, `050`, `075`, `100`)
- **Heights**: 3-digit zero-padded (`025` through `400`)
- **Pitches**: 2-digit zero-padded (`00` through `90`)
- **Widths/Lengths**: unpadded (`2`, `4`, `8`, `16`)
- **Angles** (Wedge): 3-digit zero-padded (`056` through `900`) — tenths of degrees
- **Colours**: capitalized word (`Grey`, `Blue`, `Red`, `Yellow`)

### Full type-by-type format (verified against import & export scripts)

| Type | Index | Format | Example |
|------|-------|--------|---------|
| Slab | 172 | `Slab_{width}_{length}_{pitch:02d}` | `Slab_4_2_06` |
| Ramp | 173 | `Ramp_{width}_{length}_{height:03d}` | `Ramp_4_2_025` |
| Wall | 174 | `Wall_{length}_{height:03d}_{Colour}` | `Wall_2_025_Blue` |
| Pillar | 175 | `Pillar_{sizex:03d}_{sizey:03d}_{height:03d}` | `Pillar_025_025_025` |
| SlabWall | 176 | `SlabWall_{length}_{pitch:02d}_{Colour}` | `SlabWall_2_00_Grey` |
| RampWall | 177 | `RampWall_{length}_{height:03d}_{Colour}` | `RampWall_2_025_Blue` |
| ShortSlabWall | 178 | `ShortSlabWall_{sizey:03d}_{pitch:02d}_{Colour}` | `ShortSlabWall_025_00_Blue` |
| Wedge | 179 | `Wedge_{length}_{angle:03d}_{Colour}` | `Wedge_2_056_Blue` |
| Marker_Distance | 84 | `Marker_Distance_{value}` | `Marker_Distance_25` |
