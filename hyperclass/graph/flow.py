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

class ActivationFlow:

    def __init__(self, tile: Tile, **kwargs ):
        self.tile: Tile = tile
        self.block: Block = None
        self.nodes: np.ndarray = None
        self.nnd: NNDescent = None
        self.I: np.ndarray = None
        self.D: ma.MaskedArray = None
        self.n_neighbors: int = kwargs.get( 'n_neighbors', 10 )

    def setBlock(self, iy, ix,  ):
        self.block: Block = tile.getBlock( iy, ix )
        self.nodes = self.block.getPointData().values
        n_trees = 5 + int(round((self.nodes.shape[0]) ** 0.5 / 20.0))
        n_iters = max(5, int(round(np.log2(self.nodes.shape[0]))))
        self.nnd = NNDescent( self.nodes, n_trees=n_trees, n_iters=n_iters, n_jobs = -1, n_neighbors=self.n_neighbors, max_candidates=60, verbose=True )
        self.I = self.nnd.neighbor_graph[0]
        self.D = ma.MaskedArray( self.nnd.neighbor_graph[1] )

    def spread( self, class_labels: np.ndarray, nIter: int, **kwargs ) -> np.ndarray:
        C = ma.masked_less( class_labels.flatten(), 0 )
        P = ma.masked_array(  np.full( C.shape, 0.0 ), mask = C.mask )
        index0 = np.arange( self.I.shape[0] )
        max_flt = np.finfo( P.dtype ).max
        print(f"Beginning graph flow iterations, #C = {C.count()}")
        t0 = time.time()
        for iter in range(nIter):
            PN: ma.MaskedArray = P[ self.I.flatten() ].reshape(self.I.shape) +self. D
            CN = C[ self.I.flatten() ].reshape( self.I.shape )
            best_neighbors: ma.MaskedArray = PN.argmin(axis=1, fill_value=max_flt)
            P = PN[index0, best_neighbors]
            C = CN[index0, best_neighbors]
            print(f" -->> Iter{iter + 1}: #C = {C.count()}")

        t1 = time.time()
        print(f"Completed graph flow {nIter} iterations in {(t1 - t0)} sec")
        return C.reshape( class_labels.shape )


if __name__ == '__main__':
    image_name = "ang20170720t004130_corr_v2p9"
    n_neighbors = 3
    subsample = 1
    block_index = ( 0,0 )
    nIter = 3

    t0 = time.time()
    dm = DataManager( image_name )
    tile: Tile = dm.getTile()

    aflow = ActivationFlow( tile, n_neighbors = n_neighbors )
    aflow.setBlock( *block_index )

    C = ma.masked_equal(np.full(aflow.nodes.shape[:1], -1), -1)
    C[500] = 1

    aflow.spread( C, nIter )

    print(".")

    # C = ma.masked_equal( np.full( graph_nodes.shape[:1], -1 ), -1 )
    # P: ma.MaskedArray  = ma.masked_invalid( np.full( graph_nodes.shape[:1], float("nan") ) )
    # index0 = np.arange(I.shape[0])
    # max_flt = np.finfo(P.dtype).max
    #
    # for iL in range(10):
    #     index = iL*100
    #     C[index] = iL
    #     P[index] = 0.0
    #
    # C = aflow.spread( )
    #
    # block: Block = tile.getBlock( 0,0 )
    # graph_nodes = block.getPointData( subsample = subsample )
    # t1 = time.time()
    # print(f"Completed loading data in {(t1 - t0)} sec from tile {tile.name}")
    #
    # n_trees = 5 + int(round((graph_nodes.shape[0]) ** 0.5 / 20.0))
    # n_iters = max(5, int(round(np.log2(graph_nodes.shape[0]))))
    # nnd = NNDescent( graph_nodes, n_trees=n_trees, n_iters=n_iters, n_jobs = -1, n_neighbors=n_neighbors, max_candidates=60, verbose=True )
    # I: np.ndarray = nnd.neighbor_graph[0]
    # D: ma.MaskedArray = ma.MaskedArray( nnd.neighbor_graph[1] )
    # t2 = time.time()
    # print(f"Completed computing graph in {(t2 - t1)} sec, index shape = {I.shape}, dist shape = {D.shape}")
    #
    # C = ma.masked_equal( np.full( graph_nodes.shape[:1], -1 ), -1 )
    # P: ma.MaskedArray  = ma.masked_invalid( np.full( graph_nodes.shape[:1], float("nan") ) )
    # index0 = np.arange(I.shape[0])
    # max_flt = np.finfo(P.dtype).max
    #
    # for iL in range(10):
    #     index = iL*100
    #     C[index] = iL
    #     P[index] = 0.0
    #
    # print(f"Beginning graph flow iterations, #C = {C.count()}")
    # t3 = time.time()
    # for iter in range( nIter ):
    #     PN: ma.MaskedArray =  P[ I.flatten() ].reshape( I.shape ) + D
    #     CN = C[ I.flatten() ].reshape( I.shape )
    #     best_neighbors: ma.MaskedArray = PN.argmin( axis=1, fill_value=max_flt )
    #     P = PN[ index0, best_neighbors ]
    #     C = CN[ index0, best_neighbors ]
    #     print(f" -->> Iter{iter+1}: #C = {C.count()}")
    #
    # t4 = time.time()
    # print(f"Completed graph flow {nIter} iterations in {(t4 - t3)} sec")
    #
    #
    #
    #
    #
