import xarray as xa
import umap, time, pickle
import umap.plot
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.umap.manager import UMAPManager
import os, math

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    image_name = "ang20170720t004130_corr_v2p9"
    color_band = 35
    block_index = (0,0)
    refresh = True

    dm = DataManager( image_name )
    tile: Tile = dm.getTile()
    block: Block = tile.getBlock( *block_index )
    umgr = UMAPManager( tile, refresh = refresh )
    umgr.fit( block = block )
    umgr.view_model( color_band=color_band )





