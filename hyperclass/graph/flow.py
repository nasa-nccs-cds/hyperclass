from pynndescent import NNDescent
import numpy as np
import numpy.ma as ma
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, time

class ActivationFlow:

    def __init__(self,  **kwargs ):
        self.nodes: np.ndarray = None
        self.nnd: NNDescent = None
        self.I: np.ndarray = None
        self.D: ma.MaskedArray = None
        self.n_neighbors: int = kwargs.get( 'n_neighbors', 10 )

    def setGraph( self, I: np.ndarray, D: np.ndarray ):
        self.I = I
        self.D = ma.MaskedArray( D )

    def setNodeData(self, nodes_data: np.ndarray, **kwargs ):
        self.nodes = nodes_data
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
        label_count = C.count()
        print(f"Beginning graph flow iterations, #C = {label_count}")
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
            new_label_count = C.count()
            if new_label_count == label_count:
                print( "Converged!" )
            else:
                label_count = new_label_count
                print(f"\n -->> Iter{iter + 1}: #C = {label_count}\n")
                if debug:
                    print(f"PN = {PN}")
                    print(f"CN = {CN}")
                    print(f"best_neighbors = {best_neighbors}")
                    print( f"P = {P}" )
                    print( f"C = {C}" )

        t1 = time.time()
        print(f"Completed graph flow {nIter} iterations in {(t1 - t0)} sec")
        return C.reshape( class_labels.shape )

