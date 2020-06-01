import sys
from hyperclass.plot.console import LabelingConsole
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton
from hyperclass.data.aviris.manager import DataManager, Block, Tile
from hyperclass.umap.manager import UMAPManager
from typing import List, Union, Dict, Callable, Tuple, Optional
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class MplWidget(QWidget):
    def __init__(self, umgr: UMAPManager, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.canvas = MplCanvas(self, umgr, width=10, height=8, **kwargs )
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas)

    def setBlock(self, block_coords: Tuple[int]   ):
        self.canvas.setBlock( block_coords )

    def getNewImage(self):
        return self.canvas.getNewImage()

    def getBlock(self) -> Block:
        return self.canvas.getBlock()

    def extent(self):
        return self.canvas.extent()

    def keyPressEvent( self, event ):
        event = dict( event="key", type="press", key=event.key() )
        self.process_event(event)

    def keyReleaseEvent(self, event):
        event = dict( event="key", type="release", key=event.key() )
        self.process_event(event)

    def process_event( self, event: Dict ):
        self.canvas.process_event(event )

    @property
    def button_actions(self) -> Dict[str, Callable]:
        return self.canvas.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.canvas.menu_actions

    def mpl_update(self):
        self.canvas.mpl_update()
        self.update()
        self.repaint()

class MplCanvas(FigureCanvas):

    def __init__(self, parent, umgr: UMAPManager, width=5, height=4, dpi=100, **kwargs ):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.figure )
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.console = LabelingConsole( umgr, figure=self.figure, **kwargs )

    def process_event( self, event: Dict ):
        self.console.process_event(event)

    def setBlock(self, block_coords: Tuple[int]   ):
        self.console.setBlock( block_coords )

    @property
    def button_actions(self) -> Dict[str,Callable]:
        return self.console.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.console.menu_actions

    def mpl_update(self):
        self.console.update_canvas()
        self.update()
        self.repaint()

    def getNewImage(self):
        return self.console.getNewImage()

    def getBlock(self) -> Block:
        return self.console.block

    def extent(self):
        return self.console.block.extent()
