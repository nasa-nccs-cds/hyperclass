from hyperclass.util.config import Configuration
from skimage.transform import ProjectiveTransform
import numpy as np
import xarray as xa
import pathlib
import matplotlib as mpl
from typing import List, Union, Tuple, Optional, Dict
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from PyQt5.QtCore import QSize, QCoreApplication, QSettings
import matplotlib.pyplot as plt
from typing import TextIO
from pyproj import Proj, transform
import csv
import os, math, pickle
import rioxarray as rio
from hyperclass.graph.flow import ActivationFlow

def get_color_bounds( color_values: List[float] ) -> List[float]:
    color_bounds = []
    for iC, cval in enumerate( color_values ):
        if iC == 0: color_bounds.append( cval - 0.5 )
        else: color_bounds.append( (cval + color_values[iC-1])/2.0 )
    color_bounds.append( color_values[-1] + 0.5 )
    return color_bounds

class MarkerManager:

    def __init__(self, file_name: str,  **kwargs ):
        self.config = QSettings()
        self.file_name = file_name
        self.names = None
        self.colors = None
        self.markers = None

    @property
    def file_path(self):
        data_dir = self.config.value( 'data/cache', "" )
        return os.path.join( data_dir, self.file_name )

    @property
    def hasData(self):
        return self.markers is not None

    def writeMarkers(self, names, colors, markers ):
        try:
            with open( self.file_path, 'wb' ) as f:
                print( f"Saving {len(markers)} labeled points to file {self.file_path}")
                pickle.dump( [ names, colors, markers ], f )
        except Exception as err:
            print( f" Can't save markers: {err}")

    def readMarkers(self):
        try:
            if os.path.isfile(self.file_path):
                print(f"Reading Label data from file {self.file_path}")
                with open(self.file_path, 'rb') as f:
                    label_data = pickle.load( f )
                    if label_data:
                        self.names = label_data[0]
                        self.colors = label_data[1]
                        self.markers = label_data[2]
        except Exception as err:
            print( f" Can't read markers: {err}" )

