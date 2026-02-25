import bpy
import math
import os

from bpy.app.handlers import persistent
from bpy.types import Panel, Operator, Menu
from bpy.props import BoolProperty, EnumProperty, StringProperty

bl_info = {
    "name": "LFS Tools",
    "author": "",
    "version": (3, 0),
    "blender": (2, 83, 0),
    "location": "View3D > Sidebar (N) > LFS Tools",
    "description": "LFS grid snapping and block library for Shift+A menu",
    "category": "3D View",
}

# -------------------------------------------------------
# LFS grid constants
# -------------------------------------------------------

GRID_XY = 0.0625        # 1/16 metre
GRID_Z = 0.25           # 1/4 metre
ROT_Z_STEP_DEG = 1.40625  # degrees (360/256)


# -------------------------------------------------------
# Snap functions
# -------------------------------------------------------

def snap_value(value, increment):
    return round(value / increment) * increment


def snap_rotation_z(rot_radians):
    deg = math.degrees(rot_radians)
    snapped_deg = round(deg / ROT_Z_STEP_DEG) * ROT_Z_STEP_DEG
    return math.radians(snapped_deg)


def enforce_transform(obj):
    obj.location.x = snap_value(obj.location.x, GRID_XY)
    obj.location.y = snap_value(obj.location.y, GRID_XY)
    obj.location.z = snap_value(obj.location.z, GRID_Z)

    obj.rotation_euler.x = 0.0
    obj.rotation_euler.y = 0.0
    obj.rotation_euler.z = snap_rotation_z(obj.rotation_euler.z)


def snap_handler(scene):
    for obj in bpy.context.selected_objects:
        if obj.mode == 'OBJECT':
            enforce_transform(obj)


# -------------------------------------------------------
# Library helpers (self-contained, mirrors lfs_library_loader.py)
# -------------------------------------------------------

_lib_loaded = False


def _get_library_path():
    blend_dir = os.path.dirname(bpy.data.filepath)
    return os.path.join(blend_dir, "data", "lfs_pieces_library.blend")


def _load_library():
    global _lib_loaded
    if _lib_loaded:
        return
    _lib_loaded = True
    lib_path = _get_library_path()
    if not os.path.isfile(lib_path):
        print(f"LFS Tools: Library not found: {lib_path}")
        return
    try:
        with bpy.data.libraries.load(lib_path, link=True) as (data_from, data_to):
            data_to.objects = list(data_from.objects)
        linked = sum(1 for o in bpy.data.objects if o.library is not None)
        print(f"LFS Tools: Linked {linked} objects from library")
    except Exception as e:
        print(f"LFS Tools: Failed to link library: {e}")


def _get_all_library_names():
    lib_path = _get_library_path()
    if not os.path.isfile(lib_path):
        return []
    try:
        with bpy.data.libraries.load(lib_path) as (data_from, _):
            return list(data_from.objects)
    except Exception:
        return []


def _ensure_object(name):
    if name in bpy.data.objects:
        return True
    _load_library()
    return name in bpy.data.objects


# -------------------------------------------------------
# Catalog: category -> [object names]
# -------------------------------------------------------

