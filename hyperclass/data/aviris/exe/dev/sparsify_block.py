import xarray as xa
import numpy as np
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile
from sklearn.cluster import DBSCAN
import os, math, time

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    tile_index = [1,1]
    block_index = [0,0]
    image_name = "ang20170720t004130_corr_v2p9"
    eps = 0.1
    min_samples = 2

    dm = DataManager( image_name )
    tile: Tile = dm.getTile( *tile_index )
    point_data = tile.getBlockPointData( *block_index )

    t0 = time.time()
    clustering: np.ndarray = DBSCAN( eps=eps, min_samples=min_samples, n_jobs=-1 ).fit( point_data['points'] )
    t1 = time.time()
    print( f"Completed dbscan clustering in {t1-t0} sec")
    nnoise =  np.count_nonzero( clustering == -1 )
    print(f"N Clusters: {clustering.max(initial=-1)}, N Isolates: {nnoise}")




