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

from util_arolib.types import *
from util_arolib.geometry import *
from silo_planning.types import *
from route_planning.field_route_planning import PlanningSettings


def __get_field(ref_point: Point, width: float, side: int, shape: int, access_points_per_field: int) -> Field:

    """ Creates a field following the given parameters

    Parameters
    ----------
    ref_point : Point
        Point to be taken as reference to locate the field geometries
    width : float
        Field width
    side : int
        Side of the road [0, 1]
    shape : int
        Field shape (0: rectangle, else: house-shape)
    access_points_per_field : int
        Amount of field access points

    Returns
    ----------
    field : Field
        Field
    """

    y_factor = 1.0 if side == 0 else -1.0
    length = 200.0 * y_factor

    x_ref = ref_point.x
    y_ref = ref_point.y + 20 * y_factor

    field = Field()
    field.outer_boundary.points.append( Point(x_ref, y_ref) )
    if shape == 0:  # rectangle
        field.outer_boundary.points.append( Point(x_ref, y_ref + length) )
        field.outer_boundary.points.append( Point(x_ref + width, y_ref + length) )
    else:  # house-shape
        field.outer_boundary.points.append( Point(x_ref, y_ref + 0.8 * length) )
        field.outer_boundary.points.append( Point(x_ref + 0.5 * width, y_ref + length) )
        field.outer_boundary.points.append( Point(x_ref + width, y_ref + 0.8 * length) )
    field.outer_boundary.points.append( Point(x_ref+ width, y_ref) )
    field.outer_boundary.points.append( Point(x_ref, y_ref) )

    field.subfields.append(Subfield())
    sf = field.subfields[0]
    sf.boundary_outer = get_copy_aro(field.outer_boundary)

    ref_line = Linestring()
    ref_line.points.append( get_copy_aro(field.outer_boundary.points[0]) )
    ref_line.points.append( get_copy_aro(field.outer_boundary.points[1]) )
    sf.reference_lines.append(ref_line)

    ap_dist = width / access_points_per_field
    for i in range(access_points_per_field):
        ap = FieldAccessPoint( Point(x_ref + i * ap_dist, y_ref), i )
        sf.access_points.append(ap)

    return field


def get_test_location_data_1(num_fields: int,
                             access_points_per_field: int,
                             access_points_per_silo: int,
                             compactors_per_silo: int,
                             fields: List[Field],
                             silos: List[SiloExtended],
                             compactors: List[Compactor],
                             roads: List[Linestring]):

    """ Creates n fields, 2 silos, m compactors, and 1 road following the given parameters

    The 2 silos will be located at the extrema of a horizontal road, and the fields will be located in either side of the road.

    Parameters
    ----------
    num_fields : int
        Number of fields
    access_points_per_field : int
        Amount of access points in each field
    access_points_per_silo : int
        Amount of access points in each silo
    compactors_per_silo : int
        Amount of compactors in each silo
    fields : List[Field]
        List where the generated fields will be added (the input list might be cleared!)
    silos : List[SiloExtended]
        List where the generated silos will be added (the input list might be cleared!)
    compactors : List[Compactor]
        List where the generated compactors will be added (the input list might be cleared!)
    roads : List[Linestring]
        List where the generated road will be added (the input list might be cleared!)
    """

    fields.clear()
    silos.clear()
    compactors.clear()
    roads.clear()

    x_ref = 1000.0
    y_ref = 1000.0
    field_width = 100.0
    dist_between_fields = 1000.0
    silo_dist = 1000.0
    silo_access_capacity = 10000

    if num_fields <= 0:
        num_fields = 10
    if access_points_per_field <= 0:
        access_points_per_field = 3
    if access_points_per_silo <= 0:
        access_points_per_silo = 3
    if compactors_per_silo <= 0:
        compactors_per_silo = 1

    total_field_area = 0

    field_columns = math.floor(0.5*num_fields)+1

    for side in range(2):
        for i in range(field_columns):
            if len(fields) >= num_fields:
                break
            field = __get_field( Point( x_ref + i * (field_width + dist_between_fields), y_ref ),
                                        field_width, side, i % 2, access_points_per_field)
            field.id = len(fields)
            field.name = f'field_{field.id}'
            fields.append(field)
            total_field_area = total_field_area + calc_area(field.outer_boundary)

    total_yield_mass = t_ha2Kg_sqrm( PlanningSettings().avg_mass_per_area_t_ha ) * total_field_area

    for i in range(2):
        silo = SiloExtended()
        silo.id = len(silos)
        silo.mass_capacity = 0.7 * total_yield_mass
        if i == 0:
            silo.x = x_ref - silo_dist
        else:
            silo.x = x_ref + field_columns * field_width + dist_between_fields * (field_columns - 1) + silo_dist
        silo.y = y_ref
        dx_geom = -50 if i == 0 else 50
        silo.geometry.points.extend( [ Point(silo.x,silo.y-25),
                                       Point(silo.x+dx_geom,silo.y-25),
                                       Point(silo.x+dx_geom,silo.y+25),
                                       Point(silo.x,silo.y+25),
                                       Point(silo.x,silo.y-25) ] )
        y_ref_ap = silo.y + 5.0 * (1-access_points_per_silo)
        for j in range(access_points_per_silo):
            ap = SiloAccessPoint()
            ap.id = len(silo.access_points)
            ap.x = silo.x
            ap.y = y_ref_ap - 10.0 * j
            ap.mass_capacity = silo_access_capacity
            silo.access_points.append(ap)

        for j in range(compactors_per_silo):
            comp = Compactor()
            comp.id = len(compactors)
            comp.silo_id = silo.id
            compactors.append(comp)

        silos.append(silo)

    road = Linestring()
    road.points.append(silos[0])
    road.points.append(silos[1])
    roads.append(road)
