from hyperclass.config.inputs import PrepareInputsDialog
from PyQt5.QtWidgets import QApplication
from typing import List, Union, Dict, Callable, Tuple, Optional
from hyperclass.data.manager import dataManager
import sys

input_vars = dict( embedding='scaled_lcs', directory = [ 'tics', "camera", "chip", "dec", 'ra', 'tmag' ], plot= dict( y="lcs", x='times' ) )
default_settings = {}

app = QApplication(sys.argv)
dataManager.initProject( 'tessclass', default_settings )
preferences = PrepareInputsDialog( input_vars  )
preferences.show()
sys.exit( app.exec_() )