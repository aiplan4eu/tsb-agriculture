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

from typing import Dict, Any, List, Union
from enum import Enum, auto
from util_arolib.types import MachineType

class BaseStats:

    """ Class holding the basic statistic values. """

    def __init__(self):
        self.total: float = 0.0
        """ Total/sum """

        self.min: float = float("inf")
        """ Minimum value """

        self.max: float = 0.0
        """ Maximum value """

        self.avg: float = 0.0
        """ Averag value """

        self.count: int = 0
        """ Amount of values """


    def update(self, val: float):
        """ Updates the statistic values with a new value

        Parameters
        ----------
        val : float
            New value
        """

        count = 1 + ( 0 if self.avg < 1e-9 else self.total / self.avg )
        self.total += val
        self.min = min(self.min, val)
        self.max = max(self.max, val)
        self.avg = self.total / count

class ProblemTransitStats:

    """ Class holding the statistic values of transit outside the fields. """

    class TransitType(Enum):

        """ Transit type. """

        FROM_INIT_LOC_TO_FIELD_ACCESS = auto()
        FROM_INIT_LOC_TO_SILO_ACCESS = auto()
        FROM_SILO_ACCESS_TO_FIELD_ACCESS = auto()
        FROM_FIELD_ACCESS_TO_SILO_ACCESS = auto()
        BETWEEN_FIELD_ACCESSES_DIFFERENT_FIELDS = auto()
        BETWEEN_FIELD_ACCESSES_SAME_FIELD = auto()

    def __init__(self):
        self._distance_between_field_access_points_all = BaseStats()
        self._distance_between_field_access_points_different_fields = BaseStats()
        self._distance_between_fields_and_silos = BaseStats()
        self._distance_from_init_locations = BaseStats()
        self._distance_from_init_locations_to_fields = BaseStats()
        self._distance_from_init_locations_to_silos = BaseStats()
        self._distance_between_all_locations = BaseStats()

        self._fields_distance_between_field_access_points_different_fields: Dict[int, BaseStats] = dict()

        self._machine_types_distance_between_field_access_points_all: Dict[MachineType, BaseStats] = dict()
        self._machine_types_distance_between_field_access_points_different_fields: Dict[MachineType, BaseStats] = dict()
        self._machine_types_distance_between_fields_and_silos: Dict[MachineType, BaseStats] = dict()
        self._machine_types_distance_from_init_locations: Dict[MachineType, BaseStats] = dict()
        self._machine_types_distance_from_init_locations_to_fields: Dict[MachineType, BaseStats] = dict()
        self._machine_types_distance_from_init_locations_to_silos: Dict[MachineType, BaseStats] = dict()
        self._machine_types_distance_between_all_locations: Dict[MachineType, BaseStats] = dict()

        self._machine_types_fields_distance_between_field_access_points_different_fields: Dict[int, Dict[MachineType, BaseStats]] = dict()

        self._machines_distance_between_field_access_points_all: Dict[int, BaseStats] = dict()
        self._machines_distance_between_field_access_points_different_fields: Dict[int, BaseStats] = dict()
        self._machines_distance_between_fields_and_silos: Dict[int, BaseStats] = dict()
        self._machines_distance_from_init_locations: Dict[int, BaseStats] = dict()
        self._machines_distance_from_init_locations_to_fields: Dict[int, BaseStats] = dict()
        self._machines_distance_from_init_locations_to_silos: Dict[int, BaseStats] = dict()
        self._machines_distance_between_all_locations: Dict[int, BaseStats] = dict()

        self._machines_fields_distance_between_field_access_points_different_fields: Dict[int, Dict[int, BaseStats]] = dict()

    def update_value(self,
                     val: float,
                     transit_type: TransitType,
                     machine_type: Union[MachineType, List[MachineType], None],
                     machine_id: Union[int, None],
                     field_ids: List[int]):

        """ Update the transit statistic values with a new value.

        Parameters
        ----------
        val : float
            New value
        transit_type : TransitType
            Transit type
        machine_type : MachineType | List[MachineType] | None
            Machine type(s) (disregarded if None)
        machine_id : int | None
            Machine id (disregarded if None)
        field_ids : List[int]
            Related field ids
        """

        if transit_type is ProblemTransitStats.TransitType.FROM_INIT_LOC_TO_FIELD_ACCESS:
            self._distance_from_init_locations.update(val)
            self._update_dict_value(self._machine_types_distance_from_init_locations, machine_type, val)
            self._update_dict_value(self._machines_distance_from_init_locations, machine_id, val)

            self._distance_from_init_locations_to_fields.update(val)
            self._update_dict_value(self._machine_types_distance_from_init_locations_to_fields, machine_type, val)
            self._update_dict_value(self._machines_distance_from_init_locations_to_fields, machine_id, val)
        elif transit_type is ProblemTransitStats.TransitType.FROM_INIT_LOC_TO_SILO_ACCESS:
            self._distance_from_init_locations.update(val)
            self._update_dict_value(self._machine_types_distance_from_init_locations, machine_type, val)
            self._update_dict_value(self._machines_distance_from_init_locations, machine_id, val)

            self._distance_from_init_locations_to_silos.update(val)
            self._update_dict_value(self._machine_types_distance_from_init_locations_to_silos, machine_type, val)
            self._update_dict_value(self._machines_distance_from_init_locations_to_silos, machine_id, val)
        elif transit_type is ProblemTransitStats.TransitType.FROM_SILO_ACCESS_TO_FIELD_ACCESS:
            self._distance_between_fields_and_silos.update(val)
            self._update_dict_value(self._machine_types_distance_between_fields_and_silos, machine_type, val)
            self._update_dict_value(self._machines_distance_between_fields_and_silos, machine_id, val)
        elif transit_type is ProblemTransitStats.TransitType.FROM_FIELD_ACCESS_TO_SILO_ACCESS:
            self._distance_between_fields_and_silos.update(val)
            self._update_dict_value(self._machine_types_distance_between_fields_and_silos, machine_type, val)
            self._update_dict_value(self._machines_distance_between_fields_and_silos, machine_id, val)
        elif transit_type is ProblemTransitStats.TransitType.BETWEEN_FIELD_ACCESSES_DIFFERENT_FIELDS:
            self._distance_between_field_access_points_all.update(val)
            self._update_dict_value(self._machine_types_distance_between_field_access_points_all, machine_type, val)
            self._update_dict_value(self._machines_distance_between_field_access_points_all, machine_id, val)

            self._distance_between_field_access_points_different_fields.update(val)
            self._update_dict_value(self._fields_distance_between_field_access_points_different_fields, field_ids, val)
            self._update_dict_value(self._machine_types_distance_between_field_access_points_different_fields, machine_type, val)
            self._update_dict_value(self._machines_distance_between_field_access_points_different_fields, machine_id, val)
            self._update_dict_2_value(self._machine_types_fields_distance_between_field_access_points_different_fields, field_ids, machine_type, val)
            self._update_dict_2_value(self._machines_fields_distance_between_field_access_points_different_fields, field_ids, machine_id, val)
        elif transit_type is ProblemTransitStats.TransitType.BETWEEN_FIELD_ACCESSES_SAME_FIELD:
            self._distance_between_field_access_points_all.update(val)
            self._update_dict_value(self._machine_types_distance_between_field_access_points_all, machine_type, val)
            self._update_dict_value(self._machines_distance_between_field_access_points_all, machine_id, val)

        self._distance_between_all_locations.update(val)
        self._update_dict_value(self._machine_types_distance_between_all_locations, machine_type, val)
        self._update_dict_value(self._machines_distance_between_all_locations, machine_id, val)

    @property
    def fields_distance_between_field_access_points_different_fields(self):
        return self._fields_distance_between_field_access_points_different_fields

    @property
    def distance_between_field_access_points_all(self):
        return self._distance_between_field_access_points_all

    @property
    def distance_between_field_access_points_different_fields(self):
        return self._distance_between_field_access_points_different_fields

    @property
    def distance_between_fields_and_silos (self):
        return self._distance_between_fields_and_silos

    @property
    def distance_from_init_locations(self):
        return self._distance_from_init_locations

    @property
    def distance_from_init_locations_to_field(self):
        return self._distance_from_init_locations_to_fields

    @property
    def distance_from_init_locations_to_silos(self):
        return self._distance_from_init_locations_to_silos

    @property
    def distance_between_all_locations(self):
        return self._distance_between_all_locations

    @property
    def machine_types_fields_distance_between_field_access_points_different_fields(self):
        return self._machine_types_fields_distance_between_field_access_points_different_fields

    @property
    def machine_types_distance_between_field_access_points_all(self):
        return self._machine_types_distance_between_field_access_points_all

    @property
    def machine_types_distance_between_field_access_points_different_fields(self):
        return self._machine_types_distance_between_field_access_points_different_fields

    @property
    def machine_types_distance_between_fields_and_silos (self):
        return self._machine_types_distance_between_fields_and_silos

    @property
    def machine_types_distance_from_init_locations(self):
        return self._machine_types_distance_from_init_locations

    @property
    def machine_types_distance_from_init_locations_to_fields(self):
        return self._machine_types_distance_from_init_locations_to_fields

    @property
    def machine_types_distance_from_init_locations_to_silos(self):
        return self._machine_types_distance_from_init_locations_to_silos

    @property
    def machine_types_distance_between_all_locations(self):
        return self._machine_types_distance_between_all_locations

    @property
    def machines_fields_distance_between_field_access_points_different_fields(self):
        return self._machines_fields_distance_between_field_access_points_different_fields_machines_fields_distance_between_field_access_points_different_fields

    @property
    def machines_distance_between_field_access_points_all(self):
        return self._machines_distance_between_field_access_points_all

    @property
    def machines_distance_between_field_access_points_different_fields(self):
        return self._machines_distance_between_field_access_points_different_fields

    @property
    def machines_distance_between_fields_and_silos (self):
        return self._machines_distance_between_fields_and_silos

    @property
    def machines_distance_from_init_locations(self):
        return self._machines_distance_from_init_locations

    @property
    def machines_distance_from_init_locations_to_fields(self):
        return self._machines_distance_from_init_locations_to_fields

    @property
    def machines_distance_from_init_locations_to_silos(self):
        return self._machines_distance_from_init_locations_to_silos

    @property
    def machines_distance_between_all_locations(self):
        return self._machines_distance_between_all_locations


    @staticmethod
    def _update_dict_value(values_dict: Dict, key: Any, val: float):
        if isinstance(key, list):
            for k in key:
                ProblemTransitStats._update_dict_value(values_dict, k, val)
            return

        if key is None:
            return
        stats = values_dict.get(key)
        if stats is None:
            stats = BaseStats()
            values_dict[key] = stats
        stats.update(val)

    @staticmethod
    def _update_dict_2_value(values_dict: Dict, key: Any, subkey: Any, val: float):
        if isinstance(key, list):
            for k in key:
                ProblemTransitStats._update_dict_2_value(values_dict, k, subkey, val)
            return

        if key is None or subkey is None:
            return
        stats = values_dict.get(key)
        if stats is None:
            stats = dict()
            values_dict[key] = stats
        ProblemTransitStats._update_dict_value(stats, subkey, val)


