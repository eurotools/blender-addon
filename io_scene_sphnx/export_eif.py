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
    Materials_Dict = dict()
    
    
#*===============================================================================================
#*	Get data lists from the object
#*===============================================================================================
    def GetVertexList(me):
        VertexList = []
        
        for vertex in me.vertices:
            VertexList.append("%.6f,%.6f,%.6f" % (vertex.co.x,vertex.co.z,vertex.co.y))
        return VertexList
    
    def GetUVList(me):
        UVList = []
        
        if hasattr(me.uv_layers.active, "data"):
            uv_layer = me.uv_layers.active.data
            
            if len(me.uv_layers):
                for pl_count, poly in enumerate(me.polygons):
                    for li_count, loop_index in enumerate(poly.loop_indices):
                        #print(pl_count, li_count, loop_index, "uv_layer len:", len(uv_layer))
                        UVList.append("%.6f,%.6f" % (uv_layer[loop_index].uv.x,uv_layer[loop_index].uv.y))
                UVList = list(dict.fromkeys(UVList))
        return UVList
    
    def GetVertexColorList(me):
        VertColList = []
        
        if len(me.vertex_colors):
            if hasattr(me.vertex_colors.active, "data"):
                for vertex in me.vertex_colors.active.data:
                    VertColList.append("%.6f,%.6f,%.6f,%.6f" % (vertex.color[0],vertex.color[1],vertex.color[2],vertex.color[3]))
                VertColList = list(dict.fromkeys(VertColList))
        return VertColList
    
    def GetMaterialIndex(MaterialName):
        for index, material in Materials_Dict.items():
            if material == MaterialName:
                return index
            
#*===============================================================================================
#*	Get materials and write data
#*===============================================================================================        
    def GetMaterials():
        MaterialIndex = 0
        ow("*MATERIALS {\n")
        
        for obj in scn.objects:
            if obj.hide_viewport:
                continue
            
            if obj.type == 'MESH':
                if len(obj.material_slots) > 0:
                    for s in obj.material_slots:
                        if s.material and s.material.use_nodes:
                            DiffuseColor = s.material.diffuse_color
                            for n in s.material.node_tree.nodes:
                                if n.type == 'TEX_IMAGE':
                                    ImageName = n.image.name
                                    if os.path.splitext(ImageName)[0] not in Materials_Dict.values():
                                        ow("  *MATERIAL %d {\n" % (MaterialIndex))
                                        ow("    *NAME \"%s\"\n" % (os.path.splitext(ImageName)[0]))
                                        ow("    *COL_DIFFUSE %.6f %.6f %.6f\n" % (DiffuseColor[0], DiffuseColor[1], DiffuseColor[2]))
                                        ow("    *MAP_DIFFUSE \"%s\"\n" % (bpy.path.abspath(n.image.filepath)))
                                        
                                        #Check if the texture exists
                                        if (os.path.exists(bpy.path.abspath(n.image.filepath))):
                                            ow("    *TWOSIDED\n")
                                        ow("    *MAP_DIFFUSE_AMOUNT 1.0\n")
                                        
                                        #Add data to dictionary
                                        Materials_Dict[MaterialIndex] = os.path.splitext(ImageName)[0]
                                        
                                        #Add 1 to the materials index
                                        MaterialIndex +=1
                                        ow("  }\n")
        ow("}\n\n")
        
