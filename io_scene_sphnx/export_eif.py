import bpy
import os
import math
import datetime
from mathutils import *
from math import *
from pathlib import Path
from bpy_extras.io_utils import axis_conversion
from bpy import context
from pprint import pprint

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
    
    print("[i] exporting", filepath)

    #Get scene info
    scn = bpy.context.scene 
    ow  = out.write
 
    def GetMaterials():
        MaterialIndex = 0
            
        ow("*MATERIALS {\n")
        
        for obj in bpy.context.scene.objects:
            for s in obj.material_slots:
                if s.material and s.material.use_nodes:
                    DiffuseColor = s.material.diffuse_color
                    for n in s.material.node_tree.nodes:
                        if n.type == 'TEX_IMAGE':                
                            ow("  *MATERIAL %d {\n" % (MaterialIndex))
                            ow("    *NAME \"%s\"\n" % (os.path.splitext(n.image.name)[0]))
                            ow("    *COL_DIFFUSE %.6f %.6f %.6f\n" % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))
                            ow("    *MAP_DIFFUSE \"%s\"\n" % (bpy.path.abspath(n.image.filepath)))      
                            #Check if the texture exists
                            if (os.path.exists(bpy.path.abspath(n.image.filepath))):
                                ow("    *TWOSIDED\n")
                            ow("    *MAP_DIFFUSE_AMOUNT 1.0\n")
                            
                            #Add 1 to the materials index
                            MaterialIndex +=1
        ow("  }\n")
        ow("}\n\n")
        
    def GetMesh():
        for ob in scn.objects:
            #Invert 'Y' 'Z'
            m = axis_conversion("Y", "Z", "Z", "Y").to_4x4()
            ob.matrix_world = m * ob.matrix_world
            
            if ob.hide_viewport:
                continue
            
            if ob.type == 'MESH':
                me = ob.data
                uv_layer = me.uv_layers.active.data

                VertexList = []
                UVList = []
                VertColList = []
                
                #==================GET VERTEX LIST==============================
                for vertex in me.vertices:
                    VertexList.append("%.6f,%.6f,%.6f" % (vertex.co.x,vertex.co.z,vertex.co.y))
 
                 #==================GET UV LIST==============================
                if len(me.vertex_colors):
                    for pl_count, poly in enumerate(me.polygons):
                        for li_count, loop_index in enumerate(poly.loop_indices):
                            print(pl_count, li_count, loop_index, "uv_layer len:", len(uv_layer))
                            UVList.append("%.6f,%.6f" % (uv_layer[loop_index].uv.x,uv_layer[loop_index].uv.y))
                        
                 #==================GET Vertex Color LIST==============================               
                if len(me.vertex_colors):
                    for vertex in me.vertex_colors.active.data:
                        VertColList.append("%.6f,%.6f,%.6f,%.6f" % (vertex.color[0],vertex.color[1],vertex.color[2],vertex.color[3]))
                
                #===================COUNT TRIS======================
                for face in me.polygons:
                    vertices = face.vertices
                        
                #==================PRINT DATA==============================
                ow("*MESH {\n")    
                ow("  *NAME \"%s\"\n" % (me.name))
                ow("  *VERTCOUNT %d\n" % (len(VertexList)))
                ow("  *UVCOUNT %d\n" % (len(UVList)))
                if(len(VertColList) > 0):
                    ow("  *VERTCOLCOUNT %d\n" % (len(VertColList)))
                ow("  *FACECOUNT %d\n" % (len(me.polygons)))
                ow("  *FACELAYERSCOUNT %d\n" % len(me.uv_layers))
                
                #Check if there are more than one layer
                if (len(me.uv_layers) > 1):
                    ow("  *FACESHADERCOUNT %d\n" % len(me.uv_layers))
                
                #Print Vertex data
                ow("  *VERTEX_LIST {\n")
                for list_item in VertexList:
                    dataSplit = list_item.split(",")
                    ow("    %s %s %s\n" % (dataSplit[0], dataSplit[1], dataSplit[2]))
                ow("  }\n")
                
                #Print UV data
                ow("  *UV_LIST {\n")
                for list_item in UVList:
                    dataSplit = list_item.split(",")
                    ow("    %s %s\n" % (dataSplit[0], dataSplit[1]))
                ow("  }\n")
                
                #Check if the vertex colors layer is active
                if(len(VertColList) > 0):
                    ow("  *VERTCOL_LIST {\n")
                    for list_item in VertColList:
                        dataSplit = list_item.split(",")
                        ow("    %s %s %s %s\n" % (dataSplit[0], dataSplit[1], dataSplit[2], dataSplit[3]))                    
                    ow("  }\n")
                    
                #Print Shader faces
                if (len(me.uv_layers) > 1):
                    ow("  *FACESHADERS {\n")
                    ow("  }\n")
                ow("  *FACEFORMAT VTC\n")
                
                uv_index = 0
                co_index = 0
                
                #Print Face list
                ow("  *FACE_LIST {\n")
                for poly in me.polygons:
                    #Get polygon vertices
                    PolygonVertices = poly.vertices
                    TotalIndexVertex = []
                    #Write vertices
                    ow("    %d " % (len(PolygonVertices)))
                    for vert in PolygonVertices:
                        TotalIndexVertex.append(vert) 
                        ow("%d " % vert)
                    # Write UVs
                    for Item in PolygonVertices:
                        ow("%d " % uv_index)
                        uv_index += 1
                        
                    for Item in PolygonVertices:
                        ow("%d " % co_index)
                        co_index += 1
                    ow("\n")
                ow("  }\n")
                
                #Close Tag
                ow("}\n")

    time_now = datetime.datetime.utcnow()

    #Script header
    ow("*EUROCOM_INTERCHANGE_FILE 100\n")
    ow("*COMMENT Eurocom Interchange File Version 1.00 %s\n\n" % time_now.strftime("%A %B %d %Y %H:%M"))

    #print scene info
    ow("*SCENE {\n")
    ow("  *FIRSTFRAME  %d\n" % (scn.frame_start))
    ow("  *LASTFRAME   %d\n" % (scn.frame_end  ))
    ow("  *FRAMESPEED  %d\n" % (scn.render.fps ))
    ow("  *STATICFRAME 0\n")
    ow("  *AMBIENTSTATIC 1.0 1.0 1.0\n")
    ow("}\n\n")

    #Write materials
#   GetMaterials()

    #Write Meshes
    GetMesh()

    #Close writer
    out.close()
    print('[i] done')
    
    return {'FINISHED'}
    
    
if __name__ == "__main__":
    save({}, str(Path.home()) + "/Desktop/testEIF_d.eif")