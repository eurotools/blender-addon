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
            EXPORT_AS_MAP,
            EXPORT_TRANSFORM_POS_ROT,
            EXPORT_GLOBAL_MATRIX,
        ):

    #===============================================================================================
    #  GLOBAL VARIABLES
    #===============================================================================================
    ProjectContextScene = bpy.context.scene
    
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
                    ImageNode = mat.node_tree.nodes.get('Image Texture', None)

                    #Material has texture
                    if (ImageNode is not None):
                        DiffuseColor = mat.diffuse_color
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

                        out.write('\t}\n')

                    #Material has no texture
                    else:
                        principled = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
                        base_color = principled.inputs['Base Color']
                        color = base_color.default_value

                        out.write('\t*MATERIAL %d {\n' % (MaterialIndex))
                        out.write('\t\t*NAME "%s"\n' % (mat.name))
                        out.write('\t\t*COL_DIFFUSE %.6f %.6f %.6f\n' % (color[0], color[1], color[2]))
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
                        if EXPORT_TRANSFORM_POS_ROT:
                            #===========================================[Save Previous Location and Rotation]====================================================
                            PrevLoc = [obj.location.x, obj.location.y, obj.location.z]

                            #Apply default *GEOMNODE Location
                            obj.location = (0,0,0)
                        
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
                        MeshObject.transform(EXPORT_GLOBAL_MATRIX @ ob_for_convert.matrix_world)
                        if (EXPORT_GLOBAL_MATRIX @ ob_for_convert.matrix_world).determinant() < 0.0:
                            MeshObject.flip_normals()
                        
                        #===========================================[Get Object Data]====================================================
                        #Get vertex list without duplicates
                        VertexList = []
                        for ObjVertex in MeshObject.vertices:
                            VertexList.append(ObjVertex.co)

                        #Get UVs list without duplicates
                        UVList = []
                        if len(MeshObject.uv_layers) > 0:
                            for poly in MeshObject.polygons:
                                for loop_idx in poly.loop_indices:
                                    for layer in MeshObject.uv_layers:
                                        uv_coords = layer.data[loop_idx].uv
                                        if uv_coords not in UVList:
                                            UVList.append(uv_coords)

                        #Get vertex color list without duplicates
                        VertexColList = []
                        if MeshObject.vertex_colors:
                            vcol_layer = MeshObject.vertex_colors.active
                        else:
                            vcol_layer = MeshObject.vertex_colors.new()

                        for poly in MeshObject.polygons:
                            for loop_index in poly.loop_indices:
                                loop_vert_index = MeshObject.loops[loop_index].vertex_index
                                v_color = vcol_layer.data[loop_index].color
                                VertexColList.append(v_color[:])

                        #Remove duplicates
                        VertexColList = list(dict.fromkeys(VertexColList))

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
                            out.write('\t*FACESHADERCOUNT %d\n' % len(obj.material_slots))

                        #Print Vertex List
                        out.write('\t*VERTEX_LIST {\n')
                        for VertexData in VertexList:
                            out.write('\t\t%.6f %.6f %.6f\n' % VertexData[:])
                        out.write('\t}\n')

                        #Print UV data
                        out.write('\t*UV_LIST {\n')
                        for uv in UVList:
                            out.write('\t\t%.6f %.6f\n' % (uv[0], 1.0 - uv[1]))
                        out.write('\t}\n')

                        #Print Vertex Color List
                        out.write('\t*VERTCOL_LIST {\n')
                        if(len(VertexColList) > 0):
                            for col in VertexColList:
                                out.write('\t\t%.6f %.6f %.6f %.6f\n' % (col[0] * .5, col[1] * .5, col[2] * .5, col[3]))
                        out.write('\t}\n')

                        #Print Shader faces
                        if (len(MeshObject.uv_layers) > 1):
                            ShaderIndex = 0
                            MaterialIndex = 0
                            out.write('\t*FACESHADERS {\n')
                            for mat in obj.material_slots:
                                out.write('\t\t*SHADER %d {\n' % ShaderIndex)

                                if hasattr(mat.material, 'blend_method'):
                                    if mat.material.blend_method == 'OPAQUE':
                                        out.write('\t\t\t%d %s\n' % (bpy.data.materials.find(mat.name),"Non"))
                                    else:
                                        out.write('\t\t\t%d %s\n' % (bpy.data.materials.find(mat.name),"Alp"))
                                out.write('\t\t}\n')

                                #update Counter
                                MaterialIndex +=1
                            out.write('\t}\n')

                        #Get FaceFormat
                        out.write('\t*FACEFORMAT %s\n' % "VTCMF")

                        #Print Face List, the difficult part ;P
                        out.write('\t*FACE_LIST {\n')
                        for MeshPolys in MeshObject.polygons:
                            #Write vertices ---V
                            out.write('\t\t%d ' % (len(MeshPolys.vertices)))
                            for vert in MeshPolys.vertices:
                                out.write('%d ' % vert)

                            #Write UVs ---T
                            if len(MeshObject.uv_layers) > 0:
                                for layer in MeshObject.uv_layers:
                                    for loop_idx in MeshPolys.loop_indices:
                                        out.write('%d ' % UVList.index(layer.data[loop_idx].uv))
                            else:
                                for num in range(len(MeshPolys.vertices)):
                                    out.write('%d ' % -1)

                            #Write Colors ---C
                            if len(MeshObject.vertex_colors) > 0:
                                for layer in MeshObject.vertex_colors:
                                    for loop_idx in MeshPolys.loop_indices:
                                        out.write('%d ' % VertexColList.index((layer.data[loop_idx].color[:])))
                            else:
                                for num in range(len(MeshPolys.vertices)):
                                    out.write('%d ' % -1)

                            # swy: we're missing exporting (optional) face normals here

                            #Material Index ---M
                            if len(obj.material_slots) > 0:
                                for indx, mat in enumerate(obj.material_slots):
                                    MaterialToFind = bpy.data.materials[MeshPolys.material_index].name
                                    if mat.name == MaterialToFind:
                                        out.write('%d ' % indx)
                                        break
                                    else:
                                        out.write('%d ' % 0)
                            else:
                                out.write('%d ' % -1)

                            # swy: we're missing exporting an optional shader index here

                            #Write Flags ---F
                            flags = 0
                            if len(obj.material_slots) > 0:
                                if obj.material_slots[MeshPolys.material_index].material.use_backface_culling:
                                    flags |= 1 << 16
                            out.write('%d ' % flags)

                            out.write('\n')
                        out.write('\t}\n')
                    out.write('}\n')
                    out.write('\n')

                    #===========================================[Restore Previous Location]====================================================
                    if EXPORT_TRANSFORM_POS_ROT:
                        obj.location = PrevLoc

            #===============================================================================================
            #  GEOM NODE (POSITION IN THE ENTITIES EDITOR)
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
                        out.write('\n')

            #===============================================================================================
            #  PLACE NODE (POSITION IN MAP)
            #===============================================================================================
            if EXPORT_AS_MAP:
                for obj in ProjectContextScene.objects:
                    if obj.type == 'MESH':
                        if hasattr(obj, 'data'):
                            # Axis Conversion
                            InvertAxisMatrix = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0)))
        
                            out.write('*PLACENODE {\n')
                            out.write('\t*NAME "%s"\n' % (obj.name))
                            out.write('\t*MESH "%s"\n' % (obj.name))
                            out.write('\t*WORLD_TM {\n')
                            
                            #Jump to the first frame
                            ProjectContextScene.frame_set(ProjectContextScene.frame_start)
                            
                            #Print Roation matrix
                            out.write('\t\t*TMROW0 %.6f %.6f %.6f %.6f\n' % (1,0,0,0))
                            out.write('\t\t*TMROW1 %.6f %.6f %.6f %.6f\n' % (0,1,0,0))
                            out.write('\t\t*TMROW2 %.6f %.6f %.6f %.6f\n' % (0,0,1,0))

                            #Location
                            if EXPORT_TRANSFORM_POS_ROT:
                                loc_pos = InvertAxisMatrix @ obj.location
                                out.write('\t\t*TMROW3 %.6f %.6f %.6f %.6f\n' % (loc_pos.x, loc_pos.y, loc_pos.z, 1))
                                out.write('\t\t*POS %.6f %.6f %.6f\n' % (loc_pos.x, loc_pos.y, loc_pos.z))
                            else:
                                out.write('\t\t*TMROW3 %.6f %.6f %.6f %.6f\n' % (0,0,0,1))
                                out.write('\t\t*POS %.6f %.6f %.6f\n' % (0,0,0))
                            out.write('\t\t*ROT %.6f %.6f %.6f\n' % (degrees(obj.rotation_euler.x), degrees(obj.rotation_euler.z), degrees(obj.rotation_euler.y)))
                            out.write('\t\t*SCL %.6f %.6f %.6f\n' % (obj.scale.x, obj.scale.y, obj.scale.z))
                            out.write('\t}\n')
                            out.write('}\n')
                            out.write('\n')
            #Close File
            out.flush()
            out.close()
    WriteFile()

def save(context,
            filepath,
            *,
            Output_Map=False,
            Output_Transform=False,
            global_matrix=None,
        ):

    _write(context, filepath,
            EXPORT_AS_MAP=Output_Map,
            EXPORT_TRANSFORM_POS_ROT=Output_Transform,
            EXPORT_GLOBAL_MATRIX=global_matrix,
        )

    return {'FINISHED'}
if __name__ == '__main__':
    save({}, str(Path.home()) + '/Desktop/EurocomEIF.eif')