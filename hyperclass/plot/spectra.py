from matplotlib.figure import Figure
from typing import List, Union, Dict, Callable, Tuple, Optional
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import  QSizePolicy
from matplotlib.lines import Line2D
from matplotlib.backend_bases import PickEvent, MouseEvent
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from matplotlib.axes import Axes
from collections import OrderedDict
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.gui.labels import labelsManager
import xarray as xa

def isUnlabeled(color):
    for ix in range(3):
        if color[ix] < 1.0: return False
    return True

class Spectrum:
    def __init__(self, band_values: List[float], color: List[float] ):
        self.bands = band_values
        self.color = color

    def isTransient(self):
        return isUnlabeled( self.color )

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
        self.scaled_spectra = None
        self.raw_spectra = None
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
        self.axes.set_facecolor((0.0, 0.0, 0.0))
        self.axes.get_yaxis().set_visible(False)
        self.activate_event_listening()

    def configure(self, event: Dict ):
        type = self.scaled_spectra.attrs.get('type')
        if type == 'spectra':
            plot_metadata = dataEventHandler.getMetadata( event )
            obsids = plot_metadata['obsids'].values
            targets = plot_metadata['targets'].values
            self._titles = {}
            for index in range( obsids.shape[0] ):
                self._titles[index] = f"{targets[index]}: {obsids[index]}"
        else:
            self.figure.patch.set_facecolor( (0.0, 0.0, 0.0) )
            self.axes.axis('off')
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
        if (self.axes is not None) and ( self.current_pid is not None ) and ( self.raw_spectra is not None ):
            print(f"SpectralPlot.mousePressEvent: [{event.x}, {event.y}] -> [{event.xdata}, {event.ydata}]" )
            xindex = int( event.xdata )
            data_values = self.raw_spectra[ self.current_pid ]
            axis_values = self.raw_spectra.coords[ self.raw_spectra.dims[1] ]
            xval = axis_values[xindex].values.tolist()
            yval = data_values[xindex].values.tolist()
            title = f" {xval:.2f}: {yval:.3f} "
            self.axes.set_title( title, {'fontsize': 10 }, 'right' )
            self.update_marker( event.xdata )
            self.update()

    def processEvent(self, event: Dict ):
        if dataEventHandler.isDataLoadEvent(event):
            self.scaled_spectra: xa.DataArray = dataEventHandler.getPointData(event, scaled = True)
            self.raw_spectra:    xa.DataArray = dataEventHandler.getPointData(event, scaled = False)
            self.configure( event )
        elif event.get('event') == 'pick':
            if (event.get('type') in [ 'vtkpoint', 'directory' ]) and self._active:
                self.current_pid = event.get('pid')
                self.clear_transients()
                print( f"SpectralPlot: pick event, pid = {self.current_pid}")
                scaled_values = self.scaled_spectra[self.current_pid]
                self.plot_spectrum( scaled_values, labelsManager.selectedColor )
                if self._titles is not None:
                    self.axes.set_title( self._titles.get(self.current_pid,"*SPECTRA*" ), {'fontsize': 10 }, 'left' )
                self.update_marker()
                self.axes.set_title( "", {}, 'right' )
                self.update_signal.emit()

    def update_marker(self, new_xval = None ):
        if self.marker is not None:
            self.axes.lines.remove(self.marker)
            self.marker = None
        if new_xval is not None:
            self.marker = self.axes.axvline( new_xval, color="yellow", linewidth=1, alpha=0.75 )

    def plot_spectrum(self, data: xa.DataArray, color: List[float] ):
        x = range( data.size )
        linewidth = 2 if self.overlay else 1
        if len(color) == 4: color[3] = 1.0
        spectrum = data.values
        self.current_line, = self.axes.plot( x, spectrum, linewidth=linewidth, color=color )
        self.current_line.color = color
        self.lines[ self.current_pid ] = self.current_line

    def clear(self):
        self.lines = OrderedDict()
        self.current_line = None
        self.axes.clear()

    def clear_transients(self):
        if (self.current_line is not None):
            if isUnlabeled(self.current_line.color) or not self.overlay:
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

    # def get_axes(self):
    #     h = [Size.Fixed(0.0), Size.Fixed(0.0)]
    #     v = [Size.Fixed(0.0), Size.Fixed(0.0)]
    #     divider = Divider( self.figure, (0.0, 0.0, 1., 1.), h, v, aspect=False)
    #     self.axes = Axes( self.figure, divider.get_position())
    #     self.axes.set_axes_locator(divider.new_locator(nx=1, ny=1))
    #     self.figure.add_axes(self.axes)
    #     self.axes.set_facecolor( self.parms.get( 'bc', (0.0, 0.0, 0.0)) )
    #     self.axes.xaxis.set_visible(False)
    #     self.axes.yaxis.set_visible(False)
    #
