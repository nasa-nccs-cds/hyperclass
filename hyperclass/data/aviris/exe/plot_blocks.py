import xarray as xa
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile
import os, math

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    tile_index = [1,1]
    block_index = [0,0]
    image_name = "ang20170720t004130_corr_v2p9"

    dm = DataManager( image_name )
    tile: Tile = dm.getTile( *tile_index )
    tile.plotBlock( *block_index, band_range = [13,27] )



