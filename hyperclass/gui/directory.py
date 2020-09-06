from hyperclass.gui.config import SearchBar
from hyperclass.util.config import tostr
import xarray as xa, traceback, re, time
from PyQt5.QtCore import *
from collections import OrderedDict
from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QAction, QVBoxLayout, QTableWidget, QTableView
from PyQt5.QtGui import QBrush, QColor, QMouseEvent
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
from hyperclass.data.events import dataEventHandler
from hyperclass.gui.events import EventClient, EventMode
from hyperclass.gui.labels import labelsManager, Marker
from hyperclass.gui.tasks import taskRunner, Task
from PyQt5.QtWidgets import QMessageBox

L = []


class NumericTableWidgetItem(QTableWidgetItem):

    def __lt__(self, other):
        try:
            t0, t1 = self.text(), other.text()
            return float(t0) < float(t1)
        except:
            print( f"NumericTableWidget comparison error: {self.text()} < {other.text()}")
            traceback.print_exc( 50 )
            return False

class HCTableWidget(QTableWidget) :

    def __init__(self, parent ):
        QTableWidget.__init__( self, parent )
        self.current_button = None

    def mousePressEvent(self, event: QMouseEvent):
        self.current_button = event.button()
        QTableWidget.mousePressEvent(self, event)

    # def mouseReleaseEvent(self, event: QMouseEvent):
    #     self.current_button = event.button()
    #     QTableWidget.mouseReleaseEvent(self,event)

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
        self.table  = HCTableWidget( self )
        self.table.cellPressed.connect(self.onCellPressed)
        self.table.itemSelectionChanged.connect(self.itemSelectionChanged)
        self.table.verticalHeader().sectionClicked.connect( self.onRowSelection )
        self.table.horizontalHeader().sectionClicked.connect( self.onColumnSelection )
        self.layout.addWidget( self.table )
        self.searchbar = SearchBar( self, self.findRow, self.selectRows )
        self.layout.addWidget( self.searchbar )
        self.col_data = OrderedDict()
        self.current_pid = None
        self._head_row = 0
        self._selected_row = -1
        self._search_row = 0
        self.col_headers = []
        self.sequence_bounds = []
        self.sort_column = 1
        self.selectedColumn = -1
        self.pick_enabled = False
        self._key_state = None
        self._key_state_modifiers = None
        self._marked_rows = []
        self._transients = []
        self._selected_rows = []
        self._enabled = False
        self._current_search_str = ""
        self._brushes = {}
        self.build_table.connect( self.build_table_slot )
        self.activate_event_listening()

    @property
    def selected_rows(self):
        return self._selected_rows

    @selected_rows.setter
    def selected_rows(self, value):
        if self.name == "catalog":
            print(".")
        self._selected_rows = value

    def getSelection(self) -> List[List[int]]:
        if len(self.selected_rows) > 0:
            return [ list(x) for x in zip(*self.selected_rows) ]
        return [[], [], []]

    def findRow(self, searchStr: str  ):
        if self.selectedColumn == -1:
            Task.showMessage("Workflow violation", "", "Must select a table column before this operation can be applied", QMessageBox.Warning )
        else:
            if not searchStr.startswith(self._current_search_str): self._search_row = 0
            print( f"FIND: {searchStr}")
            rows = self.table.rowCount()
            for iRow in range( self._search_row, rows ):
                item: QTableWidgetItem = self.table.item( iRow, self.selectedColumn )
                try:
                    if item.text().startswith( searchStr ):
                        pid_item: QTableWidgetItem = self.table.item(iRow, self._index_column)
                        try:
                            pid = int(pid_item.text())
                            srows = [(iRow,pid,0)]
                            self.selectRowsByIndex( srows, False )
                            self._current_search_str = searchStr
                            self._search_row = iRow
                            event = dict(event="pick", type="directory", rows=srows, mark=False)
                            self.submitEvent(event, EventMode.Gui)
                        except: pass
                        break
                except: break

    def selectRows(self, searchStr: str  ):
        if self.selectedColumn == -1:
            Task.showMessage("Workflow violation", "", "Must select a table column before this operation can be applied", QMessageBox.Warning )
        else:
            print( f"SELECT: {searchStr}")
            rows = self.table.rowCount()
            srows: List[Tuple] = []
            for iRow in range( rows ):
                item: QTableWidgetItem = self.table.item( iRow, self.selectedColumn )
                try:
                    match: re.Match = re.match( searchStr, item.text() )
                    if (match is not None):
                        pid_item: QTableWidgetItem = self.table.item(iRow, self._index_column)
                        try:    srows.append( (iRow, int(pid_item.text()), 0) )
                        except: pass
                except: break
            self.selectRowsByIndex( srows, False )
            if (self.name == "catalog"):
                event = dict( event="pick", type="directory", rows=srows, mark = False )
                self.submitEvent( event, EventMode.Gui )

    def activate(self, enable: bool ):
        self._enabled = enable
 #       print( f" DirectoryWidget[{self.name}] enabled = {enable}")

    def onCellPressed(self, row, col ):
        mark = self.table.current_button == Qt.RightButton
        if self.name in ["catalog", labelsManager.selectedLabel]:
            self.selectRow( row, mark )
            self.update()

    def recordSelection( self, reset = True ):
        self.selected_rows = [ ]
        cid = labelsManager.selectedClass
        for index in self.table.selectionModel().selectedIndexes():
            row = index.row()
            pid_item = self.table.item( row, self._index_column )
            try: self.selected_rows.append( ( row, int(pid_item.text()), cid) )
            except: pass
        return cid

    def itemSelectionChanged(self):
        cid = self.recordSelection()
        mark = (cid > 0)
        if (self.name not in ["catalog", labelsManager.selectedLabel]) and (cid > 0):
            self.clearRowsByPID([r[1] for r in self.selected_rows])
            event = dict( event="pick", type="directory", rows=self.selected_rows, mark = True )
            self.submitEvent( event, EventMode.Gui )
        else:
            print( f"Selected srows: {self.selected_rows}")
            self.selectRowsByIndex(self.selected_rows, mark)
            if (self.name == "catalog"):
                event = dict(event="pick", type="directory", rows=self.selected_rows, mark=mark )
                self.submitEvent(event, EventMode.Gui)

    def setSelectedColumnHeaderColor(self, color ):
        header = QTableWidgetItem(self.col_headers[self.selectedColumn])
        header.setBackground(QColor( color ))
        self.table.setHorizontalHeaderItem(self.selectedColumn, header)

    def onColumnSelection( self, col  ):
        self.table.sortItems(col)
        self.table.clearSelection()
        if self.selectedColumn >= 0: self.setSelectedColumnHeaderColor( "white" )
        self.selectedColumn = col
        self.setSelectedColumnHeaderColor( "yellow" )
        self.update()

    def selectRow( self, row: int, rightClick: bool ):
 #       print(f" DirectoryWidget[{self.name}] selectRow[{row}], enabled: {self._enabled}")
        if self._enabled and (row >= 0):
            table_item: QTableWidgetItem = self.table.item( row, self._index_column )
            self._selected_row = row
            mark = rightClick and self.pick_enabled
            self.clear_transients()
            event = dict( event="pick", type="directory", rows=[ (row, int( table_item.text() ), 0) ], mark = mark )
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

    def clear_transients(self):
        brush = self.getBrush()
        for row in self._transients:
            item: QTableWidgetItem = self.table.item(row, 0)
            item.setBackground( brush )
        self._transients = []

    def clear_table( self, reset_catalog = False ):
        self.table.clearSelection()
        self._selected_row = -1
        self._head_row = 0
        if (self.name == "catalog") and not reset_catalog:
            [srows, spids, scids] = self.getSelection()
            brush = self.getBrush()
            for row in (self._marked_rows + srows):
                item: QTableWidgetItem = self.table.item(row, 0)
                item.setBackground( brush )
        else:
            for column, (cid, row_data) in enumerate(self.col_data.items()):
                for row, value in enumerate(row_data):
                    self.table.setItem( row, column, QTableWidgetItem( "" ) )
            for key in self.col_data.keys():
                self.col_data[key] = []
        self.selected_rows = []
        self._marked_rows = []
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
        se1 = self._key_state_modifiers != None
        return se1

    def processEvent( self, event: Dict ):
        super().processEvent(event)
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
        if event.get('event') == 'pick':
            etype = event.get('type')
            if etype in [ 'vtkpoint', 'directory', 'plot', 'graph' ]:
                cid = labelsManager.selectedClass
                self.pick_enabled = (cid>0)
                mark = event.get('mark', False )
                if (self.name == "catalog"):
                    rspecs = event.get('rows', [])
                    self.selectRowsByIndex( rspecs, True )
                #     multi = self.shiftEnabled()
                #     if multi and mark and (cid>0):
                #         pids = event.get('pids',[])
                #         self.sequence_bounds.append(pids[0])
                #         if len( self.sequence_bounds ) == 2:
                #             self.sequence_bounds.sort()
                #             self.markRowSequence( *self.sequence_bounds )
                #             self.sequence_bounds = []
                #     elif not multi:
                #         pids = event.get('pids',[])
                #         self.selectRowsByPID( pids, mark )
                #         rspecs = event.get('rows', [])
                #         self.selectRowsByIndex(rspecs, event.get('mark', mark))
                if (self.name == labelsManager.selectedLabel) and self.pick_enabled:
                    for pid in event.get('pids',[]): self.addRow( pid )
                    rspecs = event.get('rows',[])
                    for rs in rspecs: self.addRow(rs[1])
                    self.update()
