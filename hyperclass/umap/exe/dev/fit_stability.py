import xarray as xa
import umap, time, pickle
import umap.plot
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.umap.manager import UMAPManager
from hyperclass.plot.points import datashade_points, point_cloud_3d
import plotly.graph_objs as go
import os, math

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    image_name = "ang20170720t004130_corr_v2p9"
    refresh = True
    subsample = 5
    colors =[ '#0000ff', '#00ff00', '#ff0000', '#000000' ]
    block_indices = [ [0,0], [0,1], [1,0], [1,1] ]

    dm = DataManager( image_name )
    tile: Tile = dm.getTile()
    umgr = UMAPManager(tile, refresh=refresh)

    plot_data = [ ]
    for color, block_index in zip(colors,block_indices):
        block: Block = tile.getBlock( *block_index )
        umgr.fit( block = block, subsample = subsample )
        points1 = umgr.mapper.embedding_
        plot_data.append( go.Scatter3d( x=points1[:,0], y=points1[:,1], z=points1[:,2], mode='markers',  marker= dict( color = color, size=1 ) ) )

    fig = go.Figure( data=plot_data )
    fig.show()









