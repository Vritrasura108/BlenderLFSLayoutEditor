#
#   name        LFS layout Blender Tool - Import (0.8A ready, safe UNREF)
#   version     1.2
#   author      Vritrasura, Nex_ (patched)
#
#   Goals:
#   - Import .LYT (0.8A) into Blender by duplicating library objects.
#   - Kerb (Index 132): decode colour/mapping from Flags (NOTE1/NOTE7) and map to your library names.
#   - Safe fallback: if a library object is missing, place a placeholder and name it UNREF_...
#

import bpy
import struct
import math
import os
import re
import configparser

# Load config from config.ini next to the blend file
_config = configparser.ConfigParser()
_config_path = os.path.join(os.path.dirname(bpy.data.filepath), "config.ini")
if not _config.read(_config_path):
    raise FileNotFoundError(f"config.ini not found at {_config_path} - run run_first_time.py first")

LFS_PATH   = _config.get("LFS", "path")
MAP_NAME   = _config.get("LFS", "map_name")
TRACK_NAME = _config.get("LFS", "track_name")
COLLECTION = "LFS Track"

os.system("cls")

# --------------------------
# Helpers
# --------------------------
def get_library_object_or_placeholder(name: str, placeholder_name: str = "Block_00_00"):
    """
    Returns (obj, used_placeholder_bool).
    """
    if name in bpy.data.objects:
        return bpy.data.objects[name], False

    if placeholder_name in bpy.data.objects:
        print(f"Missing library object: '{name}' -> using placeholder '{placeholder_name}'")
        return bpy.data.objects[placeholder_name], True

    # last resort: create a cube
    print(f"Missing library object: '{name}' and placeholder '{placeholder_name}' not found -> creating cube")
    mesh = bpy.data.meshes.new("UNREF_CubeMesh")
    cube = bpy.data.objects.new("UNREF_Cube", mesh)
    bpy.context.scene.collection.objects.link(cube)
    return cube, True

def duplicate(obj, collection):
    obj_copy = obj.copy()
    collection.objects.link(obj_copy)
    return obj_copy

def flags2width(flags):
    widths = [2, 4, 8, 16]
    return widths[flags & 0x03]

def flags2length(flags):
    lengths = [2, 4, 8, 16]
    return lengths[(flags >> 2) & 0x03]

def flags2sizex(flags):
    sizes = [25, 50, 75, 100]
    return sizes[flags & 0x03]

def flags2sizey(flags):
    sizes = [25, 50, 75, 100]
    return sizes[(flags >> 2) & 0x03]

def flags2height(flags):
    heights = [25, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350, 375, 400]
    return heights[(flags >> 4) & 0x0f]

def flags2pitch(flags):
    pitches = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 90]
    return pitches[(flags >> 4) & 0x0f]

def flags2concretecolour(flags):
    colours = ["Grey", "Red", "Blue", "Yellow"]
    return colours[flags & 0x03]

def flags2chalkcolour(flags):
    colours = ["White", "Red", "Blue", "Yellow"]
    return colours[flags & 0x03]

def flags2tyrecolour(flags):
    colours = ["Black", "White", "Red", "Blue", "Green", "Yellow"]
    return colours[flags & 0x07]

def flags2angle(flags):
    angles = [56, 113, 169, 225, 281, 338, 394, 450, 506, 563, 619, 675, 731, 788, 844, 900]
    return angles[(flags >> 4) & 0x0f]

def flags2control(flags):
    t = flags & 0x03
    width = ((flags >> 2) & 0x3F) * 2
    if t == 0:
        if width == 0:
            return "AutocrossStart"
        return f"FinishLine_{width:02d}"
    return f"Checkpoint{t}_{width:02d}"

def flags2insimcheckpointwidth(flags):
    return ((flags >> 2) & 0x1F) * 2

def flags2restrictedarea(flags):
    types = ["Invisible", "Marshall", "MarshallPointLeft", "MarshallPointRight"]
    return types[flags & 0x03]

