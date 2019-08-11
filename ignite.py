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
    def __init__(self, min_point, max_point, zoom):
        self.min_point = min_point
        self.max_point = max_point
        self.zoom = zoom

        self.size = None
        self.capabilities = get_capabilities()[1][str(zoom)]
        self.max_tile = (int(self.capabilities['MaxTileRow']), int(self.capabilities['MaxTileCol']))
        self.scale_denominator = float(self.capabilities['ScaleDenominator'])
        self.tile_size = (int(self.capabilities['TileWidth']), int(self.capabilities['TileHeight']))
        self.top_left_corner = tuple(map(float, self.capabilities['TopLeftCorner'].split(' ')))
        self.set_coordinates(min_point, max_point)

    def set_coordinates(self, min_point, max_point):
        self.min_point = rad_to_wmts(self, min_point)
        self.max_point = rad_to_wmts(self, max_point)
        self.size = (self.max_point[0] - self.min_point[0] + 1,
                     self.max_point[1] - self.min_point[1] + 1)

    def set_tile(self, tile):
        path = self.cache_folder / "{}_{}.jpg".format(tile[0] - self.min_point[0], tile[1] - self.min_point[1])
        if path.exists():
            img = Image.open(path)
        else:
            img = self.fetch_tile(tile)
            img.save(path)
        self.map.paste(img, ((tile[0] - self.min_point[0]) * 256, (tile[1] - self.min_point[1]) * 256))

    def fetch_tile(self, tile):
        url = "https://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w/geoportail/wmts?layer=GEOGRAPHICALGRIDSYSTEMS.MAPS" \
              "&style=normal&tilematrixset=PM&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg" \
              "&TileMatrix={}&TileCol={}&TileRow={}".format(self.zoom, tile[0], tile[1])
        response = requests.get(url)
        return Image.open(BytesIO(response.content))

    def generate(self):
        self.map = Image.new('RGB', (256 * self.size[0], 256 * self.size[1]))
        self.cache_folder.mkdir(parents=True, exist_ok=True)
        tiles = [(x, y) for x in range(self.min_point[0], self.max_point[0] + 1)
                        for y in range(self.min_point[1], self.max_point[1] + 1)]
        for tile in tiles:
            self.set_tile(tile)
        self.map.save('out.jpg', "JPEG")
        return self.map

    def set_georeference(self, dstName, sourceDS, frmt="GTiff"):
        opt = gdal.TranslateOptions(format=frmt,
                                    outputBounds=[*wmts_to_rad(self, self.min_point),
                                                  *wmts_to_rad(self, self.max_point)],
                                    outputSRS="WGS84")
        gdal.Translate(dstName, sourceDS, options=opt)

    @property
    def cache_folder(self):
        return Path("tmp_{}-{}_{}-{}_{}".format(self.min_point[0], self.min_point[1],
                                                self.max_point[0], self.max_point[1], self.zoom))


if __name__ == '__main__':
    carte = IGNMap(("6°35'41.248", "45°57'30.243"), ("7°0'43.176", "45°44'39.177"), 12)
    print(carte.size[0] * carte.size[1], "tiles")
    carte.generate()
    carte.set_georeference("out.pdf", "out.jpg", frmt="PDF")
