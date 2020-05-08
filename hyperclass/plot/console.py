import matplotlib.widgets
import matplotlib.patches
from hyperclass.plot.widgets import ColoredRadioButtons, ButtonBox
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.gridspec import GridSpec, SubplotSpec
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
from  matplotlib.transforms import Bbox
from collections import OrderedDict
from hyperclass.umap.manager import UMAPManager
import matplotlib.pyplot as plt
from matplotlib.dates import num2date
from matplotlib.collections import PathCollection
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.graph.flow import ActivationFlow
from threading import  Thread
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from skimage.transform import ProjectiveTransform
import matplotlib as mpl
import pandas as pd
import xarray as xa
import numpy as np
from typing import List, Union, Dict, Callable, Tuple, Optional
import time, math, atexit, csv
from enum import Enum

def get_color_bounds( color_values: List[float] ) -> List[float]:
    color_bounds = []
    for iC, cval in enumerate( color_values ):
        if iC == 0: color_bounds.append( cval - 0.5 )
        else: color_bounds.append( (cval + color_values[iC-1])/2.0 )
    color_bounds.append( color_values[-1] + 0.5 )
    return color_bounds

class ADirection(Enum):
    BACKWARD = -1
    STOP = 0
    FORWARD = 1

class EventSource(Thread):

    def __init__( self, action: Callable, **kwargs ):
        Thread.__init__(self)
        self.event = None
        self.action = action
        self.interval = kwargs.get( "delay",0.01 )
        self.active = False
        self.running = True
        self.daemon = True
        atexit.register( self.exit )

    def run(self):
        while self.running:
            time.sleep( self.interval )
            if self.active:
                plt.pause( 0.05 )
                self.action( self.event )

    def activate(self, delay = None ):
        if delay is not None: self.interval = delay
        self.active = True

    def deactivate(self):
        self.active = False

    def exit(self):
        self.running = False

class PageSlider(matplotlib.widgets.Slider):

    def __init__(self, ax: Axes, numpages = 10, valinit=0, valfmt='%1d', **kwargs ):
        self.facecolor=kwargs.get('facecolor',"yellow")
        self.activecolor = kwargs.pop('activecolor',"blue" )
        self.stepcolor = kwargs.pop('stepcolor', "#ff6f6f" )
        self.animcolor = kwargs.pop('animcolor', "#6fff6f" )
        self.on_animcolor = kwargs.pop('on-animcolor', "#006622")
        self.fontsize = kwargs.pop('fontsize', 10)
        self.animation_controls = kwargs.pop('dynamic', True )
        self.maxIndexedPages = 24
        self.numpages = numpages
        self.init_anim_delay: float = 0.5   # time between timer events in seconds
        self.anim_delay: float = self.init_anim_delay
        self.anim_delay_multiplier = 1.5
        self.anim_state = ADirection.STOP
        self.axes = ax
        self.event_source = EventSource( self.step, delay = self.init_anim_delay )

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
        self.button_back.on_clicked(self.step_backward)
        self.button_forward.on_clicked(self.step_forward)

        if self.animation_controls:
            afax = divider.append_axes("left", size="5%", pad=0.05)
            asax = divider.append_axes("left", size="5%", pad=0.05)
            abax = divider.append_axes("left", size="5%", pad=0.05)
            self.button_aback    = matplotlib.widgets.Button( abax, label='$\u25C0$', color=self.animcolor, hovercolor=self.activecolor)
            self.button_astop = matplotlib.widgets.Button( asax, label='$\u25FE$', color=self.animcolor, hovercolor=self.activecolor)
            self.button_aforward = matplotlib.widgets.Button( afax, label='$\u25B6$', color=self.animcolor, hovercolor=self.activecolor)

            self.button_aback.label.set_fontsize(self.fontsize)
            self.button_astop.label.set_fontsize(self.fontsize)
            self.button_aforward.label.set_fontsize(self.fontsize)
            self.button_aback.on_clicked(self.anim_backward)
            self.button_astop.on_clicked(self.anim_stop)
            self.button_aforward.on_clicked(self.anim_forward)

    def reset_buttons(self):
        if self.animation_controls:
            for button in [ self.button_aback, self.button_astop, self.button_aforward ]:
                button.color = self.animcolor
            self.refesh()

    def refesh(self):
        self.axes.figure.canvas.draw()

    def start(self):
        self.event_source.start()

    def _update(self, event):
        super(PageSlider, self)._update(event)
        i = int(self.val)
        if i >=self.valmax: return
        self._colorize(i)

    def _colorize(self, i):
        for j in range(self.numpages):
            self.pageRects[j].set_facecolor(self.facecolor)
        self.pageRects[i].set_facecolor(self.activecolor)

    def step( self, event=None ):
        if   self.anim_state == ADirection.FORWARD:  self.forward(event)
        elif self.anim_state == ADirection.BACKWARD: self.backward(event)

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

    def step_forward(self, event=None):
        self.anim_stop()
        self.forward(event)

    def step_backward(self, event=None):
        self.anim_stop()
        self.backward(event)

    def anim_forward(self, event=None):
        if self.anim_state == ADirection.FORWARD:
            self.anim_delay = self.anim_delay / self.anim_delay_multiplier
            self.event_source.interval = self.anim_delay
        elif self.anim_state == ADirection.BACKWARD:
            self.anim_delay = self.anim_delay * self.anim_delay_multiplier
            self.event_source.interval = self.anim_delay
        else:
            self.anim_delay = self.init_anim_delay
            self.anim_state = ADirection.FORWARD
            self.event_source.activate( self.anim_delay )
            self.button_aforward.color = self.on_animcolor
            self.refesh()

    def anim_backward(self, event=None):
        if self.anim_state == ADirection.FORWARD:
            self.anim_delay = self.anim_delay * self.anim_delay_multiplier
            self.event_source.interval = self.anim_delay
        elif self.anim_state == ADirection.BACKWARD:
            self.anim_delay = self.anim_delay / self.anim_delay_multiplier
            self.event_source.interval = self.anim_delay
        else:
            self.anim_delay = self.init_anim_delay
            self.anim_state = ADirection.BACKWARD
            self.event_source.activate( self.anim_delay )
            self.button_aback.color = self.on_animcolor
            self.refesh()

    def anim_stop(self, event=None):
        if self.anim_state != ADirection.STOP:
            self.anim_delay = self.init_anim_delay
            self.anim_state = ADirection.STOP
            self.event_source.deactivate()
            self.reset_buttons()

