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

import time
from unified_planning.shortcuts import *
# from up_aries import Aries
# from up_skdecide.domain import DomainImpl as SkDecideDomain
# from up_skdecide.engine import EngineImpl, Engine

import up_interface.types as upt
from up_interface import config as conf
from up_interface import fluents as upf
from up_interface.fluents import FluentNames as fn

from up_interface.actions.temporal.drive_harv_to_field_and_init import get_actions_drive_harv_from_loc_to_field_and_init as get_actions_drive_harv_from_loc_to_field_and_init__temp
from up_interface.actions.temporal.drive_tv_to_field_and_reserve_overload import get_actions_drive_tv_from_locs_to_field_and_reserve_overload as get_actions_drive_tv_from_locs_to_field_and_reserve_overload__temp
from up_interface.actions.temporal.do_overload import get_actions_do_overload_and_exit as get_actions_do_overload_and_exit__temp
from up_interface.actions.temporal.do_overload import get_actions_do_overload as get_actions_do_overload__temp
from up_interface.actions.temporal.drive_harv_to_field_exit import get_actions_drive_harv_to_field_exit as get_actions_drive_harv_to_field_exit__temp
from up_interface.actions.temporal.drive_tv_to_field_exit import get_actions_drive_tv_to_field_exit as get_actions_drive_tv_to_field_exit__temp
from up_interface.actions.temporal.drive_to_silo import get_actions_drive_tv_from_loc_to_silo as get_actions_drive_tv_from_loc_to_silo__temp
from up_interface.actions.temporal.drive_to_silo import get_actions_drive_tv_from_loc_to_silo_and_unload as get_actions_drive_tv_from_loc_to_silo_and_unload__temp
from up_interface.actions.temporal.unload_at_silo import get_actions_unload_at_silo as get_actions_unload_at_silo__temp
from up_interface.actions.temporal.sweep_silo_access import get_actions_sweep_silo_access as get_actions_sweep_silo_access__temp

from up_interface.actions.sequential.drive_harv_to_field_and_init import get_actions_drive_harv_from_loc_to_field_and_init as get_actions_drive_harv_from_loc_to_field_and_init__seq
from up_interface.actions.sequential.drive_harv_to_field_exit import get_actions_drive_harv_to_field_exit as get_actions_drive_harv_to_field_exit__seq
from up_interface.actions.sequential.drive_to_silo import get_actions_drive_tv_from_loc_to_silo as get_actions_drive_tv_from_loc_to_silo__seq
from up_interface.actions.sequential.drive_to_silo import get_actions_drive_tv_from_loc_to_silo_and_unload as get_actions_drive_tv_from_loc_to_silo_and_unload__seq
from up_interface.actions.sequential.drive_tv_to_field_and_overload import get_actions_drive_tv_from_locs_to_field_and_overload as get_actions_drive_tv_from_locs_to_field_and_overload__seq
from up_interface.actions.sequential.drive_tv_to_field_exit import get_actions_drive_tv_to_field_exit as get_actions_drive_tv_to_field_exit__seq
from up_interface.actions.sequential.unload_at_silo import get_actions_unload_at_silo as get_actions_unload_at_silo__seq

from management.global_data_manager import GlobalDataManager
from management.field_partial_plan_manager import FieldPartialPlanManager
from up_interface.problem_encoder.problem_objects import ProblemObjects
from up_interface.problem_encoder.problem_stats import *
from management.pre_assignments import *
from route_planning.field_route_planning import PlanningSettings as FieldPlanningSettings

from util_arolib.types import *
from util_arolib.geometry import *

from route_planning.types import MachineState, FieldState
from route_planning.outfield_route_planning import OutFieldRoutePlanner
from up_interface.problem_encoder.names_helper import *


