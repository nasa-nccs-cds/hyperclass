import sys
import vtk, numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.umap.manager import UMAPManager
from hyperclass.plot.point_cloud import PointCloud


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.frame = QtWidgets.QFrame()

        self.vl = QtWidgets.QVBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl.addWidget(self.vtkWidget)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        self.renderer = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer( self.renderer )

        interactorStyle = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(interactorStyle)
        interactorStyle.KeyPressActivationOff()
        interactorStyle.SetEnabled(1)

        self.frame.setLayout(self.vl)
        self.setCentralWidget(self.frame)

    def show(self):
        self.show()
        self.iren.Initialize()

    def initPlot( self, block: Block, **kwargs ):
        self.umgr = UMAPManager( block.tile, refresh=kwargs.pop('refresh', False))
        self.umgr.fit( block=block )
        self.umgr.point_cloud.createActor( self.renderer )

class VTKFrame():

    def __init__( self  ):
        self.layout = QtGui.QVBoxLayout()
        self.frame = QtWidgets.QFrame()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.layout.addWidget(self.vtkWidget)
        self.point_cloud = PointCloud()

        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        for actor in self.getActors():
            self.ren.AddActor(actor)

        self.ren.ResetCamera()
        self.frame.setLayout(self.layout)

    def getWidget(self):
        return self.frame

    def getActors(self):
        return [ self.point_cloud.createActor() ]








