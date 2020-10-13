# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

import bpy
import os
import math
from mathutils import *
from math import *
from pathlib import Path
from bpy_extras.io_utils import axis_conversion

def save(context,
     filepath,
     *,
     use_triangles=False,
     use_edges=True,
     use_normals=False,
     use_smooth_groups=False,
     use_smooth_groups_bitflags=False,
     use_uvs=True,
     use_materials=True,
     use_mesh_modifiers=True,
     use_mesh_modifiers_render=False,
     use_blen_objects=True,
     group_by_object=False,
     group_by_material=False,
     keep_vertex_order=False,
     use_vertex_groups=False,
     use_nurbs=True,
     use_selection=True,
     use_animation=False,
     global_matrix=None,
     path_mode='AUTO'
     ):

    """
    Name: 'EuroRTG'
    Blender: 280
    Group: 'Export'
    Tooltip: 'Blender RTG Exporter for EuroLand'
    """

    camera_num = 0
    out = open(filepath, "w")
    sce = bpy.context.scene
    
    out.write("EUROCOM_RTG 5.01"+"\n")
    out.write("\n")
    
    for ob in sce.objects:
        if ob.type == 'CAMERA':
            out.write("*SCENE_HIERARCHY {"+"\n")
            out.write(" Camera" + str(camera_num) +" 1 CAMERA "+ ob.name + "\n")
            out.write("}" + "\n")
            out.write("\n")
            
            out.write("*SCENE_FRAMES_PER_SECOND %u" % bpy.context.scene.render.fps + "\n")
            out.write("\n")
            
            keyframes = []
            keyframes_obj = []
            keyframes_cam = [] 
            if ob.animation_data:
                if ob.animation_data.action is not None:
                    for curve in ob.animation_data.action.fcurves:
                        print(curve.data_path, curve.array_index)
                        for key in curve.keyframe_points:
                            key_idx = int(key.co[0])
                            key_val = key.co[1]
                            # swy: append it to the keyframe list
                            keyframes_obj.append(key_idx)
                            # The curve's points has a 'co' vector giving the frame and the value 
                            print('frame: ', key_idx, ' value: ', key_val)
                        
            print(keyframes_obj)
             
            if ob.data.animation_data is not None:             
                fcurves = ob.data.animation_data.action.fcurves
                lens_fcurve = fcurves.find('lens')
                if lens_fcurve is not None:
                    for lens in lens_fcurve.keyframe_points:
                        len_idx = int(lens.co[0])
                        len_val = lens.co[1]
                        # swy: append it to the keyframe list
                        keyframes_cam.append(len_idx)
                        # The curve's points has a 'co' vector giving the frame and the value         
            
            
            # swy: deduplicate and sort the keyframe list
            keyframes_obj=sorted(set(keyframes_obj))
            print(keyframes_obj)
            
            keyframes = keyframes_obj + keyframes_cam
            
            # swy: deduplicate and sort the keyframe list
            keyframes=sorted(set(keyframes))
            print(keyframes)
            
            #for f in keyframes_obj:
            for f in range(sce.frame_start, sce.frame_end):
                # swy: restrict the keyframes to those within bounds 
                #if f < sce.frame_start or f > sce.frame_end:
                #    continue
                
                sce.frame_set(f)
                
                mtx_conv = axis_conversion(to_forward='-Z', to_up='Y')
                
                rot_thing = ob.rotation_euler
                #rot_thing = rot_thing.to_quaternion().inverted().to_euler()
                rot_thing = rot_thing.to_quaternion()
                #rot_thing.negate()
                ##rot_thing.z = -rot_thing.z
                ##rot_thing.w = -rot_thing.w
                rot_thing = rot_thing.to_euler()
                rot_thing.z = -rot_thing.z
                
                rot_thing.rotate_axis('X', radians(90))
                #rot_thing.rotate_axis('Y', radians(-90))
                #rot_thing.rotate_axis('Z', radians(-90))
                
                #rot_thing.x = -rot_thing.x
                #rot_thing.y = -rot_thing.y
                #rot_thing.z = -rot_thing.z
                
                #rot_thing = rot_thing.to_quaternion().inverted().to_euler()
                
                
                print(f, "rot_eul", degrees(rot_thing.x), degrees(rot_thing.y), degrees(rot_thing.z), rot_thing)
                
                #rot_mtx = rot_thing.to_matrix()
                rot_mtx = mtx_conv @ rot_thing.to_matrix() @ mtx_conv
                
                rot_thing = rot_mtx.to_euler()
                print(f, "rot_eul", degrees(rot_thing.x), degrees(rot_thing.y), degrees(rot_thing.z), rot_thing)
                
                
                flip_remaining_axis=Matrix(([-1,0,0],[0,1,0],[0,0,-1]))
                
                #rot_mtx = flip_remaining_axis @ rot_thing.to_matrix() @ flip_remaining_axis
                
                rot_thing = rot_mtx.to_euler()
                print(f, "rot_eul", degrees(rot_thing.x), degrees(rot_thing.y), degrees(rot_thing.z), rot_thing)
                
                
                

                loc_conv = mtx_conv @ ob.location
                
                out.write("*SCENE_FRAME %u {\n" % f)
                out.write(" Camera" + str(camera_num) + " %g %g %g %g %g %g %g %g %g  %g %g %g \n" %
                (
                    rot_mtx[0][0], rot_mtx[0][1], rot_mtx[0][2],
                    rot_mtx[1][0], rot_mtx[1][1], rot_mtx[1][2],
                    rot_mtx[2][0], rot_mtx[2][1], rot_mtx[2][2],
                    loc_conv.x, loc_conv.y, loc_conv.z # +X +Z -Y // 1,2,3 -> 1,3,-2 (for some reason 3rd one appears reversed; Z is flipped at .RTG matrix import time)
                ))
                out.write("}" + "\n")
                out.write("\n")
                
            out.write("*CAMERA_LIST {" + "\n")
            #out.write(" Camera0 %g %g  %g  %g %g  1" % (ob.data.sensor_width, ob.data.sensor_height, ob.data.lens, ob.data.clip_start, ob.data.clip_end) + "\n")
            out.write(" Camera0 %g %g  %g  %g %g  1" % (.4, .1, ob.data.lens, ob.data.clip_start, ob.data.clip_end) + "\n")
            out.write("}" + "\n")
            if keyframes:
                out.write("*CAMERA_ANIMATION {"+"\n")
                out.write(" Camera" + str(camera_num) + " focalLength ")
                #for f in keyframes:
                for f in range(sce.frame_start, sce.frame_end):
                    sce.frame_set(f)
                    len_idx = f
                    len_val = ob.data.lens
                    # The curve's points has a 'co' vector giving the frame and the value 
                    out.write("%u %u " % (len_idx, len_val))
                out.write("\n}" + "\n")
                    
        camera_num += 1
    out.close()

    return {'FINISHED'}



if __name__ == "__main__":
    save({}, str(Path.home()) + "\\Desktop\\Camera9.rtg")