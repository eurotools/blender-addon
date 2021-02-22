"""
Name: 'Eurocom Interchange File'
Blender: 2.90.1
Group: 'Export'
Tooltip: 'Blender EIF Exporter for EuroLand'
Authors: Swyter and Jmarti856
"""
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

def _write(context, filepath,
            EXPORT_GLOBAL_MATRIX,
        ):

    #===============================================================================================
    #  GLOBAL VARIABLES
    #===============================================================================================
    ProjectContextScene = bpy.context.scene

    # Axis Conversion
    InvertAxisMatrix = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0)))
    
    #===============================================================================================
    #  MAIN
    #===============================================================================================
    def WriteFile():
        # Stop edit mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        #Create new file
        with open(filepath, 'w') as out:
            #Start writing
            AmbientValue = bpy.context.scene.world.light_settings.ao_factor
            out.write('*EUROCOM_INTERCHANGE_FILE 100\n')
            out.write('*COMMENT Eurocom Interchange File Version 1.00 %s\n' % (datetime.datetime.utcnow()).strftime('%A %B %d %Y %H:%M'))
            out.write('\n')
            out.write('*OPTIONS {\n')
            out.write('\t*COORD_SYSTEM %s\n' % "LH")
            out.write('}\n')
            out.write('\n')
            out.write('*SCENE {\n')
            out.write('\t*FILENAME "%s"\n' % (bpy.data.filepath))
            out.write('\t*FIRSTFRAME %d\n' % (ProjectContextScene.frame_start))
            out.write('\t*LASTFRAME %d\n' % (ProjectContextScene.frame_end))
            out.write('\t*FRAMESPEED %d\n' % (ProjectContextScene.render.fps))
            out.write('\t*STATICFRAME %d\n' % (ProjectContextScene.frame_current))
            out.write('\t*AMBIENTSTATIC %.6f %.6f %.6f\n' %(AmbientValue, AmbientValue, AmbientValue))
            out.write('}\n')
            out.write('\n')
            
            #===============================================================================================
            #  MATERIAL LIST
            #===============================================================================================
            MaterialIndex = 0
            out.write('*MATERIALS {\n')
            for mat in bpy.data.materials:            
                if hasattr(mat.node_tree, 'nodes'):
                    DiffuseColor = mat.diffuse_color
                    ImageNode = mat.node_tree.nodes.get('Image Texture', None)
                    
                    #Material has texture
                    if (ImageNode is not None):
                        ImageName = ImageNode.image.name
                        out.write('\t*MATERIAL %d {\n' % (MaterialIndex))
                        out.write('\t\t*NAME "%s"\n' % (os.path.splitext(ImageName)[0]))
                        out.write('\t\t*COL_DIFFUSE %.6f %.6f %.6f\n' % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))

                        #Check if the texture exists
                        if (os.path.exists(bpy.path.abspath(ImageNode.image.filepath))):
                            out.write('\t\t*TWOSIDED\n')
                            out.write('\t\t*MAP_DIFFUSE "%s"\n' % (bpy.path.abspath(ImageNode.image.filepath)))
                        out.write('\t\t*MAP_DIFFUSE_AMOUNT 1.0\n')

                        #Check if use Alpha
                        if mat.blend_method.startswith('ALPHA'):
                            out.write('\t\t*MAP_HASALPHA\n')

                        MaterialIndex +=1
                        out.write('\t}\n')

                    #Material has no texture
                    else:
                        Color = DiffuseColor[0] + DiffuseColor[1] + DiffuseColor[2]
                        out.write('\t*MATERIAL %d {\n' % (MaterialIndex))
                        out.write('\t\t*NAME "%s"\n' % (mat.name))
                        out.write('\t\t*COL_DIFFUSE %.6f %.6f %.6f\n' % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))
                        out.write('\t}\n')
                        MaterialIndex +=1
            out.write('}\n')
            out.write('\n')
            
            #===============================================================================================
            #  MESH DATA
            #===============================================================================================
            for obj in ProjectContextScene.objects:
                if obj.type == 'MESH':
                    if hasattr(obj, 'data'):
                        #===========================================[Clone Object]====================================================
                        depsgraph = bpy.context.evaluated_depsgraph_get()
                        ob_for_convert = obj.evaluated_get(depsgraph)

                        try:
                            MeshObject = ob_for_convert.to_mesh()
                        except RuntimeError:
                            MeshObject = None
                        if MeshObject is None:
                            continue

                        #===========================================[Apply Matrix]====================================================
                        MeshObject.transform(EXPORT_GLOBAL_MATRIX @ obj.matrix_world)
                        if (EXPORT_GLOBAL_MATRIX @ obj.matrix_world).determinant() < 0.0:
                            MeshObject.flip_normals()

                        #===========================================[Get Object Data]====================================================
                        #Get vertex list without duplicates
                        VertexList = []
                        for ObjVertex in MeshObject.vertices:
                            VertexList.append(ObjVertex.co)

                        #Get UVs list without duplicates
                        UVList = []
                        if hasattr(MeshObject.uv_layers.active, 'data'):
                            if len(MeshObject.uv_layers):
                                for layer in MeshObject.uv_layers:
                                    uv_layer = layer.data
                                    for pl_count, poly in enumerate(MeshObject.polygons):
                                        for li_count, loop_index in enumerate(poly.loop_indices):
                                            if uv_layer[loop_index].uv not in UVList:
                                                UVList.append((uv_layer[loop_index].uv))

                        #Get vertex color list without duplicates
                        VertexColList = []
                        if len(MeshObject.vertex_colors):
                            if hasattr(MeshObject.vertex_colors.active, 'data'):
                                for layer in MeshObject.vertex_colors:
                                    for vertex in layer.data:
                                        VertexColList.append(
                                            (vertex.color[0] * .5, vertex.color[1] * .5, vertex.color[2] * .5, vertex.color[3])
                                        )
                                VertexColList = list(dict.fromkeys(VertexColList))

                        FaceFormat = 'V'
                        #===========================================[Print Object Data]==================================================== 
                        out.write('*MESH {\n')
                        out.write('\t*NAME "%s"\n' % obj.name)
                        out.write('\t*VERTCOUNT %d\n' % len(VertexList))
                        out.write('\t*UVCOUNT %d\n' % len(UVList))
                        out.write('\t*VERTCOLCOUNT %d\n' % len(VertexColList))
                        out.write('\t*FACECOUNT %d\n' % len(MeshObject.polygons))
                        out.write('\t*TRIFACECOUNT %d\n' % sum(len(p.vertices) - 2 for p in MeshObject.polygons))

                        if len(MeshObject.uv_layers) > 0:
                            out.write('\t*FACELAYERSCOUNT %d\n' % len(MeshObject.uv_layers))
                        else:
                            out.write('\t*FACELAYERSCOUNT %d\n' % 1)
                            
                        if len(MeshObject.uv_layers) > 1:
                            out.write('\t*FACESHADERCOUNT %d\n' % len(MeshObject.material_slots))

                        #Print Vertex List
                        out.write('\t*VERTEX_LIST {\n')
                        for VertexData in VertexList:
                            out.write('\t\t%.6f %.6f %.6f\n' % VertexData[:])
                        out.write('\t}\n')

                        #Print UV data
                        out.write('\t*UV_LIST {\n')
                        if (len(UVList) > 0):
                            FaceFormat += 'T'
                            for uv in UVList:
                                out.write('\t\t%.6f %.6f\n' % (uv[0], 1.0 - uv[1]))
                        out.write('\t}\n')

                        #Print Vertex Color List
                        out.write('\t*VERTCOL_LIST {\n')
                        if(len(VertexColList) > 0):
                            FaceFormat += 'C'
                            for col in VertexColList:
                                out.write('\t\t%.6f %.6f %.6f %.6f\n' % col[:])
                        out.write('\t}\n')

                        if len(obj.material_slots) > 0:
                            FaceFormat += 'M'
                            FaceFormat += 'F'

                        #Print Shader faces
                        if (len(MeshObject.uv_layers) > 1):
                            ShaderIndex = 0
                            MaterialIndex = 0
                            out.write('\t*FACESHADERS {\n')
                            for mat in MeshObject.material_slots:
                                out.write('\t\t*SHADER %d {\n' % ShaderIndex)
                                
                                if mat.material.blend_method == 'OPAQUE':
                                    out.write('\t\t\t%d %s\n' % (bpy.data.materials.find(mat.name),"Non"))
                                else:
                                    out.write('\t\t\t%d %s\n' % (bpy.data.materials.find(mat.name),"Alp"))
                                out.write('\t\t}\n')
                                
                                #update Counter
                                MaterialIndex +=1
                            out.write('\t}\n')

                        #Get FaceFormat
                        out.write('\t*FACEFORMAT %s\n' % FaceFormat)

                        #Print Face List, the difficult part ;P
                        out.write('\t*FACE_LIST {\n')
                        for MeshPolys in MeshObject.polygons:
                            #Write vertices ---V
                            out.write('\t\t%d ' % (len(MeshPolys.vertices)))
                            for vert in MeshPolys.vertices:
                                out.write('%d ' % vert)

                            #Write UVs ---T
                            if ('T' in FaceFormat):
                                for vert_idx, loop_idx in enumerate(MeshPolys.loop_indices):
                                    for layer in MeshObject.uv_layers:
                                        out.write('%d ' % UVList.index(layer.data[loop_idx].uv))

                            #Write Colors ---C
                            if ('C' in FaceFormat):
                                for color_idx, loop_idx in enumerate(MeshPolys.loop_indices):
                                    # swy: this is wrong; it should be the same layer count as any other face format block, can't be a different size. me.vertex_colors != me.uv_layers
                                    for layerIndex in MeshObject.vertex_colors:
                                        vertex = layerIndex.data[loop_idx]
                                        out.write('%d ' % VertexColList.index((vertex.color[0] * .5, vertex.color[1] * .5, vertex.color[2] * .5, vertex.color[3])))
                            # swy: we're missing exporting (optional) face normals here

                            if ('M' in FaceFormat):
                                for layer in MeshObject.uv_layers:
                                    out.write('%d ' % MeshPolys.material_index)
                                    
                            # swy: we're missing exporting an optional shader index here

                            #Write Flags ---F
                            if ('F' in FaceFormat):
                                flags = 0                             
                                
                                if obj.material_slots[MeshPolys.material_index].material.use_backface_culling:
                                    flags |= 1 << 16
                                out.write('%d ' % flags)

                            out.write('\n')
                        out.write('\t}\n')
                    out.write('}\n')
                    out.write('\n')

            #===============================================================================================
            #  GEOM NODE
            #===============================================================================================
            for obj in ProjectContextScene.objects:
                if obj.type == 'MESH':
                    if hasattr(obj, 'data'):        
                        out.write('*GEOMNODE {\n')
                        out.write('\t*NAME "%s"\n' % (obj.name))
                        out.write('\t*MESH "%s"\n' % (obj.name))
                        out.write('\t*WORLD_TM {\n')
                        out.write('\t\t*TMROW0 %.6f %.6f %.6f %.6f\n' % (1,0,0,0))
                        out.write('\t\t*TMROW1 %.6f %.6f %.6f %.6f\n' % (0,1,0,0))
                        out.write('\t\t*TMROW2 %.6f %.6f %.6f %.6f\n' % (0,0,1,0))
                        out.write('\t\t*TMROW3 %.6f %.6f %.6f %.6f\n' % (0,0,0,1))
                        out.write('\t\t*POS %.6f %.6f %.6f\n' % (0,0,0))
                        out.write('\t\t*ROT %.6f %.6f %.6f\n' % (0,0,0))
                        out.write('\t\t*SCL %.6f %.6f %.6f\n' % (1,1,1))
                        out.write('\t}\n')
                        out.write('\t*USER_FLAGS_COUNT %u\n' % 1)
                        out.write('\t*USER_FLAGS {\n')
                        out.write('\t\t*SET 0 0x00000000\n')
                        out.write('\t}\n')
                        out.write('}\n')

            #===============================================================================================
            #  PLACE NODE
            #===============================================================================================
            for obj in ProjectContextScene.objects:
                if obj.type == 'MESH':
                    if hasattr(obj, 'data'):                     

                        out.write('*PLACENODE {\n')
                        out.write('\t*NAME "%s"\n' % (obj.name))
                        out.write('\t*MESH "%s"\n' % (obj.name))
                        out.write('\t*WORLD_TM {\n')
                        
                        #Jump to the first frame
                        ProjectContextScene.frame_set(ProjectContextScene.frame_start)
                        
                        RotationMatrix = EXPORT_GLOBAL_MATRIX @ obj.matrix_world
                        RotationMatrix = EXPORT_GLOBAL_MATRIX @ RotationMatrix.transposed()
                        loc_pos = InvertAxisMatrix @ obj.location
                        
                        #Print Roation matrix
                        out.write('\t\t*TMROW0 %.6f %.6f %.6f %.6f\n' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z, 0))
                        out.write('\t\t*TMROW1 %.6f %.6f %.6f %.6f\n' % (RotationMatrix[1].x, RotationMatrix[1].y, RotationMatrix[1].z, 0))
                        out.write('\t\t*TMROW2 %.6f %.6f %.6f %.6f\n' % (RotationMatrix[2].x, RotationMatrix[2].y, RotationMatrix[2].z, 0))
                        out.write('\t\t*TMROW3 %.6f %.6f %.6f %.6f\n' % (loc_pos.x, loc_pos.y, loc_pos.z, 1))

                        # swy: these aren't actually used or read by this version of the importer
                        out.write('\t\t*POS %.6f %.6f %.6f\n' % (loc_pos.x, loc_pos.y, loc_pos.z))
                        out.write('\t\t*ROT %.6f %.6f %.6f\n' % (degrees(obj.rotation_euler.x), degrees(obj.rotation_euler.z), degrees(obj.rotation_euler.y)))
                        out.write('\t\t*SCL %.6f %.6f %.6f\n' % (obj.scale.x, obj.scale.y, obj.scale.z))
                        out.write('\t}\n')
                        out.write('}\n')
            #Close File
            out.flush()
            out.close()
    WriteFile()

def save(context,
            filepath,
            *,
            global_matrix=None,
        ):

    _write(context, filepath,
            EXPORT_GLOBAL_MATRIX=global_matrix,
        )

    return {'FINISHED'}
if __name__ == '__main__':
    save({}, str(Path.home()) + '/Desktop/EurocomEIF.eif')