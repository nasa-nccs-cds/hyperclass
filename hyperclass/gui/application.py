from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QKeyEvent
from hyperclass.gui.events import EventClient, EventMode
import os, abc

class HCMainWindow(QMainWindow, EventClient):
    __metaclass__ = abc.ABCMeta

    def __init__( self, parent, title: str ):
        QMainWindow.__init__( self, parent )
        self.setWindowTitle(title)
        self.mainMenu = self.menuBar()
        self.mainMenu.setNativeMenuBar(False)
        self.fileMenu = self.mainMenu.addMenu('File')
        self.helpMenu = self.mainMenu.addMenu('Help')
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

    def setPreferences(self):
        preferences =  self.getPreferencesDialog()
        preferences.show()

    @abc.abstractmethod
    def addMenuItems(self):
        pass

    @abc.abstractmethod
    def getPreferencesDialog(self):
        pass

    def keyPressEvent( self, event: QKeyEvent ):
        QMainWindow.keyPressEvent( self, event )
        event = dict( event="gui", type="keyPress", key=event.key(), modifiers=event.modifiers(),
                      nativeModifiers= event.nativeModifiers(), nativeScanCode=event.nativeScanCode(),
                      nativeVirtualKey=event.nativeVirtualKey() )
        print( "HCMainWindow.keyPressEvent")
        self.submitEvent( event, EventMode.Foreground )

    def keyReleaseEvent(self, event: QKeyEvent):
        QMainWindow.keyReleaseEvent( self, event )
        print("HCMainWindow.keyReleaseEvent")
        self.submitEvent( dict( event="gui", type="keyRelease"), EventMode.Foreground )