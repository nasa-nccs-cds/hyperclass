import xarray as xa
import matplotlib.pyplot as plt
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Dict
from hyperclass.umap.manager import UMAPManager

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    tile_index = [1,1]
    subsampling = 5
    ndims = 4
    image_name = "ang20170720t004130_corr_v2p9"
    band_range = [ 30, 40 ]

    fig, ax = plt.subplots( 1, 2 )
    dm = DataManager( image_name )
    tile = dm.getTile( *tile_index )
    umgr = UMAPManager( tile, subsampling, n_components=ndims )

    embedded_data: Dict[str,xa.DataArray] = umgr.transform_block( 0, 0 )

    block_raster = tile.plotBlock( 0, 0, ax=ax[0], band_range = band_range )
    dm.plotRaster( embedded_data['raster'].transpose('y','x','model'), rescale=[0,1], ax=ax[1] )

    dm.writeGeotiff( block_raster, f"raster-{tile.name}")
    dm.writeGeotiff(  embedded_data['raster'], f"bp-{tile.name}" )

    plt.show()






