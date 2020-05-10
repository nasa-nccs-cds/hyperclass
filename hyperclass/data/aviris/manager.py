from hyperclass.util.config import Configuration
from skimage.transform import ProjectiveTransform
import numpy as np
import xarray as xa
import matplotlib as mpl
from typing import List, Union, Tuple, Optional, Dict
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
import matplotlib.pyplot as plt
from typing import TextIO
import csv
import os, math, pickle
import rioxarray as rio

def get_color_bounds( color_values: List[float] ) -> List[float]:
    color_bounds = []
    for iC, cval in enumerate( color_values ):
        if iC == 0: color_bounds.append( cval - 0.5 )
        else: color_bounds.append( (cval + color_values[iC-1])/2.0 )
    color_bounds.append( color_values[-1] + 0.5 )
    return color_bounds

class TrainingDataIO:

    def __init__(self, file_path: str,  **kwargs ):
        self.file_path = file_path
        self.names = None
        self.colors = None
        self.values = None

    def writeLabelData(self, names, colors, values ):
        with open( self.file_path, 'wb' ) as f:
            print( f"Saving {len(values)} labeled points to file {self.file_path}")
            pickle.dump( [ names, colors, values ], f )

    def readLabelData(self):
        if os.path.isfile(self.file_path):
            print(f"Reading Label data from file {self.file_path}")
            with open(self.file_path, 'rb') as f:
                label_data = pickle.load( f )
                if label_data:
                    self.names = label_data[0]
                    self.colors = label_data[1]
                    self.values = label_data[2]

class Tile:

    def __init__(self, data_manager: "DataManager", **kwargs ):
        self.config = kwargs
        self.dm = data_manager
        self._data: xa.DataArray = None
        self._transform: ProjectiveTransform = None
        self.subsampling = self.iparm('sub_sampling')

    @property
    def data(self) -> xa.DataArray:
        if self._data is None:
            self._data: xa.DataArray = self.dm.getTileData(  **self.config )
        return self._data

    def iparm(self, key: str ):
        return int( self.dm.config[key] )

    @property
    def name(self) -> str:
        return self.dm.tileFileName()

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
        self.transform = ProjectiveTransform( np.array( list(self.data.transform) + [0,0,1] ).reshape(3,3) )

    def _getData( self ) -> xa.DataArray:
        ybounds, xbounds = self.getBounds()
        block_raster = self.tile.data[:, ybounds[0]:ybounds[1], xbounds[0]:xbounds[1] ]
        block_raster.attrs['block_coords'] = self.block_coords
        block_raster.name = f"{self.tile.name}_b-{self.block_coords[0]}-{self.block_coords[1]}"
        return block_raster

    @property
    def shape(self) -> Tuple[int,int]:
        return self.tile.dm.block_shape

    def getBounds(self ) -> Tuple[ Tuple[int,int], Tuple[int,int] ]:
        y0, x0 = self.block_coords[0]*self.shape[0], self.block_coords[1]*self.shape[1]
        return ( y0, y0+self.shape[0] ), ( x0, x0+self.shape[1] )

    def getPointData( self, **kwargs ) -> xa.DataArray:
        subsample = kwargs.get( 'subsample', None )
        result: xa.DataArray =  self.tile.dm.raster2points( self.data )
        return result if subsample is None else result[::subsample]

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
        self.tile_index = self.config.getShape('tile_index')
        [self.iy, self.ix] = self.tile_index
        self.block_shape = self.config.getShape( 'block_shape' )
        self.tdio = TrainingDataIO( os.path.join( self.config['data_dir'], self.trainingDataFileName() + ".pkl" ) )
        self.tile = None

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

    def getTileData(self, **kwargs ):
        tile_data: Optional[xa.DataArray] = self._readTileFile()
        if tile_data is None: tile_data = self._getTileDataFromImage()
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

    def _getTileDataFromImage(self) -> xa.DataArray:
        full_input_bands: xa.DataArray = self.readGeotiff( self.image_name )
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
        output_file = os.path.join(self.config['data_dir'], filename )
        print(f"Writing raster file {output_file}")
        raster_data.rio.to_raster(output_file)
        return output_file

    def readGeotiff( self, filename: str, iband = -1 ) -> Optional[xa.DataArray]:
        if not filename.endswith(".tif"): filename = filename + ".tif"
        input_file = os.path.join( self.config['data_dir'], filename )
        try:
            input_bands: xa.DataArray =  rio.open_rasterio(input_file)
            print(f"Reading raster file {input_file}")
            if iband >= 0:  return input_bands[iband]
            else:           return input_bands
        except Exception as err:
            print( f"WARNING: can't read input file {input_file}: {err}")
            return None

    @classmethod
    def mask_nodata(self, raster: xa.DataArray ) -> xa.DataArray:
        nodata_value = raster.attrs.get( 'data_ignore_value', -9999 )
        return raster.where(raster != nodata_value, float('nan'))

    def tileFileName(self) -> str:
        return f"{self.image_name}.{self.config.getCfg('tile_shape')}_{self.config.getCfg('tile_index')}"

    def trainingDataFileName(self) -> str:
        return f"tdata_{self.image_name}.{self.config.getCfg('tile_shape')}_{self.config.getCfg('tile_index')}"

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
        stacked_raster = raster.stack(samples=['x','y']).transpose()
        point_data = stacked_raster.dropna(dim='samples', how='any')
        print(f"  -> [{raster.name}]: Using {point_data.shape[0]} valid samples out of {stacked_raster.shape[0]} pixels")
        return point_data

    @classmethod
    def plot_pointclouds(cls, datasets: List ):
        import plotly.graph_objs as go
        plot_data = []
        for ip, dataset in enumerate( datasets ):
            points = dataset.pop( "data" )
            name = dataset.pop( "name" )
            plot_data.append( go.Scatter3d( x=points[:, 0], y=points[:, 1], z=points[:, 2], name=name, mode='markers', marker=dataset ) )
        fig = go.Figure( data=plot_data )
        fig.show()

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
        img = ax.imshow( raster.data, zorder=1, **defaults )
        ax.set_title(title)
        if colorbar and (raster.ndim == 2):
            cbar: Colorbar = ax.figure.colorbar(img, ax=ax, **cbar_kwargs )
            if colors is not None:
                cbar.set_ticklabels( [ cval[1] for cval in colors ] )
        if showplot: plt.show()
        return img
