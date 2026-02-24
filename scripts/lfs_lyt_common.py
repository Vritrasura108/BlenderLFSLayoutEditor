#
#   name        LFS layout Blender Tool - Shared Constants & Helpers
#   version     1.0
#   author      Vritrasura, Nex_
#
#   Shared lookup tables, encode/decode helpers, and constants
#   used by both lfs_lyt_export.py and lfs_lyt_import.py.
#

import os
import math
import configparser

# -------------------------------------------------------
# LFS grid constants
# -------------------------------------------------------
GRID_XY = 0.0625        # 1/16 metre
GRID_Z = 0.25           # 1/4 metre
GRID_ROT_Z = 0.0245436926  # radians (~1.40625 deg = 360/256)

# -------------------------------------------------------
# Lookup tables (used by both encode and decode)
# -------------------------------------------------------
WIDTHS = [2, 4, 8, 16]
LENGTHS = [2, 4, 8, 16]
SIZES = [25, 50, 75, 100]
HEIGHTS = [25, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350, 375, 400]
PITCHES = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 90]
CONCRETE_COLOURS = ["Grey", "Red", "Blue", "Yellow"]
CHALK_COLOURS = ["White", "Red", "Blue", "Yellow"]
TYRE_COLOURS = ["Black", "White", "Red", "Blue", "Green", "Yellow"]
ANGLES = [56, 113, 169, 225, 281, 338, 394, 450, 506, 563, 619, 675, 731, 788, 844, 900]

# -------------------------------------------------------
# Encode helpers (value -> flags bits)
# -------------------------------------------------------
def width2flags(width):
    return WIDTHS.index(width) << 0

def length2flags(length):
    return LENGTHS.index(length) << 2

def sizex2flags(x):
    return SIZES.index(x) << 0

def sizey2flags(y):
    return SIZES.index(y) << 2

def height2flags(height):
    return HEIGHTS.index(height) << 4

def pitch2flags(pitch):
    return PITCHES.index(pitch) << 4

def concretecolour2flags(colour):
    return CONCRETE_COLOURS.index(colour) << 0

def chalkcolour2flags(colour):
    return CHALK_COLOURS.index(colour) << 0

def tyrecolour2flags(colour):
    return TYRE_COLOURS.index(colour) << 0

def angle2flags(angle):
    return ANGLES.index(angle) << 4

# -------------------------------------------------------
# Decode helpers (flags bits -> value)
# -------------------------------------------------------
def flags2width(flags):
    return WIDTHS[flags & 0x03]

def flags2length(flags):
    return LENGTHS[(flags >> 2) & 0x03]

def flags2sizex(flags):
    return SIZES[flags & 0x03]

def flags2sizey(flags):
    return SIZES[(flags >> 2) & 0x03]

def flags2height(flags):
    return HEIGHTS[(flags >> 4) & 0x0F]

def flags2pitch(flags):
    return PITCHES[(flags >> 4) & 0x0F]

def flags2concretecolour(flags):
    return CONCRETE_COLOURS[flags & 0x03]

def flags2chalkcolour(flags):
    return CHALK_COLOURS[flags & 0x03]

def flags2tyrecolour(flags):
    return TYRE_COLOURS[flags & 0x07]

def flags2angle(flags):
    return ANGLES[(flags >> 4) & 0x0F]

# -------------------------------------------------------
# Control / position / diameter helpers
# -------------------------------------------------------
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

def flags2control(flags):
    t = flags & 0x03
    width = ((flags >> 2) & 0x3F) * 2
    if t == 0:
        if width == 0:
            return "AutocrossStart"
        return f"FinishLine_{width}"
    return f"Checkpoint{t}_{width}"

def flags2insimcheckpointwidth(flags):
    return ((flags >> 2) & 0x1F) * 2

def flags2restrictedarea(flags):
    types = ["Invisible", "Marshall", "MarshallPointLeft", "MarshallPointRight"]
    return types[flags & 0x03]

def flags2diameter(flags):
    radius = (flags >> 2) & 0x1F
    return radius << 1

# -------------------------------------------------------
# Glyph / arrow lists (shared between export and import)
# -------------------------------------------------------
PAINT_GLYPHS = [
    "A","B","C","D","E","F","G","H",
    "I","J","K","L","M","N","O","P",
    "Q","R","S","T","U","V","W","X",
    "Y","Z","LEFT","RIGHT","UP","DOWN","HASH","AT",
    "0","1","2","3","4","5","6","7",
    "8","9","DOT","COLON","SLASH","LPAREN","RPAREN","AMP",
]
PAINT_GLYPH_TO_ID = {g: i for i, g in enumerate(PAINT_GLYPHS)}

PAINT_ARROW = ["LEFT", "RIGHT", "STRAIGHTLEFT", "STRAIGHTRIGHT", "CURVEL", "CURVER", "STRAIGHTON"]
PAINT_ARROW_TO_ID = {g: i for i, g in enumerate(PAINT_ARROW)}

LETTERBOARD_GLYPHS = [
    "A","B","C","D","E","F","G","H",
    "I","J","K","L","M","N","O","P",
    "Q","R","S","T","U","V","W","X",
    "Y","Z","LEFT","RIGHT","UP","DOWN","HASH","AT",
    "0","1","2","3","4","5","6","7",
    "8","9","DOT","COLON","SLASH","LPAREN","RPAREN","AMP",
]

LETTERBOARD_GLYPH_TO_ID = {}
for _i, _ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    LETTERBOARD_GLYPH_TO_ID[_ch] = _i
LETTERBOARD_GLYPH_TO_ID.update({
    "LEFT": 26, "RIGHT": 27, "UP": 28, "DOWN": 29, "HASH": 30, "AT": 31,
    "DOT": 42, "COLON": 43, "SLASH": 44, "LPAREN": 45, "RPAREN": 46, "AMP": 47,
})
for _i in range(10):
    LETTERBOARD_GLYPH_TO_ID[str(_i)] = 32 + _i

