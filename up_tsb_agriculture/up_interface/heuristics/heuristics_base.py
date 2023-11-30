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
from typing import Dict
from abc import ABC, abstractmethod
import random

from unified_planning.shortcuts import *
from up_interface.fluents import FluentsManagerBase
from up_interface.problem_encoder.problem_objects import ProblemObjects
from up_interface.problem_encoder.problem_stats import *


class HeuristicBase(ABC):

    """ Base class of the heuristic cost calculators """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass


class WeightedHeuristics(HeuristicBase):

    """ Heuristic cost calculator built from the weighted combination (sum) of one or more (sub) heuristic calculators """

    def __init__(self, heuristics: Dict[HeuristicBase, float]):

        """ Class initialization

        Parameters
        ----------
        heuristics : Dict[HeuristicBase, float]
            Dictionary containing the (sub) heuristics and their corresponding weight: {heuristic: heuristic_weight}
        """

        self.__heutistics = heuristics

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = Sum(heuristic_weight * heuristic.get_cost)

        If any of the (sub) heuristics return cost==None, the returned cost will be None

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

        cost: float = 0.0
        for h, w in self.__heutistics.items():

            # #debug!
            # print(f'  getting cost for h = {h}')

            c = h.get_cost(problem, fluents_manager, objects, state)
            if c is None:
                return None
            cost += (w * c)

        # #debug!
        # print(f'Weighted cost = {cost}')

        return cost
        # return get_up_fraction(cost)

    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> float:

        """ Obtain the maximum heuristic cost for a given problem

        max_cost = Sum(heuristic.get_max_cost)

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

        cost: float = 0.0
        for h, w in self.__heutistics.items():
            c = h.get_max_cost(problem, fluents_manager, objects)
            if c is None:
                continue
            cost += (w * c)

        return cost


class HeuristicWithDeltaRandomCostFactor(HeuristicBase):

    """ Heuristic cost calculator built from the weighted combination (sum) of one or more (sub) heuristic calculators with a random cost factor """

    def __init__(self, heuristic: HeuristicBase, k: float = -0.001):
        self.__heuristic = heuristic
        self.__k = k

        """ Class initialization

        Parameters
        ----------
        heuristics : Dict[HeuristicBase, float]
            Dictionary containing the (sub) heuristics and their corresponding weight: {heuristic: heuristic_weight}
        k : float
            Factor applied to the random cost deviation, which will be applied to the output cost
        """

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Obtain the heuristic cost for a given problem and state

        cost = ( Sum(heuristic_weight * heuristic.get_cost) ) * (1.0 + k * random(0.0, 1.0))

        If any of the (sub) heuristics return cost==None, the returned cost will be None

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

        if self.__k is None:
            return self.__heuristic.get_cost(problem, fluents_manager, objects, state)
        cost = self.__heuristic.get_cost(problem, fluents_manager, objects, state)
        if cost is None:
            return None
        return cost * (1.0 + self.__k * random.uniform(0.0, 1.0))

    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> Optional[float]:

        """ Obtain the maximum heuristic cost for a given problem

        cost = ( Sum(heuristic.get_max_cost) ) * (1.0 + max(0.0, k))

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

        if self.__k is None:
            return self.__heuristic.get_max_cost(problem, fluents_manager, objects)
        cost = self.__heuristic.get_max_cost(problem, fluents_manager, objects)
        if cost is None:
            return None

        return cost * (1.0 + max(0.0, self.__k))
