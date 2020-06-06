from PyQt5 import QtWidgets
from hyperclass.gui.application import HyperclassConsole
import sys

classes = [ ('Vegetation', [0.0, 1.0, 1.0, 1.0]),
           ('Forest', [0.0, 1.0, 0.0, 1.0]),
           ('BareEarth', [1.0, 0.0, 1.0, 1.0]),
           ('Water', [0.0, 0.0, 1.0, 1.0])]

app = QtWidgets.QApplication(sys.argv)
hyperclass = HyperclassConsole( classes )
hyperclass.show()
sys.exit(app.exec_())