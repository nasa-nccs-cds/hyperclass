import numpy as np
import xarray as xa
import pathlib
from typing import List, Union, Tuple, Optional, Dict
from PyQt5.QtCore import QSettings, QCoreApplication
import os, math, pickle
from hyperclass.gui.config import SettingsManager

class DataManager(SettingsManager):

    def __init__( self, **kwargs ):
        SettingsManager.__init__(  self, **kwargs )
        self.default_settings = {"umap/nneighbors": 8, "umap/nepochs": 300, "svm/ndim": 8}

    def getInputFileData(self, input_file_id: str, subsample: int = 1 ):
        input_file_path = self.config.value(f"data/init/{input_file_id}")
        try:
            if os.path.isfile(input_file_path):
                print(f"Reading unstructured {input_file_id} data from file {input_file_path}")
                with open(input_file_path, 'rb') as f:
                    result = pickle.load(f)
                    if   isinstance( result, np.ndarray ):  return result[::subsample]
                    elif isinstance( result, list ):
                        subsampled = [ result[i] for i in range( 0, len(result), subsample ) ]
                        if isinstance( result[0], np.ndarray ):  return np.vstack( subsampled )
                        else:                                    return np.array( subsampled )
        except Exception as err:
            print(f" Can't read data[{input_file_id}] file {input_file_path}: {err}")

dataManager = DataManager()