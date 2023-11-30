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

import copy
import math
from typing import Optional

try:
    from exposed_arolib.types import *
    from exposed_arolib.io import *
    from exposed_arolib import planning as aro_planning
    from exposed_arolib.planning import *
    from exposed_arolib.geometry import *
    from exposed_arolib.io import save_outfield_info_xml, save_graph_xml
    from up_interface.problem_encoder.names_helper import *
    from util_arolib.types_wrapper import *
    from route_planning.field_route_planning import PlanningSettings, FieldRoutePlanner

    class FieldPartialPlanManager:
        """ Manager for partial infield route planning """

        NO_PLAN_ID: int = -1
        """ Id corresponding to 'no plan' """

        DEF_UNLOADING_SPEED_MASS = 100.0
        """ Default unloading speed [kg/s] """

        DEF_UNLOADING_SPEED_VOLUME = 100.0
        """ Default unloading speed [m³/s] """

        class PlanResponse:
            """Class holding the plan response data"""

            def __init__(self):
                """Class initializer"""

                self.plan_id: int = FieldPartialPlanManager.NO_PLAN_ID
                """Plan Id"""

                self.finished_field: bool = False
                """Flag stating if the harvester finished harvesting the field after the corresponding partial plan"""

                self.machine_states: Dict[int, MachineState] = dict()
                """Resulting states of the machines participating in the partial plan"""

                self.routes: Dict[int, Route] = dict()
                """Resulting (partial) routes of the machines participating in the partial plan"""

        class __BasePlanData:
            """Class holding the base data used by the planner"""

            def __init__(self):
                self.processed_field: Optional[Field] = None
                """Field (including processed geometries)"""

                self.machine: Optional[Machine] = None
                """Transport vehicle performing the overload"""

                self.base_route: Route = Route()
                """Base route of the corresponding field plan"""

                self.graph: DirectedGraph = DirectedGraph()
                """Graph of the corresponding field plan"""

        class __PlanData:
            """Class holding the data used by the planner"""

            def __init__(self):
                self.timestamp_finish: float = 0.0
                """Finish timestamp [s]"""

                self.base_plan: FieldPartialPlanManager.__BasePlanData = None
                """Holds the base data used by the planner"""

                self.parent_plan: FieldPartialPlanManager.__PlanData = None
                """Hold the pan data of the parent plan (i.e., the base plan (field init) or last overload)"""

                self.last_base_route_point_idx: int = 0
                """Index of the point of the base route corresponding to the last harvested route point"""

        def __init__(self):
            """Class initializer"""

            self.__last_base_plan_id: int = FieldPartialPlanManager.NO_PLAN_ID
            """Used to keep track of used base-plan ids and assign non repeated ones"""

            self.__last_plan_id: int = FieldPartialPlanManager.NO_PLAN_ID
            """Used to keep track of used plan ids and assign non repeated ones"""

            self.__base_plans: Dict[int, FieldPartialPlanManager.__BasePlanData] = dict()
            """Holds the computed base plans: {base_plan_id: base_plan_data}"""

            self.__plans: Dict[int, FieldPartialPlanManager.__PlanData] = dict()
            """Holds the computed plans: {plan_id: plan_data}"""

            self.__planners: Dict[int, FieldRoutePlanner] = dict()
            """Holds the infield route planners used for each field: {field_id: planner}"""

        def get_plan_field_copy(self, plan_id: int) -> Optional[Field]:
            """Get a copy of the field corresponding to a given plan_id

            Parameters
            ----------
            plan_id : int
                Plan id

            Returns
            ----------
            field_copy : Field | None
                Copy of the field (None on error, e.g., if plan with the given id does not exist)

            """
            base_plan_data = self.__get_base_plan_data(plan_id)
            if base_plan_data is None:
                return None
            return FieldPartialPlanManager.__get_base_plan_field_copy(base_plan_data)

        def get_plan_base_route_copy(self, plan_id: int) -> Optional[Route]:
            """Get a copy of the base route corresponding to a given plan_id

            Parameters
            ----------
            plan_id : int
                Plan id

            Returns
            ----------
            base_route_copy : Route | None
                Copy of the base-route (None on error, e.g., if plan with the given id does not exist)

            """
            base_plan_data = self.__get_base_plan_data(plan_id)
            if base_plan_data is None:
                return None
            return FieldPartialPlanManager.__get_base_plan_base_route_copy(base_plan_data)

        def get_plan_base_graph_copy(self, plan_id: int) -> Optional[DirectedGraph]:
            """Get a copy of the base graph corresponding to a given plan_id

            Parameters
            ----------
            plan_id : int
                Plan id

            Returns
            ----------
            graph_copy : DirectedGraph | None
                Copy of the graph (None on error, e.g., if plan with the given id does not exist)

            """
            base_plan_data = self.__get_base_plan_data(plan_id)
            if base_plan_data is None:
                return None
            return FieldPartialPlanManager.__get_base_plan_base_graph_copy(base_plan_data)

        def init_plan(self,
                      field: Field,
                      machine: Machine,
                      machine_state: MachineState,
                      outfield_info: OutFieldInfo,
                      planning_settings: PlanningSettings) -> Optional[PlanResponse]:
            """Initialize a plan for the given field and harvester, i.e., drive the machine to the field, generate the field geometric representation, create the base route and graph, etc.

            Parameters
            ----------
            field : Field
                Field to be harvested
            machine : Machine
                Harvester
            machine_state : MachineState
                Current state of the harvester
            outfield_info : OutFieldInfo
                Holds the information related to out-of-field activities (e.g., transit)
            planning_settings : PlanningSettings
                Planing settings

            Returns
            ----------
            plan_response : PlanResponse | None
                Plan response (None on error)
            """

            # print(f'FieldPartialPlanManager: Initializing plan for field {field.id} and machine {machine.id}...')

            base_plan_data = self.__plan_base(field,
                                              machine,
                                              machine_state,
                                              outfield_info,
                                              planning_settings)
            if base_plan_data is None:
                return None

            machine_states_aro: Dict[int, MachineDynamicInfo] = dict()
            machine_states_aro[base_plan_data.machine.id] = machine_state.to_aro_machine_state()

            graph = aro_planning.get_copy(base_plan_data.graph)
            routes = dict()
            plan_info = PlanGeneralInfo()

            planner = self.__get_planner(base_plan_data.processed_field.id)
            aro_resp = planner.plan_field_from_base(base_plan_data.processed_field,
                                                    {base_plan_data.machine.id: base_plan_data.machine},
                                                    machine_states_aro,
                                                    outfield_info,
                                                    {base_plan_data.machine.id: base_plan_data.base_route},
                                                    graph,
                                                    None,
                                                    planning_settings,
                                                    base_plan_data.processed_field,
                                                    routes,
                                                    plan_info)
            if aro_resp.isError():
                print(f'[ERROR]: error executing route planning: {aro_resp.msg}')
                return None

            if base_plan_data.machine.id not in routes.keys():
                print(f'[ERROR]: error retrieving route')
                return None
            route = routes[base_plan_data.machine.id]
            ind_start = -1
            ind = 0
            while ind < len(route.route_points):
                rp: RoutePoint = route.route_points[ind]
                if rp.isOfTypeWorking(False, True):
                    ind_start = ind
                    break
                ind = ind + 1
            if ind_start < 0:
                print(f'[ERROR]: error obtaining initial segment from route')
                return None

            route.route_points = route.route_points[0: ind_start + 1]

            plan_data = FieldPartialPlanManager.__PlanData()
            plan_data.base_plan = base_plan_data
            plan_data.parent_plan = None
            plan_data.last_base_route_point_idx = 0
            plan_data.timestamp_finish = route.route_points[-1].time_stamp

            self.__last_base_plan_id = self.__last_base_plan_id + 1
            self.__base_plans[self.__last_base_plan_id] = base_plan_data
            self.__last_plan_id = self.__last_plan_id + 1
            self.__plans[self.__last_plan_id] = plan_data

            machine_state = MachineState()
            machine_state.timestamp = route.route_points[-1].time_stamp
            machine_state.position = Point(route.route_points[-1])
            machine_state.bunker_mass = 0.0
            machine_state.bunker_volume = 0.0
            machine_state.location_name = get_field_location_name(field.id)

            resp = FieldPartialPlanManager.PlanResponse()
            resp.plan_id = self.__last_plan_id
            resp.finished_field = False
            resp.machine_states = {machine.id: machine_state}
            resp.routes = {machine.id: route}

            return resp

        def plan_overload(self,
                          plan_id: int,
                          machine: Machine,
                          machine_state: MachineState,
                          outfield_info: OutFieldInfo,
                          planning_settings: PlanningSettings) -> Optional[PlanResponse]:
            """Plan an overload starting from state generated by a given plan.

            Parameters
            ----------
            plan_id : int
                Id of the plan from which the overload will be planned (obtained from previous plan responses of init_plan and plan_overload)
            machine : Machine
                Transport vehicle
            machine_state : MachineState
                Current state of the transport vehicle
            outfield_info : OutFieldInfo
                Holds the information related to out-of-field activities (e.g., transit)
            planning_settings : PlanningSettings
                Planing settings

            Returns
            ----------
            plan_response : PlanResponse | None
                Plan response (None on error)
            """

            # print(f'FieldPartialPlanManager: Planning overload for plan {plan_id} and tv {machine.id}...')

            plan_data: FieldPartialPlanManager.__PlanData = self.__get_plan_data(plan_id)
            if plan_data is None:
                return None
            base_plan_data: FieldPartialPlanManager.__BasePlanData = self.__get_base_plan_data(plan_id)
            if base_plan_data is None:
                return None
            if plan_data.last_base_route_point_idx + 1 >= len(base_plan_data.base_route.route_points):
                print(f'[ERROR]: no more overload activities to plan')
                return None
            if machine.bunker_mass <= 0:
                print(f'[ERROR]: the machine has no bunker capacity')
                return None

            planning_base_route = Route()
            base_plan_data.base_route.copyToWithoutPoints(planning_base_route, True)
            planning_base_route.route_points = base_plan_data.base_route.route_points[
                                               plan_data.last_base_route_point_idx:]

            machine_states_aro: Dict[int, MachineDynamicInfo] = dict()
            # olv state
            machine_states_aro[machine.id] = machine_state.to_aro_machine_state()
            # harvester state
            mdi_harv = MachineDynamicInfo()
            mdi_harv.position = Point(planning_base_route.route_points[0])
            mdi_harv.bunkerMass = mdi_harv.bunkerVolume = 0.0
            mdi_harv.timestamp = plan_data.timestamp_finish
            machine_states_aro[base_plan_data.machine.id] = mdi_harv

            machines_aro = MachineVector()
            machines_aro.append(base_plan_data.machine)
            machines_aro.append(machine)

            graph = aro_planning.get_copy(base_plan_data.graph)

            insert_or_replace_initial_positions_in_graph(graph,
                                                         base_plan_data.processed_field.subfields[0],
                                                         machines_aro,
                                                         MachineTypeVector(),
                                                         dict_to_arolib_map(machine_states_aro,
                                                                            MachineId2DynamicInfoMap),
                                                         outfield_info,
                                                         base_plan_data.processed_field.outer_boundary,
                                                         True,
                                                         True,
                                                         False)

            # update the graph timestamps corresponding to the base route until one index before last_base_route_point_idx
            # the timestamp for last_base_route_point_idx must not be adjusted since the route planner adjusts it automatically based on the machine timestamp
            self.__update_graph_timestamps(graph, base_plan_data, plan_data, machine_state.timestamp)

            routes = dict()
            plan_info = PlanGeneralInfo()

            planning_settings_ed = copy.deepcopy(planning_settings)
            planning_settings_ed.num_overload_activities = 1
            planning_settings_ed.max_worked_mass = -1

            planner = self.__get_planner(base_plan_data.processed_field.id)
            aro_resp = planner.plan_field_from_base(base_plan_data.processed_field,
                                                    {base_plan_data.machine.id: base_plan_data.machine,
                                                     machine.id: machine},
                                                    machine_states_aro,
                                                    outfield_info,
                                                    {base_plan_data.machine.id: planning_base_route},
                                                    graph,
                                                    None,
                                                    planning_settings_ed,
                                                    base_plan_data.processed_field,
                                                    routes,
                                                    plan_info)
            if aro_resp.isError():
                print(f'[ERROR]: error executing route planning: {aro_resp.msg}')
                return None

            route_harv = routes.get(base_plan_data.machine.id)
            if route_harv is None:
                print(f'[ERROR]: error retrieving harvester route')
                return None

            route_olv = routes.get(machine.id)
            if route_olv is None:
                print(f'[ERROR]: error retrieving olv route')
                return None

            FieldPartialPlanManager.__remove_outfield_transit_from_route(routes[machine.id])
            ind = FieldPartialPlanManager.__adjust_harv_route_and_get_base_route_index(base_plan_data.base_route,
                                                                                       plan_data.last_base_route_point_idx,
                                                                                       route_harv,
                                                                                       route_olv)
            finished = (ind + 1 >= len(base_plan_data.base_route.route_points))
            if ind < 0:
                print(f'[ERROR]: error retrieving last_base_route_point_idx')
                return None

            plan_data_new = FieldPartialPlanManager.__PlanData()
            plan_data_new.base_plan = base_plan_data
            plan_data_new.parent_plan = plan_data
            plan_data_new.last_base_route_point_idx = ind
            plan_data_new.timestamp_finish = route_harv.route_points[-1].time_stamp

            self.__last_base_plan_id = self.__last_base_plan_id + 1
            self.__base_plans[self.__last_base_plan_id] = base_plan_data
            self.__last_plan_id = self.__last_plan_id + 1
            self.__plans[self.__last_plan_id] = plan_data_new

            # olv state
            rp_olv_n = route_olv.route_points[-1]
            machine_state_olv = MachineState()
            machine_state_olv.timestamp = route_olv.route_points[-1].time_stamp
            machine_state_olv.position = Point(route_olv.route_points[-1])
            machine_state_olv.bunker_mass = route_olv.route_points[-1].bunker_mass
            machine_state_olv.bunker_volume = route_olv.route_points[-1].bunker_volume
            machine_state_olv.location_name = get_field_access_location_name(base_plan_data.processed_field.id,
                                                                             FieldPartialPlanManager.__get_exit_point_idx(
                                                                                 base_plan_data.processed_field,
                                                                                 route_olv
                                                                             ))
            # harvester state
            machine_state_harv = MachineState()
            machine_state_harv.timestamp = route_harv.route_points[-1].time_stamp
            machine_state_harv.position = Point(route_harv.route_points[-1])
            machine_state_harv.bunker_mass = 0.0
            machine_state_harv.bunker_volume = 0.0
            if finished:
                machine_state_harv.location_name = get_field_access_location_name(base_plan_data.processed_field.id,
                                                                                  FieldPartialPlanManager.__get_exit_point_idx(
                                                                                      base_plan_data.processed_field,
                                                                                      route_harv
                                                                                  ))
            else:
                machine_state_harv.location_name = get_field_location_name(base_plan_data.processed_field.id)

            resp = FieldPartialPlanManager.PlanResponse()
            resp.plan_id = self.__last_plan_id
            resp.finished_field = finished
            resp.machine_states = {machine.id: machine_state_olv, base_plan_data.machine.id: machine_state_harv}
            resp.routes = {route_olv.machine_id: route_olv, route_harv.machine_id: route_harv}

            return resp

        @staticmethod
        def __get_exit_point_idx(field: Field, route: Route) -> int:
            """Get the index of the field access point used to exit the field in the given route.

            Parameters
            ----------
            field : Field
                Field
            route : Route
                Route

            Returns
            ----------
            fap_index : int
                Index of the field access point used to exit the field (<0 on error)
            """
            last_rp = route.route_points[-1]
            min_dist = math.inf
            ind = -1
            for i, fap in enumerate(field.subfields[0].access_points):
                dist = calc_dist(fap, last_rp)
                if min_dist > dist:
                    min_dist = dist
                    ind = i
            return ind

        @staticmethod
        def __is_field_valid(field: Field) -> bool:
            """Check if the given field is valid for planning.

            Parameters
            ----------
            field : Field
                Field

            Returns
            ----------
            valid : bool
                True if valid
            """
            if field is None:
                print(f'[ERROR]: invalid field')
                return False
            if len(field.subfields) == 0:
                print(f'[ERROR]: invalid field (no subfields)')
                return False
            if len(field.subfields[0].boundary_outer.points) < 4:
                print(f'[ERROR]: invalid field (invalid boundary)')
                return False
            if len(field.subfields[0].reference_lines) == 0:
                print(f'[ERROR]: invalid field (no reference lines)')
                return False
            if len(field.subfields[0].access_points) == 0:
                print(f'[ERROR]: invalid field (no access points)')
                return False
            return True

        def __get_plan_data(self, plan_id: int) -> Optional[__PlanData]:
            """Obtain the plan data corresponding to the given plan id.

            Parameters
            ----------
            plan_id : int
                Id of the plan

            Returns
            ----------
            plan_data : __PlanData | None
                Plan data (None no plan exists for the given plan id)
            """

            plan_data = self.__plans.get(plan_id)
            if plan_data is None:
                print(f'[ERROR]: invalid plan id')
            return plan_data

        def __get_base_plan_data(self, plan_id: int) -> Optional[__BasePlanData]:
            """Obtain the base-plan data corresponding to the given plan id.

            Parameters
            ----------
            plan_id : int
                Id of the plan

            Returns
            ----------
            bse_plan_data : __BasePlanData | None
                Base-plan data (None no plan exists for the given plan id, or the plan has no base-plan)
            """
            plan_data = self.__get_plan_data(plan_id)
            if plan_data is None:
                return None
            if plan_data.base_plan is None:
                print(f'[ERROR]: no base plan data available')
            return plan_data.base_plan

        def __plan_base(self,
                        field: Field,
                        machine: Machine,
                        machine_state: MachineState,
                        outfield_info: OutFieldInfo,
                        planning_settings: PlanningSettings) -> Optional[__BasePlanData]:
            """Get the base-plan corresponding to the plan initialization for the given field and harvester, i.e., drive the machine to the field, generate the field geometric representation, create the base route and graph, etc.

            Parameters
            ----------
            field : Field
                Field to be harvested
            machine : Machine
                Harvester
            machine_state : MachineState
                Current state of the harvester
            outfield_info : OutFieldInfo
                Holds the information related to out-of-field activities (e.g., transit)
            planning_settings : PlanningSettings
                Planing settings

            Returns
            ----------
            plan_response : __BasePlanData | None
                Plan response (None on error)
            """
            if not FieldPartialPlanManager.__is_field_valid(field):
                return None
            if not machine.isOfWorkingType(False):
                print(f'[ERROR]: invalid machine')
                return None

            machine_states_aro: Dict[int, MachineDynamicInfo] = dict()
            machine_states_aro[machine.id] = machine_state.to_aro_machine_state()

            planner = self.__get_planner(field.id)

            base_plan_data = FieldPartialPlanManager.__BasePlanData()
            base_plan_data.processed_field = get_copy(field)
            base_plan_data.machine = get_copy(machine)
            base_routes = dict()

            aro_resp = planner.plan_field_base(field,
                                               {machine.id: machine},
                                               machine_states_aro,
                                               outfield_info,
                                               None,
                                               planning_settings,
                                               base_plan_data.processed_field,
                                               base_routes,
                                               base_plan_data.graph)
            if aro_resp.isError():
                print(f'[ERROR]: error executing base planning: {aro_resp.msg}')
                return None

            if machine.id not in base_routes.keys():
                print(f'[ERROR]: error retrieving base route')
                return None
            base_plan_data.base_route = base_routes[machine.id]

            return base_plan_data

        def __get_planner(self, field_id: int) -> FieldRoutePlanner:
            """Get the infield planner for a given field

            Parameters
            ----------
            field_id : int
                Field id

            Returns
            ----------
            plan_response : __BasePlanData | None
                Plan response (None on error)
            """
            planner = self.__planners.get(field_id)
            if planner is not None:
                return planner
            planner = FieldRoutePlanner()
            self.__planners[field_id] = planner
            return planner

        @staticmethod
        def __update_graph_timestamps(graph: DirectedGraph,
                                      base_plan_data: __BasePlanData,
                                      plan_data: __PlanData,
                                      tv_timestamp: float):
            """Update the graph timestamps based on the base-plan and plan (i.e., based on the state of the field
            and harvester corresponding to the given plan) and the timestamp of the transport vehicle

            Parameters
            ----------
            graph : DirectedGraph
                [in, out] Graph to be updated
            base_plan_data : __BasePlanData
                Base-plan data
            plan_data : __PlanData
                Plan data
            tv_timestamp : float
                Timestamp [s] of the transport vehicle
            """
            if plan_data is None or plan_data.last_base_route_point_idx <= 0:
                return

            if tv_timestamp > plan_data.timestamp_finish:  # the tv will not try to visit any worked points before they were worked
                reset_graph_timestamps_from_base_route(graph, base_plan_data.base_route,
                                                       0, plan_data.last_base_route_point_idx - 1, -1)
                return

            FieldPartialPlanManager.__update_graph_timestamps(graph, base_plan_data, plan_data.parent_plan,
                                                              tv_timestamp)

            original_timestamp = base_plan_data.base_route.route_points[plan_data.last_base_route_point_idx].time_stamp
            delta_time = plan_data.timestamp_finish - original_timestamp

            ind_from = 0 if plan_data.parent_plan is None else plan_data.parent_plan.last_base_route_point_idx

            update_graph_timestamps_from_base_route(graph,
                                                    base_plan_data.base_route,
                                                    delta_time,
                                                    ind_from,
                                                    plan_data.last_base_route_point_idx - 1,
                                                    -1)

        @staticmethod
        def __remove_outfield_transit_from_route(route: Route):
            """Remove the route points corresponding to transit outside the field from a route

            Parameters
            ----------
            route : Route
                [in, out] Route to be updated
            """
            ind_finish = len(route.route_points) - 1
            while ind_finish >= 0:
                rp: RoutePoint = route.route_points[ind_finish]
                if rp.type is RoutePointType.FIELD_EXIT:
                    break
                ind_finish = ind_finish - 1
            if ind_finish < 0:
                route.route_points = RoutePointVector()
            else:
                route.route_points = route.route_points[0:ind_finish + 1]

        @staticmethod
        def __adjust_harv_route_and_get_base_route_index(base_route: Route,
                                                         ind_from: int,
                                                         route_harv: Route,
                                                         route_olv: Route) -> int:
            """Adjust the planned harvester route and search the point (index) of the base-route corresponding
            to the last point harvested by the harvester in th given routes

            Parameters
            ----------
            base_route : Route
                Plan base-route
            ind_from : int
                Index of the point in the base route from which to start the search
            route_harv : Route
                Planned harvester route
            route_olv : Route
                Planned transport-vehicle route

            Returns
            ----------
            base_route_point_index : int
                Index of the point of the base-route corresponding to the last point harvested by the harvester in th given routes
            """

            for i in range(len(route_harv.route_points) - 1):
                rp: RoutePoint = route_harv.route_points[i]
                if not rp.isOfTypeWorking(True, True):
                    continue
                if calc_dist(rp, route_harv.route_points[i + 1]) > 1e-3:
                    route_harv.route_points = route_harv.route_points[i:]
                    break

            overloaded_mass = route_olv.route_points[-1].bunker_mass - route_olv.route_points[0].bunker_mass
            ind = ind_from + 1
            worked_mass_start = base_route.route_points[ind_from].worked_mass
            while ind < len(base_route.route_points):
                delta_mass = base_route.route_points[ind].worked_mass - worked_mass_start
                if delta_mass >= overloaded_mass - 1e-3:
                    break
                ind = ind + 1
            if ind + 1 >= len(base_route.route_points):  # finished -> leave route as it is
                return ind
            worked_mass_finish = base_route.route_points[ind].worked_mass

            ind_end = 0
            while ind_end < len(route_harv.route_points):
                worked_mass = route_harv.route_points[ind_end].worked_mass
                next_worked_mass = math.inf
                # if ind_end+1 < len(route_harv.route_points):
                #     next_worked_mass = route_harv.route_points[ind_end+1].worked_mass
                if abs(worked_mass - worked_mass_finish) < 1e-3 < abs(next_worked_mass - worked_mass):
                    break
                ind_end = ind_end + 1
            if ind_end + 1 >= len(route_harv.route_points):
                return len(base_route.route_points)
            route_harv.route_points = route_harv.route_points[0:ind_end + 1]
            return ind

        @staticmethod
        def __get_base_plan_field_copy(base_plan: __BasePlanData) -> Optional[Field]:
            """Get a copy of the field corresponding to a base-plan

            Parameters
            ----------
            base_plan : __BasePlanData
                Base-plan data

            Returns
            ----------
            field_copy : Field | None
                Copy of the field (None on error)

            """
            if base_plan is None:
                print(f'[ERROR]: invalid base plan')
                return None
            if base_plan.processed_field is None:
                print(f'[ERROR]: no processed field available')
                return None
            return get_copy(base_plan.processed_field)

        @staticmethod
        def __get_base_plan_base_route_copy(base_plan: __BasePlanData) -> Optional[Route]:
            """Get a copy of the base route corresponding to a base-plan

            Parameters
            ----------
            base_plan : __BasePlanData
                Base-plan data

            Returns
            ----------
            base_route_copy : Field | None
                Copy of the base route (None on error)

            """
            if base_plan is None:
                print(f'[ERROR]: invalid base plan')
                return None
            if base_plan.base_route is None:
                print(f'[ERROR]: no base route available')
                return None
            return get_copy(base_plan.base_route)

        @staticmethod
        def __get_base_plan_base_graph_copy(base_plan: __BasePlanData) -> Optional[DirectedGraph]:
            """Get a copy of the base-graph corresponding to a base-plan

            Parameters
            ----------
            base_plan : __BasePlanData
                Base-plan data

            Returns
            ----------
            base_graph_copy : Field | None
                Copy of the base-graph (None on error)

            """
            if base_plan is None:
                print(f'[ERROR]: invalid base plan')
                return None
            if base_plan.graph is None:
                print(f'[ERROR]: no base graph available')
                return None
            return get_copy(base_plan.graph)


except ModuleNotFoundError as err:

    class FieldPartialPlanManager:
        """ Pseudo FieldPartialPlanManager holding needed basic information (in case arolib is not available) """

        NO_PLAN_ID: int = -1
        """ Id corresponding to 'no plan' """

        DEF_UNLOADING_SPEED_MASS = 100.0
        """ Default unloading speed [kg/s] """

        DEF_UNLOADING_SPEED_VOLUME = 100.0
        """ Default unloading speed [m³/s] """



