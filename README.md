# IGNite :world_map::fire:
Get georeferenced maps of any area.

These maps can be stored on device, and used with mobile apps such as [Avenza Maps](https://store.avenza.com/pages/app-features) (supports GPX).

* French maps by [IGN](https://geoservices.ign.fr/)
* global maps by [CyclOSM](https://www.cyclosm.org)
* georeferencing by [GDAL](https://gdal.org/)

## [Open in colab ![Open in colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eleurent/IGNite/blob/master/IGNite.ipynb)

## Command Line Usage
```
Usage: ignite.py [options] <upper_left> <lower_right> <zoom>

Options:
  -h --help                Show this screen.
  --processes <p>          Number of processes used for requests [default: 4].
  --out <file>             Output filename [default: out].
  --cache-folder <folder>  Cache directory [default: cache].
  --no-caching             Do not save temporary tiles for caching and fast reloading.
  --backend <backend>      Which backend to use, between ign and cyclosm [default: cyclosm].
Note:
  Coordinates should be given as latitude,longitude in decimal degrees.
"""
```

## Installation

### Gdal
Install [with conda](https://anaconda.org/conda-forge/gdal) or with pip: 
```
sudo apt install gdal-bin libgdal-dev
pip install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==`gdal-config --version`
```

### Other dependencies

`pip install -r requirements.txt`

## Credits

Thanks to Amine Benssy :bicyclist: for the idea and original implementation.  
Thanks to Daniel Beilharz :runner: for coming up with this neat name.
