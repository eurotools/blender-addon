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
from mathutils import Matrix, Vector, Color
from datetime import datetime
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

#-------------------------------------------------------------------------------------------------------------------------------
EXPORT_GLOBAL_MATRIX = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0))).to_4x4()
ESE_VERSION = '1.00'
EXPORT_TRI = True
EXPORT_UV=True
EXPORT_VERTEX_COLORS = True
EXPORT_APPLY_MODIFIERS=True

#SET BY USER
TRANSFORM_TO_CENTER = True
DECIMAL_PRECISION = 6
df = f'%.{DECIMAL_PRECISION}f'
dcf = f'{{:>{DECIMAL_PRECISION}f}}'

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
def write_scene_data(out, scene):
    #Get scene data
    first_frame = scene.frame_start
    last_frame = scene.frame_end
    frame_rate = scene.render.fps
    
    tick_frequency = 4800 #Matches original examples
    ticks_per_frame = tick_frequency // frame_rate
    
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
def write_node_pivot_node(out, isPivot, scene_object, scene_object_name):
    if isPivot:
        out.write('\t*NODE_PIVOT_TM {\n')
    else:
        out.write('\t*NODE_TM {\n')
    out.write('\t\t*NODE_NAME "%s"\n' % (scene_object_name))
    out.write('\t\t*INHERIT_POS %d %d %d\n' % (0, 0, 0))
    out.write('\t\t*INHERIT_ROT %d %d %d\n' % (0, 0, 0))
    out.write('\t\t*INHERIT_SCL %d %d %d\n' % (0, 0, 0))
    
    if isPivot:
        matrix_data = EXPORT_GLOBAL_MATRIX @ scene_object
        RotationMatrix = matrix_data.transposed()
    else:
        RotationMatrix = Matrix.Identity(4)
    out.write(f'\t\t*TM_ROW0 {df} {df} {df}\n' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
    out.write(f'\t\t*TM_ROW1 {df} {df} {df}\n' % (RotationMatrix[1].x, RotationMatrix[1].y, RotationMatrix[1].z))
    out.write(f'\t\t*TM_ROW2 {df} {df} {df}\n' % (RotationMatrix[2].x, RotationMatrix[2].y, RotationMatrix[2].z))
    
    #Transform position
    out.write(f'\t\t*TM_ROW3 {df} {df} {df}\n' % (RotationMatrix[0].w, RotationMatrix[1].w, RotationMatrix[2].w))
    out.write(f'\t\t*TM_POS {df} {df} {df}\n' % (RotationMatrix[0].w, RotationMatrix[1].w, RotationMatrix[2].w))
    
    #Transform rotation
    transformed_rotation = RotationMatrix.to_euler('XYZ')
    out.write(f'\t\t*TM_ROTANGLE {df} {df} {df}\n' % (transformed_rotation.x, transformed_rotation.y, transformed_rotation.z))
    out.write(f'\t\t*TM_SCALE {df} {df} {df}\n' % (1, 1, 1))
    out.write(f'\t\t*TM_SCALEANGLE {df} {df} {df}\n' % (0, 0, 0))
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


            # Start printing
            out.write("*GEOMOBJECT {\n")
            out.write('\t*NODE_NAME "%s"\n' % me.name)
            write_node_pivot_node(out, False, ob_mat.copy(), me.name)
            write_node_pivot_node(out, True, ob_mat.copy(), me.name)

            #Mesh data
            out.write('\t*MESH {\n')
            out.write('\t\t*TIMEVALUE %d\n' % 0)
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
            out.write('\t}\n')
            out.write('\t*MATERIAL_REF 0\n')
            out.write("}")

            # clean up
            ob_for_convert.to_mesh_clear()

#-------------------------------------------------------------------------------------------------------------------------------
def export_file(filepath):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene

    # Exit edit mode before exporting, so current object states are exported properly.
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    # Create text file
    with open(filepath, 'w', encoding="utf8",) as out:
        # Header data
        out.write("*3DSMAX_EUROEXPORT	300\n")
        out.write('*COMMENT "Eurocom Export Version  3.00 - %s\n' % datetime.now().strftime("%A %B %d %Y %H:%M"))
        out.write('*COMMENT "Version of Blender that output this file: %s"\n' % bpy.app.version_string)
        out.write('*COMMENT "Version of ESE Plug-in: %s"\n\n' % ESE_VERSION)

        write_scene_data(out, scene)
        scene_materials = write_scene_materials(out)
        write_mesh_data(out, scene, depsgraph, scene_materials)
                
    print(f"Archivo exportado con éxito: {filepath}")

#-------------------------------------------------------------------------------------------------------------------------------
filepath = bpy.path.abspath("C:\\Users\\Jordi Martinez\\Desktop\\EuroLand Files\\3D Examples\\test.ESE")  # Cambia la ruta si es necesario
export_file(filepath)