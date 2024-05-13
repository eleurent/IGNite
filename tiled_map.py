from docopt import docopt
# from multiprocessing.pool import Pool
from multiprocessing.dummy import Pool
from pathlib import Path
from osgeo import gdal
import PIL
from io import BytesIO
import numpy as np
import requests
import tqdm
import logging

logger = logging.getLogger(__name__)


class TiledMap:
    def __init__(self,
                 min_point: np.ndarray,
                 max_point: np.ndarray,
                 zoom: int,
                 tile_url: str,
                 output_path: str,
                 cache_folder: str,
                 no_caching: bool,
                 processes: int):
        self.min_point = min_point
        self.max_point = max_point
        self.zoom = zoom
        self.tile_url = tile_url
        self.output_path = output_path
        self.cache_folder = cache_folder
        self.no_caching = no_caching
        self.processes = processes

        self.size = self.max_point - self.min_point + 1

    def run(self):
        images = self.fetch_all()
        self.merge(images)
        self.geo_reference()

    def fetch_all(self):
        """ Fetch all tiles. """
        processes = int(self.processes) if self.processes else None
        with Pool(processes) as p:
            return list(tqdm.tqdm(p.imap(self.get_tile, self.tiles()), total=len(self.tiles()), desc="Fetching"))

    def merge(self, images):
        """ Merge all tiles. """
        tile_size = images[0].size
        map_img = PIL.Image.new('RGB', (tile_size[0] * self.size[0], tile_size[1] * self.size[1]))
        for tile, img in zip(self.tiles(), images):
            map_img.paste(img, ((tile[1] - self.min_point[0]) * tile_size[0],
                                (tile[2] - self.min_point[1]) * tile_size[1]))
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        map_img.save(Path(self.output_path).with_suffix(".jpg"), "JPEG")
        return map_img

    def tiles(self):
        z = self.zoom
        return [(z, x, y) for x in range(self.min_point[0], self.max_point[0] + 1)
                          for y in range(self.min_point[1], self.max_point[1] + 1)]

    def fetch_all_generator(self):
        for tile in self.tiles():
            yield self.get_tile(tile)

    def get_tile(self, tile):
        """
            Get or fetch a given tile image.

            When fetched, the tile image is cached locally.
        :param tile: (z, x, y) WMTS coordinates of the tile
        :return: the tile image
        """
        z, x, y = tile
        path = Path(self.cache_folder) / f"{z}_{x}_{y}"
        path = path.with_suffix(".png")  # or Path(self.TILE_URL).suffix
        try:
            img = PIL.Image.open(path)
        except FileNotFoundError:
            response = requests.get(self.TILE_URL.format(z, x, y))
            if not response.ok:
                logger.warning(f'Something wrong happened at tile {tile}, continuing... Error: Response not ok, reason:{response.reason}')
                return None
            try:
                img = PIL.Image.open(BytesIO(response.content))
            except PIL.UnidentifiedImageError as e:
                logger.warning(f'Something wrong happened at tile {tile}, continuing... Error:{e}')
                return None
            if not self.no_caching:
                path.parent.mkdir(parents=True, exist_ok=True)
                img.save(path)
        img_copy = img.copy()
        img.close()  # Explicitly close to avoid a "Too many open files" error.
        return img_copy

    def geo_reference(self, _format="PDF"):
        """
            Embed the map image to a geotagged DST file.
        :param _format: dst file format
        """
        options = gdal.TranslateOptions(
            format=_format,
            outputBounds=[*reversed(self.wmts_to_deg(self.min_point[0], self.min_point[1], self.zoom)),
                          *reversed(self.wmts_to_deg(self.max_point[0]+1, self.max_point[1]+1, self.zoom))],
            outputSRS="WGS84")
        gdal.Translate(str(Path(self.output_path).with_suffix(".pdf")),
                       str(Path(self.output_path).with_suffix(".jpg")),
                       options=options)

    def wmts_to_deg(self, x_tile: int, y_tile: int, zoom: int) -> np.ndarray:
        raise NotImplementedError


