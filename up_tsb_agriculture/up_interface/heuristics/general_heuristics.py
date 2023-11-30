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
This module contains the heuristic cost calculators that apply to both sequential and temporal planning
"""

from up_interface.heuristics.heuristics_base import *

import up_interface.types as upt
from up_interface.fluents import FluentsManagerBase
from up_interface.fluents import FluentNames as fn
from up_interface.problem_encoder.problem_objects import ProblemObjects
from up_interface.problem_encoder.problem_stats import *
from util_arolib.types import MachineType


class HeuristicInitialYieldMassInFieldsMinusHarvested(HeuristicBase):

    """ Heuristic cost calculator: cost [kg] = initial yield mass in all fields - harvested yield mass in all fields """

    def __init__(self, problem: Problem, fluents_manager: FluentsManagerBase):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        """

        total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        if total_yield_mass_in_fields_unharvested is None:
            total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unharvested)
        self.__initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unharvested()).constant_value())

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> float:

        """ Obtain the heuristic cost for a given problem and state

        cost [kg] = initial yield mass in all fields - harvested yield mass in all fields

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

        return max(0.0, self.__initial_mass_in_fields - float(state.get_value(total_harvested_mass()).constant_value()))

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

        return self.__initial_mass_in_fields


class HeuristicInitialYieldMassInFieldsMinusAssigned(HeuristicBase):
    """ Heuristic cost calculator: cost [kg] = initial yield mass in all fields - yield mass of all fields assigned to a harvester """

    def __init__(self, problem: Problem, fluents_manager: FluentsManagerBase):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        """

        total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        if total_yield_mass_in_fields_unharvested is None:
            total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unharvested)
        self.__initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unharvested()).constant_value())

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> float:

        """ Obtain the heuristic cost for a given problem and state

        cost [kg] = initial yield mass in all fields - yield mass of all fields assigned to a harvester

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

        field_yield_mass_total = fluents_manager.get_fluent(fn.field_yield_mass_total)
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        mass_total_assigned_fields = 0.0
        mass_total_unassigned_fields = 0.0

        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)
            _field_harv = state.get_value(field_harvester(_field)).constant_value()
            if _field_harv.name != objects.no_harvester.name:
                mass_total_assigned_fields += float(state.get_value(field_yield_mass_total(_field)).constant_value())
                # print(f'Field: {field.name} -: harv: {_field_harv.name}')
            else:
                mass_total_unassigned_fields += float(state.get_value(field_yield_mass_total(_field)).constant_value())

        # if abs(self.__initial_mass_in_fields - mass_total_assigned_fields - mass_total_unassigned_fields) > 1e-3:
        #     raise ValueError("HeuristicInitialYieldMassInFieldsMinusAssigned mass missmatch")
        # else:
        #     print(f'mass_total_assigned_fields = {mass_total_assigned_fields}/{self.__initial_mass_in_fields}')

        return max(0.0, self.__initial_mass_in_fields - mass_total_assigned_fields)

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

        return self.__initial_mass_in_fields


class HeuristicInitialYieldMassToStoreMinusStored(HeuristicBase):
    """ Heuristic cost calculator: cost [kg] = total yield mass to be stored in the silos (initial yield mass in fields + initial yield mass in transport vehicles) - yield mass stores in all silos """

    def __init__(self, problem: Problem, fluents_manager: FluentsManagerBase):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        """

        total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        if total_yield_mass_in_fields_unharvested is None:
            total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unharvested)
        initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unharvested()).constant_value())

        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tvs = problem.objects(upt.TransportVehicle)
        mass_in_tvs = 0.
        for tv in tvs:
            mass_in_tvs += float(problem.initial_value(tv_bunker_mass(tv)).constant_value())

        self.__initial_mass_to_store = initial_mass_in_fields + mass_in_tvs

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> float:

        """ Obtain the heuristic cost for a given problem and state

        cost [kg] = total yield mass to be stored in the silos (initial yield mass in fields + initial yield mass in transport vehicles) - yield mass stores in all silos

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

        total_yield_mass_in_silos = fluents_manager.get_fluent(fn.total_yield_mass_in_silos)
        return self.__initial_mass_to_store - float(state.get_value(total_yield_mass_in_silos()).constant_value())

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
        return self.__initial_mass_to_store


class HeuristicInitialYieldMassToStoreMinusReserved(HeuristicBase):
    """ Heuristic cost calculator: cost [kg] = total yield mass to be stored in the silos (initial yield mass in fields + initial yield mass in transport vehicles) - yield mass reserved to be stored in all silos """

    def __init__(self, problem: Problem, fluents_manager: FluentsManagerBase):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        """

        total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        if total_yield_mass_in_fields_unharvested is None:
            total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unharvested)
        initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unharvested()).constant_value())

        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tvs = problem.objects(upt.TransportVehicle)
        mass_in_tvs = 0.
        for tv in tvs:
            mass_in_tvs += float(problem.initial_value(tv_bunker_mass(tv)).constant_value())

        self.__initial_mass_to_store = initial_mass_in_fields + mass_in_tvs

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> float:

        """ Obtain the heuristic cost for a given problem and state

        cost [kg] = total yield mass to be stored in the silos (initial yield mass in fields + initial yield mass in transport vehicles) - yield mass reserved to be stored in all silos

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

        total_yield_mass_reserved_in_silos = fluents_manager.get_fluent(fn.total_yield_mass_reserved_in_silos)
        return self.__initial_mass_to_store - float(state.get_value(total_yield_mass_reserved_in_silos()).constant_value())

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
        return self.__initial_mass_to_store



class HeuristicCountUnassignedFields(HeuristicBase):
    """ Heuristic cost calculator: cost = amount of fields that have no harvester assigned to them """

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> float:

        """ Obtain the heuristic cost for a given problem and state

        cost = amount of fields that have no harvester assigned to them

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

        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        count_unassigned_fields = 0
        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)
            if state.get_value(field_harvested(_field)).bool_constant_value():
                continue
            _field_harv = state.get_value(field_harvester(_field)).constant_value()
            if _field_harv.name == objects.no_harvester.name:
                count_unassigned_fields += 1
        return count_unassigned_fields

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
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        count_unassigned_fields = 0
        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)
            if problem.initial_value(field_harvested).bool_constant_value():
                continue
            _field_harv = problem.initial_value(field_harvester).get_value(field_harvester(_field)).constant_value()
            if _field_harv.name == objects.no_harvester.name:
                count_unassigned_fields += 1
        return count_unassigned_fields