class LabelingConsole:

    def __init__(self, tile: Tile, class_labels: List[ Tuple[str,List[float]]], **kwargs ):   # class_labels: [ [label, RGBA] ... ]
        self._debug = False
        self.tile = tile
        self.flow = ActivationFlow(**kwargs)
        self.setBlock( kwargs.pop( 'block', (0,0) ) )
        self._getClassLabels( class_labels )
        self.global_bounds: Bbox = None
        self.global_crange = None
        self.plot_axes: Axes = None
        self.figure: Figure = plt.figure()
        self.image: AxesImage = None
        self.training_points: PathCollection = None
        self.frame_marker: Line2D = None
        self.control_axes = {}
        self.setup_plot(**kwargs)
        self.dataLims = {}
        self.band_axis = kwargs.pop('band', 0)
        self.z_axis_name = self.data.dims[ self.band_axis]
        self.x_axis = kwargs.pop( 'x', 2 )
        self.x_axis_name = self.data.dims[ self.x_axis ]
        self.y_axis = kwargs.pop( 'y', 1 )
        self.y_axis_name = self.data.dims[ self.y_axis ]
        self.nFrames = self.data.shape[0]
        self.point_selection_x = []
        self.point_selection_y = []
        self.point_selection_c = []
        self.training_data = []
        self.currentFrame = 0
        self.currentClass = 0
        self.umgr = UMAPManager( tile, refresh = kwargs.pop( 'refresh', False ) )

        self.add_plots( **kwargs )
        self.add_slider( **kwargs )
        self.add_selection_controls( **kwargs )
        self.add_button_box( **kwargs )
        self.toolbar = self.figure.canvas.manager.toolbar
        self._update(0)

    def setBlock( self, block_coords: Tuple[int] ):
        self.block: Block = self.tile.getBlock( *block_coords )
        self.transform = ProjectiveTransform( np.array( list(self.block.data.transform) + [0, 0, 1] ).reshape(3, 3) )
        self.flow.setNodeData( self.block.getPointData() )
        self.clearLabels()

    def clearLabels(self):
        template = self.block.data[0]
        self.labels = xa.full_like(template, -1).where( template.notnull() )
        self.labels.name = self.block.data.name + "_labels"

    def getLabeledPointData(self):
        for ip, cx in enumerate( self.point_selection_x ):
            cy = self.point_selection_y[ip]
            c = self.point_selection_c[ip]
            iy, ix = self.tile.coords2index( cy, cx )
            self.labels[ iy, ix ] = c
        point_data = self.tile.dm.raster2points( self.labels )
        return point_data

    @property
    def data(self):
        return self.block.data

    def _getClassLabels(self, class_labels: List[ Tuple[str,Tuple[float]]] ):
        self.class_labels: List[str] = []
        self.class_colors: OrderedDict[str,Tuple[float]] = {}
        for elem in class_labels:
            self.class_labels.append( elem[0] )
            self.class_colors[ elem[0] ] = elem[1]

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
        g0 =  self.plot_grid[0, 0]
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

    def update_plots(self ):
        frame_data = self.data[ self.currentFrame]
        self.image.set_data( frame_data  )
        self.plot_axes.title.set_text(f"{self.data.name}: Band {self.currentFrame+1}" )

    def onMouseRelease(self, event):
        pass

    def onMouseClick(self, event):
        if event.xdata != None and event.ydata != None:
            if not self.toolbarMode:
                if event.inaxes ==  self.plot_axes:
                    self.add_point_selection( event )
                    self.dataLims = event.inaxes.dataLim

    def add_point_selection(self, event ):
        self.point_selection_x.append( event.xdata )
        self.point_selection_y.append( event.ydata )
        self.point_selection_c.append( self.selectedClass )
        self.plot_points()

    def undo_point_selection(self, event ):
        self.point_selection_x.pop()
        self.point_selection_y.pop()
        self.point_selection_c.pop()
        self.plot_points()

    def submit_training_set(self, event ):
        print( "Submitting training set")
        labels: xa.DataArray = self.getLabeledPointData()
        new_labels: xa.DataArray = self.flow.spread( labels, 3, to_raster = True )
        print(".")
        # label_map = self.tile.dm.raster2points()
        # label_mask = labels >=0
        # class_colors: List = list(self.class_colors.values())
        # class_indices: List = labels[ label_mask ].values.tolist()
        # labeled_samples: np.ndarray = embed[ label_mask ].data
        # label_colors: List = [ class_colors[int(ic)] for ic in class_indices ]
        # dsl = dict( data=labeled_samples, name="Labeled", color=label_colors, size=10 )
        # self.tile.dm.plot_pointclouds( [ dsu, dsl ] )

    def display_manifold(self, event ):
        print( "display_manifold")
        labels: xa.DataArray = self.getLabeledPointData()
        self.umgr.fit( labels, block = self.block )
        embed = self.umgr.embedding
        dsu = dict( data=embed.data, name=self.block.data.name, color=[0.5,0.5,0.5,0.5], size=1 )
        label_mask = labels >=0
        class_colors: List = list(self.class_colors.values())
        class_indices: List = labels[ label_mask ].values.tolist()
        labeled_samples: np.ndarray = embed[ label_mask ].data
        label_colors: List = [ class_colors[int(ic)] for ic in class_indices ]
        dsl = dict( data=labeled_samples, name="Labeled", color=label_colors, size=10 )
        self.tile.dm.plot_pointclouds( [ dsu, dsl ] )

    def plot_points(self):
        self.training_points.set_offsets( np.c_[ self.point_selection_x, self.point_selection_y ] )
        self.training_points.set_facecolor( [ self.class_colors[ self.class_labels[ic] ] for ic in self.point_selection_c ] )
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()

    @property
    def selectedColor(self):
        return self.class_colors[ self.selectedClass ]

    def write_training_data(self):
        for ip, c in enumerate( self.point_selection_c ):
            x = self.point_selection_x[ip]
            y = self.point_selection_x[ip]
            self.tile.dm.tdio.writeEntry( x, y, c )

    def datalims_changed(self ) -> bool:
        previous_datalims: Bbox = self.dataLims
        new_datalims: Bbox = self.plot_axes.dataLim
        return previous_datalims.bounds != new_datalims.bounds

    def add_plots(self, **kwargs ):
        self.image = self.create_image(**kwargs)
        self.training_points = self.plot_axes.scatter( [],[], s=50, zorder=2, alpha=1 )
        self.training_points.set_edgecolor( [0,0,0] )
        self.training_points.set_linewidth( 2 )

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
        actions = [ "Submit", "Undo" ]
        self.button_box = ButtonBox( cax, [3,3], actions )
        self.button_box.addCallback( actions[0], self.submit_training_set )
        self.button_box.addCallback( actions[1], self.undo_point_selection )


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
        self.slider.start()
        plt.show()

    def start(self):
        self.slider.start()

    def __del__(self):
        self.tile.dm.tdio.flush()