_LFS_CATEGORIES = [
    ("Armco",           lambda n: n.startswith("Armco")),
    ("Bale",            lambda n: n == "Bale"),
    ("Banner",          lambda n: n.startswith("Banner")),
    ("Barrier",         lambda n: n.startswith("Barrier") or n.startswith("Railing")),
    ("Bin1",            lambda n: n.startswith("Bin1")),
    ("Bin2",            lambda n: n.startswith("Bin2")),
    ("Chalk",           lambda n: n.startswith("Chalk")),
    ("Cone",            lambda n: n.startswith("Cone")),
    ("Control",         lambda n: n.split(".")[0] in (
        "Checkpoint", "FinishLine", "RouteChecker",
        "StartPosition", "StartPosition1", "PitStopBox", "AutocrossObject")),
    ("Kerb",            lambda n: n.startswith("Kerb_")),
    ("Letter Board",    lambda n: n.startswith("Letter_Board")),
    ("Marker Corner",   lambda n: n.startswith("Marker_Corner")),
    ("Marker Distance", lambda n: n.startswith("Marker_Distance")),
    ("Marquee",         lambda n: n.startswith("Marquee")),
    ("Paint Arrow",     lambda n: n.startswith("Paint_Arrow")),
    ("Paint Letters",   lambda n: n.startswith("Paint_Letters")),
    ("Pillar",          lambda n: n.startswith("Pillar_")),
    ("Post",            lambda n: n.startswith("Post_")),
    ("Ramp",            lambda n: n.startswith("Ramp_") and not n.startswith("RampWall")),
    ("Ramp Wall",       lambda n: n.startswith("RampWall_")),
    ("Short Slab Wall", lambda n: n.startswith("ShortSlabWall_")),
    ("Sign",            lambda n: n.startswith("Sign_") or n.startswith("Chevron")),
    ("Slab",            lambda n: n.startswith("Slab_") and not n.startswith("SlabWall")),
    ("Slab Wall",       lambda n: n.startswith("SlabWall_")),
    ("Speedhump",       lambda n: n.startswith("SpeedHump")),
    ("Tyre",            lambda n: n.startswith("Tyre")),
    ("Vehicles",        lambda n: n.split(".")[0] in (
        "SUV", "Van", "Truck", "Ambulance")),
    ("Wall",            lambda n: n.startswith("Wall_")),
    ("Wedge",           lambda n: n.startswith("Wedge_")),
]

_catalog_cache = None


def _get_catalog():
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache

    all_names = _get_all_library_names()
    if not all_names:
        return {}

    catalog = {cat: [] for cat, _ in _LFS_CATEGORIES}
    for name in all_names:
        for cat, match_fn in _LFS_CATEGORIES:
            if match_fn(name):
                catalog[cat].append(name)
                break

    _catalog_cache = {k: sorted(v, key=_natural_sort_key) for k, v in catalog.items() if v}
    return _catalog_cache


# -------------------------------------------------------
# Subcategory grouping rules
# -------------------------------------------------------

def _format_size(val_str):
    """'025' -> '2.5', '050' -> '5', '100' -> '10'"""
    try:
        return f"{int(val_str) / 10:g}"
    except ValueError:
        return val_str


def _group_pillar(name):
    """Pillar_100_075_200 -> '10x7.5'"""
    parts = name.split(".")[0].split("_")
    if len(parts) >= 3:
        return f"{_format_size(parts[1])}x{_format_size(parts[2])}"
    return None


def _group_by_dims(name):
    """Slab_4_2_06 or Ramp_4_2_025 -> '4x2'"""
    parts = name.split(".")[0].split("_")
    if len(parts) >= 3:
        return f"{parts[1]}x{parts[2]}"
    return None


def _group_by_colour(name):
    """Wall_2_025_Blue -> 'Blue'"""
    parts = name.split(".")[0].split("_")
    if len(parts) >= 2:
        last = parts[-1]
        if last in ("Grey", "Blue", "Red", "Yellow", "White", "Green",
                     "Orange", "Black"):
            return last
    return None


# Categories that get sub-grouped (only applied when > 30 objects)
_SUBCATEGORY_RULES = {
    "Pillar":          _group_pillar,
    "Slab":            _group_by_dims,
    "Ramp":            _group_by_dims,
    "Wall":            _group_by_colour,
    "Slab Wall":       _group_by_colour,
    "Ramp Wall":       _group_by_colour,
    "Short Slab Wall": _group_by_colour,
    "Wedge":           _group_by_colour,
}

_subcatalog_cache = None


def _get_subcatalog():
    """Return {cat_name: {sub_key: [obj_names]}} for grouped categories."""
    global _subcatalog_cache
    if _subcatalog_cache is not None:
        return _subcatalog_cache

    catalog = _get_catalog()
    subcatalog = {}

    for cat_name, obj_names in catalog.items():
        group_fn = _SUBCATEGORY_RULES.get(cat_name)
        if group_fn and len(obj_names) > 30:
            groups = {}
            for name in obj_names:
                key = group_fn(name)
                if key is None:
                    key = "Other"
                groups.setdefault(key, []).append(name)
            subcatalog[cat_name] = {k: sorted(v, key=_natural_sort_key) for k, v in groups.items()}

    _subcatalog_cache = subcatalog
    return _subcatalog_cache


# -------------------------------------------------------
# File load handler
# -------------------------------------------------------

