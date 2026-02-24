# objecttoblock.py
#
#  name        LFS layout Blender Tool - ObjectToBlock (placeholders)
#  version     1.1
#  purpose     Read .LYT and spawn placeholder cubes for each object,
#              using the same "case index" naming logic as import.py.
#              If an object is not referenced in the known mapping,
#              it is still created and named explicitly so you can
#              identify the missing case.
#
#  Usage:
#   - Open Blender > Scripting
#   - Paste this script and run
#   - It will read: C:/LFS/data/layout/{MAP_NAME}_{TRACK_NAME}.lyt
#   - It will create cubes in collection: COLLECTION
#
#  Notes:
#   - This script does not depend on any pre-existing library objects.
#   - Every cube stores decoded LFS data in Custom Properties.
#   - UNREF_* names mark unknown/unhandled indices.
#Author : Nex_ by vibecoding with chatgpt

LFS_PATH   = "C:/LFS"
MAP_NAME   = "LA1"
TRACK_NAME = "V8"
COLLECTION = "LFS Track"
CUBE_SIZE  = 0.50  # meters (visual placeholder size)

import bpy
import struct
import math
import os

os.system("cls")

def ensure_collection(name: str) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col

def create_cube(name: str, collection: bpy.types.Collection, size: float) -> bpy.types.Object:
    import bmesh

    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=size)
    bm.to_mesh(mesh)
    bm.free()

    return obj

def flags2concretecolour(flags):
    colours = ["Grey", "Red", "Blue", "Yellow"]
    return colours[flags & 0x03]

def flags2length(flags):
    lengths = [2, 4, 8, 16]
    return lengths[(flags >> 2) & 0x03]

def flags2height(flags):
    heights = [25, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350, 375, 400]
    return heights[(flags >> 4) & 0x0f]

def flags2pitch(flags):
    pitches = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 90]
    return pitches[(flags >> 4) & 0x0f]

def flags2sizey(flags):
    sizes = [25, 50, 75, 100]
    return sizes[(flags >> 2) & 0x03]

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

def flags2restrictedarea(flags):
    types = ["Invisible", "Marshall", "MarshallPointLeft", "MarshallPointRight"]
    return types[flags & 0x03]

def flags2diameter(flags):
    radius = (flags >> 2) & 0x1f
    return radius << 1

def flags2insimcheckpointwidth(flags):
    width = ((flags >> 2) & 0x1F) * 2
    return width

def decode_object_name(index: int, flags: int, heading_byte: int) -> str:
    suffix = ""

    # Optional debug suffixes (legacy style)
    if 4 <= index <= 13:
        colours = ["White", "Red", "Blue", "Yellow"]
        suffix = colours[flags & 0x03]
    elif 48 <= index <= 55:
        colours = ["Black", "White", "Red", "Blue", "Green", "Yellow"]
        suffix = colours[flags & 0x07]

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

        case 20: name = "ConeRed"
        case 21: name = "ConeRed2"
        case 22: name = "ConeRed3"
        case 23: name = "ConeBlue"
        case 24: name = "ConeBlue2"
        case 25: name = "ConeGreen"
        case 26: name = "ConeGreen2"
        case 27: name = "ConeOrange"
        case 28: name = "ConeWhite"
        case 29: name = "ConeYellow"
        case 30: name = "ConeYellow2"

        case 40: name = "ConeRedPtr"
        case 41: name = "ConeBluePtr"
        case 42: name = "ConeGreenPtr"
        case 43: name = "ConeYellowPtr"

        case 48: name = "TyreSingle"
        case 49: name = "TyreStack2"
        case 50: name = "TyreStack3"
        case 51: name = "TyreStack4"
        case 52: name = "TyreSingleBig"
        case 53: name = "TyreStack2Big"
        case 54: name = "TyreStack3Big"
        case 55: name = "TyreStack4Big"

        case 64: name = "MarkerCurveL"
        case 65: name = "MarkerCurveR"
        case 66: name = "MarkerHardL"
        case 67: name = "MarkerHardR"
        case 68: name = "MarkerL"
        case 69: name = "MarkerLR"
        case 70: name = "MarkerR"
        case 71: name = "MarkerRL"
        case 72: name = "MarkerS2L"
        case 73: name = "MarkerS2R"
        case 74: name = "MarkerSL"
        case 75: name = "MarkerSR"
        case 76: name = "MarkerUL"
        case 77: name = "MarkerUR"

        case 84: name = "Marker25"
        case 85: name = "Marker50"
        case 86: name = "Marker75"
        case 87: name = "Marker100"
        case 88: name = "Marker125"
        case 89: name = "Marker150"
        case 90: name = "Marker200"
        case 91: name = "Marker250"

        
        case 104: name = "BarrierLong"
        case 105: name = "BarrierRed"
        case 106: name = "BarrierWhite"

        case 112: name = "Banner1"
        case 113: name = "Banner2"

        case 120: name = "Ramp1"
        case 121: name = "Ramp2"

        case 128: name = "SpeedHump6m"
        case 129: name = "SpeedHump10m"

        case 144: name = "Bale"
        case 148: name = "Railing"
        case 149: name = "StartLights"

        case 160: name = "SignKeepLeft"
        case 161: name = "SignKeepRight"

        case 168: name = "SignSpeed50"
        case 169: name = "SignSpeed80"

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
            circ_index = heading_byte + 1
            diameter = flags2diameter(flags)
            name = f"InSimCircle_{diameter:02d}"
            suffix = f"{circ_index}"

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
            # Explicit fallback: lets you identify missing case instantly
            # I = Index, F = Flags hex, H = Heading byte (raw)
            name = f"UNREF_I{index:03d}_F{flags:02X}_H{heading_byte:03d}"

    if suffix:
        return f"{name}_{suffix}"
    return name

