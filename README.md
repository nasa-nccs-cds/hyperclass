# hyperclass
Methods for hyperspectral image classification developed by the NASA Goddard Innovation Lab


### Installation

##### Build Conda Env
```
>> conda create --name hyperclass
>> conda activate hyperclass
(geoproc)>> conda install -c conda-forge xarray dask distributed matplotlib datashader plotly colorcet holoviews numpy geopandas descartes utm shapely regionmask iris rasterio cligj bottleneck scikit-image umap-learn scipy scikit-learn numba rioxarray

```

##### Install pptk
pip install ./build/pptk-0.1.0-cp37-none-macosx_10_13_x86_64.whl

##### Install hyperclass
```
(geoproc)>> git clone git@github.com:nasa-nccs-cds/hyperclass.git
(geoproc)>> cd hyperclass
(geoproc)>> python setup.py install

