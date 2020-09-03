from matplotlib.figure import Figure
from typing import List, Union, Dict, Callable, Tuple, Optional
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import *
from matplotlib.lines import Line2D
from matplotlib.backend_bases import PickEvent, MouseEvent
from hyperclass.util.config import tostr
from PyQt5.QtCore import *
from matplotlib.axes import Axes
from collections import OrderedDict
from hyperclass.data.events import dataEventHandler, DataType
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.gui.labels import labelsManager
import xarray as xa

class Spectrum:
    def __init__(self, band_values: List[float], color: List[float], cid: int ):
        self.bands = band_values
        self.color = color
        self.cid = cid

    def isTransient(self):
        return self.cid == 0

class SpectralCanvas( FigureCanvas ):

    def __init__(self, figure: Figure ):
        FigureCanvas.__init__( self, figure )
        self.figure = figure
        self.figure.patch.set_facecolor('#e2e2e2')

class SpectralPlot(QObject,EventClient):
    update_signal = pyqtSignal()

    def __init__( self, active: bool = True, **kwargs ):
        QObject.__init__(self)
        self.figure: Optional[Figure] = None
        self._active = active
        self.overlay = kwargs.get('overlay', False )
        self.axes: Optional[Axes] = None
        self.lines: OrderedDict[ int, Line2D ] = OrderedDict()
        self.current_line: Optional[Line2D] = None
        self.current_pid = -1
        self.current_cid = -1
        self.norm = None

        self.plotx: xa.DataArray = None
        self.nploty: xa.DataArray = None
        self.ploty: xa.DataArray = None

        self.rplotx: xa.DataArray = None
        self.rploty: xa.DataArray = None

        self._use_reduced_data = False
        self.marker: Line2D = None
        self._gui = None
        self._titles = None
        self.parms = kwargs
        self.update_signal.connect( self.update )

    def useReducedData(self, useReducedData: bool ):
        if self._use_reduced_data != useReducedData:
            self._use_reduced_data = useReducedData
            self.plot_spectrum()
            self.update()

    def toggleUseReducedData( self ):
        self._use_reduced_data = not self._use_reduced_data
        self.plot_spectrum()
        self.update()

    def activate( self, active: bool  ):
        self._active = active
        if self._active and (self.current_pid >= 0):
            event = dict( event="pick", type="graph", pids=[self.current_pid], cid=0 )
            self.submitEvent(event, EventMode.Gui)

    def init( self ):
        self.figure = Figure(constrained_layout=True)
        self.axes = self.figure.add_subplot(111)
        self.axes.title.set_fontsize(14)
        self.activate_event_listening()

    def configure(self, event: Dict ):
        type = self.ploty.attrs.get('type')
        self.axes.set_facecolor((0.0, 0.0, 0.0))
        if type == 'spectra':
            plot_metadata = dataEventHandler.getMetadata( event )
            self._titles = {}
            for index in range( plot_metadata[0].shape[0] ):
                self._titles[index] = "[" + ",".join( [ tostr(pm.values[index]) for pm in plot_metadata ] ) + "]"
        else:
            self.figure.patch.set_facecolor( (0.0, 0.0, 0.0) )
            self.axes.axis('off')
            self.axes.get_yaxis().set_visible(False)
            self.figure.set_constrained_layout_pads( w_pad=0., h_pad=0. )

    def gui(self, parent) :
        if self._gui is None:
            self.init( )
            self._gui = SpectralCanvas( self.figure )
            self._gui.setParent(parent)
            self._gui.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._gui.setContentsMargins( 0, 0, 0, 0 )
            self._gui.updateGeometry()
            self._gui.mpl_connect('button_press_event', self.mouseClick)

        return self._gui

    def mouseClick(self, event: MouseEvent):
        if (self.axes is not None) and ( self.current_pid >= 0 ) and ( self.ploty is not None ) and self._active:
            print(f"SpectralPlot.mousePressEvent: [{event.x}, {event.y}] -> [{event.xdata}, {event.ydata}]" )
            title = f" {event.xdata:.2f}: {event.ydata:.3f} "
            self.axes.set_title( title, {'fontsize': 10 }, 'right' )
            self.update_marker( event.xdata )
            self.update()

    def normalize(self):
        self.norm = self.ploty.attrs.get("norm", None)
        if self.norm == "median":
            self.nploty =  self.ploty / self.ploty.median( axis = 1 )
        elif self.norm == "mean":
            self.nploty =  self.ploty / self.ploty.mean( axis=1 )
        else:
            self.nploty =  self.ploty

    def processEvent(self, event: Dict ):
        super().processEvent(event)
        if dataEventHandler.isDataLoadEvent(event):
            plot_data = dataEventHandler.getPointData( event, DataType.Plot )
            reduced_data = dataEventHandler.getPointData( event, DataType.Embedding )
            if isinstance(plot_data, dict): self.plotx, self.ploty = plot_data["plotx"], plot_data["ploty"]
            else:                           self.plotx, self.ploty = plot_data.band,     plot_data
            self.rplotx, self.rploty = reduced_data['model'], reduced_data
            if self.ploty.size > 0:
                self.normalize()
                self.configure( event )
        if event.get('event') == 'pick':
            if (event.get('type') in [ 'vtkpoint', 'directory', 'reference', 'plot' ]) and self._active:
                if  self.ploty is not None:
                    pids = [ row[1] for row in event.get('rows',[]) ]
                    pids = pids + event.get('pids',[])
                    for pid in pids:
                        if pid >= 0:
                            self.current_pid = pid
                            current_line = self.lines.get( self.current_pid, None )
                            if (current_line is not None) and (current_line.cid > 0):
                                self.current_cid = current_line.cid
                            else:
                                classification = event.get('classification',-1)
                                self.current_cid = classification if (classification > 0) else labelsManager.selectedClass
                            self.clear_transients()
                            print( f"SpectralPlot: pick event, pid = {self.current_pid}, cid = {self.current_cid}")
                            self.plot_spectrum()
                            if self._titles is not None:
                                self.axes.set_title( self._titles.get(self.current_pid,"*SPECTRA*" ), {'fontsize': 10 }, 'center' )
                            self.update_marker()
                            self.axes.set_title( "", {}, 'right' )
                            self.update_signal.emit()
        elif event.get('event') == 'gui':
            if event.get('type') =='reset':
                self.clear()

    def update_marker(self, new_xval = None ):
        if self.marker is not None:
            self.axes.lines.remove(self.marker)
            self.marker = None
        if new_xval is not None:
            self.marker = self.axes.axvline( new_xval, color="yellow", linewidth=1, alpha=0.75 )

    def plot_spectrum(self):
        if (self.current_pid >= 0) and (self.nploty is not None):
            color = labelsManager.colors[self.current_cid]
            if self._use_reduced_data:
                spectrum = self.rploty[self.current_pid].values
                x = self.rplotx[ self.current_pid ].values if self.rplotx.ndim == 2 else self.rplotx.values
            else:
                spectrum = self.nploty[self.current_pid].values
                x = self.plotx[ self.current_pid ].values if self.plotx.ndim == 2 else self.plotx.values
            self.ymax, self.ymin = spectrum.max(), spectrum.min()
            self.xmax, self.xmin = x.max(), x.min()
            self.axes.set_ylim(self.ymin, self.ymax)
            self.axes.set_xlim(self.xmin, self.xmax)
            linewidth = 2 if self.overlay else 1
            if len(color) == 4: color[3] = 1.0
            if self.current_line is not None:
                self.current_line.set_visible(False)
            self.current_line, = self.axes.plot( x, spectrum, linewidth=linewidth, color=color )
            print( f"SPECTRA BOUNDS: [ {self.xmin:.2f}, {self.xmax:.2f} ] -> [ {self.ymin:.2f}, {self.ymax:.2f} ]")
            self.current_line.color = color
            self.current_line.cid = self.current_cid
            self.lines[ self.current_pid ] = self.current_line

    def clear(self):
        self.lines = OrderedDict()
        self.current_line = None
        self.axes.clear()

    def clear_transients(self):
        if (self.current_line is not None):
            if (self.current_line.cid == 0) or not self.overlay:
                index, line = self.lines.popitem()
                line.remove()
                self.current_line = None
            else:
                self.current_line.set_linewidth(1)

    def remove_spectrum(self, index: int ):
        line: Line2D = self.lines[ index ]
        line.remove()
        del self.lines[ index ]

    def has_spectrum(self, index: int ):
        return index in self.lines

    @pyqtSlot()
    def update(self):
        if self._gui is not None:
            self.figure.canvas.draw_idle()
            self._gui.update()



