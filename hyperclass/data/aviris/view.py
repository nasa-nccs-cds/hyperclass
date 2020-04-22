import xarray as xa
import matplotlib.pyplot as plt
import umap
from typing import List, Union, Tuple, Optional
import os, math

# View a Aviris subtile

def read( filepath: str, iband: int ) -> xa.DataArray:
    print( f"Reading data file {filepath}")
    dset: xa.Dataset =  xa.open_dataset(filepath)
    full_input_bands: xa.DataArray = dset['band_data']
    nodata_value = full_input_bands.attrs.get('data_ignore_value', -9999 )
    input_bands: xa.DataArray = full_input_bands.where(full_input_bands != nodata_value, float('nan'))
    return input_bands[iband]

if __name__ == '__main__':
    c0 = (1000,1000)
    c1 = (2000,2000)
    iband = 200

    data_dir = "/Users/tpmaxwel/Dropbox/Tom/Data/Aviris/processed"
    input_file = os.path.join( data_dir, f"ang20170720t004130.{c0[0]}-{c0[1]}_{c1[0]}-{c1[1]}.nc" )

    band_data: xa.DataArray = read( input_file, iband )

    print( f"{band_data.min()} {band_data.max()}")

    band_data.plot.imshow( cmap="jet", vmin=-10, vmax = 10 )
    plt.show()
