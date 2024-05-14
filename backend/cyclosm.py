import numpy as np
from tiled_map import TiledMap


class CyclOSMMap(TiledMap):
    TILE_URL = "https://b.tile-cyclosm.openstreetmap.fr/cyclosm/{}/{}/{}.png"

    def __init__(
        self,
        min_point: np.ndarray,
        max_point: np.ndarray,
        zoom: int,
        output_path: str,
        cache_folder: str,
        no_caching: bool,
        processes: int,
        jpg_quality: int = 95,
    ):
        # Get WMTS coordinates from GPS coordinates
        min_point = self.deg_to_wmts(min_point[0], min_point[1], zoom)
        max_point = self.deg_to_wmts(max_point[0], max_point[1], zoom)

        super().__init__(
            min_point=min_point,
            max_point=max_point,
            zoom=zoom,
            tile_url=self.TILE_URL,
            output_path=output_path,
            cache_folder=cache_folder,
            no_caching=no_caching,
            processes=processes,
            jpg_quality=jpg_quality,
        )

    @staticmethod
    def wmts_to_deg(x_tile: int, y_tile: int, zoom: int):
        n = 2.0 ** zoom
        lon_deg = x_tile / n * 360.0 - 180.0
        lat_rad = np.arctan(np.sinh(np.pi * (1 - 2 * y_tile / n)))
        lat_deg = np.degrees(lat_rad)
        return np.array([lat_deg, lon_deg])

    @staticmethod
    def deg_to_wmts(lat_deg: float, lon_deg: float, zoom: int):
        lat_rad = np.radians(lat_deg)
        n = 2.0 ** zoom
        x_tile = int((lon_deg + 180.0) / 360.0 * n)
        y_tile = int((1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0 * n)
        return np.array([x_tile, y_tile])


