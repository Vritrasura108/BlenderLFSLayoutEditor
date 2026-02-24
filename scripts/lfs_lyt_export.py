#
#   name        LFS layout Blender Tool - Export (0.8A ready)
#   version     1.2 + PATCH (reads custom Index/Flags from objects for LetterBoard multiline)
#   author      Vritrasura, Nex_ (patched)
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

OFFSET_X = 0
OFFSET_Y = 0
OFFSET_Z = 0

NORMALIZE = True

LYT_FLAGS = 9   # 0.8A mini_rev
LAPS = 1

os.system("cls")

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
def normalizeObject(obj):
    pos_orig = obj.location.copy()

    loc_x = obj.location.x - OFFSET_X
    loc_x = OFFSET_X + round(loc_x / 0.0625) * 0.0625
    obj.location.x = loc_x

    loc_y = obj.location.y - OFFSET_Y
    loc_y = OFFSET_Y + round(loc_y / 0.0625) * 0.0625
    obj.location.y = loc_y

    loc_z = obj.location.z - OFFSET_Z
    loc_z = OFFSET_Z + round(loc_z / 0.25) * 0.25
    obj.location.z = loc_z

    rot_z = obj.rotation_euler.z
    rot_z = round(rot_z / 0.0245436926) * 0.0245436926
    obj.rotation_euler.z = rot_z

    if (pos_orig.x, pos_orig.y, pos_orig.z) != (obj.location.x, obj.location.y, obj.location.z):
        print("Normalizing object position...")
        print(f"   original pos:   {pos_orig.x} {pos_orig.y} {pos_orig.z}")
        print(f"   normalized pos: {loc_x} {loc_y} {loc_z}")

def width2flags(width):
    widths = [2, 4, 8, 16]
    return widths.index(width) << 0

def length2flags(length):
    lengths = [2, 4, 8, 16]
    return lengths.index(length) << 2

def sizex2flags(x):
    sizes = [25, 50, 75, 100]
    return sizes.index(x) << 0

def sizey2flags(y):
    sizes = [25, 50, 75, 100]
    return sizes.index(y) << 2

def height2flags(height):
    heights = [25, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350, 375, 400]
    return heights.index(height) << 4

def pitch2flags(pitch):
    pitches = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 90]
    return pitches.index(pitch) << 4

def concretecolour2flags(colour):
    colours = ["Grey", "Red", "Blue", "Yellow"]
    return colours.index(colour) << 0

def chalkcolour2flags(colour):
    colours = ["White", "Red", "Blue", "Yellow"]
    return colours.index(colour) << 0

def tyrecolour2flags(colour):
    colours = ["Black", "White", "Red", "Blue", "Green", "Yellow"]
    return colours.index(colour) << 0

def angle2flags(angle):
    angles = [56, 113, 169, 225, 281, 338, 394, 450, 506, 563, 619, 675, 731, 788, 844, 900]
    return angles.index(angle) << 4

def carpos2flags(pos: int) -> int:
    if 1 <= pos <= 48:
        return pos - 1
    if 0 <= pos <= 47:
        return pos
    raise ValueError(f"Car position out of range: {pos} (expected 1..48 or 0..47)")

def diameter2flags(diameter: int) -> int:
    return ((diameter >> 1) & 0x1F) << 2

def restrictedarea2flags(type_name: str, diameter: int) -> int:
    types = ["Invisible", "Marshall", "MarshallPointLeft", "MarshallPointRight"]
    return types.index(type_name) | diameter2flags(diameter)

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

    group_map = {
        "White": 0, "Grey": 1, "Red": 2, "Blue": 3,
        "Cyan": 4, "Green": 5, "Orange": 6, "Yellow": 7,
    }
    c_num = group_map[colour] & 0x07

    variant = 1 if variant <= 1 else 2
    shade = 0 if variant == 1 else 1

    default_mapping = {
        "White": 0, "Grey": 1, "Red": 2, "Blue": 3,
        "Cyan": 4, "Green": 5, "Orange": 6, "Yellow": 7,
    }

    mapping = default_mapping.get(colour, 0)
    if forced_map is not None:
        mapping = max(0, min(int(forced_map), 15))

    flags = (c_num & 0x07) | ((shade & 0x01) << 3) | ((mapping & 0x0F) << 4)
    return flags & 0xFF

