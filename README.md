# hyperclass
Methods for hyperspectral image classification developed by the NASA Goddard Innovation Lab


### Installation

##### Build Conda Env
```
>> conda create --name hyperclass
>> conda activate hyperclass
(geoproc)>> conda install -c conda-forge xarray dask distributed matplotlib datashader colorcet holoviews numpy geopandas descartes utm shapely regionmask iris rasterio cligj bottleneck  umap-learn scipy scikit-learn numba 

```

##### Install hyperclass
```
(geoproc)>> git clone git@github.com:nasa-nccs-cds/hyperclass.git
(geoproc)>> cd hyperclass
(geoproc)>> python setup.py install

