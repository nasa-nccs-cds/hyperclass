import abc
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QAction
from enum import Enum
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
import time, math, os
import traceback

class EventMode(Enum):
    Foreground = 1
    Background = 2
    Gui = 3

def etmatch( event: Dict, etype: Dict  ):
    return ( event["event"] == etype["event"] ) and ( event["type"] == etype["type"] )

class EventClient:
    event_debug = False
    uninteresting_events = [ dict( event="gui", type="keyRelease"), dict( event="gui", type="keyPress") ]

    def activate_event_listening(self):
        eventCentral.addClient( self )

    def is_interesting( self, event ):
        for etype in self.uninteresting_events:
            if etmatch( event, etype ): return False
        return True

    @pyqtSlot(dict)
    def process_event_slot(self, event: Dict):
        try: self.processEvent( event )
        except Exception as err:
            print( f" processEvent error: {err}")
            traceback.print_exc( 250 )

    def processEvent(self, event: Dict ):
        if self.event_debug and self.is_interesting(event): print(f"CLASS {self.__class__.__name__}: process {event}")

    def submitEvent(self, event: Dict, mode: EventMode ):
        if self.event_debug and self.is_interesting(event): print(f"CLASS {self.__class__.__name__}: submit {event}")
        eventCentral.submitEvent( event, mode )

    @classmethod
    def event_match(cls, event: Dict, name: str, type: str, state: str = "start" ) -> bool:
        if (event['event'] == name) and  (event['type'] == type ): return True
        # if ( event['event'] == "task" ) and ( event['type'] == state ):
        #     labels = event['label'].split('.')
        #     if (name == labels[0]) and (name == type[1]): return True
        return False

class EventCentral(QObject):
    process_event = pyqtSignal(dict)

    def __init__(self):
        QObject.__init__(self)
        self._clients: List[EventClient] = []

    def addClient(self, client: EventClient ):
        try:
            self.process_event.connect( client.process_event_slot )
            self._clients.append(client)
        except Exception as err:
            print( f"Error connecting process_event_slot for client {client.__class__.__name__}: {err}")

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