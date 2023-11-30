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

import warnings

from unified_planning.shortcuts import *
from unified_planning.plans.plan import ActionInstance
from unified_planning.plans.sequential_plan import SequentialPlan

from up_interface.problem_encoder.problem_encoder import ProblemEncoder
from pre_processing.pre_assign import *
from up_interface.problem_encoder.names_helper import *
from util_arolib.types import *
import up_interface.types as upt
from up_interface.fluents import FluentNames as fn
from up_interface.actions.sequential.drive_harv_to_field_and_init import ActionDriveHarvToFieldAndInit
from up_interface.actions.sequential.drive_tv_to_field_and_overload import ActionDriveTvToFieldAndOverload
from up_interface.actions.sequential.drive_to_silo import ActionDriveToSilo
from up_interface.actions.sequential.drive_tv_to_field_exit import ActionDriveTvToFieldExit
from up_interface.actions.sequential.drive_harv_to_field_exit import ActionDriveHarvToFieldExit


class _PlanData:

    """ Class holding the plan data/information """

    def __init__(self):
        self.fields: List[Field] = list()
        """ List of fields """

        self.harvesters: List[Machine] = list()
        """ List of harvesters """

        self.tvs: List[Machine] = list()
        """ List of transport vehicles """

        self.silos: List[SiloExtended] = list()
        """ List of silos """

        self.harv_locations: Dict[int, Tuple[str, Any]] = dict()
        """ Harvesters' locations: {machine_id, (loc_name, loc_type)}"""

        self.tv_locations: Dict[int, Tuple[str, Any]] = dict()
        """ Transport vehicles' locations: {machine_id, (loc_name, loc_type)}"""

        self.tv_bunker_masses: Dict[int, Tuple[float, float, bool]] = dict()
        """ Information of the transport vehicles' bunker states and loading: {machine_id, (bunker_mass[kg], filling%[0-100], can_load)}"""

        self.field_masses: Dict[int, float] = dict()
        """ Yield-mass [kg] in the fields: {field_id, mass}"""

        self.silo_capacities: Dict[int, float] = dict()
        """ Yield-mass capacities [kg] in the silos: {silo_id, capacity}"""

        self.field_pre_assignments = FieldPreAssignments()
        """ Field pre-assignments"""

        self.tv_pre_assignments = TVPreAssignments()
        """ Transport-vehicle pre-assignments"""

        self.location_distances: Dict[str, Dict[str, float]] = dict()
        """ Distances [m] between locations: {loc_from_name: {loc_to_name: distance}}"""

        self.field_access_object_names: Dict[str, List[str]] = dict()
        """ Names of the field access (problem) object names: {field_name: [field_access_names]} """

        self.silo_access_object_names: Dict[str, List[str]] = dict()
        """ Names of the silo access (problem) object names: {silo_name: [silo_access_names]} """

        self.simulator: SequentialSimulator = None
        """ Sequential plan simulator """

        self.state: Optional[State] = None
        """ Plan state """


