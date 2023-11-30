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
This module contains the heuristic cost calculators that apply to temporal planning
"""

from typing import Tuple

from up_interface.heuristics.heuristics_base import *

import up_interface.types as upt
from up_interface.fluents import FluentsManagerBase
from up_interface.fluents import FluentNames as fn
import up_interface.config as conf
from up_interface.problem_encoder.problem_objects import ProblemObjects
from up_interface.heuristics.general_heuristics import HeuristicCountUnassignedFields


class HeuristicInitialYieldMassInFieldsMinusReserved(HeuristicBase):

    """ Heuristic cost calculator: cost [kg] = initial yield mass in all fields - yield mass in all fields reserved for overload/harvest """

    def __init__(self, problem: Problem, fluents_manager: FluentsManagerBase):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        """

        total_yield_mass_in_fields_unreserved = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        self.__initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unreserved()).constant_value())

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost [kg] = initial yield mass in all fields - yield mass in all fields reserved for overload/harvest

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

        total_yield_mass_reserved = fluents_manager.get_fluent(fn.total_yield_mass_reserved)

        return self.__initial_mass_in_fields - float(state.get_value(total_yield_mass_reserved()).constant_value())

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


class HeuristicInitialYieldMassInFieldsMinusPotentiallyReserved(HeuristicBase):

    """ Heuristic cost calculator: cost [kg] = initial yield mass in all fields - yield mass in all fields 'almost' reserved for overload/harvest """

    def __init__(self, problem: Problem, fluents_manager: FluentsManagerBase):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        """

        total_yield_mass_in_fields_unreserved = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        self.__initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unreserved()).constant_value())

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

        total_yield_mass_potentially_reserved = fluents_manager.get_fluent(fn.total_yield_mass_potentially_reserved)
        return max(0.0, self.__initial_mass_in_fields - float(state.get_value(total_yield_mass_potentially_reserved()).constant_value()))

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


class HeuristicInitialYieldMassInFieldsMinusPlannedHarvested(HeuristicBase):

    """ Heuristic cost calculator: cost [kg] = initial yield mass in all fields - harvested yield mass in all fields - yield mass to be harvested in ongoing overloads """

    def __init__(self, problem: Problem, fluents_manager: FluentsManagerBase):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        """

        total_yield_mass_in_fields_unreserved = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        self.__initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unreserved()).constant_value())

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost [kg] = initial yield mass in all fields - harvested yield mass in all fields - yield mass to be harvested in ongoing overloads

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

        total_harvested_mass_planned = fluents_manager.get_fluent(fn.total_harvested_mass_planned)
        return max(0.0, self.__initial_mass_in_fields - float(state.get_value(total_harvested_mass_planned()).constant_value()))

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

        total_yield_mass_in_fields_unreserved = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        initial_mass_in_fields = float(problem.initial_value(total_yield_mass_in_fields_unreserved()).constant_value())

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
                 state: State) -> Union[float, None]:

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


class HeuristicTotalUnreservedYieldMass(HeuristicBase):

    """ Heuristic cost calculator: cost [kg] = total yield mass in all fields that has not been harvested or reserved for overload/harvest """

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

        total_yield_mass_in_fields_unreserved = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        return max(0.0, float(state.get_value(total_yield_mass_in_fields_unreserved()).constant_value()))

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

        total_yield_mass_in_fields_unreserved = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        return float(problem.initial_value(total_yield_mass_in_fields_unreserved).constant_value())


class HeuristicTotalUnreservedYieldMass2(HeuristicBase):

    """ Heuristic cost calculator: cost [kg] = total yield mass in all fields that has not been harvested or reserved for overload/harvest """

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost [kg] = total yield mass in all fields that has not been harvested or reserved for overload/harvest

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

        field_yield_mass_after_reserve = fluents_manager.get_fluent(fn.field_yield_mass_after_reserve)
        mass_total_unreserved_2 = 0.0
        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)
            mass_total_unreserved_2 += max(0.0, float(state.get_value(field_yield_mass_after_reserve(_field)).constant_value()))
        return mass_total_unreserved_2

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

        field_yield_mass_after_reserve = fluents_manager.get_fluent(fn.field_yield_mass_after_reserve)
        mass_total_unreserved_2 = 0.0
        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)
            mass_total_unreserved_2 += float(problem.initial_value(field_yield_mass_after_reserve).constant_value())
        return mass_total_unreserved_2


