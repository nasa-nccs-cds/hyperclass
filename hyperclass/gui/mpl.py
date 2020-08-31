import sys, numpy as np
import xarray as xa
import rioxarray as rio
from matplotlib import cm
from hyperclass.plot.console import LabelingConsole
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.image import AxesImage
from hyperclass.data.events import dataEventHandler, DataType
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton
from hyperclass.data.spatial.tile import Tile, Block
from PyQt5.QtCore import *
from hyperclass.gui.events import EventClient, EventMode
from matplotlib.axes import Axes
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import collections.abc
from hyperclass.data.google import GoogleMaps
from hyperclass.gui.labels import labelsManager, Marker, format_colors
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.collections import PathCollection

class LabelingWidget(QWidget):
    def __init__(self, parent, **kwargs):
        QWidget.__init__(self, parent, **kwargs)
        self.setLayout(QVBoxLayout())
        self.canvas = LabelingCanvas(self, **kwargs)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas)

    def initPlots( self ) -> Optional[AxesImage]:
        return self.canvas.console.initPlots()

    @property
    def spectral_plot(self):
        return self.canvas.console.spectral_plot

    def setBlock(self, block_coords: Tuple[int], **kwargs    ):
        return self.canvas.setBlock( block_coords, **kwargs  )

    def getNewImage(self):
        return self.canvas.getNewImage()

    def getTile(self):
        return self.canvas.console.getTile()

    def getBlock(self) -> Block:
        return self.canvas.getBlock()

    def extent(self):
        return self.canvas.extent()

    @property
    def button_actions(self) -> Dict[str, Callable]:
        return self.canvas.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.canvas.menu_actions

    def mpl_update(self):
        self.canvas.mpl_update()
        self.update()
        self.repaint()

class LabelingCanvas(FigureCanvas):

    def __init__(self, parent,  **kwargs ):
        self.figure = Figure()
        FigureCanvas.__init__(self, self.figure )
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding )
        FigureCanvas.updateGeometry(self)
        self.console = LabelingConsole( figure=self.figure, **kwargs )

    def setBlock(self, block_coords: Tuple[int], **kwargs   ):
        return self.console.setBlock( block_coords, **kwargs  )

    @property
    def button_actions(self) -> Dict[str,Callable]:
        return self.console.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.console.menu_actions

    def mpl_update(self):
        self.console.update_canvas()
        self.update()
        self.repaint()

    def getNewImage(self):
        return self.console.getNewImage()

    def getBlock(self) -> Block:
        return self.console.block

    def extent(self):
        return self.console.block.extent()

class SatellitePlotManager(QObject, EventClient):

    def __init__(self):
        QObject.__init__(self)
        self._gui = None

    def gui( self  ):
        if self._gui is None:
            self._gui = SatellitePlotCanvas( self.process_mouse_event )
            self.activate_event_listening()
        return self._gui

    def process_mouse_event(self, event ):
        self.submitEvent( event, EventMode.Gui )

    def processEvent( self, event ):
        if event.get('event') == "gui":
            if self._gui is not None:
                if event.get('type') == "zoom":
                    xlim, ylim = event.get('xlim'), event.get('ylim')
                    self._gui.set_axis_limits( xlim, ylim )

