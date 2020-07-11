import xarray as xa
import matplotlib.pyplot as plt
from typing import List, Union, Tuple, Optional
from hyperclass.data.spatial.manager import DataManager, Dict
from hyperclass.umap.manager import UMAPManager

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    tile_index = [1,1]
    subsampling = 5
    threshold = 6.5
    axis = 'x'
    ndims = 3
    ccolors = [ (0, f"{axis}<{threshold}", [.5,1,.5]), (1, f"{axis}>{threshold}", [0,0,1]) ]
    image_name = "ang20170720t004130_corr_v2p9"
    iax = dict( x=0, y=1, z=2 )
    gbands = [ 29, 38 ]

    fig, ax = plt.subplots( 1, 2 )
    dm = DataManager( image_name )
    tile = dm.getTile( *tile_index )

    raster = dm.readGeotiff( f"raster-{tile.name}" )
    bp = dm.readGeotiff( f"bp-{tile.name}"  )
    mask =  bp[ iax[axis] ] > threshold
    dm.plotRaster( mask, colors=ccolors, ax=ax[1], title=f"UMAP-3D back projected classification: Threshold = {threshold}, axis = {axis}"   )

    bp = dm.readGeotiff( f"bp-{tile.name}"  )
    tile.plotBlock( 0, 0, band_range= gbands, ax=ax[0], title="Aviris green bands"  )

    plt.show()


