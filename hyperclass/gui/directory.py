import sys
import xarray as xa
from PyQt5.QtCore import *
from collections import OrderedDict
from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QAction, QVBoxLayout, QTableWidget
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.events import EventClient


class DirectoryWidget(QWidget,EventClient):
    build_table = pyqtSignal()

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.table  = QTableWidget( self )
        self.layout.addWidget( self.table )
        self.col_data = OrderedDict()
        self.build_table.connect( self.build_table_slot )
        self.activate_event_listening()

    def keyPressEvent( self, event ):
        event = dict( event="key", type="press", key=event.key() )
        self.processEvent(event)

    def keyReleaseEvent(self, event):
        event = dict( event="key", type="release", key=event.key() )
        self.processEvent(event)

    @pyqtSlot()
    def build_table_slot(self):
        cols = list(self.col_data.values())
        self.table.setRowCount( cols[0].size )
        self.table.setColumnCount( len( self.col_data.keys() ) )
        for column, (cid, row_data) in enumerate(self.col_data.items()):
            self.table.setColumnWidth( column, 200 )
            column_header: QTableWidgetItem = QTableWidgetItem(cid)
            self.table.setHorizontalHeaderItem( column, column_header )
            for row,item_text in enumerate(row_data):
                table_item: QTableWidgetItem  = QTableWidgetItem(item_text)
                self.table.setItem(row, column, table_item)
        self.update()

    def processEvent( self, event: Dict ):
        if dataEventHandler.isDataLoadEvent(event):
            plot_metadata = dataEventHandler.getMetadata( event )
            self.col_data['targets'] = plot_metadata['targets'].values
            self.col_data['obsids'] = plot_metadata['obsids'].values
            self.build_table.emit()

    @property
    def button_actions(self) -> Dict[str, Callable]:
        return self.canvas.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.canvas.menu_actions

