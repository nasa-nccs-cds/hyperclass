import xarray as xa
import umap, time, pickle
import umap.plot
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Block, Tile
from hyperclass.umap.manager import UMAPManager
import os, math

# Fit UMAP-transform a block of data and view the embedding

if __name__ == '__main__':

    tile_index = [1,1]
    block_index = [0, 0]
    subsampling = 5
    ndims = 3
    image_name = "ang20170720t004130_corr_v2p9"
    color_band = 200

    dm = DataManager( image_name )
    tile: Tile = dm.getTile( *tile_index )
    umgr = UMAPManager( tile, subsampling, n_components=ndims )
    block: Block = tile.getBlock(*block_index)
    umgr.transform( block, plot = True, color_band=color_band )



