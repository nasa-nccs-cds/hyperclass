from PyQt5.QtWidgets import *
from hyperclass.gui.dialog import DialogBase
import pathlib, glob
from functools import partial
import numpy as np
from typing import List, Union, Tuple, Optional, Dict, Callable
from PyQt5.QtCore import QSettings, QCoreApplication
import os, math, pickle

QCoreApplication.setOrganizationName("ilab")
QCoreApplication.setOrganizationDomain("nccs.nasa.gov")
QCoreApplication.setApplicationName("hyperclass")

class SearchBar(QWidget):

    def __init__( self, parent, findCallback: Callable[[str],None], selectCallback: Callable[[str],None] ):
        QWidget.__init__(self, parent)

        self.main_layout = QHBoxLayout()
        self.textField = None
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(2,2,2,2)

        self.main_layout.addLayout( self.createInputField( "find", onChange=findCallback ) )
        self.main_layout.addStretch( )
        self.main_layout.addLayout( self.createInputField( "select", onReturn=selectCallback ) )

        self.setLayout( self.main_layout )

    def createInputField(self, label_text, **kwargs) -> QLayout:
        layout = QHBoxLayout()
        self.textField = QLineEdit("")
        label = QLabel(label_text)
        label.setBuddy(self.textField)
        layout.addWidget(label)
        layout.addWidget(self.textField)
        self.textChangedCallback = kwargs.get( 'onChange', None )
        if self.textChangedCallback: self.textField.textChanged.connect( self.textChangedCallback )
        self.returnPressedCallback = kwargs.get( 'onReturn', None )
        if self.returnPressedCallback: self.textField.returnPressed.connect( self.returnPressed )
        return layout

    def returnPressed( self ):
        self.returnPressedCallback( self.textField.text() )

class PreferencesDialog(DialogBase):

    def __init__( self, parent, dtype: int, callback = None,  scope: QSettings.Scope = QSettings.UserScope, **kwargs ):
        self.spatial = kwargs.get( 'spatial', False )
        self.dev = kwargs.get('dev', False)
        super(PreferencesDialog, self).__init__( parent, dtype, callback, scope )
        self._row = 0

    def addApplicationContent( self, mainLayout ):
        from hyperclass.umap.manager import umapManager
        from hyperclass.learn.manager import learningManager

        if self.spatial:
            self.tileGroupBox = self.createTileGroupBox()
            mainLayout.addWidget( self.tileGroupBox )

            if  self.scope == QSettings.SystemScope:
                mainLayout.addWidget( self.createGoogleGroupBox() )
            elif self.dev:
                mainLayout.addWidget( learningManager.config_gui(self) )

        mainLayout.addWidget( umapManager.config_gui(self) )
        mainLayout.addWidget( self.createSVMGroupBox() )


    def addDataPrepContent( self, mainLayout ):
        from hyperclass.reduction.manager import reductionManager
        mainLayout.addWidget( reductionManager.config_gui(self) )

    def createDataGroupBox(self) -> QGroupBox:
        self.dirSelection =  self.createFileSystemSelectionWidget( "Data Directory",    self.DIRECTORY, "data/dir", "data/dir" )
        self.cacheSelection = self.createFileSystemSelectionWidget("Cache Directory", self.DIRECTORY, "data/cache", "data/dir")
        self.fileSelection = self.createFileSystemSelectionWidget( "Initial Data File", self.FILE,      "data/init/file",  "data/dir" )
        return self.createGroupBox( "data", [ self.dirSelection, self.cacheSelection, self.fileSelection ] )

    def createTileGroupBox(self):
        self.blockSizeSelector = self.createComboSelector("Block Side Length: ", range(100, 600, 50), "block/size")
        self.blocksPerTileSelector = self.createComboSelector("Tile Side Length: ", range(600, 2000, 200), "tile/size")
        return self.createGroupBox("tiles", [self.blockSizeSelector, self.blocksPerTileSelector])

    def createInitGroupBox(self):
        self.tileSizeSelector = self.createComboSelector("Tile Indices: ", range(100, 600, 50), "tile/indices")
        self.blocksPerTileSelector = self.createComboSelector("Block Indices: ", [x * x for x in range(1, 7)], "block/indices")
        return self.createGroupBox("tiles", [self.tileSizeSelector, self.blocksPerTileSelector])

    def createSVMGroupBox(self):
        self.nDimSelector = self.createComboSelector("#Dimensions: ", range(4, 20), "svm/ndim")
        return self.createGroupBox("svm", [self.nDimSelector])

    def createGoogleGroupBox(self):
        self.apiKeySelector = self.createSettingInputField( "API KEY", "google/api_key", "", True )
        return self.createGroupBox("google", [self.apiKeySelector])

class SettingsManager:

    def __init__( self, **kwargs ):
        self.system_settings_dir = self.settings_dir()
        QSettings.setPath(QSettings.IniFormat, QSettings.SystemScope, self.system_settings_dir )
        self.project_name = None
        self.default_settings = kwargs.get('defaults',{})

    def initProject(self, name: str, default_settings: Dict ):
        self.project_name = name
        self.default_settings = default_settings

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

    # def updateProjectName(self):
    #     settings_path = os.path.join( self.system_settings_dir, QCoreApplication.organizationDomain() + "." + QCoreApplication.applicationName() )
    #     sorted_inifiles = sorted( glob.glob(f"{settings_path}/*.ini"), key=lambda t: -os.stat(t).st_mtime)
    #     self.project_name =  os.path.splitext( os.path.basename( sorted_inifiles[0] ) )[0]

    def getSettings( self, scope: QSettings.Scope ) -> QSettings:
        assert self.project_name is not None, "Failed to set project_name"
        settings = QSettings( QSettings.IniFormat, scope, QCoreApplication.organizationDomain() + "." + QCoreApplication.applicationName(), self.project_name )
        for key, value in self.default_settings.items():
            current = settings.value(key)
            if not current: settings.setValue(key, value)
#        print(f"Saving {scope} settings for project {self.project_name} to {settings.fileName()}, writable = {settings.isWritable()}")
        return settings