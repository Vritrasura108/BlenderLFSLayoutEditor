#
#   name        LFS layout Blender Tool - Export (0.8A ready)
#   version     2.0 (refactored: shared code in lfs_lyt_common, callable export_to_lyt)
#   author      Vritrasura, Nex_ (patched)
#

import bpy
import struct
import math
import os
import sys
import re

# Ensure scripts/ is on sys.path so lfs_lyt_common can be imported
_scripts_dir = os.path.join(os.path.dirname(bpy.data.filepath), "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from lfs_lyt_common import (
    GRID_XY, GRID_Z, GRID_ROT_Z,
    width2flags, length2flags, sizex2flags, sizey2flags,
    height2flags, pitch2flags, angle2flags,
    concretecolour2flags, chalkcolour2flags, tyrecolour2flags,
    carpos2flags, diameter2flags, restrictedarea2flags,
    normalize_position, normalize_rotation_z, load_config,
    PAINT_GLYPH_TO_ID, PAINT_ARROW_TO_ID,
    LETTERBOARD_GLYPH_TO_ID,
    CONE_FLAGS_MAP,
    POST_COLOUR_TO_FLAGS, MARQUEE_COLOUR_TO_FLAGS,
    BIN1_COLOUR_TO_FLAGS, BIN2_COLOUR_TO_FLAGS,
    CHEVRON_COLOUR_TO_FLAGS, ARMCO_VARIANT_TO_FLAGS,
    SIGN_SPEED_NAME_TO_FLAGS, SIGN_METAL_NAME_TO_FLAGS,
    MARKER_CORNER_NAME_TO_FLAGS, MARKER_DISTANCE_NAME_TO_FLAGS,
    KERB_COLOUR_TO_NUM,
)

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
def normalizeObject(obj, offset=(0, 0, 0)):
    pos_orig = obj.location.copy()

    nx, ny, nz = normalize_position(
        obj.location.x, obj.location.y, obj.location.z,
        offset[0], offset[1], offset[2],
    )
    obj.location.x = nx
    obj.location.y = ny
    obj.location.z = nz

    obj.rotation_euler.z = normalize_rotation_z(obj.rotation_euler.z)

    if (pos_orig.x, pos_orig.y, pos_orig.z) != (obj.location.x, obj.location.y, obj.location.z):
        print("Normalizing object position...")
        print(f"   original pos:   {pos_orig.x} {pos_orig.y} {pos_orig.z}")
        print(f"   normalized pos: {nx} {ny} {nz}")

# -------------------------------------------------------
# Kerb (Index 132) - flags for LFS 0.8A
# -------------------------------------------------------
def kerb_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Kerb_(White|Grey|Red|Blue|Cyan|Green|Orange|Yellow)_(\d+)(?:_M(\d+))?$", name)
    if not m:
        return 0

    colour = m.group(1)
    variant = int(m.group(2))
    forced_map = m.group(3)

    c_num = KERB_COLOUR_TO_NUM[colour] & 0x07

    variant = 1 if variant <= 1 else 2
    shade = 0 if variant == 1 else 1

    mapping = KERB_COLOUR_TO_NUM.get(colour, 0)
    if forced_map is not None:
        mapping = max(0, min(int(forced_map), 15))

    flags = (c_num & 0x07) | ((shade & 0x01) << 3) | ((mapping & 0x0F) << 4)
    return flags & 0xFF

def chevron_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Chevron_(Left|Right)_(White|Black)$", name, re.IGNORECASE)
    if not m:
        return 0
    colour = m.group(2).capitalize()
    return CHEVRON_COLOUR_TO_FLAGS.get(colour, 0) & 0xFF

def armco_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Armco_(1|3|5)_(Old|New)$", name, re.IGNORECASE)
    if not m:
        return 0
    variant = m.group(2).capitalize()
    return ARMCO_VARIANT_TO_FLAGS.get(variant, 0x00) & 0xFF

