"""
Run all Blender headless tests.

Usage:
    python tests/run_tests.py
"""

import subprocess
import shutil
import sys
import os
import re

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLEND_FILE = os.path.join(REPO_DIR, "lyt_editor.blend")

TESTS = [
    os.path.join(REPO_DIR, "tests", "test_blend_scripts.py"),
    os.path.join(REPO_DIR, "tests", "test_export_import_roundtrip.py"),
]


def find_blender():
    # Prefer newest installed version from Program Files
    for base in [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Blender Foundation"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Blender Foundation"),
    ]:
        if not os.path.isdir(base):
            continue
        def version_key(name):
            m = re.search(r"(\d+)\.(\d+)", name)
            return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

        versions = sorted(os.listdir(base), key=version_key, reverse=True)
        for v in versions:
            exe = os.path.join(base, v, "blender.exe")
            if os.path.isfile(exe):
                return exe

    # Fall back to PATH
    return shutil.which("blender")


def main():
    blender = find_blender()
    if not blender:
        print("ERROR: blender not found on PATH or in Program Files")
        sys.exit(1)

    print(f"Using Blender: {blender}")
    print()

    failed = 0
    for test in TESTS:
        name = os.path.relpath(test, REPO_DIR)
        print(f"--- {name} ---")
        result = subprocess.run(
            [blender, "--background", BLEND_FILE, "--python", test],
            cwd=REPO_DIR,
        )
        if result.returncode != 0:
            failed += 1
        print()

    if failed:
        print(f"FAILED: {failed}/{len(TESTS)} test(s)")
        sys.exit(1)
    else:
        print(f"ALL PASSED: {len(TESTS)} test(s)")
        sys.exit(0)


if __name__ == "__main__":
    main()
