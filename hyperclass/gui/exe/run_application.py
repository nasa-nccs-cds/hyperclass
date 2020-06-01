import xarray as xa
import vtk, numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.application import HyperclassConsole
from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, math, sys

block_shape = (250, 250)
image_name = "ang20170720t004130_corr_v2p9"
n_neighbors = 8
n_epochs = 200
embedding_init = "random" # "spectral" "random"

classes1 = [('Unlabeled', [1.0, 1.0, 1.0, 0.5]),
           ('Obscured', [0.6, 0.6, 0.4, 1.0]),
           ('Forest', [0.0, 1.0, 0.0, 1.0]),
           ('Non-forested Land', [0.5, 0.3, 0.7, 1.0]),
           ('Urban', [1.0, 0.0, 1.0, 1.0]),
           ('Water', [0.0, 0.0, 1.0, 1.0])]

classes = [('Unlabeled', [1.0, 1.0, 1.0, 0.5]),
           ('Obscured', [0.6, 0.6, 0.4, 1.0]),
           ('Vegetation', [0.0, 1.0, 0.0, 1.0]),
           ('BareEarth', [1.0, 0.0, 1.0, 1.0]),
           ('Water', [0.0, 0.0, 1.0, 1.0])]

dm = DataManager( image_name, block_shape=block_shape )
tile: Tile = dm.getTile()
umgr = UMAPManager( tile, classes, n_neighbors=n_neighbors, init=embedding_init, n_epochs = n_epochs )

app = QtWidgets.QApplication(sys.argv)
hyperclass = HyperclassConsole( umgr )
hyperclass.show()

sys.exit(app.exec_())