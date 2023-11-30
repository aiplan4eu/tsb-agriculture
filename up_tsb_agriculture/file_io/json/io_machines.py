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

import json
import os
from typing import List

from util_arolib.types import *
from silo_planning.types import Compactor


def save_machines(path: str, machines: List[Machine], compactors: List[Compactor]):

    """ Save the machines (harvesters, transport vehicles, compactors) in a set of json output files

    The following files will be generated:
    - machines.json: json formatted file containing the harvesters and transport vehicles
    - compactors.json: json formatted file containing the compactors

    Parameters
    ----------
    path : str
        Output directory where the files will be saved
    machines : List[Machine]
        List containing the harvesters and transport vehicles to be saved
    compactors : List[Compactor]
        compactors to be saved
    """

    machines_data = list()
    for m in machines:
        if m.machinetype == MachineType.HARVESTER:
            type = 'harvester'
        elif m.machinetype == MachineType.OLV:
            type = 'transport vehicle'
        else:
            continue
        machines_data.append( {'id': m.id,
                               'type': type,
                               'manufacturer': m.manufacturer,
                               'model': m.model,
                               'width': m.width,
                               'working_width': m.working_width,
                               'length': m.length,
                               'weight': m.weight,
                               'turning_radius': m.turning_radius,
                               'bunker_mass': m.bunker_mass,
                               'bunker_volume': m.bunker_volume,
                               'def_working_speed': m.def_working_speed,
                               'max_speed_empty': m.max_speed_empty,
                               'max_speed_full': m.max_speed_full,
                               'unloading_speed_mass': m.unloading_speed_mass,
                               'unloading_speed_volume': m.unloading_speed_volume} )
    with open(f'{path}/machines.json', 'w') as f:
        json.dump({'machines': machines_data}, f, indent=2)

    machines_data = list()
    for m in compactors:
        machines_data.append( {'id': m.id,
                               'silo_id': m.silo_id,
                               'mass_per_sweep': m.mass_per_sweep} )
    with open(f'{path}/compactors.json', 'w') as f:
        json.dump({'compactors': machines_data}, f, indent=2)


def load_machines(path: str, harvesters: List[Machine], tvs: List[Machine], compactors: List[Compactor]):

    """ Load machines (harvesters, transport vehicles, compactors) from a set of json input files

    Expected files in the directory:
    - machines|harvesters|transport_vehicles.json: json formatted file containing harvesters and/or transport vehicles and their properties:
        {
            "machines": [
                {  # one machine
                    "id": 972,  # Machine Id (integer)
                    "type": "harvester",  # machine type = "harvester" | "harv" | "transport vehicle" | "tv"
                    "manufacturer": "Machine_manufacturer_XYZ",
                    "model": "Machine_model_XYZ",
                    "width": 3,  # [m]
                    "working_width": 7.5,  # [m]
                    "length": 8.59,  # [m]
                    "weight": 12500,  # [kg]
                    "turning_radius": -9999,  # [m]
                    "bunker_mass": 0,  # [kg]
                    "bunker_volume": 0,  # [m³]
                    "def_working_speed": 1.9,  # [m/s]
                    "max_speed_empty": 5,  # [m/s]
                    "max_speed_full": 5  # [m/s]
                },
                {  # another machine
                    "id": 825,
                    ...
                },
                {  # another machine
                    "id": 830,
                    ...
                },
                ...
            ]
        }
    - compactors.json: json formatted file containing harvesters and/or transport vehicles and their properties:
        {
            "machines": [
                {  # one machine
                    "id": 1010,  # Machine Id (integer)
                    "silo_id": 100,  # Id of the silo assigned to the compactor (integer)
                    "mass_per_sweep": 500.0,  #  Amount of yield-mass [kg] moved by the compactor in one sweep
                },
                {  # another machine
                    "id": 1020,
                    ...
                },
                {  # another machine
                    "id": 1030,
                    ...
                },
                ...
            ]
        }

    Parameters
    ----------
    path : str
        Directory where the files are located
    harvesters : List[Machine]
        [out] Loaded harvesters
    tvs : List[Machine]
        [out] Loaded transport vehicles
    compactors : List[Compactor]
        [out] Loaded compactors
    """

    harvesters.clear()
    tvs.clear()
    compactors.clear()

    machine_ids = set()
    for root, dirs, files in os.walk(path):
        for file in files:
            try:
                if file.lower().endswith(".json"):
                    if file.lower().find("machine_state") >= 0:
                        continue
                    if file.lower().find("machine") >= 0 or \
                            file.lower().find("harvester") >= 0 or \
                            file.lower().find("vehicle") >= 0:
                        f = open(f'{root}/{file}')
                        data = json.load(f)
                        if data is not None:
                            for m in data['machines']:
                                machine = Machine()
                                machinetype = None
                                for key, val in m.items():
                                    if key == 'id':
                                        machine.id = int(val)
                                    elif key == 'type':
                                        if val.lower().find('harv') >= 0:
                                            machinetype = MachineType.HARVESTER
                                        elif val.lower().find('tv') >= 0 or \
                                                val.lower().find('olv') >= 0 or \
                                                val.lower().find('transport') >= 0:
                                            machinetype = MachineType.OLV
                                    elif key == 'manufacturer':
                                        machine.manufacturer = val
                                    elif key == 'model':
                                        machine.model = val
                                    elif key == 'width':
                                        machine.width = float(val)
                                    elif key == 'working_width':
                                        machine.working_width = float(val)
                                    elif key == 'length':
                                        machine.length = float(val)
                                    elif key == 'weight':
                                        machine.weight = float(val)
                                    elif key == 'turning_radius':
                                        machine.turning_radius = float(val)
                                    elif key == 'bunker_mass':
                                        machine.bunker_mass = float(val)
                                    elif key == 'bunker_volume':
                                        machine.bunker_volume = float(val)
                                    elif key == 'def_working_speed':
                                        machine.def_working_speed = float(val)
                                    elif key == 'max_speed_empty':
                                        machine.max_speed_empty = float(val)
                                    elif key == 'max_speed_full':
                                        machine.max_speed_full = float(val)
                                    elif key == 'unloading_speed_mass':
                                        machine.unloading_speed_mass = float(val)
                                    elif key == 'unloading_speed_volume':
                                        machine.unloading_speed_volume = float(val)

                                if machinetype is None:
                                    print('Invalid machine entry without a valid type')
                                    continue
                                machine.machinetype = machinetype
                                if machine.machinetype is MachineType.HARVESTER:
                                    harvesters.append(machine)
                                elif machine.machinetype is MachineType.OLV:
                                    tvs.append(machine)
                                machine_ids.add(machine.id)

                    elif file.lower().find("compactor") >= 0:
                        f = open(f'{root}/{file}')
                        data = json.load(f)
                        if data is not None:
                            for c in data['compactors']:
                                compactor = Compactor()
                                for key, val in c.items():
                                    if key == 'id':
                                        compactor.id = int(val)
                                    elif key == 'silo_id':
                                        compactor.silo_id = int(val)
                                    elif key == 'mass_per_sweep':
                                        compactor.mass_per_sweep = float(val)
                                compactors.append(compactor)
            except ValueError as e:
                print(f'Error reading file {file}: {e}')

    _m_id_ref = 0
    for ms in [harvesters, tvs]:
        for m in ms:
            if m.id == Machine().id:
                while _m_id_ref in machine_ids:
                    _m_id_ref += 1
                m.id = _m_id_ref
                _m_id_ref += 1
