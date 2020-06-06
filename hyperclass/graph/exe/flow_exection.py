from hyperclass.graph.flow import ActivationFlow
import numpy as np
import numpy.ma as ma
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.tile import Tile, Block
import os, time
# import pptk

image_name = "ang20170720t004130_corr_v2p9"
n_neighbors = 10
nIter = 10
subsample = 1
block_index = (0, 0)
t0 = time.time()

aflow = ActivationFlow(n_neighbors=n_neighbors)

dm = DataManager( image_name )
tile: Tile = dm.getTile()
aflow.setBlock( tile, *block_index, subsample = subsample )

C = ma.masked_equal(np.full(aflow.nodes.shape[:1], -1), -1)
C[100] = 1

aflow.spread( C, nIter  )