class SpectralManager:

    def __init__(self):
        self.spectral_plots = []
        self._gui = None

    def gui(self, nSpectra: int, parent: QWidget ):
        if self._gui is None:
            self._gui = QTabWidget()
            for iS in range(nSpectra):
                spectral_plot = SpectralPlot(iS == 0)
                self.spectral_plots.append(spectral_plot)
                tabId = "Spectra" if iS == 0 else str(iS)
                self._gui.addTab( spectral_plot.gui(parent), tabId )
            self._gui.currentChanged.connect(self.activate_spectral_plot)
            self._gui.setTabEnabled(0, True)
        return self._gui

    def activate_spectral_plot( self, index: int ):
        for iS, plot in enumerate(self.spectral_plots):
            plot.activate( iS == index )

    def setSpectralUseReduced(self, useReducedData: bool ):
        for spectral_plot in self.spectral_plots:
            spectral_plot.useReducedData( useReducedData )

    def toggleSpectralUseReduced(self ):
        for spectral_plot in self.spectral_plots:
            spectral_plot.toggleUseReducedData()

    def addActions(self, menu: QMenu ):
        menuButton = QAction( "Toggle Spectral Reduced/Raw", self._gui )
        menuButton.setStatusTip( "Toggle Spectral Use Reduced/Raw Data"  )
        menuButton.triggered.connect(self.toggleSpectralUseReduced)
        menu.addAction( menuButton )

spectralManager = SpectralManager()