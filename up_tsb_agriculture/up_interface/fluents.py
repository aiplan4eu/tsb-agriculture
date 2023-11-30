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

from typing import Tuple, Set
from abc import ABC, abstractmethod
from enum import Enum, unique
import math
import warnings
from up_interface import config as conf
from up_interface.types import *
from up_interface.types_helper import *


@unique
class FluentNames(Enum):
    """ Enum holding the names of the fluents to be used """

    planning_failed = 'planning_failed'
    total_harvested_mass = 'total_harvested_mass'
    total_harvested_mass_planned = 'total_harvested_mass_planned'
    total_yield_mass_in_fields_unharvested = 'total_yield_mass_in_fields_unharvested'
    total_yield_mass_in_fields_unreserved = 'total_yield_mass_in_fields_unreserved'
    total_yield_mass_potentially_reserved = 'total_yield_mass_potentially_reserved'
    total_yield_mass_reserved = 'total_yield_mass_reserved'
    total_yield_mass_in_silos = 'total_yield_mass_in_silos'
    total_yield_mass_reserved_in_silos = 'total_yield_mass_reserved_in_silos'
    default_infield_transit_duration_to_access_point = 'default_infield_transit_duration_to_access_point'
    # HARVESTER
    harv_free = 'harv_free'
    harv_timestamp = 'harv_timestamp'
    harv_at_init_loc = 'harv_at_init_loc'
    harv_at_field = 'harv_at_field'
    harv_at_field_access = 'harv_at_field_access'
    harv_transit_time = 'harv_transit_time'
    harv_enabled_to_drive_to_loc = 'harv_enabled_to_drive_to_loc'
    harv_enabled_to_drive_to_field_exit = 'harv_enabled_to_drive_to_field_exit'
    harv_enabled_to_overload = 'harv_enabled_to_overload'
    harv_transit_speed_empty = 'harv_transit_speed_empty'
    harv_working_time_per_area = 'harv_working_time_per_area'
    harv_overload_count = 'harv_overload_count'
    harv_overload_id = 'harv_overload_id'
    harv_overloading = 'harv_overloading'
    harv_waiting_to_harvest = 'harv_waiting_to_harvest'
    harv_field_turn = 'harv_field_turn'
    harv_count_pre_assigned_field_turns = 'harv_count_pre_assigned_field_turns'
    harv_tv_turn = 'harv_tv_turn'
    harv_pre_assigned_tv_turns_left = 'harv_pre_assigned_tv_turns_left'
    harv_waiting_time = 'harv_waiting_time'
    # TRANSPORT VEHICLE
    tv_free = 'tv_free'
    tv_timestamp = 'tv_timestamp'
    tv_at_init_loc = 'tv_at_init_loc'
    tv_at_field = 'tv_at_field'
    tv_at_field_access = 'tv_at_field_access'
    tv_at_silo_access = 'tv_at_silo_access'
    tv_transit_time = 'tv_transit_time'
    tv_transit_speed_empty = 'tv_transit_speed_empty'
    tv_transit_speed_full = 'tv_transit_speed_full'
    tvs_all_enabled_to_drive_to_field = 'tvs_all_enabled_to_drive_to_field'
    tvs_all_enabled_to_arrive_in_field = 'tvs_all_enabled_to_arrive_in_field'
    tv_enabled_to_drive_to_field = 'tv_enabled_to_drive_to_field'
    tv_enabled_to_drive_to_silo = 'tv_enabled_to_drive_to_silo'
    tv_enabled_to_drive_to_field_exit = 'tv_enabled_to_drive_to_field_exit'
    tv_total_capacity_mass = 'tv_total_capacity_mass'
    tv_unloading_speed_mass = 'tv_unloading_speed_mass'
    tv_bunker_mass = 'tv_bunker_mass'
    tv_ready_to_unload = 'tv_ready_to_unload'
    tv_overload_id = 'tv_overload_id'
    tv_mass_to_overload = 'tv_mass_to_overload'
    tv_pre_assigned_harvester = 'tv_pre_assigned_harvester'
    tv_pre_assigned_turn = 'tv_pre_assigned_turn'
    tvs_waiting_to_overload_ref_count = 'tvs_waiting_to_overload_ref_count'
    tv_waiting_to_overload_id = 'tv_waiting_to_overload_id'
    tv_ready_to_overload = 'tv_ready_to_overload'
    tv_waiting_to_overload = 'tv_waiting_to_overload'
    tvs_waiting_to_drive_ref_count = 'tvs_waiting_to_drive_ref_count'
    tv_waiting_to_drive_id = 'tv_waiting_to_drive_id'
    tv_ready_to_drive = 'tv_ready_to_drive'
    tv_waiting_to_drive = 'tv_waiting_to_drive'
    tv_waiting_time = 'tv_waiting_time'
    tv_can_unload = 'tv_can_unload'
    tv_can_load = 'tv_can_load'
    # FIELD
    field_id = 'field_id'
    field_harvested = 'field_harvested'
    field_started_harvest_int = 'field_started_harvest_int'
    field_timestamp_harvested = 'field_timestamp_harvested'
    field_timestamp_started_harvest = 'field_timestamp_started_harvest'
    field_timestamp_assigned = 'field_timestamp_assigned'
    field_plan_id = 'field_plan_id'
    field_harvester = 'field_harvester'
    field_pre_assigned_harvester = 'field_pre_assigned_harvester'
    field_pre_assigned_turn = 'field_pre_assigned_turn'
    field_area_per_yield_mass = 'field_area_per_yield_mass'
    field_yield_mass_total = 'field_yield_mass_total'
    field_yield_mass_after_reserve = 'field_yield_mass_after_reserve'
    field_yield_mass_unharvested = 'field_yield_mass_unharvested'
    field_yield_mass_minus_planned = 'field_yield_mass_minus_planned'
    # FIELD ACCESS
    field_access_field = 'field_access_field'
    field_access_field_id = 'field_access_field_id'
    field_access_index = 'field_access_index'
    # SILO
    silo_id = 'silo_id'
    silo_available_capacity_mass = 'silo_available_capacity_mass'
    # SILO ACCESS
    silo_access_silo_id = 'silo_access_silo_id'
    silo_access_index = 'silo_access_index'
    silo_access_free = 'silo_access_free'
    silo_access_total_capacity_mass = 'silo_access_total_capacity_mass'
    silo_access_available_capacity_mass = 'silo_access_available_capacity_mass'
    silo_access_sweep_duration = 'silo_access_sweep_duration'
    silo_access_state_id = 'silo_access_state_id'
    silo_access_cleared = 'silo_access_cleared'
    silo_access_timestamp = 'silo_access_timestamp'
    # COMPACTOR
    compactor_silo_id = 'compactor_silo_id'
    compactor_mass_per_sweep = 'compactor_mass_per_sweep'
    compactor_free = 'compactor_free'
    # LOCATIONS
    transit_distance_init_fap = 'transit_distance_init_fap'
    transit_distance_init_sap = 'transit_distance_init_sap'
    transit_distance_fap_sap = 'transit_distance_fap_sap'
    transit_distance_fap_fap = 'transit_distance_fap_fap'
    transit_distance_sap_fap = 'transit_distance_sap_fap'


