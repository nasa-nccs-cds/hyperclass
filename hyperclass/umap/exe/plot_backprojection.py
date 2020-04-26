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
    rbands = [ 50, 70 ]
    gbands = [ 29, 38 ]
    bbands = [ 12, 25 ]

    fig, ax = plt.subplots( 2, 2 )
    dm = DataManager( image_name )
    tile = dm.getTile( *tile_index )

    raster = dm.readGeotiff( f"raster-{tile.name}" )
    bp = dm.readGeotiff( f"bp-{tile.name}"  )

    tile.plotBlock( 0, 0, band_range= rbands, ax=ax[0,0], title="Aviris red bands" )
    tile.plotBlock( 0, 0, band_range= gbands, ax=ax[0,1], title="Aviris green bands"  )
    tile.plotBlock( 0, 0, band_range= bbands, ax=ax[1,0], title="Aviris blue bands"  )

    bp_raster = bp.transpose('y','x','band').isel( band=[1,2,0])
    dm.plotRaster( bp_raster, rescale=[0,1], ax=ax[1,1], title="UMAP-3D back projection"   )

    plt.show()