class HeuristicTotalUnreservedYieldMassWithCountUnassignedFields(HeuristicBase):

    """
    Heuristic cost calculator: cost [kg] = total yield mass in all fields that has not been harvested or reserved for overload/harvest * a factor based on the amount of fields that have no harvester assigned to them

    cost [kg] = mass_total_unreserved * (1 + k * count_unassigned_fields)
    """

    def __init__(self, k: float = 0.1):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        k : float
            Factor for count of unassigned fields
        """

        self.__k = k

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost [kg] = mass_total_unreserved * (1 + k * count_unassigned_fields)

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

        mass_total_unreserved = HeuristicTotalUnreservedYieldMass().get_cost(problem, fluents_manager, objects, state)
        count_unassigned_fields = HeuristicCountUnassignedFields().get_cost(problem, fluents_manager, objects, state)
        return mass_total_unreserved * (1 + self.__k * count_unassigned_fields)

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

        mass_total_unreserved = HeuristicTotalUnreservedYieldMass().get_max_cost(problem, fluents_manager, objects)
        count_unassigned_fields = HeuristicCountUnassignedFields().get_max_cost(problem, fluents_manager, objects)
        return mass_total_unreserved * (1 + max(0.0, self.__k * count_unassigned_fields))


class HeuristicMassToOverloadTvsWaitingOld(HeuristicBase):

    """ Heuristic cost calculator: cost [kg] = total yield mass to be overloaded (reserved) by transport vehicles that are waiting to overload """

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost [kg] = total yield mass to be overloaded (reserved) by transport vehicles that are waiting to overload

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

        tv_mass_to_overload = fluents_manager.get_fluent(fn.tv_mass_to_overload)
        tv_waiting_to_overload = fluents_manager.get_fluent(fn.tv_waiting_to_overload)
        mass_to_overload_tvs_waiting = 0.0
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            if state.get_value(tv_waiting_to_overload(_tv)).bool_constant_value():
                mass_to_overload_tvs_waiting += float(state.get_value(tv_mass_to_overload(_tv)).constant_value())
        return mass_to_overload_tvs_waiting

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

        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        mass_to_overload_tvs_waiting = 0.0
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            mass_to_overload_tvs_waiting += float(problem.initial_value(tv_total_capacity_mass(_tv)).constant_value())
        return mass_to_overload_tvs_waiting


class HeuristicBunkerCapacityTvsWaitingToOverloadOld(HeuristicBase):

    """ Heuristic cost calculator: cost = Sum( mass bunker capacity of transport vehicle that are waiting to overload * factor ) """

    def __init__(self, cost_per_machine_waiting: Union[float, None] = None):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        cost_per_machine_waiting : float|None
            Cost per machine that is waiting. If None, the cost will be the machine's bunker mass capacity.
        """

        self.__cost_per_machine_waiting = cost_per_machine_waiting

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = Sum( mass bunker capacity of transport vehicle that are waiting to overload * factor )

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

        tv_waiting_to_overload = fluents_manager.get_fluent(fn.tv_waiting_to_overload)
        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        cost = 0.0
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            if state.get_value(tv_waiting_to_overload(_tv)).bool_constant_value():
                if self.__cost_per_machine_waiting is not None:
                    cost += self.__cost_per_machine_waiting
                else:
                    cost += float(state.get_value(tv_total_capacity_mass(_tv)).constant_value())
        return cost

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

        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        cost = 0.0
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            if self.__cost_per_machine_waiting is not None:
                cost += max(0.0, self.__cost_per_machine_waiting)
            else:
                cost += float(problem.initial_value(tv_total_capacity_mass(_tv)).constant_value())
        return cost


class HeuristicMassToOverloadTvsWaiting(HeuristicBase):

    """ Heuristic cost calculator: cost [kg] = total yield mass to be overloaded (reserved) by transport vehicles that are waiting to overload """

    def __init__(self):
        if conf.gps.cost_windows.use_old_implementation_waiting_overload:  # @todo Remove when the tv_waiting_to_overload_id approach is working
            self.__old = HeuristicMassToOverloadTvsWaitingOld()

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

        if conf.gps.cost_windows.use_old_implementation_waiting_overload:  # @todo Remove when the tv_waiting_to_overload_id approach is working
            return self.__old.get_cost(problem, fluents_manager, objects, state)

        tv_mass_to_overload = fluents_manager.get_fluent(fn.tv_mass_to_overload)
        tv_waiting_to_overload_id = fluents_manager.get_fluent(fn.tv_waiting_to_overload_id)
        mass_to_overload_tvs_waiting = 0.0
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            if int(state.get_value(tv_waiting_to_overload_id(_tv)).constant_value()) > 0:
                mass_to_overload_tvs_waiting += float(state.get_value(tv_mass_to_overload(_tv)).constant_value())
        return mass_to_overload_tvs_waiting

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

        if conf.gps.cost_windows.use_old_implementation_waiting_overload:  # @todo Remove when the tv_waiting_to_overload_id approach is working
            return self.__old.get_max_cost(problem, fluents_manager, objects)

        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        mass_to_overload_tvs_waiting = 0.0
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            mass_to_overload_tvs_waiting += float(problem.initial_value(tv_total_capacity_mass(_tv)).constant_value())
        return mass_to_overload_tvs_waiting


