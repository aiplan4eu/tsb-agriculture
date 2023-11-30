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

from unified_planning.shortcuts import *


def get_up_type_as_str(value: Any) -> str:
    """ Get the UP-type of a value as string.

    Parameters
    ----------
    value : Any
        Value

    Returns
    -------
    type : str
        UP-type of the value as string
    """

    if isinstance(value, Fraction):
        return get_up_type_as_str(Real(value))
    return f'{value.type}'.split('[')[0]


def is_up_type_bool(value: Any) -> bool:
    """ Check if a value is of UP-type Bool.

    Parameters
    ----------
    value : Any
        Value

    Returns
    -------
    is : bool
        True if the value is of UP-type Bool.
    """

    target_type = get_up_type_as_str( Bool(True) )
    if isinstance(value, str):
        return value == target_type
    return get_up_type_as_str(value) == target_type


def is_up_type_int(value):
    """ Check if a value is of UP-type Int.

    Parameters
    ----------
    value : Any
        Value

    Returns
    -------
    is : bool
        True if the value is of UP-type Int.
    """

    target_type = get_up_type_as_str( Int(0) )
    if isinstance(value, str):
        return value == target_type
    return get_up_type_as_str(value) == target_type


def is_up_type_real(value):
    """ Check if a value is of UP-type Real.

    Parameters
    ----------
    value : Any
        Value

    Returns
    -------
    is : bool
        True if the value is of UP-type Real.
    """

    target_type = get_up_type_as_str( Real(Fraction(0) ) )
    if isinstance(value, str):
        return value == target_type
    return get_up_type_as_str(value) == target_type


def get_up_fraction(value: Union[int, float, Fraction]) -> Fraction:
    """ Get a given value as a type Fraction.

    Parameters
    ----------
    value : int, float, Fraction
        Value

    Returns
    -------
    fraction : Fraction
        Fraction corresponding to the given value.
    """

    if isinstance(value, Fraction):
        return value.limit_denominator()
    return Fraction( value ).limit_denominator()
    # return Fraction( f'{value}' ).limit_denominator()


def get_up_real(value: Union[int, float, FNode, Fraction]) -> Real:
    """ Get a given value as a UP-type Real.

    Parameters
    ----------
    value : int, float, FNode, Fraction
        Value

    Returns
    -------
    real : Real
        Real corresponding to the given value.
    """

    if isinstance(value, FNode):
        return value
    if isinstance(value, Fraction):
        return Real( value.limit_denominator() )
    return Real( get_up_fraction(value) )
