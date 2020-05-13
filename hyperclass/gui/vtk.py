import sys
import vtk
from PyQt5 import QtCore, QtWidgets
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


class VTKFrame():

    def __init__( self, layout: QtWidgets.QBoxLayout  ):

        self.frame = QtWidgets.QFrame()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        layout.addWidget(self.vtkWidget)

        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        for actor in self.getActors():
            self.ren.AddActor(actor)

        self.ren.ResetCamera()
        self.frame.setLayout(layout)

    def getActors(self):
        return []