class HeuristicBunkerCapacityTvsWaitingToOverload(HeuristicBase):

    """ Heuristic cost calculator: cost = Sum(mass bunker capacity of transport vehicle that is waiting to overload * factor) """

    def __init__(self, cost_per_machine_waiting: Union[float, None] = None, increase_factor_per_machine_waiting: bool = True):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        cost_per_machine_waiting : float|None
            Cost per machine that is waiting. If None, the cost will be the machine's bunker mass capacity.
        increase_factor_per_machine_waiting : bool
            If True, a higher cost will be given to the machines that have been waiting longer.
        """

        if conf.gps.cost_windows.use_old_implementation_waiting_overload:  # @todo Remove when the tv_waiting_to_overload_id approach is working
            self.__old = HeuristicBunkerCapacityTvsWaitingToOverloadOld(cost_per_machine_waiting)

        self.__cost_per_machine_waiting = cost_per_machine_waiting
        self.__increase_factor_per_machine_waiting = increase_factor_per_machine_waiting

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

        if conf.gps.cost_windows.use_old_implementation_waiting_overload:  # @todo Remove when the tv_waiting_to_overload_id approach is working
            return self.__old.get_cost(problem, fluents_manager, objects, state)

        tv_waiting_to_overload_id = fluents_manager.get_fluent(fn.tv_waiting_to_overload_id)
        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        cost = 0.0
        count_machines_waiting = 0
        masses_tvs_waiting: List[Tuple[int, float]] = list()
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            _tv_waiting_to_overload_id = int(state.get_value(tv_waiting_to_overload_id(_tv)).constant_value())
            if _tv_waiting_to_overload_id > 0:
                count_machines_waiting += 1
                tv_cost = self.__cost_per_machine_waiting \
                    if self.__cost_per_machine_waiting is not None \
                    else float(state.get_value(tv_total_capacity_mass(_tv)).constant_value())
                if not self.__increase_factor_per_machine_waiting:
                    cost += tv_cost
                else:
                    masses_tvs_waiting.append( ( _tv_waiting_to_overload_id,  tv_cost ) )

        if len(masses_tvs_waiting) > 0:
            masses_tvs_waiting.sort(key=lambda x: x[0])
            max_id = masses_tvs_waiting[-1][0]
            for i, mass in enumerate(masses_tvs_waiting):
                cost += ( mass[1] * (max_id - mass[0]) )

        return cost

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

        if conf.gps.cost_windows.use_old_implementation_waiting_overload:  # @todo Remove when the tv_waiting_to_overload_id approach is working
            return self.__old.get_max_cost(problem, fluents_manager, objects)

        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        cost = 0.0
        count_machines_waiting = 0
        masses_tvs_waiting = list()
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            count_machines_waiting += 1
            tv_cost = max(0.0, self.__cost_per_machine_waiting) \
                if self.__cost_per_machine_waiting is not None \
                else float(problem.initial_value(tv_total_capacity_mass(_tv)).constant_value())
            if not self.__increase_factor_per_machine_waiting:
                cost += tv_cost
            else:
                masses_tvs_waiting.append( tv_cost )

        if len(masses_tvs_waiting) > 0:
            masses_tvs_waiting.sort(reverse=True)
            max_id = len(masses_tvs_waiting) - 1
            for i, mass in enumerate(masses_tvs_waiting):
                cost += ( mass * (max_id - i) )

        return cost


class HeuristicRejectHarvestersDisabledToOverload(HeuristicBase):

    """
    Heuristic cost calculator used solely to reject states where the exist harvesters that have been disabled to overload

    The returned cost will be None if one or more harvesters are disabled to overload; otherwise cost = 0
    """

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = None if one or more harvesters are disabled to overload; otherwise cost = 0

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

        harv_enabled_to_overload = fluents_manager.get_fluent(fn.harv_enabled_to_overload)
        harv_overload_id = fluents_manager.get_fluent(fn.harv_overload_id)

        if harv_enabled_to_overload is None:
            return 0

        for harv in objects.harvesters.values():
            if harv is objects.no_harvester:
                continue
            _harv = problem.object(harv.name)
            _harv_enabled_to_overload = int(state.get_value(harv_enabled_to_overload(_harv)).constant_value())
            _harv_overload_id = int(state.get_value(harv_overload_id(_harv)).constant_value())
            if _harv_overload_id > 0 > _harv_enabled_to_overload:
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


class HeuristicRejectInvalidFieldHarvestersAndTurns(HeuristicBase):

    """
    Heuristic cost calculator used solely to reject states with invalid field assignments and turns (when planning with field pre-assignments)

    The returned cost will be None if one or more field assignments or turns are invalid; otherwise cost = 0
    """

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = None if one or more field assignments or turns are invalid; otherwise cost = 0

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
        field_pre_assigned_harvester = fluents_manager.get_fluent(fn.field_pre_assigned_harvester)
        field_pre_assigned_turn = fluents_manager.get_fluent(fn.field_pre_assigned_turn)
        harv_field_turn = fluents_manager.get_fluent(fn.harv_field_turn)
        harv_count_pre_assigned_field_turns = fluents_manager.get_fluent(fn.harv_count_pre_assigned_field_turns)

        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)
            _field_harvester = state.get_value(field_harvester(_field)).constant_value()
            _field_pre_assigned_harvester = state.get_value(field_pre_assigned_harvester(_field)).constant_value()
            _field_pre_assigned_turn = int(state.get_value(field_pre_assigned_turn(_field)).constant_value())

            if _field_harvester.name == objects.no_harvester.name:
                continue

            _harv_count_pre_assigned_field_turns = int(state.get_value(harv_count_pre_assigned_field_turns(_field_harvester)).constant_value())
            _harv_field_turn = int(state.get_value(harv_field_turn(_field_harvester)).constant_value())  # it was already updated

            if _field_pre_assigned_harvester.name != objects.no_harvester.name \
                    and _field_harvester.name != _field_pre_assigned_harvester.name:
                return None  # assigned harvester != pre-assigned harvester

            if (_field_pre_assigned_harvester.name == objects.no_harvester.name
                    or _field_pre_assigned_turn == 0):  # no turn pre-assigned
                if (_harv_count_pre_assigned_field_turns > 0
                        and _harv_field_turn <= _harv_count_pre_assigned_field_turns):
                    return None
            else:  # turn pre-assigned
                if _field_pre_assigned_turn != _harv_field_turn:
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


class HeuristicBunkerMassTvsWaitingToDriveOld(HeuristicBase):

    """ Heuristic cost calculator: cost = Sum( mass in bunker of transport vehicle that is waiting to drive * factor ) """

    def __init__(self, cost_per_machine_waiting: Union[float, None] = None):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        cost_per_machine_waiting : float|None
            Cost per machine that is waiting. If None, the cost will be the current mass in the machine's bunker.
        """

        self.__cost_per_machine_waiting = cost_per_machine_waiting

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = Sum( mass in bunker of transport vehicle that is waiting to drive * factor )

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

        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_waiting_to_drive = fluents_manager.get_fluent(fn.tv_waiting_to_drive)
        cost = 0.0
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            if state.get_value(tv_waiting_to_drive(_tv)).bool_constant_value():
                if self.__cost_per_machine_waiting is not None:
                    cost += self.__cost_per_machine_waiting
                else:
                    cost += float(state.get_value(tv_bunker_mass(_tv)).constant_value())

        return cost

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

        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        cost = 0.0
        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            if self.__cost_per_machine_waiting is not None:
                cost += max(0.0, self.__cost_per_machine_waiting)
            else:
                cost += float(problem.initial_value(tv_total_capacity_mass(_tv)).constant_value())

        return cost


