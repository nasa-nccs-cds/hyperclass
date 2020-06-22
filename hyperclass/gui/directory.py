import sys
import xarray as xa
import rioxarray as rio
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.image import AxesImage
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton
from matplotlib.axes import Axes
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import collections.abc
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.plot.labels import format_colors
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class DirectoryWidget(QWidget):
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self)
        self.setLayout(QVBoxLayout())

    def keyPressEvent( self, event ):
        event = dict( event="key", type="press", key=event.key() )
        self.process_event(event)

    def keyReleaseEvent(self, event):
        event = dict( event="key", type="release", key=event.key() )
        self.process_event(event)

    def process_event( self, event: Dict ):
        pass

    @property
    def button_actions(self) -> Dict[str, Callable]:
        return self.canvas.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.canvas.menu_actions

