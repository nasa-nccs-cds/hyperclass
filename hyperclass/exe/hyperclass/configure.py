from hyperclass.config.inputs import ConfigurationDialog
from PyQt5.QtWidgets import QApplication
from hyperclass.data.manager import dataManager
import sys

default_settings = {}
app = QApplication(sys.argv)
dataManager.initProject( "hyperclass", default_settings )
preferences = ConfigurationDialog( spatial=True )
sys.exit(preferences.exec_())