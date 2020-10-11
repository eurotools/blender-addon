import bpy
import os
import math
from mathutils import *
from math import *
from pathlib import Path
from bpy_extras.io_utils import axis_conversion
from bpy import context

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
    out = open(str(Path.home()) + "\\Desktop\\TestEIF.EIF", "w")

    #Get scene info
    scn = bpy.context.scene 

    def GetMaterials():
        MaterialIndex = 0
            
        out.write("*MATERIALS {\n")
        
        for obj in bpy.context.scene.objects:
            for s in obj.material_slots:
                if s.material and s.material.use_nodes:
                    for n in s.material.node_tree.nodes:
                        if n.type == 'TEX_IMAGE':                
                            out.write("\t*MATERIAL %d {\n" % (MaterialIndex))
                            out.write("\t\t*NAME \"%s\"\n" % (os.path.splitext(n.image.name)[0]))                    
                            out.write("\t\t*MAP_DIFFUSE \"%s\"\n" % (bpy.path.abspath(n.image.filepath)))      
                            #Check if the texture exists
                            if (os.path.exists(bpy.path.abspath(n.image.filepath))):
                                out.write("\t\t*TWOSIDED True\n")
                            else:
                                out.write("\t\t*TWOSIDED False\n")
                            out.write("\t\t*MAP_DIFFUSE_AMOUNT 1.0\n")
                            
                            #Add 1 to the materials index
                            MaterialIndex +=1
        out.write("\t}\n")
        out.write("}\n\n")
        
    def GetMesh():
        for ob in scn.objects:
            if ob.type == 'MESH':
                me = ob.data
                uv_layer = me.uv_layers.active.data
                  
                out.write("*MESH {\n")    
                out.write("\t*NAME %s\n" % (me.name))
                out.write("\t*VERTCOUNT %d\n" % (len(me.vertices)))
                out.write("\t*FACECOUNT %d\n" % (len(me.polygons)))
                out.write("\t*FACELAYERSCOUNT 1\n")
                out.write("\t*FACESHADERCOUNT 1\n")
                out.write("\t*VERTEX_LIST {\n")
                for v in ob.data.vertices:
                    out.write("\t\t%.6f %.6f %.6f\n" % (v.co.x, v.co.y, v.co.z))
                out.write("\t}\n")
                out.write("\t*UV_LIST {\n")            
                for poly in me.polygons:
                    for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                        out.write("\t\t%.6f %.6f\n" % (uv_layer[loop_index].uv.x, uv_layer[loop_index].uv.y))
                out.write("\t}\n")
                out.write("\t*VERTCOL_LIST {\n")

                out.write("\t}\n")

    #Script header
    out.write("*EUROCOM_INTERCHANGE_FILE 100\n")
    out.write("*COMMENT Eurocom Interchange File Version 1.00 Monday January 06 2003 12:13\n\n")
    out.write("*OPTIONS {\n")
    out.write("\t*COORD_SYSTEM LH\n")
    out.write("}\n\n")
        
    #print scene info
    out.write("*SCENE {\n")
    out.write("\t*FIRSTFRAME %d\n" % (scn.frame_start))
    out.write("\t*LASTFRAME %d\n" % (scn.frame_end))
    out.write("\t*FRAMESPEED %d\n" % (scn.render.fps))  
    out.write("\t*STATICFRAME 0\n")
    out.write("\t*AMBIENTSTATIC 1.0 1.0 1.0\n")
    out.write("}\n\n")
    
    #Write materials
    GetMaterials()
    
    #Write Meshes
    GetMesh()
    
    #Close writer
    out.close()

    return {'FINISHED'}