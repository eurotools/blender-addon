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
            out.write("\tCamera" + str(camera_num) +" 1 CAMERA "+ ob.name + "\n")
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
            
            InvertAxisRotationMatrix = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0)))
            
            #for f in keyframes_obj:
            for f in range(sce.frame_start, sce.frame_end + 1):
                sce.frame_set(f)
                
                ConvertedMatrix = ob.rotation_euler.to_matrix()
                rot_mtx = InvertAxisRotationMatrix @ ConvertedMatrix
                RotationMatrix = rot_mtx.transposed()         

                loc_conv = InvertAxisRotationMatrix @ ob.location
                
                out.write("*SCENE_FRAME %u {\n" % f)
                out.write('\tCamera' + str(camera_num) + ' %.6f %.6f %.6f'% (RotationMatrix[0].x, (RotationMatrix[0].y * -1), RotationMatrix[0].z))
                out.write(' %.6f %.6f %.6f' % (RotationMatrix[1].x, RotationMatrix[1].y, RotationMatrix[1].z))
                out.write(' %.6f %.6f %.6f' % ((RotationMatrix[2].x * -1), (RotationMatrix[2].y * -1), (RotationMatrix[2].z) * -1))
                out.write(' %.6f %.6f %.6f\n' % (loc_conv.x, loc_conv.y, (loc_conv.z * -1))) 
                out.write("}" + "\n")
                out.write("\n")
                
            out.write("*CAMERA_LIST {" + "\n")
            out.write(" Camera0 %g %g  %g  %g %g  1" % (.4, .1, ob.data.lens, ob.data.clip_start, ob.data.clip_end) + "\n")
            out.write("}" + "\n")
            if keyframes:
                out.write("*CAMERA_ANIMATION {"+"\n")
                out.write("\tCamera" + str(camera_num) + " focalLength ")
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