import bpy
import re
from pathlib import Path
from mathutils import Matrix, Euler
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
from . import bl_info

#-------------------------------------------------------------------------------------------------------------------------------
MESH_GLOBAL_MATRIX = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0))).to_4x4()
ROT_GLOBAL_MATRIX = Matrix(((1, 0, 0),(0, 1, 0),(0, 0, 1))).to_4x4()

#-------------------------------------------------------------------------------------------------------------------------------
def get_plugin_version():
    version = bl_info.get('version', (0, 0, 0))  # Obtiene la versión o (0, 0, 0) si no está definida
    return version

#-------------------------------------------------------------------------------------------------------------------------------
def tri_edge_is_from_ngon(polygon, tri_loop_indices, tri_idx, mesh_loops):
    loop_start = polygon.loop_start
    loop_end = loop_start + polygon.loop_total

    current_loop_idx = tri_loop_indices[tri_idx]
    next_loop_idx = tri_loop_indices[(tri_idx + 1) % len(tri_loop_indices)]

    return next_loop_idx not in range(loop_start, loop_end) or current_loop_idx not in range(loop_start, loop_end)

#-------------------------------------------------------------------------------------------------------------------------------
def mesh_triangulate(me):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()

#-------------------------------------------------------------------------------------------------------------------------------
def get_tabs(level):
    return '\t' * level

#-------------------------------------------------------------------------------------------------------------------------------
def unique_ordered(values):
    result = []
    index_map = {}

    for value in values:
        if value not in index_map:
            index_map[value] = len(result)
            result.append(value)

    return result, index_map

#-------------------------------------------------------------------------------------------------------------------------------
def scaled_color(color, scale):
    return tuple(max(0.0, min(component * scale, 1.0)) for component in color[:3])

#-------------------------------------------------------------------------------------------------------------------------------
def color_layer_data(mesh):
    if hasattr(mesh, "color_attributes") and mesh.color_attributes:
        active = mesh.color_attributes.active_color or mesh.color_attributes.active
        return active.data if active else None

    if mesh.vertex_colors:
        active = mesh.vertex_colors.active
        return active.data if active else None

    return None

#-------------------------------------------------------------------------------------------------------------------------------
def active_color_layer(mesh):
    if hasattr(mesh, "color_attributes") and mesh.color_attributes:
        return mesh.color_attributes.active_color or mesh.color_attributes.active

    if mesh.vertex_colors:
        return mesh.vertex_colors.active

    return None

#-------------------------------------------------------------------------------------------------------------------------------
def color_layers(mesh):
    if hasattr(mesh, "color_attributes") and mesh.color_attributes:
        return [
            attr for attr in mesh.color_attributes
            if attr.domain in {'CORNER', 'POINT'} and attr.data_type in {'BYTE_COLOR', 'FLOAT_COLOR'}
        ]

    return list(mesh.vertex_colors)

#-------------------------------------------------------------------------------------------------------------------------------
def color_for_loop(mesh, color_layer, loop_index):
    if not color_layer:
        return None

    data_index = loop_index
    if getattr(color_layer, 'domain', 'CORNER') == 'POINT':
        data_index = mesh.loops[loop_index].vertex_index

    if data_index < 0 or data_index >= len(color_layer.data):
        return None
    return tuple(color_layer.data[data_index].color)

#-------------------------------------------------------------------------------------------------------------------------------
def int_attribute(mesh, name, domain):
    attr = mesh.attributes.get(name)
    if attr and attr.data_type == 'INT' and attr.domain == domain:
        return attr
    return None

#-------------------------------------------------------------------------------------------------------------------------------
def material_wrap(mat):
    return PrincipledBSDFWrapper(mat) if mat and mat.use_nodes else None

#-------------------------------------------------------------------------------------------------------------------------------
def _node_input(node, *names):
    if not node:
        return None
    for name in names:
        socket = node.inputs.get(name)
        if socket:
            return socket
    return None

