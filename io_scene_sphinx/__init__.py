#  Copyright (c) 2020-2021 Swyter <swyterzone+sphinx@gmail.com>
#  SPDX-License-Identifier: Zlib

bl_info = {
           'name': 'Eurocom 3D formats for Sphinx and the Cursed Mummy™',
         'author': 'Swyter, for THQ Nordic GmbH',
        'version': (2020, 10, 10),
        'blender': (2, 81, 6),
       'location': 'File > Import-Export',
    'description': 'Export and import EIF, ESE and RTG files compatible with Euroland.',
        'warning': 'Importing still doesn\'t work, export in progress. ¯\_(?)_/¯',
        'doc_url': 'https://sphinxandthecursedmummy.fandom.com/wiki/Technical',
    'tracker_url': 'https://discord.gg/sphinx',
        'support': 'COMMUNITY',
       'category': 'Import-Export',
}

import os
import bpy
import bpy.utils.previews
import bmesh

#-------------------------------------------------------------------------------------------------------------------------------
from bpy.props import(
        BoolProperty,
        IntProperty,
        FloatProperty,
        StringProperty,
        EnumProperty,
)

from bpy_extras.io_utils import(
        ImportHelper,
        ExportHelper,
        path_reference_mode,
)

#-------------------------------------------------------------------------------------------------------------------------------
# EIF Exporter
#-------------------------------------------------------------------------------------------------------------------------------
class ExportEIF(bpy.types.Operator, ExportHelper):
    """Save a static 3ds Max Euroland file, for scenes and entities"""

    bl_idname = "export_scene.eif"
    bl_label = 'Export EIF'
    bl_options = {'PRESET'}

    #-------------------------------------------------------------------------------------------------------------------------------
    filename_ext = ".eif"
    filter_glob: StringProperty(
                    default="*.eif", 
                    options={'HIDDEN'}
                ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    # Output Options
    #-------------------------------------------------------------------------------------------------------------------------------
    Output_GeomNode: BoolProperty(
        name="Output GeomNodes", 
        description="Output scene as a new map for EuroLand.", 
        default=True,
    ) # type: ignore

    Output_PlaceNode: BoolProperty(
        name="Output PlaceNodes", 
        description="Used to stamp clones of a GEOMNODE in a map.", 
        default=True,
    ) # type: ignore

    Transform_Center: BoolProperty(
        name="Transform Objects to (0,0,0)", 
        description="Transform objects location and rotation to (0,0,0).", 
        default=True,
    ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    # Mesh Options
    #-------------------------------------------------------------------------------------------------------------------------------
    Output_Mesh_Normals : BoolProperty(
        name="Mesh Normals",
        description="Export mesh normals",
        default=False,
    ) # type: ignore

    Output_Mesh_UV : BoolProperty(
        name="Mapping Coordinates",
        description="Export mesh UVs",
        default=True,
    ) # type: ignore

    Output_Mesh_Vertex_Colors : BoolProperty(
        name="Vertex Colors",
        description="Export mesh vertex colors",
        default=True,
    ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    # Precision
    #-------------------------------------------------------------------------------------------------------------------------------
    Decimal_Precision: IntProperty(
        name="Decimals:", 
        min=1, 
        max=10, 
        default=6,
    ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    # Scale
    #-------------------------------------------------------------------------------------------------------------------------------
    Output_Scale: FloatProperty(
        name="Scale", 
        min=0.01, 
        max=1000.0, 
        default=1.0,
    ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    path_mode: path_reference_mode
    check_extension = True

    #-------------------------------------------------------------------------------------------------------------------------------
    def execute(self, context):
        from mathutils import Matrix
        from . import eif_export

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "global_scale",
                                            "check_existing",
                                            "filter_glob",
                                            "path_mode",
                                        ))

        return eif_export.save(context, **keywords)

    def draw(self, context):
        pass

#-------------------------------------------------------------------------------------------------------------------------------
class EIF_EXPORT_PT_Output_Settings(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Output Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_eif"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Transform_Center')
        self.layout.prop(context.space_data.active_operator, 'Output_GeomNode')
        self.layout.prop(context.space_data.active_operator, 'Output_PlaceNode')

#-------------------------------------------------------------------------------------------------------------------------------
class EIF_EXPORT_PT_Mesh_Options(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Mesh Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_eif"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Output_Mesh_Normals')
        self.layout.prop(context.space_data.active_operator, 'Output_Mesh_UV')
        self.layout.prop(context.space_data.active_operator, 'Output_Mesh_Vertex_Colors')

#-------------------------------------------------------------------------------------------------------------------------------
class EIF_EXPORT_PT_Decimals_Precision(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Precision"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_eif"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Decimal_Precision')

#-------------------------------------------------------------------------------------------------------------------------------
class EIF_EXPORT_PT_Scale_Output(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Scale"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_eif"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Output_Scale')

#-------------------------------------------------------------------------------------------------------------------------------
# ESE Exporter
#-------------------------------------------------------------------------------------------------------------------------------
class ExportESE(bpy.types.Operator, ExportHelper):
    """Save a dynamic 3ds Max Euroland file; for cutscenes and maps"""

    bl_idname = "export_scene.ese"
    bl_label = 'Export ESE'
    bl_options = {'PRESET'}

    #-------------------------------------------------------------------------------------------------------------------------------
    filename_ext = ".ese"
    filter_glob: StringProperty(
                    default="*.ese", 
                    options={'HIDDEN'}
                ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    # Output Options
    #-------------------------------------------------------------------------------------------------------------------------------
    Output_Materials: BoolProperty(
        name="Materials",
        description="Output scene materials.",
        default=False,
    ) # type: ignore

    Output_Mesh_Anims: BoolProperty(
        name="Animated Mesh",
        description="Export mesh animations",
        default=True,
    ) # type: ignore

    Output_CameraLightAnims: BoolProperty(
        name="Animated Camera/Light settings",
        description="Export animations from Camera and Light object types.",
        default=False,
    ) # type: ignore

    Transform_Center: BoolProperty(
        name="Transform Objects to (0,0,0)", 
        description="Transform objects location and rotation to (0,0,0).", 
        default=False,
    ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    # Object Types
    #-------------------------------------------------------------------------------------------------------------------------------
    Object_Types: EnumProperty(
        name="Output Types",
        options={'ENUM_FLAG'},
        items=(('MESH', "Geometric", ""),
               ('CAMERA', "Cameras", ""),
               ('LIGHT', "Lights", ""),               
            ),
        description="Which kind of object to export",
        default={'MESH'}
    ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    # Mesh Options
    #-------------------------------------------------------------------------------------------------------------------------------
    Output_Mesh_Normals : BoolProperty(
        name="Mesh Normals",
        description="Export mesh normals",
        default=False,
    ) # type: ignore

    Output_Mesh_UV : BoolProperty(
        name="Mapping Coordinates",
        description="Export mesh UVs",
        default=False,
    ) # type: ignore

    Output_Mesh_Vertex_Colors : BoolProperty(
        name="Vertex Colors",
        description="Export mesh vertex colors",
        default=False,
    ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    # Static Output
    #-------------------------------------------------------------------------------------------------------------------------------
    Static_Frame: IntProperty(
        name="Frame #", 
        min=0, 
        max=2147483647, 
        default=1,
    ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    # Precision
    #-------------------------------------------------------------------------------------------------------------------------------
    Decimal_Precision: IntProperty(
        name="Decimals:", 
        min=1, 
        max=10, 
        default=6,
    ) # type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    # Scale
    #-------------------------------------------------------------------------------------------------------------------------------
    Output_Scale: FloatProperty(
        name="Scale Factor",
        min=0.01,
        max=1000.0,
        default=1.0,
    )# type: ignore

    #-------------------------------------------------------------------------------------------------------------------------------
    path_mode: path_reference_mode
    check_extension = True

    #-------------------------------------------------------------------------------------------------------------------------------
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

        return export_ese.save(context, **keywords)

    def draw(self, context):
        pass

#-------------------------------------------------------------------------------------------------------------------------------
class ESE_EXPORT_PT_Output_Options(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Output Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Output_Materials')
        self.layout.prop(context.space_data.active_operator, 'Output_Mesh_Anims')
        self.layout.prop(context.space_data.active_operator, 'Output_CameraLightAnims')
        self.layout.prop(context.space_data.active_operator, 'Transform_Center')

#-------------------------------------------------------------------------------------------------------------------------------
class ESE_EXPORT_PT_Object_Types(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Object Types"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        self.layout.column().prop(context.space_data.active_operator, "Object_Types")

#-------------------------------------------------------------------------------------------------------------------------------
class ESE_EXPORT_PT_Mesh_Options(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Mesh Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Output_Mesh_Normals')
        self.layout.prop(context.space_data.active_operator, 'Output_Mesh_UV')
        self.layout.prop(context.space_data.active_operator, 'Output_Mesh_Vertex_Colors')

#-------------------------------------------------------------------------------------------------------------------------------
class ESE_EXPORT_PT_Static_Output(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Static Output"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Static_Frame')

#-------------------------------------------------------------------------------------------------------------------------------
class ESE_EXPORT_PT_Decimals_Precision(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Precision"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Decimal_Precision')

#-------------------------------------------------------------------------------------------------------------------------------
class ESE_EXPORT_PT_Scale_Output(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Scale"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_ese"

    def draw(self, context):
        self.layout.prop(context.space_data.active_operator, 'Output_Scale')


#-------------------------------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------------------------------------------------
def scene_update_post_handler(scene):
    context = bpy.context

    if not (context.object is not None and context.object.type == 'MESH' and bpy.context.mode == 'EDIT_MESH'):
        return

    cur_sel_object = context.object
    cur_sel_indexes = []

    # swy: this is a bit backwards, because you can select both at the same time, but works
    in_vtx_sel_mode = context.tool_settings.mesh_select_mode[0]
    in_fac_sel_mode = context.tool_settings.mesh_select_mode[2]

    # swy: make it not work at all in edge mode or whenever both of them are toggled on; use an
    #      exclusive or / xor operation, so that we only return True if either of them is on
    if in_vtx_sel_mode ^ in_fac_sel_mode:
        thing = 0

        def callback(elem, layer):
            # use the parent function's scope: https://stackoverflow.com/a/8178808/674685
            nonlocal thing; nonlocal cur_sel_indexes
            if (elem.select):
                thing |= elem[layer]
                cur_sel_indexes.append(elem.index)

        iterate_over_mesh(context, callback)

        # swy: detect if we need to refresh the currently toggled flag elements;
        #      only do that if the selection changes; different, not every time
        #      Note: if we don't do this, we won't let the user change it
        global last_sel_object;
        global last_sel_indexes

        if cur_sel_object != last_sel_object:
            last_sel_indexes = False

        if cur_sel_indexes == last_sel_indexes:
            return

        last_sel_object  = cur_sel_object
        last_sel_indexes = cur_sel_indexes
        # --

        if in_vtx_sel_mode:
            selected = bitfield_to_enum_property(context.active_object.data.euroland, 'vertex_flags', thing)
            if context.active_object.data.euroland.vertex_flags != selected:
                context.active_object.data.euroland.vertex_flags = set((i.identifier) for i in selected)
                context.active_object.data.euroland.vertex_flags.update()
        elif in_fac_sel_mode:
            selected = bitfield_to_enum_property(context.active_object.data.euroland, 'face_flags', thing)
            if context.active_object.data.euroland.face_flags != selected:
                context.active_object.data.euroland.face_flags = set((i.identifier) for i in selected)
                context.active_object.data.euroland.face_flags.update()
    return

#-------------------------------------------------------------------------------------------------------------------------------
def update_after_enum(self, context):
    print('self.face_flags ---->', self.face_flags)

#-------------------------------------------------------------------------------------------------------------------------------
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

#-------------------------------------------------------------------------------------------------------------------------------
# swy: use a callback function to iterate across the whole thing,
#      works with vertices and faces, depending on the context:
#      https://stackoverflow.com/a/42544997/674685
#-------------------------------------------------------------------------------------------------------------------------------
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

#-------------------------------------------------------------------------------------------------------------------------------
def get_toggled_flags(context):
    in_vtx_sel_mode = context.tool_settings.mesh_select_mode[0]
    return enum_property_to_bitfield(in_vtx_sel_mode and context.mesh.euroland.vertex_flags or
                                                         context.mesh.euroland.face_flags)

#-------------------------------------------------------------------------------------------------------------------------------
# swy: the functional meat for the buttons in the Mesh > Eurocom Tools panel
#-------------------------------------------------------------------------------------------------------------------------------
class EApplyFlags(bpy.types.Operator):
    """Assigns toggled flags from the panel in the current selection"""
    bl_idname  = "wm.ea"
    bl_label   = "Apply selected flags"
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        print("EApplyFlags: ", context)

        toggled_flags = get_toggled_flags(context)

        # swy: if this element is selected; overwrite the whole layer flag value with our own
        def callback(elem, layer):
            if (elem.select):
                elem[layer] = toggled_flags

        iterate_over_mesh(context, callback)

        return {'FINISHED'}

    def draw(self, context):
        pass

#-------------------------------------------------------------------------------------------------------------------------------
class ESelectChFlags(bpy.types.Operator):
    """Select any elements with this combination of flags"""
    bl_idname  = "wm.eb"
    bl_label   = "Select any elements with this combination of flags"
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        print("ESelectChFlags: ", context)

        toggled_flags = get_toggled_flags(context)

        # swy: if the flag in the layer is part of the toggled flags (one of many); select it, and deselect everything else
        def callback(elem, layer):
            elem.select = (elem[layer] & toggled_flags) and True or False

        iterate_over_mesh(context, callback)

        return {'FINISHED'}

    def draw(self, context):
        pass

#-------------------------------------------------------------------------------------------------------------------------------
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

#-------------------------------------------------------------------------------------------------------------------------------
# swy: for this to work the identifier of each enum element must be an hex string
#-------------------------------------------------------------------------------------------------------------------------------
def bitfield_to_enum_property(prop_group, prop, bitfield):
    result = set()

    # swy: why make it easy to retrieve the properties: https://blender.stackexchange.com/a/153365/42781
    for i, item in enumerate(prop_group.bl_rna.properties[prop].enum_items):
        # swy: is this bit one of the toggled on thingies in the bitfield? add it
        if int(item.identifier, 16) & bitfield:
            result.add(item)

    return result

#-------------------------------------------------------------------------------------------------------------------------------
def enum_property_to_bitfield(prop_val):
    bitfield = 0

    for item in prop_val:
        bitfield |= int(item, 16)

    return bitfield

#-------------------------------------------------------------------------------------------------------------------------------
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

        # swy: make it not work at all in edge mode or whenever both of them are toggled on; use an
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


#-------------------------------------------------------------------------------------------------------------------------------
# swy: global variable to store icons in
#-------------------------------------------------------------------------------------------------------------------------------
custom_icons = None

#-------------------------------------------------------------------------------------------------------------------------------
# swy: avoid dereferencing non-existing icons, just in case
#-------------------------------------------------------------------------------------------------------------------------------
def sphinx_ico():
    if 'sphinx_ico' in custom_icons:
        return custom_icons['sphinx_ico'].icon_id
    return 'EXPERIMENTAL'

def menu_func_eif_export(self, context):
    self.layout.operator(ExportEIF.bl_idname, icon_value=sphinx_ico(), text='Eurocom Interchange File (.eif)')
def menu_func_ese_export(self, context):
    self.layout.operator(ExportESE.bl_idname, icon_value=sphinx_ico(), text='Eurocom Scene Export (.ese)')

#-------------------------------------------------------------------------------------------------------------------------------
# swy: un/register the whole thing in one go, see below
#-------------------------------------------------------------------------------------------------------------------------------
classes = (
    ExportEIF,
    ExportESE,

    #EIF Panels
    EIF_EXPORT_PT_Output_Settings,
    EIF_EXPORT_PT_Mesh_Options,
    EIF_EXPORT_PT_Decimals_Precision,
    EIF_EXPORT_PT_Scale_Output,

    #ESE Panels
    ESE_EXPORT_PT_Output_Options,
    ESE_EXPORT_PT_Object_Types,
    ESE_EXPORT_PT_Mesh_Options,
    ESE_EXPORT_PT_Static_Output,
    ESE_EXPORT_PT_Decimals_Precision,
    ESE_EXPORT_PT_Scale_Output,

    # swy: mesh flags panel stuff
    TOOLS_PANEL_PT_eurocom,
    EApplyFlags,
    ESelectChFlags,
    ESelectNoFlags,

    EuroProperties
)

menu_export = (menu_func_eif_export, menu_func_ese_export)

#-------------------------------------------------------------------------------------------------------------------------------
# swy: initialize and de-initialize in opposite order
#-------------------------------------------------------------------------------------------------------------------------------
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    for m in menu_export:
        bpy.types.TOPBAR_MT_file_export.append(m)

    # swy: this is a bit of a dummy property for flag display; we actually
    #      retrieve the contents from a custom mesh layer, no other way
    bpy.types.Mesh.euroland = bpy.props.PointerProperty(type=EuroProperties)

    # swy: load every custom icon image from here; as an image preview
    global custom_icons; custom_icons = bpy.utils.previews.new()
    custom_icons.load('sphinx_ico', os.path.join(os.path.dirname(__file__), 'icons/sphinx.png'), 'IMAGE')

    bpy.app.handlers.depsgraph_update_post.append(scene_update_post_handler)

#-------------------------------------------------------------------------------------------------------------------------------
def unregister():
    if scene_update_post_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(scene_update_post_handler)

    global custom_icons; custom_icons.clear()
    bpy.utils.previews.remove(custom_icons)

    for m in reversed(menu_export):
        bpy.types.TOPBAR_MT_file_export.remove(m)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()
