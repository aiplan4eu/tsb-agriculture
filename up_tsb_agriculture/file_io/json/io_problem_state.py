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

from typing import Dict, List

from util_arolib.types import Field
from route_planning.types import FieldState, MachineState
from post_processing.plan_decoder_base import PlanDecoderBase
from file_io.json.io_locations import *
from file_io.json.io_machines import *


def __get_location_name(location_type: str, location_id: int, parent_location_id: int) -> Optional[str]:

    """ Get the location name from the location_type, location_id and parent_location_id

    Parameters
    ----------
    location_type : str
        Location type
    location_id : int
        Location id
    parent_location_id : int
        Parent (Silo or Field) id (Only for access points)

    Returns
    ----------
    location_name : str
        Location name
    """

    if location_type is None or location_id is None:
        return None
    _locationtype = location_type.lower().replace('_', '')
    if _locationtype == 'field':
        return get_field_location_name(location_id)
    elif _locationtype == 'fieldaccess' or _locationtype == 'fieldaccesspoint':
        if parent_location_id is None:
            return None
        return get_field_access_location_name(parent_location_id, location_id)
    elif _locationtype == 'silo':
        return get_silo_location_name(location_id)
    elif _locationtype == 'siloaccess' or _locationtype == 'siloaccesspoint':
        if parent_location_id is None:
            return None
        return get_silo_access_location_name(parent_location_id, location_id)
    return None


