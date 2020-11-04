import bpy
import os
import math
import datetime
import bmesh
from mathutils import *
from math import *
from pathlib import Path
from bpy_extras.io_utils import axis_conversion
from bpy import context
from pprint import pprint
from decimal import Decimal
from mathutils import Euler

def save(context,
         filepath,
         *,
         use_triangles=False,
         use_edges=True,
         use_normals=False,
         use_smooth_groups=False,
         use_smooth_groups_bitflags=False,
         use_uvs=True,
         use_materials=True,
         use_mesh_modifiers=True,
         use_mesh_modifiers_render=False,
         use_blen_objects=True,
         group_by_object=False,
         group_by_material=False,
         keep_vertex_order=False,
         use_vertex_groups=False,
         use_nurbs=True,
         use_selection=True,
         use_animation=False,
         global_matrix=None,
         path_mode='AUTO'
         ):

    #Open writer
    out = open(filepath, 'w')

    print('[i] exporting', filepath)

    #Get scene info
    scn = bpy.context.scene
    ow  = out.write
    Materials_Dict = dict()
    
    # Axis Conversion
    global_matrix = axis_conversion(to_forward='Y',to_up='Z').to_4x4()
    
#*===============================================================================================
#*	Get data lists from the object
#*===============================================================================================
    def GetVertexList(me):
        VertexList = []

        for vertex in me.vertices:
            VertexList.append('%.6f,%.6f,%.6f' % (vertex.co.x,vertex.co.y,vertex.co.z))
        return VertexList

    def GetUVList(me):
        UVList = []

        if hasattr(me.uv_layers.active, 'data'):
            if len(me.uv_layers):
                for layer in me.uv_layers:
                    uv_layer = layer.data
                    for pl_count, poly in enumerate(me.polygons):
                        for li_count, loop_index in enumerate(poly.loop_indices):
                            UVList.append('%.6f,%.6f' % (uv_layer[loop_index].uv.x,1.0-uv_layer[loop_index].uv.y))
                UVList = list(dict.fromkeys(UVList))
        return UVList

    def GetVertexColorList(me):
        VertColList = []

        if len(me.vertex_colors):
            if hasattr(me.vertex_colors.active, 'data'):
                for layer in me.vertex_colors:
                    for vertex in layer.data:
                        VertColList.append('%.6f,%.6f,%.6f,%.6f' % (vertex.color[0],vertex.color[1],vertex.color[2],vertex.color[3]))
                    VertColList = list(dict.fromkeys(VertColList))
        return VertColList

    def GetMaterialIndex(MaterialName):
        for index, material in Materials_Dict.items():
            if material == MaterialName:
                return index
                
    def SearchMaterialIndex(mat):
        if hasattr(mat.material.node_tree, 'nodes'):
            ImageNode = mat.material.node_tree.nodes.get('Image Texture', None)
            if (ImageNode is not None):
                ImageName = ImageNode.image.name
                MaterialIndex = GetMaterialIndex(os.path.splitext(ImageName)[0])
            else:
                DiffuseColor = mat.material.diffuse_color
                MaterialIndex = GetMaterialIndex(DiffuseColor[0]+DiffuseColor[1]+DiffuseColor[2])
            return MaterialIndex
            
    def MirrorVertices(ob):
        for vertex in ob.data.vertices:
            vertex.co.x = vertex.co.x * -1.0
        
