from matplotlib.collections import PathCollection
from matplotlib.axes import Axes
import numpy as np


class Markers:

    def __init__(self, axes: Axes ):
        self.axes = axes
        self.markers: PathCollection = None
        self.point_selection = []

    def plot(self ):
        if self.point_selection:
            xcoords = [ ps[1] for ps in self.point_selection ]
            ycoords = [ ps[0] for ps in self.point_selection ]
            cvals   = [ ps[2] for ps in self.point_selection ]
            colors = [ self.get_color(ic) for ic in cvals ]
            self.markers.set_offsets(np.c_[ xcoords, ycoords ] )
            self.markers.set_facecolor( colors )