class HeuristicYieldMassUnassignedFields(HeuristicBase):
    """ Heuristic cost calculator: cost [kg] = yield mass in all fields that have no harvester assigned to them """

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> float:

        """ Obtain the heuristic cost for a given problem and state

        cost [kg] = yield mass in all fields that have no harvester assigned to them

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

        field_yield_mass_total = fluents_manager.get_fluent(fn.field_yield_mass_total)
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        mass_total_unassigned_fields = 0.0
        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)
            if state.get_value(field_harvested(_field)).bool_constant_value():
                continue
            _field_harv = state.get_value(field_harvester(_field)).constant_value()
            if _field_harv.name == objects.no_harvester.name:
                mass_total_unassigned_fields += float(state.get_value(field_yield_mass_total(_field)).constant_value())
        return mass_total_unassigned_fields

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
        field_yield_mass_total = fluents_manager.get_fluent(fn.field_yield_mass_total)
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        mass_total_unassigned_fields = 0.0
        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)
            if problem.initial_value(field_harvested(_field)).bool_constant_value():
                continue
            _field_harv = problem.initial_value(field_harvester(_field)).constant_value()
            if _field_harv.name == objects.no_harvester.name:
                mass_total_unassigned_fields += float(problem.initial_value(field_yield_mass_total(_field)).constant_value())
        return mass_total_unassigned_fields


class HeuristicHarvestersTransitTime(HeuristicBase):
    """ Heuristic cost calculator: cost = (transit time of all harvesters) * cost/second """

    def __init__(self, cost_per_second: float):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        cost_per_second : float
            Cost per second of transit
        """

        self.__cost_per_second = cost_per_second

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> float:

        """ Obtain the heuristic cost for a given problem and state

        cost = (transit time of all harvesters) * cost/second

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

        harv_transit_time = fluents_manager.get_fluent(fn.harv_transit_time)
        total_transit_time = 0.0
        for harv in objects.harvesters.values():
            if harv is objects.no_harvester:
                continue
            _harv = problem.object(harv.name)
            total_transit_time += float(state.get_value(harv_transit_time(_harv)).constant_value())

        return total_transit_time * self.__cost_per_second

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


class HeuristicTVsTransitTime(HeuristicBase):
    """ Heuristic cost calculator: cost = (transit time of all transport vehicles) * cost/second """

    def __init__(self, cost_per_second: float):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        cost_per_second : float
            Cost per second of transit
        """
        self.__cost_per_second = cost_per_second

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> float:

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

        tv_transit_time = fluents_manager.get_fluent(fn.tv_transit_time)
        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        total_cost = 0.0
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            if self.__cost_per_second is None:
                total_cost += ( float(state.get_value(tv_transit_time(_tv)).constant_value())
                                * float(state.get_value(tv_total_capacity_mass(_tv)).constant_value()) )
            else:
                total_cost += ( float(state.get_value(tv_transit_time(_tv)).constant_value()) * self.__cost_per_second )
        return total_cost

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


