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
import math
from pathlib import Path
from mathutils import Matrix
from datetime import datetime
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
           EXPORT_END_FRAME,
           EXTRACT_PACKED_TEXTURES=True,
           EXPORT_FIRST_ONLY=False,
           REPORT=None,
        ):

    df = f'%.{DECIMAL_PRECISION}f'

    #---------------------------------------------------------------------------------------------------------------------------
    def warning(message):
        if REPORT:
            REPORT({'WARNING'}, message)
        else:
            print("RTG export warning: " + message)

    def texture_path(mat):
        return export_material_texture_path(
            mat,
            export_filepath=filepath,
            extract_packed=EXTRACT_PACKED_TEXTURES,
            warning=warning,
        )

    #---------------------------------------------------------------------------------------------------------------------------
    def material_color(mat):
        mat_wrap = material_wrap(mat)
        if mat_wrap:
            return mat_wrap.base_color[:3], material_alpha_value(mat)
        if mat:
            return mat.diffuse_color[:3], mat.diffuse_color[3]
        return (0.8, 0.8, 0.8), 1.0

    #---------------------------------------------------------------------------------------------------------------------------
    def material_blend(mat):
        alpha = material_alpha_value(mat)
        # The legacy blend_method reports different defaults in Blender 3.6
        # and 5.x. Derive the flag from the actual material graph/alpha instead.
        rtg_flags = 1 if material_has_transparency(mat) else 0
        blend_mode = 0
        return alpha, blend_mode, rtg_flags

    #---------------------------------------------------------------------------------------------------------------------------
    def scene_frame_range(scene):
        if EXPORT_FIRST_ONLY:
            return scene.frame_start, scene.frame_start
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
    def armature_for_mesh(ob):
        if ob.parent and ob.parent.type == 'ARMATURE':
            return ob.parent
        modifier = next((mod for mod in ob.modifiers if mod.type == 'ARMATURE' and mod.object), None)
        return modifier.object if modifier else None

    def mesh_is_deforming(ob):
        return bool(armature_for_mesh(ob) or (ob.data and ob.data.shape_keys))

    def mesh_export_data(ob, ob_mat, depsgraph):
        # Applying topology-changing modifiers to a skin/morph would invalidate the
        # documented per-source-vertex weight and morph tables.
        apply_modifiers = EXPORT_APPLY_MODIFIERS and not mesh_is_deforming(ob)
        ob_eval = ob.evaluated_get(depsgraph) if apply_modifiers else ob
        try:
            temporary_mesh = ob_eval.to_mesh()
        except RuntimeError:
            return None, None, set()

        if temporary_mesh is None:
            return None, ob_eval, set()
        mesh = temporary_mesh.copy()
        ob_eval.to_mesh_clear()

        original_edge_faces = {edge.index: [] for edge in mesh.edges}
        original_edge_lookup = {tuple(sorted(edge.vertices)): edge for edge in mesh.edges}
        for poly in mesh.polygons:
            for edge_key in poly.edge_keys:
                edge = original_edge_lookup.get(tuple(sorted(edge_key)))
                if edge:
                    original_edge_faces[edge.index].append(poly)
        hard_edge_keys = {
            tuple(sorted(edge.vertices))
            for edge in mesh.edges
            if getattr(edge, "use_edge_sharp", False)
            or len(original_edge_faces[edge.index]) < 2
            or any(not face.use_smooth for face in original_edge_faces[edge.index])
        }

        if EXPORT_TRI:
            mesh_triangulate(mesh)

        bake_world = TRANSFORM_TO_CENTER and not mesh_is_deforming(ob)
        matrix = ob_mat.copy() if bake_world else Matrix.Identity(4)
        mesh.transform(Matrix.Scale(GLOBAL_SCALE, 4) @ MESH_GLOBAL_MATRIX @ matrix)
        if ob_mat.determinant() < 0.0:
            mesh.flip_normals()
        return mesh, ob_eval, hard_edge_keys

    #---------------------------------------------------------------------------------------------------------------------------
    def collect_meshes(scene, depsgraph):
        meshes = []

        def append_mesh(ob, ob_main, ob_mat, is_instance=False):
            mesh, ob_eval, hard_edge_keys = mesh_export_data(ob, ob_mat, depsgraph)
            if mesh is None:
                return
            meshes.append({
                "object": ob,
                "main": ob_main,
                "matrix": ob_mat.copy(),
                "mesh": mesh,
                "eval": ob_eval,
                "shape_name": f"{ob.name.replace(' ', '_')}Shape",
                "centered": TRANSFORM_TO_CENTER and not mesh_is_deforming(ob),
                "hard_edges": hard_edge_keys,
                "is_instance": is_instance,
            })

        for ob_main in scene.objects:
            if ob_main.type != 'MESH':
                continue
            if ob_main.parent and ob_main.parent.instance_type in {'VERTS', 'FACES'}:
                continue
            append_mesh(ob_main, ob_main, ob_main.matrix_world)

        for instance in depsgraph.object_instances:
            if not instance.is_instance or instance.object.original.type != 'MESH':
                continue
            source = instance.object.original
            append_mesh(source, source, instance.matrix_world, is_instance=True)
        return meshes

    #---------------------------------------------------------------------------------------------------------------------------
    def collect_cameras(scene):
        return sorted([obj for obj in scene.objects if obj.type == 'CAMERA'], key=lambda obj: obj.name)

    #---------------------------------------------------------------------------------------------------------------------------
    def hierarchy_name(obj):
        return obj.name.replace(" ", "_")

    def clean_name(value):
        return str(value).replace(' ', '_').replace('"', '')

    def custom_string(owner, key, default=""):
        value = owner.get(key, default) if owner else default
        if hasattr(value, "name"):
            value = value.name
        return clean_name(value) if value not in (None, "") else ""

    def scene_entities(meshes, cameras):
        entities = []
        camera_names = {}
        mesh_objects = {item["object"] for item in meshes}
        required_armatures = {armature_for_mesh(obj) for obj in mesh_objects}
        required_armatures.discard(None)

        def ancestors(obj):
            result = []
            parent = obj.parent
            while parent:
                if parent.type == 'EMPTY':
                    result.append(parent)
                parent = parent.parent
            return list(reversed(result))

        locator_objects = set()
        for obj in list(mesh_objects) + list(cameras):
            locator_objects.update(ancestors(obj))

        used_names = set()
        for locator in sorted(locator_objects, key=lambda obj: (len(ancestors(obj)), obj.name)):
            name = hierarchy_name(locator)
            used_names.add(name)
            kind = "lodGroup" if (
                locator.name.lower().startswith("lodgroup") or locator.get("rtg_lod_group")
            ) else "LOCATOR"
            entities.append({
                "name": name, "level": len(ancestors(locator)) + 1,
                "kind": kind, "object": locator,
            })

        for camera in cameras:
            # Maya/RTG camera nodes conventionally use names such as Camera0.
            # Blender often leaves the object as Camera/Camera.001 while the
            # camera datablock and bound timeline marker retain Camera0/Camera1.
            # Prefer the datablock name and keep it consistent in every RTG block.
            base = clean_name(camera.data.name or camera.name)
            name = base
            suffix = 1
            while name in used_names:
                name = f"{base}.{suffix:03d}"
                suffix += 1
            used_names.add(name)
            camera_names[camera] = name
            entities.append({
                "name": name, "level": len(ancestors(camera)) + 1,
                "kind": "CAMERA", "object": camera,
            })

        for armature in sorted(required_armatures, key=lambda obj: obj.name):
            for bone in armature.data.bones:
                level = 1
                parent = bone.parent
                while parent:
                    level += 1
                    parent = parent.parent
                entities.append({
                    "name": clean_name(bone.name), "level": level, "kind": "BONE",
                    "object": armature, "bone": bone.name,
                })

                used_names.add(clean_name(bone.name))
        used_shape_names = set()
        for mesh_data in meshes:
            base = hierarchy_name(mesh_data["object"])
            name = base
            suffix = 1
            while name in used_names:
                name = f"{base}.{suffix:03d}"
                suffix += 1
            used_names.add(name)
            mesh_data["export_name"] = name
            shape_base = clean_name(mesh_data["shape_name"])
            shape_name = shape_base
            shape_suffix = 1
            while shape_name in used_shape_names:
                shape_name = f"{shape_base}.{shape_suffix:03d}"
                shape_suffix += 1
            used_shape_names.add(shape_name)
            mesh_data["shape_name"] = shape_name
            entities.append({
                "name": name, "level": len(ancestors(mesh_data["object"])) + 1,
                # EuroLand's actual RTG implementation writes and expects MESH
                # here. The public draft incorrectly lists this as LOCATOR.
                "kind": "MESH", "object": mesh_data["object"],
                "mesh": mesh_data,
            })
        return entities, camera_names

    def bone_world_matrix(armature, bone_name):
        pose_bone = armature.pose.bones.get(bone_name) if armature.pose else None
        bone_matrix = pose_bone.matrix if pose_bone else armature.data.bones[bone_name].matrix_local
        return armature.matrix_world @ bone_matrix

    def entity_matrix(entity, depsgraph=None):
        mesh_data = entity.get("mesh")
        if mesh_data and mesh_data["centered"]:
            return Matrix.Identity(4)
        if mesh_data and mesh_data["is_instance"]:
            return mesh_data["matrix"]
        if "bone" in entity:
            armature = entity["object"]
            if depsgraph is not None:
                armature = armature.evaluated_get(depsgraph)
            return bone_world_matrix(armature, entity["bone"])
        obj = entity["object"]
        if depsgraph is not None:
            obj = obj.evaluated_get(depsgraph)
        return obj.matrix_world.copy()

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
    def write_hierarchy_list(out, entities):
        bones = [entity for entity in entities if entity["kind"] == "BONE"]
        if not bones:
            return
        out.write("HIERARCHY_LIST {\n")
        for entity in bones:
            flag = "P" if entity["level"] > 1 else "G"
            out.write("\t%u %s %s\n" % (entity["level"], flag, entity["name"]))
            matrix = transformed_matrix(entity_matrix(entity), 'BONE')
            for row_index in range(4):
                row = matrix[row_index]
                out.write(f'\t*TMROW{row_index}: {df} {df} {df}\n' % (row[0], row[1], row[2]))
        out.write("}\n\n")

    def write_scene_hierarchy(out, entities):
        out.write("*SCENE_HIERARCHY {\n")
        for entity in entities:
            if "mesh" in entity:
                out.write("\t%s %u MESH %s\n" % (
                    entity["name"], entity["level"], entity["mesh"]["shape_name"]
                ))
            else:
                out.write("\t%s %u %s\n" % (entity["name"], entity["level"], entity["kind"]))
        out.write("}\n\n")
        out.write("*SCENE_FRAMES_PER_SECOND %u\n" % bpy.context.scene.render.fps)

    #---------------------------------------------------------------------------------------------------------------------------
    def write_scene_frame(out, scene, depsgraph, entities, meshes, source_frame, output_frame):
        scene.frame_set(source_frame)
        out.write("*SCENE_FRAME %u {\n" % output_frame)
        if EXPORT_MESH_MORPH:
            morph_meshes = [item for item in meshes if item["object"].data.shape_keys]
            if morph_meshes:
                out.write("\t*MORPH_FRAMES {\n")
                for mesh_data in morph_meshes:
                    for key in mesh_data["object"].data.shape_keys.key_blocks:
                        if key.relative_key == key:
                            continue
                        out.write("\t\t*MORPHTARGET %s {\n" % clean_name(key.name))
                        out.write(f'\t\t\t*WEIGHT {df} %s\n' % (key.value, mesh_data["shape_name"]))
                        out.write("\t\t}\n")
                out.write("\t}\n")
        for entity in entities:
            matrix = transformed_matrix(entity_matrix(entity, depsgraph), entity["kind"])
            out.write(matrix_line(entity["name"], matrix))
        out.write("}\n")

    def skin_bone_names(meshes):
        names = []
        seen = set()
        for mesh_data in meshes:
            ob = mesh_data["object"]
            armature = armature_for_mesh(ob)
            if not armature:
                continue
            armature_names = {bone.name for bone in armature.data.bones}
            if ob.parent == armature and ob.parent_type == 'BONE' and ob.parent_bone:
                candidates = [ob.parent_bone]
            else:
                candidates = [group.name for group in ob.vertex_groups if group.name in armature_names]
            for name in candidates:
                if name not in seen:
                    seen.add(name)
                    names.append(name)
        return names

    def write_skin_data(out, meshes):
        bone_names = skin_bone_names(meshes)
        if not bone_names:
            return
        bone_indices = {name: index for index, name in enumerate(bone_names)}
        out.write("*BONES_LIST {\n")
        for name in bone_names:
            out.write("\t%s\n" % clean_name(name))
        out.write("}\n\n")

        out.write("*SKIN_WEIGHTS_LIST {\n")
        for mesh_data in meshes:
            ob = mesh_data["object"]
            armature = armature_for_mesh(ob)
            if not armature:
                continue
            out.write("\t*NAME %s\n" % mesh_data["shape_name"])
            group_names = {group.index: group.name for group in ob.vertex_groups}
            rigid_index = bone_indices.get(ob.parent_bone) if ob.parent == armature and ob.parent_type == 'BONE' else None
            for vertex in ob.data.vertices:
                if rigid_index is not None:
                    influences = [(rigid_index, 1.0)]
                else:
                    influences = [
                        (bone_indices[group_names[group.group]], group.weight)
                        for group in vertex.groups
                        if group.weight > 0.0 and group_names.get(group.group) in bone_indices
                    ]
                    influences.sort(key=lambda item: item[1], reverse=True)
                    influences = influences[:4]
                    total = sum(weight for _, weight in influences)
                    if total:
                        influences = [(index, weight / total) for index, weight in influences]
                out.write("\t")
                out.write(" ".join(f"{index} {df % weight}" for index, weight in influences))
                out.write("\n")
        out.write("}\n\n")

    def morph_export_coordinate(mesh_data, coordinate):
        ob = mesh_data["object"]
        matrix = Matrix.Scale(GLOBAL_SCALE, 4) @ MESH_GLOBAL_MATRIX
        if mesh_data["centered"]:
            matrix = matrix @ mesh_data["matrix"]
        co = matrix @ coordinate
        return co.x, co.y, -co.z

    def write_morph_list(out, meshes):
        morph_meshes = [item for item in meshes if item["object"].data.shape_keys]
        if not EXPORT_MESH_MORPH or not morph_meshes:
            return
        out.write("*MORPH_LIST {\n")
        for mesh_data in morph_meshes:
            ob = mesh_data["object"]
            for key in ob.data.shape_keys.key_blocks:
                if key.relative_key == key:
                    continue
                out.write("\t*DEFORMER_LIST %s {\n" % clean_name(key.name))
                out.write("\t\t*VERTEX_LIST %s %u {\n" % (mesh_data["shape_name"], len(key.data)))
                for vertex in key.data:
                    x, y, z = morph_export_coordinate(mesh_data, vertex.co)
                    out.write(f'\t\t\t{df} {df} {df}\n' % (x, y, z))
                out.write("\t\t}\n\t}\n")
        out.write("}\n\n")

    def write_datum_list(out, scene):
        datums = [obj for obj in scene.objects if obj.type == 'EMPTY' and bool(obj.get("rtg_datum", False))]
        if not datums:
            return
        out.write("*DATUM_LIST {\n")
        for datum in sorted(datums, key=lambda obj: obj.name):
            co = Matrix.Scale(GLOBAL_SCALE, 4) @ MESH_GLOBAL_MATRIX @ datum.matrix_world.translation
            parent_bone = datum.parent_bone if datum.parent and datum.parent.type == 'ARMATURE' else ""
            out.write(f'\t{clean_name(datum.name)} {df} {df} {df}' % (co.x, co.y, -co.z))
            if parent_bone:
                out.write(" %s" % clean_name(parent_bone))
            out.write("\n")
        out.write("}\n\n")

    def write_lod_list(out, meshes):
        groups = {}
        for mesh_data in meshes:
            ob = mesh_data["object"]
            group = custom_string(ob, "rtg_lod_group")
            if not group and ob.parent and (ob.parent.name.lower().startswith("lodgroup") or ob.parent.get("rtg_lod_group")):
                group = custom_string(ob.parent, "rtg_lod_group", ob.parent.name)
            if group:
                distance = float(ob.get("rtg_lod_distance", 0.0)) * GLOBAL_SCALE
                groups.setdefault(group, []).append((mesh_data["export_name"], distance))
        if not groups:
            return
        out.write("*LOD_LIST {\n")
        for group, members in sorted(groups.items()):
            out.write("\t*LOD_GROUP {\n\t\t*NAME %s\n" % group)
            for name, distance in sorted(members, key=lambda item: item[1]):
                out.write(f'\t\t{name} {df}\n' % distance)
            out.write("\t}\n")
        out.write("}\n\n")

    def write_associations(out, meshes):
        associations = []
        export_names = {item["object"].name: item["export_name"] for item in meshes}
        for mesh_data in meshes:
            ob = mesh_data["object"]
            collision = custom_string(ob, "rtg_collision_mesh")
            if collision:
                associations.append((mesh_data["export_name"], export_names.get(collision, collision)))
            source = custom_string(ob, "rtg_collision_for")
            if source:
                associations.append((export_names.get(source, source), mesh_data["export_name"]))
        if not associations:
            return
        out.write("*ASSOCIATIONS {\n")
        for source, collision in sorted(set(associations)):
            out.write("\t%s %s collisionMesh\n" % (source, collision))
        out.write("}\n\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_shader(out, mat, shader_index):
        color, _ = material_color(mat)
        alpha, blend_mode, rtg_flags = material_blend(mat)
        out.write('\t*SHADER_%d {\n' % shader_index)
        out.write(f'\t\t{df} {df} {df} {df}\n' % (color[0], color[1], color[2], 1.0))

        tex = texture_path(mat)
        if tex:
            texture_file = os.path.basename(tex).replace(" ", "_")
            texture_name = os.path.splitext(texture_file)[0]
            out.write('\t\t%s "%s" ' % (texture_name, texture_file))
        else:
            out.write('\t\t"" "" ')
        out.write(f'{df} %d %d\n' % (alpha, blend_mode, rtg_flags))
        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_meshes(out, meshes):
        # EuroLand's RTG reader treats each *MESH block as one object.  Starting a
        # second *NAME inside the same block leaves the parser in the first mesh
        # and eventually raises its generic "improper argument" exception.
        for mesh_data in meshes:
            mesh = mesh_data["mesh"]
            vertices = mesh.vertices[:]
            # RTG skin/morph tables address source vertex indices directly. Do not
            # merge coincident vertices: they may have different weights or colors.
            unique_vertices = [tuple(vertex.co) for vertex in vertices]
            color_layer = active_color_layer(mesh)
            face_flags = int_attribute(mesh, 'euro_fac_flags', 'FACE') if EXPORT_MESH_FLAGS else None

            out.write("*MESH {\n")
            out.write("\t*NAME %s\n" % mesh_data["shape_name"])
            out.write('\t*VERT_XYXRGBA %d {\n' % len(unique_vertices))
            for vertex in unique_vertices:
                out.write(f'\t\t{df} {df} {df}\n' % (vertex[0], vertex[1], -vertex[2]))
            out.write('\t}\n')

            materials = list(mesh.materials)
            if EXPORT_MATERIALS and materials:
                for mat_index, mat in enumerate(materials):
                    write_shader(out, mat, mat_index)

            out.write("\t*FACE_LIST {\n")
            for poly in mesh.polygons:
                flag_value = face_flags.data[poly.index].value if face_flags else 0
                shader_index = poly.material_index if poly.material_index < len(materials) else 0
                out.write("\t\t*FACE %d %d %d {\n" % (len(poly.vertices), shader_index, flag_value))
                vertex_indices = list(poly.vertices)
                out.write("\t\t\t%s\n" % " ".join(map(str, vertex_indices)))

                if EXPORT_MESH_UV and mesh.uv_layers.active and materials:
                    mat = materials[shader_index] if shader_index < len(materials) else None
                    tex = texture_path(mat)
                    # A RTG face-layer record is not just a list of UV pairs: it
                    # must end with the shader texture name.  Writing UVs for an
                    # untextured material makes Redux report "Unexpected record
                    # length when reading face layer record".
                    if not tex:
                        out.write("\t\t}\n")
                        continue
                    uv_items = []
                    for loop_index in poly.loop_indices:
                        uv = mesh.uv_layers.active.data[loop_index].uv
                        uv_items.append(f'{uv.x:.6f} {-uv.y:.6f}')
                    texture_file = os.path.basename(tex).replace(" ", "_")
                    uv_items.append(os.path.splitext(texture_file)[0])
                    out.write("\t\t\t%s\n" % " ".join(uv_items))
                out.write("\t\t}\n")
            out.write("\t}\n")

            hard_edges = list(mesh_data["hard_edges"])
            if hard_edges:
                out.write("\t*HARD_EDGE_LIST {\n")
                for first, second in sorted(set(tuple(sorted(pair)) for pair in hard_edges)):
                    out.write("\t\t%u %u\n" % (first, second))
                out.write("\t}\n")

            if EXPORT_MESH_VCOLORS and color_layer:
                rgb_indices = {}
                rgb_values = []
                face_rgb_indices = []
                for poly in mesh.polygons:
                    indices = []
                    for loop_index in poly.loop_indices:
                        color = color_for_loop(mesh, color_layer, loop_index) or (1.0, 1.0, 1.0, 1.0)
                        color = tuple(color[:4])
                        if color not in rgb_indices:
                            rgb_indices[color] = len(rgb_values)
                            rgb_values.append(color)
                        indices.append(rgb_indices[color])
                    face_rgb_indices.append(indices)
                out.write("\t*FACE_VERTEX_RGB {\n")
                for color in rgb_values:
                    alpha = color[3] if len(color) > 3 else 1.0
                    out.write(f'\t\t{df} {df} {df} {df}\n' % (color[0], color[1], color[2], alpha))
                out.write("\t}\n")
                out.write("\t*RGB_FACE_LIST {\n")
                for indices in face_rgb_indices:
                    out.write("\t\t*RGB_FACE %s\n" % " ".join(map(str, indices)))
                out.write("\t}\n")
            out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def camera_source_range(scene, camera, start, end):
        action = camera.animation_data.action if camera.animation_data else None
        if action is not None:
            action_start, action_end = action.frame_range
            first = max(start, int(math.floor(action_start)))
            last = min(end, int(math.ceil(action_end)))
            if first <= last:
                return first, last

        markers = sorted(scene.timeline_markers, key=lambda marker: (marker.frame, marker.name))
        for index, marker in enumerate(markers):
            if marker.camera != camera:
                continue
            next_frame = markers[index + 1].frame if index + 1 < len(markers) else end + 1
            first = max(start, marker.frame)
            last = min(end, next_frame - 1)
            if first <= last:
                return first, last

        return start, end

    #---------------------------------------------------------------------------------------------------------------------------
    def write_camera_list(out, scene, depsgraph, cameras, camera_names, start, end):
        if not cameras:
            return
        # CAMERA_LIST is the default camera state.  Scene-frame sampling leaves
        # Blender on the final frame, so evaluate this block explicitly at the
        # first exported frame rather than accidentally recording the last lens.
        out.write("*CAMERA_LIST {\n")
        for camera in cameras:
            camera_start, _camera_end = camera_source_range(scene, camera, start, end)
            scene.frame_set(camera_start)
            data = camera.evaluated_get(depsgraph).data
            out.write(f'\t%s {df} {df} {df} {df} {df} {df}\n' % (
                camera_names[camera],
                data.angle_x,
                data.angle_y,
                data.lens,
                data.clip_start * GLOBAL_SCALE,
                data.clip_end * GLOBAL_SCALE,
                1.0
            ))
        out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_camera_animation(out, scene, depsgraph, cameras, camera_names, start, end):
        if not cameras:
            return
        out.write("*CAMERA_ANIMATION {\n")
        for camera in cameras:
            camera_start, camera_end = camera_source_range(scene, camera, start, end)
            out.write("\t%s focalLength " % camera_names[camera])
            for source_frame in range(camera_start, camera_end + 1):
                scene.frame_set(source_frame)
                data = camera.evaluated_get(depsgraph).data
                # Like ESE, RTG output starts at zero even when Blender starts at
                # frame 1 (or any other source frame).
                output_frame = source_frame - start
                out.write("%u %s " % (output_frame, df % data.lens))
            out.write("\n")
        out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def cleanup_meshes(meshes):
        for mesh_data in meshes:
            mesh = mesh_data["mesh"]
            if mesh and mesh.name in bpy.data.meshes:
                bpy.data.meshes.remove(mesh)

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

            # A RTG camera transform lives in SCENE_FRAME, not in
            # CAMERA_ANIMATION (that block only animates focal length).  The old
            # standalone exporter therefore sampled every frame.  Preserve that
            # useful behaviour automatically whenever cameras are exported; the
            # explicit "first only" option remains the opt-out for static files.
            sample_cameras = bool(cameras) and not EXPORT_FIRST_ONLY and end > start
            sample_scene = EXPORT_CAMERA_LIGHT_ANIMS or EXPORT_MESH_ANIMS or sample_cameras

            # Build the base mesh/camera state at the same frame advertised as
            # the first sample.  This also avoids depending on whatever frame the
            # artist happened to have selected when pressing Export.
            scene.frame_set(start if sample_scene else EXPORT_STATIC_FRAME)
            meshes = collect_meshes(scene, depsgraph) if 'MESH' in EXPORT_OBJECTS else []
            entities, camera_names = scene_entities(meshes, cameras)

            if TRANSFORM_TO_CENTER and any(mesh_is_deforming(item["object"]) for item in meshes):
                warning("Transform Objects to (0,0,0) is not baked into skinned or morph meshes, to preserve deformation alignment.")

            with open(filepath, 'w', encoding="utf8") as out:
                # 5.01 is the documented Eurocom RTG revision and is also the
                # version emitted by the original Blender camera prototype.
                out.write("EUROCOM_RTG 5.01\n")
                out.write('*COMMENT "Version of Blender that output this file: %s"\n' % bpy.app.version_string)
                out.write('*COMMENT "Version of RTG Plug-in: %d.%d.%d"\n\n' % (
                    plugin_version[0], plugin_version[1], plugin_version[2]
                ))

                # RTG embeds its render material in each mesh's *SHADER_n block.
                # Although the public draft documents a global *MATERIAL block,
                # the original plug-in output omits it and Redux can throw its
                # generic "improper argument" exception while reading that block.
                write_hierarchy_list(out, entities)
                write_scene_hierarchy(out, entities)
                # ESE rebases its selected Blender range to 0..N. Do the same in
                # RTG so EuroLand scripts start at frame zero consistently.
                out.write("*SCENE_FIRST_FRAME 0\n")

                if sample_scene:
                    for source_frame in range(start, end + 1):
                        write_scene_frame(
                            out, scene, depsgraph, entities, meshes,
                            source_frame, source_frame - start,
                        )
                else:
                    write_scene_frame(out, scene, depsgraph, entities, meshes, EXPORT_STATIC_FRAME, 0)

                if meshes:
                    write_meshes(out, meshes)
                    write_skin_data(out, meshes)
                    write_morph_list(out, meshes)
                    write_lod_list(out, meshes)
                    write_associations(out, meshes)

                write_datum_list(out, scene)

                if cameras:
                    write_camera_list(out, scene, depsgraph, cameras, camera_names, start, end)
                    if EXPORT_CAMERA_LIGHT_ANIMS or sample_cameras:
                        write_camera_animation(
                            out, scene, depsgraph, cameras, camera_names, start, end
                        )
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
         Output_First_Only,
         Extract_Packed_Textures=True,
         report=None):

    try:
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
               EXPORT_END_FRAME=End_With_Frame,
               EXTRACT_PACKED_TEXTURES=Extract_Packed_Textures,
               EXPORT_FIRST_ONLY=Output_First_Only,
               REPORT=report)
    except PermissionError:
        message = (
            "RTG file cannot be overwritten because another program is using it. "
            "Close the file/project in EuroLand, close EuroLand, or export with a new filename."
        )
        if report:
            report({'ERROR'}, message)
            return {'CANCELLED'}
        raise

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
