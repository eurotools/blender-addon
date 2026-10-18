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
import re
from math import degrees
from pathlib import Path
from mathutils import Matrix
from datetime import datetime
from .eland_utils import *
from .face_layers import (
    color_layers as mapped_color_layers,
    enabled_layer_attributes,
    face_layer_count as configured_face_layer_count,
    face_layer_enabled,
    face_material_index,
    material_layer_attributes,
    uv_layers as mapped_uv_layers,
)

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
           EXTRACT_PACKED_TEXTURES,
           DECIMAL_PRECISION,
           GLOBAL_SCALE,
           REPORT
        ):

    EXPORT_GEOMNODE = True
    EXPORT_PLACENODE = True

    df = f'%.{DECIMAL_PRECISION}f'
    SHADER_RULES = {'Non', 'HPH', 'OPO', 'OMO', 'OPQ', 'Alp'}
    SCENE_LIGHT_SCALE = 1.0
    TEXTURED_DIFFUSE_SCALE = 1.0
    SOLID_DIFFUSE_SCALE = 1.0
    TEXTURE_VERTEX_COLOR_SCALE = 0.5

    def emit_warning(message):
        print(f'WARNING EIF: {message}')
        if REPORT:
            REPORT({'WARNING'}, message)

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
        return any(material_diffuse_image(mat) for mat in materials)

    #---------------------------------------------------------------------------------------------------------------------------
    def material_custom_shader_rule(mat):
        for property_name in ("eif_shader", "euro_shader"):
            if mat and property_name in mat:
                custom_rule = str(mat[property_name])
                if custom_rule in SHADER_RULES:
                    return custom_rule

        return None

    #---------------------------------------------------------------------------------------------------------------------------
    def material_has_alpha(mat):
        # EIF has no scalar material-opacity field.  Its Alp rule consumes the
        # alpha channel of MAP_DIFFUSE, so inferring Alp from a solid Blender
        # material's Principled Alpha creates a shader with no alpha source and
        # EuroLand falls back to the first surface in a layered face.  Preserve
        # explicit overrides, otherwise only infer alpha for an actual RGBA
        # diffuse image.
        if material_custom_shader_rule(mat) == 'Alp':
            return True
        image = material_diffuse_image(mat)
        # Blender commonly exposes RGB images through a four-component pixel
        # buffer too, so channels alone is not proof of a stored alpha channel.
        # Image.depth reflects the source file: 24-bit BMP is RGB, while 32-bit
        # images and 64/128-bit RGBA images can supply alpha.
        return bool(
            image
            and getattr(image, 'channels', 0) >= 4
            and getattr(image, 'depth', 0) in {32, 64, 128}
        )

    #---------------------------------------------------------------------------------------------------------------------------
    def material_shader_rule(mat):
        custom_rule = material_custom_shader_rule(mat)
        if custom_rule:
            return custom_rule

        return 'Alp' if material_has_alpha(mat) else 'Non'

    #---------------------------------------------------------------------------------------------------------------------------
    def material_twosided(mat):
        if mat is None:
            return False
        return not getattr(mat, "use_backface_culling", False)

    #---------------------------------------------------------------------------------------------------------------------------
    def collect_mesh_occurrences(scene, depsgraph):
        occurrences = []

        for obj in scene.objects:
            if obj.type != 'MESH':
                continue
            if obj.parent and obj.parent.instance_type in {'VERTS', 'FACES'}:
                continue
            occurrences.append((obj, obj.matrix_world.copy(), obj.name))

        for instance in depsgraph.object_instances:
            if not instance.is_instance or instance.object.type != 'MESH':
                continue

            source = instance.object.original
            occurrences.append((source, instance.matrix_world.copy(), source.name))

        return occurrences

    #---------------------------------------------------------------------------------------------------------------------------
    def collect_materials(occurrences):
        materials = []
        index_map = {}

        for obj, _matrix, _name in occurrences:
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
            texture_path = export_material_texture_path(mat, filepath, EXTRACT_PACKED_TEXTURES, emit_warning)
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
                out.write('\t\t*MAP_DIFFUSE_AMOUNT 1.00\n')

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
    def parse_user_flag(value):
        try:
            return int(value, 0) if isinstance(value, str) else int(value)
        except (TypeError, ValueError):
            return 0

    #---------------------------------------------------------------------------------------------------------------------------
    def object_user_flags(obj):
        flags = {}
        if obj and "euro_user_flags" in obj:
            value = obj["euro_user_flags"]
            if hasattr(value, '__iter__') and not isinstance(value, str):
                flags.update((index, parse_user_flag(item)) for index, item in enumerate(value))
            else:
                flags[0] = parse_user_flag(value)

        if obj:
            for property_name in obj.keys():
                match = re.fullmatch(r'euro_user_flags?_(\d+)', property_name)
                if match:
                    flags[int(match.group(1))] = parse_user_flag(obj[property_name])

        return sorted(flags.items()) if flags else [(0, 0)]

    #---------------------------------------------------------------------------------------------------------------------------
    def unique_export_name(base_name, used_names):
        if base_name not in used_names:
            used_names.add(base_name)
            return base_name

        suffix = 1
        while True:
            candidate = f"{base_name}.{suffix:03d}"
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
            suffix += 1

    #---------------------------------------------------------------------------------------------------------------------------
    def write_mesh_data(out, occurrences, depsgraph, global_material_indices):
        node_data = []
        used_names = set()

        for ob, ob_mat, base_name in occurrences:
                export_name = unique_export_name(base_name, used_names)
                mesh, ob_eval = transformed_mesh(ob, ob_mat, depsgraph)
                if mesh is None:
                    continue

                try:
                    node_data.append({
                        "name": export_name,
                        "type": ob.type,
                        "object": ob,
                        "matrix_original": ob_mat.copy(),
                        "matrix_transformed": mesh_bake_matrix(ob_mat),
                        "matrix_placement": place_node_matrix(ob_mat)
                    })

                    unique_vertices, vertex_index_map = unique_ordered(tuple(v.co) for v in mesh.vertices)

                    uv_layers = mapped_uv_layers(mesh, EXPORT_UV)
                    present_uv_layers = [layer for layer in uv_layers if layer is not None]
                    unique_uvs, uv_index_map = unique_ordered(
                        tuple(uv_data.uv)
                        for uv_layer in present_uv_layers
                        for uv_data in uv_layer.data
                    ) if present_uv_layers else ([], {})

                    mesh_color_layers = mapped_color_layers(
                        mesh,
                        color_layers(mesh),
                        EXPORT_VERTEX_COLORS,
                    )
                    present_color_layers = [layer for layer in mesh_color_layers if layer is not None]
                    unique_colors, color_index_map = unique_ordered(
                        color_for_loop(mesh, color_layer, loop_index)
                        for color_layer in present_color_layers
                        for loop_index in range(len(mesh.loops))
                    ) if present_color_layers else ([], {})

                    mesh_material_list, mesh_material_indices = mesh_materials(mesh, global_material_indices)
                    has_materials = bool(mesh_material_list)
                    material_layers = material_layer_attributes(mesh) if has_materials else {}
                    enabled_layers = enabled_layer_attributes(mesh)
                    synthesize_texture_color = not unique_colors and has_textured_material(mesh_material_list)
                    if synthesize_texture_color:
                        unique_colors = [(TEXTURE_VERTEX_COLOR_SCALE, TEXTURE_VERTEX_COLOR_SCALE, TEXTURE_VERTEX_COLOR_SCALE, 1.0)]
                    has_face_shaders = EXPORT_FACE_SHADERS and has_materials
                    layer_count = configured_face_layer_count(
                        mesh,
                        uv_layers,
                        mesh_color_layers,
                        has_materials or EXPORT_FACE_SHADERS,
                    )
                    if synthesize_texture_color:
                        layer_count = max(layer_count, 1)

                    def shader_stack_for(poly):
                        stack = []
                        for layer_index in range(layer_count):
                            local_index = face_material_index(
                                mesh, poly, layer_index, material_layers, enabled_layers
                            )
                            if not (0 <= local_index < len(mesh_material_list)):
                                continue
                            stack.append((
                                mesh_material_indices[local_index],
                                material_shader_rule(mesh_material_list[local_index]),
                            ))
                        return tuple(stack)

                    face_shader_stacks = []
                    if has_face_shaders:
                        for poly in mesh.polygons:
                            shader_stack = shader_stack_for(poly)
                            if shader_stack not in face_shader_stacks:
                                face_shader_stacks.append(shader_stack)
                    face_shader_indices = {
                        shader_stack: index
                        for index, shader_stack in enumerate(face_shader_stacks)
                    }

                    face_flags = int_attribute(mesh, 'euro_fac_flags', 'FACE')

                    faceformat = 'V'
                    # EuroLand's own colour-only face-layer EIFs keep the T
                    # component in FACEFORMAT when mapping output is enabled,
                    # even with UVCOUNT 0.  Each missing layer is represented
                    # by -1 indices in the face record.
                    if EXPORT_UV:
                        faceformat += 'T'
                    if (present_color_layers or synthesize_texture_color) and unique_colors:
                        faceformat += 'C'
                    if has_materials:
                        faceformat += 'M'
                    if has_face_shaders:
                        faceformat += 'S'
                    faceformat += 'F'

                    out.write("*MESH {\n")
                    out.write('\t*NAME "%s"\n' % export_name)
                    out.write('\t*VERTCOUNT %d\n' % len(unique_vertices))
                    out.write('\t*UVCOUNT %d\n' % len(unique_uvs))
                    out.write('\t*VERTCOLCOUNT %d\n' % len(unique_colors))
                    out.write('\t*FACECOUNT %d\n' % len(mesh.polygons))
                    out.write('\t*TRIFACECOUNT %d\n' % (sum(len(face.loop_indices) - 2 for face in mesh.polygons)))
                    out.write('\t*FACELAYERSCOUNT %d\n' % layer_count)
                    if has_face_shaders:
                        out.write('\t*FACESHADERCOUNT %d\n' % len(face_shader_stacks))

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
                        for shader_index, shader_stack in enumerate(face_shader_stacks):
                            out.write('\t\t*SHADER %d {\n' % shader_index)
                            for material_global_index, shader_rule in shader_stack:
                                out.write('\t\t\t%d\t%s\n' % (material_global_index, shader_rule))
                            out.write('\t\t}\n')
                        out.write('\t}\n')

                    out.write('\t*FACEFORMAT %s\n' % faceformat)
                    out.write("\t*FACE_LIST {\n")

                    for poly in mesh.polygons:
                        vertex_indices = [vertex_index_map[tuple(mesh.vertices[v].co)] for v in poly.vertices]
                        out.write("\t\t%d %s " % (len(poly.vertices), " ".join(map(str, vertex_indices))))

                        if EXPORT_UV:
                            for layer_index in range(layer_count):
                                uv_layer = (
                                    uv_layers[layer_index]
                                    if layer_index < len(uv_layers)
                                    else None
                                )
                                if uv_layer is not None and face_layer_enabled(
                                    mesh, poly.index, layer_index, material_layers, enabled_layers
                                ):
                                    uv_indices = []
                                    for loop_index in poly.loop_indices:
                                        uv = tuple(uv_layer.data[loop_index].uv)
                                        uv_indices.append(uv_index_map.get(uv, -1))
                                    out.write("%s " % " ".join(map(str, uv_indices)))
                                else:
                                    out.write("%s " % " ".join(["-1"] * len(poly.vertices)))

                        if (present_color_layers or synthesize_texture_color) and unique_colors:
                            for layer_index in range(layer_count):
                                layer_is_enabled = face_layer_enabled(
                                    mesh, poly.index, layer_index, material_layers, enabled_layers
                                )
                                if synthesize_texture_color and layer_is_enabled:
                                    out.write("%s " % " ".join(["0"] * len(poly.vertices)))
                                elif mesh_color_layers[layer_index] is not None and layer_is_enabled:
                                    color_indices = []
                                    for loop_index in poly.loop_indices:
                                        color = color_for_loop(mesh, mesh_color_layers[layer_index], loop_index)
                                        color_indices.append(color_index_map.get(color, -1))
                                    out.write("%s " % " ".join(map(str, color_indices)))
                                else:
                                    out.write("%s " % " ".join(["-1"] * len(poly.vertices)))

                        if has_materials:
                            for layer_index in range(layer_count):
                                local_material_index = face_material_index(
                                    mesh, poly, layer_index, material_layers, enabled_layers
                                )

                                material_index = (
                                    mesh_material_indices[local_material_index]
                                    if 0 <= local_material_index < len(mesh_material_indices)
                                    else -1
                                )
                                out.write("%d " % material_index)

                        if has_face_shaders:
                            shader_index = face_shader_indices.get(shader_stack_for(poly), 0)
                            out.write("%d " % shader_index)

                        flag_value = face_flags.data[poly.index].value if face_flags else 0
                        out.write('%d\n' % flag_value)

                    out.write("\t}\n")
                    out.write("}\n\n")
                finally:
                    ob_eval.to_mesh_clear()

        return node_data

    #---------------------------------------------------------------------------------------------------------------------------
    def write_geom_and_place_node(out, obj_matrix_data, is_geom_node=False):
        for data in obj_matrix_data:
            mesh_name = data["name"]
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
                user_flags = object_user_flags(data["object"])
                out.write('\t*USER_FLAGS_COUNT %u\n' % len(user_flags))
                out.write('\t*USER_FLAGS {\n')
                for flag_index, flag_value in user_flags:
                    out.write('\t\t*SET %u 0x%08X\n' % (flag_index, flag_value & 0xFFFFFFFF))
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
    def validate_export(occurrences):
        warnings = set()
        checked_objects = set()

        for obj, _matrix, _name in occurrences:
            pointer = obj.as_pointer()
            if pointer in checked_objects:
                continue
            checked_objects.add(pointer)

            materials = [slot.material for slot in obj.material_slots if slot.material]
            images = [material_diffuse_image(mat) for mat in materials]
            images = [image for image in images if image]
            if images and (not EXPORT_UV or not obj.data.uv_layers):
                warnings.add(f'Textured mesh {obj.name} has no exported UV coordinates.')
            for image in images:
                if not image.filepath and not (image.packed_file and EXTRACT_PACKED_TEXTURES):
                    warnings.add(f'Image {image.name} has no file path and cannot be referenced by EuroLand.')

            for mat in materials:
                principled = material_principled_node(mat)
                base_color = principled.inputs.get('Base Color') if principled else None
                if base_color and base_color.is_linked and not material_diffuse_image(mat):
                    warnings.add(f'Material {mat.name} uses a procedural Base Color and must be baked to an image.')

        for warning in sorted(warnings):
            emit_warning(warning)

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
            occurrences = collect_mesh_occurrences(scene, depsgraph)
            validate_export(occurrences)
            materials, material_indices = collect_materials(occurrences)

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
                mesh_position_data = write_mesh_data(out, occurrences, depsgraph, material_indices)

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
         Output_Scale,
         Extract_Packed_Textures=True,
         report=None):

    _write(context, filepath,
           EXPORT_GEOMNODE=Output_GeomNode,
           EXPORT_PLACENODE=Output_PlaceNode,
           TRANSFORM_TO_CENTER=Transform_Center,
           EXPORT_UV=Output_Mesh_UV,
           EXPORT_VERTEX_COLORS=Output_Mesh_Vertex_Colors,
           EXPORT_FACE_SHADERS=Output_Face_Shaders,
           EXTRACT_PACKED_TEXTURES=Extract_Packed_Textures,
           DECIMAL_PRECISION=Decimal_Precision,
           GLOBAL_SCALE=Output_Scale,
           REPORT=report)

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
         Extract_Packed_Textures=True,
         Decimal_Precision=6,
         Output_Scale=1.0)
