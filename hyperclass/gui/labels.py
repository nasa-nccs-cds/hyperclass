from PyQt5.QtWidgets import QWidget, QAction, QVBoxLayout,  QHBoxLayout, QRadioButton, QLabel, QPushButton, QFrame
from hyperclass.gui.events import EventClient
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from collections import OrderedDict
from hyperclass.gui.events import EventClient, EventMode
from PyQt5.QtCore import Qt
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import collections.abc
from functools import partial
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
    def __init__(self, location: List[float], color: List[float], cid: int ):
        self.location = location
        self.color = color
        self.cid = cid

    def isTransient(self):
        return self.cid == 0

class LabelsManager(QObject,EventClient):
    update_signal = pyqtSignal()

    def __init__( self ):
        QObject.__init__( self )
        self._colors = None
        self._labels = None
        self.buttons: List[QRadioButton] = []
        self.selectedClass = 0
        self.selectedColor = [1.0,1.0,1.0]

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
        return console

    def execute(self, action: str ):
        print( f"Executing action {action}" )
        event = dict( event='gui', type=action.lower() )
        self.submitEvent( event, EventMode.Gui )

    def onClicked(self):
        radioButton = self.sender()
        if radioButton.isChecked():
            self.selectedClass = radioButton.index
            self.selectedColor = self.colors[ radioButton.index ]
            print(f"Selected class {radioButton.index}")

labelsManager = LabelsManager()