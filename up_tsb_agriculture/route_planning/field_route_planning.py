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

from typing import Optional
from route_planning.types import FieldState


class PlanningSettings:

    """ Class holding the settings for infield route planning (for a single field) """

    DEFAULT_HEADLAND_WIDTH: float = 27.0
    """ Default (minimum) headland width [m] """

    def __init__(self):
        self.avg_mass_per_area_t_ha: float = FieldState.DEFAULT_AVG_MASS_PER_AREA_T_HA
        """ Average yield mass per area [t/ha] in the field """

        self.sample_resolution: float = 5.0
        """ Route-points sample resolution [m] """

        self.headland_width: float = 27.0
        """ Desired (minimum) headland width [m] """

        self.headland_clockwise: bool = True
        """ Harvest the headland clockwise (True) or counter-clockwise (False) """

        self.last_olv_to_silo: bool = False
        """ Must the transport vehicle performing the last overloading in the field be sent to a silo (True) or only to a field exit (False) """

        self.max_planning_time: float = 30.0
        """ Maximum planning time before aborting [s] """

        self.max_waiting_time: float = -1.0
        """ Maximum time [s] a harvester is allowed to wait for a transport vehicle to overload (disregarded if < 0) """

        self.num_overload_activities: int = -1
        """ Number of overloading activities to be planned (disregarded if < 0) """

        self.max_worked_mass: float = -1.0
        """ Maximum harvested yield-mass to be planned (disregarded if < 0) """

        self.clearance_time: float = 10.0
        """ Clearance time between machines driving over the same location [s] """

        self.cost_coef_track_cross: float = 25.0
        """ Cost coefficient related to crossing from one inner-field track to another (used for path planning) """

        self.cost_coef_boundary_cross: float = 50.0
        """ Cost coefficient related to driving over the field boundary (used for path planning) """


