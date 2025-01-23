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
from math import degrees
from mathutils import Matrix
from datetime import datetime
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

#-------------------------------------------------------------------------------------------------------------------------------
EXPORT_GLOBAL_MATRIX = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0))).to_4x4()
ESE_VERSION = '1.00'
EXPORT_TRI = True
EXPORT_NORMALS = True
EXPORT_UV=True
EXPORT_VERTEX_COLORS = True
EXPORT_APPLY_MODIFIERS=True

#SET BY USER
EXPORT_MESH = True
EXPORT_CAMERAS = True
EXPORT_LIGHTS = True
EXPORT_ANIMATIONS = True
DECIMAL_PRECISION = 6
TRANSFORM_TO_CENTER = True
df = f'%.{DECIMAL_PRECISION}f'
dcf = f'{{:>{DECIMAL_PRECISION}f}}'

#Global variables
FRAMES_COUNT = 0

#-------------------------------------------------------------------------------------------------------------------------------
def tri_edge_is_from_ngon(polygon, tri_loop_indices, tri_idx, mesh_loops):
    loop_start = polygon.loop_start
    loop_end = loop_start + polygon.loop_total

    current_loop_idx = tri_loop_indices[tri_idx]
    next_loop_idx = tri_loop_indices[(tri_idx + 1) % len(tri_loop_indices)]

    return next_loop_idx not in range(loop_start, loop_end) or current_loop_idx not in range(loop_start, loop_end)

#-------------------------------------------------------------------------------------------------------------------------------
def get_tabs(level):
    return '\t' * level

#-------------------------------------------------------------------------------------------------------------------------------
def mesh_triangulate(me):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()

#-------------------------------------------------------------------------------------------------------------------------------
def adjust_rgb(r, g, b, a):
    brightness_scale = 10
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
def write_scene_data(out, scene):
    global FRAMES_COUNT

    #Get scene data
    first_frame = scene.frame_start
    last_frame = scene.frame_end
    frame_rate = scene.render.fps
    FRAMES_COUNT = last_frame - first_frame + 1

    #tick_frequency = 4800 #Matches original examples
    #ticks_per_frame = tick_frequency // frame_rate
    ticks_per_frame = 1

    world_amb = scene.world.color if scene.world else (0.8, 0.8, 0.8)

    #Print scene data
    out.write("*SCENE {\n")
    out.write('\t*SCENE_FILENAME "%s"\n' % (bpy.data.filepath))
    out.write('\t*SCENE_FIRSTFRAME %s\n' % first_frame)
    out.write('\t*SCENE_LASTFRAME %s\n' % last_frame)
    out.write('\t*SCENE_FRAMESPEED %s\n' % frame_rate)
    out.write('\t*SCENE_TICKSPERFRAME %s\n' % ticks_per_frame)
    out.write(f'\t*SCENE_BACKGROUND_STATIC {df} {df} {df}\n' % (world_amb[0], world_amb[1], world_amb[2]))
    out.write(f'\t*SCENE_AMBIENT_STATIC {df} {df} {df}\n' % (world_amb[0], world_amb[1], world_amb[2]))
    out.write("}\n\n")
    
