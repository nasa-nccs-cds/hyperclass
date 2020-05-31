from matplotlib.image import AxesImage
from .aviris.manager import DataManager, Tile, Block
from urllib import request
from io import BytesIO
from math import log, exp, tan, atan, ceil
from PIL import Image
import sys

class GoogleMaps:
    tau = 6.283185307179586
    DEGREE = tau / 360
    ZOOM_OFFSET = 8

    def __init__( self, zoom = 14 ):
        self.zoom = zoom
        self.max_image_size = [ 800, 800 ]

    def get_google_map( self, block: Block  ) -> Image.Image:
        api_key = block.tile.dm.config["api_key"]
        extent = block.extent( 4326 )   # left, right, bottom, top
        center = [ (extent[0]+extent[1])/2, (extent[2]+extent[3])/2  ]
        ulx, uly = self.latlon2pixels(extent[3], extent[0], self.zoom )
        lrx, lry = self.latlon2pixels( extent[2], extent[1], self.zoom )
        width, height = lrx - ulx, uly - lry
        print( f"Accessing google map at {center[1]},{center[0]} with dimensions {width}x{height}" )
        url = f"http://maps.googleapis.com/maps/api/staticmap?center={center[0]},{center[1]}&size={width}x{height}&zoom={self.zoom}&sensor=false&key={api_key}&maptype=satellite"
        buffer = BytesIO(request.urlopen(url).read())
        image: Image.Image = Image.open(buffer)
        return image

    @classmethod
    def latlon2pixels( cls, lat, lon, zoom):
        mx, my = lon, log(tan((lat + cls.tau / 4) / 2))
        res = 2 ** (zoom + cls.ZOOM_OFFSET) / cls.tau
        return mx * res, my * res

    def pixels2latlon( cls, px, py, zoom ):
        res = 2 ** (zoom + cls.ZOOM_OFFSET)/cls.tau
        mx, my = px/res, py/res
        lon = mx
        lat = 2 * atan(exp(my)) - cls.tau/4
        return lat, lon

    #
    # def get_maps_image(NW_lat_long, SE_lat_long, zoom=18):
    #     ullat, ullon = NW_lat_long
    #     lrlat, lrlon = SE_lat_long
    #
    #     # convert all these coordinates to pixels
    #     ulx, uly = latlon2pixels(ullat, ullon, zoom)
    #     lrx, lry = latlon2pixels(lrlat, lrlon, zoom)
    #
    #     # calculate total pixel dimensions of final image
    #     dx, dy = lrx - ulx, uly - lry
    #
    #     # calculate rows and columns
    #     cols, rows = ceil(dx / MAXSIZE), ceil(dy / MAXSIZE)
    #
    #     # calculate pixel dimensions of each small image
    #     width = ceil(dx / cols)
    #     height = ceil(dy / rows)
    #     heightplus = height + LOGO_CUTOFF
    #
    #     # assemble the image from stitched
    #     final = Image.new('RGB', (int(dx), int(dy)))
    #     for x in range(cols):
    #         for y in range(rows):
    #             dxn = width * (0.5 + x)
    #             dyn = height * (0.5 + y)
    #             latn, lonn = pixels2latlon(
    #                 ulx + dxn, uly - dyn - LOGO_CUTOFF / 2, zoom)
    #             position = ','.join((str(latn / DEGREE), str(lonn / DEGREE)))
    #             print(x, y, position)
    #             urlparams = {
    #                 'center': position,
    #                 'zoom': str(zoom),
    #                 'size': '%dx%d' % (width, heightplus),
    #                 'maptype': 'satellite',
    #                 'sensor': 'false',
    #                 'scale': 1
    #             }
    #             if GOOGLE_MAPS_API_KEY is not None:
    #                 urlparams['key'] = GOOGLE_MAPS_API_KEY
    #
    #             url = 'http://maps.google.com/maps/api/staticmap'
    #             try:
    #                 response = requests.get(url, params=urlparams)
    #                 response.raise_for_status()
    #             except requests.exceptions.RequestException as e:
    #                 print(e)
    #                 sys.exit(1)
    #
    #             im = Image.open(BytesIO(response.content))
    #             final.paste(im, (int(x * width), int(y * height)))
    #
    #         return final
    #
