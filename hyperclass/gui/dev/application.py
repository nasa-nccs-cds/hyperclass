from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from hyperclass.learn.manager import learningManager
from hyperclass.umap.manager import umapManager
from hyperclass.gui.mpl import LabelingWidget, SatellitePlotCanvas, ReferenceImageCanvas, satellitePlotManager
from hyperclass.plot.spectra import SpectralPlot
from hyperclass.data.spatial.tile import Tile, Block
from hyperclass.gui.config import PreferencesDialog
from matplotlib.figure import Figure
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.gui.labels import labelsManager
from hyperclass.data.manager import dataManager
import matplotlib.pyplot as plt
from collections import Mapping
from functools import partial
from hyperclass.gui.application import HCMainWindow
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.events import EventClient, EventMode
from typing import List, Union, Tuple, Dict

class DevelopmentConsole(HCMainWindow):
    update_block_load_menu = pyqtSignal()
    update_tile_load_menu = pyqtSignal()

    def __init__( self, **kwargs ):
        HCMainWindow.__init__(self)
        dataEventHandler.config( subsample=kwargs.pop('subsample', None)  )
        self.title = 'hyperclass'
        self.left = 10
        self.top = 10
        self.width = 1920
        self.height = 1080
        self.NFunctionButtons = 0
        self.nSpectra = 8
        self.spectral_plots = []
        self.labelingConsole = None
        self.vtkFrame = None
        self.message_stack = []
        self.newfig : Figure = None
        self.fileChanged = True
        self.initSettings(kwargs)
        self.activate_event_listening()

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.showMessage('Ready')

        widget =  QWidget(self)
        self.setCentralWidget(widget)
        vlay = QVBoxLayout(widget)

        framesLayout = QHBoxLayout()
        vlay.addLayout(framesLayout)

        consoleLayout = QVBoxLayout()
        framesLayout.addLayout(consoleLayout, 10)
        vizLayout = QVBoxLayout()
        framesLayout.addLayout(vizLayout, 7)

        self.labelingConsole = LabelingWidget(self, **kwargs)
        self.satelliteCanvas = satellitePlotManager.gui()
        self.satelliteCanvas.setBlock( self.labelingConsole.getBlock() )
        self.addMenues( self.mainMenu, self.labelingConsole.menu_actions )
        self.addMenues( self.mainMenu, umapManager.menu_actions )
#        self.mixingFrame = MixingFrame( umapManager )
        self.labelsConsole = labelsManager.gui( learning=True )

        directoryLayout = QHBoxLayout()
        directoryLayout.addWidget( self.labelingConsole, 10 )
        directoryLayout.addWidget(self.labelsConsole, 2)
        consoleLayout.addLayout(directoryLayout, 20 )

        self.spectraTabs = QTabWidget()
        for iS in range( self.nSpectra ):
            spectral_plot = SpectralPlot( iS == 0 )
            self.spectral_plots.append(spectral_plot)
            tabId = "Spectra" if iS == 0 else str(iS)
            self.spectraTabs.addTab( spectral_plot.gui(widget), tabId )
        self.spectraTabs.currentChanged.connect( self.activate_spectral_plot )
        self.spectraTabs.setTabEnabled( 0, True )
        consoleLayout.addWidget( self.spectraTabs, 6 )

        vizTabs = QTabWidget()
        vizTabs.addTab(  umapManager.gui(), "Embedding" )
