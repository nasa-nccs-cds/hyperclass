import sys
import numpy as np
from PyQt5.QtCore import *
from collections import OrderedDict
from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QAction, QVBoxLayout, QTableWidget
from PyQt5.QtGui import QBrush, QColor
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.gui.labels import labelsManager


class NumericTableWidgetItem(QTableWidgetItem):

    def __lt__(self, other):
        t0, t1 = self.text(), other.text()
        return float(t0) < float(t1)

class DirectoryWidget(QWidget,EventClient):
    build_table = pyqtSignal()

    def __init__(self, name: str, *args, **kwargs):
        QWidget.__init__(self)
        self.name = name
        self.nRows = 0
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.table  = QTableWidget( self )
        self.table.cellClicked.connect( self.onCellClicked )
        self.table.verticalHeader().sectionClicked.connect( self.onRowSelection )
        self.table.horizontalHeader().sectionClicked.connect( self.onColumnSelection )
        self.layout.addWidget( self.table )
        self.col_data = OrderedDict()
        self.current_pid = None
        self._current_row = 0
        self.pick_enabled = False
        self._key_state = None
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
        table_item: QTableWidgetItem = self.table.item( row, 0 )
        iclass = labelsManager.selectedClass if self.pick_enabled else 0
        event = dict( event="pick", type="directory", pid=int( table_item.text() ), cid = iclass )
        self.submitEvent( event, EventMode.Gui )

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
        self.table.setRowCount( self.nRows )
        self.table.setColumnCount( 4 )
        col_headers = [ 'index', 'targets', 'obsids', 'distance']
        for column, cid in enumerate( col_headers ):
            self.table.setColumnWidth( column, 150 )
            column_header: QTableWidgetItem = QTableWidgetItem(cid)
            self.table.setHorizontalHeaderItem( column, column_header )
        for column, (cid, row_data) in enumerate(self.col_data.items()):
            for row, value in enumerate(row_data):
                if isinstance(value,str):   table_item = QTableWidgetItem( value )
                else:                       table_item = NumericTableWidgetItem( str(value) )
                self.table.setItem(row, column, table_item)
        self.table.sortItems(1)
        self.update()

    def setRowData(self, row_data: List ):
        for column, value in enumerate(row_data):
            if isinstance(value, str):
                table_item = QTableWidgetItem(value)
            else:
                table_item = NumericTableWidgetItem(str(value))
            self.table.setItem( self._current_row , column, table_item)
        self._current_row = self._current_row + 1

    def processEvent( self, event: Dict ):
        if dataEventHandler.isDataLoadEvent(event):
            plot_metadata = dataEventHandler.getMetadata( event )
            targets = plot_metadata['targets']
            obsids = plot_metadata['obsids']
            self.nRows = targets.shape[0]
            self.col_data['index'] = range( self.nRows ) if self.name == "catalog" else []
            self.col_data['targets'] = targets.values.tolist() if self.name == "catalog" else []
            self.col_data['obsids'] = obsids.values.tolist() if self.name == "catalog" else []
            self.col_data['distance'] = []
            self.build_table.emit()
        elif event.get('event') == 'pick':
            etype = event.get('type')
            if etype in [ 'vtkpoint', 'directory' ]:
                if (self.name == "catalog"):
                    self.current_pid = event.get('pid')
                    print( f"DirectoryWidget: pick event, pid = {self.current_pid}")
                    self.selectRowByIndex( self.current_pid )
                elif (self.name == labelsManager.selectedLabel) and self.pick_enabled:
                    self.current_pid = event.get('pid')
                    plot_metadata = dataEventHandler.getMetadata(event)
                    row_data = [ self.current_pid, plot_metadata['targets'].values[self.current_pid], plot_metadata['obsids'].values[self.current_pid], 0.0 ]
                    self.col_data['index'].append( row_data[0] )
                    self.col_data['targets'].append( row_data[1] )
                    self.col_data['obsids'].append( row_data[2] )
                    self.col_data['distance'].append( row_data[3] )
                    self.setRowData( row_data )
                    self.update()
        elif event.get('event') == 'gui':
            if event.get('type') == 'keyPress':      self.setKeyState( event )
            elif event.get('type') == 'keyRelease':  self.releaseKeyState( event )

    def setKeyState(self, event ):
        self._key_state = event.get('key')
        if self._key_state == Qt.Key_Control:
            self.pick_enabled = True

    def releaseKeyState(self, event ):
        self._key_state = None
        self.pick_enabled = False

    @property
    def button_actions(self) -> Dict[str, Callable]:
        return self.canvas.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.canvas.menu_actions

    def selectRowByIndex( self, pid: int, col: int = 0 ):
        rows = self.table.rowCount()
        color = labelsManager.selectedColor
        for iRow in range( rows ):
            item: QTableWidgetItem = self.table.item( iRow, col )
            if pid == int( item.text() ):
                self.table.scrollToItem( item )
                self.table.selectRow( iRow )
                if self.pick_enabled and (color is not None):
                    qcolor = [int(color[ic] * 255.99) for ic in range(3)]
                    item.setBackground( QBrush( QColor(*qcolor) ) )
                break
        self.update()



