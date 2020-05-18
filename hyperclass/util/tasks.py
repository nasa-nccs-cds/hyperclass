from typing import List, Union, Dict, Callable, Tuple, Optional

class TaskRunner:

    def __init__( self ):
        pass

    def setAction(self, action: Callable, *args):
        self.action = action
        self.args = args

    def start(self, timeout ):
        pass

    def isRunning(self):
        pass

    def quit(self):
        pass