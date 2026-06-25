#  Copyright (c) 2020-2021 Swyter <swyterzone+sphinx@gmail.com>
#  SPDX-License-Identifier: Zlib

"""
Name: 'Eurocom Scene Export'
Blender: 4.3.2
Group: 'Export'
Tooltip: 'Blender ESE Exporter for EuroLand'
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

# Global variables
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
    SCENE_LIGHT_SCALE = 1.0
    TEXTURED_DIFFUSE_SCALE = 0.5
    SOLID_DIFFUSE_SCALE = 1.0
    MAP_AMOUNT_SCALE = 1.0
    TEXTURE_VERTEX_COLOR_SCALE = 0.5

    #---------------------------------------------------------------------------------------------------------------------------
    def material_shader_rule(mat):
        if mat and "euro_shader" in mat:
            custom_rule = str(mat["euro_shader"])
            if custom_rule in {'Non', 'HPH', 'OPO', 'OMO', 'OPQ', 'Alp'}:
                return custom_rule

        if mat and "eif_shader" in mat:
            custom_rule = str(mat["eif_shader"])
            if custom_rule in {'Non', 'HPH', 'OPO', 'OMO', 'OPQ', 'Alp'}:
                return custom_rule

        return 'Non'

    #---------------------------------------------------------------------------------------------------------------------------
    def material_has_texture(mat):
        mat_wrap = PrincipledBSDFWrapper(mat) if mat and mat.use_nodes else None
        if not mat_wrap:
            return False

        tex_wrap = getattr(mat_wrap, "base_color_texture", None)
        return bool(tex_wrap and tex_wrap.image)

    #---------------------------------------------------------------------------------------------------------------------------
    def has_textured_material(materials):
        return any(material_has_texture(mat) for mat in materials)

    #---------------------------------------------------------------------------------------------------------------------------
    def scaled_color(color, scale):
        return tuple(max(0.0, min(component * scale, 1.0)) for component in color[:3])

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
    def int_attribute(mesh, name, domain):
        attr = mesh.attributes.get(name)
        if attr and attr.data_type == 'INT' and attr.domain == domain:
            return attr
        return None

    #---------------------------------------------------------------------------------------------------------------------------
    def parent_name(obj):
        return obj.parent.name if obj.parent else None

    #---------------------------------------------------------------------------------------------------------------------------
    def write_parent(out, obj, tab_level=1):
        parent = parent_name(obj)
        if parent:
            out.write('%s*NODE_PARENT "%s"\n' % (get_tabs(tab_level), parent))

    #---------------------------------------------------------------------------------------------------------------------------
    def write_scene_custom_properties(out):
        scene = bpy.context.scene
        custom_properties = {key: value for key, value in scene.items() if key != '_RNA_UI'}
        visible_properties = {
            key: value for key, value in custom_properties.items()
            if isinstance(value, (int, float, str, bool))
        }
        type_mapping = {
            int: "Numeric",
            float: "Numeric",
            str: "String",
            bool: "Boolean"
        }

        properties_list = []
        for key, value in visible_properties.items():
            type_name = type_mapping.get(type(value), type(value).__name__)
            properties_list.append({"name": key, "type": type_name, "value": value})

        if user_wants_camera_script(scene):
            properties_list.append({
                "name": "cameraScriptEditor",
                "type": "Numeric",
                "value": 1
            })

            current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            computer_name = platform.node()
            blender_version = bpy.app.version_string
            properties_list.append({
                "name": "cameraScriptEditor Info",
                "type": "String",
                "value": f"{current_time} Computer:{computer_name} UserName:{computer_name} BlenderVer:#({blender_version})"
            })

        out.write('\t*SCENE_UDPROPS {\n')
        out.write('\t\t*PROP_COUNT\t%d\n' % len(properties_list))
        for index, prop in enumerate(properties_list):
            out.write('\t\t*PROP\t%d\t"%s"\t"%s"\t"%s"\n' % (index, prop["name"], prop["type"], prop["value"]))
        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_scene_data(out, scene):
        global FRAMES_COUNT, TICKS_PER_FRAME, START_FRAME, END_FRAME

        START_FRAME = scene.frame_start
        END_FRAME = scene.frame_end

        if EXPORT_FROM_FRAME_ENABLED:
            START_FRAME = max(START_FRAME, EXPORT_FROM_FRAME)
        if EXPORT_END_FRAME_ENABLED:
            END_FRAME = min(END_FRAME, EXPORT_END_FRAME)
        if END_FRAME < START_FRAME:
            END_FRAME = START_FRAME

        scene.frame_set(EXPORT_STATIC_FRAME)

        frame_rate = scene.render.fps
        FRAMES_COUNT = END_FRAME - START_FRAME + 1

        tick_frequency = 4800
        TICKS_PER_FRAME = max(1, tick_frequency // max(1, frame_rate))

        world_amb = scene.world.color if scene.world else (0.8, 0.8, 0.8)
        export_amb = scaled_color(world_amb, SCENE_LIGHT_SCALE)

        out.write("*SCENE {\n")
        out.write('\t*SCENE_FILENAME "%s"\n' % bpy.data.filepath)
        out.write('\t*SCENE_FIRSTFRAME %s\n' % START_FRAME)
        out.write('\t*SCENE_LASTFRAME %s\n' % END_FRAME)
        out.write('\t*SCENE_FRAMESPEED %s\n' % frame_rate)
        out.write('\t*SCENE_TICKSPERFRAME %s\n' % TICKS_PER_FRAME)
        out.write(f'\t*SCENE_BACKGROUND_STATIC {df} {df} {df}\n' % export_amb)
        out.write(f'\t*SCENE_AMBIENT_STATIC {df} {df} {df}\n' % export_amb)
        write_scene_custom_properties(out)
        out.write("}\n\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_material_data(out, mat, tab_level, include_texture):
        tab = get_tabs(tab_level)
        mat_name = mat.name if mat else "Default"

        out.write(f'{tab}*MATERIAL_NAME "%s"\n' % mat_name)
        out.write(f'{tab}*MATERIAL_CLASS "Standard"\n')

        mat_wrap = PrincipledBSDFWrapper(mat) if mat and mat.use_nodes else None

        if mat_wrap:
            use_mirror = mat_wrap.metallic > 0.001
            specular = mat_wrap.specular if use_mirror else 0.0
            emission_color = getattr(mat_wrap, "emission_color", (0.0, 0.0, 0.0))
            emission_level = max(emission_color[:3]) if emission_color else 0.0
            self_illum = max(0.0, min(mat_wrap.emission_strength * emission_level, 1.0))
            textured = include_texture and getattr(mat_wrap, "base_color_texture", None) and mat_wrap.base_color_texture.image
            diffuse = (
                (TEXTURED_DIFFUSE_SCALE, TEXTURED_DIFFUSE_SCALE, TEXTURED_DIFFUSE_SCALE)
                if textured
                else scaled_color(mat_wrap.base_color, SOLID_DIFFUSE_SCALE)
            )

            out.write(f'{tab}*MATERIAL_AMBIENT {df} {df} {df}\n' % (0.0, 0.0, 0.0))
            out.write(f'{tab}*MATERIAL_DIFFUSE {df} {df} {df}\n' % diffuse)
            out.write(f'{tab}*MATERIAL_SPECULAR {df} {df} {df}\n' % (specular, specular, specular))
            out.write(f'{tab}*MATERIAL_SHINE %.1f\n' % ((1.0 - mat_wrap.roughness) if use_mirror else 0.0))
            out.write(f'{tab}*MATERIAL_SHINESTRENGTH %.1f\n' % 0.0)
            out.write(f'{tab}*MATERIAL_TRANSPARENCY %.1f\n' % (1.0 - mat_wrap.alpha))
            out.write(f'{tab}*MATERIAL_WIRESIZE %.1f\n' % 1.0)
            out.write(f'{tab}*MATERIAL_SHADING Blinn\n')
            out.write(f'{tab}*MATERIAL_XP_FALLOFF %.1f\n' % 0.0)
            out.write(f'{tab}*MATERIAL_SELFILLUM %.1f\n' % self_illum)
            out.write(f'{tab}*MATERIAL_FALLOFF In\n')
            out.write(f'{tab}*MATERIAL_XP_TYPE Filter\n')

            if include_texture:
                tex_wrap = getattr(mat_wrap, "base_color_texture", None)
                image = tex_wrap.image if tex_wrap else None

                if image:
                    out.write(f'{tab}*MAP_DIFFUSE {{\n')
                    out.write(f'{tab}\t*MAP_NAME "%s"\n' % image.name)
                    out.write(f'{tab}\t*MAP_CLASS "Bitmap"\n')
                    out.write(f'{tab}\t*MAP_SUBNO 1\n')
                    out.write(f'{tab}\t*MAP_AMOUNT %.2f\n' % (mat_wrap.metallic if use_mirror else MAP_AMOUNT_SCALE))
                    out.write(f'{tab}\t*BITMAP "%s"\n' % bpy.path.abspath(image.filepath))
                    out.write(f'{tab}\t*MAP_TYPE Screen\n')
                    out.write(f'{tab}\t*UVW_U_OFFSET %.1f\n' % 0.0)
                    out.write(f'{tab}\t*UVW_V_OFFSET %.1f\n' % 0.0)
                    out.write(f'{tab}\t*UVW_U_TILING %.1f\n' % 1.0)
                    out.write(f'{tab}\t*UVW_V_TILING %.1f\n' % 1.0)
                    out.write(f'{tab}\t*UVW_ANGLE %.1f\n' % 0.0)
                    out.write(f'{tab}\t*UVW_BLUR %.1f\n' % 1.0)
                    out.write(f'{tab}\t*UVW_BLUR_OFFSET %.1f\n' % 0.0)
                    out.write(f'{tab}\t*UVW_NOUSE_AMT %.1f\n' % 1.0)
                    out.write(f'{tab}\t*UVW_NOISE_SIZE %.1f\n' % 1.0)
                    out.write(f'{tab}\t*UVW_NOISE_LEVEL 1\n')
                    out.write(f'{tab}\t*UVW_NOISE_PHASE %.1f\n' % 0.0)
                    out.write(f'{tab}\t*BITMAP_FILTER Pyramidal\n')
                    out.write(f'{tab}}}\n')
        else:
            diffuse = mat.diffuse_color if mat else (0.8, 0.8, 0.8, 1.0)
            out.write(f'{tab}*MATERIAL_AMBIENT {df} {df} {df}\n' % (0.0, 0.0, 0.0))
            out.write(f'{tab}*MATERIAL_DIFFUSE {df} {df} {df}\n' % scaled_color(diffuse, SOLID_DIFFUSE_SCALE))
            out.write(f'{tab}*MATERIAL_SPECULAR {df} {df} {df}\n' % (0.0, 0.0, 0.0))
            out.write(f'{tab}*MATERIAL_SHINE %.1f\n' % 0.0)
            out.write(f'{tab}*MATERIAL_SHINESTRENGTH %.1f\n' % 0.0)
            out.write(f'{tab}*MATERIAL_TRANSPARENCY %.1f\n' % (1.0 - diffuse[3]))
            out.write(f'{tab}*MATERIAL_WIRESIZE %.1f\n' % 1.0)
            out.write(f'{tab}*MATERIAL_SHADING Blinn\n')
            out.write(f'{tab}*MATERIAL_XP_FALLOFF %.1f\n' % 0.0)
            out.write(f'{tab}*MATERIAL_SELFILLUM %.1f\n' % 0.0)
            out.write(f'{tab}*MATERIAL_FALLOFF In\n')
            out.write(f'{tab}*MATERIAL_XP_TYPE Filter\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def collect_scene_materials(scene):
        scene_materials = {}

        for obj in scene.objects:
            if obj.type != 'MESH':
                continue

            materials = [slot.material for slot in obj.material_slots if slot.material]
            scene_materials[obj.name] = materials if materials else [None]

        return scene_materials

    #---------------------------------------------------------------------------------------------------------------------------
    def write_scene_materials(out, scene_materials):
        out.write("*MATERIAL_LIST {\n")
        out.write("\t*MATERIAL_COUNT %d\n" % len(scene_materials))

        for index, materials in enumerate(scene_materials.values()):
            out.write("\t*MATERIAL %d {\n" % index)

            if len(materials) == 1:
                write_material_data(out, materials[0], 2, True)
            else:
                write_material_data(out, materials[0], 2, False)
                out.write("\t\t*MATERIAL_MULTIMAT\n")
                out.write("\t\t*NUMSUBMTLS %d\n" % len(materials))

                for submat_index, mat in enumerate(materials):
                    out.write("\t\t*SUBMATERIAL %d {\n" % submat_index)
                    write_material_data(out, mat, 3, True)
                    out.write("\t\t}\n")

            out.write("\t}\n")

        out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_tm_node(out, obj_matrix_data, is_pivot=False):
        if is_pivot:
            matrix_data = obj_matrix_data["matrix_transformed"]
            if TRANSFORM_TO_CENTER:
                matrix_data = Matrix.Identity(4)
            out.write('\t*NODE_PIVOT_TM {\n')
        else:
            matrix_data = obj_matrix_data["matrix_original"]
            if not TRANSFORM_TO_CENTER and obj_matrix_data["type"] == 'MESH':
                matrix_data = Matrix.Identity(4)
            out.write('\t*NODE_TM {\n')

        out.write('\t\t*NODE_NAME "%s"\n' % obj_matrix_data["name"])
        out.write('\t\t*INHERIT_POS %d %d %d\n' % (0, 0, 0))
        out.write('\t\t*INHERIT_ROT %d %d %d\n' % (0, 0, 0))
        out.write('\t\t*INHERIT_SCL %d %d %d\n' % (1, 1, 1))

        eland_data = create_euroland_matrix(matrix_data, obj_matrix_data["type"])
        eland_matrix = eland_data["eland_matrix"]
        eland_euler = eland_data["eland_euler"]

        out.write(f'\t\t*TM_ROW0 {df} {df} {df}\n' % (eland_matrix[0].x, eland_matrix[0].y, eland_matrix[0].z))
        out.write(f'\t\t*TM_ROW1 {df} {df} {df}\n' % (eland_matrix[1].x, eland_matrix[1].y, eland_matrix[1].z))
        out.write(f'\t\t*TM_ROW2 {df} {df} {df}\n' % (eland_matrix[2].x, eland_matrix[2].y, eland_matrix[2].z))

        obj_position = eland_matrix.translation
        out.write(f'\t\t*TM_ROW3 {df} {df} {df}\n' % (obj_position.x, obj_position.y, obj_position.z))
        out.write(f'\t\t*TM_POS {df} {df} {df}\n' % (obj_position.x, obj_position.y, obj_position.z))
        out.write(f'\t\t*TM_ROTANGLE {df} {df} {df}\n' % (eland_euler.x, eland_euler.y, eland_euler.z))

        transformed_scale = eland_matrix.to_scale()
        out.write(f'\t\t*TM_SCALE {df} {df} {df}\n' % (transformed_scale.x, transformed_scale.z, transformed_scale.y))
        out.write(f'\t\t*TM_SCALEANGLE {df} {df} {df}\n' % (0, 0, 0))
        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_animation_node(out, obj, obj_matrix_data):
        global TICKS_PER_FRAME, START_FRAME, END_FRAME

        out.write('\t*TM_ANIMATION {\n')
        out.write('\t\t*TM_ANIMATION "%s"\n' % obj.name)
        out.write('\t\t*TM_ANIM_FRAMES {\n')

        for frame in range(START_FRAME, END_FRAME + 1):
            bpy.context.scene.frame_set(frame)
            tick = (frame - START_FRAME) * TICKS_PER_FRAME

            matrix_data = obj.matrix_world.copy()
            if obj.type == 'MESH':
                base_rot = obj_matrix_data["matrix_original"].to_3x3().normalized().to_4x4()
                current_rot = obj.matrix_world.to_3x3().normalized()
                matrix_data = current_rot.to_4x4()

                base_eland = create_euroland_matrix(base_rot, obj_matrix_data["type"])["eland_matrix"].to_3x3()
                current_eland = create_euroland_matrix(matrix_data, obj_matrix_data["type"])["eland_matrix"].to_3x3()
                delta_eland = current_eland @ base_eland.inverted()
                delta_eland.transpose()

                eland_matrix = delta_eland.to_4x4()
                eland_position = MESH_GLOBAL_MATRIX @ obj.matrix_world.translation
                eland_matrix[0][3] = eland_position.x
                eland_matrix[1][3] = eland_position.y
                eland_matrix[2][3] = eland_position.z
            else:
                eland_matrix = create_euroland_matrix(matrix_data, obj_matrix_data["type"])["eland_matrix"]

            out.write('\t\t\t*TM_FRAME  %-5d' % tick)
            out.write(f' {df} {df} {df}' % (eland_matrix[0].x, eland_matrix[0].y, eland_matrix[0].z))
            out.write(f' {df} {df} {df}' % (eland_matrix[1].x, eland_matrix[1].y, eland_matrix[1].z))
            out.write(f' {df} {df} {df}' % (eland_matrix[2].x, eland_matrix[2].y, eland_matrix[2].z))

            obj_position = eland_matrix.translation
            out.write(f' {df} {df} {df}\n' % (obj_position.x, obj_position.y, obj_position.z))

        out.write('\t\t}\n')
        out.write('\t}\n')

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

        if TRANSFORM_TO_CENTER:
            matrix_transformed = Matrix.Diagonal(ob_mat.to_scale()).to_4x4()
        else:
            matrix_transformed = ob_mat.copy()

        mesh.transform(Matrix.Scale(GLOBAL_SCALE, 4) @ (MESH_GLOBAL_MATRIX @ matrix_transformed))

        if (MESH_GLOBAL_MATRIX @ matrix_transformed).determinant() > 0.0:
            mesh.flip_normals()

        return mesh, ob_eval

    #---------------------------------------------------------------------------------------------------------------------------
    def material_index_for_poly(poly, materials):
        if not materials:
            return -1
        if poly.material_index < len(materials):
            return poly.material_index
        return 0

    #---------------------------------------------------------------------------------------------------------------------------
    def write_mesh_data(out, scene, depsgraph, scene_materials):
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
                    obj_matrix_data = {
                        "name": ob_main.name,
                        "type": ob_main.type,
                        "matrix_original": ob_mat.copy(),
                        "matrix_transformed": Matrix.Diagonal(ob.scale).to_4x4() if TRANSFORM_TO_CENTER else ob_mat.copy()
                    }

                    vertices = mesh.vertices[:]
                    unique_vertices, vertex_index_map = unique_ordered(tuple(v.co) for v in vertices)

                    unique_uvs = []
                    uv_index_map = {}
                    if EXPORT_MESH_UV and mesh.uv_layers.active:
                        unique_uvs, uv_index_map = unique_ordered(
                            (uv.uv.x, uv.uv.y)
                            for uv in mesh.uv_layers.active.data
                        )

                    mesh_materials = scene_materials.get(ob_main.name, [])
                    colors = color_layer_data(mesh)
                    unique_colors = []
                    color_index_map = {}
                    synthesize_texture_color = False
                    if EXPORT_MESH_VCOLORS and colors:
                        unique_colors, color_index_map = unique_ordered(tuple(col.color) for col in colors)
                    elif has_textured_material(mesh_materials):
                        synthesize_texture_color = True
                        unique_colors = [(TEXTURE_VERTEX_COLOR_SCALE, TEXTURE_VERTEX_COLOR_SCALE, TEXTURE_VERTEX_COLOR_SCALE, 1.0)]

                    out.write("*GEOMOBJECT {\n")
                    out.write('\t*NODE_NAME "%s"\n' % ob_main.name)
                    write_parent(out, ob_main)
                    write_tm_node(out, obj_matrix_data)
                    write_tm_node(out, obj_matrix_data, True)

                    out.write('\t*MESH {\n')
                    out.write('\t\t*TIMEVALUE %d\n' % EXPORT_STATIC_FRAME)
                    out.write('\t\t*MESH_NUMVERTEX %u\n' % len(unique_vertices))
                    out.write('\t\t*MESH_NUMFACES %u\n' % len(mesh.polygons))

                    out.write('\t\t*MESH_VERTEX_LIST {\n')
                    for index, vertex in enumerate(unique_vertices):
                        out.write(f'\t\t\t*MESH_VERTEX  {index:>5d}\t{df}\t{df}\t{df}\n' % vertex)
                    out.write('\t\t}\n')

                    out.write('\t\t*MESH_FACE_LIST {\n')
                    for poly_index, poly in enumerate(mesh.polygons):
                        vertex_indices = [vertex_index_map[tuple(vertices[v].co)] for v in poly.vertices]
                        material_index = material_index_for_poly(poly, mesh_materials)

                        out.write('\t\t\t*MESH_FACE    {:>3d}:    A: {:>6d} B: {:>6d} C: {:>6d}'.format(
                            poly_index, vertex_indices[0], vertex_indices[1], vertex_indices[2]
                        ))
                        out.write('    AB: %-6d BC: %-6d CA: %-6d  *MESH_SMOOTHING %u  *MESH_MTLID %-3d\n' % (
                            1, 1, 1, 1 if poly.use_smooth else 0, material_index
                        ))
                    out.write('\t\t}\n')

                    if EXPORT_MATERIALS and mesh_materials:
                        out.write('\t\t*SHADER_COUNT\t%d\n' % len(mesh_materials))
                        out.write('\t\t*SHADER_LIST {\n')
                        for material_index, mat in enumerate(mesh_materials):
                            out.write('\t\t\t*SHADER\t%d {\n' % material_index)
                            out.write('\t\t\t\t%d\t%s\n' % (material_index, material_shader_rule(mat)))
                            out.write('\t\t\t}\n')
                        out.write('\t\t}\n')

                    if EXPORT_MESH_UV:
                        out.write('\t\t*MESH_NUMTVERTEX %u\n' % len(unique_uvs))
                        if unique_uvs:
                            out.write('\t\t*MESH_TVERTLIST {\n')
                            for uv_index, uv in enumerate(unique_uvs):
                                out.write(f'\t\t\t*MESH_TVERT {uv_index:>5d}\t{df}\t{df}\t{df}\n' % (uv[0], uv[1], 0.0))
                            out.write('\t\t}\n')

                            out.write('\t\t*MESH_NUMTVFACES %d\n' % len(mesh.polygons))
                            out.write('\t\t*MESH_TFACELIST {\n')
                            for poly_index, poly in enumerate(mesh.polygons):
                                uv_indices = []
                                for loop_index in poly.loop_indices:
                                    uv = mesh.uv_layers.active.data[loop_index].uv
                                    uv_indices.append(uv_index_map.get((uv.x, uv.y), -1))
                                out.write('\t\t\t*MESH_TFACE %-3d\t%d\t%d\t%d\n' % (
                                    poly_index, uv_indices[0], uv_indices[1], uv_indices[2]
                                ))
                            out.write('\t\t}\n')

                    if EXPORT_MESH_VCOLORS or synthesize_texture_color:
                        out.write('\t\t*MESH_NUMCVERTEX %u\n' % len(unique_colors))
                        if unique_colors:
                            out.write('\t\t*MESH_CVERTLIST {\n')
                            for color_index, color in enumerate(unique_colors):
                                out.write(f'\t\t\t*MESH_VERTCOL {color_index:>5d}\t{df}\t{df}\t{df}\n' % (
                                    color[0], color[1], color[2]
                                ))
                            out.write('\t\t}\n')

                            out.write('\t\t*MESH_NUMCVFACES %d\n' % len(mesh.polygons))
                            out.write('\t\t*MESH_CFACELIST {\n')
                            for poly_index, poly in enumerate(mesh.polygons):
                                if synthesize_texture_color:
                                    color_indices = [0, 0, 0]
                                else:
                                    color_indices = []
                                    for loop_index in poly.loop_indices:
                                        color_indices.append(color_index_map.get(tuple(colors[loop_index].color), -1))
                                out.write('\t\t\t*MESH_CFACE %-3d\t%d\t%d\t%d\n' % (
                                    poly_index, color_indices[0], color_indices[1], color_indices[2]
                                ))
                            out.write('\t\t}\n')

                    if EXPORT_MESH_NORMALS:
                        out.write('\t\t*MESH_NORMALS {\n')
                        for poly_index, poly in enumerate(mesh.polygons):
                            normal = poly.normal
                            out.write(f'\t\t\t*MESH_FACENORMAL {poly_index:<3d}\t{df}\t{df}\t{df}\n' % (
                                normal[0], normal[1], normal[2]
                            ))
                            for vertex_index in poly.vertices:
                                export_vertex_index = vertex_index_map[tuple(vertices[vertex_index].co)]
                                out.write(f'\t\t\t\t*MESH_VERTEXNORMAL {export_vertex_index:<3d}\t{df}\t{df}\t{df}\n' % (
                                    normal[0], normal[1], normal[2]
                                ))
                        out.write('\t\t}\n')

                    if EXPORT_MESH_FLAGS:
                        face_flags = int_attribute(mesh, 'euro_fac_flags', 'FACE')
                        vertex_flags = int_attribute(mesh, 'euro_vtx_flags', 'POINT')

                        out.write('\t\t*MESH_NUMFACEFLAGS %u\n' % len(mesh.polygons))
                        out.write('\t\t*MESH_FACEFLAGLIST {\n')
                        if face_flags:
                            for face in mesh.polygons:
                                flag_value = face_flags.data[face.index].value
                                if flag_value != 0:
                                    out.write('\t\t\t*MESH_FACEFLAG %u %u\n' % (face.index, flag_value))
                        out.write('\t\t}\n')

                        out.write('\t\t*MESH_VERTFLAGSLIST {\n')
                        if vertex_flags:
                            for vertex in vertices:
                                if vertex.index < len(vertex_flags.data):
                                    flag_value = vertex_flags.data[vertex.index].value
                                    if flag_value != 0:
                                        export_vertex_index = vertex_index_map[tuple(vertex.co)]
                                        out.write('\t\t\t*VFLAG %u %u\n' % (export_vertex_index, flag_value))
                        out.write('\t\t}\n')

                    out.write('\t}\n')

                    if EXPORT_MESH_ANIMS:
                        write_animation_node(out, ob_main, obj_matrix_data)

                    out.write(f'\t*WIREFRAME_COLOR {df} {df} {df}\n' % (ob.color[0], ob.color[1], ob.color[2]))

                    if EXPORT_MATERIALS and ob_main.name in scene_materials:
                        out.write('\t*MATERIAL_REF %d\n' % list(scene_materials.keys()).index(ob_main.name))

                    if EXPORT_MESH_MORPH and ob.data.shape_keys:
                        write_morph_data(out, ob)

                    if EXPORT_MESH_MORPH:
                        write_skin_data(out, ob, vertices)

                    out.write("}\n")

                    if EXPORT_MESH_MORPH and ob.data.shape_keys:
                        write_morph_list(out, ob)
                finally:
                    ob_eval.to_mesh_clear()

    #---------------------------------------------------------------------------------------------------------------------------
    def write_morph_data(out, ob):
        out.write('\t*MORPH_DATA {\n')
        for shape_key in ob.data.shape_keys.key_blocks:
            if shape_key.relative_key != shape_key:
                out.write('\t\t*MORPH_FRAMES "%s" %u {\n' % (shape_key.name.replace(' ', '_'), FRAMES_COUNT))
                for frame in range(FRAMES_COUNT):
                    out.write(f'\t\t\t%u {df}\n' % (frame, shape_key.value))
                out.write('\t\t}\n')
        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_morph_list(out, ob):
        out.write('*MORPH_LIST {\n')
        for shape_key in ob.data.shape_keys.key_blocks:
            if shape_key.relative_key != shape_key:
                out.write('\t*MORPH_TARGET "%s" %u {\n' % (shape_key.name.replace(' ', '_'), len(shape_key.data)))
                for vert in shape_key.data:
                    out.write('\t\t%s\t%s\t%s\n' % (df % vert.co.x, df % vert.co.y, df % vert.co.z))
                out.write('\t}\n')
        out.write('}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_skin_data(out, ob, vertices):
        armature = ob.find_armature()
        if not armature:
            return

        vertex_groups = {group.index: group.name for group in ob.vertex_groups}
        bone_names = [bone.name for bone in armature.data.bones]

        out.write('\t*SKIN_DATA {\n')
        out.write('\t\t*BONE_LIST {\n')
        for bone_index, bone_name in enumerate(bone_names):
            out.write('\t\t\t*BONE %u "%s"\n' % (bone_index, bone_name))
        out.write('\t\t}\n')

        out.write('\t\t*SKIN_VERTEX_DATA {\n')
        for vertex in vertices:
            influences = []
            for group in vertex.groups:
                bone_name = vertex_groups.get(group.group)
                if bone_name in bone_names and group.weight > 0:
                    influences.append((bone_names.index(bone_name), group.weight))

            if not influences:
                continue

            influences.sort(key=lambda item: item[1], reverse=True)
            total_weight = sum(weight for _, weight in influences)
            if total_weight:
                influences = [(bone_index, weight / total_weight) for bone_index, weight in influences]

            out.write('\t\t\t*VERTEX %5u %u' % (vertex.index, len(influences)))
            for bone_index, weight in influences:
                out.write(f' %2u {df}' % (bone_index, weight))
            out.write('\n')
        out.write('\t\t}\n')
        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_biped_bones(out, scene, depsgraph):
        for ob_main in scene.objects:
            if ob_main.type != 'ARMATURE':
                continue

            bone_data = ob_main.evaluated_get(depsgraph).data if EXPORT_APPLY_MODIFIERS else ob_main.data

            for bone in bone_data.bones:
                out.write('*BONEOBJECT {\n')
                out.write('\t*NODE_NAME "%s"\n' % bone.name)
                if bone.parent:
                    out.write('\t*NODE_PARENT "%s"\n' % bone.parent.name)
                out.write('\t*NODE_BIPED_BODY\n')
                out.write('}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_light_settings(out, light_data, current_frame, tab_level=1):
        tab = get_tabs(tab_level)

        out.write(f'{tab}*LIGHT_SETTINGS {{\n')
        out.write(f'{tab}\t*TIMEVALUE %u\n' % current_frame)
        out.write(f'{tab}\t*COLOR {df} {df} {df}\n' % (light_data.color.r, light_data.color.g, light_data.color.b))
        out.write(f'{tab}\t*FAR_ATTEN {df} {df}\n' % (light_data.shadow_soft_size, light_data.cutoff_distance))
        out.write(f'{tab}\t*HOTSPOT {df}\n' % (degrees(light_data.angle) if light_data.type in {'SUN', 'SPOT'} else 0.0))
        out.write(f'{tab}}}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_light_data(out, scene, depsgraph):
        for ob_main in scene.objects:
            if ob_main.type != 'LIGHT':
                continue

            instances = [(ob_main, ob_main.matrix_world)]
            if ob_main.is_instancer:
                instances += [
                    (dup.instance_object.original, dup.matrix_world.copy())
                    for dup in depsgraph.object_instances
                    if dup.parent and dup.parent.original == ob_main
                ]

            for ob, ob_mat in instances:
                light_object = ob.evaluated_get(depsgraph) if EXPORT_APPLY_MODIFIERS else ob.original
                light_data = light_object.data

                obj_matrix_data = {
                    "name": ob_main.name,
                    "type": ob_main.type,
                    "matrix_original": ob_mat.copy(),
                    "matrix_transformed": ob_mat.copy()
                }

                out.write("*LIGHTOBJECT {\n")
                out.write('\t*NODE_NAME "%s"\n' % ob.name)
                write_parent(out, ob)

                type_lut = {
                    'POINT': 'Omni',
                    'SPOT': 'TargetSpot',
                    'SUN': 'TargetDirect',
                    'AREA': 'TargetDirect'
                }

                out.write('\t*LIGHT_TYPE %s\n' % type_lut.get(light_data.type, 'Omni'))
                write_tm_node(out, obj_matrix_data)
                out.write('\t*LIGHT_SHADOWS %s\n' % ("On" if light_data.use_shadow else "Off"))
                out.write('\t*LIGHT_DECAY %s\n' % ("None" if light_data.type == 'SUN' else "InvSquare"))
                out.write('\t*LIGHT_AFFECT_DIFFUSE On\n')
                out.write('\t*LIGHT_AFFECT_SPECULAR %s\n' % ("On" if light_data.specular_factor > 0.001 else "Off"))
                out.write('\t*LIGHT_AMBIENT_ONLY Off\n')

                write_light_settings(out, light_data, EXPORT_STATIC_FRAME)

                if EXPORT_CAMERA_LIGHT_ANIMS:
                    out.write('\t*LIGHT_ANIMATION {\n')
                    previous = None
                    for frame in range(START_FRAME, END_FRAME + 1):
                        scene.frame_set(frame)
                        tick = (frame - START_FRAME) * TICKS_PER_FRAME
                        current = (
                            tuple(light_data.color),
                            light_data.shadow_soft_size,
                            light_data.cutoff_distance,
                            getattr(light_data, "angle", 0.0)
                        )
                        if previous != current:
                            write_light_settings(out, light_data, tick, 2)
                            previous = current
                    out.write('\t}\n')
                    write_animation_node(out, ob_main, obj_matrix_data)

                out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def user_wants_camera_script(scene):
        return bool(getattr(scene, "euro_properties", None) and scene.euro_properties.enable_camera_script)

    #---------------------------------------------------------------------------------------------------------------------------
    def iter_action_fcurves(action):
        if action is None:
            return

        legacy_fcurves = getattr(action, "fcurves", None)
        if legacy_fcurves is not None:
            for fcurve in legacy_fcurves:
                yield fcurve
            return

        slots = list(getattr(action, "slots", []))
        seen_channelbags = set()

        for layer in getattr(action, "layers", []):
            for strip in getattr(layer, "strips", []):
                for channelbag in getattr(strip, "channelbags", []):
                    pointer = channelbag.as_pointer()
                    if pointer in seen_channelbags:
                        continue
                    seen_channelbags.add(pointer)
                    for fcurve in getattr(channelbag, "fcurves", []):
                        yield fcurve

                channelbag_for_slot = getattr(strip, "channelbag", None)
                if callable(channelbag_for_slot):
                    for slot in slots:
                        try:
                            channelbag = channelbag_for_slot(slot)
                        except TypeError:
                            continue
                        if channelbag is None:
                            continue

                        pointer = channelbag.as_pointer()
                        if pointer in seen_channelbags:
                            continue
                        seen_channelbags.add(pointer)
                        for fcurve in getattr(channelbag, "fcurves", []):
                            yield fcurve

    #---------------------------------------------------------------------------------------------------------------------------
    def collect_action_keyframes(action):
        frames = set()
        for fcurve in iter_action_fcurves(action):
            for point in getattr(fcurve, "keyframe_points", []):
                frames.add(point.co[0])

        return sorted(frames)

    #---------------------------------------------------------------------------------------------------------------------------
    def write_script_camera(out):
        markers = [marker for marker in bpy.context.scene.timeline_markers if marker.camera is not None]

        out.write('\t*USER_DATA %u {\n' % 0)
        out.write('\t\tCameraScript = %u\n' % 1)
        out.write('\t\tCameraScript_numCameras = %u\n' % len(markers))
        out.write('\t\tCameraScript_globalOffset = %u\n' % 0)

        for index, marker in enumerate(markers, start=1):
            camera = marker.camera
            keyframes = []
            if camera.animation_data and camera.animation_data.action:
                keyframes = collect_action_keyframes(camera.animation_data.action)

            first_keyframe = int(keyframes[0]) if keyframes else marker.frame
            last_keyframe = int(keyframes[-1]) if keyframes else marker.frame
            timeline_frame = marker.frame + (last_keyframe - first_keyframe)
            out.write('\t\tCameraScript_camera%u = %s %u %u %u %u\n' % (
                index, marker.name, first_keyframe, last_keyframe, marker.frame, timeline_frame
            ))

        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_camera_settings(out, camera_data, current_frame, tab_level=1):
        tab = get_tabs(tab_level)

        out.write(f'{tab}*CAMERA_SETTINGS {{\n')
        out.write(f'{tab}\t*TIMEVALUE %u\n' % current_frame)
        out.write(f'{tab}\t*CAMERA_NEAR {df}\n' % camera_data.clip_start)
        out.write(f'{tab}\t*CAMERA_FAR {df}\n' % camera_data.clip_end)
        out.write(f'{tab}\t*CAMERA_FOV {df}\n' % camera_data.angle)
        out.write(f'{tab}\t*CAMERA_TDIST {df}\n' % camera_data.clip_end)
        out.write(f'{tab}}}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_camera_data(out, scene, depsgraph):
        cameras = sorted([obj for obj in scene.objects if obj.type == 'CAMERA'], key=lambda obj: obj.name)

        for ob_main in cameras:
            instances = [(ob_main, ob_main.matrix_world)]
            if ob_main.is_instancer:
                instances += [
                    (dup.instance_object.original, dup.matrix_world.copy())
                    for dup in depsgraph.object_instances
                    if dup.parent and dup.parent.original == ob_main
                ]

            for ob, ob_mat in instances:
                camera_object = ob.evaluated_get(depsgraph) if EXPORT_APPLY_MODIFIERS else ob.original
                camera_data = camera_object.data

                obj_matrix_data = {
                    "name": ob.name,
                    "type": ob_main.type,
                    "matrix_original": ob_mat.copy(),
                    "matrix_transformed": ob_mat.copy()
                }

                out.write("*CAMERAOBJECT {\n")
                out.write('\t*NODE_NAME "%s"\n' % ob.name)
                write_parent(out, ob)
                out.write('\t*CAMERA_TYPE target\n')
                write_tm_node(out, obj_matrix_data)
                write_camera_settings(out, camera_data, EXPORT_STATIC_FRAME)

                if EXPORT_CAMERA_LIGHT_ANIMS:
                    out.write('\t*CAMERA_ANIMATION {\n')
                    previous = None
                    for frame in range(START_FRAME, END_FRAME + 1):
                        scene.frame_set(frame)
                        tick = (frame - START_FRAME) * TICKS_PER_FRAME
                        current = (camera_data.clip_start, camera_data.clip_end, camera_data.angle)
                        if previous != current:
                            write_camera_settings(out, camera_data, tick, 2)
                            previous = current
                    out.write('\t}\n')
                    write_animation_node(out, ob_main, obj_matrix_data)

                if ob_main == cameras[-1] and user_wants_camera_script(scene):
                    write_script_camera(out)

                out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def restore_mode(original_mode):
        if original_mode and original_mode != 'OBJECT' and bpy.ops.object.mode_set.poll():
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except RuntimeError:
                pass

    #---------------------------------------------------------------------------------------------------------------------------
    def write_ese_file():
        depsgraph = bpy.context.evaluated_depsgraph_get()
        scene = bpy.context.scene
        original_frame = scene.frame_current
        active_object = getattr(context, "object", None)
        original_mode = active_object.mode if active_object else None

        try:
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')

            plugin_version = get_plugin_version()

            with open(filepath, 'w', encoding="utf8") as out:
                out.write("*3DSMAX_EUROEXPORT\t300\n")
                out.write('*COMMENT "Eurocom Export Version  3.00 - %s"\n' % datetime.now().strftime("%A %B %d %Y %H:%M"))
                out.write('*COMMENT "Version of Blender that output this file: %s"\n' % bpy.app.version_string)
                out.write('*COMMENT "Version of ESE Plug-in: %d.%d.%d"\n\n' % (
                    plugin_version[0], plugin_version[1], plugin_version[2]
                ))

                write_scene_data(out, scene)

                scene_materials = collect_scene_materials(scene) if EXPORT_MATERIALS else {}
                if EXPORT_MATERIALS:
                    write_scene_materials(out, scene_materials)

                if 'MESH' in EXPORT_OBJECTS:
                    write_mesh_data(out, scene, depsgraph, scene_materials)
                if 'CAMERA' in EXPORT_OBJECTS:
                    write_camera_data(out, scene, depsgraph)
                if 'LIGHT' in EXPORT_OBJECTS:
                    write_light_data(out, scene, depsgraph)
                if 'ARMATURE' in EXPORT_OBJECTS:
                    write_biped_bones(out, scene, depsgraph)
        finally:
            scene.frame_set(original_frame)
            restore_mode(original_mode)

    write_ese_file()


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
         Output_First_Only,
         Output_Transform_Animation_Keys=False,
         Output_Mesh_Keyframes_From_Market=False,
         Output_Force_Mesh_Keyframes_If_Visible=False,
         Output_Inverse_Kinematics_Joints=False,
         Output_Remove_NonUniform_Scale=False,
         Use_Keys=True,
         Force_Sample=False,
         Frames_Per_Sample=1,
         Controllers_Per_Sample=5,
         Animated_Objects_Per_Sample=5):

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
    save({}, str(Path.home()) + '/Desktop/EurocomESE.ese')
