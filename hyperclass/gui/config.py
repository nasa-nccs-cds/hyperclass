from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QCoreApplication, QSettings
from typing import List, Union, Tuple, Optional

class PreferencesDialog(QDialog):

    FILE = 0
    DIRECTORY = 1

    def __init__( self, parent=None, settings = None ):
        super(PreferencesDialog, self).__init__(parent)
        self.settings = QSettings() if settings is None else settings
        dataGroupBox = self.createDataGroupBox()
        tileGroupBox = self.createTileGroupBox()
        umapGroupBox = self.createUMAPGroupBox()
        svmGroupBox = self.createSVMGroupBox()
        googleGroupBox = self.createGoogleGroupBox()

        mainLayout = QGridLayout()
        mainLayout.addWidget(dataGroupBox, 0, 0, 1, 2)
        mainLayout.addWidget(tileGroupBox, 1, 0, 1, 1)
        mainLayout.addWidget(umapGroupBox, 1, 1, 1, 1)
        mainLayout.addWidget( svmGroupBox, 2, 0, 1, 1)
        mainLayout.addWidget(googleGroupBox, 2, 1, 1, 1)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Save)
        buttonBox.accepted.connect( self.save )
        mainLayout.addWidget( buttonBox, 3, 0, 1, 2 )
        self.setLayout(mainLayout)

    def save(self):
        self.settings.sync()

    def createFileSystemSelectionWidget(self, label, type: int, settings_key: str, directory_key: str =""  ):
        directory = self.settings.value( directory_key )
        init_value = self.settings.value( settings_key )
        fileSelection = QHBoxLayout()
        lineEdit = QLineEdit( init_value )
        label = QLabel( label )
        label.setBuddy(lineEdit)
        selectButton = QPushButton("Select")
        def select():
            if type == self.FILE:        selection = QFileDialog.getOpenFileName( self, "Select File", directory )[0]
            elif type == self.DIRECTORY: selection = QFileDialog.getExistingDirectory( self, "Select Directory", directory )
            else: raise Exception( f" Unknown dialog type: {type}")
            lineEdit.setText( selection )
        selectButton.clicked.connect(select)
        def selectionchange( value ):
            print( f"{settings_key}: {value}")
            self.settings.setValue( settings_key, value )
        lineEdit.textChanged.connect( selectionchange )
        fileSelection.addWidget( label )
        fileSelection.addWidget( lineEdit )
        fileSelection.addWidget( selectButton )
        return fileSelection

    def createGroupBox(self, label: str, widget_layouts: List[QLayout] ) -> QGroupBox :
        groupBox = QGroupBox(label)
        box_layout = QVBoxLayout()
        for widget_layout in widget_layouts:
            box_layout.addLayout( widget_layout )
        groupBox.setLayout( box_layout )
        return groupBox

    def createDataGroupBox(self) -> QGroupBox:
        dirSelection =  self.createFileSystemSelectionWidget( "Data Directory",    self.DIRECTORY, "data/dir", "data/dir" )
        cacheSelection = self.createFileSystemSelectionWidget("Cache Directory", self.DIRECTORY, "data/cache", "data/dir")
        fileSelection = self.createFileSystemSelectionWidget( "Initial Data File", self.FILE,      "data/init/file",  "data/dir" )
        return self.createGroupBox( "data", [ dirSelection, cacheSelection, fileSelection ] )

    def createSizeSelector(self, label_text: str, values: List[int], settings_key: str ) -> QLayout:
        sizeSelectorLayout = QHBoxLayout()
        comboBox = QComboBox()
        label = QLabel( label_text )
        label.setBuddy( comboBox )
        comboBox.addItems( [ str(x) for x in values ] )
        comboBox.setCurrentText( str( self.settings.value(settings_key) ) )
        sizeSelectorLayout.addWidget( label )
        sizeSelectorLayout.addWidget(comboBox)
        def selectionchange( index ):
            self.settings.setValue( settings_key, int( comboBox.currentText() ) )
        comboBox.currentIndexChanged.connect( selectionchange )
        return sizeSelectorLayout

    def createPasswordField(self, label_text: str, settings_key: str ) -> QLayout:
        layout = QHBoxLayout()
        init_value = self.settings.value( settings_key )
        pwField = QLineEdit( init_value )
        pwField.setEchoMode( QLineEdit.Password )
        label = QLabel( label_text )
        label.setBuddy( pwField )
        layout.addWidget( label )
        layout.addWidget( pwField )
        def selectionchange( value ):
            print( f"{settings_key}: {value}")
            self.settings.setValue( settings_key, value )
        pwField.textChanged.connect( selectionchange )
        return layout

    def createTileGroupBox(self):
        blockSizeSelector = self.createSizeSelector( "Block Side Length: ", range(100,600,100), "block/size" )
        blocksPerTileSelector = self.createSizeSelector( "Blocks per tile: ", [ x*x for x in range(1,7) ], "tile/nblocks" )
        return self.createGroupBox("tiles", [blockSizeSelector, blocksPerTileSelector])

    def createUMAPGroupBox(self):
        nNeighborsSelector = self.createSizeSelector( "#Neighbors: ", range(4,20), "umap/nneighbors" )
        nEpochsSelector = self.createSizeSelector( "#Epochs: ", range(50,500,50), "umap/nepochs" )
        return self.createGroupBox("umap", [nNeighborsSelector, nEpochsSelector])

    def createSVMGroupBox(self):
        nDimSelector = self.createSizeSelector( "#Dimensions: ", range(4,20), "svm/ndim" )
        return self.createGroupBox("svm", [nDimSelector])

    def createGoogleGroupBox(self):
        apiKeySelector = self.createPasswordField( "API KEY", "google/api_key" )
        return self.createGroupBox("google", [apiKeySelector])