import sys
import vtk, numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.umap.manager import UMAPManager
from hyperclass.plot.point_cloud import PointCloud
from collections import OrderedDict

class HVTKRenderWindowInteractor(QVTKRenderWindowInteractor):
    def leaveEvent(self, ev):
        try: QVTKRenderWindowInteractor.leaveEvent(self, ev)
        except TypeError: pass

    def mouseMoveEvent(self, ev):
        try: QVTKRenderWindowInteractor.mouseMoveEvent(self, ev)
        except TypeError: pass

    def keyPressEvent(self, ev):
        try: QVTKRenderWindowInteractor.keyPressEvent(self, ev)
        except TypeError: pass

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, umgr: UMAPManager, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.frame = VTKFrame( umgr )
        self.setCentralWidget(self.frame)

    def show(self):
        QtWidgets.QMainWindow.show(self)
        self.frame.Initialize()

    def initPlot( self, block: Block, class_colors: OrderedDict, **kwargs ):
        self.frame.initPlot( block, class_colors, **kwargs )

class VTKFrame(QtWidgets.QFrame):

    def __init__( self, umgr: UMAPManager  ):
        QtWidgets.QFrame.__init__( self  )
        self.umgr = umgr

        self.vl = QtWidgets.QVBoxLayout()
        self.vtkWidget = HVTKRenderWindowInteractor(self)
        self.vl.addWidget(self.vtkWidget)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        self.renderer = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer( self.renderer )

        interactorStyle = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(interactorStyle)
        interactorStyle.KeyPressActivationOff()
        interactorStyle.SetEnabled(1)

        self.setLayout(self.vl)

    def getActors(self):
        return [ self.point_cloud.createActor() ]

    def Initialize(self):
        self.iren.Initialize()
        self.iren.Start()

    def update(self, **kwargs ):
        self.umgr.point_cloud.createActor(self.renderer)
        self.umgr.point_cloud.update()
        self.vtkWidget.Render()
        QtWidgets.QFrame.update(self)











