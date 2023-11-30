# Copyright 2023  DFKI GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import types
import json
import warnings
from typing import Dict, List, Union, Optional, Any, Callable, Tuple, Set

from up_interface.config import *


def __add_dict(_values: Dict[str, Any], _name: str, _dict: Dict,
               _except: Optional[Callable[[Any, str, List[str]], bool]] = None,
               _parents: List[str] = None):

    """ Add a dict value to a dictionary

    Parameters
    ----------
    _values : Dict
        Output directory where the value will be added
    _name : str
        Name / key of the object to be added
    _dict : Dict
        dict to be added
    _except : Callable[[Any, str, List[str]], bool], None
        Function that receives the object being added, the name of the property, the list of parent property names 
        and returns True if the property must be disregarded and not saved.
    _parents : List[str]
        Names of the parent properties

    """

    _count = -1
    _values[_name] = dict()
    _parents.append(_name)
    for _k, _v in _dict.items():
        _count += 1

        _tmp = types.SimpleNamespace()
        _tmp.key = _k
        _tmp.value = _v

        add_value(_values=_values[_name], _name=f'<elem{_count}>', _value=_tmp,
                  _parent_obj=None, _except=_except, _parents=_parents)
    _parents.pop()


def __add_list_set_tuple(_values: Dict[str, Any], _name: str, _col: Union[List, Set, Tuple],
                         _except: Optional[Callable[[Any, str, List[str]], bool]] = None,
                         _parents: Optional[List[str]] = None):

    """ Add a list, set or tuple value to a dictionary

    Parameters
    ----------
    _values : Dict
        Output directory where the value will be added
    _name : str
        Name / key of the object to be added
    _col : List, Set, Tuple
        list, set or tuple to be added
               _parent_obj: Optional[Any],
    _except : Callable[[Any, str, List[str]], bool], None
        Function that receives the object being added, the name of the property, the list of parent property names
        and returns True if the property must be disregarded and not saved.
    _parents : List[str]
        Names of the parent properties

    """
    if _parents is None:
        _parents = list()

    if _except is not None and _except(_col, _name, _parents):
        return

    _values[_name] = dict()
    _parents.append(_name)
    for _i, _v in enumerate(_col):
        add_value(_values=_values[_name], _name=f'<elem{_i}>', _value=_v,
                  _parent_obj=None, _except=_except, _parents=_parents)
    _parents.pop()


def add_value(_values: Dict[str, Any], _name: Optional[str], _value: Any,
              _parent_obj: Optional[Any],
              _except: Optional[Callable[[Any, str, List[str]], bool]] = None,
              _parents: Optional[List[str]] = None):

    """ Add a value/object to a dictionary

    Parameters
    ----------
    _values : Dict
        Output directory where the value will be added
    _name : str
        Name / key of the object to be added
    _value : Any
        Value/object to be added
    _parent_obj : Any
        Parent object
    _except : Callable[[Any, str, List[str]], bool], None
        Function that receives the object being added, the name of the property, the list of parent property names
        and returns True if the property must be disregarded and not saved.
    _parents : List[str]
        Names of the parent properties
    """
    if _parents is None:
        _parents = list()

    if _except is not None and _name is not None and _except(_value, _name, _parents):
        return

    if isinstance(_value, Enum) and _name is not None:
        _values[_name] = _value.name
    elif isinstance(_value, (str, bool, int, float, complex)) and _name is not None:
        _values[_name] = _value
    elif hasattr(_value, '__dict__'):
        if _name is None:
            _sub = _values
        else:
            _sub = dict()
            _values[_name] = _sub
            _parents.append(_name)
        _vals = _value.__dict__
        for _n, _v in _vals.items():
            add_value(_values=_sub, _name=_n, _value=_v,
                      _parent_obj=_value, _except=_except, _parents=_parents)
        if _name is not None:
            _parents.pop()
    elif isinstance(_value, (list, set, tuple)) and _name is not None:
        _all_basic_types = True
        for _v in _value:
            if not isinstance(_v, (str, bool, int, float, complex)):
                _all_basic_types = False
                break
        if _all_basic_types:
            _values[_name] = _value
            return
        __add_list_set_tuple(_values=_values, _name=_name, _col=_value, _except=_except, _parents=_parents)
    elif isinstance(_value, dict) and _name is not None:
        _all_basic_types = True
        for _k, _v in _value.items():
            if (not isinstance(_k, (str, bool, int, float, complex))
                    or not isinstance(_v, (str, bool, int, float, complex))):
                _all_basic_types = False
                break
        if _all_basic_types:
            _values[_name] = _value
            return
        __add_dict(_values=_values, _name=_name, _dict=_value, _except=_except, _parents=_parents)

    elif _name is not None:
        _values[_name] = _value


