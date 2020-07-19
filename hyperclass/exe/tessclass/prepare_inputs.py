from hyperclass.config.inputs import PrepareInputsDialog
from PyQt5.QtWidgets import QApplication
from typing import List, Union, Dict, Callable, Tuple, Optional
import sys

input_vars = dict( embedding='scaled_lcs', directory = [ "camera", "chip", "dec", 'ra', 'tics', 'tmag' ], plot= dict( y="lcs", x='times' ) )

app = QApplication(sys.argv)
preferences = PrepareInputsDialog( "tessclass", input_vars  )
preferences.show()
sys.exit( app.exec_() )