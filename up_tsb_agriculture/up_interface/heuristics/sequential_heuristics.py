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

"""
This module contains the heuristic cost calculators that apply to sequential planning
"""

from typing import Tuple
import math

from up_interface.heuristics.heuristics_base import *

import up_interface.types as upt
from up_interface.fluents import FluentsManagerBase
from up_interface.fluents import FluentNames as fn
from up_interface.problem_encoder.problem_objects import ProblemObjects
from up_interface.problem_encoder.problem_stats import *
from util_arolib.types import MachineType


class HeuristicFieldHarvestingTimestampsWithMaxTimestamp(HeuristicBase):

    """ Heuristic cost calculator where the cost is obtained based on the maximum possible (harvesting) timestamps of the fields """

    def __init__(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 problem_stats: ProblemStats,
                 max_infield_transit_duration = 100,
                 k_field_assigned: float = 1,
                 k_started_harvest: float = 1,
                 k_finished_harvest: float = 1,
                 factor_field_mass: bool = False ):

        """ Heuristic cost calculator initialization

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
        max_infield_transit_duration : float
            Maximum transit duration [s] for transit inside the field (from/to a field access point)
        k_field_assigned : float
            Factor (>=0) applied to the timestamps of when a harvester is assigned to a field
        k_started_harvest : float
            Factor (>=0) applied to the timestamps of when a field starts to be harvested
        k_finished_harvest : float
            Factor (>=0) applied to the timestamps of when a field is finished
        factor_field_mass : bool
            If True, the costs will be computed relative to the field yield mass and the total amount of yield mass to be harvested in all fields
        """

        self.__k_field_assigned = max(0.0, k_field_assigned)
        self.__k_started_harvest = max(0.0, k_started_harvest)
        self.__k_finished_harvest = max(0.0, k_finished_harvest)
        self.__initial_mass_in_fields = None

        if factor_field_mass:
            total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unharvested)
            self.__initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unharvested()).constant_value())

        field_yield_mass_total = fluents_manager.get_fluent(fn.field_yield_mass_total)
        field_area_per_yield_mass = fluents_manager.get_fluent(fn.field_area_per_yield_mass)

        max_harv_working_time_per_area = problem_stats.machines.harv_working_time_per_area.max
        min_harv_speed = problem_stats.machines.harv_transit_speed_empty.min
        min_tv_speed = min( problem_stats.machines.tv_transit_speed_full.min,
                            problem_stats.machines.tv_transit_speed_empty.min)
        min_tv_total_capacity_mass = problem_stats.machines.tv_bunker_mass_capacity.min
        if MachineType.HARVESTER in problem_stats.transit.machine_types_distance_between_all_locations.keys():
            max_transit_dist_harvs = problem_stats.transit.machine_types_distance_between_all_locations.get(MachineType.HARVESTER).max
        else:
            max_transit_dist_harvs = 0
        if MachineType.OLV in problem_stats.transit.machine_types_distance_between_all_locations.keys():
            max_transit_dist_tvs = problem_stats.transit.machine_types_distance_between_all_locations.get(MachineType.OLV).max
        else:
            max_transit_dist_tvs = 0

        max_transit_duration_harvs = max_transit_dist_harvs / min_harv_speed
        max_transit_duration_tvs = max_transit_dist_tvs / min_tv_speed

        max_duration_overloads_total = 0
        max_duration_transit_harvs_total = 0
        max_duration_transit_tvs_total = 0
        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)
            _field_yield_mass_total = float(problem.initial_value(field_yield_mass_total(_field)).constant_value())
            _field_area_per_yield_mass = float(problem.initial_value(field_area_per_yield_mass(_field)).constant_value())
            max_overloads = math.ceil(_field_yield_mass_total/min_tv_total_capacity_mass) + 1

            max_duration_overloads_total += (2
                                             * max_overloads
                                             * max_harv_working_time_per_area
                                             * min_tv_total_capacity_mass
                                             * _field_area_per_yield_mass)
            # note: *2 to compensate for non-working transit during harvesting

            max_duration_transit_harvs_total += ( max_transit_duration_harvs + 2 * max_infield_transit_duration )
            max_duration_transit_tvs_total += 2 * max_overloads * ( max_transit_duration_tvs + 2 * max_infield_transit_duration )

        self.__max_timestamp = (max_duration_overloads_total
                                + max_duration_transit_harvs_total
                                + max_duration_transit_tvs_total)

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = Sum( k_field *
                     ( max_possible_field_timestamp_assigned * k_field_assigned
                     + max_possible_field_timestamp_started_harvest * k_started_harvest
                     + max_possible_field_timestamp_harvested * k_finished_harvest )
                  )
        k_field = 1 if factor_field_mass==False, else field_yield_mass / yield_mass_all_fields

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        state : State
            State

        Returns
        ----------
        cost : float
            Cost
        """

        field_timestamp_assigned = fluents_manager.get_fluent(fn.field_timestamp_assigned)
        field_timestamp_started_harvest = fluents_manager.get_fluent(fn.field_timestamp_started_harvest)
        field_timestamp_harvested = fluents_manager.get_fluent(fn.field_timestamp_harvested)
        field_started_harvest_int = fluents_manager.get_fluent(fn.field_started_harvest_int)
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_yield_mass_total = fluents_manager.get_fluent(fn.field_yield_mass_total)

        sum_timestamps_assigned = 0
        sum_timestamps_started_harvest = 0
        sum_timestamps_harvested = 0
        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)

            k = 1
            if self.__initial_mass_in_fields is not None and self.__initial_mass_in_fields > 0:
                _field_yield_mass_total = float(state.get_value(field_yield_mass_total(_field)).constant_value())
                k = _field_yield_mass_total / self.__initial_mass_in_fields

            if self.__k_field_assigned > 1e-9:
                _field_harvester = state.get_value(field_harvester(_field)).constant_value()
                if _field_harvester.name == objects.no_harvester.name:
                    timestamp = self.__max_timestamp
                else:
                    timestamp = float(state.get_value(field_timestamp_assigned(_field)).constant_value())
                sum_timestamps_assigned += ( k * timestamp )

            if self.__k_started_harvest > 1e-9:
                _field_started_harvest_int = int(state.get_value(field_started_harvest_int(_field)).constant_value())
                if _field_started_harvest_int == 0:
                    timestamp = self.__max_timestamp
                else:
                    timestamp = float(state.get_value(field_timestamp_started_harvest(_field)).constant_value())
                sum_timestamps_started_harvest += ( k * timestamp )

            if self.__k_started_harvest > 1e-9:
                _field_harvested = bool(state.get_value(field_harvested(_field)).constant_value())
                if not _field_harvested:
                    timestamp = self.__max_timestamp
                else:
                    timestamp = float(state.get_value(field_timestamp_harvested(_field)).constant_value())
                sum_timestamps_harvested += ( k * timestamp )


        return sum_timestamps_assigned + sum_timestamps_started_harvest + sum_timestamps_harvested


    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> float:

        """ Obtain the maximum heuristic cost for a given problem

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects

        Returns
        ----------
        max_cost : float
            Maximum cost
        """

        # @todo obtain max_travel_distance and time from problem_stats
        raise NotImplementedError()
        # return None

    def get_max_timestamp(self):
        return self.__max_timestamp


class HeuristicHarvestersWaitingTime(HeuristicBase):

    """ Heuristic cost calculator: cost = harvesters' total waiting time """

    def __init__(self, include_heuristic_cost: bool = False):
        self.__include_heuristic_cost = include_heuristic_cost

        if include_heuristic_cost:
            raise NotImplementedError()

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = harvesters' total waiting time

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        state : State
            State

        Returns
        ----------
        cost : float
            Cost
        """

        harv_waiting_time = fluents_manager.get_fluent(fn.harv_waiting_time)
        field_harvested = None
        if self.__include_heuristic_cost:
            field_harvested = fluents_manager.get_fluent(fn.field_harvested)
            harv_transit_speed_empty = fluents_manager.get_fluent(fn.harv_transit_speed_empty)
            tv_transit_speed_empty = fluents_manager.get_fluent(fn.tv_transit_speed_empty)
            tv_transit_speed_full = fluents_manager.get_fluent(fn.tv_transit_speed_full)
            harv_at_field = fluents_manager.get_fluent(fn.harv_at_field)
            harv_at_field_access = fluents_manager.get_fluent(fn.harv_at_field_access)
            harv_at_init_loc = fluents_manager.get_fluent(fn.harv_at_init_loc)
            default_infield_transit_duration_to_access_point = fluents_manager.get_fluent(fn.default_infield_transit_duration_to_access_point)
            _infield_transit_duration = max(0.0, float(state.get_value(default_infield_transit_duration_to_access_point()).constant_value()))

        total_waiting_time = 0
        total_waiting_time_h = 0
        for harv in objects.harvesters.values():
            if harv is objects.no_harvester:
                continue
            _harv = problem.object(harv.name)
            total_waiting_time += float(state.get_value(harv_waiting_time(_harv)).constant_value())

            if self.__include_heuristic_cost:
                _harv_speed = float(state.get_value(harv_waiting_time(_harv)).constant_value())
                _loc = self.get_machine_current_loc(_harv, state, fluents_manager, objects)
                if _loc is None:
                    continue
                if _loc.type is upt.Field:
                    _field = _loc
                    if not state.get_value(field_harvested(_field)).bool_constant_value():
                        pass

                if _loc.type is upt.FieldAccess:
                    pass
                elif _loc.type is upt.FieldAccess:
                    pass
                else:
                    continue

        return total_waiting_time + total_waiting_time_h

    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> float:

        """ Obtain the maximum heuristic cost for a given problem

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects

        Returns
        ----------
        max_cost : float
            Maximum cost
        """

        # @todo obtain max_travel_distance and time from problem_stats
        raise NotImplementedError()
        # return None

    @staticmethod
    def get_machine_current_loc(machine_obj: Object,
                                state: State,
                                fluents_manager: FluentsManagerBase,
                                objects: ProblemObjects) \
            -> Optional[Object]:
        fluents = []
        if machine_obj.type is upt.Harvester:
            fluents.append( ( fluents_manager.get_fluent(fn.harv_at_field_access), objects.no_field_access ) )
            fluents.append( ( fluents_manager.get_fluent(fn.harv_at_init_loc), objects.no_init_loc ) )
            fluents.append( ( fluents_manager.get_fluent(fn.harv_at_field), objects.no_field ) )
        elif machine_obj.type is upt.Harvester:
            fluents.append( ( fluents_manager.get_fluent(fn.tv_at_field_access), objects.no_field_access ) )
            fluents.append( ( fluents_manager.get_fluent(fn.tv_at_silo_access), objects.no_silo_access ) )
            fluents.append( ( fluents_manager.get_fluent(fn.tv_at_init_loc), objects.no_init_loc ) )
            fluents.append( ( fluents_manager.get_fluent(fn.tv_at_field), objects.no_field ) )

        for f_no in fluents:
            _loc = state.get_value(f_no[0](machine_obj)).constant_value()
            if _loc.name != f_no[1].name:
                return _loc

        return None

    @staticmethod
    def get_field_access_objects(field: Object,
                                 problem: Problem,
                                 fluents_manager: FluentsManagerBase,
                                 objects: ProblemObjects,
                                 state: State) \
            -> List[Object]:

        ret = list()

        field_id = fluents_manager.get_fluent(fn.field_id)
        field_access_field_id = fluents_manager.get_fluent(fn.field_access_field_id)

        _field_id = state.get_value(field_id(field)).constant_value()

        field_accesses = problem.objects(upt.FieldAccess)
        for field_access in field_accesses:
            if field_access.name == objects.no_field_access.name:
                continue
            _field_access_field_id = state.get_value(field_access_field_id(field_access)).constant_value()
            if _field_access_field_id == _field_id:
                ret.append(field_access)

        return ret

    def get_transit_duration_from_faps_to_unreserved_fields(self,
                                                            problem: Problem,
                                                            fluents_manager: FluentsManagerBase,
                                                            objects: ProblemObjects,
                                                            state: State,
                                                            field_accesses_from: List[Object],
                                                            harv_speed: float) \
            -> List[Tuple[float, Object]]:
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_access_field = fluents_manager.get_fluent(fn.field_access_field)

        field_accesses_to = problem.objects(upt.FieldAccess)
        for field_access_to in field_accesses_to:
            field_to = state.get_value(field_access_field(field_access_to)).constant_value()
            if state.get_value(field_harvested(field_to)).bool_constant_value():
                continue
            _harv_to = state.get_value(field_access_field(field_access_to)).constant_value()
            if _harv_to.name == objects.no_harvester.name:
                continue

            for field_access in field_accesses_from:
                pass

        raise NotImplementedError()
        # @todo Finish


class HeuristicTVsWaitingTime(HeuristicBase):

    """ Heuristic cost calculator: cost = transport vehicles' total waiting time """

    def __init__(self):
        pass

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = transport vehicles' total waiting time

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        state : State
            State

        Returns
        ----------
        cost : float
            Cost
        """

        tv_waiting_time = fluents_manager.get_fluent(fn.tv_waiting_time)
        total_waiting_time = 0
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            total_waiting_time += float(state.get_value(tv_waiting_time(_tv)).constant_value())
        return total_waiting_time

    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> float:

        """ Obtain the maximum heuristic cost for a given problem

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects

        Returns
        ----------
        max_cost : float
            Maximum cost
        """

        # @todo obtain max_travel_distance and time from problem_stats
        raise NotImplementedError()
        # return None


class HeuristicHarvestersWaitingTimeAndUnharvestedYieldMass(HeuristicBase):

    """ Heuristic cost calculator: cost = (harvesters' total waiting time) * (1+k1) + k2 """

    def __init__(self, problem: Problem, fluents_manager: FluentsManagerBase,
                 k1: float = 1, k2: float = 1):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        k1 : float
            Constant k1
        k2 : float
            Constant k2
        """

        total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unharvested)
        self.__initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unharvested()).constant_value())
        self.__k1 = k1
        self.__k2 = k2

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = (harvesters' total waiting time) * (1+k1) + k2

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        state : State
            State

        Returns
        ----------
        cost : float
            Cost
        """

        harv_waiting_time = fluents_manager.get_fluent(fn.harv_waiting_time)
        total_harvested_mass = fluents_manager.get_fluent(fn.total_harvested_mass)
        _total_harvested_mass = float(state.get_value(total_harvested_mass()).constant_value())

        if self.__initial_mass_in_fields <= 0:
            k1 = 0
            k2 = 1
        else:
            k1 = self.__k1 * (1 - _total_harvested_mass / self.__initial_mass_in_fields)
            k2 = self.__k2 * (1 - _total_harvested_mass / self.__initial_mass_in_fields)

        total_waiting_time = 0
        for harv in objects.harvesters.values():
            if harv is objects.no_harvester:
                continue
            _harv = problem.object(harv.name)
            total_waiting_time += float(state.get_value(harv_waiting_time(_harv)).constant_value())
        return total_waiting_time * (1+k1) + k2

    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> float:

        """ Obtain the maximum heuristic cost for a given problem

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects

        Returns
        ----------
        max_cost : float
            Maximum cost
        """

        # @todo obtain max_travel_distance and time from problem_stats
        raise NotImplementedError()
        # return None


class HeuristicControlMaxTemporalVariables(HeuristicBase):

    """
    Heuristic cost calculator used only to control that the process temporal parameters (timestamps, waiting times)
    are lower than the given limits, rejecting the plan if the one or more of the temporal parameters' limits is reached

    This calculator only returns cost = 0 or None
    """

    def __init__(self,
                 max_timestamp: Union[float, None] = None,
                 max_harvesters_waiting_time: Union[float, None] = None,
                 max_tvs_waiting_time: Union[float, None] = None):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        max_timestamp : float | None
            Maximum allowed timestamp [s] that a machine (harvester, transport vehicle) can have, i.e., maximum allowed plan duration (disregarded if None)
        max_harvesters_waiting_time : float | None
            Maximum allowed harvesters' waiting time [s] (disregarded if None)
        max_tvs_waiting_time : float | None
            Maximum allowed transport vehicles' waiting time [s] (disregarded if None)
        """

        self.__max_timestamp = max_timestamp
        self.__max_harvesters_waiting_time = max_harvesters_waiting_time
        self.__max_tvs_waiting_time = max_tvs_waiting_time

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        state : State
            State

        Returns
        ----------
        cost : float
            Cost
        """

        def _on_abort(reason: str):

            # #debug!
            # print(f'[{type(self).__name__}] aborted state {id(state)}: {reason}')

            return None

        if self.__max_timestamp is not None:
            harv_timestamp = fluents_manager.get_fluent(fn.harv_timestamp)
            tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)
            for harv in objects.harvesters.values():
                if harv is objects.no_harvester:
                    continue
                _harv = problem.object(harv.name)
                _harv_timestamp = float(state.get_value(harv_timestamp(_harv)).constant_value())
                if _harv_timestamp >= self.__max_timestamp:
                    return _on_abort(f'harv_timestamp({harv}) ({_harv_timestamp}) >= max_timestamp ({self.__max_timestamp})')
            for tv in objects.tvs.values():
                _tv = problem.object(tv.name)
                _tv_timestamp = float(state.get_value(tv_timestamp(_tv)).constant_value())
                if _tv_timestamp >= self.__max_timestamp:
                    return _on_abort(f'tv_timestamp({tv}) ({_tv_timestamp}) >= max_timestamp ({self.__max_timestamp})')

        if self.__max_harvesters_waiting_time is not None:
            harv_waiting_time = fluents_manager.get_fluent(fn.harv_waiting_time)
            _sum_waiting_time = 0.0
            for harv in objects.harvesters.values():
                if harv is objects.no_harvester:
                    continue
                _harv = problem.object(harv.name)
                _sum_waiting_time += float(state.get_value(harv_waiting_time(_harv)).constant_value())
            if _sum_waiting_time >= self.__max_harvesters_waiting_time:
                return _on_abort(f'sum_waiting_time_harvs ({_sum_waiting_time}) >= max_harvesters_waiting_time ({self.__max_harvesters_waiting_time})')

        if self.__max_tvs_waiting_time is not None:
            tv_waiting_time = fluents_manager.get_fluent(fn.tv_waiting_time)
            _sum_waiting_time = 0.0
            for tv in objects.tvs.values():
                _tv = problem.object(tv.name)
                _sum_waiting_time += float(state.get_value(tv_waiting_time(_tv)).constant_value())
            if _sum_waiting_time >= self.__max_tvs_waiting_time:
                return _on_abort(f'sum_waiting_time_tvs ({_sum_waiting_time}) >= max_tvs_waiting_time ({self.__max_tvs_waiting_time})')

        return 0

    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> float:

        """ Obtain the maximum heuristic cost for a given problem

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects

        Returns
        ----------
        max_cost : float
            Maximum cost
        """

        return 0