def _deferred_init():
    """Timer callback: preload catalog and register dynamic menus after file is open."""
    if not bpy.data.filepath:
        return None  # file not open yet, don't retry
    _register_dynamic_menus()
    return None  # one-shot, don't repeat


@persistent
def _on_file_load(dummy):
    global _lib_loaded, _catalog_cache, _subcatalog_cache, _menus_registered

    # Reset library/catalog caches for new file
    _lib_loaded = False
    _catalog_cache = None
    _subcatalog_cache = None

    # Unregister dynamic menus
    for cls in reversed(_dynamic_menus):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    _dynamic_menus.clear()
    _menus_registered = False

    # Rebuild for the new file
    _register_dynamic_menus()

    # Re-register snap handler
    handlers = bpy.app.handlers.depsgraph_update_post
    if snap_handler not in handlers:
        handlers.append(snap_handler)


# -------------------------------------------------------
# Operator: Toggle Snap
# -------------------------------------------------------

class LFS_SNAP_OT_toggle(Operator):
    bl_idname = "lfs_snap.toggle"
    bl_label = "Toggle LFS Snapping"
    bl_description = "Enable or disable LFS grid snapping for selected objects"

    def execute(self, context):
        handlers = bpy.app.handlers.depsgraph_update_post
        if snap_handler in handlers:
            handlers.remove(snap_handler)
            context.scene.lfs_snap_enabled = False
            self.report({'INFO'}, "LFS Snapping disabled")
        else:
            handlers.append(snap_handler)
            context.scene.lfs_snap_enabled = True
            self.report({'INFO'}, "LFS Snapping enabled")
        return {'FINISHED'}


# -------------------------------------------------------
# Operator: Toggle LFS Blocks Menu
# -------------------------------------------------------

class LFS_OT_toggle_blocks_menu(Operator):
    bl_idname = "lfs.toggle_blocks_menu"
    bl_label = "Toggle LFS Blocks in Add Menu"
    bl_description = "Show or hide LFS blocks in the Shift+A add menu"

    def execute(self, context):
        context.scene.lfs_blocks_menu_enabled = not context.scene.lfs_blocks_menu_enabled
        enabled = context.scene.lfs_blocks_menu_enabled
        self.report({'INFO'}, f"LFS Blocks menu {'enabled' if enabled else 'disabled'}")
        return {'FINISHED'}


# -------------------------------------------------------
# Operator: Toggle Blender Primitives Menu
# -------------------------------------------------------

class LFS_OT_toggle_primitives_menu(Operator):
    bl_idname = "lfs.toggle_primitives_menu"
    bl_label = "Toggle Blender Primitives in Add Menu"
    bl_description = "Show or hide default Blender primitives (Mesh, Curve, etc.) in the Shift+A add menu"

    def execute(self, context):
        context.scene.lfs_primitives_menu_enabled = not context.scene.lfs_primitives_menu_enabled
        enabled = context.scene.lfs_primitives_menu_enabled
        self.report({'INFO'}, f"Blender primitives {'shown' if enabled else 'hidden'}")
        return {'FINISHED'}


# -------------------------------------------------------
# Operator: Add LFS Piece (with parametric F9 panel)
# -------------------------------------------------------

# Enum items for parametric properties (from lfs_lyt_common.py)
_WIDTHS = [2, 4, 8, 16]
_LENGTHS = [2, 4, 8, 16]
_SIZES = [25, 50, 75, 100]
_HEIGHTS = [25, 50, 75, 100, 125, 150, 175, 200,
            225, 250, 275, 300, 325, 350, 375, 400]
_PITCHES = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 90]
_ANGLES = [56, 113, 169, 225, 281, 338, 394, 450,
           506, 563, 619, 675, 731, 788, 844, 900]
_COLOURS = ["Grey", "Red", "Blue", "Yellow"]

_E_WIDTH = [(str(v), str(v), "") for v in _WIDTHS]
_E_LENGTH = [(str(v), str(v), "") for v in _LENGTHS]
_E_SIZE = [(f"{v:03d}", f"{v/10:g}", "") for v in _SIZES]
_E_HEIGHT = [(f"{v:03d}", f"{v/10:g}", "") for v in _HEIGHTS]
_E_PITCH = [(f"{v:02d}", f"{v}\u00b0", "") for v in _PITCHES]
_E_ANGLE = [(f"{v:03d}", f"{v/10:g}\u00b0", "") for v in _ANGLES]
_E_COLOUR = [(c, c, "") for c in _COLOURS]

