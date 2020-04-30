import xarray as xa
from typing import List, Union, Tuple, Optional
import matplotlib.pyplot as plt
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
    sdata: xa.DataArray = ( block.data  )

    spec: xa.DataArray = sdata.std( dim=['x','y'], skipna=True )
    mspec: xa.DataArray = sdata.max( dim=['x','y'], skipna=True )
    nspec: xa.DataArray = sdata.min( dim=['x','y'], skipna=True )

    fig, ax = plt.subplots( 1, 1 )
    spec.plot( ax=ax )
    mspec.plot( ax=ax )
    nspec.plot( ax=ax )

    plt.yscale("log")

    plt.show()



