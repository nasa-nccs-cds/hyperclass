import matplotlib.widgets
import matplotlib.patches
from PyQt5.QtCore import Qt
from hyperclass.plot.widgets import ColoredRadioButtons, ButtonBox
from hyperclass.data.google import GoogleMaps
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.gridspec import GridSpec, SubplotSpec
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
from matplotlib.backend_bases import PickEvent, MouseEvent
from collections import OrderedDict
from hyperclass.umap.manager import UMAPManager
from functools import partial
import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.svm.manager import SVC
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
import pandas as pd
import xarray as xa
import numpy as np
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import time, math, atexit, csv

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

    def __init__(self, umgr: UMAPManager, **kwargs ):   # class_labels: [ [label, RGBA] ... ]
        self._debug = False
        self.currentFrame = 0
        self.image: Optional[AxesImage] = None
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

        self.figure: Figure = kwargs.pop( 'figure', None )
        self.google_figure: Figure = None
        if self.figure is None:
            self.figure = plt.figure()
        self.labels_image: Optional[AxesImage] = None
        self.flow_iterations = kwargs.get( 'flow_iterations', 5 )
        self.frame_marker: Optional[Line2D] = None
        self.control_axes = {}

        self.read_markers()
        block_index = umgr.tile.dm.config.getShape( 'block_index' )
        self.setBlock( kwargs.pop( 'block', block_index ), **kwargs )

        self.nFrames = self.data.shape[0]
        self.band_axis = kwargs.pop('band', 0)
        self.z_axis_name = self.data.dims[ self.band_axis]
        self.x_axis = kwargs.pop( 'x', 2 )
        self.x_axis_name = self.data.dims[ self.x_axis ]
        self.y_axis = kwargs.pop( 'y', 1 )
        self.y_axis_name = self.data.dims[ self.y_axis ]

        self.setup_plot(**kwargs)


        self.button_actions =  OrderedDict(model=   partial(self.run_task, self.build_model, "Computing embedding...", type=umgr.embedding_type ),
                                           spread=  self.spread_labels,
                                           undo=    self.undo_marker_selection,
                                           clear=   self.clearLabels,
                                           learn=   partial(  self.run_task, self.learn_classification,   "Learning class boundaries..." ),
                                           apply =  partial(  self.run_task, self.apply_classification,   "Applying learned classification..." )
                                           )

        google_actions = [[maptype, None, None, partial(self.run_task, self.download_google_map, "Accessing Landsat Image...", maptype, type='newfig')] for maptype in ['satellite', 'hybrid', 'terrain', 'roadmap']]
        self.menu_actions = OrderedDict( Layers = [ [ "Increase Labels Alpha", 'Ctrl+>', None, partial( self.update_image_alpha, "labels", True ) ],
                                                    [ "Decrease Labels Alpha", 'Ctrl+<', None, partial( self.update_image_alpha, "labels", False ) ],
                                                    [ "Increase Band Alpha",   'Alt+>',  None, partial( self.update_image_alpha, "bands", True ) ],
                                                    [ "Decrease Band Alpha",   'Alt+<',  None, partial( self.update_image_alpha, "bands", False ) ],
                                                    [ "Increase Point Sizes", 'Ctrl+}',  None, partial( self.update_point_sizes, True ) ],
                                                    [ "Decrease Point Sizes", 'Ctrl+{',  None, partial( self.update_point_sizes, False ) ],
                                                    OrderedDict( GoogleMaps=google_actions )  ]  )

        self.add_plots( **kwargs )
        self.add_slider( **kwargs )
        self.add_selection_controls( **kwargs )
        atexit.register(self.exit)
        self._update(0)

    @property
    def toolbar(self):
        return self.figure.canvas.toolbar

    @property
    def tile(self):
        return self.umgr.tile

    @property
    def transform(self):
        return self.block.transform

    def process_event( self, event: Dict ):
        print( f" LabelingConsole: process_event: {event}")
        if event['event'] == 'pick':
            if event['type'] == 'vtkpoint':
                point_index = event['pid']
                self.mark_point( point_index )
        elif event['event'] == 'key':
            if   event['type'] == "press":   self.key_mode = event['key']
            elif event['type'] == "release": self.key_mode = None

    def point_coords( self, point_index: int ) -> Dict:
        samples: xa.DataArray = self.block.getPointData().coords['samples']
        selected_sample: np.ndarray = samples[ point_index ].values
        return dict( y = selected_sample[1], x = selected_sample[0] )

    def mark_point( self, point_index: int ):
        marker = self.block.pindex2coords(point_index)
        self.add_marker( dict( c=0, **marker), labeled=False )

    def setBlock( self, block_coords: Tuple[int], **kwargs ):
        self.block: Block = self.tile.getBlock( *block_coords, init_graph=True, **self.umgr.conf )
        self.google = GoogleMaps( self.block )
        self.umgr.clear_pointcloud()
        self.update_plot_axis_bounds()
        self.plot_markers_image()
        self.clearLabels()
        self.update_plots()

    def getNewImage(self):
        return self.new_image

    def download_google_map(self, type: str, *args, **kwargs):
        self.new_image = self.google.get_tiled_google_map( type, self.google_maps_zoom_level )

    def update_plot_axis_bounds( self ):
        if self.plot_axes is not None:
            self.plot_axes.set_xlim( self.block.xlim )
            self.plot_axes.set_ylim( self.block.ylim )

    def run_task(self, executable: Callable, messsage: str, *args, **kwargs ):
        task = Task( executable, *args, **kwargs )
        taskRunner.start( task, messsage )

    def build_model(self, *args, **kwargs):
        labels: xa.DataArray = self.getExtendedLabelPoints()
        self.umgr.embed( self.block, labels, **kwargs )
        self.plot_markers_volume()

    def learn_classification( self, *args, **kwargs  ):
        t0 = time.time()
        ndim = kwargs.get('ndim',self.umgr.iparm("svc_ndim"))
        labels: xa.DataArray = self.getExtendedLabelPoints()
        embedding: xa.DataArray = self.umgr.learn( self.block, labels, ndim, **kwargs )
        t1 = time.time()
        print( f"Computed embedding[{ndim}] (shape: {embedding.shape}) in {t1-t0} sec")
        if embedding is not None:
            score = self.get_svc(**kwargs).fit( embedding.values, labels.values )
            print(f"Fit SVC model (score shape: {score.shape}) in {time.time() - t1} sec")

    def get_svc( self, **kwargs ):
        type = kwargs.get( 'svc_type', self.tile.dm.config["svc_type"] )
        if self.svc == None:
            self.svc = SVC.instance( type )
        return self.svc

    def apply_classification( self, *args, **kwargs ):
        embedding: Optional[xa.DataArray] = self.umgr.apply( self.block )
        if embedding is not None:
            prediction: np.ndarray = self.get_svc(**kwargs).predict( embedding.values )
            sample_labels = xa.DataArray( prediction, dims=['samples'], coords=dict( samples=embedding.coords['samples'] ) )
            self.plot_label_map( sample_labels, background=True )

    def clearLabels( self, event = None ):
        nodata_value = -2
        template = self.block.data[0].squeeze( drop=True )
        self.labels: xa.DataArray = xa.full_like( template, -1, dtype=np.int16 ).where( template.notnull(), nodata_value )
        self.labels.attrs['_FillValue'] = nodata_value
        self.labels.name = self.block.data.name + "_labels"
        self.labels.attrs[ 'long_name' ] = [ "labels" ]

    def updateLabelsFromMarkers(self):
        print(f"Updating {len(self.marker_list)} labels")
        for marker in self.marker_list:
            [y, x, c] = [marker[k] for k in ['y', 'x', 'c']]
            if c > 0:
                index = self.block.coords2indices(y, x)
                try:
                    self.labels[ index['iy'], index['ix'] ] = c
                except:
                    print( f"Skipping out of bounds label at local row/col coords {index['iy']} {index['ix']}")

    def getLabeledPointData( self, update = True ) -> xa.DataArray:
        if update: self.updateLabelsFromMarkers()
        labeledPointData = self.tile.dm.raster2points( self.labels )
        return labeledPointData

    def getExtendedLabelPoints( self ) -> xa.DataArray:
        if self.label_map is None: return self.getLabeledPointData( True )
        return self.tile.dm.raster2points( self.label_map )

    @property
    def data(self):
        return self.block.data

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
        for iC in range(4):
            self.control_axes[iC] = self.figure.add_subplot( self.plot_grid[iC, -1] )
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
        image: AxesImage =  self.tile.dm.plotRaster( z, ax=self.plot_axes, colorbar=colorbar, alpha=0.5, colorstretch=1.0, **kwargs )
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

    def update_plots(self):
        if self.image is not None:
            frame_data: xa.DataArray = self.data[ self.currentFrame ]
            self.image.set_data( frame_data.values  )
            self.image.set_extent( self.block.extent() )
            self.plot_axes.title.set_text(f"{self.data.name}: Band {self.currentFrame+1}" )
            self.plot_axes.title.set_fontsize( 8 )
        if self.labels_image is not None:
            self.labels_image.set_extent( self.block.extent() )
            self.labels_image.set_alpha(0.0)
        Task.mainWindow().refresh_image()

    def onMouseRelease(self, event):
        pass
        # if event.inaxes ==  self.plot_axes:
        #     for action in self.toolbar._actions.values():
        #         action.setChecked( False )

    def onMouseClick(self, event):
        if event.xdata != None and event.ydata != None:
            if not self.toolbarMode:
                if event.inaxes ==  self.plot_axes:
                    if (self.selectedClass > 0) and (self.key_mode == None):
                        marker = dict( y=event.ydata, x=event.xdata, c=self.selectedClass )
                        self.add_marker( marker )
                        self.dataLims = event.inaxes.dataLim

    def add_marker(self, marker: Dict, **kwargs ):
        is_unlabeled = (marker['c'] == 0)
        if is_unlabeled: self.clear_unlabeled()
        self.marker_list.append( marker )
        self.plot_markers_image( **kwargs )
        if is_unlabeled:    taskRunner.start( Task( self.plot_markers_volume, reset=True, labeled=False ), f"Plot markers" )
        else:               taskRunner.start( Task( self.plot_marker, marker ), f"Plot marker at {marker['y']} {marker['x']}" )

    def undo_marker_selection(self, **kwargs ):
        labeled = kwargs.pop( 'labeled', False )
        if len( self.marker_list ):
            self.marker_list.pop()
            self.update_marker_plots( labeled=labeled, **kwargs )

    def update_marker_plots( self, **kwargs ):
        self.plot_markers_image( **kwargs )
        taskRunner.start( Task(self.plot_markers_volume, reset=True, **kwargs ), f"Plot markers")

    def spread_labels(self, event):
        print( "Submitting training set" )
        labels: xa.DataArray = self.getLabeledPointData()
        sample_labels: xa.DataArray = self.block.flow.spread( labels, self.flow_iterations  )
        self.plot_label_map( sample_labels )

    def plot_label_map(self, sample_labels: xa.DataArray, **kwargs ):
        in_background = kwargs.get( 'background', False )
        self.label_map: xa.DataArray =  sample_labels.unstack(fill_value=-2).astype(np.int16)
        extent = self.tile.dm.extent( self.label_map )
        label_plot = self.label_map.where( self.label_map >= 0, 0 )
        class_alpha = kwargs.get( 'alpha', 0.7 )
        if self.labels_image is None:
            label_map_colors: List = [ [ ic, label, color[0:3] + [class_alpha] ] for ic, (label, color) in enumerate(self.class_colors.items()) ]
            self.labels_image = self.tile.dm.plotRaster( label_plot, colors=label_map_colors, ax=self.plot_axes, colorbar=False )
        else:
            self.labels_image.set_data( label_plot.values  )
            self.labels_image.set_alpha(class_alpha  )

        self.labels_image.set_extent( extent )
        if in_background:
            self.color_pointcloud(sample_labels)
        else:
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
        labeled = kwargs.get( 'labeled', True )
        if self.marker_list:
            for marker in self.marker_list:
                [y, x, c] = [ marker[k] for k in ['y', 'x', 'c'] ]
                if self.block.inBounds(y,x) and not ( labeled and (c==0) ):
                    ycoords.append(y)
                    xcoords.append(x)
                    colors.append( self.get_color(c) )
        return ycoords, xcoords, colors

    def plot_markers_image(self, **kwargs ):
        if self.marker_plot:
            ycoords, xcoords, colors = self.get_markers( **kwargs )
            self.marker_plot.set_offsets(np.c_[xcoords, ycoords])
            self.marker_plot.set_facecolor(colors)
            self.update_canvas()

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
        self.tile.dm.markers.readMarkers()
        if self.tile.dm.markers.hasData:
            self.marker_list = self.tile.dm.markers.markers
            self.umgr.class_labels = self.tile.dm.markers.names
            self.umgr.class_colors = self.tile.dm.markers.colors
            print(f"Reading {len(self.marker_list)} point labels from file { self.tile.dm.markers.file_path}")

    def write_markers(self):
        print(f"Writing {len(self.marker_list)} point labels ot file {self.tile.dm.markers.file_path}")
        self.tile.dm.markers.writeMarkers(self.class_labels, self.class_colors, self.marker_list)

    def mpl_pick_marker( self, event: PickEvent ):
        if ( event.name == "pick_event" ) and ( event.artist == self.marker_plot ) and ( self.key_mode == Qt.Key_Shift ):
            self.delete_marker( event.mouseevent.ydata, event.mouseevent.xdata )
            self.update_marker_plots()

    def delete_marker(self, y, x ):
        pindex = self.block.coords2pindex( y, x )
        if len( self.marker_list ):
            current_pindices = []
            new_marker_list = []
            for marker in self.marker_list:
                pindex1 = self.block.coords2pindex( marker['y'], marker['x'] )
                if (pindex1 != pindex) and ( pindex1 not in current_pindices ):
                    new_marker_list.append( marker )
                    current_pindices.append( pindex1 )
            self.marker_list = new_marker_list
        print(f"Marker deleted: [{y} {x}], #markers = {len(self.marker_list)}")

    def add_plots(self, **kwargs ):
        self.image = self.create_image(**kwargs)
        self.marker_plot = self.plot_axes.scatter( [], [], s=50, zorder=2, alpha=1, picker=True )
        self.marker_plot.set_edgecolor([0, 0, 0])
        self.marker_plot.set_linewidth(2)
        self.figure.canvas.mpl_connect('pick_event', self.mpl_pick_marker )
        self.plot_markers_image()

    def add_slider(self,  **kwargs ):
        self.slider = PageSlider( self.slider_axes, self.nFrames )
        self.slider_cid = self.slider.on_changed(self._update)

    def add_selection_controls( self, controls_window=0 ):
        cax = self.control_axes[controls_window]
        cax.title.set_text('Class Selection')
        self.class_selector = ColoredRadioButtons( cax, self.class_labels, list(self.class_colors.values()), active=self.currentClass )

    def add_button_box( self, buttons_window=1, **kwargs ):
        cax = self.control_axes[ buttons_window ]
        cax.title.set_text('Actions')
        actions = [ "Submit", "Undo", "Clear" ]
        self.button_box = ButtonBox( cax, [3,3], actions )
        self.button_box.addCallback(actions[0], self.spread_labels)
        self.button_box.addCallback(actions[1], self.undo_marker_selection)
        self.button_box.addCallback( actions[2], self.clearLabels )

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
        tval = self.slider.val
        self.currentFrame = int( tval )
        self.update_plots()

    def show(self):
        plt.show()

    def __del__(self):
        self.exit()

    def exit(self):
        self.write_markers()

