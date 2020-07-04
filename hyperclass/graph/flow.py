from pynndescent import NNDescent
import numpy as np
import numpy.ma as ma
import xarray as xa
from typing import List, Union, Tuple, Optional
from hyperclass.gui.events import EventClient
from hyperclass.data.aviris.manager import dataManager
from hyperclass.gui.tasks import taskRunner, Task
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import os, time, threading

class ActivationFlowManager:

    def __init__( self ):
        self.instances = {}

    def __getitem__( self, dsid ):
        return self.instances.get( dsid )

    def getActivationFlow( self, point_data: xa.DataArray, **kwargs ) -> "ActivationFlow":
        dsid = point_data.attrs['dsid']
        return self.instances.setdefault( dsid, self.create_flow( point_data, **kwargs ) )

    def create_flow(self, point_data: xa.DataArray, **kwargs):
        return ActivationFlow( point_data, **kwargs )

class ActivationFlow(QObject,EventClient):

    def __init__(self, nodes_data: xa.DataArray,  **kwargs ):
        QObject.__init__(self)
        self.nodes: xa.DataArray = None
        self.nnd: NNDescent = None
        self.I: np.ndarray = None
        self.D: np.ndarray = None
        self.P: np.ndarray = None
        self.C: np.ndarray = None
        self.reset = True
        self.condition = threading.Condition()
        background = kwargs.get( 'background', False )
        if background:
            self.init_task = Task( f"Compute NN graph", self.setNodeData, nodes_data, **kwargs )
            taskRunner.start( self.init_task )
        else:
            self.setNodeData( nodes_data, **kwargs )

    def clear(self):
        self.reset = True

    def setGraph( self, I: np.ndarray, D: np.ndarray ):
        self.I = I
        self.D = ma.MaskedArray( D )

    def setNodeData(self, nodes_data: xa.DataArray, **kwargs ):
        if nodes_data.size > 0:
            self.condition.acquire( )
            try:
                t0 = time.time()
                self.nodes = nodes_data
                self.nnd = self.getNNGraph( nodes_data, **kwargs )
                self.I = self.nnd.neighbor_graph[0]
                self.D = self.nnd.neighbor_graph[1]
                dt = (time.time()-t0)
                print( f"Computed NN Graph in {dt} sec ({dt/60} min)")
                self.condition.notifyAll()
            finally:
                self.condition.release()
        else:
            print( "No data available for this block")

    @classmethod
    def getNNGraph(cls, nodes: xa.DataArray, **kwargs ):
        n_neighbors = dataManager.config.value("umap/nneighbors", type=int)
        n_trees = kwargs.get('ntree', 5 + int(round((nodes.shape[0]) ** 0.5 / 20.0)))
        n_iters = kwargs.get('niter', max(5, 2 * int(round(np.log2(nodes.shape[0])))))
        nnd = NNDescent(nodes.values, n_trees=n_trees, n_iters=n_iters, n_neighbors=n_neighbors, max_candidates=60, verbose=True)
#        nnd._init_search_graph()
        return nnd


    def spread( self, sample_labels: xa.DataArray, nIter: int, **kwargs ) -> Optional[xa.DataArray]:
        from hyperclass.gui.labels import labelsManager
        if self.D is None:
            Task.taskNotAvailable( "Awaiting task completion", "The NN graph computation has not yet finished", **kwargs)
            return None
        sample_data = sample_labels.values
        debug = kwargs.get( 'debug', False )
        sample_mask = sample_data == 0
        if self.C is None or self.reset:
            self.C = sample_data
        else:
            self.C = np.where( sample_mask, self.C, sample_data )
        label_count = np.count_nonzero(self.C)
        if label_count == 0:
            Task.taskNotAvailable("Workflow violation", "Must label some points before this algorithm can be applied", **kwargs )
            return None
        if (self.P is None) or self.reset:   self.P = np.full( self.C.shape, float('inf') )
        self.P = np.where( sample_mask, self.P, 0.0 )
        print(f"Beginning graph flow iterations, #C = {label_count}")

        t0 = time.time()
        converged = False
        for iter in range(nIter):
            for iN in range( self.I.shape[1] ):
                FC = labelsManager.getFilteredLabels( self.C )
                for label_spec in FC:
                    pid = label_spec[0]
                    pid1 = self.I[pid,iN]
                    PN = self.P[pid] + self.D[pid,iN]
                    if ( self.C[pid1] == 0 ) or (PN < self.P[pid1]):
                        marker = "***" if ( self.C[pid1] == 0 ) else ""
                        print( f"P[{iter},{iN}]: {pid} -> {pid1}  {marker}")
                        self.C[pid1] = label_spec[1]
                        self.P[pid1] = PN
            new_label_count = np.count_nonzero(self.C)
            if new_label_count == label_count:
                print( "Converged!" )
                converged = True
                break
            else:
                label_count = new_label_count
                print(f"\n -->> Iter{iter + 1}: #C = {label_count}\n")

        t1 = time.time()
        result_attrs = dict( converged=converged, **sample_labels.attrs )
        result_attrs[ '_FillValue']=-2
        result: xa.DataArray =  xa.DataArray( self.C, dims=sample_labels.dims, coords=sample_labels.coords, attrs=result_attrs )
        print(f"Completed graph flow {nIter} iterations in {(t1 - t0)} sec, Class Range = [ {result.min().values} -> {result.max().values} ], #marked = {np.count_nonzero(result.values)}")
        self.reset = False
        return result

    def spread1( self, sample_labels: xa.DataArray, nIter: int, **kwargs ) -> Optional[xa.DataArray]:
        if self.D is None:
            Task.taskNotAvailable( "Awaiting task completion", "The NN graph computation has not yet finished", **kwargs)
            return None
        debug = kwargs.get( 'debug', False )
        sample_mask = sample_labels == -1
        if self.C is None or self.reset:
            self.C = np.ma.masked_equal( sample_labels, -1 )
        else:
            self.C = np.ma.where( sample_mask, self.C, sample_labels )

        label_count = self.C.count()
        if label_count == 0:
            Task.taskNotAvailable("Workflow violation", "Must label some points before this algorithm can be applied", **kwargs )
            return None
        if (self.P is None) or self.reset:   self.P = ma.masked_array(  np.full( self.C.shape, 0.0 ), mask = self.C.mask )
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
                print(f"\n -->> Iter{iter + 1}: #C = {label_count}\n")
                if debug: print(f"PN = {PN}"); print(f"CN = {CN}"); print(f"best_neighbors = {best_neighbors}"); print( f"P = {self.P}" ); print( f"C = {self.C}" )

        t1 = time.time()
        result_attrs = dict( converged=converged, **sample_labels.attrs )
        result_attrs[ '_FillValue']=-2
        result: xa.DataArray =  xa.DataArray( self.C.filled(0), dims=sample_labels.dims, coords=sample_labels.coords, attrs=result_attrs )
        print(f"Completed graph flow {nIter} iterations in {(t1 - t0)} sec, Class Range = [ {result.min().values} -> {result.max().values} ], #marked = {np.count_nonzero(result.values)}")
        self.reset = False
        return result

activationFlowManager = ActivationFlowManager()


