#  Copyright (c) 2020-2021 Swyter <swyterzone+sphinx@gmail.com>
#  SPDX-License-Identifier: Zlib

bl_info = {
           'name': 'Eurocom 3D formats for Sphinx and the Cursed Mummy™',
         'author': 'Swyter, for THQ Nordic GmbH',
        'version': (2020, 10, 10),
        'blender': (2, 81, 6),
       'location': 'File > Import-Export',
    'description': 'Export and import EIF, ESE and RTG files compatible with Euroland.',
        'warning': 'Importing still doesn\'t work, export in progress. ¯\_(ツ)_/¯',
        'doc_url': 'https://sphinxandthecursedmummy.fandom.com/wiki/Technical',
    'tracker_url': 'https://discord.gg/sphinx',
        'support': 'COMMUNITY',
       'category': 'Import-Export',
}

import os
import bpy
import bpy.utils.previews
import bmesh

from bpy.props import(
        BoolProperty,
        FloatProperty,
        StringProperty,
        EnumProperty,
)

from bpy_extras.io_utils import(
        ImportHelper,
        ExportHelper,
        orientation_helper,
        path_reference_mode,
        axis_conversion,
)

#===============================================================================================
#  IMPORTERS (TO DO)
#===============================================================================================
@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportRTG(bpy.types.Operator, ImportHelper):
    """Load a dynamic Maya Euroland file; for animations, scripts and maps"""
    bl_idname = "import_scene.rtg"
    bl_label = "Import RTG"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".rtg"
    filter_glob: StringProperty(default="*.rtg", options={'HIDDEN'})

    def execute(self, context):
        print("Selected: " + context.active_object.name)
        from . import import_rtg
        return import_rtg.load(context, self.filepath)

    def draw(self, context):
        pass

    @classmethod
    def poll(cls, context):
        return False

@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportEIF(bpy.types.Operator, ImportHelper):
    """Load a static 3ds Max Euroland file, for scenes and entities"""
    bl_idname = "import_scene.eif"
    bl_label = "Import EIF"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".eif"
    filter_glob: StringProperty(default="*.eif", options={'HIDDEN'})

    def execute(self, context):
        print("Selected: " + context.active_object.name)
        from . import import_eif
        return import_eif.load(context, self.filepath)

    def draw(self, context):
        pass

    @classmethod
    def poll(cls, context):
        return False

@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportESE(bpy.types.Operator, ImportHelper):
    """Load a dynamic 3ds Max Euroland file; for cutscenes and maps"""
    bl_idname = "import_scene.ese"
    bl_label = "Import ESE"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".ese"
    filter_glob: StringProperty(default="*.ese", options={'HIDDEN'})

    def execute(self, context):
        print("Selected: " + context.active_object.name)
        from . import import_ese
        return import_ese.load(context, self.filepath)

    def draw(self, context):
        pass

    @classmethod
    def poll(cls, context):
        return False

#===============================================================================================
#  EXPORTERS (ON IT)
#===============================================================================================
@orientation_helper(axis_forward='Z', axis_up='Y')
class ExportRTG(bpy.types.Operator, ExportHelper):
    """Save a dynamic Maya Euroland file; for animations, scripts and maps"""

    bl_idname = "export_scene.rtg"
    bl_label = 'Export RTG'
    bl_options = {'PRESET'}

    filename_ext = ".rtg"
    filter_glob: StringProperty(default="*.rtg", options={'HIDDEN'})

    path_mode: path_reference_mode

    check_extension = True

    def execute(self, context):
        from . import export_rtg
        return export_rtg.save(context, self.filepath)

    def draw(self, context):
        pass

@orientation_helper(axis_forward='Z', axis_up='Y')
class ExportEIF(bpy.types.Operator, ExportHelper):
    """Save a static 3ds Max Euroland file, for scenes and entities"""

    bl_idname = "export_scene.eif"
    bl_label = 'Export EIF'
    bl_options = {'PRESET'}

    filename_ext = ".eif"
    filter_glob: StringProperty(default="*.eif", options={'HIDDEN'})

    #Output Options
    Output_Map: BoolProperty(
        name="Output as a Map",
        description="Output scene as a new map for EuroLand.",
        default=False,
    )
    Output_Transform: BoolProperty(
        name="Transform Objects to (0,0,0)",
        description="Transform objects to position (0,0,0).",
        default=False,
    )

    #Scale Options
    global_scale: FloatProperty(
        name="Scale",
        min=0.01,
        max=1000.0,
        default=1.0,
    )

    path_mode: path_reference_mode
    check_extension = True

    def execute(self, context):
        from mathutils import Matrix
        from . import export_eif

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            "path_mode",
                                        ))

        global_matrix = (Matrix.Scale(self.global_scale, 4) @ Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0))).to_4x4())
        keywords["global_matrix"] = global_matrix

        return export_eif.save(context, **keywords)

    def draw(self, context):
        pass