class HeuristicHarvestersTransitDistanceWithBaseCost(HeuristicBase):
    """ Heuristic cost calculator: cost computed based on the distanced travelled by all harvesters and a base distance cost (computed based on the problem properties) """

    def __init__(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 problem_stats: ProblemStats,
                 cost_per_meter: Union[float, None] = None):

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
        cost_per_meter : float | None
            Cost per meter of transit
        """

        harvs_count = 0
        harvs = problem.objects(upt.Harvester)
        for harv in harvs:
            if harv.name != objects.no_harvester.name:
                harvs_count += 1

        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        fields_count = 0
        fields = problem.objects(upt.Field)
        for field in fields:
            if field.name != objects.no_harvester.name \
                    and not problem.initial_value(field_harvested(field)).bool_constant_value():
                fields_count += 1

        max_dist_init = 0
        if MachineType.HARVESTER in problem_stats.transit.machine_types_distance_from_init_locations_to_fields:
            max_dist_init = problem_stats.transit.machine_types_distance_from_init_locations_to_fields[MachineType.HARVESTER].max
        max_dist_between_fields = problem_stats.transit.distance_between_field_access_points_different_fields.max
        self.__base_cost = (harvs_count * max_dist_init
                            + (fields_count-harvs_count) * max_dist_between_fields
                            + (harvs_count-1) * max(max_dist_init, max_dist_between_fields))
        self.__ref_distance = max(max_dist_init, max_dist_between_fields)
        if cost_per_meter is not None:
            self.__cost_per_meter = cost_per_meter
        elif self.__base_cost > 0:
            self.__cost_per_meter = problem_stats.fields.yield_mass_total.max / self.__base_cost
        else:
            self.__cost_per_meter = 0

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> float:

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
        harv_transit_time = fluents_manager.get_fluent(fn.harv_transit_time)
        harv_transit_speed_empty = fluents_manager.get_fluent(fn.harv_transit_speed_empty)
        total_transit_dist = 0.0
        for harv in objects.harvesters.values():
            if harv is objects.no_harvester:
                continue
            _harv = problem.object(harv.name)
            speed = float(state.get_value(harv_transit_speed_empty(_harv)).constant_value())
            transit_time = float(state.get_value(harv_transit_time(_harv)).constant_value())
            total_transit_dist += (speed * transit_time)
        if total_transit_dist < 1e-6:
            return self.__base_cost
        return self.__cost_per_meter * (self.__base_cost - self.__ref_distance / total_transit_dist)

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
