from hyperclass.config.inputs import ConfigurationDialog
from PyQt5.QtWidgets import QApplication
from hyperclass.data.manager import dataManager
import sys

default_settings = {}
app = QApplication(sys.argv)
dataManager.initProject( "swiftclass", default_settings )
preferences = ConfigurationDialog()
sys.exit(preferences.exec_())