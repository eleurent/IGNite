"""IGNite: generate the geo-referenced IGN map of an area.

Usage: ignite.py [options] <upper_left> <lower_right> <zoom>

Options:
  -h --help                Show this screen.
  --processes <p>          Number of processes used for requests [default: 4].
  --out <file>             Output filename [default: out].
  --cache-folder <folder>  Cache directory [default: cache].
  --capabilities <file>    Capabilities filename [default: capabilities.xml]
  --no-caching             Do not save temporary tiles for caching and fast reloading.
  --backend <backend>      Which backend to use, between ign and cyclosm [default: cyclosm].
Note:
  Coordinates should be given as latitude,longitude in decimal degrees.
"""

from docopt import docopt
import functools
import numpy as np
from backend.ign import IGNMap
from backend.cyclosm import CyclOSMMap


def parse_position(location: str) -> np.ndarray:
    return np.asarray(tuple(map(float, location.split(","))))


if __name__ == '__main__':
    args = docopt(__doc__, version='IGNite 1.0')
    if args['--backend'] == 'ign':
        map_class = IGNMap
        map_class = functools.partial(map_class, capabilities=args['--capabilities'])
    elif args['--backend'] == 'cyclosm':
        map_class = CyclOSMMap
    else:
      raise ValueError('Invalid backend')

    tiled_map = map_class(
        min_point=parse_position(args["<upper_left>"]),
        max_point=parse_position(args["<lower_right>"]),
        zoom=int(args["<zoom>"]),
        output_path=args['--out'],
        cache_folder=args['--cache-folder'],
        no_caching=args['--no-caching'],
        processes=args['--processes'],
    )
    tiled_map.run()
