from hyperclass.data.manager import dataManager
import xarray as xa
import numpy as np
import os, glob
from collections import OrderedDict
from typing import List, Union, Tuple, Optional, Dict
from PyQt5.QtWidgets import *
from functools import partial
from PyQt5.QtCore import  QSettings
from typing import Optional, Dict

from hyperclass.gui.config import PreferencesDialog
from hyperclass.gui.dialog import DialogBase
from hyperclass.reduction.manager import reductionManager

def getXarray(  id: str, xcoords: Dict, subsample: int, xdims:OrderedDict, **kwargs ) -> xa.DataArray:
    np_data: np.ndarray = dataManager.getInputFileData( id, subsample, tuple(xdims.keys()) )
    dims, coords = [], {}
    for iS in np_data.shape:
        coord_name = xdims[iS]
        dims.append( coord_name )
        coords[ coord_name ] = xcoords[ coord_name ]
    attrs = { **kwargs, 'name': id }
    return xa.DataArray( np_data, dims=dims, coords=coords, name=id, attrs=attrs )

def prepare_inputs( input_vars, ssample = None ):
    subsample = int(dataManager.config.value("input.reduction/subsample", 1 ) ) if ssample is None else ssample
#    values = { k: dataManager.config.value(k) for k in dataManager.config.allKeys() }
    np_embedding = dataManager.getInputFileData( input_vars['embedding'], subsample )
    dims = np_embedding.shape
    mdata_vars = list(input_vars['directory'])
    xcoords = OrderedDict( samples = np.arange( dims[0] ), bands = np.arange(dims[1]) )
    xdims = OrderedDict( { dims[0]: 'samples', dims[1]: 'bands' } )
    data_vars = dict( embedding = xa.DataArray( np_embedding, dims=xcoords.keys(), coords=xcoords, name=input_vars['embedding'] ) )
    data_vars.update( { vid: getXarray( vid, xcoords, subsample, xdims ) for vid in mdata_vars } )
    pspec = input_vars['plot']
    data_vars.update( { f'plot-{vid}': getXarray( pspec[vid], xcoords, subsample, xdims, norm=pspec.get('norm','')) for vid in [ 'x', 'y' ] } )
    reduction_method = dataManager.config.value("input.reduction/method",  'None')
    ndim = int(dataManager.config.value("input.reduction/ndim", '32 '))
    if reduction_method != "None":
       reduced_spectra = reductionManager.reduce( data_vars['embedding'], reduction_method, ndim )
       coords = dict( samples=xcoords['samples'], model=np.arange(ndim) )
       data_vars['reduction'] =  xa.DataArray( reduced_spectra, dims=['samples','model'], coords=coords )

    dataset = xa.Dataset( data_vars, coords=xcoords, attrs = {'type':'spectra'} )
    dataset.attrs["colnames"] = mdata_vars
    projId = dataManager.config.value('project/id')
    file_name = f"raw" if reduction_method == "None" else f"{reduction_method}-{ndim}"
    if subsample > 1: file_name = f"{file_name}-ss{subsample}"
    output_file = os.path.join( dataManager.config.value('data/cache'), projId, file_name + ".nc" )
    print( f"Writing output to {output_file}")
    dataset.to_netcdf( output_file, format='NETCDF4', engine='netcdf4' )


class ConfigurationDialog(PreferencesDialog):

    def __init__( self, callback = None, scope: QSettings.Scope = QSettings.SystemScope  ):
        super(ConfigurationDialog, self).__init__( DialogBase.CONFIG, callback, scope, spatial=False )

class PrepareInputsDialog(PreferencesDialog):

    def __init__( self, input_vars: Optional[Dict] = None, subsample: int = None, scope: QSettings.Scope = QSettings.UserScope  ):
        self.inputs = {} if input_vars is None else [ input_vars['embedding'] ] +  input_vars['directory'] + [ input_vars['plot'][axis] for axis in ['x','y'] ]
        super(PrepareInputsDialog, self).__init__( DialogBase.DATA_PREP, partial( prepare_inputs, input_vars, subsample ), scope, spatial=False )

    def addFileContent( self, inputsLayout: QBoxLayout ):
        for input_file_id in self.inputs:
            inputsLayout.addLayout( self.createFileSystemSelectionWidget( input_file_id, self.FILE, f"data/init/{input_file_id}", "data/dir" ) )

    def getProjectList(self) -> Optional[List[str]]:
        system_settings = dataManager.getSettings( QSettings.SystemScope )
        settings_file = system_settings.fileName()
        settings_path = os.path.dirname( os.path.realpath( settings_file ) )
        inifiles = glob.glob(f"{settings_path}/*.ini")
        sorted_inifiles = sorted( inifiles, key=lambda t: os.stat(t).st_mtime )
        return [ os.path.splitext( os.path.basename( f ) )[0] for f in sorted_inifiles ]

class RuntimeDialog(PreferencesDialog):

    def __init__( self, callback = None, scope: QSettings.Scope = QSettings.UserScope  ):
        super(RuntimeDialog, self).__init__( DialogBase.RUNTIME, callback, scope, spatial=False )