def flags2diameter(flags):
    radius = (flags >> 2) & 0x1f
    return radius << 1

# --------------------------
# Kerb (Index 132) decoding
# --------------------------
def kerb_object_name_from_flags(flags: int) -> str:
    c = flags & 0x07
    shade = (flags >> 3) & 0x01  # 0 clair, 1 foncé

    colour_map = {
        0: "White",
        1: "Grey",
        2: "Red",
        3: "Blue",
        4: "Cyan",
        5: "Green",
        6: "Orange",
        7: "Yellow",
    }
    colour = colour_map.get(c, "White")
    variant = 1 if shade == 0 else 2
    return f"Kerb_{colour}_{variant}"

# --------------------------
# Posts / Marquee / Bins
# --------------------------
POST_FLAGS_TO_NAME = {
    0x01: "Orange",
    0x02: "Red",
    0x03: "White",
    0x04: "Blue",
    0x05: "Yellow",
    0x06: "Cyan",
    0x07: "Green",
}

def post_object_name_from_flags(flags: int) -> str:
    colour = POST_FLAGS_TO_NAME.get(flags & 0xFF)
    if colour is None:
        return f"UNREF_Post_F{flags:02X}"
    return f"Post_{colour}"

MARQUEE_FLAGS_TO_NAME = {
    0x03: "Red",
    0x00: "White",
    0x02: "Blue",
    0x04: "Yellow",
    0x05: "Green",
    0x09: "Grey",
    0x06: "Black",
}

def marquee_object_name_from_flags(flags: int) -> str:
    colour = MARQUEE_FLAGS_TO_NAME.get(flags & 0xFF)
    if colour is None:
        return f"UNREF_Marquee_F{flags:02X}"
    return f"Marquee_{colour}"

BIN1_FLAGS_TO_NAME = {
    0x01: "Red",
    0x02: "White",
    0x03: "Blue",
    0x04: "Yellow",
    0x05: "Green",
    0x00: "Orange",
}

def bin1_object_name_from_flags(flags: int) -> str:
    colour = BIN1_FLAGS_TO_NAME.get(flags & 0xFF)
    if colour is None:
        return f"UNREF_Bin1_F{flags:02X}"
    return f"Bin1_{colour}"

BIN2_FLAGS_TO_NAME = {
    0x01: "Red",
    0x05: "White",
    0x02: "Blue",
    0x03: "Yellow",
    0x00: "Green",
    0x06: "Orange",
    0x04: "Black",
}

def bin2_object_name_from_flags(flags: int) -> str:
    colour = BIN2_FLAGS_TO_NAME.get(flags & 0xFF)
    if colour is None:
        return f"UNREF_Bin2_F{flags:02X}"
    return f"Bin2_{colour}"

# --------------------------
# Paint / Markers / Cones
# --------------------------
PAINT_GLYPHS = [
    "A","B","C","D","E","F","G","H",
    "I","J","K","L","M","N","O","P",
    "Q","R","S","T","U","V","W","X",
    "Y","Z","LEFT","RIGHT","UP","DOWN","HASH","AT",
    "0","1","2","3","4","5","6","7",
    "8","9","DOT","COLON","SLASH","LPAREN","RPAREN","AMP",
]

PAINT_ARROW = [
    "LEFT",
    "RIGHT",
    "STRAIGHTLEFT",
    "STRAIGHTRIGHT",
    "CURVEL",
    "CURVER",
    "STRAIGHTON",
]

CONE_FLAGS_MAP = {
    "Green":  0x03,
    "Red":    0x00,
    "White":  0x05,
    "Blue":   0x01,
    "Yellow": 0x06,
    "Orange": 0x04,
    "Cyan":   0x02,
}

CONE_FLAGS_TO_NAME = {v: k for k, v in CONE_FLAGS_MAP.items()}

