import sys
import datetime
import re
import os
import logging
import warnings
import time
from ast import literal_eval
from decimal import Decimal, localcontext
from collections import namedtuple
from ordered_set import OrderedSet
from threading import Timer


class np_type:
    pass


try:
    import numpy as np
except ImportError:
    np = None
    np_ndarray = np_type
    np_bool_ = np_type
    np_int8 = np_type
    np_int16 = np_type
    np_int32 = np_type
    np_int64 = np_type
    np_uint8 = np_type
    np_uint16 = np_type
    np_uint32 = np_type
    np_uint64 = np_type
    np_intp = np_type
    np_uintp = np_type
    np_float32 = np_type
    np_float64 = np_type
    np_float_ = np_type
    np_complex64 = np_type
    np_complex128 = np_type
    np_complex_ = np_type
else:
    np_ndarray = np.ndarray
    np_bool_ = np.bool_
    np_int8 = np.int8
    np_int16 = np.int16
    np_int32 = np.int32
    np_int64 = np.int64
    np_uint8 = np.uint8
    np_uint16 = np.uint16
    np_uint32 = np.uint32
    np_uint64 = np.uint64
    np_intp = np.intp
    np_uintp = np.uintp
    np_float32 = np.float32
    np_float64 = np.float64
    np_float_ = np.float_
    np_complex64 = np.complex64
    np_complex128 = np.complex128
    np_complex_ = np.complex_

numpy_numbers = (
    np_int8, np_int16, np_int32, np_int64, np_uint8,
    np_uint16, np_uint32, np_uint64, np_intp, np_uintp,
    np_float32, np_float64, np_float_, np_complex64,
    np_complex128, np_complex_, )

logger = logging.getLogger(__name__)

py_major_version = sys.version_info.major
py_minor_version = sys.version_info.minor

py_current_version = Decimal("{}.{}".format(py_major_version, py_minor_version))

py2 = py_major_version == 2
py3 = py_major_version == 3
py4 = py_major_version == 4

MINIMUM_PY_DICT_TYPE_SORTED = Decimal('3.6')
DICT_IS_SORTED = py_current_version >= MINIMUM_PY_DICT_TYPE_SORTED

if py4:
    logger.warning('Python 4 is not supported yet. Switching logic to Python 3.')  # pragma: no cover
    py3 = True  # pragma: no cover

if py2:  # pragma: no cover
    sys.exit('Python 2 is not supported anymore. The last version of DeepDiff that supported Py2 was 3.3.0')

pypy3 = py3 and hasattr(sys, "pypy_translation_info")

strings = (str, bytes)  # which are both basestring
unicode_type = str
bytes_type = bytes
only_numbers = (int, float, complex, Decimal) + numpy_numbers
datetimes = (datetime.datetime, datetime.date, datetime.timedelta, datetime.time)
numbers = only_numbers + datetimes
booleans = (bool, np_bool_)

IndexedHash = namedtuple('IndexedHash', 'indexes item')

current_dir = os.path.dirname(os.path.abspath(__file__))

ID_PREFIX = '!>*id'

ZERO_DECIMAL_CHARACTERS = set("-0.")

KEY_TO_VAL_STR = "{}:{}"

TREE_VIEW = 'tree'
TEXT_VIEW = 'text'
DELTA_VIEW = '_delta'


def short_repr(item, max_length=15):
    """Short representation of item if it is too long"""
    item = repr(item)
    if len(item) > max_length:
        item = '{}...{}'.format(item[:max_length - 3], item[-1])
    return item


class ListItemRemovedOrAdded:  # pragma: no cover
    """Class of conditions to be checked"""
    pass


class OtherTypes:
    def __repr__(self):
        return "Error: {}".format(self.__class__.__name__)  # pragma: no cover

    __str__ = __repr__


class Skipped(OtherTypes):
    pass


class Unprocessed(OtherTypes):
    pass


class NotHashed(OtherTypes):
    pass


class NotPresent:  # pragma: no cover
    """
    In a change tree, this indicated that a previously existing object has been removed -- or will only be added
    in the future.
    We previously used None for this but this caused problem when users actually added and removed None. Srsly guys? :D
    """
    def __repr__(self):
        return 'not present'  # pragma: no cover

    __str__ = __repr__


unprocessed = Unprocessed()
skipped = Skipped()
not_hashed = NotHashed()
notpresent = NotPresent()


# Disabling remapping from old to new keys since the mapping is deprecated.
RemapDict = dict


