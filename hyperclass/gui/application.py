from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QCoreApplication, QSettings
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.mpl import MplWidget, SpectralPlotCanvas, SatellitePlotCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from collections import Mapping
from functools import partial
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.gui.points import VTKFrame, MixingFrame
from typing import List, Union, Dict, Callable, Tuple, Optional

QCoreApplication.setOrganizationName("ilab")
QCoreApplication.setOrganizationDomain("nccs.nasa.gov")
QCoreApplication.setApplicationName("hyperclass")

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
        self.umgr = umgr
        self.initSettings()

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.showMessage('Ready')

        mainMenu = self.menuBar()
        mainMenu.setNativeMenuBar(False)
        fileMenu = mainMenu.addMenu('File')
        helpMenu = mainMenu.addMenu('Help')
        blocksMenu = mainMenu.addMenu('Blocks')

        openButton = QAction( 'Open', self )
        openButton.setShortcut('Ctrl+O')
        openButton.setStatusTip('Open file')
        openButton.triggered.connect(self.selectFile)
        fileMenu.addAction(openButton)

        prefButton = QAction( 'Preferences', self)
        prefButton.setShortcut('Ctrl+P')
        prefButton.setStatusTip('Set application configuration parameters')
        prefButton.triggered.connect( self.setPreferences )
        fileMenu.addAction(prefButton)

        exitButton = QAction(QIcon('exit24.png'), 'Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Exit application')
        exitButton.triggered.connect(self.close)
        fileMenu.addAction(exitButton)

        widget =  QWidget(self)
        self.setCentralWidget(widget)
        vlay = QVBoxLayout(widget)

        framesLayout = QHBoxLayout()
        vlay.addLayout(framesLayout)

        buttonsLayout = QHBoxLayout()
        vlay.addLayout(buttonsLayout)

        consoleLayout = QVBoxLayout()
        framesLayout.addLayout(consoleLayout, 10)
        vizLayout = QVBoxLayout()
        framesLayout.addLayout(vizLayout, 7)

        self.vtkFrame = VTKFrame( umgr )
        self.labelingConsole = MplWidget(umgr, self, **kwargs)
        self.vtkFrame.addEventListener(self.labelingConsole)
        self.spectralPlot = SpectralPlotCanvas( widget, self.labelingConsole.spectral_plot )
        self.satelliteCanvas = SatellitePlotCanvas( widget, self.labelingConsole.toolbar, self.labelingConsole.getBlock() )
        self.labelingConsole.addNavigationListener( self.satelliteCanvas )
        self.addMenues(mainMenu, self.labelingConsole.menu_actions)
        self.mixingFrame = MixingFrame( umgr )

        consoleLayout.addWidget(self.labelingConsole)
        vizTabs = QTabWidget()
        vizTabs.addTab(  self.vtkFrame, "Embedding" )
#        vizTabs.addTab( self.mixingFrame, "Mixing")
        vizTabs.addTab( self.satelliteCanvas, "Satellite")
        vizLayout.addWidget( vizTabs, 15 )
        vizLayout.addWidget( self.spectralPlot, 5 )

        nBlocks = umgr.tile.nBlocks
        load_menu = blocksMenu.addMenu("load")
        for ib0 in range( nBlocks[0] ):
            for ib1 in range( nBlocks[1] ):
                bname = f"[{ib0},{ib1}]"
                menuButton = QAction( bname, self)
                menuButton.setStatusTip(f"Load block at block coords {bname}")
                menuButton.triggered.connect( partial( self.setBlock, [ib0, ib1] ) )
                load_menu.addAction(menuButton)

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

    def initSettings(self):
        self.settings = QSettings()

    def setPreferences(self):
        pass

    def selectFile(self, *args, **kwargs):
        data_dir = self.umgr.tile.dm.config['data_dir']
        fileName = QFileDialog.getOpenFileName( self, "Open File", data_dir )
        self.openFile( fileName )

    def openFile(self, fileName: str ):
        print( f"Opening file: {fileName}")

    def tabShape(self) -> QTabWidget.TabShape:
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
        if self.mixingFrame is not None:
            self.mixingFrame.update(**kwargs)

    def refresh_image( self, **kwargs ):
        try: self.labelingConsole.mpl_update()
        except AttributeError: pass
        try: self.spectralPlot.mpl_update()
        except AttributeError: pass

    def setBlock(self, block_coords: Tuple[int]):
        block = self.labelingConsole.setBlock(block_coords)
        self.satelliteCanvas.setBlock(block)

    def show(self):
        QMainWindow.show(self)
        self.vtkFrame.Initialize()
