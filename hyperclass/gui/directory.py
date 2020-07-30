from hyperclass.gui.config import SearchBar
from hyperclass.util.config import tostr
import xarray as xa, traceback
from PyQt5.QtCore import *
from collections import OrderedDict
from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QAction, QVBoxLayout, QTableWidget
from PyQt5.QtGui import QBrush, QColor
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.gui.labels import labelsManager, Marker
from hyperclass.gui.tasks import taskRunner, Task
from PyQt5.QtWidgets import QMessageBox

class NumericTableWidgetItem(QTableWidgetItem):

    def __lt__(self, other):
        try:
            t0, t1 = self.text(), other.text()
            return float(t0) < float(t1)
        except:
            print( f"NumericTableWidget comparison error: {self.text()} < {other.text()}")
            traceback.print_exc( 50 )
            return False

class DirectoryWidget(QWidget,EventClient):
    build_table = pyqtSignal()

    def __init__(self, name: str, *args, **kwargs):
        QWidget.__init__(self)
        self.name = name
        self.nRows = 0
        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(10,2,10,2)
        self.setLayout(self.layout)
        self.table  = QTableWidget( self )
        self.table.cellClicked.connect( self.onCellClicked )
        self.table.cellPressed.connect(self.onCellPressed)
        self.table.verticalHeader().sectionClicked.connect( self.onRowSelection )
        self.table.horizontalHeader().sectionClicked.connect( self.onColumnSelection )
        self.layout.addWidget( self.table )
        self.searchbar = SearchBar( self, self.findRow, self.selectRows )
        self.layout.addWidget( self.searchbar )
        self.col_data = OrderedDict()
        self.current_pid = None
        self._head_row = 0
        self._selected_row = 0
        self.col_headers = []
        self.sequence_bounds = []
        self.sort_column = 1
        self.selectedColumn = -1
        self.pick_enabled = False
        self._key_state = None
        self._key_state_modifiers = None
        self._marked_rows = []
        self._enabled = False
        self._current_search_str = ""
        self.build_table.connect( self.build_table_slot )
        self.activate_event_listening()

    def findRow(self, searchStr: str  ):
        if self.selectedColumn >= 0:
            if not searchStr.startswith(self._current_search_str): self._selected_row = 0
            print( f"FIND: {searchStr}")
            rows = self.table.rowCount()
            for iRow in range( self._selected_row, rows ):
                item: QTableWidgetItem = self.table.item( iRow, self.selectedColumn )
                try:
                    if item.text().startswith( searchStr ):
                        self.selectRow( iRow, False )
                        self._current_search_str = searchStr
                        self._selected_row = iRow
                        break
                except: break

    def selectRows(self, searchStr: str  ):
        print( f"FIND: {searchStr}")

    def activate(self, enable: bool ):
        self._enabled = enable
 #       print( f" DirectoryWidget[{self.name}] enabled = {enable}")

    def onCellClicked(self, row, col ):
        print( "dir on cell clicked")
        self.selectRow( row, False )
        self.update()

    def onCellPressed(self, row, col ):
        print( "dir on cell pressed")
        self.selectRow( row, True )

    def onColumnSelection( self, col  ):
        self.table.sortItems(col)
        self.selectedColumn = col
        self.update()

    def selectRow( self, row: int, rightClick: bool ):
 #       print(f" DirectoryWidget[{self.name}] selectRow[{row}], enabled: {self._enabled}")
        if self._enabled and (row >= 0):
            table_item: QTableWidgetItem = self.table.item( row, self._index_column )
            self._selected_row = row
            mark = rightClick and self.pick_enabled
            event = dict( event="pick", type="directory", pids=[int( table_item.text() )], mark = mark )
            self.submitEvent( event, EventMode.Gui )

    def onRowSelection( self, row  ):
        self.selectRow( row, True )

    def keyPressEvent( self, event ):
        event = dict( event="key", type="press", key=event.key() )
        self.processEvent(event)

    def keyReleaseEvent(self, event):
        event = dict( event="key", type="release", key=event.key() )
        self.processEvent(event)

    @pyqtSlot()
    def build_table_slot(self):
        ncols = len(self.col_headers)
        self.table.setRowCount( self.nRows )
        self.table.setColumnCount(  ncols )
        self._index_column = ncols - 1

        for column, cid in enumerate( self.col_headers ):
            self.table.setColumnWidth( column, 150 )
            column_header: QTableWidgetItem = QTableWidgetItem(cid)
            self.table.setHorizontalHeaderItem( column, column_header )
        for column, (cid, row_data) in enumerate(self.col_data.items()):
            for row, value in enumerate(row_data):
                if isinstance(value,str):   table_item = QTableWidgetItem( value )
                else:                       table_item = NumericTableWidgetItem( str(value) )
                self.table.setItem(row, column, table_item)
        self.table.sortItems(self.sort_column)
        self.update()

    def clear_table( self, reset_catalog = False ):
        self.table.clearSelection()
        self._selected_row = -1
        self._head_row = 0
        if (self.name == "catalog") and not reset_catalog:
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

    def setRowData(self, row_data: List ) -> QTableWidgetItem:
        rv = None
        for column, value in enumerate(row_data):
            if isinstance(value, str):
                table_item = QTableWidgetItem(value)
            else:
                table_item = NumericTableWidgetItem(str(value))
            self.table.setItem(self._head_row, column, table_item)
            if column == 0: rv = table_item
        self._head_row = self._head_row + 1
        return rv

    def shiftEnabled(self):
        se1 = self._key_state_modifiers == Qt.ShiftModifier | Qt.ControlModifier
        return se1

    def processEvent( self, event: Dict ):
        if dataEventHandler.isDataLoadEvent(event):
            plot_metadata: List[xa.DataArray] = dataEventHandler.getMetadata( event )
            self.col_headers = []
            self.nRows = None
            for mdata_array in plot_metadata:
                if not self.nRows: self.nRows = mdata_array.shape[0]
                col_name = mdata_array.attrs['name']
                self.col_data[col_name] = mdata_array.values.tolist() if self.name == "catalog" else []
                self.col_headers.append( col_name )
            self.col_data['distance'] = []
            self.col_headers.append('distance')
            self.col_data['index'] = range(self.nRows) if self.name == "catalog" else []
            self.col_headers.append('index')
            self.build_table.emit()
        elif event.get('event') == 'pick':
            etype = event.get('type')
            if etype in [ 'vtkpoint', 'directory', 'plot' ]:
                cid = labelsManager.selectedClass
                if (self.name == "catalog") or (cid == 0):
                    mark = event.get('mark')
                    multi = self.shiftEnabled()
                    if multi and mark and (cid>0):
                        pids = event.get('pids')
                        self.sequence_bounds.append(pids[0])
                        if len( self.sequence_bounds ) == 2:
                            self.sequence_bounds.sort()
                            self.markRowSequence( *self.sequence_bounds )
                            self.sequence_bounds = []
                    else:
                        for pid in event.get('pids'):
                            self.current_pid = pid
                            self.selectRowByIndex( self.current_pid, mark )
                elif (self.name == labelsManager.selectedLabel) and self.pick_enabled:
                    for pid in event.get('pids'):
                        self.current_pid = pid
                        self.addRow( self.current_pid )
                else:
                    for pid in event.get('pids'):
                        mark = self.pick_enabled and cid > 0
                        if self.selectRowByIndex(pid,mark):
                            self.current_pid = pid

        elif event.get('event') == 'gui':
            if event.get('type') == 'keyPress':      self.setKeyState( event )
            elif event.get('type') == 'keyRelease':  self.releaseKeyState()
            elif event.get('type') == 'clear':       self.clear_table( False )
            elif event.get('type') == 'reset':       self.clear_table( True )
            elif event.get('type') == 'mark':        self.markCurrentRow()
            elif event.get('type') == 'undo':        self.clearMarker( event.get('marker') )
            elif event.get('type') == 'spread':
                labels: xa.Dataset = event.get('labels')
                self.addExtendedLabels( labels )
                self.build_table.emit()

    def addRow( self, pid: int, distance: float = 0.0 ):
        item = self.getItemByIndex(pid)
        if item is None:
            plot_metadata = dataEventHandler.getMetadata()
            row_data = []
            self.col_data['index'].append(pid)
            row_data.append( pid )

            for mdata_array in plot_metadata:
                col_name = mdata_array.attrs['name']
                cval = mdata_array.values[pid]
                self.col_data[ col_name ].append( tostr(cval) )
                row_data.append( cval )

            self.col_data['distance'].append( distance )
            row_data.append(0.0)

            self.setRowData(row_data)
            self.update()
        else:
            self.selectRowByIndex(pid,False)

    def markCurrentRow(self):
        self.enablePick()
        marker = labelsManager.currentMarker
        try:
            if self.selectRowByIndex( marker.pid, True ):
                event = dict(event="pick", type="directory", pids=[marker.pid], mark=True )
                self.submitEvent(event, EventMode.Gui)
        except Exception as err:
            if marker is None:
                Task.showMessage("Workflow violation", "", "Must select a point before this operation can be applied", QMessageBox.Critical)
            else: print( f"Row selection error: {err}")
        self.releasePick()

    def addExtendedLabels(self, labels: xa.Dataset ):
        labels, distance = labelsManager.getSortedLabels(labels)
        for itemRef, d in zip(labels, distance):
            label = labelsManager.labels[ itemRef[1] ]
            if label == self.name: self.addRow( itemRef[0], d )
        try:
            self.sort_column = self.col_headers.index('distance')
            self.table.sortItems(self.sort_column)
            self.update()
        except Exception as err:
            print( f"DirectoryWidget.addExtendedLabels Exception: {err} ")
            print( f"Col headers: {self.col_headers}" )

    def clearMarker(self, marker: Marker ):
        if marker is not None:
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
        self._key_state_modifiers = event.get('modifiers')
        if self._key_state == Qt.Key_Control:
            self.pick_enabled = True
