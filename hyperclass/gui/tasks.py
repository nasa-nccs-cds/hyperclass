from typing import Dict, Tuple, Optional, Callable
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from functools import partial
import traceback, sys, time
from hyperclass.gui.events import EventClient, EventMode

class Task(QRunnable,EventClient):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, label: str, fn: Callable, *args, **kwargs):
        QRunnable.__init__(self)
        self.label = label
        self.fn = fn
        self.args = args
        self.context = kwargs.pop('task_context','console')
        self.kwargs = kwargs

    def id(self):
        return f"{id(self.fn):0X}{id(self.args):0X}{id(self.kwargs):0X}"

    @pyqtSlot()
    def run(self):
        t0 = time.time()
        try:
            self.submitEvent(dict( event='task', type='start', label=self.label), EventMode.Gui)  # Done
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            event = dict( event='task', type='error', label=self.label, exctype=exctype, value=value, traceback=traceback.format_exc() )
            self.submitEvent(  event, EventMode.Gui )
        else:
            self.submitEvent(  dict( event='task', type='result', label=self.label, result=result ), EventMode.Gui )  # Return the result of the processing
        finally:
            dt = time.time()-t0
            print( f"Completed task {self.label} in {dt} sec ({dt/60} min)")
            self.submitEvent(  dict( event='task', type='completed', label=self.label ), EventMode.Gui )  # Done

    @classmethod
    def showErrorMessage(cls, msg: str ):
        error_dialog = QtWidgets.QErrorMessage()
        error_dialog.showMessage( msg )

    @classmethod
    def showMessage(cls, title: str, caption: str, label: str, icon  ):  # QMessageBox.Critical QMessageBox.Information QMessageBox.Warning
        msg_dialog = QtWidgets.QMessageBox()
        msg_dialog.setIcon( icon )
        msg_dialog.setText( caption )
        msg_dialog.setMinimumSize(400,100)
        msg_dialog.setInformativeText(label)
        msg_dialog.setWindowTitle(title)
        msg_dialog.exec_()

class TaskRunner(QObject,EventClient):

    def __init__(self, *args, **kwargs):
        super(TaskRunner, self).__init__()
        self.threadpool = QThreadPool()
        self.executing_tasks = []
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

    def start(self, task: Task, **kwargs ):
        if task.label not in self.executing_tasks:
            print(f"Task[{task.context}] running: {task.label}")
            self.executing_tasks.append( task.label )
            self.threadpool.start(task)
        else:
            print( f"Task already running: {task.label}")

    def message(self, message: Tuple ):
        Task.showMessage( *message )

    def error(self, error: Tuple ):
        Task.showErrorMessage( str(error[1]) )
        print( str( error[2] ) )

    def kill_all_tasks(self):
        self.threadpool.clear()
        self.executing_tasks = []

    def processEvent( self, event: Dict ) :
        super().processEvent(event)
        if event.get('event') == 'task':
            if event.get('type') == 'finished':
                label = event.get('label')
                self.executing_tasks.remove( label )
                print(f"Task completed: {label}")
        elif event.get('event') == "message":
            icon = None
            type: str = event.get('type').lower()
            if type.startswith('warn'): icon = QMessageBox.Warning
            elif type.startswith('info'): icon = QMessageBox.Information
            elif type in ['critical','error']: icon = QMessageBox.Critical
            Task.showMessage( event.get('title'), event.get('caption'), event.get('label'), icon)

taskRunner = TaskRunner()