class ProblemEncoder:

    """ UP-problem encoder for the agriculture use-case. """

    __factor_full_machine = 0.95
    """ Factor used to consider a transport vehicle to be full. """

    __factor_loaded_machine = 0.05
    """ Factor used to consider a transport vehicle to have yield to unload. """

    def __init__(self
                 , data_manager: GlobalDataManager
                 , field_plan_manager: FieldPartialPlanManager
                 , out_field_route_planner: OutFieldRoutePlanner
                 , machine_initial_states: Dict[int, MachineState]
                 , field_initial_states: Dict[int, FieldState]
                 , problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings
                 , pre_assigned_fields: Union[FieldPreAssignments, None] = None
                 , pre_assigned_tvs: Union[TVPreAssignments, None] = None
                 ):

        """ Initializes the problem encoder and creates the UP-problem

        Parameters
        ----------
        data_manager : GlobalDataManager
            Data manager
        field_plan_manager : FieldPartialPlanManager
            Infield route planning manager (not used at the moment)
        out_field_route_planner : OutFieldRoutePlanner
            Route/path planner for transit outside the fields
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        field_initial_states : Dict[int, FieldState]
            Field initial states: {field_id: field_state}
        problem_settings : config.GeneralProblemSettings
            Problem configuration settings
        pre_assigned_fields : FieldPreAssignments
            Field pre-assignments (disregarded if None)
        pre_assigned_tvs : TVPreAssignments
            Transport vehicle pre-assignments (disregarded if None)
        """

        self.__fluents_manager = upf.FluentsManager()
        self.__data_manager = data_manager
        self.__field_plan_manager = field_plan_manager
        self.__out_field_route_planner = out_field_route_planner
        self.__field_initial_states = field_initial_states
        self.__machine_initial_states = machine_initial_states
        self.__problem_settings = problem_settings
        self.__problem = Problem('UP harvesting case scenario')
        self.__objects = ProblemObjects()
        self.__fields_with_silos: Dict[int, Field] = dict()
        self.__out_field_infos: Dict[int, OutFieldInfo] = dict()
        self.__field_problem_settings = FieldPlanningSettings()
        self.__problem_stats = ProblemStats()

        self.__harvested_fields = set()
        self.__remaining_mass_fields = dict()
        self.__with_field_exit = False
        self.__harvesters_at_init_loc = set()
        self.__harvesters_in_unfinished_fields = dict()
        self.__harvesters_in_finished_fields = dict()
        self.__tvs_at_init_loc = set()
        self.__tvs_at_init_loc_with_load = set()
        self.__tvs_in_unfinished_fields = dict()
        self.__tvs_in_finished_fields = dict()
        self.__tvs_at_silos_with_load = dict()
        self.__overloading_harvesters = dict()
        self.__overloading_tvs = dict()
        self.__overloading_tvs_but_full = set()

        self.__objects.count_fields = 0
        self.__objects.count_fields_to_work = 0
        self.__objects.count_harvesters = 0
        self.__objects.count_tvs = 0
        self.__objects.count_silos = 0
        self.__objects.count_compactors = 0

        self.__fluent_initial_values: List[Tuple[Fluent, Tuple, Any]] = list()

        self.__pre_assigned_tvs = pre_assigned_tvs

        print('Creating objects...')
        _t_start = time.time()
        self.__add_machines()
        self.__add_fields()
        self.__add_silos()
        self.__add_compactors()
        print(f'Objects created [{time.time() - _t_start}s]')

        print('Adding machine init locations to problem...')
        _t_start = time.time()
        self.__add_machine_init_locations(machine_initial_states)
        print(f'Machine init locations added to problem [{time.time() - _t_start}s]')

        print('Initializing fields...')
        _t_start = time.time()
        self.__init_fields_with_silos()
        print(f'Fields initialized [{time.time() - _t_start}s]')

        print('Initializing out-field information...')
        _t_start = time.time()
        self.__init_out_field_infos()
        print(f'Out-field information initialized [{time.time() - _t_start}s]')

        print('Adding objects to problem...')
        _t_start = time.time()
        self.__add_objects_to_problem()
        print(f'Objects added to problem [{time.time() - _t_start}s]')

        print('Initializing fluents and stats...')
        _t_start = time.time()
        self.__init_fluents_and_stats(machine_initial_states, field_initial_states, pre_assigned_fields)
        print(f'Fluents and stats initialized [{time.time() - _t_start}s]')

        print('Adding fluents, actions and goals to problem...')
        _t_start = time.time()
        self.__add_fluents_to_problem()
        self.__add_actions_to_problem(cyclic_pre_assigned_tv_turns = (None if self.__pre_assigned_tvs is None else self.__pre_assigned_tvs.cyclic_turns))
        self.__add_goals_to_problem()
        print(f'Fluents, actions and goals added to problem [{time.time() - _t_start}s]')

    def print_problem(self):
        """ Print the UP-problem """
        print(self.__problem)

    @property
    def problem(self) -> Problem:
        """ Get the UP-problem

        Returns
        ----------
        problem : Problem
            UP-problem
        """
        return self.__problem

    @property
    def problem_objects(self) -> ProblemObjects:
        """ Get the problem objects

        Returns
        ----------
        problem_objects : ProblemObjects
            Problem objects
        """
        return self.__objects

    @property
    def fluents_manager(self) -> upf.FluentsManagerBase:
        """ Get the fluents manager

        Returns
        ----------
        fluents_manager : FluentsManagerBase
            Fluents manager
        """
        return self.__fluents_manager

    @property
    def problem_settings(self) -> conf.GeneralProblemSettings:
        """ Get the problem configuration settings

        Returns
        ----------
        problem_settings : config.GeneralProblemSettings
            Problem configuration settings
        """
        return self.__problem_settings

    @property
    def problem_stats(self) -> ProblemStats:
        """ Get the problem statistics

        Returns
        ----------
        problem_stats : ProblemStats
            Problem statistics
        """
        return self.__problem_stats

    @property
    def data_manager(self) -> GlobalDataManager:
        """ Get the data manager

        Returns
        ----------
        data_manager : GlobalDataManager
            Data manager
        """
        return self.__data_manager

    @property
    def out_field_route_planner(self) -> OutFieldRoutePlanner:
        """ Get the route/path planner for transit outside the fields

        Returns
        ----------
        out_field_route_planner : OutFieldRoutePlanner
            Route/path planner for transit outside the fields
        """
        return self.__out_field_route_planner

    @property
    def field_initial_states(self) -> Dict[int, FieldState]:
        """ Get the field initial states

        Returns
        ----------
        field_initial_states : Dict[int, FieldState]
            Field initial states: {field_id: field_state}
        """
        return self.__field_initial_states

    @property
    def machine_initial_states(self) -> Dict[int, MachineState]:
        """ Get the machine (harvesters, transport vehicles) initial states

        Returns
        ----------
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        """
        return self.__machine_initial_states

    def __add_machines(self):

        """ Add harvester and transport vehicle objects to the problem """

        # add objects := no/invalid machine
        self.__objects.no_harvester = Object('no_harv', upt.Harvester)
        self.__objects.harvesters['no_harv'] = self.__objects.no_harvester

        machines = self.__data_manager.machines
        for machine in machines.values():

            if machine.id == self.__problem_settings.id_undef:
                raise ValueError(f'Machine id {machine.id} is reserved')

            if machine.machinetype is MachineType.HARVESTER:
                name = get_harvester_name(machine.id)
                self.__objects.harvesters[name] = Object(name, upt.Harvester)
                self.__objects.count_harvesters += 1
            elif machine.machinetype is MachineType.OLV:
                name = get_tv_name(machine.id)
                self.__objects.tvs[name] = Object(name, upt.TransportVehicle)
                self.__objects.count_tvs += 1
            else:
                print(f'[WARN] Machine with id {machine.id} has an unsupported type')
                continue

    def __add_fields(self):

        """ Add field objects to the problem """

        # add objects := no/invalid field and field_access
        self.__objects.no_field = Object('no_field', upt.Field)
        self.__objects.fields['no_field'] = self.__objects.no_field
        self.__objects.no_field_access = Object('no_field_access', upt.FieldAccess)
        self.__objects.field_accesses['no_field_access'] = self.__objects.no_field_access

        fields = self.__data_manager.fields
        for field in fields.values():
            name = get_field_location_name(field.id)
            if name in self.__objects.fields:
                raise ValueError(f'Error adding field with id {field.id}: '
                                 f'location with a given name {name} already exists')

            obj = Object(name, upt.Field)
            self.__objects.fields[name] = obj

            if field.id == self.__problem_settings.id_undef:
                raise ValueError(f'Field id {field.id} is reserved')
            if len(field.subfields) == 0:
                raise ValueError(f'Field with id {field.id} has no subfields')
            if len(field.subfields[0].access_points) == 0:
                raise ValueError(f'Field with id {field.id} has no access points')
            for i in range(len(field.subfields[0].access_points)):
                name = get_field_access_location_name(field.id, i)
                if name in self.__objects.field_accesses:
                    raise ValueError(f'Error adding access points of field with id {field.id}: '
                                     f'location with a given name {name} already exists')
                obj = Object(name, upt.FieldAccess)
                self.__objects.field_accesses[name] = obj

            self.__objects.count_fields += 1

    def __add_silos(self):

        """ Add silo objects to the problem """

        # add objects := no/invalid silo_access
        self.__objects.no_silo_access = Object('no_silo_access', upt.SiloAccess)
        self.__objects.silo_accesses['no_silo_access'] = self.__objects.no_silo_access

        silos = self.__data_manager.silos
        for silo in silos.values():

            if silo.id == self.__problem_settings.id_undef:
                raise ValueError(f'Silo id {silo.id} is reserved')

            name = get_silo_location_name(silo.id)
            if name in self.__objects.silos:
                raise ValueError(f'Error adding silo with id {silo.id}: '
                                 f'location with a given name {name} already exists')
            obj = Object(name, upt.Silo)
            self.__objects.silos[name] = obj

            for i in range(len(silo.access_points)):
                name = get_silo_access_location_name(silo.id, i)
                if name in self.__objects.silo_accesses:
                    raise ValueError(f'Error adding access points of silo with id {silo.id}: '
                                     f'location with a given name {name} already exists')
                obj = Object(name, upt.SiloAccess)
                self.__objects.silo_accesses[name] = obj

            self.__objects.count_silos += 1

    def __add_compactors(self):

        """ Add compactor objects to the problem """

        compactors = self.__data_manager.compactors

        if len(compactors.values()) > 0:
            for compactor in compactors.values():
                name = get_compactor_name(compactor.id)
                self.__objects.compactors[name] = Object(name, upt.Compactor)
                self.__objects.count_compactors += 1
        else:  # @todo we need to add a compactor otherwise tamer crashes (in the future we have to check that at least one compactor per silo exist, or remove all compactor related fluents/actions if they wont be used)
            self.__objects.compactors['no_compactor'] = Object('no_compactor', upt.Compactor)

    def __add_machine_init_locations(self, machine_initial_states: Dict[int, MachineState]):

        """ Add machine-initial-locations objects to the problem

        Parameters
        ----------
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        """

        # add objects := no/invalid silo_access
        self.__objects.no_init_loc = Object('no_init_loc', upt.MachineInitLoc)
        self.__objects.machine_init_locations['no_init_loc'] = self.__objects.no_init_loc

        for machine_id in self.__data_manager.machines.keys():
            machine_state = machine_initial_states.get(machine_id)
            if machine_state.location_name is not None:  # the machine is located somewhere else
                continue

            machine_name = get_harvester_name(machine_id)
            machine = self.__objects.harvesters.get(machine_name)
            if machine is not None:
                name = get_machine_initial_location_name(machine_name)
                obj = Object(name, upt.MachineInitLoc)
                self.__objects.machine_init_locations[name] = obj
                continue

            machine_name = get_tv_name(machine_id)
            machine = self.__objects.tvs.get(machine_name)
            if machine is not None:
                name = get_machine_initial_location_name(machine_name)
                obj = Object(name, upt.MachineInitLoc)
                self.__objects.machine_init_locations[name] = obj
                continue

    def __init_fields_with_silos(self):

        """ Initialize the fields adding to them all available silos as resource points (for infield route planning) """

        for field_id in self.__data_manager.fields.keys():
            self.__fields_with_silos[field_id] = self.__data_manager.get_field_with_silos(field_id, None)

    def __init_out_field_infos(self):

        """ Initialize the out-of-field information (for infield route planning) """

        # # get travel information from silos to field access points and vice versa using the outfield/street planner
        # for field_id, field in self.__fields_with_silos.items():
        #     if len(field.subfields) == 0:
        #         raise ValueError(f'Field with id {field_id} has no subfields')
        #     ofi = OutFieldInfo()
        #     update_travel_data(ofi,
        #                        self.__out_field_route_planner,
        #                        field.subfields[0].access_points,
        #                        self.__data_manager.silos,
        #                        self.__data_manager.machines)
        #     self.__out_field_infos[field_id] = ofi
        pass

    def __add_objects_to_problem(self):

        """ Add all objects to the problem """

        for obj in self.__objects.fields.values():
            self.__problem.add_object(obj)
        for obj in self.__objects.field_accesses.values():
            self.__problem.add_object(obj)
        for obj in self.__objects.harvesters.values():
            self.__problem.add_object(obj)
        for obj in self.__objects.tvs.values():
            self.__problem.add_object(obj)
        for obj in self.__objects.silos.values():
            self.__problem.add_object(obj)
        for obj in self.__objects.silo_accesses.values():
            self.__problem.add_object(obj)
        for obj in self.__objects.machine_init_locations.values():
            self.__problem.add_object(obj)
        for obj in self.__objects.compactors.values():
            self.__problem.add_object(obj)

    def __add_fluents_to_problem(self):

        """ Add all fluents to the problem """

        fluent_value_ranges = upf.FluentValueRanges(with_bounds=self.__problem_settings.numeric_fluent_bounds_option is not conf.NumericFluentsBoundsOption.WITHOUT_BOUNDS)

        if self.__problem_settings.numeric_fluent_bounds_option is conf.NumericFluentsBoundsOption.WITH_PROBLEM_SPECIFIC_BOUNDS:

            fluent_value_ranges.with_int_bounds = True
            fluent_value_ranges.with_int_bounds = True

            fluent_value_ranges.infield_transit_duration_to_fap = self.__problem_settings.infield_transit_duration_to_field_access

            fluent_value_ranges.field_ids.min = math.floor( self.__problem_stats.fields.field_ids.min )
            fluent_value_ranges.field_ids.max = math.ceil( self.__problem_stats.fields.field_ids.max )

            fluent_value_ranges.silo_ids.min = math.floor( self.__problem_stats.silos.silo_ids.min )
            fluent_value_ranges.silo_ids.max = math.ceil( self.__problem_stats.silos.silo_ids.max )

            fluent_value_ranges.tv_mass_capacity.min = math.floor( self.__problem_stats.machines.tv_bunker_mass_capacity.min )
            fluent_value_ranges.tv_mass_capacity.max = math.ceil( self.__problem_stats.machines.tv_bunker_mass_capacity.max )

            fluent_value_ranges.count_field_accesses_in_field.min = math.floor( self.__problem_stats.fields.field_access_points_count.min )
            fluent_value_ranges.count_field_accesses_in_field.max = math.ceil( self.__problem_stats.fields.field_access_points_count.max )

            fluent_value_ranges.count_silo_accesses_in_silo.min = math.floor( self.__problem_stats.silos.silo_access_points_count.min )
            fluent_value_ranges.count_silo_accesses_in_silo.max = math.ceil( self.__problem_stats.silos.silo_access_points_count.max )

            fluent_value_ranges.yield_mass_in_field.min = math.floor( self.__problem_stats.fields.yield_mass_remaining.min )
            fluent_value_ranges.yield_mass_in_field.max = math.ceil( self.__problem_stats.fields.yield_mass_remaining.max )

            fluent_value_ranges.harv_max_transit_speed_empty.min = math.floor( self.__problem_stats.machines.harv_transit_speed_empty.min )
            fluent_value_ranges.harv_max_transit_speed_empty.max = math.ceil( self.__problem_stats.machines.harv_transit_speed_empty.max )

            fluent_value_ranges.tv_max_transit_speed_empty.min = math.floor( self.__problem_stats.machines.tv_transit_speed_empty.min )
            fluent_value_ranges.tv_max_transit_speed_empty.max = math.ceil( self.__problem_stats.machines.tv_transit_speed_empty.max )

            fluent_value_ranges.tv_max_transit_speed_full.min = math.floor( self.__problem_stats.machines.tv_transit_speed_full.min )
            fluent_value_ranges.tv_max_transit_speed_full.max = math.ceil( self.__problem_stats.machines.tv_transit_speed_full.max )

            fluent_value_ranges.harv_working_time_per_area.min = math.floor( self.__problem_stats.machines.harv_working_time_per_area.min )
            fluent_value_ranges.harv_working_time_per_area.max = math.ceil( self.__problem_stats.machines.harv_working_time_per_area.max )

            fluent_value_ranges.tv_unloading_speed_mass.min = math.floor( self.__problem_stats.machines.tv_unloading_speed_mass.min )
            fluent_value_ranges.tv_unloading_speed_mass.max = math.ceil( self.__problem_stats.machines.tv_unloading_speed_mass.max )

            fluent_value_ranges.field_area_per_yield_mass.min = math.floor( self.__problem_stats.fields.field_area_per_yield_mass.min )
            fluent_value_ranges.field_area_per_yield_mass.max = math.ceil( self.__problem_stats.fields.field_area_per_yield_mass.max )

            fluent_value_ranges.silo_access_mass_capacity.min = math.floor( self.__problem_stats.silos.silo_access_mass_capacity.min )
            fluent_value_ranges.silo_access_mass_capacity.max = math.ceil( self.__problem_stats.silos.silo_access_mass_capacity.max )

            fluent_value_ranges.silo_access_sweep_duration.min = math.floor( self.__problem_stats.silos.silo_access_sweep_duration.min )
            fluent_value_ranges.silo_access_sweep_duration.max = math.ceil( self.__problem_stats.silos.silo_access_sweep_duration.max )

            # @todo: uncomment when using real values and not inf
            # fluent_value_ranges.compactor_mass_per_sweep.min = math.floor( self.__problem_stats.silos.compactor_mass_per_sweep.min )
            # fluent_value_ranges.compactor_mass_per_sweep.max = math.ceil( self.__problem_stats.silos.compactor_mass_per_sweep.max )


            fluent_value_ranges.count_fields_to_work = self.__objects.count_fields_to_work
            fluent_value_ranges.count_tvs = self.__objects.count_tvs
            fluent_value_ranges.total_yield_mass_in_fields = math.ceil( self.__problem_stats.fields.yield_mass_remaining.total )
            fluent_value_ranges.total_yield_mass_in_tvs = math.ceil( self.__problem_stats.machines.yield_mass_in_tvs.total )
            fluent_value_ranges.max_transit_distance_init_fap = math.ceil( self.__problem_stats.transit.distance_from_init_locations_to_field.max )
            fluent_value_ranges.max_transit_distance_init_sap = math.ceil( self.__problem_stats.transit.distance_from_init_locations_to_silos.max )
            fluent_value_ranges.max_transit_distance_fap_sap = math.ceil( self.__problem_stats.transit.distance_between_fields_and_silos.max )
            fluent_value_ranges.max_transit_distance_sap_fap = math.ceil( self.__problem_stats.transit.distance_between_fields_and_silos.max )
            fluent_value_ranges.max_transit_distance_fap_fap = math.ceil( self.__problem_stats.transit.distance_between_field_access_points_all.max )
            fluent_value_ranges.max_silo_mass_capacity = math.ceil( self.__problem_stats.silos.silo_mass_capacity.max )

            fluent_value_ranges.max_overloading_activities_field = \
                math.ceil( self.__problem_stats.fields.yield_mass_remaining.total \
                           / self.__problem_stats.machines.tv_bunker_mass_capacity.min ) \
                + (self.__objects.count_fields_to_work - 1) \
                + 1  # +1 in case it is almost full

            fluent_value_ranges.max_overloading_activities_all = \
                math.ceil( self.__problem_stats.fields.yield_mass_remaining.max \
                           / self.__problem_stats.machines.tv_bunker_mass_capacity.min ) \
                + 1  # +1 in case it is almost full

            fluent_value_ranges.max_harv_transit_time = 0
            fluent_value_ranges.max_tv_transit_time = 0
            for machine_id, machine_aro in self.__data_manager.machines.items():
                if machine_aro.machinetype is MachineType.HARVESTER:
                    min_speed = machine_aro.max_speed_empty

                    machine_obj = self.__objects.harvesters.get( get_harvester_name(machine_id) )

                    d_init = 0
                    field_id_init = None
                    if machine_obj in self.__harvesters_at_init_loc:
                        if machine_id in self.__problem_stats.transit.machines_distance_from_init_locations_to_fields.keys():
                            d_init = self.__problem_stats.transit.machines_distance_from_init_locations_to_fields[machine_id].max
                    elif machine_obj in self.__harvesters_in_finished_fields.keys():
                        field_id = get_field_id_from_location_name( self.__harvesters_in_finished_fields.get(machine_obj).name )
                        if field_id in self.__problem_stats.transit.fields_distance_between_field_access_points_different_fields.keys():
                            d_init = max(d_init, self.__problem_stats.transit.fields_distance_between_field_access_points_different_fields[field_id].max)
                            field_id_init = field_id

                    d_fields_stats = BaseStats()
                    for field_id in self.__data_manager.fields.keys():
                        field_obj = self.__objects.fields.get( get_field_location_name(field_id) )
                        if field_obj in self.__harvested_fields or field_id == field_id_init:
                            continue
                        if field_id not in self.__problem_stats.transit.fields_distance_between_field_access_points_different_fields.keys():
                            continue
                        d_fields_stats.update( self.__problem_stats.transit.fields_distance_between_field_access_points_different_fields[field_id].max )

                    d_fields = d_fields_stats.total
                    if d_fields_stats.count > 0:
                        d_fields -= d_fields_stats.min

                    max_dist = d_init + d_fields
                    fluent_value_ranges.max_harv_transit_time = max(fluent_value_ranges.max_harv_transit_time,
                                                                    max_dist / min_speed)

                elif machine_aro.machinetype is MachineType.OLV:
                    min_speed = min(machine_aro.max_speed_empty, machine_aro.max_speed_full)
                    max_dist_from_init_loc_to_field = max_dist_from_init_loc_to_silo = 0

                    if machine_id in self.__problem_stats.transit.machines_distance_from_init_locations_to_fields.keys():
                        max_dist_from_init_loc_to_field = self.__problem_stats.transit.machines_distance_from_init_locations_to_fields[machine_id].max
                    if machine_id in self.__problem_stats.transit.machines_distance_from_init_locations_to_silos.keys():
                        max_dist_from_init_loc_to_silo = self.__problem_stats.transit.machines_distance_from_init_locations_to_silos[machine_id].max
                    max_dist_field_to_silo = self.__problem_stats.transit.distance_between_fields_and_silos.max
                    max_dist_between_fields = self.__problem_stats.transit.distance_between_field_access_points_different_fields.max

                    max_overloads = math.ceil( self.__problem_stats.fields.yield_mass_remaining.total / machine_aro.bunker_mass )

                    dist_fields_to_silos = max_overloads * max_dist_field_to_silo
                    dist_silos_to_fields = ( max_overloads - 1 ) * max_dist_field_to_silo
                    dist_init = max( max_dist_from_init_loc_to_silo + max_dist_field_to_silo, # in case it goes first to unload
                                     max_dist_from_init_loc_to_field )
                    dist_change_fields = (self.__objects.count_fields_to_work - 1) \
                                         * max( 2 * max_dist_field_to_silo,
                                                max_dist_between_fields )

                    total_dist = dist_fields_to_silos + dist_silos_to_fields + dist_init + dist_change_fields

                    fluent_value_ranges.max_tv_transit_time = max(fluent_value_ranges.max_tv_transit_time,
                                                                    total_dist / min_speed)

            fluent_value_ranges.max_harv_transit_time = math.ceil(fluent_value_ranges.max_harv_transit_time)
            fluent_value_ranges.max_tv_transit_time = math.ceil(fluent_value_ranges.max_tv_transit_time)

        self.__fluents_manager.initialize(self.__problem_settings, fluent_value_ranges)
        self.__fluents_manager.add_fluents_to_problem(self.__problem, check_fluents=True)

    def __add_actions_to_problem(self, cyclic_pre_assigned_tv_turns: Union[bool, None] = True):

        """ Add all actions to the problem

        Parameters
        ----------
        cyclic_pre_assigned_tv_turns : bool
            Are the overload turns pre-assigned to the transport vehicles cyclic?
        """

        if self.__problem_settings.planning_type is conf.PlanningType.TEMPORAL:
            self.__problem.add_actions( get_actions_drive_harv_from_loc_to_field_and_init__temp( fluents_manager=self.__fluents_manager,
                                                                                                 infield_planner=self.__field_plan_manager,
                                                                                                 no_harv_object=self.__objects.no_harvester,
                                                                                                 no_field_object=self.__objects.no_field,
                                                                                                 no_field_access_object=self.__objects.no_field_access,
                                                                                                 no_init_loc_object=self.__objects.no_init_loc,
                                                                                                 problem_settings=self.__problem_settings,
                                                                                                 include_from_init_loc=(len(self.__harvesters_at_init_loc) > 0),
                                                                                                 include_from_field=(len(self.__harvesters_in_unfinished_fields.keys()) > 0) ) )

            self.__problem.add_actions( get_actions_drive_tv_from_locs_to_field_and_reserve_overload__temp(fluents_manager=self.__fluents_manager,
                                                                                                           no_harv_object=self.__objects.no_harvester,
                                                                                                           no_field_object=self.__objects.no_field,
                                                                                                           no_field_access_object=self.__objects.no_field_access,
                                                                                                           no_silo_access_object=self.__objects.no_silo_access,
                                                                                                           no_init_loc_object=self.__objects.no_init_loc,
                                                                                                           cyclic_pre_assigned_tv_turns=cyclic_pre_assigned_tv_turns,
                                                                                                           problem_settings=self.__problem_settings,
                                                                                                           include_from_init_loc=( len(self.__tvs_at_init_loc) > 0 ),
                                                                                                           include_from_field=( len(self.__tvs_in_unfinished_fields.keys()) > 0 ) ) )
            if self.__problem_settings.with_drive_to_field_exit:
                self.__problem.add_actions( get_actions_do_overload__temp(fluents_manager=self.__fluents_manager,
                                                                          no_harv_object=self.__objects.no_harvester,
                                                                          no_field_object=self.__objects.no_field,
                                                                          problem_settings=self.__problem_settings) )
                self.__problem.add_actions( get_actions_drive_harv_to_field_exit__temp(fluents_manager=self.__fluents_manager,
                                                                                       no_harv_object=self.__objects.no_harvester,
                                                                                       no_field_object=self.__objects.no_field,
                                                                                       no_field_access_object=self.__objects.no_field_access,
                                                                                       problem_settings=self.__problem_settings) )
                self.__problem.add_actions( get_actions_drive_tv_to_field_exit__temp(fluents_manager=self.__fluents_manager,
                                                                                     no_field_object=self.__objects.no_field,
                                                                                     no_field_access_object=self.__objects.no_field_access,
                                                                                     problem_settings=self.__problem_settings) )
            else:
                self.__problem.add_actions( get_actions_do_overload_and_exit__temp(fluents_manager=self.__fluents_manager,
                                                                                   no_harv_object=self.__objects.no_harvester,
                                                                                   no_field_object=self.__objects.no_field,
                                                                                   no_field_access_object=self.__objects.no_field_access,
                                                                                   problem_settings=self.__problem_settings) )
                if self.__with_field_exit:
                    self.__problem.add_actions( get_actions_drive_harv_to_field_exit__temp(fluents_manager=self.__fluents_manager,
                                                                                           no_harv_object=self.__objects.no_harvester,
                                                                                           no_field_object=self.__objects.no_field,
                                                                                           no_field_access_object=self.__objects.no_field_access,
                                                                                           problem_settings=self.__problem_settings) )
                    self.__problem.add_actions( get_actions_drive_tv_to_field_exit__temp(fluents_manager=self.__fluents_manager,
                                                                                         no_field_object=self.__objects.no_field,
                                                                                         no_field_access_object=self.__objects.no_field_access,
                                                                                         problem_settings=self.__problem_settings) )

            if self.__problem_settings.silo_planning_type is conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY:
                self.__problem.add_actions( get_actions_drive_tv_from_loc_to_silo_and_unload__temp(fluents_manager=self.__fluents_manager,
                                                                                                   no_field_access_object=self.__objects.no_field_access,
                                                                                                   no_silo_access_object=self.__objects.no_silo_access,
                                                                                                   no_init_loc_object=self.__objects.no_init_loc,
                                                                                                   problem_settings=self.__problem_settings,
                                                                                                   include_from_init_loc=( len(self.__tvs_at_init_loc_with_load) > 0),
                                                                                                   include_from_silo_access=( len(self.__tvs_at_silos_with_load.keys()) > 0 ) ) )
            else:
                self.__problem.add_actions( get_actions_drive_tv_from_loc_to_silo__temp(fluents_manager=self.__fluents_manager,
                                                                                        no_field_access_object=self.__objects.no_field_access,
                                                                                        no_silo_access_object=self.__objects.no_silo_access,
                                                                                        no_init_loc_object=self.__objects.no_init_loc,
                                                                                        problem_settings=self.__problem_settings,
                                                                                        include_from_init_loc=( len(self.__tvs_at_init_loc_with_load) > 0)) )
                self.__problem.add_actions( get_actions_unload_at_silo__temp(fluents_manager=self.__fluents_manager,
                                                                             problem_settings=self.__problem_settings) )

                if self.__problem_settings.silo_planning_type is conf.SiloPlanningType.WITH_SILO_ACCESS_CAPACITY_AND_COMPACTION:
                    self.__problem.add_actions( get_actions_sweep_silo_access__temp(fluents_manager=self.__fluents_manager,
                                                                                    problem_settings=self.__problem_settings) )
                    # raise NotImplementedError()
        elif self.__problem_settings.planning_type is conf.PlanningType.SEQUENTIAL:
            self.__problem.add_actions(
                get_actions_drive_harv_from_loc_to_field_and_init__seq(fluents_manager=self.__fluents_manager,
                                                                       infield_planner=self.__field_plan_manager,
                                                                      no_harv_object=self.__objects.no_harvester,
                                                                      no_field_object=self.__objects.no_field,
                                                                      no_field_access_object=self.__objects.no_field_access,
                                                                      no_init_loc_object=self.__objects.no_init_loc,
                                                                      problem_settings=self.__problem_settings,
                                                                      include_from_init_loc=( len(self.__harvesters_at_init_loc) > 0),
                                                                      include_from_field=( len(self.__harvesters_in_unfinished_fields.keys()) > 0)))

            self.__problem.add_actions(
                get_actions_drive_tv_from_locs_to_field_and_overload__seq(fluents_manager=self.__fluents_manager,
                                                                         no_harv_object=self.__objects.no_harvester,
                                                                         no_field_object=self.__objects.no_field,
                                                                         no_field_access_object=self.__objects.no_field_access,
                                                                         no_silo_access_object=self.__objects.no_silo_access,
                                                                         no_init_loc_object=self.__objects.no_init_loc,
                                                                         cyclic_pre_assigned_tv_turns=cyclic_pre_assigned_tv_turns,
                                                                         problem_settings=self.__problem_settings,
                                                                         include_from_init_loc=( len(self.__tvs_at_init_loc) > 0),
                                                                         include_from_field=( len(self.__tvs_in_unfinished_fields.keys()) > 0)
                                                                         ))
            if self.__with_field_exit:
                self.__problem.add_actions( get_actions_drive_harv_to_field_exit__seq(fluents_manager=self.__fluents_manager,
                                                                                    no_harv_object=self.__objects.no_harvester,
                                                                                    no_field_object=self.__objects.no_field,
                                                                                    no_field_access_object=self.__objects.no_field_access,
                                                                                    problem_settings=self.__problem_settings) )
                self.__problem.add_actions( get_actions_drive_tv_to_field_exit__seq(fluents_manager=self.__fluents_manager,
                                                                                  no_field_object=self.__objects.no_field,
                                                                                  no_field_access_object=self.__objects.no_field_access,
                                                                                  problem_settings=self.__problem_settings) )

            if self.__problem_settings.silo_planning_type is conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY:
                self.__problem.add_actions(
                    get_actions_drive_tv_from_loc_to_silo_and_unload__seq(fluents_manager=self.__fluents_manager,
                                                                          no_field_access_object=self.__objects.no_field_access,
                                                                          no_silo_access_object=self.__objects.no_silo_access,
                                                                          no_init_loc_object=self.__objects.no_init_loc,
                                                                          problem_settings=self.__problem_settings,
                                                                          include_from_init_loc=( len(self.__tvs_at_init_loc_with_load) > 0),
                                                                          include_from_silo_access=( len(self.__tvs_at_silos_with_load.keys()) > 0)))
            elif self.__problem_settings.silo_planning_type is conf.SiloPlanningType.WITH_SILO_ACCESS_AVAILABILITY:
                self.__problem.add_actions( get_actions_drive_tv_from_loc_to_silo__seq(fluents_manager=self.__fluents_manager,
                                                                                       no_field_access_object=self.__objects.no_field_access,
                                                                                       no_silo_access_object=self.__objects.no_silo_access,
                                                                                       no_init_loc_object=self.__objects.no_init_loc,
                                                                                       problem_settings=self.__problem_settings,
                                                                                       include_from_init_loc=( len(self.__tvs_at_init_loc_with_load) > 0)) )
                self.__problem.add_actions( get_actions_unload_at_silo__seq(fluents_manager=self.__fluents_manager,
                                                                            problem_settings=self.__problem_settings) )
            else:
                raise NotImplementedError()

        else:
            raise ValueError(f'Unsupported planning type {self.__problem_settings.planning_type}')

    def __add_goals_to_problem(self):

        """ Add all goals to the problem """

        def add_goal_to_problem(goal, interval = EndTiming()):
            if self.__problem_settings.planning_type is conf.PlanningType.TEMPORAL:
                self.__problem.add_timed_goal(interval, goal)
            else:
                self.__problem.add_goal(goal)

        planning_failed = self.__fluents_manager.get_fluent(fn.planning_failed)
        add_goal_to_problem( Not( planning_failed() ), EndTiming())

        field_harvested = self.__fluents_manager.get_fluent(fn.field_harvested)
        harv_free = self.__fluents_manager.get_fluent(fn.harv_free)
        tv_free = self.__fluents_manager.get_fluent(fn.tv_free)
        tv_bunker_mass = self.__fluents_manager.get_fluent(fn.tv_bunker_mass)
        silo_access_cleared = self.__fluents_manager.get_fluent(fn.silo_access_cleared)
        total_yield_mass_in_silos = self.__fluents_manager.get_fluent(fn.total_yield_mass_in_silos)

        # all fields are harvested
        __use_total_yield_mass_in_fields = True
        if __use_total_yield_mass_in_fields:
            if self.__problem_settings.planning_type is conf.PlanningType.TEMPORAL:
                total_harvested_mass = self.__fluents_manager.get_fluent(fn.total_yield_mass_reserved)
            else:
                total_harvested_mass = self.__fluents_manager.get_fluent(fn.total_harvested_mass)
            add_goal_to_problem( GE( total_harvested_mass(),
                                     self.__problem_stats.fields.yield_mass_remaining.total - 10 ),
                                 EndTiming() )

        else:
            for field in self.__objects.fields.values():
                if field is self.__objects.no_field:
                    continue
                add_goal_to_problem( field_harvested(field), EndTiming() )

        # for machine in self.__objects.harvesters.values():
        #     if machine is self.__objects.no_harvester:
        #         continue
        #
        #     # the machine is free (i.e. has no unfinished actions)
        #     add_goal_to_problem( harv_free(machine), EndTiming() )

        __use_total_yield_mass_in_silos = True
        if __use_total_yield_mass_in_silos:
            add_goal_to_problem( GE( total_yield_mass_in_silos(),
                                     self.__problem_stats.fields.yield_mass_remaining.total \
                                     + self.__problem_stats.machines.yield_mass_in_tvs.total - 10 ),
                                 EndTiming() )
        else:
            for machine in self.__objects.tvs.values():

                # the machine is free (i.e. has no unfinished actions)
                add_goal_to_problem( tv_free(machine), EndTiming() )

                # no machine has yield in the bunker
                add_goal_to_problem( LE( tv_bunker_mass(machine), 0.1 ), EndTiming() )

            if self.__problem_settings.silo_planning_type is conf.SiloPlanningType.WITH_SILO_ACCESS_CAPACITY_AND_COMPACTION:
                # no silo access points has uncollected yield
                for silo_access in self.__objects.silo_accesses.values():
                    if silo_access is self.__objects.no_silo_access:
                        continue
                    add_goal_to_problem( silo_access_cleared(silo_access), EndTiming() )

        if self.__problem_settings.planning_type is conf.PlanningType.TEMPORAL:
            if self.__problem_settings.temporal_optimization_setting is conf.TemporalOptimizationSetting.MAKESPAN:
                self.__problem.add_quality_metric(unified_planning.model.metrics.MinimizeMakespan())
        elif self.__problem_settings.planning_type is conf.PlanningType.SEQUENTIAL:
            expressions = []
            if self.__problem_settings.sequential_optimization_settings.k_harv_waiting_time > 1e-9:
                k = self.__problem_settings.sequential_optimization_settings.k_harv_waiting_time
                expression = None
                harv_waiting_time = self.__fluents_manager.get_fluent(fn.harv_waiting_time)
                for harv in self.__objects.harvesters.values():
                    if harv is self.__objects.no_harvester:
                        continue
                    if expression is None:
                        expression = harv_waiting_time(harv)
                    else:
                        expression = Plus( expression, harv_waiting_time(harv) )
                if 1-1e-9 < k < 1+1e-9:
                    expressions.append(expression)
                else:
                    expressions.append(Times(k,expression))
            if self.__problem_settings.sequential_optimization_settings.k_tv_waiting_time > 1e-9:
                k = self.__problem_settings.sequential_optimization_settings.k_tv_waiting_time
                expression = None
                tv_waiting_time = self.__fluents_manager.get_fluent(fn.tv_waiting_time)
                for tv in self.__objects.tvs.values():
                    if expression is None:
                        expression = tv_waiting_time(tv)
                    else:
                        expression = Plus( expression, tv_waiting_time(tv) )
                if 1-1e-9 < k < 1+1e-9:
                    expressions.append(expression)
                else:
                    expressions.append(Times(k,expression))
            if len(expressions) > 0:
                expression = expressions[0]
                for i, exp in enumerate(expressions, start=1):
                    expression = Plus(expression, exp)
                self.__problem.add_quality_metric(
                    unified_planning.model.metrics.MinimizeExpressionOnFinalState( expression )
                )

    def __init_fluents_and_stats(self,
                                 machine_initial_states: Dict[int, MachineState],
                                 field_initial_states: Dict[int, FieldState],
                                 pre_assigned_fields: FieldPreAssignments):

        """ Set the initial fluent values and initialize the problem statistics

        Parameters
        ----------
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        field_initial_states : Dict[int, FieldState]
            Field initial states: {field_id: field_state}
        pre_assigned_fields : FieldPreAssignments
            Field pre-assignments (disregarded if None)
        """

        print('...Initializing process_fluents_and_stats...')
        _t_start = time.time()
        self.__init_process_fluents_and_stats()
        print(f'...process_fluents_and_stats initialized [{time.time() - _t_start}s]')

        print('...Initializing location_distance_fluents_and_stats...')
        _t_start = time.time()
        self.__init_location_distance_fluents_and_stats(machine_initial_states)
        print(f'...location_distance_fluents_and_stats initialized [{time.time() - _t_start}s]')

        print('...Initializing field_fluents_and_stats...')
        _t_start = time.time()
        self.__init_field_fluents_and_stats(field_initial_states, machine_initial_states, pre_assigned_fields)
        print(f'...field_fluents_and_stats initialized [{time.time() - _t_start}s]')

        print('...Initializing machine_fluents_and_stats...')
        _t_start = time.time()
        self.__init_machine_fluents_and_stats(machine_initial_states)
        print(f'...machine_fluents_and_stats initialized [{time.time() - _t_start}s]')

        print('...Initializing silo_fluents_and_stats...')
        _t_start = time.time()
        self.__init_silo_fluents_and_stats()
        print(f'...silo_fluents_and_stats initialized [{time.time() - _t_start}s]')

        print('...Initializing compactor_fluents_and_stats...')
        _t_start = time.time()
        self.__init_compactor_fluents_and_stats()
        print(f'...compactor_fluents_and_stats initialized [{time.time() - _t_start}s]')

    def __init_process_fluents_and_stats(self):

        """ Set the initial values of general process fluents and initialize/update the respective problem statistics """
        
        self.__fluents_manager.add_fluent_initial_value(fn.planning_failed, None, False)
        self.__fluents_manager.add_fluent_initial_value(fn.default_infield_transit_duration_to_access_point, None,
                                                        self.__problem_settings.infield_transit_duration_to_field_access)

    def __init_location_distance_fluents_and_stats(self, machine_initial_states: Dict[int, MachineState]):

        """ Set the initial values of 'distance between locations' fluents and initialize/update the respective problem statistics

        Parameters
        ----------
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        """
        
        # @note: we do it separately in case the path loc1->loc2 is different from path loc2->loc1
        # @note: only the following connections are set:
        #   * field_access_points <-> field_access_points (another field)
        #   * field_access_points <-> silo_access_points
        #   * machine_initial_locations -> field_access_points
        #   * machine_initial_locations (TVs only) -> silo_access_points


        self.__problem_stats.transit = ProblemTransitStats()

        self.__init_location_distance_fluents_from_fields()
        self.__init_location_distance_fluents_from_silos()
        self.__init_location_distance_fluents_from_machine_init_locations(machine_initial_states)

    def __init_location_distance_fluents_from_fields(self):

        """ Set the initial values 'distance from field access points to other locations' fluents and initialize/update the respective problem statistics """
        
        planner = self.__out_field_route_planner

        added_field_ids = set()

        for field_id, field_aro in self.__data_manager.fields.items():
            added_field_ids.add(field_id)
            if len(field_aro.subfields) == 0:
                raise ValueError(f'Field with id {field_id} has no subfields')

            for fap_ind, fap in enumerate( field_aro.subfields[0].access_points ):
                field_access_name = get_field_access_location_name(field_id, fap_ind)
                field_access = self.__objects.field_accesses.get(field_access_name)
                if field_access is None:
                    raise ValueError(f'Field access with name {field_access_name} does not exist')

                # connect field_access_points to field_access_points of other fields
                for field_id_2, field_aro_2 in self.__data_manager.fields.items():
                    if field_id_2 == field_id: # @todo interconnect also access_points from the same field?
                        continue

                    if len(field_aro_2.subfields) == 0:
                        raise ValueError(f'Field with id {field_id_2} has no subfields')

                    for fap_ind_2, fap_2 in enumerate(field_aro_2.subfields[0].access_points):
                        field_access_name_2 = get_field_access_location_name(field_id_2, fap_ind_2)
                        field_access_2 = self.__objects.field_accesses.get(field_access_name_2)
                        if field_access_2 is None:
                            raise ValueError(f'Field access with name {field_access_name_2} does not exist')

                        if field_id_2 == field_id and field_access_2 is field_access:
                            continue

                        path = planner.get_path(fap, fap_2, None)
                        dist = getGeometryLength(path)

                        # distances field_access (this field) -> field_access (other field)
                        self.__fluents_manager.add_fluent_initial_value(fn.transit_distance_fap_fap, (field_access, field_access_2), dist)

                        self.__problem_stats.transit.update_value(dist,
                                                                  ProblemTransitStats.TransitType.BETWEEN_FIELD_ACCESSES_DIFFERENT_FIELDS,
                                                                  [MachineType.HARVESTER, MachineType.OLV],
                                                                  None,
                                                                  [field_id, field_id_2])

                # connect field_access_points to silo_access_points
                for silo_id, silo_aro in self.__data_manager.silos.items():
                    silo_name = get_silo_location_name(silo_id)
                    silo = self.__objects.silos.get(silo_name)
                    if silo is None:
                        raise ValueError(f'Silo with name {silo_name} does not exist')

                    for sap_ind, sap in enumerate(silo_aro.access_points):
                        name = get_silo_access_location_name(silo_id, sap_ind)
                        silo_access = self.__objects.silo_accesses.get(name)
                        if silo_access is None:
                            raise ValueError(f'Silo access with name {name} does not exist')

                        path = planner.get_path(fap, sap, None)
                        dist = getGeometryLength(path)

                        # distances field_access -> silo_access
                        self.__fluents_manager.add_fluent_initial_value(fn.transit_distance_fap_sap, (field_access, silo_access), dist)


                        self.__problem_stats.transit.update_value(dist,
                                                                  ProblemTransitStats.TransitType.FROM_FIELD_ACCESS_TO_SILO_ACCESS,
                                                                  MachineType.OLV,
                                                                  None,
                                                                  None)

    def __init_location_distance_fluents_from_silos(self):

        """ Set the initial values 'distance from silo access points to other locations' fluents and initialize/update the respective problem statistics """
        
        planner = self.__out_field_route_planner

        for silo_id, silo_aro in self.__data_manager.silos.items():
            for sap_ind, sap in enumerate(silo_aro.access_points):
                name = get_silo_access_location_name(silo_id, sap_ind)
                silo_access = self.__objects.silo_accesses.get(name)
                if silo_access is None:
                    raise ValueError(f'Silo access with name {name} does not exist')

                # connect silo_access_points to field_access_points
                for field_id, field_aro in self.__data_manager.fields.items():
                    if len(field_aro.subfields) == 0:
                        raise ValueError(f'Field with id {field_id} has no subfields')

                    for fap_ind, fap in enumerate(field_aro.subfields[0].access_points):
                        field_access_name = get_field_access_location_name(field_id, fap_ind)
                        field_access = self.__objects.field_accesses.get(field_access_name)
                        if field_access is None:
                            raise ValueError(f'Field access with name {field_access_name} does not exist')

                        path = planner.get_path(sap, fap, None)
                        dist = getGeometryLength(path)

                        # distances silo_access -> field_access
                        self.__fluents_manager.add_fluent_initial_value(fn.transit_distance_sap_fap, (silo_access, field_access), dist)

                        self.__problem_stats.transit.update_value(dist,
                                                                  ProblemTransitStats.TransitType.FROM_SILO_ACCESS_TO_FIELD_ACCESS,
                                                                  MachineType.OLV,
                                                                  None,
                                                                  None)

    def __init_location_distance_fluents_from_machine_init_locations(self, machine_initial_states: Dict[int, MachineState]):

        """ Set the initial values 'distance from machine initial locations to other locations' fluents and initialize/update the respective problem statistics 
        
        Parameters
        ----------
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        """
        
        planner = self.__out_field_route_planner

        for machine_id, machine_aro in self.__data_manager.machines.items():
            if machine_aro.machinetype is MachineType.HARVESTER:
                name = get_harvester_name(machine_id)
                machine = self.__objects.harvesters.get(name)
                if machine is None:
                    raise ValueError(f'Harvester with name {name} does not exist')
            elif machine_aro.machinetype is MachineType.OLV:
                name = get_tv_name(machine_id)
                machine = self.__objects.tvs.get(name)
                if machine is None:
                    raise ValueError(f'TV with name {name} does not exist')
            else:
                continue

            machine_state = machine_initial_states.get(machine_id)
            if machine_state is None:
                raise ValueError(f'Machine state for machine {name} was not given')

            if machine_state.location_name is not None:  # the machine is located somewhere else
                continue

            loc_name = get_machine_initial_location_name(name)
            loc = self.__objects.machine_init_locations.get(loc_name)
            if loc is None:
                raise ValueError(f'Machine init location with name {loc_name} does not exist')

            # connect machine_initial_locations to field_access_points
            for field_id, field_aro in self.__data_manager.fields.items():
                if len(field_aro.subfields) == 0:
                    raise ValueError(f'Field with id {field_id} has no subfields')

                for fap_ind, fap in enumerate( field_aro.subfields[0].access_points ):
                    field_access_name = get_field_access_location_name(field_id, fap_ind)
                    field_access = self.__objects.field_accesses.get(field_access_name)
                    if field_access is None:
                        raise ValueError(f'Field access with name {field_access_name} does not exist')

                    path = planner.get_path(machine_state.position, fap, machine_aro)
                    dist = getGeometryLength(path)

                    # distances init_location -> access_point
                    self.__fluents_manager.add_fluent_initial_value(fn.transit_distance_init_fap, (loc, field_access), dist)

                    self.__problem_stats.transit.update_value(dist,
                                                              ProblemTransitStats.TransitType.FROM_INIT_LOC_TO_FIELD_ACCESS,
                                                              machine_aro.machinetype,
                                                              machine_aro.id,
                                                              field_id)

            # connect machine_initial_locations to silo_access_points (only TVs)
            if machine_aro.machinetype is MachineType.OLV:
                for silo_id, silo_aro in self.__data_manager.silos.items():
                    for sap_ind, sap in enumerate(silo_aro.access_points):
                        name = get_silo_access_location_name(silo_id, sap_ind)
                        silo_access = self.__objects.silo_accesses.get(name)
                        if silo_access is None:
                            raise ValueError(f'Silo access with name {name} does not exist')

                        path = planner.get_path(machine_state.position, sap, None)
                        dist = getGeometryLength(path)

                        # distances field_access <-> silo_access
                        self.__fluents_manager.add_fluent_initial_value(fn.transit_distance_init_sap, (loc, silo_access), dist)

                        self.__problem_stats.transit.update_value(dist,
                                                                  ProblemTransitStats.TransitType.FROM_INIT_LOC_TO_SILO_ACCESS,
                                                                  machine_aro.machinetype,
                                                                  machine_aro.id,
                                                                  None)

    def __init_field_fluents_and_stats(self,
                                       field_initial_states: Dict[int, FieldState],
                                       machine_initial_states: Dict[int, MachineState],
                                       pre_assigned_fields: FieldPreAssignments):

        """ Set the initial values of field fluents and initialize/update the respective problem statistics

        Parameters
        ----------
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        field_initial_states : Dict[int, FieldState]
            Field initial states: {field_id: field_state}
        pre_assigned_fields : FieldPreAssignments
            Field pre-assignments (disregarded if None)
        """

        self.__problem_stats.fields = ProblemFieldStats()

        self.__fluents_manager.add_fluent_initial_value(fn.field_plan_id, self.__objects.no_field, FieldPartialPlanManager.NO_PLAN_ID)
        self.__fluents_manager.add_fluent_initial_value(fn.field_harvester, self.__objects.no_field, self.__objects.no_harvester)
        self.__fluents_manager.add_fluent_initial_value(fn.field_pre_assigned_harvester, self.__objects.no_field, self.__objects.no_harvester)
        self.__fluents_manager.add_fluent_initial_value(fn.field_access_field, self.__objects.no_field_access, self.__objects.no_field)

        harvester_turns: Dict[Object, Dict[int, Object]] = dict()

        for field_id, field_aro in self.__data_manager.fields.items():
            name = get_field_location_name(field_id)
            field = self.__objects.fields.get(name)
            if field is None:
                raise ValueError(f'Field with name {name} does not exist')

            self.__fluents_manager.add_fluent_initial_value(fn.field_id, field, field_id)

            self.__problem_stats.fields.field_ids.update(field_id)

            pre_assigned_harv = self.__objects.no_harvester
            pre_assigned_turn = None
            if pre_assigned_fields is not None:
                pre_assigned_harv_id_turn = pre_assigned_fields.get(field_id)
                if pre_assigned_harv_id_turn is not None:
                    pre_assigned_harv_id = pre_assigned_harv_id_turn.harv_id
                    pre_assigned_turn = pre_assigned_harv_id_turn.turn
                    if pre_assigned_turn is not None and pre_assigned_turn < 1:
                        pre_assigned_turn = None
                    harv_name = get_harvester_name(pre_assigned_harv_id)
                    pre_assigned_harv = self.__objects.harvesters.get(harv_name)
                    if pre_assigned_harv is None:
                        raise ValueError(f'The harvester with id {pre_assigned_harv_id} pre-assigned to field with id {field_id} does not exists')

            self.__fluents_manager.add_fluent_initial_value(fn.field_pre_assigned_harvester, field, pre_assigned_harv)

            self.__fluents_manager.add_fluent_initial_value(fn.field_plan_id, field, FieldPartialPlanManager.NO_PLAN_ID)

            self.__fluents_manager.add_fluent_initial_value(fn.field_harvester, field, self.__objects.no_harvester)

            if len(field_aro.subfields) == 0:
                raise ValueError(f'Field with id {field_id} has no subfields')

            area = calc_area(field_aro.subfields[0].boundary_outer)
            if area < 1e-3:
                raise ValueError(f'Field with id {field_id} has a subfield with invalid outer boundary')

            mpa = t_ha2Kg_sqrm(FieldState.DEFAULT_AVG_MASS_PER_AREA_T_HA)
            field_state = field_initial_states.get(field_id)
            if field_state is not None:
                if field_state.avg_mass_per_area_t_ha < 1e-9:
                    print(f'[WARNING] Field with id {field_id}: it has an invalid avg_mass_per_area_t_ha. Using default.')
                else:
                    mpa = t_ha2Kg_sqrm(field_state.avg_mass_per_area_t_ha)
                if field_state.harvested_percentage < -1e-9 or field_state.harvested_percentage > 100 - 1e-9:
                    print(f'[WARNING] Field with id {field_id} has an invalid harvested_percentage or it is already harvested. '
                          f'Setting it as harvested.')
                    field_mass = 0
                else:
                    field_mass_total = mpa * area
                    field_mass = field_mass_total * 0.01 * (100 - field_state.harvested_percentage)
            else:
                mpa = t_ha2Kg_sqrm(FieldState.DEFAULT_AVG_MASS_PER_AREA_T_HA)
                field_mass_total = field_mass = mpa * area

            if field_mass < 1e-3:
                field_mass = 0.0
                self.__fluents_manager.add_fluent_initial_value(fn.field_harvested, field, True)
                self.__fluents_manager.add_fluent_initial_value(fn.field_started_harvest_int, field, 1)
                self.__fluents_manager.add_fluent_initial_value(fn.field_timestamp_harvested, field, 0.0)
                self.__fluents_manager.add_fluent_initial_value(fn.field_timestamp_started_harvest, field, 0.0)
                self.__fluents_manager.add_fluent_initial_value(fn.field_timestamp_assigned, field, 0.0)
                self.__harvested_fields.add(field)

                assert pre_assigned_turn is None, f'Field {field} was pre-assigned turn {pre_assigned_turn}, but the field is already harvested'
            else:
                self.__fluents_manager.add_fluent_initial_value(fn.field_harvested, field, False)

                for machine_id, machine in self.__data_manager.machines.items():
                    if machine.machinetype == MachineType.HARVESTER \
                            and machine_id in machine_initial_states.keys() \
                            and machine_initial_states.get(machine_id).location_name == name:
                        harv_name = get_harvester_name(machine_id)
                        harv = self.__objects.harvesters.get(harv_name)
                        if pre_assigned_harv is self.__objects.no_harvester:
                            pre_assigned_harv = harv
                        else:
                            assert pre_assigned_harv == harv, f'Field {field} was pre-assigned to harvester {pre_assigned_harv}, but harvester {harv} is currently at the field'
                        if pre_assigned_turn is None or pre_assigned_turn < 1:
                            pre_assigned_turn = 1
                        else:
                            assert pre_assigned_turn == 1, f'Field {field} was pre-assigned turn {pre_assigned_turn}, but harvester {harv} is currently at the field'


                self.__problem_stats.fields.field_area.update(area)
                self.__problem_stats.fields.yield_mass_total.update(field_mass_total)
                self.__problem_stats.fields.yield_mass_remaining.update(field_mass)

                self.__remaining_mass_fields[field] = field_mass

                if pre_assigned_turn is not None and pre_assigned_harv is not self.__objects.no_harvester:
                    turns = harvester_turns.get(pre_assigned_harv)
                    if turns is None:
                        turns = dict()
                        harvester_turns[pre_assigned_harv] = turns
                    assert pre_assigned_turn not in turns.keys(), \
                        f'The turn {pre_assigned_turn} for harvester {pre_assigned_harv} was already assigned to another field'
                    assert pre_assigned_turn <= self.__objects.count_fields, \
                        f'The turn {pre_assigned_turn} for harvester {pre_assigned_harv} is invalid'
                    turns[pre_assigned_turn] = field

                self.__objects.count_fields_to_work += 1

            self.__fluents_manager.add_fluent_initial_value(fn.field_area_per_yield_mass, field, 1.0/mpa)
            self.__problem_stats.fields.field_area_per_yield_mass.update(1.0/mpa)

            self.__fluents_manager.add_fluent_initial_value(fn.field_yield_mass_total, field, field_mass)

            self.__fluents_manager.add_fluent_initial_value(fn.field_yield_mass_after_reserve, field, field_mass)
            self.__fluents_manager.add_fluent_initial_value(fn.field_yield_mass_unharvested, field, field_mass)
            self.__fluents_manager.add_fluent_initial_value(fn.field_yield_mass_minus_planned, field, field_mass)

            for ind, ap in enumerate(field_aro.subfields[0].access_points):
                name = get_field_access_location_name(field_id, ind)
                field_access = self.__objects.field_accesses.get(name)
                if field_access is None:
                    raise ValueError(f'Field access with name {name} does not exist')

                self.__fluents_manager.add_fluent_initial_value(fn.field_access_field, field_access, field)
                self.__fluents_manager.add_fluent_initial_value(fn.field_access_field_id, field_access, field_id)

                self.__fluents_manager.add_fluent_initial_value(fn.field_access_index, field_access, ind)

            self.__problem_stats.fields.field_access_points_count.update( len(field_aro.subfields[0].access_points) )

        self.__fluents_manager.add_fluent_initial_value(fn.total_yield_mass_in_fields_unreserved, None, self.__problem_stats.fields.yield_mass_remaining.total)
        self.__fluents_manager.add_fluent_initial_value(fn.total_yield_mass_in_fields_unharvested, None, self.__problem_stats.fields.yield_mass_remaining.total)

        for harv, turns in harvester_turns.items():
            sorted_turns = [(turn, field) for turn, field in turns.items() ]
            sorted_turns.sort(key=lambda x: x[0])
            for i, turn_pair in enumerate(sorted_turns):
                turn = turn_pair[0]
                field = turn_pair[1]
                assert i > 0 or turn == 1, f'The pre-assigned turns of harvester {harv} are incomplete'
                assert i == 0 or turn == sorted_turns[i-1][0] + 1, f'The pre-assigned turns of harvester {harv} are incomplete'

                self.__fluents_manager.add_fluent_initial_value(fn.field_pre_assigned_harvester, field, harv)
                self.__fluents_manager.add_fluent_initial_value(fn.field_pre_assigned_turn, field, turn)
            self.__fluents_manager.add_fluent_initial_value(fn.harv_count_pre_assigned_field_turns, harv, len(sorted_turns))

    def __init_machine_fluents_and_stats(self, machine_initial_states: Dict[int, MachineState]):

        """ Set the initial values of harvester and transport vehicle fluents and initialize/update the respective problem statistics

        Parameters
        ----------
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        """

        self.__problem_stats.machines = ProblemMachineStats()

        # # default state to set initial values

        # initialize for no/invalid machine objects
        self.__init_harvester_fluents_and_stats( self.__objects.no_harvester, None, None, False )

        tvs: Dict[int, Object] = dict()

        for machine_id, machine_aro in self.__data_manager.machines.items():
            if machine_aro.machinetype is MachineType.HARVESTER:
                name = get_harvester_name(machine_id)
                machine = self.__objects.harvesters.get(name)
                if machine is None:
                    raise ValueError(f'Harvester with name {name} does not exist')
                self.__init_harvester_fluents_and_stats( machine, machine_aro, machine_initial_states.get(machine_id) )
            elif machine_aro.machinetype is MachineType.OLV:
                name = get_tv_name(machine_id)
                machine = self.__objects.tvs.get(name)
                if machine is None:
                    raise ValueError(f'TV with name {name} does not exist')
                self.__init_tv_fluents_and_stats( machine, machine_aro, machine_initial_states.get(machine_id) )
                tvs[machine_id] = machine

        self.__check_overloading_machines()
        self.__init_pre_assigned_tvs_fluents(tvs)


    def __init_harvester_fluents_and_stats(self,
                                           machine: Object,
                                           machine_aro: Machine,
                                           machine_state: MachineState,
                                           is_valid_machine: bool = True):

        """ Set the fluent initial values of one harvester and initialize/update the respective problem statistics

        Parameters
        ----------
        machine : Object
            Harvester object
        machine_aro : Machine
            Harvester
        machine_state : MachineState
            Machine initial state
        is_valid_machine : bool
            Is it a valid harvester (True) or the object corresponds to 'no-harvester' (False)?
        """

        if is_valid_machine:

            if machine_aro.def_working_speed < 1e-3:
                raise ValueError(f'Machine {machine.name} has an invalid working speed')

            if machine_aro.working_width < 1e-3:
                raise ValueError(f'Machine {machine.name} has an invalid working width')

            wtpa = 1 / (machine_aro.def_working_speed * machine_aro.working_width)  # working time per m2

            speed_empty = machine_aro.max_speed_empty
            if speed_empty < 1e-9:
                speed_empty = machine_aro.max_speed_full
            if speed_empty < 1e-9:
                raise ValueError(f'Machine {machine.name} has an invalid transit speed')

            if machine_state is None:
                raise ValueError(f'Machine state for machine {machine.name} was not given')

            self.__fluents_manager.add_fluent_initial_value(fn.harv_free, machine, True)
            self.__fluents_manager.add_fluent_initial_value(fn.harv_transit_speed_empty, machine, speed_empty)
            self.__fluents_manager.add_fluent_initial_value(fn.harv_working_time_per_area, machine, wtpa)

            self.__problem_stats.machines.harv_transit_speed_empty.update(speed_empty)
            self.__problem_stats.machines.harv_working_time_per_area.update(wtpa)

            if machine_state.location_name is None:  # not given --> initial location
                loc_name = get_machine_initial_location_name(machine.name)
                loc = self.__objects.machine_init_locations.get( loc_name )
                if loc is None:
                    raise ValueError(f'Machine init location with name {loc_name} does not exist')
                self.__fluents_manager.add_fluent_initial_value(fn.harv_at_init_loc, machine, loc)
                self.__fluents_manager.add_fluent_initial_value(fn.harv_at_field, machine, self.__objects.no_field)
                self.__fluents_manager.add_fluent_initial_value(fn.harv_at_field_access, machine, self.__objects.no_field_access)
                self.__harvesters_at_init_loc.add(machine)

            elif machine_state.location_name in self.__objects.fields:
                loc = self.__objects.fields.get(machine_state.location_name)
                self.__fluents_manager.add_fluent_initial_value(fn.harv_at_init_loc, machine, self.__objects.no_init_loc)
                self.__fluents_manager.add_fluent_initial_value(fn.harv_at_field, machine, loc)
                self.__fluents_manager.add_fluent_initial_value(fn.harv_at_field_access, machine, self.__objects.no_field_access)
                if loc in self.__harvested_fields:
                    self.__with_field_exit = True
                    self.__harvesters_in_finished_fields[machine] = loc
                else:
                    self.__harvesters_in_unfinished_fields[machine] = loc
                    if machine_state.overloading_machine_id is not None:
                        self.__overloading_harvesters[machine.name] = (loc, get_tv_name(machine_state.overloading_machine_id))

            elif machine_state.location_name in self.__objects.field_accesses:
                loc = self.__objects.field_accesses.get(machine_state.location_name)
                self.__fluents_manager.add_fluent_initial_value(fn.harv_at_init_loc, machine, self.__objects.no_init_loc)
                self.__fluents_manager.add_fluent_initial_value(fn.harv_at_field, machine, self.__objects.no_field)
                self.__fluents_manager.add_fluent_initial_value(fn.harv_at_field_access, machine, loc)

            else:
                raise ValueError(f'Machine {machine.name} has an invalid location {machine_state.location_name}')

        elif machine is not None:
            self.__fluents_manager.add_fluent_initial_value(fn.harv_at_init_loc, machine, self.__objects.no_init_loc)
            self.__fluents_manager.add_fluent_initial_value(fn.harv_at_field, machine, self.__objects.no_field)
            self.__fluents_manager.add_fluent_initial_value(fn.harv_at_field_access, machine, self.__objects.no_field_access)

    def __init_tv_fluents_and_stats(self,
                                    machine: Object,
                                    machine_aro: Machine,
                                    machine_state: MachineState,
                                    is_valid_machine: bool = True):

        """ Set the fluent initial values of one transport vehicle and initialize/update the respective problem statistics

        Parameters
        ----------
        machine : Object
            Transport vehicle object
        machine_aro : Machine
            Transport vehicle
        machine_state : MachineState
            Machine initial state
        is_valid_machine : bool
            Is it a valid transport vehicle (True) or the object corresponds to 'no-transport-vehicle' (False)?
        """

        if is_valid_machine:

            self.__problem_stats.machines.tv_bunker_mass_capacity.update(machine_aro.bunker_mass)

            speed_empty = machine_aro.max_speed_empty
            if speed_empty < 1e-9:
                speed_empty = machine_aro.max_speed_full
            if speed_empty < 1e-9:
                raise ValueError(f'Machine {machine.name} has an invalid transit speed')

            speed_full = machine_aro.max_speed_full
            if speed_full < 1e-9:
                speed_full = speed_empty

            if machine_state is None:
                raise ValueError(f'Machine state for machine {machine.name} was not given')

            self.__fluents_manager.add_fluent_initial_value(fn.tv_free, machine, True)
            self.__fluents_manager.add_fluent_initial_value(fn.tv_transit_speed_empty, machine, speed_empty)
            self.__fluents_manager.add_fluent_initial_value(fn.tv_transit_speed_full, machine, speed_full)

            self.__problem_stats.machines.tv_transit_speed_empty.update(speed_empty)
            self.__problem_stats.machines.tv_transit_speed_full.update(speed_full)

            self.__fluents_manager.add_fluent_initial_value(fn.tv_unloading_speed_mass, machine, machine_aro.unloading_speed_mass)
            self.__fluents_manager.add_fluent_initial_value(fn.tv_total_capacity_mass, machine, machine_aro.bunker_mass)
            self.__fluents_manager.add_fluent_initial_value(fn.tv_bunker_mass, machine, machine_state.bunker_mass)

            self.__problem_stats.machines.tv_unloading_speed_mass.update(machine_aro.unloading_speed_mass)
            self.__problem_stats.machines.yield_mass_in_tvs.update(machine_state.bunker_mass)

            _force_unload = False
            _tv_can_potentially_load = True
            _tv_can_potentially_unload = False
            _tv_ready_to_unload = False

            if machine_state.location_name is None:  # not given --> initial location
                loc_name = get_machine_initial_location_name(machine.name)
                loc = self.__objects.machine_init_locations.get( loc_name )
                if loc is None:
                    raise ValueError(f'Machine init location with name {loc_name} does not exist')
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_init_loc, machine, loc)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_field, machine, self.__objects.no_field)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_field_access, machine, self.__objects.no_field_access)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_silo_access, machine, self.__objects.no_silo_access)
                self.__tvs_at_init_loc.add(machine)
                _tv_can_potentially_load = _tv_can_potentially_unload = True
                if machine_state.bunker_mass >= self.__factor_loaded_machine * machine_aro.bunker_mass:
                    self.__tvs_at_init_loc_with_load.add(machine)

                    for silo_id, silo_aro in self.__data_manager.silos.items():
                        for sap_ind, sap in enumerate(silo_aro.access_points):
                            name = get_silo_access_location_name(silo_id, sap_ind)
                            if name not in self.__objects.silo_accesses.keys():
                                continue
                            dist = calc_dist(machine_state.position, sap)
                            if dist < 10:
                                _force_unload = True
                                break
                        if _force_unload:
                            break

            elif machine_state.location_name in self.__objects.fields:
                loc = self.__objects.fields.get(machine_state.location_name)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_init_loc, machine, self.__objects.no_init_loc)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_field, machine, loc)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_field_access, machine, self.__objects.no_field_access)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_silo_access, machine, self.__objects.no_silo_access)
                _tv_can_potentially_load = True
                # _tv_can_potentially_unload = False
                _tv_can_potentially_unload = True
                self.__with_field_exit = True
                if loc in self.__harvested_fields:
                    self.__tvs_in_finished_fields[machine] = loc
                else:
                    self.__tvs_in_unfinished_fields[machine] = loc
                    if machine_state.overloading_machine_id is not None:
                       if machine_state.bunker_mass <= self.__factor_full_machine * machine_aro.bunker_mass:
                           self.__overloading_tvs[machine.name] = (loc, get_harvester_name(machine_state.overloading_machine_id))
                       else:
                           self.__overloading_tvs_but_full.add(machine.name)
                           _force_unload = True

            elif machine_state.location_name in self.__objects.field_accesses:
                loc = self.__objects.field_accesses.get(machine_state.location_name)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_init_loc, machine, self.__objects.no_init_loc)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_field, machine, self.__objects.no_field)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_field_access, machine, loc)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_silo_access, machine, self.__objects.no_silo_access)
                _tv_can_potentially_load = _tv_can_potentially_unload = True

            elif machine_state.location_name in self.__objects.silo_accesses:
                loc = self.__objects.silo_accesses.get(machine_state.location_name)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_init_loc, machine, self.__objects.no_init_loc)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_field, machine, self.__objects.no_field)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_field_access, machine, self.__objects.no_field_access)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_at_silo_access, machine, loc)
                _force_unload = machine_state.bunker_mass >= self.__factor_loaded_machine * machine_aro.bunker_mass
                _tv_can_potentially_load = _tv_can_potentially_unload = True
                if machine_state.bunker_mass >= self.__factor_loaded_machine * machine_aro.bunker_mass:
                    self.__tvs_at_silos_with_load[machine] = loc
                    if self.__fluents_manager.get_fluent(fn.tv_ready_to_unload) is not None:
                        self.__fluents_manager.add_fluent_initial_value(fn.tv_ready_to_unload, machine, True)
                        _tv_ready_to_unload = True

            else:
                raise ValueError(f'Machine {machine.name} has an invalid location {machine_state.location_name}')

            if _tv_ready_to_unload:
                self.__fluents_manager.add_fluent_initial_value(fn.tv_can_load, machine, False)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_can_unload, machine, False)
            elif _force_unload:
                self.__fluents_manager.add_fluent_initial_value(fn.tv_can_load, machine, False)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_can_unload, machine, True)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_waiting_to_drive, machine, True)
                self.__fluents_manager.add_fluent_initial_value(fn.tv_waiting_to_drive_id, machine, 1)
            else:
                if _tv_can_potentially_load and machine_state.bunker_mass <= self.__factor_full_machine * machine_aro.bunker_mass:
                    self.__fluents_manager.add_fluent_initial_value(fn.tv_can_load, machine, True)
                if _tv_can_potentially_unload and machine_state.bunker_mass >= self.__factor_loaded_machine * machine_aro.bunker_mass:
                    self.__fluents_manager.add_fluent_initial_value(fn.tv_can_unload, machine, True)


        elif machine is not None:  # we only need to initialize these fluents
            self.__fluents_manager.add_fluent_initial_value(fn.tv_at_init_loc, machine, self.__objects.no_init_loc)
            self.__fluents_manager.add_fluent_initial_value(fn.tv_at_field, machine, self.__objects.no_field)
            self.__fluents_manager.add_fluent_initial_value(fn.tv_at_field_access, machine, self.__objects.no_field_access)
            self.__fluents_manager.add_fluent_initial_value(fn.tv_at_silo_access, machine, self.__objects.no_silo_access)


    def __check_overloading_machines(self):

        """ Check the validity of the currently-overloading machines (initial plan state) """

        harvs_to_remove = list()
        for harv_name, (field, tv_name) in self.__overloading_harvesters.items():
            if tv_name in self.__overloading_tvs_but_full:
                harvs_to_remove.append(harv_name)
                continue
            field_harv = self.__overloading_tvs.get(tv_name)
            assert field_harv is not None, f'Overloading machine missmatch harvester ({harv_name}) -> tv({tv_name}): tv not overloading'
            assert field_harv[0] is field, f'Field of overloading machine missmatch harvester ({harv_name} - {field}) -> tv({tv_name} - {field_harv[0]}): field missmatch'
            assert field_harv[1] == harv_name, f'Overloading machine missmatch harvester ({harv_name}) -> tv({tv_name} - {field_harv[1]}): harvester missmatch'
        for harv_name in harvs_to_remove:
            self.__overloading_harvesters.pop(harv_name)
        for tv_name, (field, harv_name) in self.__overloading_tvs.items():
            field_tv = self.__overloading_harvesters.get(harv_name)
            assert field_tv is not None, f'Overloading machine missmatch tv({tv_name}) -> harvester ({harv_name}): harvester not overloading'
            assert field_tv[0] is field, f'Field of overloading machine missmatch tv({tv_name} - {field}) -> harvester ({harv_name} - {field_tv[0]}): field missmatch'
            assert field_tv[1] == tv_name, f'Overloading machine missmatch tv({tv_name}) -> harvester ({harv_name} - {field_tv[1]}): tv missmatch'


    def __init_pre_assigned_tvs_fluents(self, tvs: Dict[int, Object]):

        """ Set the fluent initial values corresponding to transport vehicle pre-assignments

        Parameters
        ----------
        tvs : Dict[int, Object]
            Transport vehicle objects: {tv_id: object}
        """


        if len(self.__overloading_tvs) > 0 and self.__pre_assigned_tvs is None:
            self.__pre_assigned_tvs = TVPreAssignments()
            for tv_name, (field, harv_name) in self.__overloading_tvs.items():
                tv_id = get_tv_id_from_name(tv_name)
                harv_id = get_harvester_id_from_name(harv_name)
                self.__pre_assigned_tvs.cyclic_turns = False
                self.__pre_assigned_tvs.harvester_tv_turns[harv_id] = [tv_id]

        pre_assigned_tvs = self.__pre_assigned_tvs

        if pre_assigned_tvs is not None:
            assert pre_assigned_tvs.is_valid(), f'TV pre-assignments are not valid'

            for harv_id, tv_ids in pre_assigned_tvs.harvester_tv_turns.items():
                harv_name = get_harvester_name(harv_id)
                harv = self.__objects.harvesters.get(harv_name)
                if harv is None:
                    continue
                self.__fluents_manager.add_fluent_initial_value(fn.harv_pre_assigned_tv_turns_left, harv, len(tv_ids))

        for tv_id, tv in tvs.items():
            if pre_assigned_tvs is None:
                self.__fluents_manager.add_fluent_initial_value(fn.tv_pre_assigned_harvester, tv, self.__objects.no_harvester)
                continue

            pre_assigned_harv_id, pre_assigned_turn = pre_assigned_tvs.get_tv_harvester_and_turn(tv_id)
            if pre_assigned_harv_id is None:
                self.__fluents_manager.add_fluent_initial_value(fn.tv_pre_assigned_harvester, tv, self.__objects.no_harvester)
                continue

            harv_name = get_harvester_name(pre_assigned_harv_id)
            pre_assigned_harv = self.__objects.harvesters.get(harv_name)
            assert pre_assigned_harv is not None, f'The harvester with id {pre_assigned_harv_id} pre-assigned to TV with id {tv_id} does not exists'

            self.__fluents_manager.add_fluent_initial_value(fn.tv_pre_assigned_harvester, tv, pre_assigned_harv)

            if pre_assigned_turn is not None:
                self.__fluents_manager.add_fluent_initial_value(fn.tv_pre_assigned_turn, tv, pre_assigned_turn)

    def __init_silo_fluents_and_stats(self):

        """ Set the fluent initial values corresponding to silos and initialize/update the respective problem statistics """

        # @todo: at the moment, all capacities are set to inf.

        self.__fluents_manager.add_fluent_initial_value(fn.total_yield_mass_in_silos, None, 0.0)

        for silo_id, silo_aro in self.__data_manager.silos.items():
            name = get_silo_location_name(silo_id)
            silo = self.__objects.silos.get(name)
            if silo is None:
                raise ValueError(f'Silo with name {name} does not exist')

            self.__fluents_manager.add_fluent_initial_value(fn.silo_id, silo, silo_id)

            self.__problem_stats.silos.silo_ids.update(silo_id)

            # _silo_total_capacity_mass = silo_aro.mass_capacity
            _silo_total_capacity_mass = upt.INF_CAPACITY  # @todo: momentarily set to inf
            self.__fluents_manager.add_fluent_initial_value(fn.silo_available_capacity_mass, silo, _silo_total_capacity_mass)
            self.__problem_stats.silos.silo_mass_capacity.update( _silo_total_capacity_mass )

            for ind, ap in enumerate(silo_aro.access_points):
                name = get_silo_access_location_name(silo_id, ind)
                silo_access = self.__objects.silo_accesses.get(name)
                if silo_access is None:
                    raise ValueError(f'Silo access with name {name} does not exist')

                self.__fluents_manager.add_fluent_initial_value(fn.silo_access_silo_id, silo_access, silo_id)

                self.__fluents_manager.add_fluent_initial_value(fn.silo_access_index, silo_access, ind)

                #_silo_access_total_capacity_mass = ap.mass_capacity
                _silo_access_total_capacity_mass = upt.INF_CAPACITY  # @todo: momentarily set to inf
                self.__fluents_manager.add_fluent_initial_value(fn.silo_access_total_capacity_mass, silo_access, _silo_access_total_capacity_mass)
                self.__problem_stats.silos.silo_access_mass_capacity.update( _silo_access_total_capacity_mass )

                self.__fluents_manager.add_fluent_initial_value(fn.silo_access_available_capacity_mass, silo_access, _silo_access_total_capacity_mass)

                self.__fluents_manager.add_fluent_initial_value(fn.silo_access_cleared, silo_access, True)

                self.__fluents_manager.add_fluent_initial_value(fn.silo_access_sweep_duration, silo_access, ap.sweep_duration)
                self.__problem_stats.silos.silo_access_sweep_duration.update( ap.sweep_duration )

            self.__problem_stats.silos.silo_access_points_count.update( len(silo_aro.access_points) )

    def __init_compactor_fluents_and_stats(self):

        """ Set the fluent initial values corresponding to compactors and initialize/update the respective problem statistics """

        for compactor_id, compactor_aro in self.__data_manager.compactors.items():
            name = get_compactor_name(compactor_id)
            compactor = self.__objects.compactors.get(name)
            if compactor is None:
                raise ValueError(f'Compactor with name {name} does not exist')

            self.__fluents_manager.add_fluent_initial_value(fn.compactor_silo_id, compactor, compactor_aro.silo_id)

            self.__fluents_manager.add_fluent_initial_value(fn.compactor_mass_per_sweep, compactor, compactor_aro.mass_per_sweep)
            self.__problem_stats.silos.compactor_mass_per_sweep.update( compactor_aro.mass_per_sweep )

            self.__fluents_manager.add_fluent_initial_value(fn.compactor_free, compactor, True)

    def __init_problem_fluents(self):

        """ Set the initial values to the problem fluents """

        for f, v in self.__fluent_initial_values:
            self.__problem.set_initial_value(f, v)
        self.__fluent_initial_values.clear()

