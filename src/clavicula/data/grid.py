"""
A minimal strongly-typed 2D grid that emits mutation events.

No external deps required. If you want async-friendly dispatch or
weak-ref listeners, swap the plain callback list for `blinker.Signal`.
"""

from dataclasses import dataclass
from typing import Callable, Generic, List, Tuple, TypeVar
from enum import Enum, auto

T = TypeVar("T")


class TileType(Enum):
    EMPTY = auto()
    MUTABLE_PERMANENT = auto()
    MUTABLE_DECAY = auto()
    IMMUTABLE = auto()


@dataclass(frozen=True, slots=True)
class MutationEvent(Generic[T]):
    row: int
    col: int
    old: T
    new: T


class TypedGrid(Generic[T]):
    def __init__(self, rows: int, cols: int, default: T, dtype: type):
        self._dtype = dtype
        self._rows, self._cols = rows, cols
        self._data: List[List[T]] = [[default] * cols for _ in range(rows)]
        self._listeners: List[Callable[[MutationEvent[T]], None]] = []

    @property
    def shape(self) -> Tuple[int, int]:
        return self._rows, self._cols

    def subscribe(self, fn: Callable[[MutationEvent[T]], None]) -> None:
        self._listeners.append(fn)

    def unsubscribe(self, fn: Callable[[MutationEvent[T]], None]) -> None:
        self._listeners.remove(fn)

    def __getitem__(self, pos: Tuple[int, int]) -> T:
        r, c = pos
        return self._data[r][c]

    def __setitem__(self, pos: Tuple[int, int], value: T) -> None:
        if not isinstance(value, self._dtype):
            raise TypeError(
                f"Expected {self._dtype.__name__}, got {type(value).__name__}"
            )
        r, c = pos
        old = self._data[r][c]
        if old == value:
            return
        self._data[r][c] = value
        event = MutationEvent(r, c, old, value)
        for fn in self._listeners:
            fn(event)