def __read_based_on_ref(_value: Any, _value_ref: Any, _init_out_value: Optional[Any], stop_on_error: bool = False) \
        -> Optional[Any]:
    _out_value = _init_out_value
    if isinstance(_value, dict) and hasattr(_value_ref, '__dict__'):
        if _out_value is None:
            _out_value = type(_value_ref)()
        if not read_object(_out_value, _value, _value_ref, stop_on_error):
            return None
    elif isinstance(_value, dict) and isinstance(_value_ref, dict):
        if _out_value is None:
            _out_value = type(_value_ref)()
        if not __read_dict(_out_value, _value, _value_ref, stop_on_error):
            return None
    elif isinstance(_value, dict) and isinstance(_value_ref, (list, set, tuple)):
        if _out_value is None:
            _out_value = type(_value_ref)()
        return __read_list_set_tuple(_value, _value_ref, stop_on_error)
    else:
        _out_value = read_value(_value_ref, _value)
    return _out_value


def read_value(_ref_value: Any, _value: Union[str, Any]) -> Optional[Any]:

    """ Read/parse a value/object

    Parameters
    ----------
    _ref_value : Any
        Reference value/object used to obtain the desired type
    _value : str, Dict
        _value to be read/parsed

    Returns
    ----------
    value : Any, None
        Read/parsed value (None on failure)
    """

    try:
        if type(_ref_value) is type(_value):
            return _value
        if isinstance(_value, str):
            if isinstance(_ref_value, Enum):
                __values = {member.name.lower(): member for member in type(_ref_value)}
                return __values.get(_value.lower())
        elif isinstance(_value, (bool, int, float, complex)):
            if isinstance(_ref_value, Enum):
                __values = {member.value: member for member in type(_ref_value)}
                _e_value = __values.get(_value)
                if _e_value is None:
                    warnings.warn(f'[ERROR] Error reading enum value of type {type(_ref_value)}: {_value}')
                return _e_value
            return type(_ref_value)(_value)

        warnings.warn(f'[ERROR] Error reading value of type {type(_ref_value)}: {_value}')
        return None
    except Exception as e:
        warnings.warn(f'[ERROR] Error reading value {_value} of type {type(_ref_value)} (exception) : {e}')
        return None


