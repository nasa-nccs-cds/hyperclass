from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, math, sys

block_shape = (250, 250)
image_name = "ang20170720t004130_corr_v2p9"

dm = DataManager( image_name, block_shape=block_shape )
tile: Tile = dm.getTile()
block = tile.getBlock( 0, 0 )
latlon_extent = block.extent( 4326 )

print( latlon_extent )