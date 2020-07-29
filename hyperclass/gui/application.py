from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtCore import *
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

    def __init__( self, parent, title: str ):
        QMainWindow.__init__( self, parent )
        self.setWindowTitle(title)
        self.mainMenu = self.menuBar()
        self.mainMenu.setNativeMenuBar(False)
        self.fileMenu = self.mainMenu.addMenu('App')
        self.datasetMenu = self.mainMenu.addMenu('Dataset')
        self.editMenu = self.mainMenu.addMenu('Edit')
        self.addMenuItems()

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