# -------------------------------------------------------
# Colour / variant maps (canonical forward, auto reverse)
# -------------------------------------------------------
CONE_FLAGS_MAP = {
    "Green": 0x03, "Red": 0x00, "White": 0x05, "Blue": 0x01,
    "Yellow": 0x06, "Orange": 0x04, "Cyan": 0x02,
}
CONE_FLAGS_TO_NAME = {v: k for k, v in CONE_FLAGS_MAP.items()}

POST_COLOUR_TO_FLAGS = {
    "Orange": 0x01, "Red": 0x02, "White": 0x03, "Blue": 0x04,
    "Yellow": 0x05, "Cyan": 0x06, "Green": 0x07,
}
POST_FLAGS_TO_COLOUR = {v: k for k, v in POST_COLOUR_TO_FLAGS.items()}

MARQUEE_COLOUR_TO_FLAGS = {
    "Orange": 0x01, "Red": 0x03, "White": 0x00, "Blue": 0x02,
    "Yellow": 0x04, "Green": 0x05, "Grey": 0x09, "Black": 0x06,
}
MARQUEE_FLAGS_TO_COLOUR = {v: k for k, v in MARQUEE_COLOUR_TO_FLAGS.items()}

BIN1_COLOUR_TO_FLAGS = {
    "Orange": 0x00, "Red": 0x01, "White": 0x02, "Blue": 0x03,
    "Yellow": 0x04, "Green": 0x05,
}
BIN1_FLAGS_TO_COLOUR = {v: k for k, v in BIN1_COLOUR_TO_FLAGS.items()}

BIN2_COLOUR_TO_FLAGS = {
    "Green": 0x00, "Red": 0x01, "White": 0x05, "Blue": 0x02,
    "Yellow": 0x03, "Orange": 0x06, "Black": 0x04,
}
BIN2_FLAGS_TO_COLOUR = {v: k for k, v in BIN2_COLOUR_TO_FLAGS.items()}

CHEVRON_COLOUR_TO_FLAGS = {"White": 0, "Black": 1}
CHEVRON_FLAGS_TO_COLOUR = {v: k for k, v in CHEVRON_COLOUR_TO_FLAGS.items()}

ARMCO_VARIANT_TO_FLAGS = {"Old": 0x00, "New": 0x09}
ARMCO_FLAGS_TO_VARIANT = {v: k for k, v in ARMCO_VARIANT_TO_FLAGS.items()}

# -------------------------------------------------------
# Sign / marker maps (canonical forward, auto reverse)
# -------------------------------------------------------
SIGN_SPEED_NAME_TO_FLAGS = {"40_mph": 3, "50_mph": 2, "50_kmh": 1, "80_kmh": 0}
SIGN_SPEED_FLAGS_TO_NAME = {v: k for k, v in SIGN_SPEED_NAME_TO_FLAGS.items()}

SIGN_METAL_NAME_TO_FLAGS = {
    "KeepLeft": 0, "KeepRight": 1, "Left": 2, "Right": 3,
    "UpLeft": 4, "UpRight": 5, "Forward": 6, "NoEntry": 7,
}
SIGN_METAL_FLAGS_TO_NAME = {v: k for k, v in SIGN_METAL_NAME_TO_FLAGS.items()}

MARKER_CORNER_NAME_TO_FLAGS = {
    "CurveL": 0, "CurveR": 1, "L": 2, "R": 3, "HardL": 4, "HardR": 5,
    "LR": 6, "RL": 7, "SL": 8, "SR": 9, "S2L": 10, "S2R": 11,
    "UL": 12, "UR": 13, "KinkL": 14, "KinkR": 15,
}
MARKER_CORNER_FLAGS_TO_NAME = {v: k for k, v in MARKER_CORNER_NAME_TO_FLAGS.items()}

MARKER_DISTANCE_NAME_TO_FLAGS = {"25": 0, "50": 1, "75": 2, "100": 3, "125": 4, "150": 5, "200": 6, "250": 7}
MARKER_DISTANCE_FLAGS_TO_NAME = {v: k for k, v in MARKER_DISTANCE_NAME_TO_FLAGS.items()}

KERB_COLOUR_MAP = {
    0: "White", 1: "Grey", 2: "Red", 3: "Blue",
    4: "Cyan", 5: "Green", 6: "Orange", 7: "Yellow",
}
KERB_COLOUR_TO_NUM = {v: k for k, v in KERB_COLOUR_MAP.items()}

# -------------------------------------------------------
# Grid normalization (pure, no bpy dependency)
# -------------------------------------------------------
def normalize_position(x, y, z, offset_x=0, offset_y=0, offset_z=0):
    nx = offset_x + round((x - offset_x) / GRID_XY) * GRID_XY
    ny = offset_y + round((y - offset_y) / GRID_XY) * GRID_XY
    nz = offset_z + round((z - offset_z) / GRID_Z) * GRID_Z
    return nx, ny, nz

def normalize_rotation_z(rot_z):
    return round(rot_z / GRID_ROT_Z) * GRID_ROT_Z

# -------------------------------------------------------
# Config loading
# -------------------------------------------------------
def load_config(blend_filepath):
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(blend_filepath), "config.ini")
    if not config.read(config_path):
        raise FileNotFoundError(f"config.ini not found at {config_path} - run run_first_time.py first")
    return (
        config.get("LFS", "path"),
        config.get("LFS", "map_name"),
        config.get("LFS", "track_name"),
    )
