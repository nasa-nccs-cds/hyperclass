from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.mpl import MplWidget
from hyperclass.gui.points import VTKFrame
from typing import List, Union, Dict, Callable, Tuple, Optional

class HyperclassConsole(QMainWindow):
    def __init__(self, umgr: UMAPManager):
        QMainWindow.__init__(self)

        self.title = 'hyperclass'
        self.left = 10
        self.top = 10
        self.width = 1920
        self.height = 1080
        self.NFunctionButtons = 0

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.showMessage('Ready')

        mainMenu = self.menuBar()
        mainMenu.setNativeMenuBar(False)
        fileMenu = mainMenu.addMenu('File')
        helpMenu = mainMenu.addMenu('Help')

        exitButton = QAction(QIcon('exit24.png'), 'Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Exit application')
        exitButton.triggered.connect(self.close)
        fileMenu.addAction(exitButton)

        self.vtkFrame = VTKFrame( umgr )
        self.console = MplWidget( umgr,self)

        for menuName, menuItems in self.console.menu_actions.items():
            menu = mainMenu.addMenu(menuName)
            for menuItem in menuItems:
                menuButton = QAction( menuItem[0], self )
                if menuItem[1] is not None: menuButton.setShortcut( menuItem[1] )
                if menuItem[2] is not None: menuButton.setStatusTip( menuItem[2] )
                menuButton.triggered.connect( menuItem[3] )
                menu.addAction(menuButton)

        widget =  QWidget(self)
        self.setCentralWidget(widget)
        vlay = QVBoxLayout(widget)

        framesLayout = QHBoxLayout()
        framesLayout.addWidget( self.console )
        framesLayout.addWidget( self.vtkFrame )
        vlay.addLayout(framesLayout)

        buttonsLayout = QHBoxLayout()
        for label, callback in self.console.button_actions.items():
            pybutton = QPushButton( label, self )
            pybutton.clicked.connect( callback )
            buttonsLayout.addWidget(pybutton)
        vlay.addLayout(buttonsLayout)

    def showMessage( self, message: str ):
        self.statusBar().showMessage(message)

    def update(self ):
        self.showMessage('Ready')
        self.vtkFrame.update()

    def setBlock(self, block_coords: Tuple[int]):
        self.console.setBlock(block_coords)

    def show(self):
        QMainWindow.show(self)
        self.vtkFrame.Initialize()
