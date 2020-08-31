from hyperclass.gui.unstructured.application import UnstructuredAppConsole
from hyperclass.gui.application import HCApplication
from hyperclass.data.manager import dataManager
import sys
from hyperclass.gui.labels import labelsManager

classes = [ ('class-1', [1.0, 0.0, 0.0, 1.0]),
            ('class-2', [0.0, 1.0, 0.0, 1.0]),
            ('class-3', [1.0, 0.0, 1.0, 1.0]),
            ('class-4', [0.0, 0.0, 1.0, 1.0])]
default_settings = { "umap/nneighbors": 8, "umap/nepochs": 300, "svm/ndim": 8, "umap/gpu": 0 }

app = HCApplication()
labelsManager.setLabels( classes )
dataManager.initProject( 'swiftclass', default_settings )
swiftclass = UnstructuredAppConsole()
swiftclass.gui.show()
sys.exit(app.exec_())