class SatellitePlotCanvas(FigureCanvas):

    RIGHT_BUTTON = 3
    MIDDLE_BUTTON = 2
    LEFT_BUTTON = 1

    def __init__( self, eventProcessor ):
        self.figure = Figure( constrained_layout=True )
        FigureCanvas.__init__(self, self.figure )
        self.plot = None
        self.image = None
        self.block = None
        self._eventProcessor = eventProcessor
        FigureCanvas.setSizePolicy(self, QSizePolicy.Ignored, QSizePolicy.Ignored)
        FigureCanvas.setContentsMargins( self, 0, 0, 0, 0 )
        FigureCanvas.updateGeometry(self)
        self.axes: Axes = self.figure.add_subplot(111)
        self.axes.get_xaxis().set_visible(False)
        self.axes.get_yaxis().set_visible(False)
        self.figure.set_constrained_layout_pads( w_pad=0., h_pad=0. )
        self.google_maps_zoom_level = 17
        self.google = None

    def setBlock(self, block: Block, type ='satellite'):
        print(" SatelliteCanvas.setBlock ")
        self.block = block
        self.google = GoogleMaps(block)
        try:
            extent = block.extent(4326)
            print( f"Setting satellite image extent: {extent}, xlim = {block.xlim}, ylim = {block.ylim}")
            self.image = self.google.get_tiled_google_map(type, extent, self.google_maps_zoom_level)
            self.plot: AxesImage = self.axes.imshow(self.image, extent=extent, alpha=1.0, aspect='auto' )
            self.axes.set_xlim(extent[0],extent[1])
            self.axes.set_ylim(extent[2],extent[3])
            self._mousepress = self.plot.figure.canvas.mpl_connect('button_press_event', self.onMouseClick )
            self.figure.canvas.draw_idle()
        except AttributeError:
            print( "Cant get spatial bounds for satellite image")

    def set_axis_limits( self, xlims, ylims ):
        if self.image is not None:
            xlims1, ylims1 = self.block.project_extent( xlims, ylims, 4326 )
            self.axes.set_xlim(*xlims1 )
            self.axes.set_ylim(*ylims1)
            print( f"Setting satellite image bounds: {xlims} {ylims} -> {xlims1} {ylims1}")
            self.figure.canvas.draw_idle()

    def onMouseClick(self, event):
        if event.xdata != None and event.ydata != None:
            if event.inaxes ==  self.axes:
                rightButton: bool = int(event.button) == self.RIGHT_BUTTON
                event = dict( event="pick", type="image", lat=event.ydata, lon=event.xdata, button=int(event.button), transient=rightButton )
                self._eventProcessor( event )

    def mpl_update(self):
        self.figure.canvas.draw_idle()

class ReferenceImageCanvas( FigureCanvas, EventClient ):

    RIGHT_BUTTON = 3
    MIDDLE_BUTTON = 2
    LEFT_BUTTON = 1

    def __init__(self, parent, image_spec: Dict[str,Any], **kwargs ):
        self.figure = Figure( constrained_layout=True )
        FigureCanvas.__init__(self, self.figure )
        self.spec = image_spec
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Ignored, QSizePolicy.Ignored)
        FigureCanvas.setContentsMargins( self, 0, 0, 0, 0 )
        FigureCanvas.updateGeometry(self)
        self.axes: Axes = self.figure.add_subplot(111)
        self.axes.get_xaxis().set_visible(False)
        self.axes.get_yaxis().set_visible(False)
        self.figure.set_constrained_layout_pads( w_pad=0., h_pad=0. )
        self.image: xa.DataArray = rio.open_rasterio( self.spec['path'] )
        self.xdim = self.image.dims[-1]
        self.ydim = self.image.dims[-2]
        self.classes = [ ('Unlabeled', [1.0, 1.0, 1.0, 0.5]) ] + self.format_labels( self.spec.get( 'classes', [] ) )
        if self.classes == None:    cmap = "jet"
        else:                       cmap = ListedColormap( [ item[1] for item in self.classes ] )
        self.plot: AxesImage = self.axes.imshow( self.image.squeeze().values, alpha=1.0, aspect='auto', cmap=cmap  )
        self._mousepress = self.plot.figure.canvas.mpl_connect('button_press_event', self.onMouseClick)

    @classmethod
    def format_labels( cls, classes: List[Tuple[str, Union[str, List[Union[float, int]]]]]) -> List[Tuple[str, List[float]]]:
        from hyperclass.gui.labels import format_color
        return [(label, format_color(color)) for (label, color) in classes]

    def onMouseClick(self, event):
        if event.xdata != None and event.ydata != None:
            if event.inaxes ==  self.axes:
                coords = { self.xdim: event.xdata, self.ydim: event.ydata  }
                point_data = self.image.sel( **coords, method='nearest' ).values.tolist()
                ic = point_data[0] if isinstance( point_data, collections.abc.Sequence ) else point_data
                rightButton: bool = int(event.button) == self.RIGHT_BUTTON
                if rightButton: labelsManager.setClassIndex(ic)
                event = dict( event="pick", type="reference", y=event.ydata, x=event.xdata, button=int(event.button), transient=rightButton )
                if not rightButton: event['classification'] = ic
                self.submitEvent(event, EventMode.Gui)

    def mpl_update(self):
        self.figure.canvas.draw_idle()

    def computeClassificationError(self,  labels: xa.DataArray ):
        nerr = np.count_nonzero( self.image.values - labels.values )
        nlabels = np.count_nonzero( self.image.values > 0 )
        print( f"Classication errors: {nerr} errors out of {nlabels}, {(nerr*100.0)/nlabels:.2f}% error. ")

    def processEvent( self, event: Dict ):
        super().processEvent(event)
        if event.get('event') == 'gui':
            if event.get('type') == 'spread':
                labels: xa.Dataset = event.get('labels')
                self.computeClassificationError( labels )

