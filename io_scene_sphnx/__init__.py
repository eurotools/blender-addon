#  Copyright (c) 2020-2021 Swyter <swyterzone+sphinx@gmail.com>
#  SPDX-License-Identifier: Zlib

bl_info = {
           "name": "Eurocom 3D formats for Sphinx and the Cursed Mummy™",
         "author": "Swyter, for THQ Nordic GmbH",
        "version": (2020, 10, 10),
        "blender": (2, 81, 6),
       "location": "File > Import-Export",  
    "description": "Export and import EIF, ESE and RTG files compatible with Euroland.",
        "warning": "LOL ¯\_(ツ)_/¯",
        "doc_url": "https://sphinxandthecursedmummy.fandom.com/wiki/Technical",
    "tracker_url": "https://discord.gg/sphinx",
        "support": 'COMMUNITY',
       "category": "Import-Export",
}

if "bpy" in locals():
    import importlib
    
    if "import_eif" in locals():
        importlib.reload(import_eif)
    if "export_eif" in locals():
        importlib.reload(export_eif)
    if "import_rtg" in locals():
        importlib.reload(import_rtg)
    if "export_rtg" in locals():
        importlib.reload(export_rtg)     
    if "import_ese" in locals():
        importlib.reload(import_ese)
    if "export_ese" in locals():
        importlib.reload(export_ese)

import bpy
from bpy.props import (
        BoolProperty,
        FloatProperty,
        StringProperty,
        EnumProperty,
        )
from bpy_extras.io_utils import (
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

class EIF_Export_OutputOptions(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Output Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_eif"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'Output_Map')
        layout.prop(operator, 'Output_Transform')

class EIF_Export_Scale(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_eif"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "global_scale")

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
class ESE_Export_OutputOptions(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Output Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'Output_Materials')
        layout.prop(operator, 'Output_CameraLightAnims')
        layout.prop(operator, 'Output_Animations')
        
class ESE_Export_MeshOptions(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Mesh Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'Flip_Polygons')
        layout.prop(operator, 'Output_VertexColors')

class ESE_Export_ObjectTypes(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = ""
    bl_parent_id = "FILE_PT_operator"
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.column().prop(operator, "object_types")

class ESE_Export_Scale(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "global_scale")
 
class ReloadAddon(bpy.types.Operator):
    """Reloads the whole Eurocom 3D tools, for development """
    bl_idname = "wm.reload_sphnx"
    bl_label = "Reload the Eurocom Add-on (for development)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        bpy.ops.preferences.addon_enable(module='io_scene_sphnx')
        print("LOLOL")
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


def menu_func_eif_import(self, context):
    self.layout.operator(ImportEIF.bl_idname, text="Eurocom Interchange File (.eif)")
def menu_func_eif_export(self, context):
    self.layout.operator(ExportEIF.bl_idname, text="Eurocom Interchange File (.eif)")

def menu_func_rtg_import(self, context):
    self.layout.operator(ImportRTG.bl_idname, text="Eurocom Real Time Game (.rtg)")
def menu_func_rtg_export(self, context):
    self.layout.operator(ExportRTG.bl_idname, text="Eurocom Real Time Game (.rtg)")

def menu_func_ese_import(self, context):
    self.layout.operator(ImportESE.bl_idname, text="Eurocom Scene Export (.ese)")
def menu_func_ese_export(self, context):
    self.layout.operator(ExportESE.bl_idname, text="Eurocom Scene Export (.ese)")

        
classes = (
    ImportEIF,
    ImportRTG,
    ImportESE,
    
    ExportEIF,
    EIF_Export_OutputOptions,
    EIF_Export_Scale,
    ExportRTG,
    ExportESE,
    ESE_Export_ObjectTypes,
    ESE_Export_OutputOptions,
    ESE_Export_MeshOptions,
    ESE_Export_Scale,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    #bpy.types.TOPBAR_MT_file_import.append(menu_func_eif_import)
    #bpy.types.TOPBAR_MT_file_import.append(menu_func_rtg_import)
    #bpy.types.TOPBAR_MT_file_import.append(menu_func_ese_import)
        
    bpy.types.TOPBAR_MT_file_export.append(menu_func_eif_export)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_rtg_export)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_ese_export)
    
    # swy: don't unregister this because Blender crashes with an EXCEPTION_ACCESS_VIOLATION
    #      when the add-on reenable function reloads itself, kind of sucky. load it once:
    #       WM_operator_pystring_ex > RNA_pointer_as_string_keywords >
    #        RNA_pointer_as_string_keywords_ex > RNA_property_as_string >
    #          Macro_bl_label_length
    if not hasattr(bpy.types, bpy.ops.wm.reload_sphnx.idname()):
        bpy.utils.register_class(ReloadAddon)

def unregister():
    #bpy.types.TOPBAR_MT_file_import.remove(menu_func_eif_import)
    #bpy.types.TOPBAR_MT_file_import.remove(menu_func_rtg_import)
    #bpy.types.TOPBAR_MT_file_import.remove(menu_func_ese_import)
    
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_eif_export)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_rtg_export)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_ese_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
