import xarray as xa
import umap, time, pickle
import umap.plot
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Block, Tile
from hyperclass.umap.manager import UMAPManager
import plotly.graph_objs as go
import os, math

# Fit UMAP-transform 4 blocks of data and view the embedding

if __name__ == '__main__':
    image_name = "ang20170720t004130_corr_v2p9"
    subsample = 5
    colors =[ '#0000ff', '#00ff00', '#ff0000', '#000000' ]
    indices = [ [0,0], [0,1], [1,0], [1,1] ]

    dm = DataManager( image_name )
    tile: Tile = dm.getTile()
    umgr =  UMAPManager( tile )

    data = []
    for color, block_index in zip(colors,indices):
        result = umgr.transform( tile.getBlock(*block_index) )
        points = result["points"][::subsample]
        data.append( go.Scatter3d( x=points[:,0], y=points[:,1], z=points[:,2], mode='markers', marker= dict( color = color, size=1 ) ) )

    fig = go.Figure( data=data )
    fig.show()



