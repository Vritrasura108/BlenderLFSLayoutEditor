"""
Centralized loader for LFS piece library objects.

Links the entire LFS Pieces collection from data/lfs_pieces_library.blend
on first access. Objects are linked (read-only mesh data referencing the
library file). Use obj.copy() to create local instances with their own
transforms that share the linked mesh data.

Usage (from any script that already has scripts/ on sys.path):
    from lfs_library_loader import ensure_object, ensure_objects
"""

import bpy
import os

_library_loaded = False


def _get_library_path() -> str:
    """Resolve the path to lfs_pieces_library.blend relative to the .blend file."""
    blend_dir = os.path.dirname(bpy.data.filepath)
    return os.path.join(blend_dir, "data", "lfs_pieces_library.blend")


def _load_library():
    """Link the entire LFS Pieces collection hierarchy from the library file."""
    global _library_loaded
    if _library_loaded:
        return

    _library_loaded = True

    lib_path = _get_library_path()
    if not os.path.isfile(lib_path):
        print(f"WARNING: Library file not found: {lib_path}")
        return

    try:
        with bpy.data.libraries.load(lib_path, link=True) as (data_from, data_to):
            data_to.objects = list(data_from.objects)
        linked = sum(1 for o in bpy.data.objects if o.library is not None)
        print(f"Linked {linked} objects from {lib_path}")
    except Exception as e:
        print(f"WARNING: Failed to link library: {e}")


def get_all_library_names() -> list:
    """Return list of all object names available in the external library."""
    lib_path = _get_library_path()
    if not os.path.isfile(lib_path):
        return []
    with bpy.data.libraries.load(lib_path) as (data_from, _data_to):
        return list(data_from.objects)


def ensure_object(name: str) -> bool:
    """
    Ensure that the named object exists in bpy.data.objects.
    Links library on first call if needed.
    Returns True if the object is available, False otherwise.
    """
    if name in bpy.data.objects:
        return True

    _load_library()
    return name in bpy.data.objects


def ensure_objects(names) -> dict:
    """
    Ensure multiple objects exist in bpy.data.objects.
    Returns dict of {name: bool} indicating availability.
    """
    _load_library()
    return {name: (name in bpy.data.objects) for name in names}


def get_all_objects_by_pattern(family_check, colour_check) -> list:
    """
    Return all library objects whose names match both predicates.
    Used by the text builder to discover glyph meshes.

    family_check: callable(name_upper) -> bool
    colour_check: callable(name_upper) -> bool

    Returns list of bpy.types.Object.
    """
    _load_library()

    results = []
    for obj in bpy.data.objects:
        if obj.library is None:
            continue
        name_u = obj.name.upper()
        if family_check(name_u) and colour_check(name_u):
            results.append(obj)
    return results


def reset_cache():
    """Reset the loaded state (useful for tests)."""
    global _library_loaded
    _library_loaded = False
