from hyperclass.config.inputs import PrepareInputsDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
import sys

input_vars = dict( embedding='scaled_specs', directory = [ "obsids", "target_names" ], plot= dict( y="specs", x='spectra_x_axis' ) )
subsample = 50

app = QApplication(sys.argv)
preferences = PrepareInputsDialog( "swiftclass", input_vars, subsample )
preferences.show()
sys.exit( app.exec_() )