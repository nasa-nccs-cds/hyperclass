import sys
from hyperclass.plot.console import LabelingConsole
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from functools import partial
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.mpl import MplWidget
from hyperclass.gui.points import VTKFrame
from typing import List, Union, Dict, Callable, Tuple, Optional

class MainWindow(QMainWindow):
    def __init__(self, umgr: UMAPManager):
        QMainWindow.__init__(self)

        self.title = 'test'
        self.left = 10
        self.top = 10
        self.width = 1920
        self.height = 1080
        self.NFunctionButtons = 0

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

        framesLayout = QHBoxLayout()
        self.console = MplWidget( umgr,self)
        framesLayout.addWidget( self.console )
        self.vtkFrame = VTKFrame( umgr )
        framesLayout.addWidget(self.vtkFrame)
        vlay.addLayout(framesLayout)

        buttonsLayout = QHBoxLayout()
        for label, callback in self.console.button_actions.items():
            pybutton = QPushButton( label, self )
            pybutton.clicked.connect( callback )
            buttonsLayout.addWidget(pybutton)
        vlay.addLayout(buttonsLayout)

    def ButtonClicked(self, buttonName: str ):
        self.statusBar().showMessage(f'Clicked Button {buttonName}')

    def setBlock(self, block_coords: Tuple[int]):
        self.console.setBlock(block_coords)

    def show(self):
        QtWidgets.QMainWindow.show(self)
        self.vtkFrame.Initialize()

import xarray as xa
import vtk, numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.points import VTKFrame
from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, math, sys

block_index = (0, 0)
refresh = False
image_name = "ang20170720t004130_corr_v2p9"
classes = [('Unlabeled', [1.0, 1.0, 1.0, 0.5]),
           ('Obscured', [0.6, 0.6, 0.4, 1.0]),
           ('Forest', [0.0, 1.0, 0.0, 1.0]),
           ('Non-forested Land', [0.7, 1.0, 0.0, 1.0]),
           ('Urban', [1.0, 0.0, 1.0, 1.0]),
           ('Water', [0.0, 0.0, 1.0, 1.0])]

dm = DataManager(image_name)
tile: Tile = dm.getTile()
umgr = UMAPManager(tile, classes, refresh=refresh)

app = QtWidgets.QApplication(sys.argv)

window = MainWindow(umgr)
window.show()

sys.exit(app.exec_())