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

import math
import warnings
from unified_planning.shortcuts import *
from up_interface.fluents import FluentNames as fn
import up_interface.types as upt
from management.global_data_manager import GlobalDataManager
from post_processing.plan_decoder_base import PlanDecoderBase
from management.field_partial_plan_manager import FieldPartialPlanManager
from silo_planning.types import SiloExtended
from route_planning.field_route_planning import PlanningSettings
from route_planning.types import *
from route_planning.outfield_route_planning import OutFieldRoutePlanner
from exposed_arolib.types import *
from exposed_arolib.geometry import *
import exposed_arolib.io as aio
from up_interface.problem_encoder.names_helper import *


class ArolibPlanGenerator(PlanDecoderBase):

    """ Class used to generate Arolib plans (routes) based on a decoded UP-plan

    The generated plan is an approximation to the UP-plan and might not be in line with some problem constraints (e.g., bunker mass capacity of the transport vehicles), object states, a.o.
    """

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

    class TVOverloadInfo(PlanDecoderBase.TVOverloadInfo):

        """ Class holding information about the overload activities of a transport vehicle """

        def __init__(self):
            PlanDecoderBase.TVOverloadInfo.__init__(self)
            self.overloaded_mass = 0.0

    class __TVOverloadInfo:

        """ Class holding internal information about an overload activity of a transport vehicle """

        def __init__(self):
            self.harv = None
            self.silo_access = None

    class __PlanData:

        """ Class holding plan information """

        def __init__(self):
            self.fields: Dict[str, Field] = dict()
            """ Fields: {field_object_name, field} """

            self.harvesters: Dict[str, Machine] = dict()
            """ Harvesters: {harv_object_name, machine} """

            self.tvs: Dict[str, Machine] = dict()
            """ Transport vehicles: {tv_object_name, machine} """

            self.silos: Dict[str, SiloExtended] = dict()
            """ Silos: {silo_object_name, silo} """

            self.outfield_info_base: Dict[str, OutFieldInfo] = dict()
            """ Base out-of-field information for th fields: {field_object_name, info} """

            self.outfield_transit_distances: Dict[str, Dict[str, float]] = dict()
            """ Transit distances between locations: {loc_from_object_name, {loc_to_object_name, distance} } """

            self.machine_states: Dict[str, MachineState] = dict()
            """ Current machine states: {machine_object_name, machine_state} """

            self.harv_field_turns: Dict[str, List[str]] = dict()
            """ Fields (sorted by turn) for the harvesters: {harv_object_name, sorted_field_object_names} """

            self.harv_field_entry_points: Dict[str, Dict[str, int]] = dict()
            """ Index of the access points used by the harvesters to enter the fields: {harv_object_name, {field_object_name, fap_ind} } """

            self.harv_tv_turns: Dict[str, List[str]] = dict()
            """ Transport vehicles (sorted by turn) for the harvesters: {harv_object_name, sorted_tv_object_names} """

            self.tv_overloads: Dict[str, List[ArolibPlanGenerator.__TVOverloadInfo]] = dict()
            """ Overloads' information (sorted by turn) for the transport vehicles: {tv_object_name, sorted_overloads_info} """

            self.field_planning_settings: Dict[str, PlanningSettings] = dict()
            """ Planning settings for the fields: {field_object_name, planning_settings} """

            self.field_plan_manager = FieldPartialPlanManager()
            """ Partial-plan manager for the fields: {field_object_name, plan_manager} """

            self.field_plan_responses: Dict[str, FieldPartialPlanManager.PlanResponse] = dict()
            """ Last plan-manager responses for the fields: {field_object_name, plan_response} """

            self.fields_yield_mass_factor: Dict[str, float] = dict()
            """ Holds the yield mass compensation factor (total_planned_harvested_mass / expected_total_yield_mass) for the fields: {field_object_name, mass_factor} """

            self.fields_overloads_count: Dict[str, int] = dict()
            """ Amount of planned overloads left for the fields: {field_object_name, remaining_overloads}"""

            self.fields_yield_mass_compensation: Dict[str, float] = dict()
            """ Holds the yield mass [kg] needed to compensate for differences between transport vehicles' total bunker capacity and actual filling level of the machine after planning an overload with Arolib: {field_object_name, mass_compensation} """

    def __init__(self,
                 data_manager: GlobalDataManager,
                 roads: List[Linestring],
                 machine_initial_states: Dict[int, MachineState],
                 field_initial_states: Dict[int, FieldState],
                 out_field_route_planner: OutFieldRoutePlanner,
                 problem: Problem,
                 plan_decoder: PlanDecoderBase):

        """ Initialization

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
        plan_decoder : PlanDecoderBase
            Plan decoder
        """
        PlanDecoderBase.__init__(self,
                                 data_manager=data_manager,
                                 roads=roads,
                                 machine_initial_states=machine_initial_states,
                                 field_initial_states=field_initial_states,
                                 out_field_route_planner=out_field_route_planner,
                                 problem=problem
                                 )

        self.__routes: Dict[str, Route] = dict()
        try:
            self.__init_states(problem, data_manager, machine_initial_states, field_initial_states, plan_decoder)
            self.__generate_plan(data_manager, machine_initial_states, out_field_route_planner, problem, plan_decoder)
            self._generate_silo_states_from_unloads()
        except Exception as e:
            self._ok = False
            raise e

    @property
    def routes(self) -> Dict[str, Route]:
        """ Get the generated routes

        Returns
        ----------
        routes : Dict[str, Route]
            Generated routes
        """
        return self.__routes

    def __init_states(self,
                      problem: Problem,
                      data_manager: GlobalDataManager,
                      machine_initial_states: Dict[int, MachineState],
                      field_initial_states: Dict[int, FieldState],
                      plan_decoder: PlanDecoderBase):

        """ Initialize plan decoded states

        Parameters
        ----------
        problem : Problem
            UP problem
        data_manager : GlobalDataManager
            Data manager
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        field_initial_states : Dict[int, FieldState]
            Field initial states: {field_id: field_state}
        plan_decoder : PlanDecoderBase
            Plan decoder
        """

        field_yield_mass_unharvested = problem.fluent(fn.field_yield_mass_unharvested.value)

        for f in data_manager.fields.values():
            field_name = get_field_location_name(f.id)
            init_state: FieldState = field_initial_states.get(f.id)

            mass_per_area = FieldState.DEFAULT_AVG_MASS_PER_AREA_T_HA
            if init_state is not None:
                harvested_percentage_start = max(0.0, min(100.0, init_state.harvested_percentage))
                if harvested_percentage_start is not None and harvested_percentage_start > 1e-3:
                    warnings.warn(f'[ERROR] This generator do not support partially harvested fields. '
                                  f'Field {field_name} will be planned completely and the infield planning might fail')
                mass_per_area = init_state.avg_mass_per_area_t_ha

            self._fields_mass_per_area[field_name] = mass_per_area

            field_object = problem.object(field_name)
            self._fields_yield_mass[field_name] = float(problem.initial_value(field_yield_mass_unharvested(field_object)).constant_value())

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

            machine_state = ArolibPlanGenerator.PlanMachineState()
            self._add_state(machine_states, machine_state)

            if init_state.position is not None:
                machine_state.loc_start = machine_state.loc_end = get_machine_initial_location_name(machine_name)
                machine_state.pt_start = machine_state.pt_end = get_copy(init_state.position)
            else:
                machine_state_2 = plan_decoder.machine_states.get(machine_name)
                if machine_state_2 is not None and len(machine_state_2) > 0:
                    machine_state.loc_start = machine_state.loc_end = machine_state_2[0].loc_start
                    machine_state.pt_start = machine_state.pt_end = machine_state_2[0].pt_start

            if init_state.location_name is not None and len(init_state.location_name) > 0:
                machine_state.loc_start = init_state.location_name

                if m.machinetype is MachineType.HARVESTER:
                    field_states = self._field_states.get(init_state.location_name)
                    if field_states is not None and len(field_states) > 0:
                        field_states[0].state = PlanDecoderBase.FieldHarvestingState.BEING_HARVESTED_WAITING
                        field_states[0].harvester = machine_name

            machine_state.bunker_mass_start = machine_state.bunker_mass_end = init_state.bunker_mass

        for s in data_manager.silos.values():
            silo_states = list()
            silo_name = get_silo_location_name(s.id)
            self._silo_states[silo_name] = silo_states

            silo_state = PlanDecoderBase.PlanSiloState()
            self._add_state(silo_states, silo_state)

            self._silo_unloads[silo_name] = list()

    def __generate_plan(self,
                        data_manager: GlobalDataManager,
                        machine_initial_states: Dict[int, MachineState],
                        out_field_route_planner: OutFieldRoutePlanner,
                        problem: Problem,
                        plan_decoder: PlanDecoderBase):

        """ Generate the Arolib-based plan and corresponding decoded-states

        Parameters
        ----------
        data_manager : GlobalDataManager
            Data manager
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        out_field_route_planner : OutFieldRoutePlanner
            Route/path planner for transit outside the fields
        problem : Problem
            UP problem
        plan_decoder : PlanDecoderBase
            Plan decoder
        """

        print(f'Generating arolib plan...')

        plan_data: ArolibPlanGenerator.__PlanData = ArolibPlanGenerator.__init_plan_data(problem,
                                                                                         data_manager,
                                                                                         machine_initial_states,
                                                                                         plan_decoder)

        assert len(plan_data.harv_field_turns) > 0, "No fields no harvest?"

        for tv_name, overloads in plan_data.tv_overloads.items():
            if len(overloads) == 0 or overloads[0].harv is not None:
                continue
            overload = overloads.pop(0)
            if not self.__send_tv_to_silo(plan_data, out_field_route_planner,
                                          tv_name, plan_data.tvs.get(tv_name), overload.silo_access):
                return

        while len(plan_data.harv_field_turns) > 0:
            for harv_name, fields_names in plan_data.harv_field_turns.items():
                if len(fields_names) == 0:
                    plan_data.harv_field_turns.pop(harv_name)
                    break
                harv = plan_data.harvesters.get(harv_name)
                next_field = fields_names[0]
                field_plan_resp = plan_data.field_plan_responses.get(next_field)
                if field_plan_resp is None:
                    print(f'\n\tInitializing field {next_field} with harvester {harv_name}...')

                    field_states = list()
                    self._field_states[next_field] = field_states
                    if plan_data.machine_states.get(harv_name).timestamp > 0:
                        field_state = ArolibPlanGenerator.PlanFieldState()
                        field_state.ts_start = 0.0
                        field_state.ts_end = plan_data.machine_states.get(harv_name).timestamp
                        field_state.state = PlanDecoderBase.FieldHarvestingState.UNRESERVED
                        field_state.harvested_percentage_start = field_state.harvested_percentage_end = 0
                        field_state.harvested_yield_mass_start = field_state.harvested_yield_mass_end = 0
                        field_states.append(field_state)

                    field_plan_resp = ArolibPlanGenerator.__init_field_plan(plan_data, next_field, harv_name)
                    if field_plan_resp is None:
                        warnings.warn(f'[ERROR] Error initializing plan for field {next_field} and harv {harv_name}')
                        return

                    ArolibPlanGenerator.__add_out_field_route_to_field(harv,
                                                                       field_plan_resp.routes.get(harv.id),
                                                                       out_field_route_planner)

                    route_plan = field_plan_resp.routes.get(harv.id)
                    field_access = plan_data.harv_field_entry_points.get(next_field)
                    if field_access is not None:
                        field_access = get_field_access_location_name( plan_data.fields.get(next_field).id,
                                                                       field_access.get(next_field) )
                    self.__update_from_field_init(next_field, harv_name, route_plan, field_access)

                    plan_data.machine_states[harv_name] = field_plan_resp.machine_states.get(harv.id)
                    plan_data.field_plan_responses[next_field] = field_plan_resp

                    base_route = plan_data.field_plan_manager.get_plan_base_route_copy(field_plan_resp.plan_id)

                    field_yield_mass = self._fields_yield_mass.get(next_field)
                    plan_data.fields_yield_mass_factor[next_field] = base_route.route_points[-1].worked_mass / field_yield_mass
                    plan_data.fields_yield_mass_compensation[next_field] = 0

                    print(f'\t... successful with yield_mass_factor {plan_data.fields_yield_mass_factor.get(next_field)}'
                          f'= {base_route.route_points[-1].worked_mass} / {field_yield_mass}')

                print(f'\n\tPlanning overload in field {next_field} with harvester {harv_name}...')

                harv_tv_turns = plan_data.harv_tv_turns.get(harv_name)

                if harv_tv_turns is None or len(harv_tv_turns) == 0:
                    ArolibPlanGenerator.__save_arolib_plan(plan_data, self.__routes, data_manager)

                    warnings.warn(f'[ERROR] No tv-turns left for harv {harv_name}')
                    return

                next_tv_name = harv_tv_turns.pop(0)
                tv_overloads = plan_data.tv_overloads.get(next_tv_name)

                print(f'\t\t... and tv {next_tv_name}...')

                if tv_overloads is None or len(tv_overloads) == 0:
                    ArolibPlanGenerator.__save_arolib_plan(plan_data, self.__routes, data_manager)

                    warnings.warn(f'[ERROR] No overloads left for TV {next_tv_name}')
                    return

                if harv_name != tv_overloads[0].harv:
                    continue
                next_tv_original = plan_data.tvs.get(next_tv_name)

                next_tv = get_copy(next_tv_original)
                next_tv.bunker_mass *= plan_data.fields_yield_mass_factor.get(next_field)
                next_tv.bunker_mass += plan_data.fields_yield_mass_compensation.get(next_field)

                ofi = get_copy(plan_data.outfield_info_base[next_field])
                ArolibPlanGenerator.__update_arrival_data(plan_data, next_field, plan_data.fields.get(next_field),
                                                          next_tv_name, next_tv, ofi)
                field_plan_resp = plan_data.field_plan_manager.plan_overload(field_plan_resp.plan_id,
                                                                             next_tv,
                                                                             plan_data.machine_states.get(next_tv_name),
                                                                             ofi,
                                                                             plan_data.field_planning_settings.get(next_field))

                if field_plan_resp is None:
                    ArolibPlanGenerator.__save_arolib_plan(plan_data, self.__routes, data_manager)

                    warnings.warn(f'[ERROR] Error planning overload for field {next_field}, '
                                  f'harv {harv_name}, and TV {next_tv_name}')
                    return

                tv_overload = tv_overloads.pop(0)

                ArolibPlanGenerator.__add_out_field_route_to_field(next_tv,
                                                                   field_plan_resp.routes.get(next_tv.id),
                                                                   out_field_route_planner)

                harv_state = field_plan_resp.machine_states.get(harv.id)
                if harv_state is not None:
                    plan_data.machine_states[harv_name] = harv_state
                plan_data.machine_states[next_tv_name] = field_plan_resp.machine_states.get(next_tv.id)
                plan_data.field_plan_responses[next_field] = field_plan_resp

                self.__update_from_overload(next_field, harv_name, harv.id, next_tv_name, next_tv.id,
                                            field_plan_resp, plan_data, tv_overload.silo_access)

                last_tv_route_point = field_plan_resp.routes.get(next_tv.id).route_points[-1]
                bunker_mass_diff = last_tv_route_point.bunker_mass - next_tv_original.bunker_mass
                if bunker_mass_diff > 1e-3:
                    print(f'\t... successfull with resulting bunker_mass capacity difference '
                          f'= {bunker_mass_diff} kg '
                          f'({100 * bunker_mass_diff / next_tv_original.bunker_mass} %)')

                field_ol_count = plan_data.fields_overloads_count.get(next_field)
                plan_data.fields_overloads_count[next_field] = field_ol_count - 1
                if field_ol_count == 2:
                    plan_data.fields_yield_mass_compensation[next_field] = self._fields_yield_mass.get(next_field)
                else:
                    plan_data.fields_yield_mass_compensation[next_field] = max(0.0, next_tv.bunker_mass - last_tv_route_point.bunker_mass)

                if tv_overload.silo_access is not None:
                    if not self.__send_tv_to_silo(plan_data, out_field_route_planner,
                                                  next_tv_name, next_tv, tv_overload.silo_access):
                        return

                ArolibPlanGenerator.__save_arolib_plan(plan_data, self.__routes, data_manager)

                if field_plan_resp.finished_field:
                    fields_names.pop(0)

                    field_states = self._field_states.get(next_field)
                    field_state = field_states[-1]
                    field_state.ts_end = harv_state.timestamp
                    field_state.harvested_percentage_end = 100
                    field_state.harvested_yield_mass_end = self._fields_yield_mass.get(next_field)
                    field_states.append(field_state)

                    field_state = deepcopy(field_state)
                    field_state.ts_start = field_state.ts_end
                    field_state.ts_end = None
                    field_state.state = PlanDecoderBase.FieldHarvestingState.HARVESTED
                    field_states.append(field_state)

                    break

        ArolibPlanGenerator.__save_arolib_plan(plan_data, self.__routes, data_manager)

        self._ok = True

    @staticmethod
    def __get_new_machine_state(machine_states: List[PlanDecoderBase.PlanMachineState],
                                timestamp: float,
                                loc_name: Union[str, None] = None,
                                pt: Union[Point, None] = None,
                                bunker_mass: Union[float, None] = None,
                                transit_time: Union[float, None] = None,
                                waiting_time: Union[float, None] = None,
                                action: Union[str, None] = None,
                                activity: Union[PlanDecoderBase.MachineActivity, None] = None,
                                overloading_machine: Union[str, None] = None) \
            -> PlanDecoderBase.PlanMachineState:

        """ Get a new machine decoded state based on the previous decoded state and the new state values

        Parameters
        ----------
        machine_states : List['PlanDecoderBase.PlanMachineState']
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
        machine_state = ArolibPlanGenerator.PlanMachineState()
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

    def __update_from_field_init(self, field_name: str, harv_name: str, route_plan: Route, field_access: Optional[str]):

        """ Updates the plan data based on the routes planned for the plan initialization of the given field

        Parameters
        ----------
        field_name : str
            Field object name
        harv_name : str
            Harvester object name
        route_plan : Route
            Harvester planned route
        field_access : str
            Object name of the field-access used by the harvester to enter the field (if None, the harvester was already at the field)
        """

        route = self.__routes.get(harv_name)
        if route is None:
            route = route_plan
            self.__routes[harv_name] = route
        else:
            if len(route.route_points) > 0 \
                    and abs(route.route_points[-1].time_stamp - route_plan.route_points[0].time_stamp) < 1e-9:
                route.route_points.pop_back()
            route.route_points.extend(route_plan.route_points)

        field_states = self._field_states.get(field_name)

        field_state = ArolibPlanGenerator.PlanFieldState()
        field_state.ts_start = route_plan.route_points[0].time_stamp
        field_state.ts_end = route_plan.route_points[-1].time_stamp
        field_state.state = PlanDecoderBase.FieldHarvestingState.RESERVED
        field_state.harvested_percentage_start = field_state.harvested_percentage_end = 0
        field_state.harvested_yield_mass_start = field_state.harvested_yield_mass_end = 0
        field_states.append(field_state)

        field_state = ArolibPlanGenerator.PlanFieldState()
        field_state.ts_start = route_plan.route_points[-1].time_stamp
        field_state.ts_end = None
        field_state.state = PlanDecoderBase.FieldHarvestingState.BEING_HARVESTED_WAITING
        field_state.harvested_percentage_start = field_state.harvested_percentage_end = 0
        field_state.harvested_yield_mass_start = field_state.harvested_yield_mass_end = 0
        field_states.append(field_state)

        rp_field_entry = route_plan.route_points[0]
        for rp in reversed(route_plan.route_points):
            if rp.type is RoutePointType.FIELD_ENTRY or rp.type is RoutePointType.FIELD_EXIT:
                rp_field_entry = rp
                break

        machine_states = self._machine_states.get(harv_name)
        prev_state = machine_states[-1]

        if prev_state.ts_end < route_plan.route_points[0].time_stamp - 1e-3:
            activity = PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE
            if rp_field_entry is route_plan.route_points[0]:
                activity = PlanDecoderBase.MachineActivity.WAITING_TO_OVERLOAD
            machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                        route_plan.route_points[0].time_stamp,
                                                                        pt=get_copy(route_plan.route_points[0].point()),
                                                                        waiting_time=route_plan.route_points[0].time_stamp - prev_state.ts_end,
                                                                        activity=activity)
            self._add_state(machine_states, machine_state)

        if rp_field_entry is not route_plan.route_points[0]:
            machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                        rp_field_entry.time_stamp,
                                                                        loc_name=field_access,
                                                                        pt=get_copy(rp_field_entry.point()),
                                                                        transit_time=(rp_field_entry.time_stamp - route_plan.route_points[0].time_stamp),
                                                                        activity=PlanDecoderBase.MachineActivity.TRANSIT_OFF_FIELD)
            self._add_state(machine_states, machine_state)

        machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                    route_plan.route_points[-1].time_stamp,
                                                                    loc_name=field_name,
                                                                    pt=get_copy(route_plan.route_points[-1].point()),
                                                                    activity=PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD)
        self._add_state(machine_states, machine_state)

    def __update_from_overload(self,
                               field_name: str,
                               harv_name: str, harv_id: int,
                               tv_name: str, tv_id: int,
                               field_plan_resp: FieldPartialPlanManager.PlanResponse,
                               plan_data: 'ArolibPlanGenerator.__PlanData',
                               silo_access: Optional[str]):

        """ Updates the plan data based on the routes planned for an overload in the given field

        Parameters
        ----------
        field_name : str
            Field object name
        harv_name : str
            Harvester object name
        tv_name : str
            Transport-vehicle object name
        field_plan_resp : FieldPartialPlanManager.PlanResponse
            Plan response of the field partial manager for the corresponding overload
        plan_data : __PlanData
            Plan data
        silo_access : str
            Object name of the silo-access used by the transport vehicle to unload the yield from the corresponding overload (if None -> the transport vehicle did not unload after the overload)
        """

        for m_name, m_id in [(harv_name, harv_id), (tv_name, tv_id)]:
            route = self.__routes.get(m_name)
            route_plan = field_plan_resp.routes.get(m_id)
            if route is None:
                if route_plan is not None:
                    self.__routes[m_name] = route_plan
            elif len(route_plan.route_points) > 0:
                if len(route.route_points) > 0 \
                        and abs(route.route_points[-1].time_stamp - route_plan.route_points[0].time_stamp) < 1e-9:
                    route.route_points.pop_back()
                route.route_points.extend(route_plan.route_points)

        # tv states

        tv_new_state = field_plan_resp.machine_states.get(tv_id)
        tv_route_plan = field_plan_resp.routes.get(tv_id)
        route_plan = tv_route_plan

        field_entry_ind = 0
        start_overload_ind = 0
        rp_end_overload = 0

        for i in range(len(route_plan.route_points)):
            rp = route_plan.route_points[i]
            if rp.type is RoutePointType.FIELD_ENTRY:
                field_entry_ind = i
                break

        for i in range(field_entry_ind, len(route_plan.route_points)):
            rp = route_plan.route_points[i]
            if (rp.type is RoutePointType.OVERLOADING_START
                    or rp.type is RoutePointType.OVERLOADING
                    or rp.type is RoutePointType.OVERLOADING_FINISH):
                start_overload_ind = i
                break

        for rp in reversed(route_plan.route_points):
            if (rp.type is RoutePointType.OVERLOADING_START
                    or rp.type is RoutePointType.OVERLOADING
                    or rp.type is RoutePointType.OVERLOADING_FINISH):
                rp_end_overload = rp
                break

        machine_states = self._machine_states.get(tv_name)
        prev_state = machine_states[-1]

        if field_entry_ind > 0:
            if prev_state.ts_end < route_plan.route_points[0].time_stamp - 1e-3:
                machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                            route_plan.route_points[0].time_stamp,
                                                                            pt=get_copy(route_plan.route_points[0].point()),
                                                                            waiting_time=route_plan.route_points[0].time_stamp - prev_state.ts_end,
                                                                            activity=PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE)
                self._add_state(machine_states, machine_state)

            machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                        route_plan.route_points[field_entry_ind].time_stamp,
                                                                        loc_name=field_name,
                                                                        pt=get_copy(route_plan.route_points[field_entry_ind].point()),
                                                                        transit_time=(route_plan.route_points[field_entry_ind].time_stamp - route_plan.route_points[0].time_stamp),
                                                                        activity=PlanDecoderBase.MachineActivity.TRANSIT_OFF_FIELD)
            self._add_state(machine_states, machine_state)

        rp_start_overload = rp_arrival_overload = route_plan.route_points[start_overload_ind]
        if field_entry_ind < start_overload_ind:
            rp_arrival_overload = route_plan.route_points[start_overload_ind-1]

        if start_overload_ind > 0 and field_entry_ind < start_overload_ind:
            if field_entry_ind > 0:
                machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                            rp_arrival_overload.time_stamp,
                                                                            loc_name=field_name,
                                                                            pt=get_copy(rp_arrival_overload.point()),
                                                                            activity=PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD)
                self._add_state(machine_states, machine_state)

        prev_state = machine_states[-1]
        if prev_state.ts_end < route_plan.route_points[0].time_stamp - 1e-3:
            machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                        rp_start_overload.time_stamp,
                                                                        loc_name=field_name,
                                                                        pt=get_copy(rp_start_overload.point()),
                                                                        waiting_time=rp_start_overload.time_stamp - prev_state.ts_end,
                                                                        activity=PlanDecoderBase.MachineActivity.WAITING_TO_OVERLOAD)
            self._add_state(machine_states, machine_state)

        machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                    rp_end_overload.time_stamp,
                                                                    loc_name=field_name,
                                                                    pt=get_copy(rp_end_overload.point()),
                                                                    activity=PlanDecoderBase.MachineActivity.OVERLOADING,
                                                                    overloading_machine=harv_name,
                                                                    bunker_mass=route_plan.route_points[-1].bunker_mass)
        self._add_state(machine_states, machine_state)

        machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                    tv_route_plan.route_points[-1].time_stamp,
                                                                    loc_name=tv_new_state.location_name,
                                                                    pt=get_copy(route_plan.route_points[-1].point()),
                                                                    activity=PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD)
        self._add_state(machine_states, machine_state)

        tv_overloads = self._tv_overloads.get(tv_name)
        if tv_overloads is None:
            tv_overloads = list()
            self._tv_overloads[tv_name] = tv_overloads

        overload_info = ArolibPlanGenerator.TVOverloadInfo()
        overload_info.field = field_name
        overload_info.harv = harv_name
        overload_info.silo_access = silo_access
        overload_info.ts_start = rp_start_overload.time_stamp
        overload_info.ts_end = rp_end_overload.time_stamp
        overload_info.overloaded_mass = tv_route_plan.route_points[-1].bunker_mass - tv_route_plan.route_points[0].bunker_mass
        self._add_state(tv_overloads, overload_info, remove_future_states=False)
        self._add_state(self.tv_overloads_all, overload_info, remove_future_states=False)


        # harv states

        harv_new_state = field_plan_resp.machine_states.get(harv_id)
        harv_route_plan = field_plan_resp.routes.get(harv_id)
        route_plan = harv_route_plan

        rp_end_overload = route_plan.route_points[-1]
        if harv_new_state.location_name != field_name:
            for rp in reversed(route_plan.route_points):
                if rp.isOfTypeWorking(False, True):
                    rp_end_overload = rp
                    break

        machine_states = self._machine_states.get(harv_name)
        prev_state = machine_states[-1]

        overload_start_timestamp = min(route_plan.route_points[0].time_stamp, overload_info.ts_start)

        if prev_state.ts_end < overload_start_timestamp - 1e-3:
            machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                        overload_start_timestamp,
                                                                        pt=get_copy(route_plan.route_points[0].point()),
                                                                        waiting_time=overload_start_timestamp - prev_state.ts_end,
                                                                        activity=PlanDecoderBase.MachineActivity.WAITING_TO_OVERLOAD)
            self._add_state(machine_states, machine_state)

        machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                    rp_end_overload.time_stamp,
                                                                    loc_name=field_name,
                                                                    pt=get_copy(rp_end_overload.point()),
                                                                    activity=PlanDecoderBase.MachineActivity.OVERLOADING,
                                                                    overloading_machine=tv_name)
        self._add_state(machine_states, machine_state)

        if harv_new_state.location_name is not None and harv_new_state.location_name != field_name:
            machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                        route_plan.route_points[-1].time_stamp,
                                                                        loc_name=harv_new_state.location_name,
                                                                        pt=get_copy(route_plan.route_points[-1].point()),
                                                                        activity=PlanDecoderBase.MachineActivity.TRANSIT_IN_FIELD)
            self._add_state(machine_states, machine_state)

        # field state

        field_yield_mass_total = self._fields_yield_mass.get(field_name) * plan_data.fields_yield_mass_factor.get(field_name)
        field_states = self._field_states.get(field_name)
        field_state_prev = field_states[-1]
        field_state_prev.ts_end = overload_info.ts_start

        field_state = ArolibPlanGenerator.PlanFieldState()
        field_state.ts_start = overload_info.ts_start
        field_state.ts_end = overload_info.ts_end
        field_state.state = PlanDecoderBase.FieldHarvestingState.BEING_HARVESTED
        field_state.harvested_yield_mass_start = field_state_prev.harvested_yield_mass_end
        field_state.harvested_yield_mass_end = field_state_prev.harvested_yield_mass_end + overload_info.overloaded_mass
        field_state.harvested_percentage_start = field_state_prev.harvested_percentage_end
        field_state.harvested_percentage_end = 100 * field_state.harvested_yield_mass_end / field_yield_mass_total
        field_states.append(field_state)

        field_state_prev = field_state

        field_state = ArolibPlanGenerator.PlanFieldState()
        field_state.ts_start = overload_info.ts_end
        field_state.ts_end = None
        field_state.state = PlanDecoderBase.FieldHarvestingState.BEING_HARVESTED_WAITING
        field_state.harvested_percentage_start = field_state.harvested_percentage_end = field_state_prev.harvested_percentage_end
        field_state.harvested_yield_mass_start = field_state.harvested_yield_mass_end = field_state_prev.harvested_yield_mass_end
        field_states.append(field_state)


    @staticmethod
    def __save_arolib_plan(plan_data: 'ArolibPlanGenerator.__PlanData', routes: Dict[str, Route], data_manager: GlobalDataManager):

        """ Save the current fields and routes

        Parameters
        ----------
        plan_data : __PlanData
            Plan data
        routes : Dict[str, Route]
            Machine routes: {machine_object_name: route}
        data_manager : GlobalDataManager
            Data manager
        """

        routes_v = RouteVector()
        for route in routes.values():
            routes_v.append(route)
        pseudo_field = Field()
        field_added = False
        for field_plan_resp in plan_data.field_plan_responses.values():
            field_processed = plan_data.field_plan_manager.get_plan_field_copy(field_plan_resp.plan_id)
            if field_added:
                field_processed.subfields[0].resource_points.clear()
            pseudo_field.subfields.append(field_processed.subfields[0])
            field_added = True

        minx = miny = math.inf
        maxx = maxy = -math.inf
        for sf in pseudo_field.subfields:
            for pt in sf.boundary_outer.points:
                minx = min(minx, pt.x)
                miny = min(miny, pt.y)
                maxx = max(maxx, pt.x)
                maxy = max(maxy, pt.y)
        pseudo_field.outer_boundary.points.append( Point(minx, miny) )
        pseudo_field.outer_boundary.points.append( Point(minx, maxy) )
        pseudo_field.outer_boundary.points.append( Point(maxx, maxy) )
        pseudo_field.outer_boundary.points.append( Point(maxx, miny) )
        pseudo_field.outer_boundary.points.append( Point(minx, miny) )

        machines = MachineVector()
        machines.extend( list(data_manager.machines.values()) )
        aio.save_plan_with_field_and_machines_xml(f'/tmp/plan_all_fields.xml', pseudo_field, machines,
                                                  routes_v, ProjectionType__UTM)

    @staticmethod
    def __save_arolib_partial_plan(resp: FieldPartialPlanManager.PlanResponse,
                                   field: Field,
                                   machines: List[Machine],
                                   file_name_suffix: str = None):

        """ Save the field and partial-plan routes

        Parameters
        ----------
        resp : FieldPartialPlanManager.PlanResponse
            Plan response of the field partial manager
        field : Field
            Field
        machines : List[Machine]
            Machines
        file_name_suffix : str
            File-name suffix
        """

        machines_v = MachineVector()
        machines_v.extend( machines )
        routes = RouteVector()
        for r in resp.routes.values():
            routes.append(r)
        if file_name_suffix is None or file_name_suffix == '':
            file_name = f'/tmp/plan_partial_field_{field.id}.xml'
        else:
            file_name = f'/tmp/plan_partial_field_{field.id}_{file_name_suffix}.xml'
        aio.save_plan_with_field_and_machines_xml(file_name, field, machines_v,
                                                  routes, ProjectionType__UTM)

    @staticmethod
    def __init_field_plan(plan_data: 'ArolibPlanGenerator.__PlanData', field_name: str, harv_name: str) \
            -> FieldPartialPlanManager.PlanResponse:

        """ Plan the field operation initialization for the given field and harvester

        Parameters
        ----------
        plan_data : __PlanData
            [in, out] Plan data
        field_name : str
            Field object name
        harv_name : str
            Harvester object name

        Returns
        ----------
        plan_manager_resp : FieldPartialPlanManager.PlanResponse
            Plan response of the field partial manager
        """

        field = plan_data.fields.get(field_name)
        machine = plan_data.harvesters.get(harv_name)
        ofi = get_copy(plan_data.outfield_info_base.get(field_name))
        ArolibPlanGenerator.__update_arrival_data(plan_data, field_name, field, harv_name, machine, ofi)
        return plan_data.field_plan_manager.init_plan(field=field,
                                                      machine=machine,
                                                      machine_state=plan_data.machine_states.get(harv_name),
                                                      outfield_info=ofi,
                                                      planning_settings=plan_data.field_planning_settings.get(field_name))

    @staticmethod
    def __update_arrival_data(plan_data: 'ArolibPlanGenerator.__PlanData',
                              field_name: str,
                              field: Field,
                              machine_name: str,
                              machine: Machine,
                              outfield_info: OutFieldInfo):

        """ Update the (OutFieldInfo) arrival data for a machine and a field based on the current machine state

        Parameters
        ----------
        plan_data : __PlanData
            Plan data
        field_name : str
            Field object name
        field : Field
            Field
        machine_name : str
            Machine object name
        machine : Machine
            Machine
        outfield_info : OutFieldInfo
            [in, out] Object to be updated holding the information related to out-of-field activities (e.g., transit)
        """

        machine_state: MachineState = plan_data.machine_states.get(machine_name)

        if machine_state.location_name == field_name:
            return

        dict1 = plan_data.outfield_transit_distances.get(machine_state.location_name)
        assert dict1 is not None, f'Invalid current machine location {machine_state.location_name}: ' \
                                  f'no travel distances starting from it'

        fap_ind = plan_data.harv_field_entry_points.get(machine_name)
        if fap_ind is not None:
            fap_ind = fap_ind.get(field_name)

        for ifap, fap in enumerate(field.subfields[0].access_points):

            if fap_ind is not None and ifap != fap_ind:
                continue

            fap_name = get_field_access_location_name(field.id, ifap)

            d = dict1.get(fap_name)
            if d is None:
                continue

            ad = ArrivalData()
            ad.fieldAccessPointId = fap.id
            ad.machineId = machine.id

            tc = TravelCosts()
            tc.time = d / machine.calcSpeed(machine_state.bunker_mass)
            tc.distance = d
            ad.arrivalCosts = tc
            outfield_info.add_arrivalCosts(ad)

    @staticmethod
    def __add_out_field_route_to_field(machine: Machine, route: Route, out_field_route_planner: OutFieldRoutePlanner):

        """ Adds the route segment corresponding to out-of-field transit to the given route

        Parameters
        ----------
        machine : Machine
            Machine
        route : Route
            [in, out] Route to be updated
        out_field_route_planner : OutFieldRoutePlanner
            Route planner used to plan the out-of-field route segments
        """

        if route is None or len(route.route_points) == 0:
            return
        ind_field_entry = None
        for i, rp in enumerate(route.route_points):
            if rp.type is RoutePointType.FIELD_ENTRY:
                ind_field_entry = i
                break
        if ind_field_entry == 0 or ind_field_entry is None:
            return

        rp0: RoutePoint = route.route_points[0]
        rp1: RoutePoint = route.route_points[ind_field_entry]
        ref_rp = get_copy(rp0)
        ref_rp.type = RoutePointType.TRANSIT_OF

        route_init = out_field_route_planner.get_route(rp0, rp1, machine, ref_rp, machine.id, rp0.type, rp1.type)
        if len(route_init.route_points) < 3:
            return

        time_diff = rp1.time_stamp - route_init.route_points[-1].time_stamp

        if abs(time_diff) > 1e-6:
            delta_time = rp1.time_stamp - rp0.time_stamp
            delta_time_init = route_init.route_points[-1].time_stamp - rp0.time_stamp
            factor = delta_time / delta_time_init
            for rp in route_init.route_points:
                dt = rp.time_stamp - rp0.time_stamp
                rp.time_stamp = rp0.time_stamp + factor * dt

        route_init.route_points[0] = rp0
        route_init.route_points[-1] = rp1
        route_init.route_points.extend( route.route_points[ind_field_entry+1:] )
        route.route_points = route_init.route_points

    @staticmethod
    def __init_plan_data(problem: Problem,
                         data_manager: GlobalDataManager,
                         machine_initial_states: Dict[int, MachineState],
                         plan_decoder: PlanDecoderBase) \
            -> 'ArolibPlanGenerator.__PlanData':
        plan_data = ArolibPlanGenerator.__PlanData()

        for f_id in data_manager.fields.keys():
            field_name = get_field_location_name(f_id)
            plan_data.fields[field_name] = data_manager.get_field_with_silos(f_id)

        for m_id, m in data_manager.machines.items():
            if m.machinetype is MachineType.HARVESTER:
                plan_data.harvesters[get_harvester_name(m_id)] = m
            elif m.machinetype is MachineType.OLV:
                plan_data.tvs[get_tv_name(m_id)] = m

        for s_id, s in data_manager.silos.items():
            plan_data.silos[get_silo_location_name(s_id)] = s

        plan_data.outfield_transit_distances = ArolibPlanGenerator.__init_outfield_transit_distances(problem)
        ArolibPlanGenerator.__init_outfield_info_base(problem, data_manager, plan_data)
        ArolibPlanGenerator.__init_overloads_info(plan_decoder, plan_data)
        plan_data.field_planning_settings = ArolibPlanGenerator.__init_field_planning_settings(problem)
        ArolibPlanGenerator.__init_machine_states(machine_initial_states, plan_data)
        return plan_data

    @staticmethod
    def __init_machine_states(machine_initial_states: Dict[int, MachineState], plan_data: 'ArolibPlanGenerator.__PlanData'):

        """ Initialize the machine states

        Parameters
        ----------
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        plan_data : __PlanData
            [in, out] Plan data
        """

        plan_data.machine_states = dict()
        for machines in [plan_data.harvesters, plan_data.tvs]:
            for machine_name, machine in machines.items():
                state = machine_initial_states.get(machine.id)
                assert state is not None, f'No initial state for machine {machine_name}'
                state = deepcopy(state)
                if state.location_name is None or len(state.location_name) == 0:
                    state.location_name = get_machine_initial_location_name(machine_name)
                plan_data.machine_states[machine_name] = state

    @staticmethod
    def __init_field_planning_settings(problem: Problem) -> Dict[str, PlanningSettings]:

        """ Get the initial planning setting for each field based on the problem's fluent (initial) values

        Parameters
        ----------
        problem : Problem
            Problem

        Returns
        ----------
        field_plannng_settings : Dict[str, PlanningSettings]
            Planning settings for all fields: {field_object_name: planning_settings}
        """

        field_planning_settings = dict()
        field_area_per_yield_mass = problem.fluent(fn.field_area_per_yield_mass.value)
        fields = problem.objects(upt.Field)
        for field in fields:
            planning_settings = PlanningSettings()
            m2_kg = float(problem.initial_value(field_area_per_yield_mass(field)).constant_value())
            if m2_kg < 1e-9:
                continue
            planning_settings.avg_mass_per_area_t_ha = Kg_sqrm2t_ha(1/m2_kg)
            field_planning_settings[field.name] = planning_settings
        return field_planning_settings

    @staticmethod
    def __init_outfield_transit_distances(problem: Problem) -> Dict[str, Dict[str, float]]:

        """ Get the transit distances between locations based on the problem's fluent (initial) values

        Parameters
        ----------
        problem : Problem
            Problem

        Returns
        ----------
        transit_distances : Dict[str, Dict[str, float]]
            Planning settings for all fields: {loc_from_object_name, {loc_to_object_name, distance} }
        """

        outfield_transit_distances: Dict[str, Dict[str, float]] = dict()

        transit_distance_fap_fap = problem.fluent(fn.transit_distance_fap_fap.value)
        transit_distance_fap_sap = problem.fluent(fn.transit_distance_fap_sap.value)
        transit_distance_sap_fap = problem.fluent(fn.transit_distance_sap_fap.value)

        faps = problem.objects(upt.FieldAccess)
        for fap in faps:
            faps2 = problem.objects(upt.FieldAccess)
            for fap2 in faps2:
                if fap is fap2:
                    continue
                d = float(problem.initial_value(transit_distance_fap_fap(fap, fap2)).constant_value())
                if d < -1e-9:
                    continue
                dict1 = outfield_transit_distances.get(fap.name)
                if dict1 is None:
                    dict1 = dict()
                    outfield_transit_distances[fap.name] = dict1
                dict1[fap2.name] = d

            silo_distances_1 = list()
            silo_distances_2 = list()

            saps = problem.objects(upt.SiloAccess)
            for sap in saps:
                silo_name = get_silo_name_from_silo_access_location_name(sap.name)

                d = float(problem.initial_value(transit_distance_fap_sap(fap, sap)).constant_value())
                if d < -1e-9:
                    continue
                dict1 = outfield_transit_distances.get(fap.name)
                if dict1 is None:
                    dict1 = dict()
                    outfield_transit_distances[fap.name] = dict1
                dict1[sap.name] = d
                silo_distances_1.append((silo_name, d))

                d = float(problem.initial_value(transit_distance_sap_fap(sap, fap)).constant_value())
                if d < -1e-9:
                    continue
                dict1 = outfield_transit_distances.get(sap.name)
                if dict1 is None:
                    dict1 = dict()
                    outfield_transit_distances[sap.name] = dict1
                dict1[fap.name] = d
                silo_distances_2.append((silo_name, d))

            if len(silo_distances_1) > 0:
                silo_distances_1.sort(key=lambda x: x[1])
                outfield_transit_distances[fap.name][silo_distances_1[0][0]] = silo_distances_1[0][1]

            if len(silo_distances_2) > 0:
                silo_distances_2.sort(key=lambda x: x[1])
                dict1 = outfield_transit_distances.get(silo_distances_2[0][0])
                if dict1 is None:
                    dict1 = dict()
                    outfield_transit_distances[silo_distances_2[0][0]] = dict1
                dict1[fap.name] = silo_distances_2[0][1]

        transit_distance_init_fap = problem.fluent(fn.transit_distance_init_fap.value)
        transit_distance_init_sap = problem.fluent(fn.transit_distance_init_sap.value)

        init_locs = problem.objects(upt.MachineInitLoc)
        for init_loc in init_locs:
            faps = problem.objects(upt.FieldAccess)
            for fap in faps:
                d = float(problem.initial_value(transit_distance_init_fap(init_loc, fap)).constant_value())
                if d < -1e-9:
                    continue
                dict1 = outfield_transit_distances.get(init_loc.name)
                if dict1 is None:
                    dict1 = dict()
                    outfield_transit_distances[init_loc.name] = dict1
                dict1[fap.name] = d

            saps = problem.objects(upt.SiloAccess)
            for sap in saps:
                d = float(problem.initial_value(transit_distance_init_sap(init_loc, sap)).constant_value())
                if d < -1e-9:
                    continue
                dict1 = outfield_transit_distances.get(init_loc.name)
                if dict1 is None:
                    dict1 = dict()
                    outfield_transit_distances[init_loc.name] = dict1
                dict1[sap.name] = d

        return outfield_transit_distances

    @staticmethod
    def __init_outfield_info_base(problem: Problem, data_manager: GlobalDataManager, plan_data: 'ArolibPlanGenerator.__PlanData'):

        """ Initialize the base out-field-information in plan_data.

        Parameters
        ----------
        problem : Problem
            Problem
        data_manager : GlobalDataManager
            Data manager
        plan_data : __PlanData
            [in, out] Plan data
        """

        ofis = dict()
        plan_data.outfield_info_base = ofis

        harv_transit_speed_empty = problem.fluent(fn.harv_transit_speed_empty.value)
        tv_transit_speed_empty = problem.fluent(fn.tv_transit_speed_empty.value)
        tv_transit_speed_full = problem.fluent(fn.tv_transit_speed_full.value)

        def __get_machine_speed(m: Machine, bunker_state: int) -> Optional[float]:
            try:
                if bunker_state == 0:
                    td.machineBunkerState = MachineBunkerState.MACHINE_EMPTY
                    if m.machinetype is MachineType.HARVESTER:
                        m_obj = problem.object( get_harvester_name(m.id) )
                        return float(problem.initial_value(harv_transit_speed_empty(m_obj)).constant_value())
                    elif m.machinetype is MachineType.OLV:
                        m_obj = problem.object( get_tv_name(m.id) )
                        return float(problem.initial_value(tv_transit_speed_empty(m_obj)).constant_value())
                elif m.machinetype is MachineType.HARVESTER:
                    return None
                else:
                    m_obj = problem.object( get_tv_name(m.id) )
                    return float(problem.initial_value(tv_transit_speed_full(m_obj)).constant_value())
            except:
                return None

        for field_name, field in plan_data.fields.items():
            ofi = OutFieldInfo()
            ofis[field_name] = ofi

            if len(field.subfields) <= 0:
                continue
            for ifap, fap in enumerate(field.subfields[0].access_points):
                fap_name = get_field_access_location_name(field.id, ifap)
                dict_fap: Dict = plan_data.outfield_transit_distances.get(fap_name)
                if dict_fap is None:
                    continue
                for res_p in field.subfields[0].resource_points:
                    silo_name = get_silo_location_name(res_p.id)

                    d = dict_fap.get(silo_name)
                    if d is not None:
                        td = TravelData()
                        td.fieldAccessPointId = fap.id
                        td.resourcePointId = res_p.id
                        for m in data_manager.machines.values():
                            td.machineId = m.id
                            for state in range(2):
                                speed = __get_machine_speed(m, state)
                                if speed is None:
                                    continue
                                tc = TravelCosts()
                                tc.time = d / speed
                                tc.distance = d
                                td.travelCosts = tc
                                ofi.add_FAP2RP(td)
                    dict_sap: Dict = plan_data.outfield_transit_distances.get(silo_name)
                    if dict_sap is None:
                        continue
                    d = dict_sap.get(fap_name)
                    if d is None:
                        continue
                    td = TravelData()
                    td.fieldAccessPointId = fap.id
                    td.resourcePointId = res_p.id
                    for m in data_manager.machines.values():
                        td.machineId = m.id
                        for state in range(2):
                            speed = __get_machine_speed(m, state)
                            if speed is None:
                                continue
                            tc = TravelCosts()
                            tc.time = d / speed
                            tc.distance = d
                            td.travelCosts = tc
                            ofi.add_RP2FAP(td)

    @staticmethod
    def __init_overloads_info(plan_decoder: PlanDecoderBase, plan_data: 'ArolibPlanGenerator.__PlanData'):

        """ Initialize the field turns and overloads' information in plan_data.

        Parameters
        ----------
        plan_decoder : PlanDecoderBase
            Plan decoder
        plan_data : __PlanData
            [in, out] Plan data
        """

        harvs_fields_tmp = dict()
        harvs_tvs_tmp = dict()
        for field_name, overloads in plan_decoder.field_overloads.items():
            if len(overloads.overloads) == 0:
                continue

            plan_data.fields_overloads_count[field_name] = len(overloads.overloads)

            if overloads.entry_point is not None:
                harv_field_entry_point = plan_data.harv_field_entry_points.get(overloads.harv)
                if harv_field_entry_point is None:
                    harv_field_entry_point = dict()
                    plan_data.harv_field_entry_points[overloads.harv] = harv_field_entry_point
                harv_field_entry_point[field_name] = get_field_access_id_from_location_name(overloads.entry_point)[1]

            field_turns = harvs_fields_tmp.get(overloads.harv)
            if field_turns is None:
                field_turns = list()
                harvs_fields_tmp[overloads.harv] = field_turns
            field_turns.append((field_name, overloads.overloads[0]))

            tv_turns = harvs_tvs_tmp.get(overloads.harv)
            if tv_turns is None:
                tv_turns = list()
                harvs_tvs_tmp[overloads.harv] = tv_turns
            for overload in overloads.overloads:
                tv_turns.append(overload)

        for harv_name, field_turns in harvs_fields_tmp.items():
            field_turns.sort(key=lambda x: x[1].ts_start)
            plan_data.harv_field_turns[harv_name] = list(x[0] for x in field_turns)

        for harv_name, tv_turns in harvs_tvs_tmp.items():
            tv_turns.sort(key=lambda x: x.ts_start)
            plan_data.harv_tv_turns[harv_name] = list(x.tv for x in tv_turns)

        for tv_name, unloads in plan_decoder.tv_unloads.items():
            overloads_info = list()
            plan_data.tv_overloads[tv_name] = overloads_info
            for unload in unloads:
                if unload.overload_info is not None:
                    break
                overload_info = ArolibPlanGenerator.__TVOverloadInfo()
                overload_info.harv = None
                overload_info.silo_access = unload.silo_access
                overloads_info.append(overload_info)

        for tv_name, overloads in plan_decoder.tv_overloads.items():
            overloads_info = plan_data.tv_overloads.get(tv_name)
            for overload in overloads:
                overload_info = ArolibPlanGenerator.__TVOverloadInfo()
                overload_info.harv = overload.harv
                overload_info.silo_access = overload.silo_access
                overloads_info.append(overload_info)

    def __send_tv_to_silo(self,
                          plan_data: 'ArolibPlanGenerator.__PlanData',
                          out_field_route_planner: OutFieldRoutePlanner,
                          tv_name: str,
                          machine: Machine,
                          silo_access_name: str) -> bool:

        """ Plan the transit to a silo and unload of a transport vehicle, updating the machine and silo states and the machine route

        Parameters
        ----------
        plan_data : __PlanData
            [in, out] Plan data
        out_field_route_planner : OutFieldRoutePlanner
            Route planner used to plan the out-of-field route segments
        tv_name : str
            Transport-vehicle object name
        machine : Machine
            Transport-vehicle
        silo_access_name : str
            Object name of the silo access where the machine will unload

        Returns
        ----------
        success : bool
            True on success
        """

        print(f'\tSending tv {tv_name} to silo access point {silo_access_name}...')

        tv_state: MachineState = plan_data.machine_states.get(tv_name)
        pt_access_point = ArolibPlanGenerator.__get_location_position(plan_data, silo_access_name)
        ref_rp = RoutePoint()
        ref_rp.time_stamp = tv_state.timestamp
        ref_rp.bunker_mass = tv_state.bunker_mass

        route_of = out_field_route_planner.get_route(tv_state.position,
                                                     pt_access_point,
                                                     machine,
                                                     ref_rp,
                                                     machine.id,
                                                     end_rp_type=RoutePointType.RESOURCE_POINT)

        if route_of is None or len(route_of.route_points) == 0:
            warnings.warn('[ERROR] Error obtaining route for out-of-field transit')
            return False

        unload_duration = tv_state.bunker_mass / machine.unloading_speed_mass

        last_rp = get_copy(route_of.route_points[-1])

        tv_overloads = self._tv_overloads.get(tv_name)
        if tv_overloads is None:
            tv_overloads = list()
            self._tv_overloads[tv_name] = tv_overloads

        overload_info = None if len(tv_overloads) == 0 else tv_overloads[-1]

        unload_info = PlanDecoderBase.TVUnloadInfo()
        unload_info.ts_start = last_rp.time_stamp
        unload_info.ts_end = last_rp.time_stamp + unload_duration
        unload_info.silo_access = silo_access_name
        unload_info.overload_info = overload_info
        unloads = self._tv_unloads.get(tv_name)
        if unloads is None:
            self._tv_unloads[tv_name] = [unload_info]
        else:
            unloads.append(unload_info)

        silo_name = get_silo_name_from_silo_access_location_name(silo_access_name)
        unload_info = PlanDecoderBase.SiloUnloadInfo()
        unload_info.ts_start = last_rp.time_stamp
        unload_info.ts_end = last_rp.time_stamp + unload_duration
        unload_info.silo_access = silo_access_name
        unload_info.tv = tv_name
        unload_info.unloaded_mass = last_rp.bunker_mass
        unloads = self._silo_unloads.get(silo_name)
        if unloads is None:
            self._silo_unloads[silo_name] = [unload_info]
        else:
            unloads.append(unload_info)


        # tv states

        machine_states = self._machine_states.get(tv_name)
        prev_state = machine_states[-1]

        if prev_state.ts_end < route_of.route_points[0].time_stamp - 1e-3:
            activity = PlanDecoderBase.MachineActivity.WAITING_TO_UNLOAD
            if last_rp.time_stamp > route_of.route_points[0].time_stamp + 1e-3:
                activity = PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE
            machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                        route_of.route_points[0].time_stamp,
                                                                        pt=get_copy(route_of.route_points[0].point()),
                                                                        waiting_time=route_of.route_points[0].time_stamp - prev_state.ts_end,
                                                                        activity=activity)
            self._add_state(machine_states, machine_state)

        if last_rp.time_stamp > route_of.route_points[0].time_stamp + 1e-3:
            machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                        last_rp.time_stamp,
                                                                        loc_name=silo_access_name,
                                                                        pt=get_copy(last_rp.point()),
                                                                        transit_time=(last_rp.time_stamp - route_of.route_points[0].time_stamp),
                                                                        activity=PlanDecoderBase.MachineActivity.TRANSIT_OFF_FIELD)
            self._add_state(machine_states, machine_state)

        machine_state = ArolibPlanGenerator.__get_new_machine_state(machine_states,
                                                                    last_rp.time_stamp + unload_duration,
                                                                    loc_name=silo_access_name,
                                                                    pt=get_copy(last_rp.point()),
                                                                    activity=PlanDecoderBase.MachineActivity.UNLOADING,
                                                                    bunker_mass=0.0)
        self._add_state(machine_states, machine_state)

        # tv route update

        last_rp.bunker_mass = 0.0
        last_rp.bunker_volume = 0.0
        last_rp.time_stamp += unload_duration

        route = self.__routes.get(tv_name)
        if route is None:
            route = route_of
            self.__routes[tv_name] = route
        else:
            route.route_points.extend(route_of.route_points)
        route.route_points.append(last_rp)

        tv_state.timestamp = last_rp.time_stamp
        tv_state.bunker_mass = last_rp.bunker_mass
        tv_state.bunker_volume = last_rp.bunker_volume
        tv_state.location_name = silo_access_name
        tv_state.position = pt_access_point

        return True

    @staticmethod
    def __get_location_position(plan_data: 'ArolibPlanGenerator.__PlanData', loc_name: str) -> Point:

        """ Get the position (point) of a location

        Parameters
        ----------
        plan_data : __PlanData
            Plan data
        loc_name : str
            Location object name

        Returns
        ----------
        position : Point
            Position (point) of the location
        """

        _id_ind = get_field_access_id_from_location_name(loc_name)
        if _id_ind is not None:
            field_name = get_field_location_name(_id_ind[0])
            field = plan_data.fields.get(field_name)
            return field.subfields[0].access_points[_id_ind[1]]

        _id_ind = get_silo_access_id_from_location_name(loc_name)
        if _id_ind is not None:
            silo_name = get_silo_location_name(_id_ind[0])
            silo: SiloExtended = plan_data.silos.get(silo_name)
            return silo.access_points[_id_ind[1]]
        raise ValueError(f'The location {loc_name} does not correspond to a field/silo access point')

    def gives_precise_machine_positions(self) -> bool:
        """ Check if the get_machine_state_at returns precise machine positions

        Returns
        ----------
        ok : bool
            True if the get_machine_state_at returns precise machine positions
        """
        return True

    def get_machine_state_at(self, machine_name: str, timestamp: float, ind_start: int = 0) \
            -> Union[Tuple[MachineState, int], Tuple[None, None]]:
        """ Get the interpolated state of a machine corresponding at a given timestamp

        The state values (position, bunker_mass, etc.) of the machine will be computed (interpolated) based on the known plan states of the machine before and after the given timestamp

        Parameters
        ----------
        machine_name : str
            Machine object name
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state where the search will start. If not known, set 0.

        Returns
        ----------
        machine_state : MachineState
            Machine state (None on error)
        ind : int
            Index of the last state before the given timestamp (for future search)
        """

        plan_state_ind = self.get_machine_plan_state_at(machine_name, timestamp, 0)
        if plan_state_ind is None:
            return None, None
        plan_state = plan_state_ind[0]

        state = MachineState()
        state.timestamp = timestamp
        state.timestamp_free = timestamp
        state.location_name = plan_state.loc_start
        state.bunker_mass = 0.0
        state.bunker_volume = 0.0

        if machine_name in self.harvester_names_map.keys():
            state.overloading_machine_id = get_tv_id_from_name(plan_state.overloading_machine_name)
        else:
            state.overloading_machine_id = get_harvester_id_from_name(plan_state.overloading_machine_name)

        if ind_start is None:
            ind_start = -1

        route = self.__routes.get(machine_name)
        if route is None:
            return None, None
        rp, ind_ret = calc_route_point(route.route_points, timestamp, ind_start)

        state.position = rp.point()
        state.bunker_mass = rp.bunker_mass
        state.bunker_volume = rp.bunker_volume

        if timestamp >= plan_state.ts_end:
            state.location_name = plan_state.loc_end
            return state, ind_ret

        if rp.type is RoutePointType.TRANSIT_OF:
            state.location_name = None
        else:
            state.location_name = plan_state.loc_start

        return state, ind_ret
