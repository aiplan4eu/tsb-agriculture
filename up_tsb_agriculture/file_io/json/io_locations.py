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

import json
import os
from pyproj import Proj
from typing import Dict, List, Optional

from up_interface.problem_encoder.names_helper import *
from util_arolib.types import *
from util_arolib.geometry import getCentroid2
from silo_planning.types import SiloExtended, SiloAccessPoint


def __to_point(coordinates: List[str]) -> Optional[Point]:

    """ Convert a list of coordinates (string) to the respective Point

    Parameters
    ----------
    coordinates : List[str]
        Coordinates (WGS) as a list of strings: ['x', 'y']

    Returns
    ----------
    point : Point
        Point (UTM)
    """

    if coordinates is None or len(coordinates) < 2:
        return None
    try:
        proj = Proj("+proj=utm +zone=32 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
        x, y = proj(float(coordinates[0]), float(coordinates[1]))
        return Point(x, y)
    except Exception as e:
        print(f"Error parsing point {coordinates}: {e}")
        return None


def __parse_point(data: Dict[str, Dict[str, List[str]]]) -> Optional[Point]:

    """ Convert a geojson point to Point

    Parameters
    ----------
    data : Dict[str, str]
        Dictionary holding the point data in geojson format

    Returns
    ----------
    point : Point
        Point (UTM)
    """

    try:
        geom = data.get('geometry')
        if geom is None:
            print("Error reading geometry.")
            return None
        coord = geom.get("coordinates")
        if coord is None:
            print("Error reading coordinates.")
            return None
        return __to_point( coord )

    except Exception as e:
        print(f"Error reading geometry/point: {e}")


def __parse_polygon(data: Dict[str, Any]) -> Optional[Polygon]:

    """ Convert a geojson polygon to Polygon

    Parameters
    ----------
    data : Dict[str, str]
        Dictionary holding the polygon data in geojson format

    Returns
    ----------
    polygon : Polygon
        Polygon (UTM)
    """

    try:
        geom = data.get('geometry')
        poly = Polygon()
        if geom is None:
            print("Error reading geometry.")
            return None
        if len(geom["coordinates"]) < 1:
            return None
        for coord in geom["coordinates"][0]:
            pt = __to_point( coord )
            if pt is None:
                continue
            poly.points.append(pt)

        if len(poly.points) > 1:
            if abs(poly.points[0].x - poly.points[-1].x) < 1e-5 \
                    and abs(poly.points[0].y - poly.points[-1].y) < 1e-5:
                poly.points[-1].x = poly.points[0].x
                poly.points[-1].y = poly.points[0].y
            else:
                poly.points.append(poly.points[0])
        if len(poly.points) < 3:
            print(f"Error reading polygon")
            return None

        return poly

    except Exception as e:
        print(f"Error reading geometry/polygon: {e}")
        return None


def __parse_linestring(data: Dict[str, Any]) -> Optional[Linestring]:

    """ Convert a geojson linestring to Linestring

    Parameters
    ----------
    data : Dict[str, str]
        Dictionary holding the linestring data in geojson format

    Returns
    ----------
    linestring : Linestring
        Linestring (UTM)
    """

    try:
        geom: Dict = data.get('geometry')
        ls = Linestring()
        if geom is None:
            print("Error reading geometry.")
            return None
        # _type = geom.get('type')
        # if _type is not None and _type == 'MultiLineString'
        for coord in geom["coordinates"]:
            pt = __to_point( coord )
            if pt is None:
                continue
            ls.points.append(pt)

        return ls

    except Exception as e:
        print(f"Error reading geometry/linestring: {e}")
        return None


def __parse_field_boundary(data: Dict[str, Any]) -> Optional[Tuple[str, Polygon]]:

    """ Get a field name and boundary from a geojson formatted geometry

    Parameters
    ----------
    data : Dict[str, str]
        Dictionary holding the geometry data in geojson format

    Returns
    ----------
    field_name : str
        Field name
    boundary : Polygon
        Field boundary (UTM)
    """

    try:
        props = data.get('properties')
        if props is None:
            print("Error reading properties of field.")
            return None
        field_name = props.get('field_name')
        if field_name is None:
            field_name = props.get('location_name')
        if field_name is None:
            print("Error reading field_name of field.")
            return None
    except Exception as e:
        print(f"Error reading properties of field: {e}")
        return None

    poly = __parse_polygon(data)
    if poly is None:
        print("Error reading field boundary geometry.")
        return None

    return field_name, poly


def __parse_access_point(data: Dict[str, Any]) -> Optional[Tuple[str, Point]]:

    """ Get a field access point location name and Point from a geojson formatted geometry

    Parameters
    ----------
    data : Dict[str, str]
        Dictionary holding the geometry data in geojson format

    Returns
    ----------
    location_name : str
        Location name of the access point
    point : Point
        Position of the access point (UTM)
    """

    try:
        props = data.get('properties')
        if props is None:
            print("Error reading properties of access point.")
            return None
        location_name = props.get('field_name')
        if location_name is None:
            location_name = props.get('location_name')
        if location_name is None:
            print("Error reading location_name of access point.")
            return None
    except Exception as e:
        print(f"Error reading properties of access point: {e}")
        return None

    pt = __parse_point(data)
    if pt is None:
        print("Error reading access point geometry.")
        return None

    return location_name, pt


def __parse_ref_line(data: Dict[str, Any]) -> Optional[Tuple[str, Linestring]]:

    """ Get the field location name and linestring of a track reference line from a geojson formatted geometry

    Parameters
    ----------
    data : Dict[str, str]
        Dictionary holding the geometry data in geojson format

    Returns
    ----------
    field_name : str
        Location name of the field to which the reference line belongs
    reference_line : Linestring
        Reference line as linestring (UTM)
    """

    try:
        props = data.get('properties')
        if props is None:
            print("Error reading properties of field.")
            return None
        field_name = props.get('field_name')
        if field_name is None:
            field_name = props.get('location_name')
        if field_name is None:
            print("Error reading location_name of field.")
            return None
    except Exception as e:
        print(f"Error reading properties of field: {e}")
        return None

    ls = __parse_linestring(data)
    if ls is None:
        print("Error reading field reference line geometry.")
        return None

    if len(ls.points) < 2:
        print(f"Error reading reference line")
        return None

    return field_name, ls


def __parse_silo(data: Dict[str, Any]) -> Optional[Tuple[str, SiloExtended]]:

    """ Get the SiloExtended and silo location name from a geojson formatted geometry

    Parameters
    ----------
    data : Dict[str, str]
        Dictionary holding the geometry data in geojson format

    Returns
    ----------
    location_name : str
        Silo location name
    silo : SiloExtended
        Parsed SiloExtended (UTM)
    """

    try:
        props = data.get('properties')
        if props is None:
            print("Error reading properties.")
            return None
        location_type = props.get('location_type')
        if location_type is None:
            print("Error reading location_type.")
            return None
        if location_type != 'silo':
            return None
        silo_name = props.get('name')
        if silo_name is None:
            silo_name = props.get('silo_name')
        if silo_name is None:
            silo_name = props.get('location_name')
        if silo_name is None:
            print("Error reading name of silo.")
            return None
        mass_capacity = props.get('mass_capacity')
    except Exception as e:
        print(f"Error reading properties of silo: {e}")
        return None

    poly = __parse_polygon(data)
    if poly is None:
        print("Error reading silo boundary geometry as polygon.")
        return None

    silo = SiloExtended()
    silo.name = silo_name
    silo.geometry = poly
    centroid = getCentroid2(poly)
    silo.x = centroid.x
    silo.y = centroid.y
    if mass_capacity is not None:
        silo.mass_capacity = float(mass_capacity)

    return silo_name, silo


def __parse_silo_access_point(data: Dict[str, Any]) -> Optional[Tuple[str, SiloAccessPoint]]:

    """ Get a silo access point location name and SiloAccessPoint information from a geojson formatted geometry

    Parameters
    ----------
    data : Dict[str, str]
        Dictionary holding the geometry data in geojson format

    Returns
    ----------
    location_name : str
        Location name of the access point
    access_point : SiloAccessPoint
        Parsed SiloAccessPoint (UTM)
    """

    try:
        props = data.get('properties')
        if props is None:
            print("Error reading properties.")
            return None
        location_type = props.get('location_type')
        if location_type is None:
            print("Error reading location_type.")
            return None
        if location_type != 'unloading-area' \
                and location_type != 'unloading-point' \
                and location_type != 'silo-access-point':
            return None
        silo_name = props.get('silo_name')
        if silo_name is None:
            print("Error reading name of silo.")
            return None
        mass_capacity = props.get('mass_capacity')
    except Exception as e:
        print(f"Error reading properties of silo access: {e}")
        return None

    poly = __parse_polygon(data)
    if poly is None:
        print("Error reading silo access boundary geometry.")
        return None

    sap = SiloAccessPoint()
    sap.geometry = poly
    centroid = getCentroid2(poly)
    sap.x = centroid.x
    sap.y = centroid.y
    if mass_capacity is not None:
        sap.mass_capacity = float(mass_capacity)

    return silo_name, sap


def __parse_road(data: Dict[str, str]) -> Optional[Linestring]:

    """ Get a road (linestring) from a geojson formatted geometry

    Parameters
    ----------
    data : Dict[str, str]
        Dictionary holding the geometry data in geojson format

    Returns
    ----------
    road : Linestring
        Road as linestring (UTM)
    """

    ls = __parse_linestring(data)
    if ls is None:
        print("Error reading road geometry.")
        return None

    if len(ls.points) < 2:
        print(f"Error reading road")
        return None

    return ls


def __append_point_to_json_dict(json_dict: Dict, pt: Point) -> bool:

    """ Append a point to a geojson-formatted data dictionary

    Parameters
    ----------
    json_dict : Dict
        [in, out] Geojson-formatted data dictionary
    pt : Point
        Point to be added (UTM)

    Returns
    ----------
    success : bool
        True on success
    """

    try:
        proj = Proj("+proj=utm +zone=32 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
        lat, lon = proj(pt.x, pt.y, inverse=True)
        if 'geometry' not in json_dict.keys():
            json_dict['geometry'] = dict()
        json_dict['geometry']['coordinates'] = [lat, lon]
        json_dict['geometry']['type'] = 'Point'
        return True
    except Exception as e:
        print(f"Error parsing point {pt}: {e}")
        return False


def __append_polygon_to_json_dict(json_dict: Dict, poly: Polygon) -> bool:

    """ Append a polygon to a geojson-formatted data dictionary

    Parameters
    ----------
    json_dict : Dict
        [in, out] Geojson-formatted data dictionary
    poly : Polygon
        Polygon to be added (UTM)

    Returns
    ----------
    success : bool
        True on success
    """

    coords = list()
    proj = Proj("+proj=utm +zone=32 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
    for pt in poly.points:
        try:
            lat, lon = proj(pt.x, pt.y, inverse=True)
            coords.append([lat, lon])
        except Exception as e:
            print(f"Error parsing polygon point {pt}: {e}")
            return False
    if 'geometry' not in json_dict.keys():
        json_dict['geometry'] = dict()
    json_dict['geometry']['coordinates'] = [coords]
    json_dict['geometry']['type'] = 'Polygon'

    return True


def __append_linestring_to_json_dict(json_dict: Dict, ls: Linestring) -> bool:

    """ Append a linestring to a geojson-formatted data dictionary

    Parameters
    ----------
    json_dict : Dict
        [in, out] Geojson-formatted data dictionary
    ls : Linestring
        Linestring to be added (UTM)

    Returns
    ----------
    success : bool
        True on success
    """

    coords = list()
    proj = Proj("+proj=utm +zone=32 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
    for pt in ls.points:
        try:
            lat, lon = proj(pt.x, pt.y, inverse=True)
            coords.append([lat, lon])
        except Exception as e:
            print(f"Error parsing linestring point {pt}: {e}")
            return False
    if 'geometry' not in json_dict.keys():
        json_dict['geometry'] = dict()
    json_dict['geometry']['coordinates'] = coords
    json_dict['geometry']['type'] = 'LineString'
    return True


def load_locations(path: str,
                   fields: List[Field],
                   silos: List[SiloExtended],
                   roads: List[Linestring]):

    """ Load the locations (fields, silos, roads) from a set of geojson input files

    The field, silo and access point ids will be automatically assigned

    The geojson files must follow the following format:
        {
            "type": "FeatureCollection",
            "features": [  # This level contains all objects with its properties and geometries
                {
                    "type": "Feature",
                    "properties": { ... },
                    "geometry": {...}
                },
                {
                    "type": "Feature",
                    "properties": { ... },
                    "geometry": {...}
                },
                ...
            ]
        }

    Expected files in the directory:
    - field_boundaries.geojson/.json: geojson formatted file containing the field boundaries referenced by field name:
        "properties": {
            "field_nr": null,
            "field_name": "Field_XYZ"  # Field name (identifier)
        },
        "geometry": {  # Geometry of the field boundary (WGS)
            "coordinates": [...],
            "type": "Polygon"
        }
    - field_access_points.geojson/.json: geojson formatted file containing the field access points referenced by field name:
        "properties": {
            "location_name": "Field_XYZ"  # Name of the field to which the access point belongs
        },
        "geometry": {  # Geometry of the position of the access point (WGS)
            "coordinates": [...],
            "type": "Point"
        }
    - field_reference_lines.geojson/.json: geojson formatted file containing the track reference lines referenced by field name
        "properties": {
            "location_name": "Field_XYZ"  # Name of the field to which the reference line belongs
        },
        "geometry": {  # Geometry of the reference line (WGS)
            "coordinates": [...],
            "type": "LineString"
        }
    - silos.geojson/.json: geojson formatted file containing the silos boundaries and (optionally) the silo access points referenced by silo name
        "properties": {
            "name": "Silo_XYZ",  # Silo name (identifier)
            "location_type": "silo",  # Location type = "silo"
            "mass_capacity": 1228236.768  # Silo mass capacity [kg]
        },
            "geometry": {
            "coordinates": [...],
            "type": "Polygon"
        }
    - silo_access_points.geojson/.json: geojson formatted file containing the silo access points' boundaries and information referenced by field name (the silo access points can also be located in the silos file):
        "properties": {
            "name": "Unloading_point_XYZ",  # Name of the silo access point
            "silo_name": "Silo 1",  # Name of the silo to which the access point belongs
            "location_type": "unloading-area",  # location_type = "unloading-area" | "unloading-point" | "silo-access-point"
            "mass_capacity": 40000  # Mass capacity of the silo access/unloading point [kg]
        },
            "geometry": {  # Geometry of the silo access/unloading area boundary (WGS)
            "coordinates": [...],
            "type": "Polygon"
        }
    - roads.geojson/.json: geojson formatted file containing the field boundaries referenced by field name
        "properties": {
            "name": "Road_XYZ"  # Name of the road
        },
        "geometry": {  # Geometry of the road (WGS)
            "coordinates": [...],
            "type": "LineString"
        }

    Parameters
    ----------
    path : str
        Directory where the files are located
    fields : List[Field]
        [out] Loaded fields
    silos : List[SiloExtended]
        [out] Loaded silos
    roads : List[Linestring]
        [out] Loaded roads
    """

    fields.clear()
    silos.clear()
    roads.clear()
    _boundaries: Dict[str, Polygon] = dict()
    _access_points: Dict[str, List[Point]] = dict()
    _ref_lines: Dict[str, List[Linestring]] = dict()
    _silos: Dict[str, SiloExtended] = dict()
    _saps: Dict[str, List[SiloAccessPoint]] = dict()
    for root, dirs, files in os.walk(path):
        for file in files:
            try:
                if file.lower().endswith(".json") or file.endswith(".geojson"):
                    if file.lower().find("boundaries") >= 0:
                        f = open(f'{root}/{file}')
                        data = json.load(f)
                        if data is not None:
                            for feature in data['features']:
                                data2 = __parse_field_boundary(feature)
                                if data2 is not None:
                                    _boundaries[data2[0]] = data2[1]

                    elif file.lower().find("field_access_points") >= 0:
                        f = open(f'{root}/{file}')
                        data = json.load(f)
                        if data is not None:
                            for feature in data['features']:
                                data2 = __parse_access_point(feature)
                                if data2 is not None:
                                    _list = _access_points.get(data2[0])
                                    if _list is None:
                                        _list = PointVector()
                                        _access_points[data2[0]] = _list
                                    _list.append(data2[1])

                    elif file.lower().find("reference_line") >= 0:
                        f = open(f'{root}/{file}')
                        data = json.load(f)
                        if data is not None:
                            for feature in data['features']:
                                data2 = __parse_ref_line(feature)
                                if data2 is not None:
                                    _list = _ref_lines.get(data2[0])
                                    if _list is None:
                                        _list = LinestringVector()
                                        _ref_lines[data2[0]] = _list
                                    _list.append(data2[1])

                    elif file.lower().find("silo") >= 0:
                        f = open(f'{root}/{file}')
                        data = json.load(f)
                        if data is not None:
                            for feature in data['features']:
                                data2 = __parse_silo(feature)
                                if data2 is not None:
                                    _silos[data2[0]] = data2[1]
                                else:
                                    data2 = __parse_silo_access_point(feature)
                                    if data2 is not None:
                                        _list = _saps.get(data2[0])
                                        if _list is None:
                                            _list = list()
                                            _saps[data2[0]] = _list
                                        _list.append(data2[1])

                    elif file.lower().find("silo_access_points") >= 0:
                        f = open(f'{root}/{file}')
                        data = json.load(f)
                        if data is not None:
                            for feature in data['features']:
                                data2 = __parse_silo_access_point(feature)
                                if data2 is not None:
                                    _list = _saps.get(data2[0])
                                    if _list is None:
                                        _list = list()
                                        _saps[data2[0]] = _list
                                    _list.append(data2[1])

                    elif file.lower().find("road") >= 0:
                        f = open(f'{root}/{file}')
                        data = json.load(f)
                        if data is not None:
                            for feature in data['features']:
                                data2 = __parse_road(feature)
                                if data2 is not None:
                                    roads.append(data2)

            except Exception as e:
                print(f'Error reading file {file}: {e}')

    field_ids = set()
    for field_name, boundary in _boundaries.items():
        faps = _access_points.get(field_name)
        if faps is None:
            print(f'No access points loaded for field {field_name}. Disregarding it.')
            continue

        ref_lines = _ref_lines.get(field_name)
        if ref_lines is None:
            print(f'No reference lines loaded for field {field_name}. Disregarding it.')
            continue

        field = Field()
        field.name = field_name
        field_ids.add(get_field_id_from_location_name(field_name))
        field.outer_boundary = boundary
        sf = Subfield()
        sf.boundary_outer = get_copy_aro(boundary)
        for ap in faps:
            fap = FieldAccessPoint(ap, -1)
            fap.id = len(fields) * 1000 + len(sf.access_points)
            sf.access_points.append(fap)
        sf.reference_lines = ref_lines
        field.subfields.append(sf)
        fields.append(field)

    silo_ids = set()
    for silo_name, silo in _silos.items():
        silo_ids.add(get_silo_id_from_location_name(silo_name))
        saps = _access_points.get(silo_name)
        if saps is not None:
            for _ap in saps:
                silo.access_points.append( SiloAccessPoint(_ap.x, _ap.y) )
        saps = _saps.get(silo_name)
        if saps is not None:
            silo.access_points.extend(saps)
        silos.append(silo)

    _field_id_ref = 0
    for field in fields:
        _id = get_field_id_from_location_name(field.name)
        if _id is not None:
            field.id = _id
        else:
            while _field_id_ref in field_ids:
                _field_id_ref += 1
            field.id = _field_id_ref
            _field_id_ref += 1

    _silo_id_ref = 0
    for silo in silos:
        _id = get_silo_id_from_location_name(silo.name)
        if _id is not None:
            silo.id = _id
        else:
            while _silo_id_ref in silo_ids:
                _silo_id_ref += 1
            silo.id = _silo_id_ref
            _silo_id_ref += 1


def save_locations(dir_path: str,
                   fields: List[Field],
                   silos: List[SiloExtended],
                   roads: List[Linestring]) -> bool:

    """ Save the locations (fields, silos, roads) in a set of geojson output files

    The following files will be generated:
    - field_boundaries.geojson/.json: geojson formatted file containing the field boundaries referenced by field name
    - field_access_points.geojson/.json: geojson formatted file containing the field access points referenced by field name
    - field_reference_lines.geojson/.json: geojson formatted file containing the track reference lines referenced by field name
    - silos.geojson/.json: geojson formatted file containing the silos boundaries and the silo access points referenced by silo name
    - roads.geojson/.json: geojson formatted file containing the field boundaries referenced by field name

    Parameters
    ----------
    dir_path : str
        Output directory where the files will be saved
    fields : List[Field]
        Fields to be saved
    silos : List[SiloExtended]
        Silos to be saved
    roads : List[Linestring]
        Roads to be saved

    Returns
    ----------
    success : bool
        True on success
    """

    ok = True

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    with open(f'{dir_path}/field_boundaries.geojson', 'w') as f:
        boundaries = list()
        for field in fields:
            boundary_dict = dict()
            boundary_dict['type'] = 'Feature'
            boundary_dict['properties'] = {
                "field_nr": field.id,
                "field_name": field.name
            }
            ok &= __append_polygon_to_json_dict(boundary_dict, field.outer_boundary)
            boundaries.append(boundary_dict)
        data = {"type": "FeatureCollection",
                "features": boundaries }
        json.dump(data, f, indent=4, ensure_ascii=False)

    with open(f'{dir_path}/field_reference_lines.geojson', 'w') as f:
        rls = list()
        for field in fields:
            for sf in field.subfields:
                for rl in sf.reference_lines:
                    rl_dict = dict()
                    rl_dict['type'] = 'Feature'
                    rl_dict['properties'] = {
                        "location_name": field.name
                    }
                    ok &= __append_linestring_to_json_dict(rl_dict, rl)
                    rls.append(rl_dict)
        data = {"type": "FeatureCollection",
                "features": rls }
        json.dump(data, f, indent=4, ensure_ascii=False)

    with open(f'{dir_path}/field_access_points.geojson', 'w') as f:
        faps = list()
        for field in fields:
            for sf in field.subfields:
                for fap in sf.access_points:
                    fap_dict = dict()
                    fap_dict['type'] = 'Feature'
                    fap_dict['properties'] = {
                        "location_name": field.name
                    }
                    ok &= __append_point_to_json_dict(fap_dict, fap)
                    faps.append(fap_dict)
        data = {"type": "FeatureCollection",
                "features": faps }
        json.dump(data, f, indent=4, ensure_ascii=False)

    with open(f'{dir_path}/silos.geojson', 'w') as f:
        silo_objs = list()
        for silo in silos:
            silo_dict = dict()
            silo_dict['type'] = 'Feature'
            silo_dict['properties'] = {
                "name": silo.name,
                "location_type": 'silo',
                "mass_capacity": silo.mass_capacity
            }
            ok &= __append_polygon_to_json_dict(silo_dict, silo.geometry)
            silo_objs.append(silo_dict)

            for i, sap in enumerate(silo.access_points):
                sap_dict = dict()
                sap_dict['type'] = 'Feature'
                sap_dict['properties'] = {
                    "name": f'Unloading {i+1}',
                    "silo_name": silo.name,
                    "location_type": "unloading-area",
                    "mass_capacity": sap.mass_capacity
                }
                ok &= __append_polygon_to_json_dict(sap_dict, sap.geometry)
                silo_objs.append(sap_dict)
        data = {"type": "FeatureCollection",
                "features": silo_objs }
        json.dump(data, f, indent=4, ensure_ascii=False)

    with open(f'{dir_path}/roads.geojson', 'w') as f:
        rds = list()
        for i, road in enumerate(roads):
            road_dict = dict()
            road_dict['type'] = 'Feature'
            road_dict['properties'] = {
                "name": f'Road {i}'
            }
            ok &= __append_linestring_to_json_dict(road_dict, road)
            rds.append(road_dict)

        data = {"type": "FeatureCollection",
                "features": rds }
        json.dump(data, f, indent=4, ensure_ascii=False)

    return ok
