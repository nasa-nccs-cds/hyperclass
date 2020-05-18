from hyperclass.util.tasks import TaskRunner
from PyQt5.QtCore import QEventLoop, QTimer
from typing import List, Union, Dict, Callable, Tuple, Optional


class QtTaskRunner(TaskRunner):

    def __init__(self,  ):
        TaskRunner.__init__( self )
        self.eventLoop = None

    def isRunning(self):
        return self.eventLoop.isRunning()

    def quit(self):
        return self.eventLoop.quit()

    def start( self, timeout ):
        self.eventLoop = QEventLoop()
        def executable():
            self.action(*self.args)
            exit()
        QTimer.singleShot( timeout, executable )
        self.eventLoop.exec_()