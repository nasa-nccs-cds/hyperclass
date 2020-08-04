# hyperclass
Methods for hyperspectral image classification developed by the NASA Goddard Innovation Lab


## Installation

#### Build Conda Env
```
>> conda create --name hyperclass python=3.7
>> conda activate hyperclass
(hyperclass)>> pip install netcdf4
(hyperclass)>> conda install -c conda-forge xarray dask matplotlib pynndescent numpy rasterio scikit-image umap-learn scipy scikit-learn rioxarray numba pyqt vtk googlemaps requests responses pyproj tensorflow keras 
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
  
#### VNC Setup

Certain hosts, such as the visgpu cluster at NASA, utilize a vnc rather then X conncetion.  The vnc setup procedure for visgpu02 is as follows:
* On your local machine create a file ~/.ssh/ssh_config with the following text (replace tpmaxwel with your username):
``` 
host visgpu02
        User tpmaxwel
        ForwardX11 yes
        LogLevel QUIET
        LocalForward 23128 localhost:3128
        ProxyCommand ssh -l tpmaxwel login.nccs.nasa.gov direct %h
        Protocol 2
        ConnectTimeout 30
``` 
* Install a vnc client. That can be found here https://www.realvnc.com/en/connect/download/viewer/ . You will need admin privileges to install that on your machine. 

* Connect to visgpu02:
``` 
> ssh visgpu02
``` 
* Once logged in start the vnc server:
``` 
> startvnc
``` 

* Configure the vnc client: 
    Navigate to the system preferences then to the proxy tab. There select "use these proxy settings" and from there enter for "Server: 127.0.0.1:<vncPort>" and "Type" should say "HTTP CONNECT".  The <vncPort> number will be listed in the vnc startup output on the server.

* Startup the client:
``` 
> startvnc
``` 

#### Configuration
  Set default parameters for all users:
```    
(hyperclass)>> python hyperclass/exe/configure.py
```

#### Startup the hyperclass console

```    
(hyperclass)>> python hyperclass/exe/console.py
```