#*===============================================================================================
#*	Get materials and write data
#*===============================================================================================
    def GetMaterials():
        MaterialIndex = 0

        ow('*MATERIALS {\n')
        for mat in bpy.data.materials:
            DiffuseColor = mat.diffuse_color

            #Check if material has texture
            if hasattr(mat.node_tree, 'nodes'):
                ImageNode = mat.node_tree.nodes.get('Image Texture', None)
                if (ImageNode is not None):
                    ImageName = ImageNode.image.name

                    if os.path.splitext(ImageName)[0] not in Materials_Dict.values():
                        ow('  *MATERIAL %d {\n' % (MaterialIndex))
                        ow('    *NAME \"%s\"\n' % (os.path.splitext(ImageName)[0]))
                        ow('    *COL_DIFFUSE %.6f %.6f %.6f\n' % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))

                        #Check if the texture exists
                        if (os.path.exists(bpy.path.abspath(ImageNode.image.filepath))):
                            ow('    *MAP_DIFFUSE \"%s\"\n' % (bpy.path.abspath(ImageNode.image.filepath)))
                            ow('    *TWOSIDED\n')
                        ow('    *MAP_DIFFUSE_AMOUNT 1.0\n')
                        
                        #Check if use Alpha (as a comment)
                        if mat.blend_method.startswith('ALPHA'):
                            ow('    *MAP_HASALPHA\n')
                        
                        #Add data to dictionary
                        Materials_Dict[MaterialIndex] = os.path.splitext(ImageName)[0]
                        MaterialIndex +=1

                        #Add 1 to the materials index
                        ow('  }\n')

                #Material has no texture
                else:
                    Color = DiffuseColor[0] + DiffuseColor[1] + DiffuseColor[2]
                    if Color not in Materials_Dict.values():
                        ow('  *MATERIAL %d {\n' % (MaterialIndex))
                        ow('    *NAME \"%s\"\n' % (mat.name))
                        ow('    *COL_DIFFUSE %.6f %.6f %.6f\n' % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))

                        #Add data to dictionary
                        Materials_Dict[MaterialIndex] = DiffuseColor[0]+DiffuseColor[1]+DiffuseColor[2]
                        MaterialIndex +=1

                        #Add 1 to the materials index
                        ow('  }\n')
        ow('}\n\n')
        print('Dictionary Length: %d' % len(Materials_Dict))

