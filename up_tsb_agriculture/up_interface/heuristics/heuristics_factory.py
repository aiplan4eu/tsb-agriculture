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

""" This package presents factories to create different examples of heuristics to test and use in the agriculture use-case """

from typing import List, Set

from unified_planning.engines.sequential_simulator import SequentialSimulatorMixin
from unified_planning.plans.sequential_plan import SequentialPlan

import up_interface.fluents
import up_interface.types
import up_interface.config as conf
from up_interface.heuristics.general_heuristics import *
import up_interface.heuristics.sequential_heuristics as sh
import up_interface.heuristics.temporal_heuristics as th
from up_interface.heuristics.debug_heuristics import *


class DebugHeuristicOptions:

    """ Class holding the options to add debug heuristics """

    def __init__(self,
                 fluents: Optional[Set[up_interface.fluents.FluentNames]] = None,
                 fluents_output_file: Optional[str] = None,
                 actions_conditions: Optional[Sequence[Union[Action, str]]] = None,
                 actions_conditions_output_file: Optional[str] = None):

        """ Init

        Parameters
        ----------
        fluents : Set[FluentNames]
            Set of fluents to be saved by the HeuristicDebugFluents. If None, no HeuristicDebugFluents will be added; if empty, the default fluents will be saved
        fluents_output_file : str
            Output file name/path for the HeuristicDebugFluents. If None, the default file path will be used.
        actions_conditions : Sequence[Union[Action, str]]
            Set of actions whose conditions will be saved by the HeuristicDebugActionConditions. If None, no HeuristicDebugActionConditions will be added; if empty, all problem actions will be saved
        actions_conditions_output_file : str
            Output file name/path for the HeuristicDebugActionConditions. If None, the default file path will be used.

        Returns
        ----------
        heuristics : HeuristicBase | List[HeuristicBase]
            Resulting heuristics
        """

        self.fluents = fluents
        self.fluents_output_file = fluents_output_file
        self.actions_conditions = actions_conditions
        self.actions_conditions_output_file = actions_conditions_output_file

    def add_debug_heuristics_to_weighted_heuristic_params(self, weighted_heuristic_params: Dict[HeuristicBase, float]):
        if self.fluents is not None:
            if len(self.fluents) == 0:
                if self.fluents_output_file is None:
                    weighted_heuristic_params[HeuristicDebugFluents(None)] = 0
                else:
                    weighted_heuristic_params[HeuristicDebugFluents(None, self.fluents_output_file)] = 0
            else:
                if self.fluents_output_file is None:
                    weighted_heuristic_params[HeuristicDebugFluents(self.fluents)] = 0
                else:
                    weighted_heuristic_params[HeuristicDebugFluents(self.fluents, self.fluents_output_file)] = 0

        if self.actions_conditions is not None:
            if len(self.actions_conditions) == 0:
                if self.actions_conditions_output_file is None:
                    weighted_heuristic_params[HeuristicDebugActionConditions(None)] = 0
                else:
                    weighted_heuristic_params[HeuristicDebugActionConditions(None, self.actions_conditions_output_file)] = 0
            else:
                if self.actions_conditions_output_file is None:
                    weighted_heuristic_params[HeuristicDebugActionConditions(self.actions_conditions)] = 0
                else:
                    weighted_heuristic_params[HeuristicDebugActionConditions(self.actions_conditions, self.actions_conditions_output_file)] = 0