def __read_dict(_out_value: Dict, _value: Dict, _ref_dict: Dict, stop_on_error: bool = False) -> bool:

    """ Read/parse (recursively) a  dictionary

    Parameters
    ----------
    _out_value : Any
        Output object to be updated
    _value : Dict
        Dictionary holding the object property values to be read
    _ref_dict : Any
        Reference dictionary used to obtain the desired key and value types
    stop_on_error : bool
        If true, it will stop reading/parsing if there is an error

    Returns
    ----------
    success : bool
        True on success
    """

    try:
        _out_value.clear()
        if len(_value) == 0:
            return True

        for _k, _v in _value.items():
            if not isinstance(_k, str) or not _k.startswith('<elem') or not _k.endswith('>') \
                    or not isinstance(_v, dict) or 'key' not in _v.keys() or 'value' not in _v.keys():
                _out_value = _value
                return True

        _sorted_values = dict(sorted(_value.items()))

        _ref_keys = list()
        _ref_values = list()

        for _k, _v in _ref_dict.items():
            _ref_keys.append(_k)
            _ref_values.append(_v)

        if len(_ref_keys) == 0:
            warnings.warn(f'[ERROR] Reference dict is empty')
            return False

        _i_ref = 0

        for _k, _v in _sorted_values.items():
            _ref_obj = types.SimpleNamespace()
            _ref_obj.key = _ref_keys[_i_ref]
            _ref_obj.value = _ref_values[_i_ref]

            _i_ref = _i_ref+1 if _i_ref+1 < len(_ref_keys) else 0

            if not read_object(_out_value=_ref_obj, _value=_v, _ref_obj=_ref_obj, stop_on_error=True):
                if stop_on_error:
                    return False
                continue
            _out_value[_ref_obj.key] = _ref_obj.value

        _sorted_values.clear()
        return True

    except Exception as e:
        warnings.warn(f'[ERROR] Error reading value {_value} of dict type (exception) : {e}')
        return False


def __read_list_set_tuple(_value: Union[Dict, List], _ref_col: Union[List, Set, Tuple],
                          stop_on_error: bool = False) -> Union[List, Set, Tuple, None]:

    """ Read/parse (recursively) a list, set or tuple

    Parameters
    ----------
    _value : Dict
        Dictionary holding the object property values to be read
    _ref_col : Any
        Reference list, set or tuple used to obtain the desired key and value types
    stop_on_error : bool
        If true, it will stop reading/parsing if there is an error

    Returns
    ----------
    read_collection : List, Set, Tuple, None
        Read list, set or tuple (None on failure)
    """

    try:
        if len(_value) == 0:
            return None

        if isinstance(_value, list):
            return _value

        for _k, _v in _value.items():
            if not isinstance(_k, str) or not _k.startswith('<elem') or not _k.endswith('>'):
                warnings.warn(f'[ERROR] Invalid format for List, Set, Tuple')
                return None

        _sorted_values = dict(sorted(_value.items()))

        if len(_ref_col) == 0:
            warnings.warn(f'[ERROR] Reference collection is empty')
            return None

        _i_ref = 0

        _all_values = list()

        for _k, _v in _sorted_values.items():
            _v_ref = _ref_col[_i_ref]
            _i_ref = _i_ref + 1 if _i_ref + 1 < len(_ref_col) else 0

            _v_read = __read_based_on_ref(_value=_v, _value_ref=_v_ref,
                                          _init_out_value=None, stop_on_error=stop_on_error)

            if _v_read is None:
                if stop_on_error:
                    warnings.warn(f'[ERROR] Error reading element {_k} of object {type(_v_ref)} from value {_v}')
                    return None
                # continue

            _all_values.append(_v_read)

        _sorted_values.clear()
        return type(_ref_col)(_all_values)

    except Exception as e:
        warnings.warn(f'[ERROR] Error reading value {_value} of type {type(_ref_col)} (exception) : {e}')
        return None


