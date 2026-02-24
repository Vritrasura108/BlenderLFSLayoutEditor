"""Reload all external text blocks from disk and save the blend file."""
import bpy
import os

blend_dir = os.path.dirname(bpy.data.filepath)
reloaded = 0

for text in bpy.data.texts:
    if not text.is_in_memory and text.filepath:
        # Resolve relative path (Blender uses // prefix)
        rel = text.filepath.replace("\\", "/")
        if rel.startswith("//"):
            abs_path = os.path.normpath(os.path.join(blend_dir, rel[2:]))
        else:
            abs_path = os.path.normpath(rel)

        if not os.path.isfile(abs_path):
            print(f"SKIP {text.name}: file not found at {abs_path}")
            continue

        # Read disk content and overwrite the text block directly
        with open(abs_path, "r", encoding="utf-8") as f:
            disk_content = f.read()

        text.clear()
        text.write(disk_content)
        reloaded += 1
        print(f"Reloaded: {text.name}")

bpy.ops.wm.save_mainfile()
print(f"\nRefreshed {reloaded} text blocks and saved blend file.")
