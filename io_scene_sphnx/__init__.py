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
        default={'CAMERA'}
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
        
        
def update_after_enum(self, context):
    print('self.my_enum ---->', self.my_enum)
    
class IgnitProperties(bpy.types.PropertyGroup):
    my_enum = bpy.props.EnumProperty(
        name = "My options",
        description = "My enum description",
        items = [
            # swy: configurable per-project flags
            ("Silver", "Water / NoJump (line seg.)",                                     "0x0001"),
            ("Silver", "UnderWater / Ladder (line seg. and line poly)",                  "0x0002"),
            ("Silver", "Slippery (line poly) / Wall (line seg.) / NoDive (normal poly)", "0x0004"),
            ("Silver", "Moveable / Edge (line seg.)",                                    "0x0008"),
            ("Silver", "Riser / ZipHandle (grab poly)",                                  "0x0010"),
            ("Silver", "No Camera Collision",                                            "0x0020"),
            ("Silver", "No Char Lighting",                                               "0x0040"),
            ("Silver", "User Flag8",                                                     "0x0080"),
            ("Silver", "DualSide Collision",                                             "0x0100"),
            ("Silver", "Flag10",                                                         "0x0200"),
            ("Silver", "No Dynamic Lighting",                                            "0x0400"),
            ("Silver", "No Dynamic Shadows",                                             "0x0800"),
            ("Silver", "No Cast Shadows",                                                "0x1000"),
            ("Silver", "Dont BSP Poly",                                                  "0x2000"),
            ("Silver", "BSP Only Poly",                                                  "0x4000"),
            ("Silver", "Flag16",                                                         "0x8000"),
        
            # swy: hardcoded Euroland flags
            ("Silver",     "Not backface culled",    "0x00010000"),
            ("Gold",       "Portal",                 "0x00020000"),
            ("Space Grey", "Invisible",              "0x00040000"),
            ("Space Grey", "Line segment",           "0x00080000"),
            ("Space Grey", "Facetted",               "0x00100000"),
            ("Space Grey", "Clip Portal",            "0x00200000"),
            ("Space Grey", "No collision",           "0x01000000"),
            ("Space Grey", "Always backface culled", "0x02000000")
        ],
        update=update_after_enum
    )
    # my_string = bpy.props.StringProperty()
    # my_integer = bpy.props.IntProperty()

class TOOLS_PANEL_PT_eurocom(bpy.types.Panel):
    bl_label = 'Eurocom Tools'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        #row.prop(scene.ignit_panel, "my_enum", expand=True)

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

    EIF_EXPORT_PT_output_options,
    EIF_EXPORT_PT_scale,

    ESE_EXPORT_PT_object_types,
    ESE_EXPORT_PT_output_options,
    ESE_EXPORT_PT_mesh_options,
    ESE_EXPORT_PT_scale,

    TOOLS_PANEL_PT_eurocom
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

    # swy: load every custom icon image from here; as an image preview
    global custom_icons; custom_icons = bpy.utils.previews.new()
    custom_icons.load('sphinx_ico', os.path.join(os.path.dirname(__file__), 'icons/sphinx.png'), 'IMAGE')
 

def unregister():
    bpy.utils.previews.remove(custom_icons)

    for m in reversed(menu_export):
        bpy.types.TOPBAR_MT_file_export.append(m)

    for m in reversed(menu_import):
        bpy.types.TOPBAR_MT_file_import.append(m)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()
