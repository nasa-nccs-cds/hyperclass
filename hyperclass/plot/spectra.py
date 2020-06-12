from matplotlib.figure import Figure
from typing import List, Union, Dict, Callable, Tuple, Optional
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
from collections import OrderedDict
from mpl_toolkits.axes_grid1 import Divider, Size
import xarray as xa
import numpy as np

def isUnlabeled(color):
    for ix in range(3):
        if color[ix] < 1.0: return False
    return True

class SpectralPlot:

    def __init__( self, **kwargs ):
        self.figure: Optional[Figure] = None
        self.axes: Optional[Axes] = None
        self.lines: OrderedDict[ int, Line2D ] = OrderedDict()
        self.current_line: Optional[Line2D] = None
        self.parms = kwargs

    def init( self, figure: Figure ):
        self.figure = figure
        self.axes = self.figure.add_subplot(111)
        self.figure.patch.set_facecolor( (0.0, 0.0, 0.0) )
        self.axes.axis('off')
        self.axes.title.set_text( "Point Spectra")
        self.axes.title.set_fontsize(14)
        self.axes.title.set_color( (1.0, 1.0, 1.0) )
        self.figure.set_constrained_layout_pads( w_pad=0., h_pad=0. )

    def plot_spectrum(self, index: int, data: xa.DataArray, color: List[float] ):
        x = range( data.size )
        if len(color) == 4: color[3] = 1.0
        if self.current_line is not None:
            self.current_line.set_linewidth(1)
            self.clear_unlabeled()
        self.current_line, = self.axes.plot( x, data.values, linewidth=3, color=color )
        self.lines[ index ] = self.current_line

    def clear(self):
        self.lines = OrderedDict()
        self.current_line = None

    def clear_current_line(self):
        index, line = self.lines.popitem()
        line.remove()
        self.current_line = None

    def clear_unlabeled(self):
        if self.current_line is not None:
            if isUnlabeled( self.current_line.get_color() ):
                self.clear_current_line()


    def clear_spectrum(self):
        self.clear_unlabeled()

    def remove_spectrum(self, index: int ):
        line: Line2D = self.lines[ index ]
        line.remove()
        del self.lines[ index ]

    def has_spectrum(self, index: int ):
        return index in self.lines

    def update_canvas(self):
        self.figure.canvas.draw_idle()

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
