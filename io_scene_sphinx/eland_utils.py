from mathutils import Matrix, Euler

#-------------------------------------------------------------------------------------------------------------------------------
MESH_GLOBAL_MATRIX = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0))).to_4x4()
ROT_GLOBAL_MATRIX = Matrix(((1, 0, 0),(0, 1, 0),(0, 0, 1))).to_4x4()

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
def adjust_rgb(r, g, b, a, brightness_scale = 10):
    r = min(max((r * brightness_scale), 0), 255)
    g = min(max((g * brightness_scale), 0), 255)
    b = min(max((b * brightness_scale), 0), 255)
    return r, g, b, a

#-------------------------------------------------------------------------------------------------------------------------------
def veckey2d(v):
    return round(v[0], 4), round(v[1], 4)

#-------------------------------------------------------------------------------------------------------------------------------
def veckey3d(v):
    return round(v.x, 4), round(v.y, 4), round(v.z, 4)

#-------------------------------------------------------------------------------------------------------------------------------
def create_euroland_matrix(obj_matrix, obj_type):
    
    if obj_type == 'CAMERA':
        euroland_matrix = MESH_GLOBAL_MATRIX @ obj_matrix
                
        # Cameras seems that needs to invert Z axis
        for i in range(len(euroland_matrix)):
            euroland_matrix[i][2] *= -1      
            
        #Euler stuf
        rot_yxz = euroland_matrix.to_euler('YXZ')
        euroland_euler = Euler([-angle for angle in rot_yxz], 'YXZ')          
    else: 
        transformed_matrix = ROT_GLOBAL_MATRIX @ obj_matrix
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