#        vizTabs.addTab( self.mixingFrame, "Mixing")
        vizTabs.addTab( self.satelliteCanvas, "Satellite")
        for label, image_spec in self.tabs.items():
            if image_spec.get( 'type', "none" ) == "reference":
                refCanvas = ReferenceImageCanvas(widget, image_spec)
                vizTabs.addTab( refCanvas, label )
        vizLayout.addWidget( vizTabs )

    def addMenuItems(self):
        tilesMenu: QMenu = self.mainMenu.addMenu('Tiles')
        self.load_tile = tilesMenu.addMenu("load tile")
        self.load_block = tilesMenu.addMenu("load block")
        self.update_tile_load_menu.connect(self.populate_tile_load_menu)
        self.update_block_load_menu.connect(self.populate_block_load_menu)

        openButton = QAction( 'Open', self )
        openButton.setShortcut('Ctrl+O')
        openButton.setStatusTip('Open file')
        openButton.triggered.connect(self.selectFile)
        self.datasetMenu.addAction(openButton)

    def activate_spectral_plot( self, index: int ):
        for iS, plot in enumerate(self.spectral_plots):
            plot.activate( iS == index )

    def loadCurrentBlock(self, **kwargs):
        filename = dataManager.config.value("data/init/file", None)
        if filename is not None:
            buttonReply = QMessageBox.question( self, 'Hyperclass Initialization', "Load current block?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes )
            if buttonReply == QMessageBox.Yes:
                taskRunner.start(Task(f"load dataset", self.openFile, filename, **kwargs))

    def addMenues(self, parent_menu: Union[QMenu,QMenuBar], menuSpec: Mapping ) :
        for menuName, menuItems in menuSpec.items():
            menu = parent_menu.addMenu(menuName)
            for menuItem in menuItems:
                if isinstance(menuItem, Mapping):   self.addMenues( menu, menuItem )
                else:                               self.addMenuAction( menu, menuItem )

    def populate_load_menues(self):
        self.populate_block_load_menu()
        self.populate_tile_load_menu()

    def processEvent(self, event: Dict ):
        if event.get('event') == 'gui':
            if event.get('type') == 'update':
                self.refresh_points( **event )
                self.refresh_images( **event )
            if event.get('type') == 'reload':
                filename = dataManager.config.value("data/init/file", None)
                if filename is not None:
                    taskRunner.start( Task(f"load dataset", self.openFile, filename, reset=True ) )

    @pyqtSlot()
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

    @pyqtSlot()
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
        taskRunner.start( Task("Loading block", self.setBlock, coords,  **kwargs ) )

    def runSetTile( self, coords, **kwargs ):
        taskRunner.start( Task("Loading tile", self.setTile, coords,  **kwargs ) )

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
        preferences =  PreferencesDialog( self, PreferencesDialog.RUNTIME, spatial=True, dev=True )
        preferences.exec_()

    def selectFile(self, *args, **kwargs):
        data_dir = dataManager.config.value('data/dir')
        dialog = QFileDialog( self, "Select File", data_dir )
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
        if (dialog.exec()):
            fileNames = dialog.selectedFiles()
            taskRunner.start(Task(f"load dataset", self.openFile, fileNames[0], **kwargs))
        dialog.close()

    def openFile(self, fileName: str, **kwargs ) -> Block:
        print( f"Opening file: {fileName}")
        dataManager.spatial.setImageName( fileName )
        block_indices = dataManager.config.value( 'block/indices', [0,0], type=int )
        result = self.setBlock( block_indices, **kwargs )
        self.fileChanged = True
        event = dict( event="gui", type="update" )
        self.submitEvent(event, EventMode.Gui)
        return result

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
        # if self.mixingFrame is not None:
        #     self.mixingFrame.update(**kwargs)

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
            print( f"Setting tile indices = {tile_coords}" )
            dataManager.config.setValue( "tile/indices", tile_coords )
            filename = dataManager.config.value("data/init/file", None)
            if filename is not None: taskRunner.start(Task(f"Load New Tile", self.openFile, filename, **kwargs) )
            self.update_tile_load_menu.emit()

    def setBlock(self, block_coords: Tuple[int], **kwargs ) -> Block:
        dataManager.config.setValue( 'block/indices', block_coords )
        block = self.labelingConsole.setBlock( block_coords, **kwargs )
        self.satelliteCanvas.setBlock(block)
        self.update_block_load_menu.emit()
        return block

    def show(self):
        QMainWindow.show(self)
        self.loadCurrentBlock()


