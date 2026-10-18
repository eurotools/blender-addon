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
from math import ceil, degrees
from mathutils import Matrix, Vector
from datetime import datetime
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
           EXTRACT_PACKED_TEXTURES,
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
           EXPORT_OUTPUT_FIRST_ONLY,
           EXPORT_TRANSFORM_ANIMATION_KEYS,
           EXPORT_MESH_KEYFRAMES_FROM_MARKERS,
           EXPORT_FORCE_MESH_KEYFRAMES_IF_VISIBLE,
           EXPORT_REMOVE_NONUNIFORM_SCALE,
           USE_KEYS,
           FORCE_SAMPLE,
           FRAMES_PER_SAMPLE,
           REPORT
        ):

    df = f'%.{DECIMAL_PRECISION}f'
    SCENE_LIGHT_SCALE = 1.0
    TEXTURED_DIFFUSE_SCALE = 0.5
    SOLID_DIFFUSE_SCALE = 1.0
    MAP_AMOUNT_SCALE = 1.0
    TEXTURE_VERTEX_COLOR_SCALE = 0.5
    skin_bone_plan_cache = {}

    def emit_warning(message):
        print(f'WARNING ESE: {message}')
        if REPORT:
            REPORT({'WARNING'}, message)

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

        if material_has_transparency(mat):
            return 'Alp'

        return 'Non'

    #---------------------------------------------------------------------------------------------------------------------------
    def has_textured_material(materials):
        return any(material_diffuse_image(mat) for mat in materials)

    #---------------------------------------------------------------------------------------------------------------------------
    def safe_scale_delta(current, base):
        return current / base if abs(base) > 0.000001 else current

    #---------------------------------------------------------------------------------------------------------------------------
    def uniformized_scale(scale):
        uniform = (abs(scale.x) + abs(scale.y) + abs(scale.z)) / 3.0
        return (
            uniform if scale.x >= 0 else -uniform,
            uniform if scale.y >= 0 else -uniform,
            uniform if scale.z >= 0 else -uniform,
        )

    #---------------------------------------------------------------------------------------------------------------------------
    def matrix_without_nonuniform_scale(matrix):
        if not EXPORT_REMOVE_NONUNIFORM_SCALE:
            return matrix

        scale = matrix.to_scale()
        uniform_scale = uniformized_scale(scale)
        result = matrix.to_3x3().normalized().to_4x4() @ Matrix.Diagonal(uniform_scale).to_4x4()
        result.translation = matrix.translation
        return result

    #---------------------------------------------------------------------------------------------------------------------------
    def positive_uniform_matrix_scale(matrix, tolerance=0.0001):
        """Return a positive uniform matrix scale, or None for mirrored/non-uniform transforms."""
        if matrix.to_3x3().determinant() <= 0.0:
            return None

        scale = matrix.to_scale()
        values = (abs(scale.x), abs(scale.y), abs(scale.z))
        average = sum(values) / 3.0
        if average <= 0.000001:
            return None
        if max(abs(value - average) for value in values) > max(tolerance, average * tolerance):
            return None
        return average

    #---------------------------------------------------------------------------------------------------------------------------
    def remove_uniform_scale_factor(matrix, scale):
        if abs(scale - 1.0) <= 0.000001:
            return matrix.copy()
        return matrix @ Matrix.Scale(1.0 / scale, 4)

    #---------------------------------------------------------------------------------------------------------------------------
    def skin_normalization_scale(scene, armature):
        """Find the inherited unit conversion shared by an armature and its weighted meshes.

        EuroLand biped nodes do not reliably handle a unit conversion stored as hierarchy
        scale (the common Blender import case is 0.01). Normalize only when every weighted
        mesh driven by the armature has the same positive uniform world scale. Ambiguous,
        mirrored and non-uniform rigs retain the legacy export path.
        """
        armature_scale = positive_uniform_matrix_scale(armature.matrix_world)
        if armature_scale is None or abs(armature_scale - 1.0) <= 0.000001:
            return 1.0

        weighted_meshes = [
            obj for obj in scene.objects
            if obj.type == 'MESH' and armature_for_mesh(obj) == armature and mesh_has_skin(obj)
        ]
        if not weighted_meshes:
            return 1.0

        for mesh_obj in weighted_meshes:
            mesh_scale = positive_uniform_matrix_scale(mesh_obj.matrix_world)
            if mesh_scale is None or abs(mesh_scale - armature_scale) > max(0.0001, armature_scale * 0.0001):
                return 1.0

        return armature_scale

    #---------------------------------------------------------------------------------------------------------------------------
    def frame_in_range(frame):
        rounded = int(round(frame))
        return START_FRAME <= rounded <= END_FRAME

    #---------------------------------------------------------------------------------------------------------------------------
    def sorted_frame_set(frames):
        valid = {START_FRAME, END_FRAME}
        valid.update(int(round(frame)) for frame in frames if frame_in_range(frame))
        return sorted(valid)

    #---------------------------------------------------------------------------------------------------------------------------
    def action_keyframes(action):
        frames = set()
        for fcurve in iter_action_fcurves(action):
            for point in getattr(fcurve, "keyframe_points", []):
                frames.add(float(point.co[0]))
        return frames

    #---------------------------------------------------------------------------------------------------------------------------
    def nla_strip_keyframes(strip):
        if not strip.action:
            return set()

        action_start = float(strip.action_frame_start)
        action_end = float(strip.action_frame_end)
        action_length = action_end - action_start
        strip_start = float(strip.frame_start)
        strip_end = float(strip.frame_end)
        scale = float(strip.scale)
        repeat = max(1, int(ceil(float(strip.repeat))))
        frames = {strip_start, strip_end}

        if abs(action_length) < 0.000001 or abs(scale) < 0.000001:
            return frames

        cycle_length = action_length * scale
        for cycle in range(repeat):
            cycle_start = strip_start + cycle * cycle_length
            for action_frame in action_keyframes(strip.action):
                frame = cycle_start + (action_frame - action_start) * scale
                if strip_start - 0.000001 <= frame <= strip_end + 0.000001:
                    frames.add(frame)

        return frames

    #---------------------------------------------------------------------------------------------------------------------------
    def animation_data_keyframes(animation_data, include_visibility=True):
        frames = set()
        if not animation_data:
            return frames

        if animation_data.action:
            for fcurve in iter_action_fcurves(animation_data.action):
                if not include_visibility and fcurve.data_path in {'hide_viewport', 'hide_render'}:
                    continue
                for point in getattr(fcurve, "keyframe_points", []):
                    frames.add(point.co[0])

        for track in animation_data.nla_tracks:
            if track.mute:
                continue
            for strip in track.strips:
                if not strip.mute:
                    frames.update(nla_strip_keyframes(strip))

        return frames

    #---------------------------------------------------------------------------------------------------------------------------
    def object_keyframes(obj, include_visibility=False):
        return animation_data_keyframes(obj.animation_data, include_visibility)

    #---------------------------------------------------------------------------------------------------------------------------
    def id_keyframes(data_block):
        return animation_data_keyframes(data_block.animation_data) if data_block else set()

    #---------------------------------------------------------------------------------------------------------------------------
    def sampled_frames():
        sample_step = max(1, FRAMES_PER_SAMPLE)
        frames = list(range(START_FRAME, END_FRAME + 1, sample_step))
        if frames[-1] != END_FRAME:
            frames.append(END_FRAME)
        return frames

    #---------------------------------------------------------------------------------------------------------------------------
    def transform_frames_for(obj):
        if START_FRAME == END_FRAME:
            return [START_FRAME]

        if FORCE_SAMPLE:
            return sampled_frames()

        if USE_KEYS or EXPORT_TRANSFORM_ANIMATION_KEYS:
            frames = object_keyframes(obj, EXPORT_FORCE_MESH_KEYFRAMES_IF_VISIBLE)
            if EXPORT_MESH_KEYFRAMES_FROM_MARKERS:
                frames.update(marker.frame for marker in bpy.context.scene.timeline_markers)
            return sorted_frame_set(frames)

        return list(range(START_FRAME, END_FRAME + 1))

    #---------------------------------------------------------------------------------------------------------------------------
    def mesh_has_transform_animation(obj):
        return EXPORT_MESH_ANIMS and bool(object_keyframes(obj, True))

    #---------------------------------------------------------------------------------------------------------------------------
    def data_frames_for(obj, data_block):
        if START_FRAME == END_FRAME:
            return [START_FRAME]

        if FORCE_SAMPLE:
            return sampled_frames()

        if USE_KEYS or EXPORT_TRANSFORM_ANIMATION_KEYS:
            return sorted_frame_set(object_keyframes(obj) | id_keyframes(data_block))

        return list(range(START_FRAME, END_FRAME + 1))

    #---------------------------------------------------------------------------------------------------------------------------
    def armature_for_mesh(obj):
        if obj.type != 'MESH':
            return None
        if obj.parent and obj.parent.type == 'ARMATURE':
            return obj.parent
        return obj.find_armature()

    #---------------------------------------------------------------------------------------------------------------------------
    def rigid_bone_parent(obj):
        if (
            obj.type == 'MESH'
            and obj.parent
            and obj.parent.type == 'ARMATURE'
            and obj.parent_type == 'BONE'
            and obj.parent_bone
            and obj.parent.data.bones.get(obj.parent_bone)
        ):
            return obj.parent_bone
        return None

    #---------------------------------------------------------------------------------------------------------------------------
    def export_node_name(obj):
        name = obj.name
        armature = armature_for_mesh(obj)
        if not rigid_bone_parent(obj) or not armature:
            return name

        # EuroLand reserves a leading (B)/(b) for GEOMOBJECT nodes that should be
        # converted into biped body bones. A visible rigid attachment must therefore
        # keep its normal mesh name. Only disambiguate a real mesh/bone name clash.
        bone_names = {bone.name.casefold() for bone in armature.data.bones}
        if name.casefold() in bone_names and name[:3].casefold() != '(b)':
            return '%s_mesh' % name
        return name

    #---------------------------------------------------------------------------------------------------------------------------
    def mesh_has_skin(obj):
        armature = armature_for_mesh(obj)
        if not armature or not obj.vertex_groups or not armature.data.bones:
            return False

        bone_names = {bone.name for bone in armature.data.bones}
        deform_group_indices = {
            group.index for group in obj.vertex_groups
            if group.name in bone_names
        }
        return any(
            group.group in deform_group_indices and group.weight > 0
            for vertex in obj.data.vertices
            for group in vertex.groups
        )

    #---------------------------------------------------------------------------------------------------------------------------
    def armature_has_weighted_skin(scene, armature):
        return any(
            obj.type == 'MESH'
            and armature_for_mesh(obj) == armature
            and mesh_has_skin(obj)
            for obj in scene.objects
        )

    #---------------------------------------------------------------------------------------------------------------------------
    def skin_bone_plan(scene, armature):
        """Return every weighted skin bone and the ancestors needed by its hierarchy."""
        cache_key = armature.as_pointer()
        cached = skin_bone_plan_cache.get(cache_key)
        if cached is not None:
            return cached

        armature_bones = armature.data.bones
        weighted_totals = {}
        rigid_bones = set()

        for obj in scene.objects:
            if obj.type != 'MESH' or armature_for_mesh(obj) != armature:
                continue

            rigid_bone = rigid_bone_parent(obj)
            if rigid_bone:
                rigid_bones.add(rigid_bone)

            if mesh_has_skin(obj):
                group_names = {group.index: group.name for group in obj.vertex_groups}
                for vertex in obj.data.vertices:
                    for assignment in vertex.groups:
                        bone_name = group_names.get(assignment.group)
                        if assignment.weight > 0.0 and bone_name in armature_bones:
                            weighted_totals[bone_name] = weighted_totals.get(bone_name, 0.0) + assignment.weight

        def ancestor_chain(bone_name):
            chain = []
            bone = armature_bones.get(bone_name)
            while bone:
                chain.append(bone.name)
                bone = bone.parent
            return chain

        required_all = set()
        for bone_name in set(weighted_totals) | rigid_bones:
            required_all.update(ancestor_chain(bone_name))

        if not required_all:
            required_all = {bone.name for bone in armature_bones}

        selected = required_all
        remap = {bone_name: bone_name for bone_name in weighted_totals}

        result = (selected, remap)
        skin_bone_plan_cache[cache_key] = result
        return result

    #---------------------------------------------------------------------------------------------------------------------------
    def required_bones_for_armature(scene, armature):
        """Return the complete weighted hierarchy used by EuroLand animation nodes."""
        required, _remap = skin_bone_plan(scene, armature)
        return required

    #---------------------------------------------------------------------------------------------------------------------------
    def exported_armatures(scene):
        if 'ARMATURE' in EXPORT_OBJECTS:
            return [obj for obj in scene.objects if obj.type == 'ARMATURE']

        if 'MESH' not in EXPORT_OBJECTS:
            return []

        armatures = []
        seen = set()
        for obj in scene.objects:
            if obj.type != 'MESH' or (not mesh_has_skin(obj) and not rigid_bone_parent(obj)):
                continue

            armature = armature_for_mesh(obj)
            if armature and armature.name not in seen:
                seen.add(armature.name)
                armatures.append(armature)

        return armatures

    def exported_node_names(scene):
        names = set()

        if 'MESH' in EXPORT_OBJECTS:
            names.update(export_node_name(obj) for obj in scene.objects if obj.type == 'MESH')
        if 'CAMERA' in EXPORT_OBJECTS:
            names.update(obj.name for obj in scene.objects if obj.type == 'CAMERA')
        if 'LIGHT' in EXPORT_OBJECTS:
            names.update(obj.name for obj in scene.objects if obj.type == 'LIGHT')
        if 'SHAPE' in EXPORT_OBJECTS:
            names.update(obj.name for obj in scene.objects if obj.type == 'CURVE')
        if 'HELPER' in EXPORT_OBJECTS:
            names.update(obj.name for obj in scene.objects if obj.type == 'EMPTY')

        for armature in exported_armatures(scene):
            names.update(bone.name for bone in armature.data.bones)

        return names

    #---------------------------------------------------------------------------------------------------------------------------
    def parent_name(obj):
        if not obj.parent:
            return None

        bone_parent = rigid_bone_parent(obj)
        if bone_parent:
            # Rigid Blender bone parenting is serialized as a one-bone skin. Keeping
            # NODE_PARENT here makes EuroLand treat the visible mesh as hierarchy
            # scaffolding instead of as the entity deformed by the imported biped.
            return None

        if obj.type == 'MESH' and obj.parent.type == 'ARMATURE' and mesh_has_skin(obj):
            return None

        parent = export_node_name(obj.parent)
        if parent not in exported_node_names(bpy.context.scene):
            return None

        return parent

    #---------------------------------------------------------------------------------------------------------------------------
    def write_parent(out, obj, tab_level=1):
        parent = parent_name(obj)
        if parent:
            out.write('%s*NODE_PARENT "%s"\n' % (get_tabs(tab_level), parent))

    #---------------------------------------------------------------------------------------------------------------------------
    def camera_script_markers(scene):
        exported_cameras = {
            camera for camera in scene.objects
            if camera.type == 'CAMERA'
        }
        return sorted(
            (
                marker for marker in scene.timeline_markers
                if marker.camera in exported_cameras and START_FRAME <= marker.frame <= END_FRAME
            ),
            key=lambda marker: (marker.frame, marker.name),
        )

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
            script_camera_count = len(camera_script_markers(scene))
            properties_list.append({
                "name": "cameraScriptEditor",
                "type": "Numeric",
                "value": script_camera_count
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
        if EXPORT_OUTPUT_FIRST_ONLY:
            START_FRAME = scene.frame_start
            END_FRAME = scene.frame_start
        if END_FRAME < START_FRAME:
            END_FRAME = START_FRAME

        scene.frame_set(EXPORT_STATIC_FRAME)

        frame_rate = scene.render.fps
        FRAMES_COUNT = END_FRAME - START_FRAME + 1

        tick_frequency = 4800
        TICKS_PER_FRAME = max(1, tick_frequency // max(1, frame_rate))

        world_color = scene.world.color if scene.world else (0.8, 0.8, 0.8)
        world_strength = 1.0
        if scene.world and scene.world.use_nodes and scene.world.node_tree:
            nodes = scene.world.node_tree.nodes
            output = next(
                (node for node in nodes if node.type == 'OUTPUT_WORLD' and node.is_active_output),
                None,
            )
            surface = output.inputs.get('Surface') if output else None
            background = (
                surface.links[0].from_node
                if surface and surface.is_linked and surface.links[0].from_node.type == 'BACKGROUND'
                else next((node for node in nodes if node.type == 'BACKGROUND'), None)
            )
            if background:
                color_input = background.inputs.get('Color')
                strength_input = background.inputs.get('Strength')
                if color_input and not color_input.is_linked:
                    world_color = color_input.default_value
                if strength_input and not strength_input.is_linked:
                    world_strength = max(0.0, float(strength_input.default_value))

        export_background = scaled_color(world_color, SCENE_LIGHT_SCALE)
        export_ambient = scaled_color(world_color, SCENE_LIGHT_SCALE * world_strength)

        out.write("*SCENE {\n")
        out.write('\t*SCENE_FILENAME "%s"\n' % bpy.data.filepath)
        out.write('\t*SCENE_FIRSTFRAME %s\n' % 0)
        out.write('\t*SCENE_LASTFRAME %s\n' % (END_FRAME - START_FRAME))
        out.write('\t*SCENE_FRAMESPEED %s\n' % frame_rate)
        out.write('\t*SCENE_TICKSPERFRAME %s\n' % TICKS_PER_FRAME)
        out.write(f'\t*SCENE_BACKGROUND_STATIC {df} {df} {df}\n' % export_background)
        out.write(f'\t*SCENE_AMBIENT_STATIC {df} {df} {df}\n' % export_ambient)
        write_scene_custom_properties(out)
        out.write("}\n\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_material_data(out, mat, tab_level, include_texture):
        tab = get_tabs(tab_level)
        mat_name = mat.name if mat else "Default"

        out.write(f'{tab}*MATERIAL_NAME "%s"\n' % mat_name)
        out.write(f'{tab}*MATERIAL_CLASS "Standard"\n')

        mat_wrap = material_wrap(mat)

        if mat_wrap:
            use_mirror = mat_wrap.metallic > 0.001
            specular = mat_wrap.specular if use_mirror else 0.0
            emission_color = getattr(mat_wrap, "emission_color", (0.0, 0.0, 0.0))
            emission_level = max(emission_color[:3]) if emission_color else 0.0
            self_illum = max(0.0, min(mat_wrap.emission_strength * emission_level, 1.0))
            image = material_diffuse_image(mat) if include_texture else None
            textured = bool(image)
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
                if image:
                    texture_path = export_material_texture_path(mat, filepath, EXTRACT_PACKED_TEXTURES, emit_warning)
                    out.write(f'{tab}*MAP_DIFFUSE {{\n')
                    out.write(f'{tab}\t*MAP_NAME "%s"\n' % image.name)
                    out.write(f'{tab}\t*MAP_CLASS "Bitmap"\n')
                    out.write(f'{tab}\t*MAP_SUBNO 1\n')
                    out.write(f'{tab}\t*MAP_AMOUNT %.2f\n' % (mat_wrap.metallic if use_mirror else MAP_AMOUNT_SCALE))
                    out.write(f'{tab}\t*BITMAP "%s"\n' % (texture_path or ''))
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
    def collect_mesh_occurrences(scene, depsgraph):
        occurrences = []
        used_names = set()

        for obj in scene.objects:
            if obj.type != 'MESH':
                continue
            if obj.parent and obj.parent.instance_type in {'VERTS', 'FACES'}:
                continue
            occurrences.append({
                "object": obj,
                "matrix": obj.matrix_world.copy(),
                "name": unique_export_name(export_node_name(obj), used_names),
                "is_instance": False,
            })

        for instance in depsgraph.object_instances:
            if not instance.is_instance or instance.object.type != 'MESH':
                continue
            source = instance.object.original
            if mesh_has_skin(source) or rigid_bone_parent(source):
                emit_warning(f'Skipping instanced rigged mesh {source.name}; export the rig as a normal object.')
                continue
            occurrences.append({
                "object": source,
                "matrix": instance.matrix_world.copy(),
                "name": unique_export_name(export_node_name(source), used_names),
                "is_instance": True,
            })

        return occurrences

    #---------------------------------------------------------------------------------------------------------------------------
    def collect_scene_materials(occurrences):
        scene_materials = {}

        for occurrence in occurrences:
            obj = occurrence["object"]
            materials = [slot.material for slot in obj.material_slots]
            scene_materials[occurrence["name"]] = materials if materials else [None]

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
        mesh_transform_is_baked = (
            obj_matrix_data["type"] == 'MESH'
            and obj_matrix_data.get("transform_baked", False)
        )

        if is_pivot:
            matrix_data = obj_matrix_data["matrix_transformed"]
            if obj_matrix_data["type"] == 'MESH' and (obj_matrix_data.get("transform_centered", False) or mesh_transform_is_baked):
                matrix_data = Matrix.Identity(4)
            out.write('\t*PIVOT_TM {\n')
        else:
            matrix_data = obj_matrix_data["matrix_original"]
            if obj_matrix_data["type"] == 'MESH' and (obj_matrix_data.get("transform_centered", False) or mesh_transform_is_baked):
                matrix_data = Matrix.Identity(4)
            out.write('\t*NODE_TM {\n')
        matrix_data = matrix_without_nonuniform_scale(matrix_data.copy())
        matrix_data.translation *= GLOBAL_SCALE

        out.write('\t\t*NODE_NAME "%s"\n' % obj_matrix_data["name"])
        inherit_transform = 1 if obj_matrix_data.get("inherit_parent", False) else 0
        out.write('\t\t*INHERIT_POS %d %d %d\n' % ((inherit_transform,) * 3))
        out.write('\t\t*INHERIT_ROT %d %d %d\n' % ((inherit_transform,) * 3))
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
        if matrix_data.to_3x3().determinant() < 0.0:
            out.write('\t\t*TM_MIRRORED\n')
        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_tm_animation(out, name, obj_type, frames, matrix_provider, base_mesh_matrix=None):
        global TICKS_PER_FRAME, START_FRAME, END_FRAME
        original_frame = bpy.context.scene.frame_current

        out.write('\t*TM_ANIMATION {\n')
        out.write('\t\t*NODE_NAME "%s"\n' % name)
        out.write('\t\t*TM_ANIM_FRAMES {\n')

        def mesh_tm_frame_matrix(matrix):
            matrix = matrix_without_nonuniform_scale(matrix.copy())
            rot_matrix = matrix.to_3x3().normalized().to_4x4()
            export_eland = create_euroland_matrix(rot_matrix, obj_type)["eland_matrix"].to_3x3()

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

        try:
            for frame in frames:
                bpy.context.scene.frame_set(frame)
                tick = (frame - START_FRAME) * TICKS_PER_FRAME

                matrix_data = matrix_without_nonuniform_scale(matrix_provider().copy())
                if obj_type == 'MESH':
                    if base_mesh_matrix:
                        matrix_data = matrix_data @ base_mesh_matrix.inverted()
                    matrix_data.translation *= GLOBAL_SCALE
                    eland_matrix = mesh_tm_frame_matrix(matrix_data)
                else:
                    matrix_data.translation *= GLOBAL_SCALE
                    eland_matrix = create_euroland_matrix(matrix_data, obj_type)["eland_matrix"]

                out.write('\t\t\t*TM_FRAME  %-5d' % tick)
                out.write(f' {df} {df} {df}' % (eland_matrix[0].x, eland_matrix[0].y, eland_matrix[0].z))
                out.write(f' {df} {df} {df}' % (eland_matrix[1].x, eland_matrix[1].y, eland_matrix[1].z))
                out.write(f' {df} {df} {df}' % (eland_matrix[2].x, eland_matrix[2].y, eland_matrix[2].z))

                obj_position = eland_matrix.translation
                out.write(f' {df} {df} {df}\n' % (obj_position.x, obj_position.y, obj_position.z))
        finally:
            bpy.context.scene.frame_set(original_frame)

        out.write('\t\t}\n')
        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_animation_node(out, obj, obj_matrix_data):
        base_mesh_matrix = None
        if obj.type == 'MESH' and obj_matrix_data.get("transform_baked", False):
            base_mesh_matrix = matrix_without_nonuniform_scale(obj_matrix_data["matrix_original"].copy())

        write_tm_animation(
            out,
            obj.name,
            obj_matrix_data["type"],
            transform_frames_for(obj),
            lambda: obj.matrix_world,
            base_mesh_matrix
        )

    #---------------------------------------------------------------------------------------------------------------------------
    def transformed_mesh(ob, ob_mat, depsgraph, bake_object_transform=True, use_bind_mesh=False, center_transform=False):
        ob_eval = ob.evaluated_get(depsgraph) if EXPORT_APPLY_MODIFIERS else ob.original
        mesh_is_copy = False

        try:
            if use_bind_mesh:
                mesh = ob.original.data.copy()
                mesh_is_copy = True
            else:
                mesh = ob_eval.to_mesh()
        except RuntimeError:
            return None, None, False, None

        if mesh is None:
            return None, ob_eval, mesh_is_copy, None

        if EXPORT_TRI:
            mesh_triangulate(mesh)

        if not bake_object_transform:
            matrix_transformed = Matrix.Identity(4)
        elif center_transform:
            matrix_transformed = Matrix.Diagonal(ob_mat.to_scale()).to_4x4()
        else:
            matrix_transformed = ob_mat.copy()
        matrix_transformed = matrix_without_nonuniform_scale(matrix_transformed)

        export_matrix = Matrix.Scale(GLOBAL_SCALE, 4) @ (MESH_GLOBAL_MATRIX @ matrix_transformed)
        mesh.transform(export_matrix)

        if (MESH_GLOBAL_MATRIX @ matrix_transformed).determinant() > 0.0:
            mesh.flip_normals()

        return mesh, ob_eval, mesh_is_copy, export_matrix

    #---------------------------------------------------------------------------------------------------------------------------
    def material_index_for_poly(poly, materials):
        if not materials:
            return -1
        if poly.material_index < len(materials):
            return poly.material_index
        return 0

    #---------------------------------------------------------------------------------------------------------------------------
    def write_mesh_data(out, scene, depsgraph, scene_materials, occurrences):
        animation_armatures = exported_armatures(scene) if EXPORT_MESH_ANIMS else []
        for occurrence in occurrences:
            ob_main = occurrence["object"]
            node_name = occurrence["name"]
            is_instance = occurrence["is_instance"]

            # Animation imports turn every ordinary GEOMOBJECT into an Anim Skin.
            # Keep reference floors and unrelated scene geometry out of a biped ESE.
            if animation_armatures and armature_for_mesh(ob_main) not in animation_armatures:
                continue

            instances = [(ob_main, occurrence["matrix"])]

            for ob, ob_mat in instances:
                animated_mesh = mesh_has_transform_animation(ob_main) and not is_instance
                skinned_mesh = mesh_has_skin(ob_main)
                armature = armature_for_mesh(ob_main) if skinned_mesh else None
                bind_uniform_scale = skin_normalization_scale(scene, armature) if armature else 1.0
                bone_parented_mesh = bool(rigid_bone_parent(ob_main))
                morph_mesh = bool(EXPORT_MESH_MORPH and ob_main.data.shape_keys)
                center_transform = TRANSFORM_TO_CENTER and not (animated_mesh or skinned_mesh or bone_parented_mesh)
                if TRANSFORM_TO_CENTER and not center_transform:
                    emit_warning(f'Transform to 0,0,0 is ignored for animated or rigged mesh {ob_main.name}.')
                # The 3ds Max exporter snapshots a Skin modifier at the selected
                # static frame.  Export the evaluated (posed) mesh together with
                # bone NODE_TM values from that same frame; mixing Blender's edit
                # rest mesh with an animated static pose produces an invalid ESE
                # skin reference and can send old EuroLand rasterizers out of range.
                preserve_local_space = False
                if morph_mesh and ob_main.modifiers:
                    emit_warning(f'Modifiers are ignored for morph mesh {ob_main.name} to preserve vertex topology.')
                mesh, ob_eval, mesh_is_copy, mesh_export_matrix = transformed_mesh(
                    ob,
                    ob_mat,
                    depsgraph,
                    bake_object_transform=not center_transform and not preserve_local_space,
                    use_bind_mesh=morph_mesh,
                    center_transform=center_transform,
                )
                if mesh is None:
                    continue

                try:
                    node_matrix = remove_uniform_scale_factor(ob_mat, bind_uniform_scale)
                    matrix_transformed = Matrix.Identity(4) if center_transform else node_matrix.copy()
                    obj_matrix_data = {
                        "name": node_name,
                        "type": ob_main.type,
                        "matrix_original": node_matrix.copy(),
                        "matrix_transformed": matrix_transformed,
                        "animated_mesh": animated_mesh,
                        "transform_baked": not center_transform and not preserve_local_space,
                        "transform_centered": center_transform,
                        "inherit_parent": False,
                    }

                    vertices = mesh.vertices[:]
                    if skinned_mesh:
                        unique_vertices = [tuple(vertex.co) for vertex in vertices]
                        source_vertex_index_map = {vertex.index: vertex.index for vertex in vertices}
                    else:
                        unique_vertices, vertex_index_map = unique_ordered(tuple(v.co) for v in vertices)
                        source_vertex_index_map = {
                            vertex.index: vertex_index_map[tuple(vertex.co)]
                            for vertex in vertices
                        }

                    unique_uvs = []
                    uv_index_map = {}
                    if EXPORT_MESH_UV and mesh.uv_layers.active:
                        unique_uvs, uv_index_map = unique_ordered(
                            (uv.uv.x, uv.uv.y)
                            for uv in mesh.uv_layers.active.data
                        )

                    mesh_materials = scene_materials.get(node_name, [])
                    color_layer = active_color_layer(mesh)
                    unique_colors = []
                    color_index_map = {}
                    synthesize_texture_color = False
                    if EXPORT_MESH_VCOLORS and color_layer:
                        unique_colors, color_index_map = unique_ordered(
                            color_for_loop(mesh, color_layer, loop_index)
                            for loop_index in range(len(mesh.loops))
                        )
                    elif has_textured_material(mesh_materials):
                        synthesize_texture_color = True
                        unique_colors = [(TEXTURE_VERTEX_COLOR_SCALE, TEXTURE_VERTEX_COLOR_SCALE, TEXTURE_VERTEX_COLOR_SCALE, 1.0)]

                    out.write("*GEOMOBJECT {\n")
                    out.write('\t*NODE_NAME "%s"\n' % node_name)
                    if not is_instance:
                        write_parent(out, ob_main)
                    write_tm_node(out, obj_matrix_data)
                    write_tm_node(out, obj_matrix_data, True)

                    out.write('\t*MESH {\n')
                    static_tick = (EXPORT_STATIC_FRAME - START_FRAME) * TICKS_PER_FRAME
                    out.write('\t\t*TIMEVALUE %d\n' % static_tick)
                    out.write('\t\t*MESH_NUMVERTEX %u\n' % len(unique_vertices))
                    out.write('\t\t*MESH_NUMFACES %u\n' % len(mesh.polygons))

                    out.write('\t\t*MESH_VERTEX_LIST {\n')
                    for index, vertex in enumerate(unique_vertices):
                        out.write(f'\t\t\t*MESH_VERTEX  {index:>5d}\t{df}\t{df}\t{df}\n' % vertex)
                    out.write('\t\t}\n')

                    out.write('\t\t*MESH_FACE_LIST {\n')
                    for poly_index, poly in enumerate(mesh.polygons):
                        vertex_indices = [source_vertex_index_map[v] for v in poly.vertices]
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
                                        color = color_for_loop(mesh, color_layer, loop_index)
                                        color_indices.append(color_index_map.get(color, -1))
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
                                export_vertex_index = source_vertex_index_map[vertex_index]
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
                                        export_vertex_index = source_vertex_index_map[vertex.index]
                                        out.write('\t\t\t*VFLAG %u %u\n' % (export_vertex_index, flag_value))
                        out.write('\t\t}\n')

                    out.write('\t}\n')

                    if EXPORT_MESH_ANIMS and animated_mesh and not bone_parented_mesh:
                        write_animation_node(out, ob_main, obj_matrix_data)

                    out.write('\t*PROP_MOTIONBLUR 0\n')
                    out.write('\t*PROP_CASTSHADOW 1\n')
                    out.write('\t*PROP_RECVSHADOW 1\n')
                    out.write(f'\t*WIREFRAME_COLOR {df} {df} {df}\n' % (ob.color[0], ob.color[1], ob.color[2]))

                    if EXPORT_MATERIALS and node_name in scene_materials:
                        out.write('\t*MATERIAL_REF %d\n' % list(scene_materials.keys()).index(node_name))

                    out.write('\t*MESH_ANIMATION {\n')
                    out.write('\t}\n')

                    if EXPORT_MESH_MORPH and ob.data.shape_keys:
                        write_morph_data(out, ob)

                    if mesh_has_skin(ob_main) or bone_parented_mesh:
                        write_skin_data(out, scene, ob_main, vertices, source_vertex_index_map)

                    out.write("}\n")

                    if EXPORT_MESH_MORPH and ob.data.shape_keys:
                        write_morph_list(out, ob, mesh_export_matrix)
                finally:
                    if mesh_is_copy:
                        bpy.data.meshes.remove(mesh)
                    else:
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
    def write_morph_list(out, ob, export_matrix):
        out.write('*MORPH_LIST {\n')
        for shape_key in ob.data.shape_keys.key_blocks:
            if shape_key.relative_key != shape_key:
                out.write('\t*MORPH_TARGET "%s" %u {\n' % (shape_key.name.replace(' ', '_'), len(shape_key.data)))
                for vert in shape_key.data:
                    co = export_matrix @ vert.co
                    out.write('\t\t%s\t%s\t%s\n' % (df % co.x, df % co.y, df % co.z))
                out.write('\t}\n')
        out.write('}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_skin_data(out, scene, ob, vertices, source_vertex_index_map):
        armature = armature_for_mesh(ob)
        if not armature:
            return

        rigid_bone = rigid_bone_parent(ob)
        if rigid_bone:
            export_vertex_indices = sorted(set(source_vertex_index_map.values()))
            out.write('\t*SKIN_DATA {\n')
            out.write('\t\t*NODE_NAME "%s"\n' % export_node_name(ob))
            out.write('\t\t*BONE_LIST {\n')
            out.write('\t\t\t*BONE\t0\t"%s"\n' % rigid_bone)
            out.write('\t\t}\n')
            out.write('\t\t*SKIN_VERTEX_DATA {\n')
            for vertex_index in export_vertex_indices:
                out.write(f'\t\t\t*VERTEX\t{vertex_index}\t1\t0\t{df}\n' % 1.0)
            out.write('\t\t}\n')
            out.write('\t}\n')
            return

        original_vertices = ob.data.vertices
        vertex_groups = {group.index: group.name for group in ob.vertex_groups}
        armature_bone_names = {bone.name for bone in armature.data.bones}
        used_group_names = set()

        for vertex in original_vertices:
            for group in vertex.groups:
                group_name = vertex_groups.get(group.group)
                if group_name in armature_bone_names and group.weight > 0:
                    used_group_names.add(group_name)

        _selected_bones, bone_remap = skin_bone_plan(scene, armature)

        # 3ds Max writes the Skin modifier's bone table, not hierarchy order. Blender's
        # vertex-group order is the closest stable equivalent; deduplicate defensively.
        bone_names = []
        for group in ob.vertex_groups:
            if group.name not in used_group_names:
                continue
            mapped_name = bone_remap.get(group.name, group.name)
            if mapped_name and mapped_name not in bone_names:
                bone_names.append(mapped_name)
        bone_indices = {bone_name: index for index, bone_name in enumerate(bone_names)}
        weighted_vertices = {index: [] for index in range(len(vertices))}

        for original_index, vertex in enumerate(vertices):
            if original_index >= len(original_vertices):
                continue

            export_vertex_index = source_vertex_index_map.get(original_index)
            if export_vertex_index is None:
                continue

            influence_weights = {}
            for group in original_vertices[original_index].groups:
                bone_name = vertex_groups.get(group.group)
                mapped_name = bone_remap.get(bone_name, bone_name)
                if mapped_name in bone_indices and group.weight > 0:
                    bone_index = bone_indices[mapped_name]
                    influence_weights[bone_index] = influence_weights.get(bone_index, 0.0) + group.weight

            influences = list(influence_weights.items())

            # EuroLand's runtime skin formats support at most four influences per
            # vertex. Keep the strongest four and normalize after truncation.
            influences.sort(key=lambda item: (-item[1], item[0]))
            influences = influences[:4]
            total_weight = sum(weight for _, weight in influences)
            if total_weight:
                influences = [(bone_index, weight / total_weight) for bone_index, weight in influences]
            influences.sort(key=lambda item: item[0])

            weighted_vertices[export_vertex_index] = influences

        out.write('\t*SKIN_DATA {\n')
        out.write('\t\t*NODE_NAME "%s"\n' % ob.name)
        out.write('\t\t*BONE_LIST {\n')
        for bone_index, bone_name in enumerate(bone_names):
            out.write('\t\t\t*BONE\t%u\t"%s"\n' % (bone_index, bone_name))
        out.write('\t\t}\n')

        out.write('\t\t*SKIN_VERTEX_DATA {\n')
        for vertex_index, influences in sorted(weighted_vertices.items()):
            out.write('\t\t\t*VERTEX\t%u\t%u' % (vertex_index, len(influences)))
            for bone_index, weight in influences:
                out.write(f'\t%u\t{df}' % (bone_index, weight))
            out.write('\n')
        out.write('\t\t}\n')
        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def pose_bone_world_matrix(armature, bone_name):
        pose_bone = armature.pose.bones.get(bone_name) if armature.pose else None
        if pose_bone:
            return armature.matrix_world @ pose_bone.matrix

        return armature.matrix_world @ armature.data.bones[bone_name].matrix_local

    #---------------------------------------------------------------------------------------------------------------------------
    def pose_bone_animation_matrix(armature, bone_name, normalization_scale=1.0):
        pose_bone = armature.pose.bones.get(bone_name) if armature.pose else None
        if not pose_bone:
            bone = armature.data.bones[bone_name]
            if bone.parent:
                matrix = bone.parent.matrix_local.inverted_safe() @ bone.matrix_local
                matrix.translation *= normalization_scale
                return matrix
            return remove_uniform_scale_factor(armature.matrix_world @ bone.matrix_local, normalization_scale)

        if pose_bone.parent:
            matrix = pose_bone.parent.matrix.inverted_safe() @ pose_bone.matrix
            matrix.translation *= normalization_scale
            return matrix
        return remove_uniform_scale_factor(armature.matrix_world @ pose_bone.matrix, normalization_scale)

    #---------------------------------------------------------------------------------------------------------------------------
    def armature_animation_frames(armature):
        if START_FRAME == END_FRAME:
            return [START_FRAME]

        if FORCE_SAMPLE:
            return sampled_frames()

        if USE_KEYS or EXPORT_TRANSFORM_ANIMATION_KEYS:
            return sorted_frame_set(object_keyframes(armature) | id_keyframes(armature.data))

        return list(range(START_FRAME, END_FRAME + 1))

    #---------------------------------------------------------------------------------------------------------------------------
    def write_bone_display_mesh(out, bone, normalization_scale=1.0):
        radius = max(float(bone.length) * normalization_scale * 0.06 * GLOBAL_SCALE, 0.001)
        vertices = [
            Vector((0.0, radius, 0.0)),
            Vector((radius, 0.0, 0.0)),
            Vector((0.0, 0.0, radius)),
            Vector((-radius, 0.0, 0.0)),
            Vector((0.0, 0.0, -radius)),
            Vector((0.0, -radius, 0.0)),
        ]
        faces = [
            (0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1),
            (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4),
        ]

        out.write('\t*MESH {\n')
        out.write('\t\t*TIMEVALUE 0\n')
        out.write('\t\t*MESH_NUMVERTEX %u\n' % len(vertices))
        out.write('\t\t*MESH_NUMFACES %u\n' % len(faces))
        out.write('\t\t*MESH_VERTEX_LIST {\n')
        for index, vertex in enumerate(vertices):
            out.write(f'\t\t\t*MESH_VERTEX  {index:>5d}\t{df}\t{df}\t{df}\n' % tuple(vertex))
        out.write('\t\t}\n')
        out.write('\t\t*MESH_FACE_LIST {\n')
        for index, face in enumerate(faces):
            out.write('\t\t\t*MESH_FACE    {:>3d}:    A: {:>6d} B: {:>6d} C: {:>6d}'.format(
                index, face[0], face[1], face[2]
            ))
            out.write('    AB: %-6d BC: %-6d CA: %-6d  *MESH_SMOOTHING %u  *MESH_MTLID %-3d\n' % (
                1, 1, 1, 1, -1
            ))
        out.write('\t\t}\n')
        out.write('\t\t*MESH_NORMALS {\n')
        for index, face in enumerate(faces):
            a, b, c = (vertices[vertex_index] for vertex_index in face)
            normal = (b - a).cross(c - a).normalized()
            out.write(f'\t\t\t*MESH_FACENORMAL {index}\t{df}\t{df}\t{df}\n' % tuple(normal))
            for vertex_index in face:
                vertex_normal = vertices[vertex_index].normalized()
                out.write(f'\t\t\t\t*MESH_VERTEXNORMAL {vertex_index}\t{df}\t{df}\t{df}\n' % tuple(vertex_normal))
        out.write('\t\t}\n')
        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def write_biped_bones(out, scene, depsgraph):
        for ob_main in exported_armatures(scene):
            if ob_main.type != 'ARMATURE':
                continue

            bone_data = ob_main.evaluated_get(depsgraph).data if EXPORT_APPLY_MODIFIERS else ob_main.data
            normalization_scale = skin_normalization_scale(scene, ob_main)
            weighted_skin = armature_has_weighted_skin(scene, ob_main)
            required_bones = required_bones_for_armature(scene, ob_main) if weighted_skin else None

            for bone in bone_data.bones:
                if required_bones is not None and bone.name not in required_bones:
                    continue
                is_root = bone.parent is None
                # ESE NODE_TM is the transform at the selected static output frame.
                # Weighted meshes above are evaluated at this same frame, matching
                # the reference pose emitted by Eurocom's original 3ds Max plug-in.
                bone_matrix = pose_bone_world_matrix(ob_main, bone.name)
                bone_matrix = remove_uniform_scale_factor(
                    bone_matrix,
                    normalization_scale,
                )
                obj_matrix_data = {
                    "name": bone.name,
                    "type": 'BONE',
                    "matrix_original": bone_matrix.copy(),
                    "matrix_transformed": bone_matrix.copy()
                }

                out.write('*%s {\n' % ('GEOMOBJECT' if is_root else 'BONEOBJECT'))
                out.write('\t*NODE_NAME "%s"\n' % bone.name)
                if bone.parent:
                    out.write('\t*NODE_PARENT "%s"\n' % bone.parent.name)
                out.write('\t*%s\n' % ('NODE_BIPED_SLAVE' if is_root else 'NODE_BIPED_BODY'))
                write_tm_node(out, obj_matrix_data)
                write_tm_node(out, obj_matrix_data, True)
                write_bone_display_mesh(out, bone, normalization_scale)
                if is_root:
                    out.write('\t*PROP_MOTIONBLUR 0\n')
                    out.write('\t*PROP_CASTSHADOW 1\n')
                    out.write('\t*PROP_RECVSHADOW 1\n')
                write_tm_animation(
                    out,
                    bone.name,
                    'BONE',
                    armature_animation_frames(ob_main),
                    lambda armature=ob_main, bone_name=bone.name, scale=normalization_scale:
                        pose_bone_animation_matrix(armature, bone_name, scale)
                )
                if is_root:
                    out.write(f'\t*WIREFRAME_COLOR {df} {df} {df}\n' % (0.6510, 0.7922, 0.9412))
                    out.write('\t*MESH_ANIMATION {\n')
                    out.write('\t}\n')
                out.write('}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def light_energy_scale(light_data):
        """Convert Blender light power to the unitless multiplier used by 3ds Max ESE."""
        if 'ese_intensity' in light_data:
            return max(0.0, float(light_data['ese_intensity']))
        energy = max(0.0, float(getattr(light_data, 'energy', 0.0)))
        return energy if light_data.type == 'SUN' else energy / 1000.0

    #---------------------------------------------------------------------------------------------------------------------------
    def light_attenuation(light_data):
        """Return (enabled, start, end) for EuroLand's far attenuation model."""
        if light_data.type == 'SUN':
            return False, 0.0, 0.0

        end = max(0.001, float(getattr(light_data, 'cutoff_distance', 25.0)))
        custom_start = light_data.get('ese_attenuation_start')
        start = max(0.0, float(custom_start)) if custom_start is not None else 0.0
        return True, min(start, end), end

    #---------------------------------------------------------------------------------------------------------------------------
    def light_settings_signature(light_data):
        attenuation_enabled, attenuation_start, attenuation_end = light_attenuation(light_data)
        spot_size = float(getattr(light_data, 'spot_size', 0.0)) if light_data.type == 'SPOT' else 0.0
        spot_blend = float(getattr(light_data, 'spot_blend', 0.0)) if light_data.type == 'SPOT' else 0.0
        return (
            tuple(float(component) for component in light_data.color),
            light_energy_scale(light_data),
            attenuation_enabled,
            attenuation_start,
            attenuation_end,
            spot_size,
            spot_blend,
        )

    #---------------------------------------------------------------------------------------------------------------------------
    def light_import_flags(light_data):
        """Map Blender light contribution controls to fields consumed by EuroLand."""
        decay = 'None' if light_data.type == 'SUN' else 'InvSquare'
        affects_diffuse = float(getattr(light_data, 'diffuse_factor', 1.0)) > 0.000001
        affects_specular = float(getattr(light_data, 'specular_factor', 1.0)) > 0.000001
        ambient_only = bool(light_data.get('ese_ambient_only', False))
        return decay, affects_diffuse, affects_specular, ambient_only

    #---------------------------------------------------------------------------------------------------------------------------
    def write_light_settings(out, light_data, current_frame, tab_level=1):
        tab = get_tabs(tab_level)
        attenuation_enabled, attenuation_start, attenuation_end = light_attenuation(light_data)
        is_spot = light_data.type == 'SPOT'
        falloff = degrees(float(getattr(light_data, 'spot_size', 0.0))) if is_spot else -1.0
        spot_blend = max(0.0, min(float(getattr(light_data, 'spot_blend', 0.0)), 1.0))
        hotspot = falloff * (1.0 - spot_blend) if is_spot else -1.0
        target_distance = attenuation_end if is_spot else -1.0

        out.write(f'{tab}*LIGHT_SETTINGS {{\n')
        out.write(f'{tab}\t*TIMEVALUE %u\n' % current_frame)
        # EuroLand's ESE importer consumes the short field names below. Keep
        # the standard 3ds Max ESE fields as well for round-trip compatibility.
        out.write(f'{tab}\t*COLOR {df} {df} {df}\n' % tuple(light_data.color))
        if attenuation_enabled:
            out.write(f'{tab}\t*FAR_ATTEN {df} {df}\n' % (attenuation_start, attenuation_end))
        if is_spot:
            out.write(f'{tab}\t*HOTSPOT {df}\n' % falloff)
        out.write(f'{tab}\t*LIGHT_COLOR {df} {df} {df}\n' % tuple(light_data.color))
        out.write(f'{tab}\t*LIGHT_INTENS {df}\n' % light_energy_scale(light_data))
        out.write(f'{tab}\t*LIGHT_ASPECT {df}\n' % (1.0 if is_spot else -1.0))
        if is_spot:
            out.write(f'{tab}\t*LIGHT_HOTSPOT {df}\n' % hotspot)
            out.write(f'{tab}\t*LIGHT_FALLOFF {df}\n' % falloff)
        if attenuation_enabled:
            out.write(f'{tab}\t*LIGHT_ATTNSTART {df}\n' % attenuation_start)
            out.write(f'{tab}\t*LIGHT_ATTNEND {df}\n' % attenuation_end)
        out.write(f'{tab}\t*LIGHT_TDIST {df}\n' % target_distance)
        out.write(f'{tab}\t*LIGHT_MAPBIAS {df}\n' % 1.0)
        out.write(f'{tab}\t*LIGHT_MAPRANGE {df}\n' % 4.0)
        out.write(f'{tab}\t*LIGHT_MAPSIZE 512\n')
        out.write(f'{tab}\t*LIGHT_RAYBIAS {df}\n' % 0.0)
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
                # Light datablocks have no exportable modifiers. Keep the original
                # RNA object here: evaluated light data can become invalid after a
                # frame change and has caused access violations in Blender 5.x.
                light_data = ob.original.data

                obj_matrix_data = {
                    "name": ob_main.name,
                    "type": ob_main.type,
                    "matrix_original": ob_mat.copy(),
                    "matrix_transformed": ob_mat.copy()
                }

                out.write("*LIGHTOBJECT {\n")
                out.write('\t*NODE_NAME "%s"\n' % ob.name)
                write_parent(out, ob)

                type_lut = {'POINT': 'Omni', 'SPOT': 'TargetSpot', 'SUN': 'Omni', 'AREA': 'Omni'}
                if light_data.type == 'AREA':
                    emit_warning(
                        f'Area light {ob.name} is exported as an attenuated Omni light; '
                        'ESE cannot preserve its area shape.'
                    )

                out.write('\t*LIGHT_TYPE %s\n' % type_lut.get(light_data.type, 'Omni'))
                write_tm_node(out, obj_matrix_data)
                decay, affects_diffuse, affects_specular, ambient_only = light_import_flags(light_data)
                out.write('\t*LIGHT_DECAY %s\n' % decay)
                out.write('\t*LIGHT_AFFECT_DIFFUSE %s\n' % ('On' if affects_diffuse else 'Off'))
                out.write('\t*LIGHT_AFFECT_SPECULAR %s\n' % ('On' if affects_specular else 'Off'))
                out.write('\t*LIGHT_AMBIENT_ONLY %s\n' % ('On' if ambient_only else 'Off'))
                out.write('\t*LIGHT_SHADOWS %s\n' % ("On" if light_data.use_shadow else "Off"))
                out.write('\t*LIGHT_USELIGHT 1\n')
                out.write('\t*LIGHT_SPOTSHAPE Circle\n')
                out.write('\t*LIGHT_USEGLOBAL 0\n')
                out.write('\t*LIGHT_ABSMAPBIAS 0\n')
                out.write('\t*LIGHT_OVERSHOOT 0\n')

                static_tick = (EXPORT_STATIC_FRAME - START_FRAME) * TICKS_PER_FRAME
                write_light_settings(out, light_data, static_tick)

                if EXPORT_CAMERA_LIGHT_ANIMS:
                    out.write('\t*LIGHT_ANIMATION {\n')
                    previous = None
                    light_frames = data_frames_for(ob_main, light_data)
                    for frame in light_frames:
                        scene.frame_set(frame)
                        current_light = ob_main.data
                        tick = (frame - START_FRAME) * TICKS_PER_FRAME
                        current = light_settings_signature(current_light)
                        if previous != current:
                            write_light_settings(out, current_light, tick, 2)
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
        if legacy_fcurves:
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
    def write_script_camera(out):
        scene = bpy.context.scene
        markers = camera_script_markers(scene)

        out.write('\t*USER_DATA %u {\n' % (3 + len(markers)))
        out.write('\t\tCameraScript = %u\n' % 1)
        out.write('\t\tCameraScript_numCameras = %u\n' % len(markers))
        out.write('\t\tCameraScript_globalOffset = %u\n' % 0)

        for index, marker in enumerate(markers, start=1):
            camera = marker.camera
            keyframes = sorted(
                frame for frame in (object_keyframes(camera) | id_keyframes(camera.data))
                if frame_in_range(frame)
            )

            first_keyframe = int(keyframes[0]) if keyframes else marker.frame
            last_keyframe = int(keyframes[-1]) if keyframes else marker.frame
            timeline_frame = min(END_FRAME, marker.frame + (last_keyframe - first_keyframe))
            out.write('\t\tCameraScript_camera%u = %s %u %u %u %u\n' % (
                # Marker labels are editorial metadata and often match the camera
                # datablock rather than the object. EuroLand resolves camera scripts
                # against exported node names, so always reference the linked object.
                index, camera.name, first_keyframe, last_keyframe, marker.frame, timeline_frame
            ))

        out.write('\t}\n')

    #---------------------------------------------------------------------------------------------------------------------------
    def camera_target_distance(camera_obj, camera_data):
        if 'ese_target_distance' in camera_data:
            return max(0.0, float(camera_data['ese_target_distance'])) * GLOBAL_SCALE

        for constraint in camera_obj.constraints:
            target = getattr(constraint, 'target', None)
            if (
                constraint.type in {'TRACK_TO', 'DAMPED_TRACK', 'LOCKED_TRACK'}
                and not constraint.mute
                and target is not None
            ):
                return (camera_obj.matrix_world.translation - target.matrix_world.translation).length * GLOBAL_SCALE

        dof = getattr(camera_data, 'dof', None)
        focus_object = getattr(dof, 'focus_object', None) if dof else None
        if focus_object is not None:
            return (camera_obj.matrix_world.translation - focus_object.matrix_world.translation).length * GLOBAL_SCALE

        return max(0.0, float(getattr(dof, 'focus_distance', 10.0))) * GLOBAL_SCALE

    #---------------------------------------------------------------------------------------------------------------------------
    def write_camera_settings(out, camera_obj, camera_data, current_frame, tab_level=1):
        tab = get_tabs(tab_level)

        out.write(f'{tab}*CAMERA_SETTINGS {{\n')
        out.write(f'{tab}\t*TIMEVALUE %u\n' % current_frame)
        out.write(f'{tab}\t*CAMERA_NEAR {df}\n' % (camera_data.clip_start * GLOBAL_SCALE))
        out.write(f'{tab}\t*CAMERA_FAR {df}\n' % (camera_data.clip_end * GLOBAL_SCALE))
        out.write(f'{tab}\t*CAMERA_FOV {df}\n' % camera_data.angle)
        out.write(f'{tab}\t*CAMERA_TDIST {df}\n' % camera_target_distance(camera_obj, camera_data))
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
                # Camera datablocks have no exportable modifiers. Evaluated RNA
                # can become invalid after frame_set() in Blender 5.x, so always
                # sample the original datablock at the current scene frame.
                camera_data = ob.original.data

                obj_matrix_data = {
                    "name": ob.name,
                    "type": ob_main.type,
                    "matrix_original": ob_mat.copy(),
                    "matrix_transformed": ob_mat.copy()
                }

                out.write("*CAMERAOBJECT {\n")
                out.write('\t*NODE_NAME "%s"\n' % ob.name)
                write_parent(out, ob)
                out.write('\t*CAMERA_TYPE Target\n')
                write_tm_node(out, obj_matrix_data)
                static_tick = (EXPORT_STATIC_FRAME - START_FRAME) * TICKS_PER_FRAME
                write_camera_settings(out, ob_main, camera_data, static_tick)

                if EXPORT_CAMERA_LIGHT_ANIMS:
                    out.write('\t*CAMERA_ANIMATION {\n')
                    previous = None
                    for frame in data_frames_for(ob_main, camera_data):
                        scene.frame_set(frame)
                        current_data = ob_main.data
                        tick = (frame - START_FRAME) * TICKS_PER_FRAME
                        current = (
                            float(current_data.clip_start),
                            float(current_data.clip_end),
                            float(current_data.angle),
                            camera_target_distance(ob_main, current_data),
                        )
                        if previous != current:
                            write_camera_settings(out, ob_main, current_data, tick, 2)
                            previous = current
                    out.write('\t}\n')
                    write_animation_node(out, ob_main, obj_matrix_data)

                if ob_main == cameras[-1] and user_wants_camera_script(scene):
                    write_script_camera(out)

                out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_helper_data(out, scene):
        for ob in sorted([obj for obj in scene.objects if obj.type == 'EMPTY'], key=lambda obj: obj.name):
            obj_matrix_data = {
                "name": ob.name,
                "type": ob.type,
                "matrix_original": ob.matrix_world.copy(),
                "matrix_transformed": ob.matrix_world.copy()
            }

            out.write("*HELPEROBJECT {\n")
            out.write('\t*NODE_NAME "%s"\n' % ob.name)
            write_parent(out, ob)
            write_tm_node(out, obj_matrix_data)

            if EXPORT_CAMERA_LIGHT_ANIMS or EXPORT_TRANSFORM_ANIMATION_KEYS:
                write_animation_node(out, ob, obj_matrix_data)

            out.write("}\n")

    #---------------------------------------------------------------------------------------------------------------------------
    def write_shape_data(out, scene):
        for ob in sorted([obj for obj in scene.objects if obj.type == 'CURVE'], key=lambda obj: obj.name):
            obj_matrix_data = {
                "name": ob.name,
                "type": ob.type,
                "matrix_original": ob.matrix_world.copy(),
                "matrix_transformed": ob.matrix_world.copy()
            }

            out.write("*SHAPEOBJECT {\n")
            out.write('\t*NODE_NAME "%s"\n' % ob.name)
            write_parent(out, ob)
            write_tm_node(out, obj_matrix_data)

            if EXPORT_CAMERA_LIGHT_ANIMS or EXPORT_TRANSFORM_ANIMATION_KEYS:
                write_animation_node(out, ob, obj_matrix_data)

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

        for occurrence in occurrences:
            obj = occurrence["object"]
            pointer = obj.as_pointer()
            if pointer in checked_objects:
                continue
            checked_objects.add(pointer)

            materials = [slot.material for slot in obj.material_slots if slot.material]
            images = [material_diffuse_image(mat) for mat in materials]
            images = [image for image in images if image]
            if images and (not EXPORT_MESH_UV or not obj.data.uv_layers):
                warnings.add(f'Textured mesh {obj.name} has no exported UV coordinates.')
            for image in images:
                if not image.filepath and not (image.packed_file and EXTRACT_PACKED_TEXTURES):
                    warnings.add(f'Image {image.name} has no file path and cannot be referenced by EuroLand.')

            for mat in materials:
                principled = material_principled_node(mat)
                base_color = principled.inputs.get('Base Color') if principled else None
                if base_color and base_color.is_linked and not material_diffuse_image(mat):
                    warnings.add(f'Material {mat.name} uses a procedural Base Color and must be baked to an image.')

            if EXPORT_MESH_ANIMS and USE_KEYS and not FORCE_SAMPLE:
                has_drivers = bool(obj.animation_data and obj.animation_data.drivers)
                if obj.constraints or has_drivers:
                    warnings.add(f'Animated mesh {obj.name} uses constraints or drivers; enable Force Sample.')

            armature = armature_for_mesh(obj)
            if armature:
                bone_names = {bone.name for bone in armature.data.bones}
                unused_groups = sorted(group.name for group in obj.vertex_groups if group.name not in bone_names)
                if unused_groups:
                    warnings.add(f'Mesh {obj.name} has vertex groups that are not bones: {", ".join(unused_groups)}.')

        for warning in sorted(warnings):
            emit_warning(warning)

    #---------------------------------------------------------------------------------------------------------------------------
    def write_ese_file():
        scene = bpy.context.scene
        original_frame = scene.frame_current
        active_object = getattr(context, "object", None)
        original_mode = active_object.mode if active_object else None

        try:
            if bpy.ops.object.mode_set.poll():
                bpy.ops.object.mode_set(mode='OBJECT')

            scene.frame_set(EXPORT_STATIC_FRAME)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            mesh_occurrences = collect_mesh_occurrences(scene, depsgraph)
            validate_export(mesh_occurrences)

            plugin_version = get_plugin_version()

            with open(filepath, 'w', encoding="utf8") as out:
                out.write("*3DSMAX_EUROEXPORT\t300\n")
                out.write('*COMMENT "Eurocom Export Version  3.00 - %s"\n' % datetime.now().strftime("%A %B %d %Y %H:%M"))
                out.write('*COMMENT "Version of Blender that output this file: %s"\n' % bpy.app.version_string)
                out.write('*COMMENT "Version of ESE Plug-in: %d.%d.%d"\n\n' % (
                    plugin_version[0], plugin_version[1], plugin_version[2]
                ))

                write_scene_data(out, scene)

                scene_materials = collect_scene_materials(mesh_occurrences) if EXPORT_MATERIALS else {}
                if EXPORT_MATERIALS:
                    write_scene_materials(out, scene_materials)

                if 'MESH' in EXPORT_OBJECTS:
                    write_mesh_data(out, scene, depsgraph, scene_materials, mesh_occurrences)
                if 'CAMERA' in EXPORT_OBJECTS:
                    write_camera_data(out, scene, depsgraph)
                if 'LIGHT' in EXPORT_OBJECTS:
                    write_light_data(out, scene, depsgraph)
                if 'SHAPE' in EXPORT_OBJECTS:
                    write_shape_data(out, scene)
                if 'HELPER' in EXPORT_OBJECTS:
                    write_helper_data(out, scene)
                if exported_armatures(scene):
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
         Output_Remove_NonUniform_Scale=False,
         Use_Keys=True,
         Force_Sample=False,
         Frames_Per_Sample=1,
         Extract_Packed_Textures=True,
         report=None):

    _write(context, filepath,
           EXPORT_MESH_FLAGS=Output_Mesh_Definition,
           EXPORT_MATERIALS=Output_Materials,
           EXTRACT_PACKED_TEXTURES=Extract_Packed_Textures,
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
           EXPORT_OUTPUT_FIRST_ONLY=Output_First_Only,
           EXPORT_TRANSFORM_ANIMATION_KEYS=Output_Transform_Animation_Keys,
           EXPORT_MESH_KEYFRAMES_FROM_MARKERS=Output_Mesh_Keyframes_From_Market,
           EXPORT_FORCE_MESH_KEYFRAMES_IF_VISIBLE=Output_Force_Mesh_Keyframes_If_Visible,
           EXPORT_REMOVE_NONUNIFORM_SCALE=Output_Remove_NonUniform_Scale,
           USE_KEYS=Use_Keys,
           FORCE_SAMPLE=Force_Sample,
           FRAMES_PER_SAMPLE=Frames_Per_Sample,
           REPORT=report)

    return {'FINISHED'}


if __name__ == '__main__':
    save({}, str(Path.home()) + '/Desktop/EurocomESE.ese')