class SequentialHeuristicsFactory:

    """ Factory of heuristics for sequential planning """

    class HType(Enum):

        """ Supported heuristic types

        Meanings:
        - MASS_GOALS: includes heuristics to reach yield-mass-related goals (e.g., harvested mass, stored mass, etc.)
        - WAIT_TIMES: includes heuristics to minimize the waiting times of the machines
        - MAX_TIMES: includes control heuristics to reject states that reach time-related limits (e.g., maximum plan duration)
        - AVG_TIMES_HARV_MASS: includes control heuristics to reject states that reach average time-related limits relative to the harvested mass (e.g., harvesters waiting times / harvested mass)
        - AVG_TIMES_DURATION: includes control heuristics to reject states that reach average time-related limits relative to the plan duration (e.g., harvesters waiting times / plan duration)
        - WAIT_TIMES_UNHARV_MASS: includes heuristics to minimize the waiting times of the machines with a factor related to the unharvested mass
        - MAX_FIELD_HARV_TIMES: includes heuristics that involve field harvested-timestamp and estimated maximum field harvested-timestamp
        """

        DEFAULT = auto()
        WITH__MASS_GOALS__WAIT_TIMES__MAX_TIMES__AVG_TIMES_HARV_MASS__AVG_TIMES_DURATION = auto()
        WITH__MASS_GOALS__WAIT_TIMES = auto()
        WITH__MASS_GOALS__WAIT_TIMES__2 = auto()
        WITH__WAIT_TIMES = auto()
        WITH__MASS_GOALS = auto()
        WITH__WAIT_TIMES_UNHARV_MASS = auto()
        WITH__MAX_FIELD_HARV_TIMES__WAIT_TIMES = auto()

    __DEFAULT_TYPE = HType.WITH__MASS_GOALS__WAIT_TIMES__MAX_TIMES__AVG_TIMES_HARV_MASS__AVG_TIMES_DURATION
    """ Default heuristic type """

    def __init__(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 problem_stats: ProblemStats,
                 base_plan_final_state: Optional[State] = None,
                 base_plan: Optional[SequentialPlan] = None):

        """ Class initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        problem_stats : ProblemStats
            Problem statistics
        base_plan_final_state : State | None
            Final state for a valid base plan
        base_plan : SequentialPlan | None
            Base plan used to obtain the final state (disregarded if base_plan_final_state is given)
        """

        self.__problem = problem
        self.__fluents_manager = fluents_manager
        self.__problem_objects = objects
        self.__problem_stats = problem_stats

        self.__max_timestamp = None
        self.__max_harv_waiting_time = None
        self.__max_tv_waiting_time = None
        self.__max_harv_transit_time = None
        self.__max_tv_transit_time = None

        self.__init_goal_values(base_plan_final_state, base_plan)

    def get_heuristics(self,
                       heuristic_type: Optional[Union['SequentialHeuristicsFactory.HType', Sequence['SequentialHeuristicsFactory.HType']]] = None,
                       debug_heuristic_options: Optional[DebugHeuristicOptions] = None) \
            -> Optional[ Union[HeuristicBase, List[HeuristicBase]] ]:

        """ Get the heuristic(s)

        If debug_heuristic_options is set, a HeuristicDebugXXX instances will be added to the first returned WeightedHeuristics only

        Parameters
        ----------
        heuristic_type : SequentialHeuristicsFactory.HType | Set[SequentialHeuristicsFactory.HType]
            Type of heuristics to create (single or multiple). If None -> DEFAULT
        debug_heuristic_options : DebugHeuristicOptions
            Options to add debug heuristics (if None, no debug heuristics will be added)

        Returns
        ----------
        heuristics : HeuristicBase | List[HeuristicBase]
            Resulting heuristics
        """

        _default_1 = SequentialHeuristicsFactory.__DEFAULT_TYPE
        _default_2 = SequentialHeuristicsFactory.HType.WITH__MASS_GOALS__WAIT_TIMES

        h_types = set()
        if heuristic_type is None:
            h_types.add(SequentialHeuristicsFactory.HType.DEFAULT)
        elif isinstance(heuristic_type, SequentialHeuristicsFactory.HType):
            h_types.add(heuristic_type)
        else:
            h_types = heuristic_type

        debug_heuristic_added = False
        heuristics = list()
        for h_type in h_types:
            _h_type = h_type
            if _h_type is SequentialHeuristicsFactory.HType.DEFAULT:
                _h_type = _default_1
                if self.__check_type_requirements(_h_type) is not None:
                    _h_type = _default_2

            req_error = self.__check_type_requirements(_h_type)
            assert req_error is None, f'Error creating heuristics: {req_error}'

            weighted_heuristic_params = self.__get_weighted_heuristic_params(_h_type)

            if not debug_heuristic_added and debug_heuristic_options is not None:
                debug_heuristic_options.add_debug_heuristics_to_weighted_heuristic_params(weighted_heuristic_params)
                debug_heuristic_added = True

            heuristics.append( WeightedHeuristics(weighted_heuristic_params) )

        if len(heuristics) == 1:
            return heuristics[0]

        return heuristics

    @staticmethod
    def set_default_type(def_type: Optional[HType]):

        """ Set the default heuristic-set type

        Parameters
        def_type : HType | None
        """

        if def_type is None or not isinstance(def_type, SequentialHeuristicsFactory.HType):
            SequentialHeuristicsFactory.__DEFAULT_TYPE = SequentialHeuristicsFactory.HType.WITH__MASS_GOALS__WAIT_TIMES__MAX_TIMES__AVG_TIMES_HARV_MASS__AVG_TIMES_DURATION
        else:
            SequentialHeuristicsFactory.__DEFAULT_TYPE = def_type

    def __init_goal_values(self, base_plan_final_state: Optional[State], base_plan: Optional[SequentialPlan]):

        """ Initialize some goal values based on the given base plan or final state

        Parameters
        base_plan_final_state : State | None
            Final state for a valid base plan
        base_plan : SequentialPlan | None
            Base plan used to obtain the final state (disregarded if base_plan_final_state is given)
        """

        final_state = base_plan_final_state
        if final_state is None and base_plan is not None:
            sim: SequentialSimulatorMixin = SequentialSimulator(problem=self.__problem)
            final_state = sim.get_initial_state()
            for action_instance in base_plan.actions:
                final_state = sim.apply(final_state, action_instance)
                assert final_state is not None, f'The given plan is not valid (UP simulator failed to apply action {action_instance})'
            assert sim.is_goal(final_state), f'The given plan is not valid (th final state is not a goal)'

        if final_state is not None:

            harv_timestamp = self.__fluents_manager.get_fluent(fn.harv_timestamp)
            tv_timestamp = self.__fluents_manager.get_fluent(fn.tv_timestamp)
            harv_waiting_time = self.__fluents_manager.get_fluent(fn.harv_waiting_time)
            tv_waiting_time = self.__fluents_manager.get_fluent(fn.tv_waiting_time)
            harv_transit_time = self.__fluents_manager.get_fluent(fn.harv_transit_time)
            tv_transit_time = self.__fluents_manager.get_fluent(fn.tv_transit_time)

            self.__max_timestamp = 0.0
            self.__max_harv_waiting_time = 0.0
            self.__max_tv_waiting_time = 0.0
            self.__max_harv_transit_time = 0.0
            self.__max_tv_transit_time = 0.0

            harvs = self.__problem.objects(upt.Harvester)
            for m in harvs:
                if m.name == self.__problem_objects.no_harvester.name:
                    continue
                self.__max_timestamp = max(self.__max_timestamp, float(final_state.get_value(harv_timestamp(m)).constant_value()))
                self.__max_harv_waiting_time += float(final_state.get_value(harv_waiting_time(m)).constant_value())
                self.__max_harv_transit_time += float(final_state.get_value(harv_transit_time(m)).constant_value())

            tvs = self.__problem.objects(up_interface.types.TransportVehicle)
            for m in tvs:
                self.__max_timestamp = max(self.__max_timestamp, float(final_state.get_value(tv_timestamp(m)).constant_value()))
                self.__max_tv_waiting_time += float(final_state.get_value(tv_waiting_time(m)).constant_value())
                self.__max_tv_transit_time += float(final_state.get_value(tv_transit_time(m)).constant_value())

    def __check_type_requirements(self, h_type: 'SequentialHeuristicsFactory.HType') -> Optional[str]:

        """ Check if the heuristic type is supported by this factory

        Parameters
        h_type : HType
            Heuristic type

        Returns
        error_msg : str | None
            Error message (None if supported)
        """

        type_str = f'{h_type}'
        if type_str.find('MAX_TIMES') >= 0 or type_str.find('AVG_TIMES') >= 0:
            if self.__max_timestamp is None:
                return f'The given heuristic type {h_type} requires a valid base final state'
        return None

    def __get_weighted_heuristic_params(self, h_type: 'SequentialHeuristicsFactory.HType') \
            -> Dict[HeuristicBase, float]:

        """ Get the parameters of the WeightedHeuristics for the given heuristic type

        Parameters
        h_type : HType
            Heuristic type

        Returns
        params : Dict[HeuristicBase, float]
            Parameters of the WeightedHeuristics for the given heuristic type: {sub_heuristic: weight}
        """

        HType = SequentialHeuristicsFactory.HType
        if h_type is HType.WITH__MASS_GOALS__WAIT_TIMES__MAX_TIMES__AVG_TIMES_HARV_MASS__AVG_TIMES_DURATION:
            return {
                HeuristicInitialYieldMassInFieldsMinusHarvested(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassInFieldsMinusAssigned(self.__problem, self.__fluents_manager): 0.1,
                sh.HeuristicHarvestersWaitingTime(): 5,
                # sh.HeuristicTVsWaitingTime(): 1,
                self.__get_heuristic_control_max_temporal_variables(): 1,
                self.__get_heuristic_control_average_temporal_variables_with_harvested_mass(): 1,
                self.__get_heuristic_control_average_waiting_times_with_max_timestamp(): 1,
            }
        if h_type is HType.WITH__MASS_GOALS__WAIT_TIMES:
            return {
                HeuristicInitialYieldMassInFieldsMinusHarvested(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassInFieldsMinusAssigned(self.__problem, self.__fluents_manager): 0.1,
                sh.HeuristicHarvestersWaitingTime(): 5,
                # sh.HeuristicTVsWaitingTime(): 1,
            }
        if h_type is HType.WITH__MASS_GOALS__WAIT_TIMES__2:
            return {
                HeuristicInitialYieldMassInFieldsMinusHarvested(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassInFieldsMinusAssigned(self.__problem, self.__fluents_manager): 0.1,
                sh.HeuristicHarvestersWaitingTime(): 1,
                # sh.HeuristicTVsWaitingTime(): 1,
            }
        if h_type is HType.WITH__WAIT_TIMES:
            return {
                sh.HeuristicHarvestersWaitingTime(): 5,
                # sh.HeuristicTVsWaitingTime(): 1,
            }
        if h_type is HType.WITH__MASS_GOALS:
            return {
                HeuristicInitialYieldMassInFieldsMinusHarvested(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassInFieldsMinusAssigned(self.__problem, self.__fluents_manager): 0.1,
            }
        if h_type is HType.WITH__WAIT_TIMES_UNHARV_MASS:
            return {
                sh.HeuristicHarvestersWaitingTimeAndUnharvestedYieldMass(self.__problem, self.__fluents_manager): 1
            }
        if h_type is HType.WITH__MAX_FIELD_HARV_TIMES__WAIT_TIMES:
            return {
                sh.HeuristicHarvestersWaitingTime(): 1,
                self.__get_heuristic_field_harvesting_timestamps: 1e-7,
            }
        raise NotImplementedError

    def __get_heuristic_control_max_temporal_variables(self) \
            -> sh.HeuristicControlMaxTemporalVariables:
        return sh.HeuristicControlMaxTemporalVariables( max_timestamp=self.__max_timestamp + 1,
                                                        max_harvesters_waiting_time=self.__max_harv_waiting_time + 1,
                                                        max_tvs_waiting_time=None)

    def __get_heuristic_control_average_temporal_variables_with_harvested_mass(self) \
            -> sh.HeuristicControlAverageTemporalVariablesWithHarvestedMass:
        return sh.HeuristicControlAverageTemporalVariablesWithHarvestedMass(
                    problem=self.__problem,
                    fluents_manager=self.__fluents_manager,
                    max_timestamp=sh.HeuristicControlAverageTemporalVariablesWithHarvestedMass.ControlValue(self.__max_timestamp, 3),
                    max_harvesters_waiting_time=sh.HeuristicControlAverageTemporalVariablesWithHarvestedMass.ControlValue(self.__max_harv_waiting_time, 3),
                    max_tvs_waiting_time=None
                )

    def __get_heuristic_control_average_waiting_times_with_max_timestamp(self) \
            -> sh.HeuristicControlAverageWaitingTimesWithMaxTimestamp:
        return sh.HeuristicControlAverageWaitingTimesWithMaxTimestamp(
                    max_timestamp=self.__max_timestamp,
                    max_harvesters_waiting_time=sh.HeuristicControlAverageWaitingTimesWithMaxTimestamp.ControlValue(self.__max_harv_waiting_time, 3),
                    max_tvs_waiting_time=None
                )

    def __get_heuristic_field_harvesting_timestamps(self) \
            -> sh.HeuristicFieldHarvestingTimestampsWithMaxTimestamp:
        return sh.HeuristicFieldHarvestingTimestampsWithMaxTimestamp(problem=self.__problem,
                                                                     fluents_manager=self.__fluents_manager,
                                                                     objects=self.__problem_objects,
                                                                     problem_stats=self.__problem_stats,
                                                                     max_infield_transit_duration=100,
                                                                     k_field_assigned=1,
                                                                     k_started_harvest=1,
                                                                     k_finished_harvest=1,
                                                                     factor_field_mass=False)


class TemporalHeuristicsFactory:

    """ Factory of heuristics for sequential planning """

    class HType(Enum):

        """ Supported heuristic types

        Meanings:
        - MASS_GOALS: includes heuristics to reach yield-mass-related goals (e.g., harvested mass, stored mass, etc.)
        - TV_MASS_WAIT_OL: includes heuristics related to bunker mass of transport vehicles waiting to overload
        - TV_MASS_WAIT_DRIVE: includes heuristics related to bunker mass of transport vehicles waiting to drive
        - UNHARV_MASS_HARV_WAIT_OL: includes heuristics related to unharvested mass of harvesters waiting to overload
        """

        DEFAULT = auto()
        WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL = auto()
        WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL__2 = auto()
        WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL__3 = auto()
        WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL__4 = auto()
        WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL__HARV_TRANS_DIST_BASE_COST = auto()
        WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL__HARV_TRANS_TIME = auto()
        WITH__MASS_GOALS = auto()

    __DEFAULT_TYPE = HType.WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL
    """ Default heuristic type """

    def __init__(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 problem_stats: ProblemStats,
                 problem_settings: conf.GeneralProblemSettings):

        """ Class initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        problem_stats : ProblemStats
            Problem statistics
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        """

        self.__problem = problem
        self.__fluents_manager = fluents_manager
        self.__objects = objects
        self.__problem_stats = problem_stats
        self.__problem_settings = problem_settings

    def get_heuristics(self,
                       heuristic_type: Optional[Union['TemporalHeuristicsFactory.HType', Sequence['TemporalHeuristicsFactory.HType']]] = None,
                       debug_heuristic_options: Optional[DebugHeuristicOptions] = None) \
            -> Optional[ Union[HeuristicBase, List[HeuristicBase]] ]:

        """ Get the heuristic(s)

        If debug_heuristic_options is set, a HeuristicDebugXXX instances will be added to the first returned WeightedHeuristics only

        Parameters
        ----------
        heuristic_type : TemporalHeuristicsFactory.HType | Set[TemporalHeuristicsFactory.HType]
            Type of heuristics to create (single or multiple). If None -> DEFAULT
        debug_heuristic_options : DebugHeuristicOptions
            Options to add debug heuristics (if None, no debug heuristics will be added)

        Returns
        ----------
        heuristics : HeuristicBase | List[HeuristicBase]
            Resulting heuristics
        """

        _default_1 = TemporalHeuristicsFactory.__DEFAULT_TYPE

        h_types = set()
        if heuristic_type is None:
            h_types.add(TemporalHeuristicsFactory.HType.DEFAULT)
        elif isinstance(heuristic_type, TemporalHeuristicsFactory.HType):
            h_types.add(heuristic_type)
        else:
            h_types = heuristic_type

        debug_heuristic_added = False
        heuristics = list()
        for h_type in h_types:
            _h_type = h_type
            if _h_type is TemporalHeuristicsFactory.HType.DEFAULT:
                _h_type = _default_1

            weighted_heuristic_params = self.__get_weighted_heuristic_params(_h_type)

            if not debug_heuristic_added and debug_heuristic_options is not None:
                debug_heuristic_options.add_debug_heuristics_to_weighted_heuristic_params(weighted_heuristic_params)
                debug_heuristic_added = True

            heuristics.append( WeightedHeuristics(weighted_heuristic_params) )

        if len(heuristics) == 1:
            return heuristics[0]

        return heuristics

    @staticmethod
    def set_default_type(def_type: Optional[HType]):

        """ Set the default heuristic-set type

        Parameters
        def_type : HType | None
        """

        if def_type is None or not isinstance(def_type, TemporalHeuristicsFactory.HType):
            TemporalHeuristicsFactory.__DEFAULT_TYPE = TemporalHeuristicsFactory.HType.WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL
        else:
            TemporalHeuristicsFactory.__DEFAULT_TYPE = def_type


    def __get_weighted_heuristic_params(self, h_type: 'TemporalHeuristicsFactory.HType') \
            -> Dict[HeuristicBase, float]:

        """ Get the parameters of the WeightedHeuristics for the given heuristic type

        Parameters
        h_type : HType
            Heuristic type

        Returns
        params : Dict[HeuristicBase, float]
            Parameters of the WeightedHeuristics for the given heuristic type: {sub_heuristic: weight}
        """

        HType = TemporalHeuristicsFactory.HType
        if h_type is HType.WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL:
            return {
                th.HeuristicInitialYieldMassInFieldsMinusReserved(self.__problem, self.__fluents_manager): 1,
                th.HeuristicInitialYieldMassInFieldsMinusPotentiallyReserved(self.__problem, self.__fluents_manager): 1, # @note might be redundant, it was an attempt to improve planning time with with_harv_conditions_and_effects_at_tv_arrival = True
                HeuristicInitialYieldMassInFieldsMinusHarvested(self.__problem, self.__fluents_manager): 1,
                th.HeuristicInitialYieldMassInFieldsMinusPlannedHarvested(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusReserved(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): (1 if self.__problem_settings.silo_planning_type is not conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY else 0),
                HeuristicInitialYieldMassInFieldsMinusAssigned(self.__problem, self.__fluents_manager): 0.1,
                # HeuristicTVsTransitTime(None): 0.00001,
                th.HeuristicBunkerCapacityTvsWaitingToOverload(): 0.3,
                th.HeuristicBunkerMassTvsWaitingToDrive(use_bunker_total_capacity=True): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=False): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=True): 0.02,
                # th.HeuristicRejectInvalidFieldHarvestersAndTurns(): 1,
            }
        if h_type is HType.WITH__MASS_GOALS:
            return {
                th.HeuristicInitialYieldMassInFieldsMinusPotentiallyReserved(self.__problem, self.__fluents_manager): 1,
                th.HeuristicInitialYieldMassInFieldsMinusPlannedHarvested(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusReserved(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): (1 if self.__problem_settings.silo_planning_type is not conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY else 0),
                th.HeuristicRejectHarvestersDisabledToOverload(): 1
            }
        if h_type is HType.WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL__2:
            return {
                th.HeuristicInitialYieldMassInFieldsMinusPotentiallyReserved(self.__problem, self.__fluents_manager): 1,
                th.HeuristicInitialYieldMassInFieldsMinusPlannedHarvested(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusReserved(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): (1 if self.__problem_settings.silo_planning_type is not conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY else 0),
                HeuristicInitialYieldMassInFieldsMinusAssigned(self.__problem, self.__fluents_manager): 1,
                # HeuristicTVsTransitTime(None): 0.00001,
                th.HeuristicBunkerCapacityTvsWaitingToOverload(): 0.3,
                th.HeuristicBunkerMassTvsWaitingToDrive(use_bunker_total_capacity=True): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=False): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=True): 0.02,
            }
        if h_type is HType.WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL__3:
            return {
                th.HeuristicInitialYieldMassInFieldsMinusReserved(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassInFieldsMinusHarvested(self.__problem, self.__fluents_manager): 1,
                th.HeuristicInitialYieldMassInFieldsMinusPlannedHarvested(self.__problem, self.__fluents_manager): 1,
                th.HeuristicInitialYieldMassToStoreMinusReserved(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): (1 if self.__problem_settings.silo_planning_type is not conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY else 0),
                # HeuristicInitialYieldMassInFieldsMinusAssigned(self.__problem, self.__fluents_manager): 0.1,
                # HeuristicTVsTransitTime(None): 0.00001,
                th.HeuristicBunkerCapacityTvsWaitingToOverload(): 0.3,
                th.HeuristicBunkerMassTvsWaitingToDrive(use_bunker_total_capacity=True): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=False): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=True): 0.02,
            }
        if h_type is HType.WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL__4:
            return {
                th.HeuristicInitialYieldMassInFieldsMinusReserved(self.__problem, self.__fluents_manager): 100,
                HeuristicInitialYieldMassInFieldsMinusHarvested(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusReserved(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): (1 if self.__problem_settings.silo_planning_type is not conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY else 0),
                HeuristicInitialYieldMassInFieldsMinusAssigned(self.__problem, self.__fluents_manager): 1,
                # HeuristicTVsTransitTime(None): 0.00001,
                th.HeuristicBunkerCapacityTvsWaitingToOverload(): 1,
                th.HeuristicBunkerMassTvsWaitingToDrive(use_bunker_total_capacity=True): 0.5,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=False): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=True): 0.02,
            }
        if h_type is HType.WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL__HARV_TRANS_DIST_BASE_COST:
            return {
                th.HeuristicInitialYieldMassInFieldsMinusReserved(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassInFieldsMinusHarvested(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusReserved(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): (1 if self.__problem_settings.silo_planning_type is not conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY else 0),
                # HeuristicInitialYieldMassInFieldsMinusAssigned(self.__problem, self.__fluents_manager): 0.1,
                # HeuristicTVsTransitTime(None): 0.00001,
                HeuristicHarvestersTransitDistanceWithBaseCost(self.__problem,
                                                               self.__fluents_manager,
                                                               self.__objects,
                                                               self.__problem_stats): 0.1,
                th.HeuristicBunkerCapacityTvsWaitingToOverload(): 0.3,
                th.HeuristicBunkerMassTvsWaitingToDrive(use_bunker_total_capacity=True): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=False): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=True): 0.02,
            }
        if h_type is HType.WITH__MASS_GOALS__TV_MASS_WAIT_OL__TV_MASS_WAIT_DRIVE__UNHARV_MASS_HARV_WAIT_OL__HARV_TRANS_TIME:
            return {
                th.HeuristicInitialYieldMassInFieldsMinusReserved(self.__problem, self.__fluents_manager): 1,
                th.HeuristicInitialYieldMassInFieldsMinusPotentiallyReserved(self.__problem, self.__fluents_manager): 1, # @note might be redundant, it was an attempt to improve planning time with with_harv_conditions_and_effects_at_tv_arrival = True
                HeuristicInitialYieldMassInFieldsMinusHarvested(self.__problem, self.__fluents_manager): 1,
                th.HeuristicInitialYieldMassInFieldsMinusPlannedHarvested(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusReserved(self.__problem, self.__fluents_manager): 1,
                HeuristicInitialYieldMassToStoreMinusStored(self.__problem, self.__fluents_manager): (1 if self.__problem_settings.silo_planning_type is not conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY else 0),
                HeuristicInitialYieldMassInFieldsMinusAssigned(self.__problem, self.__fluents_manager): 0.1,
                HeuristicHarvestersTransitTime(1.0): 0.001 * self.__problem_stats.fields.yield_mass_remaining.max,
                th.HeuristicBunkerCapacityTvsWaitingToOverload(): 0.3,
                th.HeuristicBunkerMassTvsWaitingToDrive(use_bunker_total_capacity=True): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=False): 0.02,
                th.HeuristicUnharvestedMassHarvestersWaitingToHarvest(use_reserved_mass=True): 0.02,
            }
        raise NotImplementedError