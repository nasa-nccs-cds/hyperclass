from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtCore import *
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.gui.labels import labelsManager
from hyperclass.data.manager import dataManager
from hyperclass.gui.events import EventClient, EventMode
import os, abc, sys

class HCApplication( QApplication, EventClient ):
    def __init__( self ):
        QApplication.__init__( self, sys.argv )
        self.installEventFilter(self)

    def eventFilter(self, object, event: QEvent ):
        if   event.type() == QEvent.KeyPress:    self.onKeyPress( event )
        elif event.type() == QEvent.KeyRelease:  self.onKeyRelease()
        return False

    def onKeyPress( self, event: QKeyEvent ):
        try:
            event = dict( event="gui", type="keyPress", key=event.key(), modifiers=event.modifiers(),
                          nativeModifiers= event.nativeModifiers(), nativeScanCode=event.nativeScanCode(),
                          nativeVirtualKey=event.nativeVirtualKey() )
        except Exception as err:
            print(f"HCApplication.keyPressEvent error: {err}")
        self.submitEvent( event, EventMode.Gui )

    def onKeyRelease(self):
        self.submitEvent( dict( event="gui", type="keyRelease"), EventMode.Foreground )



class HCMainWindow(QMainWindow, EventClient):
    __metaclass__ = abc.ABCMeta

    def __init__( self, parent = None ):
        QMainWindow.__init__( self, parent )
        self.setWindowTitle( dataManager.project_name )
        self.mainMenu = self.menuBar()
        self.mainMenu.setNativeMenuBar(False)
        self.fileMenu = self.mainMenu.addMenu('App')
        self.datasetMenu = self.mainMenu.addMenu('Dataset')
        self.editMenu = self.mainMenu.addMenu('Edit')
        self.addMenuItems()

        menuButton = QAction( "reinit", self )
        menuButton.setStatusTip(f"Return daset to initial state")
        menuButton.triggered.connect(self.reinitDataset)
        self.datasetMenu.addAction( menuButton )

        menuButton = QAction( "clear", self )
        menuButton.setStatusTip(f"Clear loaded data & reset app to initial state")
        menuButton.triggered.connect(self.clearDataset)
        self.datasetMenu.addAction( menuButton )

        prefButton = QAction( 'Preferences', self )
        prefButton.setShortcut('Ctrl+P')
        prefButton.setStatusTip('Set application configuration parameters')
        prefButton.triggered.connect( self.setPreferences )
        self.fileMenu.addAction(prefButton)

        exitButton = QAction(QIcon('exit24.png'), 'Exit', self )
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Exit application')
        exitButton.triggered.connect(self.close)
        self.fileMenu.addAction(exitButton)

#        self.helpMenu = self.mainMenu.addMenu('Help')

    def setPreferences(self):
        preferences =  self.getPreferencesDialog()
        preferences.show()

    @abc.abstractmethod
    def addMenuItems(self):
        pass

    @abc.abstractmethod
    def getPreferencesDialog(self):
        pass

    def clearDataset(self):
        labelsManager.clearMarkers()
        event = dict(event='gui', type='reset', label='clear dataset' )
        self.submitEvent(event, EventMode.Gui)
        taskRunner.kill_all_tasks()

    def reinitDataset(self):
        taskRunner.kill_all_tasks()
        event = dict(event='gui', type='reinit', label='reinit dataset' )
        self.submitEvent(event, EventMode.Gui)