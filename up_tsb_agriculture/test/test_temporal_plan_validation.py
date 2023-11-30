#!/usr/bin/env python3

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

import sys
import random

from unified_planning.shortcuts import PlanValidator
from unified_planning.engines.results import *
import up_interface.config as conf
from examples.common import complete_machine_states_near_silo, init_data_manager
from examples.location_data_gen_1 import *
from examples.machine_data_gen_1 import *
from route_planning.outfield_route_planning import SimpleOutFieldRoutePlanner
from up_interface.orchestrator import Orchestrator
from up_interface.heuristics.heuristics_factory import TemporalHeuristicsFactory
from test._common import *


def __remove_random_actions(_plan: TimeTriggeredPlan, count: int) -> TimeTriggeredPlan:
    plan_out = deepcopy(_plan)
    while count > 0 and len(plan_out.timed_actions) > 0:
        plan_out.timed_actions.pop( random.randint(0, len(plan_out.timed_actions)-1) )
        count -= 1
    return plan_out


def __swap_random_actions(_plan: TimeTriggeredPlan, count: int) -> TimeTriggeredPlan:
    plan_out = deepcopy(_plan)
    if len(plan_out.timed_actions) < 2:
        return plan_out

    while count > 0:
        ind1 = random.randint(0, len(plan_out.timed_actions)-1)
        ind2 = random.randint(0, len(plan_out.timed_actions)-1)
        while ind1 == ind2:
            ind2 = random.randint(0, len(plan_out.timed_actions) - 1)
        act1 = ( plan_out.timed_actions[ind1][0], plan_out.timed_actions[ind2][1], plan_out.timed_actions[ind1][2] )
        act2 = ( plan_out.timed_actions[ind2][0], plan_out.timed_actions[ind1][1], plan_out.timed_actions[ind2][2] )
        plan_out.timed_actions[ind1] = act2
        plan_out.timed_actions[ind2] = act1
        count -= 1

    same = True
    for _i, action in enumerate(_plan.timed_actions):
        if f'{action}' != f'{plan_out.timed_actions[_i]}':
            same = False
            break
    if same:
        return __swap_random_actions(plan, count)
    return plan_out


def __change_random_durations(_plan: TimeTriggeredPlan, count: int, _factor: float) -> TimeTriggeredPlan:
    plan_out = deepcopy(_plan)
    if len(plan_out.timed_actions) < 1:
        return plan_out

    while count > 0:
        ind1 = random.randint(0, len(plan_out.timed_actions)-1)
        while len(plan_out.timed_actions[ind1]) < 3:
            ind1 = random.randint(0, len(plan_out.timed_actions)-1)
        duration = float(plan_out.timed_actions[ind1][2])
        plan_out.timed_actions[ind1] = ( plan_out.timed_actions[ind1][0], plan_out.timed_actions[ind1][1], Fraction(duration*_factor) )
        count -= 1
    return plan_out


def __change_all_action_starts(_plan: TimeTriggeredPlan, _factor: float) -> TimeTriggeredPlan:
    plan_out = deepcopy(_plan)

    for _i, action in enumerate(plan_out.timed_actions):
        duration = float(action[0])
        plan_out.timed_actions[_i] = (Fraction(duration*_factor), action[1], action[2])
    return plan_out


def __offset_all_action_starts(_plan: TimeTriggeredPlan, delta: float) -> TimeTriggeredPlan:
    plan_out = deepcopy(_plan)

    for _i, action in enumerate(plan_out.timed_actions):
        tstart = float(action[0])
        plan_out.timed_actions[_i] = (Fraction(tstart+delta), action[1], action[2])
    return plan_out


