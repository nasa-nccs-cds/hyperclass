import sys, os, traceback
import numpy as np
from typing import List, Union, Dict, Callable, Tuple, Optional
import time, math, threading
import vtk.util.numpy_support as npsup
from collections import OrderedDict
import vtk


class PointCloud():

    def __init__( self, **kwargs ):
        self.renWin = None
        self.renderer = None
        self.colormap = None
        self.mapper = None
        self.actor = None
        self.unlabeled_color = [ 1.0, 1.0, 1.0 ]

    def setPoints (self, points: np.ndarray, labels: np.ndarray = None ):
        self.initPolyData(points)
        if labels is not None: self.set_point_colors( labels )

    def getPolydata(self):
        return self.polydata

    def set_colormap(self, label_colors: OrderedDict ):
        colors = [  np.clip( np.array( color ) * 255.99, 0, 255).astype(np.uint8) for color in label_colors.values() ]
        self.colormap = np.vstack( colors )
        print(".")

    def set_point_colors( self, sample_labels: np.array ):
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
        self.update()

    def update(self):
        if self.mapper is not None:   self.mapper.Modified()
        if self.polydata is not None: self.polydata.Modified()
        if self.actor is not None:    self.actor.Modified()
        if self.renWin is not None:   self.renWin.Render()

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

    def initPolyData( self, np_points_data: np.ndarray, **kwargs ):
        nPoints = int(np_points_data.size / 3)
        vtk_points_data = npsup.numpy_to_vtk( np_points_data.ravel(), deep=1 )
        vtk_points_data.SetNumberOfComponents(3)
        vtk_points_data.SetNumberOfTuples(nPoints)
        vtk_points = vtk.vtkPoints()
        vtk_points.SetData(vtk_points_data)
        self.polydata = vtk.vtkPolyData()
        self.polydata.SetPoints( vtk_points )
        vertices = vtk.vtkCellArray()
        np_index_seq = np.arange( 0, nPoints )
        cell_sizes = np.ones_like( np_index_seq )
        np_cell_data = np.dstack(( cell_sizes, np_index_seq) )
        vtk_cell_data = npsup.numpy_to_vtkIdTypeArray( np_cell_data.ravel(), deep=1 )
        vertices.SetCells( cell_sizes.size, vtk_cell_data )
        self.polydata.SetVerts(vertices)
        self.set_point_colors( np.full( shape=[nPoints], fill_value= 0 ) )
        self.polydata.Modified()
        if self.mapper is not None:
            self.mapper.SetInputData(self.polydata)
            self.mapper.Modified()
        if self.actor is not None:
            self.actor.Modified()

    def initMarkers( self, **kwargs ):
        marler_size = kwargs.get( 'marler_size', 10 )
        self.markers = vtk.vtkPolyData()
        self.marker_mapper = vtk.vtkPolyDataMapper()
        self.marker_mapper.SetScalarModeToUsePointData()
        self.marker_mapper.SetColorModeToMapScalars()
        self.marker_mapper.SetInputData( self.markers )
        self.marker_actor = vtk.vtkActor()
#        self.marker_actor.GetProperty().SetPointSize( marler_size )
        self.marker_actor.SetMapper(self.mapper)
        self.plotMarkers()
        self.renderer.AddActor( self.marker_actor )

    def plotMarkers(self, point_coords: np.ndarray = None, colors: List[Tuple[float]] = None  ):
        marker_points = vtk.vtkPoints()
        marker_verts  = vtk.vtkCellArray()
        marker_colors = vtk.vtkUnsignedCharArray()
        marker_colors.SetNumberOfComponents(3)
        marker_colors.SetName("Colors")
        self.markers.GetPointData().SetScalars(marker_colors)

        if colors:
            for ip in range( len( colors ) ):
                id = marker_points.InsertNextPoint( *point_coords[ip].tolist()  )
                marker_verts.InsertNextCell(1)
                marker_verts.InsertCellPoint(id)
                vtk_color = [ math.floor(c*255.99) for c in colors[ip] ]
                marker_colors.InsertNextTuple3( vtk_color )

        self.markers.SetPoints( marker_points )
        self.markers.SetVerts( marker_verts )
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
        if self.renWin is None:
            self.renWin = vtk.vtkRenderWindow()
            self.rendWinInteractor =  vtk.vtkGenericRenderWindowInteractor()
            self.renWin.SetInteractor( self.rendWinInteractor )
            self.rendWinInteractor.SetRenderWindow( self.renWin )

            self.renderer = vtk.vtkRenderer()
            self.renWin.AddRenderer( self.renderer )

            self.interactorStyle = vtk.vtkInteractorStyleTrackballCamera( )
            self.rendWinInteractor.SetInteractorStyle( self.interactorStyle )
            self.interactorStyle.KeyPressActivationOff( )
            self.interactorStyle.SetEnabled(1)
            if self.actor is not None:
                self.renderer.AddActor(self.actor)

#            self.renderer.SetBackground(1.0, 1.0, 1.0)
#            self.renderer.SetNearClippingPlaneTolerance( 0.0001 )

    def createActor(self, renderer: vtk.vtkRenderer = None ):
        if renderer is not None:
            self.renderer = renderer
        self.mapper = vtk.vtkPolyDataMapper()
        if self.polydata is not None:
            self.mapper.SetInputData(self.polydata)
        self.actor = vtk.vtkActor()
        self.actor.SetMapper(self.mapper)
        self.actor.GetProperty().SetPointSize(1)
        if self.renderer is not None:
            self.renderer.AddActor( self.actor )
        return self.actor

    def show(self):
        self.createRenderWindow()
        self.createActor()
        self.renWin.GetInteractor().Start()