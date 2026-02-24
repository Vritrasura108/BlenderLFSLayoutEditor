"""
Headless validation that the blend file can load all external scripts.

Usage:
    blender --background lyt_editor.blend --python tests/test_blend_scripts.py
"""

import bpy
import os
import sys

EXPECTED_SCRIPTS = {
    "duplicate_along_curve.py",
    "lfs_lyt_export.py",
    "lfs_lyt_import.py",
    "lfs_normalize_object.py",
    "lfs_object_to_block.py",
    "lfs_text_builder.py",
}

blend_dir = os.path.dirname(bpy.data.filepath)
errors = []


# --- Check all expected text blocks exist ---
text_names = {t.name for t in bpy.data.texts}
missing = EXPECTED_SCRIPTS - text_names
if missing:
    errors.append(f"Missing text blocks: {missing}")

# --- Check each script is externally linked and readable ---
for name in sorted(EXPECTED_SCRIPTS & text_names):
    text = bpy.data.texts[name]

    if text.is_in_memory:
        errors.append(f"{name}: still stored in memory (should be external)")
        continue

    if not text.filepath:
        errors.append(f"{name}: no filepath set")
        continue

    # Resolve relative path (Blender uses // prefix)
    rel = text.filepath.replace("\\", "/")
    if rel.startswith("//"):
        abs_path = os.path.normpath(os.path.join(blend_dir, rel[2:]))
    else:
        abs_path = os.path.normpath(rel)

    if not os.path.isfile(abs_path):
        errors.append(f"{name}: file not found at {abs_path}")
        continue

    # Verify file is non-empty and content matches
    with open(abs_path, "r", encoding="utf-8") as f:
        disk_content = f.read()

    blend_content = text.as_string()

    if not disk_content.strip():
        errors.append(f"{name}: file on disk is empty")
    elif disk_content != blend_content:
        errors.append(f"{name}: content mismatch between disk and blend")
    else:
        print(f"OK  {name} ({len(text.lines)} lines, filepath={text.filepath})")

# --- Check scripts compile without syntax errors ---
for name in sorted(EXPECTED_SCRIPTS & text_names):
    text = bpy.data.texts[name]
    try:
        compile(text.as_string(), name, "exec")
        print(f"OK  {name} compiles")
    except SyntaxError as e:
        errors.append(f"{name}: syntax error at line {e.lineno}: {e.msg}")

# --- Report ---
print()
if errors:
    print(f"FAILED - {len(errors)} error(s):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print(f"PASSED - all {len(EXPECTED_SCRIPTS)} scripts validated")
    sys.exit(0)
