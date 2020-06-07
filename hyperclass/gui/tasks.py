from typing import List, Union, Dict, Callable, Tuple, Optional
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from functools import partial
import traceback, sys

class TaskSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Task(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Task, self).__init__()
        self.fn = fn
        self.args = args
        self.context = kwargs.pop('task_context','console')
        self.kwargs = kwargs
        self.signals = TaskSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    def id(self):
        return f"{id(self.fn):0X}{id(self.args):0X}{id(self.kwargs):0X}"

    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

    @classmethod
    def mainWindow(cls) -> Optional[QMainWindow]:
        # Global function to find the (open) QMainWindow in application
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None

    @classmethod
    def showErrorMessage(cls, msg: str ):
        error_dialog = QtWidgets.QErrorMessage()
        error_dialog.showMessage( msg )

    @classmethod
    def showMessage(cls, title: str, caption: str, message: str, icon  ):  # QMessageBox.Critical QMessageBox.Information QMessageBox.Warning
        msg_dialog = QtWidgets.QMessageBox()
        msg_dialog.setIcon( icon )
        msg_dialog.setText( caption )
        msg_dialog.setInformativeText(message)
        msg_dialog.setWindowTitle(title)
        msg_dialog.exec_()

    @classmethod
    def taskNotAvailable(cls, caption: str, msg: str ):
        cls.showMessage("Task Not Available", caption, msg,  QMessageBox.Warning )

class TaskRunner(QObject):

    def __init__(self, *args, **kwargs):
        super(TaskRunner, self).__init__()
        self.threadpool = QThreadPool()
        self.executing_tasks = []
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

    def start(self, task: Task, message: str, **kwargs ):
        from hyperclass.gui.application import HyperclassConsole
        if message not in self.executing_tasks:
            print(f"Task[{task.context}] running: {message}")
            self.executing_tasks.append( message )
            hyperclass: HyperclassConsole = Task.mainWindow()
            hyperclass.showMessage( message )
            task.signals.finished.connect( partial( hyperclass.refresh, message, task.context, **kwargs ) )
            task.signals.finished.connect( partial( self.complete, message ) )
            self.threadpool.start(task)
        else:
            print( f"Task already running: {message}")


    def kill_all_tasks(self):
        self.threadpool.clear()

    def complete( self, message, **kwargs ):
        self.executing_tasks.remove( message )
        print(f"Task completed: {message}")

taskRunner = TaskRunner()