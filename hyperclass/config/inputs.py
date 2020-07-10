from hyperclass.data.swift.manager import dataManager
import xarray as xa
import numpy as np
import pickle, os
from PyQt5.QtWidgets import *
from functools import partial
from PyQt5.QtCore import  QSettings
from typing import List, Union, Tuple, Optional, Dict
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
    dsid = dataManager.config.value('dataset/id', PrepareInputsDialog.DSID )
    file_name = f"{dsid}.nc" if reduction_method == "None" else f"{dsid}.{reduction_method}-{ndim}.nc"
    output_file = os.path.join( dataManager.config.value('data/cache'), file_name )
    print( f"Writing output to {output_file}")
    dataset.to_netcdf( output_file, format='NETCDF4', engine='netcdf4' )


class PrepareInputsDialog(DialogBase):

    DSID = "swift_spectra"

    def __init__( self, input_vars: Dict, subsample: int = 1, scope: QSettings.Scope = QSettings.UserScope ):
        self.inputs =  [ input_vars['embedding'] ] +  input_vars['directory'] + [ input_vars['plot'][axis] for axis in ['x','y'] ]
        super(PrepareInputsDialog, self).__init__( partial( prepare_inputs, input_vars, subsample ), scope )

    def addContent(self):
        self.mainLayout.addLayout( self.createSettingInputField( "Dataset ID", "dataset/id", self.DSID ) )
        inputsGroupBox = QGroupBox('inputs')
        inputsLayout = QVBoxLayout()
        inputsGroupBox.setLayout( inputsLayout )

        inputsLayout.addLayout( self.createFileSystemSelectionWidget( "Data Directory",    self.DIRECTORY, "data/dir", "data/dir" ) )
        inputsLayout.addLayout( self.createFileSystemSelectionWidget("Cache Directory", self.DIRECTORY, "data/cache", "data/dir") )
        for input_file_id in self.inputs:
            inputsLayout.addLayout( self.createFileSystemSelectionWidget( input_file_id, self.FILE, f"data/init/{input_file_id}", "data/dir" ) )

        self.mainLayout.addWidget( inputsGroupBox )
        self.mainLayout.addWidget( reductionManager.gui(self) )