class HeuristicControlAverageTemporalVariablesWithHarvestedMass(HeuristicBase):

    """
    Heuristic cost calculator used only to control that the rate of process temporal values (timestamps, waiting times)
    per harvested yield mass are lower than average values obtained from temporal values of a valid plan,
    rejecting the plan if the one or more of the temporal parameters' limits is reached

    The limit values are average temporal parameters per harvested yield mass (e.g., average harvesters' waiting time / harvested mass)
    If any current state average value is >= factor * avg_val -> the heuristic cost will be None, otherwise cost = 0.
    """

    class ControlValue:

        """ Class holding the control values and respective factors """

        def __init__(self, val: float, factor: float = 3):

            """ Initializer.

            If the state average value is >= factor * val -> the heuristic cost will be None, otherwise cost = 0.

            Parameters
            ----------
            val : float
                Value used for comparison.
            factor : float
                Factor applied to the value to obtain the limit.
            """

            self.val = val
            self.factor = factor

    def __init__(self,
                 problem: Problem, fluents_manager: FluentsManagerBase,
                 max_timestamp: Union['HeuristicControlAverageTemporalVariablesWithHarvestedMass.ControlValue', None] = None,
                 max_harvesters_waiting_time: Union['HeuristicControlAverageTemporalVariablesWithHarvestedMass.ControlValue', None] = None,
                 max_tvs_waiting_time: Union['HeuristicControlAverageTemporalVariablesWithHarvestedMass.ControlValue', None] = None):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        max_timestamp : ControlValue | None
            Contains the maximum machine (harvester, transport vehicle) timestamp [s] (i.e., plan duration) of a known valid plan and the respective factor (disregarded if None)
        max_harvesters_waiting_time : ControlValue | None
            Contains the total harvesters' waiting time [s] of a known valid plan and the respective factor (disregarded if None)
        max_tvs_waiting_time : ControlValue | None
            Contains the total transport vehicles' waiting time [s] of a known valid plan and the respective factor (disregarded if None)
        """

        total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unharvested)
        initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unharvested()).constant_value())

        self.__max_avg_timestamp = None if max_timestamp is None or initial_mass_in_fields is None or initial_mass_in_fields < 1e-9 \
            else max_timestamp.val / initial_mass_in_fields * max_timestamp.factor
        self.__max_avg_harvesters_waiting_time = None if max_harvesters_waiting_time is None or initial_mass_in_fields is None or initial_mass_in_fields < 1e-9 \
            else max_harvesters_waiting_time.val / initial_mass_in_fields * max_harvesters_waiting_time.factor
        self.__max_avg_tvs_waiting_time = None if max_tvs_waiting_time is None or initial_mass_in_fields is None or initial_mass_in_fields < 1e-9 \
            else max_tvs_waiting_time.val / initial_mass_in_fields * max_tvs_waiting_time.factor

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        If any state average value is >= factor * avg_val -> the heuristic cost will be None, otherwise cost = 0.

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        state : State
            State

        Returns
        ----------
        cost : float
            Cost
        """

        total_harvested_mass = fluents_manager.get_fluent(fn.total_harvested_mass)
        _total_harvested_mass = float(problem.initial_value(total_harvested_mass()).constant_value())

        if _total_harvested_mass <= 1e-9:
            return 0

        if self.__max_avg_timestamp is not None:
            harv_timestamp = fluents_manager.get_fluent(fn.harv_timestamp)
            tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)
            for harv in objects.harvesters.values():
                if harv is objects.no_harvester:
                    continue
                _harv = problem.object(harv.name)
                _harv_timestamp = float(state.get_value(harv_timestamp(_harv)).constant_value())
                if _harv_timestamp / _total_harvested_mass >= self.__max_avg_timestamp:
                    return None
            for tv in objects.tvs.values():
                _tv = problem.object(tv.name)
                _tv_timestamp = float(state.get_value(tv_timestamp(_tv)).constant_value())
                if _tv_timestamp / _total_harvested_mass >= self.__max_avg_timestamp:
                    return None

        if self.__max_avg_harvesters_waiting_time is not None:
            harv_waiting_time = fluents_manager.get_fluent(fn.harv_waiting_time)
            _sum_waiting_time = 0.0
            for harv in objects.harvesters.values():
                if harv is objects.no_harvester:
                    continue
                _harv = problem.object(harv.name)
                _sum_waiting_time += float(state.get_value(harv_waiting_time(_harv)).constant_value())
            if _sum_waiting_time / _total_harvested_mass >= self.__max_avg_harvesters_waiting_time:
                return None

        if self.__max_avg_tvs_waiting_time is not None:
            tv_waiting_time = fluents_manager.get_fluent(fn.tv_waiting_time)
            _sum_waiting_time = 0.0
            for tv in objects.tvs.values():
                _tv = problem.object(tv.name)
                _sum_waiting_time += float(state.get_value(tv_waiting_time(_tv)).constant_value())
            if _sum_waiting_time / _total_harvested_mass >= self.__max_avg_tvs_waiting_time:
                return None

        return 0

    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> float:

        """ Obtain the maximum heuristic cost for a given problem

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects

        Returns
        ----------
        max_cost : float
            Maximum cost
        """

        return 0


