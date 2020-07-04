from PyQt5.QtWidgets import QWidget, QAction, QVBoxLayout,  QHBoxLayout, QRadioButton, QLabel, QPushButton, QFrame
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from collections import OrderedDict
from hyperclass.gui.events import EventClient, EventMode
from PyQt5.QtCore import Qt
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import collections.abc
from functools import partial
import xarray as xa
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

def format_colors( classes: List[Tuple[str,Union[str,List[float]]]] ) -> List[List[float]]:
    test_item = classes[0][1]
    if isinstance(test_item, str):
        return [  h2c(color)  for (label,color) in classes ]
    elif isinstance( test_item, collections.abc.Sequence ) and isIntRGB( test_item ):
        return [ [ c/255 for c in color ] for (label,color) in classes ]
    else:
        return [ color for (label,color) in classes ]

def set_alphas( colors, alpha ):
    return [ set_alpha(color, alpha) for color in colors ]

def set_alpha( color, alpha ):
    return color[:3] + [alpha]

class Marker:
    def __init__(self, location: List[float], color: List[float], pid: int, cid: int ):
        self.location = location
        self.color = color
        self.cid = cid
        self.pid = pid

    def isTransient(self):
        return self.cid == 0

class LabelsManager(QObject,EventClient):
    update_signal = pyqtSignal()

    def __init__( self ):
        from hyperclass.graph.flow import ActivationFlow
        QObject.__init__( self )
        self._colors = None
        self._labels = None
        self.buttons: List[QRadioButton] = []
        self.selectedClass = 0
        self.selectedColor = [1.0,1.0,1.0]
        self._markers: List[Marker] = []
        self._flow: ActivationFlow = None
        self._labels_data: xa.DataArray = None
        self.n_spread_iters = 1

    def initLabelsData( self, point_data: xa.DataArray ):
        nodata_value = -1
        template = point_data[:,0].squeeze( drop=True )
        self._labels_data: xa.DataArray = xa.full_like( template, 0, dtype=np.int32 ).where( template.notnull(), nodata_value )
        self._labels_data.attrs['_FillValue'] = nodata_value
        self._labels_data.name = point_data.attrs['dsid'] + "_labels"
        self._labels_data.attrs[ 'long_name' ] = [ "labels" ]

    def processEvent( self, event: Dict ):
        from hyperclass.data.events import dataEventHandler
        from hyperclass.graph.flow import activationFlowManager
        if dataEventHandler.isDataLoadEvent(event):
            point_data = dataEventHandler.getPointData( event )
            self.initLabelsData( point_data )
            self._flow = activationFlowManager.getActivationFlow( point_data )

    def updateLabels(self):
        for marker in self._markers:
            self._labels_data[ marker.pid ] = marker.cid

    @classmethod
    def getFilteredLabels(self, labels: np.ndarray, mask = None ) -> np.ndarray:
        indices = np.arange(labels.shape[0])
        indexed_labels = np.vstack( [indices, labels] ).transpose()
        selection = mask if mask is not None else (labels > 0)
        return indexed_labels[selection]

    def spread(self) -> Optional[xa.DataArray]:
        if self._flow is None:
            event = dict( event="message", type="warning", title='Workflow Message', caption="Awaiting task completion", msg="The data has not yet been loaded" )
            self.submitEvent( event, EventMode.Gui )
            return None
        self.updateLabels()
        return self._flow.spread( self._labels_data, self.n_spread_iters )

    def clearTransient(self):
        if len(self._markers) > 0 and self._markers[-1].cid == 0:
            self._markers.pop(-1)

    def clearMarkers(self):
        self._markers = []
        event = dict( event="labels", type="clear" )
        self.submitEvent( event, EventMode.Gui )

    def addMarker(self, marker: Marker ):
        self.clearTransient()
        self._markers.append(marker)

    def popMarker(self) -> Marker:
        marker = self._markers.pop( -1 )
        event = dict( event="labels", type="undo", marker=marker )
        self.submitEvent( event, EventMode.Gui )
        return marker

    def getMarkers( self ) -> List[Marker]:
        return self._markers

    @property
    def selectedLabel(self):
        return self._labels[ self.selectedClass ]

    @property
    def colors(self):
        return self._colors

    @property
    def labels(self):
        return self._labels

    def setLabels(self, labels: List[Tuple[str, List[float]]], **kwargs):
        unlabeled_color = kwargs.get( 'unlabeled', [1.0, 1.0, 0.0, 1.0] )
        label_list = [ ('Unlabeled', unlabeled_color ) ] + labels
        self._colors = format_colors( label_list )
        self._labels = [ item[0] for item in label_list ]

    def toDict( self, alpha ) -> OrderedDict:
        labels_dict = OrderedDict()
        for index, label in enumerate(self._labels):
            labels_dict[ label ] = set_alpha( self._colors[index], alpha )
        return labels_dict

    def gui(self, **kwargs ):
        self.show_unlabeled = kwargs.get( 'show_unlabeled', True )
        console = QWidget()
        console_layout = QVBoxLayout()
        console.setLayout( console_layout )
        radio_button_style = [ "border-style: outset", "border-width: 4px", "padding: 6px", "border-radius: 10px" ]

        labels_frame = QFrame( console )
        buttons_frame_layout = QVBoxLayout()
        labels_frame.setLayout( buttons_frame_layout )
        labels_frame.setFrameStyle( QFrame.StyledPanel | QFrame.Raised )
        labels_frame.setLineWidth( 3 )
        console_layout.addWidget( labels_frame )
        title = QLabel( "Classes" )
        title.setStyleSheet("font-weight: bold; color: black; font: 16pt" )
        buttons_frame_layout.addWidget( title )

        for index, label in enumerate(self._labels):
            if (index > 0) or self.show_unlabeled:
                radiobutton = QRadioButton( label, console )
                radiobutton.index = index
                raw_color = [str(int(c * 155.99)) for c in self._colors[index]]
                qcolor = [ str(150+int(c*105.99)) for c in self._colors[index] ]
                style_sheet = ";".join( radio_button_style + [ f"background-color:rgb({','.join(qcolor)})", f"border-color: rgb({','.join(raw_color)})" ] )
                radiobutton.setStyleSheet( style_sheet )
                radiobutton.toggled.connect(self.onClicked)
                buttons_frame_layout.addWidget( radiobutton )
                self.buttons.append( radiobutton )

        buttons_frame = QFrame( console )
        buttons_frame_layout = QVBoxLayout()
        buttons_frame.setLayout( buttons_frame_layout )
        buttons_frame.setFrameStyle( QFrame.StyledPanel | QFrame.Raised )
        buttons_frame.setLineWidth( 3 )
        console_layout.addWidget( buttons_frame )
        title = QLabel( "Actions" )
        title.setStyleSheet("font-weight: bold; color: black; font: 16pt" )
        buttons_frame_layout.addWidget( title )

        for action in [ 'Mark', 'Neighbors', 'Undo', 'Clear' ]:
            pybutton = QPushButton( action, console )
            pybutton.clicked.connect( partial( self.execute,action)  )
            buttons_frame_layout.addWidget(pybutton)

        console_layout.addStretch( 1 )
        self.buttons[0].setChecked( True )
        self.activate_event_listening()
        return console

    def execute(self, action: str ):
        print( f"Executing action {action}" )
        etype = action.lower()
        if etype == "undo":     self.popMarker()
        elif etype == "clear":  self.clearMarkers()
        elif etype == "neighbors":
            new_classes: Optional[xa.DataArray] = self.spread()
            if new_classes is not None:
                event = dict( event="labels", type="spread", labels=new_classes )
                self.submitEvent( event, EventMode.Gui )
        elif etype == "mark":
            event = dict( event='gui', type="mark" )
            self.submitEvent( event, EventMode.Gui )

    def onClicked(self):
        radioButton = self.sender()
        if radioButton.isChecked():
            self.selectedClass = radioButton.index
            self.selectedColor = self.colors[ radioButton.index ]
            print(f"Selected class {radioButton.index}")

labelsManager = LabelsManager()