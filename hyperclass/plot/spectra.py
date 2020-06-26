from matplotlib.figure import Figure
from typing import List, Union, Dict, Callable, Tuple, Optional
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import  QSizePolicy
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
from collections import OrderedDict
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.events import EventClient, EventMode
import xarray as xa

def isUnlabeled(color):
    for ix in range(3):
        if color[ix] < 1.0: return False
    return True

class SpectralCanvas( FigureCanvas ):

    def __init__(self, figure: Figure ):
        FigureCanvas.__init__( self, figure )

class SpectralPlot(EventClient):

    def __init__( self, **kwargs ):
        self.figure: Optional[Figure] = None
        self.axes: Optional[Axes] = None
        self.lines: OrderedDict[ int, Line2D ] = OrderedDict()
        self.current_line: Optional[Line2D] = None
        self.spectra = None
        self._gui = None
        self._titles = None
        self.parms = kwargs

    def init( self ):
        self.figure = Figure(constrained_layout=True)
        self.axes = self.figure.add_subplot(111)
        self.axes.title.set_fontsize(14)
        self.axes.set_facecolor((0.0, 0.0, 0.0))
        self.axes.get_yaxis().set_visible(False)
#        self.axes.figure.canvas.mpl_connect('button_press_event', self.onMouseClick)
        self.activate_event_listening()

    def configure(self ):
        type = self.spectra.attrs.get('type')
        if type == 'spectra':
            plot_metadata = dataEventHandler.getMetadata()
            obsids = plot_metadata['obsids'].values
            targets = plot_metadata['targets'].values
            self._titles = {}
            for index in range( obsids.shape[0] ):
                self._titles[index] = f"{targets[index]}: {obsids[index]}"
            self.axes.title.set_text( "Point Spectra" )
            self.axes.title.set_color((0.0, 0.0, 0.0))
        else:
            self.figure.patch.set_facecolor( (0.0, 0.0, 0.0) )
            self.axes.axis('off')
            self.axes.title.set_text( "Point Spectra")
            self.axes.title.set_color((1.0, 1.0, 1.0))
            self.figure.set_constrained_layout_pads( w_pad=0., h_pad=0. )

    def onMouseClick(self, event ):
        print( f"Spectral Plot mouse click at {event.xdata} {event.ydata}")

    def gui(self, parent) :
        if self._gui is None:
            self.init( )
            self._gui = SpectralCanvas( self.figure )
            self._gui.setParent(parent)
            self._gui.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._gui.setContentsMargins( 0, 0, 0, 0 )
            self._gui.updateGeometry()
        return self._gui

    def processEvent(self, event: Dict ):
        if dataEventHandler.isDataLoadEvent(event):
            self.spectra: xa.DataArray = dataEventHandler.getPointData( event, scaled = True )
            self.configure()
        elif event.get('event') == 'pick':
            if event.get('type') == 'vtkpoint':
                index = event.get('pid')
                color = event.get('color')
                linewidth = 3
                if color is None:
                    self.clear_current_line()
                    color = [1.0, 1.0, 1.0 ]
                    linewidth = 1
                print( f"SpectralPlot: pick event, pid = {index}")
                self.plot_spectrum( index, self.spectra[index], color, linewidth )
                if self._titles is not None:
                    self.axes.title.set_text( self._titles.get(index,"*SPECTRA*" ) )
                self.submitEvent(dict(event='task', type='completed', label="Spectral Plot"), EventMode.Gui)

    def plot_spectrum(self, index: int, data: xa.DataArray, color: List[float], linewidth ):
        x = range( data.size )
        if len(color) == 4: color[3] = 1.0
        spectrum = data.values
        if self.current_line is not None:
            self.current_line.set_linewidth(1)
        self.current_line, = self.axes.plot( x, spectrum, linewidth=linewidth, color=color )
        self.lines[ index ] = self.current_line

    def clear(self):
        self.lines = OrderedDict()
        self.current_line = None
        self.axes.clear()

    def clear_current_line(self):
        if self.current_line is not None:
            index, line = self.lines.popitem()
            line.remove()
            self.current_line = None

    def remove_spectrum(self, index: int ):
        line: Line2D = self.lines[ index ]
        line.remove()
        del self.lines[ index ]

    def has_spectrum(self, index: int ):
        return index in self.lines

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
