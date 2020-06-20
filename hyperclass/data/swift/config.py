from PyQt5.QtWidgets import *
from hyperclass.data.swift.manager import dataManager
from PyQt5.QtCore import  QSettings
from typing import List, Union, Tuple, Optional
from hyperclass.gui.dialog import DialogBase

class PrepareInputsDialog(DialogBase):

    DSID = "swift_spectra"

    def __init__( self, input_file_ids: List[str], callback = None, scope: QSettings.Scope = QSettings.UserScope ):
        self.inputs = input_file_ids
        super(PrepareInputsDialog, self).__init__( callback, scope )

    def addContent(self):
        self.mainLayout.addLayout( self.createSettingInputField( "Dataset ID", "dataset/id", self.DSID ) )
        self.mainLayout.addLayout( self.createFileSystemSelectionWidget( "Data Directory",    self.DIRECTORY, "data/dir", "data/dir" ) )
        self.mainLayout.addLayout( self.createFileSystemSelectionWidget("Cache Directory", self.DIRECTORY, "data/cache", "data/dir") )
        for input_file_id in self.inputs:
            self.mainLayout.addLayout( self.createFileSystemSelectionWidget( input_file_id, self.FILE, f"data/init/{input_file_id}", "data/dir" ) )

class SwiftPreferencesDialog(DialogBase):

    def __init__( self, callback = None, scope: QSettings.Scope = QSettings.UserScope ):
        super(PrepareInputsDialog, self).__init__( callback, scope )
        dataGroupBox = self.createDataGroupBox( input_file_ids )
        umapGroupBox = self.createUMAPGroupBox()
        svmGroupBox = self.createSVMGroupBox()

        mainLayout = QGridLayout()
        mainLayout.addWidget( dataGroupBox, 0, 0, 1, 2 )
        mainLayout.addWidget( umapGroupBox, 2, 1, 1, 1 )
        mainLayout.addWidget(  svmGroupBox, 2, 0, 1, 1 )

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect( self.save )
        mainLayout.addWidget( self.buttonBox, 3, 0, 1, 2 )
        self.setLayout(mainLayout)
        self.resize( 800, 400)

    def save(self):
        del self.settings
        self.close()
        if self.callback: self.callback()

    def createDataGroupBox(self, input_file_ids: List[str] ) -> QGroupBox:
        dirSelection =  self.createFileSystemSelectionWidget( "Data Directory",    self.DIRECTORY, "data/dir", "data/dir" )
        cacheSelection = self.createFileSystemSelectionWidget("Cache Directory", self.DIRECTORY, "data/cache", "data/dir")
        widgets = [ dirSelection, cacheSelection ]
        for input_file_id in input_file_ids:
            widgets.append( self.createFileSystemSelectionWidget( input_file_id, self.FILE, f"data/init/{input_file_id}", "data/dir" ) )
        return self.createGroupBox( "data", widgets )

    def createUMAPGroupBox(self):
        nNeighborsSelector = self.createSizeSelector( "#Neighbors: ", range(4,20), "umap/nneighbors" )
        nEpochsSelector = self.createSizeSelector( "#Epochs: ", range(50,500,50), "umap/nepochs" )
        return self.createGroupBox("umap", [nNeighborsSelector, nEpochsSelector])

    def createSVMGroupBox(self):
        nDimSelector = self.createSizeSelector( "#Dimensions: ", range(4,20), "svm/ndim" )
        return self.createGroupBox("svm", [nDimSelector])
