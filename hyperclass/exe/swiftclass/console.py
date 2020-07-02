from hyperclass.data.swift.application import SwiftConsole
from hyperclass.gui.application import HCApplication
import sys
from hyperclass.gui.labels import labelsManager

classes = [ ('Quasar', [1.0, 0.0, 0.0, 1.0]),
            ('Pulsar', [0.0, 1.0, 0.0, 1.0]),
            ('BlackHole', [1.0, 0.0, 1.0, 1.0]),
            ('BinaryStar', [0.0, 0.0, 1.0, 1.0])]

subsample = 100

app = HCApplication()
labelsManager.setLabels( classes )
swiftclass = SwiftConsole( subsample=subsample )
swiftclass.gui.show()
sys.exit(app.exec_())