# Schemas: (prefix, [param_names], format_string)
# Checked in order; longer prefixes first to avoid false matches.
_PIECE_SCHEMAS = [
    ("ShortSlabWall_", ["param_sizey", "param_pitch", "param_colour"],
     "ShortSlabWall_{param_sizey}_{param_pitch}_{param_colour}"),
    ("SlabWall_",      ["param_length", "param_pitch", "param_colour"],
     "SlabWall_{param_length}_{param_pitch}_{param_colour}"),
    ("RampWall_",      ["param_length", "param_height", "param_colour"],
     "RampWall_{param_length}_{param_height}_{param_colour}"),
    ("Pillar_",        ["param_sizex", "param_sizey", "param_height"],
     "Pillar_{param_sizex}_{param_sizey}_{param_height}"),
    ("Slab_",          ["param_width", "param_length", "param_pitch"],
     "Slab_{param_width}_{param_length}_{param_pitch}"),
    ("Ramp_",          ["param_width", "param_length", "param_height"],
     "Ramp_{param_width}_{param_length}_{param_height}"),
    ("Wall_",          ["param_length", "param_height", "param_colour"],
     "Wall_{param_length}_{param_height}_{param_colour}"),
    ("Wedge_",         ["param_length", "param_angle", "param_colour"],
     "Wedge_{param_length}_{param_angle}_{param_colour}"),
]

def _next_unique_name(base_name):
    """Find the lowest available 5-digit suffix for this base_name type."""
    used = set()
    prefix = base_name + "."
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix):
            suffix = obj.name[len(prefix):]
            if len(suffix) == 5 and suffix.isdigit():
                used.add(int(suffix))
    n = 1
    while n in used:
        n += 1
    return f"{base_name}.{n:05d}"


def _find_schema(name):
    """Return (prefix, params, fmt) for name, or None."""
    base = name.split(".")[0]
    for prefix, params, fmt in _PIECE_SCHEMAS:
        if base.startswith(prefix):
            return prefix, params, fmt
    return None


class LFS_OT_add_piece(Operator):
    bl_idname = "lfs.add_piece"
    bl_label = "Add LFS Piece"
    bl_description = "Add an LFS piece from the library at the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}

    piece_name: StringProperty(name="Piece Name")

    # Parametric properties (only relevant ones shown per piece type)
    param_width:  EnumProperty(items=_E_WIDTH,  name="Width")
    param_length: EnumProperty(items=_E_LENGTH, name="Length")
    param_sizex:  EnumProperty(items=_E_SIZE,   name="Size X")
    param_sizey:  EnumProperty(items=_E_SIZE,   name="Size Y")
    param_height: EnumProperty(items=_E_HEIGHT, name="Height")
    param_pitch:  EnumProperty(items=_E_PITCH,  name="Pitch")
    param_angle:  EnumProperty(items=_E_ANGLE,  name="Angle")
    param_colour: EnumProperty(items=_E_COLOUR, name="Colour")

    def invoke(self, context, event):
        """Parse piece_name into parameter properties on first call."""
        schema = _find_schema(self.piece_name)
        if schema:
            prefix, params, _fmt = schema
            base = self.piece_name.split(".")[0]
            parts = base[len(prefix):].split("_")
            for i, param in enumerate(params):
                if i < len(parts):
                    try:
                        setattr(self, param, parts[i])
                    except TypeError:
                        pass
        return self.execute(context)

    def execute(self, context):
        # Build piece name from parameters if schema exists
        schema = _find_schema(self.piece_name)
        if schema:
            _prefix, params, fmt = schema
            values = {p: getattr(self, p) for p in params}
            name = fmt.format(**values)
        else:
            name = self.piece_name

        if not _ensure_object(name):
            self.report({'ERROR'}, f"Piece '{name}' not found in library")
            return {'CANCELLED'}

        src = bpy.data.objects[name]
        new_obj = src.copy()
        new_obj.name = _next_unique_name(name)
        new_obj.location = context.scene.cursor.location

        context.collection.objects.link(new_obj)

        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj

        # Update displayed piece name
        self.piece_name = name

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.label(text=self.piece_name)
        schema = _find_schema(self.piece_name)
        if schema:
            _prefix, params, _fmt = schema
            for param in params:
                layout.prop(self, param)