class HeuristicBunkerMassTvsWaitingToDrive(HeuristicBase):

    """ Heuristic cost calculator: cost = Sum( mass in bunker or bunker capacity of transport vehicle that is waiting to drive * factor ) """

    def __init__(self, use_bunker_total_capacity: bool,
                 cost_per_machine_waiting: Union[float, None] = None,
                 increase_factor_per_machine_waiting: bool = True):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        use_bunker_total_capacity : bool
            If True, the cost will be the machine's bunker mass capacity, otherwise the current mass in the machine's bunker (iif cost_per_machine_waiting is None).
        cost_per_machine_waiting : float|None
            Cost per machine that is waiting. If None, the cost will be the obtained based on use_bunker_total_capacity.
        increase_factor_per_machine_waiting : bool
           If True, a higher cost will be given to the machines that have been waiting longer.
        """

        if conf.gps.cost_windows.use_old_implementation_waiting_drive:  # @todo Remove when the tv_waiting_to_drive_id approach is working
            self.__old = HeuristicBunkerMassTvsWaitingToDriveOld(cost_per_machine_waiting)

        self.__use_bunker_total_capacity = use_bunker_total_capacity
        self.__cost_per_machine_waiting = cost_per_machine_waiting
        self.__increase_factor_per_machine_waiting = increase_factor_per_machine_waiting

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = Sum( mass in bunker or bunker capacity of transport vehicle that is waiting to drive * factor )

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

        if conf.gps.cost_windows.use_old_implementation_waiting_drive:  # @todo Remove when the tv_waiting_to_drive_id approach is working
            return self.__old.get_cost(problem, fluents_manager, objects, state)

        mass_fluent = fluents_manager.get_fluent(fn.tv_total_capacity_mass) \
            if self.__use_bunker_total_capacity \
            else fluents_manager.get_fluent(fn.tv_bunker_mass)

        tv_waiting_to_drive_id = fluents_manager.get_fluent(fn.tv_waiting_to_drive_id)
        cost = 0.0
        count_machines_waiting = 0
        masses_tvs_waiting: List[Tuple[int, float]] = list()

        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            _tv_waiting_to_drive_id = int(state.get_value(tv_waiting_to_drive_id(_tv)).constant_value())
            if _tv_waiting_to_drive_id > 0:
                count_machines_waiting += 1
                tv_cost = self.__cost_per_machine_waiting \
                    if self.__cost_per_machine_waiting is not None \
                    else float(state.get_value(mass_fluent(_tv)).constant_value())
                if not self.__increase_factor_per_machine_waiting:
                    cost += tv_cost
                else:
                    masses_tvs_waiting.append( ( _tv_waiting_to_drive_id,  tv_cost ) )

        if len(masses_tvs_waiting) > 0:
            masses_tvs_waiting.sort(key=lambda x: x[0])
            max_id = masses_tvs_waiting[-1][0]
            for i, mass in enumerate(masses_tvs_waiting):
                cost += ( mass[1] * (max_id - mass[0]) )

        return cost

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

        if conf.gps.cost_windows.use_old_implementation_waiting_drive:  # @todo Remove when the tv_waiting_to_drive_id approach is working
            return self.__old.get_max_cost(problem, fluents_manager, objects)

        mass_fluent = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        cost = 0.0
        count_machines_waiting = 0
        masses_tvs_waiting = list()

        for tv in objects.tvs.values():
            _tv = problem.object(tv.name)
            count_machines_waiting += 1
            tv_cost = max(0.0, self.__cost_per_machine_waiting) \
                if self.__cost_per_machine_waiting is not None \
                else float(problem.initial_value(mass_fluent(_tv)).constant_value())
            if not self.__increase_factor_per_machine_waiting:
                cost += tv_cost
            else:
                masses_tvs_waiting.append( tv_cost )

        if len(masses_tvs_waiting) > 0:
            masses_tvs_waiting.sort(reverse=True)
            max_id = len(masses_tvs_waiting) - 1
            for i, mass in enumerate(masses_tvs_waiting):
                cost += ( mass * (max_id - i) )

        return cost


class HeuristicUnharvestedMassHarvestersWaitingToHarvest(HeuristicBase):

    """ Heuristic cost calculator: cost = Sum( unharvested yield mass in field with harvester waiting to harvest/overload * factor ) """

    def __init__(self, use_reserved_mass: bool = False, cost_per_machine_waiting: float = None):

        """ Heuristic cost calculator initialization

        Parameters
        ----------
        use_reserved_mass : bool
            If True, the cost will be the yield mass not yet reserved for overload/harvest of the fields where harvesters are waiting, otherwise the yield mass that has not been harvested or is not to be harvested in ongoing overloads (iif cost_per_machine_waiting is None).
        cost_per_machine_waiting : float|None
            Cost per machine that is waiting. If None, the cost will be the obtained based on use_bunker_total_capacity.
        """

        self.__cost_per_machine_waiting = cost_per_machine_waiting
        self.__use_reserved_mass = use_reserved_mass

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = Sum( unharvested yield mass in field with harvester waiting to harvest/overload * factor )

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

        if self.__use_reserved_mass:
            yield_mass_fluent = fluents_manager.get_fluent(fn.field_yield_mass_after_reserve)
        else:
            yield_mass_fluent = fluents_manager.get_fluent(fn.field_yield_mass_minus_planned)
        harv_waiting_to_harvest = fluents_manager.get_fluent(fn.harv_waiting_to_harvest)
        harv_at_field = fluents_manager.get_fluent(fn.harv_at_field)
        cost = 0.0
        for harv in objects.harvesters.values():
            if harv is objects.no_harvester:
                continue
            _harv = problem.object(harv.name)
            if state.get_value(harv_waiting_to_harvest(_harv)).bool_constant_value():
                if self.__cost_per_machine_waiting is not None:
                    cost += self.__cost_per_machine_waiting
                else:
                    _field = problem.object(state.get_value(harv_at_field(_harv)).constant_value().name)
                    cost += float(state.get_value(yield_mass_fluent(_field)).constant_value())
        return cost

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

        field_yield_mass_after_reserve = fluents_manager.get_fluent(fn.field_yield_mass_after_reserve)
        field_masses = []
        cost = 0.0
        for field in objects.fields.values():
            if field is objects.no_field:
                continue
            _field = problem.object(field.name)
            field_masses.append(float(problem.initial_value(field_yield_mass_after_reserve(_field)).constant_value()))
        field_masses.sort(reverse=True)

        count_harvs = 0
        for harv in objects.harvesters.values():
            if harv is objects.no_harvester:
                continue
            count_harvs += 1

        for i, field_mass in enumerate(field_masses):
            if i >= count_harvs:
                break
            cost += field_mass
        return cost


# class HeuristicHarvestersTransitTimeWithReset(HeuristicBase):
#
#     def __init__(self, cost_per_second: float):
#         self.__cost_per_second = cost_per_second
#
#     def get_cost(self,
#                  problem: Problem,
#                  fluents_manager: FluentsManagerBase,
#                  objects: ProblemObjects,
#                  state: State) -> Union[float, None]:
#
#         """ Obtain the heuristic cost for a given problem and state
#
#         Parameters
#         ----------
#         problem : Problem
#             Problem
#         fluents_manager : FluentsManagerBase
#             Fluents manager holding the problem fluents
#         objects : ProblemObjects
#             Holds all the problem objects
#         state : State
#             State
#
#         Returns
#         ----------
#         cost : float
#             Cost
#         """
#
#         harv_transit_time_with_reset = fluents_manager.get_fluent(fn.harv_transit_time_with_reset)
#         total_transit_time = 0.0
#         for harv in objects.harvesters.values():
#             if harv is objects.no_harvester:
#                 continue
#             _harv = problem.object(harv.name)
#             total_transit_time += float(state.get_value(harv_transit_time_with_reset(_harv)).constant_value())
#         return total_transit_time * self.__cost_per_second

