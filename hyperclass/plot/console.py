import matplotlib.widgets
import matplotlib.patches
from hyperclass.gui.tasks import taskRunner, Task, Callbacks
from hyperclass.plot.widgets import ColoredRadioButtons, ButtonBox
from hyperclass.data.google import GoogleMaps
from hyperclass.plot.spectra import SpectralPlot
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.gridspec import GridSpec, SubplotSpec
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
from matplotlib.colors import Normalize
from matplotlib.backend_bases import PickEvent, MouseEvent
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from collections import OrderedDict
from hyperclass.data.aviris.manager import dataManager
from hyperclass.umap.manager import UMAPManager
from PyQt5.QtWidgets import QMessageBox
from functools import partial
from pyproj import Proj, transform
import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection
from hyperclass.data.aviris.tile import Tile, Block
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.svm.manager import SVC
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
import pandas as pd
import xarray as xa
import numpy as np
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import time, math, atexit, os
from PyQt5.QtWidgets import QAction

def get_color_bounds( color_values: List[float] ) -> List[float]:
    color_bounds = []
    for iC, cval in enumerate( color_values ):
        if iC == 0: color_bounds.append( cval - 0.5 )
        else: color_bounds.append( (cval + color_values[iC-1])/2.0 )
    color_bounds.append( color_values[-1] + 0.5 )
    return color_bounds

class PageSlider(matplotlib.widgets.Slider):

    def __init__(self, ax: Axes, numpages = 10, valinit=0, valfmt='%1d', **kwargs ):
        self.facecolor=kwargs.get('facecolor',"yellow")
        self.activecolor = kwargs.pop('activecolor',"blue" )
        self.stepcolor = kwargs.pop('stepcolor', "#ff6f6f" )
        self.on_animcolor = kwargs.pop('on-animcolor', "#006622")
        self.fontsize = kwargs.pop('fontsize', 10)
        self.maxIndexedPages = 24
        self.numpages = numpages
        self.axes = ax

        super(PageSlider, self).__init__(ax, "", 0, numpages, valinit=valinit, valfmt=valfmt, **kwargs)

        self.poly.set_visible(False)
        self.vline.set_visible(False)
        self.pageRects = []
        indexMod = math.ceil( self.numpages / self.maxIndexedPages )
        for i in range(numpages):
            facecolor = self.activecolor if i==valinit else self.facecolor
            r  = matplotlib.patches.Rectangle((float(i)/numpages, 0), 1./numpages, 1, transform=ax.transAxes, facecolor=facecolor)
            ax.add_artist(r)
            self.pageRects.append(r)
            if i % indexMod == 0:
                ax.text(float(i)/numpages+0.5/numpages, 0.5, str(i+1), ha="center", va="center", transform=ax.transAxes, fontsize=self.fontsize)
        self.valtext.set_visible(False)

        divider = make_axes_locatable(ax)
        bax = divider.append_axes("right", size="5%", pad=0.05)
        fax = divider.append_axes("right", size="5%", pad=0.05)
        self.button_back = matplotlib.widgets.Button(bax, label='$\u25C1$', color=self.stepcolor, hovercolor=self.activecolor)
        self.button_forward = matplotlib.widgets.Button(fax, label='$\u25B7$', color=self.stepcolor, hovercolor=self.activecolor)
        self.button_back.label.set_fontsize(self.fontsize)
        self.button_forward.label.set_fontsize(self.fontsize)
        self.button_back.on_clicked(self.backward)
        self.button_forward.on_clicked(self. forward)

    def refesh(self):
        self.axes.figure.canvas.draw()


    def _update(self, event):
        super(PageSlider, self)._update(event)
        i = int(self.val)
        if i >=self.valmax: return
        self._colorize(i)

    def _colorize(self, i):
        for j in range(self.numpages):
            self.pageRects[j].set_facecolor(self.facecolor)
        self.pageRects[i].set_facecolor(self.activecolor)

    def forward(self, event=None):
        current_i = int(self.val)
        i = current_i+1
        if i >= self.valmax: i = self.valmin
        self.set_val(i)
        self._colorize(i)

    def backward(self, event=None):
        current_i = int(self.val)
        i = current_i-1
        if i < self.valmin: i = self.valmax -1
        self.set_val(i)
        self._colorize(i)

