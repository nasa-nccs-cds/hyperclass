import sys, os, traceback
import numpy as np
from typing import List, Union, Dict, Callable, Tuple, Optional
import time, math, threading
from sklearn.preprocessing import normalize
import xarray as xa
import vtk.util.numpy_support as npsup
from collections import OrderedDict
import vtk

class MixingSpace():

    def __init__( self, **kwargs ):
        self.renWin = None
        self.renderer = None
        self.colormap = None
        self.mapper = None
        self.actor = None
        self.picker = None
        self.polydata = None
        self.marker_actor = None
        self.points_modified = False
        self.unlabeled_color = [ 1.0, 1.0, 1.0 ]

    def process_event(self, event: Dict ):
        print( f" PointCloud.process_event: {event}")

    def setPoints (self, points: xa.DataArray, labels: xa.DataArray, **kwargs ):
        self.computMixingEmbedding( points.values, labels.values, **kwargs )
        if labels is not None: self.set_point_colors( labels )
        self.initMarkers( **kwargs )

    def getPolydata(self):
        return self.polydata

    def set_colormap(self, label_colors: OrderedDict ):
        colors = [  np.clip( np.array( color ) * 255.99, 0, 255).astype(np.uint8) for color in label_colors.values() ]
        self.colormap = np.vstack( colors )
        self.labels = { lid: color for lid, (label, color) in enumerate(label_colors.items()) }

    def keyPressEvent( self, *args ):
        print("YYY")

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
        if self.points_modified:      self.renderer.ResetCamera()
        if self.renWin is not None:   self.renWin.Render()
        self.points_modified = False

    def computMixingEmbedding (self, points: np.ndarray, label_data: np.ndarray,  **kwargs ):
        class_vectors = [ points[ label_data == lid, : ].mean( axis = 0 )  for lid in self.labels if lid > 0 ]
        subspace_vectors = [ (class_vectors[iv] - class_vectors[0]) for iv in range( 1,  len( class_vectors ) ) ]
        unit_vectors = [  ]
        for subspace_vector in subspace_vectors:
            for unit_vector in unit_vectors:
                vector_projection = subspace_vector.dot( unit_vector.flatten() )
                subspace_vector = subspace_vector - vector_projection * unit_vector
            unit_vectors.append( normalize(subspace_vector.reshape(1, -1)).flatten() )
        projection_matrix = np.vstack( unit_vectors ).transpose()
        projected_data = points.dot( projection_matrix )
        self.initPolyData(  projected_data )

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

    def plotMarkers(self, points: List[List[float]], colors: List[List[float]], **kwargs  ):
        reset = kwargs.get( 'reset', False )
        if reset: self.initMarkers( )
        for point_coords in points:
            id = self.marker_points.InsertNextPoint( *point_coords  )
            self.marker_verts.InsertNextCell(1)
            self.marker_verts.InsertCellPoint(id)
        for color in colors:
            vtk_color = [ math.floor(color[ic]*255.99) for ic in range(3) ]
            self.marker_colors.InsertNextTuple3( *vtk_color )
        self.markers.GetPointData().Modified()
        self.marker_points.Modified()
        self.marker_verts.Modified()
        self.markers.Modified()
        self.marker_mapper.Modified()
        self.marker_actor.Modified()

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

    def createActor(self, renderer: vtk.vtkRenderer = None ):
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
                self.renderer.AddActor( self.marker_actor )
        return self.actor

    def show(self):
        self.createRenderWindow()
        self.createActor()
        self.renWin.GetInteractor().Start()