CHEVRON_FLAGS_MAP = {"White": 0, "Black": 1}

def chevron_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Chevron_(Left|Right)_(White|Black)$", name, re.IGNORECASE)
    if not m:
        return 0
    colour = m.group(2).capitalize()
    return CHEVRON_FLAGS_MAP.get(colour, 0) & 0xFF

ARMCO_VARIANT_TO_FLAGS = {"Old": 0x00, "New": 0x09}

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
POST_FLAGS_MAP = {
    "Orange": 0x01, "Red": 0x02, "White": 0x03, "Blue": 0x04,
    "Yellow": 0x05, "Cyan": 0x06, "Green": 0x07,
}

MARQUEE_FLAGS_MAP = {
    "Orange": 0x01, "Red": 0x03, "White": 0x00, "Blue": 0x02,
    "Yellow": 0x04, "Green": 0x05, "Grey": 0x09, "Black": 0x06,
}

BIN1_FLAGS_MAP = {
    "Orange": 0x00, "Red": 0x01, "White": 0x02, "Blue": 0x03,
    "Yellow": 0x04, "Green": 0x05,
}

BIN2_FLAGS_MAP = {
    "Green": 0x00, "Red": 0x01, "White": 0x05, "Blue": 0x02,
    "Yellow": 0x03, "Orange": 0x06, "Black": 0x04,
}

# -------------------------------------------------------
# Paint / Markers / Cones / Letterboard / Signs
# -------------------------------------------------------
PAINT_GLYPHS = [
    "A","B","C","D","E","F","G","H",
    "I","J","K","L","M","N","O","P",
    "Q","R","S","T","U","V","W","X",
    "Y","Z","LEFT","RIGHT","UP","DOWN","HASH","AT",
    "0","1","2","3","4","5","6","7",
    "8","9","DOT","COLON","SLASH","LPAREN","RPAREN","AMP",
]
PAINT_GLYPH_TO_ID = {g:i for i,g in enumerate(PAINT_GLYPHS)}

PAINT_ARROW = ["LEFT","RIGHT","STRAIGHTLEFT","STRAIGHTRIGHT","CURVEL","CURVER","STRAIGHTON"]
PAINT_ARROW_TO_ID = {g:i for i,g in enumerate(PAINT_ARROW)}

MARKER_CORNER_MAP = {
    "CurveL": 0, "CurveR": 1, "L": 2, "R": 3, "HardL": 4, "HardR": 5,
    "LR": 6, "RL": 7, "SL": 8, "SR": 9, "S2L": 10, "S2R": 11,
    "UL": 12, "UR": 13, "KinkL": 14, "KinkR": 15,
}

MARKER_DISTANCE_MAP = {"25": 0, "50": 1, "75": 2, "100": 3, "125": 4, "150": 5, "200": 6, "250": 7}

CONE_FLAGS_MAP = {"Green": 0x03, "Red": 0x00, "White": 0x05, "Blue": 0x01, "Yellow": 0x06, "Orange": 0x04, "Cyan": 0x02}

LETTERBOARD_GLYPH_TO_ID = {}
for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    LETTERBOARD_GLYPH_TO_ID[ch] = i
LETTERBOARD_GLYPH_TO_ID.update({
    "LEFT": 26, "RIGHT": 27, "UP": 28, "DOWN": 29, "HASH": 30, "AT": 31,
    "DOT": 42, "COLON": 43, "SLASH": 44, "LPAREN": 45, "RPAREN": 46, "AMP": 47,
})
for i in range(10):
    LETTERBOARD_GLYPH_TO_ID[str(i)] = 32 + i

SIGN_SPEED_MAP = {"40_mph": 3, "50_mph": 2, "50_kmh": 1, "80_kmh": 0}
SIGN_METAL_MAP = {"KeepLeft": 0, "KeepRight": 1, "Left": 2, "Right": 3, "UpLeft": 4, "UpRight": 5, "Forward": 6, "NoEntry": 7}

