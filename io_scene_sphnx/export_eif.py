import bpy
import os
import math
import datetime
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
    out = open(filepath, "w")
    
    print("exporting", filepath)

    #Get scene info
    scn = bpy.context.scene 
    ow  = out.write
 
    def GetMaterials():
        MaterialIndex = 0
            
        ow("*MATERIALS {\n")
        
        for obj in bpy.context.scene.objects:
            for s in obj.material_slots:
                if s.material and s.material.use_nodes:
                    for n in s.material.node_tree.nodes:
                        if n.type == 'TEX_IMAGE':                
                            ow("\t*MATERIAL %d {\n" % (MaterialIndex))
                            ow("\t\t*NAME \"%s\"\n" % (os.path.splitext(n.image.name)[0]))                    
                            ow("\t\t*MAP_DIFFUSE \"%s\"\n" % (bpy.path.abspath(n.image.filepath)))      
                            #Check if the texture exists
                            if (os.path.exists(bpy.path.abspath(n.image.filepath))):
                                ow("\t\t*TWOSIDED True\n")
                            else:
                                ow("\t\t*TWOSIDED False\n")
                            ow("\t\t*MAP_DIFFUSE_AMOUNT 1.0\n")
                            
                            #Add 1 to the materials index
                            MaterialIndex +=1
        ow("\t}\n")
        ow("}\n\n")
        
    def GetMesh():
        for ob in scn.objects:
            if ob.type == 'MESH':
                me = ob.data
                uv_layer = me.uv_layers.active.data
                  
                ow("*MESH {\n")    
                ow("\t*NAME %s\n" % (me.name))
                ow("\t*VERTCOUNT %d\n" % (len(me.vertices)))
                ow("\t*FACECOUNT %d\n" % (len(me.polygons)))
                ow("\t*FACELAYERSCOUNT 1\n")
                ow("\t*FACESHADERCOUNT 1\n")
                ow("\t*VERTEX_LIST {\n")
                for v in me.vertices:
                    ow("\t\t%.6f %.6f %.6f\n" % (v.co.x, v.co.y, v.co.z))
                ow("\t}\n")
                ow("\t*UV_LIST {\n")            
                for poly in me.polygons:
                    for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                        ow("\t\t%.6f %.6f\n" % (uv_layer[loop_index].uv.x, uv_layer[loop_index].uv.y))
                ow("\t}\n")
                
                #Check if the vertex colors layer is active
                if(bool(me.vertex_colors.active)):
                    ow("\t*VERTCOL_LIST {\n")
                    for v in me.vertex_colors[0].data:
                        ow("\t\t%.6f %.6f %.6f %.6f\n" % (v.color[0], v.color[1], v.color[2], v.color[3]))                    
                    ow("\t}\n")

    time_now = datetime.datetime.utcnow()

    #Script header
    ow("*EUROCOM_INTERCHANGE_FILE 100\n")
    ow("*COMMENT Eurocom Interchange File Version 1.00 %s\n\n" % time_now.strftime("%A %B %d %Y %H:%M"))
    ow("*OPTIONS {\n")
    ow("\t*COORD_SYSTEM LH\n")
    ow("}\n\n")

    #print scene info
    ow("*SCENE {\n")
    ow("\t*FIRSTFRAME %d\n" % (scn.frame_start))
    ow("\t*LASTFRAME %d\n" % (scn.frame_end))
    ow("\t*FRAMESPEED %d\n" % (scn.render.fps))  
    ow("\t*STATICFRAME 0\n")
    ow("\t*AMBIENTSTATIC 1.0 1.0 1.0\n")
    ow("}\n\n")

    #Write materials
    GetMaterials()

    #Write Meshes
    GetMesh()

    #Close writer
    out.close()

    return {'FINISHED'}
    
    
if __name__ == "__main__":
    save({}, str(Path.home()) + "\\Desktop\\TestEIF.EIF")