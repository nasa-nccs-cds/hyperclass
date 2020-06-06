import xarray as xa
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.tile import Tile, Block
import matplotlib.pyplot as plt
import os, math

# Plot raster for block

if __name__ == '__main__':

    image_name = "ang20170720t004130_corr_v2p9"

    dm = DataManager( image_name )
    tile: Tile = dm.getTile( )
    block_indices = [ [0,0], [0,1], [1,0], [1,1] ]
    band_range = [13, 27]

    fig, axs = plt.subplots( 2, 2 )

    for bi in block_indices:
        tile.getBlock(*bi).plot( ax=axs[bi[0],bi[1]], band_range=band_range )

    plt.show()