class EIF_EXPORT_PT_output_options(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Output Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_eif"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Output_Map')
        self.layout.prop(context.space_data.active_operator, 'Output_Transform')

class EIF_EXPORT_PT_scale(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_eif"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, "global_scale")

@orientation_helper(axis_forward='Z', axis_up='Y')
class ExportESE(bpy.types.Operator, ExportHelper):
    """Save a dynamic 3ds Max Euroland file; for cutscenes and maps"""

    bl_idname = "export_scene.ese"
    bl_label = 'Export ESE'
    bl_options = {'PRESET'}

    filename_ext = ".ese"
    filter_glob: StringProperty(default="*.ese", options={'HIDDEN'})

    #Output Options
    Output_Materials: BoolProperty(
        name="Materials",
        description="Output scene materials.",
        default=False,
    )
    Output_CameraLightAnims: BoolProperty(
        name="Animated Camera/Light settings",
        description="Export animations from Camera and Light object types.",
        default=False,
    )
    Output_Animations: BoolProperty(
        name="Animations",
        description="Export animations.",
        default=True,
    )

    #Output Types
    object_types: EnumProperty(
        name="Output Types",
        options={'ENUM_FLAG'},
        items=(('CAMERA', "Cameras", ""),
               ('LIGHT', "Lights", ""),
               ('MESH', "Mesh", ""),
               ),
        description="Which kind of object to export",
        default={'CAMERA', 'LIGHT', 'MESH'}
    )

    #Mesh Options
    Output_VertexColors : BoolProperty(
        name="Vertex Colors",
        description="Export vertex colors from each mesh",
        default=False,
    )
    Flip_Polygons: BoolProperty(
        name="Flip Polygons",
        description="Flip polygons direction in which polygon faces.",
        default=False,
    )

    #Scale Options
    global_scale: FloatProperty(
        name="Scale",
        min=0.01,
        max=1000.0,
        default=1.0,
    )

    path_mode: path_reference_mode
    check_extension = True

    def execute(self, context):
        from mathutils import Matrix
        from . import export_ese

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            "path_mode",
                                            ))

        global_matrix = (Matrix.Scale(self.global_scale, 4) @ Matrix(((1, 0, 0),(0, 0, 1),(0, 1, 0))).to_4x4())
        keywords["global_matrix"] = global_matrix

        return export_ese.save(context, **keywords)

    def draw(self, context):
        pass

