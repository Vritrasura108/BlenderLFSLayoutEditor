import bpy
import math

from bpy.app.handlers import persistent
from bpy.types import Panel, Operator
from bpy.props import BoolProperty

bl_info = {
    "name": "LFS Snap Handler",
    "author": "",
    "version": (2, 0),
    "blender": (2, 83, 0),
    "location": "View3D > Sidebar (N) > LFS Tools",
    "description": "Enforce LFS grid snapping on selected objects (location, rotation)",
    "category": "3D View",
}

# LFS grid constants
GRID_XY = 0.0625        # 1/16 metre
GRID_Z = 0.25           # 1/4 metre
ROT_Z_STEP_DEG = 1.40625  # degrees (360/256)


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


@persistent
def _on_file_load(dummy):
    """Re-register snap handler after file load (Blender clears non-persistent handlers)."""
    handlers = bpy.app.handlers.depsgraph_update_post
    if snap_handler not in handlers:
        handlers.append(snap_handler)


# -------------------------------------------------------
# Operator
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
# Panel
# -------------------------------------------------------

class LFS_SNAP_PT_panel(Panel):
    bl_label = "LFS Snap Handler"
    bl_idname = "LFS_SNAP_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "LFS Tools"

    def draw(self, context):
        layout = self.layout
        enabled = context.scene.lfs_snap_enabled

        row = layout.row()
        if enabled:
            row.operator("lfs_snap.toggle", text="Disable Snapping",
                         icon='SNAP_OFF', depress=True)
        else:
            row.operator("lfs_snap.toggle", text="Enable Snapping",
                         icon='SNAP_ON')

        box = layout.box()
        box.label(text=f"XY grid: {GRID_XY} m")
        box.label(text=f"Z grid:  {GRID_Z} m")
        box.label(text=f"Rotation step: {ROT_Z_STEP_DEG:.5f}\u00b0")


# -------------------------------------------------------
# Registration
# -------------------------------------------------------

classes = (
    LFS_SNAP_OT_toggle,
    LFS_SNAP_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lfs_snap_enabled = BoolProperty(
        name="LFS Snap Enabled",
        default=True,
    )
    # Auto-activate snapping on register
    handlers = bpy.app.handlers.depsgraph_update_post
    if snap_handler not in handlers:
        handlers.append(snap_handler)
    bpy.app.handlers.load_post.append(_on_file_load)


def unregister():
    if _on_file_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_file_load)
    handlers = bpy.app.handlers.depsgraph_update_post
    if snap_handler in handlers:
        handlers.remove(snap_handler)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.lfs_snap_enabled


if __name__ == "__main__":
    register()
