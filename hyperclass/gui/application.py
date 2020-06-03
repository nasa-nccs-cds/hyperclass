from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton, QMenu, QMenuBar
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.mpl import MplWidget, SpectralPlotCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from collections import Mapping
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
        self.labelingConsole = None
        self.vtkFrame = None
        self.message_stack = []
        self.newfig : Figure = None

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

        widget =  QWidget(self)
        self.setCentralWidget(widget)
        vlay = QVBoxLayout(widget)

        self.vtkFrame = VTKFrame( umgr )
        self.labelingConsole = MplWidget(umgr, self, **kwargs)
        self.vtkFrame.addEventListener(self.labelingConsole)
        self.spectralPlot = SpectralPlotCanvas(widget, self.labelingConsole.spectral_plot)
        self.addMenues(mainMenu, self.labelingConsole.menu_actions)

        nBlocks = umgr.tile.nBlocks
        load_menu = blocksMenu.addMenu("load")
        for ib0 in range( nBlocks[0] ):
            for ib1 in range( nBlocks[1] ):
                bname = f"[{ib0},{ib1}]"
                menuButton = QAction( bname, self)
                menuButton.setStatusTip(f"Load block at block coords {bname}")
                menuButton.triggered.connect( partial( self.setBlock, [ib0, ib1] ) )
                load_menu.addAction(menuButton)

        framesLayout = QHBoxLayout()
        vlay.addLayout(framesLayout)

        buttonsLayout = QHBoxLayout()
        vlay.addLayout(buttonsLayout)

        consoleLayout = QVBoxLayout()
        framesLayout.addLayout(consoleLayout, 10)
        vizLayout = QVBoxLayout()
        framesLayout.addLayout(vizLayout, 7)

        consoleLayout.addWidget(self.labelingConsole)

        vizLayout.addWidget( self.vtkFrame, 15 )
        vizLayout.addWidget( self.spectralPlot, 5 )

        for label, callback in self.labelingConsole.button_actions.items():
            pybutton = QPushButton( label, self )
            pybutton.clicked.connect( callback )
            buttonsLayout.addWidget(pybutton)

    def addMenues(self, parent_menu: Union[QMenu,QMenuBar], menuSpec: Mapping ) :
        for menuName, menuItems in menuSpec.items():
            menu = parent_menu.addMenu(menuName)
            for menuItem in menuItems:
                if isinstance(menuItem, Mapping):   self.addMenues( menu, menuItem )
                else:                               self.addMenuAction( menu, menuItem )

    def addMenuAction(self, parent_menu: QMenu, menuItem: List ):
        menuButton = QAction(menuItem[0], self)
        if menuItem[1] is not None: menuButton.setShortcut(menuItem[1])
        if menuItem[2] is not None: menuButton.setStatusTip(menuItem[2])
        menuButton.triggered.connect(menuItem[3])
        parent_menu.addAction(menuButton)

    def tabShape(self) -> 'QTabWidget.TabShape':
        return super().tabShape()

    def showMessage( self, message: str ):
        self.message_stack.append( message )
        self.statusBar().showMessage(message)

    def refresh( self, message, task_context: str,  **kwargs ):
        self.message_stack.remove( message )
        new_message = self.message_stack[-1] if len( self.message_stack ) else 'Ready'
        self.showMessage( new_message )
        if task_context == "console":
            self.refresh_points( **kwargs )
            self.refresh_image( **kwargs )
        elif task_context == "newfig":
            self.newfig, ax = plt.subplots(1, 1)
            ax.imshow(self.labelingConsole.getNewImage(), extent=self.labelingConsole.extent(), alpha=1.0)
            plt.show( block = False )
        else:
            print( f"Warning, unknown task type: {task_context}, doing nothing for refresh.")

    def refresh_points( self, **kwargs ):
        if self.vtkFrame is not None:
            self.vtkFrame.update( **kwargs )

    def refresh_image( self, **kwargs ):
        try: self.labelingConsole.mpl_update()
        except AttributeError: pass
        try: self.spectralPlot.mpl_update()
        except AttributeError: pass

    def setBlock(self, block_coords: Tuple[int]):
        self.labelingConsole.setBlock(block_coords)

    def show(self):
        QMainWindow.show(self)
        self.vtkFrame.Initialize()
