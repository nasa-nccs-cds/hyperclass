import xarray as xa
import time, pickle
import numpy as np
from hyperclass.umap.model import UMAP
from collections import OrderedDict
from typing import List, Tuple, Optional, Dict
from hyperclass.plot.point_cloud import PointCloud
from pynndescent import NNDescent
from hyperclass.data.aviris.manager import Tile, Block
import os

cfg_str = lambda x:  "-".join( [ str(i) for i in x ] )

class UMAPManager:

    def __init__(self, tile: Tile, class_labels: List[ Tuple[str,List[float]]],  **kwargs ):
        self.tile = tile
        self.refresh = kwargs.pop('refresh', False)
        self.conf = kwargs
        self._mapper: Dict[ str, UMAP ] = {}
        self.point_cloud: PointCloud = PointCloud( **kwargs )
        self.setClassColors( class_labels )

    def mid( self, block: Block, ndim: int = 3 ):
        return "-".join( [ str(i) for i in [ ndim, *block.block_coords ]] )

    def setClassColors(self, class_labels: List[ Tuple[str,List[float]]] ):
        assert class_labels[0][0].lower() == "unlabeled", "First class label must be 'unlabeled'"
        self.class_labels: List[str] = []
        self.class_colors: OrderedDict[str,List[float]] = OrderedDict()
        for elem in class_labels:
            self.class_labels.append( elem[0] )
            self.class_colors[ elem[0] ] = elem[1]
        self.point_cloud.set_colormap( self.class_colors )

    def embedding( self, block: Block, ndim: int = 3 ) -> xa.DataArray:
        mapper: UMAP = self.getMapper( block, ndim )
        if mapper.embedding_ is None: self.embed( block, ndim = ndim )
        return self.wrap_embedding( block, mapper )

    def wrap_embedding(self, block: Block, mapper: UMAP )-> xa.DataArray:
        ax_samples = block.data.stack(samples=['x', 'y']).coords['samples']
        ax_model = np.arange( mapper.embedding_.shape[1] )
        return xa.DataArray( mapper.embedding_, dims=['samples','model'], coords=dict( samples=ax_samples, model=ax_model ) )

    def getMapper(self, block: Block, ndim: int, **kwargs ) -> UMAP:
        refresh = kwargs.pop( 'refresh', False )
        mid = self.mid( block, ndim )
        mapper = self._mapper.get( mid )
        if ( mapper is None ) or refresh:
            defaults = self.tile.dm.config.section("umap").toDict()
            parms = dict( **defaults, **kwargs, n_components=ndim )
            mapper = UMAP(**parms)
            self._mapper[mid] = mapper
        return mapper

    def iparm(self, key: str ):
        return int( self.tile.dm.config[key] )

    def color_pointcloud( self, labels: xa.DataArray, **kwargs ):
        self.point_cloud.set_point_colors( labels.values, **kwargs )

    def getBlock( self, **kwargs ) -> Optional[Block]:
        block: Optional[Block] = kwargs.get('block', None)
        if block is None:
            block_index = kwargs.get('block_index', None)
            if block_index is not None:
                block = self.tile.getBlock( *block_index )
        return block

    def embed(self, block: Block, labels: xa.DataArray = None, **kwargs) -> xa.DataArray:
        progress_callback = kwargs.get('progress_callback')
        ndim = kwargs.get( "ndim", 3 )
        t0 = time.time()
        refresh = kwargs.get('refresh',True)
        mapper = self.getMapper( block, ndim, refresh=refresh )
        point_data: xa.DataArray = block.getPointData( **kwargs )
        t1 = time.time()
        print(f"Completed data prep in {(t1 - t0)} sec, Now fitting umap[{ndim}] with {point_data.shape[0]} samples")
        labels_data = None if labels is None else labels.values
        mapper.embed(point_data.data, block.flow.nnd, labels_data, **kwargs)
        if ndim == 3:
            self.point_cloud.setPoints( mapper.embedding_, labels_data )
        t2 = time.time()
        print(f"Completed umap fitting in {(t2 - t1)} sec, embedding shape = {mapper.embedding_.shape}")
        return self.wrap_embedding( block, mapper )

    @property
    def conf_keys(self) -> List[str]:
        key_list = list(self.conf.keys())
        key_list.sort()
        return key_list

    def init_pointcloud(self, labels: np.ndarray, **kwargs):
        if labels is not None:
            labels = np.where( labels == -1, 0, labels )
            self.point_cloud.set_point_colors( labels )

    def plot_markers(self, block: Block, ycoords: List[float], xcoords: List[float], colors: List[List[float]], **kwargs ):
        point_data = block.getSelectedPointData( ycoords, xcoords )
        mapper = self.getMapper( block, 3 )
        transformed_data: np.ndarray = mapper.transform(point_data)
        self.point_cloud.plotMarkers( transformed_data.tolist(), colors )

    def update(self):
        self.point_cloud.update()

    def transform( self, block: Block, **kwargs ) -> Dict[str,xa.DataArray]:
        t0 = time.time()
        ndim = kwargs.get( 'ndim', 3 )
        mapper = self.getMapper( block, ndim )
        point_data: xa.DataArray = block.getPointData()
        transformed_data: np.ndarray = mapper.transform(point_data)
        t1 = time.time()
        print(f"Completed transform in {(t1 - t0)} sec for {point_data.shape[0]} samples")
        block_model = xa.DataArray( transformed_data, dims=['samples', 'model'], name=self.tile.data.name, attrs=self.tile.data.attrs,
                                    coords=dict( samples=point_data.coords['samples'], model=np.arange(0,transformed_data.shape[1]) ) )

        transposed_raster = block.data.stack(samples=block.data.dims[1:]).transpose()
        new_raster = block_model.reindex(samples=transposed_raster.samples).unstack()
        new_raster.attrs['long_name'] = [ f"d-{i}" for i in range( new_raster.shape[0] ) ]
        return   dict( raster=new_raster, points=block_model )