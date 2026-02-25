"""
First-time setup - creates config.ini if it doesn't exist.

Usage:
    python run_first_time.py
"""

import configparser
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.ini")

DEFAULTS = {
    "path": "C:/LFS",
    "map_name": "LA1",
    "track_name": "V8",
}


def main():
    if os.path.isfile(CONFIG_PATH):
        print(f"config.ini already exists at {CONFIG_PATH}")
        answer = input("Overwrite? [y/N]: ").strip().lower()
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    config = configparser.ConfigParser()
    config["LFS"] = {}

    print()
    print("=== LFS Layout Editor Setup ===")
    print()

    for key, default in DEFAULTS.items():
        value = input(f"  {key} [{default}]: ").strip()
        config["LFS"][key] = value if value else default

    with open(CONFIG_PATH, "w") as f:
        config.write(f)

    print()
    print(f"Config saved to {CONFIG_PATH}")


if __name__ == "__main__":
    main()
