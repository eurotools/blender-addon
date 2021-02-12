"""
Name: 'EuroRGT'
Blender: 2.90.1
Group: 'Export'
Tooltip: 'Blender RTG Exporter for EuroLand'
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

def write():
    ProjectContextScene = bpy.context.scene


    # Stop edit mode
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
            
    #===============================================================================================
    #  WRITE HEADER
    #===============================================================================================
    out = open(str(Path.home()) + "\\Desktop\\CameraExporter.ESE", "w")
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
            out.write('*CAMERAOBJECT {\n')
            out.write('\t*NODE_NAME "%s"\n' % SceneObj.name)
            out.write('\t*CAMERA_TYPE %s\n' % "Target")
            out.write('\t*NODE_TM {\n')
            out.write('\t\t*NODE_NAME "%s"\n' % SceneObj.name)
            out.write('\t\t*INHERIT_POS "%d %d %d"\n' % (0, 0, 0))
            out.write('\t\t*INHERIT_ROT "%d %d %d"\n' % (0, 0, 0))
            out.write('\t\t*INHERIT_SCL "%d %d %d"\n' % (1, 1, 1))    
    
    
    
    #Close File
    out.close()
write()