#-------------------------------------------------------------------------------------------------------------------------------
def write_material_data(out, mat, tab_level, base_material):

    tab = get_tabs(tab_level)
    out.write(f'{tab}*MATERIAL_NAME "%s"\n' % mat.name)
    out.write(f'{tab}*MATERIAL_CLASS "Standard"\n')

    # Envolver material para usar PrincipledBSDFWrapper
    mat_wrap = PrincipledBSDFWrapper(mat) if mat.use_nodes else None
        
    if mat_wrap:
        use_mirror = mat_wrap.metallic != 0.0
        use_transparency = mat_wrap.alpha != 1.0

        # The Ka statement specifies the ambient reflectivity using RGB values.
        if use_mirror:
            out.write(f'{tab}*MATERIAL_AMBIENT {df} {df} {df}\n' % (mat_wrap.metallic, mat_wrap.metallic, mat_wrap.metallic))
        else:
            out.write(f'{tab}*MATERIAL_AMBIENT {df} {df} {df}\n' % (1.0, 1.0, 1.0))
            
        # The Kd statement specifies the diffuse reflectivity using RGB values.
        out.write(f'{tab}*MATERIAL_DIFFUSE {df} {df} {df}\n' % mat_wrap.base_color[:3]) # Diffuse
        
        # XXX TODO Find a way to handle tint and diffuse color, in a consistent way with import...
        out.write(f'{tab}*MATERIAL_SPECULAR {df} {df} {df}\n' % (mat_wrap.specular, mat_wrap.specular, mat_wrap.specular))  # Specular

        shine = 1.0 - mat_wrap.roughness
        out.write(f'{tab}*MATERIAL_SHINE %.1f\n' % shine)
        
        transparency = 1.0 - mat_wrap.alpha
        out.write(f'{tab}*MATERIAL_TRANSPARENCY %.1f\n' % transparency)
                
        # Self-illumination (emission) of the material
        out.write(f'{tab}*MATERIAL_SELFILLUM %.1f\n' % mat_wrap.emission_strength)

        if base_material == False:
            #### And now, the image textures...
            image_map = {
                    "map_Kd": "base_color_texture",
                    #"map_Ka": None,  # ambient...
                    #"map_Ks": "specular_texture",
                    #"map_Ns": "roughness_texture",
                    #"map_d": "alpha_texture",
                    #"map_Tr": None,  # transmission roughness?
                    #"map_Bump": "normalmap_texture",
                    #"disp": None,  # displacement...
                    #"refl": "metallic_texture",
                    #"map_Ke": None  # emission...
                    }

            for key, mat_wrap_key in sorted(image_map.items()):
                if mat_wrap_key is None:
                    continue
                tex_wrap = getattr(mat_wrap, mat_wrap_key, None)
                if tex_wrap is None:
                    continue
                image = tex_wrap.image
                if image is None:
                    continue
                out.write(f'{tab}*MAP_DIFFUSE {{\n')
                out.write(f'{tab}\t*MATERIAL_NAME "%s"\n' % image.name)
                out.write(f'{tab}\t*MAP_CLASS "Bitmap"\n')
                if use_mirror:
                    out.write(f'{tab}\t*MAP_AMOUNT %.1f\n' % (mat_wrap.metallic))
                else:
                    out.write(f'{tab}\t*MAP_AMOUNT %.1f\n' % (1))                    
                texture_path = bpy.path.abspath(image.filepath)
                out.write(f'{tab}\t*BITMAP "%s"\n' % (texture_path))                                                
                out.write(f'{tab}}}\n')

#-------------------------------------------------------------------------------------------------------------------------------
def write_scene_materials(out):
    #Get scene materials, the key is the object name, the value is the mesh materials list
    mesh_materials = {}
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            material_list = []
            for mat_slot in obj.material_slots:
                if mat_slot.material:
                    material_list.append(mat_slot.material)
            mesh_materials[obj.name] = material_list

    # Print materials list                                        
    out.write("*MATERIAL_LIST {\n")
    out.write("\t*MATERIAL_COUNT %d\n" % len(mesh_materials))
    for index, (mesh_name, materials) in enumerate(mesh_materials.items()):
        out.write("\t*MATERIAL %d {\n" % index)
        
        materials_count = len(materials)
        if materials_count == 1:
            write_material_data(out, materials[0], 2, False)
        else:
            write_material_data(out, materials[0], 2, True)
            out.write("\t\t*MATERIAL_MULTIMAT\n")
            out.write("\t\t*NUMSUBMTLS %d\n" % materials_count)
            for submat_index, mat in enumerate(materials):
                out.write("\t\t*SUBMATERIAL %d {\n" % submat_index)
                write_material_data(out, mat, 3, False)
                out.write("\t\t}\n")
        out.write('\t}\n')            
    out.write('}\n')

    return mesh_materials

