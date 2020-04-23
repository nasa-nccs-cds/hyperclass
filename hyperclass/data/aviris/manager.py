from hyperclass.util.config import Configuration
import xarray as xa
from typing import List, Union, Tuple, Optional
import matplotlib.pyplot as plt
import os, math
import rioxarray as rio

class DataManager:

    def __init__(self, **kwargs ):
        self.config = Configuration( **kwargs )

    def create_subtile(self, input_filename: str, c0: Tuple, c1: Tuple ) -> xa.DataArray:
        full_input_bands: xa.DataArray = self.read_input_raster(input_filename)
        subset_bands = full_input_bands[:, c0[1]:c1[1], c0[0]:c1[0]]
        output_filename = f"{input_filename}.{c0[0]}-{c0[1]}_{c1[0]}-{c1[1]}.tif"
        self.write_output_raster( subset_bands, output_filename )
        subset_bands.attrs['file_path'] = output_filename
        return subset_bands

    def write_output_raster( self, raster_data: xa.DataArray, filename: str ):
        if not filename.endswith(".tif"): filename = filename + ".tif"
        output_file = os.path.join(self.config['data_dir'], filename )
        print(f"Writing raster file {output_file}")
        raster_data.rio.to_raster(output_file)

    def read_input_raster( self, filename: str, iband = -1 ) -> xa.DataArray:
        if not filename.endswith(".tif"): filename = filename + ".tif"
        input_file = os.path.join( self.config['data_dir'], filename )
        print( f"Reading raster file {input_file}")
        input_bands: xa.DataArray = rio.open_rasterio(input_file)
        return input_bands if iband < 0 else input_bands[iband]

    def read_subtile( self, base_filename: str, c0: Tuple, c1: Tuple, iband = -1 ) -> xa.DataArray:
        subtile_filename =self.subtile_file( base_filename, c0, c1 )
        result = self.read_input_raster( subtile_filename, iband )
        result.name = f"{base_filename}: Band {iband+1}" if( iband >= 0 ) else base_filename
        return result

    def subtile_file( self, base_filename: str, c0: Tuple, c1: Tuple  ) -> str:
        if base_filename.endswith(".tif"): base_filename = base_filename[:-4]
        return f"{base_filename}.{c0[0]}-{c0[1]}_{c1[0]}-{c1[1]}"

    def plot_raster(self, raster: xa.DataArray, vrange, **kwargs ):
        fig, ax = plt.subplots(1,1)
        title = kwargs.get( 'title', raster.name )
        x = raster.coords[ raster.dims[1] ]
        y = raster.coords[ raster.dims[0] ]
        try:
            xstep = (x[1] - x[0]) / 2.0
        except IndexError: xstep = .1
        try:
            ystep = (y[1] - y[0]) / 2.0
        except IndexError: ystep = .1
        left, right = x[0] - xstep, x[-1] + xstep
        bottom, top = y[-1] + ystep, y[0] - ystep
        defaults = {'origin': 'upper', 'interpolation': 'nearest'}
        if not hasattr(ax, 'projection'): defaults['aspect'] = 'auto'
        defaults.update(kwargs)
        if defaults['origin'] == 'upper':   defaults['extent'] = [left, right, bottom, top]
        else:                               defaults['extent'] = [left, right, top, bottom]

        img = ax.imshow( raster.data, vmin=vrange[0], vmax=vrange[1], cmap="jet", **defaults )
        ax.set_title(title)
        fig.colorbar(img, ax=ax)
        plt.show()
