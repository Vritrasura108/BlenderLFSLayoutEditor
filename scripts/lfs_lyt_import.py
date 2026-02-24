#
#   name        LFS layout Blender Tool - Import (0.8A ready, safe UNREF)
#   version     2.0 (refactored: shared code in lfs_lyt_common, callable import_from_lyt)
#   author      Vritrasura, Nex_ (patched)
#
#   Goals:
#   - Import .LYT (0.8A) into Blender by duplicating library objects.
#   - Kerb (Index 132): decode colour/mapping from Flags and map to library names.
#   - Safe fallback: if a library object is missing, place a placeholder named UNREF_...
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
    flags2width, flags2length, flags2sizex, flags2sizey,
    flags2height, flags2pitch, flags2angle,
    flags2concretecolour, flags2chalkcolour, flags2tyrecolour,
    flags2control, flags2diameter, flags2restrictedarea, flags2insimcheckpointwidth,
    load_config,
    PAINT_GLYPHS, PAINT_ARROW, LETTERBOARD_GLYPHS,
    CONE_FLAGS_TO_NAME,
    POST_FLAGS_TO_COLOUR, MARQUEE_FLAGS_TO_COLOUR,
    BIN1_FLAGS_TO_COLOUR, BIN2_FLAGS_TO_COLOUR,
    CHEVRON_FLAGS_TO_COLOUR,
    SIGN_SPEED_FLAGS_TO_NAME, SIGN_METAL_FLAGS_TO_NAME,
    MARKER_CORNER_FLAGS_TO_NAME, MARKER_DISTANCE_FLAGS_TO_NAME,
    KERB_COLOUR_MAP,
)

# --------------------------
# Helpers
# --------------------------
missing_library_objects = []

def get_library_object_or_placeholder(name: str, placeholder_name: str = "Block_00_00"):
    """
    Returns (obj, used_placeholder_bool).
    """
    if name in bpy.data.objects:
        return bpy.data.objects[name], False

    if name not in missing_library_objects:
        missing_library_objects.append(name)

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

# --------------------------
# Kerb (Index 132) decoding
# --------------------------
def kerb_object_name_from_flags(flags: int) -> str:
    c = flags & 0x07
    shade = (flags >> 3) & 0x01

    colour = KERB_COLOUR_MAP.get(c, "White")
    variant = 1 if shade == 0 else 2
    return f"Kerb_{colour}_{variant}"

# --------------------------
# Posts / Marquee / Bins
# --------------------------
def post_object_name_from_flags(flags: int) -> str:
    colour = POST_FLAGS_TO_COLOUR.get(flags & 0xFF)
    if colour is None:
        return f"UNREF_Post_F{flags:02X}"
    return f"Post_{colour}"

def marquee_object_name_from_flags(flags: int) -> str:
    colour = MARQUEE_FLAGS_TO_COLOUR.get(flags & 0xFF)
    if colour is None:
        return f"UNREF_Marquee_F{flags:02X}"
    return f"Marquee_{colour}"

def bin1_object_name_from_flags(flags: int) -> str:
    colour = BIN1_FLAGS_TO_COLOUR.get(flags & 0xFF)
    if colour is None:
        return f"UNREF_Bin1_F{flags:02X}"
    return f"Bin1_{colour}"

def bin2_object_name_from_flags(flags: int) -> str:
    colour = BIN2_FLAGS_TO_COLOUR.get(flags & 0xFF)
    if colour is None:
        return f"UNREF_Bin2_F{flags:02X}"
    return f"Bin2_{colour}"

# --------------------------
# Paint / Markers / Cones
# --------------------------
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
def letter_boardWY_name_from_flags(flags: int) -> str:
    # Strip floating bit (0x80) before decoding glyph
    glyph_id = (flags >> 1) & 0x3F
    colour_bit = flags & 0x01

    if glyph_id >= len(LETTERBOARD_GLYPHS):
        return f"UNREF_Letter_Board_G{glyph_id:02d}_{'Yellow' if colour_bit else 'White'}"

    glyph = LETTERBOARD_GLYPHS[glyph_id]
    colour = "Yellow" if colour_bit else "White"
    return f"Letter_Board_{glyph}_{colour}"

def letter_boardBR_name_from_flags(flags: int) -> str:
    # Strip floating bit (0x80) before decoding glyph
    glyph_id = (flags >> 1) & 0x3F
    colour_bit = flags & 0x01

    if glyph_id >= len(LETTERBOARD_GLYPHS):
        return f"UNREF_Letter_Board_G{glyph_id:02d}_{'Blue' if colour_bit else 'Red'}"

    glyph = LETTERBOARD_GLYPHS[glyph_id]
    colour = "Blue" if colour_bit else "Red"
    return f"Letter_Board_{glyph}_{colour}"

