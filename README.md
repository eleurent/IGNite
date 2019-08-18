# IGNite :world_map::fire:
Get the georeferenced IGN map of any area.

* Backend: maps provided by [IGN](https://geoservices.ign.fr/), georeferencing by [GDAL](https://gdal.org/)
* Webapp: powered by [Flask](https://github.com/pallets/flask)

## Command Line Usage
```
Usage: ignite.py [options] <upper_left> <lower_right> <zoom>

Options:
  -h --help                Show this screen.
  --processes <p>          Number of processes used for requests [default: 4].
  --out <file>             Output filename [default: out].
  --cache-folder <folder>  Cache directory [default: cache].
  --no-caching             Do not save temporary tiles for caching and fast reloading.
Note:
  Coordinates should be given as latitude,longitude in decimal degrees.
```

## Installation

### Gdal
Install with pip: 
```
sudo apt install gdal-bin libgdal-dev`
pip install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==`gdal-config --version`
```
Or [with conda](https://anaconda.org/conda-forge/gdal)

### Other dependencies

`pip install -r requirements.txt`

## Credits

Thanks to Amine Benssy :bicyclist: for the idea and original implementation.
