#  Copyright (c) 2020-2021 Swyter <swyterzone+sphinx@gmail.com>
#  SPDX-License-Identifier: Zlib

"""
Name: 'Eurocom Real Time Game'
Blender: 4.3.2
Group: 'Export'
Tooltip: 'Blender RTG Exporter for EuroLand'
Authors: Swyter and Jmarti856
"""

import bpy
import platform
from pathlib import Path
from math import degrees
from mathutils import Matrix
from datetime import datetime
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
from .eland_utils import *

#-------------------------------------------------------------------------------------------------------------------------------
EXPORT_TRI = True
EXPORT_APPLY_MODIFIERS = True
START_FRAME = 0
END_FRAME = 0

#Global variables
FRAMES_COUNT = 0
TICKS_PER_FRAME = 0

#-------------------------------------------------------------------------------------------------------------------------------
def _write(context, filepath,
           EXPORT_MESH_FLAGS,
           EXPORT_MATERIALS,
           EXPORT_MESH_ANIMS, 
           EXPORT_CAMERA_LIGHT_ANIMS, 
           TRANSFORM_TO_CENTER,
           EXPORT_OBJECTS,
           EXPORT_MESH_NORMALS,
           EXPORT_MESH_UV,
           EXPORT_MESH_VCOLORS,
           EXPORT_MESH_MORPH,
           EXPORT_STATIC_FRAME,
           DECIMAL_PRECISION,
           GLOBAL_SCALE,
           EXPORT_FROM_FRAME_ENABLED,
           EXPORT_FROM_FRAME,
           EXPORT_END_FRAME_ENABLED,
           EXPORT_END_FRAME
        ):
    
    df = f'%.{DECIMAL_PRECISION}f'
    dcf = f'{{:>{DECIMAL_PRECISION}f}}'

    #-------------------------------------------------------------------------------------------------------------------------------
    def get_camera_objects(scene, depsgraph):
        """
        Devuelve una lista de cámaras enriquecida con datos adicionales.
        Cada entrada incluye ob, ob_main y obj_matrix_data.
        """
        cameras = []

        for ob_main in sorted([obj for obj in scene.objects if obj.type == 'CAMERA'], key=lambda obj: obj.name):
            obs = [(ob_main, ob_main.matrix_world)]
            if ob_main.is_instancer:
                obs += [(dup.instance_object.original, dup.matrix_world.copy())
                        for dup in depsgraph.object_instances
                        if dup.parent and dup.parent.original == ob_main]

            for ob, ob_mat in obs:
                ob_for_convert = ob.evaluated_get(depsgraph) if EXPORT_APPLY_MODIFIERS else ob.original

                try:
                    camera_data = ob_for_convert.data
                except RuntimeError:
                    camera_data = None

                if camera_data is None:
                    continue

                obj_matrix_data = {
                    "name": ob.name,
                    "type": ob_main.type,
                    "matrix_original": ob_mat.copy(),
                    "matrix_transformed": ob_mat.copy()
                }

                cameras.append({
                    "ob": ob,
                    "ob_main": ob_main,
                    "obj_matrix_data": obj_matrix_data
                })

        return cameras

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_scene_hierarchy(out, scene, cameras):
        global FRAMES_COUNT, TICKS_PER_FRAME, START_FRAME, END_FRAME

        #Get set default scene data
        START_FRAME = scene.frame_start
        END_FRAME = scene.frame_end

        #Override values
        if EXPORT_FROM_FRAME_ENABLED and (EXPORT_FROM_FRAME >= START_FRAME):
            START_FRAME = EXPORT_FROM_FRAME
        if EXPORT_END_FRAME_ENABLED and (EXPORT_END_FRAME <= END_FRAME):
            END_FRAME = EXPORT_END_FRAME
            
        bpy.context.scene.frame_set(EXPORT_STATIC_FRAME)

        FRAMES_COUNT = END_FRAME - START_FRAME + 1

        out.write("*SCENE_HIERARCHY {"+"\n")
        for idx, camera in enumerate(cameras):
            out.write("\tCamera%d 1 CAMERA %s\n" % (idx, camera['ob'].name))
        out.write("}\n\n")
        out.write("\n")

        out.write("*SCENE_FRAMES_PER_SECOND %u" % bpy.context.scene.render.fps + "\n")

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_camera_scene_frames(out, cameras):
        for camera_index, camera in enumerate(cameras):
            ob_main = camera['ob_main']

            eland_data = create_euroland_matrix(ob_main.matrix_world.copy(), ob_main.type)
            eland_matrix = eland_data["eland_matrix"]

            out.write(f'\tCamera' + str(camera_index))
            out.write(f' {df} {df} {df}' % (eland_matrix[0].x, eland_matrix[0].y, eland_matrix[0].z))
            out.write(f' {df} {df} {df}' % (eland_matrix[1].x, eland_matrix[1].y, eland_matrix[1].z))
            out.write(f' {df} {df} {df}' % (eland_matrix[2].x, eland_matrix[2].y, eland_matrix[2].z))

            #Transform position
            obj_position = eland_matrix.translation
            out.write(f' {df} {df} {df}\n' % (obj_position.x, obj_position.y, obj_position.z*-1))

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_camera_list(out, cameras):
        out.write("*CAMERA_LIST {" + "\n")
        for camera_index, camera in enumerate(cameras):
            camera_data = camera['ob'].data
            out.write(f"\tCamera%d {df} {df} %d %d %d 1" % (camera_index, camera_data.angle, camera_data.angle, camera_data.lens, camera_data.clip_start, camera_data.clip_end) + "\n")
        out.write("}" + "\n")

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_camera_animation(out, scene, cameras):
        out.write("*CAMERA_ANIMATION {"+"\n")
        for camera_index, camera in enumerate(cameras):
            out.write("\tCamera%d focalLength " % (camera_index))
            #for f in keyframes:
            for frame in range(START_FRAME, END_FRAME + 1):
                scene.frame_set(frame)
                len_val = camera['ob'].data.lens
                # The curve's points has a 'co' vector giving the frame and the value
                out.write("%u %u " % (frame, len_val))
            out.write("\n")

        out.write("}\n")

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_rtg_file():
        depsgraph = bpy.context.evaluated_depsgraph_get()
        scene = bpy.context.scene

        # Exit edit mode before exporting, so current object states are exported properly.
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Get current plugin version
        plugin_version = get_plugin_version()

        with open(filepath, 'w', encoding="utf8",) as out:
            out.write("EUROCOM_RTG 5.01"+"\n")
            out.write('*COMMENT "Version of Blender that output this file: %s"\n' % bpy.app.version_string)
            out.write('*COMMENT "Version of RTG Plug-in: %d.%d.%d"\n\n' % (plugin_version[0], plugin_version[1], plugin_version[2]))
            out.write("\n")

            #Get cameras if requierd
            scene_cameras = []
            if 'CAMERA' in EXPORT_OBJECTS:
                scene_cameras = get_camera_objects(scene, depsgraph)
            
            #Write scene hirearchy
            write_scene_hierarchy(out, scene, scene_cameras)

            #Write scene animated frames
            for frame in range(START_FRAME, END_FRAME + 1):
                scene.frame_set(frame)

                out.write("*SCENE_FRAME %u {\n" % frame)
                if scene_cameras:
                    write_camera_scene_frames(out, scene_cameras)
                out.write("}\n")

            #Objects animation data
            if 'CAMERA' in EXPORT_OBJECTS:
                write_camera_list(out, scene_cameras)
                write_camera_animation(out, scene, scene_cameras)

    write_rtg_file()

