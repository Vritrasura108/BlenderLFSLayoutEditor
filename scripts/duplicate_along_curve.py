import bpy
from bpy.types import Panel, Operator

bl_info = {
    "name": "Duplicate Along Curve Without Deformation",
    "author": "",
    "version": (1, 2),
    "blender": (2, 83, 0),
    "location": "View3D > Side Panel > Dup Along Curve",
    "description": "duplicate along curve without distortion",
    "warning": "",
    "doc_url": "https://blendermarket.com/creators/learnasimakeit",
}


def Update_Duplicate_Distance(self, context):
    dis = context.scene.duplicated_obj_props.rigid_distance
    mods = context.active_object.modifiers

    for m in mods:
        if m.name == 'array rigid' and m.type == 'ARRAY':
            m.constant_offset_displace[0] = dis

    return


def Update_Duplicate_Size(self, context):
    size = context.scene.duplicated_obj_props.size
    dup_obj = context.active_object.children[0]
    dup_obj.scale = (size, size, size)

    return


def Update_Duplicate_Offset(self, context):
    obj = context.active_object
    offset = context.scene.duplicated_obj_props.offset
    cur_obj = None
    for mod in obj.modifiers:
        if mod.name ==  'curve rigid':
            cur_obj = mod.object
            obj.location.x = offset + cur_obj.location.x

    return


def Update_Duplicate_norm_Distance(self, context):
    dis = context.scene.duplicated_obj_props.norm_distance
    mods = context.active_object.modifiers

    for m in mods:
        if m.name == 'array norm' and m.type == 'ARRAY':
            m.relative_offset_displace[0] = dis

    return


def Update_Duplicate_norm_Offset(self, context):
    obj = context.active_object
    offset = context.scene.duplicated_obj_props.norm_offset
    for mod in obj.modifiers:
        if mod.name ==  'curve norm':
            cur_obj = mod.object
            obj.location.z = offset + cur_obj.location.z

    return

def Update_count(self, context):
    obj = context.active_object
    dup_count = context.scene.duplicated_obj_props.dup_count
    for mod in obj.modifiers:
        if mod.name == 'array norm':
            mod.count = dup_count
        elif mod.name == 'array rigid':
            mod.count = dup_count

    return

def Update_rotation(self, context):
    mesh_rotation = context.scene.duplicated_obj_props.mesh_rotation
    mesh_rotation_converted = mesh_rotation * 3.1415/180
    obj = bpy.context.active_object
    if obj is not None:
        if obj.type == "MESH":
            obj.rotation_euler[0] = mesh_rotation_converted

    return

def Update_mesh_squash(self, context):
    mesh_squash = context.scene.duplicated_obj_props.mesh_squash
    obj = bpy.context.active_object
    if obj is not None:
        obj.scale[1] = mesh_squash
        obj.scale[2] = mesh_squash

    return

def Update_mesh_stretch(self, context):
    mesh_stretch = context.scene.duplicated_obj_props.mesh_stretch
    obj = bpy.context.active_object
    if obj is not None:
        obj.scale[0] = mesh_stretch

    return

class FlipDirectionOperator(bpy.types.Operator):
    """Flip Direction"""
    bl_idname = "flip_direction.operator"
    bl_label = "Flip Direction"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = bpy.context.active_object
        cur = None
        for mod in obj.modifiers:
            if mod.name == 'curve norm' and mod.type == 'CURVE':
                cur = mod.object
            elif mod.name == 'curve rigid' and mod.type == 'CURVE':
                cur = mod.object
        if cur :
            bpy.ops.object.select_all(action='DESELECT')
            cur.select_set(True)
            bpy.context.view_layer.objects.active = cur
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.curve.select_all(action='SELECT')
            bpy.ops.curve.switch_direction()
            bpy.ops.object.mode_set(mode='OBJECT')
            cur.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        return {'FINISHED'}

def set_squash(self, value):
    self["mesh_squash"] = value


def set_stretch(self, value):
    self["mesh_stretch"] = value


def Update_size_norm_obj(self, context):
    duplicated_obj_props = context.scene.duplicated_obj_props
    size_norm_obj = duplicated_obj_props.size_norm_obj
    dup_obj = context.active_object
    dup_obj.scale = (size_norm_obj, size_norm_obj, size_norm_obj)

    set_stretch(duplicated_obj_props, size_norm_obj)
    set_squash(duplicated_obj_props, size_norm_obj)
    return

