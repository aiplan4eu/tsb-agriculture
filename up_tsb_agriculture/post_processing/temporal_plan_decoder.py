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

from typing import Dict, List, Optional

from util_arolib.types import *
from util_arolib.geometry import calc_area
from route_planning.types import MachineState, FieldState
from route_planning.outfield_route_planning import OutFieldRoutePlanner
from up_interface.problem_encoder.names_helper import *

from unified_planning.shortcuts import Problem
from unified_planning.plans.time_triggered_plan import TimeTriggeredPlan
from unified_planning.plans.plan import ActionInstance

from util_arolib.types import Linestring
from management.global_data_manager import GlobalDataManager
from post_processing.plan_decoder_base import PlanDecoderBase

from up_interface.actions.temporal.drive_harv_to_field_and_init import ActionDriveHarvToFieldAndInit
from up_interface.actions.temporal.drive_tv_to_field_and_reserve_overload import ActionDriveTvToFieldAndReserveOverload
from up_interface.actions.temporal.do_overload import ActionDoOverload
from up_interface.actions.temporal.drive_to_silo import ActionDriveToSilo
from up_interface.actions.temporal.drive_harv_to_field_exit import ActionDriveHarvToFieldExit
from up_interface.actions.temporal.drive_tv_to_field_exit import ActionDriveTvToFieldExit
from up_interface.actions.temporal.unload_at_silo import ActionUnloadAtSilo


