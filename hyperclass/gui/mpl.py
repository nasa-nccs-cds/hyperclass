import sys
from hyperclass.plot.console import LabelingConsole
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from hyperclass.umap.manager import UMAPManager
from typing import List, Union, Dict, Callable, Tuple, Optional
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import random

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class MainWindow(QMainWindow):
    def __init__(self, umgr: UMAPManager):
        QMainWindow.__init__(self)

        self.title = 'test'
        self.left = 10
        self.top = 10
        self.width = 1920
        self.height = 1080

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.statusBar().showMessage('Ready')

        mainMenu = self.menuBar()
        mainMenu.setNativeMenuBar(False)
        fileMenu = mainMenu.addMenu('File')
        helpMenu = mainMenu.addMenu('Help')

        exitButton = QAction(QIcon('exit24.png'), 'Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Exit application')
        exitButton.triggered.connect(self.close)
        fileMenu.addAction(exitButton)


        widget =  QWidget(self)
        self.setCentralWidget(widget)
        vlay = QVBoxLayout(widget)
        hlay = QHBoxLayout()
        vlay.addLayout(hlay)

        self.nameLabel = QLabel('Name:', self)
        self.line = QLineEdit(self)
        self.nameLabel2 = QLabel('Result', self)

        hlay.addWidget(self.nameLabel)
        hlay.addWidget(self.line)
        hlay.addWidget(self.nameLabel2)
        hlay.addItem(QSpacerItem(1000, 10, QSizePolicy.Expanding))

        pybutton = QPushButton('Click me', self)
        pybutton.clicked.connect(self.clickMethod)
        hlay2 = QHBoxLayout()
        hlay2.addWidget(pybutton)
        hlay2.addItem(QSpacerItem(1000, 10, QSizePolicy.Expanding))
        vlay.addLayout(hlay2)
        self.console = WidgetPlot( umgr,self)
        vlay.addWidget( self.console )

    def clickMethod(self):
        print('Clicked Pyqt button.')
        if self.line.text() == '':
            self.statusBar().showMessage('Not a Number')
        else:
            print('Number: {}'.format(float(self.line.text())*2))
            self.statusBar().showMessage('Introduction of a number')
            self.nameLabel2.setText(str(float(self.line.text())*2))

    def setBlock(self, block_coords: Tuple[int]):
        self.console.setBlock(block_coords)

    
class WidgetPlot(QWidget):
    def __init__(self, umgr: UMAPManager, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.canvas = MplCanvas(self, umgr, width=10, height=8)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas)

    def setBlock(self, block_coords: Tuple[int]   ):
        self.canvas.setBlock( block_coords )

class MplCanvas(FigureCanvas):

    def __init__(self, parent, umgr: UMAPManager, width=5, height=4, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.figure )
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.console = LabelingConsole( umgr, figure=self.figure )

    def setBlock(self, block_coords: Tuple[int]   ):
        self.console.setBlock( block_coords )


