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
from .eland_utils import *
from math import degrees
from pathlib import Path
from mathutils import Matrix
from datetime import datetime
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

#-------------------------------------------------------------------------------------------------------------------------------
EIF_VERSION = '1.00'
EXPORT_TRI=False
EXPORT_APPLY_MODIFIERS=True

#-------------------------------------------------------------------------------------------------------------------------------
def _write(context, filepath,
           EXPORT_GEOMNODE, 
           EXPORT_PLACENODE, 
           TRANSFORM_TO_CENTER, 
           EXPORT_UV,
           EXPORT_VERTEX_COLORS,
           DECIMAL_PRECISION,
           GLOBAL_SCALE
        ):
   
    df = f'%.{DECIMAL_PRECISION}f'

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
                    matrix_transformed = (to_origin @ scale_matrix)
                else:
                    matrix_transformed = ob_mat
                
                me.transform(Matrix.Scale(GLOBAL_SCALE, 4) @ (MESH_GLOBAL_MATRIX @ matrix_transformed))

                #Append data to dictionary, will be used for place and geom node.
                if me.name not in matrix_data:
                    matrix_data[ob_main.name] = {
                        "type" : ob_main.type,
                        "matrix_original" : ob_mat.copy(),
                        "matrix_transformed": matrix_transformed.copy()
                    }

                # If negative scaling, we have to invert the normals...
                if ob_mat.determinant() < 0.0:
                    me.flip_normals()

                # Crear listas únicas de coordenadas de vértices, UVs y colores de vértices
                unique_vertices = list({tuple(v.co) for v in me.vertices})

                #Get UVs
                unique_uvs = []
                if EXPORT_UV:
                    if me.uv_layers:
                        for uv_layer in me.uv_layers:
                            for loop in me.loops:
                                unique_uvs.append(tuple(uv_layer.data[loop.index].uv))
                        unique_uvs = list(set(unique_uvs))

                #Get colors
                unique_colors = []
                if EXPORT_VERTEX_COLORS:
                    if me.vertex_colors:
                        for color_layer in me.vertex_colors:
                            for loop in me.loops:
                                unique_colors.append(tuple(color_layer.data[loop.index].color))
                        unique_colors = list(set(unique_colors))

                #Get face normals
                unique_normals = []
                if EXPORT_NORMALS:
                    unique_normals = list({tuple(poly.normal) for poly in me.polygons})

                #Get number of layers that should be in EuroLand, based in the UV Layers
                faceLayersCount = len(me.uv_layers)
                materials = me.materials[:]
                material_names = [m.name if m else None for m in materials]

                # Print mesh data                       
                out.write("*MESH {\n")
                out.write('\t*NAME "%s"\n' % (ob_main.name))
                out.write('\t*VERTCOUNT %d\n' % len(unique_vertices))
                out.write('\t*UVCOUNT %d\n' %  len(unique_uvs))
                out.write('\t*VERTCOLCOUNT %d\n' % len(unique_colors))
                out.write('\t*FACECOUNT %d\n' % len(me.polygons))
                out.write('\t*TRIFACECOUNT %d\n' % (sum(len(face.loop_indices) - 2 for face in me.polygons)))
                out.write('\t*FACELAYERSCOUNT %d\n' % faceLayersCount)

                # Vert
                faceformat = "V"
                out.write('\t*VERTEX_LIST {\n')
                for v in unique_vertices:
                    out.write(f'\t\t{df} {df} {df}\n' % (v[0], v[1], v[2]))
                out.write('\t}\n')

                # Textures
                if EXPORT_UV:
                    out.write('\t*UV_LIST {\n')
                    if unique_uvs:
                        faceformat = faceformat + "T"
                        for uv in unique_uvs:
                            out.write(f'\t\t{df} {df}\n' % (uv[0], -uv[1]))
                    out.write('\t}\n')

                # Colors
                if EXPORT_VERTEX_COLORS:
                    out.write('\t*VERTCOL_LIST {\n')
                    if unique_colors:
                        faceformat = faceformat + "C"
                        for col in unique_colors:
                            color_corrected = adjust_rgb(col[0], col[1], col[2], col[3], 0.57)
                            out.write(f'\t\t{df} {df} {df} {df}\n' % (color_corrected[0], color_corrected[1], color_corrected[2], color_corrected[3]))
                    out.write('\t}\n')

                # Materials
                if EXPORT_UV and len(me.materials) > 0:
                    faceformat = faceformat + "M"
                
                # Flags
                faceformat = faceformat + "F"

                # Face Format                
                out.write('\t*FACEFORMAT %s\n' % faceformat)
                out.write("\t*FACE_LIST {\n")

                # Create mapping lists
                vertex_index_map = {v: idx for idx, v in enumerate(unique_vertices)}
                uv_index_map = {uv: idx for idx, uv in enumerate(unique_uvs)}
                color_index_map = {color: idx for idx, color in enumerate(unique_colors)}
                normal_index_map = {normal: idx for idx, normal in enumerate(unique_normals)}

                # Iterar por cada cara y generar la información
                for poly in me.polygons:
                    
                    #Vertices --- V        
                    vertex_indices = [vertex_index_map[tuple(me.vertices[v].co)] for v in reversed(poly.vertices)]
                    #--------print(f"Cara {poly.index}: Vértices ({len(poly.vertices)}): {vertex_indices}")
                    out.write(f"\t\t{len(poly.vertices)} " + " ".join(map(str, vertex_indices)) + " ")
                        
                    # Mapeo de UVs --- T
                    if EXPORT_UV and unique_uvs:
                        for uv_layer in me.uv_layers:
                            uv_indices = []
                            for loop_index in reversed(poly.loop_indices):
                                uv = tuple(uv_layer.data[loop_index].uv)
                                uv_indices.append(uv_index_map.get(uv, -1))
                            #print(f"Cara {poly.index}, Capa UV '{uv_layer.name}': {uv_indices}")
                            out.write(" ".join(map(str, uv_indices)) + " ")

                        # Si hay más capas de colores que UVs, agregar -1 para las capas faltantes
                        if faceLayersCount > len(me.uv_layers):
                            missing_color_layers = faceLayersCount - len(me.uv_layers)
                            for _ in range(missing_color_layers):
                                out.write(" ".join(["-1"] * len(poly.vertices)) + " ")

                    # Colores de vértices --- C
                    if EXPORT_VERTEX_COLORS and unique_colors:
                        for color_layer in me.vertex_colors:
                            color_indices = []
                            for loop_index in reversed(poly.loop_indices):
                                color = tuple(color_layer.data[loop_index].color)
                                color_indices.append(color_index_map.get(color, -1))
                            #print(f"Cara {poly.index}, Capa de colores '{color_layer.name}': {color_indices}")
                            out.write(" ".join(map(str, color_indices)) + " ")
                            
                        # Si hay más capas UV que colores, agregar -1 para las capas faltantes
                        if faceLayersCount > len(me.vertex_colors):
                            missing_uv_layers = faceLayersCount - len(me.vertex_colors)
                            for _ in range(missing_uv_layers):
                                out.write(" ".join(["-1"] * len(poly.vertices)) + " ")

                    # Face normals ---N
                    if EXPORT_NORMALS and unique_normals:
                        normal_index = normal_index_map[tuple(poly.normal)]
                        #print(f"Cara {poly.index}: Normal: {normal_index}")
                        out.write(" %d " % normal_index)
                    
                    # Material Index ---M
                    if EXPORT_UV and len(me.materials) > 0:
                        for layer_index in range(faceLayersCount):
                            material_index = -1
                            if poly.material_index < len(ob.material_slots) and layer_index < 1:
                                material_name = material_names[poly.material_index] 
                                material_index = materials_list.index(material_name)
                            out.write("%d " % material_index)

                    # Flags ---F
                    flags = 0
                    out.write('%d\n' % flags)

                out.write("\t}\n")
                out.write("}\n\n")

                # clean up
                ob_for_convert.to_mesh_clear()

        return matrix_data

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_geom_and_place_node(out, obj_matrix_data, isGeomNode = False):
        for mesh_name, data in obj_matrix_data.items():
            if isGeomNode:
                matrix_data = data["matrix_transformed"]

                # Apply transform matrix
                if TRANSFORM_TO_CENTER:
                    matrix_data = Matrix.Identity(4) 

                out.write('*GEOMNODE {\n')
            else:
                matrix_data = data["matrix_original"]

                # Apply transform matrix
                if not TRANSFORM_TO_CENTER:
                    matrix_data = Matrix.Identity(4) 

                out.write('*PLACENODE {\n')
            #Write common content
            out.write('\t*NAME "%s"\n' % (mesh_name))
            out.write('\t*MESH "%s"\n' % (mesh_name))
            out.write('\t*WORLD_TM {\n')

            #Calculate matrix rotations.... 
            eland_data = create_euroland_matrix(matrix_data, data["type"])
            eland_matrix = eland_data["eland_matrix"]
            eland_euler = eland_data["eland_euler"]

            #Matrix rotation
            out.write(f'\t\t*TMROW0 {df} {df} {df} {df}\n' % (eland_matrix[0].x, eland_matrix[1].x, eland_matrix[2].x, 0))
            out.write(f'\t\t*TMROW1 {df} {df} {df} {df}\n' % (eland_matrix[0].y, eland_matrix[1].y, eland_matrix[2].y, 0))
            out.write(f'\t\t*TMROW2 {df} {df} {df} {df}\n' % (eland_matrix[0].z, eland_matrix[1].z, eland_matrix[2].z, 0))     

            # Position
            obj_position = eland_matrix.translation
            out.write(f'\t\t*TMROW3 {df} {df} {df} {df}\n' % (obj_position.x, obj_position.y, obj_position.z, 1))
            out.write(f'\t\t*POS {df} {df} {df}\n' % (obj_position.x, obj_position.y, obj_position.z))
            
            # Rotation
            out.write(f'\t\t*ROT: {df} {df} {df}\n' % (degrees(eland_euler.x), degrees(eland_euler.z),degrees(eland_euler.y)))
            
            #Scale
            transformed_scale = eland_matrix.to_scale()
            out.write(f'\t\t*SCL {df} {df} {df}\n' % (transformed_scale.x, transformed_scale.z, transformed_scale.y))
            out.write('\t}\n')

            #Print flags
            if isGeomNode:
                out.write('\t*USER_FLAGS_COUNT %u\n' % 1)
                out.write('\t*USER_FLAGS {\n')
                out.write('\t\t*SET 0 0x00000000\n')
                out.write('\t}\n')
            out.write("}\n")

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_eif_file():
        depsgraph = bpy.context.evaluated_depsgraph_get()
        scene = bpy.context.scene

        # Exit edit mode before exporting, so current object states are exported properly.
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Create text file
        with open(filepath, 'w', encoding="utf8",) as out:
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
                write_geom_and_place_node(out, mesh_position_data, True)

            if EXPORT_PLACENODE:
                write_geom_and_place_node(out, mesh_position_data)                

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
         Decimal_Precision,
         Output_Scale):

    _write(context, filepath, 
           EXPORT_GEOMNODE=Output_GeomNode,
           EXPORT_PLACENODE=Output_PlaceNode, 
           TRANSFORM_TO_CENTER=Transform_Center, 
           EXPORT_UV=Output_Mesh_UV,
           EXPORT_VERTEX_COLORS=Output_Mesh_Vertex_Colors,
           DECIMAL_PRECISION=Decimal_Precision,
           GLOBAL_SCALE=Output_Scale)

    return {'FINISHED'}
if __name__ == '__main__':
    save({}, str(Path.home()) + '/Desktop/EurocomEIF.eif')