if __name__ == '__main__':

    fields = list()
    silos = list()
    compactors = list()
    roads = LinestringVector()
    machine_states = dict()
    field_states = dict()

    out_field_route_planner = SimpleOutFieldRoutePlanner(roads)

    get_test_location_data_1(2, 1, 1, 1, fields, silos, compactors, roads)
    silos = [silos[0]]
    compactors = [compactors[0]]

    machines = generate_working_group(1, 2)
    complete_machine_states_near_silo(machines, silos[0], machine_states, 0.0)

    data_manager = init_data_manager(fields, machines, silos, compactors)

    problem_settings = conf.GeneralProblemSettings()
    problem_settings.planning_type = conf.PlanningType.TEMPORAL
    problem_settings.silo_planning_type = conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY
    problem_settings.effects_settings = conf.EffectsSettings(default=conf.EffectsOption.WITH_NORMAL_EFFECTS_AND_SIM_EFFECTS)
    problem_settings.action_decomposition_settings = conf.ActionsDecompositionSettings(default=False)

    print(f'Initializing orchestrator...')

    orchestrator = Orchestrator(data_manager=data_manager,
                                out_field_route_planner=out_field_route_planner,
                                machine_states=machine_states,
                                field_states=field_states,
                                problem_settings=problem_settings,
                                pre_assigned_fields=None,
                                pre_assigned_tvs=None)

    problem_encoder = orchestrator.problem_encoder

    print(problem_encoder.problem)

    planning_settings = Orchestrator.PlanningSettings()
    planning_settings.planner_name = 'tamer'
    planning_settings.weight = 1
    planning_settings.heuristic = (TemporalHeuristicsFactory(problem=problem_encoder.problem,
                                                             fluents_manager=problem_encoder.fluents_manager,
                                                             objects=problem_encoder.problem_objects,
                                                             problem_stats=problem_encoder.problem_stats,
                                                             problem_settings=problem_settings)
                                   .get_heuristics(heuristic_type=TemporalHeuristicsFactory.HType.DEFAULT,
                                                   debug_heuristic_options=None))

    print(f'Generating plan...')

    result, problem_out = orchestrator.plan(settings=planning_settings,
                                            base_plan_final_state=None,
                                            timeout=60,
                                            compilation_types=None)

    if result.status not in [PlanGenerationResultStatus.SOLVED_SATISFICING,
                             PlanGenerationResultStatus.SOLVED_OPTIMALLY ]:
        exit(f'Planning failed: status = {result.status}')

    plan = result.plan
    if plan is None:
        exit(f'Planning failed (plan is None)')

    print_plan_info(plan)

    print('')

    plan_validator = PlanValidator(problem_kind=problem_encoder.problem.kind, plan_kind=plan.kind)

    print(f'Validating plan...')
    validation_results = plan_validator.validate(problem_encoder.problem, plan)
    if validation_results.status is not ValidationResultStatus.VALID:
        print(f'Plan validation done with {validation_results.engine_name}: {validation_results.status.name}!!!!!')
        print(f'\t {validation_results.reason}')
        sys.exit("Plan validation failed")

    print(f'Plan validation done with {validation_results.engine_name}: VALID')
    print("")

    print(f'Validating empty plan...')
    plan_invalid = deepcopy(plan)
    plan_invalid.timed_actions.clear()
    validation_results = plan_validator.validate(problem_encoder.problem, plan_invalid)
    if validation_results.status is ValidationResultStatus.VALID:
        print(f'Plan validation on invalid plan done with {validation_results.engine_name}: {validation_results.status.name}!!!!!')
        sys.exit("Plan validation on invalid plan failed")
    print(f'\tPlan validation done with {validation_results.engine_name}: {validation_results.status.name}')
    print("")

    for i in [1, 5, 10]:
        print(f'Removing {i} actions from plan and validating...')
        plan_invalid = __remove_random_actions(plan, i)
        validation_results = plan_validator.validate(problem_encoder.problem, plan_invalid)
        if validation_results.status is ValidationResultStatus.VALID:
            print(f'Plan validation on invalid plan done with {validation_results.engine_name}: {validation_results.status.name}!!!!!')
            sys.exit("Plan validation on invalid plan failed")
        print(f'\tPlan validation done with {validation_results.engine_name}: {validation_results.status.name}')
    print("")

    for i in [1, 5, 10]:
        print(f'Swapping {i} pairs of actions from plan and validating...')
        plan_invalid = __swap_random_actions(plan, i)
        validation_results = plan_validator.validate(problem_encoder.problem, plan_invalid)
        if validation_results.status is ValidationResultStatus.VALID:
            print(f'Plan validation on invalid plan done with {validation_results.engine_name}: {validation_results.status.name}!!!!!')
            sys.exit("Plan validation on invalid plan failed")
        print(f'\tPlan validation done with {validation_results.engine_name}: {validation_results.status.name}')
    print("")

    for i in [1, 5, 10]:
        for factor in [0.5, 2]:
            print(f'Changing durations of {i} actions from plan (factor = {factor}) and validating...')
            plan_invalid = __change_random_durations(plan, i, factor)
            validation_results = plan_validator.validate(problem_encoder.problem, plan_invalid)
            if validation_results.status is ValidationResultStatus.VALID:
                print(f'Plan validation on invalid plan done with {validation_results.engine_name}: {validation_results.status.name}!!!!!')
                sys.exit("Plan validation on invalid plan failed")
            print(f'\tPlan validation done with {validation_results.engine_name}: {validation_results.status.name}')

    print("")
    for factor in [0.5, 2]:
        print(f'Changing start times of all actions from plan (factor = {factor}) and validating...')
        plan_invalid = __change_all_action_starts(plan, factor)
        validation_results = plan_validator.validate(problem_encoder.problem, plan_invalid)
        if validation_results.status is ValidationResultStatus.VALID:
            print(f'Plan validation on invalid plan done with {validation_results.engine_name}: {validation_results.status.name}!!!!!')
            sys.exit("Plan validation on invalid plan failed")
        print(f'\tPlan validation done with {validation_results.engine_name}: {validation_results.status.name}')
    print("")

    for offset in [-100, -10, -1, 1, 10, 100]:
        print(f'Offsetting start times of all actions from plan by {offset}s and validating...')
        plan_invalid = __offset_all_action_starts(plan, offset)
        validation_results = plan_validator.validate(problem_encoder.problem, plan_invalid)
        if validation_results.status is not ValidationResultStatus.VALID:
            print(f'Plan validation on valid plan done with {validation_results.engine_name}: {validation_results.status.name}!!!!!')
            sys.exit("Plan validation on valid plan failed")
        print(f'\tPlan validation done with {validation_results.engine_name}: {validation_results.status.name}')
    print("")
