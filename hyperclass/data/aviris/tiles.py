import xarray as xa
from typing import List, Union, Tuple, Optional
import os, math

# Create subtiles for test and development purposes

def read( filepath: str, c0: Tuple, c1: Tuple ) -> xa.DataArray:
    print( f"Reading data file {filepath}")
    full_input_bands: xa.DataArray = xa.open_rasterio(filepath)
    nodata_value = full_input_bands.attrs.get('data_ignore_value', -9999 )
    raw_input_bands = full_input_bands[:, c0[1]:c1[1], c0[0]:c1[0] ]
    input_bands: xa.DataArray = raw_input_bands.where(raw_input_bands != nodata_value, float('nan'))
    input_bands.name = "band_data"
    return input_bands


if __name__ == '__main__':
    c0 = (1000,1000)
    c1 = (2000,2000)
    data_dir = "/Users/tpmaxwel/Dropbox/Tom/Data/Aviris/processed"
    input_file =  os.path.join( data_dir, "ang20170720t004130_corr_v2p9.tif" )
    output_file = os.path.join( data_dir, f"ang20170720t004130.{c0[0]}-{c0[1]}_{c1[0]}-{c1[1]}.nc" )

    bands: xa.DataArray = read( input_file, c0, c1 )
    print( f"Writing output file {output_file}" )
    bands.to_netcdf( output_file )

