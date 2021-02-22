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

def _write(context, filepath,
            EXPORT_FLIP_POLYGONS,
            EXPORT_OBJECTTYPES,
            EXPORT_MATERIALS,
            EXPORT_CAMERALIGHTANIMS,
            EXPORT_VERTEXCOLORS,
            EXPORT_ANIMATION,
            EXPORT_GLOBAL_MATRIX,
        ):

    #===============================================================================================
    #  GLOBAL VARIABLES
    #===============================================================================================
    ProjectContextScene = bpy.context.scene
    InvertAxisRotationMatrix = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0)))

    #===============================================================================================
    #  FUNCTIONS
    #===============================================================================================
    def PrintNODE_TM(OutputFile, SceneObject):
            ProjectContextScene.frame_set(ProjectContextScene.frame_start)

            ConvertedMatrix = SceneObject.rotation_euler.to_matrix()
            rot_mtx = InvertAxisRotationMatrix @ ConvertedMatrix
            RotationMatrix = rot_mtx.transposed()

            #Write Matrix
            OutputFile.write('\t\t*NODE_NAME "%s"\n' % SceneObject.name)
            OutputFile.write('\t\t*INHERIT_POS %u %u %u\n' % (0,0,0))
            OutputFile.write('\t\t*INHERIT_ROT %u %u %u\n' % (0,0,0))
            OutputFile.write('\t\t*INHERIT_SCL %u %u %u\n' % (1,1,1))

            if SceneObject.type == 'CAMERA':
                #Don't modify this, the cameras rotations works fine with this code.
                OutputFile.write('\t\t*TM_ROW0 %.4f %.4f %.4f\n' % (RotationMatrix[0].x, (RotationMatrix[0].y * -1), RotationMatrix[0].z))
                OutputFile.write('\t\t*TM_ROW1 %.4f %.4f %.4f\n' % (RotationMatrix[1].x, RotationMatrix[1].y, RotationMatrix[1].z))
                OutputFile.write('\t\t*TM_ROW2 %.4f %.4f %.4f\n' % ((RotationMatrix[2].x * -1), (RotationMatrix[2].y * -1), (RotationMatrix[2].z) * -1))
            else:
                #This other code needs revision, the rotations in the entity editor don't works. 
                OutputFile.write('\t\t*TM_ROW0 %.4f %.4f %.4f\n' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
                OutputFile.write('\t\t*TM_ROW1 %.4f %.4f %.4f\n' % (RotationMatrix[1].x, RotationMatrix[1].y, (RotationMatrix[1].z) * -1))
                OutputFile.write('\t\t*TM_ROW2 %.4f %.4f %.4f\n' % (RotationMatrix[2].x, (RotationMatrix[2].y * -1), (RotationMatrix[2].z) * -1))
            
            #Flip location axis
            loc_conv = InvertAxisRotationMatrix @ SceneObject.location
            OutputFile.write('\t\t*TM_ROW3 %.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))
            OutputFile.write('\t\t*TM_POS %.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))

    def PrintTM_ANIMATION(OutputFile, SceneObject, TimeValue):
            OutputFile.write('\t*TM_ANIMATION {\n')
            OutputFile.write('\t\t*NODE_NAME "%s"\n' % SceneObject.name)
            OutputFile.write('\t\t*TM_ANIM_FRAMES {\n')

            TimeValueCounter = 0
            for f in range(ProjectContextScene.frame_start, ProjectContextScene.frame_end + 1):
                ProjectContextScene.frame_set(f)

                ConvertedMatrix = SceneObject.rotation_euler.to_matrix()
                rot_mtx = InvertAxisRotationMatrix @ ConvertedMatrix
                RotationMatrix = rot_mtx.transposed()

                #Write Time Value
                OutputFile.write('\t\t\t*TM_FRAME %u ' % TimeValueCounter)

                #Write Matrix
                OutputFile.write('%.4f %.4f %.4f ' % (RotationMatrix[0].x, (RotationMatrix[0].y * -1), RotationMatrix[0].z))
                OutputFile.write('%.4f %.4f %.4f ' % (RotationMatrix[1].x, RotationMatrix[1].y, RotationMatrix[1].z))
                OutputFile.write('%.4f %.4f %.4f ' % ((RotationMatrix[2].x * -1), (RotationMatrix[2].y * -1), (RotationMatrix[2].z) * -1))
                
                #Flip location axis
                loc_conv = InvertAxisRotationMatrix @ SceneObject.location
                OutputFile.write('%.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))

                #Update counter
                TimeValueCounter += TimeValue            
            OutputFile.write('\t\t}\n')
            OutputFile.write('\t}\n')
    def GetMaterialCount():
        Materials_Number = 0
        for indx, MeshObj in enumerate(ProjectContextScene.objects):
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
            #Start writting
            out.write('*3DSMAX_EUROEXPORT	300\n')
            out.write('*COMMENT "Eurocom Export Version  3.00 - %s"\n' % (datetime.datetime.utcnow()).strftime('%A %B %d %H:%M:%S %Y'))
            out.write('*COMMENT "Version of Blender that output this file: %s"\n' % bpy.app.version_string)
            out.write('*COMMENT "Version of ESE Plug-in: 5.0.0.13"\n')
            out.write("\n")

            #===============================================================================================
            #  SCENE INFO
            #=============================================================================================== 
            BackgroundC = bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value
            AmbientValue = ProjectContextScene.world.light_settings.ao_factor
            TimeValue = 4800/ProjectContextScene.render.fps

            out.write('*SCENE {\n')
            out.write('\t*SCENE_FILENAME "%s"\n' % os.path.basename(bpy.data.filepath))
            out.write('\t*SCENE_FIRSTFRAME %u\n' % ProjectContextScene.frame_start)
            out.write('\t*SCENE_LASTFRAME %u\n' % ProjectContextScene.frame_end)
            out.write('\t*SCENE_FRAMESPEED %u\n' %  ProjectContextScene.render.fps)
            out.write('\t*SCENE_TICKSPERFRAME %u\n' % TimeValue)
            out.write('\t*SCENE_BACKGROUND_STATIC %u %u %u\n' %(BackgroundC[0], BackgroundC[1], BackgroundC[2]))    
            out.write('\t*SCENE_AMBIENT_STATIC %.4f %.4f %.4f\n' %(AmbientValue, AmbientValue, AmbientValue))
            out.write('}\n')

            #===============================================================================================
            #  MATERIAL LIST
            #===============================================================================================
            if EXPORT_MATERIALS:
                out.write('*MATERIAL_LIST {\n')
                out.write('\t*MATERIAL_COUNT %u\n' % GetMaterialCount())
                for indx, MeshObj in enumerate(ProjectContextScene.objects):
                        if MeshObj.type == 'MESH':
                            #Material
                            out.write('\t*MATERIAL %u {\n' % indx)

                            #Mesh Materials
                            if len(MeshObj.material_slots) > 0:
                                currentSubMat = 0

                                #Material Info                                    
                                MatData = bpy.data.materials[0]
                                DiffuseColor = MatData.diffuse_color
                                out.write('\t\t*MATERIAL_NAME "%s"\n' % MatData.name)
                                out.write('\t\t*MATERIAL_DIFFUSE %.4f %.4f %.4f\n' % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))
                                out.write('\t\t*MATERIAL_SPECULAR %u %u %u\n' % (MatData.specular_color[0], MatData.specular_color[1], MatData.specular_color[2]))
                                out.write('\t\t*MATERIAL_SHINE %.1f\n' % MatData.metallic)
                                out.write('\t\t*NUMSUBMTLS %u \n' % len(MeshObj.material_slots))

                                #Loop Trought Submaterials
                                for indx, Material_Data in enumerate(MeshObj.material_slots):
                                    MatData = bpy.data.materials[Material_Data.name]

                                    #Material has texture
                                    if MatData.node_tree.nodes.get('Image Texture', None):
                                        ImageNode = MatData.node_tree.nodes.get('Image Texture', None)
                                        ImageName = ImageNode.image.name
                                        DiffuseColor = MatData.diffuse_color

                                        #Submaterial
                                        out.write('\t\t*SUBMATERIAL %u {\n' % currentSubMat)
                                        out.write('\t\t\t*MATERIAL_NAME "%s"\n' % (os.path.splitext(ImageName)[0]))
                                        out.write('\t\t\t*MATERIAL_DIFFUSE %.4f %.4f %.4f\n' % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))
                                        out.write('\t\t\t*MATERIAL_SPECULAR %u %u %u\n' % (MatData.specular_color[0], MatData.specular_color[1], MatData.specular_color[2]))
                                        out.write('\t\t\t*MATERIAL_SHINE %.1f\n' % MatData.metallic)
                                        out.write('\t\t\t*MATERIAL_SELFILLUM %u\n' % int(MatData.use_preview_world))

                                        #Map Difuse
                                        out.write('\t\t\t*MAP_DIFFUSE {\n')
                                        out.write('\t\t\t\t*MAP_NAME "%s"\n' % (os.path.splitext(ImageName)[0]))
                                        out.write('\t\t\t\t*MAP_CLASS "%s"\n' % "Bitmap")
                                        out.write('\t\t\t\t*MAP_AMOUNT "%u"\n' % 1)
                                        out.write('\t\t\t\t*BITMAP "%s"\n' % (bpy.path.abspath(ImageNode.image.filepath)))
                                        out.write('\t\t\t}\n')

                                    #Material has no texture
                                    else:
                                        #Submaterial
                                        principled = next(n for n in MatData.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
                                        base_color = principled.inputs['Base Color']
                                        color = base_color.default_value

                                        out.write('\t\t*SUBMATERIAL %u {\n' % currentSubMat)
                                        out.write('\t\t\t*MATERIAL_NAME "%s"\n' % MatData.name)
                                        out.write('\t\t\t*MATERIAL_DIFFUSE %.4f %.4f %.4f\n' % ((color[0] * .5), (color[1] * .5), (color[2] * .5)))
                                        out.write('\t\t\t*MATERIAL_SPECULAR %u %u %u\n' % (MatData.specular_color[0], MatData.specular_color[1], MatData.specular_color[2]))
                                        out.write('\t\t\t*MATERIAL_SHINE %.1f\n' % MatData.metallic)
                                        out.write('\t\t\t*MATERIAL_SELFILLUM %u\n' % int(MatData.use_preview_world))

                                    out.write('\t\t}\n')
                                    currentSubMat += 1
                            out.write('\t}\n')
                out.write('}\n')

            #===============================================================================================
            #  GEOM OBJECT
            #=============================================================================================== 
            if 'MESH' in EXPORT_OBJECTTYPES:
                for indx, SceneObj in enumerate(ProjectContextScene.objects):
                    if SceneObj.type == 'MESH':
                        if hasattr(SceneObj, 'data'):
                            #===========================================[Clone Object]====================================================
                            depsgraph = bpy.context.evaluated_depsgraph_get()
                            ob_for_convert = SceneObj.evaluated_get(depsgraph)

                            try:
                                MeshObject = ob_for_convert.to_mesh()
                            except RuntimeError:
                                MeshObject = None
                            if MeshObject is None:
                                continue

                            #===========================================[Apply Matrix]====================================================
                            MeshObject.transform(EXPORT_GLOBAL_MATRIX @ SceneObj.matrix_world)
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

                            if EXPORT_VERTEXCOLORS:
                                #Get Vertex Colors List 
                                VertexColorList = []
                                for name, cl in bm.loops.layers.color.items():
                                    for tri in tris:
                                        for loop in tri:
                                            color = loop[cl] # gives a Vector((R, G, B, A))
                                            if color not in VertexColorList:
                                                VertexColorList.append(color)

                            #===========================================[Print Object Data]====================================================       
                            out.write('*GEOMOBJECT {\n')
                            out.write('\t*NODE_NAME "%s"\n' % SceneObj.name)

                            #Print Matrix Rotation
                            out.write('\t*NODE_TM {\n')
                            PrintNODE_TM(out, SceneObj)
                            out.write('\t}\n')

                            #Print Matrix Rotation again ¯\_(ツ)_/¯
                            out.write('\t*PIVOT_TM {\n')
                            PrintNODE_TM(out, SceneObj)
                            out.write('\t}\n')

                            #MESH Section
                            out.write('\t*MESH {\n')
                            out.write('\t\t*TIMEVALUE %u\n' % 0)
                            out.write('\t\t*MESH_NUMVERTEX %u\n' % len(VertexList))
                            out.write('\t\t*MESH_NUMFACES %u\n' % len(tris))

                            #Print Vertex List
                            out.write('\t\t*MESH_VERTEX_LIST {\n')
                            for idx, ListItem in enumerate(VertexList):
                                out.write('\t\t\t*MESH_VERTEX %u %.4f %.4f %.4f\n' % (idx, ListItem[0], ListItem[1], ListItem[2]))
                            out.write('\t\t}\n')

                            #Face Vertex Index
                            out.write('\t\t*MESH_FACE_LIST {\n')   
                            for i, tri in enumerate(tris):
                                out.write('\t\t\t*MESH_FACE %u: ' % i)
                                out.write('A: %u B: %u C: %u ' % (VertexList.index(tri[0].vert.co), VertexList.index(tri[1].vert.co), VertexList.index(tri[2].vert.co)))
                                out.write('AB: %u BC: %u CA: %u ' % (not tri[0].vert.hide, not tri[1].vert.hide, not tri[2].vert.hide))   
                                out.write('*MESH_SMOOTHING 1 ')
                                out.write('*MESH_MTLID %u\n' % tri[0].face.material_index)
                            out.write('\t\t}\n')

                            #Texture UVs
                            out.write('\t\t*MESH_NUMTVERTEX %u\n' % len(UVVertexList))
                            out.write('\t\t*MESH_TVERTLIST {\n')
                            for idx, TextUV in enumerate(UVVertexList):
                                out.write('\t\t\t*MESH_TVERT %u %.4f %.4f\n' % (idx, TextUV[0], TextUV[1]))
                            out.write('\t\t}\n')

                            #Face Layers UVs Index
                            layerIndex = 0
                            out.write('\t\t*MESH_NUMTFACELAYERS %u\n' % len(bm.loops.layers.uv.items()))
                            for name, uv_lay in bm.loops.layers.uv.items():
                                out.write('\t\t*MESH_TFACELAYER %u {\n' % layerIndex)
                                out.write('\t\t\t*MESH_NUMTVFACES %u \n' % len(bm.faces))
                                out.write('\t\t\t*MESH_TFACELIST {\n')           
                                for i, tri in enumerate(tris):
                                    out.write('\t\t\t\t*MESH_TFACE %u ' % i)
                                    out.write('%u %u %u\n' % (UVVertexList.index(tri[0][uv_lay].uv), UVVertexList.index(tri[1][uv_lay].uv), UVVertexList.index(tri[2][uv_lay].uv)))
                                out.write('\t\t\t}\n')
                                out.write('\t\t}\n')
                                layerIndex += 1

                            if EXPORT_VERTEXCOLORS:
                                #Vertex Colors List
                                out.write('\t\t*MESH_NUMCVERTEX %u\n' % len(VertexColorList))
                                out.write('\t\t*MESH_CVERTLIST {\n')
                                for idx, ColorArray in enumerate(VertexColorList):
                                    out.write('\t\t\t*MESH_VERTCOL %u %.4f %.4f %.4f %u\n' % (idx, (ColorArray[0] * .5), (ColorArray[1] * .5), (ColorArray[2] * .5), 1))
                                out.write('\t\t}\n')

                                #Face Color Vertex Index
                                layerIndex = 0
                                if len(bm.loops.layers.color.items()) > 0:
                                    out.write('\t\t*MESH_NUMCFACELAYERS %u\n' % len(bm.loops.layers.color.items()))
                                    for name, cl in bm.loops.layers.color.items():
                                        out.write('\t\t*MESH_CFACELAYER %u {\n' % layerIndex)
                                        out.write('\t\t\t*MESH_NUMCVFACES %u \n' % len(tris))
                                        out.write('\t\t\t*MESH_CFACELIST {\n')
                                        for i, tri in enumerate(tris):
                                            out.write('\t\t\t\t*MESH_CFACE %u ' % i)
                                            for loop in tri:
                                                out.write('%u ' % VertexColorList.index(loop[cl]))
                                            out.write('\n')
                                        out.write('\t\t\t}\n')
                                        out.write('\t\t}\n')
                                        layerIndex +=1

                            #Liberate BM Object
                            bm.free()

                            #Close blocks
                            out.write('\t}\n')
                            out.write('\t*MATERIAL_REF %u\n' % indx)
                            out.write('}\n')

            #===============================================================================================
            #  CAMERA OBJECT
            #===============================================================================================
            if 'CAMERA' in EXPORT_OBJECTTYPES:
                CamerasList = []

                for SceneObj in ProjectContextScene.objects:
                    if SceneObj.type == 'CAMERA':
                        CamerasList.append(SceneObj)
                CamerasList.sort(key = lambda o: o.name)

                for CameraObj in CamerasList:
                    if CameraObj.type == 'CAMERA':    
                        out.write('*CAMERAOBJECT {\n')
                        out.write('\t*NODE_NAME "%s"\n' % CameraObj.name)
                        out.write('\t*CAMERA_TYPE %s\n' % "Target")

                        #Print Matrix Rotation
                        out.write('\t*NODE_TM {\n')
                        PrintNODE_TM(out, CameraObj)
                        out.write('\t}\n')

                        #===============================================================================================
                        #  CAMERA SETTINGS
                        #=============================================================================================== 
                        out.write('\t*CAMERA_SETTINGS {\n')
                        out.write('\t\t*TIMEVALUE %u\n' % 0)
                        #out.write('\t\t*CAMERA_NEAR %.4f\n' % CameraObj.data.clip_start)
                        out.write('\t\t*CAMERA_NEAR %.4f\n' % 0)
                        out.write('\t\t*CAMERA_FAR %.4f\n'% CameraObj.data.clip_end)  
                        out.write('\t\t*CAMERA_FOV %.4f\n'% CameraObj.data.angle)
                        out.write('\t\t*CAMERA_TDIST %.4f\n'% 15.9229)
                        out.write('\t}\n')

                        #===============================================================================================
                        #  CAMERA ANIMATION
                        #===============================================================================================
                        if EXPORT_CAMERALIGHTANIMS:
                            out.write('\t*CAMERA_ANIMATION {\n')
                            
                            TimeValueCounter = 0
                            for f in range(ProjectContextScene.frame_start, ProjectContextScene.frame_end + 1):
                                ProjectContextScene.frame_set(f)

                                out.write('\t\t*CAMERA_SETTINGS {\n')
                                out.write('\t\t\t*TIMEVALUE %u\n' % TimeValueCounter)
                                #out.write('\t\t\t*CAMERA_NEAR %.4f\n' % CameraObj.data.clip_start)
                                out.write('\t\t\t*CAMERA_NEAR %.4f\n' % 0)
                                out.write('\t\t\t*CAMERA_FAR %.4f\n'% CameraObj.data.clip_end)  
                                out.write('\t\t\t*CAMERA_FOV %.4f\n'% CameraObj.data.angle)
                                out.write('\t\t\t*CAMERA_TDIST %.4f\n'% 15.9229)
                                out.write('\t\t}\n')

                                TimeValueCounter += TimeValue

                            out.write('\t}\n')

                        #===============================================================================================
                        #  ANIMATION
                        #===============================================================================================
                        if EXPORT_ANIMATION:
                            PrintTM_ANIMATION(out, CameraObj, TimeValue)

                        #===============================================================================================
                        #  USER DATA (ONLY FOR SCRIPTS)
                        #===============================================================================================
                        if CameraObj == CamerasList[-1] and len(CamerasList) > 1:
                            out.write('\t*USER_DATA %u {\n' % 0)
                            out.write('\t\tCameraScript = %u\n' % 1)
                            out.write('\t\tCameraScript_numCameras = %u\n' % len(CamerasList))
                            out.write('\t\tCameraScript_globalOffset = %u\n' % 0)

                            #Print Cameras Info
                            CameraNumber = 1
                            CamStart = 0
                            CamEnd = 0
                            for ob in CamerasList:
                                if ob.type == 'CAMERA':
                                    #Get Camera Keyframes
                                    if ob.animation_data:
                                        if ob.animation_data.action is not None:
                                            Keyframe_Points_list = []
                                            for curve in ob.animation_data.action.fcurves:
                                                for key in curve.keyframe_points:
                                                    key_idx = int(key.co[0])
                                                    if key_idx not in Keyframe_Points_list:
                                                        Keyframe_Points_list.append(key_idx)
                                            #Calculate EuroLand Start
                                            CamEnd = CamStart + (Keyframe_Points_list[-1] - Keyframe_Points_list[0])
                                            out.write('\t\tCameraScript_camera%u = %s %u %u %u %u\n' % (CameraNumber, ob.name, Keyframe_Points_list[0], Keyframe_Points_list[-1], CamStart, CamEnd))
                                            #Calculate EuroLand End
                                            CamStart += Keyframe_Points_list[-1] + 1
                                            CameraNumber += 1
                            out.write('\t}\n')

                        out.write('}\n')

            #===============================================================================================
            #  LIGHT OBJECT
            #===============================================================================================
            if 'LIGHT' in EXPORT_OBJECTTYPES:
                for SceneObj in ProjectContextScene.objects:
                    if SceneObj.type == 'LIGHT':
                        out.write('*LIGHTOBJECT {\n')
                        out.write('\t*NODE_NAME "%s"\n' % SceneObj.name)
                        out.write('\t*NODE_PARENT "%s"\n' % SceneObj.name)

                        type_lut={}
                        type_lut['POINT']='Omni'
                        type_lut['SPOT' ]='TargetSpot'
                        type_lut['SUN'  ]='TargetDirect'
                        type_lut['AREA' ]='TargetDirect' # swy: this is sort of wrong ¯\_(ツ)_/¯

                        out.write('\t*LIGHT_TYPE %s\n' % type_lut[SceneObj.data.type]) #Seems that always used "Omni" lights in 3dsMax, in blender is called "Point"

                        #Print Matrix Rotation
                        out.write('\t*NODE_TM {\n')
                        PrintNODE_TM(out, SceneObj)
                        out.write('\t}\n')

                        #---------------------------------------------[Light Props]---------------------------------------------
                        out.write('\t*LIGHT_DECAY %s\n' % "InvSquare") # swy: this is the only supported mode
                        out.write('\t*LIGHT_AFFECT_DIFFUSE %s\n' % "Off") #for now
                        if (SceneObj.data.specular_factor > 0.001):
                            out.write('\t*LIGHT_AFFECT_SPECULAR %s\n' % "On") #for now
                        else:
                            out.write('\t*LIGHT_AFFECT_SPECULAR %s\n' % "Off") #for now
                        out.write('\t*LIGHT_AMBIENT_ONLY %s\n' % "Off") #for now

                        #---------------------------------------------[Light Settings]---------------------------------------------           
                        out.write('\t*LIGHT_SETTINGS {\n')
                        out.write('\t\t*TIMEVALUE %u\n' % 0)
                        out.write('\t\t*COLOR %.4f %.4f %.4f\n' % (SceneObj.data.color.r, SceneObj.data.color.g, SceneObj.data.color.b))
                        out.write('\t\t*FAR_ATTEN %.4f %.4f\n' % (SceneObj.data.distance, SceneObj.data.cutoff_distance))
                        if (SceneObj.data.type == 'SUN'):
                            out.write('\t\t*HOTSPOT %u\n' % math.degrees(SceneObj.data.angle))
                        else:
                            out.write('\t\t*HOTSPOT %u\n' % 0)
                        out.write('\t}\n')

                        #===============================================================================================
                        #  LIGHT ANIMATION
                        #=============================================================================================== 
                        if EXPORT_CAMERALIGHTANIMS:
                            out.write('\t*LIGHT_ANIMATION {\n')

                            TimeValueCounter = 0
                            for f in range(ProjectContextScene.frame_start, ProjectContextScene.frame_end + 1):
                                ProjectContextScene.frame_set(f)

                                out.write('\t\t*LIGHT_SETTINGS {\n')
                                out.write('\t\t\t*TIMEVALUE %u\n' % TimeValueCounter)
                                out.write('\t\t\t*COLOR %.4f %.4f %.4f\n' % (SceneObj.data.color.r, SceneObj.data.color.g, SceneObj.data.color.b))
                                out.write('\t\t\t*FAR_ATTEN %.4f %.4f\n' % (SceneObj.data.distance, SceneObj.data.cutoff_distance))
                                if (SceneObj.data.type == 'SUN'):
                                    out.write('\t\t\t*HOTSPOT %u\n' % math.degrees(SceneObj.data.angle))
                                else:
                                    out.write('\t\t\t*HOTSPOT %u\n' % 0)
                                out.write('\t\t}\n')

                                TimeValueCounter += TimeValue

                            out.write('\t}\n')

                        #===============================================================================================
                        #  ANIMATION
                        #===============================================================================================
                        if EXPORT_ANIMATION:
                            PrintTM_ANIMATION(out, SceneObj, TimeValue)

                        #Close light object
                        out.write('}\n')
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