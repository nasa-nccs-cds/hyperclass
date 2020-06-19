import numpy as np
import xarray as xa
import pathlib
import matplotlib as mpl
from typing import List, Union, Tuple, Optional, Dict
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from PyQt5.QtCore import QSettings, QCoreApplication
import matplotlib.pyplot as plt
from hyperclass.gui.tasks import taskRunner, Task, Callbacks
import os, math, pickle

QCoreApplication.setOrganizationName("ilab")
QCoreApplication.setOrganizationDomain("nccs.nasa.gov")
QCoreApplication.setApplicationName("swiftclass")

class DataManager:

    settings_initialized = False
    default_settings = {  "umap/nneighbors": 8, "umap/nepochs": 300, "svm/ndim": 8  }

    def __init__( self, **kwargs ):   # Tile shape (y,x) matches image shape (row,col)
        self.cacheTileData = kwargs.get( 'cache_tile', True )
        self._initDefaultSettings()
        self.config = self.getSettings( QSettings.UserScope )

    @classmethod
    def root_dir(cls) -> str:
        parent_dirs = pathlib.Path(__file__).parents
        return parent_dirs[ 3 ]

    @classmethod
    def settings_dir(cls) -> str:
        return os.path.join( cls.root_dir(), 'config' )

    @classmethod
    def getSettings( cls, scope: QSettings.Scope ):
        cls._initDefaultSettings()
        return QSettings(QSettings.IniFormat, scope, QCoreApplication.organizationDomain(), QCoreApplication.applicationName())

    @classmethod
    def _initDefaultSettings(cls):
        if not cls.settings_initialized:
            cls.settings_initialized = True
            system_settings_dir = cls.settings_dir()
            QSettings.setPath( QSettings.IniFormat, QSettings.SystemScope, system_settings_dir )
            settings = cls.getSettings( QSettings.SystemScope )
            print( f"Saving system settings to {settings.fileName()}, writable = {settings.isWritable()}")
            for key, value in cls.default_settings.items():
                current = settings.value( key )
                if not current: settings.setValue( key, value )

    def getInputFileData(self, input_file_id: str):
        input_file_path = self.config.value(f"data/init/{input_file_id}")
        try:
            if os.path.isfile(input_file_path):
                print(f"Reading swift {input_file_id} data from file {input_file_path}")
                with open(input_file_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as err:
            print(f" Can't read data[{input_file_id}] file {input_file_path}: {err}")


dataManager = DataManager()