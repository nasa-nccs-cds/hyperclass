import xarray as xa
from hyperclass.plot.console import LabelingConsole
from typing import List, Union, Dict, Callable, Tuple, Optional
import time, math, atexit, json, matplotlib
import matplotlib.pyplot as plt
from hyperclass.data.aviris.manager import DataManager, Tile
import os, math

if __name__ == '__main__':
    print( f"Using backend {matplotlib.get_backend()}")
    block_index = (0,0)
    refresh = False
    image_name = "ang20170720t004130_corr_v2p9"
    classes = [ ( 'Unlabeled',          [ 1.0, 1.0, 1.0 ] ),
                ( 'Obscured',           [ 0.6, 0.6, 0.4 ] ),
                ( 'Forest',             [ 0.0, 1.0, 0.0 ] ),
                ( 'Non-forested Land',  [ 0.7, 1.0, 0.0 ] ),
                ( 'Urban',              [ 1.0, 0.0, 1.0 ] ),
                ( 'Water',              [ 0.0, 0.0, 1.0 ] ) ]


    dm = DataManager( image_name )
    tile: Tile = dm.getTile(  )

    animator = LabelingConsole( tile, classes, block = block_index, refresh=refresh )
    animator.show()

