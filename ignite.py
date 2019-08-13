"""IGNite: generate the geo-referenced IGN map of an area.

Note: coordinates should be given as latitude,longitude decimal degrees.

Usage: ignite.py [options] <upper_left> <lower_right> <zoom>

Options:
  -h --help          Show this screen.
  --out_name <file>  Output filename [default: out].
  --no-caching       Do not save temporary tiles for caching and fast reloading.
  --processes <p>    Number of processes used for requests [default: 4].
"""
from docopt import docopt
from io import BytesIO
from multiprocessing.pool import Pool
from pathlib import Path

import requests
import tqdm
from PIL import Image
from osgeo import gdal

from utils import get_capabilities, deg_to_wmts, wmts_to_deg, str_to_point


class IGNMap(object):
    TILE_URL = "https://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w/geoportail/wmts?layer=GEOGRAPHICALGRIDSYSTEMS.MAPS" \
               "&style=normal&tilematrixset=PM&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg" \
               "&TileMatrix={}&TileCol={}&TileRow={}"
    CAPABILITIES_URL = "http://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w/geoportail/wmts?SERVICE=WMTS&REQUEST=GetCapabilities"

    def __init__(self, min_point, max_point, zoom, config):
        self.min_point = min_point
        self.max_point = max_point
        self.zoom = zoom
        self.config = config

        # Set map dimensions
        self.size = None
        self.capabilities = get_capabilities(self.CAPABILITIES_URL)[1][str(zoom)]
        self.scale_denominator = float(self.capabilities['ScaleDenominator'])
        self.tile_size = (int(self.capabilities['TileWidth']), int(self.capabilities['TileHeight']))
        self.top_left_corner = tuple(map(float, self.capabilities['TopLeftCorner'].split(' ')))
        self.min_point = deg_to_wmts(self, min_point)
        self.max_point = deg_to_wmts(self, max_point)
        self.size = (self.max_point[0] - self.min_point[0] + 1, self.max_point[1] - self.min_point[1] + 1)

        self.generate()
        self.geo_reference("{}.pdf".format(self.config["--out_name"]), "{}.jpg".format(self.config["--out_name"]))

    def generate(self):
        """
            Generate the map image by fetching and merging all tiles.
        :return: the map image
        """
        # Fetch tiles
        tiles = [(x, y) for x in range(self.min_point[0], self.max_point[0] + 1)
                        for y in range(self.min_point[1], self.max_point[1] + 1)]
        with Pool(int(self.config["--processes"])) as p:
            images = list(tqdm.tqdm(p.imap(self.get_tile, tiles), total=len(tiles), desc="Fetching"))

        # Merge tiles
        map_img = Image.new('RGB', (self.tile_size[0] * self.size[0], self.tile_size[1] * self.size[1]))
        for tile, img in tqdm.tqdm(zip(tiles, images), total=len(tiles), desc="Merging"):
            map_img.paste(img, ((tile[0] - self.min_point[0]) * self.tile_size[0],
                                (tile[1] - self.min_point[1]) * self.tile_size[1]))
        map_img.save("{}.jpg".format(self.config["--out_name"]), "JPEG")
        return map_img

    def get_tile(self, tile):
        """
            Get or fetch a given tile image.

            When fetched, the tile image is cached locally.
        :param tile: (x, y) WMTS coordinates of the tile
        :return: the tile image
        """
        path = self.cache_folder / "{}_{}.jpg".format(tile[0], tile[1])
        try:
            img = Image.open(path)
        except FileNotFoundError:
            response = requests.get(self.TILE_URL.format(self.zoom, tile[0], tile[1]))
            img = Image.open(BytesIO(response.content))
            if not self.config["--no-caching"]:
                path.parent.mkdir(parents=True, exist_ok=True)
                img.save(path)
        return img

    def geo_reference(self, dst_name, source_ds, _format="PDF"):
        """
            Embed a map image to a geotagged DST file.
        :param dst_name: geo-referenced dst file
        :param source_ds: source map image
        :param _format: dst file format
        """
        options = gdal.TranslateOptions(format=_format,
                                        outputBounds=[*reversed(wmts_to_deg(self, self.min_point)),
                                                      *reversed(wmts_to_deg(self, self.max_point))],
                                        outputSRS="WGS84")
        gdal.Translate(dst_name, source_ds, options=options)

    @property
    def cache_folder(self):
        return Path("tmp_{}".format(self.zoom))


if __name__ == '__main__':
    args = docopt(__doc__, version='IGNite 1.0')
    ign_map = IGNMap(str_to_point(args["<upper_left>"]),
                     str_to_point(args["<lower_right>"]),
                     int(args["<zoom>"]),
                     args)