class FluentExtended:

    """ Class holding a fluent and its initial value """

    def __init__(self, fluent: Fluent, default_initial_value=None):
        self.fluent = fluent
        self.default_initial_value = default_initial_value


class FluentValueRange:

    """ Class holding values range (lower and upper bounds) of a variable (x=None: no x limit) """

    def __init__(self, _min: Union[int, float, None] = None, _max: Union[int, float, None] = None):
        self.min = _min
        self.max = _max


class FluentValueRanges:

    """ Class holding the value ranges and maximum values of problem-specific variables, which will be used to initialize numeric fluents """

    def __init__(self, with_bounds: bool = True):
        _def_max_yield_mass = 10000000000
        """ Default maximum yield mass [kg] """

        _def_max_transit_distance = 10000000000
        """ Default maximum transit distance between locations [m] """

        _def_max_infield_transit_duration = 10000000000
        """ Default maximum duration for transit inside the field [s] """

        _def_max_speed = 50
        """ Default maximum machine speed [m/s] """

        self.with_int_bounds = with_bounds
        """ If false, all integer fluents will be added without bounds """

        self.with_real_bounds = with_bounds
        """ If false, all real fluents will be added without bounds """


        self.field_ids = FluentValueRange()
        """ Range of values of field ids """

        self.silo_ids = FluentValueRange()
        """ Range of values of silo ids """

        self.tv_mass_capacity = FluentValueRange()
        """ Range of values of mass capacity of transport vehicles [kg] """

        self.count_field_accesses_in_field = FluentValueRange(0, 1000)
        """ Range of amount of field access points in a field """

        self.count_silo_accesses_in_silo = FluentValueRange(0, 1000)
        """ Range of amount of silo access points in a silo """

        self.yield_mass_in_field = FluentValueRange(0, _def_max_yield_mass)
        """ Range of yield mass in the fields  [kg]"""

        self.harv_max_transit_speed_empty = FluentValueRange(-1, _def_max_speed)
        """ Range of maximum harvester speeds (empty) [m/s] """

        self.tv_max_transit_speed_empty = FluentValueRange(-1, _def_max_speed)
        """ Range of maximum transport vehicle speeds (empty) [m/s] """

        self.tv_max_transit_speed_full = FluentValueRange(-1, _def_max_speed)
        """ Range of maximum transport vehicle speeds (full) [m/s] """

        self.harv_working_time_per_area = FluentValueRange(0, 1000)
        """ Range of harvesters' working time per area [s/m²] """

        self.tv_unloading_speed_mass = FluentValueRange(1, 100000)
        """ Range of transport vehicle unloading speeds [kg/s] """

        self.field_area_per_yield_mass = FluentValueRange(0, 1000000)
        """ Range of field area per yield mass [m²/kg] """

        self.silo_access_mass_capacity = FluentValueRange(0, INF_CAPACITY)
        """ Range of mass capacities in the silo access points [kg] """

        self.silo_access_sweep_duration = FluentValueRange(0, 10000)
        """ Range of silo access sweep durations [s] """

        self.compactor_mass_per_sweep = FluentValueRange(0, 100000)
        """ Range of mass compacted by the compactors in a sweep [kg] """


        self.count_fields_to_work: Optional[int] = None
        """ Amount of fields to be worked/harvested """

        self.count_tvs: Optional[int] = None
        """ Amount of transport vehicles """

        self.total_yield_mass_in_fields: float = _def_max_yield_mass
        """ Total amount of yield-mass in all fields [kg] """

        self.total_yield_mass_in_tvs: float = _def_max_yield_mass
        """ Total amount of yield-mass in all transport vehicles in the initial state [kg] """

        self.infield_transit_duration_to_fap: Optional[float] = None
        """ Duration of transit inside the field from/to a field access point [s] """

        self.max_harv_transit_time: Optional[float] = None
        """ Maximum transit time that a harvester can have in the given problem [s] """

        self.max_tv_transit_time: Optional[float] = None
        """ Maximum transit time that a transport vehicle can have in the given problem [s] """

        self.max_transit_distance_init_fap: float = _def_max_transit_distance
        """ Maximum transit transit distance from machines' initial locations to field access points [m] """

        self.max_transit_distance_init_sap: float = _def_max_transit_distance
        """ Maximum transit transit distance from machines' initial locations to silo access points [m] """

        self.max_transit_distance_fap_sap: float = _def_max_transit_distance
        """ Maximum transit transit distance from field access points to silo access points [m] """

        self.max_transit_distance_fap_fap: float = _def_max_transit_distance
        """ Maximum transit transit distance between field access points [m] """

        self.max_transit_distance_sap_fap: float = _def_max_transit_distance
        """ Maximum transit transit distance from silo access points to field access points [m] """

        self.max_silo_mass_capacity: float = INF_CAPACITY
        """ Maximum mass capacity in the silos [kg] """

        self.max_overloading_activities_all: Optional[int] = None
        """ Maximum amount of overloading activities that can exist in the given problem """

        self.max_overloading_activities_field: Optional[int] = None
        """ Maximum amount of overloading activities that an field can have in the given problem """

        self.max_process_duration: Optional[float] = None
        """ Maximum possible duration of the process for the given problem """


