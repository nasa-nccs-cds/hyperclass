from PyQt5.QtWidgets import *
from hyperclass.data.swift.manager import dataManager
from PyQt5.QtCore import  QSettings
from typing import List, Union, Tuple, Optional

class PrepareInputsDialog(QDialog):

    FILE = 0
    DIRECTORY = 1

    def __init__( self, input_file_ids: List[str], callback = None, scope: QSettings.Scope = QSettings.UserScope ):
        super(PrepareInputsDialog, self).__init__(None)
        self.callback = callback
        self.settings: QSettings = dataManager.getSettings( scope )
        self.textbox = self.createSettingInputField( "Dataset ID", "dataset/id")
        dataGroupBox = self.createDataGroupBox( input_file_ids )
        mainLayout = QGridLayout()
        mainLayout.addWidget( dataGroupBox, 0, 0, 3, 2 )

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect( self.save )
        mainLayout.addWidget( self.buttonBox, 3, 0, 1, 2 )
        self.setLayout(mainLayout)
        self.resize( 800, 400)

    def createSettingInputField(self, label_text, settings_key ) -> QLayout:
        layout = QHBoxLayout()
        init_value = self.settings.value( settings_key )
        textField = QLineEdit( init_value )
        label = QLabel( label_text )
        label.setBuddy( textField )
        layout.addWidget( label )
        layout.addWidget( textField )
        def selectionchange( value ):
            print( f"{settings_key}: {value}")
            self.settings.setValue( settings_key, value )
        textField.textChanged.connect( selectionchange )
        return layout

    def save(self):
        del self.settings
        self.close()
        if self.callback: self.callback()

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

    def createDataGroupBox(self, input_file_ids: List[str] ) -> QGroupBox:
        dirSelection =  self.createFileSystemSelectionWidget( "Data Directory",    self.DIRECTORY, "data/dir", "data/dir" )
        cacheSelection = self.createFileSystemSelectionWidget("Cache Directory", self.DIRECTORY, "data/cache", "data/dir")
        widgets = [ dirSelection, cacheSelection ]
        for input_file_id in input_file_ids:
            widgets.append( self.createFileSystemSelectionWidget( input_file_id, self.FILE, f"data/init/{input_file_id}", "data/dir" ) )
        return self.createGroupBox( "data", widgets )


class SwiftPreferencesDialog(QDialog):

    FILE = 0
    DIRECTORY = 1

    def __init__( self, input_file_ids: List[str], callback = None, scope: QSettings.Scope = QSettings.UserScope ):
        super(PrepareInputsDialog, self).__init__(None)
        self.callback = callback
        self.settings: QSettings = dataManager.getSettings( scope )
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

    def createDataGroupBox(self, input_file_ids: List[str] ) -> QGroupBox:
        dirSelection =  self.createFileSystemSelectionWidget( "Data Directory",    self.DIRECTORY, "data/dir", "data/dir" )
        cacheSelection = self.createFileSystemSelectionWidget("Cache Directory", self.DIRECTORY, "data/cache", "data/dir")
        widgets = [ dirSelection, cacheSelection ]
        for input_file_id in input_file_ids:
            widgets.append( self.createFileSystemSelectionWidget( input_file_id, self.FILE, f"data/init/{input_file_id}", "data/dir" ) )
        return self.createGroupBox( "data", widgets )

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

    def createUMAPGroupBox(self):
        nNeighborsSelector = self.createSizeSelector( "#Neighbors: ", range(4,20), "umap/nneighbors" )
        nEpochsSelector = self.createSizeSelector( "#Epochs: ", range(50,500,50), "umap/nepochs" )
        return self.createGroupBox("umap", [nNeighborsSelector, nEpochsSelector])

    def createSVMGroupBox(self):
        nDimSelector = self.createSizeSelector( "#Dimensions: ", range(4,20), "svm/ndim" )
        return self.createGroupBox("svm", [nDimSelector])
