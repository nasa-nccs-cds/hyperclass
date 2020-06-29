from PyQt5.QtWidgets import QWidget, QAction, QVBoxLayout,  QHBoxLayout, QRadioButton, QLabel, QPushButton, QFrame
from hyperclass.gui.events import EventClient
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from collections import OrderedDict
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

class LabelsManager(QObject,EventClient):
    update_signal = pyqtSignal()

    def __init__( self ):
        QObject.__init__( self )
        self._colors = None
        self._labels = None

    @property
    def colors(self):
        return self._colors

    @property
    def labels(self):
        return self._labels

    def setLabels(self, labels: List[Tuple[str, List[float]]]):
        label_list = [('Unlabeled', [1.0, 1.0, 1.0, 0.5])] + labels
        self._colors = format_colors( label_list )
        self._labels = [ item[0] for item in label_list ]

    def toDict( self, alpha ) -> OrderedDict:
        labels_dict = OrderedDict()
        for index, label in enumerate(self._labels):
            labels_dict[ label ] = set_alpha( self._colors[index], alpha )
        return labels_dict

    def gui(self):
        console = QWidget()
        console_layout = QVBoxLayout()
        console.setLayout( console_layout )
        radio_button_style = [ "border-style: outset", "border-width: 4px",  "border-color: beige",
                               "padding: 6px", "border-radius: 10px" ]
        labels_frame = QFrame( console )
        frame_layout = QVBoxLayout()
        labels_frame.setLayout( frame_layout )
        labels_frame.setFrameStyle( QFrame.StyledPanel | QFrame.Raised )
        labels_frame.setLineWidth( 3 )
        console_layout.addWidget( labels_frame )

        title = QLabel( "Classes" )
        title.setStyleSheet("font-weight: bold; color: black; font: 16pt" )
        frame_layout.addWidget( title )
        for index, label in enumerate(self._labels):
            radiobutton = QRadioButton( label, console )
            radiobutton.index = index
            qcolor = [ str(150+int(c*105.99)) for c in self._colors[index] ]
            style_sheet = ";".join( radio_button_style + [ f"background-color:rgb({','.join(qcolor)})" ] )
            radiobutton.setStyleSheet( style_sheet )
            radiobutton.toggled.connect(self.onClicked)
            frame_layout.addWidget( radiobutton )
        buttonBox = QHBoxLayout()
        for action in [ 'Explore', 'Clear' ]:
            pybutton = QPushButton( action, console )
            pybutton.clicked.connect( partial( self.execute,action)  )
            buttonBox.addWidget(pybutton)
        frame_layout.addLayout( buttonBox )
        console_layout.addStretch( 1 )
        return console

    def execute(self, action: str ):
        print( f"Executing action {action}" )

    def onClicked(self):
        radioButton = self.sender()
        if radioButton.isChecked():
            print(f"Selected class {radioButton.index}")

labelsManager = LabelsManager()