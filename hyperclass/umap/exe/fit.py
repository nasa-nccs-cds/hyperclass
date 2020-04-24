import xarray as xa
import umap, time, pickle
import umap.plot
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager
import os, math

# Fit UMAP to hyperspectral data

if __name__ == '__main__':
    c0 = (1000,1000)
    c1 = (2000,2000)
    subsampling = 10
    ndims = 3
    n_neighbors = 30
    file_name = "ang20170720t004130_corr_v2p9"

    dm = DataManager()
    output_file = os.path.join( dm.config['output_dir'], f"umap-model.ang20170720t004130.{c0[0]}-{c1[1]}_{c1[0]}-{c1[1]}.s-{subsampling}.d-{ndims}.nn-{n_neighbors}.pkl" )

    t0 = time.time()
    raster: xa.DataArray = dm.read_subtile( file_name, c0, c1 )
    training_data: xa.DataArray = dm.restructure_for_training( raster, subsampling )

    t1 = time.time()
    print( f"Completed data prep in {(t1-t0)} sec, Now fitting umap to {ndims} dims with {training_data.shape[0]} samples")
    mapper = umap.UMAP( n_components=ndims, n_neighbors=n_neighbors ).fit( training_data )
    t2 = time.time()
    print( f"Completed umap fitting in {(t2-t1)} sec, saving to file {output_file}")
    pickle.dump( mapper, open( output_file, 'wb' ) )

