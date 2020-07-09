from PyQt5.QtWidgets import *
from hyperclass.data.swift.manager import dataManager
from PyQt5.QtCore import  QSettings
from typing import List, Union, Tuple, Optional
from hyperclass.gui.dialog import DialogBase
from hyperclass.reduction.manager import reductionManager

class PrepareInputsDialog(DialogBase):

    DSID = "swift_spectra"

    def __init__( self, input_file_ids: List[str], callback = None, scope: QSettings.Scope = QSettings.UserScope ):
        self.inputs = input_file_ids
        super(PrepareInputsDialog, self).__init__( callback, scope )

    def addContent(self):
        self.mainLayout.addLayout( self.createSettingInputField( "Dataset ID", "dataset/id", self.DSID ) )
        inputsGroupBox = QGroupBox('inputs')
        inputsLayout = QVBoxLayout()
        inputsGroupBox.setLayout( inputsLayout )

        inputsLayout.addLayout( self.createFileSystemSelectionWidget( "Data Directory",    self.DIRECTORY, "data/dir", "data/dir" ) )
        inputsLayout.addLayout( self.createFileSystemSelectionWidget("Cache Directory", self.DIRECTORY, "data/cache", "data/dir") )
        for input_file_id in self.inputs:
            inputsLayout.addLayout( self.createFileSystemSelectionWidget( input_file_id, self.FILE, f"data/init/{input_file_id}", "data/dir" ) )

        self.mainLayout.addWidget( inputsGroupBox )
        self.mainLayout.addWidget( reductionManager.gui(self) )
