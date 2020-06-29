import sys, os, traceback
import numpy as np
from typing import List, Union, Dict, Callable, Tuple, Optional
import time, math, threading
import vtk.util.numpy_support as npsup
from collections import OrderedDict
import vtk

#
# class PointPickInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
#
#     def __init__(self, parent=None):
#         self.AddObserver("LeftButtonPressEvent", self.leftButtonPressEvent)
#         self.AddObserver("RightButtonPressEvent", self.rightButtonPressEvent)
#         self.AddObserver( "KeyPressEvent",self.keyPressEvent )
#
#     def OnRightButtonDown( self, *args ):
#         print("ZZZ")
#         super(self).OnRightButtonDown( *args )
#
#     def OnKeyPress(self):
#         print("SSSSSS")
#         super(self).OnKeyPress()
#
#     def keyPressEvent(self, obj, event):
#         print("YYY")
#
#     def rightButtonPressEvent(self, obj, event):
#         print("XXX")
#         self.OnRightButtonDown()
#         return
#
#     def leftButtonPressEvent(self, obj, event):
#         clickPos = self.GetInteractor().GetEventPosition()
#         picker = self.GetInteractor().GetPicker()
#         picker.Pick(clickPos[0], clickPos[1], 0, self.GetDefaultRenderer())
#         print( f"Picked point {picker.GetPointId()}")
#         self.OnLeftButtonDown()
#         return