MARKER_CORNER_FLAGS_TO_NAME = {
    0: "CurveL",
    1: "CurveR",
    2: "L",
    3: "R",
    4: "HardL",
    5: "HardR",
    6: "LR",
    7: "RL",
    8: "SL",
    9: "SR",
    10: "S2L",
    11: "S2R",
    12: "UL",
    13: "UR",
    14: "KinkL",
    15: "KinkR",
}

MARKER_DISTANCE_FLAGS_TO_NAME = {
    0: "25",
    1: "50",
    2: "75",
    3: "100",
    4: "125",
    5: "150",
    6: "200",
    7: "250",
}

def paint_letter_name_from_flags(flags: int) -> str:
    glyph_id = (flags >> 1) & 0x7F
    colour_bit = flags & 0x01

    if glyph_id >= len(PAINT_GLYPHS):
        return f"UNREF_Paint_Letters_G{glyph_id:02d}_{'Yellow' if colour_bit else 'White'}"

    glyph = PAINT_GLYPHS[glyph_id]
    colour = "Yellow" if colour_bit else "White"
    return f"Paint_Letters_{glyph}_{colour}"

def paint_arrow_name_from_flags(flags: int) -> str:
    glyph_id = (flags >> 1) & 0x7F
    colour_bit = flags & 0x01

    if glyph_id >= len(PAINT_ARROW):
        return f"UNREF_Paint_Arrow_G{glyph_id:02d}_{'Yellow' if colour_bit else 'White'}"

    glyph = PAINT_ARROW[glyph_id]
    colour = "Yellow" if colour_bit else "White"
    return f"Paint_Arrow_{glyph}_{colour}"

def cone_object_name_from_flags(flags: int, block_id: int) -> str:
    flags = flags & 0xFF
    colour = CONE_FLAGS_TO_NAME.get(flags, "Red")

    if block_id == 20:
        return f"Cone1_{colour}"
    if block_id == 21:
        return f"Cone2_{colour}"
    if block_id == 32:
        return f"Cone_Tall1_{colour}"
    if block_id == 33:
        return f"Cone_Tall2_{colour}"
    if block_id == 40:
        return f"Cone_Pointer_{colour}"

    return f"Cone_{colour}"

def marker_distance_object_name_from_flags(flags: int) -> str:
    mapping = (flags & 0x78) >> 3
    dist = MARKER_DISTANCE_FLAGS_TO_NAME.get(mapping, "25")
    return f"Marker_Distance_{dist}"

def marker_corner_object_name_from_flags(flags: int) -> str:
    mapping = (flags & 0x78) >> 3
    corner = MARKER_CORNER_FLAGS_TO_NAME.get(mapping, "CurveL")
    return f"Marker_Corner_{corner}"

# --------------------------
# Letter Board (IDs -> glyph)
# --------------------------
LETTERBOARD_GLYPHS = [
    "A","B","C","D","E","F","G","H",
    "I","J","K","L","M","N","O","P",
    "Q","R","S","T","U","V","W","X",
    "Y","Z","LEFT","RIGHT","UP","DOWN","HASH","AT",
    "0","1","2","3","4","5","6","7",
    "8","9","DOT","COLON","SLASH","LPAREN","RPAREN","AMP",
]

def letter_boardWY_name_from_flags(flags: int) -> str:
    glyph_id = (flags >> 1) & 0x7F
    colour_bit = flags & 0x01

    if glyph_id >= len(LETTERBOARD_GLYPHS):
        return f"UNREF_Letter_Board_G{glyph_id:02d}_{'Yellow' if colour_bit else 'White'}"

    glyph = LETTERBOARD_GLYPHS[glyph_id]
    colour = "Yellow" if colour_bit else "White"
    return f"Letter_Board_{glyph}_{colour}"

