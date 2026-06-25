import bpy
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
def color_layers(mesh):
    if hasattr(mesh, "color_attributes") and mesh.color_attributes:
        return [
            attr for attr in mesh.color_attributes
            if attr.domain == 'CORNER' and attr.data_type in {'BYTE_COLOR', 'FLOAT_COLOR'}
        ]

    return list(mesh.vertex_colors)

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
def material_texture_path(mat):
    mat_wrap = material_wrap(mat)
    if not mat_wrap:
        return None

    tex_wrap = getattr(mat_wrap, "base_color_texture", None)
    image = tex_wrap.image if tex_wrap else None
    return bpy.path.abspath(image.filepath) if image else None

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
