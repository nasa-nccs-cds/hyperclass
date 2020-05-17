import xarray as xa
import vtk, numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.application import MainWindow
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