#-------------------------------------------------------------------------------------------------------------------------------
def _upstream_nodes(socket):
    if not socket:
        return []

    pending = [(link.from_node, 0) for link in socket.links]
    visited = set()
    result = []

    while pending:
        node, distance = pending.pop(0)
        pointer = node.as_pointer()
        if pointer in visited:
            continue
        visited.add(pointer)
        result.append((node, distance))

        for input_socket in node.inputs:
            pending.extend((link.from_node, distance + 1) for link in input_socket.links)

    return result

#-------------------------------------------------------------------------------------------------------------------------------
def material_surface_nodes(mat):
    if not mat or not mat.use_nodes or not mat.node_tree:
        return []

    outputs = [
        node for node in mat.node_tree.nodes
        if node.bl_idname == 'ShaderNodeOutputMaterial'
    ]
    outputs.sort(key=lambda node: not getattr(node, "is_active_output", False))
    for output in outputs:
        nodes = _upstream_nodes(_node_input(output, 'Surface'))
        if nodes:
            return nodes
    return []

#-------------------------------------------------------------------------------------------------------------------------------
def material_principled_node(mat):
    if not mat or not mat.use_nodes or not mat.node_tree:
        return None

    for node, _distance in material_surface_nodes(mat):
        if node.bl_idname == 'ShaderNodeBsdfPrincipled':
            return node

    return next(
        (node for node in mat.node_tree.nodes if node.bl_idname == 'ShaderNodeBsdfPrincipled'),
        None,
    )

#-------------------------------------------------------------------------------------------------------------------------------
def _diffuse_image_score(node, distance):
    image = getattr(node, "image", None)
    text = ' '.join(filter(None, (
        node.name,
        node.label,
        getattr(image, "name", None),
        getattr(image, "filepath", None),
    ))).casefold().replace('-', '_').replace(' ', '_')

    score = max(0, 20 - distance)
    positive_tokens = {
        'base_color': 140,
        'basecolour': 140,
        'base_colour': 140,
        'albedo': 120,
        'diffuse': 110,
        'color': 45,
        'colour': 45,
    }
    negative_tokens = {
        'ambient_occlusion': -160,
        'occlusion': -140,
        '_ao': -120,
        'normal': -160,
        'roughness': -160,
        'metallic': -160,
        'metalness': -160,
        'opacity': -150,
        'alpha': -120,
        'height': -140,
        'displace': -140,
        'emission': -100,
    }

    for token, value in positive_tokens.items():
        if token in text:
            score += value
    for token, value in negative_tokens.items():
        if token in text:
            score += value
    return score

#-------------------------------------------------------------------------------------------------------------------------------
def material_diffuse_image(mat):
    if not mat or not mat.use_nodes or not mat.node_tree:
        return None

    mat_wrap = material_wrap(mat)
    direct_texture = getattr(mat_wrap, "base_color_texture", None) if mat_wrap else None
    direct_image = getattr(direct_texture, "image", None) if direct_texture else None
    if direct_image:
        return direct_image

    principled = material_principled_node(mat)
    base_color = _node_input(principled, 'Base Color', 'Base Colour')
    candidates = [
        (node, distance) for node, distance in _upstream_nodes(base_color)
        if node.bl_idname == 'ShaderNodeTexImage' and getattr(node, "image", None)
    ]

    if not candidates:
        candidates = [
            (node, 100) for node in mat.node_tree.nodes
            if node.bl_idname == 'ShaderNodeTexImage' and getattr(node, "image", None)
        ]

    if not candidates:
        return None

    ranked = sorted(
        candidates,
        key=lambda item: (_diffuse_image_score(item[0], item[1]), -item[1], item[0].name),
        reverse=True,
    )
    best_node, best_distance = ranked[0]
    best_score = _diffuse_image_score(best_node, best_distance)
    if best_distance >= 100 and len(ranked) > 1 and best_score <= 20:
        return None
    return best_node.image

