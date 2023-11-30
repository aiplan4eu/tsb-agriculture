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

import time
import warnings
from datetime import datetime

import unified_planning.shortcuts
from unified_planning.shortcuts import *
from unified_planning.engines.results import *
from unified_planning.plans.plan import Plan
from unified_planning.plans.time_triggered_plan import TimeTriggeredPlan
from unified_planning.plans.sequential_plan import SequentialPlan

from util_arolib.geometry import *
import up_interface.types as upt
from management.global_data_manager import GlobalDataManager
from management.pre_assignments import *
from up_interface.orchestrator import Orchestrator
from up_interface.problem_encoder.problem_encoder import ProblemEncoder
from up_interface.heuristics.heuristics_factory import TemporalHeuristicsFactory, SequentialHeuristicsFactory
import up_interface.config as conf
from route_planning.types import MachineState, FieldState
from route_planning.outfield_route_planning import OutFieldRoutePlanner
from pre_processing.sequential_plan_generator import SequentialPlanGenerator


class PlanResults:
    """ Class holding the planning results """

    def __init__(self):
        self.ok: bool = False
        """ Success flag """

        self.setup_time: float = -1.0
        """ Duration of the set-up process """

        self.planning_time: float = -1.0
        """ Duration of the planning process """

        self.plan_duration: float = -1.0
        """ Duration of the plan """

        self.count_actions: int = 0
        """ Amount of actions in the plan """

        self.count_overloads_total: int = 0
        """ Amount of overload activities in the plan """

        self.count_overloads_tvs: Dict[str, int] = dict()
        """ Amount of overload activities in the plan for each transport vehicle  {tv_name: count_overloads}"""

        self.fields_order: Dict[str, List[str]] = dict()
        """ Order in which the fields are harvested by each harvester {harv_name: field_name} """

        self.plan: Optional[Plan, SequentialPlan, TimeTriggeredPlan] = None
        """ Generated UP plan (None on failure) """

        self.problem_encoder: Optional[ProblemEncoder] = None
        """ Problem encoder used by the Orchestrator """

        self.validation_results: Optional[ValidationResult] = None
        """ UP validation result returned by the UP planning engine """

        self.problem_out: Optional[Problem] = None
        """ UP problem used for planning (might differ from the original problem created by the problem encoder one if a compiler was used """


