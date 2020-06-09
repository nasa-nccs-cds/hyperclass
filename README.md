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

