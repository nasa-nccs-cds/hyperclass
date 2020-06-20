from PyQt5.QtWidgets import *
from hyperclass.data.swift.manager import dataManager
from PyQt5.QtCore import  QSettings
from typing import List, Union, Tuple, Optional
import sys

class DialogBase(QDialog):

    FILE = 0
    DIRECTORY = 1

    def __init__( self, callback = None, scope: QSettings.Scope = QSettings.UserScope ):
        super(DialogBase, self).__init__(None)
        self.callback = callback
        self.scope = scope
        self.settings: QSettings = dataManager.getSettings( scope )
        self.mainLayout = QVBoxLayout()
        self.addContent()
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect( self.save )
        self.buttonBox.rejected.connect( self.cancel )
        self.mainLayout.addWidget( self.buttonBox )
        self.setLayout(self.mainLayout)
        self.resize( 800, 400)

    def addContent(self):
        pass

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

    def createSettingInputField(self, label_text, settings_key, default_value = None, hidden=False ) -> QLayout:
        layout = QHBoxLayout()
        init_value = self.settings.value( settings_key, None )
        if init_value is None:
            init_value = default_value
            self.settings.setValue( settings_key, init_value )
        textField = QLineEdit( init_value )
        if hidden: textField.setEchoMode(QLineEdit.Password)
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

    def cancel(self):
        self.close()

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

if __name__ == '__main__':
    app = QApplication(sys.argv)

    dialog = DialogBase()
    dialog.show()

    sys.exit(app.exec_())
