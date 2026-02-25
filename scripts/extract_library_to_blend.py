"""
Extract LFS Pieces collection from lyt_editor.blend into a standalone library file.

Usage:
    blender --background lyt_editor.blend --python scripts/extract_library_to_blend.py

Creates data/lfs_pieces_library.blend containing all objects, meshes,
materials, and collections from the "LFS Pieces" hierarchy.
Does NOT modify the main .blend file (uses save-as-copy).
"""

import bpy
import os
import sys

BLEND_DIR = os.path.dirname(bpy.data.filepath)
LIB_DIR = os.path.join(BLEND_DIR, "data")
LIB_PATH = os.path.join(LIB_DIR, "lfs_pieces_library.blend")


def main():
    pieces = bpy.data.collections.get("LFS Pieces")
    if pieces is None:
        print("ERROR: 'LFS Pieces' collection not found")
        sys.exit(1)

    # Collect names of all objects that belong to LFS Pieces (recursive)
    keep_objects = set()

    def walk_keep(coll):
        for obj in coll.objects:
            keep_objects.add(obj.name)
        for child in coll.children:
            walk_keep(child)

    walk_keep(pieces)
    print(f"LFS Pieces contains {len(keep_objects)} objects")

    # Remove all objects NOT in LFS Pieces from the scene
    scene_coll = bpy.context.scene.collection
    removed = 0
    for obj in list(bpy.data.objects):
        if obj.name not in keep_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    print(f"Removed {removed} non-library objects from scene")

    # Remove all top-level collections except LFS Pieces
    for coll in list(scene_coll.children):
        if coll.name != "LFS Pieces":
            scene_coll.children.unlink(coll)

    # Purge orphaned data
    bpy.ops.outliner.orphans_purge(do_recursive=True)

    # Save as copy (keeps bpy.data.filepath pointing to original lyt_editor.blend)
    os.makedirs(LIB_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=LIB_PATH, copy=True)

    file_size = os.path.getsize(LIB_PATH)
    print(f"Library saved to {LIB_PATH} ({file_size / 1024 / 1024:.1f} MB)")
    print(f"Original file NOT modified (save-as-copy mode)")


main()
