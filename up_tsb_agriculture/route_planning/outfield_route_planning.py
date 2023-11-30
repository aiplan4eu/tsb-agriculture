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

import abc
from abc import ABC
from typing import Optional

from util_arolib.types import *
from util_arolib.geometry import *


class OutFieldRoutePlanner(ABC):

    """ Base class of path/route planners for transit outside the field """

    def __init__(self):
        pass

    @abc.abstractmethod
    def get_path(self, pt_from: Point, pt_to: Point, machine: Machine) -> PointVector:

        """ Plan a path between two points for a given machine

        Parameters
        ----------
        pt_from : Point
            Starting point
        pt_to : Point
            Goal point
        machine : Machine
            Machine

        Returns
        ----------
        path : PointVector
            Planned path as a list of points
        """

        pass

    @abc.abstractmethod
    def get_route(self, pt_from: Point, pt_to: Point, machine: Machine, ref_rp: RoutePoint,
                  route_id: float = 0, start_rp_type: RoutePointType = RoutePointType.TRANSIT_OF,
                  end_rp_type: RoutePointType = RoutePointType.TRANSIT_OF) -> Route:

        """ Plan a (arolib) route between two points for a given machine

        Parameters
        ----------
        pt_from : Point
            Starting point
        pt_to : Point
            Goal point
        machine : Machine
            Machine
        ref_rp : RoutePoint
            Reference route point
        route_id : int
            Id for the output route
        start_rp_type : RoutePointType
            Route-point type for the first route point
        end_rp_type : RoutePointType
            Route-point type for the last route point

        Returns
        ----------
        route : Route
            Planned route
        """

        pass


class SimpleOutFieldRoutePlanner(OutFieldRoutePlanner):

    """ Simple path/route planner for transit outside the field """

    def __init__(self, roads: List[Linestring]):
        super(SimpleOutFieldRoutePlanner, self).__init__()
        self.__roads = roads

    def get_path(self, pt_from: Point, pt_to: Point, machine: Machine) -> PointVector:

        """ Plan a path between two points for a given machine

        Parameters
        ----------
        pt_from : Point
            Starting point
        pt_to : Point
            Goal point
        machine : Machine
            Machine

        Returns
        ----------
        path : PointVector
            Planned path as a list of points
        """

        path = PointVector()
        if self.__roads is None or len(self.__roads) == 0 or calc_dist(pt_from, pt_to) < 0.1:
            path.append(pt_from)
            if (pt_from.x != pt_to.x) and (pt_from.y != pt_to.y):
                path.append(Point(pt_from.x, pt_to.y))
            if (pt_from.x != pt_to.x) or (pt_from.y != pt_to.y):
                path.append(pt_to)
            return path

        path_2 = getBestRoadConnection(pt_from, pt_to, self.__roads, -1)
        path = PointVector()
        path.extend([pt_from])
        path.extend(path_2)
        path.extend([pt_to])
        return path


    def get_route(self, pt_from: Point, pt_to: Point, machine: Machine, ref_rp: RoutePoint,
                  route_id: int = 0, start_rp_type: RoutePointType = RoutePointType.TRANSIT_OF,
                  end_rp_type: RoutePointType = RoutePointType.TRANSIT_OF
                  ) -> Optional[Route]:

        """ Plan a (arolib) route between two points for a given machine

        Parameters
        ----------
        pt_from : Point
            Starting point
        pt_to : Point
            Goal point
        machine : Machine
            Machine
        ref_rp : RoutePoint
            Reference route point
        route_id : int
            Id for the output route
        start_rp_type : RoutePointType
            Route-point type for the first route point
        end_rp_type : RoutePointType
            Route-point type for the last route point

        Returns
        ----------
        route : Route
            Planned route
        """

        path = self.get_path(pt_from, pt_to, machine)
        if len(path) == 0:
            return None

        route = Route()
        route.route_id = route_id
        route.machine_id = machine.id
        speed = machine.calcSpeed(ref_rp.bunker_mass)

        rp = RoutePoint()
        rp.x = pt_from.x
        rp.y = pt_from.y
        rp.time_stamp = ref_rp.time_stamp
        rp.bunker_mass = ref_rp.bunker_mass
        rp.bunker_volume = ref_rp.bunker_volume
        rp.worked_mass = ref_rp.worked_mass
        rp.worked_volume = ref_rp.worked_volume
        rp.type = start_rp_type
        route.route_points.append(rp)

        for i in range(len(path)-1):
            rp = get_copy(rp)
            rp.x = path[i+1].x
            rp.y = path[i+1].y
            rp.time_stamp = rp.time_stamp + calc_dist(path[i], path[i+1]) / speed
            rp.type = RoutePointType.TRANSIT_OF
            route.route_points.append(rp)

        route.route_points[len(route.route_points)-1].type = end_rp_type
        return route
