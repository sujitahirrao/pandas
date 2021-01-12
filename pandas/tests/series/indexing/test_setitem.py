from datetime import date

import numpy as np
import pytest

from pandas import (
    DatetimeIndex,
    Index,
    MultiIndex,
    NaT,
    Series,
    Timestamp,
    date_range,
    period_range,
)
import pandas._testing as tm
from pandas.core.indexing import IndexingError

from pandas.tseries.offsets import BDay


class TestSetitemDT64Values:
    def test_setitem_none_nan(self):
        series = Series(date_range("1/1/2000", periods=10))
        series[3] = None
        assert series[3] is NaT

        series[3:5] = None
        assert series[4] is NaT

        series[5] = np.nan
        assert series[5] is NaT

        series[5:7] = np.nan
        assert series[6] is NaT

    def test_setitem_multiindex_empty_slice(self):
        # https://github.com/pandas-dev/pandas/issues/35878
        idx = MultiIndex.from_tuples([("a", 1), ("b", 2)])
        result = Series([1, 2], index=idx)
        expected = result.copy()
        result.loc[[]] = 0
        tm.assert_series_equal(result, expected)

    def test_setitem_with_string_index(self):
        # GH#23451
        ser = Series([1, 2, 3], index=["Date", "b", "other"])
        ser["Date"] = date.today()
        assert ser.Date == date.today()
        assert ser["Date"] == date.today()

    def test_setitem_with_different_tz_casts_to_object(self):
        # GH#24024
        ser = Series(date_range("2000", periods=2, tz="US/Central"))
        ser[0] = Timestamp("2000", tz="US/Eastern")
        expected = Series(
            [
                Timestamp("2000-01-01 00:00:00-05:00", tz="US/Eastern"),
                Timestamp("2000-01-02 00:00:00-06:00", tz="US/Central"),
            ],
            dtype=object,
        )
        tm.assert_series_equal(ser, expected)

    def test_setitem_tuple_with_datetimetz_values(self):
        # GH#20441
        arr = date_range("2017", periods=4, tz="US/Eastern")
        index = [(0, 1), (0, 2), (0, 3), (0, 4)]
        result = Series(arr, index=index)
        expected = result.copy()
        result[(0, 1)] = np.nan
        expected.iloc[0] = np.nan
        tm.assert_series_equal(result, expected)


class TestSetitemPeriodDtype:
    @pytest.mark.parametrize("na_val", [None, np.nan])
    def test_setitem_na_period_dtype_casts_to_nat(self, na_val):
        ser = Series(period_range("2000-01-01", periods=10, freq="D"))

        ser[3] = na_val
        assert ser[3] is NaT

        ser[3:5] = na_val
        assert ser[4] is NaT


class TestSetitemScalarIndexer:
    def test_setitem_negative_out_of_bounds(self):
        ser = Series(tm.rands_array(5, 10), index=tm.rands_array(10, 10))

        msg = "index -11 is out of bounds for axis 0 with size 10"
        with pytest.raises(IndexError, match=msg):
            ser[-11] = "foo"


class TestSetitemSlices:
    def test_setitem_slice_float_raises(self, datetime_series):
        msg = (
            "cannot do slice indexing on DatetimeIndex with these indexers "
            r"\[{key}\] of type float"
        )
        with pytest.raises(TypeError, match=msg.format(key=r"4\.0")):
            datetime_series[4.0:10.0] = 0

        with pytest.raises(TypeError, match=msg.format(key=r"4\.5")):
            datetime_series[4.5:10.0] = 0


