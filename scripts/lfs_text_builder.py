import bpy
import os
import sys
import re
import math
from mathutils import Vector

from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import (
    FloatProperty,
    StringProperty,
    EnumProperty,
    BoolProperty,
    PointerProperty,
)

# Ensure scripts/ is on sys.path so lfs_library_loader can be imported
_scripts_dir = os.path.join(os.path.dirname(bpy.data.filepath), "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

bl_info = {
    "name": "LFS Text Builder",
    "author": "",
    "version": (1, 3, 13),
    "blender": (2, 83, 0),
    "location": "View3D > Sidebar (N) > Dup Along Cur > LFS Text Builder",
    "description": "Build LFS text objects (Paint Letters / Letter Board) by auto-detecting glyph meshes in the .blend",
    "category": "3D View",
}

# LFS 0.8A indices
AXO_PAINT_LETTERS = 16
AXO_LETTER_BOARD_WY = 92
AXO_LETTER_BOARD_RB = 93

# Mapping m_num (0..48)
GLYPH_TO_MNUM = {}
for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    GLYPH_TO_MNUM[ch] = i

GLYPH_TO_MNUM.update({
    "LEFT": 26,
    "RIGHT": 27,
    "UP": 28,
    "DOWN": 29,
    "HASH": 30,
    "AT": 31,
})

for i in range(10):
    GLYPH_TO_MNUM[str(i)] = 32 + i

GLYPH_TO_MNUM.update({
    "DOT": 42,
    "COLON": 43,
    "SLASH": 44,
    "LPAREN": 45,
    "RPAREN": 46,
    "AMP": 47,
    "BLANK": 48,
})

CHAR_TO_TOKEN = {
    ".": "DOT",
    ":": "COLON",
    "/": "SLASH",
    "(": "LPAREN",
    ")": "RPAREN",
    "&": "AMP",
    "#": "HASH",
    "@": "AT",
}

MULTI_TOKENS = {
    "<": "LEFT",
    ">": "RIGHT",
    "^": "UP",
    "v": "DOWN",
}

# Mode -> (family, colour_name, axo_index, colour_bit)
MODE_INFO = {
    "PAINT_WHITE": ("PAINT", "WHITE", AXO_PAINT_LETTERS, 0),
    "PAINT_YELLOW": ("PAINT", "YELLOW", AXO_PAINT_LETTERS, 1),

    "BOARD_WHITE": ("BOARD", "WHITE", AXO_LETTER_BOARD_WY, 0),
    "BOARD_YELLOW": ("BOARD", "YELLOW", AXO_LETTER_BOARD_WY, 1),

    "BOARD_RED": ("BOARD", "RED", AXO_LETTER_BOARD_RB, 0),
    "BOARD_BLUE": ("BOARD", "BLUE", AXO_LETTER_BOARD_RB, 1),
}

def _find_or_create_collection(name: str) -> bpy.types.Collection:
    coll = bpy.data.collections.get(name)
    if coll:
        return coll
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll

def _base_name(name: str) -> str:
    return name.split(".", 1)[0]

def _token_from_char(ch: str) -> str:
    if ch in MULTI_TOKENS:
        return MULTI_TOKENS[ch]
    return CHAR_TO_TOKEN.get(ch, ch)

def _flags_for_letter(m_num: int, colour_bit: int) -> int:
    return ((m_num & 0x3F) << 1) | (colour_bit & 0x01)

def _apply_floating_bit(flags: int, enable: bool) -> int:
    if enable:
        return flags | 0x80
    return flags & 0x7F

def _safe_move_to_collection(obj: bpy.types.Object, target_coll: bpy.types.Collection):
    if obj.name not in target_coll.objects:
        target_coll.objects.link(obj)
    for c in list(obj.users_collection):
        if c != target_coll:
            c.objects.unlink(obj)

def _build_library_lookup_from_scene(family: str, colour_name: str):
    out = {}
    fam_u = family.upper()
    col_u = colour_name.upper()

    def family_ok(name_u: str) -> bool:
        if fam_u == "PAINT":
            return "PAINT" in name_u
        return ("LETTER" in name_u) or ("BOARD" in name_u)

    def colour_ok(name_u: str) -> bool:
        return col_u in name_u

    digit_aliases = {
        "0": ["0", "ZERO", "NUM0"],
        "1": ["1", "ONE", "NUM1"],
        "2": ["2", "TWO", "NUM2"],
        "3": ["3", "THREE", "NUM3"],
        "4": ["4", "FOUR", "NUM4"],
        "5": ["5", "FIVE", "NUM5"],
        "6": ["6", "SIX", "NUM6"],
        "7": ["7", "SEVEN", "NUM7"],
        "8": ["8", "EIGHT", "NUM8"],
        "9": ["9", "NINE", "NUM9"],
    }

    def score_match(base_name: str, candidates):
        bn_up = base_name.upper()

        if bn_up in candidates:
            return 3

        for cand in candidates:
            if re.search(rf"(^|_){re.escape(cand)}(_|$)", base_name, flags=re.IGNORECASE):
                return 2

        for cand in candidates:
            if cand.isdigit():
                if bn_up.endswith(cand) and (len(bn_up) == 1 or not bn_up[-2].isdigit()):
                    return 1

        return 0

    tokens = list(GLYPH_TO_MNUM.keys())
    best = {t: (0, None) for t in tokens}

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        name_u = obj.name.upper()
        if not family_ok(name_u):
            continue
        if not colour_ok(name_u):
            continue

        bn = _base_name(obj.name)

        for token in tokens:
            candidates = digit_aliases.get(token, [token])
            s = score_match(bn, candidates)
            if s > best[token][0]:
                best[token] = (s, obj)

    # If not all tokens found locally, also search external library
    missing_tokens = [t for t, (s, _obj) in best.items() if s == 0]
    if missing_tokens:
        try:
            from lfs_library_loader import get_all_objects_by_pattern
            lib_objects = get_all_objects_by_pattern(family_ok, colour_ok)
            for obj in lib_objects:
                if obj.type != "MESH":
                    continue
                bn = _base_name(obj.name)
                for token in tokens:
                    candidates = digit_aliases.get(token, [token])
                    s = score_match(bn, candidates)
                    if s > best[token][0]:
                        best[token] = (s, obj)
        except ImportError:
            pass  # Library loader not available (older setup)

    for token, (s, obj) in best.items():
        if obj is not None and s > 0:
            out[token] = obj

    return out

def _get_source_text(props) -> str:
    if props.use_text_block and props.text_block is not None:
        return props.text_block.as_string()
    return props.text or ""

def _mesh_min_local_z(obj: bpy.types.Object) -> float:
    if not obj or obj.type != "MESH":
        return 0.0
    return min(v[2] for v in obj.bound_box)

def _bottom_to_origin_offset_world(obj: bpy.types.Object) -> float:
    minz_local = _mesh_min_local_z(obj)
    return (-minz_local) * float(obj.scale.z)

# --- NEW: real geometric X bounds (for touching / constant gap) ---
def _mesh_min_local_x(obj: bpy.types.Object) -> float:
    if not obj or obj.type != "MESH":
        return 0.0
    return min(v[0] for v in obj.bound_box)

def _mesh_max_local_x(obj: bpy.types.Object) -> float:
    if not obj or obj.type != "MESH":
        return 0.0
    return max(v[0] for v in obj.bound_box)

def _glyph_x_bounds_world(obj: bpy.types.Object):
    minx = _mesh_min_local_x(obj) * float(obj.scale.x)
    maxx = _mesh_max_local_x(obj) * float(obj.scale.x)
    return (minx, maxx)

class LFS_TextProps(PropertyGroup):
    text: StringProperty(
        name="Text (quick)",
        description="Quick text (single-line UI, but you can paste newlines)",
        default="HELLO",
        options={'TEXTEDIT_UPDATE'},
    )

    use_text_block: BoolProperty(
        name="Use Text Datablock",
        description="Use a Blender Text datablock for true multi-line editing",
        default=True
    )

    text_block: PointerProperty(
        name="Text Block",
        description="Blender Text datablock containing your multi-line text",
        type=bpy.types.Text
    )

    mode: EnumProperty(
        name="Mode",
        items=[
            ("PAINT_WHITE", "Paint Letters - White", "Paint letters white"),
            ("PAINT_YELLOW", "Paint Letters - Yellow", "Paint letters yellow"),
            ("BOARD_WHITE", "Letter Board - White", "Letter board white"),
            ("BOARD_YELLOW", "Letter Board - Yellow", "Letter board yellow"),
            ("BOARD_RED", "Letter Board - Red", "Letter board red"),
            ("BOARD_BLUE", "Letter Board - Blue", "Letter board blue"),
        ],
        default="PAINT_WHITE"
    )

    letter_spacing: FloatProperty(
        name="Letter Gap",
        description="Gap between glyphs in Blender units. 0 = touch by geometry",
        default=0.0,
        min=0.0,
        soft_max=5.0
    )

    line_spacing: FloatProperty(
        name="Line Spacing",
        description="Line spacing in Blender units (PAINT: Y, BOARD: Z)",
        default=1.2,
        min=0.01,
        soft_max=10.0
    )

    space_advance: FloatProperty(
        name="Space Width",
        description="Advance for spaces in Blender units",
        default=1.0,
        min=0.0,
        soft_max=10.0
    )

    use_active_as_origin: BoolProperty(
        name="Use Active as Origin",
        description="If enabled, starts at active object location, else uses 3D cursor location",
        default=True
    )

    clear_previous: BoolProperty(
        name="Clear Previous Output",
        description="Delete previous objects in the output collection before building",
        default=True
    )

    output_collection_name: StringProperty(
        name="Output Collection",
        default="LFS_TEXT_OUT"
    )

    force_float_board: BoolProperty(
        name="Force Floating (Board)",
        description="Force floating flag (bit7) for letter boards so LFS respects Z height",
        default=True
    )

    board_ground_comp: BoolProperty(
        name="Board Ground Compensation",
        description="Add an automatic Z offset so the bottom of the board glyph sits on Z=0 (snapped to 0.25m)",
        default=True
    )

    board_lfs_lift: FloatProperty(
        name="Board LFS Lift",
        description="Extra Z lift for Letter Board in LFS (meters). Typical: 2.0",
        default=2.0,
        min=0.0,
        soft_max=10.0
    )

class LFS_TEXT_OT_build(Operator):
    bl_idname = "lfs_text.build"
    bl_label = "Build LFS Text"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.lfs_text_props

        out_coll = _find_or_create_collection(props.output_collection_name)

        if props.clear_previous:
            for o in list(out_coll.objects):
                bpy.data.objects.remove(o, do_unlink=True)

        if props.use_active_as_origin and context.active_object is not None:
            origin_loc = context.active_object.matrix_world.translation.copy()
        else:
            origin_loc = context.scene.cursor.location.copy()

        family, colour_name, axo_index, colour_bit = MODE_INFO[props.mode]
        lib_lookup = _build_library_lookup_from_scene(family, colour_name)

        if not lib_lookup:
            self.report({'ERROR'}, f"No glyphs found for {family} {colour_name}. Check object names in the .blend.")
            return {'CANCELLED'}

        raw_text = _get_source_text(props)
        text_up = (raw_text or "").replace("\r", "").upper()
        lines = text_up.split("\n")
        if not lines:
            lines = [""]

        is_board = (family.upper() == "BOARD")
        line_step = max(0.001, float(props.line_spacing))
        n_lines = len(lines)

        force_float = bool(props.force_float_board) and is_board

        created = 0

        # BOARD base Z: mesh-bottom comp + LFS pivot lift, both snapped to 0.25m
        board_base_z = 0.0
        if is_board:
            step = 0.25

            if props.board_ground_comp:
                any_glyph = next(iter(lib_lookup.values()), None)
                if any_glyph is not None:
                    raw = _bottom_to_origin_offset_world(any_glyph)
                    board_base_z += math.ceil(raw / step) * step

            board_base_z += math.ceil(float(props.board_lfs_lift) / step) * step

        for i_line, line in enumerate(lines):
            x_cursor = 0.0
            from_bottom = (n_lines - 1 - i_line) * line_step

            if is_board:
                per_line = Vector((0.0, 0.0, from_bottom + board_base_z))
            else:
                per_line = Vector((0.0, from_bottom, 0.0))

            for ch in line:
                if ch == " ":
                    x_cursor += float(props.space_advance)
                    continue

                token_u = str(_token_from_char(ch)).upper()
                m_num = GLYPH_TO_MNUM.get(token_u)
                if m_num is None:
                    continue

                src = lib_lookup.get(token_u)
                if src is None:
                    continue

                new_obj = src.copy()
                new_obj.data = src.data.copy()
                new_obj.animation_data_clear()

                # --- NEW: true geometric touching (min/max X) ---
                minx_w, maxx_w = _glyph_x_bounds_world(src)
                width_w = max(0.001, maxx_w - minx_w)
                gap = float(props.letter_spacing)

                # place so the left edge sits exactly on x_cursor
                x_place = x_cursor - minx_w
                new_obj.location = origin_loc + Vector((x_place, 0.0, 0.0)) + per_line

                new_obj.rotation_mode = src.rotation_mode
                if src.rotation_mode == 'QUATERNION':
                    new_obj.rotation_quaternion = src.rotation_quaternion.copy()
                elif src.rotation_mode == 'AXIS_ANGLE':
                    new_obj.rotation_axis_angle = src.rotation_axis_angle[:]
                else:
                    new_obj.rotation_euler = src.rotation_euler.copy()

                new_obj.scale = src.scale.copy()

                flags = _flags_for_letter(m_num, colour_bit)
                flags = _apply_floating_bit(flags, force_float)

                new_obj["Index"] = int(axo_index)
                new_obj["Flags"] = int(flags)

                new_obj.name = _base_name(src.name)
                _safe_move_to_collection(new_obj, out_coll)

                # advance to right edge + gap
                x_cursor += width_w + gap

                created += 1

        self.report({'INFO'}, f"Built {created} glyph objects in '{out_coll.name}'.")
        return {'FINISHED'}

class LFS_TEXT_PT_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Dup Along Cur"
    bl_idname = "LFS_TEXT_PT_panel"
    bl_label = "LFS Text Builder"

    def draw(self, context):
        layout = self.layout
        props = context.scene.lfs_text_props

        col = layout.column(align=True)
        col.prop(props, "mode")

        col.separator()
        col.label(text="Text Source")
        col.prop(props, "use_text_block")
        if props.use_text_block:
            col.template_ID(props, "text_block", new="text.new")
            if props.text_block is None:
                col.label(text="Create/select a Text datablock, then edit it in Text Editor.")
        else:
            col.prop(props, "text", text="")

        col.separator()
        col.label(text="Spacing")
        col.prop(props, "letter_spacing")
        col.prop(props, "line_spacing")
        col.prop(props, "space_advance")

        col.separator()
        col.label(text="Output")
        col.prop(props, "output_collection_name")
        col.prop(props, "clear_previous")
        col.prop(props, "use_active_as_origin")

        if props.mode.startswith("BOARD_"):
            col.separator()
            col.prop(props, "force_float_board")
            col.prop(props, "board_ground_comp")
            col.prop(props, "board_lfs_lift")

        col.separator()
        col.operator("lfs_text.build", icon='OUTLINER_OB_FONT')

classes = [
    LFS_TextProps,
    LFS_TEXT_OT_build,
    LFS_TEXT_PT_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lfs_text_props = PointerProperty(type=LFS_TextProps)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.lfs_text_props

if __name__ == "__main__":
    register()
