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

import random

from util_arolib.types import *
from route_planning.types import *
from silo_planning.types import *
from management.global_data_manager import GlobalDataManager


def list_to_dict(_list: List[Any]) -> Dict:

    """ Creates a dictionary from a list of objects, where the key is the object.id and the values is the object itself

    The objects must have a property 'id'

    Parameters
    ----------
    _list : List
        List of objects

    Returns
    ----------
    objects_dict : List[Any]
        Objects dictionary (objects must have property 'id')
    """

    _dict = dict()
    for item in _list:
        _dict[item.id] = item
    return _dict


def complete_machine_states_near_silo(machines: List[Machine], silo: ResourcePoint,
                                      states: Dict[int, MachineState],
                                      timestamp: float = 0.0, empty_machines: bool = True):

    """ Creates a machine state with a location near a silo for machines without states

    The objects must have a property 'id'

    Parameters
    ----------
    machines : List[Machine]
        List of machines
    silo : ResourcePoint
        silo
    states : Dict[int, MachineState]
        Machine states to be updated
    timestamp : float
        State timestamp
    empty_machines : bool
        If true, the machines will empty; otherwise, an initial bunker mass will be set for the machines.
    """

    scale = 0.3 if not empty_machines else 0.0
    for m in machines:
        if m.id in states.keys():
            continue
        state = MachineState()
        state.position.x = random.uniform(-10.0, 10.0) + silo.x
        state.position.y = random.uniform(-10.0, 10.0) + silo.y
        state.bunker_mass = max(0.0, scale * m.bunker_mass)
        state.bunker_volume = max(0.0, scale * m.bunker_volume)
        state.timestamp = timestamp
        state.timestamp_free = timestamp
        state.location_name = None
        states[m.id] = state

        if not empty_machines:
            scale = scale + 0.1
            if scale > 0.75:
                scale = 0.0


def init_data_manager(fields: List[Field], machines: List[Machine],
                      silos: List[SiloExtended], compactors: List[Compactor]) -> GlobalDataManager:

    """ Creates and initializes a data manager with the given fields, machines, silos, and compactors.

    The objects must have a property 'id'

    Parameters
    ----------
    fields : List[Field]
        List of fields
    machines : List[Machine]
        List of machines
    silos : List[SiloExtended]
        List of silos
    compactors : List[Compactor]
        List of compactors

    Returns
    ----------
    data_manager : GlobalDataManager
        Initialized data manager
    """

    data_manager = GlobalDataManager()
    for f in fields:
        if not data_manager.register_field(f):
            raise ValueError(f'Error registering field with id {f.id}')
    for m in machines:
        if not data_manager.register_machine(m):
            raise ValueError(f'Error registering machine with id {m.id}')
    for s in silos:
        if not data_manager.register_silo(s):
            raise ValueError(f'Error registering silo with id {s.id}')
    for c in compactors:
        if not data_manager.register_compactor(c):
            raise ValueError(f'Error registering compactor with id {c.id}')
    return data_manager
