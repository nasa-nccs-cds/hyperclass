from PyQt5.QtWidgets import *
from hyperclass.gui.dialog import DialogBase
import pathlib
import numpy as np
from typing import List, Union, Tuple, Optional, Dict
from PyQt5.QtCore import QSettings, QCoreApplication
import os, math, pickle
QCoreApplication.setOrganizationName("ilab")
QCoreApplication.setOrganizationDomain("nccs.nasa.gov")

class PreferencesDialog(DialogBase):

    def __init__( self, callback = None,  scope: QSettings.Scope = QSettings.UserScope ):
        super(PreferencesDialog, self).__init__( callback, scope )

    def addContent(self):
        dataGroupBox = self.createDataGroupBox()
        tileGroupBox = self.createTileGroupBox()
        umapGroupBox = self.createUMAPGroupBox()
        svmGroupBox = self.createSVMGroupBox()

        gridLayout = QGridLayout()
        gridLayout.addWidget( dataGroupBox, 0, 0, 1, 2 )
        gridLayout.addWidget( tileGroupBox, 1, 0, 1, 1 )
        gridLayout.addWidget( umapGroupBox, 1, 1, 1, 1 )
        gridLayout.addWidget(  svmGroupBox, 2, 0, 1, 1 )

        if self.scope == QSettings.SystemScope:
            googleGroupBox = self.createGoogleGroupBox()
            gridLayout.addWidget(googleGroupBox, 2, 1, 1, 1)

        self.mainLayout.addLayout(gridLayout)

    def createDataGroupBox(self) -> QGroupBox:
        dirSelection =  self.createFileSystemSelectionWidget( "Data Directory",    self.DIRECTORY, "data/dir", "data/dir" )
        cacheSelection = self.createFileSystemSelectionWidget("Cache Directory", self.DIRECTORY, "data/cache", "data/dir")
        fileSelection = self.createFileSystemSelectionWidget( "Initial Data File", self.FILE,      "data/init/file",  "data/dir" )
        return self.createGroupBox( "data", [ dirSelection, cacheSelection, fileSelection ] )

    def createTileGroupBox(self):
        blockSizeSelector = self.createComboSelector("Block Side Length: ", range(100, 600, 50), "block/size")
        blocksPerTileSelector = self.createComboSelector("Tile Side Length: ", range(600, 2000, 200), "tile/size")
        return self.createGroupBox("tiles", [blockSizeSelector, blocksPerTileSelector])

    def createInitGroupBox(self):
        blockSizeSelector = self.createComboSelector("Tile Indices: ", range(100, 600, 50), "block/indices")
        blocksPerTileSelector = self.createComboSelector("Block Indices: ", [x * x for x in range(1, 7)], "tile/indices")
        return self.createGroupBox("tiles", [blockSizeSelector, blocksPerTileSelector])

    def createUMAPGroupBox(self):
        nNeighborsSelector = self.createComboSelector("#Neighbors: ", range(4, 20), "umap/nneighbors")
        nEpochsSelector = self.createComboSelector("#Epochs: ", range(50, 500, 50), "umap/nepochs")
        return self.createGroupBox("umap", [nNeighborsSelector, nEpochsSelector])

    def createSVMGroupBox(self):
        nDimSelector = self.createComboSelector("#Dimensions: ", range(4, 20), "svm/ndim")
        return self.createGroupBox("svm", [nDimSelector])

    def createGoogleGroupBox(self):
        apiKeySelector = self.createSettingInputField( "API KEY", "google/api_key", "", True )
        return self.createGroupBox("google", [apiKeySelector])

class SettingsManager:

    def __init__( self, **kwargs ):
        system_settings_dir = self.settings_dir()
        QSettings.setPath(QSettings.IniFormat, QSettings.SystemScope, system_settings_dir)
        self.project_name = None
        self.default_settings = {}

    def setProjectName(self, name: str ):
        self.project_name = name

    @property
    def config(self) -> QSettings:
        return self.getSettings( QSettings.UserScope )

    def iparm(self, key: str ):
        return int( self.config.value(key) )

    def get_dtype(self, result ):
        if isinstance( result, np.ndarray ): return result.dtype
        else: return np.float64 if type( result[0] ) == "float" else None

    def root_dir(self) -> str:
        parent_dirs = pathlib.Path(__file__).parents
        return parent_dirs[ 3 ]

    def settings_dir(self) -> str:
        return os.path.join( self.root_dir(), 'config' )

    def getSettings( self, scope: QSettings.Scope ) -> QSettings:
        settings = QSettings(QSettings.IniFormat, scope, QCoreApplication.organizationDomain()+ "." + QCoreApplication.applicationName(), self.project_name )
        for key, value in self.default_settings.items():
            current = settings.value(key)
            if not current: settings.setValue(key, value)
        print(f"Saving system settings to {settings.fileName()}, writable = {settings.isWritable()}")
        return settings