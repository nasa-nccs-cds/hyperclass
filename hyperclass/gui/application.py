from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from hyperclass.umap.manager import UMAPManager
from hyperclass.gui.mpl import MplWidget
from hyperclass.gui.points import VTKFrame
from typing import List, Union, Dict, Callable, Tuple, Optional

class MainWindow(QMainWindow):
    def __init__(self, umgr: UMAPManager):
        QMainWindow.__init__(self)

        self.title = 'hyperclass'
        self.left = 10
        self.top = 10
        self.width = 1920
        self.height = 1080
        self.NFunctionButtons = 0

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.statusBar().showMessage('Ready')

        mainMenu = self.menuBar()
        mainMenu.setNativeMenuBar(False)
        fileMenu = mainMenu.addMenu('File')
        helpMenu = mainMenu.addMenu('Help')

        exitButton = QAction(QIcon('exit24.png'), 'Exit', self)
        exitButton.setShortcut('Ctrl+Q')
        exitButton.setStatusTip('Exit application')
        exitButton.triggered.connect(self.close)
        fileMenu.addAction(exitButton)

        widget =  QWidget(self)
        self.setCentralWidget(widget)
        vlay = QVBoxLayout(widget)

        framesLayout = QHBoxLayout()
        self.console = MplWidget( umgr,self)
        framesLayout.addWidget( self.console )
        self.vtkFrame = VTKFrame( umgr )
        framesLayout.addWidget(self.vtkFrame)
        vlay.addLayout(framesLayout)

        buttonsLayout = QHBoxLayout()
        for label, callback in self.console.button_actions.items():
            pybutton = QPushButton( label, self )
            pybutton.clicked.connect( self.wrapAction(callback) )
            buttonsLayout.addWidget(pybutton)
        vlay.addLayout(buttonsLayout)

    def wrapAction(self, action: Callable ) -> Callable:
        def x( event ):
            action(event )
            self.vtkFrame.update()
        return x

    def setBlock(self, block_coords: Tuple[int]):
        self.console.setBlock(block_coords)

    def show(self):
        QMainWindow.show(self)
        self.vtkFrame.Initialize()
