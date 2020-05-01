import xarray as xa
import umap, time, pickle
import umap.plot
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager
from hyperclass.umap.manager import UMAPManager
import os, math

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    image_name = "ang20170720t004130_corr_v2p9"
    color_band = 35
    refresh = True

    dm = DataManager( image_name )
    tile = dm.getTile()
    umgr = UMAPManager( tile, subsampling, n_components=n_dims, n_neighbors=n_links, min_dist=min_dist, refresh = refresh )
    umgr.view_model( color_band=color_band )