#
# class HeuristicTVsTransitTimeWithReset(HeuristicBase):
#
#     def __init__(self, cost_per_second: float):
#         self.__cost_per_second = cost_per_second
#
#     def get_cost(self,
#                  problem: Problem,
#                  fluents_manager: FluentsManagerBase,
#                  objects: ProblemObjects,
#                  state: State) -> Union[float, None]:
#
#         """ Obtain the heuristic cost for a given problem and state
#
#         Parameters
#         ----------
#         problem : Problem
#             Problem
#         fluents_manager : FluentsManagerBase
#             Fluents manager holding the problem fluents
#         objects : ProblemObjects
#             Holds all the problem objects
#         state : State
#             State
#
#         Returns
#         ----------
#         cost : float
#             Cost
#         """
#
#         tv_transit_time_with_reset = fluents_manager.get_fluent(fn.tv_transit_time_with_reset)
#         tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
#         total_cost = 0.0
#         for tv in objects.tvs.values():
#             _tv = problem.object(tv.name)
#             if self.__cost_per_second is None:
#                 total_cost += ( float(state.get_value(tv_transit_time_with_reset(_tv)).constant_value())
#                                 * float(state.get_value(tv_total_capacity_mass(_tv)).constant_value()) )
#             else:
#                 total_cost += ( float(state.get_value(tv_transit_time_with_reset(_tv)).constant_value()) * self.__cost_per_second )
#         return total_cost
