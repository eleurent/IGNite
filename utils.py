from pathlib import Path

import math
import requests
from lxml import etree
from pandas import DataFrame
from scipy.optimize import brentq


def decimal_degrees_to_rad(location):
    return tuple(reversed(tuple(map(math.radians, map(float, location.split(","))))))


def dms_to_rad(angle_deg):
    degre = float(angle_deg.split('°')[0])
    minutes = float(angle_deg.split('°')[1].split("'")[0])
    seconds = float(angle_deg.split('°')[1].split("'")[1])
    angle_dec = degre + (minutes / 60) + (seconds / 3600)
    return math.radians(angle_dec)


def rad_to_wmts(map, point_rad, earth_radius=6378137.0, render_pixel_size=0.00028):
    tile_radius = map.scale_denominator * render_pixel_size * map.tile_size[1]
    x = earth_radius * point_rad[0]
    y = earth_radius * math.log(math.tan(point_rad[1] / 2 + math.pi / 4))

    col = +int((x - map.top_left_corner[0]) / tile_radius)
    row = -int((y - map.top_left_corner[1]) / tile_radius)
    return col, row


def wmts_to_deg(map, point, earth_radius=6378137.0, render_pixel_size=0.00028):
    tile_radius = map.scale_denominator * render_pixel_size * map.tile_size[1]
    coords = (map.top_left_corner[0] + point[0] * tile_radius, map.top_left_corner[1] - point[1] * tile_radius)
    x = math.degrees(coords[0] / earth_radius)

    def y_x(x):
        return coords[1] - earth_radius * math.log(math.tan(x / 2 + math.pi / 4))

    y = math.degrees(brentq(y_x, 0, math.pi / 2))
    return x, y


def get_capabilities(file_name="capabilities.xml"):
    if not Path(file_name).exists():
        url = "http://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w/geoportail/wmts?SERVICE=WMTS&REQUEST=GetCapabilities"
        response = requests.get(url)
        Path(file_name).write_bytes(response.content)

    res = []
    tree = etree.parse(file_name)
    root = tree.getroot()
    # Dictionnaire des namespaces en remplacant celui de None par default
    dict_ns = root.nsmap
    dict_ns['default'] = dict_ns[None]
    del dict_ns[None]

    # Selection du Layer souhaité
    layer_elt_list = [elt for elt in root.findall('default:Contents/default:Layer', dict_ns) if
                      elt.findall('ows:Identifier', dict_ns)[0].text == 'GEOGRAPHICALGRIDSYSTEMS.MAPS']

    layer_elts = layer_elt_list[0].findall('default:TileMatrixSetLink', dict_ns)[
        0].getchildren()  # Returns list elts[TileMatrixSet, TileMatrixSetLimits]

    # Alimentation du TileMatrixset dans layer
    d = {}
    d[layer_elts[0].tag.split('}')[1]] = layer_elts[0].text
    res.append(d)

    # Alimentation des zooms
    d1 = {}
    for elt in layer_elts[1].findall('default:TileMatrixLimits',
                                     dict_ns):  # Parcourir tous les niveaux de zooms dispo
        zoom = elt.findall('default:TileMatrix', dict_ns)[0].text
        d1[zoom] = {}
        for x in elt.getchildren()[1:]:
            d1[zoom][x.tag.split('}')[1]] = x.text

        # Alimentation desTitleMatrixSet
        TMS = [elt for elt in root.findall('default:Contents/default:TileMatrixSet', dict_ns) if
               elt.findall('ows:Identifier', dict_ns)[0].text == layer_elts[0].text]
        TMS_select = [elt for elt in TMS[0].findall('default:TileMatrix', dict_ns) if
                      elt.find('ows:Identifier', dict_ns).text == zoom]
        for y in TMS_select[0].getchildren()[1:]:
            d1[zoom][y.tag.split('}')[1]] = y.text
    res.append(DataFrame(d1))
    return res