# -------------------------------------------------------
# Posts / Marquee / Bins
# -------------------------------------------------------
def post_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Post_(Green|Orange|Red|White|Blue|Yellow|Cyan)$", name)
    if not m:
        m = re.match(r"^Post(Green|Orange|Red|White|Blue|Yellow|Cyan)$", name)
        if not m:
            return 0
    return POST_COLOUR_TO_FLAGS[m.group(1)] & 0xFF

def marquee_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Marquee_(White|Grey|Blue|Red|Yellow|Green|Black)$", name)
    if not m:
        m = re.match(r"^Marquee(White|Grey|Blue|Red|Yellow|Green|Black)$", name)
        if not m:
            return 0
    return MARQUEE_COLOUR_TO_FLAGS[m.group(1)] & 0xFF

def bin1_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Bin1_(Green|Orange|Red|White|Blue|Yellow)$", name)
    if not m:
        m = re.match(r"^Bin1(Green|Orange|Red|White|Blue|Yellow)$", name)
        if not m:
            return 0
    return BIN1_COLOUR_TO_FLAGS[m.group(1)] & 0xFF

def bin2_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Bin2_(Green|Red|Blue|Yellow|Black|White|Orange)$", name)
    if not m:
        m = re.match(r"^Bin2(Green|Red|Blue|Yellow|Black|White|Orange)$", name)
        if not m:
            return 0
    return BIN2_COLOUR_TO_FLAGS[m.group(1)] & 0xFF

# -------------------------------------------------------
# Paint / Markers / Cones / Letterboard / Signs
# -------------------------------------------------------
def paint_letters_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(
        r"^Paint_Letters_([A-Z0-9]+|LEFT|RIGHT|UP|DOWN|HASH|AT|DOT|COLON|SLASH|LPAREN|RPAREN|AMP|BLANK)_(White|Yellow)$",
        name
    )
    if not m:
        return 0
    glyph = m.group(1)
    colour = m.group(2)
    if glyph not in PAINT_GLYPH_TO_ID:
        return 0
    glyph_id = PAINT_GLYPH_TO_ID[glyph]
    colour_bit = 1 if colour == "Yellow" else 0
    return ((glyph_id << 1) | colour_bit) & 0xFF

def paint_arrow_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Paint_Arrow_(LEFT|RIGHT|STRAIGHTLEFT|STRAIGHTRIGHT|CURVEL|CURVER|STRAIGHTON)_(White|Yellow)$", name)
    if not m:
        return 0
    arrow = m.group(1)
    colour = m.group(2)
    arrow_id = PAINT_ARROW_TO_ID[arrow]
    colour_bit = 1 if colour == "Yellow" else 0
    return ((arrow_id << 1) | colour_bit) & 0xFF

def cone_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^(?:Cone|Cone1|Cone2|Cone_Tall1|Cone_Tall2|Cone_Pointer)_?(White|Red|Blue|Cyan|Green|Orange|Yellow)?$", name)
    if not m:
        return 0
    colour = m.group(1)
    return CONE_FLAGS_MAP.get(colour, 0) & 0xFF

def marker_corner_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Marker_Corner_(CurveL|CurveR|HardL|HardR|UR|UL|L|R|KinkL|KinkR|LR|RL|SL|SR|S2L|S2R)$", name)
    if not m:
        return 0
    mapping = MARKER_CORNER_NAME_TO_FLAGS[m.group(1)]
    return ((mapping & 0x0F) << 3) & 0xFF

def marker_distance_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Marker_Distance_(25|50|75|100|125|150|200|250)$", name)
    if not m:
        return 0
    mapping = MARKER_DISTANCE_NAME_TO_FLAGS[m.group(1)]
    return ((mapping & 0x0F) << 3) & 0xFF

def letterboard_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Letter_Board_([A-Z]|[0-9]|LEFT|RIGHT|UP|DOWN|HASH|AT|DOT|COLON|SLASH|LPAREN|RPAREN|AMP|BLANK)_(White|Yellow|Red|Blue)$", name, re.IGNORECASE)
    if not m:
        return 0
    glyph = m.group(1).upper()
    colour = m.group(2).capitalize()
    if glyph == "BLANK":
        m_num = 48
    else:
        m_num = LETTERBOARD_GLYPH_TO_ID.get(glyph)
        if m_num is None:
            return 0
    colour_bit = 1 if colour in ("Yellow", "Blue") else 0
    base = ((m_num << 1) | colour_bit) & 0xFF
    # IMPORTANT: floating bit so LFS respects Z height for boards
    return (base | 0x80) & 0xFF

