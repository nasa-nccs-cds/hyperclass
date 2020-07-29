from hyperclass.config.inputs import PrepareInputsDialog
from PyQt5.QtWidgets import QApplication
from typing import List, Union, Dict, Callable, Tuple, Optional
from hyperclass.data.manager import dataManager
import sys

input_vars = dict( embedding='scaled_lcs', directory = [ "camera", "chip", "dec", 'ra', 'tics', 'tmag' ], plot= dict( y="lcs", x='times' ) )

app = QApplication(sys.argv)
dataManager.setProjectName("tessclass")
preferences = PrepareInputsDialog( input_vars  )
preferences.show()
sys.exit( app.exec_() )