# --------------------------
# Sign Speed (Index 168) decoding
# --------------------------
def sign_speed_object_name_from_flags(flags: int) -> str:
    mapping = (flags & 0x78) >> 3
    speed = SIGN_SPEED_FLAGS_TO_NAME.get(mapping)
    if speed is None:
        return f"UNREF_Sign_Speed_M{mapping:02d}_F{flags:02X}"
    return f"Sign_Speed_{speed}"

# --------------------------
# Sign Metal (Index 160) decoding
# --------------------------
def sign_metal_object_name_from_flags(flags: int) -> str:
    mapping = (flags & 0x78) >> 3
    kind = SIGN_METAL_FLAGS_TO_NAME.get(mapping)
    if kind is None:
        return f"UNREF_Sign_Metal_M{mapping:02d}_F{flags:02X}"
    return f"Sign_Metal_{kind}"

# --------------------------
# Chevron (Index 164 / 165) decoding
# --------------------------
def chevron_object_name_from_flags(flags: int, index: int) -> str:
    colour = CHEVRON_FLAGS_TO_COLOUR.get(flags & 0xFF)
    if colour is None:
        return f"UNREF_Chevron_F{flags:02X}"

    if index == 164:
        direction = "Right"
    elif index == 165:
        direction = "Left"
    else:
        direction = f"I{index:03d}"

    return f"Chevron_{direction}_{colour}"

def armco_object_name_from_flags(index: int, flags: int) -> str:
    flags = flags & 0xFF

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
# Resolve one object record into a name
# --------------------------
def resolve_object_name(index, flags, heading_byte):
    """Given an LYT object record (index, flags, heading_byte), return (objectName, lib_name, postRename, skip_rotation)."""
    suffix = ""

    # Chalk / Tyres: colour goes into suffix
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
        case 128: name = "SpeedHump10m"
        case 129: name = "SpeedHump6m"
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
            width = flags2width(flags)
            length = flags2length(flags)
            pitch = flags2pitch(flags)
            name = f"Slab_{width}_{length}_{pitch:02d}"

        case 173:
            width = flags2width(flags)
            length = flags2length(flags)
            height = flags2height(flags)
            name = f"Ramp_{width}_{length}_{height:03d}"

        case 174:
            colour = flags2concretecolour(flags)
            length = flags2length(flags)
            height = flags2height(flags)
            name = f"Wall_{length}_{height:03d}_{colour}"

        case 175:
            sizex = flags2sizex(flags)
            sizey = flags2sizey(flags)
            height = flags2height(flags)
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
            posID = flags & 0x3F
            name = f"StartPosition_{posID+1:02d}"

        case 185:
            posID = flags & 0x3F
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

    # Determine library lookup name and whether to post-rename
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

    skip_rotation = name.startswith("RouteChecker") or name.startswith("InSimCircle")

    return objectName, lib_name, postRename, skip_rotation

# --------------------------
# Core import function (callable from tests / other scripts)
# --------------------------
def import_from_lyt(lyt_path, collection):
    """Import a .lyt file into the given Blender collection. Returns list of created objects."""
    created_objects = []

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

            objectName, lib_name, postRename, skip_rotation = resolve_object_name(index, flags, heading_byte)

            lib_obj, used_placeholder = get_library_object_or_placeholder(lib_name, placeholder_name="Block_00_00")
            newobj = duplicate(lib_obj, collection)

            if postRename or used_placeholder:
                newobj.name = objectName

            newobj.location.x = x
            newobj.location.y = y
            newobj.location.z = z

            if not skip_rotation:
                newobj.rotation_euler.z = rad

            created_objects.append(newobj)

            print(f"Putting {objectName} -> [{x:.3f}, {y:.3f}, {z:.3f}] azimuth={deg:.1f}")

    return created_objects

# --------------------------
# Standalone execution (Blender text editor / --python)
# --------------------------
if __name__ == "__main__":
    os.system("cls")

    LFS_PATH, MAP_NAME, TRACK_NAME = load_config(bpy.data.filepath)
    COLLECTION = "LFS Track"

    lyt_path = f"{LFS_PATH}/data/layout/{MAP_NAME}_{TRACK_NAME}.lyt"
    collection = bpy.data.collections.get(COLLECTION)
    if collection is None:
        raise RuntimeError(f"Collection '{COLLECTION}' not found")

    import_from_lyt(lyt_path, collection)
