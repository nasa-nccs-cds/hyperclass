from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.mpl import SpectralPlotCanvas
from hyperclass.gui.directory import DirectoryWidget
from hyperclass.data.aviris.config import PreferencesDialog
from matplotlib.figure import Figure
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.data.swift.manager import dataManager
import matplotlib.pyplot as plt
from collections import Mapping
from functools import partial
from hyperclass.plot.labels import format_colors
from hyperclass.gui.points import VTKFrame
from hyperclass.plot.spectra import SpectralPlot
from typing import List, Union, Tuple
import xarray as xa
import os


class SwiftConsole(QMainWindow):
    def __init__( self, classes: List[Tuple[str,Union[str,List[float]]]], **kwargs ):
        QMainWindow.__init__(self)
        self.umgr = UMAPManager( format_colors(classes) )
        self.title = 'swiftclass'
        self.left = 10
        self.top = 10
        self.width = 1920
        self.height = 1080
        self.NFunctionButtons = 0
        self.directoryConsole = None
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

        self.load_dataset = fileMenu.addMenu("Load Dataset")

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
        self.directoryConsole = DirectoryWidget( self, **kwargs )
        self.vtkFrame.addEventListener(self.directoryConsole)
        self.spectral_plot = SpectralPlot()
        self.spectralPlot = SpectralPlotCanvas( widget, self.spectral_plot )

        consoleLayout.addWidget(self.directoryConsole)
        vizTabs = QTabWidget()
        vizTabs.addTab(  self.vtkFrame, "Embedding" )

        vizLayout.addWidget( vizTabs, 15 )
        vizLayout.addWidget( self.spectralPlot, 5 )
        self.populate_load_menues()

    def addMenues(self, parent_menu: Union[QMenu,QMenuBar], menuSpec: Mapping ) :
        for menuName, menuItems in menuSpec.items():
            menu = parent_menu.addMenu(menuName)
            for menuItem in menuItems:
                if isinstance(menuItem, Mapping):   self.addMenues( menu, menuItem )
                else:                               self.addMenuAction( menu, menuItem )

    def populate_load_menues(self):
        self.populate_dataset_load_menu()

    def populate_dataset_load_menu(self):
        directory = dataManager.config.value('data/cache')
        for file in os.listdir(directory):
            if file.endswith(".nc"):
                dsid = file[:-3]
                menuButton = QAction( dsid, self )
                menuButton.setStatusTip(f"Load Dataset {dsid}")
                menuButton.triggered.connect( partial(self.runLoadDataset, dsid ))
                self.load_dataset.addAction(menuButton)

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

    def runLoadDataset( self, dsid: str, **kwargs ):
        taskRunner.start(Task(self.loadDataset, dsid, **kwargs), f"Load Dataset {dsid}")

    def loadDataset( self, dsid: str, *args, **kwargs ):
        data_dir = dataManager.config.value('data/cache')
        data_file = os.path.join( data_dir, dsid + ".nc" )
        dataset: xa.Dataset = xa.open_dataset( data_file )
        print( f"Opened Dataset {dsid} from file {data_file}")

    def loadCurrentDataset(self):
        dsid = dataManager.config.value("dataset/id",None)
        if dsid is not None: self.loadDataset( dsid )

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
        else:
            print( f"Warning, unknown task type: {task_context}, doing nothing for refresh.")

    def refresh_points( self, **kwargs ):
        if self.vtkFrame is not None:
            self.vtkFrame.update( **kwargs )

    def refresh_images( self, **kwargs ):
        try: self.directoryConsole.mpl_update()
        except AttributeError: pass
        try: self.spectralPlot.mpl_update()
        except AttributeError: pass

    def show(self):
        QMainWindow.show(self)
        self.vtkFrame.Initialize()
        self.loadCurrentDataset()


