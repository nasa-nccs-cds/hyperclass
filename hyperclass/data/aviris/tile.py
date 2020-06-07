from skimage.transform import ProjectiveTransform
import numpy as np
import xarray as xa
from typing import List, Union, Tuple, Optional, Dict
from pyproj import Proj, transform
from .manager import dataManager
from hyperclass.gui.tasks import taskRunner, Task
import os, math, pickle
from hyperclass.graph.flow import ActivationFlow

class Tile:

    def __init__(self, **kwargs ):
        self.config = kwargs
        self._data: xa.DataArray = None
        self._transform: ProjectiveTransform = None
        self.subsampling: int =  kwargs.get('subsample',1)

    @property
    def data(self) -> xa.DataArray:
        if self._data is None:
            self._data: xa.DataArray = dataManager.getTileData(  **self.config )
        return self._data

    def iparm(self, key: str ):
        return int( dataManager.config.value(key) )

    @property
    def name(self) -> str:
        return dataManager.tileFileName()

    @property
    def transform(self) -> Optional[ProjectiveTransform]:
        if self.data is None: return None
        if self._transform is None:
            self._transform = ProjectiveTransform( np.array(list(self.data.transform) + [0, 0, 1]).reshape(3, 3) )
        return self._transform

    def get_block_transform( self, iy, ix ) -> ProjectiveTransform:
        tr0 = self.data.transform
        iy0, ix0 = iy*dataManager.block_shape[0], ix*dataManager.block_shape[1]
        y0, x0 = tr0[5] + iy0 * tr0[4], tr0[2] + ix0 * tr0[0]
        tr1 = [ tr0[0], tr0[1], x0, tr0[3], tr0[4], y0, 0, 0, 1  ]
        return  ProjectiveTransform( np.array(tr1).reshape(3, 3) )

    @property
    def filename(self) -> str:
        return self.data.attrs['filename']

    @property
    def nBlocks(self) -> List[ List[int] ]:
        return [ self.data.shape[i+1]//dataManager.block_shape[i] for i in range(2) ]

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
        point_data = dataManager.raster2points( self.data )
        return point_data[::subsample]

    def coords2index(self, cy, cx ) -> Tuple[int,int]:     # -> iy, ix
        coords = self.transform.inverse(np.array([[cx, cy], ]))
        return (math.floor(coords[0, 1]), math.floor(coords[0, 0]))

    def index2coords(self, iy, ix ) -> Tuple[float,float]:
        return self.transform(np.array([[ix+0.5, iy+0.5], ]))

class Block:

    def __init__(self, tile: Tile, iy: int, ix: int, **kwargs ):
        self.tile: Tile = tile
        self.init_task = None
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

    def flow_init( self, **kwargs ):
        if self._flow is None:
            n_neighbors = self.config.pop( 'n_neighbors', self.iparm('umap/nneighbors') )
            print( f"Computing NN graph using {n_neighbors} neighbors")
            self._flow = ActivationFlow( self.getPointData(), n_neighbors=n_neighbors,  **self.config )

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
        stacked_data: xa.DataArray = self.data.stack( samples=self.data.dims[-2:] )
        filtered_samples = stacked_data[1].dropna( dim="samples" )
        indices = np.arange(filtered_samples.shape[0])
        point_indices = xa.DataArray( indices, dims=['samples'], coords=dict(samples=filtered_samples.samples) )
        result = point_indices.reindex( samples=stacked_data.samples, fill_value= -1 )
        return result.unstack()

    def iparm(self, key: str ):
        return int( dataManager.config.value(key) )

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
        return dataManager.block_shape

    def getBounds(self ) -> Tuple[ Tuple[int,int], Tuple[int,int] ]:
        y0, x0 = self.block_coords[0]*self.shape[0], self.block_coords[1]*self.shape[1]
        return ( y0, y0+self.shape[0] ), ( x0, x0+self.shape[1] )

    def getPointData( self, **kwargs ) -> xa.DataArray:
        if self._point_data is None:
            subsample = kwargs.get( 'subsample', None )
            result: xa.DataArray =  dataManager.raster2points( self.data )
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
            plot_data =  dataManager.getRGB(self.data)
        dataManager.plotRaster( plot_data, **kwargs )
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