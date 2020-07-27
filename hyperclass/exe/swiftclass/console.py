from hyperclass.gui.unstructured.application import UnstructuredAppConsole
from hyperclass.gui.application import HCApplication
import sys
from hyperclass.gui.labels import labelsManager

classes = [ ('class-1', [1.0, 0.0, 0.0, 1.0]),
            ('class-2', [0.0, 1.0, 0.0, 1.0]),
            ('class-3', [1.0, 0.0, 1.0, 1.0]),
            ('class-4', [0.0, 0.0, 1.0, 1.0])]


app = HCApplication()
labelsManager.setLabels( classes )
swiftclass = UnstructuredAppConsole('swiftclass')
swiftclass.gui.show()
sys.exit(app.exec_())