# hyperclass
Methods for hyperspectral image classification developed by the NASA Goddard Innovation Lab


## Installation

#### Build Conda Env
```
>> conda create --name hyperclass python=3.7
>> conda activate hyperclass
(hyperclass)>> conda install -c conda-forge xarray dask matplotlib pynndescent numpy rasterio scikit-image umap-learn scipy scikit-learn rioxarray numba pyqt vtk googlemaps requests responses pyproj 
```

#### Install Hyperclass
```
(hyperclass)>> git clone git@github.com:nasa-nccs-cds/hyperclass.git
(hyperclass)>> cd hyperclass
(hyperclass)>> python setup.py install
```

#### Install with rapids-ai
``` 
>> conda create --name hyperclass python=3.7
>> conda activate hyperclass``
(hyperclass)>> conda install -c rapidsai -c nvidia -c conda-forge -c defaults rapids matplotlib pynndescent  rasterio  rioxarray  pyqt vtk googlemaps requests responses pyproj umap-learn scikit-image
```

#### GeoProc environment 
``` 
>> conda create --name geohyperclass python=3.6
>> conda activate geohyperclass``
(hyperclass)>> conda install -c conda-forge xarray dask matplotlib pynndescent numpy rasterio scikit-image umap-learn scipy scikit-learn rioxarray numba pyqt vtk googlemaps requests responses pyproj python-wget utm bottleneck geopandas regionmask shapely 
```
#### Google Maps Access
  To access google maps you must obtain an API key: <https://cloud.google.com/docs/authentication/api-keys>
  
#### Configuration
  Set default parameters for all users:
```    
(hyperclass)>> python hyperclass/exe/configure.py
```

#### Startup the hyperclass console

```    
(hyperclass)>> python hyperclass/exe/console.py
```
