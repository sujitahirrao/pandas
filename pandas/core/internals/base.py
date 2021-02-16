"""
Base class for the internal managers. Both BlockManager and ArrayManager
inherit from this class.
"""
from typing import (
    List,
    TypeVar,
)

from pandas.errors import AbstractMethodError

from pandas.core.base import PandasObject
from pandas.core.indexes.api import (
    Index,
    ensure_index,
)

T = TypeVar("T", bound="DataManager")


class DataManager(PandasObject):

    # TODO share more methods/attributes

    axes: List[Index]

    @property
    def items(self) -> Index:
        raise AbstractMethodError(self)

    def __len__(self) -> int:
        return len(self.items)

    @property
    def ndim(self) -> int:
        return len(self.axes)

    def reindex_indexer(
        self: T,
        new_axis,
        indexer,
        axis: int,
        fill_value=None,
        allow_dups: bool = False,
        copy: bool = True,
        consolidate: bool = True,
        only_slice: bool = False,
    ) -> T:
        raise AbstractMethodError(self)

    def reindex_axis(
        self,
        new_index,
        axis: int,
        method=None,
        limit=None,
        fill_value=None,
        copy: bool = True,
        consolidate: bool = True,
        only_slice: bool = False,
    ):
        """
        Conform data manager to new index.
        """
        new_index = ensure_index(new_index)
        new_index, indexer = self.axes[axis].reindex(
            new_index, method=method, limit=limit
        )

        return self.reindex_indexer(
            new_index,
            indexer,
            axis=axis,
            fill_value=fill_value,
            copy=copy,
            consolidate=consolidate,
            only_slice=only_slice,
        )

    def _equal_values(self: T, other: T) -> bool:
        """
        To be implemented by the subclasses. Only check the column values
        assuming shape and indexes have already been checked.
        """
        raise AbstractMethodError(self)

    def equals(self, other: object) -> bool:
        """
        Implementation for DataFrame.equals
        """
        if not isinstance(other, DataManager):
            return False

        self_axes, other_axes = self.axes, other.axes
        if len(self_axes) != len(other_axes):
            return False
        if not all(ax1.equals(ax2) for ax1, ax2 in zip(self_axes, other_axes)):
            return False

        return self._equal_values(other)
