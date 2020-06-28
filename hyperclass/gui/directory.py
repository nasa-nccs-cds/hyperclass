import sys
import numpy as np
from PyQt5.QtCore import *
from collections import OrderedDict
from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QAction, QVBoxLayout, QTableWidget
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.events import EventClient, EventMode


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
        self.table.verticalHeader().sectionClicked.connect( self.onRowSelection )
        self.table.horizontalHeader().sectionClicked.connect( self.onColumnSelection )
        self.layout.addWidget( self.table )
        self.col_data = OrderedDict()
        self.current_pid = None
        self.build_table.connect( self.build_table_slot )
        self.activate_event_listening()

    def onCellClicked(self, row, col ):
        self.table.selectRow(row)
        self.selectRow(row)
        self.update()

    def onColumnSelection( self, col  ):
        self.table.sortItems(col)
        self.update()

    def selectRow( self, row ):
        print(f"DirectoryWidget:onRowSelection: {row} ")
        table_item: QTableWidgetItem = self.table.item( row, 0 )
        event = dict( event="pick", type="directory", pid=int( table_item.text() ) )
        self.submitEvent( event, EventMode.Foreground )

    def onRowSelection( self, row  ):
        self.selectRow(row)

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
            targets = plot_metadata['targets']
            obsids = plot_metadata['obsids']
            self.col_data['index'] = range( targets.shape[0] )
            self.col_data['targets'] = targets.values.tolist()
            self.col_data['obsids'] = obsids.values.tolist()
            self.build_table.emit()
        elif event.get('event') == 'pick':
            if event.get('type') == 'vtkpoint':
                self.current_pid = event.get('pid')
                color = event.get( 'color', [1.0, 1.0, 1.0 ] )
                print( f"DirectoryWidget: pick event, pid = {self.current_pid}")
                self.selectRowByIndex( self.current_pid )

    @property
    def button_actions(self) -> Dict[str, Callable]:
        return self.canvas.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.canvas.menu_actions

    def selectRowByIndex(self, pid: int, col: int = 0 ):
        rows = self.table.rowCount()
        for iRow in range( rows ):
            item: QTableWidgetItem = self.table.item( iRow, col )
            if pid == int( item.text() ):
                self.table.scrollToItem( item )
                self.table.selectRow( iRow )
                break
        self.update()



