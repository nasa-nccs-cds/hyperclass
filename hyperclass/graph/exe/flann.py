from pyflann import *
import xarray as xa
import numpy as np
from hyperclass.data.aviris.tile import Tile, Block
import os, math, sys

block_shape = (500, 500)
block_indices = (0,0)
image_name = "ang20170720t004130_corr_v2p9"


dm = DataManager( image_name, block_shape=block_shape )
tile: Tile = dm.getTile()
block = tile.getBlock( *block_indices )
data: np.ndarray = block.getPointData().values

flann = FLANN()
result, dists = flann.nn(data)