# class RemapDict(dict):
#     """
#     DISABLED
#     Remap Dictionary.

#     For keys that have a new, longer name, remap the old key to the new key.
#     Other keys that don't have a new name are handled as before.
#     """

#     def __getitem__(self, old_key):
#         new_key = EXPANDED_KEY_MAP.get(old_key, old_key)
#         if new_key != old_key:
#             logger.warning(
#                 "DeepDiff Deprecation: %s is renamed to %s. Please start using "
#                 "the new unified naming convention.", old_key, new_key)
#         if new_key in self:
#             return self.get(new_key)
#         else:  # pragma: no cover
#             raise KeyError(new_key)


class indexed_set(set):
    """
    A set class that lets you get an item by index

    >>> a = indexed_set()
    >>> a.add(10)
    >>> a.add(20)
    >>> a[0]
    10
    """


JSON_CONVERTOR = {
    Decimal: float,
    OrderedSet: list,
    type: lambda x: x.__name__,
    bytes: lambda x: x.decode('utf-8')
}


def json_convertor_default(default_mapping=None):
    _convertor_mapping = JSON_CONVERTOR.copy()
    if default_mapping:
        _convertor_mapping.update(default_mapping)

    def _convertor(obj):
        for original_type, convert_to in _convertor_mapping.items():
            if isinstance(obj, original_type):
                return convert_to(obj)
        raise TypeError('We do not know how to convert {} of type {} for json serialization. Please pass the default_mapping parameter with proper mapping of the object to a basic python type.'.format(obj, type(obj)))

    return _convertor


def add_to_frozen_set(parents_ids, item_id):
    return parents_ids | {item_id}


def convert_item_or_items_into_set_else_none(items):
    if items:
        if isinstance(items, strings):
            items = {items}
        else:
            items = set(items)
    else:
        items = None
    return items


RE_COMPILED_TYPE = type(re.compile(''))


def convert_item_or_items_into_compiled_regexes_else_none(items):
    if items:
        if isinstance(items, (strings, RE_COMPILED_TYPE)):
            items = [items]
        items = [i if isinstance(i, RE_COMPILED_TYPE) else re.compile(i) for i in items]
    else:
        items = None
    return items


def get_id(obj):
    """
    Adding some characters to id so they are not just integers to reduce the risk of collision.
    """
    return "{}{}".format(ID_PREFIX, id(obj))


def get_type(obj):
    """
    Get the type of object or if it is a class, return the class itself.
    """
    if isinstance(obj, np_ndarray):
        return obj.dtype.type
    return obj if type(obj) is type else type(obj)


def type_in_type_group(item, type_group):
    return get_type(item) in type_group


def type_is_subclass_of_type_group(item, type_group):
    return isinstance(item, type_group) or issubclass(item, type_group) or type_in_type_group(item, type_group)


def get_doc(doc_filename):
    try:
        with open(os.path.join(current_dir, doc_filename), 'r') as doc_file:
            doc = doc_file.read()
    except Exception:  # pragma: no cover
        doc = 'Failed to load the docstrings. Please visit: https://github.com/seperman/deepdiff'  # pragma: no cover
    return doc


number_formatting = {
    "f": r'{:.%sf}',
    "e": r'{:.%se}',
}


def number_to_string(number, significant_digits, number_format_notation="f"):
    """
    Convert numbers to string considering significant digits.
    """
    try:
        using = number_formatting[number_format_notation]
    except KeyError:
        raise ValueError("number_format_notation got invalid value of {}. The valid values are 'f' and 'e'".format(number_format_notation)) from None
    if isinstance(number, Decimal):
        tup = number.as_tuple()
        with localcontext() as ctx:
            ctx.prec = len(tup.digits) + tup.exponent + significant_digits
            number = number.quantize(Decimal('0.' + '0' * significant_digits))
    result = (using % significant_digits).format(number)
    # Special case for 0: "-0.00" should compare equal to "0.00"
    if set(result) <= ZERO_DECIMAL_CHARACTERS:
        result = "0.00"
    # https://bugs.python.org/issue36622
    if number_format_notation == 'e' and isinstance(number, float):
        result = result.replace('+0', '+')
    return result


class DeepDiffDeprecationWarning(DeprecationWarning):
    """
    Use this warning instead of DeprecationWarning
    """
    pass


def cartesian_product(a, b):
    """
    Get the Cartesian product of two iterables

    **parameters**

    a: list of lists
    b: iterable to do the Cartesian product
    """

    for i in a:
        for j in b:
            yield i + (j,)


