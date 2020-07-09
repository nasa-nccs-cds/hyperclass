from hyperclass.data.tess.config import PrepareInputsDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
import sys

input_file_ids = [ "camera", "chip", "dec", "lcs", 'ra', 'scaled_lcs', 'tics', 'times', 'tmag' ]
app = QApplication(sys.argv)
preferences = PrepareInputsDialog( [], None,  QSettings.SystemScope)
preferences.show()
sys.exit(app.exec_())