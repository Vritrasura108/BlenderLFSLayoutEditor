"""
Roundtrip export/import test for all LFS Pieces.

Copies every object from the 'LFS Pieces' subcollections into 'LFS Track',
arranges them on a grid, exports to .lyt, imports back, re-exports, and
verifies the two .lyt files are byte-for-byte identical (after sorting
object records).

Usage:
    blender --background lyt_editor.blend --python tests/test_export_import_roundtrip.py
"""

import bpy
import struct
import math
import os
import sys
import tempfile

# ---------------------------------------------------------------------------
# Setup: make scripts/ importable
# ---------------------------------------------------------------------------
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from lfs_lyt_export import export_to_lyt, name2blockid, name2flags
from lfs_lyt_import import import_from_lyt, missing_library_objects
from lfs_library_loader import get_all_library_names, ensure_objects

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUBCOLLECTIONS = [
    "Slab", "Wedge", "Pillar", "RampWall", "SlabWall", "Wall",
    "Armco", "Bale", "Banner", "Barrier", "Chalk", "Cone",
    "Marker", "Railing", "ShortSlabWall", "Tyre", "Sign",
    "speedhump", "Control", "Post", "Ramp",
]

GRID_SPACING = 20.0    # metres between objects (generous to avoid overlap)
GRID_Z = 0.0           # all objects at ground level
LFS_ROT_STEP = 2 * math.pi / 256  # ~1.40625 degrees in radians

