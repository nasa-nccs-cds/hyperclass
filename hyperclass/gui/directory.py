import sys
import numpy as np
from PyQt5.QtCore import *
from collections import OrderedDict
from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QAction, QVBoxLayout, QTableWidget
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.events import EventClient

class NumericTableWidgetItem(QTableWidgetItem):

    def __lt__(self, other):
        t0, t1 = self.text(), other.text()
        return float(t0) < float(t1)

class DirectoryWidget(QWidget,EventClient):
    build_table = pyqtSignal()

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.table  = QTableWidget( self )
        self.table.cellClicked.connect( self.onCellClicked )
        self.table.verticalHeader().sectionDoubleClicked.connect( self.onRowSelection )
        self.table.horizontalHeader().sectionDoubleClicked.connect( self.onColumnSelection )
        self.layout.addWidget( self.table )
        self.col_data = OrderedDict()
        self.build_table.connect( self.build_table_slot )
        self.activate_event_listening()

    def onCellClicked(self, row, col ):
        print( f"DirectoryWidget:cell_clicked: {row} {col} ")

    def onColumnSelection(self, col  ):
        self.table.sortItems(col)
        self.update()

    def onRowSelection(self, row  ):
        print(f"DirectoryWidget:onRowSelection: {row} ")

    def keyPressEvent( self, event ):
        event = dict( event="key", type="press", key=event.key() )
        self.processEvent(event)

    def keyReleaseEvent(self, event):
        event = dict( event="key", type="release", key=event.key() )
        self.processEvent(event)

    @pyqtSlot()
    def build_table_slot(self):
        cols = list(self.col_data.values())
        self.table.setRowCount( len(cols[0]) )
        self.table.setColumnCount( len( self.col_data.keys() ) )
        for column, (cid, row_data) in enumerate(self.col_data.items()):
            self.table.setColumnWidth( column, 200 )
            column_header: QTableWidgetItem = QTableWidgetItem(cid)
            self.table.setHorizontalHeaderItem( column, column_header )
            for row, value in enumerate(row_data):
                if isinstance(value,str):   table_item = QTableWidgetItem( value )
                else:                       table_item = NumericTableWidgetItem( str(value) )
                self.table.setItem(row, column, table_item)
        self.table.sortItems(1)
        self.update()

    def processEvent( self, event: Dict ):
        if dataEventHandler.isDataLoadEvent(event):
            plot_metadata = dataEventHandler.getMetadata( event )
            targets = plot_metadata['targets'].values.tolist()
            obsids = plot_metadata['obsids'].values.tolist()
            self.col_data['index'] = range( len( targets ) )
            self.col_data['targets'] = targets
            self.col_data['obsids'] = obsids
            self.build_table.emit()

    @property
    def button_actions(self) -> Dict[str, Callable]:
        return self.canvas.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.canvas.menu_actions