class DuplicatedObjectProperties(bpy.types.PropertyGroup):


    size_norm_obj: bpy.props.FloatProperty(
        name='size_norm_obj', default=1, soft_min=0.001, soft_max=5, update=Update_size_norm_obj)

    mesh_squash: bpy.props.FloatProperty(
        name='curve_profile_squash', default=1, min=0.01, soft_max=3, update=Update_mesh_squash)
    mesh_stretch: bpy.props.FloatProperty(
        name='curve_profile_stretch', default=1, min=0.01, soft_max=3, update=Update_mesh_stretch)

    mesh_rotation: bpy.props.FloatProperty(
        name='mesh_rotation', default=0, soft_min=-180, soft_max=180, update=Update_rotation)

    dup_count: bpy.props.IntProperty(
        name='Count', default=3, soft_min=1, soft_max=30, update=Update_count)

    rigid_distance: bpy.props.FloatProperty(
        name='Distance', default=1, soft_min=0.001, soft_max=10, update=Update_Duplicate_Distance)
    size: bpy.props.FloatProperty(
        name='Size', default=1, soft_min=0.001, soft_max=5, update=Update_Duplicate_Size)
    offset: bpy.props.FloatProperty(
        name='Size', default=0, soft_min=-20, soft_max=20, update=Update_Duplicate_Offset)

    norm_distance: bpy.props.FloatProperty(
        name='Distance', default=1, soft_min=0.001, soft_max=5, update=Update_Duplicate_norm_Distance)
    norm_offset: bpy.props.FloatProperty(
        name='Size', default=0, soft_min=-20, soft_max=20, update=Update_Duplicate_norm_Offset)


