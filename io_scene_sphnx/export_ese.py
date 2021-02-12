"""
Name: 'EuroRGT'
Blender: 2.90.1
Group: 'Export'
Tooltip: 'Blender ESE Exporter for EuroLand'
Authors: Swyter and Jmarti856
"""
import bpy
import os
import math
import datetime
from mathutils import *
from math import *
from pathlib import Path
from bpy_extras.io_utils import axis_conversion 


#===============================================================================================
#  Main Method
#===============================================================================================
def WriteFile():
    #===============================================================================================
    #  Global Vars
    #===============================================================================================
    mtx_conv = axis_conversion(to_forward='-Z', to_up='Y')
    global_matrix = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0)))
    ProjectContextScene = bpy.context.scene
                  
    #===============================================================================================
    #  WRITE HEADER
    #===============================================================================================
    # Stop edit mode
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    
    #Create new file
    out = open(str(Path.home()) + "\\Desktop\\CameraExporter.ESE", "w")
    
    #Start writting
    out.write('*3DSMAX_EUROEXPORT	300\n')
    out.write('*COMMENT "Eurocom Export Version  3.00" - %s\n' % (datetime.datetime.utcnow()).strftime('%A %B %d %H:%M:%S %Y'))
    out.write('*COMMENT "Version of Blender that output this file: %s\n' % bpy.app.version_string)
    out.write('*COMMENT "Version of ESE Plug-in: 5.0.0.13"\n')
    out.write("\n")
    
    #===============================================================================================
    #  SCENE INFO
    #=============================================================================================== 
    AmbientValue = bpy.context.scene.world.light_settings.ao_factor
    
    out.write('*SCENE {\n')
    out.write('\t*SCENE_FILENAME "%s"\n' % os.path.basename(bpy.data.filepath))
    out.write('\t*SCENE_FIRSTFRAME %d\n' % ProjectContextScene.frame_start)
    out.write('\t*SCENE_LASTFRAME %d\n' % ProjectContextScene.frame_end)
    
    #For some reason works in the console but not in this script  ¯\_(ツ)_/¯
    #out.write('\t*SCENE_FRAMESPEED "%d"' %  ProjectContextScene.render.fps)
    #out.write('\t*SCENE_TICKSPERFRAME "%d"' % (4800/fps))
    out.write('\t*SCENE_FRAMESPEED 30\n')
    out.write('\t*SCENE_TICKSPERFRAME 160\n')
    out.write('\t*AMBIENTSTATIC %.4f %.4f %.4f\n' %(AmbientValue, AmbientValue, AmbientValue))
    out.write('}\n')
    
    #===============================================================================================
    #  Camera Object
    #=============================================================================================== 
    for SceneObj in ProjectContextScene.objects:
        if SceneObj.type == 'CAMERA':
            TimeValue = 160
            #===============================================================================================
            #  NODE
            #=============================================================================================== 
            ProjectContextScene.frame_set(ProjectContextScene.frame_start)         
            loc_conv = mtx_conv @ SceneObj.location
            loc_conv.z = -loc_conv.z
            
            FieldOfView = math.degrees(2 * math.atan(SceneObj.data.sensor_width /(2 * SceneObj.data.lens)))

            #---------------------------------------------[Get Rotation matrix]---------------------------------------------                        
            CameraMatrixRot = SceneObj.rotation_euler.to_matrix()
            RotationMatrix = global_matrix @ CameraMatrixRot
            
            #---------------------------------------------[Write Data To File]---------------------------------------------
            out.write('*CAMERAOBJECT {\n')
            out.write('\t*NODE_NAME "%s"\n' % SceneObj.name)
            out.write('\t*CAMERA_TYPE %s\n' % "Target")            
            out.write('\t*NODE_TM {\n')
            out.write('\t\t*NODE_NAME "%s"\n' % SceneObj.name)
            out.write('\t\t*INHERIT_POS %d %d %d\n' % (0, 0, 0))
            out.write('\t\t*INHERIT_ROT %d %d %d\n' % (0, 0, 0))
            out.write('\t\t*INHERIT_SCL %d %d %d\n' % (1, 1, 1))    
            out.write('\t\t*TM_ROW0 %.4f %.4f %.4f\n' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
            out.write('\t\t*TM_ROW1 %.4f %.4f %.4f\n' % (RotationMatrix[1].x, RotationMatrix[1].y, RotationMatrix[1].z))
            out.write('\t\t*TM_ROW2 %.4f %.4f %.4f\n' % (RotationMatrix[2].x, RotationMatrix[2].y, RotationMatrix[2].z))
            out.write('\t\t*TM_ROW3 %.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))
            out.write('\t\t*TM_POS %.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))
            out.write('\t\t*TM_ROTANGLE %.4f %.4f %.4f\n' % (math.radians(SceneObj.rotation_euler.x), math.radians(SceneObj.rotation_euler.y),math.radians(SceneObj.rotation_euler.z)))
            out.write('\t\t*TM_SCALE %.4f %.4f %.4f\n' % (SceneObj.scale.x, SceneObj.scale.y,SceneObj.scale.z))            
            out.write('\t\t*TM_SCALEANGLE %.4f %.4f %.4f\n' % (0, 0, 0))
            out.write('\t}\n')
            
            #===============================================================================================
            #  CAMERA SETTINGS
            #=============================================================================================== 
            out.write('\t*CAMERA_SETTINGS {\n')
            out.write('\t\t*TIMEVALUE %d\n' % TimeValue) #needs checking
            out.write('\t\t*CAMERA_NEAR %.4f\n' % SceneObj.data.clip_start)
            out.write('\t\t*CAMERA_FAR %.4f\n'% SceneObj.data.clip_end)  
            out.write('\t\t*CAMERA_FOV %.4f\n'% FieldOfView)
            out.write('\t\t*CAMERA_TDIST %.4f\n'% 32.1137)
        
            out.write('\t}\n')
            
            #===============================================================================================
            #  ANIMATION
            #=============================================================================================== 
            TimeValueCounter = 0            
            out.write('\t*TM_ANIMATION {\n')
            out.write('\t\t*NODE_NAME "%s"\n' % SceneObj.name)
            out.write('\t\t*TM_ANIM_FRAMES {\n')
            
            for f in range(ProjectContextScene.frame_start, ProjectContextScene.frame_end + 1):
                ProjectContextScene.frame_set(f)
                
                #---------------------------------------------[Get Position]---------------------------------------------
                loc_conv = mtx_conv @ SceneObj.location
                loc_conv.z = -loc_conv.z
            
                #---------------------------------------------[Get Rotation matrix]---------------------------------------------   
                CameraMatrixRot = SceneObj.rotation_euler.to_matrix()
                RotationMatrix = global_matrix @ CameraMatrixRot
                
                #Write Time Value
                out.write('\t\t\t*TM_FRAME %d ' % TimeValueCounter)
                
                #Write Matrix
                out.write('%.4f %.4f %.4f ' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
                out.write('%.4f %.4f %.4f ' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
                out.write('%.4f %.4f %.4f ' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
                
                #Write Position
                out.write('%.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))
                
                #Update counter
                TimeValueCounter += TimeValue            
            out.write('\t\t}\n')
            out.write('\t}\n') 

    out.write('}\n')
    #Close File
    out.close()
WriteFile()