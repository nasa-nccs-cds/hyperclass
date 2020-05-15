from __future__ import unicode_literals
import sys, os, matplotlib
matplotlib.use('Qt5Agg')
from typing import List, Union, Dict, Callable, Tuple, Optional
from PyQt5 import QtCore, QtWidgets
from hyperclass.plot.console import LabelingConsole
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from hyperclass.umap.manager import UMAPManager
from matplotlib.figure import Figure
from hyperclass.data.aviris.manager import DataManager, Tile, Block
progname = os.path.basename(sys.argv[0])
progversion = "0.1"

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, umgr: UMAPManager, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.frame = MplCanvas( umgr, self )
        self.setCentralWidget(self.frame)

class MplCanvas(FigureCanvas):

    def __init__(self, umgr: UMAPManager, parent=None, width=5, height=4, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.figure )
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.console = LabelingConsole( umgr, figure=self.figure )

    def setBlock(self, block_coords: Tuple[int]   ):
        self.console.setBlock( block_coords )