class TemporalPlanDecoder(PlanDecoderBase):

    """ Decoder of UP temporal plans for the agriculture use-case """

    class PlanMachineState(PlanDecoderBase.PlanMachineState):

        """ Class holding information about the state of a machine """

        def __init__(self):
            PlanDecoderBase.PlanMachineState.__init__(self)
            self.ts_end: Optional[float] = None
            self.bunker_mass_end: float = 0.0

            self.transit_time_start: Optional[float] = None
            self.transit_time_end: Optional[float] = None
            self.waiting_time_end: Optional[float] = None
            self.action = None
            self.activity = None

    class PlanFieldState(PlanDecoderBase.PlanFieldState):

        """ Class holding information about the state of a field """

        def __init__(self):
            PlanDecoderBase.PlanFieldState.__init__(self)

            self.ts_end: Optional[float] = None
            self.harvested_percentage_end: Optional[float] = None
            self.harvested_yield_mass_end: Optional[float] = None

    class PlanSiloState(PlanDecoderBase.PlanSiloState):

        """ Class holding information about the state of a silo """

        def __init__(self):
            PlanDecoderBase.PlanSiloState.__init__(self)

            self.ts_end = None
            self.yield_mass_end = 0.0

    class FieldOverloadInfo(PlanDecoderBase.FieldOverloadInfo):

        """ Class holding information about the state of an overload activity """

        def __init__(self):
            PlanDecoderBase.FieldOverloadInfo.__init__(self)

            self.ts_end = None

    class TVOverloadInfo(PlanDecoderBase.TVOverloadInfo):

        """ Class holding information about the overload activities of a transport vehicle """

        def __init__(self):
            PlanDecoderBase.TVOverloadInfo.__init__(self)

            self.ts_end = None

    def __init__(self,
                 data_manager: GlobalDataManager,
                 roads: List[Linestring],
                 machine_initial_states: Dict[int, MachineState],
                 field_initial_states: Dict[int, FieldState],
                 out_field_route_planner: OutFieldRoutePlanner,
                 problem: Problem,
                 plan: TimeTriggeredPlan):

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
        plan : TimeTriggeredPlan
            Temporal plan
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
            self.__init_states(data_manager, machine_initial_states, field_initial_states)
            self.__parse_plan(plan)
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
        """

        for f in data_manager.fields.values():
            field_states = list()
            field_name = get_field_location_name(f.id)
            self._field_states[field_name] = field_states

            field_state = TemporalPlanDecoder.PlanFieldState()
            self._add_state(field_states, field_state)
            init_state: FieldState = field_initial_states.get(f.id)

            mass_per_area = FieldState.DEFAULT_AVG_MASS_PER_AREA_T_HA
            if init_state is not None:
                field_state.harvested_percentage_start = max(0.0, min(100.0, init_state.harvested_percentage))
                mass_per_area = init_state.avg_mass_per_area_t_ha

            self._fields_mass_per_area[field_name] = mass_per_area

            area = calc_area(f.subfields[0].boundary_outer)
            if area < 1e-3:
                raise ValueError(f'Field with id {f.id} has a subfield with invalid outer boundary')
            yield_mass = t_ha2Kg_sqrm(mass_per_area) * area
            self._fields_yield_mass[field_name] = yield_mass

            field_state.harvested_yield_mass_start = 0.01 * field_state.harvested_percentage_start * yield_mass

        for m in data_manager.machines.values():
            if m.machinetype is MachineType.HARVESTER:
                machine_name = get_harvester_name(m.id)
            elif m.machinetype is MachineType.OLV:
                machine_name = get_tv_name(m.id)
            else:
                continue

            machine_states = list()
            self._machine_states[machine_name] = machine_states

            init_state: MachineState = machine_initial_states.get(m.id)
            if init_state is None:
                continue

            machine_state = TemporalPlanDecoder.PlanMachineState()
            self._add_state(machine_states, machine_state)

            if init_state.position is not None:
                machine_state.loc_start = get_machine_initial_location_name(machine_name)

            if init_state.location_name is not None and len(init_state.location_name) > 0:
                machine_state.loc_start = init_state.location_name

                if m.machinetype is MachineType.HARVESTER:
                    field_states = self._field_states.get(init_state.location_name)
                    if field_states is not None and len(field_states) > 0:
                        field_states[0].state = TemporalPlanDecoder.FieldHarvestingState.BEING_HARVESTED_WAITING
                        field_states[0].harvester = machine_name

            machine_state.bunker_mass_start = machine_state.bunker_mass_end = init_state.bunker_mass

        for s in data_manager.silos.values():
            silo_states = list()
            silo_name = get_silo_location_name(s.id)
            self._silo_states[silo_name] = silo_states

            silo_state = TemporalPlanDecoder.PlanSiloState()
            self._add_state(silo_states, silo_state)

            self._silo_unloads[silo_name] = list()

    def __parse_plan(self, plan: TimeTriggeredPlan):

        """ Parse/decode the plan

        Parameters
        ----------
        plan : TimeTriggeredPlan
            Temporal plan
        """

        drive_harv_to_field_and_init_action_names = {member.value for member in ActionDriveHarvToFieldAndInit.ActionNames}
        drive_tv_to_field_and_overload_action_names = {member.value for member in ActionDriveTvToFieldAndReserveOverload.ActionNames}
        do_overload_action_names = {member.value for member in ActionDoOverload.ActionNames}
        drive_to_silo_action_names = {member.value for member in ActionDriveToSilo.ActionNames}
        drive_harv_to_field_exit_action_names = {member.value for member in ActionDriveHarvToFieldExit.ActionNames}
        drive_tv_to_field_exit_action_names = {member.value for member in ActionDriveTvToFieldExit.ActionNames}
        unload_at_silo_action_names = {member.value for member in ActionUnloadAtSilo.ActionNames}
        
        for start, action, duration in plan.timed_actions:
            ts_start = float(start)
            ts_end = None
            if duration is not None:
                ts_end = ts_start + float(duration)

            if action.action.name in drive_harv_to_field_and_init_action_names:
                self.__parse_action_drive_harv_field_and_init(action, ts_start, ts_end)
            elif action.action.name in drive_tv_to_field_and_overload_action_names:
                self.__parse_action_drive_tv_to_field_and_reserve_overload(action, ts_start, ts_end)
            elif action.action.name in do_overload_action_names:
                self.__parse_action_do_overload(action, ts_start, ts_end)
            elif action.action.name in drive_harv_to_field_exit_action_names:
                self.__parse_action_drive_harv_to_field_exit(action, ts_start, ts_end)
            elif action.action.name in drive_tv_to_field_exit_action_names:
                self.__parse_action_drive_tv_to_field_exit(action, ts_start, ts_end)
            elif action.action.name in drive_to_silo_action_names:
                self.__parse_action_drive_tv_to_silo(action, ts_start, ts_end)
            elif action.action.name in unload_at_silo_action_names:
                self.__parse_action_unload_at_silo(action, ts_start, ts_end)

        self._generate_silo_states_from_unloads()

    def __parse_action_drive_harv_field_and_init(self, action: ActionInstance, ts_start: float, ts_end: float):

        """ Parse/decode a 'actions.temporal.ActionDriveHarvToFieldAndInit' action and add the resulting decoded state(s)

        Parameters
        ----------
        action : ActionInstance
            UP action instance
        ts_start : State
            Start timestamp [s] of the UP state resulting from the action
        ts_end : State
            End timestamp [s] of the UP state resulting from the action
        """

        only_init = (action.action.name.find('drive') < 0)

        loc_from = field_access = None
        machine_name = field_name = None
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

        field = self._field_names_map.get(field_name)
        if field is None:
            raise ValueError(f'Invalid field = {field_name}')

        if not only_init:
            pt_from = self._harvester_init_locations_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._field_access_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._silo_access_names_map.get(loc_from)
            if pt_from is None:
                raise ValueError(f'Invalid loc_from = {loc_from}')
            pt_to = self._field_access_names_map.get(field_access)
            if pt_to is None:
                raise ValueError(f'Invalid loc_from = {field_access}')

            machine_state = TemporalPlanDecoder.PlanMachineState()
            machine_state.ts_start = ts_start
            machine_state.ts_end = ts_end
            machine_state.loc_start = loc_from
            machine_state.loc_end = field_access
            machine_state.pt_start = pt_from
            machine_state.pt_end = pt_to
            machine_state.activity = PlanDecoderBase.MachineActivity.TRANSIT_OFF_FIELD
            self._add_state(machine_states, machine_state)

        machine_state = TemporalPlanDecoder.PlanMachineState()
        machine_state.ts_start = ts_start if only_init else ts_end
        machine_state.loc_start = field_name
        machine_state.pt_start = self._get_point_from_machine_location(field_name)[0]
        machine_state.activity = PlanDecoderBase.MachineActivity.WAITING_TO_OVERLOAD
        self._add_state(machine_states, machine_state)

        field_states = self._field_states.get(field_name)
        field_state = self.__init_field_state_from_last(field_name)
        field_state.ts_start = ts_start
        field_state.state = TemporalPlanDecoder.FieldHarvestingState.RESERVED
        field_state.harvester = machine_name
        field_state.tv = None
        self._add_state(field_states, field_state)

        overloads = self._field_overloads.get(field_name)
        if overloads is None:
            overloads = TemporalPlanDecoder.FieldOverloads()
            self._field_overloads[field_name] = overloads
        overloads.harv = machine_name
        overloads.entry_point = field_access

    def __parse_action_drive_tv_to_field_and_reserve_overload(self, action: ActionInstance, ts_start, ts_end):

        """ Parse/decode a 'actions.temporal.ActionDriveTvToFieldAndReserveOverload' action and add the resulting decoded state(s)

        Parameters
        ----------
        action : ActionInstance
            UP action instance
        ts_start : State
            Start timestamp [s] of the UP state resulting from the action
        ts_end : State
            End timestamp [s] of the UP state resulting from the action
        """

        only_reserve_overload = (action.action.name.find('drive') < 0)

        machine_name = loc_from = field_name = field_access = None
        for i, param in enumerate(action.action.parameters):
            if param.name == 'tv':
                machine_name = f'{action.actual_parameters[i]}'
            elif param.name == 'loc_from':
                loc_from = f'{action.actual_parameters[i]}'
            elif param.name == 'field':
                field_name = f'{action.actual_parameters[i]}'
            elif param.name == 'field_access':
                field_access = f'{action.actual_parameters[i]}'

        machine_states = self._machine_states.get(machine_name)
        if machine_states is None:
            raise ValueError(f'Invalid tv = {machine_name}')

        field = self._field_names_map.get(field_name)
        if field is None:
            raise ValueError(f'Invalid field = {field_name}')

        if not only_reserve_overload:
            pt_from = self._tv_init_locations_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._field_access_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._silo_access_names_map.get(loc_from)
            if pt_from is None:
                raise ValueError(f'Invalid loc_from = {loc_from}')
            pt_to = self._field_access_names_map.get(field_access)
            if pt_to is None:
                raise ValueError(f'Invalid loc_from = {field_access}')

            machine_state = self.__init_tv_state_from_last(machine_name)
            machine_state.ts_start = ts_start
            machine_state.ts_end = ts_end
            machine_state.loc_start = loc_from
            machine_state.loc_end = field_access
            machine_state.pt_start = pt_from
            machine_state.pt_end = pt_to
            machine_state.activity = PlanDecoderBase.MachineActivity.TRANSIT_OFF_FIELD
            self._add_state(machine_states, machine_state)

        machine_state = self.__init_tv_state_from_last(machine_name)
        machine_state.ts_start = ts_start if only_reserve_overload else ts_end
        machine_state.loc_start = field_name
        machine_state.pt_start = self._get_point_from_machine_location(field_name)[0]
        machine_state.activity = PlanDecoderBase.MachineActivity.WAITING_TO_OVERLOAD
        self._add_state(machine_states, machine_state)

    def __parse_action_do_overload(self, action: ActionInstance, ts_start, ts_end):

        """ Parse/decode a 'actions.temporal.ActionDoOverload' action and add the resulting decoded state(s)

        Parameters
        ----------
        action : ActionInstance
            UP action instance
        ts_start : State
            Start timestamp [s] of the UP state resulting from the action
        ts_end : State
            End timestamp [s] of the UP state resulting from the action
        """

        field_exit_tv = None
        field_exit_harv = None
        harv_name = tv_name = field_name = None
        for i, param in enumerate(action.action.parameters):
            if param.name == 'harv':
                harv_name = f'{action.actual_parameters[i]}'
            elif param.name == 'tv':
                tv_name = f'{action.actual_parameters[i]}'
            elif param.name == 'field':
                field_name = f'{action.actual_parameters[i]}'
            elif param.name == 'field_exit_tv':
                field_exit_tv = f'{action.actual_parameters[i]}'
            elif param.name == 'field_exit_harv':
                field_exit_harv = f'{action.actual_parameters[i]}'

        if field_exit_tv is not None and field_exit_tv not in self._field_access_names_map.keys():
            field_exit_tv = None
        if field_exit_harv is not None and field_exit_harv not in self._field_access_names_map.keys():
            field_exit_harv = None

        harv_states = self._machine_states.get(harv_name)
        if harv_states is None:
            raise ValueError(f'Invalid harv = {harv_name}')
        tv_states = self._machine_states.get(tv_name)
        if tv_states is None:
            raise ValueError(f'Invalid tv = {tv_name}')
        field = self._field_names_map.get(field_name)
        if field is None:
            raise ValueError(f'Invalid field = {field_name}')

        field_states = self._field_states.get(field_name)
        field_state = self.__init_field_state_from_last(field_name)
        field_state.ts_start = ts_start
        field_state.ts_end = ts_end
        field_state.state = TemporalPlanDecoder.FieldHarvestingState.BEING_HARVESTED
        field_state.harvester = harv_name
        field_state.tv = tv_name

        tv = self._tv_names_map.get(tv_name)
        last_tv_state = self._machine_states.get(tv_name)[-1]
        last_tv_bunker_mass = last_tv_state.bunker_mass_end if last_tv_state.bunker_mass_end is not None else last_tv_state.bunker_mass_start

        field_yield_mass = self._fields_yield_mass.get(field_name)
        field_state.harvested_yield_mass_end = min(field_yield_mass, field_state.harvested_yield_mass_start + tv.bunker_mass - last_tv_bunker_mass)
        field_state.harvested_percentage_end = 100 * field_state.harvested_yield_mass_end / field_yield_mass

        harvested_mass = field_state.harvested_yield_mass_end - field_state.harvested_yield_mass_start

        self._add_state(field_states, field_state)

        field_states = self._field_states.get(field_name)
        field_state = self.__init_field_state_from_last(field_name)
        field_state.ts_start = ts_end
        field_state.state = TemporalPlanDecoder.FieldHarvestingState.HARVESTED \
            if field_state.harvested_percentage_start > 100 - 1e-3 \
            else TemporalPlanDecoder.FieldHarvestingState.BEING_HARVESTED_WAITING
        field_state.harvester = harv_name
        field_state.tv = None
        self._add_state(field_states, field_state)

        pt_field = self._get_point_from_machine_location(field_name)[0]

        # overload
        machine_state = TemporalPlanDecoder.PlanMachineState()
        machine_state.ts_start = ts_start
        machine_state.ts_end = ts_end
        machine_state.loc_start = field_name
        machine_state.pt_start = machine_state.pt_end = pt_field
        machine_state.activity = PlanDecoderBase.MachineActivity.OVERLOADING
        machine_state.overloading_machine_name = tv_name
        self._add_state(harv_states, machine_state)

        machine_state = self.__init_tv_state_from_last(tv_name)
        machine_state.ts_start = ts_start
        machine_state.ts_end = ts_end
        machine_state.loc_start = field_name
        machine_state.pt_start = machine_state.pt_end = pt_field
        machine_state.bunker_mass_end = machine_state.bunker_mass_start + harvested_mass
        machine_state.activity = PlanDecoderBase.MachineActivity.OVERLOADING
        machine_state.overloading_machine_name = harv_name
        self._add_state(tv_states, machine_state)

        # field exit
        if field_exit_harv is not None:
            machine_state = TemporalPlanDecoder.PlanMachineState()
            machine_state.ts_start = ts_end
            machine_state.loc_start = field_exit_harv
            machine_state.pt_start = pt_field
            machine_state.pt_end = self._get_point_from_machine_location(field_exit_harv)[0]
            machine_state.activity = PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE
            self._add_state(harv_states, machine_state)
        if field_exit_tv is not None:
            machine_state = self.__init_tv_state_from_last(tv_name)
            machine_state.ts_start = ts_end
            machine_state.loc_start = field_exit_tv
            machine_state.pt_start = pt_field
            machine_state.pt_end = self._get_point_from_machine_location(field_exit_tv)[0]
            machine_state.activity = PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE
            self._add_state(tv_states, machine_state)

        field_overloads = self._field_overloads.get(field_name)
        if field_overloads is None:
            field_overloads = TemporalPlanDecoder.FieldOverloads()
            self._field_overloads[field_name] = field_overloads
        if field_overloads.harv is not None and field_overloads.harv != harv_name:
            raise ValueError('Missmatch in assigned harvester to field')
        field_overloads.harv = harv_name
        overload_info = TemporalPlanDecoder.FieldOverloadInfo()
        overload_info.ts_start = ts_start
        overload_info.ts_end = ts_end
        overload_info.tv = tv_name
        self._add_state(field_overloads.overloads, overload_info, remove_future_states=False)

        tv_overloads = self._tv_overloads.get(tv_name)
        if tv_overloads is None:
            tv_overloads = list()
            self._tv_overloads[tv_name] = tv_overloads
        overload_info = TemporalPlanDecoder.TVOverloadInfo()
        overload_info.ts_start = ts_start
        overload_info.ts_end = ts_end
        overload_info.harv = harv_name
        overload_info.field = field_name
        self._add_state(tv_overloads, overload_info, remove_future_states=False)
        self._add_state(self.tv_overloads_all, overload_info, remove_future_states=False)

    def __parse_action_drive_harv_to_field_exit(self, action: ActionInstance, ts_start, ts_end):

        """ Parse/decode a 'actions.temporal.ActionDriveHarvToFieldExit' action and add the resulting decoded state(s)

        Parameters
        ----------
        action : ActionInstance
            UP action instance
        ts_start : State
            Start timestamp [s] of the UP state resulting from the action
        ts_end : State
            End timestamp [s] of the UP state resulting from the action
        """

        harv_name = field_access = field_name = None
        for i, param in enumerate(action.action.parameters):
            if param.name == 'harv':
                harv_name = f'{action.actual_parameters[i]}'
            elif param.name == 'field':
                field_name = f'{action.actual_parameters[i]}'
            elif param.name == 'field_access':
                field_access = f'{action.actual_parameters[i]}'

        machine_states = self._machine_states.get(harv_name)
        if machine_states is None:
            raise ValueError(f'Invalid harv = {harv_name}')
        field = self._field_names_map.get(field_name)
        if field is None:
            raise ValueError(f'Invalid field = {field_name}')

        machine_state = TemporalPlanDecoder.PlanMachineState()
        machine_state.ts_start = ts_start
        machine_state.ts_end = ts_end
        machine_state.loc_start = field_name
        machine_state.loc_end = field_access
        machine_state.pt_start = self._get_point_from_machine_location(field_name)[0]
        machine_state.pt_end = self._get_point_from_machine_location(field_access)[0]
        machine_state.activity = PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD
        self._add_state(machine_states, machine_state)

        machine_state = TemporalPlanDecoder.PlanMachineState()
        machine_state.ts_start = ts_end
        machine_state.loc_start = field_access
        machine_state.pt_start = self._get_point_from_machine_location(field_access)[0]
        machine_state.activity = PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE
        self._add_state(machine_states, machine_state)

        field_states = self._field_states.get(field_name)
        field_state = self.__init_field_state_from_last(field_name)
        field_state.ts_start = ts_start
        field_state.tv = None
        field_state.state = TemporalPlanDecoder.FieldHarvestingState.HARVESTED
        self._add_state(field_states, field_state)

    def __parse_action_drive_tv_to_field_exit(self, action: ActionInstance, ts_start, ts_end):

        """ Parse/decode a 'actions.temporal.ActionDriveTvToFieldExit' action and add the resulting decoded state(s)

        Parameters
        ----------
        action : ActionInstance
            UP action instance
        ts_start : State
            Start timestamp [s] of the UP state resulting from the action
        ts_end : State
            End timestamp [s] of the UP state resulting from the action
        """

        tv_name = field_access = field_name = None
        for i, param in enumerate(action.action.parameters):
            if param.name == 'tv':
                tv_name = f'{action.actual_parameters[i]}'
            elif param.name == 'field':
                field_name = f'{action.actual_parameters[i]}'
            elif param.name == 'field_access':
                field_access = f'{action.actual_parameters[i]}'

        machine_states = self._machine_states.get(tv_name)
        if machine_states is None:
            raise ValueError(f'Invalid tv = {tv_name}')
        field = self._field_names_map.get(field_name)
        if field is None:
            raise ValueError(f'Invalid field = {field_name}')

        machine_state = self.__init_tv_state_from_last(tv_name)
        machine_state.ts_start = ts_start
        machine_state.ts_end = ts_end
        machine_state.loc_start = field_name
        machine_state.loc_end = field_access
        machine_state.pt_start = self._get_point_from_machine_location(field_name)[0]
        machine_state.pt_end = self._get_point_from_machine_location(field_access)[0]
        machine_state.activity = PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD
        self._add_state(machine_states, machine_state)

        machine_state = self.__init_tv_state_from_last(tv_name)
        machine_state.ts_start = ts_end
        machine_state.loc_start = field_access
        machine_state.pt_start = self._get_point_from_machine_location(field_access)[0]
        machine_state.activity = PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE
        self._add_state(machine_states, machine_state)

    def __parse_action_drive_tv_to_silo(self, action: ActionInstance, ts_start, ts_end):

        """ Parse/decode a 'actions.temporal.ActionDriveToSilo' action and add the resulting decoded state(s)

        Parameters
        ----------
        action : ActionInstance
            UP action instance
        ts_start : State
            Start timestamp [s] of the UP state resulting from the action
        ts_end : State
            End timestamp [s] of the UP state resulting from the action
        """

        only_init = (action.action.name.find('drive') < 0)
        with_unload = ( action.action.name.find('_and_unload') >= 0 )

        machine_name = loc_from = silo_name = silo_access = None
        for i, param in enumerate(action.action.parameters):
            if param.name == 'tv':
                machine_name = f'{action.actual_parameters[i]}'
            elif param.name == 'loc_from':
                loc_from = f'{action.actual_parameters[i]}'
            elif param.name == 'silo':
                silo_name = f'{action.actual_parameters[i]}'
            elif param.name == 'silo_access':
                silo_access = f'{action.actual_parameters[i]}'

        machine_states = self._machine_states.get(machine_name)
        if machine_states is None:
            raise ValueError(f'Invalid tv = {machine_name}')

        silo_unloads = self._silo_unloads.get(silo_name)
        if silo_unloads is None:
            raise ValueError(f'Invalid silo = {silo_name}')

        pt_from = None
        if not only_init:
            pt_from = self._tv_init_locations_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._field_access_names_map.get(loc_from)
            if pt_from is None:
                pt_from = self._silo_access_names_map.get(loc_from)
            if pt_from is None:
                raise ValueError(f'Invalid loc_from = {loc_from}')
        pt_to = self._silo_access_names_map.get(silo_access)
        if pt_to is None:
            raise ValueError(f'Invalid loc_from = {silo_access}')
        silo = self._silo_names_map.get(silo_name)
        if silo is None:
            raise ValueError(f'Invalid silo = {silo_name}')

        if with_unload:
            machine_state = self.__init_tv_state_from_last(machine_name)
            bunker_mass_start = machine_state.bunker_mass_start
            if only_init:
                unload_time = ts_end - ts_start
                transit_time = 0.0
            else:
                machine_id = get_tv_id_from_name(machine_name)
                machine = self._data_manager.machines.get(machine_id)
                if machine is not None:
                    unload_time = min(ts_end - ts_start, machine_state.bunker_mass_start / machine.unloading_speed_mass)
                else:
                    unload_time = min(ts_end - ts_start, 1.0)
                transit_time = ts_end-ts_start-unload_time

            if transit_time > 1e-9:
                machine_state.ts_start = ts_start
                machine_state.ts_end = ts_start + transit_time
                machine_state.loc_start = loc_from
                machine_state.loc_end = silo_access
                machine_state.pt_start = pt_from
                machine_state.pt_end = pt_to
                machine_state.activity = PlanDecoderBase.MachineActivity.TRANSIT_OFF_FIELD
                self._add_state(machine_states, machine_state)

            timestamp_start_unload = ts_start + transit_time

            machine_state = self.__init_tv_state_from_last(machine_name)
            machine_state.ts_start = timestamp_start_unload
            machine_state.ts_end = ts_end
            machine_state.loc_start = silo_access
            machine_state.loc_end = silo_access
            machine_state.pt_start = pt_to
            machine_state.pt_end = pt_to
            machine_state.bunker_mass_end = 0
            machine_state.activity = PlanDecoderBase.MachineActivity.UNLOADING
            self._add_state(machine_states, machine_state)

            silo_unload = PlanDecoderBase.SiloUnloadInfo()
            silo_unload.ts_start = timestamp_start_unload
            silo_unload.ts_end = ts_end
            silo_unload.unloaded_mass = bunker_mass_start
            silo_unload.silo_access = silo_access
            silo_unload.tv = machine_name
            self._add_state(silo_unloads, silo_unload, remove_future_states=False)

            unload_info = TemporalPlanDecoder.TVUnloadInfo()
            unload_info.ts_start = timestamp_start_unload
            unload_info.ts_end = ts_end
            unload_info.silo_access = silo_access
            tv_overloads = self._tv_overloads.get(machine_name)
            if tv_overloads is not None and len(tv_overloads) > 0:
                if tv_overloads[-1].ts_start < timestamp_start_unload:
                    unload_info.overload_info = tv_overloads[-1]
                else:
                    unload_info.overload_info, _ = self._get_state_at(tv_overloads, timestamp_start_unload)
                unload_info.overload_info.silo_access = silo_access
            tv_unloads = self._tv_unloads.get(machine_name)
            if tv_unloads is None:
                tv_unloads = list()
                self._tv_unloads[machine_name] = tv_unloads
            self._add_state(tv_unloads, unload_info, remove_future_states=False)

        elif not only_init:
            machine_state = self.__init_tv_state_from_last(machine_name)
            machine_state.ts_start = ts_start
            machine_state.ts_end = ts_end
            machine_state.loc_start = loc_from
            machine_state.loc_end = silo_access
            machine_state.pt_start = pt_from
            machine_state.pt_end = pt_to
            machine_state.activity = PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD
            self._add_state(machine_states, machine_state)

        machine_state = self.__init_tv_state_from_last(machine_name)
        machine_state.ts_start = ts_end
        machine_state.loc_start = silo_access
        machine_state.activity = PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE if with_unload else PlanDecoderBase.MachineActivity.WAITING_TO_UNLOAD
        self._add_state(machine_states, machine_state)

    def __parse_action_unload_at_silo(self, action: ActionInstance, ts_start, ts_end):

        """ Parse/decode a 'actions.temporal.ActionUnloadAtSilo' action and add the resulting decoded state(s)

        Parameters
        ----------
        action : ActionInstance
            UP action instance
        ts_start : State
            Start timestamp [s] of the UP state resulting from the action
        ts_end : State
            End timestamp [s] of the UP state resulting from the action
        """

        machine_name = silo_access = None
        for i, param in enumerate(action.action.parameters):
            if param.name == 'tv':
                machine_name = f'{action.actual_parameters[i]}'
            elif param.name == 'silo_access':
                silo_access = f'{action.actual_parameters[i]}'

        machine_states = self._machine_states.get(machine_name)
        if machine_states is None:
            raise ValueError(f'Invalid tv = {machine_name}')
        pt_from = self._silo_access_names_map.get(silo_access)
        if pt_from is None:
            raise ValueError(f'Invalid silo_access = {silo_access}')

        silo_name = get_silo_name_from_silo_access_location_name(silo_access)
        silo_unloads = self._silo_unloads.get(silo_name)
        if silo_unloads is None:
            raise ValueError(f'Invalid silo = {silo_name} obtained from silo_access = {silo_access}')

        machine_state = self.__init_tv_state_from_last(machine_name)
        machine_state.ts_start = ts_start
        machine_state.ts_end = ts_end
        machine_state.loc_start = silo_access
        machine_state.loc_end = silo_access
        machine_state.pt_start = machine_state.pt_end = pt_from
        machine_state.bunker_mass_end = 0
        machine_state.activity = PlanDecoderBase.MachineActivity.UNLOADING
        self._add_state(machine_states, machine_state)

        silo_unload = PlanDecoderBase.SiloUnloadInfo()
        silo_unload.ts_start = ts_start
        silo_unload.ts_end = ts_end
        silo_unload.unloaded_mass = machine_state.bunker_mass_start
        silo_unload.silo_access = silo_access
        silo_unload.tv = machine_name
        self._add_state(silo_unloads, silo_unload, remove_future_states=False)

        machine_state = self.__init_tv_state_from_last(machine_name)
        machine_state.ts_start = ts_end
        machine_state.loc_start = silo_access
        machine_state.pt_start = pt_from
        machine_state.activity = PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE
        self._add_state(machine_states, machine_state)

        unload_info = TemporalPlanDecoder.TVUnloadInfo()
        unload_info.ts_start = ts_start
        unload_info.ts_end = ts_end
        unload_info.silo_access = silo_access
        tv_overloads = self._tv_overloads.get(machine_name)
        if tv_overloads is not None and len(tv_overloads) > 0:
            if tv_overloads[-1].ts_start < ts_start:
                unload_info.overload_info = tv_overloads[-1]
            else:
                unload_info.overload_info, _ = self._get_state_at(tv_overloads, ts_start)
            unload_info.overload_info.silo_access = silo_access
        tv_unloads = self._tv_unloads.get(machine_name)
        if tv_unloads is None:
            tv_unloads = list()
            self._tv_unloads[machine_name] = tv_unloads
        self._add_state(tv_unloads, unload_info, remove_future_states=False)

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

        state = TemporalPlanDecoder.PlanFieldState()
        state_prev = self._field_states.get(field_name)[-1]
        state.harvester = state_prev.harvester
        state.tv = state_prev.tv
        state.harvested_percentage_start = state_prev.harvested_percentage_start \
            if state_prev.harvested_percentage_end is None \
            else state_prev.harvested_percentage_end
        state.harvested_yield_mass_start = state_prev.harvested_yield_mass_start \
            if state_prev.harvested_yield_mass_end is None \
            else state_prev.harvested_yield_mass_end
        return state

    def __init_tv_state_from_last(self, tv_name: str) -> PlanMachineState:

        """ Partially initialize a decoded state for a given transport vehicle based on its previous decoded state

        Parameters
        ----------
        tv_name : str
            Transport vehicle object name

        Returns
        ----------
        tv_state : PlanMachineState
            Partially initialized decoded state for the given transport vehicle
        """

        state = TemporalPlanDecoder.PlanMachineState()
        state_prev = self._machine_states.get(tv_name)[-1]
        state.bunker_mass_start = state.bunker_mass_end = state_prev.bunker_mass_end
        return state
