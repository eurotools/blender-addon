#  Copyright (c) 2020-2021 Swyter <swyterzone+sphinx@gmail.com>
#  SPDX-License-Identifier: Zlib

"""
Name: 'Eurocom Scene Export'
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
from . import bl_info

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

    up_vec      = Vector((0, 1, 0))
    right_vec   = Vector((0, 1, 0))
    forward_vec = Vector((1, 0, 0))

    euroland_mtx = Matrix((up_vec,
                           right_vec,
                           forward_vec))

    InvertAxisRotationMatrix = Matrix(((1, 0, 0),
                                       (0, 0, 1),
                                       (0, 1, 0)))

    #===============================================================================================
    #  FUNCTIONS
    #===============================================================================================
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
            # swy: reset the indentation level to zero
            global block_level; block_level = 0

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


            def PrintNODE_TM(tag_name, object):
                    bpy.context.scene.frame_set(bpy.context.scene.frame_start)
                    w_new_block('*' + tag_name + ' {')

                    ConvertedMatrix = object.rotation_euler.to_matrix()
                    rot_mtx = ConvertedMatrix # @ InvertAxisRotationMatrix
                    RotationMatrix = rot_mtx #.transposed()

                    #Write Matrix
                    write_scope('*NODE_NAME "%s"' % object.name)

                    write_scope('*TM_ROW0 %.4f %.4f %.4f' % (obj.matrix_world[0].x, obj.matrix_world[0].y, obj.matrix_world[0].z))
                    write_scope('*TM_ROW1 %.4f %.4f %.4f' % (obj.matrix_world[1].x, obj.matrix_world[1].y, obj.matrix_world[1].z))
                    write_scope('*TM_ROW2 %.4f %.4f %.4f' % (obj.matrix_world[2].x, obj.matrix_world[2].y, obj.matrix_world[2].z))

                    #Flip location axis
                    loc_conv = object.location # @ InvertAxisRotationMatrix
                    write_scope('*TM_ROW3 %.4f %.4f %.4f' % (obj.matrix_world[0].w, obj.matrix_world[1].w, obj.matrix_world[2].w))
                    #write_scope('*TM_POS  %.4f %.4f %.4f' % (loc_conv.x, loc_conv.y, loc_conv.z))

                    w_end_block('}')

            def PrintTM_ANIMATION(object, TimeValue):
                    w_new_block('*TM_ANIMATION {')
                    write_scope('*NODE_NAME "%s"' % object.name)

                    w_new_block('*TM_ANIM_FRAMES {')
                    last_matrix = False
                    TimeValueCounter = 0
                    for f in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):

                        bpy.context.scene.frame_set(f + 1)
                        nex_matrix = [object.rotation_euler.copy(), object.location.copy()]

                        bpy.context.scene.frame_set(f)
                        cur_matrix = [object.rotation_euler.copy(), object.location.copy()]

                        if True: # (cur_matrix != last_matrix or cur_matrix != nex_matrix):
                            last_matrix = cur_matrix

                            ConvertedMatrix = object.rotation_euler.to_matrix()

                            rot_mtx = ConvertedMatrix # @ InvertAxisRotationMatrix
                            RotationMatrix = rot_mtx #.transposed()


                            thing=object.matrix_world.invert()

                            #Write Time Value
                            write_scope_no_cr('*TM_FRAME  %5u' % f)

                            #Write Matrix
                            out.write('  %.4f %.4f %.4f' % (thing[0].x, thing[0].y, thing[0].z))
                            out.write('  %.4f %.4f %.4f' % (thing[1].x, thing[1].y, thing[1].z))
                            out.write('  %.4f %.4f %.4f' % (thing[2].x, thing[2].y, RotationMatrix[2].z))

                            #Flip location axis
                            loc_conv = object.location
                            out.write('  %.4f %.4f %.4f' % (loc_conv.x, loc_conv.y, loc_conv.z))
                            out.write('\n')

                        #Update counter
                        TimeValueCounter += TimeValue
                    w_end_block('}') # NODE_NAME
                    w_end_block('}') # TM_ANIMATION


            # here's the first line that gets written; we start here, with the basic header
            write_scope('*3DSMAX_EUROEXPORT	300')

            # swy: turn a (2021, 8, 16) tuple into "2021.08.16"
            version_date = '.'.join(('%02u' % x) for x in bl_info['version'])

            write_scope('*COMMENT "Eurocom Export Version %s - %s"' % (version_date, datetime.datetime.utcnow().strftime('%a %b %d %H:%M:%S %Y')))
            write_scope('*COMMENT "Version of Blender that output this file: %s"' % bpy.app.version_string)
            write_scope('*COMMENT "Version of ESE Plug-in: 5.0.0.13"')
            write_scope('')

            #===============================================================================================
            #  SCENE INFO
            #===============================================================================================
            TimeValue = 1 # 4800 / bpy.context.scene.render.fps
            frame_count = bpy.context.scene.frame_end - bpy.context.scene.frame_start + 1

            w_new_block('*SCENE {')
            write_scope('*SCENE_FILENAME "%s"'     % os.path.basename(bpy.data.filepath))
            write_scope('*SCENE_FIRSTFRAME %u '    % bpy.context.scene.frame_start)
            write_scope('*SCENE_LASTFRAME %u '     % bpy.context.scene.frame_end)
            write_scope('*SCENE_FRAMESPEED %u '    % bpy.context.scene.render.fps)
            write_scope('*SCENE_TICKSPERFRAME %u ' % TimeValue)
            w_end_block('}') # SCENE

            #===============================================================================================
            #  GEOM OBJECT
            #===============================================================================================
            if 'MESH' in EXPORT_OBJECTTYPES:
                for indx, obj_orig in enumerate(bpy.context.scene.objects):

                    obj      = obj_orig.copy()
                    obj.data = obj_orig.data.copy()

                    #obj.data.transform(obj.matrix_world.inverted() @ Matrix(([-1,0,0],[0,0,-1],[0,1,0])).to_4x4() @ obj.matrix_world)
                    #obj.data.transform(Matrix(([1,0,0],[0,0,-1],[0,1,0])).to_4x4())

                    if obj.type == 'MESH':
                        if hasattr(obj, 'data'):
                            #===========================================[Clone Object]====================================================
                            depsgraph = bpy.context.evaluated_depsgraph_get()
                            ob_for_convert = obj.evaluated_get(depsgraph)

                            #obj.data.transform(Matrix(([1,0,0],[0,0,1],[0,-1,0])).to_4x4())

                            try:
                                MeshObject = obj.to_mesh()
                            except RuntimeError:
                                MeshObject = None
                            if MeshObject is None:
                                continue

                            #===========================================[Apply Matrix]====================================================
                            #MeshObject.transform(euroland_mtx.transposed().to_4x4())
                            #MeshObject.transform(Matrix(([1,0,0],[0,0,-1],[0,1,0])).to_4x4())

                            #MeshObject.transform(obj.matrix_world @ Matrix(([-1,0,0],[0,0,-1],[0,1,0])).to_4x4() @ obj.matrix_world.inverted())

                            #obj.matrix_world = Matrix(([1,0,0],[0,0,1],[0,-1,0])).to_4x4() @ obj.matrix_world
                            obj.matrix_world = Matrix(([-1,0,0],[0,0,1],[0,-1,0])).to_4x4() @ obj.matrix_world

                            translation, rotation, scale = obj.matrix_world.decompose()
                            obj.matrix_world = Matrix.Translation(translation) @ rotation.to_matrix().inverted().to_4x4() @ Matrix.Diagonal(scale.to_4d()) 

                            #obj.matrix_world = Matrix(([-1,0,0],[0,0,1],[0,-1,0])).to_4x4() @ obj.matrix_world

                            #e=Euler()
                            #e.rotate_axis('X', radians(90))
                            #MeshObject.transform(e.to_matrix().to_4x4())

                            #if EXPORT_FLIP_POLYGONS:
                            #MeshObject.flip_normals()

                            #===========================================[Triangulate Object]====================================================
                            bm = bmesh.new()
                            bm.from_mesh(MeshObject)
                            tris = bm.calc_loop_triangles()

                            #===========================================[Get Object Data]====================================================
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


                            #===============================================================================================
                            #  MATERIAL LIST
                            #===============================================================================================
                            w_new_block('*MATERIAL_LIST {')
                            write_scope('*MATERIAL_COUNT %u' % GetMaterialCount())
                            w_new_block('*MATERIAL %u {' % indx)

                            #Mesh Materials
                            if len(obj.material_slots) > 0:
                                currentSubMat = 0

                                #Material Info
                                MatData = bpy.data.materials[0]
                                DiffuseColor = MatData.diffuse_color
                                write_scope('*MATERIAL_NAME "%s"' % MatData.name)
                                if not MatData.use_backface_culling:
                                    write_scope('*MATERIAL_TWOSIDED')
                                write_scope('*NUMSUBMTLS %u ' % len(obj.material_slots))

                                #Loop Trought Submaterials
                                for indx, Material_Data in enumerate(obj.material_slots):

                                    if Material_Data.name == '':
                                        continue
                                    
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

                                        w_end_block('}') # SUBMATERIAL

                                    #Material has no texture
                                    else:
                                        #Submaterial
                                        principled = [n for n in MatData.node_tree.nodes if n.type == 'BSDF_PRINCIPLED']
                                        if principled:
                                            principled = next(n for n in MatData.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
                                            base_color = principled.inputs['Base Color']
                                            color = base_color.default_value

                                            w_new_block('*SUBMATERIAL %u {' % currentSubMat)
                                            write_scope('*MATERIAL_NAME "%s"' % MatData.name)
                                            write_scope('*MATERIAL_DIFFUSE %.4f %.4f %.4f' % ((color[0] * .5), (color[1] * .5), (color[2] * .5)))
                                            write_scope('*MATERIAL_SPECULAR %u %u %u' % (MatData.specular_color[0], MatData.specular_color[1], MatData.specular_color[2]))
                                            write_scope('*MATERIAL_SHINE %.1f' % MatData.metallic)
                                            write_scope('*MATERIAL_SELFILLUM %u' % int(MatData.use_preview_world))
                                            w_end_block('}') # SUBMATERIAL

                                    currentSubMat += 1
                            w_end_block('}') # MATERIAL
                            w_end_block('}') # MATERIAL_LIST



                            #===========================================[Print Object Data]====================================================
                            w_new_block('*GEOMOBJECT {')
                            write_scope('*NODE_NAME "%s"' % obj.name)

                            #Print Matrix Rotation
                            PrintNODE_TM('NODE_TM', obj)

                            #Print Matrix Rotation again ¯\_(ツ)_/¯
                            #PrintNODE_TM('PIVOT_TM', obj)

                            #MESH Section
                            w_new_block('*MESH {')
                            write_scope('*MESH_NUMVERTEX %u' % len(bm.verts))
                            write_scope('*MESH_NUMFACES %u'  % len(tris))

                            #Print Vertex List
                            w_new_block('*MESH_VERTEX_LIST {')
                            for idx, vert in enumerate(bm.verts):
                                vtx = vert.co # @ euroland_mtx
                                write_scope('*MESH_VERTEX  %5u  %4.4f %4.4f %4.4f' % (idx, vtx.x, vtx.y, vtx.z))
                            w_end_block('}') # MESH_VERTEX_LIST

                            # swy: the calc_loop_triangles() doesn't modify the original faces, and instead does temporary ad-hoc triangulation
                            #      returning us a list of three loops per "virtual triangle" that only exists in the returned thingie
                            #      i.e. len(tri_loop) should always be 3, but internally, for each loop .face we're a member of
                            #           still has 4 vertices and the four (different) loops of an n-gon, and .link_loop_next
                            #           points to the original model's loop chain; the loops of our triangle aren't really linked
                            def tri_edge_is_from_ngon(tri_loop, tri_idx):
                                return tri_loop[(tri_idx + 1) % len(tri_loop)] == tri_loop[tri_idx].link_loop_next

                            #Face Vertex Index
                            w_new_block('*MESH_FACE_LIST {')
                            for i, tri in enumerate(tris):
                                write_scope_no_cr('*MESH_FACE %3u:' % i)
                                out.write('    A: %3u B: %3u C: %3u' % (tri[0].vert.index, tri[1].vert.index, tri[2].vert.index))
                                out.write('    AB: %u BC: %u CA: %u' % (tri_edge_is_from_ngon(tri, 0), tri_edge_is_from_ngon(tri, 1), tri_edge_is_from_ngon(tri, 2)))
                                out.write('  *MESH_MTLID %u\n' % tri[0].face.material_index)
                            w_end_block('}') # MESH_FACE

                            #Texture UVs
                            if len(UVVertexList) > 0:
                                write_scope('*MESH_NUMTVERTEX %u' % len(UVVertexList))
                                w_new_block('*MESH_TVERTLIST {')
                                for idx, TextUV in enumerate(UVVertexList):
                                    write_scope('*MESH_TVERT %3u %.4f %.4f' % (idx, TextUV[0], TextUV[1]))
                                w_end_block('}') # MESH_TVERTLIST

                            #Face Layers UVs Index
                            layerIndex = 0
                            if bm.loops.layers == 1:
                                #write_scope('*MESH_NUMTFACELAYERS %u' % len(bm.loops.layers.uv.items()))
                                for name, uv_lay in bm.loops.layers.uv.items():
                                    #w_new_block('*MESH_TFACELAYER %u {' % layerIndex)
                                    write_scope('*MESH_NUMTVFACES %u' % len(bm.faces))
                                    w_new_block('*MESH_TFACELIST {')
                                    for i, tri in enumerate(tris):
                                        write_scope('*MESH_TFACE %u' % i)
                                        write_scope('%u %u %u' % (UVVertexList.index(tri[0][uv_lay].uv), UVVertexList.index(tri[1][uv_lay].uv), UVVertexList.index(tri[2][uv_lay].uv)))
                                    w_end_block("}") # MESH_TFACELIST
                                    #w_end_block("}")
                                    layerIndex += 1

                            # swy: refresh the custom mesh layer/attributes in case they don't exist
                            if 'euro_vtx_flags' not in bm.verts.layers.int:
                                    bm.verts.layers.int.new('euro_vtx_flags')

                            if 'euro_fac_flags' not in bm.faces.layers.int:
                                    bm.faces.layers.int.new('euro_fac_flags')

                            euro_vtx_flags = bm.verts.layers.int['euro_vtx_flags']
                            euro_fac_flags = bm.faces.layers.int['euro_fac_flags']

                            # swy: add the custom mesh attributes here
                            write_scope("*MESH_NUMFACEFLAGS %u" % len(bm.faces))
                            w_new_block("*MESH_FACEFLAGLIST {")
                            for face in bm.faces:
                                a = face[euro_fac_flags]
                                # swy: don't set it where it isn't needed
                                if face[euro_fac_flags] != 0:
                                    write_scope('*MESH_FACEFLAG %u %u' % (face.index, face[euro_fac_flags]))
                            w_end_block("}") # MESH_NUMFACEFLAGS

                            w_new_block('*MESH_VERTFLAGSLIST {')
                            for idx, vert in enumerate(bm.verts):
                                # swy: don't set it where it isn't needed
                                if vert[euro_vtx_flags] != 0:
                                    write_scope('*VFLAG %u %u' % (idx, vert[euro_vtx_flags]))
                            w_end_block('}') # MESH_VERTFLAGSLIST

                            if len(VertexColorList) > 0:
                                #Vertex Colors List
                                write_scope('*MESH_NUMCVERTEX %u' % len(VertexColorList))
                                w_new_block('*MESH_CVERTLIST {')
                                for idx, ColorArray in enumerate(VertexColorList):
                                    write_scope('*MESH_VERTCOL %u %.4f %.4f %.4f %u' % (idx,
                                        (ColorArray[0] * .5),
                                        (ColorArray[1] * .5),
                                        (ColorArray[2] * .5), 1) # swy: fix dumping the alpha channel
                                    )
                                w_end_block('}') # MESH_CVERTLIST

                            if True:
                                #Face Color Vertex Index
                                layerIndex = 0
                                if len(bm.loops.layers.color.items()) > 0:
                                    write_scope('*MESH_NUMCFACELAYERS %u' % len(bm.loops.layers.color.items()))
                                    for name, cl in bm.loops.layers.color.items():
                                        w_new_block('*MESH_CFACELAYER %u {' % layerIndex)
                                        write_scope('*MESH_NUMCVFACES %u ' % len(tris))
                                        w_new_block('*MESH_CFACELIST {')
                                        for i, tri in enumerate(tris):
                                            write_scope_no_cr('*MESH_CFACE %5u  ' % i)
                                            for loop in tri:
                                                out.write('%u ' % VertexColorList.index(loop[cl]))
                                            out.write('\n')
                                        w_end_block('}') # MESH_CFACELIST
                                        w_end_block('}') # MESH_CFACELAYER
                                        layerIndex +=1

                            #Close blocks
                            w_end_block('}') # MESH

                            # swy: wireframe color was added on Blender 2.8 and is a per-object thing in Object Properties > Viewport Display > Color
                            write_scope('*WIREFRAME_COLOR %.4f %.4f %.4f' % (obj.color[0], obj.color[1], obj.color[2]))

                            #===============================================================================================
                            #  ANIMATION
                            #===============================================================================================
                            #if frame_count > 1:
                            #    PrintTM_ANIMATION(obj, TimeValue)

                            #Material Reference
                            if EXPORT_MATERIALS:
                                write_scope('*MATERIAL_REF %u' % indx)

                            #===============================================================================================
                            #  SHAPE KEYS
                            #===============================================================================================
                            # swy: here go our blend shape weights with the mixed-in amount for each frame in the timeline
                            if obj.data.shape_keys:
                                w_new_block('*MORPH_DATA {')
                                for key in obj.data.shape_keys.key_blocks:
                                    if key.relative_key != key:
                                        w_new_block('*MORPH_FRAMES "%s" %u {' % (key.name.replace(' ', '_'), frame_count))

                                        for f in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
                                            bpy.context.scene.frame_set(f)
                                            write_scope('%u %f' % (f, key.value))

                                        w_end_block('}') # MORPH_FRAMES
                                w_end_block('}') # MORPH_DATA

                            #===============================================================================================
                            #  SKELETAL RIGGING / BONE HIERARCHY DEFINITION / ARMATURE
                            #===============================================================================================
                            for indx, mod in enumerate(obj.modifiers):
                                # swy: find the armature element between the possible mesh modifiers
                                if mod.type == 'ARMATURE' and mod.object and mod.object.type == 'ARMATURE':
                                    armat = mod.object
                                    w_new_block("*SKIN_DATA {")
                                    w_new_block("*BONE_LIST {")

                                    # create a skeletal lookup list for bone names
                                    bone_names = [bone.name for bone in armat.data.bones]

                                    for bidx, bone in enumerate(armat.data.bones):
                                        write_scope('*BONE %u "%s"' % (bidx, bone.name))
                                    w_end_block("}") # BONE_LIST

                                    # create a vertex group lookup list for names
                                    # https://blender.stackexchange.com/a/28273/42781
                                    vgroup_names = [vgroup.name for vgroup in obj.vertex_groups]

                                    w_new_block('*SKIN_VERTEX_DATA {')
                                    for vidx, vert in enumerate(obj.data.vertices):
                                        write_scope_no_cr('*VERTEX %5u %u' % (vidx, len(vert.groups)))

                                        # swy: make it so that the bones that have more influence appear first
                                        #      in the listing, otherwise order seems random.
                                        sorted_groups = sorted(vert.groups, key = lambda i: i.weight, reverse = True)

                                        for gidx, group in enumerate(sorted_groups):
                                            # swy: get the actual vertex group name from the local index (the .group thing)
                                            cur_vgroup_name = vgroup_names[group.group]
                                            # swy: and test it to see if it matches a bone name from the bound armature/skeleton
                                            #      otherwise it probably isn't a weighting group and is used for something else
                                            if cur_vgroup_name not in bone_names:
                                                continue

                                            # swy: because the bone names are in the same order as in the BONE_LIST above everything works out
                                            global_bone_index = bone_names.index(cur_vgroup_name)
                                            out.write('  %2u %f' % (global_bone_index, group.weight))
                                        out.write("\n")

                                    w_end_block("}") # SKIN_VERTEX_DATA
                                    w_end_block("}") # SKIN_DATA

                                    # swy: we only support one armature modifier/binding per mesh for now, stop looking for more
                                    break

                            w_end_block('}') # GEOMOBJECT

                            # swy: here goes the changed geometry/vertex positions for each of the shape keys, globally.
                            #      they are referenced by name.
                            if obj.data.shape_keys:
                                for key in obj.data.shape_keys.key_blocks:
                                    # swy: don't export the 'Basis' one that is just the normal mesh data other keys are relative/substracted to
                                    if key.relative_key != key:
                                        w_new_block('*MORPH_LIST {')
                                        w_new_block('*MORPH_TARGET "%s" %u {' % (key.name.replace(' ', '_'), len(key.data)))

                                        for vidx, vert in enumerate(key.data):
                                            write_scope('%f %f %f' % (vert.co.x, vert.co.y, vert.co.z))

                                        w_end_block('}') # MORPH_TARGET
                                        w_end_block('}') # MORPH_LIST

                            # swy: free the current mesh's BMesh triangulated helper object, we won't be needing it anymore
                            #      all the related geometry operations have been done
                            bm.free()

            for indx, obj in enumerate(bpy.context.scene.objects):
                if obj.type == 'ARMATURE':
                    for bidx, bone in enumerate(obj.data.bones):
                        w_new_block('*BONEOBJECT {')
                        write_scope('*NODE_NAME "%s"' % bone.name)
                        write_scope('*NODE_BIPED_BODY')
                        if (bone.parent):
                            write_scope('*NODE_PARENT "%s"' % bone.parent.name)
                        w_end_block('}') # BONEOBJECT

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

                    #Print Matrix Rotation
                    PrintNODE_TM('NODE_TM', CameraObj)

                    #===============================================================================================
                    #  CAMERA SETTINGS
                    #===============================================================================================
                    w_new_block('*CAMERA_SETTINGS {')
                    write_scope('*TIMEVALUE %u' % 0)
                    write_scope('*CAMERA_FOV %.4f' % CameraObj.data.angle)
                    w_end_block('}') # CAMERA_SETTINGS

                    #===============================================================================================
                    #  CAMERA ANIMATION
                    #===============================================================================================
                    if frame_count > 1:
                        w_new_block('*CAMERA_ANIMATION {')

                        TimeValueCounter = 0
                        for f in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
                            bpy.context.scene.frame_set(f)

                            w_new_block('*CAMERA_SETTINGS {')
                            write_scope('*TIMEVALUE %u' % TimeValueCounter)
                            write_scope('*CAMERA_FOV %.4f'% CameraObj.data.angle)
                            w_end_block('}')

                            TimeValueCounter += TimeValue

                        w_end_block('}') # CAMERA_ANIMATION

                        PrintTM_ANIMATION(CameraObj, TimeValue)
                        
                    #===============================================================================================
                    #  USER DATA (ONLY FOR SCRIPTS)
                    #===============================================================================================
                    # swy: Jmarti856 found that this is needed for the time range of each camera to show up properly in
                    #      the script timeline, without this all of them cover the entire thing from beginning to end
                    if CameraObj == CamerasList[-1] and len(CamerasList) > 1:
                        w_new_block('*USER_DATA %u {' % 0)
                        write_scope('CameraScript = %u' % 1)
                        write_scope('CameraScript_numCameras = %u' % len(CamerasList))
                        write_scope('CameraScript_globalOffset = %u' % 0)

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
                                        write_scope('CameraScript_camera%u = %s %u %u %u %u' % (CameraNumber, ob.name, Keyframe_Points_list[0], Keyframe_Points_list[-1], CamStart, CamEnd))
                                        
                                        #Calculate EuroLand End
                                        CamStart += Keyframe_Points_list[-1] + 1
                                        CameraNumber += 1
                                        
                        w_end_block('}') # USER_DATA
                    w_end_block('}') # CAMERAOBJECT

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
                        PrintNODE_TM('NODE_TM', obj)

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
                        w_end_block('}') # LIGHTOBJECT

                        #===============================================================================================
                        #  LIGHT ANIMATION
                        #===============================================================================================
                        if frame_count > 1:
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
                                w_end_block('}') # LIGHT_SETTINGS

                                TimeValueCounter += TimeValue

                            w_end_block('}') # LIGHT_ANIMATION

                            PrintTM_ANIMATION(obj, TimeValue)

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