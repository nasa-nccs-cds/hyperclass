from PyQt5 import QtWidgets
from hyperclass.gui.application import HyperclassConsole
from hyperclass.data.aviris.manager import dataManager
import sys


app = QtWidgets.QApplication(sys.argv)
swiftclass = SwiftclassConsole(  )
swiftclass.show()
sys.exit(app.exec_())