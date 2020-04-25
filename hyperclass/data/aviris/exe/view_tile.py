from hyperclass.data.aviris.manager import DataManager
from glue import qglue

c0 = (1000 ,1000)
c1 = (2000 ,2000)
iband = 200
file_name = "ang20170720t004130_corr_v2p9"

dm = DataManager()
raster = dm.read_subtile( file_name, c0, c1, iband )
dm.plot_raster( raster )

#app = qglue( )

#app.show()