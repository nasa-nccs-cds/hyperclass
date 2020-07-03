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
        n_neighbors = kwargs.pop('n_neighbors', dataManager.iparm('umap/nneighbors'))
        print(f"Computing NN graph using {n_neighbors} neighbors")
        return ActivationFlow( point_data, n_neighbors=n_neighbors, **kwargs )

class ActivationFlow(QObject,EventClient):

    def __init__(self, nodes_data: xa.DataArray,  **kwargs ):
        QObject.__init__(self)
        self.nodes: xa.DataArray = None
        self.nnd: NNDescent = None
        self.I: np.ndarray = None
        self.D: ma.MaskedArray = None
        self.P: ma.MaskedArray = None
        self.C: ma.MaskedArray = None
        self.reset = True
        self.condition = threading.Condition()
        self.n_neighbors: int = kwargs.get( 'n_neighbors', 10 )
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
                n_neighbors: int = kwargs.pop('n_neighbors', self.n_neighbors )
                self.nnd = self.getNNGraph( nodes_data, n_neighbors=n_neighbors, **kwargs )
                self.I = self.nnd.neighbor_graph[0]
                self.D = ma.MaskedArray(self.nnd.neighbor_graph[1])
                dt = (time.time()-t0)
                print( f"Computed NN[{self.n_neighbors}] Graph in {dt} sec ({dt/60} min)")
                self.condition.notifyAll()
            finally:
                self.condition.release()
        else:
            print( "No data available for this block")

    @classmethod
    def getNNGraph(cls, nodes: xa.DataArray, **kwargs ):
        n_neighbors: int = kwargs.get('n_neighbors', 10)
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
        debug = kwargs.get( 'debug', False )
        sample_mask = sample_labels == 0
        if self.C is None or self.reset:
            self.C = np.ma.masked_equal( sample_labels, -1 )
        else:
            self.C = np.ma.where( sample_mask, self.C, sample_labels )

        filtered_labels = labelsManager.getFilteredLabels( sample_labels.values )
        test_label = filtered_labels[0]
        ic0 = test_label[0]
        n_I = self.I[ ic0 ]
        n_D = self.D[ ic0 ]

        label_count = np.count_nonzero(self.C.filled(0))
        if label_count == 0:
            Task.taskNotAvailable("Workflow violation", "Must label some points before this algorithm can be applied", **kwargs )
            return None
        if (self.P is None) or self.reset:   self.P = np.full( self.C.shape, float('inf') )
        self.P = np.ma.where( sample_mask, self.P, 0.0 )
        index0 = np.arange( self.I.shape[0] )
        print(f"Beginning graph flow iterations, #C = {label_count}")
        if debug: print(f"I = {self.I}" ); print(f"D = {self.D}" ); print(f"P = {self.P}" ); print(f"C = {self.C}" )
        t0 = time.time()
        converged = False
        NN = self.I.shape[1]
        PN: np.ndarray = np.full( self.I.shape, float('inf'), self.P.dtype )
        CN: np.ndarray = np.full( self.I.shape, 0, np.int )
        for iter in range(nIter):
            assigned_CN_count0 = np.count_nonzero(CN)
            assigned_PN_count0 = np.count_nonzero( PN < 1.0e100 )
            assigned_P_count0 = np.count_nonzero( self.P < 1.0e100)
            assigned_C_count0 = np.count_nonzero( self.C )
            for iN in range(NN):
                IN = self.I[:,iN]
                PN[ IN, iN ] = self.P + self.D[:,iN]
                CN[ IN, iN ] = self.C
                tCN = CN[ IN[ic0] ]
                tC = self.C[ ic0 ]
                assigned_CN_count1 = np.count_nonzero(CN)
                assigned_PN_count1 = np.count_nonzero(PN < 1.0e100)
                print( '.')
            assigned_CN_count1 = np.count_nonzero(CN)
            assigned_PN_count1 = np.count_nonzero(PN < 1.0e100)
            best_neighbors: ma.MaskedArray = PN.argmin(axis=1)
            self.P = PN[index0, best_neighbors]
            self.C = np.ma.array( CN[index0, best_neighbors], mask = self.C.mask )
            assigned_P_count1 = np.count_nonzero(self.P < 1.0e100)
            assigned_C_count1 = np.count_nonzero(self.C)

            PN0 = PN[test_label[0]]
            CN0 = CN[test_label[0]]
            PNN = { iN: PN[iN] for iN in n_I }
            CNN = { iN: CN[iN] for iN in n_I }
            filtered_C = labelsManager.getFilteredLabels( self.C )
            filtered_P = labelsManager.getFilteredLabels(self.P)
            filtered_best_neighbors = labelsManager.getFilteredLabels(best_neighbors)

            new_label_count = np.count_nonzero(self.C.filled(0))
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


