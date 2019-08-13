from pathlib import Path

import math
import requests
from lxml import etree
from pandas import DataFrame
from scipy.optimize import brentq


def str_to_point(location):
    return tuple(map(float, location.split(",")))


def deg_to_wmts(ign_map, point_deg, earth_radius=6378137.0, render_pixel_size=0.00028):
    tile_radius = ign_map.scale_denominator * render_pixel_size * ign_map.tile_size[1]
    long_lat_rad = tuple(reversed(tuple(map(math.radians, point_deg))))
    x = earth_radius * long_lat_rad[0]
    y = earth_radius * math.log(math.tan(long_lat_rad[1] / 2 + math.pi / 4))

    col = +int((x - ign_map.top_left_corner[0]) / tile_radius)
    row = -int((y - ign_map.top_left_corner[1]) / tile_radius)
    return col, row


def wmts_to_deg(ign_map, point, earth_radius=6378137.0, render_pixel_size=0.00028):
    tile_radius = ign_map.scale_denominator * render_pixel_size * ign_map.tile_size[1]
    coords = (ign_map.top_left_corner[0] + point[0] * tile_radius, ign_map.top_left_corner[1] - point[1] * tile_radius)

    def y_x(x):
        return coords[1] - earth_radius * math.log(math.tan(x / 2 + math.pi / 4))

    return math.degrees(brentq(y_x, 0, math.pi / 2)), math.degrees(coords[0] / earth_radius)


def get_capabilities(url, file_name="capabilities.xml"):
    # Fetch file
    if not Path(file_name).exists():
        response = requests.get(url)
        Path(file_name).write_bytes(response.content)

    # Parse file
    tree = etree.parse(file_name)
    root = tree.getroot()

    # Namespaces
    dict_ns = root.nsmap
    dict_ns['default'] = dict_ns[None]
    del dict_ns[None]

    # Layer selection
    layer_elements = [elt for elt in root.findall('default:Contents/default:Layer', dict_ns) if
                      elt.findall('ows:Identifier', dict_ns)[0].text == 'GEOGRAPHICALGRIDSYSTEMS.MAPS']
    layer_elements = layer_elements[0].findall('default:TileMatrixSetLink', dict_ns)[
        0].getchildren()  # Returns a list elts[TileMatrixSet, TileMatrixSetLimits]

    # Set TileMatrixSet
    d = {layer_elements[0].tag.split('}')[1]: layer_elements[0].text}
    res = [d]

    # Set zooms
    d1 = {}
    for elt in layer_elements[1].findall('default:TileMatrixLimits', dict_ns):
        zoom = elt.findall('default:TileMatrix', dict_ns)[0].text
        d1[zoom] = {}
        for x in elt.getchildren()[1:]:
            d1[zoom][x.tag.split('}')[1]] = x.text

        # Alimentation desTitleMatrixSet
        TMS = [elt for elt in root.findall('default:Contents/default:TileMatrixSet', dict_ns) if
               elt.findall('ows:Identifier', dict_ns)[0].text == layer_elements[0].text]
        TMS_select = [elt for elt in TMS[0].findall('default:TileMatrix', dict_ns) if
                      elt.find('ows:Identifier', dict_ns).text == zoom]
        for y in TMS_select[0].getchildren()[1:]:
            d1[zoom][y.tag.split('}')[1]] = y.text
    res.append(DataFrame(d1))
    return res