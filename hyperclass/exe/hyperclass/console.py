from hyperclass.gui.application import HCApplication
from hyperclass.gui.spatial.application import SpatialAppConsole
from hyperclass.data.manager import dataManager
from hyperclass.gui.labels import labelsManager
import sys

classes = [ ('Vegetation', [0.0, 1.0, 1.0, 1.0]),
           ('Forest', [0.0, 1.0, 0.0, 1.0]),
           ('BareEarth', [1.0, 0.0, 1.0, 1.0]),
           ('Water', [0.0, 0.0, 1.0, 1.0])]

valid_bands = [[0, 212], [216, 312], [316, 421]]
default_settings = {'block/size': 300, "umap/nneighbors": 8, "umap/nepochs": 300, 'tile/size': 1200, 'block/indices': [0, 0], 'tile/indices': [0, 0], "svm/ndim": 8}

app = HCApplication()
labelsManager.setLabels( classes )
dataManager.initProject( 'hyperclass', default_settings )
hyperclass = SpatialAppConsole( valid_bands=valid_bands )
dataManager.config.setValue( 'tile/indices', [1,1] )
hyperclass.show()
sys.exit(app.exec_())