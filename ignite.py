# -*- coding: utf-8 -*-
"""
Created on Sat May 27 18:36:36 2017

@author: amine
"""
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen, Request
import os

import requests
from PIL import Image
from lxml import etree
from pandas import DataFrame
from scipy.optimize import brentq
import math
from osgeo import gdal


class IGNMap(object):

    def __init__(self, upper_left_corner, lower_right_corner, zoom):
        self.upper_left_corner = upper_left_corner
        self.lower_right_corner = lower_right_corner
        self.zoom = zoom

        self.size = None
        self.capabilities = IGNMap.get_capabilities()[1][str(zoom)]
        self.max_tile = (int(self.capabilities['MaxTileRow']), int(self.capabilities['MaxTileCol']))
        self.scale_denominator = float(self.capabilities['ScaleDenominator'])
        self.tile_size = (int(self.capabilities['TileWidth']), int(self.capabilities['TileHeight']))
        self.top_left_corner = tuple(map(float, self.capabilities['TopLeftCorner'].split(' ')))
        self.set_coordinates(upper_left_corner, lower_right_corner)

    def set_coordinates(self, upper_left_corner, lower_right_corner):
        self.upper_left_corner = self.coord_wmts(upper_left_corner)
        self.lower_right_corner = self.coord_wmts(lower_right_corner)
        self.size = (self.lower_right_corner[0] - self.upper_left_corner[0] + 1,
                     self.lower_right_corner[1] - self.upper_left_corner[1] + 1)

    def cache_folder(self):
        return Path("tmp_{}-{}_{}-{}_{}".format(self.upper_left_corner[0], self.upper_left_corner[1],
                                                self.lower_right_corner[0], self.lower_right_corner[1], self.zoom))

    def generate_map(self):
        map_IGN = Image.new('RGB', (256 * self.size[0], 256 * self.size[1]))
        self.cache_folder().mkdir(parents=True, exist_ok=True)
        for x in range(self.upper_left_corner[1], min(self.upper_left_corner[1] + self.size[1], self.max_tile[1])):
            for y in range(self.upper_left_corner[0], min(self.upper_left_corner[0] + self.size[0], self.max_tile[0])):
                path = self.cache_folder() / "{}_{}.jpg".format(x - self.upper_left_corner[1], y - self.upper_left_corner[0])
                if path.exists():
                    img = Image.open(path)
                else:
                    img = self.request_tile(x, y)
                    img.save(path)
                map_IGN.paste(img, ((x - self.upper_left_corner[1]) * 256, (y - self.upper_left_corner[0]) * 256))
                map_IGN.save('map_IGN.jpg', "JPEG")
        return map_IGN

    def request_tile(self, x, y):
        url = "https://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w/geoportail/wmts?layer=GEOGRAPHICALGRIDSYSTEMS.MAPS" \
              "&style=normal&tilematrixset=PM&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg" \
              "&TileMatrix={}&TileCol={}&TileRow={}".format(self.zoom, x, y)
        response = requests.get(url)
        return Image.open(BytesIO(response.content))

    def set_georeference(self, dstName, sourceDS, frmt="GTiff"):
        opt = gdal.TranslateOptions(format=frmt, outputBounds=self.get_ullr_tile(), outputSRS="WGS84")
        gdal.Translate(dstName, sourceDS, options=opt)

    @staticmethod
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

    @staticmethod
    def d2r(angle_deg):
        degre = float(angle_deg.split('°')[0])
        minutes = float(angle_deg.split('°')[1].split("'")[0])
        secondes = float(angle_deg.split('°')[1].split("'")[1])

        angle_dec = degre + (minutes / 60) + (secondes / 3600)

        return math.radians(angle_dec)

    def coord_wmts(self, point_rad, earth_radius=6378137.0, render_pixel_size=0.00028):
        tile_size = self.scale_denominator * render_pixel_size * self.tile_size[1]
        x = earth_radius * IGNMap.d2r(point_rad[0])
        y = earth_radius * math.log(math.tan(IGNMap.d2r(point_rad[1]) / 2 + math.pi / 4))

        row = int((self.top_left_corner[1] - y) / tile_size)
        col = int((x - self.top_left_corner[0]) / tile_size)
        return row, col

    def get_ullr_tile(self, earth_radius=6378137.0, render_pixel_size=0.00028):
        taille_tuile = self.scale_denominator * render_pixel_size * self.tile_size[1]

        # Calcul de X et Y a partir de TILECOL et TILEROW
        coords = lambda point:  (self.top_left_corner[0] + point[1] * taille_tuile,
                                 self.top_left_corner[1] - point[0] * taille_tuile)

        # Calcul longitudes et latitudes en deg
        ul_x = math.degrees(coords(self.upper_left_corner)[0] / earth_radius)
        lr_x = math.degrees(coords(self.lower_right_corner)[0] / earth_radius)
        Y_ul = coords(self.upper_left_corner)[1]
        Y_lr = coords(self.lower_right_corner)[1]

        def uly(x):
            return Y_ul - earth_radius * math.log(math.tan(x / 2 + math.pi / 4))

        def lry(x):
            return Y_lr - earth_radius * math.log(math.tan(x / 2 + math.pi / 4))

        ul_y = math.degrees(brentq(uly, 0, math.pi / 2))
        lr_y = math.degrees(brentq(lry, 0, math.pi / 2))

        return [ul_x, ul_y, lr_x, lr_y]




if __name__ == '__main__':
    carte = IGNMap(("6°35'41.248", "45°57'30.243"), ("7°0'43.176", "45°44'39.177"), 12)
    print(carte.size[0] * carte.size[1], "tiles")
    carte.generate_map()
    #    carte.set_georeference("map_IGN_geo.tiff", "map_IGN.jpg", frmt = "GTiff")
    #    carte.set_georeference("map_IGN_geo.jpg", "map_IGN.jpg", frmt = "JPEG")
    carte.set_georeference("pyr_geo.pdf", "map_IGN.jpg", frmt="PDF")

