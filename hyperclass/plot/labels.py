from matplotlib.collections import PathCollection
from matplotlib.axes import Axes
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import collections.abc
import numpy as np

def h2c( hexColor: str ) -> List[float]:
    hc = hexColor.strip( "# ")
    cv = [ int(hc[i0:i0+2],16) for i0 in range(0,len(hc),2) ]
    cv = cv if len(cv) == 4 else cv + [255]
    return [ c/255 for c in cv ]

def isIntRGB( color ):
    for val in color:
        if val > 1: return True
    return False

def format_colors( classes: List[Tuple[str,Union[str,List[float]]]] ) -> List[Tuple[str,List[float]]]:
    test_item = classes[0][1]
    if isinstance(test_item, str):
        return [ ( label, h2c(color) ) for (label,color) in classes ]
    elif isinstance( test_item, collections.abc.Sequence ) and isIntRGB( test_item ):
        return [ ( label, [ c/255 for c in color ] ) for (label,color) in classes ]
    else:
        return classes

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