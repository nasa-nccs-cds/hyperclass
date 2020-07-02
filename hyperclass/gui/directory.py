import sys
import numpy as np
import xarray as xa
from PyQt5.QtCore import *
from collections import OrderedDict
from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QAction, QVBoxLayout, QTableWidget
from PyQt5.QtGui import QBrush, QColor
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.gui.labels import labelsManager, Marker


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
        self.table.cellPressed.connect(self.onCellPressed)
        self.table.verticalHeader().sectionClicked.connect( self.onRowSelection )
        self.table.horizontalHeader().sectionClicked.connect( self.onColumnSelection )
        self.layout.addWidget( self.table )
        self.col_data = OrderedDict()
        self.current_pid = None
        self._head_row = 0
        self._selected_row = -1
        self.pick_enabled = False
        self._key_state = None
        self._marked_rows = []
        self.build_table.connect( self.build_table_slot )
        self.activate_event_listening()

    def onCellClicked(self, row, col ):
        print( "dir on cell clicked")
        self.selectRow( row, False )
        self.update()

    def onCellPressed(self, row, col ):
        print( "dir on cell pressed")
        self.selectRow( row, True )

    def onColumnSelection( self, col  ):
        self.table.sortItems(col)
        self.update()

    def selectRow( self, row: int, rightClick: bool ):
        if row >= 0:
            table_item: QTableWidgetItem = self.table.item( row, 0 )
            iclass = labelsManager.selectedClass if ( self.pick_enabled ) else 0
            self._selected_row = row
            if rightClick or (iclass == 0):
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

    def clear_table(self):
        self.table.clearSelection()
        self._selected_row = -1
        self._head_row = 0
        if (self.name == "catalog"):
            brush = QBrush( QColor(255, 255, 255) )
            for row in self._marked_rows:
                item: QTableWidgetItem = self.table.item(row, 0)
                item.setBackground( brush )
            self._marked_rows = []
        else:
            for column, (cid, row_data) in enumerate(self.col_data.items()):
                for row, value in enumerate(row_data):
                    self.table.setItem( row, column, QTableWidgetItem( "" ) )
            for key in self.col_data.keys():
                self.col_data[key] = []
        self.update()

    def setRowData(self, row_data: List ):
        for column, value in enumerate(row_data):
            if isinstance(value, str):
                table_item = QTableWidgetItem(value)
            else:
                table_item = NumericTableWidgetItem(str(value))
            self.table.setItem(self._head_row, column, table_item)
        self._head_row = self._head_row + 1

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
                    item = self.getItemByIndex( self.current_pid )
                    if item is None:
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
            elif event.get('type') == 'clear':       self.clear_table()
            elif event.get('type') == 'mark':        self.markCurrentRow()
            elif event.get('type') == 'undo':        self.clearMarker( event.get('marker') )
        elif event.get('event') == 'labels':
            if event.get('type') == 'spread':
                labels = event.get('labels')
                self.addExtendedLabels( labels )
                self.build_table.emit()

    def markCurrentRow(self):
        self.enablePick()
        self.selectRow(self._selected_row, True)
        self.releasePick()

    def addExtendedLabels(self, labels: xa.DataArray ):
        pass

    def clearMarker(self, marker: Marker ):
        if (self.name == "catalog"):    self.unselectRowByIndex( marker.pid )
        else:                           self.clearRowByIndex( marker.pid )

    def enablePick(self):
        self.pick_enabled = True
        event = dict(event="gui", type="keyPress", key=Qt.Key_Control )
        self.submitEvent(event, EventMode.Foreground)

    def releasePick(self):
        self.pick_enabled = False
        event = dict(event="gui", type="keyRelease", key=Qt.Key_Control )
        self.submitEvent(event, EventMode.Foreground)

    def setKeyState(self, event ):
        self._key_state = event.get('key')
        if self._key_state == Qt.Key_Control:
            self.pick_enabled = True
            print( "directory pick enabled" )

    def releaseKeyState(self, event ):
        self._key_state = None
        self.pick_enabled = False

    @property
    def button_actions(self) -> Dict[str, Callable]:
        return self.canvas.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.canvas.menu_actions

    def getItemByIndex(self, pid: int) -> Optional[QTableWidgetItem]:
        rows = self.table.rowCount()
        for iRow in range( rows ):
            item: QTableWidgetItem = self.table.item( iRow, 0 )
            if (item is None) or (pid == int(item.text())):
                return item
        return None

    def selectRowByIndex( self, pid: int ):
        rows = self.table.rowCount()
        color = labelsManager.selectedColor
        cid = labelsManager.selectedClass
        for iRow in range( rows ):
            item: QTableWidgetItem = self.table.item( iRow, 0 )
            if item == None: break
            if pid == int( item.text() ):
                self._selected_row = iRow
                self.table.scrollToItem( item )
                if self.pick_enabled and (cid > 0) and (color is not None):
                    self.table.clearSelection()
                    qcolor = [int(color[ic] * 255.99) for ic in range(3)]
                    item.setBackground( QBrush( QColor(*qcolor) ) )
                    self._marked_rows.append( iRow )
                else:
                    self.table.selectRow(iRow)
                break
        self.update()

    def unselectRowByIndex(self, pid: int):
        rows = self.table.rowCount()
        self.table.clearSelection()
        for iRow in range(rows):
            item: QTableWidgetItem = self.table.item(iRow, 0)
            if item == None: break
            if pid == int(item.text()):
                if iRow in self._marked_rows:
                    if self._selected_row == iRow: self._selected_row = -1
                    item.setBackground( QBrush( QColor( 255, 255, 255 ) ) )
                    self._marked_rows.remove(iRow)
                break
        self.update()

    def clearRowByIndex(self, pid: int):
        rows = self.table.rowCount()
        self.table.clearSelection()
        self._selected_row = -1
        for iRow in range(rows):
            item: QTableWidgetItem = self.table.item(iRow, 0)
            if item == None: break
            if item.text() and (pid == int(item.text())):
                for column in range(self.table.columnCount()):
                    self.table.setItem( iRow, column, QTableWidgetItem( "" ) )
                self._head_row = iRow
                break
        self.update()




