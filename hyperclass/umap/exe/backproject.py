import xarray as xa
import matplotlib.pyplot as plt
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Dict
from hyperclass.umap.manager import UMAPManager

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    tile_index = [1,1]
    block_index = [0, 0]
    subsampling = 5
    n_dims = 3
    n_links = 10
    min_dist = 0.01
    image_name = "ang20170720t004130_corr_v2p9"
    band_range = [ 30, 40 ]
    model_to_rgb = [0,2,1]

    fig, ax = plt.subplots( 1, 2 )
    dm = DataManager( image_name )
    tile = dm.getTile( *tile_index )
    block = tile.getBlock( *block_index )
    umgr =  UMAPManager( tile, subsampling, n_components=n_dims, n_neighbors=n_links, min_dist=min_dist )

    embedded_data: Dict[str,xa.DataArray] = umgr.transform( block )

    block_raster = block.plot( ax=ax[0], band_range = band_range )
    raster_data: xa.DataArray = embedded_data['raster'][model_to_rgb].transpose('y','x','model')
    print( "Plotting back projection")

    raster_data = dm.norm_to_bounds( raster_data, ('x', 'y'), (0, 1), 0.3 )

    dm.plotRaster( raster_data, ax=ax[1] )

    dm.writeGeotiff( block_raster, f"raster-{tile.name}")
    dm.writeGeotiff(  embedded_data['raster'], f"bp-{tile.name}" )

    plt.show()