def letter_boardBR_name_from_flags(flags: int) -> str:
    glyph_id = (flags >> 1) & 0x7F
    colour_bit = flags & 0x01

    if glyph_id >= len(LETTERBOARD_GLYPHS):
        return f"UNREF_Letter_Board_G{glyph_id:02d}_{'Blue' if colour_bit else 'Red'}"

    glyph = LETTERBOARD_GLYPHS[glyph_id]
    colour = "Blue" if colour_bit else "Red"
    return f"Letter_Board_{glyph}_{colour}"

# --------------------------
# Sign Speed (Index 168) decoding
# --------------------------
SIGN_SPEED_FLAGS_TO_NAME = {
    0: "80_kmh",
    1: "50_kmh",
    2: "50_mph",
    3: "40_mph",
}

def sign_speed_object_name_from_flags(flags: int) -> str:
    mapping = (flags & 0x78) >> 3
    speed = SIGN_SPEED_FLAGS_TO_NAME.get(mapping)
    if speed is None:
        return f"UNREF_Sign_Speed_M{mapping:02d}_F{flags:02X}"
    return f"Sign_Speed_{speed}"

# --------------------------
# Sign Metal (Index 160) decoding
# --------------------------
SIGN_METAL_FLAGS_TO_NAME = {
    0: "KeepLeft",
    1: "KeepRight",
    2: "Left",
    3: "Right",
    4: "UpLeft",
    5: "UpRight",
    6: "Forward",
    7: "NoEntry",
}

def sign_metal_object_name_from_flags(flags: int) -> str:
    mapping = (flags & 0x78) >> 3
    kind = SIGN_METAL_FLAGS_TO_NAME.get(mapping)
    if kind is None:
        return f"UNREF_Sign_Metal_M{mapping:02d}_F{flags:02X}"
    return f"Sign_Metal_{kind}"

# --------------------------
# Chevron (Index 164 / 165) decoding
# --------------------------
CHEVRON_FLAGS_TO_NAME = {
    0: "White",
    1: "Black",
}

def chevron_object_name_from_flags(flags: int, index: int) -> str:
    colour = CHEVRON_FLAGS_TO_NAME.get(flags & 0xFF)
    if colour is None:
        return f"UNREF_Chevron_F{flags:02X}"

    if index == 164:
        direction = "Right"
    elif index == 165:
        direction = "Left"
    else:
        direction = f"I{index:03d}"

    return f"Chevron_{direction}_{colour}"

ARMCO_FLAGS_TO_VARIANT = {
    0x00: "Old",
    0x09: "New",
}

def armco_object_name_from_flags(index: int, flags: int) -> str:
    flags = flags & 0xFF

    # Détection "New" = bit 3 activé
    if flags & 0x08:
        variant = "New"
    else:
        variant = "Old"

    if index == 96:
        return f"Armco_1_{variant}"
    if index == 97:
        return f"Armco_3_{variant}"
    if index == 98:
        return f"Armco_5_{variant}"

    return f"UNREF_Armco_I{index:03d}_F{flags:02X}"


# --------------------------
# Main import
# --------------------------
lyt_path = f"{LFS_PATH}/data/layout/{MAP_NAME}_{TRACK_NAME}.lyt"
collection = bpy.data.collections.get(COLLECTION)
if collection is None:
    raise RuntimeError(f"Collection '{COLLECTION}' not found")