#            print( "directory pick enabled" )

    def releaseKeyState( self ):
        self._key_state = None
        self._key_state_modifiers = None
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
            item: QTableWidgetItem = self.table.item( iRow, self._index_column )
            try:
                if pid == int(item.text()): return item
            except: break
        return None

    def getRowRange(self, pid0: int, pid1: int) -> Optional[List[int]]:
        rows = self.table.rowCount()
        pindices = [ pid0, pid1 ]
        row_range = []
        for iRow in range( rows ):
            item: QTableWidgetItem = self.table.item( iRow, self._index_column )
            try:
                if int(item.text()) in pindices:
                    row_range.append( iRow )
                    if len( row_range ) == 2:
                        row_range.sort()
                        return row_range
            except Exception as ex:
                print( f"GetRowRange({iRow}:{pindices}), Exception: {ex}" )
                break
        return None

#    self.table.setRangeSelected(QTableWidgetSelectionRange)
    def markRowSequence( self, pid0, pid1 ):
        self._key_state_modifiers = None
        row_range = self.getRowRange( pid0, pid1 )
        if row_range is None:
            print( "NULL row_range")
        else:
            pids = []
            for iRow in range( row_range[0], row_range[1]+1 ):
                item: QTableWidgetItem = self.table.item( iRow, self._index_column )
                try: pids.append( int(item.text()) )
                except: break
            event = dict( event="pick", type="directory", pids=pids, mark=True )
            self.submitEvent(event, EventMode.Gui)

        # row_range = self.getRowRange( pid0, pid1 )
        # self.table.clearSelection()
        # for iRow in range( row_range[0], row_range[1]+1 ):
        #     item: QTableWidgetItem = self.table.item(iRow, 0)
        #     if item == None: break
        #     try:
        #         color = labelsManager.selectedColor
        #         qcolor = [int(color[ic] * 255.99) for ic in range(3)]
        #         item.setBackground(QBrush(QColor(*qcolor)))
        #         self._marked_rows.append(iRow)
        #     except:
        #         break
        # self.update()

    def selectRowByIndex( self, pid: int, mark: bool ) -> bool:
        rows = self.table.rowCount()
        rv = False
        for iRow in range( rows ):
            item: QTableWidgetItem = self.table.item( iRow, self._index_column )
            if item == None: break
            try:
                if pid == int( item.text() ):
                    rv = True
                    self._selected_row = iRow
                    self.table.scrollToItem( item )
                    if mark:
                        color = labelsManager.selectedColor
                        self.table.clearSelection()
                        qcolor = [int(color[ic] * 255.99) for ic in range(3)]
                        item.setBackground( QBrush( QColor(*qcolor) ) )
                        self._marked_rows.append( iRow )
#                        if multi: self.multiMark( )
                    else:
                        self.table.clearSelection()
                        self.table.selectRow(iRow)
                    break
            except: break
        self.update()
        return rv

#    def markRows( self, )

    def unselectRowByIndex(self, pid: int):
        rows = self.table.rowCount()
        self.table.clearSelection()
        for iRow in range(rows):
            item: QTableWidgetItem = self.table.item(iRow, self._index_column )
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
            item: QTableWidgetItem = self.table.item( iRow, self._index_column )
            if item == None: break
            if item.text() and (pid == int(item.text())):
                for column in range(self.table.columnCount()):
                    self.table.setItem( iRow, column, QTableWidgetItem( "" ) )
                self._head_row = iRow
                break
        self.update()




