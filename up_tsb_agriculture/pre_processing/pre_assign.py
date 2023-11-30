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

import math
from typing import List, Dict, Optional
from util_arolib.types import Field, MachineType, Machine
from util_arolib.geometry import calc_dist, calc_area
from silo_planning.types import SiloExtended
from route_planning.types import FieldState, MachineState
from management.pre_assignments import FieldPreAssignment, FieldPreAssignments, TVPreAssignments
from up_interface.problem_encoder.names_helper import *


def get_pre_assigned_fields(pre_assign_fields_count: int, pre_assign_field_turns_count: int,
                            fields: List[Field], machines: List[Machine],
                            field_states: Dict[int, FieldState], machine_states: Dict[int, MachineState]
                            ) -> Optional[FieldPreAssignments]:

    """ Pre-assign fields to harvesters

    Parameters
    ----------
    pre_assign_fields_count : int
        Maximum amount of fields to pre-assign
    pre_assign_field_turns_count : int
        Maximum amount of field turns to pre-assign to a harvester
    fields : List[Field]
        List of fields
    machines : List[Machine]
        List of machines
    field_states : Dict[int, FieldState]
        Current states of the fields: {field_id, field_state}
    machine_states : Dict[int, MachineState]
        Current states of the machines: {machine_id, machine_state}

    Returns
    ----------
    pre_assignments : FieldPreAssignments
        Pre-assignments of fields to harvesters
    """

    if pre_assign_fields_count <= 0:
        return None

    harvesters = []
    for m in machines:
        if m.machinetype == MachineType.HARVESTER:
            harvesters.append(m)

    fields_to_work = []

    for f in fields:
        state = field_states.get(f.id)
        if state is None or state.harvested_percentage < 99.9:
            fields_to_work.append(f)

    if len(harvesters) > len(fields_to_work):
        return None

    # if len(harvesters) < 2 and pre_assign_field_turns_count <= 0:
    #     return None

    ret = FieldPreAssignments()
    harv_turns = dict()
    count = 0
    count_turns = 0
    for h in harvesters:
        harv_turns[h.id] = 0
        if count_turns < pre_assign_field_turns_count:
            state = machine_states.get(h.id)
            if state is None:
                continue
            try:
                field_id = get_field_id_from_location_name(state.location_name)
                if field_id is None or field_id not in fields_to_work:
                    continue
                harv_turns[h.id] = 1
                ass = FieldPreAssignment()
                ass.harv_id = h.id
                ass.turn = 1
                ret.field_pre_assignments[field_id] = ass
                count += 1
                count_turns += 1
                if count >= pre_assign_fields_count:
                    break
            except:
                pass

    fields_to_work.sort(key=lambda x: calc_area(x.outer_boundary), reverse=True)

    ind_harv = 0
    for f in fields_to_work:
        if count >= pre_assign_fields_count:
            break
        if f.id in ret.field_pre_assignments.keys():
            continue
        turn = 0
        if count_turns < pre_assign_field_turns_count:
            turn = harv_turns.get(harvesters[ind_harv].id) + 1
            harv_turns[harvesters[ind_harv].id] = turn
            count_turns += 1

        ass = FieldPreAssignment()
        ass.harv_id = harvesters[ind_harv].id
        ass.turn = turn
        ret.field_pre_assignments[f.id] = ass
        count += 1
        ind_harv = ind_harv + 1 if ind_harv + 1 < len(harvesters) else 0
    return ret


