import abc
from PyQt5.QtCore import *
from enum import Enum
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import time, math, os

class EventMode(Enum):
    Foreground = 1
    Background = 2
    Gui = 3

class EventClient:
    __metaclass__ = abc.ABCMeta

    def __init__(self, **kwargs):
        eventCentral.addClient( self )

    @pyqtSlot(dict)
    def gui_process_event(self, event: Dict):
        self.processEvent( event )

    @abc.abstractmethod
    def processEvent(self, event: Dict ):
        pass

    def submitEvent(self, event: Dict, mode: EventMode ):
        eventCentral.submitEvent( event, mode )

class EventCentral:

    def __init__(self):
        self._clients: List[EventClient] = []

    def addClient(self, client: EventClient ):
        self._clients.append( client )

    def submitEvent(self, event: Dict, mode: EventMode ):
        from hyperclass.gui.tasks import taskRunner, Task
        for client in self._clients:
            if mode == EventMode.Foreground:
                client.processEvent(event)
            elif mode == EventMode.Background:
                task = Task(  f"Submitting event: {event}", client.processEvent, event )
                taskRunner.start( task )
            elif mode == EventMode.Gui:
                client.gui_process_event(event)

eventCentral = EventCentral()