class PointCloud():

    def __init__( self, **kwargs ):
        self.renWin = None
        self.renderer: vtk.vtkRenderer = None
        self.colormap = None
        self.mapper: vtk.vtkMapper = None
        self.actor: vtk.vtkActor = None
        self.picker: vtk.vtkPicker = None
        self.polydata: vtk.vtkPolyData= None
        self.marker_actor: vtk.vtkActor = None
        self.points_modified = False
        self.unlabeled_color = [ 1.0, 1.0, 1.0 ]

    def process_event(self, event: Dict ):
        print( f" PointCloud.process_event: {event}")

    def setPoints(self, points: np.ndarray, labels: np.ndarray = None, **kwargs ):
        self.initPolyData(points)
        if labels is not None: self.set_point_colors( labels )
        self.initMarkers( **kwargs )

    def getPolydata(self):
        return self.polydata

    def set_colormap(self, label_colors: OrderedDict ):
        colors = [  np.clip( np.array( color ) * 255.99, 0, 255).astype(np.uint8) for color in label_colors.values() ]
        self.colormap = np.vstack( colors )
        print(".")

    def update_point_sizes(self, increase: bool):
        psize = self.actor.GetProperty().GetPointSize()
        psize = psize + 1 if increase else psize - 1
        print( f"Update point size: {psize}")
        self.actor.GetProperty().SetPointSize( max( psize, 1 ) )
        self.update()

    def set_point_colors( self, sample_labels: np.array, **kwargs ):
        if self.polydata is None:
            print( "Points are not yet available" )
        else:
            labels = np.where( sample_labels >= 0, sample_labels, 0 )
            colors = self.colormap[ labels ]
            vtk_color_data: vtk.vtkUnsignedCharArray  = npsup.numpy_to_vtk( colors.ravel(), deep=1, array_type=npsup.get_vtk_array_type(np.uint8) )
            vtk_color_data.SetNumberOfComponents( colors.shape[1] )
            vtk_color_data.SetNumberOfTuples( colors.shape[0] )
            vtk_color_data.SetName('colors')
            vtkpts = self.polydata.GetPointData()
            vtkpts.SetScalars(vtk_color_data)
            vtkpts.SetActiveScalars('colors')
            vtkpts.Modified()

    def update(self):
        if self.mapper is not None:   self.mapper.Modified()
        if self.polydata is not None: self.polydata.Modified()
        if self.actor is not None:    self.actor.Modified()
        if self.points_modified and self.renderer is not None:
            self.renderer.ResetCamera()
        if self.renWin is not None:   self.renWin.Render()
        self.points_modified = False


    # def get_lut( self, class_colors: OrderedDict ) -> vtk.vtkLookupTable:
    #     lut = vtk.vtkLookupTable()
    #     colors = list(class_colors.values())
    #     n = len(colors)
    #     lut.SetTableRange( 0, n )
    #     lut.SetNumberOfTableValues(n)
    #     lut.Build()
    #     for ic in range(n):
    #         vc = [ math.floor(c*255.99) for c in colors[ic] ]
    #         lut.SetTableValue( ic, vc[0], vc[1], vc[2], 1 )
    #     return lut

    def initPolyData( self, np_points_data: Optional[np.ndarray] = None, **kwargs ):
        vtk_points = vtk.vtkPoints()
        self.polydata = vtk.vtkPolyData()
        self.polydata.SetPoints( vtk_points )
        vertices = vtk.vtkCellArray()
        self.polydata.SetVerts(vertices)

        if np_points_data is not None:
            nPoints = int(np_points_data.size / 3)
            vtk_points_data = npsup.numpy_to_vtk( np_points_data.ravel(), deep=1 )
            vtk_points_data.SetNumberOfComponents(3)
            vtk_points_data.SetNumberOfTuples(nPoints)
            vtk_points.SetData(vtk_points_data)
            np_index_seq = np.arange( 0, nPoints )
            cell_sizes = np.ones_like( np_index_seq )
            np_cell_data = np.dstack(( cell_sizes, np_index_seq) )
            vtk_cell_data = npsup.numpy_to_vtkIdTypeArray( np_cell_data.ravel(), deep=1 )
            vertices.SetCells( cell_sizes.size, vtk_cell_data )
            self.set_point_colors( np.full( shape=[nPoints], fill_value= 0 ) )
            self.polydata.Modified()
            self.points_modified = True

        if self.mapper is not None:
            self.mapper.SetInputData(self.polydata)
            self.mapper.Modified()
        if self.actor is not None:
            self.actor.Modified()

    def clear(self):
        self.initPolyData()
        self.initMarkers()

    def initMarkers( self, **kwargs ):
        print( "Initializing Markers")
        if self.marker_actor is None:
            marker_size = kwargs.get( 'marker_size', 10 )
            self.markers = vtk.vtkPolyData()
            self.marker_mapper = vtk.vtkPolyDataMapper()
            self.marker_mapper.SetInputData( self.markers )
            self.marker_actor = vtk.vtkActor()
            self.marker_actor.GetProperty().SetPointSize( marker_size )
            self.marker_actor.SetMapper( self.marker_mapper )
        self.marker_points = vtk.vtkPoints()
        self.marker_verts  = vtk.vtkCellArray()
        self.marker_colors = vtk.vtkUnsignedCharArray()
        self.marker_colors.SetNumberOfComponents(3)
        self.marker_colors.SetName("colors")
        self.markers.SetPoints( self.marker_points )
        self.markers.SetVerts( self.marker_verts )
        self.markers.GetPointData().SetScalars(self.marker_colors)
        self.markers.GetPointData().SetActiveScalars('colors')
        self.markers.Modified()
        self.marker_actor.Modified()
        self.marker_mapper.Modified()

    def plotMarkers(self, points: List[List[float]], colors: List[List[float]] = None, **kwargs  ):
        reset = kwargs.get( 'reset', True )
        if reset: self.initMarkers( )
        print(f"PointCloud-> Plot Markers: {points} {colors} " )
        for point_coords in points:
            id = self.marker_points.InsertNextPoint( *point_coords  )
            self.marker_verts.InsertNextCell(1)
            self.marker_verts.InsertCellPoint(id)
        for iC in range( len(points) ):
            if colors is None:  vtk_color = [ 255, 255, 255 ]
            else:
                color = colors[iC]
                vtk_color = [ int(color[ic]*255.99) for ic in range(3) ]
            self.marker_colors.InsertNextTuple3( *vtk_color )
        self.markers.GetPointData().Modified()
        self.marker_points.Modified()
        self.marker_verts.Modified()
        self.marker_colors.Modified()
        self.markers.Modified()
        self.marker_mapper.Modified()
        self.marker_actor.Modified()

    # def create_LUT(self, **args):
    #     lut = vtk.vtkLookupTable()
    #     lut_type = args.get('type', "blue-red")
    #     invert = args.get('invert', False)
    #     number_of_colors = args.get('number_of_colors', 256)
    #     alpha_range = 1.0, 1.0
    #
    #     if lut_type == "blue-red":
    #         if invert:
    #             hue_range = 0.0, 0.6667
    #         else:
    #             hue_range = 0.6667, 0.0
    #         saturation_range = 1.0, 1.0
    #         value_range = 1.0, 1.0
    #
    #     lut.SetHueRange(hue_range)
    #     lut.SetSaturationRange(saturation_range)
    #     lut.SetValueRange(value_range)
    #     lut.SetAlphaRange(alpha_range)
    #     lut.SetNumberOfTableValues(number_of_colors)
    #     lut.SetRampToSQRT()
    #     lut.Modified()
    #     lut.ForceBuild()
    #     return lut

    def createRenderWindow( self, **kwargs ):
        from hyperclass.gui.points import HCRenderWindowInteractor
        if self.renWin is None:
            self.renWin = vtk.vtkRenderWindow()
            self.rendWinInteractor =  HCRenderWindowInteractor()
            self.renWin.SetInteractor( self.rendWinInteractor )
            self.picker = vtk.vtkPointPicker()
            self.rendWinInteractor.SetPicker( self.picker )
            self.rendWinInteractor.SetRenderWindow( self.renWin )

            self.rendWinInteractor.AddObserver( "KeyPressEvent", self.keyPressEvent )

            self.renderer = vtk.vtkRenderer()
            self.renWin.AddRenderer( self.renderer )

            self.interactorStyle = vtk.vtkInteractorStyleTrackballCamera()
            self.interactorStyle.SetDefaultRenderer( self.renderer )
            self.rendWinInteractor.SetInteractorStyle( self.interactorStyle )
            self.interactorStyle.KeyPressActivationOff( )
            self.interactorStyle.SetEnabled(1)
            if self.actor is not None:
                self.renderer.AddActor(self.actor)
            if self.marker_actor is not None:
                self.renderer.AddActor(self.marker_actor)

#            self.renderer.SetBackground(1.0, 1.0, 1.0)
#            self.renderer.SetNearClippingPlaneTolerance( 0.0001 )

    def createActors(self, renderer: vtk.vtkRenderer = None):
        if self.actor is None:
            if renderer is not None:
                self.renderer = renderer
            self.mapper = vtk.vtkPolyDataMapper()
            if self.polydata is not None:
                self.mapper.SetInputData(self.polydata)
            self.actor = vtk.vtkActor()
            self.actor.SetMapper(self.mapper)
            self.actor.GetProperty().SetPointSize(2)
            if self.renderer is not None:
                self.renderer.AddActor( self.actor )
        if self.marker_actor is None:
            self.initMarkers()
            if self.renderer is not None:
                self.renderer.AddActor( self.marker_actor )
        return self.actor

    def show(self):
        self.createRenderWindow()
        self.createActors()
        self.renWin.GetInteractor().Start()