def read_object(_out_value: Any, _value: Dict, _ref_obj: Optional[Any] = None, stop_on_error: bool = False) -> bool:

    """ Read/parse (recursively) an object

    Parameters
    ----------
    _out_value : Any
        Output object to be updated
    _value : Dict
        Dictionary holding the object property values to be read
    _ref_obj : Any, None
        Reference object used to obtain the desired type
    stop_on_error : bool
        If true, it will stop reading/parsing if there is an error

    Returns
    ----------
    success : bool
        True on success
    """

    try:
        if _ref_obj is None:
            _ref_obj = type(_out_value)()

        if type(_ref_obj) is not type(_out_value):
            warnings.warn(f'[ERROR] Missmatch in types {type(_ref_obj)} and {type(_out_value)}')
            return False

        if not isinstance(_value, dict) or not hasattr(_ref_obj, '__dict__'):
            warnings.warn(f'[ERROR] Invalid type of object of type {type(_ref_obj)} or value {_value}')
            return False

        _vals_ref = _ref_obj.__dict__
        for _n, _v in _value.items():
            _v_ref = _vals_ref.get(_n)
            if _v_ref is None:
                continue

            _v2 = __read_based_on_ref(_value=_v, _value_ref=_v_ref,
                                      _init_out_value=getattr(_out_value, _n), stop_on_error=stop_on_error)
            if _v2 is None:
                warnings.warn(f'[ERROR] Error reading attribute {_n} of object {type(_v_ref)} from value {_v}')
                if stop_on_error:
                    return False
                continue
            setattr(_out_value, _n, _v2)

            # if isinstance(_v, dict) and hasattr(_v_ref, '__dict__'):
            #     if not read_object(getattr(_out_value, _n), _v, _v_ref, stop_on_error):
            #         warnings.warn(f'[ERROR] Error reading attribute {_n} of object {type(_v_ref)} from value {_v}')
            #         if stop_on_error:
            #             return False
            #         continue
            # elif isinstance(_v, dict) and isinstance(_v_ref, dict):
            #     if not __read_dict(getattr(_out_value, _n), _v, _v_ref, stop_on_error):
            #         warnings.warn(f'[ERROR] Error reading attribute {_n} of object {type(_v_ref)} from value {_v}')
            #         if stop_on_error:
            #             return False
            #         continue
            # elif isinstance(_v, dict) and isinstance(_v_ref, (list, set, tuple)):
            #     _v2 = __read_list_set_tuple(_v, _v_ref, stop_on_error)
            #     if _v2 is None:
            #         warnings.warn(f'[ERROR] Error reading attribute {_n} of object {type(_v_ref)} from value {_v}')
            #         if stop_on_error:
            #             return False
            #         continue
            #     setattr(_out_value, _n, _v2)
            # else:
            #     _v2 = read_value(_v_ref, _v)
            #     if _v2 is None:
            #         if stop_on_error:
            #             return False
            #         continue
            #     setattr(_out_value, _n, _v2)
        return True

    except Exception as e:
        warnings.warn(f'[ERROR] Error reading value {_value} of type {type(_ref_obj)} (exception) : {e}')
        return False


def save_object_in_file(filename: str, _obj: Any, _except: Optional[Callable[[Any, str, List[str]], bool]] = None) -> bool:

    """ Save an object in a json output file

    Parameters
    ----------
    filename : str
        Output file where the files will be saved
    _obj : Any
        Object to be saved
    _except : Callable[[Any, str, List[str]], bool], None
        Function that receives the object being added, the name of the property, the list of parent property names
        and returns True if the property must be disregarded and not saved.

    Returns
    ----------
    success : bool
        True on success
    """

    try:
        with open(filename, 'w') as f:
            values = dict()
            add_value(values, _name=None, _value=_obj, _parent_obj=None, _except=_except)
            json.dump(values, f, indent=2)
        return True
    except Exception as e:
        warnings.warn(f'[ERROR] Error saving file (exception): {e}')
        return False


def load_object_from_file(filename: str, _obj: Any, _ref_obj: Optional[Any] = None) -> bool:

    """ Load an object from a json input file

    If an input is not given, the value of _obj is not overwritten

    Parameters
    ----------
    filename : str
        Output file where the files will be saved
    _obj : Any
        Loaded _obj
    _ref_obj : Any, None
        Reference object used to obtain the desired types

    Returns
    ----------
    success : bool
        True on success
    """

    if not hasattr(_obj, '__dict__'):
        warnings.warn(f'[ERROR] _obj is not an object/class')
        return False
    try:
        with open(filename, 'r') as f:
            data: Dict = json.load(f)
            if data is None:
                warnings.warn(f'[ERROR] No JSON data was loaded')
                return False
            return read_object(_out_value=_obj, _value=data, _ref_obj=_ref_obj)

    except Exception as e:
        warnings.warn(f'[ERROR] Error loading file (exception): {e}')
        return False