try:
    import os

    from exposed_arolib.types import *
    from exposed_arolib.cartography import *
    from exposed_arolib.planning import *
    from exposed_arolib.misc import *
    from exposed_arolib.geometry import *
    from exposed_arolib.components import *
    from exposed_arolib.io import *
    from util_arolib.types_wrapper import *

    from exposed_arolib.types import copy_arolib_type
    from exposed_arolib.planning import copy_arolib_type as copy_arolib_type__planning


    class FieldRoutePlanner:
        """ Cost used as an interface to the Arolib field geometry processing and route planning functionalities """

        log_level = LogLevel.ERROR
        """ Arolib log level """

        def __init__(self):
            """ Class initialization """

            self.__cellsInfoManager = GridCellsInfoManager()
            """ Grid-maps' cells' information manager """

            self.__biomass_maps: Dict[int, ArolibGrid_t] = dict()
            """ Biomass [t/ha] grid-maps for each field: {field_id: gridmap} """

        def register_biomass_map(self, field_id: int, mass_map: ArolibGrid_t) -> bool:
            """ Register/update a biomass [t/ha] grid-map for a given field

            Parameters
            ----------
            field_id : int
                Field id
            mass_map : ArolibGrid_t
                Biomass [t/ha] grid-map

            Returns
            ----------
            success : bool
                True on success"""

            mass_map_name = f'FieldRoutePlanner__massmap_{field_id}'
            if mass_map is None:
                if field_id not in self.__biomass_maps.keys():
                    return True
                self.__biomass_maps.pop(field_id)
                return self.__cellsInfoManager.removeGrid(mass_map_name)
            self.__biomass_maps[field_id] = mass_map
            return self.__cellsInfoManager.registerGridFromLayout(mass_map_name, mass_map.getLayout(), True)

        def plan_field(self,
                       field: Field,
                       machines: Dict[int, Machine],
                       machine_states: Dict[int, MachineDynamicInfo],
                       outfield_info: OutFieldInfo,
                       remaining_area_map: Optional[ArolibGrid_t],
                       planning_settings: PlanningSettings,
                       processed_field: Field,
                       routes: Dict[int, Route],
                       plan_info: PlanGeneralInfo) -> AroResp:

            """Generate the field geometric representation and plan the machine routes.

            Parameters
            ----------
            field : Field
                Field to be harvested
            machines : Dict[int, Machine]
                Working group of machines: {machine_id: machine}
            machine_states : Dict[int, MachineDynamicInfo]
                Current machine states: {machine_id: machine_state}
            outfield_info : OutFieldInfo
                Holds the information related to out-of-field activities (e.g., transit)
            remaining_area_map : ArolibGrid_t
                Grid-map corresponding to the area of the field that has not been worked yet (cell values: 1: not-worked; 0: worked)
            planning_settings : PlanningSettings
                Planing settings
            processed_field : Field
                [out] Resulting field including the generated field geometries
            routes :  Dict[int, Route]
                [out] Planned machine routes: {machine_id: route}
            plan_info :  PlanGeneralInfo
                [out] Resulting plan information

            Returns
            ----------
            arolib_response : AroResp
                Arolib response with error id (0:=OK) and message
            """

            base_routes = dict()
            graph = DirectedGraph()
            aro_resp = self.plan_field_base(field,
                                            machines,
                                            machine_states,
                                            outfield_info,
                                            remaining_area_map,
                                            planning_settings,
                                            processed_field,
                                            base_routes,
                                            graph)
            if aro_resp.isError():
                return aro_resp

            return self.plan_field_from_base(processed_field,
                                             # create a copy to avoid potential equal-reference problem?
                                             machines,
                                             machine_states,
                                             outfield_info,
                                             base_routes,
                                             graph,
                                             remaining_area_map,
                                             planning_settings,
                                             processed_field,
                                             routes,
                                             plan_info)

        def plan_field_base(self,
                            field: Field,
                            machines: Dict[int, Machine],
                            machine_states: Dict[int, MachineDynamicInfo],
                            outfield_info: OutFieldInfo,
                            remaining_area_map: Optional[ArolibGrid_t],
                            planning_settings: PlanningSettings,
                            processed_field: Field,
                            base_routes: Dict[int, Route],
                            graph: DirectedGraph) -> AroResp:

            """Initialize a plan for the given field and machines, i.e., drive the primary machine to the field, generate the field geometric representation, create the base route and graph, etc.

            Parameters
            ----------
            field : Field
                Field
            machines : Dict[int, Machine]
                Working group of machines: {machine_id: machine}
            machine_states : Dict[int, MachineDynamicInfo]
                Current machine states: {machine_id: machine_state}
            outfield_info : OutFieldInfo
                Holds the information related to out-of-field activities (e.g., transit)
            remaining_area_map : ArolibGrid_t
                Grid-map corresponding to the area of the field that has not been worked yet (cell values: 1: not-worked; 0: worked)
            planning_settings : PlanningSettings
                Planing settings
            processed_field : Field
                [out] Resulting field including the generated field geometries
            base_routes :  Dict[int, Route]
                [out] Planned base-routes: {machine_id: route}
            graph :  DirectedGraph
                [out] Resulting field graph

            Returns
            ----------
            arolib_response : AroResp
                Arolib response with error id (0:=OK) and message
            """

            machines_vec = MachineVector()
            machines_vec.extend(machines.values())
            aro_machine_states = dict_to_arolib_map(machine_states, MachineId2DynamicInfoMap)

            _remaining_area_map = remaining_area_map
            if _remaining_area_map is None:
                _remaining_area_map = ArolibGrid_t()

            if field is not processed_field:
                copy_arolib_type(field, processed_field)

            base_routes.clear()
            if graph is not None:
                graph.clear()

            aro_resp = self.__process_field_geometries(processed_field,
                                                       machines_vec,
                                                       planning_settings)
            if aro_resp.isError():
                print(f'[ERROR] Error generating field geometries: {aro_resp.msg}')
                return aro_resp

            base_routes_all = RouteVector()
            aro_resp = self.__plan_base_routes(processed_field,
                                               machines_vec,
                                               outfield_info,
                                               _remaining_area_map,
                                               aro_machine_states,
                                               planning_settings,
                                               base_routes_all)
            if aro_resp.isError():
                print(f'[ERROR] Error generating base routes: {aro_resp.msg}')
                return aro_resp

            for br in base_routes_all:
                base_routes[br.machine_id] = br

            if graph is None:
                return AroResp.ok('')

            aro_resp = self.__generate_graph(processed_field,
                                             machines_vec,
                                             outfield_info,
                                             aro_machine_states,
                                             base_routes_all,
                                             planning_settings,
                                             graph)

            if aro_resp.isError():
                print(f'[ERROR] Error generating graph: {aro_resp.msg}')
                return aro_resp

            return AroResp.ok('')

        def plan_field_from_base(self,
                                 field: Field,
                                 machines: Dict[int, Machine],
                                 machine_states: Dict[int, MachineDynamicInfo],
                                 outfield_info: OutFieldInfo,
                                 base_routes: Dict[int, Route],
                                 graph: Optional[DirectedGraph],
                                 remaining_area_map: Optional[ArolibGrid_t],
                                 planning_settings: PlanningSettings,
                                 processed_field: Field,
                                 routes: Dict[int, Route],
                                 plan_info: PlanGeneralInfo) -> AroResp:

            """Plan the machine routes for the given field and machines based on the given base-routes.

            Parameters
            ----------
            field : Field
                Field
            machines : Dict[int, Machine]
                Working group of machines: {machine_id: machine}
            machine_states : Dict[int, MachineDynamicInfo]
                Current machine states: {machine_id: machine_state}
            outfield_info : OutFieldInfo
                Holds the information related to out-of-field activities (e.g., transit)
            base_routes :  Dict[int, Route]
                base-routes: {machine_id: route}
            graph :  DirectedGraph
                [in, out] Field graph
            remaining_area_map : ArolibGrid_t
                Grid-map corresponding to the area of the field that has not been worked yet (cell values: 1: not-worked; 0: worked)
            planning_settings : PlanningSettings
                Planing settings
            processed_field : Field
                [out] Resulting field
            routes :  Dict[int, Route]
                [out] Planned routes: {machine_id: route}
            plan_info :  PlanGeneralInfo
                [out] Resulting plan information

            Returns
            ----------
            arolib_response : AroResp
                Arolib response with error id (0:=OK) and message
            """

            if field is not processed_field:
                copy_arolib_type(field, processed_field)

            machines_vec = MachineVector()
            machines_vec.extend(machines.values())
            base_routes_vec = RouteVector()
            base_routes_vec.extend(base_routes.values())
            aro_machine_states = dict_to_arolib_map(machine_states, MachineId2DynamicInfoMap)

            _remaining_area_map = remaining_area_map if remaining_area_map is not None else ArolibGrid_t()

            routes.clear()

            if graph is None:
                graph = DirectedGraph()
                aro_resp = self.__generate_graph(processed_field,
                                                 machines_vec,
                                                 outfield_info,
                                                 aro_machine_states,
                                                 base_routes_vec,
                                                 planning_settings,
                                                 graph)
                if aro_resp.isError():
                    print(f'[ERROR] Error generating graph: {aro_resp.msg}')
                    return aro_resp

            routes_vec = RouteVector()
            aro_resp = self.__plan_operation(processed_field,
                                             machines_vec,
                                             outfield_info,
                                             aro_machine_states,
                                             base_routes_vec,
                                             graph,
                                             _remaining_area_map,
                                             planning_settings,
                                             routes_vec,
                                             plan_info)
            if aro_resp.isError():
                print(f'[ERROR] Error planning the routes: {aro_resp.msg}')
                return aro_resp

            for r in routes_vec:
                routes[r.machine_id] = r

            return AroResp.ok('')

        def __create_mass_factor_map(self, field: Field) -> ArolibGrid_t:
            """Create the mass-factor grid-map for a given field.

            Parameters
            ----------
            field : Field
                Field

            Returns
            ----------
            mass_factor_map : ArolibGrid_t
                Mass-factor grid-map
            """

            cellsize = 2.0
            boundary = field.outer_boundary.points
            if len(boundary) == 0:
                boundary = field.subfields[0].boundary_outer.points
            mass_factor_map = ArolibGrid_t()
            mass_factor_map.convertPolygonToGrid(boundary, cellsize, 1.0, False)

            mass_factor_map_name = f'FieldRoutePlanner__massfactormap_{field.id}'

            self.__cellsInfoManager.registerGridFromLayout(mass_factor_map_name, mass_factor_map.getLayout(), True)

            return mass_factor_map

        def __update_mass_factor_map(self, mass_factor_map: ArolibGrid_t, boundary: Polygon):
            """Update the mass-factor grid-map based on boundary of the area of the field that has not been worked.

            Parameters
            ----------
            mass_factor_map : ArolibGrid_t
                [in, out] Mass-factor grid-map to be updated
            boundary : Polygon
                Boundary of the area of the field that has not been worked
            """

            if len(boundary.points) == 0:
                # set all values to 1.0
                mass_factor_map.setAllValues(1.0)
                return
            # set all values to 'no value'
            mass_factor_map.unsetAllValues()
            # set all values inside the polygon to 1.0
            mass_factor_map.updatePolygonProportionally(boundary, 1.0, False)

        def __get_mass_calculator(self, field_id: int,
                                  avg_mass_per_area: float) -> IEdgeMassCalculator:
            """Create the yield-mass calculator for a given field.

            Parameters
            ----------
            field_id : int
                Field id
            avg_mass_per_area : float
                Average yield-mass per area-unit [t/ha]

            Returns
            ----------
            mass_calculator : IEdgeMassCalculator
                Yield-mass calculator
            """

            mass_calculator = EMC_MassGrid()
            mass_calculator.setGridCellsInfoManager(self.__cellsInfoManager)
            mass_calculator.setParameters(avg_mass_per_area)
            mass_map = self.__biomass_maps.get(field_id)
            if mass_map is not None:
                mass_calculator.setMassMap(mass_map)
            return mass_calculator

        def __get_speed_calculator_headland(self) -> IEdgeSpeedCalculator:
            """Create the machine working-speed calculator for the headland.

            Returns
            ----------
            speed_calculator : IEdgeSpeedCalculator
                Machine speed calculator
            """
            return EdgeWorkingSpeedCalculatorDef()

        def __get_speed_calculator_infield(self) -> IEdgeSpeedCalculator:
            """Create the machine working-speed calculator for the inner-field.

            Returns
            ----------
            speed_calculator : IEdgeSpeedCalculator
                Machine speed calculator
            """
            return EdgeWorkingSpeedCalculatorDef()

        def __get_speed_calculator_transit(self) -> IEdgeSpeedCalculator:
            """Create the machine infield transit-speed calculator.

            Returns
            ----------
            speed_calculator : IEdgeSpeedCalculator
                Machine speed calculator
            """
            return EdgeTransitSpeedCalculatorDef()

        def __get_cost_calculator(self, planning_settings: PlanningSettings) -> IEdgeCostCalculator:
            """Create the edge-cost calculator.

            Parameters
            ----------
            planning_settings : PlanningSettings
                Planning settings

            Returns
            ----------
            cost_calculator : IEdgeCostCalculator
                Edge-cost calculator
            """

            params = CostCalculatorGeneralParameters()
            params.crossCostMult = planning_settings.cost_coef_track_cross
            params.boundaryCrossCostMult = planning_settings.cost_coef_boundary_cross
            calculator = ECC_timeOptimization()
            calculator.setGeneralParameters(params)
            return calculator

        def __process_field_geometries(self,
                                       field: Field,
                                       machines: MachineVector,
                                       planning_settings: PlanningSettings) -> AroResp:

            """Create the field geometric representation for the given field.

            Parameters
            ----------
            field : Field
                [in, out] Field to be processed
            machines : MachineVector
                Working group of machines

            Returns
            ----------
            arolib_response : AroResp
                Arolib response with error id (0:=OK) and message
            """

            working_width: float = -1
            for machine in machines:
                if machine.isOfWorkingType(False):
                    working_width = max(working_width, machine.working_width)

            fgp_params_hl = FieldGeometryProcessorHeadlandParameters()

            fgp_params_hl.numTracks = 0
            fgp_params_hl.headlandWidth = planning_settings.headland_width
            fgp_params_hl.sampleResolution = planning_settings.sample_resolution
            fgp_params_hl.trackWidth = working_width

            fgp_params_if = FieldGeometryProcessorInfieldParameters()
            fgp_params_if.sampleResolution = planning_settings.sample_resolution
            fgp_params_if.trackDistance = working_width
            fgp_params_if.checkForRemainingTracks = True
            fgp_params_if.onlyUntilBoundaryIntersection = False

            # FieldGeometryProcessorHeadlandParameters__set__numTracks(fgp_params_hl, 0)
            # FieldGeometryProcessorHeadlandParameters__set__headlandWidth(fgp_params_hl,
            #                                                              planning_settings.headland_width)
            # FieldGeometryProcessorHeadlandParameters__set__sampleResolution(fgp_params_hl,
            #                                                                 planning_settings.sample_resolution)
            # FieldGeometryProcessorHeadlandParameters__set__trackWidth(fgp_params_hl, working_width)
            #
            # fgp_params_if = FieldGeometryProcessorInfieldParameters()
            # FieldGeometryProcessorInfieldParameters__set__sampleResolution(fgp_params_if,
            #                                                                planning_settings.sample_resolution)
            # FieldGeometryProcessorInfieldParameters__set__trackDistance(fgp_params_if, working_width)
            # FieldGeometryProcessorInfieldParameters__set__checkForRemainingTracks(fgp_params_if, True)
            # FieldGeometryProcessorInfieldParameters__set__onlyUntilBoundaryIntersection(fgp_params_if, False)

            fgp = FieldGeometryProcessor(self.log_level)
            return fgp.processSubfieldWithSurroundingHeadland(field.subfields[0],
                                                              fgp_params_hl,
                                                              fgp_params_if,
                                                              Point.invalidPoint(),
                                                              0)

        def __plan_base_routes(self,
                               field: Field,
                               machines: MachineVector,
                               outfield_info: OutFieldInfo,
                               remaining_area_map: Optional[ArolibGrid_t],
                               machine_states: MachineId2DynamicInfoMap,
                               planning_settings: PlanningSettings,
                               base_routes: RouteVector) -> AroResp:

            """Plan the base route for the given field and machines

            Parameters
            ----------
            field : Field
                Field
            machines : MachineVector
                Working group of machines
            outfield_info : OutFieldInfo
                Holds the information related to out-of-field activities (e.g., transit)
            remaining_area_map : ArolibGrid_t
                Grid-map corresponding to the area of the field that has not been worked yet (cell values: 1: not-worked; 0: worked)
            machine_states : MachineId2DynamicInfoMap
                Current machine states
            planning_settings : PlanningSettings
                Planing settings
            base_routes : RouteVector
                [out] Planned base-routes

            Returns
            ----------
            arolib_response : AroResp
                Arolib response with error id (0:=OK) and message
            """

            mass_calculator = self.__get_mass_calculator(field.id, planning_settings.avg_mass_per_area_t_ha)
            speed_calculator_hl = self.__get_speed_calculator_headland()
            speed_calculator_if = self.__get_speed_calculator_infield()
            speed_calculator_transit = self.__get_speed_calculator_transit()

            brp_params = BaseRoutesPlannerParameters()

            brp_params.avgMassPerArea = planning_settings.avg_mass_per_area_t_ha
            brp_params.workHeadlandFirst = True
            brp_params.workedAreaTransitRestriction = HeadlandWorkedAreaTransitRestriction.TRANSIT_ONLY_OVER_WORKED_AREA
            brp_params.startHeadlandFromOutermostTrack = True
            brp_params.finishHeadlandWithOutermostTrack = False
            brp_params.headlandClockwise = planning_settings.headland_clockwise
            brp_params.restrictToBoundary = True
            brp_params.monitorPlannedAreasInHeadland = False
            brp_params.headlandSpeedMultiplier = 1.0
            brp_params.limitStartToExtremaTracks = True

            # BaseRoutesPlannerParameters__set__avgMassPerArea(brp_params, planning_settings.avg_mass_per_area_t_ha)
            # BaseRoutesPlannerParameters__set__workHeadlandFirst(brp_params, True)
            # BaseRoutesPlannerParameters__set__workedAreaTransitRestriction(brp_params,
            #                                                                HeadlandWorkedAreaTransitRestriction__TRANSIT_ONLY_OVER_WORKED_AREA)
            # BaseRoutesPlannerParameters__set__startHeadlandFromOutermostTrack(brp_params, True)
            # BaseRoutesPlannerParameters__set__finishHeadlandWithOutermostTrack(brp_params, False)
            # BaseRoutesPlannerParameters__set__headlandClockwise(brp_params, planning_settings.headland_clockwise)
            # BaseRoutesPlannerParameters__set__restrictToBoundary(brp_params, True)
            # BaseRoutesPlannerParameters__set__monitorPlannedAreasInHeadland(brp_params, False)
            # BaseRoutesPlannerParameters__set__headlandSpeedMultiplier(brp_params, 1.0)
            # BaseRoutesPlannerParameters__set__limitStartToExtremaTracks(brp_params, True)

            br_planner = BaseRoutesPlanner(self.log_level)
            br_planner.setInfieldTrackSequencer(TrackSequencerClosestNext())

            return br_planner.plan(field.subfields[0],
                                   machines,
                                   brp_params,
                                   mass_calculator,
                                   speed_calculator_hl,
                                   speed_calculator_if,
                                   speed_calculator_transit,
                                   base_routes,
                                   None,
                                   machine_states,
                                   None,
                                   outfield_info,
                                   remaining_area_map)

        def __generate_graph(self,
                             field: Field,
                             machines: MachineVector,
                             outfield_info: OutFieldInfo,
                             machine_states: MachineId2DynamicInfoMap,
                             base_routes: RouteVector,
                             planning_settings: PlanningSettings,
                             graph: DirectedGraph) -> AroResp:

            """Generate the field graph

            Parameters
            ----------
            field : Field
                Field
            machines : MachineVector
                Working group of machines
            outfield_info : OutFieldInfo
                Holds the information related to out-of-field activities (e.g., transit)
            machine_states : MachineId2DynamicInfoMap
                Current machine states
            base_routes : RouteVector
                Planned base-routes
            planning_settings : PlanningSettings
                Planing settings
            graph : DirectedGraph
                [out] Resulting graph

            Returns
            ----------
            arolib_response : AroResp
                Arolib response with error id (0:=OK) and message
            """

            gp_params = GraphProcessorSettings()
            gp_params.incVisitPeriods = True
            gp_params.workingWidth = -1
            for machine in machines:
                if machine.isOfWorkingType(False):
                    gp_params.workingWidth = max(gp_params.workingWidth, machine.working_width)
            gp_params.workingWidthHL = gp_params.workingWidth

            graph_processor = GraphProcessor(self.log_level)
            return graph_processor.createGraph(field.subfields[0],
                                               base_routes,
                                               machines,
                                               gp_params,
                                               outfield_info,
                                               machine_states,
                                               graph)

        def __plan_operation(self,
                             field: Field,
                             machines: MachineVector,
                             outfield_info: OutFieldInfo,
                             machine_states: MachineId2DynamicInfoMap,
                             base_routes: RouteVector,
                             graph: DirectedGraph,
                             remaining_area_map: ArolibGrid_t,
                             planning_settings: PlanningSettings,
                             routes: RouteVector,
                             plan_info: PlanGeneralInfo) -> AroResp:

            """Plan the machine routes

            Parameters
            ----------
            field : Field
                Field
            machines : MachineVector
                Working group of machines
            outfield_info : OutFieldInfo
                Holds the information related to out-of-field activities (e.g., transit)
            machine_states : MachineId2DynamicInfoMap
                Current machine states
            base_routes : RouteVector
                Base-routes
            graph : DirectedGraph
                [in, out] Field graph (updated after planning)
            remaining_area_map : ArolibGrid_t
                Grid-map corresponding to the area of the field that has not been worked yet (cell values: 1: not-worked; 0: worked)
            planning_settings : PlanningSettings
                Planing settings
            routes : RouteVector
                Planned routes
            plan_info :  PlanGeneralInfo
                [out] Resulting plan information

            Returns
            ----------
            arolib_response : AroResp
                Arolib response with error id (0:=OK) and message
            """

            cost_calculator = self.__get_cost_calculator(planning_settings)

            planner_params = FieldProcessPlannerParametersPy()
            set_params_directly = True

            if set_params_directly:  # Setting the parameters via FieldProcessPlannerParametersPy
                params1 = RoutePlannerStandaloneMachinesSettings()
                params2 = MultiOLVPlannerSettings()

                # shared attributes
                params1.clearanceTime = params2.clearanceTime = planning_settings.clearance_time
                params1.includeWaitInCost = params2.includeWaitInCost = True
                params1.collisionAvoidanceOption = params2.collisionAvoidanceOption = CollisionAvoidanceOption__COLLISION_AVOIDANCE__OVERALL
                params1.switchOnlyAtTrackEnd = params2.switchOnlyAtTrackEnd = False

                # RoutePlannerStandaloneMachinesSettings
                params1.maxPlanningTime = planning_settings.max_planning_time
                params1.finishAtResourcePoint = planning_settings.last_olv_to_silo

                # MultiOLVPlannerSettings
                params2.max_planning_time = planning_settings.max_planning_time
                params2.max_waiting_time = planning_settings.max_waiting_time
                params2.numOverloadActivities = planning_settings.num_overload_activities
                params2.harvestedMassLimit = planning_settings.max_worked_mass
                params2.sendLastOlvToResourcePoint = planning_settings.last_olv_to_silo
                params2.numFixedInitalOlvsInOrder = 0
                params2.includeCostOfOverload = True
                params2.threadsOption = ThreadsOption__MULTIPLE_THREADS

                planner_params.set_routePlannerStandaloneMachinesSettings(params1)
                planner_params.set_multiOLVPlannerSettings(params2)

            else:  # Setting the parameters via parseFromStringMap
                planner_params_str_map = planner_params.parseToStringMap(planner_params)  # to get defaults

                planner_params_str_map["clearanceTime"] = double2string(planning_settings.clearance_time)
                planner_params_str_map["maxPlanningTime"] = double2string(planning_settings.max_planning_time)
                planner_params_str_map["max_planning_time"] = double2string(planning_settings.max_planning_time)
                planner_params_str_map["numOverloadActivities"] = double2string(
                    planning_settings.num_overload_activities)
                planner_params_str_map["harvestedMassLimit"] = double2string(planning_settings.max_worked_mass)
                planner_params_str_map["finishAtResourcePoint"] = "1" if planning_settings.last_olv_to_silo else "0"
                planner_params_str_map[
                    "sendLastOlvToResourcePoint"] = "1" if planning_settings.last_olv_to_silo else "0"

                planner_params_str_map["threadsOption"] = "0"  # multiple threads
                planner_params_str_map["numFixedInitalOlvsInOrder"] = "0"
                planner_params_str_map["switchOnlyAtTrackEnd"] = "0"
                planner_params_str_map["includeCostOfOverload"] = "1"  # True
                planner_params_str_map["includeWaitInCost"] = "1"  # True
                planner_params_str_map["collisionAvoidanceOption"] = "2"  # avoidance overall

                FieldProcessPlannerParameters.parseFromStringMap(planner_params, planner_params_str_map, False)

            planner = FieldProcessPlanner(self.log_level)
            return planner.planSubfield(graph,
                                        field.subfields[0],
                                        base_routes,
                                        routes,
                                        machines,
                                        outfield_info,
                                        machine_states,
                                        planner_params,
                                        ArolibGrid_t(),
                                        remaining_area_map,
                                        cost_calculator,
                                        plan_info)  # @todo: check if this is right (the c++ method receives a raw pointer)

except ModuleNotFoundError as err:
    pass