class DuplicatedObject_PT_main(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Dup Along Cur"
    bl_idname = "DuplicatedObject_PT_main"
    bl_label = "Duplicated Along Curve"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.active_object

        layout.operator("dup_obj_normal.operator")
        for m in obj.modifiers:
            if m.name == 'array norm' and m.type == 'ARRAY' :
                box = layout.box()
                row = box.row()
                row.prop(scene.duplicated_obj_props, "norm_distance",
                         text='Distance', slider=True)
                row.prop(scene.duplicated_obj_props, "norm_offset",
                         text='Offset', slider=True)
                row = box.row()
                row.prop(scene.duplicated_obj_props, "dup_count",
                         text='Count')
                row.prop(scene.duplicated_obj_props, "mesh_rotation",
                         text='Rotation')
                box.prop(scene.duplicated_obj_props, "size_norm_obj",
                         text='Size', slider=True)
                row = box.row()
                row.prop(scene.duplicated_obj_props, "mesh_stretch",
                         text='Stretch', slider=True)
                row.prop(scene.duplicated_obj_props, "mesh_squash",
                         text='Squash', slider=True)
                box.operator("flip_direction.operator")



        layout.operator("dup_obj_rigid.operator")
        for m in obj.modifiers:
            if m.name == 'array rigid' and m.type == 'ARRAY' :
                box = layout.box()
                row = box.row()
                row.prop(scene.duplicated_obj_props, "rigid_distance",
                         text='Distance', slider=True)
                row.prop(scene.duplicated_obj_props, "offset",
                         text='Offset', slider=True)
                row = box.row()
                row.prop(scene.duplicated_obj_props, "dup_count",
                         text='Count')
                row.prop(scene.duplicated_obj_props, "mesh_rotation",
                         text='Rotation')

                box.prop(scene.duplicated_obj_props, "size",
                         text='Size', slider=True)

                box.operator("flip_direction.operator")
                row = box.row()
                row.scale_y = 1.5
                row.operator("confirm_dup_result.operator")


class DupObjRigidOperator(bpy.types.Operator):
    """select a mesh and a curve, order does not matter
rotate mesh facing X axle as the along curve direction for better result"""
    bl_idname = "dup_obj_rigid.operator"
    bl_label = "Duplicate Along Curve Rigid"
    bl_options = {'REGISTER', 'UNDO'}

    duplicated_obj = None
    curve = None
    proxy = None

    @classmethod
    def poll(cls, context):
        c = True
        obj = context.active_object
        selected_objs = context.selected_objects
        if obj is not None:
            for mod in obj.modifiers:
                if  'array norm' in mod.name :
                    c = False
                elif 'array norm' in mod.name :
                    c = False
        return c  and len(selected_objs)==2


    def execute(self, context):

        list_objs = bpy.context.selected_objects
        dup_count = context.scene.duplicated_obj_props.dup_count

        if len(list_objs) == 2:
            for ob in list_objs:
                if ob.type == 'MESH':
                    duplicated_obj = ob
                elif ob.type == 'CURVE':
                    curve = ob

            if curve != None and duplicated_obj != None:
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
                bpy.ops.mesh.primitive_plane_add(
                    size=0.001)

                proxy = bpy.context.active_object
                proxy.location = curve.location


                array_modifier = proxy.modifiers.new(
                    name="array rigid", type='ARRAY')
                array_modifier.use_relative_offset = False
                array_modifier.use_constant_offset = True
                array_modifier.fit_type = 'FIXED_COUNT'
                array_modifier.count = dup_count

                array_modifier.constant_offset_displace[0] = 1
                array_modifier.show_in_editmode = True
                array_modifier.show_on_cage = True
                array_modifier.show_expanded = False

                curve_modifier = proxy.modifiers.new(
                    name="curve rigid", type='CURVE')
                curve_modifier.object = curve
                curve_modifier.show_in_editmode = True
                curve_modifier.show_on_cage = True
                curve_modifier.show_expanded = False

                duplicated_obj.parent = proxy
                duplicated_obj.hide_set(1)
                duplicated_obj.location = (0,0,0)
                proxy.instance_type = 'FACES'


        return {'FINISHED'}


class DupObjNormalOperator(bpy.types.Operator):
    """select a mesh and a curve, order does not matter
rotate mesh facing X axle as the along curve direction for better result"""
    bl_idname = "dup_obj_normal.operator"
    bl_label = "Duplicate Along Curve Deform"
    bl_options = {'REGISTER', 'UNDO'}

    duplicated_obj = None
    curve = None

    @classmethod
    def poll(cls, context):
        c = True
        obj = context.active_object
        selected_objs = context.selected_objects
        if obj is not None:
            for mod in obj.modifiers:
                if  'array norm' in mod.name :
                    c = False
                elif 'array norm' in mod.name :
                    c = False
        return c and len(selected_objs)==2

    def execute(self, context):

        list_objs = bpy.context.selected_objects

        dup_count = context.scene.duplicated_obj_props.dup_count

        if len(list_objs) == 2:
            for ob in list_objs:
                if ob.type == 'MESH':
                    duplicated_obj = ob
                elif ob.type == 'CURVE':
                    curve = ob

            if curve != None and duplicated_obj != None:
                bpy.context.view_layer.objects.active = duplicated_obj
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

                duplicated_obj.location = curve.location

                array_modifier = duplicated_obj.modifiers.new(
                    name="array norm", type='ARRAY')
                array_modifier.use_relative_offset = True
                array_modifier.use_constant_offset = False
                array_modifier.fit_type = 'FIXED_COUNT'
                array_modifier.count = dup_count

                array_modifier.curve = curve
                array_modifier.show_in_editmode = True
                array_modifier.show_on_cage = True
                array_modifier.show_expanded = False

                curve_modifier = duplicated_obj.modifiers.new(
                    name="curve norm", type='CURVE')
                curve_modifier.object = curve
                curve_modifier.show_in_editmode = True
                curve_modifier.show_on_cage = True
                curve_modifier.show_expanded = False

        return {'FINISHED'}


class ConfirmResultOperator(bpy.types.Operator):
    """Confirm Duplication Result"""
    bl_idname = "confirm_dup_result.operator"
    bl_label = "Confirm Rigid Duplication Result"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        return context.active_object is not None


    def execute(self, context):
        proxy = context.active_object
        dup_obj = context.active_object.children[0]
        dup_obj.hide_set(0)

        bpy.ops.object.duplicates_make_real()

        list_dup = bpy.context.selected_objects
        dup_coll = bpy.data.collections.new('Duplicate_Collection')
        dup_coll.name = dup_obj.name + dup_coll.name
        bpy.context.scene.collection.children.link(dup_coll)

        for ob in list_dup:
            for coll in ob.users_collection:
                coll.objects.unlink(ob)

            dup_coll.objects.link(ob)

        bpy.data.objects.remove(proxy, do_unlink=True)
        bpy.data.objects.remove(dup_obj, do_unlink=True)

        return {'FINISHED'}


classes = [
    DuplicatedObject_PT_main, DuplicatedObjectProperties, DupObjRigidOperator, DupObjNormalOperator, ConfirmResultOperator,FlipDirectionOperator,

]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.duplicated_obj_props = bpy.props.PointerProperty(
        type=DuplicatedObjectProperties)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.duplicated_obj_props


if __name__ == "__main__":
    register()
