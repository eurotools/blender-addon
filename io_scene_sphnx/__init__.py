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

class EuroProperties(bpy.types.PropertyGroup):
    ''' Per-face bitfield for Euroland entities. ''' 
    my_enum: bpy.props.EnumProperty(
        name = "Eurocom flags",
        options = {'ENUM_FLAG'},
        items = [
            # swy: configurable per-project flags0
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
        default=set(),
        update=update_after_enum
    )
    
    
class EApplyFlags(bpy.types.Operator):
    """Assigns toggled flags from the panel in the current selection"""
    bl_idname = "wm.ea"
    bl_label = "Apply selected flags"
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        print("EApplyFlags: ", context)
        return {'FINISHED'}

    def draw(self, context):
        pass
        
class ESelectChFlags(bpy.types.Operator):
    """Select any elements with this combination of flags"""
    bl_idname = "wm.eb"
    bl_label = "Select any elements with this combination of flags"
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        print("ESelectChFlags: ", context)
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
        return {'FINISHED'}

    def draw(self, context):
        pass

@classmethod
def poll(cls, context):
    return False

class TOOLS_PANEL_PT_eurocom(bpy.types.Panel):
    bl_label = 'Eurocom Tools'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    def draw(self, context):
        box = self.layout.box()
        row = box.column_flow(columns=2)
        row.prop(context.mesh.euroland, "my_enum", expand=True)
        box.operator(EApplyFlags.bl_idname, icon='MODIFIER', text='Apply to selected')
        
        butt = self.layout.split()
        butt.label(text="Select any elements with...")
        
        butt = self.layout.split(align=True)
        butt.operator(ESelectChFlags.bl_idname, text='These flags checked')
        butt.operator(ESelectNoFlags.bl_idname, text='No flags checked')

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


    bpy.utils.register_class(EuroProperties)
    bpy.types.Mesh.euroland = bpy.props.PointerProperty(type=EuroProperties)

    # swy: load every custom icon image from here; as an image preview
    global custom_icons; custom_icons = bpy.utils.previews.new()
    custom_icons.load('sphinx_ico', os.path.join(os.path.dirname(__file__), 'icons/sphinx.png'), 'IMAGE')

    class IconPanel(bpy.types.Panel):
        """Creates a Panel width all possible icons"""
        bl_label = "Icons"
        bl_idname = "icons_panel"
        bl_space_type = 'PROPERTIES'
        bl_region_type = 'WINDOW'
        bl_context = "object"

        def draw(self, context):
            icons = ['NONE', 'QUESTION', 'ERROR', 'CANCEL', 'TRIA_RIGHT', 'TRIA_DOWN', 'TRIA_LEFT', 'TRIA_UP', 'ARROW_LEFTRIGHT', 'PLUS', 'DISCLOSURE_TRI_RIGHT', 'DISCLOSURE_TRI_DOWN', 'RADIOBUT_OFF', 'RADIOBUT_ON', 'MENU_PANEL', 'BLENDER', 'GRIP', 'DOT', 'COLLAPSEMENU', 'X', 'DUPLICATE', 'TRASH', 'COLLECTION_NEW', 'OPTIONS', 'NODE', 'NODE_SEL', 'WINDOW', 'WORKSPACE', 'RIGHTARROW_THIN', 'BORDERMOVE', 'VIEWZOOM', 'ADD', 'REMOVE', 'PANEL_CLOSE', 'COPY_ID', 'EYEDROPPER', 'CHECKMARK', 'AUTO', 'CHECKBOX_DEHLT', 'CHECKBOX_HLT', 'UNLOCKED', 'LOCKED', 'UNPINNED', 'PINNED', 'SCREEN_BACK', 'RIGHTARROW', 'DOWNARROW_HLT', 'FCURVE_SNAPSHOT', 'OBJECT_HIDDEN', 'TOPBAR', 'STATUSBAR', 'PLUGIN', 'HELP', 'GHOST_ENABLED', 'COLOR', 'UNLINKED', 'LINKED', 'HAND', 'ZOOM_ALL', 'ZOOM_SELECTED', 'ZOOM_PREVIOUS', 'ZOOM_IN', 'ZOOM_OUT', 'DRIVER_DISTANCE', 'DRIVER_ROTATIONAL_DIFFERENCE', 'DRIVER_TRANSFORM', 'FREEZE', 'STYLUS_PRESSURE', 'GHOST_DISABLED', 'FILE_NEW', 'FILE_TICK', 'QUIT', 'URL', 'RECOVER_LAST', 'THREE_DOTS', 'FULLSCREEN_ENTER', 'FULLSCREEN_EXIT', 'BRUSHES_ALL', 'LIGHT', 'MATERIAL', 'TEXTURE', 'ANIM', 'WORLD', 'SCENE', 'OUTPUT', 'SCRIPT', 'PARTICLES', 'PHYSICS', 'SPEAKER', 'TOOL_SETTINGS', 'SHADERFX', 'MODIFIER', 'BLANK1', 'FAKE_USER_OFF', 'FAKE_USER_ON', 'VIEW3D', 'GRAPH', 'OUTLINER', 'PROPERTIES', 'FILEBROWSER', 'IMAGE', 'INFO', 'SEQUENCE', 'TEXT', 'SPREADSHEET', 'SOUND', 'ACTION', 'NLA', 'PREFERENCES', 'TIME', 'NODETREE', 'CONSOLE', 'TRACKER', 'ASSET_MANAGER', 'NODE_COMPOSITING', 'NODE_TEXTURE', 'NODE_MATERIAL', 'UV', 'OBJECT_DATAMODE', 'EDITMODE_HLT', 'UV_DATA', 'VPAINT_HLT', 'TPAINT_HLT', 'WPAINT_HLT', 'SCULPTMODE_HLT', 'POSE_HLT', 'PARTICLEMODE', 'TRACKING', 'TRACKING_BACKWARDS', 'TRACKING_FORWARDS', 'TRACKING_BACKWARDS_SINGLE', 'TRACKING_FORWARDS_SINGLE', 'TRACKING_CLEAR_BACKWARDS', 'TRACKING_CLEAR_FORWARDS', 'TRACKING_REFINE_BACKWARDS', 'TRACKING_REFINE_FORWARDS', 'SCENE_DATA', 'RENDERLAYERS', 'WORLD_DATA', 'OBJECT_DATA', 'MESH_DATA', 'CURVE_DATA', 'META_DATA', 'LATTICE_DATA', 'LIGHT_DATA', 'MATERIAL_DATA', 'TEXTURE_DATA', 'ANIM_DATA', 'CAMERA_DATA', 'PARTICLE_DATA', 'LIBRARY_DATA_DIRECT', 'GROUP', 'ARMATURE_DATA', 'COMMUNITY', 'BONE_DATA', 'CONSTRAINT', 'SHAPEKEY_DATA', 'CONSTRAINT_BONE', 'CAMERA_STEREO', 'PACKAGE', 'UGLYPACKAGE', 'EXPERIMENTAL', 'BRUSH_DATA', 'IMAGE_DATA', 'FILE', 'FCURVE', 'FONT_DATA', 'RENDER_RESULT', 'SURFACE_DATA', 'EMPTY_DATA', 'PRESET', 'RENDER_ANIMATION', 'RENDER_STILL', 'LIBRARY_DATA_BROKEN', 'BOIDS', 'STRANDS', 'LIBRARY_DATA_INDIRECT', 'GREASEPENCIL', 'LINE_DATA', 'LIBRARY_DATA_OVERRIDE', 'GROUP_BONE', 'GROUP_VERTEX', 'GROUP_VCOL', 'GROUP_UVS', 'FACE_MAPS', 'RNA', 'RNA_ADD', 'MOUSE_LMB', 'MOUSE_MMB', 'MOUSE_RMB', 'MOUSE_MOVE', 'MOUSE_LMB_DRAG', 'MOUSE_MMB_DRAG', 'MOUSE_RMB_DRAG', 'MEMORY', 'PRESET_NEW', 'DECORATE', 'DECORATE_KEYFRAME', 'DECORATE_ANIMATE', 'DECORATE_DRIVER', 'DECORATE_LINKED', 'DECORATE_LIBRARY_OVERRIDE', 'DECORATE_UNLOCKED', 'DECORATE_LOCKED', 'DECORATE_OVERRIDE', 'FUND', 'TRACKER_DATA', 'HEART', 'ORPHAN_DATA', 'USER', 'SYSTEM', 'SETTINGS', 'OUTLINER_OB_EMPTY', 'OUTLINER_OB_MESH', 'OUTLINER_OB_CURVE', 'OUTLINER_OB_LATTICE', 'OUTLINER_OB_META', 'OUTLINER_OB_LIGHT', 'OUTLINER_OB_CAMERA', 'OUTLINER_OB_ARMATURE', 'OUTLINER_OB_FONT', 'OUTLINER_OB_SURFACE', 'OUTLINER_OB_SPEAKER', 'OUTLINER_OB_FORCE_FIELD', 'OUTLINER_OB_GROUP_INSTANCE', 'OUTLINER_OB_GREASEPENCIL', 'OUTLINER_OB_LIGHTPROBE', 'OUTLINER_OB_IMAGE', 'OUTLINER_COLLECTION', 'RESTRICT_COLOR_OFF', 'RESTRICT_COLOR_ON', 'HIDE_ON', 'HIDE_OFF', 'RESTRICT_SELECT_ON', 'RESTRICT_SELECT_OFF', 'RESTRICT_RENDER_ON', 'RESTRICT_RENDER_OFF', 'RESTRICT_INSTANCED_OFF', 'OUTLINER_DATA_EMPTY', 'OUTLINER_DATA_MESH', 'OUTLINER_DATA_CURVE', 'OUTLINER_DATA_LATTICE', 'OUTLINER_DATA_META', 'OUTLINER_DATA_LIGHT', 'OUTLINER_DATA_CAMERA', 'OUTLINER_DATA_ARMATURE', 'OUTLINER_DATA_FONT', 'OUTLINER_DATA_SURFACE', 'OUTLINER_DATA_SPEAKER', 'OUTLINER_DATA_LIGHTPROBE', 'OUTLINER_DATA_GP_LAYER', 'OUTLINER_DATA_GREASEPENCIL', 'GP_SELECT_POINTS', 'GP_SELECT_STROKES', 'GP_MULTIFRAME_EDITING', 'GP_ONLY_SELECTED', 'GP_SELECT_BETWEEN_STROKES', 'MODIFIER_OFF', 'MODIFIER_ON', 'ONIONSKIN_OFF', 'ONIONSKIN_ON', 'RESTRICT_VIEW_ON', 'RESTRICT_VIEW_OFF', 'RESTRICT_INSTANCED_ON', 'MESH_PLANE', 'MESH_CUBE', 'MESH_CIRCLE', 'MESH_UVSPHERE', 'MESH_ICOSPHERE', 'MESH_GRID', 'MESH_MONKEY', 'MESH_CYLINDER', 'MESH_TORUS', 'MESH_CONE', 'MESH_CAPSULE', 'EMPTY_SINGLE_ARROW', 'LIGHT_POINT', 'LIGHT_SUN', 'LIGHT_SPOT', 'LIGHT_HEMI', 'LIGHT_AREA', 'CUBE', 'SPHERE', 'CONE', 'META_PLANE', 'META_CUBE', 'META_BALL', 'META_ELLIPSOID', 'META_CAPSULE', 'SURFACE_NCURVE', 'SURFACE_NCIRCLE', 'SURFACE_NSURFACE', 'SURFACE_NCYLINDER', 'SURFACE_NSPHERE', 'SURFACE_NTORUS', 'EMPTY_AXIS', 'STROKE', 'EMPTY_ARROWS', 'CURVE_BEZCURVE', 'CURVE_BEZCIRCLE', 'CURVE_NCURVE', 'CURVE_NCIRCLE', 'CURVE_PATH', 'LIGHTPROBE_CUBEMAP', 'LIGHTPROBE_PLANAR', 'LIGHTPROBE_GRID', 'COLOR_RED', 'COLOR_GREEN', 'COLOR_BLUE', 'TRIA_RIGHT_BAR', 'TRIA_DOWN_BAR', 'TRIA_LEFT_BAR', 'TRIA_UP_BAR', 'FORCE_FORCE', 'FORCE_WIND', 'FORCE_VORTEX', 'FORCE_MAGNETIC', 'FORCE_HARMONIC', 'FORCE_CHARGE', 'FORCE_LENNARDJONES', 'FORCE_TEXTURE', 'FORCE_CURVE', 'FORCE_BOID', 'FORCE_TURBULENCE', 'FORCE_DRAG', 'FORCE_FLUIDFLOW', 'RIGID_BODY', 'RIGID_BODY_CONSTRAINT', 'IMAGE_PLANE', 'IMAGE_BACKGROUND', 'IMAGE_REFERENCE', 'NODE_INSERT_ON', 'NODE_INSERT_OFF', 'NODE_TOP', 'NODE_SIDE', 'NODE_CORNER', 'ANCHOR_TOP', 'ANCHOR_BOTTOM', 'ANCHOR_LEFT', 'ANCHOR_RIGHT', 'ANCHOR_CENTER', 'SELECT_SET', 'SELECT_EXTEND', 'SELECT_SUBTRACT', 'SELECT_INTERSECT', 'SELECT_DIFFERENCE', 'ALIGN_LEFT', 'ALIGN_CENTER', 'ALIGN_RIGHT', 'ALIGN_JUSTIFY', 'ALIGN_FLUSH', 'ALIGN_TOP', 'ALIGN_MIDDLE', 'ALIGN_BOTTOM', 'BOLD', 'ITALIC', 'UNDERLINE', 'SMALL_CAPS', 'CON_ACTION', 'HOLDOUT_OFF', 'HOLDOUT_ON', 'INDIRECT_ONLY_OFF', 'INDIRECT_ONLY_ON', 'CON_CAMERASOLVER', 'CON_FOLLOWTRACK', 'CON_OBJECTSOLVER', 'CON_LOCLIKE', 'CON_ROTLIKE', 'CON_SIZELIKE', 'CON_TRANSLIKE', 'CON_DISTLIMIT', 'CON_LOCLIMIT', 'CON_ROTLIMIT', 'CON_SIZELIMIT', 'CON_SAMEVOL', 'CON_TRANSFORM', 'CON_TRANSFORM_CACHE', 'CON_CLAMPTO', 'CON_KINEMATIC', 'CON_LOCKTRACK', 'CON_SPLINEIK', 'CON_STRETCHTO', 'CON_TRACKTO', 'CON_ARMATURE', 'CON_CHILDOF', 'CON_FLOOR', 'CON_FOLLOWPATH', 'CON_PIVOT', 'CON_SHRINKWRAP', 'MODIFIER_DATA', 'MOD_WAVE', 'MOD_BUILD', 'MOD_DECIM', 'MOD_MIRROR', 'MOD_SOFT', 'MOD_SUBSURF', 'HOOK', 'MOD_PHYSICS', 'MOD_PARTICLES', 'MOD_BOOLEAN', 'MOD_EDGESPLIT', 'MOD_ARRAY', 'MOD_UVPROJECT', 'MOD_DISPLACE', 'MOD_CURVE', 'MOD_LATTICE', 'MOD_TINT', 'MOD_ARMATURE', 'MOD_SHRINKWRAP', 'MOD_CAST', 'MOD_MESHDEFORM', 'MOD_BEVEL', 'MOD_SMOOTH', 'MOD_SIMPLEDEFORM', 'MOD_MASK', 'MOD_CLOTH', 'MOD_EXPLODE', 'MOD_FLUIDSIM', 'MOD_MULTIRES', 'MOD_FLUID', 'MOD_SOLIDIFY', 'MOD_SCREW', 'MOD_VERTEX_WEIGHT', 'MOD_DYNAMICPAINT', 'MOD_REMESH', 'MOD_OCEAN', 'MOD_WARP', 'MOD_SKIN', 'MOD_TRIANGULATE', 'MOD_WIREFRAME', 'MOD_DATA_TRANSFER', 'MOD_NORMALEDIT', 'MOD_PARTICLE_INSTANCE', 'MOD_HUE_SATURATION', 'MOD_NOISE', 'MOD_OFFSET', 'MOD_SIMPLIFY', 'MOD_THICKNESS', 'MOD_INSTANCE', 'MOD_TIME', 'MOD_OPACITY', 'REC', 'PLAY', 'FF', 'REW', 'PAUSE', 'PREV_KEYFRAME', 'NEXT_KEYFRAME', 'PLAY_SOUND', 'PLAY_REVERSE', 'PREVIEW_RANGE', 'ACTION_TWEAK', 'PMARKER_ACT', 'PMARKER_SEL', 'PMARKER', 'MARKER_HLT', 'MARKER', 'KEYFRAME_HLT', 'KEYFRAME', 'KEYINGSET', 'KEY_DEHLT', 'KEY_HLT', 'MUTE_IPO_OFF', 'MUTE_IPO_ON', 'DRIVER', 'SOLO_OFF', 'SOLO_ON', 'FRAME_PREV', 'FRAME_NEXT', 'NLA_PUSHDOWN', 'IPO_CONSTANT', 'IPO_LINEAR', 'IPO_BEZIER', 'IPO_SINE', 'IPO_QUAD', 'IPO_CUBIC', 'IPO_QUART', 'IPO_QUINT', 'IPO_EXPO', 'IPO_CIRC', 'IPO_BOUNCE', 'IPO_ELASTIC', 'IPO_BACK', 'IPO_EASE_IN', 'IPO_EASE_OUT', 'IPO_EASE_IN_OUT', 'NORMALIZE_FCURVES', 'VERTEXSEL', 'EDGESEL', 'FACESEL', 'CURSOR', 'PIVOT_BOUNDBOX', 'PIVOT_CURSOR', 'PIVOT_INDIVIDUAL', 'PIVOT_MEDIAN', 'PIVOT_ACTIVE', 'CENTER_ONLY', 'ROOTCURVE', 'SMOOTHCURVE', 'SPHERECURVE', 'INVERSESQUARECURVE', 'SHARPCURVE', 'LINCURVE', 'NOCURVE', 'RNDCURVE', 'PROP_OFF', 'PROP_ON', 'PROP_CON', 'PROP_PROJECTED', 'PARTICLE_POINT', 'PARTICLE_TIP', 'PARTICLE_PATH', 'SNAP_FACE_CENTER', 'SNAP_PERPENDICULAR', 'SNAP_MIDPOINT', 'SNAP_OFF', 'SNAP_ON', 'SNAP_NORMAL', 'SNAP_GRID', 'SNAP_VERTEX', 'SNAP_EDGE', 'SNAP_FACE', 'SNAP_VOLUME', 'SNAP_INCREMENT', 'STICKY_UVS_LOC', 'STICKY_UVS_DISABLE', 'STICKY_UVS_VERT', 'CLIPUV_DEHLT', 'CLIPUV_HLT', 'SNAP_PEEL_OBJECT', 'GRID', 'OBJECT_ORIGIN', 'ORIENTATION_GLOBAL', 'ORIENTATION_GIMBAL', 'ORIENTATION_LOCAL', 'ORIENTATION_NORMAL', 'ORIENTATION_VIEW', 'COPYDOWN', 'PASTEDOWN', 'PASTEFLIPUP', 'PASTEFLIPDOWN', 'VIS_SEL_11', 'VIS_SEL_10', 'VIS_SEL_01', 'VIS_SEL_00', 'AUTOMERGE_OFF', 'AUTOMERGE_ON', 'UV_VERTEXSEL', 'UV_EDGESEL', 'UV_FACESEL', 'UV_ISLANDSEL', 'UV_SYNC_SELECT', 'TRANSFORM_ORIGINS', 'GIZMO', 'ORIENTATION_CURSOR', 'NORMALS_VERTEX', 'NORMALS_FACE', 'NORMALS_VERTEX_FACE', 'SHADING_BBOX', 'SHADING_WIRE', 'SHADING_SOLID', 'SHADING_RENDERED', 'SHADING_TEXTURE', 'OVERLAY', 'XRAY', 'LOCKVIEW_OFF', 'LOCKVIEW_ON', 'AXIS_SIDE', 'AXIS_FRONT', 'AXIS_TOP', 'LAYER_USED', 'LAYER_ACTIVE', 'OUTLINER_OB_HAIR', 'OUTLINER_DATA_HAIR', 'HAIR_DATA', 'OUTLINER_OB_POINTCLOUD', 'OUTLINER_DATA_POINTCLOUD', 'POINTCLOUD_DATA', 'OUTLINER_OB_VOLUME', 'OUTLINER_DATA_VOLUME', 'VOLUME_DATA', 'HOME', 'DOCUMENTS', 'TEMP', 'SORTALPHA', 'SORTBYEXT', 'SORTTIME', 'SORTSIZE', 'SHORTDISPLAY', 'LONGDISPLAY', 'IMGDISPLAY', 'BOOKMARKS', 'FONTPREVIEW', 'FILTER', 'NEWFOLDER', 'FOLDER_REDIRECT', 'FILE_PARENT', 'FILE_REFRESH', 'FILE_FOLDER', 'FILE_BLANK', 'FILE_BLEND', 'FILE_IMAGE', 'FILE_MOVIE', 'FILE_SCRIPT', 'FILE_SOUND', 'FILE_FONT', 'FILE_TEXT', 'SORT_DESC', 'SORT_ASC', 'LINK_BLEND', 'APPEND_BLEND', 'IMPORT', 'EXPORT', 'LOOP_BACK', 'LOOP_FORWARDS', 'BACK', 'FORWARD', 'FILE_ARCHIVE', 'FILE_CACHE', 'FILE_VOLUME', 'FILE_3D', 'FILE_HIDDEN', 'FILE_BACKUP', 'DISK_DRIVE', 'MATPLANE', 'MATSPHERE', 'MATCUBE', 'MONKEY', 'HAIR', 'ALIASED', 'ANTIALIASED', 'MAT_SPHERE_SKY', 'MATSHADERBALL', 'MATCLOTH', 'MATFLUID', 'WORDWRAP_OFF', 'WORDWRAP_ON', 'SYNTAX_OFF', 'SYNTAX_ON', 'LINENUMBERS_OFF', 'LINENUMBERS_ON', 'SCRIPTPLUGINS', 'DISC', 'DESKTOP', 'EXTERNAL_DRIVE', 'NETWORK_DRIVE', 'SEQ_SEQUENCER', 'SEQ_PREVIEW', 'SEQ_LUMA_WAVEFORM', 'SEQ_CHROMA_SCOPE', 'SEQ_HISTOGRAM', 'SEQ_SPLITVIEW', 'SEQ_STRIP_META', 'SEQ_STRIP_DUPLICATE', 'IMAGE_RGB', 'IMAGE_RGB_ALPHA', 'IMAGE_ALPHA', 'IMAGE_ZDEPTH', 'HANDLE_AUTOCLAMPED', 'HANDLE_AUTO', 'HANDLE_ALIGNED', 'HANDLE_VECTOR', 'HANDLE_FREE', 'VIEW_PERSPECTIVE', 'VIEW_ORTHO', 'VIEW_CAMERA', 'VIEW_PAN', 'VIEW_ZOOM', 'BRUSH_BLOB', 'BRUSH_BLUR', 'BRUSH_CLAY', 'BRUSH_CLAY_STRIPS', 'BRUSH_CLONE', 'BRUSH_CREASE', 'BRUSH_FILL', 'BRUSH_FLATTEN', 'BRUSH_GRAB', 'BRUSH_INFLATE', 'BRUSH_LAYER', 'BRUSH_MASK', 'BRUSH_MIX', 'BRUSH_NUDGE', 'BRUSH_PINCH', 'BRUSH_SCRAPE', 'BRUSH_SCULPT_DRAW', 'BRUSH_SMEAR', 'BRUSH_SMOOTH', 'BRUSH_SNAKE_HOOK', 'BRUSH_SOFTEN', 'BRUSH_TEXDRAW', 'BRUSH_TEXFILL', 'BRUSH_TEXMASK', 'BRUSH_THUMB', 'BRUSH_ROTATE', 'GPBRUSH_SMOOTH', 'GPBRUSH_THICKNESS', 'GPBRUSH_STRENGTH', 'GPBRUSH_GRAB', 'GPBRUSH_PUSH', 'GPBRUSH_TWIST', 'GPBRUSH_PINCH', 'GPBRUSH_RANDOMIZE', 'GPBRUSH_CLONE', 'GPBRUSH_WEIGHT', 'GPBRUSH_PENCIL', 'GPBRUSH_PEN', 'GPBRUSH_INK', 'GPBRUSH_INKNOISE', 'GPBRUSH_BLOCK', 'GPBRUSH_MARKER', 'GPBRUSH_FILL', 'GPBRUSH_AIRBRUSH', 'GPBRUSH_CHISEL', 'GPBRUSH_ERASE_SOFT', 'GPBRUSH_ERASE_HARD', 'GPBRUSH_ERASE_STROKE', 'SMALL_TRI_RIGHT_VEC', 'KEYTYPE_KEYFRAME_VEC', 'KEYTYPE_BREAKDOWN_VEC', 'KEYTYPE_EXTREME_VEC', 'KEYTYPE_JITTER_VEC', 'KEYTYPE_MOVING_HOLD_VEC', 'HANDLETYPE_FREE_VEC', 'HANDLETYPE_ALIGNED_VEC', 'HANDLETYPE_VECTOR_VEC', 'HANDLETYPE_AUTO_VEC', 'HANDLETYPE_AUTO_CLAMP_VEC', 'COLORSET_01_VEC', 'COLORSET_02_VEC', 'COLORSET_03_VEC', 'COLORSET_04_VEC', 'COLORSET_05_VEC', 'COLORSET_06_VEC', 'COLORSET_07_VEC', 'COLORSET_08_VEC', 'COLORSET_09_VEC', 'COLORSET_10_VEC', 'COLORSET_11_VEC', 'COLORSET_12_VEC', 'COLORSET_13_VEC', 'COLORSET_14_VEC', 'COLORSET_15_VEC', 'COLORSET_16_VEC', 'COLORSET_17_VEC', 'COLORSET_18_VEC', 'COLORSET_19_VEC', 'COLORSET_20_VEC', 'COLLECTION_COLOR_01', 'COLLECTION_COLOR_02', 'COLLECTION_COLOR_03', 'COLLECTION_COLOR_04', 'COLLECTION_COLOR_05', 'COLLECTION_COLOR_06', 'COLLECTION_COLOR_07', 'COLLECTION_COLOR_08', 'EVENT_A', 'EVENT_B', 'EVENT_C', 'EVENT_D', 'EVENT_E', 'EVENT_F', 'EVENT_G', 'EVENT_H', 'EVENT_I', 'EVENT_J', 'EVENT_K', 'EVENT_L', 'EVENT_M', 'EVENT_N', 'EVENT_O', 'EVENT_P', 'EVENT_Q', 'EVENT_R', 'EVENT_S', 'EVENT_T', 'EVENT_U', 'EVENT_V', 'EVENT_W', 'EVENT_X', 'EVENT_Y', 'EVENT_Z', 'EVENT_SHIFT', 'EVENT_CTRL', 'EVENT_ALT', 'EVENT_OS', 'EVENT_F1', 'EVENT_F2', 'EVENT_F3', 'EVENT_F4', 'EVENT_F5', 'EVENT_F6', 'EVENT_F7', 'EVENT_F8', 'EVENT_F9', 'EVENT_F10', 'EVENT_F11', 'EVENT_F12', 'EVENT_ESC', 'EVENT_TAB', 'EVENT_PAGEUP', 'EVENT_PAGEDOWN', 'EVENT_RETURN', 'EVENT_SPACEKEY']
            for i in icons:
                row = self.layout.row()
                row.label(text=i, icon=i)

    bpy.utils.register_class(IconPanel)
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
