# IGNite :world_map::fire:
Generate the geo-referenced IGN map of an area.

## Installation

Required packages:
* gdal
  * with pip: 
         `sudo apt install gdal-bin libgdal-dev`
         ```pip install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==`gdal-config --version` ```
  * [with conda](https://anaconda.org/conda-forge/gdal)
* `pip install docopt tqdm`

## Usage
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
