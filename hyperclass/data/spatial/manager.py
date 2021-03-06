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
from hyperclass.data.manager import DataManager
from hyperclass.gui.config import SettingsManager
from hyperclass.util.accessor import _register_accessor
def register_datamanager_accessor(name): return _register_accessor(name, DataManager)

def get_color_bounds( color_values: List[float] ) -> List[float]:
    color_bounds = []
    for iC, cval in enumerate( color_values ):
        if iC == 0: color_bounds.append( cval - 0.5 )
        else: color_bounds.append( (cval + color_values[iC-1])/2.0 )
    color_bounds.append( color_values[-1] + 0.5 )
    return color_bounds

def get_rounded_dims( master_shape: List[int], subset_shape: List[int] ) -> List[int]:
    dims = [ int(round(ms/ss)) for (ms,ss) in zip(master_shape,subset_shape) ]
    return [ max(d, 1) for d in dims ]

class MarkerManager:

    def __init__(self, file_name: str, config: QSettings, **kwargs ):
        self.file_name = file_name
        self.names = None
        self.colors = None
        self.markers = None
        self.config = config

    @property
    def file_path(self):
        if self.file_name.startswith( "/" ):
            return self.file_name
        else:
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


class SpatialDataManager():

    def __init__( self, settings: SettingsManager, **kwargs ):   # Tile shape (y,x) matches image shape (row,col)
        self._settings = settings
        self.cacheTileData = kwargs.get( 'cache_tile', True )
        self._image_name = None

    @property
    def config(self):
        return self._settings.config

    def setImageName( self, fileName: str ):
        image_name = fileName[:-4] if fileName.endswith(".tif") else fileName
        self.config.setValue( "data/init/file", image_name )

    @property
    def image_name(self):
        if self._image_name is None:
            self._image_name = self.config.value("data/init/file")
        return self._image_name

    @property
    def tile_shape(self) -> List[int]:
        return self.config.value( 'tile/shape', [ 1000, 1000 ], type=int )

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

    def setTilesPerImage( self, image_specs ):
        block_size = self.config.value( 'block/size', 250, type=int)
        tile_size  = self.config.value( 'tile/size', 1000, type=int)
        ishape = image_specs['shape'] if image_specs else [ tile_size, tile_size ]
        tile_array_shape = get_rounded_dims( ishape, [tile_size]*2 )
        tile_shape = get_rounded_dims( ishape, tile_array_shape )
        block_array_shape = get_rounded_dims( tile_shape, [ block_size ]*2  )
        block_shape = get_rounded_dims( tile_shape, block_array_shape )
        self.config.setValue( 'tile/shape', tile_shape )
        self.config.setValue( 'tile/array_shape', tile_array_shape )
        self.config.setValue( 'block/shape', block_shape )
        self.config.setValue( 'block/array_shape', block_array_shape)

    def getTileData(self, **kwargs ) -> Optional[xa.DataArray]:
        tile_data: Optional[xa.DataArray] = self._readTileFile() if self.cacheTileData else None
        if tile_data is None: tile_data = self._getTileDataFromImage()
        if tile_data is None: return None
        tile_data = self.mask_nodata( tile_data )
        init_shape = [ *tile_data.shape ]
        valid_bands =   self.config.value('data/valid_bands', None ) # [[0, 195], [214, 286], [319, 421]] #
        if valid_bands is not None:
            dataslices = [tile_data.isel(band=slice(valid_band[0], valid_band[1])) for valid_band in valid_bands]
            tile_data = xa.concat(dataslices, dim="band")
            print( f"-------------\n         ***** Selecting valid bands ({valid_bands}), init_shape = {init_shape}, resulting Tile shape = {tile_data.shape}")
        result =  self.rescale(tile_data, **kwargs)
        return result

    def set_tile_transform( self, data: xa.DataArray ):
        tr0 = data.transform
        tile_indices = [ int(iv) for iv in self.config.value( "tile/indices", [0,0] ) ]
        iy0, ix0 =  tile_indices[0] * self.tile_shape[0], tile_indices[1] * self.tile_shape[1]
        y0, x0 = tr0[5] + iy0 * tr0[4], tr0[2] + ix0 * tr0[0]
        data.attrs['transform'] = [ tr0[0], tr0[1], x0, tr0[3], tr0[4], y0  ]

    def _computeSpatialNorm(self, tile_raster: xa.DataArray, refresh=False) -> xa.DataArray:
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
        image_attrs = dict(shape=full_input_bands.shape[-2:], attrs=full_input_bands.attrs)
        self.setTilesPerImage( image_attrs )
        ybounds, xbounds = self.getTileBounds()
        tile_raster = full_input_bands[:, ybounds[0]:ybounds[1], xbounds[0]:xbounds[1] ]
        tile_filename = self.tileFileName()
        tile_raster.attrs['tile_coords'] = self.tile_index
        tile_raster.attrs['filename'] = tile_filename
        tile_raster.attrs['image']  = self.image_name
        tile_raster.attrs['image_shape'] = full_input_bands.shape
        self.config.setValue( self.image_name, image_attrs )
        self.set_tile_transform( tile_raster )
        if self.cacheTileData: self.writeGeotiff( tile_raster, tile_filename )
        return tile_raster

    def _readTileFile( self, iband = -1 ) -> Optional[xa.DataArray]:
        tile_filename =self.tileFileName()
        print(f"Reading tile file {tile_filename}")
        tile_raster: Optional[xa.DataArray] = self.readGeotiff(tile_filename, iband)
        if tile_raster is not None:
            tile_raster.name = f"{self.image_name}: Band {iband+1}" if( iband >= 0 ) else self.image_name
            tile_raster.attrs['filename'] = tile_filename
            image_specs = self.config.value(self.image_name, None)
            self.setTilesPerImage( image_specs )
        return tile_raster

    @classmethod
    def getRGB(cls, raster_data: xa.DataArray ) -> xa.DataArray:
        b = raster_data.isel( band=slice( 13, 27 ) ).mean(dim="band", skipna=True)
        g = raster_data.isel( band=slice( 29, 44 ) ).mean(dim="band", skipna=True)
        r = raster_data.isel( band=slice( 51, 63 ) ).mean(dim="band", skipna=True)
        rgb: xa.DataArray = xa.concat( [r,g,b], 'band' )
        return cls.scale_to_bounds( rgb, (0, 1) ).transpose('y', 'x', 'band')


    def writeGeotiff(self, raster_data: xa.DataArray, filename: str = None ) -> str:
        try:
            if filename is None: filename = raster_data.name
            if not filename.endswith(".tif"): filename = filename + ".tif"
            output_file = os.path.join(self.config.value('data/cache'), filename )
            print(f"Writing (raster) tile file {output_file}")
            raster_data.rio.to_raster( output_file )
            return output_file
        except Exception as err:
            print(f"Unable to write raster file to {output_file}: {err}")
            return None

    def readGeotiff( self, filename: str, iband = -1 ) -> Optional[xa.DataArray]:
        if not filename.endswith(".tif"): filename = filename + ".tif"
        try:
            input_file = os.path.join(self.config.value('data/dir'), filename)
            input_bands: xa.DataArray =  rio.open_rasterio(input_file)
            if 'transform' not in input_bands.attrs.keys():
                gts = input_bands.spatial_ref.GeoTransform.split()
                input_bands.attrs['transform'] = [ float(gts[i]) for i in [ 1,2,0,4,5,3 ] ]
            print(f"Reading raster file {input_file}, dims = {input_bands.dims}, shape = {input_bands.shape}")
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

    def _fmt(self, value) -> str:
        return str(value).strip("([])").replace(",", "-").replace(" ", "")

    def _icfg(self, settings_key: str ) -> str:
        return self._fmt( self.config.value( settings_key, type=int ) )

    def markerFileName(self) -> str:
        try:
            return self.image_name.strip("/").replace("/","_")
        except Exception:
            return ""

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

    def rescale(self, raster: xa.DataArray, **kwargs ) -> xa.DataArray:
        norm_type = kwargs.get('norm', 'none')
        refresh = kwargs.get('refresh', False )
        if norm_type == "none":
            result = raster
        else:
            if norm_type == "spatial":
                norm: xa.DataArray = self._computeSpatialNorm( raster, refresh )
            elif norm_type == "spectral":
                norm: xa.DataArray = raster.mean( dim=['band'], skipna=True )
            result =  raster / norm
            result.attrs = raster.attrs
        return result

    @classmethod
    def raster2points(cls, raster: xa.DataArray ) -> xa.DataArray:
        stacked_raster = raster.stack(samples=raster.dims[-2:]).transpose()
        if np.issubdtype( raster.dtype, np.integer ):
            nodata = stacked_raster.attrs.get('_FillValue',-2)
            point_data = stacked_raster.where( stacked_raster != nodata, drop=True ).astype(np.int32)
        else:
            point_data = stacked_raster.dropna(dim='samples', how='any')
        print(f" raster2points -> [{raster.name}]: Using {point_data.shape[0]} valid samples out of {stacked_raster.shape[0]} pixels")
        return point_data

    @classmethod
    def get_color_bounds( cls, raster: xa.DataArray ):
        colorstretch = 1.25
        ave = raster.mean(skipna=True).values
        std = raster.std(skipna=True).values
        return dict( vmin= ave - std*colorstretch, vmax= ave + std*colorstretch  )

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
            defaults.update( cls.get_color_bounds( raster ) )
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


