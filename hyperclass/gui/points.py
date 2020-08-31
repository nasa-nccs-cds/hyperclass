import vtk, numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt, QObject
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5.QtWidgets import QApplication
from typing import List, Union, Dict, Callable, Tuple, Optional
from PyQt5.QtGui import QCursor
from hyperclass.plot.point_cloud import PointCloud
from hyperclass.gui.events import EventClient, EventMode

class HCRenderWindowInteractor(vtk.vtkGenericRenderWindowInteractor):

    def __init__(self, picker: vtk.vtkPointPicker, submit_event: Callable ):
        self.debug = True
        vtk.vtkGenericRenderWindowInteractor.__init__(self)
        self.submit_event = submit_event
        self.renderer = None
        self.pick_enabled = False
        self.SetPicker(picker)
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
            picked_point = picker.GetPointId()
            if picked_point >= 0:
                print( f"Picked point {picked_point}, tolerance = {picker.GetTolerance()}, useCells = {picker.GetUseCells()}, nprops = {picker.GetPickList().GetNumberOfItems()}")
                event = dict(event="pick", type="vtkpoint", pids=[picked_point], transient=True, mark=True )
                self.submit_event( event, EventMode.Gui )
            else:
                print(f"Point pick failed")
        else:
            vtk.vtkGenericRenderWindowInteractor.RightButtonPressEvent(self, *args)


class VTKWidget(QVTKRenderWindowInteractor,EventClient):
    def __init__(self, parent, point_cloud: PointCloud ):
        self.rw: vtk.vtkRenderWindow = vtk.vtkRenderWindow()
        self.point_cloud: PointCloud = point_cloud
        self.iren = HCRenderWindowInteractor( point_cloud.picker, self.submitEvent )
        self.iren.SetRenderWindow( self.rw )
        QVTKRenderWindowInteractor.__init__( self, parent, iren=self.iren, rw=self.rw )
        self.activate_event_listening()

    @staticmethod
    def _getPixelRatio():
        pos = QCursor.pos()
        for screen in QApplication.screens():
            rect = screen.geometry()
            if rect.contains(pos):
                return screen.devicePixelRatio()
        return 1

    def update(self, **kwargs ):
        self.point_cloud.createActors(self.iren.renderer)
        self.point_cloud.update( **kwargs )
        self.rw.Render()

    @property
    def renderer(self):
        return self.iren.renderer

    def setRenderer( self, renderer: vtk.vtkRenderer ):
        self.iren.setRenderer( renderer )
        self.rw.AddRenderer( renderer )

    # def leaveEvent(self, ev):
    #     try: QVTKRenderWindowInteractor.leaveEvent(self, ev)
    #     except TypeError: pass
    #
    # def mousePressEvent(self, ev: QtGui.QMouseEvent):
    #     try:
    #         QVTKRenderWindowInteractor.mousePressEvent(self, ev)
    #     except TypeError: pass
    #
    # def mouseMoveEvent(self, ev):
    #     try:
    #         QVTKRenderWindowInteractor.mouseMoveEvent(self, ev)
    #     except TypeError: pass
    #
    # def keyPressEvent(self, ev):
    #     try:
    #         QVTKRenderWindowInteractor.keyPressEvent(self, ev)
    #     except TypeError: pass

class VTKFrame(QtWidgets.QFrame):

    def __init__( self, point_cloud: PointCloud  ):
        QtWidgets.QFrame.__init__( self  )
        self.vl = QtWidgets.QVBoxLayout()
        self.vtkWidget = VTKWidget( self, point_cloud )
        self.vl.addWidget(self.vtkWidget)
        self.renderer = vtk.vtkRenderer()
        self.vtkWidget.setRenderer( self.renderer )
        self.setLayout(self.vl)
        self._key_state = None
        self._key_state_modifiers = None

    def update_plot(self, points ):
        self.vtkWidget.point_cloud.setPoints( points )

    def plotMarkers(self, **kwargs):
        self.vtkWidget.point_cloud.plotMarkers(**kwargs)

    def clear(self):
        self.vtkWidget.point_cloud.clear()

    def color_by_metric( self, metric: np.array, **kwargs ):
        self.vtkWidget.point_cloud.color_by_metric( metric, **kwargs  )

    def set_point_colors( self, **kwargs ):
        self.vtkWidget.point_cloud.set_point_colors( **kwargs )

    @property
    def keyState(self):
        return self._key_state

    def setKeyState(self, event ):
        self._key_state = event.get('key')
        self._key_state_modifiers = event.get('modifiers')
        k = self._key_state
        k0 = Qt.Key_Control
        k1 = Qt.Key_Meta
        k2 = Qt.Key_Alt
        k3 = Qt.Key_Option
        if self._key_state == Qt.Key_Control:
            self.vtkWidget.iren.pick_enabled = True

    def releaseKeyState( self ):
        self._key_state = None
        self._key_state_modifiers = None
        self.vtkWidget.iren.pick_enabled = False

    @property
    def iren(self):
        return self.vtkWidget.iren

    def Initialize(self):
        self.iren.Initialize()
        self.iren.Start()

    def gui_update(self, **kwargs ):
        self.vtkWidget.update( **kwargs )
        QtWidgets.QFrame.update(self)

# class MixingFrame(QtWidgets.QFrame):
#
#     def __init__( self, umgr: UMAPManager  ):
#         QtWidgets.QFrame.__init__( self  )
#         self.umgr = umgr
#         self.vl = QtWidgets.QVBoxLayout()
#         self.vtkWidget = VTKWidget(self)
#         self.vl.addWidget(self.vtkWidget)
#         self.renderer = vtk.vtkRenderer()
#         self.vtkWidget.setRenderer( self.renderer )
#         self.setLayout(self.vl)
#         self.iren.addEventListener( self.umgr.point_cloud )
#
#     def addEventListener( self, listener ):
#         self.iren.addEventListener( listener )
#
#     @property
#     def iren(self):
#         return self.vtkWidget.iren
#
#     def Initialize(self):
#         self.iren.Initialize()
#         self.iren.Start()
#
#     def update(self, **kwargs ):
#         self.umgr.mixing_space.createActor(self.renderer)
#         self.umgr.mixing_space.update()
#         self.vtkWidget.Render()
#         QtWidgets.QFrame.update(self)
#
#









