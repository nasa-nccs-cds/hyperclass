from hyperclass.graph.flow import ActivationFlow
import numpy as np
import xarray as xa
import numpy.ma as ma
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, time


def getLabels( point_data: xa.DataArray  ):
    labels = xa.full_like( point_data[:,0], float('nan') )
    labels[5] = 1
    return labels

image_name = "ang20170720t004130_corr_v2p9"
n_neighbors = 3
nIter = 1
use_tile = True
t0 = time.time()

aflow = ActivationFlow(n_neighbors=n_neighbors)

if use_tile:
    subsample = 20000
    block_index = (0, 0)
    dm = DataManager( image_name )
    tile: Tile = dm.getTile()
    block = tile.getBlock( *block_index )
    point_data = block.getPointData( subsample = subsample )
    aflow.setNodeData( point_data )
    C = getLabels( point_data )

else:
    I = np.array( [ [0 ,1 ,3], [1 ,0 ,2], [2 ,1 ,3], [3 ,0 ,2], ])
    D = np.array( [ [0. ,2. ,0.1], [0. ,2., 3.], [0. ,3. ,.2], [0. ,.1, .2], ])
    C = np.array( [ 1, -1, -1, -1 ] )
    aflow.setGraph( I, D )

C = aflow.spread( C, nIter, debug = True  )

aflow.spread( C, nIter, debug = True  )