def sign_speed_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Sign_Speed_(50_kmh|80_kmh|40_mph|50_mph)$", name)
    if not m:
        return 0
    mapping = SIGN_SPEED_NAME_TO_FLAGS[m.group(1)]
    return ((mapping & 0x0F) << 3) & 0xFF

def sign_metal_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Sign_Metal_(KeepLeft|KeepRight|Left|Right|UpLeft|UpRight|Forward|NoEntry)$", name)
    if not m:
        return 0
    mapping = SIGN_METAL_NAME_TO_FLAGS[m.group(1)]
    return ((mapping & 0x0F) << 3) & 0xFF

# -------------------------------------------------------
# Name -> flags / index
# -------------------------------------------------------
def name2flags(objname: str) -> int:
    name = objname.split(".")[0]
    field = name.split("_")
    block = field[0]
    flags = 0x00

    if name.startswith("Post"):
        return post_flags_from_name(name)
    if name.startswith("Marquee"):
        return marquee_flags_from_name(name)
    if name.startswith("Bin1"):
        return bin1_flags_from_name(name)
    if name.startswith("Bin2"):
        return bin2_flags_from_name(name)
    if name.startswith("Cone"):
        return cone_flags_from_name(name)
    if name.startswith("Kerb_"):
        return kerb_flags_from_name(name)
    if name.startswith("Paint_Letters_"):
        return paint_letters_flags_from_name(name)
    if name.startswith("Paint_Arrow_"):
        return paint_arrow_flags_from_name(name)
    if name.startswith("Marker_Corner"):
        return marker_corner_flags_from_name(name)
    if name.startswith("Marker_Distance"):
        return marker_distance_flags_from_name(name)
    if name.startswith("Letter_Board"):
        return letterboard_flags_from_name(name)
    if name.startswith("Sign_Speed"):
        return sign_speed_flags_from_name(name)
    if name.startswith("Sign_Metal"):
        return sign_metal_flags_from_name(name)
    if name.startswith("Chevron_"):
        return chevron_flags_from_name(name)
    if name.startswith("Armco_"):
        return armco_flags_from_name(name)

    if block == "Slab":
        width = int(field[1])
        length = int(field[2])
        pitch = int(field[3])
        flags = width2flags(width) | length2flags(length) | pitch2flags(pitch)

    elif block == "Ramp":
        width = int(field[1])
        length = int(field[2])
        height = int(field[3])
        flags = width2flags(width) | length2flags(length) | height2flags(height)

    elif block in ["Wall", "RampWall"]:
        colour = field[3]
        length = int(field[1])
        height = int(field[2])
        flags = concretecolour2flags(colour) | length2flags(length) | height2flags(height)

    elif block == "Pillar":
        sizex = int(field[1])
        sizey = int(field[2])
        height = int(field[3])
        flags = sizex2flags(sizex) | sizey2flags(sizey) | height2flags(height)

    elif block == "SlabWall":
        colour = field[3]
        length = int(field[1])
        pitch = int(field[2])
        flags = concretecolour2flags(colour) | length2flags(length) | pitch2flags(pitch)

    elif block == "ShortSlabWall":
        colour = field[3]
        sizey = int(field[1])
        pitch = int(field[2])
        flags = concretecolour2flags(colour) | sizey2flags(sizey) | pitch2flags(pitch)

    elif block == "Wedge":
        colour = field[3]
        length = int(field[1])
        angle = int(field[2])
        flags = concretecolour2flags(colour) | length2flags(length) | angle2flags(angle)

    elif block in ["ChalkLeft", "ChalkLeft2", "ChalkLeft3", "ChalkRight", "ChalkRight2", "ChalkRight3",
                   "ChalkLine", "ChalkLine2", "ChalkLineAhead", "ChalkLineAhead2"]:
        colour = field[1]
        flags = chalkcolour2flags(colour)

    elif block in ["TyreSingle", "TyreSingleBig", "TyreStack2", "TyreStack3", "TyreStack4",
                   "TyreStack2Big", "TyreStack3Big", "TyreStack4Big"]:
        colour = field[1]
        flags = tyrecolour2flags(colour)

    elif block == "FinishLine":
        flags = ((int(field[1]) >> 1) << 2)

    elif block in ["Checkpoint1", "Checkpoint2", "Checkpoint3"]:
        t = int(re.search(r"\d+", block).group())
        flags = ((int(field[1]) >> 1) << 2) | (t & 0x03)

    elif block == "StartPosition":
        flags = carpos2flags(int(field[1]))

    elif block == "PitStartPoint":
        flags = carpos2flags(int(field[1]))

    elif block == "RouteChecker":
        flags = diameter2flags(int(field[1]))

    elif block == "RestrictedArea":
        flags = restrictedarea2flags(field[1], int(field[2]))

    elif block == "InSimCheckpoint":
        flags = diameter2flags(int(field[1]))

    elif block == "InSimCircle":
        flags = diameter2flags(int(field[1]))

    return flags & 0xFF