# -------------------------------------------------------
# Dynamic menus for Shift+A
# -------------------------------------------------------

_dynamic_menus = []
_menus_registered = False


def _sanitize_idname(name):
    """Convert a display name to a valid bl_idname component."""
    return ''.join(c if c.isalnum() or c == '_' else '_'
                   for c in name.replace(" ", "_").lower())


import re

_NUM_RE = re.compile(r'(\d+\.?\d*)')


def _natural_sort_key(s):
    """Sort key that orders numbers numerically: '2.5' < '5' < '10'."""
    parts = _NUM_RE.split(s)
    result = []
    for part in parts:
        try:
            result.append(float(part))
        except ValueError:
            result.append(part.lower())
    return result


def _make_flat_draw_func(cat_name):
    """Draw function for categories without sub-groups (flat object list)."""
    def draw(self, context):
        layout = self.layout
        catalog = _get_catalog()
        for obj_name in catalog.get(cat_name, []):
            op = layout.operator("lfs.add_piece", text=obj_name)
            op.piece_name = obj_name
    return draw


def _make_grouped_draw_func(cat_name, cat_safe):
    """Draw function for categories with sub-groups (shows sub-menus)."""
    def draw(self, context):
        layout = self.layout
        subcatalog = _get_subcatalog()
        groups = subcatalog.get(cat_name, {})
        for sub_key in sorted(groups.keys(), key=_natural_sort_key):
            sub_safe = _sanitize_idname(sub_key)
            layout.menu(f"LFS_MT_sub_{cat_safe}_{sub_safe}",
                        text=sub_key, icon='MESH_CUBE')
    return draw


def _make_sub_draw_func(cat_name, sub_key):
    """Draw function for a specific sub-group (flat object list)."""
    def draw(self, context):
        layout = self.layout
        subcatalog = _get_subcatalog()
        for obj_name in subcatalog.get(cat_name, {}).get(sub_key, []):
            op = layout.operator("lfs.add_piece", text=obj_name)
            op.piece_name = obj_name
    return draw


def _register_dynamic_menus():
    global _menus_registered
    if _menus_registered:
        return

    catalog = _get_catalog()
    if not catalog:
        return

    subcatalog = _get_subcatalog()

    for cat_name in sorted(catalog.keys()):
        cat_safe = _sanitize_idname(cat_name)
        cat_idname = f"LFS_MT_cat_{cat_safe}"

        if cat_name in subcatalog:
            # Register sub-group menus first
            for sub_key in sorted(subcatalog[cat_name].keys(), key=_natural_sort_key):
                sub_safe = _sanitize_idname(sub_key)
                sub_idname = f"LFS_MT_sub_{cat_safe}_{sub_safe}"
                sub_cls = type(
                    sub_idname, (Menu,),
                    {
                        "bl_idname": sub_idname,
                        "bl_label": sub_key,
                        "draw": _make_sub_draw_func(cat_name, sub_key),
                    }
                )
                bpy.utils.register_class(sub_cls)
                _dynamic_menus.append(sub_cls)

            # Category menu shows sub-group menus
            draw_fn = _make_grouped_draw_func(cat_name, cat_safe)
        else:
            # Flat list
            draw_fn = _make_flat_draw_func(cat_name)

        cat_cls = type(
            cat_idname, (Menu,),
            {
                "bl_idname": cat_idname,
                "bl_label": cat_name,
                "draw": draw_fn,
            }
        )
        bpy.utils.register_class(cat_cls)
        _dynamic_menus.append(cat_cls)

    _menus_registered = True


class LFS_MT_add_blocks(Menu):
    bl_idname = "LFS_MT_add_blocks"
    bl_label = "LFS Blocks"

    def draw(self, context):
        layout = self.layout
        catalog = _get_catalog()
        if not catalog:
            layout.label(text="Library not found", icon='ERROR')
            return
        for cat_name in sorted(catalog.keys()):
            safe = _sanitize_idname(cat_name)
            layout.menu(f"LFS_MT_cat_{safe}", text=cat_name, icon='MESH_CUBE')