#*===============================================================================================
#*	Write object data to the file
#*===============================================================================================
    def GetMesh():
        for obj in scn.objects:
            #Duplicate object
            ob = obj.copy()
            ob.data = obj.data.copy()
            
            #Export clon
            if ob.hide_viewport:
                continue
            if ob.type == 'MESH':
                
                #Apply Axis conversion
                if global_matrix is not None:
                    ob.data.transform(global_matrix)
                    ob.rotation_euler = Euler((0.3, 0.4, 0.0), 'XZY')
                    
                #Mirror Vertices
                MirrorVertices(ob)
                
                if hasattr(ob, 'data'):            
                    me = ob.data
            
                    VertexList = GetVertexList(ob.data)
                    UVList = GetUVList(ob.data)
                    VertColList = GetVertexColorList(ob.data)
                    NumFaceLayers = len(me.uv_layers)
                    MatSlots = ob.material_slots
                    FaceFormat = 'V'

                    #==================PRINT DATA==============================
                    ow('*MESH {\n')
                    ow('	*NAME "%s" \n' % (ob.name))
                    ow('	*VERTCOUNT    %3d\n' % (len(VertexList)))
                    ow('	*UVCOUNT      %3d\n' % (len(UVList)))
                    ow('	*VERTCOLCOUNT %3d\n' % (len(VertColList)))
                    ow('	*FACECOUNT    %3d\n' % (len(me.polygons)))
                    ow('	*TRIFACECOUNT %3d\n' % (sum(len(p.vertices) - 2 for p in me.polygons)))

                    if NumFaceLayers > 0:
                        ow('	*FACELAYERSCOUNT %d\n' % (NumFaceLayers))
                    else:
                        ow('	*FACELAYERSCOUNT %d\n' % (NumFaceLayers + 1))

                    #Check if there are more than one layer
                    if (len(me.uv_layers) > 1):
                        ow('	*FACESHADERCOUNT %d\n' % len(MatSlots))

                    #Print Vertex data
                    ow('	*VERTEX_LIST {\n')
                    for list_item in VertexList:
                        dataSplit = list_item.split(',')
                        ow('		%s %s %s\n' % (dataSplit[0], dataSplit[1], dataSplit[2]))
                    ow('	}\n')

                    #Print UV data
                    ow('	*UV_LIST {\n')
                    if (len(UVList) > 0):
                        FaceFormat += 'T'
                        for list_item in UVList:
                            dataSplit = list_item.split(',')
                            ow('		%s %s\n' % (dataSplit[0], dataSplit[1]))
                    ow('	}\n')

                    #Check if the vertex colors layer is active
                    ow('	*VERTCOL_LIST {\n')
                    if(len(VertColList) > 0):
                        FaceFormat +='C'
                        for list_item in VertColList:
                            dataSplit = list_item.split(',')
                            ow('		%s %s %s %s\n' % (dataSplit[0], dataSplit[1], dataSplit[2], dataSplit[3]))
                    ow('	}\n')

                    if len(MatSlots) > 0:
                        FaceFormat +='M'
                        
                    #Flags
                    if len(MatSlots) > 0:
                        FaceFormat +='F'
                        
                    #Print Shader faces
                    if (len(me.uv_layers) > 1):
                        ShaderIndex = 0
                        MaterialIndex = 0
                        ow('	*FACESHADERS {\n')
                        for mat in MatSlots:
                            ow('		*SHADER %d {\n' % ShaderIndex)                           
                            if mat.material.blend_method == 'OPAQUE':                               
                                ow('			%d	%s\n' % (SearchMaterialIndex(mat),"Non"))
                                ow('		}\n')
                            else:
                                ow('			%d	%s\n' % (SearchMaterialIndex(mat),"Alp"))
                                ow('		}\n')
                            MaterialIndex +=1
                        ow('	}\n')

                    #Get FaceFormat
                    ow('	*FACEFORMAT %s\n' % FaceFormat)

                    #Print Face list
                    ow('	*FACE_LIST {\n')
                    for poly in me.polygons:
                        #Get polygon vertices
                        PolygonVertices = poly.vertices

                        #Write vertices ---V
                        ow('		%d ' % (len(PolygonVertices)))
                        for vert in PolygonVertices:
                            ow('%d ' % vert)

                        #Write UVs ---T
                        if ('T' in FaceFormat):
                            for vert_idx, loop_idx in enumerate(poly.loop_indices):
                                for layer in me.uv_layers:
                                    uv_coords = layer.data[loop_idx].uv
                                    ow('%d ' % UVList.index('%.6f,%.6f' % (uv_coords.x, 1.0-float(uv_coords.y))))

                        #Write Colors ---C
                        if ('C' in FaceFormat):
                            for color_idx, loop_idx in enumerate(poly.loop_indices):
                                for layerIndex in me.vertex_colors:
                                    vertex = layerIndex.data[loop_idx]
                                    ow('%d ' % VertColList.index('%.6f,%.6f,%.6f,%.6f' % (vertex.color[0],vertex.color[1],vertex.color[2],vertex.color[3])))
                        
                        #Write Material Index ---M
                        if ('M' in FaceFormat):
                            ow('%d ' % SearchMaterialIndex(MatSlots[poly.material_index]))
                            
                        #Write Flags ---F
                        if ('F' in FaceFormat):
                            if MatSlots[poly.material_index].material.use_backface_culling == False:
                                ow('%d ' % 65536)
                            else:
                                ow('%d ' % 00000)
                        ow('\n')
                    ow('	}\n')

                #Close Tag
                ow('}\n')
                
                #Write GeomNode
                GetGeomNode(ob)

                #Write PlaceNode
                GetPlaceNode(ob)
                
            bpy.data.objects.remove(ob, do_unlink=True)