def name2blockid(objname: str) -> int:
    name = objname.split(".")[0]

    if name.startswith("Paint_Letters"):
        return 16
    if name.startswith("Paint_Arrow"):
        return 17
    if name.startswith("Cone1"):
        return 20
    if name.startswith("Cone2"):
        return 21
    if name.startswith("Cone_Tall1"):
        return 32
    if name.startswith("Cone_Tall2"):
        return 33
    if name.startswith("Cone_Pointer"):
        return 40
    if name.startswith("Marker_Corner"):
        return 64
    if name.startswith("Marker_Distance"):
        return 84
    if re.match(r"^Letter_Board_.*_(White|Yellow)$", name, re.IGNORECASE):
        return 92
    if re.match(r"^Letter_Board_.*_(Red|Blue)$", name, re.IGNORECASE):
        return 93

    if name.startswith("Armco_1_"): return 96
    if name.startswith("Armco_3_"): return 97
    if name.startswith("Armco_5_"): return 98

    if name.startswith("Post"):
        return 136
    if name.startswith("Marquee"):
        return 140
    if name.startswith("Bin1"):
        return 145
    if name.startswith("Bin2"):
        return 146

    if name.startswith("Sign_Metal"):
        return 160
    if name.startswith("Chevron_Right"):
        return 164
    if name.startswith("Chevron_Left"):
        return 165

    if name.startswith("Sign_Speed_"):
        return 168

    if name.startswith("Kerb_") or name.startswith("Kerb"):
        return 132

    field = name.split("_")
    block = field[0]

    match block:
        case "AutocrossStart": return 0
        case "Bale": return 144
        case "Banner1": return 112
        case "Banner2": return 113
        case "BarrierLong": return 104
        case "BarrierRed": return 105
        case "BarrierWhite": return 106
        case "ChalkLine": return 4
        case "ChalkLine2": return 5
        case "ChalkLineAhead": return 6
        case "ChalkLineAhead2": return 7
        case "ChalkLeft": return 8
        case "ChalkLeft2": return 9
        case "ChalkLeft3": return 10
        case "ChalkRight": return 11
        case "ChalkRight2": return 12
        case "ChalkRight3": return 13
        case "Checkpoint1" | "Checkpoint2" | "Checkpoint3": return 0
        case "Cone1": return 20
        case "Cone2": return 21
        case "Cone_Tall1": return 32
        case "Cone_Tall2": return 33
        case "Cone_Pointer": return 40
        case "FinishLine": return 0
        case "InSimCheckpoint": return 252
        case "InSimCircle": return 253
        case "Pillar": return 175
        case "PitStartPoint": return 185
        case "PitStopBox": return 186
        case "Railing1": return 147
        case "Railing2": return 148
        case "Ramp": return 173
        case "Ramp1": return 120
        case "Ramp2": return 121
        case "RampWall": return 177
        case "RestrictedArea": return 254
        case "RouteChecker": return 255
        case "ShortSlabWall": return 178
        case "Slab": return 172
        case "SlabWall": return 176
        case "StartLights": return 149
        case "StartPosition": return 184
        case "SUV": return 124
        case "Van": return 125
        case "Truck": return 126
        case "Ambulance": return 127
        case "SpeedHump10m": return 128
        case "SpeedHump6m":  return 129
        case "SpeedHump2m":  return 130
        case "SpeedHump1m":  return 131
        case "TyreSingle": return 48
        case "TyreStack2": return 49
        case "TyreStack3": return 50
        case "TyreStack4": return 51
        case "TyreSingleBig": return 52
        case "TyreStack2Big": return 53
        case "TyreStack3Big": return 54
        case "TyreStack4Big": return 55
        case "Wall": return 174
        case "Wedge": return 179
        case _:
            return 0x00