#-------------------------------------------------------------------------------------------------------------------------------
def save(context, 
         filepath, 
         *, 
         Output_Mesh_Definition,
         Output_Materials, 
         Output_Mesh_Anims, 
         Output_CameraLightAnims,
         Transform_Center,
         Object_Types,
         Output_Mesh_Normals,
         Output_Mesh_UV,
         Output_Mesh_Vertex_Colors,
         Output_Mesh_Morph,
         Static_Frame,
         Decimal_Precision,
         Output_Scale,
         Enable_Start_From_Frame,
         Start_From_Frame,
         Enable_End_With_Frame,
         End_With_Frame,
         Output_First_Only):

    _write(context, filepath,
           EXPORT_MESH_FLAGS=Output_Mesh_Definition,
           EXPORT_MATERIALS=Output_Materials,
           EXPORT_MESH_ANIMS=Output_Mesh_Anims, 
           EXPORT_CAMERA_LIGHT_ANIMS=Output_CameraLightAnims, 
           TRANSFORM_TO_CENTER = Transform_Center,
           EXPORT_OBJECTS=Object_Types,
           EXPORT_MESH_NORMALS=Output_Mesh_Normals,
           EXPORT_MESH_UV=Output_Mesh_UV,
           EXPORT_MESH_VCOLORS=Output_Mesh_Vertex_Colors,
           EXPORT_MESH_MORPH=Output_Mesh_Morph,
           EXPORT_STATIC_FRAME=Static_Frame,
           DECIMAL_PRECISION=Decimal_Precision,
           GLOBAL_SCALE=Output_Scale,
           EXPORT_FROM_FRAME_ENABLED=Enable_Start_From_Frame,
           EXPORT_FROM_FRAME=Start_From_Frame,
           EXPORT_END_FRAME_ENABLED=Enable_End_With_Frame,
           EXPORT_END_FRAME=End_With_Frame)

    return {'FINISHED'}
if __name__ == '__main__':
    save({}, str(Path.home()) + '/Desktop/EurocomRTG.rtg')