#  Copyright (c) 2020-2021 Swyter <swyterzone+sphinx@gmail.com>
#  SPDX-License-Identifier: Zlib

"""
Name: 'Eurocom Interchange File'
Blender: 4.3.2
Group: 'Export'
Tooltip: 'Blender EIF Exporter for EuroLand'
Authors: Swyter and Jmarti856
"""

import os
import bpy
from math import radians, degrees
from mathutils import Matrix
from datetime import datetime
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

#-------------------------------------------------------------------------------------------------------------------------------
EXPORT_GLOBAL_MATRIX = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0))).to_4x4()
EXPORT_TRI=False
EXPORT_UV=True
EXPORT_VERTEX_COLORS = True
EXPORT_APPLY_MODIFIERS=True
EIF_VERSION = '1.00'

#SET BY USER
EXPORT_GEOMNODE = True
EXPORT_PLACENODE = True
TRANSFORM_TO_CENTER = True
DECIMAL_PRECISION = 6
df = f'%.{DECIMAL_PRECISION}f'

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
    world_amb = (scene.world.color.r, scene.world.color.g, scene.world.color.b, 1.0) if scene.world else (0.8, 0.8, 0.8, 1.0)

    out.write("*SCENE {\n")
    out.write('\t*FILENAME "%s"\n' % (bpy.data.filepath))
    out.write('\t*FIRSTFRAME %s\n' % (scene.frame_start))
    out.write('\t*LASTFRAME %s\n' % (scene.frame_end))
    out.write('\t*FRAMESPEED %s\n' % (scene.render.fps))
    out.write('\t*STATICFRAME %s\n' % (scene.frame_current))
    out.write(f'\t*AMBIENTSTATIC {df} {df} {df}\n' % (world_amb[0], world_amb[1], world_amb[2]))
    out.write("}\n\n")

#-------------------------------------------------------------------------------------------------------------------------------
def write_materials(out):
    unique_materials = []
        
    # Iterar sobre los objetos en la escena
    out.write('*MATERIALS {\n')
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and obj.data.materials:
            for mat in obj.data.materials:
                if mat.name in unique_materials:
                    continue  # Saltar si el material ya fue procesado.
                unique_materials.append(mat.name)  # Añadir el material al conjunto.
                
                out.write('\t*MATERIAL %d {\n' % (len(unique_materials) - 1))
                out.write('\t\t*NAME "%s"\n' % (mat.name))

                print('----------------------------------------------------------')
                print('\nnewmtl %s' % mat.name)  # Define a new material: matname_imgname
                
                # Envolver material para usar PrincipledBSDFWrapper
                mat_wrap = PrincipledBSDFWrapper(mat) if mat.use_nodes else None
                
                if mat_wrap:
                    use_mirror = mat_wrap.metallic != 0.0
                    use_transparency = mat_wrap.alpha != 1.0
                
                    # The Ka statement specifies the ambient reflectivity using RGB values.
                    if use_mirror:
                        print(f'Ka {df} {df} {df}' % (mat_wrap.metallic, mat_wrap.metallic, mat_wrap.metallic))
                    else:
                        print(f'Ka {df} {df} {df}' % (1.0, 1.0, 1.0))
                        
                    # The Kd statement specifies the diffuse reflectivity using RGB values.
                    out.write(f'\t\t*COL_DIFFUSE {df} {df} {df}\n' % mat_wrap.base_color[:3]) # Diffuse
                    print(f'Kd {df} {df} {df}' % mat_wrap.base_color[:3]) # Diffuse
                    # XXX TODO Find a way to handle tint and diffuse color, in a consistent way with import...
                    out.write(f'\t\t*COL_SPECULAR {df} {df} {df}\n' % (mat_wrap.specular, mat_wrap.specular, mat_wrap.specular))  # Specular
                    print(f'Ks {df} {df} {df}' % (mat_wrap.specular, mat_wrap.specular, mat_wrap.specular))  # Specular
                                            
                    #==============================Swyter, maybe we could use this for the *FACESHADERS block??? 
                    # See http://en.wikipedia.org/wiki/Wavefront_.obj_file for whole list of values...
                    # Note that mapping is rather fuzzy sometimes, trying to do our best here.
                    if mat_wrap.specular == 0:
                        print('illum 1')  # no specular.
                    elif use_mirror:
                        if use_transparency:
                            print('illum 6')  # Reflection, Transparency, Ray trace
                        else:
                            print('illum 3')  # Reflection and Ray trace
                    elif use_transparency:
                        print('illum 9')  # 'Glass' transparency and no Ray trace reflection... fuzzy matching, but...
                    else:
                        print('illum 2')  # light normally
                        
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

                        texture_path = bpy.path.abspath(image.filepath)
                        print('%s %s' % (key, texture_path))
                        if not (os.path.exists(texture_path)):
                            out.write('\t\t*TWOSIDED\n')
                        out.write('\t\t*MAP_DIFFUSE "%s"\n' % (texture_path))
                        out.write('\t\t*COMMENT diffuse texture class "Bitmap"\n')
                        
                        if use_mirror:
                            out.write('\t\t*MAP_DIFFUSE_AMOUNT %.1f\n' % (mat_wrap.metallic))
                        else:
                            out.write('\t\t*MAP_DIFFUSE_AMOUNT %.1f\n' % (1))
                        if use_transparency:
                            out.write('\t\t*MAP_HASALPHA\n')
                out.write('\t}\n')
    out.write('}\n\n')

    return unique_materials

