#
#	name		LFS LYT Object Normalize Tool
#	version:	1.0
#   author:     Vritrasura, Nex_
#
#   Special thanks to Nex_ for modelling a majority of LFS blocks!

import bpy
import math

def normalizeObject(obj):
    pos_orig = obj.location
    
    loc_x = obj.location.x
    loc_x = round(loc_x / 0.0625) * 0.0625
    obj.location.x = loc_x
    
    loc_y = obj.location.y
    loc_y = round(loc_y / 0.0625) * 0.0625
    obj.location.y = loc_y
    
    loc_z = obj.location.z
    loc_z = round(loc_z / 0.25) * 0.25
    obj.location.z = loc_z
    
    rot_z = obj.rotation_euler.z
    rot_z = round(rot_z / 0.0245436926) * 0.0245436926
    obj.rotation_euler.z = rot_z

    pos_norm = obj.location

    if pos_orig != pos_norm:
        print(f"original pos:   {obj.location.x} {obj.location.y} {obj.location.z}")
        print(f"normalized pos: {loc_x} {loc_y} {loc_z}")
    
objects = bpy.context.selected_objects

for obj in objects:
    normalizeObject(obj)
    print("Done...")