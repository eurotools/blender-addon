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
                    DiffuseColor = s.material.diffuse_color
                    for n in s.material.node_tree.nodes:
                        if n.type == 'TEX_IMAGE':                
                            ow("\t*MATERIAL %d {\n" % (MaterialIndex))
                            ow("\t\t*NAME \"%s\"\n" % (os.path.splitext(n.image.name)[0]))
                            ow("\t\t*COL_DIFFUSE %.6f %.6f %.6f\n" % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))
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
                total_triangles = 0
                VertexList = []
                UVList = []
                VertColList = []
                
                #==================GET VERTEX LIST==============================
                for vertex in me.vertices:
                    VertexList.append("%.6f,%.6f,%.6f" % (vertex.co.x,vertex.co.y,vertex.co.z))
 
                 #==================GET UV LIST==============================                   
                for count, poly in enumerate(me.polygons):
                    for loop_index in poly.loop_indices:
                        print(count, loop_index, "uv_layer len:", len(me.uv_layers))
                        UVList.append("%.6f,%.6f" % (uv_layer[0].uv.x,uv_layer[0].uv.y))
                        
                 #==================GET Vertex Color LIST==============================               
                if(bool(me.vertex_colors.active)):
                    for vertex in me.vertex_colors[0].data:
                        VertColList.append("%.6f,%.6f,%.6f,%.6f" % (vertex.color[0],vertex.color[1],vertex.color[2],vertex.color[3]))
                
                #===================COUNT TRIS======================
                for face in me.polygons:
                    vertices = face.vertices
                    triangles = len(vertices) - 2
                    total_triangles += triangles
                        
                #==================PRINT DATA==============================
                ow("*MESH {\n")    
                ow("\t*NAME \"%s\"\n" % (me.name))
                ow("\t*VERTCOUNT %d\n" % (len(VertexList)))
                ow("\t*UVCOUNT %d\n" % (len(UVList)))
                if(len(VertColList) > 0):
                    ow("\t*VERTCOLCOUNT %d\n" % (len(VertColList)))
                ow("\t*FACECOUNT %d\n" % (len(me.polygons)))
                ow("\t*TRIFACECOUNT %d\n" % (total_triangles))
                ow("\t*FACELAYERSCOUNT %d\n" % len(me.uv_layers))
                
                #Check if there are more than one layer
                if (len(me.uv_layers) > 1):
                    ow("\t*FACESHADERCOUNT %d\n" % len(me.uv_layers))
                
                #Print Vertex data
                ow("\t*VERTEX_LIST {\n")
                for list_item in VertexList:
                    dataSplit = list_item.split(",")
                    ow("\t\t%s %s %s\n" % (dataSplit[0], dataSplit[1], dataSplit[2]))
                ow("\t}\n")
                
                #Print UV data
                ow("\t*UV_LIST {\n")
                for list_item in UVList:
                    dataSplit = list_item.split(",")
                    ow("\t\t%s %s\n" % (dataSplit[0], dataSplit[1]))
                ow("\t}\n")
                
                #Check if the vertex colors layer is active
                if(len(VertColList) > 0):
                    ow("\t*VERTCOL_LIST {\n")
                    for list_item in VertColList:
                        dataSplit = list_item.split(",")
                        ow("\t\t%s %s %s %s\n" % (dataSplit[0], dataSplit[1], dataSplit[2], dataSplit[3]))                    
                    ow("\t}\n")
                    
                #Print Shader faces
                if (len(me.uv_layers) > 1):
                    ow("\t*FACESHADERS {\n")
                    ow("\t}\n")
                ow("\t*FACEFORMAT VT\n")
                
                CalcIndex = 0
                
                #Print Face list
                ow("\t*FACE_LIST {\n")
                for poly in me.polygons:
                    #Get polygon vertices
                    PolygonVertices = poly.vertices
                    TotalIndexVertex = []
                    #Write vertices
                    ow("\t\t%d " % (len(PolygonVertices)))
                    for vert in PolygonVertices:
                        TotalIndexVertex.append(vert) 
                        ow("%d " % vert)
                    # Write UVs
                    for Item in PolygonVertices:
                        ow("%d " % CalcIndex)
                        CalcIndex += 1
                    ow("\n")
                ow("\t}\n")
                
                #Close Tag
                ow("}\n")

    time_now = datetime.datetime.utcnow()

    #Script header
    ow("*EUROCOM_INTERCHANGE_FILE 100\n")
    ow("*COMMENT Eurocom Interchange File Version 1.00 %s\n\n" % time_now.strftime("%A %B %d %Y %H:%M"))
    ow("*OPTIONS {\n")
    ow("\t*COORD_SYSTEM LH\n")
    ow("}\n\n")

    #print scene info
    ow("*SCENE {\n")
    ow("\t*FILENAME \"%s\"\n" % (os.path.abspath(r'C:\Users\Jordi Martinez\Desktop\Sphinx and the shadow of set\CutScenes\Abydos\CS_Aby_South.elf')))
    ow("\t*FIRSTFRAME %d\n" % (scn.frame_start))
    ow("\t*LASTFRAME %d\n" % (scn.frame_end))
    ow("\t*FRAMESPEED %d\n" % (scn.render.fps))  
    ow("\t*STATICFRAME 0\n")
    ow("\t*AMBIENTSTATIC 1.0 1.0 1.0\n")
    ow("}\n\n")

    #Write materials
#    GetMaterials()

    #Write Meshes
    GetMesh()

    #Close writer
    out.close()

    return {'FINISHED'}
    
    
if __name__ == "__main__":
    save({}, str(Path.home()) + "\\Desktop\\TestEIF.eif")