with open(lyt_path, "rb") as f:
    header = struct.unpack("<6sBBHBB", f.read(12))
    magic = header[0]
    version = header[1]
    revision = header[2]
    objCount = header[3]

    if magic != b"LFSLYT":
        raise RuntimeError("Not a valid LFS .LYT file (bad magic)")

    print(f"Importing {objCount} objects from {lyt_path} (ver={version}, rev={revision})")

    for i in range(objCount):
        objitems = struct.unpack("<hhBBBB", f.read(8))

        x = objitems[0] / 16.0
        y = objitems[1] / 16.0
        z = objitems[2] / 4.0

        flags = objitems[3]
        index = objitems[4]
        heading_byte = objitems[5]

        deg = ((heading_byte * 360) / 256) - 180
        rad = deg * math.pi / 180.0

        print(f"Parsing [{i+1:04d}/{objCount}] X={x:.3f} Y={y:.3f} Z={z:.3f} Flags=0x{flags:02X} Index={index} Head={deg:.1f}")

        suffix = ""

        # Chalk / Tyres legacy naming support (kept)
        if 4 <= index <= 13:
            suffix = flags2chalkcolour(flags)
        elif 48 <= index <= 55:
            suffix = flags2tyrecolour(flags)

        # Resolve base name by Index
        match index:
            case 0:
                name = flags2control(flags)

            case 4:  name = "ChalkLine"
            case 5:  name = "ChalkLine2"
            case 6:  name = "ChalkLineAhead"
            case 7:  name = "ChalkLineAhead2"
            case 8:  name = "ChalkLeft"
            case 9:  name = "ChalkLeft2"
            case 10: name = "ChalkLeft3"
            case 11: name = "ChalkRight"
            case 12: name = "ChalkRight2"
            case 13: name = "ChalkRight3"

            case 16:
                name = paint_letter_name_from_flags(flags)
            case 17:
                name = paint_arrow_name_from_flags(flags)

            case 20:
                name = cone_object_name_from_flags(flags, 20)
            case 21:
                name = cone_object_name_from_flags(flags, 21)
            case 32:
                name = cone_object_name_from_flags(flags, 32)
            case 33:
                name = cone_object_name_from_flags(flags, 33)
            case 40:
                name = cone_object_name_from_flags(flags, 40)

            case 48: name = "TyreSingle"
            case 49: name = "TyreStack2"
            case 50: name = "TyreStack3"
            case 51: name = "TyreStack4"
            case 52: name = "TyreSingleBig"
            case 53: name = "TyreStack2Big"
            case 54: name = "TyreStack3Big"
            case 55: name = "TyreStack4Big"

            case 64:
                name = marker_corner_object_name_from_flags(flags)
            case 84:
                name = marker_distance_object_name_from_flags(flags)

            case 92:
                name = letter_boardWY_name_from_flags(flags)
            case 93:
                name = letter_boardBR_name_from_flags(flags)

            case 96:
                name = armco_object_name_from_flags(index, flags)
            case 97:
                name = armco_object_name_from_flags(index, flags)
            case 98:
                name = armco_object_name_from_flags(index, flags)


            case 104: name = "BarrierLong"
            case 105: name = "BarrierRed"
            case 106: name = "BarrierWhite"

            case 112: name = "Banner1"
            case 113: name = "Banner2"

            case 120: name = "Ramp1"
            case 121: name = "Ramp2"

            case 124: name = "SUV"
            case 125: name = "Van"
            case 126: name = "Truck"
            case 127: name = "Ambulance"
            case 128: name = "SpeedHump6m"
            case 129: name = "SpeedHump10m"
            case 130: name = "SpeedHump2m"
            case 131: name = "SpeedHump1m"

            case 132:
                name = kerb_object_name_from_flags(flags)

            case 136:
                name = post_object_name_from_flags(flags)

            case 140:
                name = marquee_object_name_from_flags(flags)

            case 144: name = "Bale"

            case 145:
                name = bin1_object_name_from_flags(flags)
            case 146:
                name = bin2_object_name_from_flags(flags)

            case 147: name = "Railing1"
            case 148: name = "Railing2"
            
            case 149: name = "StartLights"

            case 160:
                name = sign_metal_object_name_from_flags(flags)

            case 164:
                name = chevron_object_name_from_flags(flags, 164)
            case 165:
                name = chevron_object_name_from_flags(flags, 165)

            case 168:
                name = sign_speed_object_name_from_flags(flags)

            case 172:
                width = pow(2, 1 + (flags & 0x03))
                length = pow(2, 1 + ((flags & 0x0C) >> 2))
                pitch = round(((flags & 0xF0) >> 4) * 6.0)
                name = f"Slab_{length}_{width}_{pitch:02d}"

            case 173:
                width = pow(2, 1 + (flags & 0x03))
                length = pow(2, 1 + ((flags & 0x0C) >> 2))
                height = 1 + ((flags & 0xF0) >> 4)
                height = round((height / 4.0) * 100)
                name = f"Ramp_{length}_{width}_{height:03d}"

            case 174:
                colour = flags2concretecolour(flags)
                length = flags2length(flags)
                height = flags2height(flags)
                name = f"Wall_{length}_{height:03d}_{colour}"

            case 175:
                sizex = (((flags >> 0) & 0x03) + 1) * 25
                sizey = (((flags >> 2) & 0x03) + 1) * 25
                height = (((flags >> 4) & 0x0f) + 1) * 25
                name = f"Pillar_{sizex:03d}_{sizey:03d}_{height:03d}"

            case 176:
                colour = flags2concretecolour(flags)
                length = flags2length(flags)
                pitch = flags2pitch(flags)
                name = f"SlabWall_{length}_{pitch:02d}_{colour}"

            case 177:
                colour = flags2concretecolour(flags)
                length = flags2length(flags)
                height = flags2height(flags)
                name = f"RampWall_{length}_{height:03d}_{colour}"

            case 178:
                colour = flags2concretecolour(flags)
                sizey = flags2sizey(flags)
                pitch = flags2pitch(flags)
                name = f"ShortSlabWall_{sizey:03d}_{pitch:02d}_{colour}"

            case 179:
                colour = flags2concretecolour(flags)
                length = flags2length(flags)
                angle = flags2angle(flags)
                name = f"Wedge_{length}_{angle:03d}_{colour}"

            case 184:
                posID = flags & 0x3f
                name = f"StartPosition_{posID+1:02d}"

            case 185:
                posID = flags & 0x3f
                name = f"PitStartPoint_{posID+1:02d}"

            case 186:
                name = "PitStopBox"

            case 252:
                width = flags2insimcheckpointwidth(flags)
                name = f"InSimCheckpoint_{width:02d}"

            case 253:
                circle_index = heading_byte + 1
                diameter = flags2diameter(flags)
                name = f"InSimCircle_{diameter:02d}"
                suffix = f"{circle_index}"

            case 254:
                t = flags2restrictedarea(flags)
                diameter = flags2diameter(flags)
                name = f"RestrictedArea_{t}_{diameter:02d}"

            case 255:
                route_index = heading_byte + 1
                diameter = flags2diameter(flags)
                name = f"RouteChecker_{diameter:02d}"
                suffix = f"{route_index}"

            case _:
                name = f"UNREF_I{index:03d}_F{flags:02X}_H{heading_byte:03d}"

        objectName = name
        if suffix:
            objectName = f"{name}_{suffix}"

        # Special: these are duplicated from base prototypes
        postRename = False
        if name.startswith("StartPosition"):
            lib_name = "StartPosition"
            postRename = True
        elif name.startswith("PitStartPoint"):
            lib_name = "PitStartPoint"
            postRename = True
        elif name.startswith("RouteChecker"):
            lib_name = objectName
            postRename = True
        elif name.startswith("InSimCircle"):
            lib_name = objectName
            postRename = True
        else:
            lib_name = objectName

        lib_obj, used_placeholder = get_library_object_or_placeholder(lib_name, placeholder_name="Block_00_00")
        newobj = duplicate(lib_obj, collection)

        if postRename or used_placeholder:
            newobj.name = objectName

        newobj.location.x = x
        newobj.location.y = y
        newobj.location.z = z

        # RouteChecker / InSimCircle store index in heading byte, don't rotate
        if not name.startswith("RouteChecker") and not name.startswith("InSimCircle"):
            newobj.rotation_euler.z = rad

        print(f"Putting {objectName} -> [{x:.3f}, {y:.3f}, {z:.3f}] azimuth={deg:.1f}")
