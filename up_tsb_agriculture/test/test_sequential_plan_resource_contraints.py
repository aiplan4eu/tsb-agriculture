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

from unified_planning.shortcuts import PlanValidator
from unified_planning.engines.results import *
import up_interface.config as conf
from examples.common import complete_machine_states_near_silo, init_data_manager
from examples.location_data_gen_1 import *
from examples.machine_data_gen_1 import *
from route_planning.outfield_route_planning import SimpleOutFieldRoutePlanner
from management.field_partial_plan_manager import FieldPartialPlanManager
from pre_processing.sequential_plan_generator import SequentialPlanGenerator
from validation.sequential_plan_validation import *
from test._common import *


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
    problem_settings.planning_type = conf.PlanningType.SEQUENTIAL
    problem_settings.silo_planning_type = conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY
    problem_settings.effects_settings = conf.EffectsSettings(default=conf.EffectsOption.WITH_NORMAL_EFFECTS_AND_SIM_EFFECTS)
    problem_settings.action_decomposition_settings = conf.ActionsDecompositionSettings(default=False)

    print(f'Initializing problem encoder...')

    problem_encoder = ProblemEncoder(data_manager=data_manager,
                                     field_plan_manager=FieldPartialPlanManager(),
                                     out_field_route_planner=out_field_route_planner,
                                     machine_initial_states=machine_states,
                                     field_initial_states=field_states,
                                     problem_settings=problem_settings,
                                     pre_assigned_fields=None,
                                     pre_assigned_tvs=None)

    sequential_plan_generator = SequentialPlanGenerator(problem_encoder=problem_encoder)

    print(f'Generating plan with SequentialPlanGenerator...')

    try:
        plan = sequential_plan_generator.get_plan()
    except Exception as e:
        print(f'ERROR: SequentialPlanGenerator failed with exception: {e}')
        exit(f'SequentialPlanGenerator failed with exception: {e}')

    if plan is None:
        exit(f'SequentialPlanGenerator failed')

    print_plan_info(plan)

    max_timestamp = sequential_plan_generator.get_max_machine_timestamp()
    max_harv_waiting_time = sequential_plan_generator.get_harvesters_waiting_time()
    max_tv_waiting_time = sequential_plan_generator.get_tvs_waiting_time()
    print(f'\tmax_timestamp = {max_timestamp}')
    print(f'\tmax_harv_waiting_time = {max_harv_waiting_time}')
    print(f'\tmax_tv_waiting_time = {max_tv_waiting_time}')

    print('')

    plan_validator = PlanValidator(problem_kind=problem_encoder.problem.kind, plan_kind=plan.kind)

    print(f'Validating plan...')
    validation_results = plan_validator.validate(problem_encoder.problem, plan)
    if validation_results.status is not ValidationResultStatus.VALID:
        print(f'Plan validation done with {validation_results.engine_name}: {validation_results.status.name}!!!!!')
        print(f'\t {validation_results.reason}')
        sys.exit("Plan validation failed")

    print(f'Plan validation done with {validation_results.engine_name}: VALID')

    if not validate_sequential_plan(problem_encoder, plan):
        sys.exit("Internal validation failed")
