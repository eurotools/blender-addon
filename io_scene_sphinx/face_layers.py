# SPDX-License-Identifier: Zlib
"""Shared EuroLand face-layer helpers used by the UI, EIF and ESE exporters."""

import re


MAX_FACE_LAYERS = 8
MATERIAL_ATTRIBUTE_PREFIX = "euro_material_layer_"
ENABLED_ATTRIBUTE_PREFIX = "euro_layer_enabled_"
UV_PROPERTY_PREFIX = "euro_uv_layer_"
COLOR_PROPERTY_PREFIX = "euro_color_layer_"


def int_face_attribute(mesh, name):
    attr = mesh.attributes.get(name)
    if attr and attr.data_type == 'INT' and attr.domain == 'FACE':
        return attr
    return None


def material_layer_attributes(mesh):
    result = {}
    for attr in mesh.attributes:
        match = re.fullmatch(r'euro_material_layer_(\d+)', attr.name)
        if not match or attr.data_type != 'INT' or attr.domain != 'FACE':
            continue
        index = int(match.group(1))
        if 0 < index < MAX_FACE_LAYERS:
            result[index] = attr
    return result


def enabled_layer_attributes(mesh):
    result = {}
    for attr in mesh.attributes:
        match = re.fullmatch(r'euro_layer_enabled_(\d+)', attr.name)
        if not match or attr.data_type != 'INT' or attr.domain != 'FACE':
            continue
        index = int(match.group(1))
        if 0 < index < MAX_FACE_LAYERS:
            result[index] = attr
    return result


def _mapped_layer(mesh, collection, property_prefix, layer_index):
    configured_name = str(mesh.get(f"{property_prefix}{layer_index}", ""))
    if configured_name:
        item = collection.get(configured_name)
        if item:
            return item
    return collection[layer_index] if layer_index < len(collection) else None


def uv_layers(mesh, enabled=True):
    if not enabled:
        return []
    return [
        _mapped_layer(mesh, mesh.uv_layers, UV_PROPERTY_PREFIX, index)
        for index in range(MAX_FACE_LAYERS)
    ]


def color_layers(mesh, available_layers, enabled=True):
    if not enabled:
        return []
    by_name = {layer.name: layer for layer in available_layers}
    result = []
    for index in range(MAX_FACE_LAYERS):
        configured_name = str(mesh.get(f"{COLOR_PROPERTY_PREFIX}{index}", ""))
        if configured_name and configured_name in by_name:
            result.append(by_name[configured_name])
        else:
            result.append(available_layers[index] if index < len(available_layers) else None)
    return result


def face_layer_enabled(mesh, polygon_index, layer_index, material_attributes=None, enabled_attributes=None):
    if layer_index == 0:
        return True
    material_attributes = material_attributes if material_attributes is not None else material_layer_attributes(mesh)
    enabled_attributes = enabled_attributes if enabled_attributes is not None else enabled_layer_attributes(mesh)
    enabled_attr = enabled_attributes.get(layer_index)
    if enabled_attr and polygon_index < len(enabled_attr.data):
        return bool(enabled_attr.data[polygon_index].value)
    material_attr = material_attributes.get(layer_index)
    return bool(
        material_attr
        and polygon_index < len(material_attr.data)
        and material_attr.data[polygon_index].value >= 0
    )


def face_material_index(mesh, polygon, layer_index, material_attributes=None, enabled_attributes=None):
    if layer_index == 0:
        return polygon.material_index
    if not face_layer_enabled(mesh, polygon.index, layer_index, material_attributes, enabled_attributes):
        return -1
    material_attributes = material_attributes if material_attributes is not None else material_layer_attributes(mesh)
    attr = material_attributes.get(layer_index)
    if not attr or polygon.index >= len(attr.data):
        return -1
    return attr.data[polygon.index].value


def face_layer_count(mesh, mapped_uv_layers=None, mapped_color_layers=None, has_materials=True):
    material_attributes = material_layer_attributes(mesh)
    enabled_attributes = enabled_layer_attributes(mesh)
    highest = 0 if has_materials else -1

    for index, layer in enumerate(mapped_uv_layers or []):
        if layer is not None:
            highest = max(highest, index)
    for index, layer in enumerate(mapped_color_layers or []):
        if layer is not None:
            highest = max(highest, index)
    if material_attributes:
        highest = max(highest, max(material_attributes))
    if enabled_attributes:
        highest = max(highest, max(enabled_attributes))

    return max(1, min(MAX_FACE_LAYERS, highest + 1))


def material_stack(mesh, polygon, layer_count, material_attributes=None, enabled_attributes=None):
    material_attributes = material_attributes if material_attributes is not None else material_layer_attributes(mesh)
    enabled_attributes = enabled_attributes if enabled_attributes is not None else enabled_layer_attributes(mesh)
    return tuple(
        face_material_index(mesh, polygon, index, material_attributes, enabled_attributes)
        for index in range(layer_count)
    )
