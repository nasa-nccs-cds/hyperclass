from collections import OrderedDict, MutableSet
from typing import List, Union, Dict, Callable, Tuple, Optional

class ItemContainer( OrderedDict ):

    def add(self, key: int, value: Tuple ):
        self[key] = value

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

    def __sub__(self, other: "ItemContainer" ):
        rv = ItemContainer( self )
        for key, value in other.items(): del rv[key]
        return rv

    def __isub__(self, other: "ItemContainer" ):
        for key, value in other.items(): del self[key]

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
