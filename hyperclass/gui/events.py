import abc
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QAction
from enum import Enum
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import time, math, os

class EventMode(Enum):
    Foreground = 1
    Background = 2
    Gui = 3

class EventClient:
    __metaclass__ = abc.ABCMeta

    def activate_event_listening(self):
        eventCentral.addClient( self )

    @pyqtSlot(dict)
    def process_event_slot(self, event: Dict):
        self.processEvent( event )

    @abc.abstractmethod
    def processEvent(self, event: Dict ):
        pass

    def submitEvent(self, event: Dict, mode: EventMode ):
        eventCentral.submitEvent( event, mode )

class EventCentral(QObject):
    process_event = pyqtSignal(dict)

    def __init__(self):
        QObject.__init__(self)
        self._clients: List[EventClient] = []

    def addClient(self, client: EventClient ):
        self._clients.append( client )
        self.process_event.connect( client.process_event_slot )

    def submitEvent(self, event: Dict, mode: EventMode ):
        from hyperclass.data.events import dataEventHandler
        from hyperclass.gui.tasks import taskRunner, Task
        dataEventHandler.reset( event )
        if mode == EventMode.Gui:
            self.process_event.emit( event )
        else:
            for client in self._clients:
                if mode == EventMode.Foreground:
                    client.processEvent(event)
                elif mode == EventMode.Background:
                    task_label = ".".join( [ event.get(id,"") for id in [ 'event', 'type', 'label'] ] )
                    task = Task( task_label, client.processEvent, event )
                    taskRunner.start( task )

eventCentral = EventCentral()