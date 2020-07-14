from hyperclass.data.manager import dataManager
import xarray as xa
import numpy as np
import os, glob
from typing import List, Union, Tuple, Optional, Dict
from PyQt5.QtWidgets import *
from functools import partial
from PyQt5.QtCore import  QSettings
from typing import Optional, Dict
from hyperclass.gui.dialog import DialogBase
from hyperclass.reduction.manager import reductionManager

def getXarray(  id: str, coords: Dict, subsample, **kwargs ) -> xa.DataArray:
    np_data: np.ndarray = dataManager.getInputFileData( id, subsample )
    xdims = ['samples'] if np_data.ndim == 1 else [ 'samples', 'bands' ]
    xcoords = { 'samples':coords['samples'] }
    if np_data.ndim == 2: xcoords['bands'] = coords['bands']
    attrs = { **kwargs, 'name': id }
    return xa.DataArray( np_data, dims=xdims, coords=xcoords, name=id, attrs=attrs )

def prepare_inputs( input_vars, subsample ):
    values = { k: dataManager.config.value(k) for k in dataManager.config.allKeys() }
    np_embedding = dataManager.getInputFileData( input_vars['embedding'], subsample )
    xcoords = dict( samples = np.arange( np_embedding.shape[0] ), bands = np.arange(np_embedding.shape[1]) )
    xdims = list(xcoords.keys())
    data_vars = dict( embedding = xa.DataArray( np_embedding, dims=xdims, coords=xcoords, name=input_vars['embedding'] ) )
    data_vars.update( { f'dir-{idx}': getXarray( vid, xcoords, subsample ) for idx, vid in enumerate( input_vars['directory']) } )
    pspec = input_vars['plot']
    data_vars.update( { f'plot-{vid}': getXarray( pspec[vid], xcoords, subsample, norm=pspec.get('norm','')) for vid in [ 'x', 'y' ] } )
    reduction_method = dataManager.config.value("input.reduction/method",  'None')
    ndim = int(dataManager.config.value("input.reduction/ndim", '32 '))
    if reduction_method != "None":
       reduced_spectra = reductionManager.reduce( data_vars['embedding'], reduction_method, ndim )
       coords = dict( samples=xcoords['samples'], model=np.arange(ndim) )
       data_vars['reduction'] =  xa.DataArray( reduced_spectra, dims=['samples','model'], coords=coords )

    dataset = xa.Dataset( data_vars, coords=xcoords, attrs = {'type':'spectra'} )
    projId = dataManager.config.value('project/id')
    file_name = f"{projId}.nc" if reduction_method == "None" else f"{projId}.{reduction_method}-{ndim}.nc"
    output_file = os.path.join( dataManager.config.value('data/cache'), file_name )
    print( f"Writing output to {output_file}")
    dataset.to_netcdf( output_file, format='NETCDF4', engine='netcdf4' )


class ConfigurationDialog(DialogBase):

    def __init__( self, proj_name: str, callback = None, scope: QSettings.Scope = QSettings.SystemScope  ):
        dataManager.setProjectName( proj_name )
        super(ConfigurationDialog, self).__init__( proj_name, callback, scope )

class PrepareInputsDialog(ConfigurationDialog):

    def __init__( self, app_name: Optional[str], input_vars: Optional[Dict] = None, subsample: int = 1, scope: QSettings.Scope = QSettings.UserScope  ):
        self.inputs = {} if input_vars is None else [ input_vars['embedding'] ] +  input_vars['directory'] + [ input_vars['plot'][axis] for axis in ['x','y'] ]
        super(PrepareInputsDialog, self).__init__( app_name, partial( prepare_inputs, input_vars, subsample ), scope )

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


