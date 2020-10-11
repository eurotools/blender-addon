#  Copyright (c) 2020 Swyter <swyterzone+sphinx@gmail.com>
#
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
           "name": "Eurocom 3D formats for Sphinx and the Cursed Mummy",
         "author": "Swyter, for THQ Nordic",
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


@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportEIF(bpy.types.Operator, ImportHelper):
    """Load a static 3ds Max Euroland file"""
    bl_idname = "import_scene.eif"
    bl_label = "Import EIF"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".eif"
    filter_glob: StringProperty(
            default="*.eif",
            options={'HIDDEN'},
            )

    def execute(self, context):
        print("Selected: " + context.active_object.name)
        from . import import_eif

        if self.split_mode == 'OFF':
            self.use_split_objects = False
            self.use_split_groups = False
        else:
            self.use_groups_as_vgroups = False

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "split_mode",
                                            ))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix

        if bpy.data.is_saved and context.preferences.filepaths.use_relative_paths:
            import os
            keywords["relpath"] = os.path.dirname(bpy.data.filepath)

        return import_eif.load(context, **keywords)

    def draw(self, context):
        pass

@orientation_helper(axis_forward='-Z', axis_up='Y')
class ExportEIF(bpy.types.Operator, ExportHelper):
    """Save a static 3ds Max Euroland file"""

    bl_idname = "export_scene.eif"
    bl_label = 'Export EIF'
    bl_options = {'PRESET'}

    filename_ext = ".eif"
    filter_glob: StringProperty(
            default="*.eif",
            options={'HIDDEN'},
            )

    path_mode: path_reference_mode

    check_extension = True

    def execute(self, context):
        from . import export_obj

        from mathutils import Matrix
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            ))

        global_matrix = (Matrix.Scale(self.global_scale, 4) @
                         axis_conversion(to_forward=self.axis_forward,
                                         to_up=self.axis_up,
                                         ).to_4x4())

        keywords["global_matrix"] = global_matrix
        return export_obj.save(context, **keywords)

    def draw(self, context):
        pass


@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportRTG(bpy.types.Operator, ImportHelper):
    """Load a dynamic Maya Euroland file"""
    bl_idname = "import_scene.rtg"
    bl_label = "Import RTG"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".rtg"
    filter_glob: StringProperty(
            default="*.rtg",
            options={'HIDDEN'},
            )

    def execute(self, context):
        print("Selected: " + context.active_object.name)
        from . import import_eif

        if self.split_mode == 'OFF':
            self.use_split_objects = False
            self.use_split_groups = False
        else:
            self.use_groups_as_vgroups = False

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "split_mode",
                                            ))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix

        if bpy.data.is_saved and context.preferences.filepaths.use_relative_paths:
            import os
            keywords["relpath"] = os.path.dirname(bpy.data.filepath)

        return import_eif.load(context, **keywords)

    def draw(self, context):
        pass

@orientation_helper(axis_forward='-Z', axis_up='Y')
class ExportRTG(bpy.types.Operator, ExportHelper):
    """Save a dynamic Maya Euroland file"""

    bl_idname = "export_scene.rtg"
    bl_label = 'Export RTG'
    bl_options = {'PRESET'}

    filename_ext = ".rtg"
    filter_glob: StringProperty(
            default="*.rtg",
            options={'HIDDEN'},
            )

    path_mode: path_reference_mode

    check_extension = True

    def execute(self, context):
        from . import export_obj

        from mathutils import Matrix
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            ))

        global_matrix = (Matrix.Scale(self.global_scale, 4) @
                         axis_conversion(to_forward=self.axis_forward,
                                         to_up=self.axis_up,
                                         ).to_4x4())

        keywords["global_matrix"] = global_matrix
        return export_obj.save(context, **keywords)

    def draw(self, context):
        pass
        
        
@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportESE(bpy.types.Operator, ImportHelper):
    """Load a dynamic 3ds Max Euroland file"""
    bl_idname = "import_scene.ese"
    bl_label = "Import ESE"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".ese"
    filter_glob: StringProperty(
            default="*.ese",
            options={'HIDDEN'},
            )

    def execute(self, context):
        print("Selected: " + context.active_object.name)
        from . import import_eif

        if self.split_mode == 'OFF':
            self.use_split_objects = False
            self.use_split_groups = False
        else:
            self.use_groups_as_vgroups = False

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "split_mode",
                                            ))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix

        if bpy.data.is_saved and context.preferences.filepaths.use_relative_paths:
            import os
            keywords["relpath"] = os.path.dirname(bpy.data.filepath)

        return import_eif.load(context, **keywords)

    def draw(self, context):
        pass

@orientation_helper(axis_forward='-Z', axis_up='Y')
class ExportESE(bpy.types.Operator, ExportHelper):
    """Save a dynamic 3ds Max Euroland file"""

    bl_idname = "export_scene.ese"
    bl_label = 'Export ESE'
    bl_options = {'PRESET'}

    filename_ext = ".ese"
    filter_glob: StringProperty(
            default="*.ese",
            options={'HIDDEN'},
            )

    path_mode: path_reference_mode

    check_extension = True

    def execute(self, context):
        from . import export_obj

        from mathutils import Matrix
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            ))

        global_matrix = (Matrix.Scale(self.global_scale, 4) @
                         axis_conversion(to_forward=self.axis_forward,
                                         to_up=self.axis_up,
                                         ).to_4x4())

        keywords["global_matrix"] = global_matrix
        return export_obj.save(context, **keywords)

    def draw(self, context):
        pass

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
    ExportRTG,
    ExportESE,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_eif_import)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_rtg_import)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_ese_import)
        
    bpy.types.TOPBAR_MT_file_export.append(menu_func_eif_export)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_rtg_export)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_ese_export)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_eif_import)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_rtg_import)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_ese_import)
    
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_eif_export)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_rtg_export)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_ese_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