class PointCloudImageCanvas( FigureCanvas, EventClient ):

    RIGHT_BUTTON = 3
    MIDDLE_BUTTON = 2
    LEFT_BUTTON = 1

    def __init__(self, parent,  **kwargs ):
        self.figure = Figure( constrained_layout=True )
        self.init_canvas(parent)
        self.axes: Axes = self.get_axes()
        self._plot: PathCollection = None
        self._marker_plot: PathCollection = None
        self.back_color = np.array( [ [ 1.0, 1.0, 1.0, 1.0 ] ] )
        self.clear()
        self.activate_event_listening( )
        self.draw()
        self.figure.canvas.mpl_connect('pick_event', self.on_pick)

    def init_canvas( self, parent ):
        FigureCanvas.__init__(self, self.figure )
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Ignored, QSizePolicy.Ignored)
        FigureCanvas.setContentsMargins( self, 0, 0, 0, 0 )
        FigureCanvas.updateGeometry(self)

    def get_axes(self) -> Axes:
        from hyperclass.data.manager import dataManager
        self.ndims = dataManager.config.value("umap/dims", type=int)
        spargs = {} if  self.ndims==2 else dict( projection='3d' )
        axes: Axes = self.figure.add_subplot(111,**spargs)
        if self.ndims == 2:
            axes.get_xaxis().set_visible(False)
            axes.get_yaxis().set_visible(False)
        axes.set_facecolor((0.0, 0.0, 0.0))
        self.figure.set_constrained_layout_pads( w_pad=0., h_pad=0. )
        return axes

    def set_colormap(self, colors: Dict ):
        cvals =  list(colors.values())
        self.colors = np.array( cvals, dtype = np.float32 )
 #       self.cmap = ListedColormap([ item[1] for item in colors.items() ] )
     #   self._plot._facecolors[event.ind, :] = (1, 0, 0, 1)
     #   self._plot._edgecolors[event.ind, :] = (1, 0, 0, 1)

    def plotMarkers(self, **kwargs  ):
        reset = kwargs.get( 'reset', False )
        if self._plot is not None:
            plot_offsets = self._plot._offsets3d if (self.ndims == 3) else np.hsplit( self._plot.get_offsets(), self.ndims )
            new_offsets = []
            new_colors = []
            for marker in labelsManager.getMarkers():
                for pid in marker.pids:
                    new_offsets.append( [ x[ pid ] for x in plot_offsets ] )
                    new_colors.append( marker.color )
            if len( new_offsets ) > 0:
                point_data = np.array(new_offsets)
                color_data = np.array(new_colors)
                pcoords = [x.squeeze() for x in np.hsplit(point_data, point_data.shape[1])]
                if self._marker_plot is None:
                    self._marker_plot = self.axes.scatter(*pcoords, c=color_data, s=25)
                else:
                    if (self.ndims == 3):
                        self._marker_plot._offsets3d = pcoords
                        self._marker_plot._facecolor3d = color_data
                        self._marker_plot._edgecolor3d = color_data
                    else:
                        self._marker_plot.set_offsets( point_data )
                        self._marker_plot.set_facecolor( color_data )
                        self._marker_plot.set_edgecolor(color_data)
                self.mpl_update()

    def clear(self):
        if self._marker_plot is not None:
            if self.ndims == 2:  self._marker_plot.set_offsets( np.array([]) )
            else:                self._plot._offsets3d = [ np.array([]), np.array([]), np.array([]) ]
            self._marker_plot.set_array( np.array([]) )
        if self._plot is not None:
            self._plot.set_facecolor([1.0,1.0,1.0])

    def color_by_metric( self, metric: np.array, **kwargs ):
        masked_metric: np.ma.MaskedArray = np.ma.masked_invalid(metric)
        maxval = masked_metric.max()
        metric_data = masked_metric.filled(maxval)/maxval
        self._plot.set_array( metric_data )
        self._plot.set_cmap( cm.get_cmap('jet') )

    def set_point_colors( self, **kwargs ):
        color_data = kwargs.get( 'data', None )
        if color_data is None:
            sample_labels = kwargs.get( 'labels', None )
            if sample_labels is None: return
            fcolors = np.where( sample_labels.values.reshape(-1,1) > 0, self.colors[sample_labels.values], self.back_color )
            if  self.ndims == 3:
                self._plot._facecolor3d = fcolors
                self._plot._edgecolor3d = fcolors
            else:
                self._plot.set_facecolor( fcolors )
                self._plot.set_edgecolor( fcolors )
        else:
            self.color_by_metric( color_data )
        self.mpl_update()

    @classmethod
    def format_labels( cls, classes: List[Tuple[str, Union[str, List[Union[float, int]]]]]) -> List[Tuple[str, List[float]]]:
        from hyperclass.gui.labels import format_color
        return [(label, format_color(color)) for (label, color) in classes]

    def onMouseClick(self, event):
        if event.xdata != None and event.ydata != None:
            if event.inaxes ==  self.axes:
                inBounds, idx = self._plot.contains( event )
                print(f"Pick event: {event.xdata} {event.ydata}, {inBounds}, {idx}")
                ic, color = labelsManager.selectedColor( True )
                transient = labelsManager.selectedClass == 0
                fc = self._plot.get_facecolor()
                pids = idx['ind'].tolist()
                for ix in pids: fc[ix] = color
                if self.ndims == 3:
                    self._plot._facecolor3d = fc
                    self._plot._edgecolor3d = fc
                else:
                    self._plot.set_facecolor(fc)
                    self._plot.set_edgecolor(fc)
                self.mpl_update()
                event = dict(event="pick", type="plot", pids = pids, transient=transient, mark= not transient )
                self.submitEvent(event, EventMode.Gui)

                # coords = { self.xdim: event.xdata, self.ydim: event.ydata  }
                # point_data = self.image.sel( **coords, method='nearest' ).values.tolist()
                # ic = point_data[0] if isinstance( point_data, collections.abc.Sequence ) else point_data
                # rightButton: bool = int(event.button) == self.RIGHT_BUTTON
                # if rightButton: labelsManager.setClassIndex(ic)
                # event = dict( event="pick", type="reference", y=event.ydata, x=event.xdata, button=int(event.button), transient=rightButton )
                # if not rightButton: event['classification'] = ic
                # self.submitEvent(event, EventMode.Gui)

    def on_pick( self, event ):
        print( f"Pick event, pid = {event.ind}")

    def mpl_update(self):
        self.draw_idle()
        self.update()
        self.flush_events()
