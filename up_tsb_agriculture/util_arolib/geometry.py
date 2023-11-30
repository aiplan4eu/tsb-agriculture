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

try:
    import exposed_arolib.geometry as ag

    addSampleToGeometryClosestToPoint = ag.addSampleToGeometryClosestToPoint
    calc_area = ag.calc_area
    calc_dist = ag.calc_dist
    calc_dist_to_line = ag.calc_dist_to_line
    calc_dist_to_line2 = ag.calc_dist_to_line2
    calc_dist_to_linestring = ag.calc_dist_to_linestring
    calc_vector_to_line = ag.calc_vector_to_line
    extend_line = ag.extend_line
    getBestRoadConnection = ag.getBestRoadConnection
    getCentroid = ag.getCentroid
    getCentroid2 = ag.getCentroid
    getGeometryLength = ag.getGeometryLength
    getNormVector = ag.getNormVector
    getNormVector_2 = ag.getNormVector
    getParallelVector = ag.getParallelVector
    getParallelVector2 = ag.getParallelVector
    getPointAtRelativeDist = ag.getPointAtRelativeDist
    getPointInLineAtDist = ag.getPointInLineAtDist
    get_angle = ag.get_angle
    get_angle_2 = ag.get_angle
    move_point_to_dist_to_line = ag.move_point_to_dist_to_line
    setVectorLength = ag.setVectorLength
    correct_polygon = ag.correct_polygon