#===============================================================================================
#  ESE OUTPUT PANELS OPTIONS
#===============================================================================================
class ESE_EXPORT_PT_output_options(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Output Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Output_Materials')
        self.layout.prop(context.space_data.active_operator, 'Output_CameraLightAnims')
        self.layout.prop(context.space_data.active_operator, 'Output_Animations')

class ESE_EXPORT_PT_mesh_options(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Mesh Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Flip_Polygons')
        self.layout.prop(context.space_data.active_operator, 'Output_VertexColors')

class ESE_EXPORT_PT_object_types(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = ""
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        self.layout.column().prop(context.space_data.active_operator, "object_types")

class ESE_EXPORT_PT_scale(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, "global_scale")


num_objects = 0
thing = 0

def scene_update_post_handler(scene):
    global num_objects
    #if len(scene.objects) == num_objects:
        # Nothing to do
    #    return
    num_objects = len(scene.objects) 
    # Your code here    

    context = bpy.context

    # swy: this is a bit backwards, because you can select both at the same time, but works
    in_vtx_sel_mode = context.tool_settings.mesh_select_mode[0]
    in_fac_sel_mode = context.tool_settings.mesh_select_mode[2]

    # swy: make it not work at all in edge mode or whenever both of them are toggled on use an
    #      exclusive or / xor operation, so that we only return True if either of them is on
    if in_vtx_sel_mode ^ in_fac_sel_mode:
        #qqqq = enum_property_to_bitfield(context.mesh.euroland.vertex_flags)
        #ssss = bitfield_to_enum_property(context.mesh.euroland, 'vertex_flags', thing)
        global thing
        thing = 0

        def callback(elem, layer):
            if (elem.select):
                global thing
                thing |=  elem[layer]

        iterate_over_mesh(context, callback)

        ssss = bitfield_to_enum_property(context.active_object.data.euroland, 'vertex_flags', thing)

        if context.active_object.data.euroland.vertex_flags != ssss:
            context.active_object.data.euroland.vertex_flags = set(context.active_object.data.euroland.) # "0x0008"


    return

def update_after_enum(self, context):
    print('self.face_flags ---->', self.face_flags)
    

class EuroProperties(bpy.types.PropertyGroup):
    ''' Per-face bitfield for Euroland entities. ''' 
    face_flags: bpy.props.EnumProperty(
        name = "Eurocom face flags",
        options = {'ENUM_FLAG'},
        items = [
            # swy: configurable per-project flags
            ("", "Project Flags", ""),
            ("0x0001", "Water / NoJump (line seg.)",                                     "0x0001"),
            ("0x0002", "UnderWater / Ladder (line seg. and line poly)",                  "0x0002"),
            ("0x0004", "Slippery (line poly) / Wall (line seg.) / NoDive (normal poly)", "0x0004"),
            ("0x0008", "Moveable / Edge (line seg.)",                                    "0x0008"),
            (None),
            ("0x0010", "Riser / ZipHandle (grab poly)",                                  "0x0010"),
            ("0x0020", "No Camera Collision",                                            "0x0020"),
            ("0x0040", "No Char Lighting",                                               "0x0040"),
            ("0x0080", "User Flag8",                                                     "0x0080"),
            (None),
            ("0x0100", "DualSide Collision",                                             "0x0100"),
            ("0x0200", "Flag10",                                                         "0x0200"),
            ("0x0400", "No Dynamic Lighting",                                            "0x0400"),
            ("0x0800", "No Dynamic Shadows",                                             "0x0800"),
            (None),
            ("0x1000", "No Cast Shadows",                                                "0x1000"),
            ("0x2000", "Dont BSP Poly",                                                  "0x2000"),
            ("0x4000", "BSP Only Poly",                                                  "0x4000"),
            ("0x8000", "Flag16",                                                         "0x8000"),

            # swy: hardcoded Euroland flags
            ("", "Hardcoded Flags", ""),
            ("0x00010000", "Not backface culled",    "0x00010000"),
            ("0x00020000", "Portal",                 "0x00020000"),
            ("0x00040000", "Invisible",              "0x00040000"),
            ("0x00080000", "Line segment",           "0x00080000"),
            (None),
            ("0x00100000", "Facetted",               "0x00100000"),
            ("0x00200000", "Clip Portal",            "0x00200000"),
            ("0x01000000", "No collision",           "0x01000000"),
            ("0x02000000", "Always backface culled", "0x02000000")
        ],
        default = set(),
        update = update_after_enum
    )
    vertex_flags: bpy.props.EnumProperty(
        name = "Eurocom vertex flags",
        options = {'ENUM_FLAG'},
        items = [
            # swy: configurable per-project flags
            ("", "Project Flags", ""),
            ("0x0001", "Soft Skin Normal",     "0x0001"),
            ("0x0002", "Flag2",                "0x0002"),
            ("0x0004", "Flag3",                "0x0004"),
            ("0x0008", "Flag4",                "0x0008"),
            (None),
            ("0x0010", "Flag5",                "0x0010"),
            ("0x0020", "Flag6",                "0x0020"),
            ("0x0040", "Flag7",                "0x0040"),
            ("0x0080", "Flag8",                "0x0080"),
            (None),
            ("0x0100", "User Flag 1",          "0x0100"),
            ("0x0200", "User Flag 2",          "0x0200"),
            ("0x0400", "User Flag 3",          "0x0400"),
            ("0x0800", "User Flag 4",          "0x0800"),
            (None),
            ("0x1000", "Cloth Handrail",       "0x1000"),
            ("0x2000", "Cloth Breakpoint",     "0x2000"),
            ("0x4000", "Cloth Vertex",         "0x4000"),
            ("0x8000", "Fixed Cloth Vertex",   "0x8000"),
        ],
        default = set(),
        update = update_after_enum
    )
    
# swy: use a callback function to iterate across the whole thing,
#      works with vertices and faces, depending on the context:
#      https://stackoverflow.com/a/42544997/674685
def iterate_over_mesh(context, func):
    me = bpy.context.active_object.data
    bm = bmesh.from_edit_mesh(me)

    if 'euro_vtx_flags' not in bm.verts.layers.int:
            bm.verts.layers.int.new('euro_vtx_flags')

    if 'euro_fac_flags' not in bm.faces.layers.int:
            bm.faces.layers.int.new('euro_fac_flags')

    euro_vtx_flags = bm.verts.layers.int['euro_vtx_flags']
    euro_fac_flags = bm.faces.layers.int['euro_fac_flags']

    in_vtx_sel_mode = context.tool_settings.mesh_select_mode[0]

    if in_vtx_sel_mode:
        for v in bm.verts:
            func(v, euro_vtx_flags)
    else:
        for f in bm.faces:
            func(f, euro_fac_flags)

    # swy: without this it doesn't work: https://blender.stackexchange.com/a/188323/42781
    bm.select_flush_mode()
    bmesh.update_edit_mesh(me)

# swy: the functional meat for the buttons in the Mesh > Eurocom Tools panel
class EApplyFlags(bpy.types.Operator):
    """Assigns toggled flags from the panel in the current selection"""
    bl_idname  = "wm.ea"
    bl_label   = "Apply selected flags"
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        print("EApplyFlags: ", context)

        toggled_flags = enum_property_to_bitfield(context.mesh.euroland.vertex_flags)

        # swy: if this element is selected; overwrite the whole layer flag value with our own
        def callback(elem, layer):
            if (elem.select):
                elem[layer] = toggled_flags

        iterate_over_mesh(context, callback)

        return {'FINISHED'}

    def draw(self, context):    
        pass
        
class ESelectChFlags(bpy.types.Operator):
    """Select any elements with this combination of flags"""
    bl_idname  = "wm.eb"
    bl_label   = "Select any elements with this combination of flags"
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        print("ESelectChFlags: ", context)

        toggled_flags = enum_property_to_bitfield(context.mesh.euroland.vertex_flags)

        # swy: if the flag in the layer is part of the toggled flags (one of many); select it, and deselect everything else
        def callback(elem, layer):
            elem.select = (elem[layer] & toggled_flags) and True or False

        iterate_over_mesh(context, callback)

        return {'FINISHED'}

    def draw(self, context):
        pass



class ESelectNoFlags(bpy.types.Operator):
    """Select any elements with no flags checked"""
    bl_idname = "wm.ec"
    bl_label = "Select any elements with no flags checked"
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        print("ESelectNoFlags: ", context)

        # swy: if the flag in the layer says zero; select it, and deselect everything else
        def callback(elem, layer):
            elem.select = (elem[layer] == 0) and True or False

        iterate_over_mesh(context, callback)

        return {'FINISHED'}

    def draw(self, context):
        pass

import textwrap

@classmethod
def poll(cls, context):
    return False

# swy: for this to work the identifier of each enum element must be an hex string
def bitfield_to_enum_property(prop_group, prop, bitfield):
    result = set()

    # swy: why make it easy to retrieve the properties: https://blender.stackexchange.com/a/153365/42781
    for i, item in enumerate(prop_group.bl_rna.properties[prop].enum_items):
        # swy: is this bit one of the toggled on thingies in the bitfield? add it
        if int(item.identifier, 16) & bitfield:
            result.add(item)

    return result

def enum_property_to_bitfield(prop_val):
    bitfield = 0

    for item in prop_val:
        bitfield |= int(item, 16)

    return bitfield

class TOOLS_PANEL_PT_eurocom(bpy.types.Panel):
    bl_label = 'Eurocom Tools'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        return (context.object is not None and context.object.type == 'MESH' and bpy.context.mode == 'EDIT_MESH')

    def draw(self, context):
        box = self.layout.box()
        row = box.column_flow(columns=2)

        # --

        # swy: this is a bit backwards, because you can select both at the same time, but works
        in_vtx_sel_mode = context.tool_settings.mesh_select_mode[0]
        in_fac_sel_mode = context.tool_settings.mesh_select_mode[2]

        # swy: make it not work at all in edge mode or whenever both of them are toggled on use an
        #      exclusive or / xor operation, so that we only return True if either of them is on
        if in_vtx_sel_mode ^ in_fac_sel_mode:
            if in_fac_sel_mode:
                row.prop(context.mesh.euroland, "face_flags",   expand=True)
            if in_vtx_sel_mode:
                row.prop(context.mesh.euroland, "vertex_flags", expand=True)

            box.operator(
                EApplyFlags.bl_idname, icon=(in_fac_sel_mode and 'FACESEL' or 'VERTEXSEL'),
                text='Apply to selected ' + (in_fac_sel_mode and 'faces'   or 'vertices')
            )

            butt = self.layout.split()
            butt.label(text="Select any elements with...")
            
            butt = self.layout.split(align=True)
            butt.operator(ESelectChFlags.bl_idname, text='These flags checked')
            butt.operator(ESelectNoFlags.bl_idname, text='No flags checked')
        else:
            # swy: bad selection mode; tell the user about it
            box.alignment = 'CENTER'
            text_row = box.column_flow(columns=1)

            icon_row = text_row.row()
            icon_row.alignment = 'CENTER'
            icon_row.label(icon='FACESEL')
            icon_row.label(icon='VERTEXSEL')

            # swy: this is a bit of a silly way of wrapping the text and overflowing
            #      into various lines across the box
            text_list = textwrap.wrap(
                "Go into either the «face» or «vertex» select mode to edit the EuroLand flags...",
                width = (context.region.width / 7.2) / context.preferences.system.ui_scale
            )
            for line in text_list:
                text_row.label(text=(' ' * 6) + line)


# swy: global variable to store icons in
custom_icons = None

def menu_func_eif_import(self, context):
    self.layout.operator(ImportEIF.bl_idname, icon_value=custom_icons['sphinx_ico'].icon_id, text='Eurocom Interchange File (.eif)')
def menu_func_eif_export(self, context):
    self.layout.operator(ExportEIF.bl_idname, icon_value=custom_icons['sphinx_ico'].icon_id, text='Eurocom Interchange File (.eif)')

def menu_func_rtg_import(self, context):
    self.layout.operator(ImportRTG.bl_idname, icon_value=custom_icons['sphinx_ico'].icon_id, text='Eurocom Real Time Game (.rtg)')
def menu_func_rtg_export(self, context):
    self.layout.operator(ExportRTG.bl_idname, icon_value=custom_icons['sphinx_ico'].icon_id, text='Eurocom Real Time Game (.rtg)')

def menu_func_ese_import(self, context):
    self.layout.operator(ImportESE.bl_idname, icon_value=custom_icons['sphinx_ico'].icon_id, text='Eurocom Scene Export (.ese)')
def menu_func_ese_export(self, context):
    self.layout.operator(ExportESE.bl_idname, icon_value=custom_icons['sphinx_ico'].icon_id, text='Eurocom Scene Export (.ese)')

# swy: un/register the whole thing in one go, see below
classes = (
    ImportEIF,
    ImportRTG,
    ImportESE,

    ExportEIF,
    ExportRTG,
    ExportESE,

    # swy: export panel stuff
    EIF_EXPORT_PT_output_options,
    EIF_EXPORT_PT_scale,

    ESE_EXPORT_PT_object_types,
    ESE_EXPORT_PT_output_options,
    ESE_EXPORT_PT_mesh_options,
    ESE_EXPORT_PT_scale,

    # swy: mesh flags panel stuff
    TOOLS_PANEL_PT_eurocom,
    EApplyFlags,
    ESelectChFlags,
    ESelectNoFlags
)

menu_import = (menu_func_eif_import, menu_func_rtg_import, menu_func_ese_import)
menu_export = (menu_func_eif_export, menu_func_rtg_export, menu_func_ese_export)

# swy: initialize and de-initialize in opposite order
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    for m in menu_import:
        bpy.types.TOPBAR_MT_file_import.append(m)

    for m in menu_export:
        bpy.types.TOPBAR_MT_file_export.append(m)

    # swy: this is a bit of a dummy property for flag display; we actually
    #      retrieve the contents from a custom mesh layer, no other way
    bpy.utils.register_class(EuroProperties)
    bpy.types.Mesh.euroland = bpy.props.PointerProperty(type=EuroProperties)

    # swy: load every custom icon image from here; as an image preview
    global custom_icons; custom_icons = bpy.utils.previews.new()
    custom_icons.load('sphinx_ico', os.path.join(os.path.dirname(__file__), 'icons/sphinx.png'), 'IMAGE')

    bpy.app.handlers.depsgraph_update_post.append(scene_update_post_handler)

def unregister():
    global custom_icons; custom_icons.clear()
    bpy.utils.previews.remove(custom_icons)

    bpy.app.handlers.depsgraph_update_post.remove(scene_update_post_handler)

    for m in reversed(menu_export):
        bpy.types.TOPBAR_MT_file_export.remove(m)

    for m in reversed(menu_import):
        bpy.types.TOPBAR_MT_file_import.remove(m)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()
