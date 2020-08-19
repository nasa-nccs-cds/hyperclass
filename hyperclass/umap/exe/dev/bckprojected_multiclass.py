import xarray as xa
import matplotlib.pyplot as plt
from typing import List, Union, Tuple, Optional
from hyperclass.data.spatial.manager import DataManager, Dict

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    tile_index = [1,1]
    subsampling = 5
    ndims = 3
    ccolors = [ (0, f"x>6.5", [.5,1,.5]), (1, f"x>6.5", [0,0,1]), (2, f"y>8", [1,0,0]), (3, f"y<5", [1,1,0]) ]
    image_name = "ang20170720t004130_corr_v2p9"

    fig, ax = plt.subplots( 1, 1 )
    dm = DataManager( image_name )
    tile = dm.getTile( *tile_index )

    raster = dm.readGeotiff( f"raster-{tile.name}" )
    bp = dm.readGeotiff( f"bp-{tile.name}"  )

    mask1 =  bp[ 0 ] > 6.5
    mask2 =  bp[ 1 ] > 8
    mask3 =  bp[ 1 ] < 5

    mask = mask1 + mask2*2 + mask3*3

    dm.plotRaster( mask, colors=ccolors, ax=ax, title=f"UMAP-3D back projected classification"   )

    plt.show()


