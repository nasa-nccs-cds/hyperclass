import sys
import vtk
from PyQt5 import QtCore, QtWidgets, QtGui
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from hyperclass.plot.point_cloud import PointCloud


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



