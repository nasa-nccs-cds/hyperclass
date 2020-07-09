from matplotlib.figure import Figure
from typing import List, Union, Dict, Callable, Tuple, Optional
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import  QSizePolicy
from matplotlib.lines import Line2D
from matplotlib.backend_bases import PickEvent, MouseEvent
from hyperclass.util.config import tostr
from PyQt5.QtCore import *
from matplotlib.axes import Axes
from collections import OrderedDict
from hyperclass.data.events import dataEventHandler, DataType
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.gui.labels import labelsManager
import xarray as xa

class Spectrum:
    def __init__(self, band_values: List[float], color: List[float], cid: int ):
        self.bands = band_values
        self.color = color
        self.cid = cid

    def isTransient(self):
        return self.cid == 0

class SpectralCanvas( FigureCanvas ):

    def __init__(self, figure: Figure ):
        FigureCanvas.__init__( self, figure )
        self.figure = figure
        self.figure.patch.set_facecolor('#e2e2e2')

class SpectralPlot(QObject,EventClient):
    update_signal = pyqtSignal()

    def __init__( self, active: bool, **kwargs ):
        QObject.__init__(self)
        self.figure: Optional[Figure] = None
        self._active = active
        self.overlay = kwargs.get('overlay', False )
        self.axes: Optional[Axes] = None
        self.lines: OrderedDict[ int, Line2D ] = OrderedDict()
        self.current_line: Optional[Line2D] = None
        self.current_pid = -1
        self.plotx: xa.DataArray = None
        self.ploty: xa.DataArray = None
        self.marker: Line2D = None
        self._gui = None
        self._titles = None
        self.parms = kwargs
        self.update_signal.connect( self.update )

    def activate( self, active: bool  ):
        self._active = active

    def init( self ):
        self.figure = Figure(constrained_layout=True)
        self.axes = self.figure.add_subplot(111)
        self.axes.title.set_fontsize(14)
        self.activate_event_listening()

    def configure(self, event: Dict ):
        type = self.ploty.attrs.get('type')
        self.axes.set_facecolor((0.0, 0.0, 0.0))
        if type == 'spectra':
            plot_metadata = dataEventHandler.getMetadata( event )
            self._titles = {}
            for index in range( plot_metadata[0].shape[0] ):
                self._titles[index] = "[" + ",".join( [ tostr(pm.values[index]) for pm in plot_metadata ] ) + "]"
        else:
            self.figure.patch.set_facecolor( (0.0, 0.0, 0.0) )
            self.axes.axis('off')
            self.axes.get_yaxis().set_visible(False)
            self.figure.set_constrained_layout_pads( w_pad=0., h_pad=0. )

    def gui(self, parent) :
        if self._gui is None:
            self.init( )
            self._gui = SpectralCanvas( self.figure )
            self._gui.setParent(parent)
            self._gui.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._gui.setContentsMargins( 0, 0, 0, 0 )
            self._gui.updateGeometry()
            self._gui.mpl_connect('button_press_event', self.mouseClick)

        return self._gui

    def mouseClick(self, event: MouseEvent):
        if (self.axes is not None) and ( self.current_pid is not None ) and ( self.ploty is not None ):
            print(f"SpectralPlot.mousePressEvent: [{event.x}, {event.y}] -> [{event.xdata}, {event.ydata}]" )
            xindex = int( event.xdata )
            data_values = self.ploty[ self.current_pid ]
            axis_values = self.plotx[ self.current_pid ]
            xval = axis_values[xindex].values.tolist()
            yval = data_values[xindex].values.tolist()
            title = f" {xval:.2f}: {yval:.3f} "
            self.axes.set_title( title, {'fontsize': 10 }, 'right' )
            self.update_marker( event.xdata )
            self.update()

    def processEvent(self, event: Dict ):
        if dataEventHandler.isDataLoadEvent(event):
            plot_data = dataEventHandler.getPointData( event, DataType.Plot )
            self.plotx: xa.DataArray = plot_data["plotx"]
            self.ploty: xa.DataArray = plot_data["ploty"]
            self.configure( event )
        elif event.get('event') == 'pick':
            if (event.get('type') in [ 'vtkpoint', 'directory' ]) and self._active:
                if  self.ploty is not None:
                    self.current_pid = event.get('pid')
                    cid = labelsManager.selectedClass
                    self.clear_transients()
                    print( f"SpectralPlot: pick event, pid = {self.current_pid}")
                    self.plot_spectrum( self.current_pid, cid, labelsManager.selectedColor )
                    if self._titles is not None:
                        self.axes.set_title( self._titles.get(self.current_pid,"*SPECTRA*" ), {'fontsize': 10 }, 'center' )
                    self.update_marker()
                    self.axes.set_title( "", {}, 'right' )
                    self.update_signal.emit()

    def update_marker(self, new_xval = None ):
        if self.marker is not None:
            self.axes.lines.remove(self.marker)
            self.marker = None
        if new_xval is not None:
            self.marker = self.axes.axvline( new_xval, color="yellow", linewidth=1, alpha=0.75 )

    def plot_spectrum(self, pid: int, cid: int, color: List[float] ):
        spectrum = self.ploty[self.current_pid].values
        x = self.plotx[ self.current_pid ].values
        ymax, ymin = spectrum.max(), spectrum.min()
        xmax, xmin = x.max(), x.min()
        linewidth = 2 if self.overlay else 1
        if len(color) == 4: color[3] = 1.0
        self.current_line, = self.axes.plot( x, spectrum, linewidth=linewidth, color=color )
        self.axes.set_ybound(ymin, ymax)
        self.axes.set_xbound(xmin, xmax)
        print( f"SPECTRA BOUNDS: [ {xmin:.2f}, {xmax:.2f} ] -> [ {ymin:.2f}, {ymax:.2f} ]")
        self.current_line.color = color
        self.current_line.cid = cid
        self.lines[ self.current_pid ] = self.current_line

    def clear(self):
        self.lines = OrderedDict()
        self.current_line = None
        self.axes.clear()

    def clear_transients(self):
        if (self.current_line is not None):
            if (self.current_line.cid == 0) or not self.overlay:
                index, line = self.lines.popitem()
                line.remove()
                self.current_line = None
            else:
                self.current_line.set_linewidth(1)

    def remove_spectrum(self, index: int ):
        line: Line2D = self.lines[ index ]
        line.remove()
        del self.lines[ index ]

    def has_spectrum(self, index: int ):
        return index in self.lines

    @pyqtSlot()
    def update(self):
        if self._gui is not None:
            self.figure.canvas.draw_idle()
            self._gui.update()