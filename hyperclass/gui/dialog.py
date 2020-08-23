from PyQt5.QtWidgets import *
from PyQt5.QtCore import  QSettings
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
from typing import List
import sys

class DialogBase(QDialog):

    FILE = 0
    DIRECTORY = 1

    CONFIG = 0
    DATA_PREP = 1
    RUNTIME = 2

    def __init__( self, parent, dtype: int, callback = None, scope: QSettings.Scope = QSettings.UserScope ):
        super(DialogBase, self).__init__( parent )
        self.callback = callback
        self.scope = scope
        self.widgets = []
        self.layouts = []
        self.updateSettings()
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect( self.save )
        self.buttonBox.rejected.connect( self.cancel )
        self.mainLayout = QVBoxLayout()
        self.mainLayout.addWidget( self.buttonBox )
        self.addContent(dtype)
        self.setLayout(self.mainLayout)
        self.resize( 800, 400)

    def addFileContent(self, inputsLayout: QBoxLayout ):
        pass

    def addApplicationContent(self, inputsLayout: QBoxLayout ):
        pass

    def addDataPrepContent(self, inputsLayout: QBoxLayout ):
        pass

    def getProjectList(self) -> Optional[List[str]]:
        return None

    def updateSettings(self):
        from hyperclass.data.manager import dataManager
        self.settings: QSettings = dataManager.getSettings(self.scope)

    def addContent( self, dtype: int ):
        from hyperclass.data.manager import dataManager
        self.mainLayout.addLayout( self.createComboSelector("Project ID", [dataManager.project_name], "project/id", dataManager.project_name ) )
        self.inputsGroupBox = QGroupBox( 'inputs' )
        self.inputsLayout = QVBoxLayout()
        self.inputsLayout.addLayout( self.createFileSystemSelectionWidget("Data Directory", self.DIRECTORY, "data/dir", "data/dir"))
        self.inputsLayout.addLayout( self.createFileSystemSelectionWidget("Cache Directory", self.DIRECTORY, "data/cache", "data/dir"))
        self.mainLayout.addWidget(self.inputsGroupBox)
        self.addFileContent( self.inputsLayout )
        self.addDataPrepContent( self.inputsLayout )
    #    if dtype == self.RUNTIME: self.addApplicationContent( self.inputsLayout )
        self.inputsGroupBox.setLayout(self.inputsLayout)

    def createComboSelector(self, label_text: str, values: List, settings_key: str, default_value = None,
                            update_dialog: bool = False, callback: Callable[[str],None] = None ) -> QLayout:
        sizeSelectorLayout = QHBoxLayout(); self.layouts.append( sizeSelectorLayout )
        comboBox = QComboBox(); self.widgets.append( comboBox )
        label = QLabel( label_text ); self.widgets.append( label )
        label.setBuddy( comboBox )
        comboBox.addItems( [ str(x) for x in values ] )
        comboBox.setCurrentText( str( self.settings.value(settings_key,default_value) ) )
        sizeSelectorLayout.addWidget( label )
        sizeSelectorLayout.addWidget(comboBox)
        def selectionchange( index ):
            value = comboBox.currentText()
            self.settings.setValue( settings_key, value )
            if update_dialog: self.addContent()
            if callback is not None: callback( value )
        comboBox.currentIndexChanged.connect( selectionchange )
        self.settings.setValue(settings_key, comboBox.currentText())
        return sizeSelectorLayout

    def createSettingInputField(self, label_text, settings_key, default_value = None, **kwargs ) -> QLayout:
        layout = QHBoxLayout(); self.layouts.append( layout )
        init_value = self.settings.value( settings_key, None )
        if init_value is None:
            init_value = default_value
            self.settings.setValue( settings_key, init_value )
        textField = QLineEdit( init_value ); self.widgets.append( textField )
        if bool(kwargs.get('hidden',False)): textField.setEchoMode(QLineEdit.Password)
        label = QLabel( label_text ); self.widgets.append( label )
        label.setBuddy( textField )
        layout.addWidget( label )
        layout.addWidget( textField )
        callback = kwargs.get( 'callback', None )
        def selectionchange( value ):
            print( f"{settings_key}: {value}")
            self.settings.setValue( settings_key, value )
            if callback is not None: callback( value )
        textField.textChanged.connect( selectionchange )
        return layout

    def save(self):
        del self.settings
        if self.callback is not None:
            self.callback()
        self.close()

    def cancel(self):
        self.close()

    def createFileSystemSelectionWidget(self, label, type: int, settings_key: str, directory_key: str =""  ):
        directory = self.settings.value( directory_key )
        init_value = self.settings.value( settings_key )
        fileSelection = QHBoxLayout(); self.layouts.append( fileSelection )
        lineEdit = QLineEdit( init_value ); self.widgets.append( lineEdit )
        label = QLabel( label ); self.widgets.append( label )
        label.setBuddy(lineEdit)
        selectButton = QPushButton("Select"); self.widgets.append( selectButton )
        def select():
            if type == self.FILE:        selection = QFileDialog.getOpenFileName( self, "Select File", directory )[0]
            elif type == self.DIRECTORY: selection = QFileDialog.getExistingDirectory( self, "Select Directory", directory )
            else: raise Exception( f" Unknown dialog type: {type}")
            if selection: lineEdit.setText( selection )
        selectButton.clicked.connect(select)
        def selectionchange( value ):
            print( f"{settings_key}: {value}")
            self.settings.setValue( settings_key, value.strip(' "') )
        lineEdit.textChanged.connect( selectionchange )
        fileSelection.addWidget( label )
        fileSelection.addWidget( lineEdit )
        fileSelection.addWidget( selectButton )
        return fileSelection

    def createGroupBox(self, label: str, widget_layouts: List[ Union[QLayout,QWidget] ] ) -> QGroupBox :
        groupBox = QGroupBox(label)
        box_layout = QVBoxLayout()
        for widget_layout in widget_layouts:
            if isinstance( widget_layout, QLayout ):
                box_layout.addLayout( widget_layout  )
            elif isinstance( widget_layout, QWidget ):
                box_layout.addWidget( widget_layout  )
            else: raise Exception( f" Unrecognized object added to layout: {widget_layout} ")
        groupBox.setLayout( box_layout )
        return groupBox

if __name__ == '__main__':
    app = QApplication(sys.argv)

    dialog = DialogBase()
    dialog.exec_()

    sys.exit(app.exec_())