class FluentsManagerBase(ABC):

    """ Base class of the FluentsManager """

    def __init__(self):
        self._fluents: Dict[str, FluentExtended] = dict()
        self._fluents_initial_values: Dict[str, List[Tuple[Union[Tuple, Any, None]], Any]] = dict()
        self._name_values = [member.value for member in FluentNames]
        self._initialized: bool = False

    def initialize(self,
                   problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings,
                   fluent_value_ranges: FluentValueRanges = FluentValueRanges()):

        """ Initialize the FluentsManager with the given problem settings and fluents' value ranges

        Parameters
        ----------
        problem_settings : config.GeneralProblemSettings
            Problem settings
        fluent_value_ranges : FluentValueRanges
            Holds all value ranges and maximum values of problem-specific variables, which will be used to initialize numeric fluents
        """

        self._initialize(problem_settings, fluent_value_ranges)
        self._initialized = True

    @abstractmethod
    def _initialize(self,
                    problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings,
                    fluent_value_ranges: FluentValueRanges = FluentValueRanges()):
        """ (Child implementation) Initialize the FluentsManager with the given problem settings and fluents' value ranges

        Parameters
        ----------
        problem_settings : config.GeneralProblemSettings
            Problem settings
        fluent_value_ranges : FluentValueRanges
            Holds all value ranges and maximum values to be set to the fluents during their initialization
        """
        pass

    @abstractmethod
    def fluent_enabled_for_problem_settings(self,
                                            fluent: Union[str, Fluent],
                                            problem_settings: conf.GeneralProblemSettings) \
            -> bool:
        """ (Child implementation) Check if a fluent is enabled for the given problem settings.

        Parameters
        ----------
        fluent : str, Fluent
            Fluent or fluent name
        problem_settings : config.GeneralProblemSettings
            Problem settings
        Returns
        -------
        enabled : bool
            True if the fluent is enabled
        """
        pass

    def add_fluents_to_problem(self, problem: Problem,
                               fluents_to_add: Optional[Set[Union[str, FluentNames]]] = None,
                               check_fluents: bool = True):

        """ Add all registered fluents to a problem.

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_to_add : Set[str | FluentNames]
            Names of the fluents to be added (if None -> all registered fluents will be added)
        check_fluents : bool
            If True, it will check if values were added for non-registered fluents and print a warning
        """

        if not self._initialized:
            raise Exception("The fluents manager has not been initialized ")

        def get_fluent_value(fluent_: Fluent, value, allow_none: bool = True):
            if value is None:
                if allow_none:
                    return None
                raise ValueError(f'Invalid value: {value}')

            f_type = get_up_type_as_str(fluent_)
            if is_up_type_bool(f_type) and isinstance(value, bool):
                _value = Bool(value)
            elif is_up_type_int(f_type) and isinstance(value, int):
                _value = Int(value)
            elif is_up_type_real(f_type) and isinstance(value, (int, float)):
                _value = get_up_real(value)
            else:
                _value = value

            v_type = get_up_type_as_str(_value)
            if v_type != f_type:
                raise ValueError(f'Missmatch in value ({v_type}) and fluent ({f_type}) types')
            return _value

        if fluents_to_add is None:
            fluents_dict = self._fluents
        else:
            fluents_dict = dict()
            for name in fluents_to_add:
                fluent_ext = self.get_fluent_ext(name)
                assert fluent_ext is not None, f"Fluent {name} is not registered"
                fluents_dict[name] = fluent_ext

        for name, fluent_ext in fluents_dict.items():
            fluent = fluent_ext.fluent
            problem.add_fluent(fluent,
                               default_initial_value=get_fluent_value(fluent, fluent_ext.default_initial_value, True))
            fluent_vals = self._fluents_initial_values.get(name)
            if fluent_vals is None:
                continue
            for params, init_val in fluent_vals:
                _init_val = get_fluent_value(fluent, init_val, False)
                if params is None:
                    problem.set_initial_value(fluent(), _init_val)
                elif isinstance(params, tuple) or isinstance(params, list):
                    problem.set_initial_value(fluent(*params), _init_val)
                else:
                    problem.set_initial_value(fluent(params), _init_val)

        if check_fluents:
            for name in self._fluents_initial_values.keys():
                if name not in self._fluents.keys():
                    warnings.warn(f'Initial values were added for non-registered fluent {name}')

    def add_fluent_initial_value(self,
                                 fluent_name: Union[str, FluentNames],
                                 params: Union[Tuple, Any, None],
                                 value: Any):

        """ Register (internally) the initial value of a fluent.

        Parameters
        ----------
        fluent_name : str, FluentNames
            Fluent name (or enum)
        params : Tuple, Any, None
            Fluent parameters
        value: Any
            Fluent initial value
        """

        if isinstance(fluent_name, FluentNames):
            _fluent_name = fluent_name.value
        else:
            _fluent_name = fluent_name
        if _fluent_name not in self._name_values:
            raise ValueError(f'The fluent name {fluent_name} does not correspond to any of the supported fluent names')
        fluent_vals = self._fluents_initial_values.get(_fluent_name)
        if fluent_vals is None:
            fluent_vals = list()
            self._fluents_initial_values[_fluent_name] = fluent_vals
        fluent_vals.append( (params, value) )

    @property
    def fluents(self) -> Dict[str, FluentExtended]:
        """ Get the (extended) fluents (fluents + initial values)

        Returns
        -------
        fluents : Dict[str, FluentExtended]
            Fluents dictionary: key: fluent name ; value: extended fluent (fluent + initial value)
        """
        return self._fluents

    def get_fluent(self, name: Union[FluentNames, str]) -> Union[Fluent, None]:
        """ Get a specific fluent

        Parameters
        ----------
        name : str, FluentNames
            Fluent name (or enum)

        Returns
        -------
        fluent : Fluent, None
            The respective fluent or None if a fluent with the given name is not registered
        """

        f_ext = self.get_fluent_ext(name)
        if f_ext is None:
            return None
            # raise ValueError(f'The fluent {name} does not exist')
        return f_ext.fluent

    def get_fluent_ext(self, name: Union[FluentNames, str]) -> Optional[FluentExtended]:
        """ Get a specific (extended) fluent

        Parameters
        ----------
        name : str, FluentNames
            Fluent name (or enum)

        Returns
        -------
        fluent : Fluent, None
            The respective (extended) fluent or None if a fluent with the given name is not registered
        """

        if isinstance(name, str):
            f_ext = self._fluents.get(name)
        elif isinstance(name, FluentNames):
            f_ext = self._fluents.get(name.value)
        else:
            raise TypeError(f'Invalid name type')
        if f_ext is None:
            return None
            # raise ValueError(f'The fluent {name} does not exist')
        return f_ext

    def _add_fluent(self,
                    problem_settings: conf.GeneralProblemSettings,
                    fluent: Fluent,
                    default_initial_value: Any = None):
        """ Register (internally) a fluent and its default initial value

        Parameters
        ----------
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        fluent : Fluent
            Fluent
        default_initial_value :
            Default fluent initial value
        """

        if fluent.name not in self._name_values:
            raise ValueError(f'The fluent name {fluent.name} does not correspond to any of the supported fluent names')
        if fluent.name in self._fluents.keys():
            print(f'[WARN] Fluent {fluent.name} was already added and will be overwritten')

        if not self.fluent_enabled_for_problem_settings(fluent, problem_settings):
            print(f'[WARN] Fluent {fluent.name} is not enabled for the given problem settings')
            return

        self._fluents[fluent.name] = FluentExtended(fluent, default_initial_value)


