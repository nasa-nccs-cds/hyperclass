from hyperclass.data.swift.config import InputPreferencesDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
import sys

input_file_ids = [ "obsids", "specs", "scaled_specs", "target_names", 'spectra_x_axis' ]
app = QApplication(sys.argv)
preferences = InputPreferencesDialog(None, input_file_ids, QSettings.SystemScope)
preferences.show()
sys.exit(app.exec_())