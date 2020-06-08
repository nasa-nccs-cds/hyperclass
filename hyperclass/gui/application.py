from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QCoreApplication, QSettings
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.mpl import MplWidget, SpectralPlotCanvas, SatellitePlotCanvas
from .config import PreferencesDialog
from matplotlib.figure import Figure
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.data.aviris.manager import dataManager
import matplotlib.pyplot as plt
from collections import Mapping
from functools import partial
from hyperclass.data.aviris.tile import Tile, Block
from hyperclass.gui.points import VTKFrame, MixingFrame
from typing import List, Union, Dict, Callable, Tuple, Optional

class HyperclassConsole(QMainWindow):
    def __init__( self, classes: List[ Tuple[str,List[float]]], **kwargs ):
        QMainWindow.__init__(self)
        self.umgr = UMAPManager(classes)
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
        self.initSettings()

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.showMessage('Ready')

        mainMenu = self.menuBar()
        mainMenu.setNativeMenuBar(False)
        fileMenu = mainMenu.addMenu('File')
        helpMenu = mainMenu.addMenu('Help')
        tilesMenu: QMenu = mainMenu.addMenu('Tiles')
        self.load_tile = tilesMenu.addMenu("load tile")
        self.load_block = tilesMenu.addMenu("load block")

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

        self.vtkFrame = VTKFrame( self.umgr )
        self.labelingConsole = MplWidget( self.umgr, self, **kwargs)
        self.vtkFrame.addEventListener(self.labelingConsole)
        self.spectralPlot = SpectralPlotCanvas( widget, self.labelingConsole.spectral_plot )
        self.satelliteCanvas = SatellitePlotCanvas( widget, self.labelingConsole.toolbar, self.labelingConsole.getBlock() )
        self.labelingConsole.addNavigationListener( self.satelliteCanvas )
        self.addMenues(mainMenu, self.labelingConsole.menu_actions)
        self.mixingFrame = MixingFrame( self.umgr )

        consoleLayout.addWidget(self.labelingConsole)
        vizTabs = QTabWidget()
        vizTabs.addTab(  self.vtkFrame, "Embedding" )
#        vizTabs.addTab( self.mixingFrame, "Mixing")
        vizTabs.addTab( self.satelliteCanvas, "Satellite")
        vizLayout.addWidget( vizTabs, 15 )
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

    def populate_load_menues(self):
        self.populate_block_load_menu()
        self.populate_tile_load_menu()

    def populate_block_load_menu(self):
        tile = self.labelingConsole.getTile()
        nBlocks = tile.nBlocks
        for action in self.load_block.actions():
            self.load_block.removeAction( action)

        for ib0 in range( nBlocks[0] ):
            for ib1 in range( nBlocks[1] ):
                bname = f"[{ib0},{ib1}]"
                menuButton = QAction( bname, self)
                menuButton.setStatusTip(f"Load block at block coords {bname}")
                menuButton.triggered.connect( partial( self.runSetBlock, [ib0, ib1] ) )
                self.load_block.addAction(menuButton)

    def populate_tile_load_menu(self):
        nTiles = dataManager.config.value( 'tile/dims', [0,0], type=int )
        for action in self.load_tile.actions():
            self.load_tile.removeAction( action)

        for it0 in range( nTiles[0] ):
            for it1 in range( nTiles[1] ):
                tname = f"[{it0},{it1}]"
                menuButton = QAction( tname, self)
                menuButton.setStatusTip(f"Load tile at index {tname}")
                menuButton.triggered.connect( partial( self.runSetTile, [it0, it1] ) )
                self.load_tile.addAction(menuButton)

    def runSetBlock( self, coords, **kwargs ):
        taskRunner.start( Task(self.setBlock, coords,  **kwargs ), "Loading block" )

    def runSetTile( self, coords, **kwargs ):
        taskRunner.start( Task(self.setTile, coords,  **kwargs ), "Loading tile" )

    def addMenuAction(self, parent_menu: QMenu, menuItem: List ):
        menuButton = QAction(menuItem[0], self)
        if menuItem[1] is not None: menuButton.setShortcut(menuItem[1])
        if menuItem[2] is not None: menuButton.setStatusTip(menuItem[2])
        menuButton.triggered.connect(menuItem[3])
        parent_menu.addAction(menuButton)

    def initSettings(self):
        self.settings = dataManager.config

    def setPreferences(self):
        preferences =  PreferencesDialog()
        preferences.show()

    def selectFile(self, *args, **kwargs):
        data_dir = dataManager.config.value('data/dir')
        dialog = QFileDialog( self, "Select File", data_dir )
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
        if (dialog.exec()):
            fileNames = dialog.selectedFiles()
            taskRunner.start(Task(self.openFile, fileNames[0], **kwargs), f"Load Data File")
        dialog.close()

    def openFile(self, fileName: str, **kwargs ):
        print( f"Opening file: {fileName}")
        dataManager.setImageName( fileName )
        block_indices = dataManager.config.value( 'block/indices', [0,0], type=int )
        self.setBlock( block_indices, refresh_tile=True, **kwargs )
        self.populate_load_menues()

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
            self.refresh_images( **kwargs )
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

    def refresh_images( self, **kwargs ):
        try: self.labelingConsole.mpl_update()
        except AttributeError: pass
        try: self.spectralPlot.mpl_update()
        except AttributeError: pass
        try: self.satelliteCanvas.mpl_update()
        except AttributeError: pass

    def setTile(self, tile_coords: Tuple[int], **kwargs ):
        current_tile_coords = dataManager.config.value( "tile/indices", None )
        if current_tile_coords is None or current_tile_coords != tile_coords:
            dataManager.config.setValue( "tile/indices", tile_coords )
            filename = dataManager.config.value("data/init/file", None)
            if filename is not None: taskRunner.start(Task(self.openFile, filename, **kwargs), f"Load New Tile")

    def setBlock(self, block_coords: Tuple[int], **kwargs ):
        block = self.labelingConsole.setBlock( block_coords, **kwargs )
        self.populate_block_load_menu()
        self.satelliteCanvas.setBlock(block)

    def show(self):
        QMainWindow.show(self)
        self.vtkFrame.Initialize()
