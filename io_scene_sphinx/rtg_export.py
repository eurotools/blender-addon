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
import os
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
    def get_mesh_objects(scene, depsgraph):
        meshes = []

        for ob_main in scene.objects:
            # ignore dupli children
            if ob_main.parent and ob_main.parent.instance_type in {'VERTS', 'FACES'}:
                continue

            obs = [(ob_main, ob_main.matrix_world)]
            if ob_main.is_instancer:
                obs += [(dup.instance_object.original, dup.matrix_world.copy())
                        for dup in depsgraph.object_instances
                        if dup.parent and dup.parent.original == ob_main]
                # ~ print(ob_main.name, 'has', len(obs) - 1, 'dupli children')
                
            for ob, ob_mat in obs:
                ob_for_convert = ob.evaluated_get(depsgraph) if EXPORT_APPLY_MODIFIERS else ob.original

                try:
                    me = ob_for_convert.to_mesh()
                except RuntimeError:
                    me = None

                if me is None:
                    continue

                # _must_ do this before applying transformation, else tessellation may differ
                if EXPORT_TRI:
                    # _must_ do this first since it re-allocs arrays
                    mesh_triangulate(me)

                # Create transform matrix
                if TRANSFORM_TO_CENTER:
                    to_origin = Matrix.Identity(4)
                    scale_matrix = Matrix.Diagonal(ob.scale).to_4x4()

                    matrix_transformed = to_origin @ scale_matrix
                else:
                    matrix_transformed = ob_mat
                
                # Apply transform matrix
                me.transform(MESH_GLOBAL_MATRIX @ matrix_transformed)

                obj_matrix_data = {
                    "name" : ob_main.name,
                    "type" : ob_main.type,
                    "matrix_original" : ob_mat.copy(),
                    "matrix_transformed": matrix_transformed.copy()
                }

                # If negative scaling, we have to invert the normals...
                if ob_mat.determinant() < 0.0:
                    me.flip_normals()

                meshes.append({
                    "ob": ob,
                    "me" : me,
                    "ob_main": ob_main,
                    "obj_matrix_data": obj_matrix_data
                })

        return meshes
    
    #-------------------------------------------------------------------------------------------------------------------------------
    def write_scene_hierarchy(out, scene, cameras, meshes):
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
        for idx, mesh in enumerate(meshes):
            out.write("\%s 1 MESH %sShape\n" % (mesh['ob'].name, mesh['ob'].name))
        out.write("}\n\n")
        out.write("\n")

        out.write("*SCENE_FRAMES_PER_SECOND %u" % bpy.context.scene.render.fps + "\n")

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_camera_scene_frames(out, cameras):
        for camera_index, camera in enumerate(cameras):
            ob_main = camera['ob_main']

            eland_data = create_euroland_matrix(ob_main.matrix_world.copy(), ob_main.type)
            eland_matrix = eland_data["eland_matrix"]

            out.write(f'\tCamera%d' % (camera_index))
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
    def write_scene_mesh(out, scene, meshes):
        out.write("*MESH {"+"\n")
        for mesh in meshes:
            me = mesh['me']
            ob = mesh['ob'] 

            # Crear listas únicas de coordenadas de vértices, UVs y colores de vértices
            unique_vertices = list({tuple(v.co) for v in me.vertices})

            out.write("\t*NAME %sShape\n" % (mesh['ob'].name))

            #Vertex list
            out.write('\t*VERT_XYXRGBA %d{\n' % (len(unique_vertices)))
            for vertex in unique_vertices:
                out.write(f'\t\t{df} {df} {df}\n' % (vertex[0], vertex[1], vertex[2]*-1))
            out.write('\t}\n')

            # Create mapping lists
            unique_vertices = list({tuple(v.co) for v in me.vertices})
            vertex_index_map = {v: idx for idx, v in enumerate(unique_vertices)}

            #Materials
            material_names = []
            for mat_idx, mat in enumerate(ob.data.materials):
                # Envolver material para usar PrincipledBSDFWrapper
                mat_wrap = PrincipledBSDFWrapper(mat) if mat.use_nodes else None
                
                if mat_wrap:
                    use_mirror = mat_wrap.metallic != 0.0
                    use_transparency = mat_wrap.alpha != 1.0
                
                    out.write('\t*SHADER_%d {\n' % (mat_idx))         
                    out.write(f'\t\t{df} {df} {df} ' % (mat_wrap.base_color[:3])) # Diffuse
                    out.write(f"{df}\n" % (1))

                    #### And now, the image textures...
                    image_map = {
                            "map_Kd": "base_color_texture",
                            }

                    #Print texture name
                    for key, mat_wrap_key in sorted(image_map.items()):
                        if mat_wrap_key is None:
                            continue
                        tex_wrap = getattr(mat_wrap, mat_wrap_key, None)
                        if tex_wrap is None:
                            continue
                        image = tex_wrap.image
                        if image is None:
                            continue

                        texture_path = bpy.path.abspath(image.filepath)
                        texture_name = os.path.basename(texture_path).replace(" ", "_")

                        out.write('\t\t%s "%s"' % (texture_name, texture_path))
                        material_names.append(texture_name)

                    #print blend data
                    if mat_wrap.specular == 0:
                        illum = 1  # No specular
                    elif use_mirror:
                        if use_transparency:
                            illum = 6  # Reflection, Transparency, Ray trace
                        else:
                            illum = 3  # Reflection and Ray trace
                    elif use_transparency:
                        illum = 9  # 'Glass' transparency and no Ray trace reflection
                    else:
                        illum = 2  # Light normally

                    # Determinar blend-mode basado en illum
                    blend_mode = 0 if illum in (1, 2, 9) else 1

                    #print data   
                    out.write(f' {df} ' % (mat_wrap.alpha))
                    out.write(' %d ' % (blend_mode))
                    out.write('%d\n' % 0)
                    out.write("\t}\n")
            
            # swy: refresh the custom mesh layer/attributes in case they don't exist
            if 'euro_fac_flags' not in me.attributes:
                me.attributes.new(name='euro_fac_flags', type='INT', domain='FACE')

            euro_fac_flags = me.attributes['euro_fac_flags']

            #Face list
            out.write("\t*FACE_LIST {\n")
            for p_index, poly in enumerate(me.polygons):
                flag_value = euro_fac_flags.data[poly.index].value
                out.write("\t\t*FACE %d %d %d {\n" % (len(poly.vertices), poly.material_index, flag_value))
                
                #Print vertex
                vertex_indices = [vertex_index_map[tuple(me.vertices[v].co)] for v in (poly.vertices)]
                out.write(f"\t\t\t" + " ".join(map(str, vertex_indices)) + " \n")

                #Print UVs
                if material_names:
                    out.write("\t\t\t")
                    # Iterar solo sobre la capa activa
                    active_uv_layer = me.uv_layers.active
                    for loop_index in poly.loop_indices:
                        uv = active_uv_layer.data[loop_index].uv
                        out.write(f' {uv[0]:.6f} { -uv[1]:.6f}')

                    #Print material name
                    out.write(" %s\n" % (material_names[poly.material_index]))
                out.write("\t\t}\n")
            out.write("\t}\n")
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
            
            scene_meshes = []
            if 'MESH' in EXPORT_OBJECTS:
                scene_meshes = get_mesh_objects(scene, depsgraph)
            
            #Write scene hirearchy
            write_scene_hierarchy(out, scene, scene_cameras, scene_meshes)

            #Write scene animated frames
            if EXPORT_CAMERA_LIGHT_ANIMS:
                for frame in range(START_FRAME, END_FRAME + 1):
                    scene.frame_set(frame)

                    out.write("*SCENE_FRAME %u {\n" % frame)
                    if scene_cameras:
                        write_camera_scene_frames(out, scene_cameras)
                    out.write("}\n")

            #Output Meshes if required
            if 'MESH' in EXPORT_OBJECTS:
                write_scene_mesh(out, scene, scene_meshes)

            #Output Cameras if required
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