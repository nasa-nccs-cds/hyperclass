from PyQt5 import QtWidgets
from hyperclass.gui.application import HyperclassConsole
from typing import List, Union, Tuple, Optional
import sys

classes = [ ('Corn-no till', "#0000FF"),
           ('Corn-min till', "#FF9900" ),
           ('Grass/Pasture', "#3333FF"),
           ('Grass/Trees',   "#99CC00"),
            ('Hay-windrowed', "#66FF33"),
            ('Soybean-no till', "#993399"),
            ('Soybean-min till', "#33FFCC"),
            ('Soybean-clean till', "#336699"),
            ('Woods', "#996600") ]


app = QtWidgets.QApplication(sys.argv)
hyperclass = HyperclassConsole( classes )
hyperclass.show()
sys.exit(app.exec_())





