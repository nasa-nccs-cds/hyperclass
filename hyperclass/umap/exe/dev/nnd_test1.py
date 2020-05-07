from pynndescent import NNDescent
import xarray as xa
import numpy as np
import numpy.ma as ma
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.umap.manager import UMAPManager
from hyperclass.plot.points import datashade_points, point_cloud_3d
import plotly.graph_objs as go
import os, time

# Fit compute NN graph over block

if __name__ == '__main__':
    image_name = "ang20170720t004130_corr_v2p9"
    n_neighbors = 10
    subsample = 100

    t0 = time.time()
    dm = DataManager( image_name )
    tile: Tile = dm.getTile()
    umgr = UMAPManager (tile )
    block: Block = tile.getBlock( 0,0 )
    graph_nodes = block.getPointData( subsample = subsample )
    t1 = time.time()
    print(f"Completed loading data in {(t1 - t0)} sec from tile {tile.name}")

    n_trees = 5 + int(round((graph_nodes.shape[0]) ** 0.5 / 20.0))
    n_iters = max(5, int(round(np.log2(graph_nodes.shape[0]))))
    nnd = NNDescent( graph_nodes, n_trees=n_trees, n_iters=n_iters, n_jobs = -1, n_neighbors=n_neighbors, max_candidates=60, verbose=True )
    I: np.ndarray = nnd.neighbor_graph[0]
    D: ma.MaskedArray = ma.MaskedArray( nnd.neighbor_graph[1] )
    t2 = time.time()
    print(f"Completed computing graph in {(t2 - t1)} sec, index shape = {I.shape}, dist shape = {D.shape}")

    C = ma.masked_equal( np.full( graph_nodes.shape[:1], -1 ), -1 )
    P: ma.MaskedArray  = ma.masked_invalid( np.full( graph_nodes.shape[:1], float("nan") ) )
#    node_index = np.arange(I.shape[0])

    for iL in range(3):
        index = iL*100
        C[index] = iL
        P[index] = 0.0

    max_flt = np.finfo(P.dtype).max

    t3 = time.time()
    PN0: ma.MaskedArray  = P[ I.flatten() ]
    PN: ma.MaskedArray = PN0.reshape( I.shape ) + D
    CN = C[ I.flatten() ].reshape( I.shape )
    best_neighbors: ma.MaskedArray = PN.argmin( axis=1, fill_value=max_flt )
    index0 =  np.arange(best_neighbors.size)
    neighbor_index = I[ index0, best_neighbors ]
    P = PN[ index0, neighbor_index ]
    C = CN[ index0, neighbor_index ]
    t4 = time.time()
    print(f"Completed graph flow iteration in {(t4 - t3)} sec")


    print( ". " )