# Objects that cannot roundtrip (export produces index 0 with no useful flags)
SKIP_PREFIXES = ("UNREF_", "Block_00")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_or_create_collection(name):
    """Get existing collection or create a new one linked to the scene."""
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def clear_collection(coll):
    """Remove all objects from a collection."""
    for obj in list(coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


PREFIX_TO_SUBCOLLECTION = [
    ("SlabWall_", "SlabWall"), ("ShortSlabWall_", "ShortSlabWall"),
    ("Slab_", "Slab"), ("Wedge_", "Wedge"), ("Pillar_", "Pillar"),
    ("RampWall_", "RampWall"), ("Wall_", "Wall"),
    ("Armco_", "Armco"), ("Bale", "Bale"),
    ("Banner", "Banner"), ("BarrierLong", "Barrier"), ("BarrierRed", "Barrier"),
    ("BarrierWhite", "Barrier"), ("Railing", "Barrier"),
    ("Chalk", "Chalk"), ("Cone", "Cone"), ("Marker", "Marker"),
    ("Tyre", "Tyre"), ("Sign_", "Sign"), ("Chevron_", "Sign"),
    ("SpeedHump", "speedhump"), ("Post_", "Post"), ("Marquee_", "Post"),
    ("Bin1_", "Post"), ("Bin2_", "Post"),
    ("Ramp_", "Ramp"), ("Ramp1", "Ramp"), ("Ramp2", "Ramp"),
    ("Checkpoint", "Control"), ("FinishLine", "Control"),
    ("AutocrossStart", "Control"), ("StartPosition", "Control"),
    ("PitStartPoint", "Control"), ("PitStopBox", "Control"),
    ("RouteChecker", "Control"), ("RestrictedArea", "Control"),
    ("InSimCheckpoint", "Control"), ("InSimCircle", "Control"),
    ("StartLights", "Control"),
    ("Kerb_", "Kerb"), ("Letter_Board", "Letter_Board"),
    ("Paint_", "Paint"),
]


def _infer_subcollection(base_name):
    """Infer the subcollection name from an object's base name."""
    for prefix, sub in PREFIX_TO_SUBCOLLECTION:
        if base_name.startswith(prefix):
            return sub
    return "Unknown"


def _filter_exportable(name):
    """Return True if an object with this name can be exported in the roundtrip."""
    base_name = name.split(".")[0]
    if any(base_name.startswith(p) for p in SKIP_PREFIXES):
        return False
    try:
        name2blockid(name)
        name2flags(name)
    except (IndexError, ValueError, KeyError):
        print(f"  SKIP {name} (template / cannot export)")
        return False
    sub = _infer_subcollection(base_name)
    return sub in SUBCOLLECTIONS


def collect_library_objects():
    """Walk 'LFS Pieces' subcollections and return list of (subcoll_name, obj).
    Falls back to external library file if collection not in scene."""
    pieces = bpy.data.collections.get("LFS Pieces")
    if pieces is not None:
        results = []
        for subcoll in pieces.children:
            if subcoll.name not in SUBCOLLECTIONS:
                continue
            for obj in subcoll.objects:
                base_name = obj.name.split(".")[0]
                if any(base_name.startswith(p) for p in SKIP_PREFIXES):
                    continue
                try:
                    name2blockid(obj.name)
                    name2flags(obj.name)
                except (IndexError, ValueError, KeyError):
                    print(f"  SKIP {obj.name} (template / cannot export)")
                    continue
                results.append((subcoll.name, obj))
        return results

    # Fallback: load from external library file
    all_names = get_all_library_names()
    if not all_names:
        print("ERROR: 'LFS Pieces' collection not found and external library is empty or missing")
        sys.exit(1)

    print(f"Loading {len(all_names)} objects from external library...")
    ensure_objects(all_names)

    results = []
    for name in all_names:
        if name not in bpy.data.objects:
            continue
        if not _filter_exportable(name):
            continue
        obj = bpy.data.objects[name]
        base_name = name.split(".")[0]
        sub = _infer_subcollection(base_name)
        results.append((sub, obj))
    return results


def parse_lyt_records(path):
    """Read a .lyt file and return a sorted list of 8-byte object records."""
    with open(path, "rb") as f:
        header = f.read(12)
        magic = header[:6]
        if magic != b"LFSLYT":
            raise RuntimeError(f"Bad magic in {path}")
        obj_count = struct.unpack_from("<H", header, 8)[0]
        records = []
        for _ in range(obj_count):
            records.append(f.read(8))
    return sorted(records)


def record_to_str(rec):
    """Pretty-print one 8-byte record for diagnostics."""
    x, y, z, flags, idx, heading = struct.unpack("<hhBBBB", rec)
    return f"X={x} Y={y} Z={z} Flags=0x{flags:02X} Idx={idx} Head={heading}"


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------
def run_test():
    errors = []

    # 1) Collect library objects
    lib_objects = collect_library_objects()
    if not lib_objects:
        print("ERROR: No objects found in LFS Pieces subcollections")
        sys.exit(1)

    print(f"\nFound {len(lib_objects)} library objects across subcollections:")
    by_sub = {}
    for sub, obj in lib_objects:
        by_sub.setdefault(sub, []).append(obj.name)
    for sub in sorted(by_sub):
        print(f"  {sub}: {len(by_sub[sub])} objects")

    # 2) Prepare LFS Track collection
    track_coll = get_or_create_collection("LFS Track")
    clear_collection(track_coll)

    # 3) Duplicate objects into LFS Track, arranged on a grid
    cols = int(math.ceil(math.sqrt(len(lib_objects))))
    placed = []

    for i, (sub, lib_obj) in enumerate(lib_objects):
        col = i % cols
        row = i // cols

        copy = lib_obj.copy()
        track_coll.objects.link(copy)

        # Grid-snapped position (multiples of 0.0625 for XY, 0.25 for Z)
        copy.location.x = round(col * GRID_SPACING / 0.0625) * 0.0625
        copy.location.y = round(row * GRID_SPACING / 0.0625) * 0.0625
        copy.location.z = GRID_Z

        # Assign a deterministic rotation (cycle through a few heading values)
        heading_steps = [0, 32, 64, 96, 128, 160, 192, 224]
        step = heading_steps[i % len(heading_steps)]
        rot_rad = ((step * 360 / 256) - 180) * math.pi / 180.0
        # RouteChecker / InSimCircle: heading byte = index, skip rotation
        base_name = copy.name.split(".")[0]
        if not base_name.startswith("RouteChecker") and not base_name.startswith("InSimCircle"):
            copy.rotation_euler.z = rot_rad

        placed.append(copy)

    print(f"\nPlaced {len(placed)} objects into 'LFS Track' on {cols}x{(len(placed)+cols-1)//cols} grid")

    # 4) Export to first .lyt
    tmp_dir = tempfile.mkdtemp(prefix="lfs_roundtrip_")
    lyt_path_1 = os.path.join(tmp_dir, "test_export_1.lyt")

    # Select all objects for export
    bpy.ops.object.select_all(action='DESELECT')
    for obj in placed:
        obj.select_set(True)

    export_to_lyt(placed, lyt_path_1, normalize=True)

    records_1 = parse_lyt_records(lyt_path_1)
    print(f"\nExported {len(records_1)} records to {lyt_path_1}")

    # 5) Clear and reimport
    clear_collection(track_coll)
    imported = import_from_lyt(lyt_path_1, track_coll)
    print(f"\nImported {len(imported)} objects from {lyt_path_1}")

    if len(imported) != len(records_1):
        errors.append(f"Count mismatch: exported {len(records_1)} but imported {len(imported)}")

    # 6) Re-export
    lyt_path_2 = os.path.join(tmp_dir, "test_export_2.lyt")
    export_to_lyt(imported, lyt_path_2, normalize=True)

    records_2 = parse_lyt_records(lyt_path_2)
    print(f"\nRe-exported {len(records_2)} records to {lyt_path_2}")

    # 7) Compare sorted records
    if len(records_1) != len(records_2):
        errors.append(f"Record count mismatch: first={len(records_1)} second={len(records_2)}")
    else:
        mismatches = 0
        for i, (r1, r2) in enumerate(zip(records_1, records_2)):
            if r1 != r2:
                mismatches += 1
                if mismatches <= 20:  # limit output
                    errors.append(
                        f"Record {i} mismatch:\n"
                        f"  first:  {record_to_str(r1)}\n"
                        f"  second: {record_to_str(r2)}"
                    )
        if mismatches > 20:
            errors.append(f"... and {mismatches - 20} more mismatches")
        if mismatches > 0:
            errors.append(f"Total mismatched records: {mismatches}/{len(records_1)}")

    # 8) Detailed position/rotation check on reimported objects
    pos_errors = 0
    for obj in imported:
        x16 = round(obj.location.x * 16.0)
        y16 = round(obj.location.y * 16.0)
        z4 = round(obj.location.z * 4.0)

        # Validate coordinates are within LFS bounds
        if x16 < -32768 or x16 > 32767:
            pos_errors += 1
        if y16 < -32768 or y16 > 32767:
            pos_errors += 1
        if z4 < 0 or z4 > 255:
            pos_errors += 1

    if pos_errors:
        errors.append(f"{pos_errors} coordinate bound violations in imported objects")

    # Cleanup temp files
    try:
        os.remove(lyt_path_1)
        os.remove(lyt_path_2)
        os.rmdir(tmp_dir)
    except OSError:
        pass

    # 9) Report
    print()
    if errors:
        print(f"FAILED - {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.stdout.flush()
        sys.exit(1)
    else:
        missing_info = f", {len(missing_library_objects)} missing model(s)" if missing_library_objects else ""
        print(f"PASSED - roundtrip test with {len(placed)} objects{missing_info}")
        if missing_library_objects:
            print(f"\n  Missing library models:")
            for name in missing_library_objects:
                print(f"    - {name}")
        sys.stdout.flush()
        sys.exit(0)


run_test()
