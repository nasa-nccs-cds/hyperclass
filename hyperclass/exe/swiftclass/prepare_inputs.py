from hyperclass.config.inputs import PrepareInputsDialog
from PyQt5.QtWidgets import QApplication
from typing import List, Union, Dict, Callable, Tuple, Optional
import sys

input_vars = dict( embedding='scaled_specs', directory = [ "obsids", "target_names" ], plot= dict( y="specs", x='spectra_x_axis' ) )

app = QApplication(sys.argv)
preferences = PrepareInputsDialog( "swiftclass", input_vars )
preferences.show()
sys.exit( app.exec_() )