except ModuleNotFoundError as err:

    import math
    import matplotlib.pyplot as pyplot
    from copy import deepcopy
    from typing import List, Tuple, Union
    from util_arolib.types import Point, Polygon, Linestring, LinestringVector, get_copy_aro

    from shapely.geometry import Polygon as ShapelyPolygon


    def calc_dist(p0: Point, p1: Point) -> float:

        """ Compute the distance between two points

        Parameters
        ----------
        p0 : Point
            One point
        p1 : Point
            Another point

        Returns
        ----------
        distance : float
            Distance between the two points [m]
        """

        return math.sqrt(pow(p1.x - p0.x, 2) + pow(p1.y - p0.y, 2))


    def calc_area(poly: Polygon) -> float:

        """ Compute the area of a polygon

        Parameters
        ----------
        poly : Polygon
            Polygon

        Returns
        ----------
        area : float
            Area of the polygon [m²]
        """

        p = ShapelyPolygon([ (p.x, p.y) for p in poly.points ])
        return p.area


    def getGeometryLength(geom: List[Point], start_index: int = 0, end_index: int = -1) -> float:

        """ Compute the length of a linestring

        Parameters
        ----------
        geom : List[Point]
            Linestring
        start_index : int
            Index from where to start computing
        end_index : int
            Index where to stop computing (inclusive)

        Returns
        ----------
        length : float
            Length of the linestring [m]
        """

        if len(geom) < 2:
            return 0.0
        if end_index < 0:
            end_index = len(geom)-1
        if start_index < 0 or start_index >= len(geom) or end_index >= len(geom) or start_index >= end_index:
            return 0.0

        length = 0.0
        for i in range( end_index-start_index ):
            length += calc_dist( geom[start_index+i], geom[start_index+i+1] )
        return length

    def get_angle(p1_0: Point, p1_1: Point, p2_0: Point, p2_1: Point, in_deg: bool = False, limit: bool = False) -> float:

        """ Compute the angle between two lines

        Parameters
        ----------
        p1_0 : Point
            First point of the first line
        p1_1 : Point
            Second point of the first line
        p2_0 : Point
            First point of the second line
        p2_1 : Point
            Second point of the second line
        in_deg : Point
            Return the angle in degrees (True) or Radians (False)
        limit : Point
            Return the angle in a range [-pi, pi] (True) or [-2pi, 2pi] (False)

        Returns
        ----------
        angle : float
            Angle between the two lines [° or Rad]
        """

        if (p1_0.x == p1_1.x and p1_0.y == p1_1.y) or (p2_0.x == p2_1.x and p2_0.y == p2_1.y):
            return 0

        angle = math.atan2( (p2_1.y - p2_0.y) , (p2_1.x - p2_0.x) ) - math.atan2( (p1_1.y - p1_0.y) , (p1_1.x - p1_0.x) )

        if angle > math.pi:
            angle -= 2 * math.pi
        if angle < -math.pi:
            angle += 2 * math.pi

        if limit:
            if angle < -0.5*math.pi:
                angle += math.pi
            elif angle > 0.5*math.pi:
                angle -= math.pi
        if in_deg:
            return angle * 180.0 / math.pi

        return angle

    def get_angle_2(p1: Point, pivot: Point, p2: Point, in_deg: bool = False, limit: bool = False) -> float:

        """ Compute the angle formed by three points

        Parameters
        ----------
        p1 : Point
            First point
        pivot : Point
            Middle point
        p2 : Point
            Last point
        in_deg : Point
            Return the angle in degrees (True) or Radians (False)
        limit : Point
            Return the angle in a range [-pi, pi] (True) or [-2pi, 2pi] (False)

        Returns
        ----------
        angle : float
            Angle formed by the three points
        """

        return get_angle(pivot, p1, pivot, p2, in_deg, limit)

    def getCentroid(p0: Point, p1: Point) -> Point:

        """ Get the point in the middle of two points

        Parameters
        ----------
        p0 : Point
            Second point
        p1 : Point
            First point

        Returns
        ----------
        centroid : Point
            Point in the middle of the two points
        """

        return Point( p0.x + 0.5 * (p1.x - p0.x) , p0.y + 0.5 * (p1.y - p0.y) )

    def getCentroid2(poly: Polygon) -> Point:

        """ Get the centroid of a polygon

        Parameters
        ----------
        poly : Polygon
            Polygon

        Returns
        ----------
        centroid : Point
            Centroid of the polygon
        """

        shapely_poly = ShapelyPolygon([[p.x, p.y] for p in poly.points])
        centroid = shapely_poly.centroid
        pt = Point()
        pt.x = centroid.xy[0][0]
        pt.y = centroid.xy[1][0]
        return pt


    def calc_dist_to_line(p0: Point, p1: Point, p: Point, infinite: bool = True, _abs: bool = True) -> float:

        """ Compute the distance from one point to a line

        Parameters
        ----------
        p0 : Point
            First point of the line
        p1 : Point
            Second point of the line
        p : Point
            Point from which to compute the distance
        infinite : bool
            Consider the line to be infinite (True) or bounded by the given points p0,p1 (False)
        _abs : bool
            If False, the sign (+,-) of the returned distance will be associated with the location of the point with respect to the line and its direction; otherwise, the returned distance will be always >= 0

        Returns
        ----------
        distance : float
            Distance from the point to the line [m]
        """

        if p0.x == p1.x and p0.y == p1.y:
            return calc_dist(p0, p)
        ang = get_angle_2(p0, p1, p)
        d_p_p1 = calc_dist(p1, p)
        dist = d_p_p1 * math.sin(ang)
        if not infinite:
            ang1 = get_angle(p0, p, p0, p1, False, False)
            ang2 = get_angle(p1, p, p1, p0, False, False)
            if abs(ang1) > 0.5 * math.pi or abs(ang2) > 0.5 * math.pi:
                neg = dist < 0
                dist = min(calc_dist(p, p0), calc_dist(p, p1))
                if neg:
                    dist = -dist
        if _abs:
            dist = abs(dist)
        return dist

    def calc_dist_to_line2(p0: Point, p1: Point, p: Point,
                           p0_to_infinity: bool = True, p1_to_infinity: bool = True, _abs: bool = True) -> float:

        """ Compute the distance from one point to a line

        Parameters
        ----------
        p0 : Point
            First point of the line
        p1 : Point
            Second point of the line
        p : Point
            Point from which to compute the distance
        p0_to_infinity : bool
            Consider the line to be infinite from the side of p0 (True) or bounded by p0 (False)
        p1_to_infinity : bool
            Consider the line to be infinite from the side of p1 (True) or bounded by p1 (False)
        _abs : bool
            If False, the sign (+,-) of the returned distance will be associated with the location of the point with respect to the line and its direction; otherwise, the returned distance will be always >= 0

        Returns
        ----------
        distance : float
            Distance from the point to the line [m]
        """

        if p0_to_infinity == p1_to_infinity:
            return calc_dist_to_line(p0, p1, p, p0_to_infinity, _abs)

        if p0.x == p1.x and p0.y == p1.y:
            return calc_dist(p0, p)

        dx = p1.x - p0.x
        dy = p1.y - p0.y
        dist = ( dy*p.x - dx*p.y + p1.x*p0.y - p0.x*p1.y ) / math.sqrt(dx*dx + dy*dy)

        ang1 = get_angle(p0, p, p0, p1, False, False)
        ang2 = get_angle(p1, p, p1, p0, False, False)
        if abs(ang1) > 0.5*math.pi or abs(ang2) > 0.5*math.pi:
            neg = dist < 0
            if p0_to_infinity and calc_dist(p, p1) < calc_dist(p, p0):
                dist = calc_dist(p, p1)
                if neg:
                    dist = -dist
            elif p1_to_infinity and calc_dist(p, p0) < calc_dist(p, p1):
                dist = calc_dist(p, p0)
                if neg:
                    dist = -dist
        if _abs:
            dist = abs(dist)
        return dist

    def calc_dist_to_linestring(points: List[Point], p: Point, infinite: bool = False) -> float:

        """ Compute the distance from one point to a linestring

        Parameters
        ----------
        points : List[Point]
            Linestring
        p : Point
            Point from which to compute the distance
        infinite : bool
            Consider the linestring to be infinite before/after its first/last points (mantaining the first/last segment directions) (True) or bounded by its first and last points (False)

        Returns
        ----------
        distance : float
            Distance from the point to the linestring [m]
        """

        if len(points) == 0:
            raise ValueError('Linestring is empty')

        if len(points) == 1:
            return calc_dist(points[0], p)

        elif len(points) == 2:
            return calc_dist_to_line(points[0], points[1], p, infinite, True)

        min_dist = calc_dist_to_line2(points[0], points[1], p, infinite, False, True)
        for i in range(len(points)-1):
            if i+1 != len(points)-1:
                dist = calc_dist_to_line(points[i], points[i+1], p, False, True)
            else:
                dist = calc_dist_to_line2(points[i], points[i+1], p, False, infinite, True)
            if min_dist > dist:
                min_dist = dist
        return min_dist


    def getNormVector(p0: Point, p1: Point, length: float) -> Union[Tuple[float, float], None]:

        """ Compute the x and y of the vector normal to a line

        Parameters
        ----------
        p0 : Point
            First point of the line
        p1 : Point
            Second point of the line
        length : bool
            Length for the output normal vector

        Returns
        ----------
        (dX, dY) : Tuple(float), None
            dX and dY values the vector normal to the line, where the vector is [(0,0), (dX, dY)]
        """

        deltaX = p1.x - p0.x
        deltaY = p1.y - p0.y
        _len = math.sqrt(deltaX*deltaX + deltaY*deltaY)
        if _len == 0:
            return None
        dX = length * deltaY/_len
        dY = length * (-deltaX)/_len
        return dX, dY

    def getNormVector_2(p0: Point, p1: Point, vec: Point, length: float) -> bool:

        """ Compute the vector normal to a line

        Parameters
        ----------
        p0 : Point
            First point of the line
        p1 : Point
            Second point of the line
        vec : Point
            [out] Output point vec corresponding to the vector normal to the line, where the vector is [(0,0), vec]
        length : bool
            Length for the output normal vector

        Returns
        ----------
        success : bool
            True on success
        """

        xy = getNormVector(p0, p1, length)
        if xy is not None:
            vec.x = xy[0]
            vec.y = xy[1]
            return True
        return False

    def extend_line(p0: Point, p1: Point, dist: float) -> Point:

        """ Get the extension point of a line (the extension is applied in the side of the second point)

        Parameters
        ----------
        p0 : Point
            First point of the line
        p1 : Point
            Second point of the line
        dist : float
            Extension distance

        Returns
        ----------
        extension_point : Point
            Extension point of the line (applied in the side of the p1)
        """

        new_p1 = Point()
        dx = p1.x - p0.x
        dy = p1.y - p0.y
        _len = math.sqrt(dx*dx + dy*dy)

        if _len == 0:
            return Point(p0.x, p0.y)
        new_p1.x = p1.x + dist * dx/_len
        new_p1.y = p1.y + dist * dy/_len

        # dx = new_p1.x - p0.x
        # dy = new_p1.y - p0.y
        # _len = math.sqrt(dx*dx + dy*dy)

        return new_p1

    def calc_vector_to_line(p0: Point, p1: Point, p: Point, infinite: bool = True) -> Point:

        """ Compute the vector from a point to a line (corresponding to the shortest connection between the point and the line),
         where the length of the vector is the distance between the point and the line

        Parameters
        ----------
        p0 : Point
            First point of the line
        p1 : Point
            Second point of the line
        p : Point
            Point from which to compute the vector
        infinite : bool
            Consider the line to be infinite (True) or bounded by the given points p0,p1 (False)

        Returns
        ----------
        vector_point : Point
            Point p corresponding to the vector from the point to the line, where the vector is [(0,0), p].
        """

        ret = Point(p.x, p.y)
        dist = calc_dist_to_line(p0, p1, p, True, False)
        getNormVector_2(p0, p1, ret, dist)
        ret.x *= -1
        ret.y *= -1
        if infinite:
            return ret

        ang1 = get_angle(p0, p, p0, p1, False, False)
        ang2 = get_angle(p1, p, p1, p0, False, False)

        if abs(ang1) > 0.5*math.pi or abs(ang2) > 0.5*math.pi:
            if calc_dist(p, p0) < calc_dist(p, p1):
                ret.x = p0.x - p.x
                ret.y = p0.y - p.y
            else:
                ret.x = p1.x - p.x
                ret.y = p1.y - p.y

        return ret

    def move_point_to_dist_to_line(p0: Point, p1: Point, p: Point, d: float, _abs: bool) -> bool:

        """ Move a point to a give distance from a line (following the shortest connection between the point and the line)

        Parameters
        ----------
        p0 : Point
            First point of the line
        p1 : Point
            Second point of the line
        p : Point
            [in/out] Point to be moved
        d : Point
            Distance to be moved
        _abs : bool
            If False, the sign (+,-) of the returned distance will be associated with the location of the point with respect to the line and its direction; otherwise, the returned distance will be always >= 0


        Returns
        ----------
        success : bool
            True on success
        """

        if _abs:
            d = abs(d)
        dist = calc_dist_to_line(p0, p1, p, False, _abs)
        if abs(dist) < 0.0001:
            return False
        p2 = calc_vector_to_line(p0, p1, p, False)
        p2.x += p.x
        p2.y += p.y
        p_ = extend_line(p2, p, d-dist)
        p.x, p.y = p_.x, p_.y
        dist_new = calc_dist_to_line(p0, p1, p, False, _abs)
        if abs( d - dist_new ) > 0.001 and abs( dist - dist_new ) > 0.0001:
            return move_point_to_dist_to_line(p0, p1, p, d, _abs)

        return True

    def addSampleToGeometryClosestToPoint(geom: List[Point], p: Point, max_points: int = 0, min_dist: float = 1e-3) -> int:

        """ Add one or more samples (points) to a linestring which are closest to a given point

        Parameters
        ----------
        geom : List[Point]
            [in, out] Linestring
        p : Point
            Point used as reference to add the sample
        max_points : int
            Maximum amount of points/samples to be added (there might be more than one position where the distance between the linestring segment and the given point is the same)
        min_dist : float
            If the distance between a sample/point to be added and the previous or next point is <= min_dist, the sample will not be added


        Returns
        ----------
        ind_or_count : int
            <0 on error. If max_points == 0, the returned value corresponds to the index of the new (or existing) sample; otherwise the returned value is the amount of inserted samples.
        """

        if len(geom) == 0:
            return -1
        elif len(geom) == 1:
            return 0

        eps = 1e-3

        min_dist = abs(min_dist)

        indexes = set()
        d_min = float("inf")
        for i in range(len(geom)-1):
            d = calc_dist_to_line( geom[i], geom[i+1], p, False )
            if d_min > d-eps:
                if d_min - d > eps:
                    indexes = {i}
                elif len(indexes)+1 <= max_points or max_points <= 0:
                    indexes.add(i)
                d_min = min(d_min, d)

        count = 0
        for i in indexes:
            sample = Point(p.x, p.y)
            move_point_to_dist_to_line( geom[i+count], geom[i+1+count], sample, 0, True)
            if calc_dist(geom[i+1+count], sample) > min_dist and calc_dist(geom[i+count], sample) > min_dist:
                if max_points == 1:
                    geom.insert( i+1, sample )
                    return i+1
                else:
                    count += 1
                    geom.insert( i+count, sample )
            elif max_points == 1:
                return i if calc_dist(geom[i+1], sample) > calc_dist(geom[i], sample) else i+1

        return count

    def getBestRoadConnection(p_start: Point, p_finish: Point, roads: LinestringVector, res: float = -1) -> List[Point]:

        """ Get the shortest path between two points via given roads (linestrings)

        Parameters
        ----------
        p_start : Point
            Start point
        p_finish : Point
            Goal point
        roads : List[Linestring]
            Roads (linestrings) to be used to connect the points
        res : float
            (not implemented) Points resolution [m] of the output path


        Returns
        ----------
        path : List[Point]
            Shortest path between the two points via the given roads
        """

        ret: List[Point] = LinestringVector()
        road_pts: List[Point] = LinestringVector()

        min_dist_start = float("inf")
        min_dist_finish = float("inf")
        for road in roads:
            if len(road.points) < 2:
                continue
            dist_start = calc_dist_to_linestring( road.points, p_start, False )
            dist_finish = calc_dist_to_linestring( road.points, p_finish, False )

            if min_dist_start + min_dist_finish > dist_start + dist_finish:
                min_dist_start = dist_start
                min_dist_finish = dist_finish
                road_pts = get_copy_aro( road.points )

        if len(road_pts) == 0:
            return ret

        ind_start = addSampleToGeometryClosestToPoint(road_pts, p_start, 1)
        size_prev = len(road_pts)
        ind_finish = addSampleToGeometryClosestToPoint(road_pts, p_finish, 1)

        if size_prev < len(road_pts) and ind_start >= ind_finish: # update ind_start if a point was added before it
            ind_start += 1

        if ind_start == ind_finish:
            ret.append(road_pts[ind_start])

        if len(ret) == 1:
            return ret

        reverse: bool = ind_start > ind_finish
        if reverse:
            ind_start, ind_finish = ind_finish, ind_start

        if calc_dist(road_pts[0], road_pts[-1]) < 1e-3:  # closed road/polygon
            l1 = getGeometryLength(road_pts, ind_start, ind_finish)
            l2 = getGeometryLength(road_pts) - l1
            if l1 <= l2:
                ret = road_pts[ind_start:ind_finish+1]
            else:
                ret = road_pts[ind_finish:-1]
                ret.extend( road_pts[1:ind_start+1] )
                reverse = not reverse
        else:
            ret = road_pts[ind_start:ind_finish+1]

        if reverse:
            ret.reverse()

        # if res > 0:
        #     ret = sample_geometry(ret, res);

        return ret

    def getPointAtRelativeDist(geom: List[Point], d: float) -> Tuple[Point, int]:

        """ Get the point in a linestring located at a given relative distance (relative to the linestring length) starting from the first point of the linestring

        Parameters
        ----------
        geom : Point
            Linestring
        d : float
            Relative distance [0,1], relative to the linestring length.


        Returns
        ----------
        point : Point
            Point in the linestring located at the given relative distance
        ind : int
            Index of the linestring sample located before the returned point
        """

        if len(geom) == 0:
            return Point(), -1

        d = min(1.0, max(0.0, d))
        dist = 0.0

        if d + 1e-5 >= 1.0:
            return geom[-1], len(geom)-1

        length_ls = getGeometryLength(geom)
        dist_ls = d * length_ls
        for i in range(len(geom)-1):
            p1 = geom[i]
            p2 = geom[i+1]
            point_dist = calc_dist(p1, p2)
            dist += point_dist

            if dist_ls > dist:
                continue

            diff = dist_ls - (dist - point_dist)
            return getPointInLineAtDist(p1, p2, diff), i

        return geom[-1], len(geom)-1

    def getPointInLineAtDist(p0: Point, p1: Point, dist: float) -> Point:

        """ Get the point in a line's direction located at a given distance from the first point of the given line

        Parameters
        ----------
        p0 : Point
            First point of the line
        p1 : Point
            Second point of the line
        dist : float
            Distance from p0. If >= 0, the returned point will be in the direction of p1; otherwise in opposite direction.


        Returns
        ----------
        point : Point
            Point in the line's direction located at a given distance from p0
        """

        if calc_dist(p0, p1) < 1e-6:
            return Point(p0.x, p0.y)
        v = Point(p1.x-p0.x, p1.y-p0.y)
        setVectorLength(v, dist)
        return Point(p0.x+v.x, p0.y+v.y)

    def setVectorLength(vec: Point, length: float) -> bool:

        """ Set the length of a vector

        Parameters
        ----------
        vec : Point
            [in, out] Vector point to be adjusted, where the vector is < (0,0), vec >
        length : float
            Desired length.

        Returns
        ----------
        success : bool
            True on success
        """

        if vec.x == 0.0 and vec.y == 0.0:
            return False
        vec2 = Point(vec.x, vec.y)
        return getParallelVector2( Point(0, 0), vec2, vec, length )

    def getParallelVector2(p0: Point, p1: Point, vec: Point, length: float) -> bool:

        """ Get the vector parallel to a line

        Parameters
        ----------
        p0 : Point
            First point of the line
        p1 : Point
            Second point of the line
        vec : Point
            [out] Output parallel vector point, where the vector is < (0,0), vec >
        length : float
            Desired length of the output vector.

        Returns
        ----------
        success : bool
            True on success
        """

        deltaX = p1.x - p0.x
        deltaY = p1.y - p0.y
        _len = math.sqrt(deltaX * deltaX + deltaY * deltaY)
        if _len == 0:
            return False
        vec.x = length * deltaX / _len
        vec.y = length * deltaY / _len
        return True

    def correct_polygon(poly: Polygon, clockwise: bool):

        """ Closes the polygon if open (other corrections are not done)

        Parameters
        ----------
        poly : Polygon
            Polygon
        clockwise : bool
            (Not implemented).
        """

        if len(poly.points) < 3:
            return

        if calc_dist(poly.points[0], poly.points[-1]) > 1e-9:
            poly.points.append( get_copy_aro(poly.points[0]) )
