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

    def getLoadedData(self, event: Dict, subsample=None  ) -> Optional[ Union[xa.DataArray,xa.Dataset,Block] ]:
        if (self._loaded_data is None) and self.isDataLoadEvent(event) :
            self._loaded_data = event.get('result')
        return self._loaded_data


dataEventHandler = DataEventHandler()