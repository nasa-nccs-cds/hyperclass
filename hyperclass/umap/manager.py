import xarray as xa
import umap, time, pickle
import numpy as np
from typing import List, Union, Tuple, Optional, Dict
from hyperclass.plot.points import datashade_points, point_cloud_3d
from hyperclass.data.aviris.manager import DataManager, Tile
import os, math
cfg_str = lambda x:  "-".join( [ str(i) for i in x ] )

class UMAPManager:

    def __init__(self, tile: Tile, subsampling: int, **kwargs ):
        self.tile = tile
        self.subsampling = subsampling
        self.conf: Dict = dict( n_components=3 )
        self.conf.update( kwargs )
        self.mapper_file_path = self._mapperFilePath()
        self._getMapper()

    def _getMapper(self):
        self.mapper = self._loadMapper()
        if self.mapper is None:
            self.mapper = umap.UMAP(**self.conf)
            self._fit()

    def _mapperFilePath( self ) -> str:
        ts = cfg_str( self.tile.dm.tile_shape  )
        ti = cfg_str( self.tile.tile_coords )
        map_conf_str = ".".join( f"{key}-{self.conf[key]}" for key in self.conf_keys )
        file_name = f"umap.{self.tile.dm.image_name}.{ts}-{ti}.s-{self.subsampling}.{map_conf_str}.pkl"
        return os.path.join( self.tile.dm.config['output_dir'], file_name )

    def _loadMapper(self) -> Optional[umap.UMAP]:
        mapper: umap.UMAP = None
        if os.path.isfile( self.mapper_file_path ):
            t0 = time.time()
            mapper = pickle.load( open( self.mapper_file_path, "rb" ) )
            t1 = time.time()
            print( f"Completed map load in {(t1-t0)} sec.")
        return mapper

    def _fit( self ):
        t0 = time.time()
        training_data: xa.DataArray = self.tile.getTilePointData( self.subsampling )
        t1 = time.time()
        print(f"Completed data prep in {(t1 - t0)} sec, Now fitting umap to {self.conf['n_components']} dims with {training_data.shape[0]} samples")
        self.mapper.fit( training_data.data )
        t2 = time.time()
        print(f"Completed umap fitting in {(t2 - t1)} sec, serializing mapper to file {self.mapper_file_path}")
        pickle.dump( self.mapper, open(self.mapper_file_path, 'wb') )

    @property
    def conf_keys(self) -> List[str]:
        key_list = list(self.conf.keys())
        key_list.sort()
        return key_list

    def view_model( self, **kwargs ):
        color_band = kwargs.pop( 'color_band', None )
        model_data = self.mapper.embedding_
        plot_parms = dict( cmap="jet", **kwargs )
        if color_band is not None:
            plot_parms['values'] = self.tile.getBandPointData( color_band, self.subsampling )
        if model_data.shape[1] == 2:
            datashade_points( model_data, **plot_parms )
        else:
            point_cloud_3d( model_data, **plot_parms )




