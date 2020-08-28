from PyQt5.QtWidgets import *
from PyQt5.QtCore import QObject
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.application import HCMainWindow
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.umap.manager import umapManager
from hyperclass.gui.directory import DirectoryWidget
from collections import OrderedDict
from matplotlib.figure import Figure
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.data.manager import dataManager
from collections import Mapping
from functools import partial
from hyperclass.gui.labels import labelsManager
from hyperclass.plot.spectra import SpectralPlot
from typing import List, Union, Dict
import xarray as xa
import os


class UnstructuredAppMainWindow(HCMainWindow):

    def __init__( self, parent ):
        HCMainWindow.__init__( self, parent )

    def addMenuItems( self  ):

        menuButton = QAction( "find: ", self )
        menuButton.setStatusTip(f"Find row in table")
        menuButton.triggered.connect( self.findTableRow )
        self.editMenu.addAction( menuButton )

        menuButton = QAction( "select (regex): ", self )
        menuButton.setStatusTip(f"Select rows in table")
        menuButton.triggered.connect( self.selectTableRows )
        self.editMenu.addAction( menuButton )

        self.loadDatasetMenu = self.datasetMenu.addMenu('Load')

    def findTableRow(self):
        print("find")
        # text: qt.QString = QInputDialog::getText(this, tr("QInputDialog::getText()"),
        #                              tr("User name:"), QLineEdit::Normal,
        #                                                           QDir::home().dirName(), & ok);
        # if (ok & & !text.isEmpty())
        # textLabel->setText(text);

    def selectTableRows(self):
        print( "select" )



    def getPreferencesDialog(self):
        from hyperclass.config.inputs import RuntimeDialog
        return RuntimeDialog(self)

class UnstructuredAppConsole(QObject, EventClient):
    def __init__( self,  **kwargs ):
        QObject.__init__(self)
        dataEventHandler.config( subsample=kwargs.pop('subsample', None)  )
        self.gui = UnstructuredAppMainWindow( None )

        self.left = 10
        self.top = 10
        self.width = 1920
        self.height = 1080
        self.nSpectra = 5
        self.spectral_plots = []
        self.NFunctionButtons = 0
        self.directoryConsole = None
        self.message_stack = []
        self.newfig : Figure = None
        self.fileChanged = True
        self.initSettings(kwargs)
        self.activate_event_listening()

        self.gui.setGeometry(self.left, self.top, self.width, self.height)
        self.addMenues( self.gui.mainMenu, umapManager.menu_actions )
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

        directoryLayout = QHBoxLayout()
        self.directoryConsole = DirectoryWidget('catalog')
        self.labelsConsole = labelsManager.gui( learning=False )

        self.directoryTabs = QTabWidget()
        self.directoryTabs.addTab(  self.directoryConsole, "Catalog" )
        self.classDirecories = OrderedDict( { "Catalog": self.directoryConsole } )
        for label in labelsManager.labels[1:]:
            classDirectoryConsole = DirectoryWidget(label)
            self.classDirecories[ label ] = classDirectoryConsole
            self.directoryTabs.addTab( classDirectoryConsole, label )
        self.directoryTabs.currentChanged.connect( lambda index: self.activate_class_directory( index ) )
        self.activate_class_directory( self.directoryTabs.currentIndex() )

        directoryLayout.addWidget( self.directoryTabs, 10 )
        directoryLayout.addWidget(self.labelsConsole, 2)
        consoleLayout.addLayout(directoryLayout, 10 )

        self.spectraTabs = QTabWidget()
        for iS in range( self.nSpectra ):
            spectral_plot = SpectralPlot( iS == 0 )
            self.spectral_plots.append(spectral_plot)
            tabId = "Spectra" if iS == 0 else str(iS)
            self.spectraTabs.addTab( spectral_plot.gui(widget), tabId )
        self.spectraTabs.currentChanged.connect( self.activate_spectral_plot )
        self.spectraTabs.setTabEnabled( 0, True )
        consoleLayout.addWidget( self.spectraTabs, 6 )

        self.vizTabs = QTabWidget()
        self.vizTabs.addTab(  umapManager.gui(self.gui), "Embedding" )
        vizLayout.addWidget( self.vizTabs )

        self.populate_load_menues()

    def selectClassDirectory(self, ic: int ):
        self.directoryTabs.setCurrentIndex( ic )

    def activate_class_directory( self, index: int ):
        for iS, ctable in enumerate(self.classDirecories.values()):
            ctable.activate( iS == index )

    def activate_spectral_plot( self, index: int ):
        for iS, plot in enumerate(self.spectral_plots):
            plot.activate( iS == index )

    def addMenues(self, parent_menu: Union[QMenu,QMenuBar], menuSpec: Mapping ) :
        for menuName, menuItems in menuSpec.items():
            menu = parent_menu.addMenu(menuName)
            for menuItem in menuItems:
                if isinstance(menuItem, Mapping):   self.addMenues( menu, menuItem )
                else:                               self.addMenuAction( menu, menuItem )

    def populate_load_menues(self):
        self.populate_dataset_load_menu()

    @property
    def datasetDir(self):
        dsdir = os.path.join( dataManager.config.value('data/cache'), dataManager.project_name )
        os.makedirs( dsdir, exist_ok=True )
        return dsdir

    def populate_dataset_load_menu(self):
        for file in os.listdir( self.datasetDir ):
            if file.endswith(".nc"):
                dsid = file[:-3]
                menuButton = QAction( dsid, self.gui )
                menuButton.setStatusTip(f"Load Dataset {dsid}")
                menuButton.triggered.connect( partial(self.runLoadDataset, dsid ))
                self.gui.loadDatasetMenu.addAction(menuButton)

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
        load_dataset_in_background = True
        if load_dataset_in_background:
            taskRunner.start( Task( f"Load Dataset {dsid}", self.loadDataset, dsid, **kwargs) )
        else:
            dset = self.loadDataset( dsid, **kwargs )
            event = dict(event='task', type='result', label='load dataset', result=dset )
            self.submitEvent(event, EventMode.Gui)

    def loadDataset( self, dsid: str, *args, **kwargs ) -> xa.Dataset:
        data_file = os.path.join( self.datasetDir, dsid + ".nc" )
        dataset: xa.Dataset = xa.open_dataset( data_file )
        print( f"Opened Dataset {dsid} from file {data_file}")
        dataset.attrs['dsid'] = dsid
        dataset.attrs['type'] = 'spectra'
        labelsManager.clearMarkers()
        return dataset

    def loadCurrentProject(self):
        projId = dataManager.config.value("project/id",None)
        if projId is not None: self.loadDataset( projId )

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
        umapManager.update({})
        self.refresh_images( **kwargs )

    def refresh_images( self, **kwargs ):
        try: self.spectral_plot.update()
        except AttributeError: pass

    def show(self):
        self.gui.show()
        self.gui.activateWindow()
        self.gui.raise_()
        self.submitEvent( dict( event="gui", type="show" ), EventMode.Gui )
        self.loadCurrentProject()

    def processEvent(self, event: Dict ):
        super().processEvent(event)
        if event.get('event') == 'task':
            if event.get('type') == 'completed':
                print( "SwiftConsole: refreshing panels on task completion")
                self.refresh( event.get('label') )