#-------------------------------------------------------------------------------------------------------------------------------
def material_opacity_image(mat):
    """Return the image which supplies the material's alpha/opacity input."""
    if not mat or not mat.use_nodes or not mat.node_tree:
        return None

    principled = material_principled_node(mat)
    alpha = _node_input(principled, 'Alpha')
    candidates = [
        (node, distance) for node, distance in _upstream_nodes(alpha)
        if node.bl_idname == 'ShaderNodeTexImage' and getattr(node, "image", None)
    ]
    if not candidates:
        return None

    # Prefer the nearest image.  Names containing alpha/opacity break ties for
    # node groups where several images feed a small alpha-processing chain.
    def opacity_rank(item):
        node, distance = item
        image = node.image
        text = ' '.join(filter(None, (
            node.name,
            node.label,
            getattr(image, "name", None),
            getattr(image, "filepath", None),
        ))).casefold()
        semantic_score = int('alpha' in text) + int('opacity' in text)
        return (-distance, semantic_score, node.name)

    return max(candidates, key=opacity_rank)[0].image

#-------------------------------------------------------------------------------------------------------------------------------
def material_has_transparency(mat):
    if not mat:
        return False
    if mat.diffuse_color[3] < 0.999:
        return True
    if not mat.use_nodes or not mat.node_tree:
        return False

    principled = material_principled_node(mat)
    alpha = _node_input(principled, 'Alpha')
    if alpha:
        if alpha.is_linked or float(alpha.default_value) < 0.999:
            return True

    return any(
        node.bl_idname == 'ShaderNodeBsdfTransparent'
        for node, _distance in material_surface_nodes(mat)
    )

#-------------------------------------------------------------------------------------------------------------------------------
def material_alpha_value(mat):
    if not mat:
        return 1.0

    diffuse_alpha = float(mat.diffuse_color[3])
    principled = material_principled_node(mat)
    alpha = _node_input(principled, 'Alpha')
    if alpha and not alpha.is_linked:
        node_alpha = float(alpha.default_value)
        # Blender 3.6 and 5.x expose different synchronization behavior between
        # Material.diffuse_color and the Principled alpha socket. Preserve an
        # explicitly translucent material color, otherwise use the node value.
        if diffuse_alpha < 0.999 or node_alpha >= 0.999:
            return diffuse_alpha
        return node_alpha

    return diffuse_alpha

#-------------------------------------------------------------------------------------------------------------------------------
def material_texture_path(mat):
    image = material_diffuse_image(mat)
    return bpy.path.abspath(image.filepath) if image else None

#-------------------------------------------------------------------------------------------------------------------------------
def export_image_texture_path(image, export_filepath=None, extract_packed=False, warning=None):
    if not image:
        return None

    source_path = bpy.path.abspath(image.filepath) if image.filepath else ''
    if not extract_packed or not image.packed_file or not export_filepath:
        return source_path or None

    source_name = image.name or (Path(source_path).name if source_path else 'texture')
    safe_name = re.sub(r'[<>:"/\\|?*]+', '_', source_name).strip('. ') or 'texture.png'
    known_extensions = {'.bmp', '.dds', '.gif', '.jpg', '.jpeg', '.png', '.tga', '.tif', '.tiff', '.webp'}
    if Path(safe_name).suffix.lower() not in known_extensions:
        format_extension = {
            'BMP': '.bmp', 'IRIS': '.rgb', 'JPEG': '.jpg', 'JPEG2000': '.jp2',
            'PNG': '.png', 'TARGA': '.tga', 'TARGA_RAW': '.tga', 'TIFF': '.tif',
            'WEBP': '.webp',
        }.get(getattr(image, 'file_format', ''), Path(source_path).suffix or '.png')
        safe_name += format_extension

    output_dir = Path(export_filepath).resolve().parent / 'textures'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / safe_name

    try:
        output_path.write_bytes(image.packed_file.data)
        return str(output_path)
    except (OSError, RuntimeError) as exc:
        message = f'Could not extract packed image {image.name}: {exc}'
        if warning:
            warning(message)
        else:
            print(f'WARNING: {message}')
        return source_path or None

