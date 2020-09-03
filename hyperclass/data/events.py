from typing import List, Union, Dict, Callable, Tuple, Optional
from hyperclass.data.spatial.tile import Tile, Block
from enum import Enum
import xarray as xa

class DataType(Enum):
    Embedding = 1
    Plot = 2
    Image = 3
    Directory = 4

class DataEventHandler:

    def __init__(self):
        self._loaded_data: Optional[xa.Dataset] = None
        self._subsample: int = None

    def reset( self, event: Dict ):
        if self.isDataLoadEvent( event ):
            self._loaded_data = None

    def varid(self, data_type: DataType ) -> List[str]:
        if data_type == DataType.Embedding: return [ "reduction", "embedding" ]
        elif data_type == DataType.Plot: return [ "plot-x", "plot-y" ]

    def subsample(self, samples: xa.DataArray) -> xa.DataArray:
        if self._subsample is None: return samples
        rv = samples[::self._subsample]
        rv.load()
        return rv

    def config(self, **kwargs ):
        self._subsample = kwargs.pop('subsample', None)

    def isDataLoadEvent(self, event: Dict ) -> bool:
        if event.get('event') == 'task':
            label: str = event.get('label', '')
            if label.lower().startswith('load dataset'):
                if event.get('type') == 'result':
                    return True
        return False

    @property
    def data(self):
        return self._loaded_data

    def getLoadedData(self, event: Dict  ):
        if (event is not None) and (self._loaded_data is None) and self.isDataLoadEvent(event) :
            self._loaded_data = event.get('result')

    def getDataArray(self, varname: str ) -> Optional[xa.DataArray]:
        return self._loaded_data.data_vars.get( varname, None )

    def getPointData(self, event: Dict, type: DataType = DataType.Embedding, **kwargs ) -> Union[Dict[str,Optional[xa.DataArray]],Optional[xa.DataArray]]:
        self.getLoadedData(event)
        if isinstance(self._loaded_data, Block):
            return self._loaded_data.getPointData( subsample = self._subsample )
        elif isinstance(self._loaded_data, xa.Dataset):
            dset_type = self._loaded_data.attrs['type']
            if dset_type == 'spectra':
                point_data: Union[Dict[str,Optional[xa.DataArray]],Optional[xa.DataArray]] = None
                if type == DataType.Embedding:
                    raw_data = self.getDataArray( "reduction" )
                    if raw_data is None: raw_data = self.getDataArray( "embedding" )
                    point_data: Optional[xa.DataArray] = dataEventHandler.subsample( raw_data )
                    pdm =  point_data.mean( axis=0 )
                    point_data = point_data - pdm
                    point_data = point_data / point_data.std()
                    point_data.attrs['dsid'] = self._loaded_data.attrs['dsid']
                    point_data.attrs['type'] = dset_type
                elif type == DataType.Plot:
                    point_data: Dict[str,Optional[xa.DataArray]] = { 'plotx': self.getDataArray("plot-x"), 'ploty': self.getDataArray("plot-y") }
                    for pdata in point_data.values():
                        pdata.attrs['dsid'] = self._loaded_data.attrs['dsid']
                        pdata.attrs['type'] = dset_type
                return point_data

    def getMetadata(self, event: Dict = None ) -> List[xa.DataArray]:
        self.getLoadedData( event )
        dset_type = self._loaded_data.attrs.get('type')
        mdata: List[xa.DataArray] = []
        if dset_type == 'spectra':
            colnames = self._loaded_data.attrs['colnames']
            for colname in colnames:
                mdata.append( dataEventHandler.subsample(  self._loaded_data[colname] ) )
        return mdata


dataEventHandler = DataEventHandler()