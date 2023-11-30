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

from enum import Enum
from copy import deepcopy
from typing import List, Tuple, Any
try:
    import exposed_arolib.types as at

    point_ref = at.point_ref
    Point = at.Point
    PointVector = at.PointVector
    Polygon = at.Polygon
    PolygonVector = at.PolygonVector
    Linestring = at.Linestring
    LinestringVector = at.LinestringVector
    Pose2D = at.Pose2D
    ResourcePoint = at.ResourcePoint
    ResourcePointVector = at.ResourcePointVector
    FieldAccessPoint = at.FieldAccessPoint
    FieldAccessPointVector = at.FieldAccessPointVector
    Track = at.Track
    CompleteHeadland = at.CompleteHeadland
    PartialHeadland = at.PartialHeadland
    Headlands = at.Headlands
    Subfield = at.Subfield
    SubfieldVector = at.SubfieldVector
    Field = at.Field
    MachineType = at.MachineType
    Machine = at.Machine
    MachineDynamicInfo = at.MachineDynamicInfo
    MachineId2DynamicInfoMap = at.MachineId2DynamicInfoMap
    RoutePointType = at.RoutePointType
    RoutePoint = at.RoutePoint
    Route = at.Route
    OutFieldInfo = at.OutFieldInfo
    tonnes2Kg = at.tonnes2Kg
    sqrmeters2hectares = at.sqrmeters2hectares
    t_ha2Kg_sqrm = at.t_ha2Kg_sqrm

    get_copy = at.get_copy
    get_copy_aro = at.get_copy

    AROLIB_TYPES_FOUND = True


