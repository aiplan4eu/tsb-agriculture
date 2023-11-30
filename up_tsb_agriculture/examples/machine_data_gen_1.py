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

from util_arolib.types import *
from silo_planning.types import *


def generate_working_group(num_harvesters: int, num_tvs: int) -> List[Machine]:

    """ Creates a list of basic machines (with default-ish parameters) composed by n harvesters and m transport vehicles

    Parameters
    ----------
    num_harvesters : int
        Number of harvesters
    num_tvs : int
        Number of transport vehicles

    Returns
    ----------
    machines : List[Machine]
        Created machines
    """

    if num_harvesters <= 0:
        num_harvesters = 2
    if num_tvs <= 0:
        num_tvs = num_harvesters * 3

    machines = list()

    for i in range(num_harvesters):
        m = Machine()
        m.id = i
        m.machinetype = MachineType.HARVESTER
        m.manufacturer = 'Test manufacturer'
        m.model = 'Harvester v1'
        m.width = 3.2
        m.length = 7.2
        m.weight = 20000
        m.bunker_mass = m.bunker_volume = 0
        m.working_width = 6
        m.max_speed_empty = 3.0
        m.max_speed_full = 3.0
        m.def_working_speed = 2.5
        m.unloading_speed_mass = 100
        m.unloading_speed_volume = 100
        m.turning_radius = 6.4

        machines.append(m)

    for i in range(num_tvs):
        mass_capacity_t = 10 if i % 2 == 0 else 8
        m = Machine()
        m.id = 100 + i
        m.machinetype = MachineType.OLV
        m.manufacturer = 'Test manufacturer'
        m.model = f'OLV_({mass_capacity_t}t)'
        m.width = 2.75
        m.length = 10
        m.weight = 20000
        m.bunker_mass = m.bunker_volume = 8000
        m.working_width = m.width
        m.max_speed_empty = 2.5 + 0.5 * i
        m.max_speed_full = 2.5 + 0.5 * i
        m.def_working_speed = 2.5 + 0.5 * i
        m.unloading_speed_mass = 200
        m.unloading_speed_volume = 200
        m.turning_radius = 5.7

        machines.append(m)

    return machines
