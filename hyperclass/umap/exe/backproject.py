import xarray as xa
import umap, time, pickle
import numpy as np
from typing import List, Union, Tuple, Optional
from hyperclass.umap.manager import UMAPManager
import os, math

# overlay regions of a UMAP embedding in geographic space

def get_band_data( filepath: str, iband: int ) -> xa.DataArray:
    print( f"Reading data file {filepath}")
    dset: xa.Dataset =  xa.open_dataset(filepath)
    band_data: xa.DataArray = dset['band_data'][iband]
    return band_data

def get_index_data( band_data: np.ndarray, subsampling: int ) -> np.ndarray:
    indices: np.ndarray = np.extract( np.isfinite( band_data.flatten() ), np.arange(0, band_data.size) )
    return indices[::subsampling]

if __name__ == '__main__':
    from hyperclass.util.config import Configuration
    config = Configuration()
    c0 = (1000,1000)
    c1 = (2000,2000)
    color_band = 200
    subsampling = 5
    ndims = 3
    file_name = "ang20170720t004130_corr_v2p9"

    mgr = UMAPManager()
    map_file = os.path.join( mgr.dm.config['output_dir'], f"umap-model.ang20170720t004130.{c0[0]}-{c1[1]}_{c1[0]}-{c1[1]}.s-{subsampling}.d-{ndims}.pkl" )
    band_data: xa.DataArray = mgr.dm.read_subtile( file_name, c0, c1, color_band )
    index_array = get_index_data( band_data.values,  subsampling )

    t0 = time.time()
    mapper = pickle.load( open( map_file, "rb" ) )
    points = np.concatenate( ( index_array.reshape(index_array.size, 1), mapper.embedding_ ),  axis = 1 ).
    t1 = time.time()
    print( f"Completed map load in {(t1-t0)} sec, Now transforming data")




