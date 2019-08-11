# -*- coding: utf-8 -*-
"""
Created on Sat May 27 18:36:36 2017

@author: amine
"""
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image
from osgeo import gdal

from utils import get_capabilities, rad_to_wmts, wmts_to_rad


class IGNMap(object):
    def __init__(self, upper_left_corner, lower_right_corner, zoom):
        self.upper_left_corner = upper_left_corner
        self.lower_right_corner = lower_right_corner
        self.zoom = zoom

        self.size = None
        self.capabilities = get_capabilities()[1][str(zoom)]
        self.max_tile = (int(self.capabilities['MaxTileRow']), int(self.capabilities['MaxTileCol']))
        self.scale_denominator = float(self.capabilities['ScaleDenominator'])
        self.tile_size = (int(self.capabilities['TileWidth']), int(self.capabilities['TileHeight']))
        self.top_left_corner = tuple(map(float, self.capabilities['TopLeftCorner'].split(' ')))
        self.set_coordinates(upper_left_corner, lower_right_corner)

    def set_coordinates(self, upper_left_corner, lower_right_corner):
        self.upper_left_corner = rad_to_wmts(self, upper_left_corner)
        self.lower_right_corner = rad_to_wmts(self, lower_right_corner)
        self.size = (self.lower_right_corner[0] - self.upper_left_corner[0] + 1,
                     self.lower_right_corner[1] - self.upper_left_corner[1] + 1)

    def request_tile(self, x, y):
        url = "https://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w/geoportail/wmts?layer=GEOGRAPHICALGRIDSYSTEMS.MAPS" \
              "&style=normal&tilematrixset=PM&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg" \
              "&TileMatrix={}&TileCol={}&TileRow={}".format(self.zoom, x, y)
        response = requests.get(url)
        return Image.open(BytesIO(response.content))

    def generate(self):
        map_IGN = Image.new('RGB', (256 * self.size[0], 256 * self.size[1]))
        self.cache_folder.mkdir(parents=True, exist_ok=True)
        for x in range(self.upper_left_corner[0], min(self.upper_left_corner[0] + self.size[0], self.max_tile[0])):
            for y in range(self.upper_left_corner[1], min(self.upper_left_corner[1] + self.size[1], self.max_tile[1])):
                path = self.cache_folder / "{}_{}.jpg".format(x - self.upper_left_corner[0], y - self.upper_left_corner[1])
                if path.exists():
                    img = Image.open(path)
                else:
                    img = self.request_tile(x, y)
                    img.save(path)
                map_IGN.paste(img, ((x - self.upper_left_corner[0]) * 256, (y - self.upper_left_corner[1]) * 256))
                map_IGN.save('map_IGN.jpg', "JPEG")
        return map_IGN

    def set_georeference(self, dstName, sourceDS, frmt="GTiff"):
        opt = gdal.TranslateOptions(format=frmt,
                                    outputBounds=[*wmts_to_rad(self, self.upper_left_corner),
                                                  *wmts_to_rad(self, self.lower_right_corner)],
                                    outputSRS="WGS84")
        gdal.Translate(dstName, sourceDS, options=opt)

    @property
    def cache_folder(self):
        return Path("tmp_{}-{}_{}-{}_{}".format(self.upper_left_corner[0], self.upper_left_corner[1],
                                                self.lower_right_corner[0], self.lower_right_corner[1], self.zoom))


if __name__ == '__main__':
    carte = IGNMap(("6°35'41.248", "45°57'30.243"), ("7°0'43.176", "45°44'39.177"), 12)
    print(carte.size[0] * carte.size[1], "tiles")
    carte.generate()
    #    carte.set_georeference("map_IGN_geo.tiff", "map_IGN.jpg", frmt = "GTiff")
    #    carte.set_georeference("map_IGN_geo.jpg", "map_IGN.jpg", frmt = "JPEG")
    carte.set_georeference("pyr_geo.pdf", "map_IGN.jpg", frmt="PDF")
