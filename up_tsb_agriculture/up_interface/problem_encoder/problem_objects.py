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
from unified_planning.shortcuts import *
import up_interface.types as upt

class ProblemObjects:

    """ Class holding the UP problem objects. """

    def __init__(self):
        self.fields: Dict[str, Object] = dict()
        """ Field objects: {object_name: object} """

        self.field_accesses: Dict[str, Object] = dict()
        """ Field-access objects: {object_name: object} """

        self.silos: Dict[str, Object] = dict()
        """ Silo objects: {object_name: object} """

        self.silo_accesses: Dict[str, Object] = dict()
        """ Silo-access objects: {object_name: object} """

        self.machine_init_locations: Dict[str, Object] = dict()
        """ Machine initial location objects: {object_name: object} """

        self.harvesters: Dict[str, Object] = dict()
        """ Harvester objects: {object_name: object} """

        self.tvs: Dict[str, Object] = dict()
        """ Tv objects objects: {object_name: object} """

        self.compactors: Dict[str, Object] = dict()
        """ Compactor objects: {object_name: object} """

        self.no_harvester: Object = None
        """ Object corresponding to 'no-harvester' """

        self.no_compactor: Object = None
        """ Object corresponding to 'no-compactor' """

        self.no_init_loc: Object = None
        """ Object corresponding to 'no-machine-initial-location' """

        self.no_field: Object = None
        """ Object corresponding to 'no-field' """

        self.no_field_access: Object = None
        """ Object corresponding to 'no-field-access' """

        self.no_silo_access: Object = None
        """ Object corresponding to 'no-silo-access' """

        self.count_fields: int = 0
        """ Amount of fields in the problem (without the 'no-field' object) """

        self.count_fields_to_work: int = 0
        """ Amount of unfinished fields in the problem, i.e., fields that have yield to harvest (without the 'no-field' object) """

        self.count_harvesters: int = 0
        """ Amount of harvesters in the problem (without the 'no-harvester' object) """

        self.count_tvs: int = 0
        """ Amount of transport vehicles in the problem """

        self.count_silos: int = 0
        """ Amount of silos in the problem """

        self.count_compactors: int = 0
        """ Amount of compactors in the problem (without the 'no-compactor' object) """

    def get_no_object_by_type(self, object_type: Type) -> Optional[Object]:
        if object_type is upt.Field:
            return self.no_field
        if object_type is upt.FieldAccess:
            return self.no_field_access
        if object_type is upt.Harvester:
            return self.no_harvester
        if object_type is upt.SiloAccess:
            return self.no_silo_access
        if object_type is upt.Compactor:
            return self.no_compactor
        return None