#                 elif (self.name != "catalog"):
#                     pids = event.get('pids',[])
# #                    mark = self.pick_enabled and (cid > 0)
#                     self.selectRowsByPID(pids, mark)
#                     rspecs = event.get('rows',[])
#                     self.selectRowsByIndex( rspecs, mark )

        elif event.get('event') == 'gui':
            if event.get('type') == 'clear':       self.clear_table( False )
            elif event.get('type') == 'keyPress':      self.setKeyState( event )
            elif event.get('type') == 'keyRelease':  self.releaseKeyState()
            elif event.get('type') == 'reset':       self.clear_table( True )
            elif event.get('type') == 'mark':        self.markSelectedRows()
            elif event.get('type') == 'undo':        self.undo( event )
            elif event.get('type') == 'spread':
                labels: xa.Dataset = event.get('labels')
                self.addExtendedLabels( labels )
                self.build_table.emit()

    def addRow( self, pid: int, distance: float = 0.0 ):
        item = self.getItemByPID(pid)
        self.current_pid = pid
        if item is None:
            plot_metadata = dataEventHandler.getMetadata()
            row_data = []

            for mdata_array in plot_metadata:
                col_name = mdata_array.attrs['name']
                cval = mdata_array.values[pid]
                self.col_data[ col_name ].append( tostr(cval) )
                row_data.append( cval )

            self.col_data['distance'].append( distance )
            row_data.append(0.0)
            self.col_data['index'].append(pid)
            row_data.append( pid )
            self.setRowData(row_data)
        else:
            self.selectRowsByPID( [pid], False)

    def markSelectedRows(self):
        self.enablePick()
        self.clear_transients()
        cid = self.recordSelection()
        if len(self.selected_rows) > 0:
            if cid > 0:
                if self.name not in [ "catalog", labelsManager.selectedLabel ]  and (cid > 0):
                    self.clearRowsByPID( [ r[1] for r in self.selected_rows ] )

            if  (self.name == "catalog"):
                event = dict(event="pick", type="directory", rows=self.selected_rows, mark=True )
                self.submitEvent(event, EventMode.Gui)
                self._marked_rows = self._marked_rows + self.selected_rows
                labelsManager.addAction("select", "directory", [ r[1] for r in self.selected_rows ], cid, name=self.name)

            # else:
            #     marker = labelsManager.currentMarker
            #     if marker is not None:
            #         selection = self.selectRowsByPID(marker.pids, True)
            #         rows = [ (row, pid, cid) for (pid,row) in selection.items() ]

            # except Exception as err:
            #     if marker is None:
            #         Task.showMessage("Workflow violation", "", "Must select a point before this operation can be applied", QMessageBox.Warning )
            #     else: print( f"Row selection error: {err}")
        self.releasePick()

    def addExtendedLabels(self, labels: xa.Dataset ):
        labels, distance = labelsManager.getSortedLabels(labels)
        for itemRef, d in zip(labels, distance):
            label = labelsManager.labels[ itemRef[1] ]
            if label == self.name:
                self.addRow( itemRef[0], d )
                self.update()
        try:
            self.sort_column = self.col_headers.index('distance')
            self.table.sortItems(self.sort_column)
            self.update()
        except Exception as err:
            print( f"DirectoryWidget.addExtendedLabels Exception: {err} ")
            print( f"Col headers: {self.col_headers}" )

    def undo(self, event: Dict ):
        if event.get('atype') == 'select':
            pids = event.get('pids')
            if (self.name == "catalog"):    self.unmarkRowsByPID(pids)
            else:                           self.clearRowsByPID(pids)

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

    def getItemByPID(self, pid: int) -> Optional[QTableWidgetItem]:
        rows = self.table.rowCount()
        for iRow in range( rows ):
            item: QTableWidgetItem = self.table.item( iRow, self._index_column )
            try:
                if pid == int(item.text()): return item
            except: break
        return None

    def getRowItems(self, rows: List[int], cid: int ) -> List[Tuple]:
        rItems = []
        for iRow in rows:
            item: QTableWidgetItem = self.table.item( iRow, self._index_column )
            try:
                pid = int(item.text())
                rItems.append( ( iRow, pid, cid ) )
            except: pass
        return rItems

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

    def selectRowsByPID(self, pids: List[int], mark: bool) -> Dict[int,int]:
        rows = self.table.rowCount()
        selection = OrderedDict()
        mark_item: QTableWidgetItem = None
        cid = labelsManager.selectedClass if mark else 0
        for iRow in range( rows ):
            item: QTableWidgetItem = self.table.item( iRow, self._index_column )
            if item == None: break
            try:
                pid = int( item.text() )
                if pid in pids:
                    selection[pid] = iRow
                    mark_item = self.table.item( iRow, 0  )
                    mark_item.setBackground( self.getBrush(cid) )
                    if (cid>0): self._marked_rows.append( iRow )
                    else: self.selected_rows.append( (iRow, pid, cid) )
                    if cid == 0: self._transients.append(iRow)
                if cid > 0: labelsManager.addAction("select", "directory", pids, cid, name=self.name )
            except: break
        if mark_item: self.table.scrollToItem(mark_item)
        self.update()
        return selection

    def getBrush(self, cid: int = -1 ) -> QBrush:
        return self._brushes.setdefault( cid, self._createBrush(cid) )

    def _createBrush( self, cid: int ) -> QBrush:
        color = labelsManager.colors[ cid ] if cid >= 0 else (1,1,1)
        qcolor = [int(color[ic] * 255.99) for ic in range(3)]
        return QBrush(QColor(*qcolor))

    def selectRowsByIndex(self, rspecs: List[Tuple], mark: bool ):
        if len( rspecs ) > 0:
            self.clear_transients()
            cid = labelsManager.selectedClass if mark else 0
            pids = []
            brush = self.getBrush( cid )
            for rspec in rspecs:
                iRow = rspec[0]
                mark_item: QTableWidgetItem = self.table.item(iRow, 0)
                mark_item.setBackground( brush )
                if cid == 0:
                    self._transients.append( iRow )
                else:
                    pids.append( rspec[1] )
                    self._marked_rows.append(rspec[0])
            self._selected_row = rspecs[ len(rspecs) // 2 ][0]
            scroll_item = self.table.item( self._selected_row, 0)
            self.table.scrollToItem( scroll_item )
            if len(pids) > 0: labelsManager.addAction( "select", "directory", pids, cid, name=self.name )
            self.update()

    def unmarkRowsByPID(self, pids: List[int]):
 #       self.table.clearSelection()
        unmarked_rows = []
        for iRow in self._marked_rows:
            item = self.table.item(iRow, self._index_column )
            if item == None: break
            if int(item.text()) in pids:
                if self._selected_row == iRow: self._selected_row = -1
                mark_item = self.table.item( iRow, 0 )
                mark_item.setBackground( self.getBrush() )
                unmarked_rows.append( iRow )
        for iRow in unmarked_rows: self._marked_rows.remove(iRow)
        self.update()

    def clearRowsByPID(self, pids: List[int] ):
        rows = self.table.rowCount()
 #       self.table.clearSelection()
        self._selected_row, pid = -1, -1
        for iRow in range(rows):
            item: QTableWidgetItem = self.table.item( iRow, self._index_column )
            if item == None: break
            try:
                pid = int(item.text())
                if item.text() and (pid in pids):
                    for column in range(self.table.columnCount()):
                        self.table.setItem( iRow, column, QTableWidgetItem( "" ) )
                    self._head_row = iRow
                    break
            except ValueError: pass
            except Exception as err:
                print( f"clearRowByPID error, r={iRow}, p={pid}, index col = {self._index_column}: {err}")
                traceback.print_exc(50)
        self.update()






