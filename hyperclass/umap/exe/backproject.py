import xarray as xa
import umap, time, pickle
import umap.plot
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager
from hyperclass.umap.manager import UMAPManager
import os, math

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':
    tile_shape = (1000,1000)
    block_shape = ( 250, 250 )
    tile_index = [1,1]
    subsampling = 5
    ndims = 3
    image_name = "ang20170720t004130_corr_v2p9"
    color_band = 200

    dm = DataManager( image_name )
    tile = dm.getTile( *tile_index )
    umgr = UMAPManager( tile, subsampling, n_components=ndims )
    embedded_data: xa.Dataset = umgr.transform_block( 0, 0 )
    dm.plotRaster( embedded_data['raster'] )






