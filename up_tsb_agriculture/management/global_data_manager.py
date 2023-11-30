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

import copy
from typing import Union, Dict
from util_arolib.types import *
from util_arolib.types import get_copy as get_copy_aro
from util_arolib.geometry import correct_polygon
from silo_planning.types import *


class GlobalDataManager:

    """ Class used to register and access all objects in the problem, incl. fields, machines and silos """

    # @todo: replace with realistic values
    DEF_HARV_UNLOADING_SPEED_MASS = 100.0
    DEF_HARV_UNLOADING_SPEED_VOLUME = 100.0
    DEF_TV_UNLOADING_SPEED_MASS = 200.0
    DEF_TV_UNLOADING_SPEED_VOLUME = 200.0
    DEF_MASS_PER_SWEEP = 500.0

    def __init__(self):
        self.__fields: Dict[int, Field] = dict()
        """ Registered fields: {field_id: field}"""

        self.__machines: Dict[int, Machine] = dict()
        """ Registered machines (harvesters, transport vehicles): {machine_id: machine}"""

        self.__silos: Dict[int, SiloExtended] = dict()
        """ Registered silos: {silo_id: silo}"""

        self.__compactors: Dict[int, Compactor] = dict()
        """ Registered compactors: {compactor_id: compactor}"""

    def register_field(self, field: Field) -> bool:

        """ Register/add a field with unique id

        Note: the saved object is an (adjusted) copy of the input object

        Parameters
        ----------
        field : Field
            Field

        Returns
        ----------
        success : bool
            True on success
        """

        if field.id in self.__fields.keys():
            print(f'[ERROR]: a field with given id was already registered')
            return False

        field_new = self.__initialize_field(field)
        if field_new is None:
            return False
        self.__fields[field_new.id] = field_new
        return True

    def register_machine(self, machine: Machine) -> bool:

        """ Register/add a machine with unique id

        Note: the saved object is an (adjusted) copy of the input object

        Parameters
        ----------
        machine : Machine
            Machine

        Returns
        ----------
        success : bool
            True on success
        """

        if machine.id in self.__machines.keys():
            print(f'[ERROR]: a machine with given id {machine.id} was already registered')
            return False
        m = get_copy_aro(machine)
        if m.unloading_speed_mass <= 0.0:
            m.unloading_speed_mass = self.DEF_HARV_UNLOADING_SPEED_MASS if m.machinetype is MachineType.HARVESTER \
                                     else self.DEF_TV_UNLOADING_SPEED_MASS
        if m.unloading_speed_volume <= 0.0:
            m.unloading_speed_mass = self.DEF_HARV_UNLOADING_SPEED_VOLUME if m.machinetype is MachineType.HARVESTER \
                                     else self.DEF_TV_UNLOADING_SPEED_VOLUME
        m.bunker_mass = max(m.bunker_mass, 0.0)
        m.bunker_volume = max(m.bunker_volume, 0.0)
        self.__machines[machine.id] = m
        return True

    def register_silo(self, silo: SiloExtended) -> bool:

        """ Register/add a silo with unique id

        Note: the saved object is an (adjusted) copy of the input object

        Parameters
        ----------
        silo : SiloExtended
            Silo

        Returns
        ----------
        success : bool
            True on success
        """

        if silo.id in self.__silos.keys():
            print(f'[ERROR]: a silo with given id was already registered')
            return False
        self.__silos[silo.id] = copy.deepcopy(silo)
        return True

    def register_compactor(self, compactor: Compactor) -> bool:

        """ Register/add a compactor with unique id

        Note: the saved object is an (adjusted) copy of the input object

        Parameters
        ----------
        compactor : Compactor
            Compactor

        Returns
        ----------
        success : bool
            True on success
        """

        if compactor.id in self.__compactors.keys():
            print(f'[ERROR]: a compactor with given id {compactor.id} was already registered')
            return False
        if compactor.silo_id not in self.__silos.keys():
            print(f'[ERROR]: a compactor with given id {compactor.id} belongs to an unregistered silo')
            return False
        c = copy.deepcopy(compactor)
        if c.mass_per_sweep <= 0.0:
            c.unloading_speed_mass = self.DEF_MASS_PER_SWEEP
        self.__compactors[compactor.id] = c
        return True

    @property
    def fields(self) -> Dict[int, Field]:

        """ Get all registered fields

        Returns
        ----------
        fields : Dict[int, Field]
            Registered fields: {field_id: field}
        """

        return self.__fields

    @property
    def machines(self) -> Dict[int, Machine]:

        """ Get all registered machines (harvesters, transport vehicles)

        Returns
        ----------
        machines : Dict[int, Machine]
            Registered machines: {machine_id: machine}
        """

        return self.__machines

    @property
    def silos(self) -> Dict[int, SiloExtended]:
        """ Get all registered silos

        Returns
        ----------
        silos : Dict[int, SiloExtended]
            Registered silos: {silo_id: silo}
        """
        return self.__silos

    @property
    def compactors(self) -> Dict[int, Compactor]:
        """ Get all registered compactors

        Returns
        ----------
        compactors : Dict[int, Compactor]
            Registered compactors: {compactor_id: compactor}
        """
        return self.__compactors

    def get_field(self, field_id: int) -> Union[Field, None]:

        """ Get the registered field with the given id

        Parameters
        ----------
        field_id : int
            Field id

        Returns
        ----------
        field : Field
            Registered field (None if not found)
        """

        return self.__fields.get(field_id)

    def get_field_with_silos(self, field_id: int, silos: List[ Union[SiloExtended, ResourcePoint] ] = None) -> Union[Field, None]:

        """ Get a copy of a registered field adding the given silos/resource points

        Parameters
        ----------
        field_id : int
            Field id
        silos : List[ Union[SiloExtended, ResourcePoint] ]
            Silos / resource points. If None, it will add all registered silos.

        Returns
        ----------
        field : Field
            Copy of the registered field with silos (None if not found)
        """

        f = self.__fields.get(field_id)
        if f is None:
            return None
        f_new = get_copy_aro(f)
        for sf in f_new.subfields:
            sf.resource_points = ResourcePointVector()
            if silos is None:
                for silo in self.__silos.values():
                    sf.resource_points.append( copy.deepcopy(silo) )
            else:
                for silo in silos:
                    sf.resource_points.append( copy.deepcopy(silo) )
        return f_new

    def get_machine(self, machine_id: int) -> Union[Machine, None]:
        """ Get the registered machine with the given id

        Parameters
        ----------
        machine_id : int
            Machine id

        Returns
        ----------
        machine : Machine
            Registered machine (None if not found)
        """
        return self.__machines.get(machine_id)

    def get_silo(self, silo_id: int) -> Union[SiloExtended, None]:
        """ Get the registered silo with the given id

        Parameters
        ----------
        silo_id : int
            Silo id

        Returns
        ----------
        silo : SiloExtended
            Registered silo (None if not found)
        """
        return self.__silos.get(silo_id)

    def get_compactor(self, compactor_id: int) -> Union[Compactor, None]:
        """ Get the registered silo with the given id

        Parameters
        ----------
        compactor_id : int
            Compactor id

        Returns
        ----------
        compactor : Compactor
            Registered compactor (None if not found)
        """
        return self.__compactors.get(compactor_id)

    def get_field_copy(self, field_id: int) -> Union[Field, None]:

        """ Get a copy the registered field with the given id

        Parameters
        ----------
        field_id : int
            Field id

        Returns
        ----------
        field : Field
            Copy of the registered field (None if not found)
        """

        f = self.__fields.get(field_id)
        if f is None:
            print(f'[ERROR]: invalid field id')
            return None
        return get_copy_aro(f)

    def get_machine_copy(self, machine_id: int) -> Union[Machine, None]:
        """ Get a copy the registered field with the given id

        Parameters
        ----------
        machine_id : int
            Machine id

        Returns
        ----------
        machine : Machine
            Copy of the registered machine (None if not found)
        """
        m = self.__machines.get(machine_id)
        if m is None:
            print(f'[ERROR]: invalid machine id')
            return None
        return get_copy_aro(m)

    def get_silo_copy(self, silo_id: int) -> Union[SiloExtended, None]:
        """ Get a copy the registered field with the given id

        Parameters
        ----------
        silo_id : int
            Silo id

        Returns
        ----------
        silo : SiloExtended
            Copy of the registered silo (None if not found)
        """
        s = self.__silos.get(silo_id)
        if s is None:
            print(f'[ERROR]: invalid silo id')
            return None
        return copy.deepcopy(s)

    def get_compactor_copy(self, compactor_id: int) -> Union[Compactor, None]:
        """ Get a copy the registered field with the given id

        Parameters
        ----------
        compactor_id : int
            Compactor id

        Returns
        ----------
        compactor : Compactor
            Copy of the registered compactor (None if not found)
        """
        c = self.__compactors.get(compactor_id)
        if c is None:
            print(f'[ERROR]: invalid compactor id')
            return None
        return copy.deepcopy(c)

    @staticmethod
    def __initialize_field(_field: Field) -> Union[Field, None]:
        """ Initialize a field

        Parameters
        ----------
        _field : Field
            Field

        Returns
        ----------
        initialize_field : Field
            Initialized field (None on error)
        """

        if len(_field.subfields) == 0:
            print(f'[ERROR]: invalid field: the field has no subfield')
            return None

        field = get_copy_aro(_field)
        field.subfields = SubfieldVector()
        for sf in _field.subfields:
            if len(sf.boundary_outer.points) > 2 \
                    and len(sf.access_points) > 0 \
                    and len(sf.reference_lines) > 0 \
                    and len(sf.reference_lines[0].points) > 1:
                field.subfields.append(sf)
                break
        if len(field.subfields) == 0:
            print(f'[ERROR]: invalid field: the field has no valid subfield '
                  f'(boundary, access points, reference lines, ...)')
            return None
        sf = field.subfields[0]
        sf.resource_points = ResourcePointVector()

        correct_polygon(field.outer_boundary, True)
        for sf in field.subfields:
            correct_polygon(sf.boundary_outer, True)
            correct_polygon(sf.boundary_inner, True)

        return field