def cartesian_product_of_shape(dimentions, result=None):
    """
    Cartesian product of a dimentions iterable.
    This is mainly used to traverse Numpy ndarrays.

    Each array has dimentions that are defines in ndarray.shape
    """
    if result is None:
        result = ((),)  # a tuple with an empty tuple
    for dimension in dimentions:
        result = cartesian_product(result, range(dimension))
    return result


def get_numpy_ndarray_rows(obj, shape=None):
    """
    Convert a multi dimensional numpy array to list of rows
    """
    if shape is None:
        shape = obj.shape

    dimentions = shape[:-1]
    for path_tuple in cartesian_product_of_shape(dimentions):
        result = obj
        for index in path_tuple:
            result = result[index]
        yield path_tuple, result


class _NotFound:

    def __eq__(self, other):
        return False

    __req__ = __eq__

    def __repr__(self):
        return 'not found'

    __str__ = __repr__


not_found = _NotFound()


warnings.simplefilter('once', DeepDiffDeprecationWarning)


class OrderedSetPlus(OrderedSet):

    def lpop(self):
        """
        Remove and return the first element from the set.
        Raises KeyError if the set is empty.
        Example:
            >>> oset = OrderedSet([1, 2, 3])
            >>> oset.lpop()
            1
        """
        if not self.items:
            raise KeyError("Set is empty")

        elem = self.items[0]
        del self.items[0]
        del self.map[elem]
        return elem


class RepeatedTimer:
    """
    Threaded Repeated Timer by MestreLion
    https://stackoverflow.com/a/38317060/1497443
    """

    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.start_time = time.time()
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _get_duration_sec(self):
        return int(time.time() - self.start_time)

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        self.kwargs.update(duration=self._get_duration_sec())
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        duration = self._get_duration_sec()
        self._timer.cancel()
        self.is_running = False
        return duration


LITERAL_EVAL_PRE_PROCESS = [
    ('Decimal(', ')', Decimal),
]


def literal_eval_extended(item):
    """
    An extend version of literal_eval
    """
    try:
        return literal_eval(item)
    except (SyntaxError, ValueError):
        for begin, end, func in LITERAL_EVAL_PRE_PROCESS:
            if item.startswith(begin) and item.endswith(end):
                # Extracting and removing extra quotes so for example "Decimal('10.1')" becomes "'10.1'" and then '10.1'
                item2 = item[len(begin): -len(end)].strip('\'\"')
                return func(item2)
        raise


def time_to_seconds(t):
    return (t.hour * 60 + t.minute) * 60 + t.second


def _get_numbers_distance(num1, num2, max_=1):
    """
    Get the distance of 2 numbers. The output is a number between 0 to the max.
    The reason is the
    When max is returned means the 2 numbers are really far, and 0 means they are equal.
    """
    try:
        # Since we have a default cutoff of 0.3 distance when
        # getting the pairs of items during the ingore_order=True
        # calculations, we need to make the divisor of comparison very big
        # so that any 2 numbers can be chosen as pairs.
        divisor = (num1 + num2) * 1000
    except Exception:
        return max_
    else:
        if not divisor:
            return max_
        try:
            return min(max_, abs((num1 - num2) / divisor))
        except Exception:
            return max_
    return max_


def _get_datetime_distance(date1, date2, max_):
    return _get_numbers_distance(date1.timestamp(), date2.timestamp(), max_)


def _get_date_distance(date1, date2, max_):
    return _get_numbers_distance(date1.toordinal(), date2.toordinal(), max_)


def _get_timedelta_distance(timedelta1, timedelta2, max_):
    return _get_numbers_distance(timedelta1.total_seconds(), timedelta2.total_seconds(), max_)


def _get_time_distance(time1, time2, max_):
    return _get_numbers_distance(time_to_seconds(time1), time_to_seconds(time2), max_)


TYPES_TO_DIST_FUNC = [
    (only_numbers, _get_numbers_distance),
    (datetime.datetime, _get_datetime_distance),
    (datetime.date, _get_date_distance),
    (datetime.timedelta, _get_timedelta_distance),
    (datetime.time, _get_time_distance),
]


def get_numeric_types_distance(num1, num2, max_):
    for type_, func in TYPES_TO_DIST_FUNC:
        if isinstance(num1, type_) and isinstance(num2, type_):
            return func(num1, num2, max_)
    return not_found


class bcolors:
    """
    For color printing and debugging
    https://stackoverflow.com/a/287944/1497443
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
