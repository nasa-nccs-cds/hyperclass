from hyperclass.config.inputs import PrepareInputsDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
from typing import List, Union, Dict, Callable, Tuple, Optional
import sys


input_vars = dict( embedding='scaled_lcs', directory = [ "camera", "chip", "dec", 'ra', 'tics', 'tmag' ], plot= dict( y="lcs", x='times' ) )
subsample = 50

app = QApplication(sys.argv)
preferences = PrepareInputsDialog( input_vars, subsample, QSettings.SystemScope )
preferences.show()
sys.exit( app.exec_() )