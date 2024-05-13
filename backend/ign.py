from pathlib import Path
import numpy as np
import requests
from lxml import etree
from pandas import DataFrame
from scipy.optimize import brentq

from tiled_map import TiledMap


class IGNMap(TiledMap):
    TILE_URL = "https://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w/geoportail/wmts?layer=GEOGRAPHICALGRIDSYSTEMS.MAPS" \
               "&style=normal&tilematrixset=PM&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg" \
               "&TileMatrix={}&TileCol={}&TileRow={}"
    CAPABILITIES_URL = "http://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w/geoportail/wmts?SERVICE=WMTS&REQUEST=GetCapabilities"

    def __init__(
        self,
        min_point: np.ndarray,
        max_point: np.ndarray,
        zoom: int,
        output_path: str,
        cache_folder: str,
        no_caching: bool,
        processes: int,
        convert_to_wmts: bool = True,
    ):
        # Get WMTS coordinates from GPS coordinates
        self.capabilities = self.get_capabilities(self.CAPABILITIES_URL)[1][str(zoom)]
        self.scale_denominator = float(self.capabilities['ScaleDenominator'])
        self.tile_size = (int(self.capabilities['TileWidth']), int(self.capabilities['TileHeight']))
        self.top_left_corner = np.array(list(map(float, self.capabilities['TopLeftCorner'].split(' '))))
        if convert_to_wmts:
            min_point = self.deg_to_wmts(min_point)
            max_point = self.deg_to_wmts(max_point)

        super().__init__(
            min_point=min_point,
            max_point=max_point,
            zoom=zoom,
            tile_url=self.TILE_URL,
            output_path=output_path,
            cache_folder=cache_folder,
            no_caching=no_caching,
            processes=processes,
        )

    def deg_to_wmts(self, lat_deg: float, long_deg: float, zoom: int, earth_radius=6378137.0, render_pixel_size=0.00028):
        point_deg = np.array([lat_deg, long_deg])
        tile_radius = self.scale_denominator * render_pixel_size * self.tile_size[1]
        position = earth_radius * np.array([np.radians(point_deg)[1],
                                            np.log(np.tan(np.radians(point_deg)[0] / 2 + np.pi / 4))])
        wmts = np.floor((position - self.top_left_corner) / tile_radius) * np.array([1, -1])
        return wmts.astype(np.int)

    def wmts_to_deg(self, x_tile: int, y_tile: int, zoom: int, earth_radius=6378137.0, render_pixel_size=0.00028):
        point = np.array([x_tile, y_tile])
        tile_radius = self.scale_denominator * render_pixel_size * self.tile_size[1]
        coords = self.top_left_corner + point * np.array([1, -1]) * tile_radius

        def y_x(x):
            return coords[1] - earth_radius * np.log(np.tan(x / 2 + np.pi / 4))

        return np.array([np.degrees(brentq(y_x, 0, np.pi / 2)), np.degrees(coords[0] / earth_radius)])

    @staticmethod
    def get_capabilities(url, file_name="capabilities.xml"):
        # Fetch file
        if not Path(file_name).exists():
            response = requests.get(url)
            Path(file_name).parent.mkdir(parents=True, exist_ok=True)
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
                          elt.findall('ows:Identifier', dict_ns)[0].text == 'GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2']
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
