import xarray as xa
import matplotlib.pyplot as plt
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Dict
from hyperclass.umap.manager import UMAPManager

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    tile_index = [1,1]
    subsampling = 5
    ndims = 3
    image_name = "ang20170720t004130_corr_v2p9"
    color_band = 200

    fig, ax = plt.subplots( 1, 2 )
    dm = DataManager( image_name )
    tile = dm.getTile( *tile_index )

    raster = dm.readGeotiff( f"raster-{tile.name}" )
    bp = dm.readGeotiff( f"bp-{tile.name}"  )

    dm.plotRaster( raster[color_band], ax=ax[0] )

    bp_raster = bp.transpose('y','x','band').isel( band=[1,2,0])
    dm.plotRaster( bp_raster, rescale=[0,1], ax=ax[1] )

    plt.show()


