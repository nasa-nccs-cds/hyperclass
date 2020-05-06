from pynndescent import NNDescent
import xarray as xa
import numpy as np
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
    knn_indices, knn_dists = nnd.neighbor_graph
    t2 = time.time()
    print(f"Completed computing graph in {(t2 - t1)} sec, index shape = {knn_indices.shape}, dist shape = {knn_dists.shape}")

    I = xa.DataArray( knn_indices, dims=['samples', 'neighbors'], coords = dict( samples = graph_nodes.coords['samples'], neighbors=np.arange(knn_indices.shape[1]) ) )
    D = xa.DataArray( knn_dists,   dims=['samples', 'neighbors'], coords = dict( samples = graph_nodes.coords['samples'], neighbors=np.arange(knn_indices.shape[1])))
    test_labels =  xa.full_like( graph_nodes[:,0], float("nan") )
    P = xa.full_like( test_labels, float("nan") )
    for iL in range(3):
        index = iL*100
        test_labels[index] = iL
        P[index] = 0.0

    I0 = I.unstack().astype( np.int64 )
    index = I0.stack( neighbor_indices=[...] )
    PN = P[ index ].unstack()

    print( ". " )