#-------------------------------------------------------------------------------------------------------------------------------
def write_mesh_data(out, scene, depsgraph, materials_list):
    matrix_data = {}

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

            # Apply transform matrix
            if TRANSFORM_TO_CENTER:
                # Create an empty matrix and get the original scale
                to_origin = Matrix.Identity(4)
                scale_matrix = Matrix.Diagonal(ob.scale).to_4x4()

                # Construir la matriz transformada respetando la escala
                matrix_transformed = EXPORT_GLOBAL_MATRIX @ (to_origin @ scale_matrix)
                me.transform(matrix_transformed)
            else:
                matrix_transformed = EXPORT_GLOBAL_MATRIX @ ob_mat
                me.transform(matrix_transformed)

            #Append data to dictionary, will be used for place and geom node.
            if me.name not in matrix_data:
                matrix_data[ob_main.name] = {
                    "matrix_original" : ob_mat.copy(),
                    "matrix_transformed": matrix_transformed.copy()
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
                            uv_list.append((uv[0], -uv[1]))
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

            # Print mesh data
            out.write("*MESH {\n")
            out.write('\t*NAME "%s"\n' % (ob_main.name))
            out.write('\t*VERTCOUNT %d\n' % len(me_verts))
            out.write('\t*UVCOUNT %d\n' % uv_unique_count)
            out.write('\t*VERTCOLCOUNT %d\n' % vcolor_unique_count)
            out.write('\t*FACECOUNT %d\n' % len(me.polygons))
            out.write('\t*TRIFACECOUNT %d\n' % (sum(len(face.loop_indices) - 2 for face in me.polygons)))
            out.write('\t*FACELAYERSCOUNT %d\n' % sum(1 for uv_layer in me.uv_layers if uv_layer.active))

            # Vert
            out.write('\t*VERTEX_LIST {\n')
            for v in me_verts:
                out.write(f'\t\t{df} {df} {df}\n' % (v.co.x, v.co.y, v.co.z))
            out.write('\t}\n')

            # UVs
            out.write('\t*UV_LIST {\n')
            for uv in uv_list:
                out.write(f'\t\t{df} {df}\n' % uv[:])
            out.write('\t}\n')

            # Vertex Colors
            out.write('\t*VERTCOL_LIST {\n')
            for col in vcolor_list:
                out.write(f'\t\t{df} {df} {df} {df}\n' % (col[0]*0.57, col[1]*0.57, col[2]*0.57, col[3]))
            out.write('\t}\n')

            # Face Format
            out.write('\t*FACEFORMAT VTCMF\n')
            out.write("\t*FACE_LIST {\n")
            for f, f_index in face_index_pairs:               
                
                f_v = [(vi, me_verts[v_idx], l_idx)
                        for vi, (v_idx, l_idx) in enumerate(zip(f.vertices, f.loop_indices))]

                #Vertices ---V
                vertex_count = len(f_v)
                out.write("\t\t%d " % vertex_count)
                for vi, v, li in reversed(f_v):
                    out.write("%d " % (v.index))

                # Mapeo de UVs --- T
                if uv_list and faceuv:
                    for vi, v_idx, l_idx in reversed(f_v):
                        uv_idx = uv_face_mapping[f_index][vi] if uv_face_mapping[f_index] else 0
                        out.write("%d " % (uv_idx))
                else:
                    # Rellenar con ceros si no hay mapeo UV
                    for _ in range(vertex_count):
                        out.write("%d " % -1)

                # Colores de vértices --- C
                if vcolor_list and facecolors:
                    for vi, v, li in reversed(f_v):
                        color_idx = vcolor_face_mapping[f_index][vi] if vcolor_face_mapping[f_index] else 0
                        out.write("%d " % color_idx)
                else:
                    # Rellenar con ceros si no hay mapeo de colores
                    for _ in range(vertex_count):
                        out.write("%d " % 0)
            
                #Face normals ---N
                # swy: we're missing exporting (optional) face normals here

                # Material --- M
                if len(material_names) > 0  and len(materials_list) > 0:
                    f_mat = min(f.material_index, len(materials) - 1)
                    material_name = material_names[f_mat] 
                    mesh_material_index = materials_list.index(material_name)
                    out.write("%d " % mesh_material_index)
                else:
                    out.write("%d " % -1)

                #Shaders ---S
                # swy: we're missing exporting an optional shader index here

                #Flags ---F
                flags = 0
                if ob_for_convert is not None and len(ob_for_convert.material_slots) > 0:
                    if ob_for_convert.material_slots[f.material_index].material.use_backface_culling:
                        flags |= 1 << 16
                out.write('%d\n' % flags)
            out.write("\t}\n")
            out.write("}\n\n")

            # clean up
            ob_for_convert.to_mesh_clear()

    return matrix_data

#-------------------------------------------------------------------------------------------------------------------------------
def write_geom_node(out, object_matrix_data):
    for mesh_name, data in object_matrix_data.items():
        matrix_transformed = data["matrix_transformed"]

        # Apply transform matrix
        if not TRANSFORM_TO_CENTER:
            matrix_transformed = Matrix.Identity(4) 

        out.write('*GEOMNODE {\n')
        out.write('\t*NAME "%s"\n' % (mesh_name))
        out.write('\t*MESH "%s"\n' % (mesh_name))
        out.write('\t*WORLD_TM {\n')
        
        # Transformar la malla según la matriz global y local
        if TRANSFORM_TO_CENTER:
            matrix_transformed = (matrix_transformed.inverted() @ matrix_transformed).normalized()
        out.write(f'\t\t*TMROW0 {df} {df} {df} {df}\n' % (matrix_transformed[0].x, matrix_transformed[0].y, matrix_transformed[0].z, 0))
        out.write(f'\t\t*TMROW1 {df} {df} {df} {df}\n' % (matrix_transformed[1].x, matrix_transformed[1].y, matrix_transformed[1].z, 0))
        out.write(f'\t\t*TMROW2 {df} {df} {df} {df}\n' % (matrix_transformed[2].x, matrix_transformed[2].y, matrix_transformed[2].z, 0))
        
        #Transform position
        out.write(f'\t\t*TMROW3 {df} {df} {df} {df}\n' % (matrix_transformed[0].w, matrix_transformed[1].w, matrix_transformed[2].w, 1))
        out.write(f'\t\t*POS {df} {df} {df}\n' % (matrix_transformed[0].w, matrix_transformed[1].w, matrix_transformed[2].w))
        
        #Transform rotation
        transformed_rotation = matrix_transformed.to_euler()
        out.write(f'\t\t*ROT {df} {df} {df}\n' % (degrees(transformed_rotation.x), degrees(transformed_rotation.y), degrees(transformed_rotation.z)))

        #Transform scale
        transformed_scale = matrix_transformed.to_scale()
        out.write(f'\t\t*SCL {df} {df} {df}\n' % (transformed_scale.x, transformed_scale.y, transformed_scale.z))
        out.write('\t}\n')

        #Print flags
        out.write('\t*USER_FLAGS_COUNT %u\n' % 1)
        out.write('\t*USER_FLAGS {\n')
        out.write('\t\t*SET 0 0x00000000\n')
        out.write('\t}\n')
        out.write("}\n")

#-------------------------------------------------------------------------------------------------------------------------------
def write_place_node(out, object_matrix_data):
    for mesh_name, data in object_matrix_data.items():
        matrix_original = data["matrix_original"]

        # Apply transform matrix
        if not TRANSFORM_TO_CENTER:
            matrix_original = Matrix.Identity(4) 

        out.write('*PLACENODE {\n')
        out.write('\t*NAME "%s"\n' % (mesh_name))
        out.write('\t*MESH "%s"\n' % (mesh_name))
        out.write('\t*WORLD_TM {\n')

        # Transformar la malla según la matriz global y local
        transformed_matrix = EXPORT_GLOBAL_MATRIX @ matrix_original
        transformed_matrix_transposed = transformed_matrix.normalized()
        pos = transformed_matrix_transposed.translation.copy()

        # Do weird EuroLand things....
        transformed_matrix_transposed = transformed_matrix_transposed.transposed()
        row1 = transformed_matrix_transposed[1][:] 
        transformed_matrix_transposed[1][:] = transformed_matrix_transposed[2][:] 
        transformed_matrix_transposed[2][:] = row1 
        transformed_matrix_transposed = transformed_matrix_transposed.to_3x3()

        out.write(f'\t\t*TMROW0 {df} {df} {df} {df}\n' % (transformed_matrix_transposed[0].x, transformed_matrix_transposed[0].y, transformed_matrix_transposed[0].z, 0))
        out.write(f'\t\t*TMROW1 {df} {df} {df} {df}\n' % (transformed_matrix_transposed[1].x, transformed_matrix_transposed[1].y, transformed_matrix_transposed[1].z, 0))
        out.write(f'\t\t*TMROW2 {df} {df} {df} {df}\n' % (transformed_matrix_transposed[2].x, transformed_matrix_transposed[2].y, transformed_matrix_transposed[2].z, 0))

        #Transform position
        out.write(f'\t\t*TMROW3 {df} {df} {df} {df}\n' % (pos.x, pos.y, pos.z, 1))
        out.write(f'\t\t*POS {df} {df} {df}\n' % (pos.x, pos.y, pos.z))
        
        #Transform rotation
        transformed_rotation = transformed_matrix_transposed.to_euler()
        out.write(f'\t\t*ROT {df} {df} {df}\n' % (degrees(transformed_rotation.x), degrees(transformed_rotation.y), degrees(transformed_rotation.z)))

        #Transform scale
        transformed_scale = transformed_matrix_transposed.to_scale()
        out.write(f'\t\t*SCL {df} {df} {df}\n' % (transformed_scale.x, transformed_scale.y, transformed_scale.z))
        out.write('\t}\n')
        out.write('}\n')

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
        out.write("*EUROCOM_INTERCHANGE_FILE 100\n")
        out.write('*COMMENT Eurocom Interchange File Version 1.00 %s\n' % datetime.now().strftime("%A %B %d %Y %H:%M"))
        out.write('*COMMENT Version of eif-plugin that wrote this file %s\n' % EIF_VERSION)
        out.write('*COMMENT Version of blender that wrote this file %s\n\n' % bpy.app.version_string)
        out.write("*OPTIONS {\n")
        out.write("\t*COORD_SYSTEM LH\n")
        out.write("}\n\n")

        write_scene_data(out, scene)
        processed_materials = write_materials(out)
        mesh_position_data = write_mesh_data(out, scene, depsgraph, processed_materials)

        if EXPORT_GEOMNODE:
            write_geom_node(out, mesh_position_data)

        if EXPORT_PLACENODE:
            write_place_node(out, mesh_position_data)
                
    print(f"Archivo exportado con éxito: {filepath}")

#-------------------------------------------------------------------------------------------------------------------------------
filepath = bpy.path.abspath("C:\\Users\\Jordi Martinez\\Desktop\\EuroLand Files\\3D Examples\\test.EIF")  # Cambia la ruta si es necesario
export_file(filepath)
