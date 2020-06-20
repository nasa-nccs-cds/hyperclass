from hyperclass.data.swift.config import PrepareInputsDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
import sys
from hyperclass.data.swift.manager import dataManager
import xarray as xa
import numpy as np
import pickle, os

def prepare_inputs():
    data_vars = dict( )

    obsids = dataManager.getInputFileData( "obsids" )
    target_names = dataManager.getInputFileData( "target_names" )
    samples = np.arange( len(obsids) )

    data_vars['obsids'] = xa.DataArray( obsids, dims=['samples'], coords=dict( samples=samples) )
    data_vars['targets'] = xa.DataArray( target_names, dims=['samples'], coords=dict( samples=samples) )

    bands_data = dataManager.getInputFileData( "spectra_x_axis" )
    bands = np.array( bands_data, dtype=np.single )

    spectra_data = dataManager.getInputFileData( "specs" )
    spectra = np.array( spectra_data, dtype=np.single )
    data_vars['spectra'] = xa.DataArray( spectra, dims=['samples','bands'], coords=dict( samples=samples, bands=bands ) )

    scaled_spectra_data = dataManager.getInputFileData( "scaled_specs" )
    scaled_spectra = np.array( scaled_spectra_data, dtype=np.single )
    data_vars['scaled_spectra'] = xa.DataArray( scaled_spectra, dims=['samples','bands'], coords=dict( samples=samples, bands=bands ) )

    dataset = xa.Dataset( data_vars, coords=dict( samples=samples, bands=bands ) )
    dsid = dataManager.config.value('dataset/id', PrepareInputsDialog.DSID )
    output_file = os.path.join( dataManager.config.value('data/cache'), dsid + ".nc" )
    print( f"Writing output to {output_file}")
    dataset.to_netcdf( output_file )

input_file_ids = [ "obsids", "specs", "scaled_specs", "target_names", 'spectra_x_axis' ]
app = QApplication(sys.argv)
preferences = PrepareInputsDialog(input_file_ids, prepare_inputs, QSettings.SystemScope)
preferences.show()
sys.exit(app.exec_())