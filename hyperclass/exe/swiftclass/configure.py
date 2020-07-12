from hyperclass.config.inputs import ConfigurationDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
import sys

app = QApplication(sys.argv)
preferences = ConfigurationDialog("swiftclass")
preferences.show()
sys.exit(app.exec_())