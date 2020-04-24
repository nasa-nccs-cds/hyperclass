import xarray as xa
import umap, time, pickle
import numpy as np
from typing import List, Union, Tuple, Optional
from hyperclass.plot.points import datashade_points, point_cloud_3d
from hyperclass.data.aviris.manager import DataManager
import os, math


class UMAPManager:

    def __init__(self, **kwargs ):
        self.dm = DataManager( **kwargs )

    def view_model( self, model_data: np.ndarray, color_data: np.ndarray, vrange, **kwargs ):
        if model_data.shape[1] == 2:
            datashade_points( model_data, values=color_data, vrange=vrange, cmap="jet" )
        else:
            point_cloud_3d( model_data, values=color_data, vrange=vrange, cmap="jet" )



