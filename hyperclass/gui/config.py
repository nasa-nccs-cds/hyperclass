from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QCoreApplication, QSettings
from typing import List, Union, Tuple, Optional

class PreferencesDialog(QDialog):

    FILE = 0
    DIRECTORY = 1

    def __init__(self, parent=None):
        super(PreferencesDialog, self).__init__(parent)
        self.settings = QSettings()
        dataGroupBox = self.createDataGroupBox()
        tileGroupBox = self.createTileGroupBox()

        mainLayout = QGridLayout()
        mainLayout.addWidget(dataGroupBox, 0, 0, 1, 2)
        mainLayout.addWidget(tileGroupBox, 1, 0, 1, 1)
        self.setLayout(mainLayout)

        #        lineEdit.setEchoMode(QLineEdit.Password)

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
            self.settings.setValue( settings_key, selection )
        selectButton.clicked.connect(select)
        fileSelection.addWidget( label )
        fileSelection.addWidget( lineEdit )
        fileSelection.addWidget( selectButton )
        return fileSelection

    def createDataGroupBox(self):
        dataGroupBox = QGroupBox("data")
        dirSelection =  self.createFileSystemSelectionWidget( "Data Directory",    self.DIRECTORY, "data/dir",        "data/dir" )
        fileSelection = self.createFileSystemSelectionWidget( "Initial Data File", self.FILE,      "data/init/file",  "data/dir" )
        layout = QVBoxLayout()
        layout.addLayout(dirSelection)
        layout.addLayout(fileSelection)
        dataGroupBox.setLayout(layout)
        return dataGroupBox

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

    def createTileGroupBox(self):
        tilesGroupBox = QGroupBox("tiles")
        layout = QVBoxLayout()
        blockSizeSelector = self.createSizeSelector( "Block Side Length: ", range(100,600,100), "block/size" )
        blocksPerTileSelector = self.createSizeSelector( "Blocks per tile: ", [ x*x for x in range(1,7) ], "tile/nblocks" )
        layout.addLayout( blockSizeSelector )
        layout.addLayout( blocksPerTileSelector )
        tilesGroupBox.setLayout(layout)
        return tilesGroupBox


if __name__ == '__main__':


    import sys

    app = QApplication(sys.argv)
    preferences = PreferencesDialog()
    preferences.show()
    sys.exit(app.exec_())