from matplotlib.figure import Figure
from typing import List, Union, Dict, Callable, Tuple, Optional
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
import numpy as np

class SpectralPlot:

    def __init__( self, **kwargs ):
        self.figure: Figure = kwargs.pop( 'figure', None )
        if self.figure is None:
            self.figure = plt.figure()
        self.axes: Axes = self.figure.add_subplot(1,1)
        self.lines = Dict[ int, Line2D ]
        self.current_line: Optional[Line2D] = None

    def plot_spectrum(self, index: int, data: np.ndarray, color: Tuple ):
        x = range( data.size )
        if self.current_line is not None: self.current_line.set_linewidth(1)
        self.current_line, = self.axes.plot( x, data, linewidth=3, color=color )
        self.lines[ index ] = self.current_line

    def remove_spectrum(self, index: int ):
        line: Line2D = self.lines[ index ]
        line.remove()
        del self.lines[ index ]

    def has_spectrum(self, index: int ):
        return index in self.lines