#        event = dict( event="gui", type="update" )
#        self.submitEvent(event, EventMode.Gui )

    def gui_update(self, **kwargs ):
        self.mpl_update()

    def setKeyState(self, event):
        pass

    def releaseKeyState(self):
        pass

    def init_plot(self, point_data: np.ndarray):
        cids: np.ndarray = labelsManager.labels_data().values
        fcolors = np.where(cids.reshape(-1,1) > 0, self.colors[cids], self.back_color )
        pcoords = [ x.squeeze() for x in np.hsplit(point_data, self.ndims) ]
        self._plot: PathCollection = self.axes.scatter( *pcoords, s=1, c=fcolors, pickradius=2.0  )
        self._mousepress = self._plot.figure.canvas.mpl_connect('button_press_event', self.onMouseClick)
        #        self.plot.set_array( point_colors )

    def update_plot( self, point_data: np.ndarray ):
        if self._plot is None:
            self.init_plot( point_data )
        else:
            xlim = (np.min(point_data[:,0]), np.max(point_data[:,0]))
            ylim = (np.min(point_data[:, 1]), np.max(point_data[:, 1]))
            self.axes.set_xlim( *xlim )
            self.axes.set_ylim( *ylim )
            if self.ndims == 3:
                zlim = (np.min(point_data[:, 2]), np.max(point_data[:, 2]))
                self.axes.set_zlim(*zlim)
                self._plot._offsets3d = [ x.squeeze() for x in np.hsplit(point_data, 3) ]
                print( f" update point cloud plot: xlim={xlim}, ylim={ylim}, zlim={zlim}, sample = {point_data[0]}, dist = {point_data[0] - point_data[1000]}")
            else:
                self._plot.set_offsets(point_data)
                print( f" update point cloud plot: xlim={xlim}, ylim={ylim}, sample = {point_data[0]}, dist = {point_data[0] - point_data[1000]}")
        self.draw()
        self.update()
        self.flush_events()

satellitePlotManager = SatellitePlotManager()

