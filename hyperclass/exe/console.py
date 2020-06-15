from PyQt5 import QtWidgets
from hyperclass.gui.application import HyperclassConsole
import sys

classes = [ ('BareEarth', [1.0, 1.0, 0.0, 1.0]),
           ('Forest', [0.0, 1.0, 0.0, 1.0]),
           ('Urban', [1.0, 0.0, 1.0, 1.0]),
           ('Water', [0.0, 0.0, 1.0, 1.0])]

valid_bands = [[3, 193], [210, 287], [313, 421]]

app = QtWidgets.QApplication(sys.argv)
hyperclass = HyperclassConsole( classes, valid_bands=valid_bands )
hyperclass.show()
sys.exit(app.exec_())