# -------------------------------------------------------
# Export single object to file handle
# -------------------------------------------------------
def exportObject(obj, f, offset=(0, 0, 0)):
    x = obj.location[0] - offset[0]
    y = obj.location[1] - offset[1]
    z = obj.location[2] - offset[2]

    x = round(x * 16.0)
    y = round(y * 16.0)
    z = round(z * 4.0)

    error = False
    if x < -32768 or x > 32767:
        error = True
    if y < -32768 or y > 32767:
        error = True
    if z < 0 or z > 255:
        error = True

    if error:
        x = y = z = 0

    if obj.name.startswith("RouteChecker") or obj.name.startswith("InSimCircle"):
        rotation = int(re.search(r"_([0-9]+)$", obj.name.split(".")[0]).group(1)) - 1 if re.search(r"_([0-9]+)$", obj.name.split(".")[0]) else 0
    else:
        deg = math.degrees(obj.rotation_euler[2])
        while deg < 0:
            deg += 360
        rotation = round((deg + 180) * 256 / 360)
        while rotation > 255:
            rotation -= 256

    heading = round((rotation * 360 / 256) - 180, 1)

    # If builder wrote custom props ("Index" / "Flags"), export them.
    # Required for Letter_Board multi-line (floating bit 0x80 + correct index).
    if "Flags" in obj:
        flags = int(obj["Flags"]) & 0xFF
    else:
        flags = name2flags(obj.name)

    if "Index" in obj:
        idx = int(obj["Index"]) & 0xFF
    else:
        idx = name2blockid(obj.name)

    f.write(struct.pack("<hhBBBB", x, y, z, flags & 0xFF, idx & 0xFF, int(round(rotation)) & 0xFF))

    print(
        f"Exporting {obj.name} -> "
        f"X={x} Y={y} Z={z} "
        f"Flags=0x{flags:02X} Index={idx} Rot={int(round(rotation))} HeadingDeg={heading}"
    )

# -------------------------------------------------------
# Core export function (callable from tests / other scripts)
# -------------------------------------------------------
def export_to_lyt(objects, output_path, normalize=True, laps=1, lyt_flags=9, offset=(0, 0, 0)):
    count = len(objects)
    print(f"Exporting {count} objects")

    with open(output_path, "wb+") as f:
        f.write(b"LFSLYT")
        f.write(struct.pack("<BBHBB", 0, 252, count, laps, lyt_flags))

        for obj in objects:
            if normalize:
                normalizeObject(obj, offset)
            exportObject(obj, f, offset)

    print(f"Done: {output_path}")

# -------------------------------------------------------
# Standalone execution (Blender text editor / --python)
# -------------------------------------------------------
if __name__ == "__main__":
    os.system("cls")

    LFS_PATH, MAP_NAME, TRACK_NAME = load_config(bpy.data.filepath)

    objects = bpy.context.selected_objects
    out_path = f"{LFS_PATH}/data/layout/{MAP_NAME}_{TRACK_NAME}.lyt"
    export_to_lyt(objects, out_path)
