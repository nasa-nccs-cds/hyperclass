import sys, os, traceback
import numpy as np
from typing import List, Union, Dict, Callable, Tuple, Optional
import time, math, threading
import vtk.util.numpy_support as npsup
from collections import OrderedDict
import vtk


class PointCloud():

    def __init__( self, **kwargs ):
        self.vrange = None
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

    def setNormalizedScalarRange(self, normalized_scalar_range):
        self.setScalarRange(self.getScaledRange(normalized_scalar_range))
        return self.current_scalar_range

    def setScalarRange(self, scalar_range=None):
        if scalar_range: self.current_scalar_range = scalar_range
        self.mapper.SetScalarRange(self.current_scalar_range[0], self.current_scalar_range[1])
        #        print " ------------------------->>>>>>>>>>>>>>>>>>>> PointCloud: Set Scalar Range: %s " % str( self.current_scalar_range )
        self.mapper.Modified()
        self.actor.Modified()
        self.actor.SetVisibility(True)

    def getScalarRange(self):
        return self.current_scalar_range

    def getScaledRange(self, srange):
        dv = self.vrange[1] - self.vrange[0]
        vmin = self.vrange[0] + srange[0] * dv
        vmax = self.vrange[0] + srange[1] * dv
        return (vmin, vmax)

    # def color_scalars(self, color_data: np.ndarray, **args):
    #     vtk_color_data = npsup.numpy_to_vtk(color_data)
    #     vtk_color_data.SetName('vardata')
    #     self.polydata.GetPointData().SetScalars(vtk_color_data)
    #     self.polydata.Modified()
    #     self.mapper.Modified()
    #     self.actor.Modified()

    def set_colormap(self, label_colors: OrderedDict ):
        label_colors["unlabeled"] = self.unlabeled_color
        self.colormap = np.clip(np.array(list(label_colors.values())) * 255.99, 0, 255).astype(np.uint8)

    def set_point_colors( self, sample_labels: np.array ):
        print( f"sample_labels0:  {sample_labels.min()} -> {sample_labels.max()}")
        sample_labels = self.init_colormap(sample_labels)
        print(f"sample_labels1:  {sample_labels.min()} -> {sample_labels.max()}")
        colors = self.colormap[ sample_labels ]
        vtk_color_data: vtk.vtkUnsignedCharArray  = npsup.numpy_to_vtk( colors.ravel(), deep=1, array_type=npsup.get_vtk_array_type(np.uint8) )
        vtk_color_data.SetNumberOfComponents( colors.shape[1] )
        vtk_color_data.SetNumberOfTuples( colors.shape[0] )
        vtk_color_data.SetName('colors')
        vtkpts = self.polydata.GetPointData()
        vtkpts.SetScalars(vtk_color_data)
        vtkpts.SetActiveScalars('colors')
        self.polydata.Modified()

    def init_colormap(self, sample_labels: np.array ):
        if self.colormap is None:
            nlabels = max( int( sample_labels.max() ) + 1, 1 )
            nvals =  nlabels*3
            self.colormap = np.array( [0xFF]*nvals ).reshape( nlabels, 3 )
        sample_labels = sample_labels.astype(np.int)
        sample_labels[ sample_labels == -1 ] = 0
        return np.nan_to_num( sample_labels )


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
        self.np_points = np_points_data
        nPoints = int(self.np_points.size / 3)
        vtk_points_data = npsup.numpy_to_vtk(self.np_points)
        vtk_points_data.SetNumberOfComponents(3)
        vtk_points_data.SetNumberOfTuples(nPoints)
        vtk_points = vtk.vtkPoints()
        vtk_points.SetData(vtk_points_data)
        self.polydata = vtk.vtkPolyData()
        self.polydata.SetPoints( vtk_points )
        vertices = vtk.vtkCellArray()
        np_index_seq = np.arange( 0, nPoints )
        cell_sizes = np.ones_like( np_index_seq )
        self.np_cell_data = np.dstack((cell_sizes, np_index_seq)).flatten()
        vtk_cell_data = npsup.numpy_to_vtkIdTypeArray(self.np_cell_data)
        vertices.SetCells( cell_sizes.size, vtk_cell_data )
        self.polydata.SetVerts(vertices)
        if self.mapper is not None:
            self.mapper.SetInputData(self.polydata)
            self.mapper.Modified()

#        self.initMarkers()
#        self.mapper.Modified()
#        self.actor.Modified()

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
            rendWinInteractor =  vtk.vtkGenericRenderWindowInteractor()
            self.renWin.SetInteractor( rendWinInteractor )
            rendWinInteractor.SetRenderWindow( self.renWin )

            self.renderer = vtk.vtkRenderer()
            self.renWin.AddRenderer( self.renderer )

            interactorStyle = vtk.vtkInteractorStyleTrackballCamera( )
            rendWinInteractor.SetInteractorStyle( interactorStyle )
            interactorStyle.KeyPressActivationOff( )
            interactorStyle.SetEnabled(1)
            if self.actor is not None:
                self.renderer.AddActor(self.actor)

#            self.renderer.SetBackground(1.0, 1.0, 1.0)
#            self.renderer.SetNearClippingPlaneTolerance( 0.0001 )

    def createActor(self):
        self.mapper = vtk.vtkPolyDataMapper()
        self.mapper.SetScalarModeToUsePointData()
        self.mapper.SetColorModeToMapScalars()
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