class Tile:

    def __init__(self, data_manager: "DataManager", **kwargs ):
        self.config = kwargs
        self.dm: DataManager = data_manager
        self._data: xa.DataArray = None
        self._transform: ProjectiveTransform = None
        self.subsampling: int =  kwargs.get('subsample',1)

    @property
    def data(self) -> xa.DataArray:
        if self._data is None:
            self._data: xa.DataArray = self.dm.getTileData(  **self.config )
        return self._data

    def iparm(self, key: str ):
        return int( self.dm.config.value(key) )

    @property
    def name(self) -> str:
        return self.dm.tileFileName()

    @property
    def transform(self) -> Optional[ProjectiveTransform]:
        if self.data is None: return None
        if self._transform is None:
            self._transform = ProjectiveTransform( np.array(list(self.data.transform) + [0, 0, 1]).reshape(3, 3) )
        return self._transform

    def get_block_transform( self, iy, ix ) -> ProjectiveTransform:
        tr0 = self.data.transform
        iy0, ix0 = iy*self.dm.block_shape[0], ix*self.dm.block_shape[1]
        y0, x0 = tr0[5] + iy0 * tr0[4], tr0[2] + ix0 * tr0[0]
        tr1 = [ tr0[0], tr0[1], x0, tr0[3], tr0[4], y0, 0, 0, 1  ]
        return  ProjectiveTransform( np.array(tr1).reshape(3, 3) )

    @property
    def filename(self) -> str:
        return self.data.attrs['filename']

    @property
    def nBlocks(self) -> List[ List[int] ]:
        return [ self.data.shape[i+1]//self.dm.block_shape[i] for i in range(2) ]

    def getBlock(self, iy: int, ix: int, **kwargs ) -> Optional["Block"]:
        init_graph = kwargs.get('init_graph',False)
        if self.data is None: return None
        block = Block( self, iy, ix, **kwargs )
        if init_graph: block.flow_init()
        return block

    def getBandPointData( self, iband: int, **kwargs  ) -> xa.DataArray:
        band_data: xa.DataArray = self.data[iband]
        point_data = band_data.stack(samples=band_data.dims).dropna(dim="samples")
        return point_data[::self.subsampling]

    def getPointData( self, **kwargs ) -> xa.DataArray:
        subsample = kwargs.get( 'subsample', None )
        if subsample is None: subsample = self.subsampling
        point_data = self.dm.raster2points( self.data )
        return point_data[::subsample]

    def coords2index(self, cy, cx ) -> Tuple[int,int]:     # -> iy, ix
        coords = self.transform.inverse(np.array([[cx, cy], ]))
        return (math.floor(coords[0, 1]), math.floor(coords[0, 0]))

    def index2coords(self, iy, ix ) -> Tuple[float,float]:
        return self.transform(np.array([[ix+0.5, iy+0.5], ]))

class Block:

    def __init__(self, tile: Tile, iy: int, ix: int, **kwargs ):
        self.tile: Tile = tile
        self.config = kwargs
        self.block_coords = (iy,ix)
        self.data = self._getData()
        self.transform = tile.get_block_transform( iy, ix )
        self.index_array: xa.DataArray = self.get_index_array()
        self._flow = None
        self._samples_axis: Optional[xa.DataArray] = None
        tr = self.transform.params.flatten()
        self.data.attrs['transform'] = self.transform
        self._xlim = [ tr[2], tr[2] + tr[0] * (self.data.shape[2]) ]
        self._ylim = [ tr[5] + tr[4] * (self.data.shape[1]), tr[5] ]
        self._point_data = None

    def flow_init(self):
        if self._flow is None:
            n_neighbors = self.config.pop( 'n_neighbors', self.iparm('umap/nneighbors') )
            print( f"Computing NN graph using {n_neighbors} neighbors")
            self._flow = ActivationFlow( n_neighbors=n_neighbors, **self.config )
            self._flow.setNodeData( self.getPointData() )

    @property
    def flow(self):
        self.flow_init()
        return self._flow

    def _getData( self ) -> Optional[xa.DataArray]:
        if self.tile.data is None: return None
        ybounds, xbounds = self.getBounds()
        block_raster = self.tile.data[:, ybounds[0]:ybounds[1], xbounds[0]:xbounds[1] ]
        block_raster.attrs['block_coords'] = self.block_coords
        block_raster.name = f"{self.tile.name}_b-{self.block_coords[0]}-{self.block_coords[1]}"
        return block_raster

    def get_index_array(self) -> xa.DataArray:
        point_data: xa.DataArray = self.tile.dm.raster2points(self.data)
        indices = range( point_data.shape[0] )
        point_index_array = xa.DataArray( indices, dims=["samples"], coords=dict(samples=point_data.coords['samples']) )
        return point_index_array.unstack(fill_value=-1)

    def iparm(self, key: str ):
        return int( self.tile.dm.config.value(key) )

    @property
    def xlim(self): return self._xlim

    @property
    def ylim(self): return self._ylim

    def extent(self, epsg: int = None ) -> List[float]:   # left, right, bottom, top
        if epsg is None:
            return [ self.xlim[0], self.xlim[1], self.ylim[0], self.ylim[1] ]
        else:
            inProj = Proj( self.data.spatial_ref.crs_wkt )
            outProj = Proj(epsg)
            y, x = transform( inProj, outProj, self.xlim, self.ylim )
            return x + y

    def inBounds(self, yc: float, xc: float ) -> bool:
        if (yc < self._ylim[0]) or (yc > self._ylim[1]): return False
        if (xc < self._xlim[0]) or (xc > self._xlim[1]): return False
        return True

    @property
    def shape(self) -> Tuple[int,int]:
        return self.tile.dm.block_shape

    def getBounds(self ) -> Tuple[ Tuple[int,int], Tuple[int,int] ]:
        y0, x0 = self.block_coords[0]*self.shape[0], self.block_coords[1]*self.shape[1]
        return ( y0, y0+self.shape[0] ), ( x0, x0+self.shape[1] )

    def getPointData( self, **kwargs ) -> xa.DataArray:
        if self._point_data is None:
            subsample = kwargs.get( 'subsample', None )
            result: xa.DataArray =  self.tile.dm.raster2points( self.data )
            self._point_data =  result if subsample is None else result[::subsample]
            self._samples_axis = self._point_data.coords['samples']
        return self._point_data

    @property
    def samples_axis(self) -> xa.DataArray:
        if self._samples_axis is None: self.getPointData()
        return  self._samples_axis

    def getSelectedPointData( self, cy: List[float], cx: List[float] ) -> np.ndarray:
        yIndices, xIndices = self.multi_coords2indices(cy, cx)
        return  self.data.values[ :, yIndices, xIndices ].transpose()

    def getSelectedPointIndices( self, cy: List[float], cx: List[float] ) -> np.ndarray:
        yIndices, xIndices = self.multi_coords2indices(cy, cx)
        return  yIndices * self.shape[1] + xIndices

    def getSelectedPoint( self, cy: float, cx: float ) -> np.ndarray:
        index = self.coords2indices(cy, cx)
        return self.data[ :, index['iy'], index['ix'] ].values.reshape(1, -1)

    def plot(self,  **kwargs ) -> xa.DataArray:
        color_band = kwargs.pop( 'color_band', None )
        band_range = kwargs.pop( 'band_range', None )
        if color_band is not None:
            plot_data = self.data[color_band]
        elif band_range is not None:
            plot_data = self.data.isel( band=slice( band_range[0], band_range[1] ) ).mean(dim="band", skipna=True)
        else:
            plot_data =  self.tile.dm.getRGB(self.data)
        self.tile.dm.plotRaster( plot_data, **kwargs )
        return plot_data

    def coords2indices(self, cy, cx) -> Dict:
        coords = self.transform.inverse(np.array([[cx, cy], ]))
        return dict( iy =math.floor(coords[0, 1]), ix = math.floor(coords[0, 0]) )

    def multi_coords2indices(self, cy: List[float], cx: List[float]) -> Tuple[np.ndarray, np.ndarray]:
        coords = np.array( list( zip( cx, cy ) ) )
        trans_coords = np.floor(self.transform.inverse(coords))
        indices = trans_coords.transpose().astype( np.int16 )
        return indices[1], indices[0]

    def indices2coords(self, iy, ix) -> Dict:
        (iy,ix) = self.transform(np.array([[ix+0.5, iy+0.5], ]))
        return dict( iy = iy, ix = ix )

    def pindex2coords(self, point_index: int) -> Dict:
        selected_sample: List = self.samples_axis.values[point_index]
        return dict( y = selected_sample[0], x = selected_sample[1] )

    def indices2pindex( self, iy, ix ) -> int:
        return self.index_array.values[ iy, ix ]

    def coords2pindex( self, cy, cx ) -> int:
        index = self.coords2indices( cy, cx )
        return self.index_array.values[ index['iy'], index['ix'] ]

    def multi_coords2pindex(self, ycoords: List[float], xcoords: List[float] ) -> np.ndarray:
        ( yi, xi ) = self.multi_coords2indices( ycoords, xcoords )
        return self.index_array.values[ yi, xi ]

class DataManager:

    valid_bands = [ [3,193], [210,287], [313,421] ]

    default_settings = { 'block/size': 300, "umap/nneighbors": 8, "umap/nepochs": 300, 'tile/nblocks': 16,
                         'block/indices': [0,0], 'tile/indices': [0,0], "svm/ndim": 8  }

    def __init__(self, image_name: str,  **kwargs ):   # Tile shape (y,x) matches image shape (row,col)
        self.getDefaultSettings()
        self.config= QSettings()
        self.image_name = image_name[:-4] if image_name.endswith(".tif") else image_name
        [self.iy, self.ix] = self.tile_index
        self.markers = MarkerManager( self.markerFileName() + ".pkl" )
        self.tile = None

    @classmethod
    def root_dir(cls) -> str:
        parent_dirs = pathlib.Path(__file__).parents
        return parent_dirs[ 3 ]

    @classmethod
    def settings_dir(cls) -> str:
        return os.path.join( cls.root_dir(), 'config' )

    @classmethod
    def getDefaultSettings(cls) -> QSettings:
        system_settings_dir = cls.settings_dir()
        QSettings.setPath( QSettings.IniFormat, QSettings.SystemScope, system_settings_dir )
        settings = QSettings( QSettings.IniFormat, QSettings.SystemScope, 'nccs.nasa.gov', 'hyperclass' )
        print( f"Saving system settings to {settings.fileName()}, writable = {settings.isWritable()}")
        for key, value in cls.default_settings.items():
            current = settings.value( key )
            if not current: settings.setValue( key, value )
        return settings

    @property
    def tile_shape(self):
        block_size = self.config.value( 'block/size', 250 )
        tile_size =  round( math.sqrt( self.config.value( 'tile/nblocks', 16 ) ) ) * block_size
        return  [ tile_size, tile_size ]

    @property
    def block_shape(self):
        block_size = self.config.value( 'block/size', 250 )
        return  [ block_size, block_size ]

    @property
    def tile_index(self):
        return  self.config.value( 'tile/indices', [0,0] )

    @classmethod
    def extent(cls, image_data: xa.DataArray ) -> List[float]: # left, right, bottom, top
        xc, yc = image_data.coords[image_data.dims[-1]].values, image_data.coords[image_data.dims[-2]].values
        dx2, dy2 = (xc[1]-xc[0])/2, (yc[0]-yc[1])/2
        return [ xc[0]-dx2,  xc[-1]+dx2,  yc[-1]-dy2,  yc[0]+dy2 ]

    def getTileBounds(self) -> Tuple[ Tuple[int,int], Tuple[int,int] ]:
        y0, x0 = self.iy*self.tile_shape[0], self.ix*self.tile_shape[1]
        return ( y0, y0+self.tile_shape[0] ), ( x0, x0+self.tile_shape[1] )

    def getTile(self) -> Tile:
        if self.tile is None:
            self.tile = Tile( self )
        return self.tile

    def getXArray(self, fill_value: float, shape: Tuple[int], dims: Tuple[str], **kwargs ) -> xa.DataArray:
        coords = kwargs.get( "coords", { dim: np.arange(shape[id]) for id, dim in enumerate(dims) } )
        result: xa.DataArray = xa.DataArray( np.full( shape, fill_value ), dims=dims, coords=coords )
        result.attrs.update( kwargs.get("attrs",{}) )
        result.name = kwargs.get( "name", "")
        return result

    def getTileData(self, **kwargs ) -> Optional[xa.DataArray]:
        tile_data: Optional[xa.DataArray] = self._readTileFile()
        if tile_data is None: tile_data = self._getTileDataFromImage()
        if tile_data is None: return None
        tile_data = self.mask_nodata( tile_data )
        if self.valid_bands:
            dataslices = [tile_data.isel(band=slice(valid_band[0], valid_band[1])) for valid_band in self.valid_bands]
            tile_data = xa.concat(dataslices, dim="band")
            print( f"Selecting valid bands, resulting Tile shape = {tile_data.shape}")
        return self.rescale(tile_data, **kwargs)

    def _computeNorm(self, tile_raster: xa.DataArray, refresh=False ) -> xa.DataArray:
        norm_file = os.path.join( self.config.value('data/cache'), self.normFileName )
        if not refresh and os.path.isfile( norm_file ):
            print( f"Loading norm from global norm file {norm_file}")
            return xa.DataArray.from_dict( pickle.load( open( norm_file, 'rb' ) ) )
        else:
            print(f"Computing norm and saving to global norm file {norm_file}")
            norm: xa.DataArray = tile_raster.mean(dim=['x','y'], skipna=True )
            pickle.dump( norm.to_dict(), open( norm_file, 'wb' ) )
            return norm

    def _getTileDataFromImage(self) -> Optional[xa.DataArray]:
        full_input_bands: xa.DataArray = self.readGeotiff( self.image_name )
        if full_input_bands is None: return None
        ybounds, xbounds = self.getTileBounds()
        tile_raster = full_input_bands[:, ybounds[0]:ybounds[1], xbounds[0]:xbounds[1] ]
        tile_filename = self.tileFileName()
        tile_raster.attrs['tile_coords'] = self.tile_index
        tile_raster.attrs['filename'] = tile_filename
        self.writeGeotiff( tile_raster, tile_filename )
        return tile_raster

    def _readTileFile( self, iband = -1 ) -> Optional[xa.DataArray]:
        tile_filename =self.tileFileName()
        print(f"Reading tile file {tile_filename}")
        tile_raster: Optional[xa.DataArray] = self.readGeotiff(tile_filename, iband)
        if tile_raster is not None:
            tile_raster.name = f"{self.image_name}: Band {iband+1}" if( iband >= 0 ) else self.image_name
            tile_raster.attrs['filename'] = tile_filename
        return tile_raster

    @classmethod
    def getRGB(cls, raster_data: xa.DataArray ) -> xa.DataArray:
        b = raster_data.isel( band=slice( 13, 27 ) ).mean(dim="band", skipna=True)
        g = raster_data.isel( band=slice( 29, 44 ) ).mean(dim="band", skipna=True)
        r = raster_data.isel( band=slice( 51, 63 ) ).mean(dim="band", skipna=True)
        rgb: xa.DataArray = xa.concat( [r,g,b], 'band' )
        return cls.scale_to_bounds( rgb, (0, 1) ).transpose('y', 'x', 'band')


    def writeGeotiff(self, raster_data: xa.DataArray, filename: str = None ) -> str:
        if filename is None: filename = raster_data.name
        if not filename.endswith(".tif"): filename = filename + ".tif"
        output_file = os.path.join(self.config.value('data/cache'), filename )
        print(f"Writing raster file {output_file}")
        raster_data.rio.to_raster(output_file)
        return output_file

    def readGeotiff( self, filename: str, iband = -1 ) -> Optional[xa.DataArray]:
        if not filename.endswith(".tif"): filename = filename + ".tif"
        try:
            input_file = os.path.join(self.config.value('data/dir'), filename)
            input_bands: xa.DataArray =  rio.open_rasterio(input_file)
            print(f"Reading raster file {input_file}")
            if iband >= 0:  return input_bands[iband]
            else:           return input_bands
        except Exception as err:
            print( f"WARNING: can't read input file {filename}: {err}")
            return None

    @classmethod
    def mask_nodata(self, raster: xa.DataArray ) -> xa.DataArray:
        nodata_value = raster.attrs.get( 'data_ignore_value', -9999 )
        return raster.where(raster != nodata_value, float('nan'))

    def tileFileName(self) -> str:
        return f"{self.image_name}.{self._fmt(self.tile_shape)}_{self._fmt(self.tile_index)}"

    def _cfg(self, settings_key: str ) -> str:
        return self._fmt( self.config.value( settings_key ) )

    def _fmt(self, value) -> str:
        return str(value).strip("([ ])").replace(",", "-")

    def markerFileName(self) -> str:
        return f"tdata_{self.image_name}.{self._cfg('tile_shape')}_{self._cfg('tile_index')}"

    @property
    def normFileName( self ) -> str:
        return f"global_norm.pkl"

    @classmethod
    def scale_to_bounds(cls, raster: xa.DataArray, bounds: Tuple[float, float] ) -> xa.DataArray:
        vmin = raster.min( dim=raster.dims[:2], skipna=True )
        vmax = raster.max(dim=raster.dims[:2], skipna=True )
        scale = (bounds[1]-bounds[0])/(vmax-vmin)
        return  (raster - vmin)*scale + bounds[0]

    @classmethod
    def norm_to_bounds(cls, raster: xa.DataArray, dims: Tuple[str, str], bounds: Tuple[float, float], stretch: float ) -> xa.DataArray:
        scale = ( ( bounds[1] - bounds[0] ) * stretch ) / raster.std(dim=['x', 'y'])
        return  ( raster - raster.mean(dim=dims) ) * scale + (( bounds[1] + bounds[0] )/2.0)

    @classmethod
    def unit_norm(cls, raster: xa.DataArray, dim: List[str] ):
        std: xa.DataArray = raster.std(dim=dim, skipna=True)
        meanval: xa.DataArray = raster.mean(dim=dim, skipna=True)
        unit_centered: xa.DataArray = ( ( raster - meanval ) / std ) + 0.5
        unit_centered = unit_centered.where( unit_centered > 0, 0 )
        unit_centered = unit_centered.where(unit_centered < 1, 1 )
        return unit_centered

    @classmethod
    def normalize(cls, raster: xa.DataArray, scale = 1.0, center = True ):
        std = raster.std(dim=['x','y'], skipna=True)
        if center:
            meanval = raster.mean(dim=['x','y'], skipna=True)
            centered= raster - meanval
        else:
            centered = raster
        result =  centered * scale / std
        result.attrs = raster.attrs
        return result

    def rescale(self, raster: xa.DataArray, refresh=False) -> xa.DataArray:
        norm = self._computeNorm( raster, refresh )
        result =  raster / norm
        result.attrs = raster.attrs
        return result

    @classmethod
    def raster2points(cls, raster: xa.DataArray ) -> xa.DataArray:
        stacked_raster = raster.stack(samples=raster.dims[-2:]).transpose()
        if np.issubdtype( raster.dtype, np.integer ):
            nodata = stacked_raster.attrs.get('_FillValue',-2)
            point_data = stacked_raster.where( stacked_raster != nodata, drop=True ).astype(np.int16)
        else:
            point_data = stacked_raster.dropna(dim='samples', how='any')
        print(f" raster2points -> [{raster.name}]: Using {point_data.shape[0]} valid samples out of {stacked_raster.shape[0]} pixels")
        return point_data

    @classmethod
    def plotRaster(cls, raster: xa.DataArray, **kwargs ):
        from matplotlib.colorbar import Colorbar
        ax = kwargs.pop( 'ax', None )
        showplot = ( ax is None )
        if showplot: fig, ax = plt.subplots(1,1)
        colors = kwargs.pop('colors', None )
        title = kwargs.pop( 'title', raster.name )
        rescale = kwargs.pop( 'rescale', None )
        colorbar = kwargs.pop( 'colorbar', True )
        colorstretch = kwargs.pop( 'colorstretch', 1.5 )
        x = raster.coords[ raster.dims[1] ].values
        y = raster.coords[ raster.dims[0] ].values
        try:
            xstep = (x[1] - x[0]) / 2.0
        except IndexError: xstep = .1
        try:
            ystep = (y[1] - y[0]) / 2.0
        except IndexError: ystep = .1
        left, right = x[0] - xstep, x[-1] + xstep
        bottom, top = y[-1] + ystep, y[0] - ystep
        defaults = dict( origin= 'upper', interpolation= 'nearest' )
        defaults["alpha"] = kwargs.get( "alpha", 1.0 )
        cbar_kwargs = {}
        if colors is  None:
            defaults.update( dict( cmap="jet" ) )
        else:
            rgbs = [ cval[2] for cval in colors ]
            cmap: ListedColormap = ListedColormap( rgbs )
            color_values = [ float(cval[0]) for cval in colors]
            color_bounds = get_color_bounds(color_values)
            norm = mpl.colors.BoundaryNorm( color_bounds, len( colors )  )
            cbar_kwargs.update( dict( cmap=cmap, norm=norm, boundaries=color_bounds, ticks=color_values, spacing='proportional' ) )
            defaults.update( dict( cmap=cmap, norm=norm ) )
        if not hasattr(ax, 'projection'): defaults['aspect'] = 'auto'
        vrange = kwargs.pop( 'vrange', None )
        if vrange is not None:
            defaults['vmin'] = vrange[0]
            defaults['vmax'] = vrange[1]
        if (colors is  None) and ("vmax" not in defaults):
            ave = raster.mean(skipna=True).values
            std = raster.std(skipna=True).values
            defaults['vmin'] = ave - std*colorstretch
            defaults['vmax'] = ave + std*colorstretch
        defaults.update(kwargs)
        if defaults['origin'] == 'upper':   defaults['extent'] = [left, right, bottom, top]
        else:                               defaults['extent'] = [left, right, top, bottom]
        if rescale is not None:
            raster = cls.scale_to_bounds(raster, rescale)
        img = ax.imshow( raster.data, zorder=1, **defaults )
        ax.set_title(title)
        if colorbar and (raster.ndim == 2):
            cbar: Colorbar = ax.figure.colorbar(img, ax=ax, **cbar_kwargs )
            if colors is not None:
                cbar.set_ticklabels( [ cval[1] for cval in colors ] )
        if showplot: plt.show()
        return img
