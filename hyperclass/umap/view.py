import xarray as xa
import umap, time, pickle
import numpy as np
from typing import List, Union, Tuple, Optional
from hyperclass.plot.points import datashade_points, point_cloud_3d
import os, math

# plot a UMAP embedding

def get_color_data( filepath: str, iband: int, subsampling: int ) -> xa.DataArray:
    print( f"Reading data file {filepath}")
    dset: xa.Dataset =  xa.open_dataset(filepath)
    band_data: xa.DataArray = dset['band_data'][iband]
    nodata_value = band_data.attrs.get('data_ignore_value', -9999 )
    band_data: xa.DataArray = band_data.where(band_data != nodata_value, float('nan'))
    band_data = band_data.stack(samples=band_data.dims).dropna( dim="samples" )
    return band_data[::subsampling]

if __name__ == '__main__':
    from hyperclass.util.config import Configuration
    config = Configuration()
    c0 = (1000,1000)
    c1 = (2000,2000)
    color_band = 200
    subsampling = 5
    ndims = 3

    data_file = os.path.join( config['data_dir'], f"ang20170720t004130.{c0[0]}-{c0[1]}_{c1[0]}-{c1[1]}.nc" )
    mapping_file = os.path.join( config['output_dir'], f"umap-model.ang20170720t004130.{c0[0]}-{c1[1]}_{c1[0]}-{c1[1]}.s-{subsampling}.d-{ndims}.pkl" )
    color_data = get_color_data( data_file, color_band, subsampling )

    t0 = time.time()
    mapper = pickle.load( open( mapping_file, "rb" ) )
    t1 = time.time()
    print( f"Completed map load in {(t1-t0)} sec, Now transforming data")

    if ndims == 2:
        datashade_points( mapper.embedding_, values = color_data.values, vrange = [ 0, 10 ], cmap="jet" )
    else:
        point_cloud_3d( mapper.embedding_, values = color_data.values, cmap="jet", vrange = [ -10, 10 ] )