def plan_and_validate(data_manager: GlobalDataManager,
                      machine_states: Dict[int, MachineState],
                      field_states: Dict[int, FieldState],
                      problem_settings: conf.GeneralProblemSettings,
                      out_field_route_planner: OutFieldRoutePlanner,
                      pre_assigned_fields: FieldPreAssignments = None,
                      pre_assigned_tvs: TVPreAssignments = None,
                      planner: Optional[str] = 'tamer',
                      use_custom_heuristic: bool = True,
                      print_problem: bool = True,
                      print_engines_info: bool = True) -> PlanResults:

    """ Creates a problem with the Orchestrator, plans and validates the resulting plan.

    Parameters
    ----------
    data_manager : GlobalDataManager
        Data manager
    machine_states : Dict[int, MachineState]
        Initial machine states
    field_states : Dict[int, FieldState]
        Initial field states
    problem_settings : config.GeneralProblemSettings
        Problem configuration settings
    out_field_route_planner : OutFieldRoutePlanner
        Route/path planner for transit outside the fields
    pre_assigned_fields : FieldPreAssignments
        Field pre-assignments (disregarded if None)
    pre_assigned_tvs : TVPreAssignments
        Transport vehicle pre-assignments (disregarded if None)
    planner : str, None
        Planner name (None -> automatically selected by UP)
    use_custom_heuristic : bool
        Use (default) custom heuristic (True) or the planner's built-in heuristic (False)
    print_problem : bool
        Print the problem information?
    print_engines_info : bool
        Print the information of all registered engines?

    Returns
    ----------
    planning_results : PlanResults
        Planning results
    """

    t_start = time.time()

    unified_planning.shortcuts.get_environment().credits_stream = None

    if print_engines_info:
        up.shortcuts.print_engines_info()

    timeout = 60 * 1

    total_field_area = 0

    for f in data_manager.fields.values():
        total_field_area += calc_area(f.outer_boundary)

    compilation_types = None

    orchestrator = Orchestrator(data_manager=data_manager,
                                out_field_route_planner=out_field_route_planner,
                                machine_states=machine_states,
                                field_states=field_states,
                                problem_settings=problem_settings,
                                pre_assigned_fields=pre_assigned_fields,
                                pre_assigned_tvs=pre_assigned_tvs)

    problem_encoder = orchestrator.problem_encoder

    if print_problem:
        print('PROBLEM\n')
        print(f'{problem_encoder.problem.kind}')
        print('\n')
        problem_encoder.print_problem()
        print('\nACTIONS:')
        for action in problem_encoder.problem.actions:
            print(f'\t{action.name}')
        print('')

    max_timestamp = None
    max_harv_waiting_time = None
    max_tv_waiting_time = None
    base_plan_final_state = None
    if problem_settings.planning_type is conf.PlanningType.SEQUENTIAL \
            and problem_settings.silo_planning_type is conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY:
        t_start_pre_plan = time.time()
        sequential_plan_generator = SequentialPlanGenerator(problem_encoder=problem_encoder)
        try:
            plan_0 = sequential_plan_generator.get_plan()
        except Exception as e:
            print(f'Pre-planning failed with exception: {e}')
            plan_0 = None
        print(f'Pre-planning result after {time.time() - t_start_pre_plan} s')
        if plan_0 is None:
            print('\tFAILED')
        else:
            max_timestamp = sequential_plan_generator.get_max_machine_timestamp()
            max_harv_waiting_time = sequential_plan_generator.get_harvesters_waiting_time()
            max_tv_waiting_time = sequential_plan_generator.get_tvs_waiting_time()
            print(f'\tmax_timestamp = {max_timestamp}')
            print(f'\tmax_harv_waiting_time = {max_harv_waiting_time}')
            print(f'\tmax_tv_waiting_time = {max_tv_waiting_time}')
            base_plan_final_state = sequential_plan_generator.final_state

    heuristic = None
    if use_custom_heuristic:
        if problem_settings.planning_type is conf.PlanningType.TEMPORAL:
            heuristic = TemporalHeuristicsFactory(problem=problem_encoder.problem,
                                                   fluents_manager=problem_encoder.fluents_manager,
                                                   objects=problem_encoder.problem_objects,
                                                   problem_stats=problem_encoder.problem_stats,
                                                   problem_settings=problem_settings) \
                                                    .get_heuristics(heuristic_type=TemporalHeuristicsFactory.HType.DEFAULT)

        else:
            heuristic = SequentialHeuristicsFactory(problem=problem_encoder.problem,
                                                     fluents_manager=problem_encoder.fluents_manager,
                                                     objects=problem_encoder.problem_objects,
                                                     problem_stats=problem_encoder.problem_stats,
                                                     base_plan_final_state=base_plan_final_state)\
                                                        .get_heuristics(heuristic_type=SequentialHeuristicsFactory.HType.DEFAULT)

    planning_settings = Orchestrator.PlanningSettings()
    planning_settings.planner_name = planner
    if use_custom_heuristic:
        planning_settings.weight = 1
    planning_settings.heuristic = heuristic

    plan_results = PlanResults()
    plan_results.problem_encoder = problem_encoder
    plan_results.setup_time = time.time()-t_start

    print(f'Start planning at: {datetime.now()}')
    t_start = time.time()
    result, plan_results.problem_out = orchestrator.plan(settings=planning_settings,
                                                         base_plan_final_state=base_plan_final_state,
                                                         timeout=timeout,
                                                         compilation_types=compilation_types)
    plan_results.planning_time = time.time()-t_start

    plan = None
    if result is not None:
        print(f'Planning result after {plan_results.planning_time} s: {result.status.name}')
        plan = result.plan
        plan_results.plan = plan

    if plan is not None:
        plan_results.ok = True
        plan_results.count_actions = 0
        plan_results.plan_duration = -1
        plan_results.count_overloads_total = 0
        plan_results.count_overloads_tvs = dict()
        print("Plan: ")
        if plan.kind is PlanKind.TIME_TRIGGERED_PLAN:
            plan_results.count_actions = len(plan.timed_actions)
            for start, action, duration in plan.timed_actions:
                if duration is None:
                    print("\t%s -> %s: %s [--]" % (float(start), float(start), action))
                else:
                    print("\t%s -> %s: %s [%s]" % (float(start), float(start)+float(duration), action, float(duration)))
                    plan_results.plan_duration = max(plan_results.plan_duration, float(start) + float(duration))
                if 'do_overload' in action.action.name:
                    plan_results.count_overloads_total += 1
                    count_machine = 0
                    machine_param_ind = -1
                    for i, param in enumerate(action.action.parameters):
                        if param.type is upt.TransportVehicle:
                            machine_param_ind = i
                            break
                    machine = f'{action.actual_parameters[machine_param_ind]}'
                    if machine in plan_results.count_overloads_tvs.keys():
                        count_machine = plan_results.count_overloads_tvs[machine]
                    plan_results.count_overloads_tvs[machine] = count_machine + 1
                elif 'init' in action.action.name and 'harv' in action.action.name and 'field' in action.action.name:
                    field_param_ind = -1
                    machine_param_ind = -1
                    for i, param in enumerate(action.action.parameters):
                        if param.type is upt.Harvester:
                            machine_param_ind = i
                        elif param.type is upt.Field:
                            field_param_ind = i
                    if machine_param_ind >= 0 and field_param_ind >= 0:
                        machine = f'{action.actual_parameters[machine_param_ind]}'
                        field = f'{action.actual_parameters[field_param_ind]}'
                        if machine not in plan_results.fields_order.keys():
                            plan_results.fields_order[machine] = list()
                        plan_results.fields_order[machine].append(field)

                # print(f'\t\taction name = {action.action.name}')
                # print(f'\t\taction params = {action.action.parameters}')
                # print(f'\t\taction actual params = {action.actual_parameters}')
        elif plan.kind is PlanKind.SEQUENTIAL_PLAN:
            plan_results.count_actions = len(plan.actions)
            for action in plan.actions:
                print(f'\t{action}')
                if 'overload' in f'{action}':
                    plan_results.count_overloads_total += 1
                    count_machine = 0
                    machine_param_ind = -1
                    for i, param in enumerate(action.action.parameters):
                        if param.type is upt.TransportVehicle:
                            machine_param_ind = i
                            break
                    machine = f'{action.actual_parameters[machine_param_ind]}'
                    if machine in plan_results.count_overloads_tvs.keys():
                        count_machine = plan_results.count_overloads_tvs[machine]
                    plan_results.count_overloads_tvs[machine] = count_machine + 1
                elif 'init' in action.action.name and 'field' in action.action.name:
                    field_param_ind = -1
                    machine_param_ind = -1
                    for i, param in enumerate(action.action.parameters):
                        if param.type is upt.Harvester:
                            machine_param_ind = i
                        elif param.type is upt.Field:
                            field_param_ind = i
                    if machine_param_ind >= 0 and field_param_ind >= 0:
                        machine = f'{action.actual_parameters[machine_param_ind]}'
                        field = f'{action.actual_parameters[field_param_ind]}'
                        if machine not in plan_results.fields_order.keys():
                            plan_results.fields_order[machine] = list()
                        plan_results.fields_order[machine].append(field)
        else:
            warnings.warn(f'[ERROR] Invalid plan kind: {plan.kind}')

        print(f'# actions = {plan_results.count_actions}')
        print(f'plan duration = {plan_results.plan_duration}')
        print(f'total # of overloads = {plan_results.count_overloads_total}')
        for m, o in plan_results.count_overloads_tvs.items():
            print(f'\t {m}: {o}')

    else:
        plan_results.ok = False
        print("No plan found.")

    count_fields = len(data_manager.fields.values())
    print(f'average field area = {total_field_area} / {count_fields} = {total_field_area/count_fields/10000} ha')
    print(f'Set-up time:  {plan_results.setup_time} s')
    print(f'Fields order:')
    for harv, fields in plan_results.fields_order.items():
        print(f'\t{harv}: {fields}')

    if result is not None:
        print(f'Planning result after {plan_results.planning_time} s: {result.status.name}')

    if plan_results.ok:
        with PlanValidator(problem_kind=problem_encoder.problem.kind, plan_kind=plan.kind) as plan_validator:
            plan_results.validation_results = plan_validator.validate(problem_encoder.problem, plan)
            if plan_results.validation_results.status is ValidationResultStatus.VALID:
                print(f'Plan validation done with {plan_results.validation_results.engine_name}: VALID')
            else:
                print(f'Plan validation done with {plan_results.validation_results.engine_name}: {plan_results.validation_results.status.name}!!!!!')
                print(f'\t {plan_results.validation_results.reason}')

    return plan_results
