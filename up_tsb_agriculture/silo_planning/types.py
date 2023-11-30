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

from typing import List
from util_arolib.types import Point, ResourcePoint, Polygon, get_copy_aro, AROLIB_TYPES_FOUND


class SiloAccessPoint(Point):

    """ Silo access/unloading point """

    def __init__(self, *argv):
        if len(argv) > 0:
            Point.__init__(self, *argv)
        else:
            Point.__init__(self)

        self.geometry = Polygon()
        """ Boundary """

        self.mass_capacity = 20000
        """ Mass capacity [kg] """

        self.sweep_duration = 60
        """ Duration of a compactor sweep """

    if AROLIB_TYPES_FOUND:
        def __deepcopy__(self, memodict={}) -> 'SiloAccessPoint':
            ret = get_copy_aro(self)
            ret.geometry = get_copy_aro(self.geometry)
            ret.mass_capacity = self.mass_capacity
            ret.sweep_duration = self.sweep_duration
            ret.__class__ = SiloAccessPoint
            return ret


class SiloExtended(ResourcePoint):

    """ Silo """

    def __init__(self):
        super(SiloExtended, self).__init__()

        self.name: str = ''
        """ Name """

        self.mass_capacity: float = 300000
        """ Mass capacity [kg] """

        self.access_points: List[SiloAccessPoint] = list()
        """ Access/unloading points """

    if AROLIB_TYPES_FOUND:
        def __deepcopy__(self, memodict={}) -> 'SiloExtended':
            ret = get_copy_aro(self)
            ret.name = self.name
            ret.mass_capacity = self.mass_capacity
            ret.access_points = self.access_points
            ret.__class__ = SiloExtended
            return ret


class Compactor:

    """ Compacting machine """

    def __init__(self):
        self.id: int = -1
        """ Machine id """

        self.silo_id: int = -1
        """ Id of the silo assigned to the compactor """

        self.mass_per_sweep: float = 500.0
        """ Amount of yield-mass [kg] moved by the compactor in one sweep """
