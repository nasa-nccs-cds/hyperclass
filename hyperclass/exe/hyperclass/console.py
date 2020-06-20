from PyQt5 import QtWidgets
from hyperclass.data.aviris.application import HyperclassConsole
from hyperclass.data.aviris.manager import dataManager
import sys

classes = [ ('Vegetation', [1.0, 1.0, 0.0, 1.0]),
           ('Forest', [0.0, 1.0, 0.0, 1.0]),
           ('BareEarth', [1.0, 0.0, 1.0, 1.0]),
           ('Water', [0.0, 0.0, 1.0, 1.0])]

valid_bands = [[3, 193], [210, 287], [313, 421]]

app = QtWidgets.QApplication(sys.argv)
hyperclass = HyperclassConsole( classes, valid_bands=valid_bands )
dataManager.config.setValue( 'tile/indices', [1,1] )
hyperclass.show()
sys.exit(app.exec_())