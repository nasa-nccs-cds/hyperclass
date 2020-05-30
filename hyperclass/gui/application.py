from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.mpl import MplWidget
from functools import partial
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.gui.points import VTKFrame
from typing import List, Union, Dict, Callable, Tuple, Optional

class HyperclassConsole(QMainWindow):
    def __init__( self, umgr: UMAPManager, **kwargs ):
        QMainWindow.__init__(self)

        self.title = 'hyperclass'
        self.left = 10
        self.top = 10
        self.width = 1920
        self.height = 1080
        self.NFunctionButtons = 0
        self.console = None
        self.vtkFrame = None
        self.message_stack = []

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.showMessage('Ready')

        mainMenu = self.menuBar()
        mainMenu.setNativeMenuBar(False)
        fileMenu = mainMenu.addMenu('File')
        helpMenu = mainMenu.addMenu('Help')
        blocksMenu = mainMenu.addMenu('Blocks')

        exitButton = QAction(QIcon('exit24.png'), 'Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Exit application')
        exitButton.triggered.connect(self.close)
        fileMenu.addAction(exitButton)

        self.vtkFrame = VTKFrame( umgr )
        self.console = MplWidget( umgr, self, **kwargs )
        self.vtkFrame.addEventListener( self.console )

        for menuName, menuItems in self.console.menu_actions.items():
            menu = mainMenu.addMenu(menuName)
            for menuItem in menuItems:
                menuButton = QAction( menuItem[0], self )
                if menuItem[1] is not None: menuButton.setShortcut( menuItem[1] )
                if menuItem[2] is not None: menuButton.setStatusTip( menuItem[2] )
                menuButton.triggered.connect( menuItem[3] )
                menu.addAction(menuButton)

        nBlocks = umgr.tile.nBlocks
        load_menu = blocksMenu.addMenu("load")
        for ib0 in range( nBlocks[0] ):
            for ib1 in range( nBlocks[1] ):
                bname = f"[{ib0},{ib1}]"
                menuButton = QAction( bname, self)
                menuButton.setStatusTip(f"Load block at block coords {bname}")
                menuButton.triggered.connect( partial( self.setBlock, [ib0, ib1] ) )
                load_menu.addAction(menuButton)

        widget =  QWidget(self)
        self.setCentralWidget(widget)
        vlay = QVBoxLayout(widget)

        framesLayout = QHBoxLayout()
        framesLayout.addWidget( self.console, 10 )
        framesLayout.addWidget( self.vtkFrame, 6 )
        vlay.addLayout(framesLayout)

        buttonsLayout = QHBoxLayout()
        for label, callback in self.console.button_actions.items():
            pybutton = QPushButton( label, self )
            pybutton.clicked.connect( callback )
            buttonsLayout.addWidget(pybutton)
        vlay.addLayout(buttonsLayout)

    def tabShape(self) -> 'QTabWidget.TabShape':
        return super().tabShape()

    def showMessage( self, message: str ):
        self.message_stack.append( message )
        self.statusBar().showMessage(message)

    def refresh( self, message, **kwargs ):
        self.message_stack.remove( message )
        new_message = self.message_stack[-1] if len( self.message_stack ) else 'Ready'
        self.showMessage( new_message )
        self.refresh_points( **kwargs )
        self.refresh_image( **kwargs )

    def refresh_points( self, **kwargs ):
        if self.vtkFrame is not None:
            self.vtkFrame.update( **kwargs )

    def refresh_image( self, **kwargs ):
        if self.console is not None:
            self.console.mpl_update()

    def setBlock(self, block_coords: Tuple[int]):
        self.console.setBlock(block_coords)

    def show(self):
        QMainWindow.show(self)
        self.vtkFrame.Initialize()
