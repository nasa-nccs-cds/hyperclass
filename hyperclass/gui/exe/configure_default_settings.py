from hyperclass.gui.config import PreferencesDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
import sys

app = QApplication(sys.argv)
settings = QSettings( QSettings.SystemScope )
preferences = PreferencesDialog(app,settings)
preferences.show()
sys.exit(app.exec_())