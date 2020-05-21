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
    subsamples = [ 4, 3, 2, 1 ]
    colors =[ '#ff0000', '#00ff00', '#0000ff', '#000000' ]

    dm = DataManager( image_name )
    tile: Tile = dm.getTile()
    umgr = UMAPManager(tile, refresh=refresh)
    block: Block = tile.getBlock(0,0)

    plot_data = [ ]
    for color, ss in zip(colors,subsamples):
        umgr.embed(block = block, subsample = ss)
        points1 = umgr.mapper.embedding_
        plot_data.append( go.Scatter3d( x=points1[:,0], y=points1[:,1], z=points1[:,2], mode='markers',  marker= dict( color = color, size=1 ) ) )

    fig = go.Figure( data=plot_data )
    fig.show()

