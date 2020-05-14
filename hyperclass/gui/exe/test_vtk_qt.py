import sys
import xarray as xa
import vtk, numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.vtk import MainWindow
from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, math

block_index = [0,0]
image_name = "ang20170720t004130_corr_v2p9"

dm = DataManager( image_name )
tile: Tile = dm.getTile()
block: Block = tile.getBlock( *block_index )

app = QtWidgets.QApplication(sys.argv)

window = MainWindow()
window.initPlot( block )
window.show()

sys.exit(app.exec_())
