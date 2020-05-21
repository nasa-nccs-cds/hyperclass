import xarray as xa
import time, pickle, copy
import numpy as np
from hyperclass.umap.model import UMAP
from collections import OrderedDict
from typing import List, Union, Tuple, Optional, Dict, Callable
from hyperclass.plot.points import datashade_points, point_cloud_3d, point_cloud_vtk
from hyperclass.plot.point_cloud import PointCloud
from pynndescent import NNDescent
from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, math
cfg_str = lambda x:  "-".join( [ str(i) for i in x ] )

class UMAPManager:

    def __init__(self, tile: Tile, class_labels: List[ Tuple[str,List[float]]],  **kwargs ):
        self.tile = tile
        self._block: Optional[Block] = None
        self.refresh = kwargs.pop('refresh', False)
        self.conf = kwargs
        self._embedding: xa.DataArray = None
        self.mapper: UMAP = None
        self.point_cloud: PointCloud = PointCloud( **kwargs )
        self.setClassColors( class_labels )

    def setClassColors(self, class_labels: List[ Tuple[str,List[float]]] ):
        assert class_labels[0][0].lower() == "unlabeled", "First class label must be 'unlabeled'"
        self.class_labels: List[str] = []
        self.class_colors: OrderedDict[str,List[float]] = OrderedDict()
        for elem in class_labels:
            self.class_labels.append( elem[0] )
            self.class_colors[ elem[0] ] = elem[1]
        self.point_cloud.set_colormap( self.class_colors )

    @property
    def embedding(self) -> xa.DataArray:
        return self._embedding

    def _getMapper( self, refresh = False ):
        if (self.mapper is None) or refresh:
            parms = self.tile.dm.config.section("umap").toDict()
            self.mapper = UMAP(**parms)

    def _getMapper1( self, block = None ):
        if self.mapper is None:
            mapper_file_path = self._mapperFilePath( block )
            if self.refresh and os.path.isfile( mapper_file_path):
                print( f"Removing older version of mapper at {mapper_file_path}")
                os.remove( mapper_file_path)
            self.mapper = self._loadMapper( mapper_file_path )
            if self.mapper is None:
                parms = self.tile.dm.config.section("umap").toDict()
                self.mapper = UMAP(**parms)

    def _mapperFilePath( self, block: Block = None ) -> str:
        path_cfg = self.tile.dm.config.toStr( ['tiles','umap'] )
        if block is not None:
            path_cfg = path_cfg + f"_b-{block.block_coords[0]}-{block.block_coords[1]}"
        file_name = f"umap.{self.tile.dm.image_name}.{path_cfg}.pkl"
        return os.path.join( self.tile.dm.config['output_dir'], file_name )

    def _loadMapper( self, mapper_file_path ) -> Optional[UMAP]:
        mapper: UMAP = None
        if os.path.isfile( mapper_file_path ):
            t0 = time.time()
            mapper = pickle.load( open( mapper_file_path, "rb" ) )
            t1 = time.time()
            print( f"Completed loading UMAP in {(t1-t0)} sec from file {mapper_file_path}.")
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

    def embed(self, nnd: NNDescent, labels: xa.DataArray = None, **kwargs):
        progress_callback = kwargs.get('progress_callback')
        t0 = time.time()
        self._block = self.getBlock( **kwargs )
        self._getMapper( True )
        point_data: xa.DataArray = self._block.getPointData( **kwargs ) if self._block else self.tile.getPointData( **kwargs )
        t1 = time.time()
        print(f"Completed data prep in {(t1 - t0)} sec, Now fitting umap to {self.iparm('n_components')} dims with {point_data.shape[0]} samples")
        labels_data = None if labels is None else labels.values
        self.mapper.embed( point_data.data, nnd, labels_data, **kwargs )
        edata = self.mapper.embedding_
        self._embedding = xa.DataArray( edata, dims=['samples','model'], coords=dict( samples=point_data.coords['samples'], model=np.arange(edata.shape[1]) ) )
        self.point_cloud.setPoints( edata, labels_data )
        t2 = time.time()
        print(f"Completed umap fitting in {(t2 - t1)} sec")
        # mapper_path = self._mapperFilePath( block )
        # if not os.path.isfile( mapper_path ):
        #     print(f"Serializing mapper to file {mapper_path}")
        #     pickle.dump( self.mapper, open( mapper_path, 'wb' ) )

    @property
    def conf_keys(self) -> List[str]:
        key_list = list(self.conf.keys())
        key_list.sort()
        return key_list

    def init_pointcloud(self, labels: np.ndarray, **kwargs):
        if labels is not None:
            labels = np.where( labels == -1, 0, labels )
            self.point_cloud.set_point_colors( labels )

    def plot_markers(self, ycoords: List[float], xcoords: List[float], colors: List[List[float]], **kwargs ):
        for ic, color in enumerate( colors ):
            self.plot_marker( ycoords[ic], xcoords[ic], color, **kwargs )

        # point_data = self._block.getSelectedPointData( ycoords, xcoords )
        # transformed_data: np.ndarray = self.mapper.transform(point_data)
        # self.point_cloud.plotMarkers( transformed_data, colors )


    def plot_marker(self, ycoord: float, xcoord: float, color: List[float], **kwargs ):
        point_data = self._block.getSelectedPoint( ycoord, xcoord )
        transformed_data: np.ndarray = self.mapper.transform(point_data)
        self.point_cloud.plotMarker( transformed_data[0].tolist(), color, **kwargs )

    def update(self):
        self.point_cloud.update()

    def view_model( self, **kwargs ):
        color_band = kwargs.pop( 'color_band', None )
        reduction_axes =  kwargs.pop( 'reduction_axes', 0 )
        self._getMapper()
        model_data = self.mapper.embedding_
        plot_parms = dict( cmap="jet", **kwargs )
        if color_band is not None:
            plot_parms['values'] = self.tile.getBandPointData( color_band  )
        if model_data.shape[1] == 2:
            datashade_points( model_data, **plot_parms )
        elif model_data.shape[1] == 3:
            point_cloud_vtk( model_data, **plot_parms )
        else:
            xmodel_data = xa.DataArray( model_data, dims=["samples","band"], coords=dict(samples=range(model_data.shape[0]),band=range(model_data.shape[1])))
            point_cloud_vtk( xmodel_data.drop_sel(band=reduction_axes).values, **plot_parms )

    def transform( self, block: Block, **kwargs ) -> Dict[str,xa.DataArray]:
        t0 = time.time()
        plot = kwargs.get( 'plot', False )
        self._getMapper()
        point_data: xa.DataArray = block.getPointData()
        transformed_data: np.ndarray = self.mapper.transform( point_data )
        t1 = time.time()
        print(f"Completed transform in {(t1 - t0)} sec for {point_data.shape[0]} samples")
        block_model = xa.DataArray( transformed_data, dims=['samples', 'model'], name=self.tile.data.name, attrs=self.tile.data.attrs,
                                    coords=dict( samples=point_data.coords['samples'], model=np.arange(0,transformed_data.shape[1]) ) )
        if plot:
            color_band = kwargs.pop( 'color_band', 200 )
            color_data = point_data[:,color_band]
            self.view_transform( block_model, values=color_data, **kwargs )

        transposed_raster = block.data.stack(samples=block.data.dims[1:]).transpose()
        new_raster = block_model.reindex(samples=transposed_raster.samples).unstack()
        new_raster.attrs['long_name'] = [ f"d-{i}" for i in range( new_raster.shape[0] ) ]
        return   dict( raster=new_raster, points=block_model )

    def view_transform( self, model_data: xa.DataArray,  **kwargs ):
        plot_parms = dict( cmap="jet", **kwargs )
        if model_data.shape[1] == 2:
            datashade_points( model_data, **plot_parms )
        else:
            point_cloud_vtk( model_data, **plot_parms )