def post_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Post_(Green|Orange|Red|White|Blue|Yellow|Cyan)$", name)
    if not m:
        m = re.match(r"^Post(Green|Orange|Red|White|Blue|Yellow|Cyan)$", name)
        if not m:
            return 0
    return POST_FLAGS_MAP[m.group(1)] & 0xFF

def marquee_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Marquee_(White|Grey|Blue|Red|Yellow|Green|Black)$", name)
    if not m:
        m = re.match(r"^Marquee(White|Grey|Blue|Red|Yellow|Green|Black)$", name)
        if not m:
            return 0
    return MARQUEE_FLAGS_MAP[m.group(1)] & 0xFF

def bin1_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Bin1_(Green|Orange|Red|White|Blue|Yellow)$", name)
    if not m:
        m = re.match(r"^Bin1(Green|Orange|Red|White|Blue|Yellow)$", name)
        if not m:
            return 0
    return BIN1_FLAGS_MAP[m.group(1)] & 0xFF

def bin2_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Bin2_(Green|Red|Blue|Yellow|Black|White|Orange)$", name)
    if not m:
        m = re.match(r"^Bin2(Green|Red|Blue|Yellow|Black|White|Orange)$", name)
        if not m:
            return 0
    return BIN2_FLAGS_MAP[m.group(1)] & 0xFF

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
    mapping = MARKER_CORNER_MAP[m.group(1)]
    return ((mapping & 0x0F) << 3) & 0xFF

def marker_distance_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Marker_Distance_(25|50|75|100|125|150|200|250)$", name)
    if not m:
        return 0
    mapping = MARKER_DISTANCE_MAP[m.group(1)]
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
    mapping = SIGN_SPEED_MAP[m.group(1)]
    return ((mapping & 0x0F) << 3) & 0xFF

def sign_metal_flags_from_name(obj_name: str) -> int:
    name = obj_name.split(".")[0]
    m = re.match(r"^Sign_Metal_(KeepLeft|KeepRight|Left|Right|UpLeft|UpRight|Forward|NoEntry)$", name)
    if not m:
        return 0
    mapping = SIGN_METAL_MAP[m.group(1)]
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
# Export object
# -------------------------------------------------------
def exportObject(obj, f):
    x = obj.location[0] - OFFSET_X
    y = obj.location[1] - OFFSET_Y
    z = obj.location[2] - OFFSET_Z

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

    # ---- PATCH IMPORTANT ----
    # If your builder wrote custom props ("Index" / "Flags"), we export them.
    # This is REQUIRED for Letter_Board multi-line, because it needs floating bit (0x80)
    # and the correct axo index (92/93), otherwise your recomputed flags from name can lose info.
    if "Flags" in obj:
        flags = int(obj["Flags"]) & 0xFF
    else:
        flags = name2flags(obj.name)

    if "Index" in obj:
        idx = int(obj["Index"]) & 0xFF
    else:
        idx = name2blockid(obj.name)

    if idx in (132, 136, 92, 93, 16):
        print("EXPORT DEBUG:", obj.name, "idx=", idx, "flags=", hex(flags))

    f.write(struct.pack("<hhBBBB", x, y, z, flags & 0xFF, idx & 0xFF, int(round(rotation)) & 0xFF))

    print(
        f"Exporting {obj.name} -> "
        f"X={x} Y={y} Z={z} "
        f"Flags=0x{flags:02X} Index={idx} Rot={int(round(rotation))} HeadingDeg={heading}"
    )

# -------------------------------------------------------
# Main
# -------------------------------------------------------
objects = bpy.context.selected_objects
count = len(objects)
print(f"Exporting {count} objects")

out_path = f"{LFS_PATH}/data/layout/{MAP_NAME}_{TRACK_NAME}.lyt"
with open(out_path, "wb+") as f:
    f.write(b"LFSLYT")
    f.write(struct.pack("<BBHBB", 0, 252, count, LAPS, LYT_FLAGS))

    for obj in objects:
        if NORMALIZE:
            normalizeObject(obj)
        exportObject(obj, f)

print(f"Done: {out_path}")
