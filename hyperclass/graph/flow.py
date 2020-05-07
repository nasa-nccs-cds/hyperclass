from pynndescent import NNDescent
import numpy as np
import numpy.ma as ma
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, time

class ActivationFlow:

    def __init__(self,  **kwargs ):
        self.tile: Tile = None
        self.block: Block = None
        self.nodes: np.ndarray = None
        self.nnd: NNDescent = None
        self.I: np.ndarray = None
        self.D: ma.MaskedArray = None
        self.n_neighbors: int = kwargs.get( 'n_neighbors', 10 )

    def setGraph( self, I: np.ndarray, D: np.ndarray ):
        self.I = I
        self.D = ma.MaskedArray( D )

    def setBlock(self, tile: Tile, iy, ix, **kwargs ):
        self.tile: Tile = tile
        self.block: Block = tile.getBlock( iy, ix )
        self.nodes = self.block.getPointData( **kwargs ).values
        n_trees = 5 + int(round((self.nodes.shape[0]) ** 0.5 / 20.0))
        n_iters = max(5, int(round(np.log2(self.nodes.shape[0]))))
        self.nnd = NNDescent( self.nodes, n_trees=n_trees, n_iters=n_iters, n_jobs = -1, n_neighbors=self.n_neighbors, max_candidates=60, verbose=True )
        self.I = self.nnd.neighbor_graph[0]
        self.D = ma.MaskedArray( self.nnd.neighbor_graph[1] )

    def spread( self, class_labels: np.ndarray, nIter: int, **kwargs ) -> np.ndarray:
        debug = kwargs.get( 'debug', False )
        C = ma.masked_less( class_labels.flatten(), 0 )
        P = ma.masked_array(  np.full( C.shape, 0.0 ), mask = C.mask )
        index0 = np.arange( self.I.shape[0] )
        max_flt = np.finfo( P.dtype ).max
        print(f"Beginning graph flow iterations, #C = {C.count()}")
        if debug:
            print(f"I = {self.I}" )
            print(f"D = {self.D}" )
            print(f"P = {P}" )
            print(f"C = {C}" )
        t0 = time.time()
        for iter in range(nIter):
            PN: ma.MaskedArray = P[ self.I.flatten() ].reshape(self.I.shape) + self.D
            CN = C[ self.I.flatten() ].reshape( self.I.shape )
            best_neighbors: ma.MaskedArray = PN.argmin(axis=1, fill_value=max_flt)
            P = PN[index0, best_neighbors]
            C = CN[index0, best_neighbors]
            print(f"\n -->> Iter{iter + 1}: #C = {C.count()}\n")
            if debug:
                print(f"PN = {PN}")
                print(f"CN = {CN}")
                print(f"best_neighbors = {best_neighbors}")
                print( f"P = {P}" )
                print( f"C = {C}" )

        t1 = time.time()
        print(f"Completed graph flow {nIter} iterations in {(t1 - t0)} sec")
        return C.reshape( class_labels.shape )

