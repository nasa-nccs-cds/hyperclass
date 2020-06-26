from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QKeyEvent

from hyperclass.data.events import dataEventHandler
from hyperclass.gui.application import HCMainWindow
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.directory import DirectoryWidget
from matplotlib.figure import Figure
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.data.swift.manager import dataManager
from collections import Mapping
from functools import partial
from hyperclass.plot.labels import format_colors
from hyperclass.plot.spectra import SpectralPlot
from typing import List, Union, Tuple, Dict
import xarray as xa
import os, abc

class SwiftMainWindow(HCMainWindow):

    def __init__( self, parent, title: str ):
        HCMainWindow.__init__( self, parent, title )

    def addMenuItems(self):
        self.load_dataset = self.fileMenu.addMenu("Load Dataset")

    def getPreferencesDialog(self):
        from hyperclass.data.aviris.config import PreferencesDialog
        return PreferencesDialog()

class SwiftConsole(EventClient):
    def __init__( self, classes: List[Tuple[str,Union[str,List[float]]]], **kwargs ):
        self.gui = SwiftMainWindow(None, 'swiftclass')
        dataEventHandler.config( subsample=kwargs.pop('subsample')  )
        self.umgr = UMAPManager( format_colors(classes), **kwargs )

        self.left = 10
        self.top = 10
        self.width = 1920
        self.height = 1080
        self.NFunctionButtons = 0
        self.directoryConsole = None
        self.message_stack = []
        self.newfig : Figure = None
        self.fileChanged = True
        self.initSettings(kwargs)
        self.activate_event_listening()

        self.gui.setGeometry(self.left, self.top, self.width, self.height)
        self.showMessage('Ready')

        widget =  QWidget( self.gui )
        self.gui.setCentralWidget(widget)
        vlay = QVBoxLayout(widget)

        framesLayout = QHBoxLayout()
        vlay.addLayout(framesLayout)

        buttonsLayout = QHBoxLayout()
        vlay.addLayout(buttonsLayout)

        consoleLayout = QVBoxLayout()
        framesLayout.addLayout( consoleLayout, 10 )
        vizLayout = QVBoxLayout()
        framesLayout.addLayout( vizLayout, 8 )

        self.directoryConsole = DirectoryWidget( self.gui, **kwargs )
        self.spectral_plot = SpectralPlot()

        consoleLayout.addWidget(self.directoryConsole, 10 )
        consoleLayout.addWidget( self.spectral_plot.gui(widget), 6 )

        vizTabs = QTabWidget()
        vizTabs.addTab(  self.umgr.gui(), "Embedding" )
        vizLayout.addWidget( vizTabs )

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
                menuButton = QAction( dsid, self.gui )
                menuButton.setStatusTip(f"Load Dataset {dsid}")
                menuButton.triggered.connect( partial(self.runLoadDataset, dsid ))
                self.gui.load_dataset.addAction(menuButton)

    def addMenuAction(self, parent_menu: QMenu, menuItem: List ):
        menuButton = QAction(menuItem[0], self.gui )
        if menuItem[1] is not None: menuButton.setShortcut(menuItem[1])
        if menuItem[2] is not None: menuButton.setStatusTip(menuItem[2])
        menuButton.triggered.connect(menuItem[3])
        parent_menu.addAction(menuButton)

    def initSettings(self, kwargs ):
        valid_bands = kwargs.pop('valid_bands', None )
        if valid_bands: dataManager.config.setValue( 'data/valid_bands', valid_bands )
        self.tabs = kwargs.pop('tabs',{})
        self.settings = dataManager.config

    def runLoadDataset( self, dsid: str, **kwargs ):
        taskRunner.start( Task( f"Load Dataset {dsid}", self.loadDataset, dsid, **kwargs) )

    def loadDataset( self, dsid: str, *args, **kwargs ) -> xa.Dataset:
        data_dir = dataManager.config.value('data/cache')
        data_file = os.path.join( data_dir, dsid + ".nc" )
        dataset: xa.Dataset = xa.open_dataset( data_file )
        print( f"Opened Dataset {dsid} from file {data_file}")
        dataset.attrs['dsid'] = dsid
        dataset.attrs['type'] = 'spectra'
        return dataset

    def loadCurrentDataset(self):
        dsid = dataManager.config.value("dataset/id",None)
        if dsid is not None: self.loadDataset( dsid )

    def tabShape(self) -> QTabWidget.TabShape:
        return self.gui.tabShape()

    def showMessage( self, message: str ):
        self.message_stack.append( message )
        self.gui.statusBar().showMessage(message)

    def refresh( self, message,  **kwargs ):
        try: self.message_stack.remove( message )
        except ValueError:
            print( f"Atempt to remove unrecognized message: {message}, msgs = {self.message_stack}")
        new_message = self.message_stack[-1] if len( self.message_stack ) else 'Ready'
        self.showMessage( new_message )
        self.umgr.update()
        self.refresh_images( **kwargs )

    def refresh_images( self, **kwargs ):
        try: self.directoryConsole.mpl_update()
        except AttributeError: pass
        try: self.spectral_plot.update()
        except AttributeError: pass

    def show(self):
        self.gui.show()
        self.gui.activateWindow()
        self.gui.raise_()
        self.submitEvent( dict( event="show" ), EventMode.Gui )
        self.loadCurrentDataset()

    def processEvent(self, event: Dict ):
        if event.get('event') == 'task':
            if event.get('type') == 'completed':
                print( "SwiftConsole: refreshing panels on task completion")
                self.refresh( event.get('label') )



