#  Copyright (c) 2020-2021 Swyter <swyterzone+sphinx@gmail.com>
#  SPDX-License-Identifier: Zlib

"""
Name: 'Eurocom Interchange File'
Blender: 4.3.2
Group: 'Export'
Tooltip: 'Blender EIF Exporter for EuroLand'
Authors: Swyter and Jmarti856
"""

import bpy
from math import degrees
from pathlib import Path
from mathutils import Matrix
from datetime import datetime
from .eland_utils import *

#-------------------------------------------------------------------------------------------------------------------------------
EXPORT_TRI = False
EXPORT_APPLY_MODIFIERS = True


#-------------------------------------------------------------------------------------------------------------------------------
def _write(context, filepath,
           EXPORT_GEOMNODE,
           EXPORT_PLACENODE,
           TRANSFORM_TO_CENTER,
           EXPORT_UV,
           EXPORT_VERTEX_COLORS,
           EXPORT_FACE_SHADERS,
           DECIMAL_PRECISION,
           GLOBAL_SCALE
        ):

    EXPORT_GEOMNODE = True
    EXPORT_PLACENODE = True

    df = f'%.{DECIMAL_PRECISION}f'
    SHADER_RULES = {'Non', 'HPH', 'OPO', 'OMO', 'OPQ', 'Alp'}
    SCENE_LIGHT_SCALE = 1.0
    TEXTURED_DIFFUSE_SCALE = 1.0
    SOLID_DIFFUSE_SCALE = 1.0
    MAP_AMOUNT_SCALE = 1.0
    TEXTURE_VERTEX_COLOR_SCALE = 0.5

    #---------------------------------------------------------------------------------------------------------------------------
    def material_diffuse(mat):
        mat_wrap = material_wrap(mat)
        if mat_wrap:
            return mat_wrap.base_color[:3]
        if mat:
            return mat.diffuse_color[:3]
        return (0.8, 0.8, 0.8)

    #---------------------------------------------------------------------------------------------------------------------------
    def has_textured_material(materials):
        return any(material_texture_path(mat) for mat in materials)

    #---------------------------------------------------------------------------------------------------------------------------
    def material_map_amount(mat):
        mat_wrap = material_wrap(mat)
        if mat_wrap and mat_wrap.metallic != 0.0:
            return mat_wrap.metallic
        return 1.0

    #---------------------------------------------------------------------------------------------------------------------------
    def material_has_alpha(mat):
        if mat is None:
            return False

        mat_wrap = material_wrap(mat)
        alpha = mat_wrap.alpha if mat_wrap else mat.diffuse_color[3]
        if alpha < 0.999:
            return True

        blend_method = getattr(mat, "blend_method", "OPAQUE")
        if blend_method in {'BLEND', 'HASHED', 'CLIP'}:
            return True

        texture_path = material_texture_path(mat)
        return bool(texture_path and texture_path.lower().endswith((".tga", ".png")))

    #---------------------------------------------------------------------------------------------------------------------------
    def material_shader_rule(mat):
        if mat and "eif_shader" in mat:
            custom_rule = str(mat["eif_shader"])
            if custom_rule in SHADER_RULES:
                return custom_rule

        mat_wrap = material_wrap(mat)
        alpha = mat_wrap.alpha if mat_wrap else (mat.diffuse_color[3] if mat else 1.0)
        blend_method = getattr(mat, "blend_method", "OPAQUE") if mat else "OPAQUE"

        return 'Non'

    #---------------------------------------------------------------------------------------------------------------------------
    def material_twosided(mat):
        if mat is None:
            return False
        return not getattr(mat, "use_backface_culling", False)

    #---------------------------------------------------------------------------------------------------------------------------
    def collect_materials(scene):
        materials = []
        index_map = {}

        for obj in scene.objects:
            if obj.type != 'MESH':
                continue

            for slot in obj.material_slots:
                mat = slot.material
                key = mat.name if mat else "Default"
                if key not in index_map:
                    index_map[key] = len(materials)
                    materials.append(mat)

        return materials, index_map

    #---------------------------------------------------------------------------------------------------------------------------
    def mesh_materials(mesh, global_material_indices):
        materials = list(mesh.materials)
        if not materials:
            return [], []

        material_indices = []
        for mat in materials:
            key = mat.name if mat else "Default"
            material_indices.append(global_material_indices.get(key, -1))

        return materials, material_indices

    #---------------------------------------------------------------------------------------------------------------------------
    def write_scene_data(out, scene):
        world_amb = (scene.world.color.r, scene.world.color.g, scene.world.color.b) if scene.world else (0.8, 0.8, 0.8)
        export_amb = scaled_color(world_amb, SCENE_LIGHT_SCALE)

        out.write("*SCENE {\n")
        out.write('\t*FILENAME "%s"\n' % bpy.data.filepath)
        out.write('\t*FIRSTFRAME %s\n' % scene.frame_start)
        out.write('\t*LASTFRAME %s\n' % scene.frame_end)
        out.write('\t*FRAMESPEED %s\n' % scene.render.fps)
        out.write('\t*STATICFRAME %s\n' % scene.frame_current)
        out.write(f'\t*AMBIENTSTATIC {df} {df} {df}\n' % export_amb)
        out.write("}\n\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_materials(out, materials):
        out.write('*MATERIALS {\n')

        for index, mat in enumerate(materials):
            name = mat.name if mat else "Default"
            diffuse = material_diffuse(mat)
            texture_path = material_texture_path(mat)
            export_diffuse = (
                (TEXTURED_DIFFUSE_SCALE, TEXTURED_DIFFUSE_SCALE, TEXTURED_DIFFUSE_SCALE)
                if texture_path
                else scaled_color(diffuse, SOLID_DIFFUSE_SCALE)
            )

            out.write('\t*MATERIAL %d {\n' % index)
            out.write('\t\t*NAME "%s"\n' % name)
            out.write(f'\t\t*COL_DIFFUSE {df} {df} {df}\n' % export_diffuse)

            if texture_path:
                out.write('\t\t*MAP_DIFFUSE "%s"\n' % texture_path)
                out.write('\t\t*MAP_DIFFUSE_AMOUNT %.2f\n' % (material_map_amount(mat) * MAP_AMOUNT_SCALE))

            if material_has_alpha(mat):
                out.write('\t\t*MAP_HASALPHA\n')

            if material_twosided(mat):
                out.write('\t\t*TWOSIDED\n')

            out.write('\t}\n')

        out.write('}\n\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def mesh_bake_matrix(ob_mat):
        if TRANSFORM_TO_CENTER:
            return Matrix.Identity(4)

        return ob_mat.copy()

    #---------------------------------------------------------------------------------------------------------------------------
    def place_node_matrix(ob_mat):
        if TRANSFORM_TO_CENTER:
            matrix = ob_mat.copy()
            matrix.translation = matrix.translation * GLOBAL_SCALE
            return matrix

        return Matrix.Identity(4)

    #---------------------------------------------------------------------------------------------------------------------------
    def mesh_node_matrix(matrix):
        matrix = matrix.copy()
        rot_matrix = matrix.to_3x3().normalized().to_4x4()
        export_eland = create_euroland_matrix(rot_matrix, 'MESH')["eland_matrix"].to_3x3()

        export_eland.transpose()
        scale = matrix.to_scale()
        scale_values = (scale.x, scale.z, scale.y)
        for row_index, scale_value in enumerate(scale_values):
            export_eland[row_index][0] *= scale_value
            export_eland[row_index][1] *= scale_value
            export_eland[row_index][2] *= scale_value

        result = export_eland.to_4x4()
        position = MESH_GLOBAL_MATRIX @ matrix.translation
        result[0][3] = position.x
        result[1][3] = position.y
        result[2][3] = position.z
        return result

    #---------------------------------------------------------------------------------------------------------------------------
    def transformed_mesh(ob, ob_mat, depsgraph):
        ob_eval = ob.evaluated_get(depsgraph) if EXPORT_APPLY_MODIFIERS else ob.original

        try:
            mesh = ob_eval.to_mesh()
        except RuntimeError:
            return None, None

        if mesh is None:
            return None, ob_eval

        if EXPORT_TRI:
            mesh_triangulate(mesh)

        matrix_transformed = mesh_bake_matrix(ob_mat)

        mesh.transform(Matrix.Scale(GLOBAL_SCALE, 4) @ (MESH_GLOBAL_MATRIX @ matrix_transformed))

        if (MESH_GLOBAL_MATRIX @ matrix_transformed).determinant() < 0.0:
            mesh.flip_normals()

        return mesh, ob_eval

    #---------------------------------------------------------------------------------------------------------------------------
    def face_layer_count(mesh, uv_layers, mesh_color_layers, has_materials):
        layer_count = max(
            len(uv_layers) if EXPORT_UV else 0,
            len(mesh_color_layers) if EXPORT_VERTEX_COLORS else 0,
            1 if has_materials or EXPORT_FACE_SHADERS else 0
        )
        return max(1, layer_count)

    #---------------------------------------------------------------------------------------------------------------------------
    def write_mesh_data(out, scene, depsgraph, global_material_indices):
        matrix_data = {}

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
                mesh, ob_eval = transformed_mesh(ob, ob_mat, depsgraph)
                if mesh is None:
                    continue

                try:
                    matrix_data[ob_main.name] = {
                        "type": ob_main.type,
                        "matrix_original": ob_mat.copy(),
                        "matrix_transformed": mesh_bake_matrix(ob_mat),
                        "matrix_placement": place_node_matrix(ob_mat)
                    }

                    unique_vertices, vertex_index_map = unique_ordered(tuple(v.co) for v in mesh.vertices)

                    uv_layers = list(mesh.uv_layers) if EXPORT_UV else []
                    unique_uvs, uv_index_map = unique_ordered(
                        tuple(uv_data.uv)
                        for uv_layer in uv_layers
                        for uv_data in uv_layer.data
                    ) if uv_layers else ([], {})

                    mesh_color_layers = color_layers(mesh) if EXPORT_VERTEX_COLORS else []
                    unique_colors, color_index_map = unique_ordered(
                        tuple(color_data.color)
                        for color_layer in mesh_color_layers
                        for color_data in color_layer.data
                    ) if mesh_color_layers else ([], {})

                    mesh_material_list, mesh_material_indices = mesh_materials(mesh, global_material_indices)
                    has_materials = bool(mesh_material_list)
                    synthesize_texture_color = not unique_colors and has_textured_material(mesh_material_list)
                    if synthesize_texture_color:
                        unique_colors = [(TEXTURE_VERTEX_COLOR_SCALE, TEXTURE_VERTEX_COLOR_SCALE, TEXTURE_VERTEX_COLOR_SCALE, 1.0)]
                    has_face_shaders = EXPORT_FACE_SHADERS and has_materials
                    layer_count = face_layer_count(mesh, uv_layers, mesh_color_layers, has_materials)
                    if synthesize_texture_color:
                        layer_count = max(layer_count, 1)

                    face_flags = int_attribute(mesh, 'euro_fac_flags', 'FACE')

                    faceformat = 'V'
                    if uv_layers and unique_uvs:
                        faceformat += 'T'
                    if (mesh_color_layers or synthesize_texture_color) and unique_colors:
                        faceformat += 'C'
                    if has_materials:
                        faceformat += 'M'
                    if has_face_shaders:
                        faceformat += 'S'
                    faceformat += 'F'

                    out.write("*MESH {\n")
                    out.write('\t*NAME "%s"\n' % ob_main.name)
                    out.write('\t*VERTCOUNT %d\n' % len(unique_vertices))
                    out.write('\t*UVCOUNT %d\n' % len(unique_uvs))
                    out.write('\t*VERTCOLCOUNT %d\n' % len(unique_colors))
                    out.write('\t*FACECOUNT %d\n' % len(mesh.polygons))
                    out.write('\t*TRIFACECOUNT %d\n' % (sum(len(face.loop_indices) - 2 for face in mesh.polygons)))
                    out.write('\t*FACELAYERSCOUNT %d\n' % layer_count)
                    if has_face_shaders:
                        out.write('\t*FACESHADERCOUNT %d\n' % len(mesh_material_list))

                    out.write('\t*VERTEX_LIST {\n')
                    for vertex in unique_vertices:
                        out.write(f'\t\t{df} {df} {df}\n' % vertex)
                    out.write('\t}\n')

                    if EXPORT_UV:
                        out.write('\t*UV_LIST {\n')
                        for uv in unique_uvs:
                            out.write(f'\t\t{df} {df}\n' % (uv[0], -uv[1]))
                        out.write('\t}\n')

                    if EXPORT_VERTEX_COLORS or synthesize_texture_color:
                        out.write('\t*VERTCOL_LIST {\n')
                        for color in unique_colors:
                            alpha = color[3] if len(color) > 3 else 1.0
                            out.write(f'\t\t{df} {df} {df} {df}\n' % (color[0], color[1], color[2], alpha))
                        out.write('\t}\n')

                    if has_face_shaders:
                        out.write('\t*FACESHADERS {\n')
                        for shader_index, mat in enumerate(mesh_material_list):
                            material_global_index = mesh_material_indices[shader_index]
                            out.write('\t\t*SHADER %d {\n' % shader_index)
                            out.write('\t\t\t%d\t%s\n' % (material_global_index, material_shader_rule(mat)))
                            out.write('\t\t}\n')
                        out.write('\t}\n')

                    out.write('\t*FACEFORMAT %s\n' % faceformat)
                    out.write("\t*FACE_LIST {\n")

                    for poly in mesh.polygons:
                        vertex_indices = [vertex_index_map[tuple(mesh.vertices[v].co)] for v in poly.vertices]
                        out.write("\t\t%d %s " % (len(poly.vertices), " ".join(map(str, vertex_indices))))

                        if uv_layers and unique_uvs:
                            for layer_index in range(layer_count):
                                if layer_index < len(uv_layers):
                                    uv_indices = []
                                    for loop_index in poly.loop_indices:
                                        uv = tuple(uv_layers[layer_index].data[loop_index].uv)
                                        uv_indices.append(uv_index_map.get(uv, -1))
                                    out.write("%s " % " ".join(map(str, uv_indices)))
                                else:
                                    out.write("%s " % " ".join(["-1"] * len(poly.vertices)))

                        if (mesh_color_layers or synthesize_texture_color) and unique_colors:
                            for layer_index in range(layer_count):
                                if synthesize_texture_color:
                                    out.write("%s " % " ".join(["0"] * len(poly.vertices)))
                                elif layer_index < len(mesh_color_layers):
                                    color_indices = []
                                    for loop_index in poly.loop_indices:
                                        color = tuple(mesh_color_layers[layer_index].data[loop_index].color)
                                        color_indices.append(color_index_map.get(color, -1))
                                    out.write("%s " % " ".join(map(str, color_indices)))
                                else:
                                    out.write("%s " % " ".join(["-1"] * len(poly.vertices)))

                        if has_materials:
                            material_index = mesh_material_indices[poly.material_index] if poly.material_index < len(mesh_material_indices) else mesh_material_indices[0]
                            for layer_index in range(layer_count):
                                out.write("%d " % (material_index if layer_index == 0 else -1))

                        if has_face_shaders:
                            shader_index = poly.material_index if poly.material_index < len(mesh_material_list) else 0
                            out.write("%d " % shader_index)

                        flag_value = face_flags.data[poly.index].value if face_flags else 0
                        out.write('%d\n' % flag_value)

                    out.write("\t}\n")
                    out.write("}\n\n")
                finally:
                    ob_eval.to_mesh_clear()

        return matrix_data

    #---------------------------------------------------------------------------------------------------------------------------
    def write_geom_and_place_node(out, obj_matrix_data, is_geom_node=False):
        for mesh_name, data in obj_matrix_data.items():
            if is_geom_node:
                matrix_data = Matrix.Identity(4)
                out.write('*GEOMNODE {\n')
            else:
                matrix_data = data["matrix_placement"]
                out.write('*PLACENODE {\n')

            out.write('\t*NAME "%s"\n' % mesh_name)
            out.write('\t*MESH "%s"\n' % mesh_name)
            out.write('\t*WORLD_TM {\n')

            if data["type"] == 'MESH':
                eland_matrix = mesh_node_matrix(matrix_data)
                eland_euler = eland_matrix.to_euler('ZXY')
            else:
                eland_data = create_euroland_matrix(matrix_data, data["type"])
                eland_matrix = eland_data["eland_matrix"]
                eland_euler = eland_data["eland_euler"]

            out.write(f'\t\t*TMROW0 {df} {df} {df} {df}\n' % (eland_matrix[0].x, eland_matrix[0].y, eland_matrix[0].z, 0))
            out.write(f'\t\t*TMROW1 {df} {df} {df} {df}\n' % (eland_matrix[1].x, eland_matrix[1].y, eland_matrix[1].z, 0))
            out.write(f'\t\t*TMROW2 {df} {df} {df} {df}\n' % (eland_matrix[2].x, eland_matrix[2].y, eland_matrix[2].z, 0))

            obj_position = eland_matrix.translation
            out.write(f'\t\t*TMROW3 {df} {df} {df} {df}\n' % (obj_position.x, obj_position.y, obj_position.z, 1))
            out.write(f'\t\t*POS {df} {df} {df}\n' % (obj_position.x, obj_position.y, obj_position.z))
            out.write(f'\t\t*ROT: {df} {df} {df}\n' % (degrees(eland_euler.x), degrees(eland_euler.z), degrees(eland_euler.y)))

            transformed_scale = eland_matrix.to_scale()
            out.write(f'\t\t*SCL {df} {df} {df}\n' % (transformed_scale.x, transformed_scale.z, transformed_scale.y))
            out.write('\t}\n')

            if is_geom_node:
                out.write('\t*USER_FLAGS_COUNT %u\n' % 1)
                out.write('\t*USER_FLAGS {\n')
                out.write('\t\t*SET 0 0x00000000\n')
                out.write('\t}\n')

            out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def restore_mode(original_mode):
        if original_mode and original_mode != 'OBJECT' and bpy.ops.object.mode_set.poll():
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except RuntimeError:
                pass

    #---------------------------------------------------------------------------------------------------------------------------
    def write_eif_file():
        depsgraph = bpy.context.evaluated_depsgraph_get()
        scene = bpy.context.scene
        original_frame = scene.frame_current
        active_object = getattr(context, "object", None)
        original_mode = active_object.mode if active_object else None

        try:
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')

            plugin_version = get_plugin_version()
            materials, material_indices = collect_materials(scene)

            with open(filepath, 'w', encoding="utf8") as out:
                out.write("*EUROCOM_INTERCHANGE_FILE 100\n")
                out.write('*COMMENT Eurocom Interchange File Version 1.00 %s\n' % datetime.now().strftime("%A %B %d %Y %H:%M"))
                out.write('*COMMENT Version of eif-plugin that wrote this file %d.%d\n' % (plugin_version[0], plugin_version[1]))
                out.write('*COMMENT Version of blender that wrote this file %s\n\n' % bpy.app.version_string)
                out.write("*OPTIONS {\n")
                out.write("\t*COORD_SYSTEM LH\n")
                out.write("}\n\n")

                write_scene_data(out, scene)
                write_materials(out, materials)
                mesh_position_data = write_mesh_data(out, scene, depsgraph, material_indices)

                if EXPORT_GEOMNODE:
                    write_geom_and_place_node(out, mesh_position_data, True)

                if EXPORT_PLACENODE:
                    write_geom_and_place_node(out, mesh_position_data)
        finally:
            scene.frame_set(original_frame)
            restore_mode(original_mode)

    write_eif_file()


#-------------------------------------------------------------------------------------------------------------------------------
def save(context,
         filepath,
         *,
         Output_GeomNode,
         Output_PlaceNode,
         Transform_Center,
         Output_Mesh_UV,
         Output_Mesh_Vertex_Colors,
         Output_Face_Shaders,
         Decimal_Precision,
         Output_Scale):

    _write(context, filepath,
           EXPORT_GEOMNODE=Output_GeomNode,
           EXPORT_PLACENODE=Output_PlaceNode,
           TRANSFORM_TO_CENTER=Transform_Center,
           EXPORT_UV=Output_Mesh_UV,
           EXPORT_VERTEX_COLORS=Output_Mesh_Vertex_Colors,
           EXPORT_FACE_SHADERS=Output_Face_Shaders,
           DECIMAL_PRECISION=Decimal_Precision,
           GLOBAL_SCALE=Output_Scale)

    return {'FINISHED'}


if __name__ == '__main__':
    save({},
         str(Path.home()) + '/Desktop/EurocomEIF.eif',
         Output_GeomNode=True,
         Output_PlaceNode=True,
         Transform_Center=True,
         Output_Mesh_UV=True,
         Output_Mesh_Vertex_Colors=True,
         Output_Face_Shaders=True,
         Decimal_Precision=6,
         Output_Scale=1.0)
