from hyperclass.util.config import Configuration
from skimage.transform import ProjectiveTransform
import numpy as np
import xarray as xa
import matplotlib as mpl
from typing import List, Union, Tuple, Optional, Dict
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
import matplotlib.pyplot as plt
import os, math, pickle
import rioxarray as rio

def get_color_bounds( color_values: List[float] ) -> List[float]:
    color_bounds = []
    for iC, cval in enumerate( color_values ):
        if iC == 0: color_bounds.append( cval - 0.5 )
        else: color_bounds.append( (cval + color_values[iC-1])/2.0 )
    color_bounds.append( color_values[-1] + 0.5 )
    return color_bounds


class Tile:

    def __init__(self, data_manager: "DataManager", iy: int, ix: int, **kwargs ):
        self.config = kwargs
        self.dm = data_manager
        self.tile_coords = (iy,ix)
        self._data: xa.DataArray = None
        self._transform: ProjectiveTransform = None


    @property
    def data(self) -> xa.DataArray:
        if self._data is None:
            self._data: xa.DataArray = self.dm.getTileData( *self.tile_coords, **self.config )
        return self._data

    @property
    def name(self) -> str:
        return f"{self.dm.image_name}.{self.dm.tile_shape[0]}-{self.dm.tile_shape[1]}_{self.tile_coords[0]}-{self.tile_coords[0]}"

    @property
    def transform(self) -> ProjectiveTransform:
        if self._transform is None:
            self._transform = ProjectiveTransform( np.array(list(self.data.transform) + [0, 0, 1]).reshape(3, 3) )
        return self._transform

    @property
    def filename(self) -> str:
        return self.data.attrs['filename']

    @property
    def nBlocks(self) -> List[ List[int] ]:
        return [ self.data.shape[i+1]//self.dm.block_shape[i] for i in [1,2] ]

    def getBlock(self, iy: int, ix: int) -> "Block":
        return Block( self, iy, ix )

    def getBandPointData( self, iband: int, subsampling: int = 1,  **kwargs  ) -> xa.DataArray:
        band_data: xa.DataArray = self.data[iband]
        point_data = band_data.stack(samples=band_data.dims).dropna(dim="samples")
        return point_data[::subsampling]

    def getPointData( self, subsampling: int ) -> xa.DataArray:
        point_data = self.dm.raster2points( self.data )
        return point_data[::subsampling]

    def coords2index(self, cy, cx ) -> Tuple[int,int]:
        coords = self.transform.inverse(np.array([[cx, cy], ]))
        return (math.floor(coords[0, 0]), math.floor(coords[0, 1]))

    def index2coords(self, iy, ix ) -> Tuple[float,float]:
        return self.transform(np.array([[ix+0.5, iy+0.5], ]))

class Block:

    def __init__(self, tile: Tile, iy: int, ix: int, **kwargs ):
        self.tile: Tile = tile
        self.config = kwargs
        self.block_coords = (iy,ix)
        self.data = self._getData()
        self.transform = ProjectiveTransform( np.array( list(self.data.transform) + [0,0,1] ).reshape(3,3) )

    def _getData( self ) -> xa.DataArray:
        ybounds, xbounds = self.getBounds()
        block_raster = self.tile.data[:, ybounds[0]:ybounds[1], xbounds[0]:xbounds[1] ]
        block_raster.attrs['block_coords'] = self.block_coords
        return block_raster

    @property
    def shape(self) -> Tuple[int,int]:
        return self.tile.dm.block_shape

    def getBounds(self ) -> Tuple[ Tuple[int,int], Tuple[int,int] ]:
        y0, x0 = self.block_coords[0]*self.shape[0], self.block_coords[1]*self.shape[1]
        return ( y0, y0+self.shape[0] ), ( x0, x0+self.shape[1] )

    def getPointData( self ) -> xa.DataArray:
        return self.tile.dm.raster2points( self.data )

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

    def coords2index(self, cy, cx ) -> Tuple[int,int]:
        coords = self.transform.inverse(np.array([[cx, cy], ]))
        return (math.floor(coords[0, 0]), math.floor(coords[0, 1]))

    def index2coords(self, iy, ix ) -> Tuple[float,float]:
        return self.transform(np.array([[ix+0.5, iy+0.5], ]))


class DataManager:

    valid_bands = [ [3,193], [210,287], [313,421] ]

    def __init__(self, image_name: str,  **kwargs ):   # Tile shape (y,x) matches image shape (row,col)
        self.config = Configuration( **kwargs )
        self.image_name = image_name[:-4] if image_name.endswith(".tif") else image_name
        self.tile_shape = self.config.getShape( 'tile_shape' )
        self.block_shape = self.config.getShape( 'block_shape' )
        self.tiles = {}

    def getTileBounds(self, iy: int, ix: int ) -> Tuple[ Tuple[int,int], Tuple[int,int] ]:
        y0, x0 = iy*self.tile_shape[0], ix*self.tile_shape[1]
        return ( y0, y0+self.tile_shape[0] ), ( x0, x0+self.tile_shape[1] )

    def getTile(self, iy: int, ix: int ) -> Tile:
        cached_tile: Tile = self.tiles.get( (iy,ix), None )
        if cached_tile is not None: return cached_tile
        new_tile = Tile( self, iy, ix )
        self.tiles[ (iy,ix) ] = new_tile
        return new_tile

    def getTileData(self, iy: int, ix: int, **kwargs ):
        tile_data: Optional[xa.DataArray] = self._readTileFile( iy, ix )
        if tile_data is None: tile_data = self._getTileDataFromImage( iy, ix )
        tile_data = self.mask_nodata( tile_data )
        if self.valid_bands:
            dataslices = [tile_data.isel(band=slice(valid_band[0], valid_band[1])) for valid_band in self.valid_bands]
            tile_data = xa.concat(dataslices, dim="band")
            print( f"Selecting valid bands, resulting Tile shape = {tile_data.shape}")
        return self.rescale(tile_data, **kwargs)

    def _computeNorm(self, tile_raster: xa.DataArray, refresh=False ) -> xa.DataArray:
        norm_file = os.path.join( self.config['data_dir'], self.normFileName )
        if not refresh and os.path.isfile( norm_file ):
            print( f"Loading norm from global norm file {norm_file}")
            return xa.DataArray.from_dict( pickle.load( open( norm_file, 'rb' ) ) )
        else:
            print(f"Computing norm and saving to global norm file {norm_file}")
            norm: xa.DataArray = tile_raster.mean(dim=['x','y'], skipna=True )
            pickle.dump( norm.to_dict(), open( norm_file, 'wb' ) )
            return norm

    def _getTileDataFromImage(self, iy: int, ix: int ) -> xa.DataArray:
        full_input_bands: xa.DataArray = self.readGeotiff( self.image_name )
        ybounds, xbounds = self.getTileBounds( iy, ix )
        tile_raster = full_input_bands[:, ybounds[0]:ybounds[1], xbounds[0]:xbounds[1] ]
        tile_filename = self.tileFileName(iy, ix)
        tile_raster.attrs['tile_coords'] =(iy,ix)
        tile_raster.attrs['filename'] = tile_filename
        self.writeGeotiff( tile_raster, tile_filename )
        return tile_raster

    def _readTileFile( self, iy: int, ix: int, iband = -1 ) -> Optional[xa.DataArray]:
        tile_filename =self.tileFileName(iy, ix)
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


    def writeGeotiff(self, raster_data: xa.DataArray, filename: str) -> str:
        if not filename.endswith(".tif"): filename = filename + ".tif"
        output_file = os.path.join(self.config['data_dir'], filename )
        print(f"Writing raster file {output_file}")
        raster_data.rio.to_raster(output_file)
        return output_file

    def readGeotiff( self, filename: str, iband = -1 ) -> Optional[xa.DataArray]:
        if not filename.endswith(".tif"): filename = filename + ".tif"
        input_file = os.path.join( self.config['data_dir'], filename )
        if os.path.isfile( input_file ):
            print( f"Reading raster file {input_file}")
            input_bands: xa.DataArray =  rio.open_rasterio(input_file)
            if iband >= 0:
                return input_bands[iband]
            else:
                return input_bands
        else:
            return None

    @classmethod
    def mask_nodata(self, raster: xa.DataArray ) -> xa.DataArray:
        nodata_value = raster.attrs.get( 'data_ignore_value', -9999 )
        return raster.where(raster != nodata_value, float('nan'))

    def tileFileName(self, iy: int, ix: int) -> str:
        return f"{self.image_name}.{self.tile_shape[0]}-{self.tile_shape[1]}_{iy}-{ix}"

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

    def rescale(self, raster: xa.DataArray, refresh=False):
        norm = self._computeNorm( raster, refresh )
        result =  raster / norm
        result.attrs = raster.attrs
        return result

    @classmethod
    def raster2points(cls, raster: xa.DataArray ) -> xa.DataArray:
        transposed_raster = raster.stack(samples=raster.dims[1:]).transpose()
        point_data = transposed_raster.dropna(dim='samples', how='any')
        print(f" Creating point data: shape = {point_data.shape}, dims = {point_data.dims}")
        print(f"  -> Using {point_data.shape[0]} valid samples out of {raster.shape[1] * raster.shape[2]} pixels")
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
        x = raster.coords[ raster.dims[1] ]
        y = raster.coords[ raster.dims[0] ]
        try:
            xstep = (x[1] - x[0]) / 2.0
        except IndexError: xstep = .1
        try:
            ystep = (y[1] - y[0]) / 2.0
        except IndexError: ystep = .1
        left, right = x[0] - xstep, x[-1] + xstep
        bottom, top = y[-1] + ystep, y[0] - ystep
        defaults = dict( origin= 'upper', interpolation= 'nearest' )
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
        if "vmax" not in defaults:
            ave = raster.mean(skipna=True)
            std = raster.std(skipna=True)
            defaults['vmin'] = ave - std*colorstretch
            defaults['vmax'] = ave + std*colorstretch
        defaults.update(kwargs)
        if defaults['origin'] == 'upper':   defaults['extent'] = [left, right, bottom, top]
        else:                               defaults['extent'] = [left, right, top, bottom]
        if rescale is not None:
            raster = cls.scale_to_bounds(raster, rescale)
        img = ax.imshow( raster.data, **defaults )
        ax.set_title(title)
        if colorbar and (raster.ndim == 2):
            cbar: Colorbar = ax.figure.colorbar(img, ax=ax, **cbar_kwargs )
            if colors is not None:
                cbar.set_ticklabels( [ cval[1] for cval in colors ] )
        if showplot: plt.show()
        return img