#-------------------------------------------------------------------------------------------------------------------------------
def write_node_pivot_node(out, isPivot, obj_matrix_data):
    if isPivot:
        out.write('\t*NODE_PIVOT_TM {\n')
    else:
        out.write('\t*NODE_TM {\n')
    out.write('\t\t*NODE_NAME "%s"\n' % (obj_matrix_data["name"]))
    out.write('\t\t*INHERIT_POS %d %d %d\n' % (0, 0, 0))
    out.write('\t\t*INHERIT_ROT %d %d %d\n' % (0, 0, 0))
    out.write('\t\t*INHERIT_SCL %d %d %d\n' % (0, 0, 0))
    
    matrix_data = obj_matrix_data["matrix_transformed"]
    RotationMatrix = matrix_data.transposed()
    if not isPivot:
        RotationMatrix = Matrix.Identity(4)
        
    out.write(f'\t\t*TM_ROW0 {df} {df} {df}\n' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
    out.write(f'\t\t*TM_ROW1 {df} {df} {df}\n' % (RotationMatrix[1].x, RotationMatrix[1].y, RotationMatrix[1].z))
    out.write(f'\t\t*TM_ROW2 {df} {df} {df}\n' % (RotationMatrix[2].x, RotationMatrix[2].y, RotationMatrix[2].z))
    
    #Transform position
    transformed_position = EXPORT_GLOBAL_MATRIX @ obj_matrix_data["location"]
    out.write(f'\t\t*TM_ROW3 {df} {df} {df}\n' % (transformed_position.x,transformed_position.y,transformed_position.z))
    out.write(f'\t\t*TM_POS {df} {df} {df}\n' % (transformed_position.x,transformed_position.y,transformed_position.z))
    
    #Transform rotation
    transformed_rotation = RotationMatrix.to_euler('XYZ')
    out.write(f'\t\t*TM_ROTANGLE {df} {df} {df}\n' % (transformed_rotation.x, transformed_rotation.y, transformed_rotation.z))

    #Print scale
    scale = EXPORT_GLOBAL_MATRIX @ obj_matrix_data["scale"]
    out.write(f'\t\t*TM_SCALE {df} {df} {df}\n' % (scale.x, scale.y, scale.z))
    out.write(f'\t\t*TM_SCALEANGLE {df} {df} {df}\n' % (0, 0, 0))
    out.write('\t}\n')

#-------------------------------------------------------------------------------------------------------------------------------
def write_animation_node(out, ob, ob_mat, ob_for_convert):
    out.write('\t*TM_ANIMATION {\n')
    out.write('\t\t*TM_ANIMATION "%s"\n' % ob_for_convert.name)
    previous_matrix_data = None
    
    out.write('\t\t*TM_ANIM_FRAMES {\n')
    for f in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
        bpy.context.scene.frame_set(f)
      
        # Apply transformation matrix to light object
        if ob.type == 'CAMERA':
            matrix_transformed = EXPORT_GLOBAL_MATRIX @ ob_mat
        else:
            matrix_transformed = EXPORT_GLOBAL_MATRIX @ ob_mat
            matrix_transformed.transposed()

        obj_matrix_data = {
            "name" : ob.name,
            "matrix_transformed": matrix_transformed.copy(),
            "location": ob.location.copy(),
            "rotation": ob.matrix_world.copy()
        }

        #Print only the unique keyframes
        if previous_matrix_data is None or \
        (obj_matrix_data["matrix_transformed"] != previous_matrix_data["matrix_transformed"] or
            obj_matrix_data["location"] != previous_matrix_data["location"]):
            
            # Get data
            matrix_data = obj_matrix_data["matrix_transformed"]
            RotationMatrix = matrix_data.transposed()          

            #Print rotation
            out.write('\t\t\t*TM_FRAME  {:<5d}'.format(f))
            if ob.type == 'CAMERA':
                out.write(f' {df} {df} {df}' % (RotationMatrix[0].x,      RotationMatrix[0].y * -1, RotationMatrix[0].z     ))
                out.write(f' {df} {df} {df}' % (RotationMatrix[1].x,      RotationMatrix[1].y,      RotationMatrix[1].z     ))
                out.write(f' {df} {df} {df}' % (RotationMatrix[2].x * -1, RotationMatrix[2].y * -1, RotationMatrix[2].z * -1))
            
            else:
                RotationMatrix = EXPORT_GLOBAL_MATRIX @ obj_matrix_data["rotation"]
                RotationMatrix = RotationMatrix.transposed()
                out.write(f' {df} {df} {df}' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
                out.write(f' {df} {df} {df}' % (RotationMatrix[1].x, RotationMatrix[1].y, RotationMatrix[1].z))
                out.write(f' {df} {df} {df}' % (RotationMatrix[2].x, RotationMatrix[2].y, RotationMatrix[2].z))

            #Transform position
            transformed_position = EXPORT_GLOBAL_MATRIX @ obj_matrix_data["location"]
            out.write(f' {df} {df} {df}\n' % (transformed_position.x, transformed_position.y, transformed_position.z))

            # Actualizamos los datos anteriores con los datos actuales
            previous_matrix_data = obj_matrix_data
    out.write('\t\t}\n')
    out.write('\t}\n')

#-------------------------------------------------------------------------------------------------------------------------------
def write_mesh_data(out, scene, depsgraph, scene_materials):
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

            matrix_transformed = EXPORT_GLOBAL_MATRIX @ ob_mat
            me.transform(matrix_transformed)
            obj_matrix_data = {
                "name" : me.name,
                "matrix_transformed": matrix_transformed.copy(),
                "location": ob.location.copy(),
                "scale": ob.scale.copy()
            }

            # If negative scaling, we have to invert the normals...
            if ob_mat.determinant() < 0.0:
                me.flip_normals()

            if EXPORT_UV:
                faceuv = len(me.uv_layers) > 0
                if faceuv:
                    uv_layer = me.uv_layers.active.data[:]
            else:
                faceuv = False

            if EXPORT_VERTEX_COLORS:
                facecolors = len(me.vertex_colors) > 0
                if facecolors:
                    color_layer = me.vertex_colors.active.data[:]
            else:
                facecolors = False

            me_verts = me.vertices[:]

            # Make our own list so it can be sorted to reduce context switching
            face_index_pairs = [(face, index) for index, face in enumerate(me.polygons)]

            if not (len(face_index_pairs) + len(me.vertices)):  # Make sure there is something to write
                # clean up
                bpy.data.meshes.remove(me)
                continue  # dont bother with this mesh.

            loops = me.loops
            materials = me.materials[:]
            material_names = [m.name if m else None for m in materials]

            # UV
            uv_unique_count = 0
            uv_list = []
            if faceuv:
                # in case removing some of these dont get defined.
                uv = f_index = uv_index = uv_key = uv_val = uv_ls = None

                uv_face_mapping = [None] * len(face_index_pairs)

                uv_dict = {}
                uv_get = uv_dict.get
                for f, f_index in face_index_pairs:
                    uv_ls = uv_face_mapping[f_index] = []
                    for uv_index, l_index in enumerate(f.loop_indices):
                        uv = uv_layer[l_index].uv
                        # include the vertex index in the key so we don't share UV's between vertices,
                        # allowed by the OBJ spec but can cause issues for other importers, see: T47010.

                        # this works too, shared UV's for all verts
                        #~ uv_key = veckey2d(uv)
                        uv_key = loops[l_index].vertex_index, veckey2d(uv)

                        uv_val = uv_get(uv_key)
                        if uv_val is None:
                            uv_val = uv_dict[uv_key] = uv_unique_count
                            uv_list.append((uv[0], uv[1]))
                            uv_unique_count += 1
                        uv_ls.append(uv_val)

                del uv_dict, uv, f_index, uv_index, uv_ls, uv_get, uv_key, uv_val
                # Only need uv_unique_count and uv_face_mapping

            # Vertex Colors
            vcolor_unique_count = 0
            vcolor_list = []
            if facecolors:
                # Crear el mapeo de colores de vértices
                vcolor_face_mapping = [None] * len(face_index_pairs)
                
                vcolor_dict = {}
                vcolor_get = vcolor_dict.get
                for f, f_index in face_index_pairs:
                    color_ls = vcolor_face_mapping[f_index] = []
                    for col_index, l_index in enumerate(f.loop_indices):
                        v_color = color_layer[l_index].color

                        # Usamos un diccionario para evitar colores duplicados
                        color_key = (v_color[0], v_color[1], v_color[2], v_color[3])  # Clave por el color RGBA
                        
                        color_val = vcolor_get(color_key)
                        if color_val is None:
                            color_val = vcolor_dict[color_key] = vcolor_unique_count
                            vcolor_list.append(v_color)  # Añadir el nuevo color a la lista
                            vcolor_unique_count +=1
                        color_ls.append(color_val)

                # Limpieza de variables temporales
                del vcolor_dict, v_color, f_index, col_index, color_ls, vcolor_get, color_key, color_val

            # Añadir por defecto el color de la escena para que no se vea completamente negro en EuroLand
            if not vcolor_list:
                if scene.world:
                    ambient_color = (scene.world.color.r, scene.world.color.g, scene.world.color.b, 1.0)  # Añadir alpha = 1.0
                else:
                    ambient_color = (0.8, 0.8, 0.8, 1.0)
                vcolor_list.append(adjust_rgb(ambient_color[0], ambient_color[1], ambient_color[2], ambient_color[3]))
                vcolor_unique_count +=1

            # NORMAL, Smooth/Non smoothed.
            if EXPORT_NORMALS:
                normal_list = []
                no_unique_count = 0
                no_key = no_val = None
                normals_to_idx = {}
                no_get = normals_to_idx.get
                loops_to_normals = [0] * len(loops)
                for f, f_index in face_index_pairs:
                    for l_idx in f.loop_indices:
                        no_key = veckey3d(loops[l_idx].normal)
                        no_val = no_get(no_key)
                        if no_val is None:
                            no_val = normals_to_idx[no_key] = no_unique_count
                            normal_list.append(no_key)
                            no_unique_count += 1
                        loops_to_normals[l_idx] = no_val
                del normals_to_idx, no_get, no_key, no_val

            # Start printing
            out.write("*GEOMOBJECT {\n")
            out.write('\t*NODE_NAME "%s"\n' % me.name)
            write_node_pivot_node(out, False, obj_matrix_data)
            write_node_pivot_node(out, True, obj_matrix_data)

            #Mesh data
            out.write('\t*MESH {\n')
            out.write('\t\t*TIMEVALUE %d\n' % scene.frame_current)
            out.write('\t\t*MESH_NUMVERTEX %u\n' % len(me_verts))
            out.write('\t\t*MESH_NUMFACES %u\n' % len(me.polygons))

            #Vertex
            out.write('\t\t*MESH_VERTEX_LIST {\n')
            if TRANSFORM_TO_CENTER:
                # Calcular el desplazamiento necesario para mover el objeto al origen (0,0,0)
                object_location = matrix_transformed.to_translation()
                inverse_translation_matrix = Matrix.Translation(-object_location)

                for vindex, v in enumerate(me_verts):
                    # Desplazar los vértices para que el objeto esté en el origen (0, 0, 0), pero con la rotación intacta
                    new_co = inverse_translation_matrix @ v.co
                    out.write(f'\t\t\t*MESH_VERTEX  {{:>5d}}   {dcf}    {dcf}    {dcf}\n'.format(vindex, new_co.x, new_co.y, new_co.z))
            else:
                for vindex, v in enumerate(me_verts):
                    out.write(f'\t\t\t*MESH_VERTEX  {{:>5d}}   {dcf}    {dcf}    {dcf}\n'.format(vindex, v.co.x, v.co.y, v.co.z))
            out.write('\t\t}\n')    
            
            #Faces
            out.write('\t\t*MESH_FACE_LIST {\n')
            for f, f_index in face_index_pairs:               
                
                f_v = [(vi, me_verts[v_idx], l_idx)
                        for vi, (v_idx, l_idx) in enumerate(zip(f.vertices, f.loop_indices))]
                
                vertex_indices = [v.index for vi, v, li in (f_v)]

                #Get material name from mesh materials list
                f_mat = min(f.material_index, len(materials) - 1)
                material_name = material_names[f_mat] 

                #Find index in the global scene list (*MATERIALS_LIST)
                mesh_materials = scene_materials[ob_main.name]
                mesh_materials_names = [m.name if m else None for m in mesh_materials]
                mesh_material_index = mesh_materials_names.index(material_name)
                
                # swy: the calc_loop_triangles() doesn't modify the original faces, and instead does temporary ad-hoc triangulation
                #      returning us a list of three loops per "virtual triangle" that only exists in the returned thingie
                #      i.e. len(tri_loop) should always be 3, but internally, for each loop .face we're a member of
                #           still has 4 vertices and the four (different) loops of an n-gon, and .link_loop_next
                #           points to the original model's loop chain; the loops of our triangle aren't really linked
                edges_from_ngon = []  # Almacenar el resultado para cada borde del triángulo
                for tri_idx in range(len(vertex_indices)):
                    is_from_ngon = tri_edge_is_from_ngon(f, vertex_indices, tri_idx, loops)
                    edges_from_ngon.append(1 if is_from_ngon else 0)

                #Face Vertex Index
                out.write('\t\t\t*MESH_FACE    {:>3d}:    A: {:>6d} B: {:>6d} C: {:>6d}'.format(f_index, vertex_indices[0], vertex_indices[1], vertex_indices[2]))
                out.write('    AB: {:<6d} BC: {:<6d} CA: {:<6d}  *MESH_SMOOTHING   *MESH_MTLID {:<3d}\n'.format(edges_from_ngon[0], edges_from_ngon[1], edges_from_ngon[2], mesh_material_index))
            out.write('\t\t}\n')

            #UVs
            if faceuv:
                out.write('\t\t*MESH_NUMTVERTEX %d\n' % uv_unique_count)
                out.write('\t\t*MESH_TVERTLIST {\n')
                for idx, TextUV in enumerate(uv_list):
                    out.write(f'\t\t\t*MESH_TVERT {{:<3d}}  {dcf}   {dcf}   {dcf}\n'.format(idx, TextUV[0], TextUV[1], 0))
                out.write('\t\t}\n') 
                
                #UVs mapping
                out.write('\t\t*MESH_NUMTVFACES %d\n' % len(me.polygons))
                out.write('\t\t*MESH_TFACELIST {\n')
                for f, f_index in face_index_pairs:               
                    
                    f_v = [(vi, me_verts[v_idx], l_idx)
                            for vi, (v_idx, l_idx) in enumerate(zip(f.vertices, f.loop_indices))]

                    out.write('\t\t\t*MESH_TFACE {:<3d}  '.format(f_index))
                    for vi, v_idx, l_idx in (f_v):
                        uv_idx = uv_face_mapping[f_index][vi] if uv_face_mapping[f_index] else 0
                        out.write("%d   " % (uv_idx))
                    out.write("\n")
                out.write('\t\t}\n')

            # Vertex Colors
            out.write('\t\t*MESH_NUMCVERTEX %d\n' % vcolor_unique_count)
            out.write('\t\t*MESH_CVERTLIST {\n')
            for idx, col in enumerate(vcolor_list):
                out.write(f'\t\t\t*MESH_VERTCOL {{:<3d}}  {dcf}   {dcf}   {dcf}   {dcf}\n'.format(idx, col[0], col[1], col[2], col[3]))
            out.write('\t\t}\n') 
            
            # Vertex Colors mapping
            out.write('\t\t*MESH_NUMCVFACES %d\n' % len(me.polygons))
            out.write('\t\t*MESH_CFACELIST {\n')
            for f, f_index in face_index_pairs:               
                
                f_v = [(vi, me_verts[v_idx], l_idx)
                        for vi, (v_idx, l_idx) in enumerate(zip(f.vertices, f.loop_indices))]

                out.write('\t\t\t*MESH_CFACE {:<3d}  '.format(f_index))
                if vcolor_list and facecolors:
                    for vi, v_idx, l_idx in f_v:
                        color_idx = vcolor_face_mapping[f_index][vi] if vcolor_face_mapping[f_index] else 0
                        out.write("%d   " % (color_idx))
                else:
                    for _ in range(3):
                        out.write("%d   " % (0))
                out.write("\n")
            out.write('\t\t}\n')

            #Normals
            if EXPORT_NORMALS:
                out.write('\t\t*MESH_NORMALS {\n')
                for f, f_index in face_index_pairs:  
                    # Imprimir la normal de la cara
                    face_normal = loops_to_normals[f_index]
                    out.write(f'\t\t\t*MESH_FACENORMAL {{:<3d}}  {dcf}   {dcf}   {dcf}\n'.format(f_index, normal_list[face_normal][0], normal_list[face_normal][1], normal_list[face_normal][2]))

                    # Imprimir las normales de los vértices correspondientes
                    f_v = [(vi, me_verts[v_idx], l_idx)
                            for vi, (v_idx, l_idx) in enumerate(zip(f.vertices, f.loop_indices))]
                    
                    vertex_indices = [v.index for vi, v, li in (f_v)]
                    for tri_idx in range(len(vertex_indices)):
                        out.write(f'\t\t\t\t*MESH_VERTEXNORMAL {{:<3d}}  {dcf}   {dcf}   {dcf}\n'.format(vertex_indices[tri_idx], normal_list[face_normal][0], normal_list[face_normal][1], normal_list[face_normal][2]))
                out.write('\t\t}\n')

            #Close Mesh block
            out.write('\t}\n')

            #Print animations
            if FRAMES_COUNT > 0 and EXPORT_ANIMATIONS:
                write_animation_node(out, ob, ob_mat, ob_for_convert)

            out.write(f'\t*WIREFRAME_COLOR {df} {df} {df}\n' % (ob.color[0], ob.color[1], ob.color[2]))
            out.write('\t*MATERIAL_REF %d\n' % list(scene_materials.keys()).index(ob.name))
            out.write("}\n")

            # clean up
            ob_for_convert.to_mesh_clear()

#-------------------------------------------------------------------------------------------------------------------------------
def write_light_settings(out, light_object, current_frame, tab_level = 1):
    tab = get_tabs(tab_level)

    out.write(f'{tab}*LIGHT_SETTINGS {{\n')
    out.write(f'{tab}\t*TIMEVALUE %u\n' % current_frame)
    out.write(f'{tab}\t*COLOR {df} {df} {df}\n' % (light_object.color.r, light_object.color.g, light_object.color.b))
    out.write(f'{tab}\t*FAR_ATTEN {df} {df}\n' % (light_object.shadow_soft_size, light_object.cutoff_distance))
    if (light_object.type == 'SUN'):
        out.write(f'{tab}\t*HOTSPOT %u\n' % degrees(light_object.angle))
    else:
        out.write(f'{tab}\t*HOTSPOT %u\n' % 0)
    out.write(f'{tab}}}\n')

#-------------------------------------------------------------------------------------------------------------------------------
def write_light_data(out, scene, depsgraph):
    global FRAMES_COUNT

    for ob_main in scene.objects:
        # Check if the object is a light source
        if ob_main.type != 'LIGHT':
            continue

        # Handle object instances (duplicated lights)
        obs = [(ob_main, ob_main.matrix_world)]
        if ob_main.is_instancer:
            obs += [(dup.instance_object.original, dup.matrix_world.copy())
                    for dup in depsgraph.object_instances
                    if dup.parent and dup.parent.original == ob_main]
            # ~ print(ob_main.name, 'has', len(obs) - 1, 'dupli children')

        for ob, ob_mat in obs:
            ob_for_convert = ob.evaluated_get(depsgraph) if EXPORT_APPLY_MODIFIERS else ob.original

            try:
                # Extract the light data
                light_data = ob_for_convert.data
            except AttributeError:
                light_data = None

            if light_data is None:
                continue
            
            # Apply transformation matrix to light object
            matrix_transformed = EXPORT_GLOBAL_MATRIX @ ob_mat
            obj_matrix_data = {
                "name" : ob.name,
                "matrix_transformed": matrix_transformed.copy(),
                "location": ob.location.copy(),
                "scale": ob.scale.copy()
            }

            # If negative scaling, we need to invert the direction of light if it's directional
            if ob_mat.determinant() < 0.0 and light_data.type == 'SUN':
                # Invert the direction of a sun light (directional light)
                obj_matrix_data["direction"] = (-ob_for_convert.matrix_world.to_3x3() @ light_data.direction).normalized()

            # Print ligth data                
            out.write("*LIGHTOBJECT {\n")
            out.write('\t*NODE_NAME "%s"\n' % ob.name)
            out.write('\t*NODE_PARENT "%s"\n' % ob.name)
            
            type_lut = {}
            type_lut['POINT'] = 'Omni'
            type_lut['SPOT' ] = 'TargetSpot'
            type_lut['SUN'  ] = 'TargetDirect'
            type_lut['AREA' ] = 'TargetDirect' # swy: this is sort of wrong ¯\_(ツ)_/¯

            out.write('\t*LIGHT_TYPE %s\n' % type_lut[light_data.type]) #Seems that always used "Omni" lights in 3dsMax, in blender is called "Point"
            write_node_pivot_node(out, False, obj_matrix_data)

            #---------------------------------------------[Light Props]---------------------------------------------
            if (light_data.use_shadow):
                out.write('\t*LIGHT_SHADOWS %s\n' % "On") #for now
            else:
                out.write('\t*LIGHT_SHADOWS %s\n' % "Off") #for now
            out.write('\t*LIGHT_DECAY %s\n' % "InvSquare") # swy: this is the only supported mode
            out.write('\t*LIGHT_AFFECT_DIFFUSE %s\n' % "Off") #for now
            if (light_data.specular_factor > 0.001):
                out.write('\t*LIGHT_AFFECT_SPECULAR %s\n' % "On") #for now
            else:
                out.write('\t*LIGHT_AFFECT_SPECULAR %s\n' % "Off") #for now
            out.write('\t*LIGHT_AMBIENT_ONLY %s\n' % "Off") #for now

            write_light_settings(out, light_data, scene.frame_current)

            #---------------------------------------------[Light Animation]---------------------------------------------
            print(FRAMES_COUNT)
            if FRAMES_COUNT > 1 and EXPORT_ANIMATIONS:
                out.write('\t*LIGHT_ANIMATION {\n')
                previous_light_data = None

                for frame in range(scene.frame_start, scene.frame_end + 1):
                    scene.frame_set(frame)

                    # current frame data
                    try:
                        # Extract the light data
                        light_data = ob_for_convert.data
                    except AttributeError:
                        light_data = None

                    if light_data is None:
                        continue

                    if previous_light_data is None or \
                    (light_data.color != previous_light_data.color or
                        light_data.shadow_soft_size != previous_light_data.shadow_soft_size or
                        light_data.cutoff_distance != previous_light_data.cutoff_distance or
                        (light_data.type == 'SUN' and light_data.angle != previous_light_data.angle)):

                        # Si hay alguna propiedad diferente, escribimos la configuración de la luz
                        write_light_settings(out, light_data, scene.frame_current, 2)

                        # Actualizamos los datos anteriores con los datos actuales
                        previous_light_data = light_data
                out.write('\t}\n')
                write_animation_node(out, ob, ob_mat, ob_for_convert)
            out.write("}\n")

#-------------------------------------------------------------------------------------------------------------------------------
def write_camera_settings(out, camera_object, camera_data, current_frame, tab_level = 1):
    tab = get_tabs(tab_level)

    out.write(f'{tab}*CAMERA_SETTINGS {{\n')
    out.write(f'{tab}\t*TIMEVALUE %u\n' % current_frame)
    #out.write(f'{tab}\t*CAMERA_NEAR %d\n' % (camera_object.clip_start))
    #out.write(f'{tab}\t*CAMERA_FAR %d\n' % (camera_object.clip_end))
    out.write(f'{tab}\t*CAMERA_FOV {df}\n' % (camera_object.angle))
    #out.write(f'{tab}\t*CAMERA_TDIST {df}\n' % (camera_data.location.length))
    out.write(f'{tab}}}\n')
    
#-------------------------------------------------------------------------------------------------------------------------------
def write_camera_data(out, scene, depsgraph):
    global FRAMES_COUNT

    for ob_main in scene.objects:
        # Check if the object is a camera source
        if ob_main.type != 'CAMERA':
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
                camera_data = ob_for_convert.data
            except RuntimeError:
                camera_data = None

            if camera_data is None:
                continue
            
            # Apply transformation matrix to light object
            matrix_transformed = EXPORT_GLOBAL_MATRIX @ ob_mat
            obj_matrix_data = {
                "name" : ob.name,
                "matrix_transformed": matrix_transformed.copy(),
                "location": ob.location.copy(),
                "scale": ob.scale.copy()
            }
      
        # Imprime el bloque con las propiedades de la cámara
        camera_type = camera_data.type
        out.write("*CAMERAOBJECT {\n")
        out.write('\t*NODE_NAME %s\n' % ob.name)
        out.write('\t*CAMERA_TYPE %s\n' % camera_type)
        write_node_pivot_node(out, False, obj_matrix_data)
        write_camera_settings(out, camera_data, ob, scene.frame_current)

        #---------------------------------------------[Camera Animation]---------------------------------------------
        print(FRAMES_COUNT)
        if FRAMES_COUNT > 1 and EXPORT_ANIMATIONS:
            out.write('\t*CAMERA_ANIMATION {\n')
            previous_camera_data = None

            for frame in range(scene.frame_start, scene.frame_end + 1):
                scene.frame_set(frame)

                # current frame data
                try:
                    # Extract the light data
                    camera_data = ob_for_convert.data
                except AttributeError:
                    camera_data = None

                if camera_data is None:
                    continue

                if previous_camera_data is None or \
                (camera_data.clip_start != previous_camera_data.clip_start or
                    camera_data.clip_end != previous_camera_data.clip_end or
                    camera_data.angle != previous_camera_data.angle):

                    # Si hay alguna propiedad diferente, escribimos la configuración de la luz
                    write_camera_settings(out, camera_data, ob, scene.frame_current, 2)

                    # Actualizamos los datos anteriores con los datos actuales
                    previous_camera_data = camera_data
            out.write('\t}\n')
            write_animation_node(out, ob, ob_mat, ob_for_convert)
        out.write("}\n")

#-------------------------------------------------------------------------------------------------------------------------------
def export_file(filepath):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene

    # Exit edit mode before exporting, so current object states are exported properly.
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    # Set the first frame
    bpy.context.scene.frame_set(0)

    # Create text file
    with open(filepath, 'w', encoding="utf8",) as out:
        # Header data
        out.write("*3DSMAX_EUROEXPORT	300\n")
        out.write('*COMMENT "Eurocom Export Version  3.00 - %s\n' % datetime.now().strftime("%A %B %d %Y %H:%M"))
        out.write('*COMMENT "Version of Blender that output this file: %s"\n' % bpy.app.version_string)
        out.write('*COMMENT "Version of ESE Plug-in: %s"\n\n' % ESE_VERSION)

        write_scene_data(out, scene)
        
        #Mesh
        scene_materials = write_scene_materials(out)

        #scene objects data
        if EXPORT_MESH:
            write_mesh_data(out, scene, depsgraph, scene_materials)    
        if EXPORT_CAMERAS:
            write_camera_data(out, scene, depsgraph)
        if EXPORT_LIGHTS:
            write_light_data(out, scene, depsgraph)
                
    print(f"Archivo exportado con éxito: {filepath}")

#-------------------------------------------------------------------------------------------------------------------------------
filepath = bpy.path.abspath("C:\\Users\\Jordi Martinez\\Desktop\\EuroLand Files\\3D Examples\\test.ESE")  # Cambia la ruta si es necesario
export_file(filepath)