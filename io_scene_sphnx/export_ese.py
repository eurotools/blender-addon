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
import datetime
from mathutils import *
from math import *
from pathlib import Path
from bpy_extras.io_utils import axis_conversion 

#===============================================================================================
#  GLOBAL VARIABLES
#===============================================================================================
mtx_conv = axis_conversion(to_forward='-Z', to_up='Y')
global_matrix = Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0)))
ProjectContextScene = bpy.context.scene


#===============================================================================================
#  FUNCTIONS
#===============================================================================================
def PrintNODE_TM(OutputFile, SceneObject):
        ProjectContextScene.frame_set(ProjectContextScene.frame_start)
        
        loc_conv = mtx_conv @ SceneObject.location
        loc_conv.z = -loc_conv.z
                    
        CameraMatrixRot = SceneObject.rotation_euler.to_matrix()
        RotationMatrix = global_matrix @ CameraMatrixRot
       
        OutputFile.write('\t*NODE_TM {\n')
        OutputFile.write('\t\t*NODE_NAME "%s"\n' % SceneObject.name)
        OutputFile.write('\t\t*INHERIT_POS %d %d %d\n' % (0, 0, 0))
        OutputFile.write('\t\t*INHERIT_ROT %d %d %d\n' % (0, 0, 0))
        OutputFile.write('\t\t*INHERIT_SCL %d %d %d\n' % (1, 1, 1))    
        OutputFile.write('\t\t*TM_ROW0 %.4f %.4f %.4f\n' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
        OutputFile.write('\t\t*TM_ROW1 %.4f %.4f %.4f\n' % (RotationMatrix[1].x, RotationMatrix[1].y, RotationMatrix[1].z))
        OutputFile.write('\t\t*TM_ROW2 %.4f %.4f %.4f\n' % (RotationMatrix[2].x, RotationMatrix[2].y, RotationMatrix[2].z))
        OutputFile.write('\t\t*TM_ROW3 %.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))
        OutputFile.write('\t\t*TM_POS %.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))
        OutputFile.write('\t\t*TM_ROTANGLE %.4f %.4f %.4f\n' % (math.radians(SceneObject.rotation_euler.x), math.radians(SceneObject.rotation_euler.y),math.radians(SceneObject.rotation_euler.z)))
        OutputFile.write('\t\t*TM_SCALE %.4f %.4f %.4f\n' % (SceneObject.scale.x, SceneObject.scale.y,SceneObject.scale.z))            
        OutputFile.write('\t\t*TM_SCALEANGLE %.4f %.4f %.4f\n' % (0, 0, 0))
        OutputFile.write('\t}\n')
        
def PrintTM_ANIMATION(OutputFile, SceneObject, TimeValue):
        OutputFile.write('\t*TM_ANIMATION {\n')
        OutputFile.write('\t\t*NODE_NAME "%s"\n' % SceneObject.name)
        OutputFile.write('\t\t*TM_ANIM_FRAMES {\n')
        
        TimeValueCounter = 0
        for f in range(ProjectContextScene.frame_start, ProjectContextScene.frame_end + 1):
            ProjectContextScene.frame_set(f)
            
            #---------------------------------------------[Get Position]---------------------------------------------
            loc_conv = mtx_conv @ SceneObject.location
            loc_conv.z = -loc_conv.z
        
            #---------------------------------------------[Get Rotation matrix]---------------------------------------------   
            CameraMatrixRot = SceneObject.rotation_euler.to_matrix()
            RotationMatrix = global_matrix @ CameraMatrixRot
            
            #Write Time Value
            OutputFile.write('\t\t\t*TM_FRAME %d ' % TimeValueCounter)
            
            #Write Matrix
            OutputFile.write('%.4f %.4f %.4f ' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
            OutputFile.write('%.4f %.4f %.4f ' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
            OutputFile.write('%.4f %.4f %.4f ' % (RotationMatrix[0].x, RotationMatrix[0].y, RotationMatrix[0].z))
            
            #Write Position
            OutputFile.write('%.4f %.4f %.4f\n' % (loc_conv.x, loc_conv.y, loc_conv.z))
            
            #Update counter
            TimeValueCounter += TimeValue            
        OutputFile.write('\t\t}\n')
        OutputFile.write('\t}\n')    
                
#===============================================================================================
#  Main Method
#===============================================================================================
def WriteFile():
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
    TimeValue = 4800/ProjectContextScene.render.fps
    
    out.write('*SCENE {\n')
    out.write('\t*SCENE_FILENAME "%s"\n' % os.path.basename(bpy.data.filepath))
    out.write('\t*SCENE_FIRSTFRAME %d\n' % ProjectContextScene.frame_start)
    out.write('\t*SCENE_LASTFRAME %d\n' % ProjectContextScene.frame_end)
    out.write('\t*SCENE_FRAMESPEED %d\n' %  ProjectContextScene.render.fps)
    out.write('\t*SCENE_TICKSPERFRAME %d\n' % TimeValue)
    out.write('\t*AMBIENTSTATIC %.4f %.4f %.4f\n' %(AmbientValue, AmbientValue, AmbientValue))
    out.write('}\n')
    
    #===============================================================================================
    #  Camera Object
    #=============================================================================================== 
    for SceneObj in ProjectContextScene.objects:
        if SceneObj.type == 'CAMERA':    
            out.write('*CAMERAOBJECT {\n')
            out.write('\t*NODE_NAME "%s"\n' % SceneObj.name)
            out.write('\t*CAMERA_TYPE %s\n' % "Target")
            
            PrintNODE_TM(out, SceneObj)
            
            #===============================================================================================
            #  CAMERA SETTINGS
            #=============================================================================================== 
            FieldOfView = math.degrees(2 * math.atan(SceneObj.data.sensor_width /(2 * SceneObj.data.lens)))
            out.write('\t*CAMERA_SETTINGS {\n')
            out.write('\t\t*TIMEVALUE %d\n' % 0)
            out.write('\t\t*CAMERA_NEAR %.4f\n' % SceneObj.data.clip_start)
            out.write('\t\t*CAMERA_FAR %.4f\n'% SceneObj.data.clip_end)  
            out.write('\t\t*CAMERA_FOV %.4f\n'% FieldOfView)
            out.write('\t\t*CAMERA_TDIST %.4f\n'% 32.1137)
            out.write('\t}\n')
   
            #===============================================================================================
            #  CAMERA ANIMATION
            #===============================================================================================  
            out.write('\t*CAMERA_ANIMATION {\n')

            TimeValueCounter = 0
            for f in range(ProjectContextScene.frame_start, ProjectContextScene.frame_end + 1):
                ProjectContextScene.frame_set(f)
                
                FieldOfView = math.degrees(2 * math.atan(SceneObj.data.sensor_width /(2 * SceneObj.data.lens)))
                out.write('\t\t*CAMERA_SETTINGS {\n')
                out.write('\t\t\t*TIMEVALUE %d\n' % 0)
                out.write('\t\t\t*CAMERA_NEAR %.4f\n' % SceneObj.data.clip_start)
                out.write('\t\t\t*CAMERA_FAR %.4f\n'% SceneObj.data.clip_end)  
                out.write('\t\t\t*CAMERA_FOV %.4f\n'% FieldOfView)
                out.write('\t\t\t*CAMERA_TDIST %.4f\n'% 32.1137)
                out.write('\t\t}\n')
                
                TimeValueCounter += TimeValue
                
            out.write('\t}\n')
            
            #===============================================================================================
            #  ANIMATION
            #===============================================================================================                         
            PrintTM_ANIMATION(out, SceneObj, TimeValue)
            out.write('}\n')
            
    #===============================================================================================
    #  Ligth Object
    #===============================================================================================
    for SceneObj in ProjectContextScene.objects:
        if SceneObj.type == 'LIGHT':
            out.write('*LIGHTOBJECT {\n')
            out.write('\t*NODE_NAME "%s"\n' % SceneObj.name)
            out.write('\t*NODE_PARENT "%s"\n' % SceneObj.name)
            out.write('\t*LIGHT_TYPE %s\n' % "Omni") #Seems that always used "Omni" lights in 3dsMax, in blender is called "Point"
            
            PrintNODE_TM(out, SceneObj)
            
            #---------------------------------------------[Light Props]---------------------------------------------
            out.write('\t*LIGHT_DECAY %s\n' % "None") #for now
            out.write('\t*LIGHT_AFFECT_DIFFUSE %s\n' % "Off") #for now
            if (SceneObj.data.specular_factor > 0.001):
                out.write('\t*LIGHT_AFFECT_SPECULAR %s\n' % "On") #for now
            else:
                out.write('\t*LIGHT_AFFECT_SPECULAR %s\n' % "Off") #for now
            out.write('\t*LIGHT_AMBIENT_ONLY %s\n' % "Off") #for now
            
            #---------------------------------------------[Light Settings]---------------------------------------------           
            out.write('\t*LIGHT_SETTINGS {\n')
            out.write('\t\t*TIMEVALUE %d\n' % 0)
            out.write('\t\t*LIGHT_COLOR %.4f %.4f %.4ff\n' % (SceneObj.data.color.r * 1, SceneObj.data.color.g * 1, SceneObj.data.color.b * 1))
            out.write('\t\t*FAR_ATTEN %d %d\n' % (SceneObj.data.distance, SceneObj.data.cutoff_distance))
            if (SceneObj.data.type == 'SUN'):
                out.write('\t\t*HOTSPOT %d\n' % math.degrees(SceneObj.data.angle))
            else:
                out.write('\t\t*HOTSPOT %d\n' % 0)
            out.write('\t}\n')
            
            #===============================================================================================
            #  LIGHT ANIMATION
            #===============================================================================================  
            out.write('\t*LIGHT_ANIMATION {\n')

            TimeValueCounter = 0
            for f in range(ProjectContextScene.frame_start, ProjectContextScene.frame_end + 1):
                ProjectContextScene.frame_set(f)
                
                out.write('\t\t*LIGHT_SETTINGS {\n')
                out.write('\t\t\t*TIMEVALUE %d\n' % TimeValueCounter)
                out.write('\t\t\t*LIGHT_COLOR %.4f %.4f %.4f\n' % (SceneObj.data.color.r * 1, SceneObj.data.color.g * 1, SceneObj.data.color.b * 1))
                out.write('\t\t*FAR_ATTEN %d %d\n' % (SceneObj.data.distance, SceneObj.data.cutoff_distance))
                if (SceneObj.data.type == 'SUN'):
                    out.write('\t\t*HOTSPOT %d\n' % math.degrees(SceneObj.data.angle))
                else:
                    out.write('\t\t*HOTSPOT %d\n' % 0)
                out.write('\t}\n')
                
                TimeValueCounter += TimeValue
                
            out.write('\t}\n')
            
            #===============================================================================================
            #  ANIMATION
            #===============================================================================================                         
            PrintTM_ANIMATION(out, SceneObj, TimeValue)
                        
            #Close ligth object
            out.write('}\n')
    #Close File
    out.close()
WriteFile()