_original_add_draw = None


def _custom_add_draw(self, context):
    """Replacement for VIEW3D_MT_add.draw that respects both toggle properties."""
    if context.scene.lfs_blocks_menu_enabled:
        self.layout.menu("LFS_MT_add_blocks", icon='OUTLINER_COLLECTION')
        self.layout.separator()
    if context.scene.lfs_primitives_menu_enabled and _original_add_draw is not None:
        _original_add_draw(self, context)


# -------------------------------------------------------
# Panel
# -------------------------------------------------------

class LFS_PT_tools(Panel):
    bl_label = "LFS Tool Settings"
    bl_idname = "LFS_PT_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "LFS Tools"

    def draw(self, context):
        layout = self.layout

        # Snap toggle
        enabled = context.scene.lfs_snap_enabled
        row = layout.row()
        row.operator("lfs_snap.toggle",
                     text="Enable Snapping",
                     icon='SNAP_ON' if enabled else 'SNAP_OFF',
                     depress=enabled)

        box = layout.box()
        box.label(text=f"XY grid: {GRID_XY} m")
        box.label(text=f"Z grid:  {GRID_Z} m")
        box.label(text=f"Rotation step: {ROT_Z_STEP_DEG:.5f}\u00b0")

        layout.separator()

        # LFS Pieces menu toggle
        blocks_on = context.scene.lfs_blocks_menu_enabled
        row = layout.row()
        row.operator("lfs.toggle_blocks_menu",
                     text="Show LFS Pieces",
                     icon='HIDE_OFF' if blocks_on else 'HIDE_ON',
                     depress=blocks_on)

        # Blender primitives menu toggle
        prims_on = context.scene.lfs_primitives_menu_enabled
        row = layout.row()
        row.operator("lfs.toggle_primitives_menu",
                     text="Show Blender Primitives",
                     icon='HIDE_OFF' if prims_on else 'HIDE_ON',
                     depress=prims_on)


# -------------------------------------------------------
# Registration
# -------------------------------------------------------

_static_classes = (
    LFS_SNAP_OT_toggle,
    LFS_OT_toggle_blocks_menu,
    LFS_OT_toggle_primitives_menu,
    LFS_OT_add_piece,
    LFS_MT_add_blocks,
    LFS_PT_tools,
)


def register():
    for cls in _static_classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.lfs_snap_enabled = BoolProperty(
        name="LFS Snap Enabled",
        default=True,
    )
    bpy.types.Scene.lfs_blocks_menu_enabled = BoolProperty(
        name="LFS Blocks Menu Enabled",
        default=True,
    )
    bpy.types.Scene.lfs_primitives_menu_enabled = BoolProperty(
        name="Blender Primitives Menu Enabled",
        default=True,
    )

    # Auto-activate snapping on register
    handlers = bpy.app.handlers.depsgraph_update_post
    if snap_handler not in handlers:
        handlers.append(snap_handler)
    bpy.app.handlers.load_post.append(_on_file_load)

    # Replace Shift+A menu draw with our custom version
    global _original_add_draw
    _original_add_draw = bpy.types.VIEW3D_MT_add.draw
    bpy.types.VIEW3D_MT_add.draw = _custom_add_draw

    # Deferred init: preload catalog and register dynamic menus after Blender is ready
    bpy.app.timers.register(_deferred_init, first_interval=0.5)


def unregister():
    # Restore original Shift+A menu draw
    global _original_add_draw
    if _original_add_draw is not None:
        bpy.types.VIEW3D_MT_add.draw = _original_add_draw
        _original_add_draw = None

    # Unregister dynamic menus
    global _menus_registered, _catalog_cache, _subcatalog_cache
    for cls in reversed(_dynamic_menus):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    _dynamic_menus.clear()
    _menus_registered = False
    _catalog_cache = None
    _subcatalog_cache = None

    if _on_file_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_file_load)
    handlers = bpy.app.handlers.depsgraph_update_post
    if snap_handler in handlers:
        handlers.remove(snap_handler)

    for cls in reversed(_static_classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.lfs_snap_enabled
    del bpy.types.Scene.lfs_blocks_menu_enabled
    del bpy.types.Scene.lfs_primitives_menu_enabled


if __name__ == "__main__":
    register()
