import vtk
from vtk import *
import math


def get_lut( self ) -> vtk.vtkLookupTable:
    lut = vtk.vtkLookupTable()
    colors = [ [1.0, 0.0, 0.0], [1.0, 0.0, 1.0], [0.0, 0.0, 1.0], [0.0, 1.0, 1.0] ]
    n = len(colors)
    lut.SetTableRange(0, n)
    lut.SetNumberOfTableValues(n)
    lut.Build()
    for ic in range(n):
        vc = [math.floor(c * 255.99) for c in colors[ic]]
        lut.SetTableValue(ic, vc[0], vc[1], vc[2], 1)
    return lut

#setup points and vertices
Points = vtk.vtkPoints()
Vertices = vtk.vtkCellArray()

id = Points.InsertNextPoint(1.0, 0.0, 0.0)
Vertices.InsertNextCell(1)
Vertices.InsertCellPoint(id)
id = Points.InsertNextPoint(0.0, 0.0, 0.0)
Vertices.InsertNextCell(1)
Vertices.InsertCellPoint(id)
id = Points.InsertNextPoint(0.0, 1.0, 0.0)
Vertices.InsertNextCell(1)
Vertices.InsertCellPoint(id)

#setup colors
Colors = vtk.vtkUnsignedCharArray()
Colors.SetNumberOfComponents(3)
Colors.SetName("Colors")
Colors.InsertNextTuple3(255,0,0)
Colors.InsertNextTuple3(0,255,0)
Colors.InsertNextTuple3(0,0,255)
polydata.GetPointData().SetScalars(Colors)
polydata.GetPointData().SetActiveScalars('Colors')

polydata = vtk.vtkPolyData()
polydata.SetPoints(Points)
polydata.SetVerts(Vertices)
polydata.GetPointData().SetScalars(Colors)
polydata.GetPointData().SetActiveScalars('Colors')
polydata.Modified()

lut = get_lut()
mapper = vtk.vtkPolyDataMapper()
mapper.SetInputData(polydata)
mapper.SetLookupTable( lut )
mapper.SetScalarRange(*lut.GetTableRange())
mapper.ScalarVisibilityOn()

actor = vtk.vtkActor()
actor.SetMapper(mapper)
actor.GetProperty().SetPointSize(20)

renderer = vtk.vtkRenderer()
renderWindow = vtk.vtkRenderWindow()
renderWindow.AddRenderer(renderer)
renderWindowInteractor = vtk.vtkRenderWindowInteractor()
renderWindowInteractor.SetRenderWindow(renderWindow)

renderer.AddActor(actor)

renderWindow.Render()
renderWindowInteractor.Start()