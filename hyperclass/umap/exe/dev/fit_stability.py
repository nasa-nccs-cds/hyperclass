from hyperclass.data.aviris.tile import Tile, Block
from hyperclass.umap.manager import UMAPManager
import plotly.graph_objs as go

# Fit UMAP to hyperspectral data and view embedding

if __name__ == '__main__':

    image_name = "ang20170720t004130_corr_v2p9"
    refresh = True
    subsample = 5
    colors =[ '#000000', '#00ff00', '#ff0000', '#0000ff' ]
    block_indices = [ [0,0], [0,1], [1,0], [1,1] ]

    dm = DataManager( image_name )
    tile: Tile = dm.getTile()
    umgr = UMAPManager(tile, refresh=refresh)

    plot_data = [ ]
    for color, block_index in zip(colors,block_indices):
        block: Block = tile.getBlock( *block_index )
        umgr.embed(block = block, subsample = subsample)
        points1 = umgr._mapper.embedding_
        plot_data.append( go.Scatter3d( x=points1[:,0], y=points1[:,1], z=points1[:,2], mode='markers',  marker= dict( color = color, size=1 ) ) )

    fig = go.Figure( data=plot_data )
    fig.show()









