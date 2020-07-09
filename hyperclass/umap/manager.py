import xarray as xa
import time, pickle
import numpy as np
from hyperclass.gui.labels import labelsManager, Marker
from hyperclass.data.events import dataEventHandler
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from hyperclass.graph.flow import activationFlowManager
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.data.events import dataEventHandler, DataType
from hyperclass.gui.points import VTKFrame
from hyperclass.umap.model import UMAP
from collections import OrderedDict
from typing import List, Tuple, Optional, Dict
from hyperclass.plot.point_cloud import PointCloud
from hyperclass.data.aviris.manager import dataManager
from hyperclass.data.aviris.tile import Tile, Block
from hyperclass.gui.tasks import taskRunner, Task

cfg_str = lambda x:  "-".join( [ str(i) for i in x ] )

class UMAPManager(QObject,EventClient):
    update_signal = pyqtSignal()

    def __init__(self,  **kwargs ):
        QObject.__init__(self)
        self.point_cloud: PointCloud = PointCloud( **kwargs )
        self._gui: VTKFrame = None
        self.embedding_type = kwargs.pop('embedding_type', 'umap')
        self.conf = kwargs
        self.learned_mapping: Optional[UMAP] = None
        self._mapper: Dict[ str, UMAP ] = {}
        self._current_mapper: UMAP = None
        self.setClassColors()
        self.update_signal.connect( self.update )

    def gui( self ):
        if self._gui is None:
            self._gui = VTKFrame( self.point_cloud )
            self.activate_event_listening()
        return self._gui

    def plotMarkers(self):
        self.point_cloud.plotMarkers()
        self.update_signal.emit()

    def processEvent( self, event: Dict ):
        print(f"UMAPManager.processEvent: {event}")
        if dataEventHandler.isDataLoadEvent(event):
            point_data = dataEventHandler.getPointData( event, DataType.Embedding )
            self.embedding( point_data )
        elif event.get('event') == 'labels':
            if event.get('type') == 'clear':       self.plotMarkers()
            elif event.get('type') == 'undo':      self.plotMarkers()
            elif event.get('type') == 'spread':
                labels: xa.Dataset = event.get('labels')
                self.point_cloud.set_point_colors( labels['C'] )
                self.update_signal.emit()
        elif event.get('event') == 'gui':
            if event.get('type') == 'keyPress':      self._gui.setKeyState( event )
            elif event.get('type') == 'keyRelease':  self._gui.releaseKeyState( event )
        elif event.get('event') == 'pick':
            etype = event.get('type')
            if etype in [ 'directory', "vtkpoint" ]:
                if self._current_mapper is not None:
                    try:
                        pid = event.get('pid')
                        cid = event.get('cid', labelsManager.selectedClass )
                        color = labelsManager.selectedColor if etype == "vtkpoint" else labelsManager.colors[cid]
                        embedding = self._current_mapper.embedding
                        transformed_data: np.ndarray = embedding[ [pid] ]
                        labelsManager.addMarker( Marker( transformed_data.tolist(), color, pid, cid ) )
                        self.point_cloud.plotMarkers()
                        self.update_signal.emit()
                    except Exception as err:
                        print( f"Point selection error: {err}")

    def setClassColors(self ):
        self.class_labels: List[str] = labelsManager.labels
        self.class_colors: OrderedDict[str,List[float]] = labelsManager.toDict( 1.0 )
        self.point_cloud.set_colormap( self.class_colors )

    def embedding( self, point_data: xa.DataArray, ndim: int = 3 ) -> Optional[xa.DataArray]:
        mapper: UMAP = self.getMapper( point_data.attrs['dsid'], ndim )
        if mapper.embedding is not None:
            return self.wrap_embedding(point_data.coords[ point_data.dims[0] ], mapper.embedding )
        return self.embed( point_data, ndim = ndim )

    def wrap_embedding(self, ax_samples: xa.DataArray, embedding: np.ndarray, **kwargs )-> xa.DataArray:
        ax_model = np.arange( embedding.shape[1] )
        return xa.DataArray( embedding, dims=['samples','model'], coords=dict( samples=ax_samples, model=ax_model ) )

    def getMapper(self, dsid: str, ndim: int ) -> UMAP:
        mid = f"{ndim}-{dsid}"
        mapper = self._mapper.get( mid )
        if ( mapper is None ):
            n_neighbors = dataManager.config.value("umap/nneighbors", type=int)
            n_epochs = dataManager.config.value("umap/nepochs", type=int)
            parms = dict( n_neighbors=n_neighbors, n_epochs=n_epochs ); parms.update( **self.conf, n_components=ndim )
            mapper = UMAP(**parms)
            self._mapper[mid] = mapper
        self._current_mapper = mapper
        return mapper

    def iparm(self, key: str ):
        return int( dataManager.config.value(key) )

    def color_pointcloud( self, labels: xa.DataArray, **kwargs ):
        self.point_cloud.set_point_colors( labels.values, **kwargs )

    def clear_pointcloud(self):
        self.point_cloud.clear()

    def update_point_sizes(self, increase: bool  ):
        self.point_cloud.update_point_sizes( increase )

    def learn(self, block: Block, labels: xa.DataArray, ndim: int, **kwargs ) -> Tuple[Optional[xa.DataArray],Optional[xa.DataArray]]:
        from hyperclass.graph.flow import ActivationFlow
        if block.flow.nnd is None:
            event = dict( event="message", type="warning", title='Workflow Message', caption="Awaiting task completion", msg="The NN graph computation has not yet finished" )
            self.submitEvent( event, EventMode.Gui )
            return None, None
        self.learned_mapping = self.getMapper( block.dsid, ndim )
        point_data: xa.DataArray = block.getPointData( **kwargs )
        labels_mask = ( labels > 0 )
        filtered_labels: xa.DataArray = labels.where( labels_mask, drop = True )
        filtered_point_data: xa.DataArray = point_data.where( labels_mask, drop=True )
        nnd = ActivationFlow.getNNGraph( filtered_point_data, **kwargs )
        self.learned_mapping.embed(filtered_point_data.data, nnd, filtered_labels.values, **kwargs)
        coords = dict(samples=filtered_point_data.samples, model=np.arange(self.learned_mapping_embedding.shape[1]))
        return xa.DataArray(self.learned_mapping.embedding, dims=['samples', 'model'], coords=coords), filtered_labels

    def apply(self, block: Block, **kwargs ) -> Optional[xa.DataArray]:
        if (self.learned_mapping is None) or (self.learned_mapping.embedding is None):
            Task.taskNotAvailable( "Workflow violation", "Must learn a classication before it can be applied", **kwargs )
            return None
        point_data: xa.DataArray = block.getPointData( **kwargs )
        embedding: np.ndarray = self.learned_mapping.transform( point_data )
        return self.wrap_embedding( point_data.coords['samples'], embedding )

    # def computeMixingSpace(self, block: Block, labels: xa.DataArray = None, **kwargs) -> xa.DataArray:
    #     ndim = kwargs.get( "ndim", 3 )
    #     t0 = time.time()
    #     point_data: xa.DataArray = block.getPointData( **kwargs )
    #     t1 = time.time()
    #     print(f"Completed data prep in {(t1 - t0)} sec, Now fitting umap[{ndim}] with {point_data.shape[0]} samples")
    #     self.mixing_space.setPoints( point_data, labels )
    #     t2 = time.time()
    #     print(f"Completed computing  mixing space in {(t2 - t1)/60.0} min")

    def embed( self, point_data: xa.DataArray, labels: xa.DataArray = None, **kwargs ) -> Optional[xa.DataArray]:
        flow = activationFlowManager.getActivationFlow( point_data )
        if flow.nnd is None:
            event = dict( event="message", type="warning", title='Workflow Message', caption="Awaiting task completion", msg="The NN graph computation has not yet finished" )
            self.submitEvent( event, EventMode.Gui )
            return None
        ndim = kwargs.get( "ndim", 3 )
        t0 = time.time()
        mapper = self.getMapper( point_data.attrs['dsid'], ndim )
        mapper.flow = flow
        t1 = time.time()
        labels_data = None if labels is None else labels.values
        if point_data.shape[1] <= ndim:
            mapper.set_embedding( point_data )
        else:
            print(f"Completed data prep in {(t1 - t0)} sec, Now fitting umap[{ndim}] with {point_data.shape[0]} samples")
            if mapper.embedding is not None:
                mapper.init = mapper.embedding
            etype = self.embedding_type.lower()
            if etype == "umap":
                mapper.embed(point_data.data, flow.nnd, labels_data, **kwargs)
            elif etype == "spectral":
                mapper.spectral_embed(point_data.data, flow.nnd, labels_data, **kwargs)
            else: raise Exception( f" Unknown embedding type: {etype}")
        if ndim == 3:
            self.point_cloud.setPoints(mapper.embedding, labels_data)
        t2 = time.time()
        self.update_signal.emit()
        print(f"Completed umap fitting in {(t2 - t1)/60.0} min, embedding shape = { mapper.embedding.shape}" )
        return self.wrap_embedding(point_data.coords['samples'], mapper.embedding )

    @property
    def conf_keys(self) -> List[str]:
        key_list = list(self.conf.keys())
        key_list.sort()
        return key_list

    # def plot_markers_transform(self, block: Block, ycoords: List[float], xcoords: List[float], colors: List[List[float]], **kwargs ):
    #     point_data = block.getSelectedPointData( ycoords, xcoords )
    #     mapper = self.getMapper( block, 3 )
    #     if hasattr(mapper, 'embedding_'):
    #         transformed_data: np.ndarray = mapper.transform(point_data)
    #         self.point_cloud.plotMarkers( transformed_data.tolist(), colors )

    def plot_markers(self, block: Block, ycoords: List[float], xcoords: List[float], colors: List[List[float]], **kwargs ):
        pindices: np.ndarray  = block.multi_coords2pindex( ycoords, xcoords )
        mapper = self.getMapper( block.dsid, 3 )
        if mapper.embedding is not None:
            transformed_data: np.ndarray = mapper.embedding[ pindices]
            self.point_cloud.plotMarkers( transformed_data.tolist(), colors, **kwargs )
            self.update_signal.emit()

    def reset_markers(self):
        self.point_cloud.initMarkers( )

    @pyqtSlot()
    def update(self):
        self._gui.update()

    def transform( self, block: Block, **kwargs ) -> Dict[str,xa.DataArray]:
        t0 = time.time()
        ndim = kwargs.get( 'ndim', 3 )
        mapper = self.getMapper( block.dsid, ndim )
        point_data: xa.DataArray = block.getPointData()
        transformed_data: np.ndarray = mapper.transform(point_data)
        t1 = time.time()
        print(f"Completed transform in {(t1 - t0)} sec for {point_data.shape[0]} samples")
        block_model = xa.DataArray( transformed_data, dims=['samples', 'model'], name=block.tile.data.name, attrs=block.tile.data.attrs,
                                    coords=dict( samples=point_data.coords['samples'], model=np.arange(0,transformed_data.shape[1]) ) )

        transposed_raster = block.data.stack(samples=block.data.dims[-2:]).transpose()
        new_raster = block_model.reindex(samples=transposed_raster.samples).unstack()
        new_raster.attrs['long_name'] = [ f"d-{i}" for i in range( new_raster.shape[0] ) ]
        return   dict( raster=new_raster, points=block_model )