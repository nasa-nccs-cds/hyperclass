from pynndescent import NNDescent
import numpy as np
import numpy.ma as ma
import xarray as xa
from typing import List, Union, Tuple, Optional
from PyQt5.QtWidgets import QMessageBox
from hyperclass.gui.tasks import taskRunner, Task
import os, time

class ActivationFlow:

    def __init__(self, nodes_data: xa.DataArray,  **kwargs ):
        self.nodes: xa.DataArray = None
        self.nnd: NNDescent = None
        self.I: np.ndarray = None
        self.D: ma.MaskedArray = None
        self.P: ma.MaskedArray = None
        self.C: ma.MaskedArray = None
        self.n_neighbors: int = kwargs.get( 'n_neighbors', 10 )
        self.init_task = Task( self.setNodeData, nodes_data, **kwargs )
        taskRunner.start( self.init_task, f"Compute NN graph" )

    def setGraph( self, I: np.ndarray, D: np.ndarray ):
        self.I = I
        self.D = ma.MaskedArray( D )

    def setNodeData(self, nodes_data: xa.DataArray, **kwargs ):
        if nodes_data.size > 0:
            t0 = time.time()
            self.nodes = nodes_data
            n_trees =  kwargs.get( 'ntree', 5 + int(round((self.nodes.shape[0]) ** 0.5 / 20.0)) )
            n_iters = kwargs.get( 'niter', max(5, 2*int(round(np.log2(self.nodes.shape[0])))))
            self.nnd = NNDescent( self.nodes.values, n_trees=n_trees, n_iters=n_iters, n_neighbors=self.n_neighbors, max_candidates=60, verbose=True )
            self.nnd._init_search_graph()  # Allowing this to be executed lazily causes problems with multithreading
            self.I = self.nnd.neighbor_graph[0]
            self.D = ma.MaskedArray( self.nnd.neighbor_graph[1] )
            print( f"Computed NN[{self.n_neighbors}] Graph in {time.time()-t0} sec")
        else:
            print( "No data available for this block")

    def spread( self, sample_labels: xa.DataArray, nIter: int, **kwargs ) -> Optional[xa.DataArray]:
        if self.D is None:
            Task.taskNotAvailable( "Awaiting task completion", "The NN graph computation has not yet finished")
            return None
        debug = kwargs.get( 'debug', False )
        reset = kwargs.get( "reset", False)
        sample_mask = sample_labels == -1
        if self.C is None or reset:  self.C = np.ma.masked_equal( sample_labels, -1 )
        else:                        self.C = np.ma.where( sample_mask, self.C, sample_labels )
        label_count = self.C.count()
        if label_count == 0:
            Task.taskNotAvailable("Workflow violation", "Must label some points before this algorithm can be applied" )
            return None
        if (self.P is None) or reset:   self.P = ma.masked_array(  np.full( self.C.shape, 0.0 ), mask = self.C.mask )
        else:                           self.P = np.ma.where( sample_mask, self.P, 0.0 )
        index0 = np.arange( self.I.shape[0] )
        max_flt = np.finfo( self.P.dtype ).max
        print(f"Beginning graph flow iterations, #C = {label_count}")
        if debug: print(f"I = {self.I}" ); print(f"D = {self.D}" ); print(f"P = {self.P}" ); print(f"C = {self.C}" )
        t0 = time.time()
        converged = False
        for iter in range(nIter):
            PN: ma.MaskedArray = self.P[ self.I.flatten() ].reshape(self.I.shape) + self.D
            CN: ma.MaskedArray = self.C[ self.I.flatten() ].reshape( self.I.shape )
            best_neighbors: ma.MaskedArray = PN.argmin(axis=1, fill_value=max_flt)
            self.P = PN[index0, best_neighbors]
            self.C = CN[index0, best_neighbors]
            new_label_count = self.C.count()
            if new_label_count == label_count:
                print( "Converged!" )
                converged = True
                break
            else:
                label_count = new_label_count
 #               print(f"\n -->> Iter{iter + 1}: #C = {label_count}\n")
                if debug: print(f"PN = {PN}"); print(f"CN = {CN}"); print(f"best_neighbors = {best_neighbors}"); print( f"P = {self.P}" ); print( f"C = {self.C}" )

        t1 = time.time()
        result_attrs = dict( converged=converged, **sample_labels.attrs, _FillValue=-2 )
        result: xa.DataArray =  xa.DataArray( self.C.filled(0), dims=sample_labels.dims, coords=sample_labels.coords, attrs=result_attrs )
        print(f"Completed graph flow {nIter} iterations in {(t1 - t0)} sec, Class Range = [ {result.min().values} -> {result.max().values} ]")
        return result