class SequentialPlanGenerator:

    """ Generator of sequential plans for the agriculture use-case

    The generated plans might be trivial, but can be used as benchmark
    """

    _ActionInstance = Tuple[str, Dict[str, Any]]
    """ Internal action instance: (action_name, {action_parameter: parameter_value}) """

    def __init__(self, problem_encoder: ProblemEncoder):

        """ Class initialization

        Parameters
        ----------
        problem_encoder : ProblemEncoder
            Problem encoder
        """

        self.__problem_encoder = problem_encoder
        """ Problem encoder """

        self.__plan: Optional[List[ActionInstance]] = None
        """ Plan as a list of UP action instances """

        self.__final_state: Optional[State] = None
        """ Plan final state """

    def plan(self) -> Union[List[ActionInstance], None]:

        """ Generate a sequential plan

        Returns
        ----------
        plan : List[ActionInstance], None
            Plan as a list of UP action instances (None if it failed to generate a plan)
        """

        plan_data = _PlanData()

        plan_data.simulator = SequentialSimulator(self.__problem_encoder.problem)
        plan_data.state = plan_data.simulator.get_initial_state()

        self.__get_unfinished_fields(plan_data)
        self.__get_machines_from_problem(plan_data)
        self.__get_silos_from_problem(plan_data)
        self.__get_field_accesses(plan_data)
        self.__get_silo_accesses(plan_data)
        self.__get_machines_initial_locations(plan_data)
        self.__get_tv_initial_bunker_masses(plan_data)
        self.__get_field_initial_masses(plan_data)
        self.__get_silo_initial_capacities(plan_data)
        self.__get_field_pre_assignments(plan_data)
        self.__get_tv_pre_assignments(plan_data)

        self.__plan = self.__get_plan(plan_data)
        if len(self.__plan) == 0:
            return None

        self.__final_state = plan_data.state
        return self.__plan

    def get_plan(self) -> Optional[SequentialPlan]:

        """ Get the generated sequential plan (if it has not been generated, it is generated)

        Returns
        ----------
        plan : SequentialPlan, None
            UP Plan (None if it failed to generate a plan)
        """

        if self.__plan is None:
            self.plan()
        if len(self.__plan) == 0:
            return None
        return SequentialPlan(actions=self.__plan)

    @property
    def final_state(self) -> Union[State, None]:

        """ Get the final state of the generated plan (if existent)

        Returns
        ----------
        plan : State
            final state of the generated plan (None if non-existent)
        """

        return self.__final_state

    def get_max_machine_timestamp(self, include_harvs = True, include_tvs = True) -> Union[float, None]:

        """ Get the maximum machine timestamp of the generated plan (if existent)

        Parameters
        ----------
        include_harvs : bool
            Include harvesters?
        include_tvs : bool
            Include transport vehicles?

        Returns
        ----------
        max_machine_timestamp : float, None
            Maximum machine timestamp [s] of the generated plan (None if no plan exists)
        """

        if self.__final_state is None:
            return None

        problem = self.__problem_encoder.problem
        max_timestamp = 0.0

        if include_harvs:
            machine_objects = problem.objects(upt.Harvester)
            for machine_obj in machine_objects:
                if machine_obj.name == self.__problem_encoder.problem_objects.no_harvester.name:
                    continue
                machine_obj = ObjectExp(machine_obj)
                harv_timestamp = FluentExp(problem.fluent(fn.harv_timestamp.value), machine_obj)
                max_timestamp = max(max_timestamp, float(self.__final_state.get_value(harv_timestamp).constant_value()))

        if include_tvs:
            machine_objects = problem.objects(upt.TransportVehicle)
            for machine_obj in machine_objects:
                machine_obj = ObjectExp(machine_obj)
                tv_timestamp = FluentExp(problem.fluent(fn.tv_timestamp.value), machine_obj)
                max_timestamp = max(max_timestamp, float(self.__final_state.get_value(tv_timestamp).constant_value()))

        return max_timestamp

    def get_harvesters_waiting_time(self) -> Union[float, None]:

        """ Get the total harvesters' waiting time for the generated plan (if existent)

        Returns
        ----------
        waiting_time : float, None
            Total harvesters' waiting time [s] (None if no plan exists)
        """

        if self.__final_state is None:
            return None
        problem = self.__problem_encoder.problem
        machine_objects = problem.objects(upt.Harvester)
        waiting_time_total = 0.0
        for machine_obj in machine_objects:
            if machine_obj.name == self.__problem_encoder.problem_objects.no_harvester.name:
                continue
            machine_obj = ObjectExp(machine_obj)
            harv_waiting_time = FluentExp(problem.fluent(fn.harv_waiting_time.value), machine_obj)
            waiting_time_total += float(self.__final_state.get_value(harv_waiting_time).constant_value())
        return waiting_time_total

    def get_tvs_waiting_time(self) -> Union[float, None]:

        """ Get the total transport vehicles' waiting time for the generated plan (if existent)

        Returns
        ----------
        waiting_time : float, None
            Total transport vehicles' waiting time [s] (None if no plan exists)
        """

        if self.__final_state is None:
            return None
        problem = self.__problem_encoder.problem
        machine_objects = problem.objects(upt.TransportVehicle)
        waiting_time_total = 0.0
        for machine_obj in machine_objects:
            machine_obj = ObjectExp(machine_obj)
            tv_waiting_time = FluentExp(problem.fluent(fn.tv_waiting_time.value), machine_obj)
            waiting_time_total += float(self.__final_state.get_value(tv_waiting_time).constant_value())
        return waiting_time_total

    def __get_unfinished_fields(self, plan_data: _PlanData):

        """ Update the fields in plan_data with the fields that are not completely harvested

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        plan_data.fields.clear()
        problem = self.__problem_encoder.problem
        for field in self.__problem_encoder.data_manager.fields.values():
            name = get_field_location_name(field.id)
            try:
                field_obj = problem.object(name)
            except:
                continue
            field_harvested = problem.fluent(fn.field_harvested.value)
            if problem.initial_value(field_harvested(field_obj)).bool_constant_value():
                continue
            plan_data.fields.append(field)

    def __get_machines_from_problem(self, plan_data: _PlanData):

        """ Update the machines in plan_data from the corresponding objects and static fluents in the problem

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        plan_data.harvesters.clear()
        plan_data.tvs.clear()
        for machine in self.__problem_encoder.data_manager.machines.values():
            if machine.machinetype is MachineType.HARVESTER:
                machine_list = plan_data.harvesters
                machine_name = get_harvester_name(machine.id)
                obj_type = upt.Harvester
            elif machine.machinetype is MachineType.OLV:
                machine_list = plan_data.tvs
                machine_name = get_tv_name(machine.id)
                obj_type = upt.TransportVehicle
            else:
                continue

            try:
                obj = self.__problem_encoder.problem.object(machine_name)
                if obj.type is obj_type:
                    machine_list.append(machine)
            except:
                continue

    def __get_silos_from_problem(self, plan_data: _PlanData):

        """ Update the silos in plan_data from the corresponding objects and static fluents in the problem

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        plan_data.silos.clear()
        silo_objs = self.__problem_encoder.problem.objects(upt.Silo)
        for silo_obj in silo_objs:
            silo_id = get_silo_id_from_location_name(silo_obj.name)
            if silo_id is None:
                continue
            silo = self.__problem_encoder.data_manager.get_silo(silo_id)
            if silo is not None:
                plan_data.silos.append(silo)

    def __get_machines_initial_locations(self, plan_data: _PlanData):

        """ Update the machine locations in plan_data from the problem's initial state

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        plan_data.harv_locations.clear()
        plan_data.tv_locations.clear()
        problem = self.__problem_encoder.problem
        for machine_type in [MachineType.HARVESTER, MachineType.OLV]:
            if machine_type is MachineType.HARVESTER:
                machines = plan_data.harvesters
                locations = plan_data.harv_locations
                get_machine_name = get_harvester_name
                machine_at_init_loc = problem.fluent(fn.harv_at_init_loc.value)
                machine_at_field = problem.fluent(fn.harv_at_field.value)
                machine_at_field_access = problem.fluent(fn.harv_at_field_access.value)
                machines_at_silo_access = None
            else:
                machines = plan_data.tvs
                locations = plan_data.tv_locations
                get_machine_name = get_tv_name
                machine_at_init_loc = problem.fluent(fn.tv_at_init_loc.value)
                machine_at_field = problem.fluent(fn.tv_at_field.value)
                machine_at_field_access = problem.fluent(fn.tv_at_field_access.value)
                machines_at_silo_access = problem.fluent(fn.tv_at_silo_access.value)

            for machine in machines:
                name = get_machine_name(machine.id)
                machine_obj = problem.object(name)

                _machine_at_loc = problem.initial_value( machine_at_init_loc(machine_obj) ).constant_value()
                if _machine_at_loc.name != self.__problem_encoder.problem_objects.no_init_loc.name:
                    locations[machine.id] = (_machine_at_loc.name, upt.MachineInitLoc)
                    continue

                _machine_at_loc = problem.initial_value( machine_at_field(machine_obj) ).constant_value()
                if _machine_at_loc.name != self.__problem_encoder.problem_objects.no_field.name:
                    locations[machine.id] = (_machine_at_loc.name, upt.Field)
                    continue

                _machine_at_loc = problem.initial_value( machine_at_field_access(machine_obj) ).constant_value()
                if _machine_at_loc.name != self.__problem_encoder.problem_objects.no_field.name:
                    locations[machine.id] = (_machine_at_loc.name, upt.FieldAccess)
                    continue

                if machines_at_silo_access is not None:
                    _machine_at_loc = problem.initial_value( machines_at_silo_access(machine_obj) ).constant_value()
                    if _machine_at_loc.name != self.__problem_encoder.problem_objects.no_silo_access.name:
                        locations[machine.id] = (_machine_at_loc.name, upt.SiloAccess)
                        continue

                raise ValueError('Invalid machine initial location')

    def __get_tv_initial_bunker_masses(self, plan_data: _PlanData):

        """ Update the transport vehicles' bunker/loading information in plan_data from the problem's initial state

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        plan_data.tv_bunker_masses.clear()
        problem = self.__problem_encoder.problem

        tv_can_load = problem.fluent(fn.tv_can_load.value)
        tv_bunker_mass = problem.fluent(fn.tv_bunker_mass.value)
        tv_total_capacity_mass = problem.fluent(fn.tv_total_capacity_mass.value)

        for tv in plan_data.tvs:
            name = get_tv_name(tv.id)
            tv_obj = problem.object(name)

            _tv_can_load = problem.initial_value( tv_can_load(tv_obj) ).bool_constant_value()
            _tv_bunker_mass = float( problem.initial_value( tv_bunker_mass(tv_obj) ).constant_value() )
            _tv_total_capacity_mass = float( problem.initial_value( tv_total_capacity_mass(tv_obj) ).constant_value() )

            plan_data.tv_bunker_masses[tv.id] = (_tv_bunker_mass,
                                                 100 * _tv_bunker_mass / _tv_total_capacity_mass,
                                                 _tv_can_load)

    def __get_field_initial_masses(self, plan_data: _PlanData):

        """ Update the fields yield-masses in plan_data from the problem's initial state

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        plan_data.field_masses.clear()
        problem = self.__problem_encoder.problem

        field_yield_mass_unharvested = problem.fluent(fn.field_yield_mass_unharvested.value)

        for field in plan_data.fields:
            name = get_field_location_name(field.id)
            field_obj = problem.object(name)
            plan_data.field_masses[field.id] = float( problem.initial_value( field_yield_mass_unharvested(field_obj) ).constant_value() )

    def __get_silo_initial_capacities(self, plan_data: _PlanData):

        """ Update the silo capacities in plan_data from the problem's initial state

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        plan_data.silo_capacities.clear()
        problem = self.__problem_encoder.problem

        silo_available_capacity_mass = problem.fluent(fn.silo_available_capacity_mass.value)

        for silo in plan_data.silos:
            name = get_silo_location_name(silo.id)
            silo_obj = problem.object(name)
            plan_data.silo_capacities[silo.id] = float( problem.initial_value( silo_available_capacity_mass(silo_obj) ).constant_value() )

    def __get_field_pre_assignments_from_problem(self, fields: List[Field]) -> FieldPreAssignments:

        """ Get the field pre-assignments set in the problem

        Parameters
        ----------
        fields : List[Field]
            List of fields

        Returns
        ----------
        pre_assignments : FieldPreAssignments
            Field pre-assignments set in the problem
        """

        pre_assignments = FieldPreAssignments()
        problem = self.__problem_encoder.problem
        for field in fields:
            name = get_field_location_name(field.id)
            field_obj = problem.object(name)

            field_pre_assigned_harvester = problem.fluent(fn.field_pre_assigned_harvester.value)
            _field_pre_assigned_harvester = problem.initial_value(field_pre_assigned_harvester(field_obj)).constant_value()

            if _field_pre_assigned_harvester.name == self.__problem_encoder.problem_objects.no_harvester.name:
                continue

            pre_assignment = FieldPreAssignment()
            pre_assignment.harv_id = get_harvester_id_from_name(_field_pre_assigned_harvester.name)

            field_pre_assigned_turn = problem.fluent(fn.field_pre_assigned_turn.value)
            _field_pre_assigned_turn = problem.initial_value(field_pre_assigned_turn(field_obj)).int_constant_value()
            if _field_pre_assigned_turn > 0:
                pre_assignment.turn = _field_pre_assigned_turn
            pre_assignments.field_pre_assignments[field.id] = pre_assignment

        return pre_assignments

    def __get_field_pre_assignments(self, plan_data: _PlanData):

        """ Update the field pre-assignments in plan_data, taking into account the pre-assignments set in the problem,
        so that all fields are pre-assigned to a harvester (incl. turns)

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        fields = plan_data.fields

        pre_assignments_original = self.__get_field_pre_assignments_from_problem(fields)

        fields_no_assigned_harv: List[Field] = list()
        harv_turns = pre_assignments_original.get_sorted_fields_for_harvesters()

        pre_assigned_harvs_not_turns = dict()

        max_harv_turns = 0
        for harv_id, turns in harv_turns.items():
            max_harv_turns = max(max_harv_turns, len(turns))

        for field in fields:
            pre_assignment = pre_assignments_original.field_pre_assignments.get(field.id)
            if pre_assignment is None or pre_assignment.harv_id is None:
                fields_no_assigned_harv.append(field)
                continue
            if pre_assignment.harv_id not in harv_turns.keys():
                if pre_assignment.harv_id in pre_assigned_harvs_not_turns.keys():
                    pre_assigned_harvs_not_turns[pre_assignment.harv_id].append(field.id)
                else:
                    pre_assigned_harvs_not_turns[pre_assignment.harv_id] = [field.id]
            elif field.id not in harv_turns[pre_assignment.harv_id]:
                harv_turns[pre_assignment.harv_id].append(field.id)

        if len(fields_no_assigned_harv) == len(fields):
            plan_data.field_pre_assignments = get_pre_assigned_fields(len(fields), len(fields),
                                                                      fields, plan_data.harvesters,
                                                                      self.__problem_encoder.field_initial_states,
                                                                      self.__problem_encoder.machine_initial_states)
            return

        for harv_id, field_ids in pre_assigned_harvs_not_turns.items():
            harv_turns[harv_id] = field_ids

        harvs_no_pre_assignment = list()
        for harv in plan_data.harvesters:
            if harv.id not in harv_turns.keys() and harv.id not in pre_assigned_harvs_not_turns.keys():
                harvs_no_pre_assignment.append(harv)

        harvs_no_pre_assignment.sort(key=lambda x: x.def_working_speed, reverse=False)
        while len(harvs_no_pre_assignment) > 0 and len( harv_turns.keys() ) < len(plan_data.tvs):
            harv = harvs_no_pre_assignment.pop()
            harv_turns[harv.id] = list()
        for harv in harvs_no_pre_assignment:
            plan_data.harvesters.remove(harv)

        for harv_id, turns in harv_turns.items():
            if len(fields_no_assigned_harv) == 0:
                break
            while len(turns) < max_harv_turns and len(fields_no_assigned_harv) > 0:
                turns.append( fields_no_assigned_harv.pop().id )

        while len(fields_no_assigned_harv) > 0:
            for harv_id, turns in harv_turns.items():
                if len(fields_no_assigned_harv) == 0:
                    break
                turns.append( fields_no_assigned_harv.pop().id )

        plan_data.field_pre_assignments = FieldPreAssignments()
        plan_data.field_pre_assignments.from_harvesters_assigned_sorted_fields(harv_turns)

    def __get_tv_pre_assignments(self, plan_data: _PlanData):

        """ Update the transport-vehicle pre-assignments in plan_data, taking into account the pre-assignments set in the problem,
        so that all transport-vehicles are pre-assigned to a harvester (incl. cyclic turns)

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        problem = self.__problem_encoder.problem
        base_tv_pre_assignments: Optional[TVPreAssignments] = None
        harv_tv_turns: Dict[int, List[Tuple[int, int]]] = dict()  # {harv_id, [ (tv_id, tv_turn) ]}
        for tv in plan_data.tvs:
            name = get_tv_name(tv.id)
            tv_obj = problem.object(name)

            tv_pre_assigned_harvester = problem.fluent(fn.tv_pre_assigned_harvester.value)
            _tv_pre_assigned_harvester = problem.initial_value(tv_pre_assigned_harvester(tv_obj)).constant_value()
            if _tv_pre_assigned_harvester.name == self.__problem_encoder.problem_objects.no_harvester.name:
                continue

            _tv_pre_assigned_harvester_id = get_harvester_id_from_name(_tv_pre_assigned_harvester.name)

            if base_tv_pre_assignments is None:
                base_tv_pre_assignments = TVPreAssignments()

            tv_pre_assigned_turn = problem.fluent(fn.tv_pre_assigned_turn.value)
            _tv_pre_assigned_turn = int(problem.initial_value(tv_pre_assigned_turn(tv_obj)).constant_value())
            if _tv_pre_assigned_turn <= 0:
                base_tv_pre_assignments.tv_assigned_harvesters_without_turns[tv.id] = _tv_pre_assigned_harvester_id
                continue
            turns = harv_tv_turns.get(_tv_pre_assigned_harvester_id)
            if turns is None:
                turns = []
                harv_tv_turns[_tv_pre_assigned_harvester_id] = turns
            turns.append( (tv.id, _tv_pre_assigned_turn) )
        for harv_id, turns in harv_tv_turns.items():
            turns.sort(key=lambda x: x[1])
            base_tv_pre_assignments.harvester_tv_turns[harv_id] = list(x[0] for x in turns)


        machines = list()
        machines.extend(plan_data.harvesters)
        machines.extend(plan_data.tvs)

        plan_data.tv_pre_assignments = get_pre_assigned_tvs(len(plan_data.tvs),
                                                            len(plan_data.tvs), len(plan_data.tvs),
                                                            machines=machines,
                                                            machine_states=self.__problem_encoder.machine_initial_states,
                                                            silos=plan_data.silos, cyclic_turns=True,
                                                            base_pre_assignments=base_tv_pre_assignments)


    def __get_field_accesses(self, plan_data: _PlanData):

        """ Update the field access points in plan_data from the corresponding objects and static fluents in the problem

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        problem = self.__problem_encoder.problem
        field_access_field = problem.fluent(fn.field_access_field.value)
        fap_objs = problem.objects(upt.FieldAccess)
        for fap_obj in fap_objs:
            _field_access_field = problem.initial_value(field_access_field(fap_obj)).constant_value()
            faps = plan_data.field_access_object_names.get(_field_access_field.name)
            if faps is None:
                faps = list()
                plan_data.field_access_object_names[_field_access_field.name] = faps
            faps.append(fap_obj.name)

    def __get_silo_accesses(self, plan_data: _PlanData):

        """ Update the silo access points in plan_data from the corresponding objects and static fluents in the problem

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        """

        problem = self.__problem_encoder.problem
        silo_access_silo_id = problem.fluent(fn.silo_access_silo_id.value)
        sap_objs = problem.objects(upt.SiloAccess)
        for sap_obj in sap_objs:
            _silo_access_silo_id = problem.initial_value(silo_access_silo_id(sap_obj)).int_constant_value()
            _silo_name = get_silo_location_name(_silo_access_silo_id)
            saps = plan_data.silo_access_object_names.get(_silo_name)
            if saps is None:
                saps = list()
                plan_data.silo_access_object_names[_silo_name] = saps
            saps.append(sap_obj.name)

    def __get_plan(self, plan_data: _PlanData) -> Union[List[ActionInstance], None]:

        """ Generate a sequential plan

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information

        Returns
        ----------
        plan : List[ActionInstance], None
            Plan as a list of UP action instances (None if it failed to generate a plan)
        """

        actions: List[ActionInstance] = list()
        harvesters_sorted_fields = plan_data.field_pre_assignments.get_sorted_fields_for_harvesters()

        def __on_fail():
            #debug!
            print('\nPlanned actions before fail:')
            for action in actions:
                print(f'\t{action}')
            return []

        for harv_id, field_ids in harvesters_sorted_fields.items():
            tv_ids = plan_data.tv_pre_assignments.harvester_tv_turns.get(harv_id)
            tv_ind = 0
            for i, field_id in enumerate(field_ids):
                next_field_id = field_ids[i+1] if i+1 < len(field_ids) else None

                if not self.__send_harv_to_field_and_init(actions, plan_data, harv_id, field_id):
                    warnings.warn('Error adding actions: send_harv_to_field_and_init')
                    return __on_fail()

                while True:

                    next_tv_id = tv_ids[tv_ind]

                    (tv_bunker_mass, tv_filling_pc, can_load) = plan_data.tv_bunker_masses.get(next_tv_id)

                    if tv_filling_pc > 90 or not can_load:
                        if not self.__send_tv_to_silo_and_unload(actions, plan_data, next_tv_id):
                            warnings.warn('Error adding actions: send_tv_to_silo_and_unload')
                            return __on_fail()

                    if not self.__send_tv_to_field_and_overload(actions, plan_data, next_tv_id, field_id, harv_id, next_field_id):
                        warnings.warn('Error adding actions: send_tv_to_field_and_overload')
                        return __on_fail()

                    remaining_mass_field = plan_data.field_masses.get(field_id)

                    (tv_bunker_mass, tv_filling_pc, can_load) = plan_data.tv_bunker_masses.get(next_tv_id)
                    if tv_filling_pc > 50 or next_field_id is None:
                        if not self.__send_tv_to_silo_and_unload(actions, plan_data, next_tv_id):
                            warnings.warn('Error adding actions: send_tv_to_silo_and_unload')
                            return __on_fail()

                        if tv_ind+1 < len(tv_ids):
                            tv_ind += 1
                        else:
                            tv_ind = 0

                    if remaining_mass_field < 0.1:
                        break

        return actions

    def __apply_actions(self, plan_data: _PlanData, actions: Union[ _ActionInstance, List[_ActionInstance] ] ) \
            -> Union[ActionInstance, None]:

        """ Applies a given action to the current plan state. If more than one action is given,
        it will apply the actions in order until one of the succeeds.

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        actions : _ActionInstance, List[_ActionInstance]
            Action to be applied or list of actions that will be applied in order until one succeeds.

        Returns
        ----------
        action_instance : List[ActionInstance], None
            UP ActionInstance of the action that succeeded (None if it failed apply any of the given actions)
        """

        if isinstance(actions, list):
            _actions = actions
        else:
            _actions = [actions]
        problem = self.__problem_encoder.problem
        for (_action_name, _params) in _actions:
            try:
                action: Action = problem.action(_action_name)
                _params_ordered = list()
                for param in action.parameters:
                    _val = _params.get(param.name)
                    if not isinstance(_val, Object):
                        _val = problem.object(_val)
                    # if not isinstance(_val, ObjectExp):
                    #     _val = ObjectExp( problem.object(_val) )
                    _params_ordered.append(_val)
                action_instance = ActionInstance(action, tuple(_params_ordered))

                state_new = plan_data.simulator.apply(plan_data.state, action_instance)
                if state_new is not None:
                    plan_data.state = state_new
                    return action_instance
            except:
                continue
        return None

    def __get_dist_between_locations(self, plan_data: _PlanData, fluent: Fluent, obj_from: Object, obj_to: Object) \
            -> Union[float, None]:

        """ Get the distance between two locations from plan_data. If the distance has not been obtained from the problem static fluents,
        it will be obtained and plan_data will be updated

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        fluent : Fluent
            Distance fluent
        obj_from : Object
            Problem object corresponding to the start location
        obj_to : Object
            Problem object corresponding to the goal location

        Returns
        ----------
        distance : float|None
            Distance between the two locations (None if the connection between the locations does not exist in the problem)
        """

        loc_dist = plan_data.location_distances.get(obj_from.name)
        if loc_dist is None:
            loc_dist = dict()
            plan_data.location_distances[obj_from.name] = loc_dist
        dist = loc_dist.get(obj_to.name)
        if dist is not None:
            return dist
        dist = float( self.__problem_encoder.problem.initial_value( fluent(obj_from, obj_to) ).constant_value() )
        if dist < -1e-9:
            return None
        loc_dist[obj_to.name] = dist
        return dist

    def __get_best_silo_access(self, plan_data: _PlanData,
                               loc_from_name: str, loc_from_type: Type, mass_to_unload: float) \
            -> Tuple[Union[str, None], Union[str, None], Union[float, None]]:

        """ Get the closest (valid) silo access/unloading point that can be reached by a transport vehicle from a given location

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        loc_from_name : str
            Name of the start location
        loc_from_type : Type
            Type of the start location (MachineInitLoc, FieldAccess)
        mass_to_unload : float
            Amount of yield-mass to be unloaded at the silo access/unloading point

        Returns
        ----------
        silo_name : str|None
            Location name of the silo corresponding to the best/closest silo access point (None if it failed to find a valid silo access)
        silo_access_name : str|None
            Location name of the best/closest silo access point (None if it failed to find a valid silo access)
        distance : float|None
            Travel distance between the start location and the silo access (None if it failed to find a valid silo access)
        """

        problem = self.__problem_encoder.problem

        loc_from_obj = problem.object(loc_from_name)
        if loc_from_type is upt.FieldAccess:
            dist_fluent = problem.fluent( fn.transit_distance_fap_sap.value )
        elif loc_from_type is upt.MachineInitLoc:
            dist_fluent = problem.fluent( fn.transit_distance_init_sap.value )
        else:
            return None, None, None

        best_silo = None
        best_sap = None
        min_dist = math.inf
        for silo in plan_data.silos:
            silo_capacity = plan_data.silo_capacities.get(silo.id)
            if silo_capacity < mass_to_unload:
                continue
            silo_name = get_silo_location_name(silo.id)
            saps = plan_data.silo_access_object_names.get(silo_name)
            if saps is None:
                continue
            for sap_name in saps:
                sap_obj = problem.object(sap_name)
                dist = self.__get_dist_between_locations(plan_data, dist_fluent, loc_from_obj, sap_obj )
                if dist is None or dist > min_dist:
                    continue
                best_silo = silo_name
                best_sap = sap_name
                min_dist = dist

        return best_silo, best_sap, min_dist

    def __get_best_field_access(self, plan_data: _PlanData, field_name: str, loc_from_name: str, loc_from_type: Type) \
            -> Tuple[Union[str, None], Union[float, None]]:

        """ Get the closest access point of a given field that can be reached by a machine from a given location

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        field_name : str
            Location name of the field
        loc_from_name : str
            Name of the start location
        loc_from_type : Type
            Type of the start location (MachineInitLoc, FieldAccess, SiloAccess)

        Returns
        ----------
        field_access_name : str|None
            Location name of the best/closest field access point (None if it failed to find one)
        distance : float|None
            Travel distance between the start location and the field access (None if it failed to find one)
        """

        problem = self.__problem_encoder.problem

        loc_from_obj = problem.object(loc_from_name)
        if loc_from_type is upt.SiloAccess:
            dist_fluent = problem.fluent( fn.transit_distance_sap_fap.value )
        elif loc_from_type is upt.FieldAccess:
            dist_fluent = problem.fluent( fn.transit_distance_fap_fap.value )
        elif loc_from_type is upt.MachineInitLoc:
            dist_fluent = problem.fluent( fn.transit_distance_init_fap.value )
        else:
            return None, None

        best_fap = None
        min_dist = math.inf
        faps = plan_data.field_access_object_names.get(field_name)
        if faps is None:
            return None, None

        for fap_name in faps:
            fap_obj = problem.object(fap_name)
            dist = self.__get_dist_between_locations(plan_data, dist_fluent, loc_from_obj, fap_obj )
            if dist is None or dist > min_dist:
                continue
            best_fap = fap_name
            min_dist = dist

        return best_fap, min_dist

    def __get_best_field_exit_to_silo(self, plan_data: _PlanData, field_name: str, tv_bunker_mass: float) \
            -> Tuple[Union[str, None], Union[str, None], Union[str, None], Union[float, None]]:

        """ Get the closest (valid) silo access/unloading point that can be reached by a transport vehicle from inside a given field,
        as well as the corresponding field exit

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        field_name : str
            Location name of the field
        tv_bunker_mass : float
            Amount of yield-mass to be unloaded at the silo access/unloading point

        Returns
        ----------
        field_exit_name : str|None
            Location name of the field access (exit) point used to reach the best/closest silo access point (None if it failed to find a valid silo access)
        silo_name : str|None
            Location name of the silo corresponding to the best/closest silo access point (None if it failed to find a valid silo access)
        silo_access_name : str|None
            Location name of the best/closest silo access point (None if it failed to find a valid silo access)
        distance : float|None
            Travel distance between the start location and the silo access (None if it failed to find a valid silo access)
        """

        silo_name_best = None
        silo_access_name_best = None
        fap_name_best = None
        min_dist = math.inf
        faps = plan_data.field_access_object_names.get(field_name)
        if faps is not None:
            for fap_name in faps:
                (silo_name, silo_access_name, dist) = self.__get_best_silo_access(plan_data, fap_name, upt.FieldAccess,
                                                                                  tv_bunker_mass)
                if silo_name is not None and dist < min_dist:
                    fap_name_best = fap_name
                    silo_name_best = silo_name
                    silo_access_name_best = silo_access_name
                    min_dist = dist

        return fap_name_best, silo_name_best, silo_access_name_best, min_dist

    def __get_best_field_exit_to_field(self, plan_data: _PlanData, field_from_name: str, field_to_name: str) \
            -> Tuple[Union[str, None], Union[str, None], Union[float, None]]:

        """ Get the closest access point of a given field that can be reached by a machine from inside another given field,
        as well as the corresponding field exit

        Parameters
        ----------
        plan_data : _PlanData
            Plan data/information
        field_from_name : str
            Location name of the starting field
        field_to_name : str
            Location name of the target field

        Returns
        ----------
        field_from_exit_name : str|None
            Location name of the field access (exit) point used to reach the best/closest access point in the target field (None if it failed to find one)
        silo_access_name : str|None
            Location name of the best/closest access point in the target field (None if it failed to find one)
        distance : float|None
            Travel distance between the start location and the access point in the target field (None if it failed to find a valid silo access)
        """

        field_access_name_best = None
        fap_name_best = None
        min_dist = math.inf
        faps = plan_data.field_access_object_names.get(field_from_name)
        if faps is not None:
            for fap_name in faps:
                (field_access_name, dist) = self.__get_best_field_access(plan_data, field_to_name, fap_name, upt.FieldAccess)
                if field_access_name is not None and dist < min_dist:
                    fap_name_best = fap_name
                    field_access_name_best = field_access_name
                    min_dist = dist

        return fap_name_best, field_access_name_best, min_dist

    def __send_harv_to_field_and_init(self,
                                      actions: List[ActionInstance],
                                      plan_data: _PlanData,
                                      harv_id: int,
                                      field_id: int) -> bool:

        """ Plan the action(s) needed to send a given harvester to a given field and initialize the harvesting process
         from the current plan state

        Parameters
        ----------
        actions : List[ActionInstance]
            Current list of planned actions to be updated
        plan_data : _PlanData
            Plan data/information
        harv_id : int
            Id of the harvester
        field_id : int
            Id of the target field

        Returns
        ----------
        success : bool
            True on success
        """

        (loc_name, loc_type) = plan_data.harv_locations.get(harv_id)
        harv_name = get_harvester_name(harv_id)
        field_name = get_field_location_name(field_id)

        if loc_type is upt.Field:

            if loc_name != field_name:
                (field_exit_name, field_access_name, dist) = self.__get_best_field_exit_to_field(plan_data, loc_name, field_name)
                if field_exit_name is None:
                    return False
                __Action = ActionDriveHarvToFieldExit
                action = self.__apply_actions( plan_data,
                                               ( __Action.ActionNames.DRIVE_HARV_TO_FIELD_EXIT.value,
                                                 { __Action.ParameterNames.FIELD.value: loc_name,
                                                   __Action.ParameterNames.FIELD_ACCESS.value: field_exit_name,
                                                   __Action.ParameterNames.HARV.value: harv_name } ) )
                if action is None:
                    return False
                actions.append( action )

                __Action = ActionDriveHarvToFieldAndInit
                action = self.__apply_actions( plan_data,
                                               ( __Action.ActionNames.DRIVE_HARV_FROM_FAP_TO_FIELD_AND_INIT.value,
                                                 { __Action.ParameterNames.FIELD.value: field_name,
                                                   __Action.ParameterNames.HARV.value: harv_name,
                                                   __Action.ParameterNames.LOC_FROM.value: loc_name,
                                                   __Action.ParameterNames.FIELD_ACCESS.value: field_access_name} ) )
                if action is None:
                    return False
                actions.append( action )

            else:
                __Action = ActionDriveHarvToFieldAndInit
                action = self.__apply_actions( plan_data,
                                               ( __Action.ActionNames.INIT_HARV_IN_FIELD.value,
                                                 { __Action.ParameterNames.FIELD.value: field_name,
                                                   __Action.ParameterNames.HARV.value: harv_name } ) )
                if action is None:
                    return False
                actions.append( action )

        elif loc_type is upt.FieldAccess or loc_type is upt.MachineInitLoc:
            (field_access_name, _) = self.__get_best_field_access(plan_data, field_name, loc_name, loc_type)
            if field_access_name is None:
                return False
            __Action = ActionDriveHarvToFieldAndInit
            __action_name = __Action.ActionNames.DRIVE_HARV_FROM_FAP_TO_FIELD_AND_INIT.value \
                if loc_type is upt.FieldAccess \
                else ActionDriveHarvToFieldAndInit.ActionNames.DRIVE_HARV_FROM_INIT_LOC_TO_FIELD_AND_INIT.value

            action = self.__apply_actions( plan_data,
                                           ( __action_name,
                                             { __Action.ParameterNames.FIELD.value: field_name,
                                               __Action.ParameterNames.HARV.value: harv_name,
                                               __Action.ParameterNames.LOC_FROM.value: loc_name,
                                               __Action.ParameterNames.FIELD_ACCESS.value: field_access_name } ) )
            if action is None:
                return False
            actions.append(action)
        else:
            return False

        plan_data.harv_locations[harv_id] = (field_name, upt.Field)

        return True

    def __send_tv_to_silo_and_unload(self,
                                     actions: List[ActionInstance],
                                     plan_data: _PlanData,
                                     tv_id: int) -> bool:

        """ Plan the action(s) needed to send a given transport vehicle to a silo and unload from the current plan state

        Parameters
        ----------
        actions : List[ActionInstance]
            Current list of planned actions to be updated
        plan_data : _PlanData
            Plan data/information
        tv_id : int
            Id of the transport vehicle

        Returns
        ----------
        success : bool
            True on success
        """

        (tv_bunker_mass, tv_filling_pc, can_load) = plan_data.tv_bunker_masses.get(tv_id)
        (loc_name, loc_type) = plan_data.tv_locations.get(tv_id)
        tv_name = get_tv_name(tv_id)

        if loc_type is upt.Field:
            (fap_name, silo_name, silo_access_name, dist) = self.__get_best_field_exit_to_silo(plan_data, loc_name, tv_bunker_mass)
            if fap_name is None:
                return False
            __Action = ActionDriveTvToFieldExit
            action = self.__apply_actions( plan_data,
                                           ( __Action.ActionNames.DRIVE_TV_TO_FIELD_EXIT.value,
                                             { __Action.ParameterNames.FIELD.value: loc_name,
                                               __Action.ParameterNames.FIELD_ACCESS.value: fap_name,
                                               __Action.ParameterNames.TV.value: tv_name } ) )
            if action is None:
                return False
            actions.append(action)

            __Action = ActionDriveToSilo
            action = self.__apply_actions( plan_data,
                                           ( __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_SILO_AND_UNLOAD.value,
                                             { __Action.ParameterNames.LOC_FROM.value: fap_name,
                                               __Action.ParameterNames.SILO.value: silo_name,
                                               __Action.ParameterNames.SILO_ACCESS.value: silo_access_name,
                                               __Action.ParameterNames.TV.value: tv_name } ) )
            if action is None:
                return False
            actions.append(action)

        elif loc_type is upt.FieldAccess or loc_type is upt.MachineInitLoc:
            (silo_name, silo_access_name, _) = self.__get_best_silo_access(plan_data, loc_name, loc_type, tv_bunker_mass)
            if silo_name is None:
                return False
            __Action = ActionDriveToSilo
            __action_name = __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_SILO_AND_UNLOAD.value \
                if loc_type is upt.FieldAccess \
                else __Action.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_SILO_AND_UNLOAD.value

            action = self.__apply_actions( plan_data,
                                           ( __action_name,
                                             { __Action.ParameterNames.LOC_FROM.value: loc_name,
                                               __Action.ParameterNames.SILO.value: silo_name,
                                               __Action.ParameterNames.SILO_ACCESS.value: silo_access_name,
                                               __Action.ParameterNames.TV.value: tv_name } ) )
            if action is None:
                return False
            actions.append(action)
        else:
            return False

        silo_id = get_silo_id_from_location_name(silo_name)
        silo_capacity = plan_data.silo_capacities.get(silo_id)
        plan_data.silo_capacities[silo_id] = silo_capacity - tv_bunker_mass

        plan_data.tv_bunker_masses[tv_id] = (0.0, 0.0, True)
        plan_data.tv_locations[tv_id] = (silo_access_name, upt.SiloAccess)

        return True

    def __send_tv_to_field_and_overload(self,
                                        actions: List[ActionInstance],
                                        plan_data: _PlanData,
                                        tv_id: int,
                                        field_id: int,
                                        harv_id: int,
                                        next_field_id: Union[int, None]) -> bool:

        """ Plan the action(s) needed to send a given transport vehicle to a given field and overload from a given harvester
         from the current plan state

        Parameters
        ----------
        actions : List[ActionInstance]
            Current list of planned actions to be updated
        plan_data : _PlanData
            Plan data/information
        tv_id : int
            Id of the transport vehicle
        field_id : int
            Id of the target field
        harv_id : int
            Id of the harvester
        next_field_id : int|None
            Id of the field that will be harvested after this field is finished (None if this is the last field assigned to this harvester)

        Returns
        ----------
        success : bool
            True on success
        """

        (tv_bunker_mass, tv_filling_pc, can_load) = plan_data.tv_bunker_masses.get(tv_id)
        (loc_name, loc_type) = plan_data.tv_locations.get(tv_id)
        tv_name = get_tv_name(tv_id)
        harv_name = get_harvester_name(harv_id)
        field_name = get_field_location_name(field_id)

        tv = self.__problem_encoder.data_manager.get_machine(tv_id)
        tv_capacity = tv.bunker_mass - tv_bunker_mass
        field_mass = plan_data.field_masses.get(field_id)
        mass_to_overload = tv_capacity if field_mass > tv_capacity else field_mass
        tv_bunker_mass_new = tv_bunker_mass + mass_to_overload

        tv_field_exit_name = self.__get_best_field_exit_to_silo(plan_data, field_name, tv_bunker_mass_new)[0]
        if next_field_id is not None:
            next_field_name = get_field_location_name(next_field_id)
            harv_field_exit_name = self.__get_best_field_exit_to_field(plan_data, field_name, next_field_name)[0]
        else:
            harv_field_exit_name = plan_data.field_access_object_names.get(field_name)[0]

        field_mass_new = field_mass - mass_to_overload

        if loc_type is upt.Field:

            if loc_name != field_name:
                (field_exit_name, field_access_name, dist) = self.__get_best_field_exit_to_field(plan_data, loc_name, field_name)
                if field_access_name is None:
                    return False
                __Action = ActionDriveTvToFieldExit
                action = self.__apply_actions( plan_data,
                                               ( __Action.ActionNames.DRIVE_TV_TO_FIELD_EXIT.value,
                                                 { __Action.ParameterNames.FIELD.value: loc_name,
                                                   __Action.ParameterNames.FIELD_ACCESS.value: field_exit_name,
                                                   __Action.ParameterNames.TV.value: tv_name } ) )
                if action is None:
                    return False
                actions.append(action)

                __Action = ActionDriveTvToFieldAndOverload
                possible_actions = list()
                possible_actions_names = [
                    __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS.value,
                    __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_TV_WAITS.value,
                    __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value,
                    __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                ]
                for __action_name in possible_actions_names:
                    possible_actions.append( ( __action_name,
                                               { __Action.ParameterNames.FIELD.value: field_name,
                                                 __Action.ParameterNames.TV.value: tv_name,
                                                 __Action.ParameterNames.HARV.value: harv_name,
                                                 __Action.ParameterNames.LOC_FROM.value: field_exit_name,
                                                 __Action.ParameterNames.FIELD_ACCESS.value: field_access_name,
                                                 __Action.ParameterNames.FIELD_EXIT_TV.value: tv_field_exit_name,
                                                 __Action.ParameterNames.FIELD_EXIT_HARV.value: harv_field_exit_name} ) )

                action = self.__apply_actions(plan_data, possible_actions)
                if action is None:
                    return False
                actions.append(action)
                field_finished = ( action.action.name == __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value
                                   or action.action.name == __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value )

            else:
                __Action = ActionDriveTvToFieldAndOverload
                possible_actions = list()
                possible_actions_names = [
                    __Action.ActionNames.OVERLOAD_HARV_WAITS.value,
                    __Action.ActionNames.OVERLOAD_TV_WAITS.value,
                    __Action.ActionNames.OVERLOAD_HARV_WAITS_FIELD_FINISHED.value,
                    __Action.ActionNames.OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                ]
                for __action_name in possible_actions_names:
                    possible_actions.append( ( __action_name,
                                               { __Action.ParameterNames.FIELD.value: field_name,
                                                 __Action.ParameterNames.TV.value: tv_name,
                                                 __Action.ParameterNames.HARV.value: harv_name,
                                                 __Action.ParameterNames.FIELD_EXIT_TV.value: tv_field_exit_name,
                                                 __Action.ParameterNames.FIELD_EXIT_HARV.value: harv_field_exit_name} ) )

                action = self.__apply_actions(plan_data, possible_actions)
                if action is None:
                    return False
                actions.append(action)
                field_finished = ( action.action.name == __Action.ActionNames.OVERLOAD_HARV_WAITS_FIELD_FINISHED.value
                                   or action.action.name == __Action.ActionNames.OVERLOAD_TV_WAITS_FIELD_FINISHED.value )

        elif loc_type is upt.FieldAccess or loc_type is upt.SiloAccess or loc_type is upt.MachineInitLoc:
            (field_access_name, _) = self.__get_best_field_access(plan_data, field_name, loc_name, loc_type)

            __Action = ActionDriveTvToFieldAndOverload
            possible_actions = list()
            if loc_type is upt.FieldAccess:
                possible_actions_names = [
                    __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS.value,
                    __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_TV_WAITS.value,
                    __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value,
                    __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                ]
            elif loc_type is upt.SiloAccess:
                possible_actions_names = [
                    __Action.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS.value,
                    __Action.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_TV_WAITS.value,
                    __Action.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value,
                    __Action.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                ]
            else:
                possible_actions_names = [
                    __Action.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_HARV_WAITS.value,
                    __Action.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_TV_WAITS.value,
                    __Action.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value,
                    __Action.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                ]
            for __action_name in possible_actions_names:
                possible_actions.append( ( __action_name,
                                           { __Action.ParameterNames.FIELD.value: field_name,
                                             __Action.ParameterNames.TV.value: tv_name,
                                             __Action.ParameterNames.HARV.value: harv_name,
                                             __Action.ParameterNames.LOC_FROM.value: loc_name,
                                             __Action.ParameterNames.FIELD_ACCESS.value: field_access_name,
                                             __Action.ParameterNames.FIELD_EXIT_TV.value: tv_field_exit_name,
                                             __Action.ParameterNames.FIELD_EXIT_HARV.value: harv_field_exit_name} ) )

            action = self.__apply_actions(plan_data, possible_actions)
            if action is None:
                return False
            actions.append(action)
            field_finished = ( action.action.name == __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value
                               or action.action.name == __Action.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                               or action.action.name == __Action.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value
                               or action.action.name == __Action.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                               or action.action.name == __Action.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value
                               or action.action.name == __Action.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value )
        else:
            return False

        if field_finished:
            plan_data.field_masses[field_id] = 0.0
            plan_data.harv_locations[harv_id] = (harv_field_exit_name, upt.FieldAccess)
        else:
            plan_data.field_masses[field_id] = field_mass_new

        plan_data.tv_bunker_masses[tv_id] = (tv_bunker_mass_new, 100 * tv_bunker_mass_new / tv.bunker_mass, True)
        plan_data.tv_locations[tv_id] = (tv_field_exit_name, upt.FieldAccess)

        return True
