from hyperclass.data.swift.config import PrepareInputsDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
from typing import List, Union, Dict, Callable, Tuple, Optional
import sys
from hyperclass.data.swift.manager import dataManager
import xarray as xa
import numpy as np
import pickle, os

from hyperclass.reduction.manager import reductionManager
input_vars = dict( embedding='scaled_lcs', directory = [ "camera", "chip", "dec", 'ra', 'tics', 'tmag' ], plot= dict( y="lcs", x='times', norm="median" ) )
subsample = 50

def getXarray(  id: str, coords: Dict, subsample, **kwargs ) -> xa.DataArray:
    np_data: np.ndarray = dataManager.getInputFileData( id, subsample )
    xdims = ['samples'] if np_data.ndim == 1 else [ 'samples', 'bands' ]
    xcoords = { 'samples':coords['samples'] }
    if np_data.ndim == 2: xcoords['bands'] = coords['bands']
    attrs = { **kwargs, 'name': id }
    return xa.DataArray( np_data, dims=xdims, coords=xcoords, name=id, attrs=attrs )

def prepare_inputs():
    np_embedding = dataManager.getInputFileData( input_vars['embedding'], subsample )
    xcoords = dict( samples = np.arange( np_embedding.shape[0] ), bands = np.arange(np_embedding.shape[1]) )
    xdims = list(xcoords.keys())
    data_vars = dict( embedding = xa.DataArray( np_embedding, dims=xdims, coords=xcoords, name=input_vars['embedding'] ) )
    data_vars.update( { f'dir-{idx}': getXarray( vid, xcoords, subsample ) for idx, vid in enumerate( input_vars['directory']) } )
    pspec = input_vars['plot']
    data_vars.update( { f'plot-{vid}': getXarray( pspec[vid], xcoords, subsample, norm=pspec.get('norm',None)) for vid in [ 'x', 'y' ] } )

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


app = QApplication(sys.argv)
input_file_ids = [ input_vars['embedding'] ] +  input_vars['directory'] + [ input_vars['plot'][axis] for axis in ['x','y'] ]
preferences = PrepareInputsDialog( input_file_ids, prepare_inputs, QSettings.SystemScope )
preferences.show()
sys.exit( app.exec_() )