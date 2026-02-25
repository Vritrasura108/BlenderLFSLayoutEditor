"""
Remove the LFS Pieces collection from lyt_editor.blend after extraction.

Usage:
    blender --background lyt_editor.blend --python scripts/remove_pieces_from_main.py

Run this AFTER extract_library_to_blend.py has created the external library.
Removes all objects and subcollections from "LFS Pieces", purges orphaned
data, and saves the file.
"""

import bpy
import os
import sys

# Safety check: verify library file exists before removing objects
BLEND_DIR = os.path.dirname(bpy.data.filepath)
LIB_PATH = os.path.join(BLEND_DIR, "data", "lfs_pieces_library.blend")

if not os.path.isfile(LIB_PATH):
    print(f"ERROR: Library file not found at {LIB_PATH}")
    print("Run extract_library_to_blend.py first!")
    sys.exit(1)


def main():
    pieces = bpy.data.collections.get("LFS Pieces")
    if pieces is None:
        print("'LFS Pieces' already removed")
        sys.exit(0)

    # Count before removal
    obj_count = 0

    def count_objects(coll):
        nonlocal obj_count
        obj_count += len(coll.objects)
        for child in coll.children:
            count_objects(child)

    count_objects(pieces)
    print(f"Removing {obj_count} objects from 'LFS Pieces'...")

    # Recursively remove all objects and subcollections
    def remove_all(coll):
        for obj in list(coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for child in list(coll.children):
            remove_all(child)
            bpy.data.collections.remove(child)

    remove_all(pieces)
    bpy.data.collections.remove(pieces)

    # Purge orphaned data (meshes, materials with no users)
    bpy.ops.outliner.orphans_purge(do_recursive=True)

    bpy.ops.wm.save_mainfile()
    print("Removed LFS Pieces and saved")

    file_size = os.path.getsize(bpy.data.filepath)
    print(f"New file size: {file_size / 1024 / 1024:.1f} MB")


main()
