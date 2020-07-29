from hyperclass.config.inputs import ConfigurationDialog
from PyQt5.QtWidgets import QApplication
from hyperclass.data.manager import dataManager
import sys

app = QApplication(sys.argv)
dataManager.setProjectName("swiftclass")
preferences = ConfigurationDialog()
preferences.show()
sys.exit(app.exec_())