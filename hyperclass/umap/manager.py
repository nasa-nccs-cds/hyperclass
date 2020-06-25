import xarray as xa
import time, pickle
import numpy as np

from hyperclass.data.events import dataEventHandler
from hyperclass.graph.flow import activationFlowManager
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.gui.points import VTKFrame
from hyperclass.umap.model import UMAP
from collections import OrderedDict
from typing import List, Tuple, Optional, Dict
from hyperclass.plot.point_cloud import PointCloud
from hyperclass.data.aviris.manager import dataManager
from hyperclass.data.aviris.tile import Tile, Block
from hyperclass.gui.tasks import taskRunner, Task

cfg_str = lambda x:  "-".join( [ str(i) for i in x ] )

class UMAPManager(EventClient):

    def __init__(self, class_labels: List[ Tuple[str,List[float]]],  **kwargs ):
        self.point_cloud: PointCloud = PointCloud( **kwargs )
        self._gui: VTKFrame = None
        self.embedding_type = kwargs.pop('embedding_type', 'umap')
        self.conf = kwargs
        self.learned_mapping: Optional[UMAP] = None
        self._mapper: Dict[ str, UMAP ] = {}
        self.setClassColors( [ ('Unlabeled', [1.0, 1.0, 1.0, 0.5]) ] + class_labels )

    def gui( self ):
        if self._gui is None:
            self._gui = VTKFrame( self.point_cloud )
            self.activate_event_listening()
        return self._gui

    def processEvent( self, event: Dict ):
        print( f" **** UMAPManager.processEvent: {event}")
        if dataEventHandler.isDataLoadEvent(event):
            point_data = dataEventHandler.getPointData( event, scaled = True )
            self.embedding( point_data )
        if (event.get('event') == 'gui') and (event.get('type') == 'keyPress'):
            self._gui.keyPress( )

    def setClassColors(self, class_labels: List[ Tuple[str,List[float]]] ):
        self.class_labels: List[str] = []
        self.class_colors: OrderedDict[str,List[float]] = OrderedDict()
        for elem in class_labels:
            self.class_labels.append( elem[0] )
            color = elem[1] if (len( elem[1] ) == 4) else elem[1] + [1.0]
            self.class_colors[ elem[0] ] = color
        self.point_cloud.set_colormap( self.class_colors )


    def embedding( self, point_data: xa.DataArray, ndim: int = 3 ) -> Optional[xa.DataArray]:
        mid = f"{ndim}-{point_data.attrs['dsid']}"
        mapper: UMAP = self.getMapper( mid, ndim )
        if mapper.embedding_ is not None:
            return self.wrap_embedding( point_data.coords[ point_data.dims[0] ], mapper.embedding_ )
        return self.embed( point_data, ndim = ndim )

    def wrap_embedding(self, ax_samples: xa.DataArray, embedding: np.ndarray, **kwargs )-> xa.DataArray:
        ax_model = np.arange( embedding.shape[1] )
        return xa.DataArray( embedding, dims=['samples','model'], coords=dict( samples=ax_samples, model=ax_model ) )

    def getMapper(self, mid: str, ndim: int ) -> UMAP:
        mapper = self._mapper.get( mid )
        if ( mapper is None ):
            n_neighbors = dataManager.config.value("umap/nneighbors", type=int)
            n_epochs = dataManager.config.value("umap/nepochs", type=int)
            parms = dict( n_neighbors=n_neighbors, n_epochs=n_epochs ); parms.update( **self.conf, n_components=ndim )
            mapper = UMAP(**parms)
            self._mapper[mid] = mapper
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
        self.learned_mapping = self.getMapper( self.mid( block, ndim ), ndim )
        point_data: xa.DataArray = block.getPointData( **kwargs )
        labels_mask = ( labels > 0 )
        filtered_labels: xa.DataArray = labels.where( labels_mask, drop = True )
        filtered_point_data: xa.DataArray = point_data.where( labels_mask, drop=True )
        nnd = ActivationFlow.getNNGraph( filtered_point_data, **kwargs )
        self.learned_mapping.embed(filtered_point_data.data, nnd, filtered_labels.values, **kwargs)
        coords = dict( samples=filtered_point_data.samples, model=np.arange(self.learned_mapping.embedding_.shape[1]) )
        return xa.DataArray( self.learned_mapping.embedding_, dims=['samples','model'], coords=coords ), filtered_labels

    def apply(self, block: Block, **kwargs ) -> Optional[xa.DataArray]:
        if (self.learned_mapping is None) or (self.learned_mapping.embedding_ is None):
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
        t1 = time.time()
        print(f"Completed data prep in {(t1 - t0)} sec, Now fitting umap[{ndim}] with {point_data.shape[0]} samples")
        labels_data = None if labels is None else labels.values
        if mapper.embedding_ is not None:
            mapper.init = mapper.embedding_
        etype = self.embedding_type.lower()
        if etype == "umap":
            mapper.embed(point_data.data, flow.nnd, labels_data, **kwargs)
        elif etype == "spectral":
            mapper.spectral_embed(point_data.data, flow.nnd, labels_data, **kwargs)
        else: raise Exception( f" Unknown embedding type: {etype}")
        if ndim == 3:
            self.point_cloud.setPoints( mapper.embedding_, labels_data )
        t2 = time.time()
        print(f"Completed umap fitting in {(t2 - t1)/60.0} min, embedding shape = {mapper.embedding_.shape}")
        return self.wrap_embedding( point_data.coords['samples'], mapper.embedding_ )

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
        mapper = self.getMapper( self.mid( block, 3 ), 3 )
        if mapper.embedding_ is not None:
            transformed_data: np.ndarray = mapper.embedding_[ pindices ]
            self.point_cloud.plotMarkers( transformed_data.tolist(), colors, **kwargs )

    def reset_markers(self):
        self.point_cloud.initMarkers( )

    def update(self):
        self._gui.update()

    def transform( self, block: Block, **kwargs ) -> Dict[str,xa.DataArray]:
        t0 = time.time()
        ndim = kwargs.get( 'ndim', 3 )
        mapper = self.getMapper( self.mid( block, ndim ), ndim )
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