def attach_lfs_properties(obj: bpy.types.Object,
                          mini_rev: int,
                          x_i: int, y_i: int, z_b: int,
                          flags: int, index: int, heading_b: int,
                          deg: float):
    obj["lfs_index"] = int(index)
    obj["lfs_flags"] = int(flags)
    obj["lfs_heading_byte"] = int(heading_b)
    obj["lfs_heading_deg"] = float(deg)
    obj["lfs_x16"] = int(x_i)
    obj["lfs_y16"] = int(y_i)
    obj["lfs_z4"] = int(z_b)
    obj["lfs_mini_rev_or_flags"] = int(mini_rev)
    obj["lfs_source"] = f"{MAP_NAME}_{TRACK_NAME}.lyt"

def main():
    col = ensure_collection(COLLECTION)

    path = f"{LFS_PATH}/data/layout/{MAP_NAME}_{TRACK_NAME}.lyt"
    with open(path, "rb") as f:
        magic, version, revision, objCount, laps, mini_rev = struct.unpack("<6sBBHBB", f.read(12))

        if magic != b"LFSLYT":
            raise ValueError("Pas un fichier LFS .LYT (magic LFSLYT absent).")

        print(f"Header: version={version} revision={revision} objCount={objCount} laps={laps} mini_rev/flags={mini_rev}")

        for i in range(objCount):
            x_i, y_i, z_b, flags, index, heading_b = struct.unpack("<hhBBBB", f.read(8))

            x = x_i / 16.0
            y = y_i / 16.0
            z = z_b / 4.0

            deg = ((heading_b * 360.0) / 256.0) - 180.0
            rad = math.radians(deg)

            obj_name = decode_object_name(index, flags, heading_b)

            if obj_name.startswith("UNREF_"):
                print(f"WARNING: Object non référencé -> {obj_name}")

            cube = create_cube(obj_name, col, CUBE_SIZE)

            cube.location.x = x
            cube.location.y = y
            cube.location.z = z

            # Special objects that use heading byte as index
            if not (obj_name.startswith("RouteChecker") or obj_name.startswith("InSimCircle")):
                cube.rotation_euler.z = rad

            attach_lfs_properties(
                cube,
                mini_rev,
                x_i, y_i, z_b,
                flags, index, heading_b,
                deg
            )

            print(f"[{i:04d}] {obj_name} @ ({x:.3f},{y:.3f},{z:.3f}) flags={flags:02X} index={index} heading={deg:.1f}")

if __name__ == "__main__":
    main()
