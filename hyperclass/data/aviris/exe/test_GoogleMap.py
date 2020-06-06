from hyperclass.data.aviris.tile import Tile, Block
import matplotlib.pyplot as plt
from hyperclass.data.google import GoogleMaps

block_shape = (250, 250)
image_name = "ang20170720t004130_corr_v2p9"

dm = DataManager( image_name, block_shape=block_shape )
tile: Tile = dm.getTile()
block: Block = tile.getBlock( 0, 0 )

google = GoogleMaps(block)
google_image = google.get_tiled_google_map('satellite')

plt.show()