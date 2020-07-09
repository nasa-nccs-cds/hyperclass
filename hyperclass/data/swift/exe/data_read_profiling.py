from hyperclass.data.swift.manager import dataManager
import xarray as xa
import numpy as np
import pickle, os, time

t1 = time.time()
spectral_file = "/usr/local/web/ILAB/data/results/swift/swift_spectra.nc"
spectral_dataset: xa.Dataset = xa.open_dataset( spectral_file )
spectra1 = spectral_dataset[ "spectra" ]
m0 = spectra1.mean().data
print( f"Computed spectral mean ({m0}) from netcdf data in {time.time()-t1} secs.")

t0 = time.time()
spectra_data = dataManager.getInputFileData( "specs" )
spectra0 = np.array( spectra_data, dtype=np.single )
m0 = spectra0.mean()
print( f"Computed spectral mean ({m0}) from pickled data in {time.time()-t0} secs.")


