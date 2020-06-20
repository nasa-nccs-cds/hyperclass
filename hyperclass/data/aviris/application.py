from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.mpl import MplWidget, SpectralPlotCanvas, SatellitePlotCanvas, ReferenceImageCanvas
from hyperclass.data.aviris.config import PreferencesDialog
from matplotlib.figure import Figure
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.data.aviris.manager import dataManager
import matplotlib.pyplot as plt
from collections import Mapping
from functools import partial
from hyperclass.plot.labels import format_colors
from hyperclass.gui.points import VTKFrame, MixingFrame
from typing import List, Union, Tuple


class HyperclassConsole(QMainWindow):
    def __init__( self, classes: List[Tuple[str,Union[str,List[float]]]], **kwargs ):
        QMainWindow.__init__(self)
        self.umgr = UMAPManager( format_colors(classes) )
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
        self.fileChanged = True
        self.initSettings(kwargs)

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
        self.satelliteCanvas.addEventListener(self.labelingConsole)
        self.labelingConsole.addNavigationListener( self.satelliteCanvas )
        self.addMenues(mainMenu, self.labelingConsole.menu_actions)
        self.mixingFrame = MixingFrame( self.umgr )

        consoleLayout.addWidget(self.labelingConsole)
        vizTabs = QTabWidget()
        vizTabs.addTab(  self.vtkFrame, "Embedding" )
#        vizTabs.addTab( self.mixingFrame, "Mixing")
        vizTabs.addTab( self.satelliteCanvas, "Satellite")
        for label, image_spec in self.tabs.items():
            if image_spec.get( 'type', "none" ) == "reference":
                refCanvas = ReferenceImageCanvas(widget, image_spec)
                refCanvas.addEventListener(self.labelingConsole)
                vizTabs.addTab( refCanvas, label )
        vizLayout.addWidget( vizTabs, 15 )
        vizLayout.addWidget( self.spectralPlot, 5 )

        for label, callback in self.labelingConsole.button_actions.items():
            pybutton = QPushButton( label, self )
            pybutton.clicked.connect( callback )
            buttonsLayout.addWidget(pybutton)

    def loadCurrentBlock(self, **kwargs):
        filename = dataManager.config.value("data/init/file", None)
        if filename is not None:
            buttonReply = QMessageBox.question( self, 'Hyperclass Initialization', "Load current block?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes )
            if buttonReply == QMessageBox.Yes:
                taskRunner.start(Task(self.openFile, filename, **kwargs), f"Load Data File")

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
        nBlocks = dataManager.config.value("block/array_shape", [ 1, 1 ], type=int )
        block_indices = dataManager.config.value("block/indices", [-1, -1], type=int)
        for action in self.load_block.actions():
            self.load_block.removeAction( action)

        for ib0 in range( nBlocks[0] ):
            for ib1 in range( nBlocks[1] ):
                if ( [ib0, ib1] != block_indices ):
                    bname = f"[{ib0},{ib1}]"
                    menuButton = QAction( bname, self.load_block )
                    menuButton.setStatusTip(f"Load block at block coords {bname}")
                    menuButton.triggered.connect( partial( self.runSetBlock, [ib0, ib1] ) )
                    self.load_block.addAction(menuButton)

    def populate_tile_load_menu(self):
        nTiles = dataManager.config.value("tile/array_shape", [1, 1], type=int)
        tile_indices = dataManager.config.value("tile/indices", [-1, -1], type=int)
        for action in self.load_tile.actions():
            self.load_tile.removeAction( action)

        for it0 in range( nTiles[0] ):
            for it1 in range( nTiles[1] ):
                if ( [it0, it1] != tile_indices ):
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

    def initSettings(self, kwargs ):
        valid_bands = kwargs.pop('valid_bands', None )
        if valid_bands: dataManager.config.setValue( 'data/valid_bands', valid_bands )
        self.tabs = kwargs.pop('tabs',{})
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
        self.setBlock( block_indices, **kwargs )
        self.fileChanged = True

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
        if self.fileChanged:
            self.populate_load_menues()
            self.fileChanged = False

    def setTile(self, tile_coords: Tuple[int], **kwargs ):
        current_tile_coords = dataManager.config.value( "tile/indices", None )
        if current_tile_coords is None or current_tile_coords != tile_coords:
            dataManager.config.setValue( "tile/indices", tile_coords )
            filename = dataManager.config.value("data/init/file", None)
            if filename is not None: taskRunner.start(Task(self.openFile, filename, **kwargs), f"Load New Tile")

    def setBlock(self, block_coords: Tuple[int], **kwargs ):
        block = self.labelingConsole.setBlock( block_coords, **kwargs )
        self.satelliteCanvas.setBlock(block)

    def show(self):
        QMainWindow.show(self)
        self.vtkFrame.Initialize()
        self.loadCurrentBlock()


