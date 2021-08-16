#  Copyright (c) 2020-2021 Swyter <swyterzone+sphinx@gmail.com>
#  SPDX-License-Identifier: Zlib

"""
Name: 'EUROEXPORT'
Blender: 2.90.1
Group: 'Export'
Tooltip: 'Blender ESE Exporter for EuroLand'
Authors: Swyter and Jmarti856
"""
import bpy
import os
import math
import bmesh
import datetime
from mathutils import *
from math import *
from pathlib import Path
from bpy_extras.io_utils import axis_conversion

block_level = 0

def _write(context, filepath,
            EXPORT_FLIP_POLYGONS,
            EXPORT_OBJECTTYPES,
            EXPORT_MATERIALS,
            EXPORT_CAMERALIGHTANIMS,
            EXPORT_VERTEXCOLORS,
            EXPORT_ANIMATION,
            EXPORT_GLOBAL_MATRIX,
        ):

    # swy: convert from the blender to the euroland coordinate system; we can't do that with the
    #      standard matrix transformations
    InvertAxisRotationMatrix = Matrix(((1, 0, 0),
                                       (0, 0, 1),
                                       (0, 1, 0)))

    #===============================================================================================
    #  FUNCTIONS
    #===============================================================================================
    def PrintNODE_TM(OutputFile, object):
            bpy.context.scene.frame_set(bpy.context.scene.frame_start)

            ConvertedMatrix = object.rotation_euler.to_matrix()
            rot_mtx = InvertAxisRotationMatrix @ ConvertedMatrix
            RotationMatrix = rot_mtx.transposed()

            #Write Matrix
            OutputFile.write('\t\t*NODE_NAME "%s"\n' % object.name)
            OutputFile.write('\t\t*INHERIT_POS %u %u %u\n' % (0,0,0))
            OutputFile.write('\t\t*INHERIT_ROT %u %u %u\n' % (0,0,0))
            OutputFile.write('\t\t*INHERIT_SCL %u %u %u\n' % (1,1,1))

            if object.type == 'CAMERA':
                #Don't modify this, the cameras rotations works fine with this code.
                OutputFile.write('\t\t*TM_ROW0 %.4f %.4f %.4f\n' % (RotationMatrix[0].x,      RotationMatrix[0].y * -1, RotationMatrix[0].z     ))
                OutputFile.write('\t\t*TM_ROW1 %.4f %.4f %.4f\n' % (RotationMatrix[1].x,      RotationMatrix[1].y,      RotationMatrix[1].z     ))
                OutputFile.write('\t\t*TM_ROW2 %.4f %.4f %.4f\n' % (RotationMatrix[2].x * -1, RotationMatrix[2].y * -1, RotationMatrix[2].z * -1))
            else:
                #This other code needs revision, the rotations in the entity editor don't works. 
                OutputFile.write('\t\t*TM_ROW0 %.4f %.4f %.4f\n' % (RotationMatrix[0].x, RotationMatrix[0].y,      RotationMatrix[0].z     ))
                OutputFile.write('\t\t*TM_ROW1 %.4f %.4f %.4f\n' % (RotationMatrix[1].x, RotationMatrix[1].y,      RotationMatrix[1].z * -1))
                OutputFile.write('\t\t*TM_ROW2 %.4f %.4f %.4f\n' % (RotationMatrix[2].x, RotationMatrix[2].y * -1, RotationMatrix[2].z * -1))
            
            #Flip location axis
            loc_conv = InvertAxisRotationMatrix @ object.location
            OutputFile.write('\t\t*TM_ROW3 %.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))
            OutputFile.write('\t\t*TM_POS  %.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))

    def PrintTM_ANIMATION(OutputFile, object, TimeValue):
            OutputFile.write('\t*TM_ANIMATION {\n')
            OutputFile.write('\t\t*NODE_NAME "%s"\n' % object.name)
            OutputFile.write('\t\t*TM_ANIM_FRAMES {\n')

            TimeValueCounter = 0
            for f in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
                bpy.context.scene.frame_set(f)

                ConvertedMatrix = object.rotation_euler.to_matrix()

                rot_mtx = InvertAxisRotationMatrix @ ConvertedMatrix
                RotationMatrix = rot_mtx.transposed()

                #Write Time Value
                OutputFile.write('\t\t\t*TM_FRAME  %u ' % TimeValueCounter)

                #Write Matrix
                OutputFile.write('%.4f %.4f %.4f  ' % (RotationMatrix[0].x,      RotationMatrix[0].y * -1, RotationMatrix[0].z     ))
                OutputFile.write('%.4f %.4f %.4f  ' % (RotationMatrix[1].x,      RotationMatrix[1].y,      RotationMatrix[1].z     ))
                OutputFile.write('%.4f %.4f %.4f  ' % (RotationMatrix[2].x * -1, RotationMatrix[2].y * -1, RotationMatrix[2].z * -1))
                
                #Flip location axis
                loc_conv = InvertAxisRotationMatrix @ object.location
                OutputFile.write('%.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))

                #Update counter
                TimeValueCounter += TimeValue
            OutputFile.write('\t\t}\n')
            OutputFile.write('\t}\n')

    def GetMaterialCount():
        Materials_Number = 0
        for indx, MeshObj in enumerate(bpy.context.scene.objects):
            if MeshObj.type == 'MESH':
                Materials_Number += 1
        return Materials_Number

    #===============================================================================================
    #  MAIN
    #===============================================================================================
    def WriteFile():
        # Stop edit mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        #Create new file
        with open(filepath, 'w') as out:

            # swy: make a no-carriage-return version
            def write_scope_no_cr(dump):
                out.write(('\t' * block_level) + dump)

            def write_scope(dump):
                write_scope_no_cr(dump + '\n')

            def w_new_block(dump):
                write_scope(dump)
                global block_level; block_level += 1

            def w_end_block(dump):
                global block_level; block_level -= 1
                write_scope(dump)

            #Start writting
            write_scope('*3DSMAX_EUROEXPORT	300')
            write_scope('*COMMENT "Eurocom Export Version  3.00 - %s"' % (datetime.datetime.utcnow()).strftime('%A %B %d %H:%M:%S %Y'))
            write_scope('*COMMENT "Version of Blender that output this file: %s"' % bpy.app.version_string)
            write_scope('*COMMENT "Version of ESE Plug-in: 5.0.0.13"')
            write_scope('')

            #===============================================================================================
            #  SCENE INFO
            #=============================================================================================== 
            TimeValue = 4800 / bpy.context.scene.render.fps

            w_new_block('*SCENE {')
            write_scope('*SCENE_FILENAME     "%s"' % os.path.basename(bpy.data.filepath))
            write_scope('*SCENE_FIRSTFRAME    %u ' % bpy.context.scene.frame_start)
            write_scope('*SCENE_LASTFRAME     %u ' % bpy.context.scene.frame_end)
            write_scope('*SCENE_FRAMESPEED    %u ' % bpy.context.scene.render.fps)
            write_scope('*SCENE_TICKSPERFRAME %u ' % TimeValue)
            w_end_block('}')

            #===============================================================================================
            #  MATERIAL LIST
            #===============================================================================================
            if EXPORT_MATERIALS:
                w_new_block('*MATERIAL_LIST {')
                write_scope('*MATERIAL_COUNT %u' % GetMaterialCount())
                for indx, MeshObj in enumerate(bpy.context.scene.objects):
                        if MeshObj.type == 'MESH':
                            #Material
                            w_new_block('*MATERIAL %u {' % indx)

                            #Mesh Materials
                            if len(MeshObj.material_slots) > 0:
                                currentSubMat = 0

                                #Material Info                                    
                                MatData = bpy.data.materials[0]
                                DiffuseColor = MatData.diffuse_color
                                write_scope('*MATERIAL_NAME "%s"' % MatData.name)
                                write_scope('*MATERIAL_DIFFUSE %.4f %.4f %.4f' % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))
                                write_scope('*MATERIAL_SPECULAR %u %u %u' % (MatData.specular_color[0], MatData.specular_color[1], MatData.specular_color[2]))
                                write_scope('*MATERIAL_SHINE %.1f' % MatData.metallic)
                                write_scope('*NUMSUBMTLS %u ' % len(MeshObj.material_slots))

                                #Loop Trought Submaterials
                                for indx, Material_Data in enumerate(MeshObj.material_slots):
                                    MatData = bpy.data.materials[Material_Data.name]

                                    #Material has texture
                                    if MatData.node_tree.nodes.get('Image Texture', None):
                                        ImageNode = MatData.node_tree.nodes.get('Image Texture', None)
                                        ImageName = ImageNode.image.name
                                        DiffuseColor = MatData.diffuse_color

                                        #Submaterial
                                        w_new_block('*SUBMATERIAL %u {' % currentSubMat)
                                        write_scope('*MATERIAL_NAME "%s"' % (os.path.splitext(ImageName)[0]))
                                        write_scope('*MATERIAL_DIFFUSE %.4f %.4f %.4f' % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))
                                        write_scope('*MATERIAL_SPECULAR %u %u %u' % (MatData.specular_color[0], MatData.specular_color[1], MatData.specular_color[2]))
                                        write_scope('*MATERIAL_SHINE %.1f' % MatData.metallic)
                                        write_scope('*MATERIAL_SELFILLUM %u' % int(MatData.use_preview_world))

                                        #Map Difuse
                                        w_new_block('*MAP_DIFFUSE {')
                                        write_scope('*MAP_NAME "%s"' % (os.path.splitext(ImageName)[0]))
                                        write_scope('*MAP_CLASS "%s"' % "Bitmap")
                                        write_scope('*MAP_AMOUNT "%u"' % 1)
                                        write_scope('*BITMAP "%s"' % (bpy.path.abspath(ImageNode.image.filepath)))
                                        w_end_block('}')

                                    #Material has no texture
                                    else:
                                        #Submaterial
                                        principled = next(n for n in MatData.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
                                        base_color = principled.inputs['Base Color']
                                        color = base_color.default_value

                                        w_new_block('*SUBMATERIAL %u {' % currentSubMat)
                                        write_scope('*MATERIAL_NAME "%s"' % MatData.name)
                                        write_scope('*MATERIAL_DIFFUSE %.4f %.4f %.4f' % ((color[0] * .5), (color[1] * .5), (color[2] * .5)))
                                        write_scope('*MATERIAL_SPECULAR %u %u %u' % (MatData.specular_color[0], MatData.specular_color[1], MatData.specular_color[2]))
                                        write_scope('*MATERIAL_SHINE %.1f' % MatData.metallic)
                                        write_scope('*MATERIAL_SELFILLUM %u' % int(MatData.use_preview_world))

                                    w_end_block('}')
                                    currentSubMat += 1
                            w_end_block('}')
                w_end_block('}')

            #===============================================================================================
            #  GEOM OBJECT
            #===============================================================================================
            if 'MESH' in EXPORT_OBJECTTYPES:
                for indx, obj in enumerate(bpy.context.scene.objects):
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
                            if EXPORT_FLIP_POLYGONS:
                                MeshObject.flip_normals()

                            #===========================================[Triangulate Object]====================================================
                            bm = bmesh.new()
                            bm.from_mesh(MeshObject)
                            tris = bm.calc_loop_triangles()

                            #===========================================[Get Object Data]====================================================
                            #Get vertex list without duplicates
                            VertexList = []
                            for tri in tris:
                                for loop in tri:
                                    if loop.vert.co not in VertexList:
                                        VertexList.append(loop.vert.co)              

                            #Get UV Layer Active
                            UVVertexList = []                    
                            for name, uvl in bm.loops.layers.uv.items():
                                for i, tri in enumerate(tris):
                                    for loop in tri:
                                        DataToAppend = loop[uvl].uv
                                        if DataToAppend not in UVVertexList:
                                            UVVertexList.append(DataToAppend)

                            if True:
                                #Get Vertex Colors List 
                                VertexColorList = []
                                for name, cl in bm.loops.layers.color.items():
                                    for tri in tris:
                                        for loop in tri:
                                            color = loop[cl] # gives a Vector((R, G, B, A))
                                            if color not in VertexColorList:
                                                VertexColorList.append(color)

                            #===========================================[Print Object Data]====================================================       
                            w_new_block('*GEOMOBJECT {')
                            write_scope('*NODE_NAME "%s"' % obj.name)

                            #Print Matrix Rotation
                            w_new_block('*NODE_TM {')
                            PrintNODE_TM(out, obj)
                            w_end_block('}')

                            #Print Matrix Rotation again ¯\_(ツ)_/¯
                            w_new_block('*PIVOT_TM {')
                            PrintNODE_TM(out, obj)
                            w_end_block('}')

                            #MESH Section
                            w_new_block('*MESH {')
                            write_scope('*TIMEVALUE %u' % 0)
                            write_scope('*MESH_NUMVERTEX %u' % len(VertexList))
                            write_scope('*MESH_NUMFACES %u' % len(tris))

                            #Print Vertex List
                            w_new_block('*MESH_VERTEX_LIST {')
                            for idx, ListItem in enumerate(VertexList):
                                write_scope('*MESH_VERTEX %u %.4f %.4f %.4f' % (idx, ListItem[0], ListItem[1], ListItem[2]))
                            w_end_block('}')

                            #Face Vertex Index
                            w_new_block('*MESH_FACE_LIST {')   
                            for i, tri in enumerate(tris):
                                write_scope_no_cr('*MESH_FACE %u: ' % i)
                                out.write('A: %u B: %u C: %u ' % (VertexList.index(tri[0].vert.co), VertexList.index(tri[1].vert.co), VertexList.index(tri[2].vert.co)))
                                out.write('AB: %u BC: %u CA: %u ' % (not tri[0].vert.hide, not tri[1].vert.hide, not tri[2].vert.hide))   
                                out.write('*MESH_SMOOTHING 1 ')
                                out.write('*MESH_MTLID %u\n' % tri[0].face.material_index)
                            w_end_block('}')

                            #Texture UVs
                            if len(UVVertexList) > 0:
                                write_scope('*MESH_NUMTVERTEX %u' % len(UVVertexList))
                                w_new_block('*MESH_TVERTLIST {')
                                for idx, TextUV in enumerate(UVVertexList):
                                    write_scope('*MESH_TVERT %u %.4f %.4f' % (idx, TextUV[0], TextUV[1]))
                                w_end_block('}')

                            #Face Layers UVs Index
                            layerIndex = 0
                            #out.write('\t\t*MESH_NUMTFACELAYERS %u\n' % len(bm.loops.layers.uv.items()))
                            #for name, uv_lay in bm.loops.layers.uv.items():
                            #    out.write('\t\t*MESH_TFACELAYER %u {\n' % layerIndex)
                            #    out.write('\t\t\t*MESH_NUMTVFACES %u \n' % len(bm.faces))
                            #    out.write('\t\t\t*MESH_TFACELIST {\n')           
                            #    for i, tri in enumerate(tris):
                            #        out.write('\t\t\t\t*MESH_TFACE %u ' % i)
                            #        out.write('%u %u %u\n' % (UVVertexList.index(tri[0][uv_lay].uv), UVVertexList.index(tri[1][uv_lay].uv), UVVertexList.index(tri[2][uv_lay].uv)))
                            #    out.write('\t\t\t}\n')
                            #    out.write('\t\t}\n')
                            #    layerIndex += 1

                            # swy: fix-me: add the custom mesh attributes here
                            write_scope("*MESH_NUMFACEFLAGS %u" % len(bm.faces))
                            w_new_block("*MESH_FACEFLAGLIST {")
                            for i, tri in enumerate(tris):
                                write_scope('*MESH_FACEFLAG %u %u' % (i, 0))
                            w_end_block("}")

                            for indx, mod in enumerate(obj.modifiers):
                                if mod.type == 'ARMATURE' and mod.object and mod.object.type == 'ARMATURE':
                                    armat = mod.object
                                    w_new_block("*SKIN_DATA {")
                                    w_new_block("*BONE_LIST {")
                                    for bidx, bone in enumerate(armat.data.bones):
                                        write_scope('*BONE %u "%s"' % (bidx, bone.name))
                                    w_end_block("}")

                                    w_new_block('*SKIN_VERTEX_DATA {')
                                    for vidx, vert in enumerate(obj.data.vertices):
                                        #for bidx, bone in enumerate(armat.data.bones):
                                            write_scope('*VERTEX %u %u' % (vidx, len(vert.groups)))
                                            for gidx, group in enumerate(vert.groups):
                                                out.write('  %u %f' % (gidx, group.weight))
                                            out.write("\n")
                                    w_end_block("}")
                                    w_end_block("}")

                                    break

                            if True:
                                #Vertex Colors List
                                write_scope('*MESH_NUMCVERTEX %u' % len(VertexColorList))
                                w_new_block('*MESH_CVERTLIST {')
                                for idx, ColorArray in enumerate(VertexColorList):
                                    write_scope('*MESH_VERTCOL %u %.4f %.4f %.4f %u' % (idx, (ColorArray[0] * .5), (ColorArray[1] * .5), (ColorArray[2] * .5), 1))
                                w_end_block('}')

                                #Face Color Vertex Index
                                layerIndex = 0
                                if len(bm.loops.layers.color.items()) > 0:
                                    write_scope('*MESH_NUMCFACELAYERS %u' % len(bm.loops.layers.color.items()))
                                    for name, cl in bm.loops.layers.color.items():
                                        w_new_block('*MESH_CFACELAYER %u {' % layerIndex)
                                        write_scope('*MESH_NUMCVFACES %u ' % len(tris))
                                        w_new_block('*MESH_CFACELIST {\n')
                                        for i, tri in enumerate(tris):
                                            write_scope_no_cr('*MESH_CFACE %u ' % i)
                                            for loop in tri:
                                                out.write('%u ' % VertexColorList.index(loop[cl]))
                                            out.write('\n')
                                        w_end_block('}')
                                        w_end_block('}')
                                        layerIndex +=1

                            w_new_block('*MESH_VERTFLAGSLIST {')
                            for vidx, vert in enumerate(obj.data.vertices):
                                write_scope('*VFLAG %u %u' % (vidx, 0))
                            w_end_block('}')

                            #Liberate BM Object
                            bm.free()

                            #Close blocks
                            w_end_block('}')

                            #===============================================================================================
                            #  ANIMATION
                            #===============================================================================================
                            if EXPORT_ANIMATION:
                                PrintTM_ANIMATION(out, obj, TimeValue)
                            
                            #Material Reference
                            if EXPORT_MATERIALS:
                                write_scope('*MATERIAL_REF %u' % indx)
                            w_end_block('}')

            for indx, obj in enumerate(bpy.context.scene.objects):
                if obj.type == 'ARMATURE':
                    for bidx, bone in enumerate(obj.data.bones):
                        w_new_block('*BONEOBJECT {')
                        write_scope('*NODE_NAME "%s"' % bone.name)
                        write_scope('*NODE_BIPED_BODY')
                        if (bone.parent):
                            write_scope('*NODE_PARENT "%s"' % bone.parent.name)
                        w_end_block('}')

            #===============================================================================================
            #  CAMERA OBJECT
            #===============================================================================================
            if 'CAMERA' in EXPORT_OBJECTTYPES:
                CamerasList = []

                for obj in bpy.context.scene.objects:
                    if obj.type == 'CAMERA':
                        CamerasList.append(obj)
                CamerasList.sort(key = lambda o: o.name)

                for CameraObj in CamerasList:  
                    w_new_block('*CAMERAOBJECT {')
                    write_scope('*NODE_NAME "%s"' % CameraObj.name)
                    write_scope('*CAMERA_TYPE %s' % "Target")

                    #Print Matrix Rotation
                    w_new_block('*NODE_TM {')
                    PrintNODE_TM(out, CameraObj)
                    w_end_block('}')

                    #===============================================================================================
                    #  CAMERA SETTINGS
                    #=============================================================================================== 
                    w_new_block('*CAMERA_SETTINGS {')
                    write_scope('*TIMEVALUE %u' % 0)
                    write_scope('*CAMERA_FOV %.4f'% CameraObj.data.angle)
                    w_end_block('}')

                    #===============================================================================================
                    #  CAMERA ANIMATION
                    #===============================================================================================
                    if EXPORT_ANIMATION:
                        w_new_block('*CAMERA_ANIMATION {')
                        
                        TimeValueCounter = 0
                        for f in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
                            bpy.context.scene.frame_set(f)

                            w_new_block('*CAMERA_SETTINGS {')
                            write_scope('*TIMEVALUE %u' % TimeValueCounter)
                            write_scope('*CAMERA_FOV %.4f'% CameraObj.data.angle)
                            w_end_block('}')

                            TimeValueCounter += TimeValue

                        w_end_block('}')

                    #===============================================================================================
                    #  ANIMATION
                    #===============================================================================================
                    if EXPORT_ANIMATION:
                        PrintTM_ANIMATION(out, CameraObj, TimeValue)

                    w_end_block('}')

            #===============================================================================================
            #  LIGHT OBJECT
            #===============================================================================================
            if 'LIGHT' in EXPORT_OBJECTTYPES:
                for obj in bpy.context.scene.objects:
                    if obj.type == 'LIGHT':
                        w_new_block('*LIGHTOBJECT {')
                        write_scope('*NODE_NAME "%s"' % obj.name)
                        write_scope('*NODE_PARENT "%s"' % obj.name)

                        type_lut = {}
                        type_lut['POINT'] = 'Omni'
                        type_lut['SPOT' ] = 'TargetSpot'
                        type_lut['SUN'  ] = 'TargetDirect'
                        type_lut['AREA' ] = 'TargetDirect' # swy: this is sort of wrong ¯\_(ツ)_/¯

                        write_scope('*LIGHT_TYPE %s' % type_lut[obj.data.type]) #Seems that always used "Omni" lights in 3dsMax, in blender is called "Point"

                        #Print Matrix Rotation
                        w_new_block('*NODE_TM {')
                        PrintNODE_TM(out, obj)
                        w_end_block('}')

                        #---------------------------------------------[Light Props]---------------------------------------------
                        write_scope('*LIGHT_DECAY %s' % "InvSquare") # swy: this is the only supported mode
                        write_scope('*LIGHT_AFFECT_DIFFUSE %s' % "Off") #for now
                        if (obj.data.specular_factor > 0.001):
                            write_scope('*LIGHT_AFFECT_SPECULAR %s' % "On") #for now
                        else:
                            write_scope('*LIGHT_AFFECT_SPECULAR %s' % "Off") #for now
                        write_scope('*LIGHT_AMBIENT_ONLY %s' % "Off") #for now

                        #---------------------------------------------[Light Settings]---------------------------------------------           
                        w_new_block('*LIGHT_SETTINGS {')
                        write_scope('*TIMEVALUE %u' % 0)
                        write_scope('*COLOR %.4f %.4f %.4f' % (obj.data.color.r, obj.data.color.g, obj.data.color.b))
                        write_scope('*FAR_ATTEN %.4f %.4f' % (obj.data.distance, obj.data.cutoff_distance))
                        if (obj.data.type == 'SUN'):
                            write_scope('*HOTSPOT %u' % math.degrees(obj.data.angle))
                        else:
                            write_scope('*HOTSPOT %u' % 0)
                        w_end_block('}')

                        #===============================================================================================
                        #  LIGHT ANIMATION
                        #=============================================================================================== 
                        if EXPORT_ANIMATION:
                            w_new_block('*LIGHT_ANIMATION {')

                            TimeValueCounter = 0
                            for f in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
                                bpy.context.scene.frame_set(f)

                                w_new_block('*LIGHT_SETTINGS {')
                                write_scope('*TIMEVALUE %u' % TimeValueCounter)
                                write_scope('*COLOR %.4f %.4f %.4f' % (obj.data.color.r, obj.data.color.g, obj.data.color.b))
                                write_scope('*FAR_ATTEN %.4f %.4f' % (obj.data.distance, obj.data.cutoff_distance))
                                if (obj.data.type == 'SUN'):
                                    write_scope('*HOTSPOT %u' % math.degrees(obj.data.angle))
                                else:
                                    write_scope('*HOTSPOT %u' % 0)
                                w_end_block('}')

                                TimeValueCounter += TimeValue

                            w_end_block('}')

                        #===============================================================================================
                        #  ANIMATION
                        #===============================================================================================
                        if EXPORT_ANIMATION:
                            PrintTM_ANIMATION(out, obj, TimeValue)

                        #Close light object
                        w_end_block('}')
            #Close File
            out.flush()
            out.close()
            del out
    WriteFile()

def save(context,
            filepath,
            *,
            Flip_Polygons=False,
            object_types={'CAMERA'},         
            Output_Materials=False,
            Output_CameraLightAnims=True,
            Output_VertexColors=True,
            Output_Animations=False,
            global_matrix=None,
        ):

    _write(context, filepath,
            EXPORT_FLIP_POLYGONS=Flip_Polygons,           
            EXPORT_OBJECTTYPES=object_types,
            EXPORT_ANIMATION=Output_Animations,
            EXPORT_MATERIALS=Output_Materials,
            EXPORT_CAMERALIGHTANIMS=Output_CameraLightAnims,
            EXPORT_VERTEXCOLORS=Output_VertexColors,
            EXPORT_GLOBAL_MATRIX=global_matrix,
        )

    return {'FINISHED'}
if __name__ == '__main__':
    save({}, str(Path.home()) + '/Desktop/EurocomESE.ese')