"""Dump the full structure of LFS Pieces collection."""
import bpy
import sys

pieces = bpy.data.collections.get("LFS Pieces")
if not pieces:
    print("ERROR: 'LFS Pieces' collection not found")
    sys.exit(1)

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

dump_collection(pieces)
sys.exit(0)
