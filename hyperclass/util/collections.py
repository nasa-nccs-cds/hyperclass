from collections import OrderedDict, MutableSet
from typing import List, Union, Dict, Callable, Tuple, Optional

class RS:

    def __init__(self, row: int, pid: int, mid: int, cid: int = -1 ):
        self._pid = pid
        self._row = row
        self._mid = mid
        self._cid = mid if cid == -1 else cid
        print( f"new ROW: pid={self._pid} row={self._row} mid={self._mid} cid={self._cid} " )

    @property
    def pid(self):
        return self._pid

    @property
    def row(self):
        return self._row

    @property
    def mid(self):
        return self._mid

    @property
    def cid(self):
        return self._cid

    def mark( self, cid: int ) -> "RS":
        self._cid = cid
        return self

    def reset(self):
        self._cid = self.mid

class ItemContainer( OrderedDict ):

    def __init__( self, items: List[RS] = None ):
        OrderedDict.__init__( self )
        if items is not None:
            for item in items: self.add( item )

    def add(self, item: RS ):
        self[item.pid] = item

    def size(self) -> int:
        return len(self.keys())

    def ids(self) -> List[int]:
        return list(self.keys())

    def __add__(self, other: "ItemContainer" ):
        rv = ItemContainer( self )
        for key, value in other.items(): rv[key] = value
        return rv

    def __iadd__(self, other: "ItemContainer" ):
        for key, value in other.items(): self[key] = value
        return self

    def __sub__(self, pids: List ):
        rv = ItemContainer( self )
        for pid in pids:
            try: del rv[pid]
            except: pass
        return rv

    def __isub__(self, pids: List ):
        for pid in pids:
            try: del self[pid]
            except: pass
        return self

    def __iter__(self):
        return self.values().__iter__()

class OrderedSet( OrderedDict, MutableSet):

    def update(self, *args, **kwargs):
        if kwargs:
            raise TypeError("update() takes no keyword arguments")

        for s in args:
            for e in s:
                 self.add(e)

    def add(self, elem):
        self[elem] = None

    def discard(self, elem):
        self.pop(elem, None)

    def size(self):
        return len(self.keys())

    def extract(self, last=True ):
        ival = self.popitem(last)
        return None if ival is None else ival[0]

    def __le__(self, other):
        return all(e in other for e in self)

    def __lt__(self, other):
        return self <= other and self != other

    def __ge__(self, other):
        return all(e in self for e in other)

    def __gt__(self, other):
        return self >= other and self != other

    def __repr__(self):
        return 'OrderedSet([%s])' % (', '.join(map(repr, self.keys())))

    def __str__(self):
        return '{%s}' % (', '.join(map(repr, self.keys())))

    def difference(self, other): return self.__sub__( other )
    def difference_update(self, other):  self.__isub__( other )
    def intersection(self, other): return self.__and__( other )
    def intersection_update(self, other): self.__iand__( other )
    def issubset(self, other): return self.__le__( other )
    def issuperset(self, other): return self.__ge__( other )
    def symmetric_difference(self, other): return self.__xor__( other )
    def symmetric_difference_update(self, other): return self.__ixor__( other )
    def union(self, other): return self.__or__( other )
