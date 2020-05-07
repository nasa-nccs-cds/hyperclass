from hyperclass.graph.flow import ActivationFlow
import numpy as np
import numpy.ma as ma
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, time

image_name = "ang20170720t004130_corr_v2p9"
n_neighbors = 3
nIter = 3
use_tile = True
t0 = time.time()

aflow = ActivationFlow(n_neighbors=n_neighbors)

if use_tile:
    subsample = 20000
    block_index = (0, 0)
    dm = DataManager( image_name )
    tile: Tile = dm.getTile()
    aflow.setBlock( tile, *block_index, subsample = subsample )
    C = ma.masked_equal(np.full(aflow.nodes.shape[:1], -1), -1)
    C[5] = 1

else:
    I = np.array( [ [0 ,1 ,3], [1 ,0 ,2], [2 ,1 ,3], [3 ,0 ,2], ])
    D = np.array( [ [0. ,2. ,0.1], [0. ,2., 3.], [0. ,3. ,.2], [0. ,.1, .2], ])
    C = np.array( [ 1, -1, -1, -1 ] )
    aflow.setGraph( I, D )

aflow.spread( C, nIter, debug = True  )


