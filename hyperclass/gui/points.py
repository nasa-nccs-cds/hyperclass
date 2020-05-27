import sys
import vtk, numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.umap.manager import UMAPManager
from hyperclass.plot.point_cloud import PointCloud
from collections import OrderedDict

class HCRenderWindowInteractor(vtk.vtkGenericRenderWindowInteractor):

    def __init__(self):
        vtk.vtkGenericRenderWindowInteractor.__init__(self)
        self.renderer = None
        self.enable_pick_sym = "Alt_L"
        self.pick_enabled = False
        self.SetPicker( vtk.vtkPointPicker() )
        interactorStyle = vtk.vtkInteractorStyleTrackballCamera()
        self.SetInteractorStyle(interactorStyle)
        interactorStyle.KeyPressActivationOff()
        interactorStyle.SetEnabled(1)

    def setRenderer( self, renderer: vtk.vtkRenderer ):
        self.renderer = renderer

    def RightButtonPressEvent( self, *args  ):
        if self.pick_enabled:
            clickPos = self.GetEventPosition()
            picker = self.GetPicker()
            picker.Pick(clickPos[0], clickPos[1], 0, self.renderer )
            print( f"Picked point {picker.GetPointId()}")
        else:
            vtk.vtkGenericRenderWindowInteractor.RightButtonPressEvent(self, *args)

    def KeyPressEvent( self, *args ):
        vtk.vtkGenericRenderWindowInteractor.KeyPressEvent( self, *args )
        sym = self.GetKeySym()
        print( f"KeyPressEvent: {sym}")
        if sym == self.enable_pick_sym: self.pick_enabled = True

    def KeyReleaseEvent( self, *args ):
        vtk.vtkGenericRenderWindowInteractor.KeyReleaseEvent( self, *args )
        sym = self.GetKeySym()
        print( f"KeyReleaseEvent: {sym}")
        if sym == self.enable_pick_sym: self.pick_enabled = False

class VTKWidget(QVTKRenderWindowInteractor):
    def __init__(self, parent ):
        self.rw = vtk.vtkRenderWindow()
        self.iren = HCRenderWindowInteractor()
        self.iren.SetRenderWindow( self.rw )
        QVTKRenderWindowInteractor.__init__( self, parent, iren=self.iren, rw=self.rw )
        self.picker = vtk.vtkPointPicker()

    @property
    def renderer(self):
        return self.iren.renderer

    def setRenderer( self, renderer: vtk.vtkRenderer ):
        self.iren.setRenderer( renderer )
        self.rw.AddRenderer( renderer )

    def leaveEvent(self, ev):
        try: QVTKRenderWindowInteractor.leaveEvent(self, ev)
        except TypeError: pass

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        print( "mousePressEvent" )
        try:
            QVTKRenderWindowInteractor.mousePressEvent(self, ev)
        except TypeError: pass

    def mouseMoveEvent(self, ev):
        try:
            QVTKRenderWindowInteractor.mouseMoveEvent(self, ev)
        except TypeError: pass

    def keyPressEvent(self, ev):
        try:
            print( "Key Press event")
            QVTKRenderWindowInteractor.keyPressEvent(self, ev)
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
        self.vtkWidget = VTKWidget(self)
        self.vl.addWidget(self.vtkWidget)
        self.renderer = vtk.vtkRenderer()
        self.vtkWidget.setRenderer( self.renderer )
        self.setLayout(self.vl)

    @property
    def iren(self):
        return self.vtkWidget.iren

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











