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

import up_interface.types as upt
from util_arolib.types import *
from route_planning.types import MachineState, FieldState
from route_planning.outfield_route_planning import OutFieldRoutePlanner
from up_interface.problem_encoder.names_helper import *
from up_interface.fluents import FluentNames as fn
from up_interface.actions.sequential.drive_harv_to_field_and_init import ActionDriveHarvToFieldAndInit
from up_interface.actions.sequential.drive_tv_to_field_and_overload import ActionDriveTvToFieldAndOverload
from up_interface.actions.sequential.drive_to_silo import ActionDriveToSilo
from up_interface.actions.sequential.drive_harv_to_field_exit import ActionDriveHarvToFieldExit
from up_interface.actions.sequential.drive_tv_to_field_exit import ActionDriveTvToFieldExit
from up_interface.actions.sequential.unload_at_silo import ActionUnloadAtSilo

from unified_planning.shortcuts import *
from unified_planning.plans.sequential_plan import SequentialPlan
from unified_planning.plans.plan import ActionInstance

from util_arolib.types import Point, Linestring
from management.global_data_manager import GlobalDataManager
from post_processing.plan_decoder_base import PlanDecoderBase


class SequentialPlanDecoder(PlanDecoderBase):

    """ Decoder of UP sequential plans for the agriculture use-case """

    class PlanMachineState(PlanDecoderBase.PlanMachineState):

        """ Class holding information about the state of a machine """

        def __init__(self):
            PlanDecoderBase.PlanMachineState.__init__(self)

            self.ts_end = 0.0
            self.bunker_mass_end = 0.0
            self.transit_time_end = 0.0
            self.waiting_time_end = 0.0
            self.activity = PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE

    class PlanFieldState(PlanDecoderBase.PlanFieldState):

        """ Class holding information about the state of a field """

        def __init__(self):
            PlanDecoderBase.PlanFieldState.__init__(self)

            self.ts_end = 0.0
            self.harvested_percentage_end = 0.0
            self.harvested_yield_mass_end = 0.0

    class PlanSiloState(PlanDecoderBase.PlanSiloState):

        """ Class holding information about the state of a silo """

        def __init__(self):
            PlanDecoderBase.PlanSiloState.__init__(self)

            self.ts_end = 0.0
            self.yield_mass_end = 0.0

    class FieldOverloadInfo(PlanDecoderBase.FieldOverloadInfo):

        """ Class holding information about the state of an overload activity """

        def __init__(self):
            PlanDecoderBase.FieldOverloadInfo.__init__(self)

            self.ts_end = 0.0

    class TVOverloadInfo(PlanDecoderBase.TVOverloadInfo):

        """ Class holding information about the overload activities of a transport vehicle """

        def __init__(self):
            PlanDecoderBase.TVOverloadInfo.__init__(self)

            self.ts_end = 0.0

    def __init__(self,
                 data_manager: GlobalDataManager,
                 roads: List[Linestring],
                 machine_initial_states: Dict[int, MachineState],
                 field_initial_states: Dict[int, FieldState],
                 out_field_route_planner: OutFieldRoutePlanner,
                 problem: Problem,
                 plan: SequentialPlan):

        """ Decoder initialization

        Parameters
        ----------
        data_manager : GlobalDataManager
            Data manager
        roads : List[Linestring]
            Roads
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        field_initial_states : Dict[int, FieldState]
            Field initial states: {field_id: field_state}
        out_field_route_planner : OutFieldRoutePlanner
            Route/path planner for transit outside the fields
        problem : Problem
            UP problem
        plan : SequentialPlan
            Sequential plan
        """

        PlanDecoderBase.__init__(self,
                                 data_manager=data_manager,
                                 roads=roads,
                                 machine_initial_states=machine_initial_states,
                                 field_initial_states=field_initial_states,
                                 out_field_route_planner=out_field_route_planner,
                                 problem=problem
                                 )
        try:
            self.__init_states(problem, data_manager, machine_initial_states, field_initial_states)
            self.__parse_plan(problem, plan)
            self._ok = True
        except Exception as e:
            self._ok = False
            raise e

    def gives_precise_machine_positions(self) -> bool:
        """ Check if the get_machine_state_at returns precise machine positions

        Returns
        ----------
        ok : bool
            True if the get_machine_state_at returns precise machine positions
        """
        return False

    def __init_states(self,
                      problem: Problem,
                      data_manager: GlobalDataManager,
                      machine_initial_states: Dict[int, MachineState],
                      field_initial_states: Dict[int, FieldState]):

        """ Initialize plan decoded states

        Parameters
        ----------
        data_manager : GlobalDataManager
            Data manager
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        field_initial_states : Dict[int, FieldState]
            Field initial states: {field_id: field_state}
        problem : Problem
            UP problem
        """

        initial_plan_state = SequentialSimulator(problem).get_initial_state()

        field_objects = problem.objects(upt.Field)
        for field_object in field_objects:
            field_name = f'{field_object}'
            field_id = get_field_id_from_location_name(field_name)
            if field_id is None:
                continue
            field_obj = ObjectExp(problem.object(field_name))

            field_states = list()
            self._field_states[field_name] = field_states
            field_state = SequentialPlanDecoder.PlanFieldState()

            init_state: FieldState = field_initial_states.get(field_id)

            mass_per_area = FieldState.DEFAULT_AVG_MASS_PER_AREA_T_HA
            if init_state is not None:
                field_state.harvested_percentage_start = field_state.harvested_percentage_end \
                                                       = max(0.0, min(100.0, init_state.harvested_percentage))
                mass_per_area = init_state.avg_mass_per_area_t_ha

            fluent = FluentExp(problem.fluent(fn.field_yield_mass_total.value), field_obj)
            _field_yield_mass = float(initial_plan_state.get_value(fluent).constant_value())
            _field_yield_mass_total = 100 * _field_yield_mass / (100.0-field_state.harvested_percentage_start)
            field_state.harvested_yield_mass_start = field_state.harvested_yield_mass_end \
                                                   = _field_yield_mass_total - _field_yield_mass

            self._add_state(field_states, field_state)
            self._fields_mass_per_area[field_name] = mass_per_area
            self._fields_yield_mass[field_name] = _field_yield_mass_total

        machines = dict()
        harv_objects = problem.objects(upt.Harvester)
        for harv_object in harv_objects:
            if get_harvester_id_from_name(f'{harv_object}') is None:
                continue
            machines[harv_object] = MachineType.HARVESTER

        tv_objects = problem.objects(upt.TransportVehicle)
        for tv_object in tv_objects:
            machines[tv_object] = MachineType.OLV

        for machine_object, machine_type in machines.items():
            machine_name = f'{machine_object}'
            machine_obj = ObjectExp(problem.object(machine_name))

            loc_name, pt = self.__get_machine_location(problem, initial_plan_state, machine_type, machine_obj)
            if loc_name is None:
                raise ValueError(f'Invalid initial location for machine {machine_name}')

            machine_states = list()
            self._machine_states[machine_name] = machine_states
            machine_state = SequentialPlanDecoder.PlanMachineState()
            self._add_state(machine_states, machine_state)

            machine_state.loc_start = machine_state.loc_end = loc_name
            machine_state.pt_start = machine_state.pt_end = pt

            if machine_type is MachineType.OLV:
                fluent = FluentExp(problem.fluent(fn.tv_bunker_mass.value), machine_obj)
                machine_state.bunker_mass_start = machine_state.bunker_mass_end \
                                                = float(initial_plan_state.get_value(fluent).constant_value())

        silo_objects = problem.objects(upt.Silo)
        for silo_object in silo_objects:
            silo_name = f'{silo_object}'
            silo_states = list()
            self._silo_states[silo_name] = silo_states
            silo_state = SequentialPlanDecoder.PlanSiloState()
            self._add_state(silo_states, silo_state)

            self._silo_unloads[silo_name] = list()

    def __parse_plan(self, problem: Problem, plan: SequentialPlan):

        """ Parse/decode the plan

        Parameters
        ----------
        problem : Problem
            UP problem
        plan : SequentialPlan
            Sequential plan
        """

        drive_harv_to_field_and_init_action_names = {member.value for member in ActionDriveHarvToFieldAndInit.ActionNames}
        drive_tv_to_field_and_overload_action_names = {member.value for member in ActionDriveTvToFieldAndOverload.ActionNames}
        drive_to_silo_action_names = {member.value for member in ActionDriveToSilo.ActionNames}
        drive_harv_to_field_exit_action_names = {member.value for member in ActionDriveHarvToFieldExit.ActionNames}
        drive_tv_to_field_exit_action_names = {member.value for member in ActionDriveTvToFieldExit.ActionNames}
        unload_at_silo_action_names = {member.value for member in ActionUnloadAtSilo.ActionNames}

        with SequentialSimulator(problem) as simulator:
            state_prev: Optional[State] = None
            prev_action = None
            state = simulator.get_initial_state()
            for action in plan.actions:
                state_new = simulator.apply(state, action)

                if state_new is None:
                    state_new = simulator.apply(state, action)
                    print(f'ERROR: Simulator returned state=None for action {action}')
                    if prev_action is not None:
                        print(f'Previous action: {prev_action}')
                    if state_prev is not None:
                        print(f'Previous state:')
                        print(f'{state_prev}')
                        print('')

                    raise ValueError(f'Simulator returned state=None for action {action}')

                # #debug!
                # else:
                #     print(f'Simulator returned state!=None for action {action}')

                prev_action = action
                state_prev = state
                state = state_new

                if action.action.name in drive_harv_to_field_and_init_action_names:
                    self.__parse_action_drive_harv_to_field_and_init(problem, action, state)
                elif action.action.name in drive_tv_to_field_and_overload_action_names:
                    self.__parse_action_drive_tv_to_field_and_overload(problem, action, state)
                elif action.action.name in drive_harv_to_field_exit_action_names \
                        or action.action.name in drive_tv_to_field_exit_action_names:
                    self.__parse_action_drive_machine_to_field_exit(problem, action, state)
                elif action.action.name in drive_to_silo_action_names:
                    self.__parse_action_drive_tv_to_silo(problem, action, state)
                elif action.action.name in unload_at_silo_action_names:
                    self.__parse_action_drive_tv_to_silo(problem, action, state)
                else:
                    raise ValueError(f'Unexpected action {action.action.name}')

            self._generate_silo_states_from_unloads()
            self.__print_final_state(problem, action, state)

    def __get_machine_location(self, problem: Problem, state: State,
                               machine_type: MachineType, machine: ObjectExp) \
            -> Tuple[Union[str, None], Union[Point, None]]:

        """ Get the location object name and respective location position for a given machine

        Parameters
        ----------
        problem : Problem
            UP problem
        state : State
            UP state
        machine_type : MachineType
            Machine type
        machine : ObjectExp
            Machine object

        Returns
        ----------
        location_name : str | None
            Location name (None on error)
        location_position : Point | None
            Location position (None on error)
        """

        if machine_type is MachineType.HARVESTER:
            machine_at_field = FluentExp(problem.fluent(fn.harv_at_field.value), machine)
            machine_at_field_access = FluentExp(problem.fluent(fn.harv_at_field_access.value), machine)
            machine_at_init_loc = FluentExp(problem.fluent(fn.harv_at_init_loc.value), machine)
            machine_at_silo_access = None
            init_locations_names_map = self._harvester_init_locations_names_map
        elif machine_type is MachineType.OLV:
            machine_at_field = FluentExp(problem.fluent(fn.tv_at_field.value), machine)
            machine_at_field_access = FluentExp(problem.fluent(fn.tv_at_field_access.value), machine)
            machine_at_init_loc = FluentExp(problem.fluent(fn.tv_at_init_loc.value), machine)
            machine_at_silo_access = FluentExp(problem.fluent(fn.tv_at_silo_access.value), machine)
            init_locations_names_map = self._tv_init_locations_names_map
        else:
            return None, None

        loc_name = f'{state.get_value(machine_at_init_loc)}'
        pt = init_locations_names_map.get(loc_name)
        if pt is None:
            loc_name = f'{state.get_value(machine_at_field_access)}'
            pt = self._field_access_names_map.get(loc_name)
        if pt is None and machine_at_silo_access is not None:
            loc_name = f'{state.get_value(machine_at_silo_access)}'
            pt = self._silo_access_names_map.get(loc_name)
        if pt is None:
            loc_name = f'{state.get_value(machine_at_field)}'
            pt = self._get_point_from_machine_location(loc_name)[0]

        if pt is None:
            return None, None
        return loc_name, pt

    @staticmethod
    def __get_new_machine_state(machine_states: List['SequentialPlanDecoder.PlanMachineState'],
                                timestamp: float,
                                loc_name: Union[str, None] = None,
                                pt: Union[Point, None] = None,
                                bunker_mass: Union[float, None] = None,
                                transit_time: Union[float, None] = None,
                                waiting_time: Union[float, None] = None,
                                action: Union[str, None] = None,
                                activity: Union['SequentialPlanDecoder.MachineActivity', None] = None,
                                overloading_machine: Union[str, None] = None) \
            -> 'SequentialPlanDecoder.PlanMachineState':

        """ Get a new machine decoded state based on the previous decoded state and the new state values

        Parameters
        ----------
        machine_states : List['SequentialPlanDecoder.PlanMachineState']
            List of machine states to be taken as reference
        timestamp : float
            Machine timestamp [s]
        loc_name : str | None
            New location name (if None, it takes the one from the last decoded state in the input list machine_states)
        pt : Point | None
            New position (if None, it takes the one from the last decoded state in the input list machine_states)
        bunker_mass : float | None
            New bunker mass (if None, it takes the one from the last decoded state in the input list machine_states)
        transit_time : float | None
            New transit time (if None, it takes the one from the last decoded state in the input list machine_states)
        waiting_time : float | None
            New waiting time (if None, it takes the one from the last decoded state in the input list machine_states)
        action : str | None
            Name of the action causing the state (if None, it takes the one from the last decoded state in the input list machine_states)
        activity : MachineActivity | None
            New machine activity (if None, it takes the one from the last decoded state in the input list machine_states)
        loc_name : str | None
            New machine-id participating in the overload (if None, it takes the one from the last decoded state in the input list machine_states)

        Returns
        ----------
        new_machine_state : PlanMachineState
            New machine decoded state
        """

        last_state = machine_states[-1]
        machine_state = SequentialPlanDecoder.PlanMachineState()
        machine_state.ts_start = last_state.ts_end
        machine_state.ts_end = timestamp
        machine_state.loc_start = last_state.loc_end
        machine_state.loc_end = loc_name if loc_name is not None else last_state.loc_end
        machine_state.pt_start = last_state.pt_end
        machine_state.pt_end = pt if pt is not None else last_state.pt_end
        machine_state.bunker_mass_start = last_state.bunker_mass_end
        machine_state.bunker_mass_end = bunker_mass if bunker_mass is not None else last_state.bunker_mass_end
        machine_state.transit_time_start = last_state.transit_time_end
        machine_state.transit_time_end = transit_time if transit_time is not None else last_state.transit_time_end
        machine_state.waiting_time_start = last_state.waiting_time_end
        machine_state.waiting_time_end = waiting_time if waiting_time is not None else last_state.waiting_time_end
        machine_state.action = action
        machine_state.activity = activity if activity is not None else last_state.activity
        machine_state.overloading_machine_name = overloading_machine
        return machine_state

    def __parse_action_drive_harv_to_field_and_init(self, problem: Problem, action: ActionInstance, plan_state: State):

        """ Parse/decode a 'actions.sequential.ActionDriveHarvToFieldAndInit' action and add the resulting decoded state(s)

        Parameters
        ----------
        problem : Problem
            UP problem
        action : ActionInstance
            UP action instance
        plan_state : State
            UP state resulting from the action
        """

        loc_from = None
        field_access = None
        machine_name = field_name = pt_to = None
        for i, param in enumerate(action.action.parameters):
            if param.name == 'harv':
                machine_name = f'{action.actual_parameters[i]}'
            elif param.name == 'loc_from':
                loc_from = f'{action.actual_parameters[i]}'
            elif param.name == 'field':
                field_name = f'{action.actual_parameters[i]}'
            elif param.name == 'field_access':
                field_access = f'{action.actual_parameters[i]}'

        machine_states = self._machine_states.get(machine_name)
        if machine_states is None:
            raise ValueError(f'Invalid harv = {machine_name}')

        if loc_from is not None:
            pt_from = self._harvester_init_locations_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._field_access_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._silo_access_names_map.get(loc_from)
            if pt_from is None:
                raise ValueError(f'Invalid loc_from = {loc_from}')
        if field_access is not None:
            pt_to = self._field_access_names_map.get(field_access)
            if pt_to is None:
                raise ValueError(f'Invalid loc_from = {field_access}')
            field = self._field_names_map.get(field_name)
            if field is None:
                raise ValueError(f'Invalid field = {field_name}')

        machine_obj = ObjectExp(problem.object(machine_name))

        harv_timestamp = FluentExp(problem.fluent(fn.harv_timestamp.value), machine_obj)
        _harv_timestamp = float(plan_state.get_value(harv_timestamp).constant_value())

        harv_transit_time = FluentExp(problem.fluent(fn.harv_transit_time.value), machine_obj)
        _harv_transit_time = float(plan_state.get_value(harv_transit_time).constant_value())

        loc_name, pt = self.__get_machine_location(problem, plan_state, MachineType.HARVESTER, machine_obj)
        if loc_name is None:
            raise ValueError(f'Unable to obtain the location for machine {machine_name}')

        prev_harv_state = machine_states[-1]
        _transit_duration = max(0.0, _harv_transit_time - prev_harv_state.transit_time_end)

        timestamp_start_transit = _harv_timestamp - _transit_duration

        if timestamp_start_transit > prev_harv_state.ts_end:
            self._add_state(machine_states,
                            self.__get_new_machine_state(machine_states,
                                                         timestamp=timestamp_start_transit,
                                                         activity=PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE))

        if _transit_duration > 1e-9:
            if loc_from is None or field_access is None:
                raise ValueError(f'Transit duration > 0 for an action without transit')

            self._add_state(machine_states,
                            self.__get_new_machine_state(machine_states,
                                                         timestamp=timestamp_start_transit + _transit_duration,
                                                         loc_name=field_access,
                                                         pt=pt_to,
                                                         transit_time=_harv_transit_time,
                                                         action=action.action.name,
                                                         activity=PlanDecoderBase.MachineActivity.TRANSIT_OFF_FIELD))

        self._add_state(machine_states,
                        self.__get_new_machine_state(machine_states,
                                                     timestamp=_harv_timestamp,
                                                     loc_name=loc_name,
                                                     pt=pt,
                                                     action=action.action.name,
                                                     activity=PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD))

        field_states = self._field_states.get(field_name)

        field_state = self.__init_field_state_from_last(field_name)
        field_state.ts_start = _harv_timestamp - _transit_duration
        field_state.ts_end = _harv_timestamp
        field_state.state = SequentialPlanDecoder.FieldHarvestingState.RESERVED
        field_state.harvester = machine_name
        field_state.tv = None
        self._add_state(field_states, field_state)

        field_state = self.__init_field_state_from_last(field_name)
        field_state.ts_start = _harv_timestamp
        field_state.ts_end = None
        field_state.state = SequentialPlanDecoder.FieldHarvestingState.BEING_HARVESTED_WAITING
        self._add_state(field_states, field_state)

        overloads = self._field_overloads.get(field_name)
        if overloads is None:
            overloads = SequentialPlanDecoder.FieldOverloads()
            self._field_overloads[field_name] = overloads
        overloads.harv = machine_name
        overloads.entry_point = field_access

    def __parse_action_drive_tv_to_field_and_overload(self, problem: Problem, action: ActionInstance, plan_state: State):

        """ Parse/decode a 'actions.sequential.ActionDriveTvToFieldAndOverload' action and add the resulting decoded state(s)

        Parameters
        ----------
        problem : Problem
            UP problem
        action : ActionInstance
            UP action instance
        plan_state : State
            UP state resulting from the action
        """

        only_overload = action.action.name.startswith('drive_tv_from')
        harv_waits = (action.action.name.find('_harv_waits') >= 0)
        field_finished = (action.action.name.find('_field_finished') >= 0)

        loc_from = None
        field_access = None
        field_exit_harv = None
        tv_name = harv_name = field_name = pt_to = None

        for i, param in enumerate(action.action.parameters):
            if param.name == 'field':
                field_name = f'{action.actual_parameters[i]}'
            elif param.name == 'tv':
                tv_name = f'{action.actual_parameters[i]}'
            elif param.name == 'harv':
                harv_name = f'{action.actual_parameters[i]}'
            elif param.name == 'field_exit_tv':
                field_exit_tv = f'{action.actual_parameters[i]}'
            elif param.name == 'loc_from':
                loc_from = f'{action.actual_parameters[i]}'
            elif param.name == 'field_access':
                field_access = f'{action.actual_parameters[i]}'
            elif param.name == 'field_exit_harv':
                field_exit_harv = f'{action.actual_parameters[i]}'

        tv_states = self._machine_states.get(tv_name)
        if tv_states is None:
            raise ValueError(f'Invalid tv = {tv_name}')
        harv_states = self._machine_states.get(harv_name)
        if harv_states is None:
            raise ValueError(f'Invalid harv = {harv_name}')
        if loc_from is not None:
            pt_from = self._tv_init_locations_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._field_access_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._silo_access_names_map.get(loc_from)
            if pt_from is None:
                raise ValueError(f'Invalid loc_from = {loc_from}')
            if field_access is not None:
                pt_to = self._field_access_names_map.get(field_access)
                if pt_to is None:
                    raise ValueError(f'Invalid field_access = {field_access}')
        field = self._field_names_map.get(field_name)
        if field is None:
            raise ValueError(f'Invalid field = {field_name}')

        harv_obj = ObjectExp(problem.object(harv_name))
        tv_obj = ObjectExp(problem.object(tv_name))

        default_infield_transit_duration_to_access_point = FluentExp(problem.fluent(fn.default_infield_transit_duration_to_access_point.value))
        _infield_transit_duration = float(plan_state.get_value(default_infield_transit_duration_to_access_point).constant_value())

        harv_timestamp = FluentExp(problem.fluent(fn.harv_timestamp.value), harv_obj)
        _harv_timestamp = float(plan_state.get_value(harv_timestamp).constant_value())

        harv_waiting_time = FluentExp(problem.fluent(fn.harv_waiting_time.value), harv_obj)
        _harv_waiting_time = float(plan_state.get_value(harv_waiting_time).constant_value())

        tv_timestamp = FluentExp(problem.fluent(fn.tv_timestamp.value), tv_obj)
        _tv_timestamp = float(plan_state.get_value(tv_timestamp).constant_value())

        tv_transit_time = FluentExp(problem.fluent(fn.tv_transit_time.value), tv_obj)
        _tv_transit_time = float(plan_state.get_value(tv_transit_time).constant_value())

        tv_waiting_time = FluentExp(problem.fluent(fn.tv_waiting_time.value), tv_obj)
        _tv_waiting_time = float(plan_state.get_value(tv_waiting_time).constant_value())

        tv_bunker_mass = FluentExp(problem.fluent(fn.tv_bunker_mass.value), tv_obj)
        _tv_bunker_mass = float(plan_state.get_value(tv_bunker_mass).constant_value())

        prev_harv_state = harv_states[-1]
        prev_tv_state = tv_states[-1]
        delta_timestamp_harv = max(0.0, _harv_timestamp - prev_harv_state.ts_end)
        delta_timestamp_tv = max(0.0, _tv_timestamp - prev_tv_state.ts_end)
        transit_duration = max(0.0, _tv_transit_time - prev_tv_state.transit_time_end)
        waiting_duration_harv = max(0.0, _harv_waiting_time - prev_harv_state.waiting_time_end)
        waiting_duration_tv = max(0.0, _tv_waiting_time - prev_tv_state.waiting_time_end)
        mass_to_overload = _tv_bunker_mass - prev_tv_state.bunker_mass_end

        if transit_duration > 1e-9 and (loc_from is None or field_access is None):
            raise ValueError(f'Transit duration > 0 for an action without transit')

        infield_transit_duration = max(0.0, _infield_transit_duration)
        if harv_waits:
            overload_duration = max(0.0, delta_timestamp_tv - transit_duration - 2*infield_transit_duration)
            infield_transit_duration = 0.5 * (delta_timestamp_tv - transit_duration - overload_duration)
        else:
            if field_finished:
                overload_duration = max(0.0, delta_timestamp_harv - infield_transit_duration)
                infield_transit_duration = max(0.0, delta_timestamp_harv - overload_duration)
            else:
                overload_duration = delta_timestamp_harv
                infield_transit_duration = min( infield_transit_duration,
                                                max(0.0, 0.5*(delta_timestamp_tv - transit_duration - overload_duration)) )

        _timestamp_overload_end = _tv_timestamp - infield_transit_duration
        _timestamp_overload_start = _timestamp_overload_end - overload_duration

        _timestamp_tv_start_transit = _timestamp_tv_arrives_to_field = _timestamp_tv_arrives_to_overload = None

        if transit_duration > 1e-9:
            _timestamp_tv_start_transit = prev_tv_state.ts_end
            _timestamp_tv_arrives_to_field = _timestamp_tv_start_transit + transit_duration
            _timestamp_tv_arrives_to_overload = _timestamp_tv_arrives_to_field + infield_transit_duration

        field_pt = prev_harv_state.pt_end

        # HARVESTER

        loc_name, pt = self.__get_machine_location(problem, plan_state, MachineType.HARVESTER, harv_obj)
        if loc_name is None:
            raise ValueError(f'Unable to obtain the location for machine {harv_name}')

        if _timestamp_overload_start > prev_harv_state.ts_end:
            self._add_state(harv_states,
                            self.__get_new_machine_state(harv_states,
                                                         timestamp=_timestamp_overload_start,
                                                         waiting_time=_harv_waiting_time,
                                                         # action=None,
                                                         action=action.action.name,
                                                         activity=PlanDecoderBase.MachineActivity.WAITING_TO_OVERLOAD))

        if field_finished:
            self._add_state(harv_states,
                            self.__get_new_machine_state(harv_states,
                                                         timestamp=_harv_timestamp - infield_transit_duration,
                                                         loc_name=field_name,
                                                         pt=field_pt,
                                                         action=action.action.name,
                                                         activity=PlanDecoderBase.MachineActivity.OVERLOADING,
                                                         overloading_machine=tv_name))
        self._add_state(harv_states,
                        self.__get_new_machine_state(harv_states,
                                                     timestamp=_harv_timestamp,
                                                     loc_name=loc_name,
                                                     pt=pt,
                                                     action=action.action.name,
                                                     activity=PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD if field_finished else PlanDecoderBase.MachineActivity.OVERLOADING,
                                                     overloading_machine=tv_name))

        # TV

        loc_name, pt = self.__get_machine_location(problem, plan_state, MachineType.OLV, tv_obj)
        if loc_name is None:
            raise ValueError(f'Unable to obtain the location for machine {tv_name}')

        if _timestamp_tv_start_transit is not None:
            if _timestamp_tv_start_transit > prev_tv_state.ts_end:
                self._add_state(tv_states,
                                self.__get_new_machine_state(tv_states,
                                                             timestamp=_timestamp_tv_start_transit,
                                                             action=None,
                                                             activity=PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE))
            self._add_state(tv_states,
                            self.__get_new_machine_state(tv_states,
                                                         timestamp=_timestamp_tv_arrives_to_field,
                                                         loc_name=field_access,
                                                         pt=pt_to,
                                                         transit_time=_tv_transit_time,
                                                         action=action.action.name,
                                                         activity=PlanDecoderBase.MachineActivity.TRANSIT_OFF_FIELD))
            self._add_state(tv_states,
                            self.__get_new_machine_state(tv_states,
                                                         timestamp=_timestamp_tv_arrives_to_overload,
                                                         loc_name=field_name,
                                                         pt=field_pt,
                                                         action=action.action.name,
                                                         activity=PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD))
            if _timestamp_tv_arrives_to_overload < _timestamp_overload_start:
                self._add_state(tv_states,
                                self.__get_new_machine_state(tv_states,
                                                             timestamp=_timestamp_overload_start,
                                                             waiting_time=_tv_waiting_time,
                                                             action=action.action.name,
                                                             activity=PlanDecoderBase.MachineActivity.WAITING_TO_OVERLOAD))
        else:
            if _timestamp_overload_start > prev_tv_state.ts_end:
                self._add_state(tv_states,
                                self.__get_new_machine_state(tv_states,
                                                             timestamp=_timestamp_overload_start,
                                                             waiting_time=_tv_waiting_time,
                                                             action=action.action.name,
                                                             activity=PlanDecoderBase.MachineActivity.WAITING_TO_OVERLOAD))

        self._add_state(tv_states,
                        self.__get_new_machine_state(tv_states,
                                                     timestamp=_timestamp_overload_end,
                                                     bunker_mass=_tv_bunker_mass,
                                                     action=action.action.name,
                                                     activity=PlanDecoderBase.MachineActivity.OVERLOADING,
                                                     overloading_machine=harv_name))

        self._add_state(tv_states,
                        self.__get_new_machine_state(tv_states,
                                                     timestamp=_tv_timestamp,
                                                     loc_name=loc_name,
                                                     pt=pt,
                                                     action=action.action.name,
                                                     activity=PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD))

        tv_overloads = self._tv_overloads.get(tv_name)
        if tv_overloads is None:
            tv_overloads = list()
            self._tv_overloads[tv_name] = tv_overloads
        overload_info = SequentialPlanDecoder.TVOverloadInfo()
        overload_info.ts_start = _timestamp_overload_start
        overload_info.ts_end = _timestamp_overload_end
        overload_info.harv = harv_name
        overload_info.field = field_name
        self._add_state(tv_overloads, overload_info, remove_future_states=False)
        self._add_state(self.tv_overloads_all, overload_info, remove_future_states=False)

        # FIELD

        field_states = self._field_states.get(field_name)

        field_state = self.__init_field_state_from_last(field_name)
        field_state.ts_start = _timestamp_overload_start
        field_state.ts_end = _timestamp_overload_end
        field_state.state = SequentialPlanDecoder.FieldHarvestingState.BEING_HARVESTED
        field_state.harvester = harv_name
        field_state.tv = tv_name
        field_state.harvested_yield_mass_end = field_state.harvested_yield_mass_start + mass_to_overload
        field_state.harvested_percentage_end = (100 * field_state.harvested_yield_mass_end
                                                / self._fields_yield_mass[field_name])
        self._add_state(field_states, field_state)

        field_state = self.__init_field_state_from_last(field_name)
        field_state.ts_start = _timestamp_overload_end
        field_state.state = SequentialPlanDecoder.FieldHarvestingState.HARVESTED if field_finished else SequentialPlanDecoder.FieldHarvestingState.BEING_HARVESTED_WAITING
        field_state.tv = None
        self._add_state(field_states, field_state)

        field_overloads = self._field_overloads.get(field_name)
        if field_overloads is None:
            field_overloads = SequentialPlanDecoder.FieldOverloads()
            self._field_overloads[field_name] = field_overloads
        if field_overloads.harv is not None and field_overloads.harv != harv_name:
            raise ValueError('Missmatch in assigned harvester to field')
        field_overloads.harv = harv_name
        overload_info = SequentialPlanDecoder.FieldOverloadInfo()
        overload_info.ts_start = _timestamp_overload_start
        overload_info.ts_end = _timestamp_overload_end
        overload_info.tv = tv_name
        self._add_state(field_overloads.overloads, overload_info, remove_future_states=False)

    def __parse_action_drive_machine_to_field_exit(self, problem: Problem, action: ActionInstance, plan_state: State):

        """ Parse/decode a 'actions.sequential.ActionDriveHarvToFieldExit' or 'actions.sequential.ActionDriveTvToFieldExit' action and add the resulting decoded state(s)

        Parameters
        ----------
        problem : Problem
            UP problem
        action : ActionInstance
            UP action instance
        plan_state : State
            UP state resulting from the action
        """

        machine_name = machine_type = None

        for i, param in enumerate(action.action.parameters):
            if param.name == 'field':
                field_name = f'{action.actual_parameters[i]}'
            elif param.name == 'field_access':
                field_access = f'{action.actual_parameters[i]}'
            elif param.name == 'harv':
                machine_name = f'{action.actual_parameters[i]}'
                machine_type = MachineType.HARVESTER
            elif param.name == 'tv':
                machine_name = f'{action.actual_parameters[i]}'
                machine_type = MachineType.OLV

        machine_states = self._machine_states.get(machine_name)
        if machine_states is None:
            raise ValueError(f'Invalid harv = {machine_states}')

        machine_obj = ObjectExp(problem.object(machine_name))

        machine_timestamp = FluentExp( problem.fluent(fn.harv_timestamp.value) if machine_type is MachineType.HARVESTER else problem.fluent(fn.tv_timestamp.value),
                                       machine_obj )
        _machine_timestamp = float(plan_state.get_value(machine_timestamp).constant_value())

        prev_machine_state = machine_states[-1]
        delta_timestamp = max(0.0, _machine_timestamp - prev_machine_state.ts_end)
        infield_transit_duration = min(delta_timestamp, 30)

        _timestamp_start = _machine_timestamp - infield_transit_duration

        loc_name, pt = self.__get_machine_location(problem, plan_state, machine_type, machine_obj)
        if loc_name is None:
            raise ValueError(f'Unable to obtain the location for machine {machine_name}')

        if _timestamp_start > prev_machine_state.ts_end:
            self._add_state(machine_states,
                            self.__get_new_machine_state(machine_states,
                                                         timestamp=_timestamp_start,
                                                         action=None,
                                                         activity=PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE))

        self._add_state(machine_states,
                        self.__get_new_machine_state(machine_states,
                                                     timestamp=_machine_timestamp,
                                                     loc_name=loc_name,
                                                     pt=pt,
                                                     action=action.action.name,
                                                     activity=PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD))

    def __parse_action_drive_tv_to_silo(self, problem: Problem, action: ActionInstance, plan_state: State):

        """ Parse/decode a 'actions.sequential.ActionDriveToSilo' action and add the resulting decoded state(s)

        Parameters
        ----------
        problem : Problem
            UP problem
        action : ActionInstance
            UP action instance
        plan_state : State
            UP state resulting from the action
        """

        loc_from = None
        tv_name = silo_name = silo_access = None

        for i, param in enumerate(action.action.parameters):
            if param.name == 'tv':
                tv_name = f'{action.actual_parameters[i]}'
            elif param.name == 'loc_from':
                loc_from = f'{action.actual_parameters[i]}'
            elif param.name == 'silo':
                silo_name = f'{action.actual_parameters[i]}'
            elif param.name == 'silo_access':
                silo_access = f'{action.actual_parameters[i]}'

        tv_states = self._machine_states.get(tv_name)
        if tv_states is None:
            raise ValueError(f'Invalid tv = {tv_name}')

        silo_unloads = self._silo_unloads.get(silo_name)
        if silo_unloads is None:
            raise ValueError(f'Invalid silo = {silo_name}')

        if loc_from is not None:
            pt_from = self._tv_init_locations_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._field_access_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._silo_access_names_map.get(loc_from)
            if pt_from is None:
                raise ValueError(f'Invalid loc_from = {loc_from}')
        pt_to = self._silo_access_names_map.get(silo_access)
        if pt_to is None:
            raise ValueError(f'Invalid silo_access = {silo_access}')
        silo = self._silo_names_map.get(silo_name)
        if silo is None:
            raise ValueError(f'Invalid silo = {silo_name}')

        with_unload = (action.action.name.find('_unload') >= 0)
        tv_waits = (action.action.name.find('_tv_waits') >= 0)

        tv_obj = ObjectExp(problem.object(tv_name))

        tv_timestamp = FluentExp(problem.fluent(fn.tv_timestamp.value), tv_obj)
        _tv_timestamp = float(plan_state.get_value(tv_timestamp).constant_value())

        tv_transit_time = FluentExp(problem.fluent(fn.tv_transit_time.value), tv_obj)
        _tv_transit_time = float(plan_state.get_value(tv_transit_time).constant_value())

        tv_waiting_time = FluentExp(problem.fluent(fn.tv_waiting_time.value), tv_obj)
        _tv_waiting_time = float(plan_state.get_value(tv_waiting_time).constant_value())

        tv_bunker_mass = FluentExp(problem.fluent(fn.tv_bunker_mass.value), tv_obj)
        _tv_bunker_mass = float(plan_state.get_value(tv_bunker_mass).constant_value())

        prev_tv_state = tv_states[-1]
        delta_timestamp_tv = max(0.0, _tv_timestamp - prev_tv_state.ts_end)
        waiting_duration = max(0.0, _tv_waiting_time - prev_tv_state.waiting_time_end)
        transit_duration = max(0.0, _tv_transit_time - prev_tv_state.transit_time_end)
        mass_to_unload = prev_tv_state.bunker_mass_end - _tv_bunker_mass
        unload_duration = 0

        if with_unload:
            machine_id = get_tv_id_from_name(tv_name)
            machine = self._data_manager.machines.get(machine_id)
            if machine is not None:
                unload_duration = max(0.0, mass_to_unload / machine.unloading_speed_mass)
            else:
                unload_duration = 1.0
            unload_duration = min(unload_duration, delta_timestamp_tv - transit_duration - waiting_duration)

        timestamp_start_transit = _tv_timestamp - transit_duration - unload_duration - waiting_duration
        timestamp_start_unload = _tv_timestamp - unload_duration

        if timestamp_start_transit > prev_tv_state.ts_end:
            self._add_state(tv_states,
                            self.__get_new_machine_state(tv_states,
                                                         timestamp=timestamp_start_transit,
                                                         action=None,
                                                         activity=PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE))

        if transit_duration > 1e-9:
            if loc_from is None:
                raise ValueError(f'Transit duration > 0 for an action without transit')
            self._add_state(tv_states,
                            self.__get_new_machine_state(tv_states,
                                                         timestamp=timestamp_start_unload - waiting_duration,
                                                         loc_name=silo_access,
                                                         pt=pt_to,
                                                         transit_time=_tv_transit_time,
                                                         action=action.action.name,
                                                         activity=PlanDecoderBase.MachineActivity.TRANSIT_OFF_FIELD))

        loc_name, pt = self.__get_machine_location(problem, plan_state, MachineType.OLV, tv_obj)
        if loc_name is None:
            raise ValueError(f'Unable to obtain the location for machine {tv_name}')

        if waiting_duration > 1e-9:
            self._add_state(tv_states,
                            self.__get_new_machine_state(tv_states,
                                                         timestamp=timestamp_start_unload,
                                                         loc_name=loc_name,
                                                         pt=pt,
                                                         bunker_mass=_tv_bunker_mass,
                                                         waiting_time=_tv_waiting_time,
                                                         action=action.action.name,
                                                         activity=PlanDecoderBase.MachineActivity.WAITING_TO_UNLOAD))
        self._add_state(tv_states,
                        self.__get_new_machine_state(tv_states,
                                                     timestamp=_tv_timestamp,
                                                     loc_name=loc_name,
                                                     pt=pt,
                                                     bunker_mass=_tv_bunker_mass,
                                                     action=action.action.name,
                                                     activity=PlanDecoderBase.MachineActivity.UNLOADING if with_unload else PlanDecoderBase.MachineActivity.WAITING_TO_UNLOAD))

        if with_unload:
            silo_unload = PlanDecoderBase.SiloUnloadInfo()
            silo_unload.ts_start = timestamp_start_unload
            silo_unload.ts_end = _tv_timestamp
            silo_unload.unloaded_mass = mass_to_unload
            silo_unload.silo_access = silo_access
            silo_unload.tv = tv_name
            self._add_state(silo_unloads, silo_unload, remove_future_states=False)

            unload_info = SequentialPlanDecoder.TVUnloadInfo()
            unload_info.ts_start = timestamp_start_unload
            unload_info.ts_end = _tv_timestamp
            unload_info.silo_access = silo_access
            tv_overloads = self._tv_overloads.get(tv_name)
            if tv_overloads is not None and len(tv_overloads) > 0:
                if tv_overloads[-1].ts_start < timestamp_start_unload:
                    unload_info.overload_info = tv_overloads[-1]
                else:
                    unload_info.overload_info, _ = self._get_state_at(tv_overloads, timestamp_start_unload)
                unload_info.overload_info.silo_access = silo_access
            tv_unloads = self._tv_unloads.get(tv_name)
            if tv_unloads is None:
                tv_unloads = list()
                self._tv_unloads[tv_name] = tv_unloads
            self._add_state(tv_unloads, unload_info, remove_future_states=False)

    def __parse_action_unload_at_silo(self, problem: Problem, action: ActionInstance, plan_state: State):

        """ Parse/decode a 'actions.sequential.ActionUnloadAtSilo' action and add the resulting decoded state(s)

        Parameters
        ----------
        problem : Problem
            UP problem
        action : ActionInstance
            UP action instance
        plan_state : State
            UP state resulting from the action
        """

        tv_name = silo_access = None

        for i, param in enumerate(action.action.parameters):
            if param.name == 'tv':
                tv_name = f'{action.actual_parameters[i]}'
            elif param.name == 'silo_access':
                silo_access = f'{action.actual_parameters[i]}'

        tv_states = self._machine_states.get(tv_name)
        if tv_states is None:
            raise ValueError(f'Invalid tv = {tv_name}')

        silo_name = get_silo_name_from_silo_access_location_name(silo_access)

        silo_unloads = self._silo_unloads.get(silo_name)
        if silo_unloads is None:
            raise ValueError(f'Invalid silo = {silo_name} obtained from silo_access = {silo_access}')

        tv_obj = ObjectExp(problem.object(tv_name))

        tv_timestamp = FluentExp(problem.fluent(fn.tv_timestamp.value), tv_obj)
        _tv_timestamp = float(plan_state.get_value(tv_timestamp).constant_value())

        tv_waiting_time = FluentExp(problem.fluent(fn.tv_waiting_time.value), tv_obj)
        _tv_waiting_time = float(plan_state.get_value(tv_waiting_time).constant_value())

        tv_bunker_mass = FluentExp(problem.fluent(fn.tv_bunker_mass.value), tv_obj)
        _tv_bunker_mass = float(plan_state.get_value(tv_bunker_mass).constant_value())

        prev_tv_state = tv_states[-1]
        delta_timestamp_tv = max(0.0, _tv_timestamp - prev_tv_state.ts_end)
        waiting_duration = max(0.0, _tv_waiting_time - prev_tv_state.waiting_time_end)
        mass_to_unload = prev_tv_state.bunker_mass_end - _tv_bunker_mass
        unload_duration = 0

        machine_id = get_tv_id_from_name(tv_name)
        machine = self._data_manager.machines.get(machine_id)
        if machine is not None:
            unload_duration = max(0.0, mass_to_unload / machine.unloading_speed_mass)
        else:
            unload_duration = 1.0
        unload_duration = max(0.0, delta_timestamp_tv - unload_duration - waiting_duration)

        timestamp_start_unload = _tv_timestamp - unload_duration - waiting_duration

        if timestamp_start_unload > prev_tv_state.ts_end or waiting_duration > 1e-9:
            self._add_state(tv_states,
                            self.__get_new_machine_state(tv_states,
                                                         timestamp=timestamp_start_unload,
                                                         waiting_time=_tv_waiting_time,
                                                         action=None,
                                                         activity=PlanDecoderBase.MachineActivity.WAITING_TO_UNLOAD))

        loc_name, pt = self.__get_machine_location(problem, plan_state, MachineType.OLV, tv_obj)
        if loc_name is None:
            raise ValueError(f'Unable to obtain the location for machine {tv_name}')

        self._add_state(tv_states,
                        self.__get_new_machine_state(tv_states,
                                                     timestamp=_tv_timestamp,
                                                     loc_name=loc_name,
                                                     pt=pt,
                                                     bunker_mass=_tv_bunker_mass,
                                                     action=action.action.name,
                                                     activity=PlanDecoderBase.MachineActivity.UNLOADING))

        silo_unload = PlanDecoderBase.SiloUnloadInfo()
        silo_unload.ts_start = timestamp_start_unload
        silo_unload.ts_end = _tv_timestamp
        silo_unload.unloaded_mass = mass_to_unload
        silo_unload.silo_access = silo_access
        silo_unload.tv = tv_name
        self._add_state(silo_unloads, silo_unload, remove_future_states=False)

        unload_info = SequentialPlanDecoder.TVUnloadInfo()
        unload_info.ts_start = timestamp_start_unload
        unload_info.ts_end = _tv_timestamp
        unload_info.silo_access = silo_access
        tv_overloads = self._tv_overloads.get(tv_name)
        if tv_overloads is not None and len(tv_overloads) > 0:
            if tv_overloads[-1].ts_start < timestamp_start_unload:
                unload_info.overload_info = tv_overloads[-1]
            else:
                unload_info.overload_info, _ = self._get_state_at(tv_overloads, timestamp_start_unload)
            unload_info.overload_info.silo_access = silo_access
        tv_unloads = self._tv_unloads.get(tv_name)
        if tv_unloads is None:
            tv_unloads = list()
            self._tv_unloads[tv_name] = tv_unloads
        self._add_state(tv_unloads, unload_info, remove_future_states=False)

    @staticmethod
    def __print_final_state(problem: Problem, action: ActionInstance, plan_state: State):

        """ Print information of the given UP state

        Parameters
        ----------
        problem : Problem
            UP problem
        action : ActionInstance
            UP action instance
        plan_state : State
            UP state
        """

        max_timestamp = 0
        harv_waiting_time_total = 0
        tv_waiting_time_total = 0
        for machine in problem.objects(upt.Harvester):
            timestamp = FluentExp(problem.fluent(fn.harv_timestamp.value), machine)
            _timestamp = float(plan_state.get_value(timestamp).constant_value())
            max_timestamp = max(max_timestamp, _timestamp)

            waiting_time = FluentExp(problem.fluent(fn.harv_waiting_time.value), machine)
            _waiting_time = float(plan_state.get_value(waiting_time).constant_value())
            harv_waiting_time_total += _waiting_time

        for machine in problem.objects(upt.TransportVehicle):
            timestamp = FluentExp(problem.fluent(fn.tv_timestamp.value), machine)
            _timestamp = float(plan_state.get_value(timestamp).constant_value())
            max_timestamp = max(max_timestamp, _timestamp)

            waiting_time = FluentExp(problem.fluent(fn.tv_waiting_time.value), machine)
            _waiting_time = float(plan_state.get_value(waiting_time).constant_value())
            tv_waiting_time_total += _waiting_time

        print('Plan final state:')
        print(f'\tMax timestamp: {max_timestamp} s')
        print(f'\tTotal harvester(s) waiting time: {harv_waiting_time_total} s')
        print(f'\tTotal tv(s) waiting time: {tv_waiting_time_total} s')

    def __init_field_state_from_last(self, field_name: str) -> PlanFieldState:

        """ Partially initialize a decoded state for a given field based on its previous decoded state

        Parameters
        ----------
        field_name : str
            Field object name

        Returns
        ----------
        field_state : PlanFieldState
            Partially initialized decoded state for the given field
        """

        state = SequentialPlanDecoder.PlanFieldState()
        state_prev = self._field_states.get(field_name)[-1]
        state.harvester = state_prev.harvester
        state.tv = state_prev.tv
        state.harvested_percentage_start = state_prev.harvested_percentage_start \
            if state_prev.harvested_percentage_end is None \
            else state_prev.harvested_percentage_end
        state.harvested_percentage_end = state.harvested_percentage_start
        state.harvested_yield_mass_start = state_prev.harvested_yield_mass_start \
            if state_prev.harvested_yield_mass_end is None \
            else state_prev.harvested_yield_mass_end
        state.harvested_yield_mass_end = state.harvested_yield_mass_start
        return state