#-------------------------------------------------------------------------------------------------------------------------------
def export_material_texture_path(mat, export_filepath=None, extract_packed=False, warning=None):
    return export_image_texture_path(
        material_diffuse_image(mat),
        export_filepath,
        extract_packed,
        warning,
    )

#-------------------------------------------------------------------------------------------------------------------------------
def material_has_texture(mat):
    return bool(material_texture_path(mat))

#-------------------------------------------------------------------------------------------------------------------------------
def adjust_rgb(r, g, b, a, brightness_scale = 10):
    r = min(max((r * brightness_scale), 0), 255)
    g = min(max((g * brightness_scale), 0), 255)
    b = min(max((b * brightness_scale), 0), 255)
    return r, g, b, a

#-------------------------------------------------------------------------------------------------------------------------------
def create_euroland_matrix(obj_matrix, obj_type):
    
    if obj_type == 'CAMERA':
        def convert_axis(vector):
            return Matrix(((1, 0, 0), (0, 0, 1), (0, 1, 0))) @ vector

        obj_rot = obj_matrix.to_3x3().normalized()
        right = convert_axis(obj_rot.col[0]).normalized()
        up = convert_axis(obj_rot.col[1]).normalized()
        forward = right.cross(up).normalized()
        position = MESH_GLOBAL_MATRIX @ obj_matrix.translation

        euroland_matrix = Matrix.Identity(4)
        euroland_matrix[0].x = right.x
        euroland_matrix[0].y = right.y
        euroland_matrix[0].z = right.z
        euroland_matrix[1].x = up.x
        euroland_matrix[1].y = up.y
        euroland_matrix[1].z = up.z
        euroland_matrix[2].x = forward.x
        euroland_matrix[2].y = forward.y
        euroland_matrix[2].z = forward.z
        euroland_matrix[0][3] = position.x
        euroland_matrix[1][3] = position.y
        euroland_matrix[2][3] = position.z

        euroland_euler = euroland_matrix.to_euler('YXZ')
    else: 
        matrix_scale = Matrix.Diagonal(obj_matrix.to_scale()).to_4x4()
        transformed_matrix = (ROT_GLOBAL_MATRIX @ obj_matrix).normalized()
        transformed_matrix = transformed_matrix @ matrix_scale
        transformed_pos = MESH_GLOBAL_MATRIX @ transformed_matrix.translation

        # 3ds Max/ESE stores transform axes as row vectors, whereas Blender uses
        # column-vector transforms.  Mesh data has historically used the legacy
        # layout below, but biped bones must be transposed after the Blender -> ESE
        # axis conversion or EuroLand interprets every rotation as its inverse.
        if obj_type == 'BONE':
            transformed_matrix = transformed_matrix.transposed()

        # Crear una matriz 4x4 vacía (matriz identidad como base)
        euroland_matrix = Matrix.Identity(4)

        # Rellenar la matriz con los datos en el orden especificado
        for i, indices in enumerate([(0, 0), (2, 0), (1, 0)]):  # Fila X, Y, Z
            euroland_matrix[i].x = transformed_matrix[indices[0]].x
            euroland_matrix[i].y = transformed_matrix[indices[0]].z
            euroland_matrix[i].z = transformed_matrix[indices[0]].y

        # Agregar la posición/translation a la matriz
        euroland_matrix[0][3] = transformed_pos.x  # Posición X
        euroland_matrix[1][3] = transformed_pos.y  # Posición Y
        euroland_matrix[2][3] = transformed_pos.z  # Posición Z  
        
        #Euler stufff
        euroland_euler = obj_matrix.to_euler('ZXY')
    #Pack data
    matrix_data = {
        "eland_matrix": euroland_matrix,
        "eland_euler": euroland_euler
    }

    return matrix_data
