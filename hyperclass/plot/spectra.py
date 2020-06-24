from matplotlib.figure import Figure
from typing import List, Union, Dict, Callable, Tuple, Optional
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from hyperclass.data.aviris.tile import Tile, Block
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

class SpectralPlot(EventClient):

    def __init__( self, **kwargs ):
        self.figure: Optional[Figure] = None
        self.axes: Optional[Axes] = None
        self.lines: OrderedDict[ int, Line2D ] = OrderedDict()
        self.current_line: Optional[Line2D] = None
        self.spectra = None
        self._gui = None
        self.parms = kwargs

    def init( self ):
        self.figure = Figure(constrained_layout=True)
        self.axes = self.figure.add_subplot(111)
        self.figure.patch.set_facecolor( (0.0, 0.0, 0.0) )
        self.axes.axis('off')
        self.axes.title.set_text( "Point Spectra")
        self.axes.title.set_fontsize(14)
        self.axes.title.set_color( (1.0, 1.0, 1.0) )
        self.axes.set_facecolor((0.0, 0.0, 0.0))
        self.figure.set_constrained_layout_pads( w_pad=0., h_pad=0. )
        self.activate_event_listening()

    def gui(self, parent) :
        if self._gui is None:
            self.init( )
            self._gui = FigureCanvas( self.figure )
            self._gui.setParent(parent)
            self._gui.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._gui.setContentsMargins( 0, 0, 0, 0 )
            self._gui.updateGeometry()
        return self._gui

    def processEvent(self, event: Dict ):
        if dataEventHandler.isDataLoadEvent(event):
            result = dataEventHandler.getLoadedData( event )
            if isinstance(result, Block):
                self.spectra = dataEventHandler.subsample( result.getPointData() )
            elif isinstance(result, xa.DataArray):
                self.spectra = dataEventHandler.subsample( result )
            elif isinstance(result, xa.Dataset):
                dset_type = result.attrs['type']
                if dset_type == 'spectra':
                    self.spectra: xa.DataArray = dataEventHandler.subsample( result['spectra'] )
                    self.spectra.attrs['dsid'] = result.attrs['dsid']
        elif event.get('event') == 'pick':
            if event.get('type') == 'vtkpoint':
                index = event.get('pid')
                color = [1.0, 1.0, 1.0 ]
                print( f"SpectralPlot: pick event, pid = {index}")
                self.plot_spectrum( index, self.spectra[index], color )
                self.submitEvent(dict(event='task', type='completed', label="Spectral Plot"), EventMode.Gui)

    def plot_spectrum(self, index: int, data: xa.DataArray, color: List[float] ):
        x = range( data.size )
        if len(color) == 4: color[3] = 1.0
        if self.current_line is not None:
            self.current_line.set_linewidth(1)
        self.current_line, = self.axes.plot( x, data.values, linewidth=3, color=color )
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
            self._gui.repaint()

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
