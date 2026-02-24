# BlenderLFSLayoutEditor

A Live for Speed layout editor tool for Blender 4.0+.

## First-time setup

Before using the editor, create a `config.ini` file with your LFS installation path.

You can either run the interactive setup script:

```bash
python run_first_time.py
```

Or create `config.ini` manually in the project root:

```ini
[LFS]
path = C:/LFS
map_name = LA1
track_name = V8
```

`config.ini` is gitignored since it contains local paths.

## Usage

Open `lyt_editor.blend` in Blender 4.0+.

The Python scripts live in the `scripts/` folder and are linked (not embedded) in the blend file. This means you can edit them in any external editor.

After editing a script externally, reload it inside Blender's text editor with **Alt+R** (Text > Reload).

## Scripts

| Script | Description |
| ------ | ----------- |
| `duplicate_along_curve.py` | Duplicate objects along a curve without deformation |
| `lfs_lyt_export.py` | Export Blender scene to LFS .lyt layout file |
| `lfs_lyt_import.py` | Import LFS .lyt layout file into Blender |
| `lfs_normalize_object.py` | Snap object positions/rotations to LFS grid |
| `lfs_object_to_block.py` | Spawn placeholder cubes from .lyt data |
| `lfs_text_builder.py` | Build LFS text objects (paint letters / letter boards) |

## Testing

Run the headless validation tests:

```bash
python tests/run_tests.py
```

This verifies all scripts are correctly linked in the blend file, match their files on disk, and compile without errors.

## Changelog

### v21.0

- Extracted all Python scripts from the blend file into `scripts/` as standalone files
- Renamed scripts to snake_case naming convention
- Blend file now links external scripts via relative paths (`//scripts/...`)
- Moved LFS path, map name, and track name configuration to `config.ini`
- Added `run_first_time.py` for interactive first-time setup
- Added `.gitignore` for blend backups and config
- Added headless test suite (`tests/run_tests.py`, `tests/test_blend_scripts.py`)
- Renamed blend file to version-less `lyt_editor.blend`

### v20.9

- Initial public release with all scripts embedded in the blend file
