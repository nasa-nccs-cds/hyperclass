import numpy as np
import xarray as xa
import pathlib
import matplotlib as mpl
from typing import List, Union, Tuple, Optional, Dict
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from PyQt5.QtCore import QSettings, QCoreApplication
import matplotlib.pyplot as plt
import os, math, pickle
import rioxarray as rio

QCoreApplication.setOrganizationName("ilab")
QCoreApplication.setOrganizationDomain("nccs.nasa.gov")
QCoreApplication.setApplicationName("hyperclass")

def get_color_bounds( color_values: List[float] ) -> List[float]:
    color_bounds = []
    for iC, cval in enumerate( color_values ):
        if iC == 0: color_bounds.append( cval - 0.5 )
        else: color_bounds.append( (cval + color_values[iC-1])/2.0 )
    color_bounds.append( color_values[-1] + 0.5 )
    return color_bounds

class MarkerManager:

    def __init__(self, file_name: str, config: QSettings, **kwargs ):
        self.file_name = file_name
        self.names = None
        self.colors = None
        self.markers = None
        self.config = config

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

class DataManager:

    valid_bands = [ [3,193], [210,287], [313,421] ]
    settings_initialized = False
    default_settings = { 'block/size': 300, "umap/nneighbors": 8, "umap/nepochs": 300, 'tile/nblocks': 16,
                         'block/indices': [0,0], 'tile/indices': [0,0], "svm/ndim": 8  }

    def __init__( self, **kwargs ):   # Tile shape (y,x) matches image shape (row,col)
        self.cacheTileData = kwargs.get( 'cache_tile', True )
        self._initDefaultSettings()
        self.config = self.getSettings( QSettings.UserScope )
        print(f"Saving user settings to {self.config.fileName()}, writable = {self.config.isWritable()}")
        self.image_name = None
        self.setImageName( self.config.value("data/init/file") )
        self.markers = MarkerManager( self.markerFileName() + ".pkl", self.config )

    def setImageName( self, image_name: str ):
        if image_name: self.image_name = image_name[:-4] if image_name.endswith(".tif") else image_name

    @classmethod
    def root_dir(cls) -> str:
        parent_dirs = pathlib.Path(__file__).parents
        return parent_dirs[ 3 ]

    @classmethod
    def settings_dir(cls) -> str:
        return os.path.join( cls.root_dir(), 'config' )

    @classmethod
    def getSettings( cls, scope: QSettings.Scope ):
        cls._initDefaultSettings()
        return QSettings(QSettings.IniFormat, scope, QCoreApplication.organizationDomain(), QCoreApplication.applicationName())

    @classmethod
    def _initDefaultSettings(cls):
        if not cls.settings_initialized:
            cls.settings_initialized = True
            system_settings_dir = cls.settings_dir()
            QSettings.setPath( QSettings.IniFormat, QSettings.SystemScope, system_settings_dir )
            settings = cls.getSettings( QSettings.SystemScope )
            print( f"Saving system settings to {settings.fileName()}, writable = {settings.isWritable()}")
            for key, value in cls.default_settings.items():
                current = settings.value( key )
                if not current: settings.setValue( key, value )

    @property
    def tile_shape(self):
        block_size = self.config.value( 'block/size', 250, type=int )
        tile_size =  round( math.sqrt( self.config.value( 'tile/nblocks', 16, type=int ) ) ) * block_size
        return  [ tile_size, tile_size ]

    @property
    def block_shape(self):
        block_size = self.config.value( 'block/size', 250, type=int )
        return  [ block_size, block_size ]

    @property
    def tile_index(self):
        return  self.config.value( 'tile/indices', [0,0], type=int )

    @property
    def iy(self):
        return self.tile_index[0]

    @property
    def ix(self):
        return self.tile_index[1]

    @classmethod
    def extent(cls, image_data: xa.DataArray ) -> List[float]: # left, right, bottom, top
        xc, yc = image_data.coords[image_data.dims[-1]].values, image_data.coords[image_data.dims[-2]].values
        dx2, dy2 = (xc[1]-xc[0])/2, (yc[0]-yc[1])/2
        return [ xc[0]-dx2,  xc[-1]+dx2,  yc[-1]-dy2,  yc[0]+dy2 ]

    def getTileBounds(self) -> Tuple[ Tuple[int,int], Tuple[int,int] ]:
        y0, x0 = self.iy*self.tile_shape[0], self.ix*self.tile_shape[1]
        return ( y0, y0+self.tile_shape[0] ), ( x0, x0+self.tile_shape[1] )

    def getXArray(self, fill_value: float, shape: Tuple[int], dims: Tuple[str], **kwargs ) -> xa.DataArray:
        coords = kwargs.get( "coords", { dim: np.arange(shape[id]) for id, dim in enumerate(dims) } )
        result: xa.DataArray = xa.DataArray( np.full( shape, fill_value ), dims=dims, coords=coords )
        result.attrs.update( kwargs.get("attrs",{}) )
        result.name = kwargs.get( "name", "")
        return result

    def getTileData(self, **kwargs ) -> Optional[xa.DataArray]:
        tile_data: Optional[xa.DataArray] = self._readTileFile() if self.cacheTileData else None
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
        if self.cacheTileData:
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
        return str(value).strip("([])").replace(",", "-").replace(" ", "")

    def markerFileName(self) -> str:
        return f"tdata_{self.image_name}.{self._cfg('block/size')}.{self._cfg('tile/nblocks')}_{self._cfg('tile/indices')}"

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

dataManager = DataManager()