class HeuristicControlAverageWaitingTimesWithMaxTimestamp(HeuristicBase):

    """
    Heuristic cost calculator used only to control that the process duration is not higher than a given limit and
    that the rate of machine waiting times per process duration are lower than average values obtained from temporal
    values of a valid plan, rejecting the plan if the one or more of the temporal parameters' limits is reached

    The limit values are average waiting times per plan duration (e.g., average harvesters' waiting time / plan duration)
    If the current process timestamp is > max_timestamp or any current state average waiting times is >= factor * avg_val -> the heuristic cost will be None, otherwise cost = 0.
    """

    class ControlValue:

        """ Class holding the control values and respective factors """

        def __init__(self, val: float, factor: float = 3):

            """ Initializer.

            If the state average value is >= factor * val -> the heuristic cost will be None, otherwise cost = 0.

            Parameters
            ----------
            val : float
                Value used for comparison.
            factor : float
                Factor applied to the value to obtain the limit.
            """

            self.val = val
            self.factor = factor

    def __init__(self,
                 max_timestamp: float,
                 max_harvesters_waiting_time: Union['HeuristicControlAverageTemporalVariablesWithHarvestedMass.ControlValue', None] = None,
                 max_tvs_waiting_time: Union['HeuristicControlAverageTemporalVariablesWithHarvestedMass.ControlValue', None] = None):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        max_timestamp : float
            Duration [s] of a known valid plan.
        max_harvesters_waiting_time : ControlValue | None
            Contains the total harvesters' waiting time [s] of a known valid plan and the respective factor (disregarded if None)
        max_tvs_waiting_time : ControlValue | None
            Contains the total transport vehicles' waiting time [s] of a known valid plan and the respective factor (disregarded if None)
        """

        self.__max_timestamp = max_timestamp + 1 if max_timestamp is not None and max_timestamp > 1e-9 else None
        self.__max_avg_harvesters_waiting_time = None if max_harvesters_waiting_time is None \
            else max_harvesters_waiting_time.val / max_timestamp * max_harvesters_waiting_time.factor
        self.__max_avg_tvs_waiting_time = None if max_tvs_waiting_time is None \
            else max_tvs_waiting_time.val / max_timestamp * max_tvs_waiting_time.factor

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        If the current process timestamp is > max_timestamp or any current state average waiting times is >= factor * avg_val -> the heuristic cost will be None, otherwise cost = 0.

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        state : State
            State

        Returns
        ----------
        cost : float
            Cost
        """

        if self.__max_timestamp is None or self.__max_avg_harvesters_waiting_time is None and self.__max_avg_tvs_waiting_time:
            return 0

        harv_timestamp = fluents_manager.get_fluent(fn.harv_timestamp)
        tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)

        max_timestamp = 0.0

        for harv in objects.harvesters.values():
            if harv is objects.no_harvester:
                continue
            _harv = problem.object(harv.name)
            max_timestamp = max(max_timestamp, float(state.get_value(harv_timestamp(_harv)).constant_value()))

        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            max_timestamp = max(max_timestamp, float(state.get_value(tv_timestamp(_tv)).constant_value()))

        if max_timestamp > self.__max_timestamp:
            return None

        if max_timestamp <= 1e-9:
            return 0

        if self.__max_avg_harvesters_waiting_time is not None:
            harv_waiting_time = fluents_manager.get_fluent(fn.harv_waiting_time)
            _sum_waiting_time = 0.0
            for harv in objects.harvesters.values():
                if harv is objects.no_harvester:
                    continue
                _harv = problem.object(harv.name)
                _sum_waiting_time += float(state.get_value(harv_waiting_time(_harv)).constant_value())
            if _sum_waiting_time / max_timestamp >= self.__max_avg_harvesters_waiting_time:
                return None

        if self.__max_avg_tvs_waiting_time is not None:
            tv_waiting_time = fluents_manager.get_fluent(fn.tv_waiting_time)
            _sum_waiting_time = 0.0
            for tv in objects.tvs.values():
                _tv = problem.object(tv.name)
                _sum_waiting_time += float(state.get_value(tv_waiting_time(_tv)).constant_value())
            if _sum_waiting_time / max_timestamp >= self.__max_avg_tvs_waiting_time:
                return None

        return 0

    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> float:

        """ Obtain the maximum heuristic cost for a given problem

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects

        Returns
        ----------
        max_cost : float
            Maximum cost
        """

        return 0
