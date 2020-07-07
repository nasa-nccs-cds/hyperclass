from typing import List, Union, Dict, Callable, Tuple, Optional
from hyperclass.data.aviris.tile import Tile, Block
from enum import Enum
import xarray as xa

class DataType(Enum):
    Scaled = 1
    Reduced = 2
    Raw = 3

class DataEventHandler:

    def __init__(self):
        self._loaded_data = None
        self._subsample = None

    def reset( self, event: Dict ):
        if self.isDataLoadEvent( event ):
            self._loaded_data = None

    def subsample(self, samples: xa.DataArray) -> xa.DataArray:
        if self.subsample is None: return samples
        return samples[::self._subsample]

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
        if (self._loaded_data is None) and self.isDataLoadEvent(event) :
            self._loaded_data = event.get('result')

    def getPointData(self, event: Dict, type: DataType = DataType.Reduced, **kwargs ) -> xa.DataArray:
        self.getLoadedData(event)
        if isinstance(self._loaded_data, Block):
            return self._loaded_data.getPointData( subsample = self._subsample )
        elif isinstance(self._loaded_data, xa.Dataset):
            dset_type = self._loaded_data.attrs['type']
            if dset_type == 'spectra':
                if type == DataType.Reduced:
                    if 'reduced_spectra' in self._loaded_data:
                        varid = 'reduced_spectra'
                    else: varid = 'scaled_spectra'
                elif type == DataType.Scaled:
                    varid = 'scaled_spectra'
                elif type == DataType.Raw:
                    varid = 'spectra'
                else: raise Exception( f"Unrecognized DataType: {type}")
                point_data: xa.DataArray = dataEventHandler.subsample( self._loaded_data[varid] )
                point_data.attrs['dsid'] = self._loaded_data.attrs['dsid']
                point_data.attrs['type'] = dset_type
                return point_data

    def getMetadata(self, event: Dict = {} ) -> Dict[str,xa.DataArray]:
        self.getLoadedData( event )
        dset_type = self._loaded_data.attrs.get('type')
        if dset_type == 'spectra':
            return { key: dataEventHandler.subsample(  self._loaded_data.variables[key] ) for key in [ 'obsids', 'targets'] }
        else: return {}


dataEventHandler = DataEventHandler()