#  Copyright (c) 2020-2021 Swyter <swyterzone+sphinx@gmail.com>
#  SPDX-License-Identifier: Zlib

"""
Name: 'Eurocom Real Time Game'
Blender: 4.3.2
Group: 'Export'
Tooltip: 'Blender RTG Exporter for EuroLand'
Authors: Swyter and Jmarti856
"""

import os
import bpy
from pathlib import Path
from mathutils import Matrix
from datetime import datetime
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
from .eland_utils import *

#-------------------------------------------------------------------------------------------------------------------------------
EXPORT_TRI = True
EXPORT_APPLY_MODIFIERS = True
START_FRAME = 0
END_FRAME = 0


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

    #---------------------------------------------------------------------------------------------------------------------------
    def unique_ordered(values):
        result = []
        index_map = {}
        for value in values:
            if value not in index_map:
                index_map[value] = len(result)
                result.append(value)
        return result, index_map

    #---------------------------------------------------------------------------------------------------------------------------
    def color_layer_data(mesh):
        if hasattr(mesh, "color_attributes") and mesh.color_attributes:
            active = mesh.color_attributes.active_color or mesh.color_attributes.active
            return active.data if active else None
        if mesh.vertex_colors:
            active = mesh.vertex_colors.active
            return active.data if active else None
        return None

    #---------------------------------------------------------------------------------------------------------------------------
    def material_wrap(mat):
        return PrincipledBSDFWrapper(mat) if mat and mat.use_nodes else None

    #---------------------------------------------------------------------------------------------------------------------------
    def texture_path(mat):
        mat_wrap = material_wrap(mat)
        if not mat_wrap:
            return None
        tex_wrap = getattr(mat_wrap, "base_color_texture", None)
        image = tex_wrap.image if tex_wrap else None
        return bpy.path.abspath(image.filepath) if image else None

    #---------------------------------------------------------------------------------------------------------------------------
    def material_color(mat):
        mat_wrap = material_wrap(mat)
        if mat_wrap:
            return mat_wrap.base_color[:3], mat_wrap.alpha
        if mat:
            return mat.diffuse_color[:3], mat.diffuse_color[3]
        return (0.8, 0.8, 0.8), 1.0

    #---------------------------------------------------------------------------------------------------------------------------
    def material_blend(mat):
        mat_wrap = material_wrap(mat)
        alpha = mat_wrap.alpha if mat_wrap else (mat.diffuse_color[3] if mat else 1.0)
        blend_method = getattr(mat, "blend_method", "OPAQUE") if mat else "OPAQUE"
        rtg_flags = 1 if alpha < 0.999 or blend_method in {'BLEND', 'HASHED', 'CLIP'} else 0
        blend_mode = 0
        return alpha, blend_mode, rtg_flags

    #---------------------------------------------------------------------------------------------------------------------------
    def int_attribute(mesh, name, domain):
        attr = mesh.attributes.get(name)
        if attr and attr.data_type == 'INT' and attr.domain == domain:
            return attr
        return None

    #---------------------------------------------------------------------------------------------------------------------------
    def scene_frame_range(scene):
        start = scene.frame_start
        end = scene.frame_end
        if EXPORT_FROM_FRAME_ENABLED:
            start = max(start, EXPORT_FROM_FRAME)
        if EXPORT_END_FRAME_ENABLED:
            end = min(end, EXPORT_END_FRAME)
        if end < start:
            end = start
        return start, end

    #---------------------------------------------------------------------------------------------------------------------------
    def transformed_matrix(obj_matrix, obj_type):
        return create_euroland_matrix(Matrix.Scale(GLOBAL_SCALE, 4) @ obj_matrix, obj_type)["eland_matrix"]

    #---------------------------------------------------------------------------------------------------------------------------
    def matrix_line(name, matrix):
        return (
            f'\t{name}'
            f' {df} {df} {df}' % (matrix[0].x, matrix[0].y, matrix[0].z)
            + f' {df} {df} {df}' % (matrix[1].x, matrix[1].y, matrix[1].z)
            + f' {df} {df} {df}' % (matrix[2].x, matrix[2].y, matrix[2].z)
            + f' {df} {df} {df}\n' % (matrix.translation.x, matrix.translation.y, matrix.translation.z)
        )

    #---------------------------------------------------------------------------------------------------------------------------
    def mesh_export_data(ob, ob_mat, depsgraph):
        ob_eval = ob.evaluated_get(depsgraph) if EXPORT_APPLY_MODIFIERS else ob.original
        try:
            mesh = ob_eval.to_mesh()
        except RuntimeError:
            return None, None

        if mesh is None:
            return None, ob_eval

        if EXPORT_TRI:
            mesh_triangulate(mesh)

        if TRANSFORM_TO_CENTER:
            matrix = Matrix.Diagonal(ob_mat.to_scale()).to_4x4()
        else:
            matrix = ob_mat.copy()

        mesh.transform(Matrix.Scale(GLOBAL_SCALE, 4) @ (MESH_GLOBAL_MATRIX @ matrix))
        if ob_mat.determinant() < 0.0:
            mesh.flip_normals()
        return mesh, ob_eval

    #---------------------------------------------------------------------------------------------------------------------------
    def collect_meshes(scene, depsgraph):
        meshes = []
        for ob_main in scene.objects:
            if ob_main.type != 'MESH':
                continue
            if ob_main.parent and ob_main.parent.instance_type in {'VERTS', 'FACES'}:
                continue

            instances = [(ob_main, ob_main.matrix_world)]
            if ob_main.is_instancer:
                instances += [
                    (dup.instance_object.original, dup.matrix_world.copy())
                    for dup in depsgraph.object_instances
                    if dup.parent and dup.parent.original == ob_main
                ]

            for ob, ob_mat in instances:
                mesh, ob_eval = mesh_export_data(ob, ob_mat, depsgraph)
                if mesh is None:
                    continue
                meshes.append({
                    "object": ob,
                    "main": ob_main,
                    "matrix": ob_mat.copy(),
                    "mesh": mesh,
                    "eval": ob_eval,
                    "shape_name": f"{ob.name}Shape"
                })
        return meshes

    #---------------------------------------------------------------------------------------------------------------------------
    def collect_cameras(scene):
        return sorted([obj for obj in scene.objects if obj.type == 'CAMERA'], key=lambda obj: obj.name)

    #---------------------------------------------------------------------------------------------------------------------------
    def hierarchy_name(obj):
        return obj.name.replace(" ", "_")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_material_list(out, meshes):
        if not EXPORT_MATERIALS:
            return

        out.write("*MATERIAL {\n")
        seen = set()
        for mesh_data in meshes:
            for mat in mesh_data["object"].data.materials:
                if mat is None or mat.name in seen:
                    continue
                seen.add(mat.name)
                color, alpha = material_color(mat)
                out.write('\t*MATERIAL {\n')
                out.write('\t\t*NAME "%s"\n' % mat.name)
                out.write(f'\t\t*COL_AMBIENT {df} {df} {df}\n' % (1.0, 1.0, 1.0))
                out.write(f'\t\t*COL_DIFFUSE {df} {df} {df}\n' % color)
                out.write(f'\t\t*COL_SPECULAR {df} {df} {df}\n' % (0.0, 0.0, 0.0))
                out.write(f'\t\t*COL_EMMISION {df}\n' % 0.0)
                out.write(f'\t\t*SHININESS {df}\n' % 0.0)
                out.write(f'\t\t*TRANSPARENCY {df}\n' % (1.0 - alpha))
                tex = texture_path(mat)
                if tex:
                    out.write('\t\t*MAP_DIFFUSE "%s"\n' % tex)
                out.write('\t}\n')
        out.write("}\n\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_scene_hierarchy(out, meshes, cameras):
        out.write("*SCENE_HIERARCHY {\n")
        for camera in cameras:
            out.write("\t%s 1 CAMERA\n" % hierarchy_name(camera))
        for mesh_data in meshes:
            out.write("\t%s 1 MESH %s\n" % (hierarchy_name(mesh_data["object"]), mesh_data["shape_name"]))
        out.write("}\n\n")
        out.write("*SCENE_FRAMES_PER_SECOND %u\n" % bpy.context.scene.render.fps)

    #---------------------------------------------------------------------------------------------------------------------------
    def write_scene_frame(out, scene, meshes, cameras, frame):
        scene.frame_set(frame)
        out.write("*SCENE_FRAME %u {\n" % frame)
        for camera in cameras:
            matrix = transformed_matrix(camera.matrix_world.copy(), camera.type)
            out.write(matrix_line(hierarchy_name(camera), matrix))
        for mesh_data in meshes:
            matrix = transformed_matrix(mesh_data["object"].matrix_world.copy(), mesh_data["object"].type)
            out.write(matrix_line(hierarchy_name(mesh_data["object"]), matrix))
        out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_shader(out, mat, shader_index):
        color, _ = material_color(mat)
        alpha, blend_mode, rtg_flags = material_blend(mat)
        out.write('\t*SHADER_%d {\n' % shader_index)
        out.write(f'\t\t{df} {df} {df} {df}\n' % (color[0], color[1], color[2], 1.0))

        tex = texture_path(mat)
        if tex:
            texture_name = os.path.basename(tex).replace(" ", "_")
            out.write('\t\t%s "%s" ' % (texture_name, tex))
        else:
            out.write('\t\t"" "" ')
        out.write(f'{df} %d %d\n' % (alpha, blend_mode, rtg_flags))
        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_meshes(out, meshes):
        out.write("*MESH {\n")
        for mesh_data in meshes:
            mesh = mesh_data["mesh"]
            ob = mesh_data["object"]
            vertices = mesh.vertices[:]
            unique_vertices, vertex_index_map = unique_ordered(tuple(v.co) for v in vertices)
            colors = color_layer_data(mesh)
            face_flags = int_attribute(mesh, 'euro_fac_flags', 'FACE')

            out.write("\t*NAME %s\n" % mesh_data["shape_name"])
            out.write('\t*VERT_XYXRGBA %d {\n' % len(unique_vertices))
            for vertex in unique_vertices:
                out.write(f'\t\t{df} {df} {df}\n' % (vertex[0], vertex[1], -vertex[2]))
            out.write('\t}\n')

            materials = list(ob.data.materials)
            if EXPORT_MATERIALS and materials:
                for mat_index, mat in enumerate(materials):
                    write_shader(out, mat, mat_index)

            out.write("\t*FACE_LIST {\n")
            for poly in mesh.polygons:
                flag_value = face_flags.data[poly.index].value if face_flags else 0
                shader_index = poly.material_index if poly.material_index < len(materials) else 0
                out.write("\t\t*FACE %d %d %d {\n" % (len(poly.vertices), shader_index, flag_value))
                vertex_indices = [vertex_index_map[tuple(vertices[v].co)] for v in poly.vertices]
                out.write("\t\t\t%s\n" % " ".join(map(str, vertex_indices)))

                if EXPORT_MESH_UV and mesh.uv_layers.active and materials:
                    uv_items = []
                    for loop_index in poly.loop_indices:
                        uv = mesh.uv_layers.active.data[loop_index].uv
                        uv_items.append(f'{uv.x:.6f} {-uv.y:.6f}')
                    mat = materials[shader_index] if shader_index < len(materials) else None
                    tex = texture_path(mat)
                    if tex:
                        uv_items.append(os.path.basename(tex).replace(" ", "_"))
                    out.write("\t\t\t%s\n" % " ".join(uv_items))
                out.write("\t\t}\n")
            out.write("\t}\n")

            if EXPORT_MESH_VCOLORS and colors:
                out.write("\t*FACE_VERTEX_RGB {\n")
                for color_data in colors:
                    color = color_data.color
                    alpha = color[3] if len(color) > 3 else 1.0
                    out.write(f'\t\t{df} {df} {df} {df}\n' % (color[0], color[1], color[2], alpha))
                out.write("\t}\n")
        out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_camera_list(out, cameras):
        if not cameras:
            return
        out.write("*CAMERA_LIST {\n")
        for camera in cameras:
            data = camera.data
            out.write(f'\t%s {df} {df} {df} {df} {df} {df}\n' % (
                hierarchy_name(camera),
                data.angle,
                data.angle,
                data.lens,
                data.clip_start,
                data.clip_end,
                1.0
            ))
        out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_camera_animation(out, scene, cameras, start, end):
        if not cameras:
            return
        out.write("*CAMERA_ANIMATION {\n")
        for camera in cameras:
            out.write("\t%s focalLength " % hierarchy_name(camera))
            for frame in range(start, end + 1):
                scene.frame_set(frame)
                out.write("%u %s " % (frame, df % camera.data.lens))
            out.write("\n")
        out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def cleanup_meshes(meshes):
        for mesh_data in meshes:
            mesh_data["eval"].to_mesh_clear()

    #---------------------------------------------------------------------------------------------------------------------------
    def restore_mode(original_mode):
        if original_mode and original_mode != 'OBJECT' and bpy.ops.object.mode_set.poll():
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except RuntimeError:
                pass

    #---------------------------------------------------------------------------------------------------------------------------
    def write_rtg_file():
        depsgraph = bpy.context.evaluated_depsgraph_get()
        scene = bpy.context.scene
        original_frame = scene.frame_current
        active_object = getattr(context, "object", None)
        original_mode = active_object.mode if active_object else None
        start, end = scene_frame_range(scene)
        meshes = []

        try:
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')

            plugin_version = get_plugin_version()
            cameras = collect_cameras(scene) if 'CAMERA' in EXPORT_OBJECTS else []
            meshes = collect_meshes(scene, depsgraph) if 'MESH' in EXPORT_OBJECTS else []

            with open(filepath, 'w', encoding="utf8") as out:
                out.write("EUROCOM_RTG 5.01\n")
                out.write('*COMMENT "Version of Blender that output this file: %s"\n' % bpy.app.version_string)
                out.write('*COMMENT "Version of RTG Plug-in: %d.%d.%d"\n\n' % (
                    plugin_version[0], plugin_version[1], plugin_version[2]
                ))

                write_material_list(out, meshes)
                write_scene_hierarchy(out, meshes, cameras)

                if EXPORT_CAMERA_LIGHT_ANIMS or EXPORT_MESH_ANIMS:
                    for frame in range(start, end + 1):
                        write_scene_frame(out, scene, meshes, cameras, frame)

                if meshes:
                    write_meshes(out, meshes)

                if cameras:
                    write_camera_list(out, cameras)
                    if EXPORT_CAMERA_LIGHT_ANIMS:
                        write_camera_animation(out, scene, cameras, start, end)
        finally:
            cleanup_meshes(meshes)
            scene.frame_set(original_frame)
            restore_mode(original_mode)

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
           TRANSFORM_TO_CENTER=Transform_Center,
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
    save({},
         str(Path.home()) + '/Desktop/EurocomRTG.rtg',
         Output_Mesh_Definition=True,
         Output_Materials=True,
         Output_Mesh_Anims=False,
         Output_CameraLightAnims=False,
         Transform_Center=False,
         Object_Types={'MESH', 'CAMERA'},
         Output_Mesh_Normals=True,
         Output_Mesh_UV=True,
         Output_Mesh_Vertex_Colors=True,
         Output_Mesh_Morph=False,
         Static_Frame=1,
         Decimal_Precision=6,
         Output_Scale=1.0,
         Enable_Start_From_Frame=False,
         Start_From_Frame=1,
         Enable_End_With_Frame=False,
         End_With_Frame=250,
         Output_First_Only=False)