class LabelingConsole:

    RIGHT_BUTTON = 3
    MIDDLE_BUTTON = 2
    LEFT_BUTTON = 1

    def __init__(self, umgr: UMAPManager, **kwargs ):   # class_labels: [ [label, RGBA] ... ]
        self._debug = False
        self.currentFrame = 0
        self.block: Block = None
        self.slider: Optional[PageSlider] = None
        self.image: Optional[AxesImage] = None
        self.labels = None
        self.transients = []
        self.plot_axes: Optional[Axes] = None
        self.marker_list: List[Dict] = []
        self.marker_plot: Optional[PathCollection] = None
        self.label_map: Optional[xa.DataArray] = None
        self.umgr: UMAPManager = umgr
        self.svc: Optional[SVC] = None
        self.dataLims = {}
        self.key_mode = None
        self.currentClass = 0
        self.google: GoogleMaps = None
        self.google_maps_zoom_level = 17
        self.new_image = None
        self.nFrames = None

        self.figure: Figure = kwargs.pop( 'figure', None )
        self.google_figure: Figure = None
        if self.figure is None:
            self.figure = plt.figure()
        self.labels_image: Optional[AxesImage] = None
        self.flow_iterations = kwargs.get( 'flow_iterations', 5 )
        self.frame_marker: Optional[Line2D] = None
        self.control_axes = {}
        self._tiles: Dict[List,Tile] = {}

        self.read_markers()
        self.spectral_plot = SpectralPlot()
        self.navigation_listeners = []
        self.setup_plot(**kwargs)

        self.button_actions =  OrderedDict(model=   partial(self.run_task, self.build_model, "Computing embedding...", type=umgr.embedding_type ),
                                           spread=  self.spread_labels,
                                           undo=    self.undo_marker_selection,
                                           clear=   self.clearLabels,
#                                            mixing=  partial(self.run_task, self.computeMixingSpace, "Computing mixing space..." ),
                                           learn=   partial(  self.run_task, self.learn_classification,   "Learning class boundaries..." ),
                                           apply =  partial(  self.run_task, self.apply_classification,   "Applying learned classification..." )
                                           )

        google_actions = [[maptype, None, None, partial(self.run_task, self.download_google_map, "Accessing Landsat Image...", maptype, task_context='newfig')] for maptype in ['satellite', 'hybrid', 'terrain', 'roadmap']]
        self.menu_actions = OrderedDict( Layers = [ [ "Increase Labels Alpha", 'Ctrl+>', None, partial( self.update_image_alpha, "labels", True ) ],
                                                    [ "Decrease Labels Alpha", 'Ctrl+<', None, partial( self.update_image_alpha, "labels", False ) ],
                                                    [ "Increase Band Alpha",   'Alt+>',  None, partial( self.update_image_alpha, "bands", True ) ],
                                                    [ "Decrease Band Alpha",   'Alt+<',  None, partial( self.update_image_alpha, "bands", False ) ],
                                                    [ "Increase Point Sizes", 'Ctrl+}',  None, partial( self.update_point_sizes, True ) ],
                                                    [ "Decrease Point Sizes", 'Ctrl+{',  None, partial( self.update_point_sizes, False ) ] ] )
 #                                                   OrderedDict( GoogleMaps=google_actions )  ]  )

        self.add_selection_controls( **kwargs )
        atexit.register(self.exit)
        self._update(0)

    @property
    def tile(self):
        tile_indices = dataManager.config.value( 'tile/indices', [0,0] )
        return self._tiles.setdefault( tuple(tile_indices), Tile() )

    @property
    def toolbar(self)-> NavigationToolbar:
        return self.figure.canvas.toolbar

    @property
    def transform(self):
        return self.block.transform

    def process_event( self, event: Dict ):
        print( f" LabelingConsole: process_event: {event}")
        if event['event'] == 'pick':
            transient = event.pop('transient',True)
            if event['type'] == 'vtkpoint':
                point_index = event['pid']
                self.mark_point( point_index, transient )
            elif event['type'] == 'image':
                self.add_marker( self.get_image_selection_marker( event ), transient )
        elif event['event'] == 'key':
            if   event['type'] == "press":   self.key_mode = event['key']
            elif event['type'] == "release": self.key_mode = None

    def get_image_selection_marker( self, event ) -> Dict:
        if 'lat' in event:
            lat, lon = event['lat'], event['lon']
            proj = Proj( self.data.spatial_ref.crs_wkt )
            x, y = proj( lon, lat )
        else:
            x, y = event['x'], event['y']
        if 'label' in event:
            self.class_selector.set_active( event['label'] )
        return dict( c=self.selectedClass, x=x, y=y )

    def point_coords( self, point_index: int ) -> Dict:
        samples: xa.DataArray = self.block.getPointData().coords['samples']
        selected_sample: np.ndarray = samples[ point_index ].values
        return dict( y = selected_sample[1], x = selected_sample[0] )

    def mark_point( self, point_index: int, transient: bool ):
        marker = self.block.pindex2coords(point_index)
        self.add_marker( dict( c=0, **marker), transient, labeled=False )

    def setBlock( self, block_coords: Tuple[int], **kwargs ) -> Block:
        print( f"LabelingConsole setBlock: {block_coords}")
        self.block: Block = self.tile.getBlock( *block_coords, init_graph=True, **self.umgr.conf )
        if self.block is not None:
            dataManager.config.setValue( 'block/indices', block_coords )
            self.nFrames = self.data.shape[0]
            self.band_axis = kwargs.pop('band', 0)
            self.z_axis_name = self.data.dims[self.band_axis]
            self.x_axis = kwargs.pop('x', 2)
            self.x_axis_name = self.data.dims[self.x_axis]
            self.y_axis = kwargs.pop('y', 1)
            self.y_axis_name = self.data.dims[self.y_axis]

            self.add_plots(**kwargs)
            self.add_slider(**kwargs)
            self.initLabels()

            self.google = GoogleMaps( self.block )
            self.umgr.clear_pointcloud()
            self.update_plot_axis_bounds()
            self.plot_markers_image()
            self.update_plots()

        return self.block

    def getNewImage(self):
        return self.new_image

    def getTile(self):
        return self.tile

    def download_google_map(self, type: str, *args, **kwargs):
        self.new_image = self.google.get_tiled_google_map( type, self.google_maps_zoom_level )

    def update_plot_axis_bounds( self ):
        if self.plot_axes is not None:
            self.plot_axes.set_xlim( self.block.xlim )
            self.plot_axes.set_ylim( self.block.ylim )

    def run_task(self, executable: Callable, messsage: str, *args, **kwargs ):
        task = Task( executable, *args, **kwargs )
        taskRunner.start( task, messsage )

    def computeMixingSpace(self, *args, **kwargs):
        labels: xa.DataArray = self.getExtendedLabelPoints()
        self.umgr.computeMixingSpace( self.block, labels, **kwargs )
        self.plot_markers_volume()

    def build_model(self, *args, **kwargs):
        if self.block is None:
            Task.taskNotAvailable( "Workflow violation", "Must load a block first", **kwargs )
        else:
            labels: xa.DataArray = self.getExtendedLabelPoints()
            self.umgr.embed( self.block, labels, **kwargs )
            self.plot_markers_volume()

    def learn_classification( self, *args, **kwargs  ):
        t0 = time.time()
        if self.block is None:
            Task.taskNotAvailable( "Workflow violation", "Must load a block and spread some labels first", **kwargs )
        else:
            ndim = kwargs.get('ndim',self.umgr.iparm("svm/ndim"))
            full_labels: xa.DataArray = self.getExtendedLabelPoints()
            embedding, labels = self.umgr.learn( self.block, full_labels, ndim, **kwargs )
            if embedding is not None:
                t1 = time.time()
                print(f"Computed embedding[{ndim}] (shape: {embedding.shape}) in {t1 - t0} sec")
                score = self.get_svc(**kwargs).fit( embedding.values, labels.values, **kwargs )
                if score is not None:
                    print(f"Fit SVC model (score shape: {score.shape}) in {time.time() - t1} sec")

    def get_svc( self, **kwargs ):
        type = kwargs.get( 'svc_type', 'SVCL' )
        if self.svc == None:
            self.svc = SVC.instance( type )
        return self.svc

    def apply_classification( self, *args, **kwargs ):
        embedding: Optional[xa.DataArray] = self.umgr.apply( self.block, **kwargs )
        if embedding is not None:
            callbacks = Callbacks( kwargs )
            prediction: np.ndarray = self.get_svc().predict( embedding.values, **kwargs )
            sample_labels = xa.DataArray( prediction, dims=['samples'], coords=dict( samples=embedding.coords['samples'] ) )
            self.plot_label_map( sample_labels )

    def initLabels(self):
        nodata_value = -2
        template = self.block.data[0].squeeze( drop=True )
        self.labels: xa.DataArray = xa.full_like( template, -1, dtype=np.int16 ).where( template.notnull(), nodata_value )
        self.labels.attrs['_FillValue'] = nodata_value
        self.labels.name = self.block.data.name + "_labels"
        self.labels.attrs[ 'long_name' ] = [ "labels" ]

    def clearLabels( self, ask_permission = True ):
        if ask_permission and (len(self.marker_list) > 0):
            buttonReply = QMessageBox.question( None, 'Hyperclass', "Are you sure you want to delete all current labels?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if buttonReply == QMessageBox.No: return
        self.initLabels()
        if len(self.marker_list) > 0:
            self.marker_list = []
            self.update_marker_plots()
            self.plot_label_map( self.getLabeledPointData() )
            self.block.flow.clear()
            self.labels_image.set_alpha(0.0)
            self.umgr.reset_markers()
            self.spectral_plot.clear()

    def updateLabelsFromMarkers(self):
        print(f"Updating {len(self.marker_list)} labels")
        self.clear_transients()
        for marker in self.marker_list:
            [y, x, c] = [marker[k] for k in ['y', 'x', 'c']]
            index = self.block.coords2indices(y, x)
            try:
                self.labels[ index['iy'], index['ix'] ] = c
            except:
                print( f"Skipping out of bounds label at local row/col coords {index['iy']} {index['ix']}")

    def getLabeledPointData( self, update = True ) -> xa.DataArray:
        if update: self.updateLabelsFromMarkers()
        labeledPointData = dataManager.raster2points( self.labels )
        return labeledPointData

    def getExtendedLabelPoints( self ) -> xa.DataArray:
        if self.label_map is None: return self.getLabeledPointData( True )
        return dataManager.raster2points( self.label_map )

    @property
    def data(self):
        return None if self.block is None else self.block.data

    @property
    def class_labels(self):
        return self.umgr.class_labels

    @property
    def class_colors(self) -> Dict[str,List[float]]:
        return self.umgr.class_colors

    @property
    def toolbarMode(self) -> str:
        return self.toolbar.mode

    @classmethod
    def time_merge( cls, data_arrays: List[xa.DataArray], **kwargs ) -> xa.DataArray:
        time_axis = kwargs.get('time',None)
        frame_indices = range( len(data_arrays) )
        merge_coord = pd.Index( frame_indices, name=kwargs.get("dim","time") ) if time_axis is None else time_axis
        result: xa.DataArray =  xa.concat( data_arrays, dim=merge_coord )
        return result

    def setup_plot(self, **kwargs):
        self.plot_grid: GridSpec = self.figure.add_gridspec( 4, 4 )
        self.plot_axes = self.figure.add_subplot( self.plot_grid[:, 0:-1] )
        self.figure.suptitle(f"Point Labeling Console",fontsize=14)
        for iC in range(2):
            y0,y1 = 2*iC, 2*(iC+1)
            self.control_axes[iC] = self.figure.add_subplot( self.plot_grid[y0:y1, -1] )
            self.control_axes[iC].xaxis.set_major_locator(plt.NullLocator())
            self.control_axes[iC].yaxis.set_major_locator(plt.NullLocator())
        self.slider_axes: Axes = self.figure.add_axes([0.1, 0.01, 0.8, 0.04])  # [left, bottom, width, height]
        self.plot_grid.update( left = 0.05, bottom = 0.1, top = 0.95, right = 0.95 )

    def invert_yaxis(self):
        self.plot_axes.invert_yaxis()

    def get_xy_coords(self,  ) -> Tuple[ np.ndarray, np.ndarray ]:
        return self.get_coord(self.x_axis ), self.get_coord( self.y_axis )

    def get_anim_coord(self ) -> np.ndarray:
        return self.get_coord( 0 )

    def get_coord(self,   iCoord: int ) -> np.ndarray:
        return self.data.coords[  self.data.dims[iCoord] ].values

    def create_image(self, **kwargs ) -> AxesImage:
        z: xa.DataArray =  self.data[ 0, :, : ]
        colorbar = kwargs.pop( 'colorbar', False )
        image: AxesImage =  dataManager.plotRaster( z, ax=self.plot_axes, colorbar=colorbar, alpha=0.5, **kwargs )
        self._cidpress = image.figure.canvas.mpl_connect('button_press_event', self.onMouseClick)
        self._cidrelease = image.figure.canvas.mpl_connect('button_release_event', self.onMouseRelease )
        self.plot_axes.callbacks.connect('ylim_changed', self.on_lims_change)
        overlays = kwargs.get( "overlays", {} )
        for color, overlay in overlays.items():
            overlay.plot( ax=self.plot_axes, color=color, linewidth=2 )
        return image

    def on_lims_change(self, ax ):
         if ax == self.plot_axes:
             (x0, x1) = ax.get_xlim()
             (y0, y1) = ax.get_ylim()
             print(f"ZOOM Event: Updated bounds: ({x0},{x1}), ({y0},{y1})")
         for listener in self.navigation_listeners:
             listener.set_axis_limits( ax.get_xlim(), ax.get_ylim() )

    def update_plots(self):
        if self.image is not None:
            frame_data: xa.DataArray = self.data[ self.currentFrame ]
            self.image.set_data( frame_data.values  )
            drange = dataManager.get_color_bounds( frame_data )
            self.image.set_norm( Normalize( **drange ) )
            self.image.set_extent( self.block.extent() )
            plot_name = os.path.basename(self.data.name)
            self.plot_axes.title.set_text(f"{plot_name}: Band {self.currentFrame+1}" )
            self.plot_axes.title.set_fontsize( 8 )
        if self.labels_image is not None:
            self.labels_image.set_extent( self.block.extent() )
            self.labels_image.set_alpha(0.0)

    def addNavigationListener( self, listener ):
        self.navigation_listeners.append( listener )

    def onMouseRelease(self, event):
        if event.inaxes ==  self.plot_axes:
             if   self.toolbarMode == "zoom rect":   self.toolbar.zoom()
             elif self.toolbarMode == "pan/zoom":    self.toolbar.pan()

        #         for listener in self.navigation_listeners:
        #             listener.set_axis_limits( self.plot_axes.get_xlim(), self.plot_axes.get_ylim() )

    def onMouseClick(self, event):
        if event.xdata != None and event.ydata != None:
            if not self.toolbarMode and (event.inaxes == self.plot_axes) and (self.key_mode == None):
                rightButton: bool = int(event.button) == self.RIGHT_BUTTON
                marker = dict( y=event.ydata, x=event.xdata, c=self.selectedClass )
                self.add_marker( marker, rightButton )
                self.dataLims = event.inaxes.dataLim

    def clear_transients(self):
        self.marker_list = [ marker for marker in self.marker_list if marker not in self.transients ]
        self.spectral_plot.clear_current_line()

    def add_marker(self, marker: Dict, transient: bool, **kwargs ):
        self.clear_transients()
        if transient: self.transients = [ marker ]
        self.marker_list.append( marker )
        taskRunner.start( Task( self.plot_marker, marker ), f"Plot marker at {marker['y']} {marker['x']}" )
        self.plot_markers_image( **kwargs )
        self.plot_spectrum( marker )

    def plot_spectrum(self, marker ):
        [y, x, c] = [marker[k] for k in ['y', 'x', 'c']]
        color = self.get_color(c)
        pindex = self.block.coords2pindex( y, x )
        if pindex >= 0:
            pdata = self.block.getPointData( )
            self.spectral_plot.plot_spectrum( pindex, pdata[pindex], color )

    def undo_marker_selection(self, **kwargs ):
        if len( self.marker_list ):
            self.marker_list.pop()
            self.update_marker_plots( **kwargs )

    def update_marker_plots( self, **kwargs ):
        taskRunner.start( Task(self.plot_markers_image, **kwargs ), f"Plot markers" )
        taskRunner.start( Task(self.plot_markers_volume, reset=True, **kwargs ), f"Plot markers")

    def spread_labels(self, *args, **kwargs):
        if self.block is None:
            Task.taskNotAvailable( "Workflow violation", "Must load a block and label some points first", **kwargs )
        else:
            print( "Submitting training set" )
            labels: xa.DataArray = self.getLabeledPointData()
            sample_labels: Optional[xa.DataArray] = self.block.flow.spread( labels, self.flow_iterations, **kwargs )
            if sample_labels is not None:
                self.plot_label_map( sample_labels )

    def plot_label_map(self, sample_labels: xa.DataArray, **kwargs ):
        self.label_map: xa.DataArray =  sample_labels.unstack(fill_value=-2).astype(np.int16)
        extent = dataManager.extent( self.label_map )
        label_plot = self.label_map.where( self.label_map >= 0, 0 )
        class_alpha = kwargs.get( 'alpha', 0.7 )
        if self.labels_image is None:
            label_map_colors: List = [ [ ic, label, color[0:3] + [class_alpha] ] for ic, (label, color) in enumerate(self.class_colors.items()) ]
            self.labels_image = dataManager.plotRaster( label_plot, colors=label_map_colors, ax=self.plot_axes, colorbar=False )
        else:
            self.labels_image.set_data( label_plot.values  )
            self.labels_image.set_alpha(class_alpha  )

        self.labels_image.set_extent( extent )
        taskRunner.start( Task( self.color_pointcloud, sample_labels), "Plot labels" )

    def show_labels(self):
        if self.labels_image is not None:
            self.labels_image.set_alpha(1.0)
            self.update_canvas()

    def color_pointcloud(self, sample_labels: xa.DataArray, **kwargs ):
        self.umgr.color_pointcloud( sample_labels, **kwargs )

    def get_layer(self, layer_id: str ):
        if layer_id == "bands": return self.image
        if layer_id == "labels": return self.labels_image
        raise Exception( f"Unrecognized layer: {layer_id}")

    def update_image_alpha( self, layer: str, increase: bool, *args, **kwargs ):
        image = self.get_layer( layer )
        if image is not None:
            current = image.get_alpha()
            if increase:   new_alpha = min( 1.0, current + 0.1 )
            else:          new_alpha = max( 0.0, current - 0.1 )
            print( f"Update Image Alpha: {new_alpha}")
            image.set_alpha( new_alpha )
            self.figure.canvas.draw_idle()

    def update_point_sizes( self, increase: bool, *args, **kwargs  ):
        print( " ...update_point_sizes...  ")
        self.umgr.update_point_sizes( increase )
        Task.mainWindow().refresh_points()

    def get_color(self, class_index: int = None ) -> List[float]:
        if class_index is None: class_index = self.selectedClass
        return self.class_colors[self.class_labels[ class_index ]]

    def clear_unlabeled(self):
        if self.marker_list:
            self.marker_list = [ marker for marker in self.marker_list if marker['c'] > 0 ]

    def get_markers( self, **kwargs ) -> Tuple[ List[float], List[float], List[List[float]] ]:
        ycoords, xcoords, colors = [], [], []
#        labeled = kwargs.get( 'labeled', True )
        if self.marker_list:
            for marker in self.marker_list:
                [y, x, c] = [ marker[k] for k in ['y', 'x', 'c'] ]
                if self.block.inBounds(y,x):   #  and not ( labeled and (c==0) ):
                    ycoords.append(y)
                    xcoords.append(x)
                    colors.append( self.get_color(c) )
        return ycoords, xcoords, colors

    def plot_markers_image(self, **kwargs ):
        if self.marker_plot:
            ycoords, xcoords, colors = self.get_markers( **kwargs )
            self.marker_plot.set_offsets(np.c_[xcoords, ycoords])
            self.marker_plot.set_facecolor(colors)

    def plot_markers_volume(self, **kwargs):
        ycoords, xcoords, colors = self.get_markers( **kwargs )
        if len(xcoords):
            self.umgr.plot_markers( self.block, ycoords, xcoords, colors, **kwargs )
        else:
            reset = kwargs.get('reset', False)
            if reset: self.umgr.reset_markers()

    def plot_marker(self, marker: Dict, **kwargs ):
        self.umgr.plot_markers( self.block, [marker['y']], [marker['x']], [ self.get_color(marker['c']) ], **kwargs )

    def update_canvas(self):
        self.figure.canvas.draw_idle()

    def read_markers(self):
        dataManager.markers.readMarkers()
        if dataManager.markers.hasData:
            self.marker_list = dataManager.markers.markers
            self.umgr.class_labels = dataManager.markers.names
            self.umgr.class_colors = dataManager.markers.colors
            print(f"Reading {len(self.marker_list)} point labels from file { dataManager.markers.file_path}")

    def write_markers(self):
        print(f"Writing {len(self.marker_list)} point labels to file {dataManager.markers.file_path}")
        dataManager.markers.writeMarkers(self.class_labels, self.class_colors, self.marker_list)

    def mpl_pick_marker( self, event: PickEvent ):
        rightButton: bool = int(event.mouseevent.button) == self.RIGHT_BUTTON
        if ( event.name == "pick_event" ) and ( event.artist == self.marker_plot ) and rightButton: #  and ( self.key_mode == Qt.Key_Shift ):
            self.delete_marker( event.mouseevent.ydata, event.mouseevent.xdata )
            self.update_marker_plots()


    def delete_marker(self, y, x ):
        pindex = self.block.coords2pindex( y, x )
        if len( self.marker_list ):
            current_pindices = []
            new_marker_list = []
            for marker in self.marker_list:
                pindex1 = self.block.coords2pindex(marker['y'], marker['x'])
                if (pindex1 != pindex) and ( pindex1 not in current_pindices ):
                    new_marker_list.append( marker )
                    current_pindices.append( pindex1 )
                else:
                    print(f"Marker[{pindex1}] deleted at [{y} {x}]" )
            self.marker_list = new_marker_list
        print(f"#Markers remaining = {len(self.marker_list)}")

    def initPlots(self, **kwargs):
        self.add_plots( **kwargs )

    def add_plots(self, **kwargs ):
        if self.image is None:
            self.image = self.create_image(**kwargs)
            self.marker_plot = self.plot_axes.scatter( [], [], s=50, zorder=2, alpha=1, picker=True )
            self.marker_plot.set_edgecolor([0, 0, 0])
            self.marker_plot.set_linewidth(2)
            self.figure.canvas.mpl_connect('pick_event', self.mpl_pick_marker )
            self.plot_markers_image()

    def add_slider(self,  **kwargs ):
        if self.slider is None:
            self.slider = PageSlider( self.slider_axes, self.nFrames )
            self.slider_cid = self.slider.on_changed(self._update)

    def add_selection_controls( self, controls_window=0 ):
        cax = self.control_axes[controls_window]
        cax.title.set_text('Class Selection')
        self.class_selector = ColoredRadioButtons( cax, self.class_labels, list(self.class_colors.values()), active=self.currentClass )

    def wait_for_key_press(self):
        keyboardClick = False
        while keyboardClick != True:
            keyboardClick = plt.waitforbuttonpress()

    @property
    def selectedClass(self) -> int:
        return self.class_labels.index( self.class_selector.value_selected )

    @property
    def selectedClassLabel(self) -> str:
        return self.class_selector.value_selected

    def _update( self, val ):
        if self.slider is not None:
            tval = self.slider.val
            self.currentFrame = int( tval )
            self.update_plots()

    def show(self):
        plt.show()

    def __del__(self):
        self.exit()

    def exit(self):
        self.write_markers()

