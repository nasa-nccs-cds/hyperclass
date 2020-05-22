'''
Created on Sep 18, 2013

@author: tpmaxwel
'''

from __future__ import print_function, division
import sys, os, traceback
import numpy
import vtk, time, math, threading
from vtk.util import numpy_support


class vtkPointCloud():

    def __init__(self, pcIndex=0, nPartitions=1):
        self.nPartitions = nPartitions
        self.polydata = None
        self.vardata = None
        self.vrange = None
        self.np_index_seq = None
        self.np_cell_data = None
        self.points = None
        self.pcIndex = pcIndex
        self.earth_radius = 100.0
        self.spherical_scaling = 0.4
        self.vtk_planar_points = None
        self.vtk_spherical_points = None
        self.np_points_data = None
        self.grid = None
        #        self.threshold_target = "vardata"
        self.current_scalar_range = None
        self.nlevels = None
        self.current_subset_specs = None
        self.updated_subset_specs = None
        self.mapper = vtk.vtkPolyDataMapper()
        self.mapper.SetScalarModeToUsePointData()
        self.mapper.SetColorModeToMapScalars()
        self.actor = vtk.vtkActor()
        self.actor.SetMapper(self.mapper)

    def getPoint(self, iPt):
        try:
            dval = self.vardata[iPt]
            pt = self.vtk_planar_points.GetPoint(iPt)
            self.printLogMessage(" getPoint[%d/%d]: dval=%s, pt=%s " % (iPt, self.vardata.shape[0], str(dval), str(pt)))
        except Exception as err:
            print("Pick Error for point %d: %s" % (iPt, str(err)), file=sys.stderr)
            print("Vardata(%s) shape: %s " % (self.vardata.__class__.__name__, str(self.vardata.shape)), file=sys.stderr)
            return None, None
        return pt, dval

    def printLogMessage(self, msg_str, **args):
        error = args.get("error", False)
        if error:
            print(" Proxy Node %d Error: %s" % (self.pcIndex, msg_str), file=sys.stderr)
        else:
            print(" Proxy Node %d: %s" % (self.pcIndex, msg_str))
        sys.stdout.flush()

    def getNLevels(self):
        #        if self.nlevels == None:
        #            print>>sys.stderr, " Undefined nlevels in getNLevels, proc %d " % self.pcIndex
        return self.nlevels

    def getGrid(self):
        return self.grid

    def hasResultWaiting(self):
        return False

    def getThresholdingRanges(self):
        return self.current_subset_specs

    #        return self.trange if ( self.threshold_target == "vardata" ) else self.crange

    def getValueRange(self, var_name=None, range_type=ScalarRangeType.Full):
        return self.vrange if (range_type == ScalarRangeType.Full) else self.trange

    def generateSubset(self, **args):
        pass

    def refresh(self, force=False):
        if force or (self.current_subset_specs and (self.current_subset_specs != self.updated_subset_specs)):
            self.generateSubset()
            self.updated_subset_specs = self.current_subset_specs

    def getData(self, dtype):
        if dtype == ExecutionDataPacket.VARDATA:
            return self.vardata
        elif dtype == ExecutionDataPacket.INDICES:
            return self.np_index_seq
        elif dtype == ExecutionDataPacket.POINTS:
            return self.np_points_data
        elif dtype == ExecutionDataPacket.HEIGHTS:
            return self.np_points_data

    def getCellData(self):
        return self.np_cell_data

    def updateVertices(self, **args):
        self.vertices = vtk.vtkCellArray()
        cell_sizes = numpy.ones_like(self.np_index_seq)
        self.np_cell_data = numpy.dstack((cell_sizes, self.np_index_seq)).flatten()
        self.vtk_cell_data = numpy_support.numpy_to_vtkIdTypeArray(self.np_cell_data)
        self.vertices.SetCells(cell_sizes.size, self.vtk_cell_data)
        self.polydata.SetVerts(self.vertices)

    #        self.polydata.Modified()
    #        self._mapper.Modified()
    #        self.actor.Modified()
    #        self.actor.SetVisibility( True  )

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

    def updateScalars(self, **args):
        #        print " ---> Update Scalars[%d]" % self.pcIndex
        if isNone(self.vardata):
            wait = args.get('wait', True)
            if wait:
                self.waitForData(ExecutionDataPacket.VARDATA)
            else:
                return
        vtk_color_data = numpy_support.numpy_to_vtk(self.vardata)
        vtk_color_data.SetName('vardata')
        self.polydata.GetPointData().SetScalars(vtk_color_data)
        self.polydata.Modified()
        self.mapper.Modified()
        self.actor.Modified()

    def initPoints(self, **args):
        if isNone(self.np_points_data):
            wait = args.get('wait', True)
            if wait:
                self.waitForData(ExecutionDataPacket.POINTS)
            else:
                return
        vtk_points_data = numpy_support.numpy_to_vtk(self.np_points_data)
        vtk_points_data.SetNumberOfComponents(3)
        vtk_points_data.SetNumberOfTuples(int(self.np_points_data.size / 3))
        self.vtk_planar_points = vtk.vtkPoints()
        self.vtk_planar_points.SetData(vtk_points_data)
        self.createPolydata(**args)

    def setPointHeights(self, ptheights):
        try:
            if self.topo == PlotType.Planar:
                self.np_points_data[2::3] = ptheights
                vtk_points_data = numpy_support.numpy_to_vtk(self.np_points_data)
                vtk_points_data.SetNumberOfComponents(3)
                vtk_points_data.SetNumberOfTuples(len(self.np_points_data) // 3)
                self.vtk_planar_points.SetData(vtk_points_data)
                self.polydata.SetPoints(self.vtk_planar_points)
                self.vtk_planar_points.Modified()
            elif self.topo == PlotType.Spherical:
                self.np_sp_grid_data[0::3] = self.spherical_scaling * ptheights + self.earth_radius
                vtk_sp_grid_data = numpy_support.numpy_to_vtk(self.np_sp_grid_data)
                size = vtk_sp_grid_data.GetSize()
                vtk_sp_grid_data.SetNumberOfComponents(3)
                vtk_sp_grid_data.SetNumberOfTuples(size // 3)
                vtk_sp_grid_points = vtk.vtkPoints()
                vtk_sp_grid_points.SetData(vtk_sp_grid_data)
                self.vtk_spherical_points = vtk.vtkPoints()
                self.shperical_to_xyz_trans.TransformPoints(vtk_sp_grid_points, self.vtk_spherical_points)
                #                pt0 = self.vtk_spherical_points.GetPoint(0)
                #            print "VTK Set point Heights, samples: %s %s %s " % ( str( ptheights[0] ), str( self.np_sp_grid_data[0] ), str( pt0 ) )
                self.polydata.SetPoints(self.vtk_spherical_points)
                self.vtk_spherical_points.Modified()
            self.polydata.Modified()
        except Exception as err:
            self.printLogMessage("Processing point heights: %s " % str(err), error=True)

    def createPolydata(self, **args):
        if self.polydata == None:
            self.polydata = vtk.vtkPolyData()
            vtk_pts = self.getPoints()
            self.polydata.SetPoints(vtk_pts)
            self.initializePointsActor(self.polydata, **args)

    def computeSphericalPoints(self, **args):
        lon_data = self.np_points_data[0::3]
        lat_data = self.np_points_data[1::3]
        z_data = self.np_points_data[2::3]
        radian_scaling = math.pi / 180.0
        theta = (90.0 - lat_data) * radian_scaling
        phi = lon_data * radian_scaling

        r = z_data * self.spherical_scaling + self.earth_radius
        self.np_sp_grid_data = numpy.dstack((r, theta, phi)).flatten()
        vtk_sp_grid_data = numpy_support.numpy_to_vtk(self.np_sp_grid_data)

        #         if self.grid == PlotType.List:
        # #             r = numpy.empty( lon_data.shape, lon_data.dtype )
        # #             r.fill(  self.earth_radius )
        #             r = z_data * self.spherical_scaling + self.earth_radius
        #             self.np_sp_grid_data = numpy.dstack( ( r, theta, phi ) ).flatten()
        #             vtk_sp_grid_data = numpy_support.numpy_to_vtk( self.np_sp_grid_data )
        #         elif self.grid == PlotType.Grid:
        #             thetaB = theta.reshape( [ theta.shape[0], 1 ] )
        #             phiB = phi.reshape( [ 1, phi.shape[0] ] )
        #             grid_data = numpy.array( [ ( self.earth_radius, t, p ) for (t,p) in numpy.broadcast(thetaB,phiB) ] )
        #             self.np_sp_grid_data = grid_data.flatten()
        #             vtk_sp_grid_data = numpy_support.numpy_to_vtk( self.np_sp_grid_data )
        #         else:
        #             print>>sys.stderr, "Unrecognized grid type: %s " % str( self.grid )
        #             return
        size = vtk_sp_grid_data.GetSize()
        vtk_sp_grid_data.SetNumberOfComponents(3)
        vtk_sp_grid_data.SetNumberOfTuples(size // 3)
        vtk_sp_grid_points = vtk.vtkPoints()
        vtk_sp_grid_points.SetData(vtk_sp_grid_data)
        self.vtk_spherical_points = vtk.vtkPoints()
        self.shperical_to_xyz_trans.TransformPoints(vtk_sp_grid_points, self.vtk_spherical_points)

    def initializePointsActor(self, polydata, **args):
        lut = args.get('lut', None)
        if lut == None: lut = self.create_LUT()
        if vtk.VTK_MAJOR_VERSION <= 5:
            self.mapper.SetInput(self.polydata)
        else:
            self.mapper.SetInputData(self.polydata)
        if lut:  self.mapper.SetLookupTable(lut)

    #        if self.vrange:
    #            self._mapper.SetScalarRange( self.vrange[0], self.vrange[1] )
    #            self.printLogMessage( " init scalar range %s " % str(self.vrange) )

    def getNumberOfPoints(self):
        return len(self.np_points_data) // 3

    def getPoints(self, **args):
        if self.topo == PlotType.Spherical:
            if not self.vtk_spherical_points:
                self.refresh()
                self.computeSphericalPoints()
            return self.vtk_spherical_points
        if self.topo == PlotType.Planar:
            if not self.vtk_planar_points:
                self.initPoints(**args)
            return self.vtk_planar_points

    def updatePoints(self, clear=False):
        if clear:
            self.np_points_data = self.point_collection.getPoints()
            self.vrange = self.point_collection.getVarDataRange()
            self.vtk_spherical_points = None
            self.vtk_planar_points = None
        self.polydata.SetPoints(self.getPoints())

    @classmethod
    def getXYZPoint(cls, lon, lat, r=None):
        theta = (90.0 - lat) * cls.radian_scaling
        phi = lon * cls.radian_scaling
        spherical_coords = (r, theta, phi)
        return cls.shperical_to_xyz_trans.TransformDoublePoint(*spherical_coords)

    def setTopo(self, topo, **args):
        if topo != self.topo:
            self.topo = topo
            self.clearClipping()
            #            if self.actor.GetVisibility():
            pts = self.getPoints(**args)
            self.polydata.SetPoints(pts)
            return pts
        return None

    def setVisiblity(self, visibleLevelIndex):
        isVisible = (visibleLevelIndex < 0) or (visibleLevelIndex == self.iLevel)
        if isVisible:
            self.updatePoints()
        self.actor.SetVisibility(isVisible)
        return isVisible

    def isVisible(self):
        return self.actor.GetVisibility()

    def hide(self):
        #        print "PointCloud- hide()"
        self.actor.VisibilityOff()

    def show(self):
        if not self.actor.GetVisibility():
            self.actor.VisibilityOn()

    def getBounds(self, **args):
        topo = args.get('topo', self.topo)
        lev = args.get('lev', None)
        if topo == PlotType.Spherical:
            return [-self.earth_radius, self.earth_radius, -self.earth_radius, self.earth_radius, -self.earth_radius, self.earth_radius]
        else:
            b = list(self.grid_bounds)
            #            if lev:
            #                lev_bounds = ( lev[0], lev[-1] )
            #                b[4] = lev_bounds[0] if ( lev_bounds[0] < lev_bounds[1] ) else lev_bounds[1]
            #                b[5] = lev_bounds[1] if ( lev_bounds[0] < lev_bounds[1] ) else lev_bounds[0]
            #            elif ( b[4] == b[5] ):
            #                b[4] = b[4] - 100.0
            #                b[5] = b[5] + 100.0
            return b

    def getAxisBounds(self, **args):
        return list(self.grid_bounds)

    #         topo = args.get( 'topo', self.topo )
    #         lev = args.get( 'lev', None )
    #         if topo == PlotType.Spherical:
    #             return [ 0.0, 360.0, -90.0, 90.0, -self.earth_radius, self.earth_radius ]
    #         else:
    #             b = list( self.grid_bounds )
    # #            if lev:
    # #                lev_bounds = ( lev[0], lev[-1] )
    # #                b[4] = lev_bounds[0] if ( lev_bounds[0] < lev_bounds[1] ) else lev_bounds[1]
    # #                b[5] = lev_bounds[1] if ( lev_bounds[0] < lev_bounds[1] ) else lev_bounds[0]
    # #            elif ( b[4] == b[5] ):
    # #                b[4] = b[4] - 100.0
    # #                b[5] = b[5] + 100.0
    #             return b

    def setClipping(self, clippingPlanes):
        self.mapper.SetClippingPlanes(clippingPlanes)

    def clearClipping(self):
        self.mapper.RemoveAllClippingPlanes()

    def setPointSize(self, point_size):
        if point_size != None:
            try:
                self.actor.GetProperty().SetPointSize(point_size)
            except TypeError:
                print("Error setting point size: value = %s " % str(point_size), file=sys.stderr)

    def getPointSize(self):
        return self.actor.GetProperty().GetPointSize()

    def getPointValue(self, iPt):
        return self.var_data[iPt]

    def create_LUT(self, **args):
        lut = vtk.vtkLookupTable()
        lut_type = args.get('type', "blue-red")
        invert = args.get('invert', False)
        number_of_colors = args.get('number_of_colors', 256)
        alpha_range = 1.0, 1.0

        if lut_type == "blue-red":
            if invert:
                hue_range = 0.0, 0.6667
            else:
                hue_range = 0.6667, 0.0
            saturation_range = 1.0, 1.0
            value_range = 1.0, 1.0

        lut.SetHueRange(hue_range)
        lut.SetSaturationRange(saturation_range)
        lut.SetValueRange(value_range)
        lut.SetAlphaRange(alpha_range)
        lut.SetNumberOfTableValues(number_of_colors)
        lut.SetRampToSQRT()
        lut.Modified()
        lut.ForceBuild()
        return lut
