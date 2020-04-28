import xarray as xa
from hyperclass.plot.console import LabelingConsole
from typing import List, Union, Dict, Callable, Tuple, Optional
import time, math, atexit, json
from hyperclass.data.aviris.manager import DataManager, Tile
import os, math

if __name__ == '__main__':

    tile_index = [1,1]
    block_index = [0,0]
    image_name = "ang20170720t004130_corr_v2p9"

    dm = DataManager( image_name )
    tile: Tile = dm.getTile( *tile_index )

    animator = LabelingConsole( tile )
    animator.show()