#*===============================================================================================
#*	Get GeomNode of each object
#*===============================================================================================
    def GetGeomNode(ob):
        ow('*GEOMNODE {\n')
        ow('	*NAME "%s" \n' % (ob.name))
        ow('	*MESH "%s" \n' % (ob.name))
        ow('	*WORLD_TM {\n')
        ow('		*TMROW0 1.000000 0.000000 0.000000 0.000000\n')
        ow('		*TMROW1 0.000000 1.000000 0.000000 0.000000\n')
        ow('		*TMROW2 0.000000 0.000000 1.000000 0.000000\n')
        ow('		*TMROW3 0.000000 0.000000 0.000000 1.000000\n')
        ow('		*POS 0.000000 0.000000 0.000000\n')
        ow('		*ROT -0.000000 0.000000 0.000000\n')
        ow('		*SCL 1.000000 1.000000 1.000000\n')
        ow('	}\n')
        #ow('	*USER_FLAGS_COUNT 1\n')
        #ow('	*USER_FLAGS {\n')
        #ow('		*SET 0 %s\n' % ('0x00004000'))
        #ow('	}\n')
        ow('}\n')

#*===============================================================================================
#*	Get Place node of each object
#*===============================================================================================
    def GetPlaceNode(ob):
        ow('*PLACENODE {\n')
        ow('	*NAME "%s" \n' % (ob.name))
        ow('	*MESH "%s" \n' % (ob.name))
        ow('	*WORLD_TM {\n')
        RotationMatrix = ob.matrix_world
        ow('		*TMROW0 %.6f %.6f %.6f 0.0\n' % (RotationMatrix[0].x,RotationMatrix[0].y,RotationMatrix[0].z))
        ow('		*TMROW1 %.6f %.6f %.6f 0.0\n' % (RotationMatrix[1].x,RotationMatrix[1].y,RotationMatrix[1].z))
        ow('		*TMROW2 %.6f %.6f %.6f 0.0\n' % (RotationMatrix[2].x,RotationMatrix[2].y,RotationMatrix[2].z))
        ow('		*TMROW3 %.6f %.6f %.6f 1.0\n' % (RotationMatrix[0].w,RotationMatrix[1].w,RotationMatrix[2].w))
        ow('		*POS    %.6f %.6f %.6f\n' % (ob.location.x, ob.location.y, ob.location.z))
        ow('		*ROT    %.6f %.6f %.6f\n' % (radians(ob.rotation_euler.x), radians(ob.rotation_euler.y), radians(ob.rotation_euler.z)))
        ow('		*SCL    %.6f %.6f %.6f\n' % (ob.scale.x, ob.scale.y, ob.scale.z))
        ow('	}\n')
        ow('}\n')

#*===============================================================================================
#*	Write file header
#*===============================================================================================
    # Stop edit mode
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
     
    bpy.context.scene.world.light_settings.use_ambient_occlusion = True

    #Script header
    time_now = datetime.datetime.now()
    ow('*EUROCOM_INTERCHANGE_FILE 100\n')
    ow('*COMMENT Eurocom Interchange File Version 1.00 %s\n\n' % time_now.strftime('%A %B %d %Y %H:%M'))

    #print scene info
    ow('*SCENE {\n')
    ow('	*FILENAME  "%s"\n' % (bpy.data.filepath))
    ow('	*FIRSTFRAME  %3d\n' % (scn.frame_start))
    ow('	*LASTFRAME   %3d\n' % (scn.frame_end  ))
    ow('	*FRAMESPEED  %3d\n' % (scn.render.fps ))
    ow('	*STATICFRAME %3d\n' % (scn.frame_current))
    AmbientValue = bpy.context.scene.world.light_settings.ao_factor
    ow('	*AMBIENTSTATIC %.6f %.6f %.6f\n' %(AmbientValue, AmbientValue, AmbientValue))
    ow('}\n\n')

    #Write materials
    GetMaterials()

    #Write Meshes
    GetMesh()

    #Close writer
    out.close()
    print('[i] done')

    return {'FINISHED'}


if __name__ == '__main__':
    save({}, str(Path.home()) + '/Desktop/testEIF_d.eif')