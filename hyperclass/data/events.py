from typing import List, Union, Dict, Callable, Tuple, Optional
from hyperclass.data.aviris.tile import Tile, Block
import xarray as xa

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

    def getPointData(self, event: Dict, **kwargs ) -> xa.DataArray:
        scaled: bool = kwargs.get( 'scaled', False )
        self.getLoadedData(event)
        if isinstance(self._loaded_data, Block):
            return self._loaded_data.getPointData( subsample = self._subsample )
        elif isinstance(self._loaded_data, xa.Dataset):
            dset_type = self._loaded_data.attrs['type']
            if dset_type == 'spectra':
                varid = 'scaled_spectra' if scaled else 'spectra'
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