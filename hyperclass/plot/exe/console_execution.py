import xarray as xa
from hyperclass.plot.console import LabelingConsole
from typing import List, Union, Dict, Callable, Tuple, Optional
import time, math, atexit, json
import matplotlib.pyplot as plt
from hyperclass.data.aviris.manager import DataManager, Tile
import os, math

if __name__ == '__main__':

    block_index = (0,0)
    image_name = "ang20170720t004130_corr_v2p9"
    classes = [ 'Obscured', 'Forest',  'Non-forested Land', 'Urban', 'Water' ]


    dm = DataManager( image_name )
    tile: Tile = dm.getTile(  )

    animator = LabelingConsole( tile, classes, block = block_index )
    animator.show()

    keyboardClick = False
    while keyboardClick != True:
        keyboardClick = plt.waitforbuttonpress()
