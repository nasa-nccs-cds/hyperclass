import xarray as xa
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, math

# Plot raster for block

if __name__ == '__main__':

    tile_index = [1,1]
    block_index = [0,0]
    image_name = "ang20170720t004130_corr_v2p9"

    dm = DataManager( image_name )
    tile: Tile = dm.getTile( *tile_index )
    block: Block = tile.getBlock( *block_index )
    block.plot( band_range = [13,27] )



