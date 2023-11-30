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

from typing import List, Dict, Union, Tuple, Optional


class FieldPreAssignment:

    """ Class holding the field pre-assignment information """

    def __init__(self):
        self.harv_id: Optional[int] = None
        """ Id of the harvester pre-assigned to the field """

        self.turn: Optional[int] = None
        """ Turn pre-assigned to the field """


class FieldPreAssignments:

    """ Class holding the information of all field pre-assignments """

    def __init__(self):
        self.field_pre_assignments: Dict[int, FieldPreAssignment] = dict()
        """ Field pre-assignments: {field_id: field_pre_assignment} """

    def get(self, field_id: int) -> Union[FieldPreAssignment, None]:
        """ Get the pre-assignment of a given field

        Parameters
        ----------
        field_id : int
            Field id

        Returns
        ----------
        field_pre_assignment : FieldPreAssignment | None
            Field pre-assignment (None if field does not exist or no pre-assignment exist for that field)
        """
        return self.field_pre_assignments.get(field_id)

    def from_harvesters_assigned_sorted_fields(self, harv_sorted_fields: Dict[int, List[int]]):
        """ Re-initialize the field pre-assignments based on a given list of field-turns for the harvesters

        Parameters
        ----------
        harv_sorted_fields : Dict[int, List[int]]
            Field turns for harvesters: {harv_id, [field_ids_sorted_by_turn]}
        """
        self.field_pre_assignments = dict()
        for harv_id, field_ids in harv_sorted_fields.items():
            for i, field_id in enumerate(field_ids):
                assert field_id not in self.field_pre_assignments.keys(), f'Field with id {field_id} was assigned to more than one harvester'
                ass = FieldPreAssignment()
                ass.harv_id = harv_id
                ass.turn = i+1
                self.field_pre_assignments[field_id] = ass

    def get_sorted_fields_for_harvesters(self) -> Dict[int, List[int]]:
        """ Get the field-turns for the harvesters for the current field pre-assignments

        Returns
        ----------
        harv_sorted_fields : Dict[int, List[int]]
            Field turns for harvesters: {harv_id, [field_ids_sorted_by_turn]}
        """

        harv_turns = dict()
        for field_id, ass in self.field_pre_assignments.items():
            if ass.harv_id is None or ass.turn is None or ass.turn < 1:
                continue
            turns = harv_turns.get(ass.harv_id)
            if turns is None:
                turns = dict()
                harv_turns[ass.harv_id] = turns
            assert ass.turn not in turns, f'Harvester with id {ass.harv_id} has repeated field turns'
            turns[ass.turn] = field_id

        sorted_fields = dict()
        for harv_id, turns in harv_turns.items():
            sorted_turns = [(turn, field_id) for turn, field_id in turns.items() ]
            sorted_turns.sort(key=lambda x: x[0])
            assert sorted_turns[0][0] == 1, f'The first field turn for harvester with id {harv_id} is not 1'
            assert sorted_turns[-1][0] == len(sorted_turns), f'Field turns for harvester with id {harv_id} missing'
            sorted_fields[harv_id] = [ turn[1] for turn in sorted_turns ]
        return sorted_fields

    def is_valid(self) -> bool:
        """ Check if the current field pre-assignments are valid

        For instance, they are not valid if more than one field have the same harvester+turn assigned to them.

        Returns
        ----------
        valid : bool
            True if valid
        """
        try:
            self.get_sorted_fields_for_harvesters()
            return True
        except:
            return False

    def get_last_pre_assigned_turn(self, harv_id: Union[int, None]) -> int:
        """ Get the maximum amount of field turns preassigned to a given harvester or all harvesters

        Parameters
        ----------
        harv_id : int | None
            Id of the harvester (if None, the maximum amount of field turns preassigned to all harvesters will be returned, e.g., if one harvester has 4 turns and another one 5, 5 will be returned)

        Returns
        ----------
        max_turns : int
            Maximum amount of field turns for the given or all harvester(s)
        """

        max_turn = 0
        harv_turns = self.get_sorted_fields_for_harvesters()
        if harv_id is None:  # all harvesters
            for ids in harv_turns.values():
                max_turn = max(max_turn, len(ids))
        else:
            ids = harv_turns.get(harv_id)
            if ids is not None:
                max_turn = len(ids)
        return max_turn

class TVPreAssignments:

    """ Class holding the information of all transport vehicle pre-assignments """

    def __init__(self):
        self.harvester_tv_turns: Dict[int, List[int]] = dict()
        """ Transport vehicles with assigned harvester overload turns: {harv_id: [tv_ids_sorted_by_turn]} """

        self.tv_assigned_harvesters_without_turns: Dict[int, int] = dict()  # {tv_id, harv_id}
        """ Harvesters assigned to transport vehicles without overload turn: {tv_id: harv_id} """

        self.cyclic_turns: bool = True
        """ Flag stating whether the assigned transport vehicle overload turns are cyclic for the corresponding harvester (after the last turn, the turns are repeated) or not (once the turns are over, any available/valid transport vehicle can overload from this harvester"""

        self.filling_level_percentage_to_force_unload: float = 50
        """ Bunker filling level % threshold used to force the transport vehicle to drive to the silo and unload after its overload turn """

    def get_tv_harvester_and_turn(self, tv_id: int) -> Tuple[Union[int, None], Union[int, None]]:
        """ Get the pre-assigned harvester and, if existent, overload turn for a given transport vehicle

        Parameters
        ----------
        tv_id : int
            Transport vehicle Id

        Returns
        ----------
        harv_id : int | None
            Id of the harvester pre-assigned to the transport vehicle (None id no harvester was pre-assigned)
        turn : int | None
            Overload turn pre-assigned to the transport vehicle (None id no turn was pre-assigned)
        """

        assert self.is_valid(), f'Assignments are not valid'
        harv_id = self.tv_assigned_harvesters_without_turns.get(tv_id)
        if harv_id is not None:
            return harv_id, None
        for harv_id, tv_ids in self.harvester_tv_turns.items():
            for i, _id in enumerate(tv_ids):
                if _id == tv_id:
                    return harv_id, i+1
        return None, None

    def is_valid(self) -> bool:
        """ Check if the current transport vehicle pre-assignments are valid

        For instance, they are not valid if a transport vehicle was assigned to more than one harvester.

        Returns
        ----------
        valid : bool
            True if valid
        """

        tvs_with_turns = set()
        for tv_ids in self.harvester_tv_turns.values():
            for tv_id in tv_ids:
                if tv_id in tvs_with_turns:
                    print(f'Tv with id {tv_id} was assigned a turn for more than one harvester')
                    return False
                if tv_id in tvs_with_turns or tv_id in self.tv_assigned_harvesters_without_turns.keys():
                    print(f'Tv with id {tv_id} was assigned both with and without turn')
                    return False
                tvs_with_turns.add(tv_id)
        for harv_id in self.tv_assigned_harvesters_without_turns.values():
            turns = self.harvester_tv_turns.get(harv_id)
            if turns is not None and len(turns) > 0:
                print(f'Harvester with id {harv_id} was assigned both with and without turns')
                return False

        return True

    def get_max_turns(self):
        """ Get the maximum amount of overload turns preassigned to a harvester
        Returns
        ----------
        max_turns : int
            Maximum amount of overload turns preassigned to a harvester
        """

        assert self.is_valid(), f'Assignments are not valid'
        max_turn = 0
        for tv_ids in self.harvester_tv_turns.values():
            max_turn = max(max_turn, len(tv_ids))
        return max_turn