def get_pre_assigned_tvs(pre_assign_harvs_count: int, tvs_per_harvester: int, assign_turns_count: int,
                         machines: List[Machine], machine_states: Dict[int, MachineState],
                         silos: List[SiloExtended],
                         cyclic_turns: bool,
                         base_pre_assignments: TVPreAssignments = None,
                         ) -> TVPreAssignments:

    """ Pre-assign transport vehicles to harvesters

    Parameters
    ----------
    pre_assign_harvs_count : int
        Maximum amount of harvesters to pre-assign
    tvs_per_harvester : int
        Maximum amount of transport vehicles to pre-assign to a harvester
    assign_turns_count : int
        Maximum amount of transport-vehicle turns to pre-assign to a harvester
    machines : List[Machine]
        List of machines
    machine_states : Dict[int, MachineState]
        Current states of the machines: {machine_id, machine_state}
    silos : List[SiloExtended]
        List of silos
    cyclic_turns : bool
        Assign the transport-vehicle turns as cyclic (True) or not (False)
    base_pre_assignments : TVPreAssignments
        Pre-assignments of transport vehicles to harvesters to take as base

    Returns
    ----------
    pre_assignments : TVPreAssignments
        Pre-assignments of transport vehicles to harvesters
    """

    if pre_assign_harvs_count <= 0 or tvs_per_harvester <= 0:
        return base_pre_assignments

    def __is_harv_tv_pre_assignment_valid(harv_id, tv_id):
        if base_pre_assignments is None:
            return True
        hid = base_pre_assignments.tv_assigned_harvesters_without_turns.get(tv_id)
        if hid is None:
            return True
        return harv_id == hid

    harvesters_states = dict()
    tvs_states = dict()
    tvs = list()
    max_tv_speed = 0
    overloading_harvesters = dict()
    overloading_tvs = dict()
    tvs_with_turn = set()

    if base_pre_assignments is not None:
        for harv_id, tv_ids in base_pre_assignments.harvester_tv_turns.items():
            for tv_id in tv_ids:
                assert tv_id  not in tvs_with_turn, f'TV with id {tv_id} was pre-assigned to more than one harvester'
                tvs_with_turn.add(tv_id)

    for m in machines:
        if m.machinetype is MachineType.HARVESTER:
            machine_state = machine_states.get(m.id)
            harvesters_states[m] = machine_state
            overloading_machines = overloading_harvesters
        elif m.machinetype is MachineType.OLV:
            machine_state = machine_states.get(m.id)
            tvs_states[m] = machine_state
            tvs.append(m.id)
            max_tv_speed = max(max_tv_speed,m.max_speed_full, m.max_speed_empty)
            overloading_machines = overloading_tvs
        else:
            continue
        if machine_state is not None and machine_state.location_name is not None:
            field_id = get_field_id_from_location_name(machine_state.location_name)
            if field_id is not None \
                    and machine_state.overloading_machine_id is not None:
                overloading_machines[m.id] = (field_id, machine_state.overloading_machine_id)

    if len(harvesters_states) == 0 or len(tvs_states) == 0:
        return base_pre_assignments

    durations_to_harvs = dict()
    min_durations_to_harvs: List[Tuple[float, int]] = list()
    durations_to_silos: List[Tuple[float, int]] = list()
    tvs_with_dist = set()
    tvs_full = set()

    for tv, tv_state in tvs_states.items():
        if tv_state is not None \
                and tv_state.bunker_mass > 1e-9 \
                and tv_state.bunker_mass > 0.9 * tv.bunker_mass:
            tvs_full.add(tv.id)
            tv_speed = max(tv.max_speed_full, tv.max_speed_empty)
            if tv_state.position is None:
                durations_to_silos.append((0.1 / tv_speed, tv.id))
                continue
            min_dist = math.inf
            for silo in silos:
                for sap in silo.access_points:
                    min_dist = min(min_dist, calc_dist(tv_state.position, sap))
            durations_to_silos.append((min_dist / tv_speed, tv.id))
    durations_to_silos.sort(key=lambda x: x[0])

    overloading_harvs_to_remove = list()
    for harv_id, (field_id, tv_id) in overloading_harvesters.items():
        if tv_id in tvs_full or not __is_harv_tv_pre_assignment_valid(harv_id, tv_id):
            overloading_harvs_to_remove.append(harv_id)
            continue
        field_harv = overloading_tvs.get(tv_id)
        assert field_harv is not None, f'Overloading machine missmatch harvester ({harv_id}) -> tv({tv_id}): tv not overloading'
        assert field_harv[0] == field_id, f'Field of overloading machine missmatch harvester ({harv_id} - {field_id}) -> tv({tv_id} - {field_harv[0]}): field missmatch'
        assert field_harv[1] == harv_id, f'Overloading machine missmatch harvester ({harv_id}) -> tv({tv_id} - {field_harv[1]}): harvester missmatch'
    for harv_name in overloading_harvs_to_remove:
        overloading_harvesters.pop(harv_name)
    for tv_id, (field_id, harv_id) in overloading_tvs.items():
        if tv_id in tvs_full:
            continue
        field_tv = overloading_harvesters.get(harv_id)
        assert field_tv is not None, f'Overloading machine missmatch tv({tv_id}) -> harvester ({harv_id}): harvester not overloading'
        assert field_tv[0] == field_id, f'Field of overloading machine missmatch tv({tv_id} - {field_id}) -> harvester ({harv_id} - {field_tv[0]}): field missmatch'
        assert field_tv[1] == tv_id, f'Overloading machine missmatch tv({tv_id}) -> harvester ({harv_id} - {field_tv[1]}): tv missmatch'

    for harv, harv_state in harvesters_states.items():
        durations_to_harv = []
        durations_to_harvs[harv.id] = durations_to_harv
        if harv_state is None:
            min_durations_to_harvs.append((math.inf, harv.id))
            continue

        harv_in_field_id = None
        if harv_state.location_name is not None:
            harv_in_field_id = get_field_id_from_location_name(harv_state.location_name)

        for tv, tv_state in tvs_states.items():
            if tv.id in tvs_full or tv_state is None:
                continue

            tv_in_field_id = None
            if tv_state.location_name is not None:
                tv_in_field_id = get_field_id_from_location_name(tv_state.location_name)

            tv_speed = max(tv.max_speed_full, tv.max_speed_empty)
            if tv_state.position is not None \
                and harv_state.position is not None:
                dist = calc_dist(tv_state.position, harv_state.position)
                if harv_in_field_id is None or tv_in_field_id is None or harv_in_field_id != tv_in_field_id:
                    dist = max(dist, 100)
                durations_to_harv.append( (dist / tv_speed, tv.id) )
                tvs_with_dist.add(tv.id)
                continue

            if tv_state.location_name is not None \
                    and tv_state.location_name == harv_state.location_name \
                    and harv_state.location_name != '' :
                durations_to_harv.append( (0, tv.id) )
                tvs_with_dist.add(tv.id)
                continue

        if len(durations_to_harv) > 0:
            durations_to_harv.sort(key=lambda x: x[0])
            min_durations_to_harvs.append((durations_to_harv[0][0], harv.id))
        else:
            min_durations_to_harvs.append((math.inf, harv.id))

    min_durations_to_harvs.sort(key=lambda x: x[0])
    durations_to_silos.sort(key=lambda x: x[0])
    sorted_harvesters: List[int] = list([x[1] for x in min_durations_to_harvs])
    sorted_tvs_full: List[int] = list([x[1] for x in durations_to_silos])

    tvs_without_dist = list()
    for tv_id in tvs:
        if tv_id not in tvs_with_dist and tv_id not in tvs_full:
            tvs_without_dist.append(tv_id)

    count = 0
    count_turns = 0
    ind_harv = 0
    added_tvs = set()
    tv_assignments = TVPreAssignments()
    tv_assignments.cyclic_turns = None if assign_turns_count < 1 else cyclic_turns
    if base_pre_assignments is not None:
        tv_assignments.harvester_tv_turns = base_pre_assignments.harvester_tv_turns.copy()
    harvesters_no_turns = dict()
    assigned_tvs_per_harv = 0

    for harv_id, turns in tv_assignments.harvester_tv_turns.items():
        for tv_id in turns:
            added_tvs.add(tv_id)

    while count < pre_assign_harvs_count and len(sorted_harvesters) > 0:
        if ind_harv >= len(sorted_harvesters):
            assigned_tvs_per_harv += 1
            ind_harv = 0
        harv_id = sorted_harvesters[ind_harv]

        turns = tv_assignments.harvester_tv_turns.get(harv_id)
        if turns is not None and len(turns) > assigned_tvs_per_harv:
            ind_harv += 1
            continue

        closest_tv = None

        if harv_id in overloading_harvesters.keys():
            (_, tv_id) = overloading_harvesters.pop(harv_id)
            closest_tv = tv_id

        if closest_tv is None:
            harv_dists = durations_to_harvs.get(harv_id)
            if harv_dists is not None:
                while len(harv_dists) > 0:
                    d_tv = harv_dists.pop(0)
                    if d_tv[1] in added_tvs or not __is_harv_tv_pre_assignment_valid(harv_id, d_tv[1]):
                        continue
                    closest_tv = d_tv[1]
                    break

        if closest_tv is None:
            for i, tv_id in enumerate(sorted_tvs_full):
                if __is_harv_tv_pre_assignment_valid(harv_id, tv_id):
                    closest_tv = sorted_tvs_full.pop(i)
                    break

        if closest_tv is None:
            for i, tv_id in enumerate(tvs_without_dist):
                if __is_harv_tv_pre_assignment_valid(harv_id, tv_id):
                    closest_tv = tvs_without_dist.pop(i)
                    break

        if closest_tv is None:
            max_duration = 0
            for harv, harv_dists in durations_to_harvs.items():
                while len(harv_dists) > 0:
                    d_tv = harv_dists[-1]
                    if not __is_harv_tv_pre_assignment_valid(harv_id, d_tv[1]):
                        continue
                    if d_tv[1] in added_tvs:
                        harv_dists.pop()
                        continue
                    if d_tv[0] > max_duration:
                        max_duration = d_tv[0]
                        closest_tv = d_tv[1]
                    break

        if closest_tv is None:
            break

        if closest_tv in added_tvs:
            continue

        added_tvs.add(closest_tv)
        turns =  tv_assignments.harvester_tv_turns.get(harv_id)
        turns_dict = tv_assignments.harvester_tv_turns
        if turns is None and count_turns >= assign_turns_count:
            turns_dict = harvesters_no_turns
            turns = harvesters_no_turns.get(harv_id)
        if turns is None:
            turns = list()
            turns_dict[harv_id] = turns
        turns.append(closest_tv)
        if len(turns) >= tvs_per_harvester:
            sorted_harvesters.pop(ind_harv)

        ind_harv += 1
        count_turns += 1
        if base_pre_assignments is None or closest_tv not in base_pre_assignments.tv_assigned_harvesters_without_turns.keys():
            count += 1

    if base_pre_assignments is not None:
        for tv_id, harv_id in base_pre_assignments.tv_assigned_harvesters_without_turns.items():
            assert harv_id not in base_pre_assignments.harvester_tv_turns.keys(), \
                f'Harvester with id {harv_id} was assigned with and without turns'
            if tv_id not in added_tvs:
                tv_assignments.tv_assigned_harvesters_without_turns[tv_id] = harv_id

    for harv_id, tv_ids in harvesters_no_turns.items():
        for tv_id in tv_ids:
            tv_assignments.tv_assigned_harvesters_without_turns[tv_id] = harv_id

    return tv_assignments