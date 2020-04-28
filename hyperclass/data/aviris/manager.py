from hyperclass.util.config import Configuration
import xarray as xa
import matplotlib as mpl
from typing import List, Union, Tuple, Optional, Dict
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
import matplotlib.pyplot as plt
import os, math
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
        self.dm = data_manager
        self.tile_coords = (iy,ix)
        self._data: xa.DataArray = None

    @property
    def data(self) -> xa.DataArray:
        if self._data is None:
            self._data: xa.DataArray = self.dm.getTileData(*self.tile_coords)
        return self._data

    @property
    def name(self) -> str:
        return f"{self.dm.image_name}.{self.dm.tile_shape[0]}-{self.dm.tile_shape[1]}_{self.tile_coords[0]}-{self.tile_coords[0]}"

    @property
    def file_path(self) -> str:
        return self.data.attrs['file_path']

    @property
    def block_shape(self) -> Tuple[int,int]:
        return self.dm.block_shape

    def getBlockBounds(self, iy: int, ix: int ) -> Tuple[ Tuple[int,int], Tuple[int,int] ]:
        y0, x0 = iy*self.block_shape[0], ix*self.block_shape[1]
        return ( y0, y0+self.block_shape[0] ), ( x0, x0+self.block_shape[1] )

    @property
    def nBlocks(self) -> List[ List[int] ]:
        return [ self.data.shape[i+1]//self.block_shape[i] for i in [1,2] ]

    def getBlock( self, iy: int, ix: int ) -> xa.DataArray:
        ybounds, xbounds = self.getBlockBounds( iy, ix )
        block_raster = self.data[:, ybounds[0]:ybounds[1], xbounds[0]:xbounds[1] ]
        block_raster.attrs['block_coords'] = (iy, ix)
        return block_raster

    @classmethod
    def getPointData(cls, raster: xa.DataArray ) -> xa.DataArray:
        transposed_raster = raster.stack(samples=raster.dims[1:]).transpose()
        point_data = transposed_raster.dropna(dim='samples', how='any')
        print(f" Creating point data: shape = {point_data.shape}, dims = {point_data.dims}")
        print(f"  -> Using {point_data.shape[0]} valid samples out of {raster.shape[1] * raster.shape[2]} pixels")
        return point_data

    def getBandPointData( self, iband: int, subsampling: int = 1, normalize = 1.0, **kwargs  ) -> Dict[str,xa.DataArray]:
        band_data: xa.DataArray = self.data[iband]
        band_data = self.dm.normalize(band_data, normalize) if normalize else band_data
        point_data = band_data.stack(samples=band_data.dims).dropna(dim="samples")
        return dict( raster = band_data, points = point_data[::subsampling] )

    def getTilePointData( self, subsampling: int = 1, normalize = 1.0 ) -> Dict[str,xa.DataArray]:
        raster = self.dm.normalize( self.data, normalize ) if normalize else self.data
        point_data = self.getPointData( raster )
        return dict( raster = raster, points = point_data[::subsampling] )

    def getBlockPointData( self, iy: int, ix: int, normalize = 1.0 ) -> Dict[str,xa.DataArray]:
        raster = self.dm.normalize(  self.getBlock(iy,ix), normalize ) if normalize else  self.getBlock(iy,ix)
        return dict( raster = raster, points = self.getPointData( raster ) )

    def plotBlock(self, iy, ix, **kwargs ):
        block_data = self.dm.normalize(  self.getBlock( iy, ix ) )
        color_band = kwargs.pop( 'color_band', None )
        band_range = kwargs.pop('band_range', None)
        if color_band is not None:
            plot_data = block_data[color_band]
        elif band_range is not None:
            plot_data = block_data.isel( band=slice( band_range[0], band_range[1] ) ).mean(dim="band", skipna=True)
        else:
            plot_data =  self.dm.getRGB(block_data)
        self.dm.plotRaster( plot_data, **kwargs )
        return block_data

class DataManager:

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

    def getTileData(self, iy: int, ix: int ):
        tile_data: Optional[xa.DataArray] = self.readTileFile( iy, ix )
        if tile_data is None: tile_data = self.getTileDataFromImage( iy, ix )
        return tile_data

    def getTileDataFromImage(self, iy: int, ix: int ) -> xa.DataArray:
        full_input_bands: xa.DataArray = self.readGeotiff(self.image_name)
        ybounds, xbounds = self.getTileBounds( iy, ix )
        tile_raster = full_input_bands[:, ybounds[0]:ybounds[1], xbounds[0]:xbounds[1] ]
        tile_filename = self.tileFileName(iy, ix)
        output_filepath = self.writeGeotiff(tile_raster, tile_filename)
        tile_raster.attrs['file_path'] = output_filepath
        tile_raster.attrs['tile_coords'] =(iy,ix)
        return tile_raster

    @classmethod
    def getRGB(cls, raster_data: xa.DataArray ) -> xa.DataArray:
        b = raster_data.isel( band=slice( 13, 27 ) ).mean(dim="band", skipna=True)
        g = raster_data.isel( band=slice( 29, 44 ) ).mean(dim="band", skipna=True)
        r = raster_data.isel( band=slice( 51, 63 ) ).mean(dim="band", skipna=True)
        rgb: xa.DataArray = xa.concat( [r,g,b], 'band' )
        return cls.rescale( rgb, (0,1) ).transpose('y','x','band')


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
            input_bands: xa.DataArray = rio.open_rasterio(input_file)
            return input_bands if iband < 0 else input_bands[iband]
        else:
            return None

    def readTileFile( self, iy: int, ix: int, iband = -1 ) -> Optional[xa.DataArray]:
        tile_filename =self.tileFileName(iy, ix)
        print(f"Reading tile file {tile_filename}")
        tile_raster: Optional[xa.DataArray] = self.readGeotiff(tile_filename, iband)
        if tile_raster is not None:
            nodata_value = tile_raster.attrs.get('data_ignore_value', -9999)
            tile_raster: xa.DataArray = tile_raster.where(tile_raster != nodata_value, float('nan'))
            tile_raster.name = f"{self.image_name}: Band {iband+1}" if( iband >= 0 ) else self.image_name
        return tile_raster

    def tileFileName(self, iy: int, ix: int) -> str:
        return f"{self.image_name}.{self.tile_shape[0]}-{self.tile_shape[1]}_{iy}-{ix}"

    @classmethod
    def rescale(cls, raster: xa.DataArray, rescale: Tuple[float,float] ) -> xa.DataArray:
        vmin = raster.min( dim=raster.dims[:2], skipna=True )
        vmax = raster.max(dim=raster.dims[:2], skipna=True )
        scale = (rescale[1]-rescale[0])/(vmax-vmin)
        return  (raster - vmin)*scale + rescale[0]

    @classmethod
    def normalize(cls, raster: xa.DataArray, scale = 1.0, center = True ):
        std = raster.std(dim=raster.dims[-2:], skipna=True)
        if center:
            meanval = raster.mean(dim=raster.dims[-2:], skipna=True)
            centered= raster - meanval
        else:
            centered = raster
        result =  centered * scale / std
        result.attrs = raster.attrs
        return result

    @classmethod
    def plotRaster(cls, raster: xa.DataArray, **kwargs ):
        from matplotlib.colorbar import Colorbar
        ax = kwargs.pop( 'ax', None )
        showplot = ( ax is None )
        if showplot: fig, ax = plt.subplots(1,1)
        colors = kwargs.pop('colors', None )
        title = kwargs.pop( 'title', raster.name )
        rescale = kwargs.pop( 'rescale', None )
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
            defaults.update( dict( vmin=-1, vmax=1, cmap="jet" ) )
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
        defaults.update(kwargs)
        if defaults['origin'] == 'upper':   defaults['extent'] = [left, right, bottom, top]
        else:                               defaults['extent'] = [left, right, top, bottom]
        if rescale is not None:
            raster = cls.rescale( raster, rescale )
        img = ax.imshow( raster.data, **defaults )
        ax.set_title(title)
        if raster.ndim == 2:
            cbar: Colorbar = ax.figure.colorbar(img, ax=ax, **cbar_kwargs )
            if colors is not None:
                cbar.set_ticklabels( [ cval[1] for cval in colors ] )
        if showplot: plt.show()
        return img
