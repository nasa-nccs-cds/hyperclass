import xarray as xa
import umap, time, pickle
import umap.plot
from typing import List, Union, Tuple, Optional
import os, math

# Fit UMAP to hyperspectral data

def read( filepath: str, c0: Tuple, c1: Tuple ) -> xa.DataArray:
    print( f"Reading data file {filepath}")
    dset: xa.Dataset =  xa.open_dataset(filepath)
    full_input_bands: xa.DataArray = dset['band_data']
    nodata_value = full_input_bands.attrs.get('data_ignore_value', -9999 )
    input_bands: xa.DataArray = full_input_bands.where(full_input_bands != nodata_value, float('nan'))
    return input_bands

def normalize( bands: xa.DataArray ):
    meanval = bands.mean( dim=bands.dims[1:], skipna=True )
    std = bands.std( dim=bands.dims[1:], skipna=True )
    return ( bands - meanval ) / std

def restructure_for_training( band_data: xa.DataArray ) -> xa.DataArray:
    normalized = normalize( band_data )
    training_data = normalized.stack( samples=normalized.dims[1:] ).transpose().dropna( dim='samples', how='any' )
    print( f"training_data: shape = {training_data.shape}, dims = {training_data.dims}, {training_data.shape[0]} valid samples out of {normalized.shape[1]*normalized.shape[2]} pixels" )
    return training_data

if __name__ == '__main__':
    from hyperclass.util.config import Configuration
    config = Configuration()
    c0 = (1000,1000)
    c1 = (2000,2000)
    subsampling = 5
    ndims = 3

    input_file = os.path.join( config['data_dir'], f"ang20170720t004130.{c0[0]}-{c0[1]}_{c1[0]}-{c1[1]}.nc" )
    output_file = os.path.join( config['output_dir'], f"umap-model.ang20170720t004130.{c0[0]}-{c1[1]}_{c1[0]}-{c1[1]}.s-{subsampling}.d-{ndims}.pkl" )

    t0 = time.time()
    bands: xa.DataArray = read( input_file, c0, c1 )
    training_data: xa.DataArray = restructure_for_training( bands )
    subsample = training_data[::subsampling]
    t1 = time.time()
    print( f"Completed data prep in {(t1-t0)} sec, Now fitting umap to {ndims} dims with {subsample.shape[0]} samples")
    mapper = umap.s( n_components=ndims ).fit( subsample )
    t2 = time.time()
    print( f"Completed umap fitting in {(t2-t1)} sec, saving to file {output_file}")
    pickle.dump( mapper, open( output_file, 'wb' ) )