class TestSetitemBooleanMask:
    def test_setitem_boolean(self, string_series):
        mask = string_series > string_series.median()

        # similar indexed series
        result = string_series.copy()
        result[mask] = string_series * 2
        expected = string_series * 2
        tm.assert_series_equal(result[mask], expected[mask])

        # needs alignment
        result = string_series.copy()
        result[mask] = (string_series * 2)[0:5]
        expected = (string_series * 2)[0:5].reindex_like(string_series)
        expected[-mask] = string_series[mask]
        tm.assert_series_equal(result[mask], expected[mask])

    def test_setitem_boolean_corner(self, datetime_series):
        ts = datetime_series
        mask_shifted = ts.shift(1, freq=BDay()) > ts.median()

        msg = (
            r"Unalignable boolean Series provided as indexer \(index of "
            r"the boolean Series and of the indexed object do not match"
        )
        with pytest.raises(IndexingError, match=msg):
            ts[mask_shifted] = 1

        with pytest.raises(IndexingError, match=msg):
            ts.loc[mask_shifted] = 1

    def test_setitem_boolean_different_order(self, string_series):
        ordered = string_series.sort_values()

        copy = string_series.copy()
        copy[ordered > 0] = 0

        expected = string_series.copy()
        expected[expected > 0] = 0

        tm.assert_series_equal(copy, expected)

    @pytest.mark.parametrize("func", [list, np.array, Series])
    def test_setitem_boolean_python_list(self, func):
        # GH19406
        ser = Series([None, "b", None])
        mask = func([True, False, True])
        ser[mask] = ["a", "c"]
        expected = Series(["a", "b", "c"])
        tm.assert_series_equal(ser, expected)

    @pytest.mark.parametrize("value", [None, NaT, np.nan])
    def test_setitem_boolean_td64_values_cast_na(self, value):
        # GH#18586
        series = Series([0, 1, 2], dtype="timedelta64[ns]")
        mask = series == series[0]
        series[mask] = value
        expected = Series([NaT, 1, 2], dtype="timedelta64[ns]")
        tm.assert_series_equal(series, expected)

    def test_setitem_boolean_nullable_int_types(self, any_nullable_numeric_dtype):
        # GH: 26468
        ser = Series([5, 6, 7, 8], dtype=any_nullable_numeric_dtype)
        ser[ser > 6] = Series(range(4), dtype=any_nullable_numeric_dtype)
        expected = Series([5, 6, 2, 3], dtype=any_nullable_numeric_dtype)
        tm.assert_series_equal(ser, expected)

        ser = Series([5, 6, 7, 8], dtype=any_nullable_numeric_dtype)
        ser.loc[ser > 6] = Series(range(4), dtype=any_nullable_numeric_dtype)
        tm.assert_series_equal(ser, expected)

        ser = Series([5, 6, 7, 8], dtype=any_nullable_numeric_dtype)
        loc_ser = Series(range(4), dtype=any_nullable_numeric_dtype)
        ser.loc[ser > 6] = loc_ser.loc[loc_ser > 1]
        tm.assert_series_equal(ser, expected)


class TestSetitemViewCopySemantics:
    def test_setitem_invalidates_datetime_index_freq(self):
        # GH#24096 altering a datetime64tz Series inplace invalidates the
        #  `freq` attribute on the underlying DatetimeIndex

        dti = date_range("20130101", periods=3, tz="US/Eastern")
        ts = dti[1]
        ser = Series(dti)
        assert ser._values is not dti
        assert ser._values._data.base is not dti._data._data.base
        assert dti.freq == "D"
        ser.iloc[1] = NaT
        assert ser._values.freq is None

        # check that the DatetimeIndex was not altered in place
        assert ser._values is not dti
        assert ser._values._data.base is not dti._data._data.base
        assert dti[1] == ts
        assert dti.freq == "D"

    def test_dt64tz_setitem_does_not_mutate_dti(self):
        # GH#21907, GH#24096
        dti = date_range("2016-01-01", periods=10, tz="US/Pacific")
        ts = dti[0]
        ser = Series(dti)
        assert ser._values is not dti
        assert ser._values._data.base is not dti._data._data.base
        assert ser._mgr.blocks[0].values is not dti
        assert ser._mgr.blocks[0].values._data.base is not dti._data._data.base

        ser[::3] = NaT
        assert ser[0] is NaT
        assert dti[0] == ts


class TestSetitemCallable:
    def test_setitem_callable_key(self):
        # GH#12533
        ser = Series([1, 2, 3, 4], index=list("ABCD"))
        ser[lambda x: "A"] = -1

        expected = Series([-1, 2, 3, 4], index=list("ABCD"))
        tm.assert_series_equal(ser, expected)

    def test_setitem_callable_other(self):
        # GH#13299
        inc = lambda x: x + 1

        ser = Series([1, 2, -1, 4])
        ser[ser < 0] = inc

        expected = Series([1, 2, inc, 4])
        tm.assert_series_equal(ser, expected)


