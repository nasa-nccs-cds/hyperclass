import abc
import xarray as xa
import numpy as np
from hyperclass.gui.tasks import taskRunner, Task
from PyQt5.QtCore import *
from enum import Enum
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import time, math, atexit, os

class EventMode(Enum):
    Foreground = 1
    Background = 2
    Gui = 3

class EventClient:
    __metaclass__ = abc.ABCMeta

    def __init__(self, **kwargs):
        eventCentral.addClient( self )
        self.process_event = pyqtSignal()
        self.process_event.connect( self.processEvent )

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
        for client in self._clients:
            if mode == EventMode.Foreground:
                client.processEvent(event)
            elif mode == EventMode.Background:
                task = Task( client.processEvent, event )
                taskRunner.start(task, f"Submitting event: {event}")
            elif mode == EventMode.Gui:
                client.process_event.emit( event )

eventCentral = EventCentral()