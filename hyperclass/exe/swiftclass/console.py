from hyperclass.data.swift.application import SwiftConsole
from hyperclass.gui.application import HCApplication
import sys



classes = [ ('Type 1', [1.0, 1.0, 0.0, 1.0]),
            ('Type 2', [0.0, 1.0, 0.0, 1.0]),
            ('Type 3', [1.0, 0.0, 1.0, 1.0]),
            ('Type 4', [0.0, 0.0, 1.0, 1.0])]

subsample = 50

app = HCApplication()
swiftclass = SwiftConsole( classes, subsample=subsample )
swiftclass.gui.show()
sys.exit(app.exec_())