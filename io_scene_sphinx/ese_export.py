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
ESE_VERSION = '1.00'
EXPORT_TRI = True
EXPORT_APPLY_MODIFIERS = True
START_FRAME = 0
END_FRAME = 0

#Global variables
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
           EXPORT_END_FRAME,
           EXPORT_ONLY_FIRST_FRAME):
    
    df = f'%.{DECIMAL_PRECISION}f'
    dcf = f'{{:>{DECIMAL_PRECISION}f}}'

    #-------------------------------------------------------------------------------------------------------------------------------
    def printCustomProperties(out):
        scene = bpy.context.scene
        custom_properties = {key: value for key, value in scene.items() if key not in '_RNA_UI'}

        #print only the visible ones
        visible_properties = {key: value for key, value in custom_properties.items() if isinstance(value, (int, float, str, bool))}      
        type_mapping = {
            int: "Numeric",
            float: "Numeric",
            str: "String",
            bool: "Boolean"
        }   

        # Save scene custom properties
        properties_list = []
        for key, value in visible_properties.items():
            type_name = type_mapping.get(type(value), type(value).__name__)

            #create dict object
            property_data = {"name": key,"type": type_name,"value": value}
            properties_list.append(property_data)

        # Check for the camera script property
        if scene.euro_properties:
            euro_properties = scene.euro_properties

            # Si la propiedad 'enable_camera_script' no existe, puedes establecerla o usarla
            if not hasattr(euro_properties, 'enable_camera_script'):
                euro_properties.enable_camera_script = False

            # Acceder al valor de la propiedad
            if euro_properties.enable_camera_script:
                property_data = {
                    "name": "cameraScriptEditor",
                    "type": "Numeric",
                    "value": 1}
                properties_list.append(property_data)

                #add info
                current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                computer_name = platform.node() 
                user_name = platform.uname().node
                blender_version = bpy.app.version_string

                # Crear la propiedad extra con la información requerida
                extra_property = {
                    "name": "cameraScriptEditor Info",
                    "type": "String",
                    "value": f"{current_time} Computer:{computer_name} UserName:{user_name} BlenderVer:#({blender_version})"
                }
                properties_list.append(extra_property)

        # Imprimir las propiedades almacenadas
        out.write('\t*SCENE_UDPROPS {\n')
        out.write('\t\t*PROP_COUNT\t%d\n' % len(properties_list))
        for index, property_data in enumerate(properties_list):
            out.write('\t\t*PROP\t%d\t"%s"\t"%s"\t"%s"\n' % (index, property_data["name"], property_data["type"], property_data["value"]))
        out.write('\t}\n')

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_scene_data(out, scene):
        global FRAMES_COUNT, TICKS_PER_FRAME, START_FRAME, END_FRAME, EXPORT_STATIC_FRAME

        #Get set default scene data
        START_FRAME = scene.frame_start
        END_FRAME = scene.frame_end

        #Check frame is in range
        if EXPORT_STATIC_FRAME < START_FRAME:
            EXPORT_STATIC_FRAME = START_FRAME
        if EXPORT_STATIC_FRAME > END_FRAME:
            EXPORT_STATIC_FRAME = END_FRAME      

        #Override values
        if EXPORT_FROM_FRAME_ENABLED and (EXPORT_FROM_FRAME >= START_FRAME):
            EXPORT_STATIC_FRAME = EXPORT_FROM_FRAME
            START_FRAME = EXPORT_FROM_FRAME
        if EXPORT_END_FRAME_ENABLED and (EXPORT_END_FRAME <= END_FRAME):
            END_FRAME = EXPORT_END_FRAME
        if EXPORT_ONLY_FIRST_FRAME:
            EXPORT_STATIC_FRAME = START_FRAME

        # Set the first frame
        bpy.context.scene.frame_set(EXPORT_STATIC_FRAME)

        #Get scene data
        frame_rate = scene.render.fps
        FRAMES_COUNT = END_FRAME - START_FRAME + 1

        tick_frequency = 4800 #Matches original examples
        TICKS_PER_FRAME = tick_frequency // frame_rate

        world_amb = scene.world.color if scene.world else (0.8, 0.8, 0.8)

        #Print scene data
        out.write("*SCENE {\n")
        out.write('\t*SCENE_FILENAME "%s"\n' % (bpy.data.filepath))
        out.write('\t*SCENE_FIRSTFRAME %s\n' % START_FRAME)
        out.write('\t*SCENE_LASTFRAME %s\n' % END_FRAME)
        out.write('\t*SCENE_FRAMESPEED %s\n' % frame_rate)
        out.write('\t*SCENE_TICKSPERFRAME %s\n' % TICKS_PER_FRAME)
        out.write(f'\t*SCENE_BACKGROUND_STATIC {df} {df} {df}\n' % (world_amb[0], world_amb[1], world_amb[2]))
        out.write(f'\t*SCENE_AMBIENT_STATIC {df} {df} {df}\n' % (world_amb[0], world_amb[1], world_amb[2]))
        printCustomProperties(out)
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
            elif materials_count > 1:
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
    def write_tm_node(out, obj_matrix_data, isPivot = False):

        if isPivot:
            matrix_data = obj_matrix_data["matrix_transformed"]

            # Apply transform matrix
            if TRANSFORM_TO_CENTER:
                matrix_data = Matrix.Identity(4) 

            out.write('\t*NODE_PIVOT_TM {\n')
        else:
            matrix_data = obj_matrix_data["matrix_original"]

            # Apply transform matrix
            if not TRANSFORM_TO_CENTER:
                matrix_data = Matrix.Identity(4) 

            out.write('\t*NODE_TM {\n')

        out.write('\t\t*NODE_NAME "%s"\n' % (obj_matrix_data["name"]))
        out.write('\t\t*INHERIT_POS %d %d %d\n' % (0, 0, 0))
        out.write('\t\t*INHERIT_ROT %d %d %d\n' % (0, 0, 0))
        out.write('\t\t*INHERIT_SCL %d %d %d\n' % (0, 0, 0))
            
        #Calculate matrix rotations.... 
        eland_data = create_euroland_matrix(matrix_data, obj_matrix_data["type"])
        eland_matrix = eland_data["eland_matrix"]
        eland_euler = eland_data["eland_euler"]

        out.write(f'\t\t*TM_ROW0 {df} {df} {df}\n' % (eland_matrix[0].x, eland_matrix[1].x, eland_matrix[2].x))
        out.write(f'\t\t*TM_ROW1 {df} {df} {df}\n' % (eland_matrix[0].y, eland_matrix[1].y, eland_matrix[2].y))
        out.write(f'\t\t*TM_ROW2 {df} {df} {df}\n' % (eland_matrix[0].z, eland_matrix[1].z, eland_matrix[2].z))
        
        #Transform position
        obj_position = eland_matrix.translation
        out.write(f'\t\t*TM_ROW3 {df} {df} {df}\n' % (obj_position.x,obj_position.y,obj_position.z))
        out.write(f'\t\t*TM_POS {df} {df} {df}\n' % (obj_position.x,obj_position.y,obj_position.z))
        
        #Transform rotation
        out.write(f'\t\t*TM_ROTANGLE {df} {df} {df}\n' % (eland_euler.x, eland_euler.y, eland_euler.z))

        #Print scale
        transformed_scale = eland_matrix.to_scale()
        out.write(f'\t\t*TM_SCALE {df} {df} {df}\n' % (transformed_scale.x, transformed_scale.z, transformed_scale.y))
        out.write(f'\t\t*TM_SCALEANGLE {df} {df} {df}\n' % (0, 0, 0))
        out.write('\t}\n')

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_animation_node(out, object_data, object_matrix_data):
        global TICKS_PER_FRAME, START_FRAME, END_FRAME
        
        out.write('\t*TM_ANIMATION {\n')
        out.write('\t\t*TM_ANIMATION "%s"\n' % object_data.name)

        frameIndex = 0 
        out.write('\t\t*TM_ANIM_FRAMES {\n')
        for f in range(START_FRAME, END_FRAME + 1):
            bpy.context.scene.frame_set(f)
                
            # Calculate frame index
            if f > 0:
                frameIndex += TICKS_PER_FRAME

            #Print rotation
            out.write('\t\t\t*TM_FRAME  {:<5d}'.format(frameIndex))

            eland_data = create_euroland_matrix(object_data.matrix_world.copy(), object_data.type)
            eland_matrix = eland_data["eland_matrix"]

            if not TRANSFORM_TO_CENTER:
                current_matrix = object_data.matrix_world.copy()        
                relative_matrix = current_matrix @ object_matrix_data["matrix_original"]
                eland_data = create_euroland_matrix(relative_matrix, object_data.type)
                eland_matrix = eland_data["eland_matrix"]
                eland_matrix.translation = (Matrix.Identity(4) @ current_matrix).translation

            out.write(f' {df} {df} {df}' % (eland_matrix[0].x, eland_matrix[1].x, eland_matrix[2].x))
            out.write(f' {df} {df} {df}' % (eland_matrix[0].y, eland_matrix[1].y, eland_matrix[2].y))
            out.write(f' {df} {df} {df}' % (eland_matrix[0].z, eland_matrix[1].z, eland_matrix[2].z))
            
            #Transform position
            obj_position = eland_matrix.translation
            out.write(f' {df} {df} {df}\n' % (obj_position.x, obj_position.y, obj_position.z))

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

                # Create transform matrix
                if TRANSFORM_TO_CENTER:
                    to_origin = Matrix.Identity(4)
                    scale_matrix = Matrix.Diagonal(ob.scale).to_4x4()

                    matrix_transformed = to_origin @ scale_matrix
                else:
                    matrix_transformed = ob_mat
                
                # Apply transform matrix
                me.transform(MESH_GLOBAL_MATRIX @ matrix_transformed)

                obj_matrix_data = {
                    "name" : ob_main.name,
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
                if EXPORT_MESH_UV:
                    if me.uv_layers:
                        for uv_layer in me.uv_layers:
                            for loop in me.loops:
                                unique_uvs.append(tuple(uv_layer.data[loop.index].uv))
                        unique_uvs = list(set(unique_uvs))

                #Get colors
                unique_colors = []
                if EXPORT_MESH_VCOLORS:
                    if me.vertex_colors:
                        for color_layer in me.vertex_colors:
                            for loop in me.loops:
                                unique_colors.append(tuple(color_layer.data[loop.index].color))
                        unique_colors = list(set(unique_colors))

                # Create mapping lists
                vertex_index_map = {v: idx for idx, v in enumerate(unique_vertices)}
                uv_index_map = {uv: idx for idx, uv in enumerate(unique_uvs)}
                color_index_map = {color: idx for idx, color in enumerate(unique_colors)}
                mesh_materials = scene_materials[ob_main.name]
                mesh_materials_names = [m.name if m else None for m in mesh_materials]
                
                # Start printing
                out.write("*GEOMOBJECT {\n")
                out.write('\t*NODE_NAME "%s"\n' % ob_main.name)
                write_tm_node(out, obj_matrix_data)
                write_tm_node(out, obj_matrix_data, True)

                #Mesh data
                out.write('\t*MESH {\n')
                out.write('\t\t*TIMEVALUE %d\n' % EXPORT_STATIC_FRAME)
                out.write('\t\t*MESH_NUMVERTEX %u\n' % len(unique_vertices))
                out.write('\t\t*MESH_NUMFACES %u\n' % len(me.polygons))

                #-------------------------------------------------------------------------------------------------------------------------------
                #Vertex lists
                out.write('\t\t*MESH_VERTEX_LIST {\n')
                for vindex, vertex in enumerate(unique_vertices):
                    out.write(f'\t\t\t*MESH_VERTEX  {{:>5d}}\t{dcf}\t{dcf}\t{dcf}\n'.format(vindex, vertex[0], vertex[1], vertex[2]))
                out.write('\t\t}\n')    
                
                #Vertex mapping
                out.write('\t\t*MESH_FACE_LIST {\n')
                for p_index, poly in enumerate(me.polygons):
                    
                    vertex_indices = [vertex_index_map[tuple(me.vertices[v].co)] for v in (poly.vertices)]

                    #Get material index
                    material_index = -1
                    if poly.material_index < len(me.materials):
                        material_name = me.materials[poly.material_index].name
                        if material_name in mesh_materials_names:
                            material_index = mesh_materials_names.index(material_name)
                    
                    # swy: the calc_loop_triangles() doesn't modify the original faces, and instead does temporary ad-hoc triangulation
                    #      returning us a list of three loops per "virtual triangle" that only exists in the returned thingie
                    #      i.e. len(tri_loop) should always be 3, but internally, for each loop .face we're a member of
                    #           still has 4 vertices and the four (different) loops of an n-gon, and .link_loop_next
                    #           points to the original model's loop chain; the loops of our triangle aren't really linked
                    edges_from_ngon = []  # Almacenar el resultado para cada borde del triángulo
                    for tri_idx in range(len(vertex_indices)):
                        is_from_ngon = tri_edge_is_from_ngon(poly, vertex_indices, tri_idx, me.loops)
                        edges_from_ngon.append(1 if is_from_ngon else 0)

                    #Face Vertex Index
                    out.write('\t\t\t*MESH_FACE    {:>3d}:    A: {:>6d} B: {:>6d} C: {:>6d}'.format(p_index, vertex_indices[0], vertex_indices[1], vertex_indices[2]))
                    out.write('    AB: {:<6d} BC: {:<6d} CA: {:<6d}  *MESH_SMOOTHING   *MESH_MTLID {:<3d}\n'.format(edges_from_ngon[0], edges_from_ngon[1], edges_from_ngon[2], material_index))
                out.write('\t\t}\n')

                #-------------------------------------------------------------------------------------------------------------------------------
                if EXPORT_MESH_UV:
                    #Print list
                    out.write('\t\t*MESH_NUMTVERTEX %u\n' % len(unique_uvs))
                    if unique_uvs:
                        out.write('\t\t*MESH_TVERTLIST {\n')
                        for uv_index, uv in enumerate(unique_uvs):
                            out.write(f'\t\t\t*MESH_TVERT {{:>5d}}\t{dcf}\t{dcf}\t{dcf}\n'.format(uv_index, uv[0], uv[1], 0))
                        out.write('\t\t}\n')

                        #Map UVs
                        out.write('\t\t*MESH_NUMTVFACES %d\n' % len(me.polygons))
                        out.write('\t\t*MESH_TFACELIST {\n')
                        for p_index, poly in enumerate(me.polygons):
                            uv_indices = []
                            for loop_index in (poly.loop_indices):
                                vertex = tuple(me.uv_layers.active.data[loop_index].uv)
                                uv_indices.append(uv_index_map.get(vertex, -1))
                            out.write(f'\t\t\t*MESH_TFACE {{:<3d}}\t{dcf}\t{dcf}\t{dcf}\n'.format(p_index, uv_indices[0], uv_indices[1], uv_indices[2]))
                        out.write('\t\t}\n')

                #-------------------------------------------------------------------------------------------------------------------------------
                if EXPORT_MESH_VCOLORS:
                    #Print list
                    out.write('\t\t*MESH_NUMCVERTEX %u\n' % len(unique_colors))
                    if unique_colors:
                        out.write('\t\t*MESH_CVERTLIST {\n')
                        for col_index, col  in enumerate(unique_colors):
                            out.write(f'\t\t\t*MESH_VERTCOL {{:>5d}}\t{dcf}\t{dcf}\t{dcf}\t{dcf}\n'.format(col_index, col[0], col[1], col[2], col[3]))
                        out.write('\t\t}\n')

                        #Map colors
                        out.write('\t\t*MESH_NUMCVFACES %d\n' % len(me.polygons))
                        out.write('\t\t*MESH_CFACELIST {\n')
                        for p_index, poly in enumerate(me.polygons):
                            color_indices = []
                            for loop_index in (poly.loop_indices):
                                color = tuple(me.vertex_colors.active.data[loop_index].color)
                                color_indices.append(color_index_map.get(color, -1))
                            out.write(f'\t\t\t*MESH_CFACE {{:<3d}}\t{dcf}\t{dcf}\t{dcf}\n'.format(p_index, color_indices[0], color_indices[1], color_indices[2]))
                        out.write('\t\t}\n')           

                #-------------------------------------------------------------------------------------------------------------------------------
                if EXPORT_MESH_NORMALS:
                    out.write('\t\t*MESH_NORMALS {\n')
                    for p_index, poly in enumerate(me.polygons):
                        poly_normals = poly.normal
                        vertex_indices = [vertex_index_map[tuple(me.vertices[v].co)] for v in (poly.vertices)]    
                    
                        out.write(f'\t\t\t*MESH_FACENORMAL {{:<3d}}\t{dcf}\t{dcf}\t{dcf}\n'.format(p_index, poly_normals[0], poly_normals[1], poly_normals[2]))
                        for tri_idx in range(len(vertex_indices)):
                            out.write(f'\t\t\t\t*MESH_VERTEXNORMAL {{:<3d}}\t{dcf}\t{dcf}\t{dcf}\n'.format(tri_idx, poly_normals[0], poly_normals[1], poly_normals[2]))
                    out.write('\t\t}\n')

                #-------------------------------------------------------------------------------------------------------------------------------
                if EXPORT_MESH_FLAGS:
                    # swy: refresh the custom mesh layer/attributes in case they don't exist
                    if 'euro_fac_flags' not in me.attributes:
                        me.attributes.new(name='euro_fac_flags', type='INT', domain='FACE')
                        
                    if 'euro_vtx_flags' not in me.attributes:
                        me.attributes.new(name='euro_vtx_flags', type='INT', domain='FACE')

                    euro_vtx_flags = me.attributes['euro_vtx_flags']
                    euro_fac_flags = me.attributes['euro_fac_flags']

                    # swy: add the custom mesh attributes here
                    out.write('\t\t*MESH_NUMFACEFLAGS %u\n' % len(me.polygons))
                    out.write('\t\t*MESH_FACEFLAGLIST {\n')
                    for face in me.polygons:
                        flag_value = euro_fac_flags.data[poly.index].value
                        # swy: don't set it where it isn't needed
                        if flag_value != 0:
                            out.write(f'\t\t\t*MESH_FACEFLAG %u %u\n' % (face.index, flag_value))
                    out.write('\t\t}\n') # MESH_NUMFACEFLAGS

                    out.write('\t\t*MESH_VERTFLAGSLIST {\n')
                    for idx, vert in enumerate(me.vertices):
                        flag_value = euro_vtx_flags.data[vert.index].value
                        if flag_value != 0:
                            out.write(f'\t\t\t*VFLAG %u %u\n' % (idx, flag_value))
                    out.write('\t\t}\n') # MESH_VERTFLAGSLIST            

                #Close mesh block
                out.write('\t}\n')

                #Print animations
                if EXPORT_MESH_ANIMS:
                    write_animation_node(out, ob_main, obj_matrix_data)

                out.write(f'\t*WIREFRAME_COLOR {df} {df} {df}\n' % (ob.color[0], ob.color[1], ob.color[2]))
                out.write('\t*MATERIAL_REF %d\n' % list(scene_materials.keys()).index(ob.name))

                #-------------------------------------------------------------------------------------------------------------------------------
                #  SHAPE KEYS
                #-------------------------------------------------------------------------------------------------------------------------------
                # swy: here go our blend shape weights with the mixed-in amount for each frame in the timeline
                if EXPORT_MESH_MORPH:
                    if ob.data.shape_keys:
                        out.write('\t*MORPH_DATA {')
                        for key in ob.data.shape_keys.key_blocks:
                            if key.relative_key != key:
                                out.write(f'\n\t*MORPH_FRAMES "%s" %u {{\n' % (key.name.replace(' ', '_'), FRAMES_COUNT))

                                for f in range(START_FRAME, END_FRAME + 1):
                                    bpy.context.scene.frame_set(f)
                                    out.write(f'\t\t\t%u {df}\n' % (f, key.value))

                                out.write('\t\t}\n') # MORPH_FRAMES
                        out.write('\t}') # MORPH_DATA

                    #-------------------------------------------------------------------------------------------------------------------------------
                    #  SKELETAL RIGGING / BONE HIERARCHY DEFINITION / ARMATURE
                    #-------------------------------------------------------------------------------------------------------------------------------
                    for indx, mod in enumerate(ob.modifiers):
                        # swy: find the armature element between the possible mesh modifiers
                        if mod.type == 'ARMATURE' and mod.object and mod.object.type == 'ARMATURE':
                            armat = mod.object
                            out.write('\t*SKIN_DATA {\n')
                            out.write('\t\t*BONE_LIST {\n')

                            # create a skeletal lookup list for bone names
                            bone_names = [bone.name for bone in armat.data.bones]

                            for bidx, bone in enumerate(armat.data.bones):
                                out.write('\t\t\n*BONE %u "%s"\n' % (bidx, bone.name))
                            out.write('\t\t}') # BONE_LIST

                            # create a vertex group lookup list for names
                            # https://blender.stackexchange.com/a/28273/42781
                            vgroup_names = [vgroup.name for vgroup in ob.vertex_groups]

                            out.write('\t\t*SKIN_VERTEX_DATA {\n')
                            for vidx, vert in enumerate(me.vertices):
                                out.write('\t\t\n*VERTEX %5u %u' % (vidx, len(vert.groups)))

                                # swy: make it so that the bones that have more influence appear first
                                #      in the listing, otherwise order seems random.
                                sorted_groups = sorted(vert.groups, key = lambda i: i.weight, reverse = True)

                                for gidx, group in enumerate(sorted_groups):
                                    # swy: get the actual vertex group name from the local index (the .group thing)
                                    cur_vgroup_name = vgroup_names[group.group]
                                    # swy: and test it to see if it matches a bone name from the bound armature/skeleton
                                    #      otherwise it probably isn't a weighting group and is used for something else
                                    if cur_vgroup_name not in bone_names:
                                        continue

                                    # swy: because the bone names are in the same order as in the BONE_LIST above everything works out
                                    global_bone_index = bone_names.index(cur_vgroup_name)
                                    out.write(f'  %2u {df}' % (global_bone_index, group.weight))
                                out.write("\n")

                            out.write('\t\t}') # SKIN_VERTEX_DATA
                            out.write('\t}') # SKIN_DATA

                            # swy: we only support one armature modifier/binding per mesh for now, stop looking for more
                            break

                    out.write("}\n") # GEOMOBJECT

                    # swy: here goes the changed geometry/vertex positions for each of the shape keys, globally.
                    #      they are referenced by name.
                    if ob.data.shape_keys:
                        for key in ob.data.shape_keys.key_blocks:
                            # swy: don't export the 'Basis' one that is just the normal mesh data other keys are relative/substracted to
                            if key.relative_key != key:
                                out.write('*MORPH_LIST {\n')
                                out.write('\t*MORPH_TARGET "%s" %u {\n' % (key.name.replace(' ', '_'), len(key.data)))

                                for vidx, vert in enumerate(key.data):
                                    out.write('\t\t\t{df}\t{df}\t{df}\n' % (vert.co.x, vert.co.y, vert.co.z))

                                out.write('\t}\n') # MORPH_TARGET
                                out.write('}\n') # MORPH_LIST

                # clean up
                ob_for_convert.to_mesh_clear()

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_biped_bones(out, scene, depsgraph):
        for ob_main in scene.objects:
            # Check if the object is a bone source
            if ob_main.type != 'ARMATURE':
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
                    # Extract the bone data
                    bone_data = ob_for_convert.data
                except AttributeError:
                    bone_data = None

                if bone_data is None:
                    continue
                
                # Apply transformation matrix to light object
                obj_matrix_data = {
                    "name" : ob_main.name,
                    "type" : ob_main.type,
                    "matrix_original" : ob_mat.copy(),
                    "matrix_transformed": ob_mat.copy()
                }
                
                for bidx, bone in enumerate(bone_data.bones):
                    out.write('*BONEOBJECT {\n')
                    out.write('*NODE_NAME "%s"\n' % bone.name)
                    out.write('*NODE_BIPED_BODY\n')
                    if (bone.parent):
                        out.write('*NODE_PARENT "%s"\n' % bone.parent.name)
                    out.write('}') # BONEOBJECT

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
                obj_matrix_data = {
                    "name" : ob_main.name,
                    "type" : ob_main.type,
                    "matrix_original" : ob_mat.copy(),
                    "matrix_transformed": ob_mat.copy()
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
                write_tm_node(out, obj_matrix_data)

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

                write_light_settings(out, light_data, EXPORT_STATIC_FRAME)

                #---------------------------------------------[Light Animation]---------------------------------------------
                if EXPORT_CAMERA_LIGHT_ANIMS:
                    out.write('\t*LIGHT_ANIMATION {\n')
                    previous_light_data = None
                    frameIndex = 0

                    for frame in range(START_FRAME, END_FRAME + 1):
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
                            write_light_settings(out, light_data, frameIndex, 2)

                            # Actualizamos los datos anteriores con los datos actuales
                            previous_light_data = light_data
                            frameIndex += TICKS_PER_FRAME
                    out.write('\t}\n')
                    write_animation_node(out, ob_main, obj_matrix_data)
                out.write("}\n")

    #-------------------------------------------------------------------------------------------------------------------------------
    def userWantsCameraScript(scene):
        printScript = False
        
        if "cameraScriptEditor" in scene.keys():
            camera_script_value = scene["cameraScriptEditor"]
        
            # Comprueba si el valor es mayor a 0
            if isinstance(camera_script_value, (int, float)) and camera_script_value > 0:
                printScript = True
        return printScript

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_script_camera(out):
        markers = [m for m in bpy.context.scene.timeline_markers if m.camera is not None]
        num_cameras = len(markers)

        out.write('\t*USER_DATA %u {\n' % 0)
        out.write('\t\tCameraScript = %u\n' % 1)
        out.write('\t\tCameraScript_numCameras = %u\n' % num_cameras)
        out.write('\t\tCameraScript_globalOffset = %u\n' % 0)

        # Recorrer los marcadores y generar la información requerida
        for idx, marker in enumerate(markers, start=1):
            name = marker.name
            position = marker.frame  # Keyframe del marcador
            camera = marker.camera

            # Obtener el primer y último keyframe de la cámara asociada
            if camera.animation_data and camera.animation_data.action:
                fcurves = camera.animation_data.action.fcurves
                keyframes = sorted(set(kp.co[0] for fc in fcurves for kp in fc.keyframe_points))
                first_keyframe = int(keyframes[0]) if keyframes else position
                last_keyframe = int(keyframes[-1]) if keyframes else position
                timeline_frame = position + (last_keyframe - first_keyframe)

                # Imprimir la información en el formato requerido
                out.write('\t\tCameraScript_camera%u = %s %u %u %u %u\n' % (idx, name, first_keyframe, last_keyframe, position, timeline_frame))
        out.write('\t}\n')

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_camera_settings(out, camera_object, camera_data, current_frame, tab_level = 1):
        tab = get_tabs(tab_level)

        out.write(f'{tab}*CAMERA_SETTINGS {{\n')
        out.write(f'{tab}\t*TIMEVALUE %u\n' % current_frame)
        out.write(f'{tab}\t*CAMERA_NEAR %d\n' % (camera_object.clip_start))
        out.write(f'{tab}\t*CAMERA_FAR %d\n' % (camera_object.clip_end))
        out.write(f'{tab}\t*CAMERA_FOV {df}\n' % (camera_object.angle))
        #out.write(f'{tab}\t*CAMERA_TDIST {df}\n' % (camera_data.location.length))
        out.write(f'{tab}}}\n')

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_camera_data(out, scene, depsgraph):
        global FRAMES_COUNT

        CamerasList = sorted([obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA'], key=lambda obj: obj.name)

        for ob_main in CamerasList:
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
                            
                # Apply transformation matrix to camera object
                obj_matrix_data = {
                    "name" : ob.name,
                    "type" : ob_main.type,
                    "matrix_original" : ob_mat.copy(),
                    "matrix_transformed": ob_mat.copy()
                }
        
            # Imprime el bloque con las propiedades de la cámara
            out.write("*CAMERAOBJECT {\n")
            out.write('\t*NODE_NAME "%s"\n' % ob.name)
            out.write('\t*CAMERA_TYPE %s\n' % "target")
            write_tm_node(out, obj_matrix_data)
            write_camera_settings(out, camera_data, ob, EXPORT_STATIC_FRAME)

            #---------------------------------------------[Camera Animation]---------------------------------------------
            if EXPORT_CAMERA_LIGHT_ANIMS:
                out.write('\t*CAMERA_ANIMATION {\n')
                previous_camera_data = None
                frameIndex = 0
                
                for frame in range(START_FRAME, END_FRAME + 1):
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

                        # Si hay alguna propiedad diferente, escribimos la configuración de la cámara
                        write_camera_settings(out, camera_data, ob, frameIndex, 2)

                        # Actualizamos los datos anteriores con los datos actuales
                        previous_camera_data = camera_data
                        frameIndex += TICKS_PER_FRAME
                out.write('\t}\n')
                write_animation_node(out, ob_main, obj_matrix_data)
                
                
            #-------------------------------------------------------------------------------------------------------------------------------
            # swy: Jmarti856 found that this is needed for the time range of each camera to show up properly in
            #      the script timeline, without this all of them cover the entire thing from beginning to end
            #-------------------------------------------------------------------------------------------------------------------------------
            if ob_main == CamerasList[-1]:
                if userWantsCameraScript(scene):
                        write_script_camera(out)            
            out.write("}\n")

    #-------------------------------------------------------------------------------------------------------------------------------
    def write_ese_file():
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
            
            scene_materials={}
            if EXPORT_MATERIALS:
                scene_materials = write_scene_materials(out)

            if 'MESH' in EXPORT_OBJECTS:
                write_mesh_data(out, scene, depsgraph, scene_materials)
            if 'CAMERA' in EXPORT_OBJECTS:
                write_camera_data(out, scene, depsgraph)
            if 'LIGHT' in EXPORT_OBJECTS:
                write_light_data(out, scene, depsgraph)
            if 'ARMATURE' in EXPORT_OBJECTS:
                write_biped_bones(out, scene, depsgraph)
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
         Output_First_Only):

    _write(context, filepath,
           EXPORT_MESH_FLAGS=Output_Mesh_Definition,
           EXPORT_MATERIALS=Output_Materials,
           EXPORT_MESH_ANIMS=Output_Mesh_Anims, 
           EXPORT_CAMERA_LIGHT_ANIMS=Output_CameraLightAnims, 
           TRANSFORM_TO_CENTER = Transform_Center,
           EXPORT_OBJECTS=Object_Types,
           EXPORT_MESH_NORMALS=Output_Mesh_Normals,
           EXPORT_MESH_UV=Output_Mesh_UV,
           EXPORT_MESH_VCOLORS = Output_Mesh_Vertex_Colors,
           EXPORT_MESH_MORPH=Output_Mesh_Morph,
           EXPORT_STATIC_FRAME = Static_Frame,
           DECIMAL_PRECISION=Decimal_Precision,
           GLOBAL_SCALE=Output_Scale,
           EXPORT_FROM_FRAME_ENABLED = Enable_Start_From_Frame,
           EXPORT_FROM_FRAME = Start_From_Frame,
           EXPORT_END_FRAME_ENABLED = Enable_End_With_Frame,
           EXPORT_END_FRAME = End_With_Frame,
           EXPORT_ONLY_FIRST_FRAME = Output_First_Only)

    return {'FINISHED'}
if __name__ == '__main__':
    save({}, str(Path.home()) + '/Desktop/EurocomEIF.eif')
