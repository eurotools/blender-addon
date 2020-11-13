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

    with open(filepath, 'w') as out:
        ow = out.write
        
        # swy: add a macro to write a whole line, carriage return included
        def wl(line):
            ow(line + '\n')

        print('[i] exporting', filepath)
        
        #*===============================================================================================
        #* Write file header
        #*===============================================================================================
        
        # Stop edit mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.context.scene.world.light_settings.use_ambient_occlusion = True
        
        # Get scene info
        scn = bpy.context.scene

        # Script header
        wl('*EUROCOM_INTERCHANGE_FILE 100')
        wl('*COMMENT Eurocom Interchange File Version 1.00 %s' % (datetime.datetime.utcnow()).strftime('%A %B %d %Y %H:%M'))
        wl('')
        # print scene info
        wl('*SCENE {')
        wl('  *FILENAME   "%s"' % (bpy.data.filepath))
        wl('  *FIRSTFRAME  %3d' % (scn.frame_start  ))
        wl('  *LASTFRAME   %3d' % (scn.frame_end    ))
        wl('  *FRAMESPEED  %3d' % (scn.render.fps   ))
        wl('  *STATICFRAME %3d' % (scn.frame_current))
        AmbientValue = bpy.context.scene.world.light_settings.ao_factor
        wl('  *AMBIENTSTATIC %.6f %.6f %.6f' %(AmbientValue, AmbientValue, AmbientValue))
        wl('}') 
        wl('')
        
        Materials_Dict = dict()

        # Axis Conversion
        global_matrix = axis_conversion(to_forward='Y', to_up='Z').to_4x4()

    #*===============================================================================================
    #* Get data lists from the object
    #*===============================================================================================
        def GetVertexList(me):
            VertexList = []

            for vertex in me.vertices:
                VertexList.append(
                    (vertex.co.x, vertex.co.y, vertex.co.z)
                )
            return VertexList

        def GetUVList(me):
            UVList = []

            if hasattr(me.uv_layers.active, 'data'):
                if len(me.uv_layers):
                    for layer in me.uv_layers:
                        uv_layer = layer.data
                        for pl_count, poly in enumerate(me.polygons):
                            for li_count, loop_index in enumerate(poly.loop_indices):
                                UVList.append(
                                    (uv_layer[loop_index].uv.x, 1.0 - uv_layer[loop_index].uv.y)
                                )
                    UVList = list(dict.fromkeys(UVList))
            return UVList

        def GetVertexColorList(me):
            VertColList = []

            if len(me.vertex_colors):
                if hasattr(me.vertex_colors.active, 'data'):
                    for layer in me.vertex_colors:
                        for vertex in layer.data:
                            VertColList.append(
                                (vertex.color[0] * .5, vertex.color[1] * .5, vertex.color[2] * .5, vertex.color[3])
                            )
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

    #*===============================================================================================
    #* Get materials and write data
    #*===============================================================================================
        def GetMaterials():
            MaterialIndex = 0

            wl('*MATERIALS {')
            for mat in bpy.data.materials:
                DiffuseColor = mat.diffuse_color

                #Check if material has texture
                if hasattr(mat.node_tree, 'nodes'):
                    ImageNode = mat.node_tree.nodes.get('Image Texture', None)
                    if (ImageNode is not None):
                        ImageName = ImageNode.image.name

                        if os.path.splitext(ImageName)[0] not in Materials_Dict.values():
                            wl('  *MATERIAL %d {' % (MaterialIndex))
                            wl('    *NAME "%s"' % (os.path.splitext(ImageName)[0]))
                            wl('    *COL_DIFFUSE %.6f %.6f %.6f' % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))

                            #Check if the texture exists
                            if (os.path.exists(bpy.path.abspath(ImageNode.image.filepath))):
                                wl('    *MAP_DIFFUSE "%s"' % (bpy.path.abspath(ImageNode.image.filepath)))
                                wl('    *TWOSIDED')
                            wl('    *MAP_DIFFUSE_AMOUNT 1.0')

                            #Check if use Alpha (as a comment)
                            if mat.blend_method.startswith('ALPHA'):
                                wl('    *MAP_HASALPHA')

                            #Add data to dictionary
                            Materials_Dict[MaterialIndex] = os.path.splitext(ImageName)[0]
                            MaterialIndex +=1

                            #Add 1 to the materials index
                            wl('  }')

                    #Material has no texture
                    else:
                        Color = DiffuseColor[0] + DiffuseColor[1] + DiffuseColor[2]
                        if Color not in Materials_Dict.values():
                            wl('  *MATERIAL %d {' % (MaterialIndex))
                            wl('    *NAME \"%s\"' % (mat.name))
                            wl('    *COL_DIFFUSE %.6f %.6f %.6f' % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))

                            #Add data to dictionary
                            Materials_Dict[MaterialIndex] = DiffuseColor[0]+DiffuseColor[1]+DiffuseColor[2]
                            MaterialIndex +=1

                            #Add 1 to the materials index
                            wl('  }')
            wl('}')
            wl('')
            print('Dictionary Length: %d' % len(Materials_Dict))

    #*===============================================================================================
    #* Write object data to the file
    #*===============================================================================================
        def GetMesh():
            for obj in scn.objects:
                #Duplicate object
                ob = obj.copy()
                ob.data = obj.data.copy()

                # export cloned object
                if ob.hide_viewport:
                    continue

                if ob.type == 'MESH':

                    #Apply Axis conversion
                    if global_matrix is not None:
                        ob.data.transform(global_matrix)
                        ob.rotation_euler = Euler((0.3, 0.4, 0.0), 'XZY')

                    if hasattr(ob, 'data'):
                        me = ob.data

                        VertexList = GetVertexList(ob.data)
                        UVList = GetUVList(ob.data)
                        VertColList = GetVertexColorList(ob.data)
                        NumFaceLayers = len(me.uv_layers)
                        MatSlots = ob.material_slots
                        FaceFormat = 'V'

                        #==================PRINT DATA==============================
                        wl('*MESH {')
                        wl('  *NAME "%s"' % (ob.name))
                        wl('  *VERTCOUNT    %3d' % (len(VertexList)))
                        wl('  *UVCOUNT      %3d' % (len(UVList)))
                        wl('  *VERTCOLCOUNT %3d' % (len(VertColList)))
                        wl('  *FACECOUNT    %3d' % (len(me.polygons)))
                        wl('  *TRIFACECOUNT %3d' % (sum(len(p.vertices) - 2 for p in me.polygons)))

                        if NumFaceLayers > 0:
                            wl('  *FACELAYERSCOUNT %d' % (NumFaceLayers))
                        else:
                            wl('  *FACELAYERSCOUNT %d' % (NumFaceLayers + 1))

                        #Check if there are more than one layer
                        if (len(me.uv_layers) > 1):
                            wl('  *FACESHADERCOUNT %d' % len(MatSlots))

                        #Print Vertex data
                        wl('  *VERTEX_LIST {')
                        for vtx in VertexList:
                            wl('    %.6f %.6f %.6f' % (vtx[0], vtx[1], vtx[2]))
                        wl('  }')

                        #Print UV data
                        wl('  *UV_LIST {')
                        if (len(UVList) > 0):
                            FaceFormat += 'T'
                            for uv in UVList:
                                wl('    %.6f %.6f' % (uv[0], uv[1]))
                        wl('  }')

                        #Check if the vertex colors layer is active
                        wl('  *VERTCOL_LIST {')
                        if(len(VertColList) > 0):
                            FaceFormat += 'C'
                            for col in VertColList:
                                wl('    %.6f %.6f %.6f %.6f' % (col[0], col[1], col[2], col[3]))
                        wl('  }')

                        if len(MatSlots) > 0:
                            FaceFormat += 'M'

                        #Flags
                        if len(MatSlots) > 0:
                            FaceFormat += 'F'

                        #Print Shader faces
                        if (len(me.uv_layers) > 1):
                            ShaderIndex = 0
                            MaterialIndex = 0
                            wl(' *FACESHADERS {')
                            for mat in MatSlots:
                                wl('  *SHADER %d {' % ShaderIndex)
                                if mat.material.blend_method == 'OPAQUE':
                                    wl('   %d %s' % (SearchMaterialIndex(mat),"Non"))
                                    wl('  }')
                                else:
                                    wl('   %d %s' % (SearchMaterialIndex(mat),"Alp"))
                                    wl('  }')
                                MaterialIndex +=1
                            wl(' }')

                        #Get FaceFormat
                        wl(' *FACEFORMAT %s' % FaceFormat)

                        #Print Face list
                        wl(' *FACE_LIST {')
                        for poly in me.polygons:
                            #Get polygon vertices
                            PolygonVertices = poly.vertices

                            #Write vertices ---V
                            ow('    %d ' % (len(PolygonVertices)))
                            for vert in PolygonVertices:
                                ow('%d ' % vert)

                            #Write UVs ---T
                            if ('T' in FaceFormat):
                                for vert_idx, loop_idx in enumerate(poly.loop_indices):
                                    for layer in me.uv_layers:
                                        uv_coords = layer.data[loop_idx].uv
                                        ow('%d ' % UVList.index((uv_coords.x, 1.0 - float(uv_coords.y))))

                            #Write Colors ---C
                            if ('C' in FaceFormat):
                                for color_idx, loop_idx in enumerate(poly.loop_indices):
                                    for layerIndex in me.vertex_colors:
                                        vertex = layerIndex.data[loop_idx]
                                        ow('%d ' % VertColList.index((vertex.color[0] * .5, vertex.color[1] * .5, vertex.color[2] * .5, vertex.color[3])))

                            #Write Material Index ---M
                            if ('M' in FaceFormat):
                                ow('%d ' % SearchMaterialIndex(MatSlots[poly.material_index]))

                            #Write Flags ---F
                            if ('F' in FaceFormat):
                                flags = 0
                                
                                if MatSlots[poly.material_index].material.use_backface_culling:
                                    flags |= 1 << 16
   
                                ow('%d ' % flags)
                            ow('\n')
                        wl(' }')

                    #Close Tag
                    wl('}')

                    #Write GeomNode
                    GetGeomNode(ob)

                    #Write PlaceNode
                    GetPlaceNode(ob)

                bpy.data.objects.remove(ob, do_unlink=True)

    #*===============================================================================================
    #* Get GeomNode of each object
    #*===============================================================================================
        def GetGeomNode(ob):
            wl('*GEOMNODE {')
            wl('  *NAME "%s"' % (ob.name))
            wl('  *MESH "%s"' % (ob.name))
            wl('  *WORLD_TM {')
            wl('    *TMROW0 1 0 0 0')
            wl('    *TMROW1 0 1 0 0')
            wl('    *TMROW2 0 0 1 0')
            wl('    *TMROW3 0 0 0 1')
            wl('    *POS    0 0 0')
            wl('    *ROT   -0 0 0')
            wl('    *SCL    1 1 1')
            wl('  }')
            wl('}')

    #*===============================================================================================
    #* Get Place node of each object
    #*===============================================================================================
        def GetPlaceNode(ob):
            wl('*PLACENODE {')
            wl('  *NAME "%s"' % (ob.name))
            wl('  *MESH "%s"' % (ob.name))
            wl('  *WORLD_TM {')
            RotationMatrix = ob.matrix_world
            wl('    *TMROW0 %.6f %.6f %.6f 0' % (RotationMatrix[0].x,RotationMatrix[0].y,RotationMatrix[0].z))
            wl('    *TMROW1 %.6f %.6f %.6f 0' % (RotationMatrix[1].x,RotationMatrix[1].y,RotationMatrix[1].z))
            wl('    *TMROW2 %.6f %.6f %.6f 0' % (RotationMatrix[2].x,RotationMatrix[2].y,RotationMatrix[2].z))
            wl('    *TMROW3 %.6f %.6f %.6f 1' % (RotationMatrix[0].w,RotationMatrix[1].w,RotationMatrix[2].w))
            # swy: these aren't actually used or read by this version of the importer
            wl('    *POS    %.6f %.6f %.6f'   % (ob.location.x, ob.location.y, ob.location.z))
            wl('    *ROT    %.6f %.6f %.6f'   % (radians(ob.rotation_euler.x), radians(ob.rotation_euler.y), radians(ob.rotation_euler.z)))
            wl('    *SCL    %.6f %.6f %.6f'   % (ob.scale.x, ob.scale.y, ob.scale.z))
            wl(' }')
            wl('}')
        
        #Write materials
        GetMaterials()

        #Write Meshes
        GetMesh()

        #Close writer
        print('[i] done')

    return {'FINISHED'}


if __name__ == '__main__':
    save({}, str(Path.home()) + '/Desktop/testEIF_d.eif')