class FluentsManager(FluentsManagerBase):
    """ Default FluentsManager """

    def __init__(self):

        super(FluentsManager, self).__init__()

        fn = FluentNames

        # Establish which fluents are exclusive for temporal or sequential planning

        self.__fluents_only_temporal = {
            fn.total_harvested_mass_planned.value,
            fn.total_yield_mass_in_fields_unreserved.value,
            fn.total_yield_mass_potentially_reserved.value,
            fn.total_yield_mass_reserved.value,
            fn.harv_free.value,
            fn.harv_enabled_to_drive_to_loc.value,
            fn.harv_enabled_to_drive_to_field_exit.value,
            fn.harv_enabled_to_overload.value,
            fn.harv_overload_count.value,
            fn.harv_overload_id.value,
            fn.harv_overloading.value,
            fn.harv_waiting_to_harvest.value,
            fn.tv_free.value,
            fn.tvs_all_enabled_to_drive_to_field.value,
            fn.tvs_all_enabled_to_arrive_in_field.value,
            fn.tv_enabled_to_drive_to_field.value,
            fn.tv_enabled_to_drive_to_silo.value,
            fn.tv_enabled_to_drive_to_field_exit.value,
            fn.tv_overload_id.value,
            fn.tv_mass_to_overload.value,
            fn.tvs_waiting_to_overload_ref_count.value,
            fn.tv_waiting_to_overload_id.value,
            fn.tv_ready_to_overload.value,
            fn.tv_waiting_to_overload.value,
            fn.tvs_waiting_to_drive_ref_count.value,
            fn.tv_waiting_to_drive_id.value,
            fn.tv_ready_to_drive.value,
            fn.tv_waiting_to_drive.value,
            fn.field_yield_mass_after_reserve.value,
            fn.field_yield_mass_minus_planned.value
        }

        self.__fluents_only_sequential = {
            fn.total_yield_mass_in_fields_unharvested.value,
            fn.field_started_harvest_int.value,
            fn.field_timestamp_harvested.value,
            fn.field_timestamp_started_harvest.value,
            fn.field_timestamp_assigned.value,
            fn.harv_timestamp.value,
            fn.harv_waiting_time.value,
            fn.tv_timestamp.value,
            fn.tv_waiting_time.value,
            fn.silo_access_timestamp.value
        }

    def fluent_enabled_for_problem_settings(self,
                                            fluent: Union[str, Fluent],
                                            problem_settings: conf.GeneralProblemSettings) -> bool:
        """  Check if a fluent is enabled for the given problem settings.

        Parameters
        ----------
        fluent : str, Fluent
            Fluent or fluent name
        problem_settings : config.GeneralProblemSettings
            Problem settings
        Returns
        -------
        enabled : bool
            True if the fluent is enabled
        """

        if isinstance(fluent, Fluent):
            fluent_name = fluent.name
        else:
            fluent_name = fluent
        if problem_settings.planning_type is conf.PlanningType.TEMPORAL \
                and fluent_name in self.__fluents_only_sequential:
            return False
        elif problem_settings.planning_type is conf.PlanningType.SEQUENTIAL \
                and fluent_name in self.__fluents_only_temporal:
            return False

        fn = FluentNames

        if problem_settings.control_windows.enable_driving_opening_time is None \
                or problem_settings.control_windows.enable_driving_opening_time <= 0.0:
            if fluent_name == fn.harv_enabled_to_drive_to_loc.value \
                    or fluent_name == fn.harv_enabled_to_drive_to_field_exit.value \
                    or fluent_name == fn.tv_enabled_to_drive_to_silo.value \
                    or fluent_name == fn.tv_enabled_to_drive_to_field_exit.value:
                return False

        if problem_settings.control_windows.enable_overload_opening_time is None \
                or problem_settings.control_windows.enable_overload_opening_time <= 0.0:
            if fluent_name == fn.harv_enabled_to_overload.value:
                return False

        if problem_settings.cost_windows.waiting_harvest_opening_time is None \
                or problem_settings.cost_windows.waiting_harvest_opening_time <= 0.0:
            if fluent_name == fn.harv_waiting_to_harvest.value:
                return False

        if problem_settings.control_windows.enable_driving_tvs_to_field_opening_time is None \
                or problem_settings.control_windows.enable_driving_tvs_to_field_opening_time <= 0.0:
            if fluent_name == fn.tvs_all_enabled_to_drive_to_field.value \
                    or fluent_name == fn.tv_enabled_to_drive_to_field.value:
                return False

        if problem_settings.control_windows.enable_arriving_tvs_in_field_opening_time is None \
                or problem_settings.control_windows.enable_arriving_tvs_in_field_opening_time <= 0.0:
            if fluent_name == fn.tvs_all_enabled_to_arrive_in_field.value:
                return False

        if problem_settings.cost_windows.waiting_overload_opening_time is None \
                or problem_settings.cost_windows.waiting_overload_opening_time <= 0.0:
            if problem_settings.cost_windows.use_old_implementation_waiting_overload:
                if fluent_name == fn.tvs_waiting_to_overload_ref_count.value \
                        or fluent_name == fn.tv_waiting_to_overload_id.value \
                        or fluent_name == fn.tv_ready_to_overload.value \
                        or fluent_name == fn.tv_waiting_to_overload.value:
                    return False
        else:
            if problem_settings.cost_windows.use_old_implementation_waiting_overload:
                if fluent_name == fn.tvs_waiting_to_overload_ref_count.value \
                        or fluent_name == fn.tv_waiting_to_overload_id.value \
                        or fluent_name == fn.tv_ready_to_overload.value:
                    return False
            else:
                if fluent_name == fn.tv_waiting_to_overload.value:
                    return False

        if ( ( problem_settings.cost_windows.waiting_drive_opening_time is None
               or problem_settings.cost_windows.waiting_drive_opening_time <= 0.0 )
              and ( problem_settings.cost_windows.waiting_drive_from_silo_opening_time is None
                    or problem_settings.cost_windows.waiting_drive_from_silo_opening_time <= 0.0 ) ):
            if (fluent_name == fn.tvs_waiting_to_drive_ref_count.value
                    or fluent_name == fn.tv_waiting_to_drive_id.value
                    or fluent_name == fn.tv_ready_to_drive.value
                    or fluent_name == fn.tv_waiting_to_drive.value):
                return False
        else:
            if problem_settings.cost_windows.use_old_implementation_waiting_drive:
                if fluent_name == fn.tvs_waiting_to_drive_ref_count.value \
                        or fluent_name == fn.tv_waiting_to_drive_id.value \
                        or fluent_name == fn.tv_ready_to_drive.value:
                    return False
            else:
                if fluent_name == fn.tv_waiting_to_drive.value:
                    return False

        if problem_settings.silo_planning_type is not conf.SiloPlanningType.WITH_SILO_ACCESS_CAPACITY_AND_COMPACTION:
            if fluent_name == fn.compactor_silo_id.value \
                    or fluent_name == fn.compactor_mass_per_sweep.value \
                    or fluent_name == fn.compactor_free.value:
                return False

        if problem_settings.silo_planning_type is conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY:
            if fluent_name == fn.tv_ready_to_unload.value \
                    or fluent_name == fn.silo_access_timestamp.value:
                return False

        return True

    def _initialize(self,
                    problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings,
                    fluent_value_ranges: FluentValueRanges = FluentValueRanges()):
        """ Initialize the FluentsManager with the given problem settings and fluents' value ranges

        Parameters
        ----------
        problem_settings : config.GeneralProblemSettings
            Problem settings
        fluent_value_ranges : FluentValueRanges
            Holds all value ranges and maximum values of problem-specific variables, which will be used to initialize numeric fluents
        """

        fvr = fluent_value_ranges
        fn = FluentNames

        _max_mass_factor = 2  # to be sure the limits will not be exceeded (otherwise the planner sometimes fails to yield a plan)

        # --------------PROCESS FLUENTS--------------

        # [BOOL] Has the plan failed?
        # Workaround to be used as precondition for all actions
        self._add_fluent(problem_settings, 
                         Fluent(fn.planning_failed.value, BoolType()),
                         default_initial_value=False)

        # [REAL] Total yield mass harvested in all fields
        self._add_fluent(problem_settings, 
                         Fluent(fn.total_harvested_mass.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.total_yield_mass_in_fields * _max_mass_factor)),
                         default_initial_value=0.0)

        # [Real] Total remaining (unharvested) yield mass in all fields
        self._add_fluent(problem_settings, 
                         Fluent(fn.total_yield_mass_in_fields_unharvested.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.total_yield_mass_in_fields * _max_mass_factor)),
                         default_initial_value=fvr.total_yield_mass_in_fields)

        # [REAL] Total yield mass planned to be harvested in all fields (i.e., the harvester started the harvesting window)
        self._add_fluent(problem_settings, 
                         Fluent(fn.total_harvested_mass_planned.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.total_yield_mass_in_fields * _max_mass_factor)),
                         default_initial_value=0.0)

        # [Real/CONST] Total remaining (unreserved) yield mass in all fields
        self._add_fluent(problem_settings, 
                         Fluent(fn.total_yield_mass_in_fields_unreserved.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.total_yield_mass_in_fields * _max_mass_factor)),
                         default_initial_value=fvr.total_yield_mass_in_fields)

        # [Real] Total potentially reserved yield mass (planned) - Before we actually know how much will be reserved
        self._add_fluent(problem_settings, 
                         Fluent(fn.total_yield_mass_potentially_reserved.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.total_yield_mass_in_fields * _max_mass_factor)),
                         default_initial_value=0.0)

        # [Real] Total reserved yield mass (planned)
        self._add_fluent(problem_settings, 
                         Fluent(fn.total_yield_mass_reserved.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.total_yield_mass_in_fields * _max_mass_factor)),
                         default_initial_value=0.0)


        _max_mass_to_store = None if fvr.total_yield_mass_in_fields is None or fvr.total_yield_mass_in_tvs is None \
            else math.ceil( fvr.total_yield_mass_in_fields + fvr.total_yield_mass_in_tvs ) * _max_mass_factor

        # [REAL] Total mass stored at the silos
        self._add_fluent(problem_settings, 
                         Fluent(fn.total_yield_mass_in_silos.value,
                                self._get_real_type(fvr.with_real_bounds, 0, _max_mass_to_store)),
                         default_initial_value=0.0)

        # [REAL] Total mass reserved to be stored at the silos
        self._add_fluent(problem_settings, 
                         Fluent(fn.total_yield_mass_reserved_in_silos.value,
                                self._get_real_type(fvr.with_real_bounds, 0, _max_mass_to_store)),
                         default_initial_value=0.0)

        # [Real/CONST] Default infield transit duration from/to an access point
        # @todo Used to access the value from the problem object
        self._add_fluent(problem_settings,
                         Fluent(fn.default_infield_transit_duration_to_access_point.value,
                                self._get_real_type(fvr.with_real_bounds, fvr.infield_transit_duration_to_fap, fvr.infield_transit_duration_to_fap)),
                         default_initial_value=self._get_fraction(fvr.infield_transit_duration_to_fap))

        # --------------MACHINE FLUENTS--------------

        # [BOOL] Is the machine available
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_free.value, BoolType(), machine=Harvester),
                         default_initial_value=True)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_free.value, BoolType(), machine=TransportVehicle),
                         default_initial_value=True)

        # [Real] The machine timestamp
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_timestamp.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.max_process_duration),
                                machine=Harvester),
                         default_initial_value=0)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_timestamp.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.max_process_duration),
                                machine=TransportVehicle),
                         default_initial_value=0)

        # [MachineLocation] Location of a specified machine
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_at_init_loc.value, MachineInitLoc, machine=Harvester),
                         default_initial_value=None)
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_at_field.value, Field, machine=Harvester), None)
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_at_field_access.value, FieldAccess, machine=Harvester),
                         default_initial_value=None)

        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_at_init_loc.value, MachineInitLoc, machine=TransportVehicle),
                         default_initial_value=None)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_at_field.value, Field, machine=TransportVehicle),
                         default_initial_value=None)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_at_field_access.value, FieldAccess, machine=TransportVehicle),
                         default_initial_value=None)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_at_silo_access.value, SiloAccess, machine=TransportVehicle),
                         default_initial_value=None)

        # [REAL] Machine transit time (off field)
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_transit_time.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.max_harv_transit_time),
                                machine=Harvester),
                         default_initial_value=0)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_transit_time.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.max_tv_transit_time),
                                machine=TransportVehicle),
                         default_initial_value=0)

        # [REAL] Machine transit speeds (off field)
        min_val = -1 if fvr.harv_max_transit_speed_empty.min is None else fvr.harv_max_transit_speed_empty.min
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_transit_speed_empty.value,
                                self._get_real_type(fvr.with_real_bounds, min_val, fvr.harv_max_transit_speed_empty.max),
                                machine=Harvester),
                         default_initial_value=self._get_fraction(min_val))
        min_val = self._get_fraction( -1 if fvr.tv_max_transit_speed_empty.min is None else fvr.tv_max_transit_speed_empty.min )
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_transit_speed_empty.value,
                                self._get_real_type(fvr.with_real_bounds, min_val, fvr.tv_max_transit_speed_empty.max),
                                machine=TransportVehicle),
                         default_initial_value=self._get_fraction(min_val))
        min_val = self._get_fraction( -1 if fvr.tv_max_transit_speed_full.min is None else fvr.tv_max_transit_speed_full.min )
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_transit_speed_full.value,
                                self._get_real_type(fvr.with_real_bounds, min_val, fvr.tv_max_transit_speed_full.max),
                                machine=TransportVehicle),
                         default_initial_value=self._get_fraction(min_val))

        # [BOOL] Workaround to enable/force planning of driving to a field or silo in a window
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_enabled_to_drive_to_loc.value, BoolType(), machine=Harvester),
                         default_initial_value=True)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tvs_all_enabled_to_drive_to_field.value, BoolType()),
                         default_initial_value=True)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tvs_all_enabled_to_arrive_in_field.value, BoolType(), field=Field),
                         default_initial_value=False)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_enabled_to_drive_to_field.value, BoolType(), machine=TransportVehicle),
                         default_initial_value=True)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_enabled_to_drive_to_silo.value, BoolType(), machine=TransportVehicle),
                         default_initial_value=True)

        # [BOOL] Workaround to enable/force planning of driving to a field exit in a window
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_enabled_to_drive_to_field_exit.value, BoolType(), machine=Harvester),
                         default_initial_value=True)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_enabled_to_drive_to_field_exit.value, BoolType(), machine=TransportVehicle),
                         default_initial_value=True)

        # [BOOL] Workaround to enable/force planning of harvesting+overload in a window
        #        0 := disable overloading for harvester in cases where it is acceptable (e.g. it arrived in the field or finished the previous overload and must wait for a TV)
        #       -1 := disable in critical cases (e.g., the corresponding TV is in the field and should start overloading right ahead)
        #       >0 := overloading id of the next TV
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_enabled_to_overload.value,
                                self._get_int_type(fvr.with_int_bounds, -1, fvr.max_overloading_activities_field),
                                machine=Harvester),
                         default_initial_value=0)

        # [REAL] Time the machine spends waiting to overload or drive [s]
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_waiting_time.value,
                                self._get_real_type(fvr.with_real_bounds, 0, None),
                                machine=Harvester),
                         default_initial_value=0)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_waiting_time.value,
                                self._get_real_type(fvr.with_real_bounds, 0, None),
                                machine=TransportVehicle),
                         default_initial_value=0)

        # --------------HARVESTER FLUENTS--------------

        # [REAL/CONST] Time needed by a harvester to work one square meter [s/m2]
        min_val = 0 if fvr.harv_working_time_per_area.min is None else fvr.harv_working_time_per_area.min
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_working_time_per_area.value,
                                self._get_real_type(fvr.with_real_bounds, min_val, fvr.harv_working_time_per_area.max),
                                machine=Harvester),
                         default_initial_value=self._get_fraction(min_val))

        # [INT] Number of planned overloads
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_overload_count.value,
                                self._get_int_type(fvr.with_int_bounds, -1, fvr.max_overloading_activities_field),
                                machine=Harvester),
                         default_initial_value=-1)

        # [INT] Current overload
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_overload_id.value,
                                self._get_int_type(fvr.with_int_bounds, -1, fvr.max_overloading_activities_field),
                                machine=Harvester),
                         default_initial_value=-1)

        # [BOOL] The harvester is overloading
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_overloading.value, BoolType(), machine=Harvester),
                         default_initial_value=False)

        # [BOOL] The harvester is waiting to harvest
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_waiting_to_harvest.value, BoolType(), machine=Harvester),
                         default_initial_value=False)

        # [INT] Current field turn
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_field_turn.value,
                                self._get_int_type(fvr.with_int_bounds, 0, fvr.count_fields_to_work),
                                # self._get_int_type(fvr.with_int_bounds, 0, None if fvr.count_fields_to_work is None else 10*fvr.count_fields_to_work),  #@todo apparently tamer tries to plan invalid actions that try to set this fluent over the limit
                                machine=Harvester),
                         default_initial_value=0)

        # [INT] Amount of (field) turns assigned to the harvester
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_count_pre_assigned_field_turns.value,
                                self._get_int_type(fvr.with_int_bounds, 0, fvr.count_fields_to_work),
                                machine=Harvester),
                         default_initial_value=0)

        # [INT] Current TV turn
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_tv_turn.value,
                                self._get_int_type(fvr.with_int_bounds, 0, fvr.max_overloading_activities_all),
                                # self._get_int_type(fvr.with_int_bounds, 0, None if fvr.max_overloading_activities_all is None else 10*fvr.max_overloading_activities_all),  #@todo apparently tamer tries to plan invalid actions that try to set this fluent over the limit
                                machine=Harvester),
                         default_initial_value=0)

        # [INT] Amount of (tv) overloading turns left assigned to the harvester
        self._add_fluent(problem_settings, 
                         Fluent(fn.harv_pre_assigned_tv_turns_left.value,
                                self._get_int_type(fvr.with_int_bounds, -fvr.max_overloading_activities_all if fvr.max_overloading_activities_all is not None else None,
                                                   fvr.count_tvs),
                                machine=Harvester),
                         default_initial_value=0)

        # --------------TV FLUENTS--------------

        # [REAL] Machine total mass capacity
        min_val = 0 if fvr.tv_mass_capacity.min is None else fvr.tv_mass_capacity.min
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_total_capacity_mass.value,
                                self._get_real_type(fvr.with_real_bounds, min_val, fvr.tv_mass_capacity.max),
                                machine=TransportVehicle),
                         default_initial_value=self._get_fraction(min_val))

        # [REAL/CONST] Machine unloading speed [kg/s] / [m³/s]
        min_val = 1 if fvr.tv_unloading_speed_mass.min is None else fvr.tv_unloading_speed_mass.min
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_unloading_speed_mass.value,
                                self._get_real_type(fvr.with_real_bounds, min_val, fvr.tv_unloading_speed_mass.max),
                                machine=TransportVehicle),
                         default_initial_value=self._get_fraction(min_val))

        # [REAL] Machine current bunker mass and volume (volume not supported at the moment)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_bunker_mass.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.tv_mass_capacity.max),
                                machine=TransportVehicle),
                         default_initial_value=0)

        # [BOOL] Is the transport vehicle at a silo access ready to unload
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_ready_to_unload.value, BoolType(), machine=TransportVehicle),
                         default_initial_value=False)

        # [INT] Reserved overload
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_overload_id.value,
                                self._get_int_type(fvr.with_int_bounds, -1, fvr.max_overloading_activities_field),
                                machine=TransportVehicle),
                         default_initial_value=-1)

        # [REAL] Mass to be overloaded to the TV
        self._add_fluent(problem_settings,  Fluent(fn.tv_mass_to_overload.value,
                                                   self._get_real_type(fvr.with_real_bounds, 0, fvr.tv_mass_capacity.max),
                                                   machine=TransportVehicle),
                         default_initial_value=0)

        # [Harvester] Harvester pre-assigned to the TV (assignment done externally before planning)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_pre_assigned_harvester.value, Harvester, machine=TransportVehicle),
                         default_initial_value=None)

        # [INT] Pre-assigned turn in which the TV must overload from the pre-assigned harvester (assignment done externally before planning)
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_pre_assigned_turn.value, self._get_int_type(fvr.with_int_bounds, 0, fvr.count_tvs), machine=TransportVehicle),
                         default_initial_value=0)

        # [INT] Reference value to be used to assign tv_waiting_to_overload_id in the order the tvs start waiting
        self._add_fluent(problem_settings, 
                         Fluent(fn.tvs_waiting_to_overload_ref_count.value,
                                self._get_int_type(fvr.with_int_bounds, 1, fvr.max_overloading_activities_field)),
                         default_initial_value=1)

        # [INT] If the transport vehicle is waiting in the field to start the overload, it will get an id (count) > 0
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_waiting_to_overload_id.value,
                                self._get_int_type(fvr.with_int_bounds, 0, fvr.max_overloading_activities_field),
                                machine=TransportVehicle),
                         default_initial_value=0)

        # [INT] Is the transport vehicle in the field ready to start the overload (0: False, 1: True)
        # @note: we use int instead of bool to make arithmetic operations
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_ready_to_overload.value,
                                self._get_int_type(fvr.with_int_bounds, 0, 1),
                                machine=TransportVehicle),
                         default_initial_value=0)

        # [BOOL] Is the transport vehicle waiting in the field to start the overload
        # @todo Remove fluent when the tv_waiting_to_drive_id approach is working
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_waiting_to_overload.value, BoolType(), machine=TransportVehicle),
                         default_initial_value=False)


        _max_tv_transits = None
        if fvr.count_fields_to_work is not None \
                and fvr.count_tvs is not None \
                and fvr.max_overloading_activities_field is not None :
            _max_tv_transits = fvr.max_overloading_activities_field \
                               * 4  # to_silo(init) + to_field + to_field_exit + to_silo

        # [INT] Reference value to be used to assign tv_waiting_to_drive_id in the order the tvs start waiting
        self._add_fluent(problem_settings, 
                         Fluent(fn.tvs_waiting_to_drive_ref_count.value,
                                self._get_int_type(fvr.with_int_bounds, 1, _max_tv_transits)),
                         default_initial_value=1)

        # [INT] If the transport vehicle is waiting to start driving, it will get an id (count) > 0
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_waiting_to_drive_id.value,
                                self._get_int_type(fvr.with_int_bounds, 0, _max_tv_transits),
                                machine=TransportVehicle),
                         default_initial_value=0)

        # [INT] Is the transport vehicle ready to start driving (0: False, 1: True)
        # @note: we use int instead of bool to make arithmetic operations
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_ready_to_drive.value,
                                self._get_int_type(fvr.with_int_bounds, 0, 1),
                                machine=TransportVehicle),
                         default_initial_value=0)

        # [BOOL] Is the transport vehicle waiting in to start driving
        # @todo Remove fluent when the tv_waiting_to_drive_id approach is working
        self._add_fluent(problem_settings, 
                         Fluent(fn.tv_waiting_to_drive.value, BoolType(), machine=TransportVehicle),
                         default_initial_value=False)

        # [BOOL] The TV has yield to unload
        self._add_fluent(problem_settings,
                         Fluent(fn.tv_can_unload.value, BoolType(), machine=TransportVehicle),
                         default_initial_value=False)

        # [BOOL] The TV has enough capacity to overload
        self._add_fluent(problem_settings,
                         Fluent(fn.tv_can_load.value, BoolType(), machine=TransportVehicle),
                         default_initial_value=True)

        # --------------FIELD FLUENTS--------------

        # [INT/CONST] Field id
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_id.value,
                                self._get_int_type(fvr.with_int_bounds, fvr.field_ids.min, fvr.field_ids.max),
                                field=Field),
                         default_initial_value=problem_settings.id_undef)

        # [BOOL] Is a field completely harvested
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_harvested.value, BoolType(), field=Field),
                         default_initial_value=False)

        # [Int] A field has started to being harvested (1: started ; 0: not stated)
        self._add_fluent(problem_settings,
                         Fluent(fn.field_started_harvest_int.value, self._get_int_type(fvr.with_int_bounds, 0,1), field=Field),
                         default_initial_value=0)

        # [Real] Timestamp of when the field was finished
        self._add_fluent(problem_settings,
                         Fluent(fn.field_timestamp_harvested.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.max_process_duration),
                                field=Field),
                         default_initial_value=0)

        # [Real] Timestamp of when the field was started to be harvested
        self._add_fluent(problem_settings,
                         Fluent(fn.field_timestamp_started_harvest.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.max_process_duration),
                                field=Field),
                         default_initial_value=0)

        # [Real] Timestamp of when the field was assigned to a harvester
        self._add_fluent(problem_settings,
                         Fluent(fn.field_timestamp_assigned.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.max_process_duration),
                                field=Field),
                         default_initial_value=0)

        # [INT] Current plan id for the field (field planning)
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_plan_id.value,
                                self._get_int_type(fvr.with_int_bounds, problem_settings.id_undef, INF_INTEGER),
                                field=Field),
                         default_initial_value=None)

        # [Harvester] Harvester assigned to harvest the field
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_harvester.value, Harvester, field=Field),
                         default_initial_value=None)

        # [Harvester] Harvester pre-assigned to harvest the field (assignment done externally before planning)
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_pre_assigned_harvester.value, Harvester, field=Field),
                         default_initial_value=None)

        # [INT] Pre-assigned turn in which the field must be harvested by the pre-assigned harvester (assignment done externally before planning)
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_pre_assigned_turn.value,
                                self._get_int_type(fvr.with_int_bounds, 0, fvr.count_fields_to_work), field=Field),
                         default_initial_value=0)

        # [Real/CONST] Amount of area that must be covered to harvest one kg of yield [m2/kg]
        min_val = 0 if fvr.field_area_per_yield_mass.min is None else fvr.field_area_per_yield_mass.min
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_area_per_yield_mass.value,
                                self._get_real_type(fvr.with_real_bounds, min_val, fvr.field_area_per_yield_mass.max),
                                field=Field),
                         default_initial_value=self._get_fraction(min_val))

        # [Real/CONST] Total yield mass in the field
        min_val = 0 if fvr.yield_mass_in_field.min is None else fvr.yield_mass_in_field.min
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_yield_mass_total.value,
                                self._get_real_type(fvr.with_real_bounds, min_val, fvr.yield_mass_in_field.max * _max_mass_factor),
                                field=Field),
                         default_initial_value=0)

        # [Real] Yield mass in the field after overload reservations (planned)
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_yield_mass_after_reserve.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.yield_mass_in_field.max * _max_mass_factor),
                                field=Field),
                         default_initial_value=0)

        # [Real] Remaining yield mass in the field
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_yield_mass_unharvested.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.yield_mass_in_field.max * _max_mass_factor),
                                field=Field),
                         default_initial_value=0)

        # [Real] Remaining yield mass in the field (minus the one being harvested)
        self._add_fluent(problem_settings,
                         Fluent(fn.field_yield_mass_minus_planned.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.yield_mass_in_field.max * _max_mass_factor),
                                field=Field),
                         default_initial_value=0)

        # --------------FIELD-ACCESS FLUENTS--------------

        # [OBJECT/CONST] Field to which the access point belongs
        self._add_fluent(problem_settings, Fluent(fn.field_access_field.value, Field, access_point=FieldAccess))

        # [INT/CONST] Id of the field to which the access point belongs
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_access_field_id.value,
                                self._get_int_type(fvr.with_int_bounds, fvr.field_ids.min, fvr.field_ids.max),
                                access_point=FieldAccess),
                         default_initial_value=problem_settings.id_undef)

        # [INT/CONST] Index of the field access point within the field's list
        self._add_fluent(problem_settings, 
                         Fluent(fn.field_access_index.value,
                                self._get_int_type(fvr.with_int_bounds, 0, fvr.count_field_accesses_in_field.max - 1),
                                access_point=FieldAccess),
                         default_initial_value=0)

        # --------------SILO TYPES--------------

        # [INT/CONST] Silo id
        self._add_fluent(problem_settings, 
                         Fluent(fn.silo_id.value,
                                self._get_int_type(fvr.with_int_bounds, fvr.silo_ids.min, fvr.silo_ids.max),
                                silo=Silo),
                         default_initial_value=problem_settings.id_undef)

        # [REAL] Silo available mass capacity
        self._add_fluent(problem_settings, 
                         Fluent(fn.silo_available_capacity_mass.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.max_silo_mass_capacity),
                                silo=Silo),
                         default_initial_value=0)

        # --------------SILO-ACCESS FLUENTS--------------

        # [INT/CONST] Id of the silo to which the access point belongs
        self._add_fluent(problem_settings, 
                         Fluent(fn.silo_access_silo_id.value,
                                self._get_int_type(fvr.with_int_bounds, fvr.silo_ids.min, fvr.silo_ids.max),
                                access_point=SiloAccess),
                         default_initial_value=problem_settings.id_undef)

        # [INT/CONST] Index of the field access point within the field's list
        self._add_fluent(problem_settings, 
                         Fluent(fn.silo_access_index.value,
                                self._get_int_type(fvr.with_int_bounds, 0, fvr.count_silo_accesses_in_silo.max-1),
                                access_point=SiloAccess),
                         default_initial_value=0)

        # [REAL] Silo-access mass capacity
        min_val = self._get_fraction( 0 if fvr.silo_access_mass_capacity.min is None else fvr.silo_access_mass_capacity.min )
        self._add_fluent(problem_settings, 
                         Fluent(fn.silo_access_total_capacity_mass.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.silo_access_mass_capacity.max),
                                silo_access=SiloAccess),
                         default_initial_value=min_val)

        # [REAL] Silo-access available mass capacity
        self._add_fluent(problem_settings, 
                         Fluent(fn.silo_access_available_capacity_mass.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.silo_access_mass_capacity.max),
                                silo_access=SiloAccess),
                         default_initial_value=0)

        # [BOOL] Is the silo access available
        self._add_fluent(problem_settings, 
                         Fluent(fn.silo_access_free.value, BoolType(), silo_access=SiloAccess),
                         default_initial_value=True)

        # [REAL] Time [s] needed by a compactor to move yield from the silo access to the silo main storage location
        # @todo update default with realistic values
        def_value = 300
        min_val = 0 if fvr.silo_access_sweep_duration.min is None else fvr.silo_access_sweep_duration.min
        def_value = self._get_fraction( def_value if fvr.silo_access_sweep_duration.max is None else min(fvr.silo_access_sweep_duration.max, def_value) )
        self._add_fluent(problem_settings,
                         Fluent(fn.silo_access_sweep_duration.value,
                                self._get_real_type(fvr.with_real_bounds, min_val, fvr.silo_access_sweep_duration.max),
                                silo_access=SiloAccess),
                         default_initial_value=def_value)

        # [BOOL] Is silo-access clear of yield
        self._add_fluent(problem_settings, 
                         Fluent(fn.silo_access_cleared.value, BoolType(), silo_access=SiloAccess),
                         default_initial_value=True)

        # [Real] The timestamp from when the silo access is free
        self._add_fluent(problem_settings,
                         Fluent(fn.silo_access_timestamp.value,
                                self._get_real_type(fvr.with_real_bounds, 0, fvr.max_process_duration),
                                silo_access=SiloAccess),
                         default_initial_value=0)

        # --------------COMPACTOR FLUENTS--------------

        # [INT/CONST] Id of the silo to which the compactor belongs
        self._add_fluent(problem_settings, 
                         Fluent(fn.compactor_silo_id.value,
                                self._get_int_type(fvr.with_int_bounds, fvr.silo_ids.min, fvr.silo_ids.max),
                                compactor=Compactor),
                         default_initial_value=problem_settings.id_undef)

        # [REAL] Amount of mass [kg] a compactor can clear in one sweep
        # @todo update default with realistic values
        def_value = 500
        min_val = 0 if fvr.compactor_mass_per_sweep.min is None else fvr.compactor_mass_per_sweep.min
        def_value = self._get_fraction( def_value if fvr.compactor_mass_per_sweep.max is None else min(fvr.compactor_mass_per_sweep.max, def_value) )
        self._add_fluent(problem_settings, 
                         Fluent(fn.compactor_mass_per_sweep.value,
                                self._get_real_type(fvr.with_real_bounds, min_val, fvr.compactor_mass_per_sweep.max),
                                compactor=Compactor),
                         default_initial_value=def_value)

        # [BOOL] Is the compactor available
        self._add_fluent(problem_settings, 
                         Fluent(fn.compactor_free.value, BoolType(), compactor=Compactor),
                         default_initial_value=True)

        # --------------LOCATION FLUENTS--------------

        # [Real/CONST] Transit distance between two locations
        self._add_fluent(problem_settings, 
                         Fluent(fn.transit_distance_init_fap.value,
                                self._get_real_type(fvr.with_real_bounds, -1, fvr.max_transit_distance_init_fap),
                                loc1=MachineInitLoc, loc2=FieldAccess),
                         default_initial_value=-1)
        self._add_fluent(problem_settings, 
                         Fluent(fn.transit_distance_init_sap.value,
                                self._get_real_type(fvr.with_real_bounds, -1, self._get_fraction(fvr.max_transit_distance_init_sap)),
                                loc1=MachineInitLoc, loc2=SiloAccess),
                         default_initial_value=-1)
        self._add_fluent(problem_settings, 
                         Fluent(fn.transit_distance_fap_sap.value,
                                self._get_real_type(fvr.with_real_bounds, -1, fvr.max_transit_distance_fap_sap),
                                loc1=FieldAccess, loc2=SiloAccess),
                         default_initial_value=-1)
        self._add_fluent(problem_settings, 
                         Fluent(fn.transit_distance_fap_fap.value,
                                self._get_real_type(fvr.with_real_bounds, -1, fvr.max_transit_distance_fap_fap),
                                loc1=FieldAccess, loc2=FieldAccess),
                         default_initial_value=-1)
        self._add_fluent(problem_settings, 
                         Fluent(fn.transit_distance_sap_fap.value,
                                self._get_real_type(fvr.with_real_bounds, -1, fvr.max_transit_distance_sap_fap),
                                loc1=SiloAccess, loc2=FieldAccess),
                         default_initial_value=-1)

    @staticmethod
    def _get_fraction(val: Union[int, float, Fraction, None]):
        """ Get the Fraction corresponding to a value if the value is not None, otherwise returns None.

        Parameters
        ----------
        val : value
            Fluent name (or enum)

        Returns
        -------
        fraction : Fraction, None
            Fraction corresponding to the value if the value is not None, otherwise returns None.
        """
        return val if val is None else get_up_fraction(val)

    @staticmethod
    def _get_int_type(with_bounds: bool, _min: Union[int, None], _max: [int, None]) -> IntType:
        """ Get the UP Int with the given value ranges

        Parameters
        ----------
        with_bounds : bool
            If false, no bounds will be set
        _min : int, None
            Minimum value (lower bound).
        _max : int, None
            Maximum value (upper bound)

        Returns
        -------
        int : IntType, None
            IntType(min, max)
        """

        if not with_bounds:
            return IntType()

        return IntType(_min, _max)

    @staticmethod
    def _get_real_type(with_bounds: bool, _min: Union[float, None], _max: [float, None], offset: float = 0.001) -> RealType:
        """ Get the UP Real with the given value ranges

        The Real lower/upper bounds might have a small -/+ offset (if they are not None) to avoid float-precision issues.

        Parameters
        ----------
        with_bounds : bool
            If false, no bounds will be set
        _min : float, None
            Minimum value (lower bound).
        _max : float, None
            Maximum value (upper bound)

        Returns
        -------
        real : RealType, None
            RealType(min, max), with min = _min - offset | None, max = _max + offset | None
        """

        if not with_bounds:
            return RealType()

        _delta_val = max(0.0, offset) if offset is not None else 0.0
        _min_ = None if _min is None else FluentsManager._get_fraction(_min - _delta_val)
        _max_ = None if _max is None else FluentsManager._get_fraction(_max + _delta_val)
        return RealType(_min_, _max_)
