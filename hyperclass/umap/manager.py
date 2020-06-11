import xarray as xa
import time, pickle
import numpy as np
from hyperclass.umap.model import UMAP
from collections import OrderedDict
from typing import List, Tuple, Optional, Dict
from hyperclass.plot.point_cloud import PointCloud
from hyperclass.plot.mixing import MixingSpace
from hyperclass.data.aviris.manager import dataManager
from hyperclass.data.aviris.tile import Tile, Block
from hyperclass.gui.tasks import taskRunner, Task

cfg_str = lambda x:  "-".join( [ str(i) for i in x ] )

class UMAPManager:

    def __init__(self, class_labels: List[ Tuple[str,List[float]]],  **kwargs ):
        self.embedding_type = kwargs.pop('embedding_type', 'umap')
        self.conf = kwargs
        self.learned_mapping: Optional[UMAP] = None
        self._mapper: Dict[ str, UMAP ] = {}
        self.point_cloud: PointCloud = PointCloud( **kwargs )
        self.mixing_space: MixingSpace = MixingSpace( **kwargs )
        self.setClassColors( [ ('Unlabeled', [1.0, 1.0, 1.0, 0.5]) ] + class_labels )

    def mid( self, block: Block, ndim: int = 3 ):
        return "-".join( [ str(i) for i in [ ndim, *block.block_coords ]] )

    def setClassColors(self, class_labels: List[ Tuple[str,List[float]]] ):
        self.class_labels: List[str] = []
        self.class_colors: OrderedDict[str,List[float]] = OrderedDict()
        for elem in class_labels:
            self.class_labels.append( elem[0] )
            self.class_colors[ elem[0] ] = elem[1]
        self.point_cloud.set_colormap( self.class_colors )
        self.mixing_space.set_colormap( self.class_colors )

    def embedding( self, block: Block, ndim: int = 3 ) -> xa.DataArray:
        mapper: UMAP = self.getMapper( block, ndim )
        if mapper.embedding_ is not None:
            return self.wrap_embedding( block, mapper.embedding_ )
        return self.embed( block, ndim = ndim )

    def wrap_embedding(self, block: Block, embedding: np.ndarray, **kwargs )-> xa.DataArray:
        ax_samples = block.getPointData(**kwargs).coords['samples']
        ax_model = np.arange( embedding.shape[1] )
        return xa.DataArray( embedding, dims=['samples','model'], coords=dict( samples=ax_samples, model=ax_model ) )

    def getMapper(self, block: Block, ndim: int ) -> UMAP:
        mid = self.mid( block, ndim )
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
        self.mixing_space.set_point_colors( labels.values, **kwargs )

    def clear_pointcloud(self):
        self.point_cloud.clear()
        self.mixing_space.clear()

    def update_point_sizes(self, increase: bool  ):
        self.point_cloud.update_point_sizes( increase )
        self.mixing_space.update_point_sizes( increase )

    def learn(self, block: Block, labels: xa.DataArray, ndim: int, **kwargs ) -> xa.DataArray:
        self.learned_mapping = self.getMapper( block, ndim )
        point_data: xa.DataArray = block.getPointData( **kwargs )
        self.learned_mapping.embed(point_data.data, block.flow.nnd, labels.values, **kwargs)
        return self.wrap_embedding( block, self.learned_mapping.embedding_ )

    def apply(self, block: Block, **kwargs ) -> Optional[xa.DataArray]:
        if (self.learned_mapping is None) or (self.learned_mapping.embedding_ is None):
            Task.taskNotAvailable( "Workflow violation", "Must learn a classication before it can be applied", **kwargs )
            return None
        point_data: xa.DataArray = block.getPointData( **kwargs )
        embedding: np.ndarray = self.learned_mapping.transform( point_data )
        return self.wrap_embedding( block, embedding )

    def computeMixingSpace(self, block: Block, labels: xa.DataArray = None, **kwargs) -> xa.DataArray:
        ndim = kwargs.get( "ndim", 3 )
        t0 = time.time()
        point_data: xa.DataArray = block.getPointData( **kwargs )
        t1 = time.time()
        print(f"Completed data prep in {(t1 - t0)} sec, Now fitting umap[{ndim}] with {point_data.shape[0]} samples")
        self.mixing_space.setPoints( point_data, labels )
        t2 = time.time()
        print(f"Completed computing  mixing space in {(t2 - t1)/60.0} min")

    def embed(self, block: Block, labels: xa.DataArray = None, **kwargs) -> xa.DataArray:
        ndim = kwargs.get( "ndim", 3 )
        t0 = time.time()
        mapper = self.getMapper( block, ndim )
        point_data: xa.DataArray = block.getPointData( **kwargs )

        t1 = time.time()
        print(f"Completed data prep in {(t1 - t0)} sec, Now fitting umap[{ndim}] with {point_data.shape[0]} samples")
        labels_data = None if labels is None else labels.values
        if mapper.embedding_ is not None:
            mapper.init = mapper.embedding_
        etype = self.embedding_type.lower()
        if etype == "umap":
            mapper.embed(point_data.data, block.flow.nnd, labels_data, **kwargs)
        elif etype == "spectral":
            mapper.spectral_embed(point_data.data, block.flow.nnd, labels_data, **kwargs)
        else: raise Exception( f" Unknown embedding type: {etype}")
        if ndim == 3:
            self.point_cloud.setPoints( mapper.embedding_, labels_data )
        t2 = time.time()
        print(f"Completed umap fitting in {(t2 - t1)/60.0} min, embedding shape = {mapper.embedding_.shape}")
        return self.wrap_embedding( block, mapper.embedding_ )

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
        mapper = self.getMapper( block, 3 )
        if mapper.embedding_ is not None:
            transformed_data: np.ndarray = mapper.embedding_[ pindices ]
            self.point_cloud.plotMarkers( transformed_data.tolist(), colors, **kwargs )
            self.mixing_space.plotMarkers( transformed_data.tolist(), colors, **kwargs )

    def reset_markers(self):
        self.point_cloud.initMarkers( )
        self.mixing_space.initMarkers( )

    def update(self):
        self.point_cloud.update()
        self.mixing_space.update()

    def transform( self, block: Block, **kwargs ) -> Dict[str,xa.DataArray]:
        t0 = time.time()
        ndim = kwargs.get( 'ndim', 3 )
        mapper = self.getMapper( block, ndim )
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