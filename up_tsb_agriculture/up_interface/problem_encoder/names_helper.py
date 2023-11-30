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

from typing import Tuple, Union

def get_street_location_name() -> str:

    """ Get the object name for street location

    Returns
    ----------
    location_name : str
        Object name for street location
    """

    return f'loc_street_all'


def get_field_location_name(field_id: int) -> str:

    """ Get the object name for a field location based on its Id

    Parameters
    ----------
    field_id : int
        Field id

    Returns
    ----------
    location_name : str
        Object name for field location
    """

    return f'loc_field_{field_id}'

def get_field_id_from_location_name(name: str) -> Union[int, None]:

    """ Get the Id of a field based on its object name

    Parameters
    ----------
    name : int
        Object name

    Returns
    ----------
    id : int|None
        Id of the field (None if the object name is invalid)
    """

    if name is None:
        return None
    base = 'loc_field_'
    ind = name.find(base)
    if ind != 0:
        return None
    try:
        return int( name[len(base):] )
    except:
        return None


def get_field_access_location_name(field_id: int, access_point_idx: int) -> str:

    """ Get the object name for a field access location based on its field's Id and the index of the field access

    Parameters
    ----------
    field_id : int
        Field id
    access_point_idx : int
        Access point index

    Returns
    ----------
    location_name : str
        Object name for the field access location
    """

    return f'loc_field_access_point_{field_id}_{access_point_idx}'

def get_field_access_id_from_location_name(name: str) -> Union[Tuple[int, int], None]:

    """ Get the field Id and field access index based on the field access object name

    Parameters
    ----------
    name : int
        Field access object name

    Returns
    ----------
    field_id : int|None
        Id of the field (None if the object name is invalid)
    access_point_idx : int
        Index of the field access point
    """

    if name is None:
        return None
    base = 'loc_field_access_point_'
    ind = name.find(base)
    if ind != 0:
        return None
    try:
        ind2 = name.find('_', len(base))
        return int( name[len(base):ind2] ), int( name[ind2+1:] )
    except:
        return None

def get_field_name_from_field_access_location_name(name: str) -> Union[str, None]:

    """ Get the field object name corresponding to a field access based on the field access object name

    Parameters
    ----------
    name : str
        Field access object name

    Returns
    ----------
    silo_name : str|None
        Object name of the field (None if the object name is invalid)
    """

    try:
        return get_field_location_name( get_field_access_id_from_location_name(name)[0] )
    except:
        return None


def get_silo_location_name(silo_id: int) -> str:

    """ Get the object name for a silo location based on its Id

    Parameters
    ----------
    silo_id : int
        Silo id

    Returns
    ----------
    location_name : str
        Object name for the silo location
    """

    return f'loc_silo_{silo_id}'

def get_silo_id_from_location_name(name: str) -> Union[int, None]:

    """ Get the Id of a silo based on its object name

    Parameters
    ----------
    name : str
        Object name

    Returns
    ----------
    id : int|None
        Id of the silo (None if the object name is invalid)
    """

    if name is None:
        return None
    base = 'loc_silo_'
    ind = name.find(base)
    if ind != 0:
        return None
    try:
        return int( name[len(base):] )
    except:
        return None


def get_silo_access_location_name(silo_id: int, access_point_idx: int) -> str:

    """ Get the object name for a silo access location based on its silo's Id and the index of the silo access

    Parameters
    ----------
    silo_id : int
        Silo id
    access_point_idx : int
        Access point index

    Returns
    ----------
    location_name : str
        Object name for the silo access location
    """

    return f'loc_silo_access_point_{silo_id}_{access_point_idx}'

def get_silo_access_id_from_location_name(name: str) -> Union[Tuple[int, int], None]:

    """ Get the silo Id and silo access index based on the silo access object name

    Parameters
    ----------
    name : str
        Silo access object name

    Returns
    ----------
    silo_id : int|None
        Id of the silo (None if the object name is invalid)
    access_point_idx : int
        Index of the silo access point
    """

    if name is None:
        return None
    base = 'loc_silo_access_point_'
    ind = name.find(base)
    if ind != 0:
        return None
    try:
        ind2 = name.find('_', len(base))
        return int( name[len(base):ind2] ), int( name[ind2+1:] )
    except:
        return None

def get_silo_name_from_silo_access_location_name(name: str) -> Union[str, None]:

    """ Get the silo object name corresponding to a silo access based on the silo access object name

    Parameters
    ----------
    name : str
        Silo access object name

    Returns
    ----------
    silo_name : str|None
        Object name of the silo (None if the object name is invalid)
    """

    try:
        return get_silo_location_name( get_silo_access_id_from_location_name(name)[0] )
    except:
        return None


def get_machine_initial_location_name(machine_name: str) -> str:

    """ Get the object name for a machine's initial location based on its object name

    Parameters
    ----------
    machine_name : str
        Machine object name

    Returns
    ----------
    location_name : str
        Object name for the machine's initial location
    """

    return f'loc_0_{machine_name}'

def get_machine_name_from_initial_location_name(name: str) -> Union[str, None]:

    """ Get the object name of a machine corresponding to a given machine's initial location object name

    Parameters
    ----------
    name : str
        Machine's initial location name

    Returns
    ----------
    machine_name : str|None
        Object name of the machine (None if the object name is invalid)
    """

    base = 'loc_0_'
    ind = name.find(base)
    if ind != 0:
        return None
    try:
        return name[len(base):]
    except:
        return None


def get_harvester_name(machine_id: int):

    """ Get the object name for a harvester based on its Id

    Parameters
    ----------
    machine_id : int
        Machine id

    Returns
    ----------
    machine_name : str
        Object name for the harvester
    """

    return f'harv_{machine_id}'

def get_harvester_id_from_name(name: str) -> Union[int, None]:

    """ Get the Id of a harvester based on its object name

    Parameters
    ----------
    name : str
        Object name

    Returns
    ----------
    id : int|None
        Id of the harvester (None if the object name is invalid)
    """

    if name is None:
        return None
    base = 'harv_'
    ind = name.find(base)
    if ind != 0:
        return None
    try:
        return int( name[len(base):] )
    except:
        return None

def get_tv_name(machine_id: int):

    """ Get the object name for a transport vehicle based on its Id

    Parameters
    ----------
    machine_id : int
        Machine id

    Returns
    ----------
    machine_name : str
        Object name for the transport vehicle
    """

    return f'tv_{machine_id}'

def get_tv_id_from_name(name: str) -> Union[int, None]:

    """ Get the Id of a transport vehicle based on its object name

    Parameters
    ----------
    name : str
        Object name

    Returns
    ----------
    id : int|None
        Id of the transport vehicle (None if the object name is invalid)
    """

    if name is None:
        return None
    base = 'tv_'
    ind = name.find(base)
    if ind != 0:
        return None
    try:
        return int( name[len(base):] )
    except:
        return None


def get_compactor_name(compactor_id: int):

    """ Get the object name for a compactor based on its Id

    Parameters
    ----------
    compactor_id : int
        Compactor id

    Returns
    ----------
    machine_name : str
        Object name for the compactor
    """

    return f'compactor_{compactor_id}'

def get_compactor_id_from_name(name: str) -> Union[int, None]:

    """ Get the Id of a compactor based on its object name

    Parameters
    ----------
    name : str
        Object name

    Returns
    ----------
    id : int|None
        Id of the compactor (None if the object name is invalid)
    """

    if name is None:
        return None
    base = 'compactor_'
    ind = name.find(base)
    if ind != 0:
        return None
    try:
        return int( name[len(base):] )
    except:
        return None