def __get_location_ids(location_name: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:

    """ Get the location_type, location_id and parent_location_id from the location name

    Parameters
    ----------
    location_name : str
        Location name

    Returns
    ----------
    location_type : str
        Location type
    location_id : int
        Location id
    parent_location_id : int
        Parent (Silo or Field) id (Only for access points)
    """

    location_ids = get_field_id_from_location_name(location_name)
    if location_ids is not None:
        return 'field', location_ids, None
    location_ids = get_field_access_id_from_location_name(location_name)
    if location_ids is not None:
        return 'field_access', location_ids[1], location_ids[0]
    location_ids = get_silo_id_from_location_name(location_name)
    if location_ids is not None:
        return 'silo', location_ids, None
    location_ids = get_silo_access_id_from_location_name(location_name)
    if location_ids is not None:
        return 'silo_access', location_ids[1], location_ids[0]
    return None, None, None


def save_machine_states(path: str, states: Dict[int, MachineState]):

    """ Save the machine states (harvesters, transport vehicles) in a json output file

    Parameters
    ----------
    path : str
        Output directory where the file will be saved
    states : Dict[int, MachineState]
        Machine states: {machine_id: machine_state}
    """

    machines_data = list()
    for machine_id, state in states.items():
        proj = Proj("+proj=utm +zone=32 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
        lon, lat = proj(state.position.x, state.position.y, inverse=True)

        location_type, location_id,  parent_location_id = __get_location_ids(state.location_name)
        machines_data.append({ 'machine_id': machine_id,
                               'state': {'timestamp': state.timestamp,
                                         'timestamp_free': state.timestamp_free,
                                         'position_lat': lat,
                                         'position_lon': lon,
                                         'bunker_mass': state.bunker_mass,
                                         'bunker_volume': state.bunker_volume,
                                         'location_type': location_type,
                                         'location_id': location_id,
                                         'parent_location_id': parent_location_id,
                                         'overloading_machine_id': state.overloading_machine_id} })
    with open(f'{path}/machine_states.json', 'w') as f:
        json.dump({'machine_states': machines_data}, f, indent=2)


def load_machine_states(path: str) -> Dict[int, MachineState]:

    """ Load machine states (harvesters, transport vehicles) from one or more json input files

    Expected files in the directory:
    - machine_states|machine_state.json: json formatted file containing harvesters and/or transport vehicles states:
        {
            "machine_states": [
                {  # one machine
                    "machine_id": 972,
                    "state": {
                        "timestamp": 922,  # [s]
                        "timestamp_free": 922,  # [s]
                        "position_lon": 8.297373280313662,
                        "position_lat": 52.36187751360036,
                        "bunker_mass": 0.0,  # [kg]
                        "bunker_volume": 0.0,  # [m³]
                        "location_name": "loc_field_2",
                        "overloading_machine_id": 726
                    }
                },
                {  # another machine
                    "machine_id": 825,
                    "state": {...}
                },
                {  # another machine
                    "machine_id": 926,
                    "state": {...}
                }
            ]
        }

    Parameters
    ----------
    path : str
        Directory where the file(s) is/are located

    Returns
    ----------
    states : Dict[int, MachineState]
        Loaded machine states: {machine_id: machine_state}
    """

    states = dict()

    for root, dirs, files in os.walk(path):
        for file in files:
            try:
                if file.lower().endswith(".json"):
                    if file.lower().find("machine_state") >= 0:
                        f = open(f'{root}/{file}')
                        data = json.load(f)
                        if data is not None:
                            for state_data in data['machine_states']:
                                machine_id = state_data.get('machine_id')
                                if machine_id is None:
                                    continue
                                s = state_data.get('state')
                                if s is None:
                                    continue
                                state = MachineState()
                                lat = 0.0
                                lon = 0.0
                                location_type = location_id = parent_location_id = None
                                for key, val in s.items():
                                    if val is None:
                                        continue
                                    if key == 'timestamp':
                                        state.timestamp = float(val)
                                    elif key == 'timestamp_free':
                                        state.timestamp_free = float(val)
                                    elif key == 'position_lat':
                                        lat = float(val)
                                    elif key == 'position_lon':
                                        lon = float(val)
                                    elif key == 'bunker_mass':
                                        state.bunker_mass = float(val)
                                    elif key == 'bunker_volume':
                                        state.bunker_volume = float(val)
                                    elif key == 'location_name':
                                        state.location_name = val
                                    elif key == 'location_type':
                                        location_type = val
                                    elif key == 'location_id':
                                        location_id = val
                                    elif key == 'parent_location_id':
                                        parent_location_id = val
                                    elif key == 'overloading_machine_id':
                                        state.overloading_machine_id = int(val)
                                if state.location_name is None:
                                    state.location_name = __get_location_name(location_type, location_id, parent_location_id)
                                try:
                                    proj = Proj("+proj=utm +zone=32 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
                                    x, y = proj(latitude=lat, longitude=lon)
                                    state.position.x = x
                                    state.position.y = y
                                    states[int(machine_id)] = state
                                except Exception as e:
                                    print(f"Error parsing point coordinates ({lat}, {lon}): {e}")

            except Exception as e:
                print(f'Error reading file {file}: {e}')

    return states


def save_field_states(path: str, states: Dict[str, FieldState]):

    """ Save the field states in a json output file (referenced by field name)

    Parameters
    ----------
    path : str
        Output directory where the file will be saved
    states : Dict[str, FieldState]
        Field states: {field_name: field_state}
    """

    field_data = list()
    for field_name, state in states.items():
        field_data.append({'field_name': field_name,
                           'state': {'avg_mass_per_area_t_ha': state.avg_mass_per_area_t_ha,
                                     'harvested_percentage': state.harvested_percentage}})
    with open(f'{path}/field_states.json', 'w') as f:
        json.dump({'field_states': field_data}, f, indent=2)


def save_field_states_2(path: str, states: Dict[int, FieldState], fields: List[Field]):

    """ Save the field states in a json output file (referenced by field name)

    Parameters
    ----------
    path : str
        Output directory where the file will be saved
    states : Dict[int, FieldState]
        Field states: {field_id: field_state}
    fields : List[Field]
        List of fields (used to obtain the field names). Only states of these fields will be saved.
    """

    states_2 = dict()
    for field in fields:
        state = states.get(field.id)
        if state is not None:
            states_2[field.name] = state
    return save_field_states(path, states_2)


def load_field_states(path: str) -> Dict[str, FieldState]:

    """ Load field states from one or more json input files

    Expected files in the directory:
    - field_states|field_state.json: json formatted file containing field states:
        {
            "field_states": [
                {  # one field
                    "field_name": "Field_1",
                    "state": {
                        "avg_mass_per_area_t_ha": 33.72,  # [t/ha]
                        "harvested_percentage": 0.0  # [0, 100] %
                    }
                },
                {  # another field
                    "field_name": "Field_2",
                    "state": {...}
                },
                {  # another field
                    "field_name": "Field_3",
                    "state": { ... }
                }
            ]
        }

    Parameters
    ----------
    path : str
        Directory where the file(s) is/are located

    Returns
    ----------
    states : Dict[str, FieldState]
        Loaded field states: {field_name: field_state}
    """

    states = dict()

    for root, dirs, files in os.walk(path):
        for file in files:
            try:
                if file.lower().endswith(".json"):
                    if file.lower().find("field_state") >= 0:
                        f = open(f'{root}/{file}')
                        data = json.load(f)
                        if data is not None:
                            for state_data in data['field_states']:
                                field_name = state_data.get('field_name')
                                if field_name is None:
                                    field_name = state_data.get('location_name')
                                if field_name is None:
                                    continue
                                s = state_data.get('state')
                                if s is None:
                                    continue
                                state = FieldState()
                                for key, val in s.items():
                                    if key == 'avg_mass_per_area_t_ha':
                                        state.avg_mass_per_area_t_ha = float(val)
                                    elif key == 'harvested_percentage':
                                        state.harvested_percentage = max(0.0, min(100.0, float(val)))
                                states[field_name] = state

            except Exception as e:
                print(f'Error reading file {file}: {e}')

    return states


def load_field_states_2(path: str, fields: List[Field]) -> Dict[int, FieldState]:

    """ Load field states from one or more json input files

    Expected files in the directory:
    - field_states|field_state.json: json formatted file containing field states:
        {
            "field_states": [
                {  # one field
                    "field_name": "Field_1",
                    "state": {
                        "avg_mass_per_area_t_ha": 33.72,  # [t/ha]
                        "harvested_percentage": 0.0  # [0, 100] %
                    }
                },
                {  # another field
                    "field_name": "Field_2",
                    "state": {...}
                },
                {  # another field
                    "field_name": "Field_3",
                    "state": { ... }
                }
            ]
        }

    Parameters
    ----------
    path : str
        Directory where the file(s) is/are located
    fields : List[Field]
        List of fields (used to obtain the field ids).

    Returns
    ----------
    states : Dict[int, FieldState]
        Loaded field states: {field_id: field_state}
    """

    states = dict()
    states_by_name = load_field_states(path)
    for field in fields:
        state = states_by_name.get(field.name)
        if state is not None:
            states[field.id] = state
    return states


class FieldStateDeviations:

    """ Class holding the deviations to be applied to field states """

    def __init__(self):
        self.delta_harvested_percentage: Dict[int, float] = dict()
        """ Deviation to the field harvested percentage [%] (key = field id) """


class MachineStateDeviations:

    """ Class holding the deviations to be applied to machine states """

    def __init__(self):
        self.delta_bunker_mass: Dict[int, float] = dict()
        """ Deviation to the yield mass in the bunker [kg] (key = machine id) """

        self.delta_position: Dict[int, Point] = dict()
        """ Deviation to the position of the machine [UTM] (key = machine id) """


class PlanDeviations:

    """ Class holding the deviations to be applied to the object states """

    def __init__(self):
        self.field_states = FieldStateDeviations()
        """ Deviations to be applied to the field states """

        self.machine_states = MachineStateDeviations()
        """ Deviations to be applied to the machine states """


def save_problem_state_from_plan(dir_path: str,
                                 plan_decoder: PlanDecoderBase,
                                 timestamp: float,
                                 deviations: Optional[PlanDeviations] = None) -> bool:

    """ Save all json/geojson files  corresponding to a problem's locations and machines as well as the locations' and machines' states at a given timestamp of a plan

    Parameters
    ----------
    dir_path : str
        Path to the directory where the state data will be saved
    plan_decoder : PlanDecoderBase
        Plan decoder containing the problem information and the decoded plan
    timestamp : float
        Timestamp [s] of the state that will be saved
    deviations : PlanDeviations
        Deviations to be applied to the states

    Returns
    ----------
    success : bool
        True on success
    """

    ok = True

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    fields = list(plan_decoder.field_names_map.values())
    silos = list(plan_decoder.silo_names_map.values())
    machines = list(plan_decoder.harvester_names_map.values())
    machines.extend(plan_decoder.tv_names_map.values())
    compactors = list(plan_decoder.data_manager.compactors.values())

    ok &= save_locations(dir_path, fields, silos, plan_decoder.roads)
    save_machines(dir_path, machines, compactors)

    field_states = dict()
    delta_harvested_percentage = dict() if deviations is None or deviations.field_states is None \
        else deviations.field_states.delta_harvested_percentage
    for name, field in plan_decoder.field_names_map.items():
        field_state = plan_decoder.get_field_state_at(name, timestamp)[0]
        delta = delta_harvested_percentage.get(field.id)
        if delta is not None:
            field_state.harvested_percentage = max( 0.0, min(100.0, field_state.harvested_percentage + delta ) )
        field_states[field.name] = field_state

    save_field_states(dir_path, field_states)

    machine_states = dict()
    delta_bunker_mass = dict()
    delta_position = dict()
    if deviations is not None and deviations.machine_states is not None:
        delta_position = deviations.machine_states.delta_position
        delta_bunker_mass = deviations.machine_states.delta_bunker_mass

    harvesters = set()
    for name, machine in plan_decoder.harvester_names_map.items():
        state, _ = plan_decoder.get_machine_state_at(name, timestamp)
        if state is not None:
            harvesters.add(machine.id)
            machine_states[machine.id] = state

    for name, machine in plan_decoder.tv_names_map.items():
        state, _ = plan_decoder.get_machine_state_at(name, timestamp)
        if state is not None:
            machine_states[machine.id] = state

    for _id, state in machine_states.items():

        delta = delta_bunker_mass.get(_id)
        if delta is not None:
            if _id in harvesters:
                print(f'WARNING: applying delta_bunker_mass to harvester with id {_id}')
            old_mass = state.bunker_mass
            state.bunker_mass = max( 0.0, state.bunker_mass + delta )
            print(f'Changing bunker mass of machine with id {_id}: {old_mass} -> {state.bunker_mass} Kg')

        delta = delta_position.get(_id)
        if delta is not None:
            if state.location_name is not None and state.location_name != get_street_location_name():
                print(f'WARNING: cannot apply delta_position to machine with id {_id} (current location is {state.location_name})')
            else:
                old_pos = get_copy_aro(state.position)
                state.position.x += delta.x
                state.position.y += delta.y
                print(f'Changing position of machine with id {_id}: '
                      f'({old_pos.x}, {old_pos.y}) -> ({state.position.x}, {state.position.y})')

    save_machine_states(dir_path, machine_states)

    return ok
