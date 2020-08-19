import xarray as xa
import matplotlib.pyplot as plt
from typing import List, Union, Tuple, Optional
from hyperclass.data.spatial.manager import DataManager, Dict
from hyperclass.umap.manager import umapManager

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    image_name = "ang20170720t004130_corr_v2p9"
    band_range = [ 30, 40 ]
    model_to_rgb = [1,2,0]
    block_index = (0,0)

    fig, ax = plt.subplots( 1, 2 )
    dm = DataManager( image_name )
    tile = dm.getTile( )
    block = tile.getBlock( *block_index )

    embedded_data: Dict[str,xa.DataArray] = umapManager.transform( block )

    block_raster = block.plot( ax=ax[0], band_range = band_range )
    raster_data: xa.DataArray = embedded_data['raster'][model_to_rgb].transpose('y','x','model')
    print( "Plotting back projection")

    raster_data = dm.norm_to_bounds( raster_data, ('x', 'y'), (0, 1), 0.3 )

    dm.plotRaster( raster_data, ax=ax[1] )

    dm.writeGeotiff( block_raster, f"raster-{tile.name}")
    dm.writeGeotiff(  embedded_data['raster'], f"bp-{tile.name}" )

    plt.show()