@pytest.mark.parametrize(
    "obj,expected,key",
    [
        (
            # these induce dtype changes
            Series([2, 3, 4, 5, 6, 7, 8, 9, 10]),
            Series([np.nan, 3, np.nan, 5, np.nan, 7, np.nan, 9, np.nan]),
            slice(None, None, 2),
        ),
        (
            # gets coerced to float, right?
            Series([True, True, False, False]),
            Series([np.nan, 1, np.nan, 0]),
            slice(None, None, 2),
        ),
        (
            # these induce dtype changes
            Series(np.arange(10)),
            Series([np.nan, np.nan, np.nan, np.nan, np.nan, 5, 6, 7, 8, 9]),
            slice(None, 5),
        ),
        (
            # changes dtype GH#4463
            Series([1, 2, 3]),
            Series([np.nan, 2, 3]),
            0,
        ),
        (
            # changes dtype GH#4463
            Series([False]),
            Series([np.nan]),
            0,
        ),
        (
            # changes dtype GH#4463
            Series([False, True]),
            Series([np.nan, 1.0]),
            0,
        ),
    ],
)
class TestSetitemCastingEquivalents:
    """
    Check each of several methods that _should_ be equivalent to `obj[key] = np.nan`

    We assume that
        - obj.index is the default Index(range(len(obj)))
        - the setitem does not expand the obj
    """

    def test_int_key(self, obj, key, expected, indexer_sli):
        if not isinstance(key, int):
            return

        obj = obj.copy()
        indexer_sli(obj)[key] = np.nan
        tm.assert_series_equal(obj, expected)

    def test_slice_key(self, obj, key, expected, indexer_si):
        # Note: no .loc because that handles slice edges differently
        obj = obj.copy()
        indexer_si(obj)[key] = np.nan
        tm.assert_series_equal(obj, expected)

    def test_intlist_key(self, obj, key, expected, indexer_sli):
        ilkey = list(range(len(obj)))[key]

        obj = obj.copy()
        indexer_sli(obj)[ilkey] = np.nan
        tm.assert_series_equal(obj, expected)

    def test_mask_key(self, obj, key, expected, indexer_sli):
        # setitem with boolean mask
        mask = np.zeros(obj.shape, dtype=bool)
        mask[key] = True

        obj = obj.copy()
        indexer_sli(obj)[mask] = np.nan
        tm.assert_series_equal(obj, expected)

    def test_series_where(self, obj, key, expected):
        mask = np.zeros(obj.shape, dtype=bool)
        mask[key] = True

        obj = obj.copy()
        res = obj.where(~mask, np.nan)
        tm.assert_series_equal(res, expected)

    def test_index_where(self, obj, key, expected, request):
        mask = np.zeros(obj.shape, dtype=bool)
        mask[key] = True

        if obj.dtype == bool and not mask.all():
            # When mask is all True, casting behavior does not apply
            msg = "Index/Series casting behavior inconsistent GH#38692"
            mark = pytest.mark.xfail(reason=msg)
            request.node.add_marker(mark)

        res = Index(obj).where(~mask, np.nan)
        tm.assert_index_equal(res, Index(expected))

    @pytest.mark.xfail(reason="Index/Series casting behavior inconsistent GH#38692")
    def test_index_putmask(self, obj, key, expected):
        mask = np.zeros(obj.shape, dtype=bool)
        mask[key] = True

        res = Index(obj).putmask(mask, np.nan)
        tm.assert_index_equal(res, Index(expected))


class TestSetitemWithExpansion:
    def test_setitem_empty_series(self):
        # GH#10193
        key = Timestamp("2012-01-01")
        series = Series(dtype=object)
        series[key] = 47
        expected = Series(47, [key])
        tm.assert_series_equal(series, expected)

    def test_setitem_empty_series_datetimeindex_preserves_freq(self):
        # GH#33573 our index should retain its freq
        series = Series([], DatetimeIndex([], freq="D"), dtype=object)
        key = Timestamp("2012-01-01")
        series[key] = 47
        expected = Series(47, DatetimeIndex([key], freq="D"))
        tm.assert_series_equal(series, expected)
        assert series.index.freq == expected.index.freq


def test_setitem_scalar_into_readonly_backing_data():
    # GH#14359: test that you cannot mutate a read only buffer

    array = np.zeros(5)
    array.flags.writeable = False  # make the array immutable
    series = Series(array)

    for n in range(len(series)):
        msg = "assignment destination is read-only"
        with pytest.raises(ValueError, match=msg):
            series[n] = 1

        assert array[n] == 0


def test_setitem_slice_into_readonly_backing_data():
    # GH#14359: test that you cannot mutate a read only buffer

    array = np.zeros(5)
    array.flags.writeable = False  # make the array immutable
    series = Series(array)

    msg = "assignment destination is read-only"
    with pytest.raises(ValueError, match=msg):
        series[1:3] = 1

    assert not array.any()


@pytest.mark.parametrize(
    "key", [0, slice(0, 1), [0], np.array([0]), range(1)], ids=type
)
@pytest.mark.parametrize("dtype", [complex, int, float])
def test_setitem_td64_into_complex(key, dtype, indexer_sli):
    # timedelta64 should not be treated as integers
    arr = np.arange(5).astype(dtype)
    ser = Series(arr)
    td = np.timedelta64(4, "ns")

    indexer_sli(ser)[key] = td
    assert ser.dtype == object
    assert arr[0] == 0  # original array is unchanged

    if not isinstance(key, int) and not (
        indexer_sli is tm.loc and isinstance(key, slice)
    ):
        # skip key/indexer_sli combinations that will have mismatched lengths
        ser = Series(arr)
        indexer_sli(ser)[key] = np.full((1,), td)
        assert ser.dtype == object
        assert arr[0] == 0  # original array is unchanged