class ProblemFieldStats:

    """ Class holding the statistic values of the fields. """

    def __init__(self):
        self.field_ids = BaseStats()
        self.yield_mass_total = BaseStats()
        self.yield_mass_remaining = BaseStats()
        self.field_access_points_count = BaseStats()
        self.field_area_per_yield_mass = BaseStats()
        self.field_area = BaseStats()

class ProblemMachineStats:

    """ Class holding the statistic values of the machines (harvesters, transport vehicles). """

    def __init__(self):
        self.tv_bunker_mass_capacity = BaseStats()
        self.yield_mass_in_tvs = BaseStats()
        self.harv_transit_speed_empty = BaseStats()
        self.tv_transit_speed_empty = BaseStats()
        self.tv_transit_speed_full = BaseStats()
        self.harv_working_time_per_area = BaseStats()
        self.tv_unloading_speed_mass = BaseStats()

class ProblemSiloStats:

    """ Class holding the statistic values of the silos. """

    def __init__(self):
        self.silo_ids = BaseStats()
        self.silo_access_points_count = BaseStats()
        self.silo_mass_capacity = BaseStats()
        self.silo_access_mass_capacity = BaseStats()
        self.silo_access_sweep_duration = BaseStats()
        self.compactor_mass_per_sweep = BaseStats()

class ProblemStats:

    """ Class holding all the statistic values of the problem. """

    def __init__(self):
        self.transit = ProblemTransitStats()
        self.fields = ProblemFieldStats()
        self.machines = ProblemMachineStats()
        self.silos = ProblemSiloStats()