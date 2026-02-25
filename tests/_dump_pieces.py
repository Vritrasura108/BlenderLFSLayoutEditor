"""Dump the full structure of LFS Pieces collection or external library."""
import bpy
import os
import sys

# Ensure scripts/ is on sys.path
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def dump_collection(coll, indent=0):
    prefix = "  " * indent
    obj_count = len(coll.objects)
    child_count = len(coll.children)
    print(f"{prefix}[{coll.name}] ({obj_count} objects, {child_count} subcollections)")

    # List objects sorted by name
    for obj in sorted(coll.objects, key=lambda o: o.name):
        print(f"{prefix}  - {obj.name}  (type={obj.type})")

    # Recurse into child collections
    for child in sorted(coll.children, key=lambda c: c.name):
        dump_collection(child, indent + 1)


pieces = bpy.data.collections.get("LFS Pieces")
if pieces:
    dump_collection(pieces)
    sys.exit(0)

# Fallback: load from external library
from lfs_library_loader import get_all_library_names, ensure_objects

all_names = get_all_library_names()
if not all_names:
    print("ERROR: 'LFS Pieces' collection not found and external library is empty or missing")
    sys.exit(1)

print(f"Loading {len(all_names)} objects from external library...")
ensure_objects(all_names)

for name in sorted(all_names):
    if name in bpy.data.objects:
        obj = bpy.data.objects[name]
        print(f"  - {obj.name}  (type={obj.type})")
    else:
        print(f"  - {name}  (FAILED to load)")

sys.exit(0)
