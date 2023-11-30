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

from typing import Dict, List, Type
from util_arolib.types import *
from route_planning.types import MachineState


def arolib_vector_to_list(_vec) -> List[Any]:

    """ Create a python list from an arolib vector

    Parameters
    ----------
    _vec :
        Arolib vector

    Returns
    ----------
    list : List[Any]
        Python list
    """

    return list(_vec)


def list_to_arolib_vector(_list: List, _vector_type: Type) -> Any:

    """ Create an arolib vector from a python list

    Parameters
    ----------
    _list :
        Python list
    _vector_type :
        Arolib vector type

    Returns
    ----------
    vector :
        Arolib vector
    """

    _vec = _vector_type()
    _vec.extend(_list)
    return _vec


def arolib_map_to_dict(_map) -> Dict:

    """ Create a python dictionary from an arolib map

    Parameters
    ----------
    _map :
        Arolib map

    Returns
    ----------
    dict : Dict[Any]
        Python dictionary
    """

    return {item.key(): item.data() for item in _map}


def dict_to_arolib_map(_dict: Dict, _map_type: Type) -> Any:

    """ Create an arolib map from a python dictionary

    Parameters
    ----------
    _dict :
        Python dictionary
    _map_type :
        Arolib map type

    Returns
    ----------
    map :
        Arolib map
    """

    _map = _map_type()
    for key, val in _dict.items():
        _map[key] = val
    return _map


def from_arolib_machine_state(mdi: MachineDynamicInfo) -> MachineState:

    """ Create a MachineState from an arolib MachineDynamicInfo

    Parameters
    ----------
    mdi : MachineDynamicInfo
        Arolib MachineDynamicInfo

    Returns
    ----------
    machine_state : MachineState
        Machine state
    """

    state = MachineState()
    state.from_aro_machine_state(mdi)
    return state


def to_arolib_machine_state(state: MachineState) -> MachineDynamicInfo:

    """ Create an arolib MachineDynamicInfo from a MachineState

    Parameters
    ----------
    state : MachineState
        Machine state

    Returns
    ----------
    arolib_machine_state : MachineDynamicInfo
        Arolib MachineDynamicInfo
    """

    return state.to_aro_machine_state()
