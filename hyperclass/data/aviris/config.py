from PyQt5.QtWidgets import *
from hyperclass.data.aviris.manager import dataManager
from PyQt5.QtCore import  QSettings
from typing import List, Union, Tuple, Optional
from hyperclass.gui.dialog import DialogBase

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
        blockSizeSelector = self.createSizeSelector( "Block Side Length: ", range(100,600,50), "block/size" )
        blocksPerTileSelector = self.createSizeSelector( "Tile Side Length: ", range(600,2000,200), "tile/size" )
        return self.createGroupBox("tiles", [blockSizeSelector, blocksPerTileSelector])

    def createInitGroupBox(self):
        blockSizeSelector = self.createSizeSelector( "Tile Indices: ", range(100,600,50), "block/indices" )
        blocksPerTileSelector = self.createSizeSelector( "Block Indices: ", [ x*x for x in range(1,7) ], "tile/indices" )
        return self.createGroupBox("tiles", [blockSizeSelector, blocksPerTileSelector])

    def createUMAPGroupBox(self):
        nNeighborsSelector = self.createSizeSelector( "#Neighbors: ", range(4,20), "umap/nneighbors" )
        nEpochsSelector = self.createSizeSelector( "#Epochs: ", range(50,500,50), "umap/nepochs" )
        return self.createGroupBox("umap", [nNeighborsSelector, nEpochsSelector])

    def createSVMGroupBox(self):
        nDimSelector = self.createSizeSelector( "#Dimensions: ", range(4,20), "svm/ndim" )
        return self.createGroupBox("svm", [nDimSelector])

    def createGoogleGroupBox(self):
        apiKeySelector = self.createSettingInputField( "API KEY", "google/api_key", "", True )
        return self.createGroupBox("google", [apiKeySelector])