#*===============================================================================================
#*	Write object data to the file
#*===============================================================================================
    def GetMesh():
        for ob in scn.objects:        
            if ob.hide_viewport:
                continue
            
            if ob.type == 'MESH':
                if hasattr(ob, "data"):
                    me = ob.data

                    VertexList = GetVertexList(ob.data)
                    UVList = GetUVList(ob.data)
                    VertColList = GetVertexColorList(ob.data)
                    
                    FaceFormat = "V"
                                           
                    #==================PRINT DATA==============================
                    ow("*MESH {\n")    
                    ow("  *NAME \"%s\"\n" % (me.name))
                    ow("  *VERTCOUNT %d\n" % (len(VertexList)))
                    ow("  *UVCOUNT %d\n" % (len(UVList)))
                    if(len(VertColList) > 0):
                        ow("  *VERTCOLCOUNT %d\n" % (len(VertColList)))
                    ow("  *FACECOUNT %d\n" % (len(me.polygons)))
                    ow("  *TRIFACECOUNT %d\n" % (sum(len(p.vertices) - 2 for p in me.polygons)))
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
                    if (len(UVList) > 0):
                        FaceFormat += "T"
                        
                        ow("  *UV_LIST {\n")
                        for list_item in UVList:
                            dataSplit = list_item.split(",")
                            ow("    %s %s\n" % (dataSplit[0], dataSplit[1]))
                        ow("  }\n")
                    
                    #Check if the vertex colors layer is active
                    if(len(VertColList) > 0):
                        FaceFormat +="C"
                        
                        ow("  *VERTCOL_LIST {\n")
                        for list_item in VertColList:
                            dataSplit = list_item.split(",")
                            ow("    %s %s %s %s\n" % (dataSplit[0], dataSplit[1], dataSplit[2], dataSplit[3]))                    
                        ow("  }\n")
                    
                    if len(ob.material_slots) > 0:
                        FaceFormat +="M"
                        
                    #Print Shader faces
                    if (len(me.uv_layers) > 1):
                        ow("  *FACESHADERS {\n")
                        ow("  }\n")
                        
                    #Get FaceFormat
                    ow("  *FACEFORMAT %s\n" % FaceFormat)
                    
                    uv_index = 0
                    co_index = 0
                    
                    #Print Face list
                    ow("  *FACE_LIST {\n")
                    for poly in me.polygons:
                        #Get polygon vertices
                        PolygonVertices = poly.vertices
                        
                        #Write vertices ---V
                        ow("    %d " % (len(PolygonVertices)))
                        for vert in PolygonVertices:
                            ow("%d " % vert)
                            
                        #Write UVs ---T
                        if ("T" in FaceFormat):
                            for vert_idx, loop_idx in enumerate(poly.loop_indices):
                                uv_coords = me.uv_layers.active.data[loop_idx].uv
                                ow("%d " % UVList.index("%.6f,%.6f" % (uv_coords.x, uv_coords.y)))
                                
                        #Write Colors ---C
                        if ("C" in FaceFormat):
                            for color_idx, loop_idx in enumerate(poly.loop_indices):
                                vertex = me.vertex_colors.active.data[loop_idx]
                                ow("%d " % VertColList.index("%.6f,%.6f,%.6f,%.6f" % (vertex.color[0],vertex.color[1],vertex.color[2],vertex.color[3])))
                        
                        #Write Material Index ---M
                        if ("M" in FaceFormat):
                            s = ob.material_slots[poly.material_index]
                            if s.material and s.material.use_nodes:
                                for n in s.material.node_tree.nodes:
                                    if n.type == 'TEX_IMAGE':
                                        ow("%d " % GetMaterialIndex(os.path.splitext(n.image.name)[0]))
                        ow("\n")
                    ow("  }\n")
                
                #Close Tag
                ow("}\n")

#*===============================================================================================
#*	Write file header
#*===============================================================================================
    # Stop edit mode
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
        
    bpy.context.scene.world.light_settings.use_ambient_occlusion = True
    
    #Script header
    time_now = datetime.datetime.now()
    ow("*EUROCOM_INTERCHANGE_FILE 100\n")
    ow("*COMMENT Eurocom Interchange File Version 1.00 %s\n\n" % time_now.strftime("%A %B %d %Y %H:%M"))

    #print scene info
    ow("*SCENE {\n")
    ow("  *FILENAME \"%s\"\n" % (bpy.data.filepath))
    ow("  *FIRSTFRAME  %d\n" % (scn.frame_start))
    ow("  *LASTFRAME   %d\n" % (scn.frame_end  ))
    ow("  *FRAMESPEED  %d\n" % (scn.render.fps ))
    ow("  *STATICFRAME %d\n" % (scn.frame_current))
    AmbientValue = bpy.context.scene.world.light_settings.ao_factor
    ow("  *AMBIENTSTATIC %.6f %.6f %.6f\n" %(AmbientValue, AmbientValue, AmbientValue))
    ow("}\n\n")

    #Write materials
    GetMaterials()

    #Write Meshes
    GetMesh()

    #Close writer
    out.close()
    print('[i] done')
    
    return {'FINISHED'}
    
    
if __name__ == "__main__":
    save({}, str(Path.home()) + "/Desktop/testEIF_d.eif")