except ModuleNotFoundError as err:

    AROLIB_TYPES_FOUND = False

    class Point:

        """ Point """

        def __init__(self, _x: float = 0.0, _y: float = 0.0):

            """ Point initialization

            Parameters
            ----------
            _x : float
                X-coordinate
            _y : float
                Y-coordinate
            """

            self.x: float = _x
            """ X-coordinate """

            self.y: float = _y
            """ Y-coordinate """

        def point(self):
            """ Point accessor """
            return self

    def point_ref(p: Point) -> Point:
        """ Point accessor """
        return p

    class PointVector(list):
        """ Implementation of a vector of points """
        pass


    class Polygon:

        """ Polygon - without holes """

        def __init__(self):
            self.id: int = -1
            """ Id """

            self.points: List[Point] = list()
            """ Points """


    class PolygonVector(list):
        """ Implementation of a vector of polygons """
        pass

    class Linestring:

        """ Linestring """

        def __init__(self):
            self.id: int = -1
            """ Id """

            self.points: List[Point] = list()
            """ Points """


    class LinestringVector(list):
        """ Implementation of a vector of line-strings """
        pass

    class Pose2D(Point):

        """ 2D Pose """

        def __init__(self, _x: float = 0.0, _y: float = 0.0, _ang: float = 0.0):

            """ Pose initialization

            Parameters
            ----------
            _x : float
                X-coordinate
            _y : float
                Y-coordinate
            _ang : float
                Angle (x-y plane)
            """

            super(Pose2D, self).__init__(_x, _y)
            self.angle: float = _ang
            """ Angle (x-y plane) """


    class ResourcePoint(Point):

        """ Resource point (e.g. loading/unloading locations) """

        def __init__(self):
            super(ResourcePoint, self).__init__()
            self.id: int = -1
            """ Id """

            self.geometry = Polygon()
            """ Boundary """


    class ResourcePointVector(list):
        """ Implementation of a vector of resource points """
        pass


    class FieldAccessPoint(Point):

        """ Field access point """

        def __init__(self, point: Point, _id: int = -1):

            """ Field access point initialization

            Parameters
            ----------
            point : Point
                Position/location
            _id : int
                Id
            """

            super(FieldAccessPoint, self).__init__(point.x, point.y)
            self.id: int = _id
            """ Id """


    class FieldAccessPointVector(list):
        """ Implementation of a vector of field access points """
        pass


    class Track:

        """ Field track """

        def __init__(self):
            self.id: int = -1
            """ Id """

            self.points: List[Point] = list()
            """ Track points (middle linestring) """

            self.boundary = Polygon()
            """ Track boundary """

            self.width: float = -1.0
            """ Track width """


    class CompleteHeadland:

        """ Complete/surrounding headland """

        def __init__(self):
            self.headlandWidth: float = -1.0
            """ Headland width """

            self.middle_track = Polygon()
            """ Middle track-points """

            self.tracks: List[Track] = list()
            """ Tracks """

            self.boundaries: Tuple[Polygon, Polygon] = (Polygon(), Polygon())
            """ Headland boundaries (field boundary and inner-field boundary) """


    class PartialHeadland:

        """ Partial headland """

        def __init__(self):
            self.id: int = -1
            """ Id """

            self.boundary = Polygon()
            """ Headland boundary """

            self.tracks: List[Track] = list()
            """ Tracks """

            self.connectingHeadlandIds: Tuple[int, int] = (-1, -1)
            """ Ids of the partial headlands connected to this partial headland (in both sides) """


    class Headlands:

        """ Headlands """

        def __init__(self):
            self.complete = CompleteHeadland()
            """ Complete/surrounding headland """

            self.partial: List[PartialHeadland] = list()
            """ Partial headlands """


    class Subfield:

        """ Subfield """

        def __init__(self):
            self.id: int = -1
            """ Id """

            self.boundary_outer = Polygon()
            """ Outer boundary """

            self.boundary_inner = Polygon()
            """ Inner boundary (inner-field boundary) """

            self.headlands = Headlands()
            """ Headlands """

            self.tracks: List[Track] = list()
            """ Inner-field tracks """

            self.resource_points: List[ResourcePoint] = list()
            """ Resource points associated to the subfield """

            self.access_points: List[FieldAccessPoint] = list()
            """ Access points """

            self.reference_lines: List[Linestring] = list()
            """ Inner-field reference track lines """


    class SubfieldVector(list):
        """ Implementation of a vector of subfields """
        pass


    class Field:

        """ Field """

        def __init__(self):
            self.id: int = -1
            """ Id """

            self.name: str = ''
            """ Name """

            self.outer_boundary = Polygon()
            """ Outer boundary """

            self.subfields: List[Subfield] = list()
            """ Subfields """

            self.external_roads: List[Linestring] = list()
            """ External roads """


    class MachineType(Enum):

        """ Enum for the type of machine """

        HARVESTER = 0
        """ Harvester """
        OLV = 1
        """ Overload vehicle (transport vehicle) """
        UNDEFINED_TYPE = 10
        """ Undef """


    class Machine:

        """ Machine """

        def __init__(self):
            self.id = -99999
            """ Id """

            self.machinetype: MachineType = MachineType.UNDEFINED_TYPE
            """ Machine type """

            self.manufacturer = "_UNDEF_"
            """ Manufacturer """

            self.model = "_UNDEF_"
            """ Machine model """

            self.width = -99999
            """ Width [m] """

            self.length = -99999
            """ Length [m] """

            self.height = -99999
            """ Height [m] """

            self.weight = -99999
            """ Weight (mass) [kg] """

            self.bunker_mass = -99999
            """ Bunker mass capacity [kg] """

            self.bunker_volume = -99999
            """ Bunker volume capacity [m³] """

            self.working_width = -99999
            """ Working width [m] """

            self.max_speed_empty = -99999
            """ Maximum speed when the machine is empty [m/s] """

            self.max_speed_full = -99999
            """ Maximum speed when the machine is full [m/s] """

            self.def_working_speed = -99999
            """ Default working speed [m/s] """

            self.unloading_speed_mass = -99999
            """ Unloading speed (mass) [kg/s] """

            self.unloading_speed_volume = -99999
            """ Unloading speed (volume) [m³/s] """

            self.turning_radius = -99999
            """ Turning radius [m] """

        def calcSpeed(self, currentMass: float) -> float:

            """ Compute the maximum speed of the machine for a given amount of mass in the bunker

            Parameters
            ----------
            currentMass : float
                Mass in the bunker [kg]

            Returns
            ----------
            speed : float
                Maximum speed [m/s] of the machine for the given amount of mass in the bunker
            """

            if self.bunker_mass == 0:
                return self.max_speed_empty
            return (self.max_speed_empty + min(1.0, max(0.0, currentMass / self.bunker_mass) )
                    * (self.max_speed_full - self.max_speed_empty))


    class MachineDynamicInfo:

        """ Machine dynamic information (machine state) """

        def __init__(self):
            self.position = Point()
            """ Position/location """

            self.bunkerMass: float = 0.0
            """ Yield-mass in the bunker [kg] """

            self.bunkerVolume: float = 0.0
            """ Yield-volume in the bunker [m³] """

            self.timestamp: float = 0.0
            """ Timestamp [s] of the information/state """


    class MachineId2DynamicInfoMap(dict):
        """ Implementation of a map of machines' dynamic information """
        pass


    class RoutePointType(Enum):

        """ Enum for the type of route point """

        DEFAULT = 0
        TRACK_START = 1
        TRACK_END = 2
        RESOURCE_POINT = 3
        FIELD_ENTRY = 4
        FIELD_EXIT = 5
        OVERLOADING_START = 6
        OVERLOADING_FINISH = 7
        OVERLOADING = 8
        HEADLAND = 9
        INITIAL_POSITION = 10
        HARVESTING = 11
        TRANSIT = 12
        SEEDING = 13
        SPRAYING = 14
        CULTIVATING = 15
        PLOUGHING = 16
        SCANNING = 50
        TRANSIT_OF = 60


    class RoutePoint(Point):

        """ Route point """

        def __init__(self, _x: float = 0.0, _y: float = 0.0):

            """ Route point initialization

            Parameters
            ----------
            _x : float
                X-coordinate
            _y : float
                Y-coordinate
            """

            super(RoutePoint, self).__init__(_x, _y)

            self.time_stamp: float = -1.0
            """ Timestamp [s] """

            self.bunker_mass: float = 0.0
            """ Amount of yield-mass [kg] in the machine's bunker """

            self.bunker_volume: float = 0.0
            """ Amount of yield-volume [m³] in the machine's bunker """

            self.worked_mass: float = 0.0
            """ Amount of yield-mass [kg] worked until this moment by the machine (for harvesters) """

            self.worked_volume: float = 0.0
            """ Amount of yield-volume [m³] worked until this moment by the machine (for harvesters) """

            self.track_id: int = -99
            """ Id of the field track related to the route point """

            self.type: RoutePointType = RoutePointType.DEFAULT
            """ Route-point type """


    class Route:

        """ Route """

        def __init__(self):
            self.machine_id: int = -1
            """ Id of the machine to which this route belongs """

            self.route_id: int = -1
            """ Route id """

            self.route_points: List[RoutePoint] = list()
            """ Route points """

            self.baseDateTime: str = ''
            """ Base date/time (the timestamps of the route points are relative to this timestamp) """


    class OutFieldInfo:

        """ Information for activities done outside the field (e.g., transit, unloading, etc) """

        def __init__(self):
            pass


    def tonnes2Kg(value: float) -> float:

        """ Convert tonnes to kg

        Parameters
        ----------
        value : float
            Value in tonnes

        Returns
        ----------
        value_converted : float
            Value in kg
        """

        return value * 1000


    def sqrmeters2hectares(value: float) -> float:

        """ Convert m² to hectares

        Parameters
        ----------
        value : float
            Value in m²

        Returns
        ----------
        value_converted : float
            Value in hectares
        """

        return value * 0.0001


    def t_ha2Kg_sqrm(value: float) -> float:

        """ Convert t/ha to kg/m²

        Parameters
        ----------
        value : float
            Value in t/ha

        Returns
        ----------
        value_converted : float
            Value in kg/m²
        """

        return tonnes2Kg(value) * sqrmeters2hectares(1.0)


    def get_copy(x: Any):
        """ Get copy of an object """
        return deepcopy(x)


    def get_copy_aro(x: Any):
        """ Get copy of an arolib object """
        return deepcopy(x)
