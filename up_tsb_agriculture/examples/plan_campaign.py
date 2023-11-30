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

""" Script to run examples on loaded campaign data """

import pathlib
import random
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from unified_planning.plans.plan import PlanKind
from up_interface import config as conf
from examples.arg_parser_common import add_common_args, update_from_args
from examples.arg_parser_common import ConfigParams as CommonConfigParams
from examples.common import init_data_manager
from examples.plan_and_validate import plan_and_validate, PlanResults
from examples.common import complete_machine_states_near_silo
from route_planning.outfield_route_planning import SimpleOutFieldRoutePlanner
from route_planning.field_route_planning import PlanningSettings
from post_processing.sequential_plan_decoder import SequentialPlanDecoder
from post_processing.temporal_plan_decoder import TemporalPlanDecoder
from pre_processing.pre_assign import *
from file_io.json.io_problem_state import *
from file_io.json.io_common import *
from visualization.scene_plotter import ScenePlotter
from visualization.temporal_plan_plotter import TemporalPlanPlotter
from visualization.sequential_plan_plotter import SequentialPlanPlotter
from visualization.plan_simulation_1 import PlanSimulator1

try:
    from post_processing.arolib_plan_generator import ArolibPlanGenerator
    __with_arolib = True

except ModuleNotFoundError as err:
    __with_arolib = False


class ConfigParams(CommonConfigParams):

    """ Class holding the example configuration parameters/arguments """

    def __init__(self):

        """ Class initialization with default parameter/argument values """

        # super(CommonConfigParams, self).__init__()
        super().__init__()
        self.path = ''
        """ Path to the directory fom which the campaign files will be loaded' """

        self.max_fields: int = -1
        """ Maximum amount of fields to be included in the campaign (if <= 0, all fields) """

        self.max_harvs: int = -1
        """ Maximum amount of harvesters to be included in the campaign (if <= 0, all harvesters) """

        self.max_tvs: int = -1
        """ Maximum amount of transport vehicles to be included in the campaign (if <= 0, all TVs) """


def __get_argument_parser() -> ArgumentParser:

    """ Get the ArgumentParser for the example.

    Returns
    ----------
    parser : ArgumentParser
        Argument-parser
    """

    c = ConfigParams()

    parser = ArgumentParser(prog='plan_campaign',
                            description='Load and plan a campaign with the given settings',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--path', '-p',
                        default=None,
                        help='Path to the directory fom which the campaign files will be loaded. '
                             'Will overwrite the path given in the config_file if loaded!')

    parser.add_argument('--max_fields', '-maxf', type=int, default=c.max_fields,
                        help='Maximum amount of fields to be included in the campaign (if <= 0, all fields)')
    parser.add_argument('--max_harvs', '-maxh', type=int, default=c.max_harvs,
                        help='Maximum amount of harvesters to be included in the campaign (if <= 0, all harvesters)')
    parser.add_argument('--max_tvs', '-maxtv', type=int, default=c.max_tvs,
                        help='Maximum amount of transport vehicles to be included in the campaign (if <= 0, all TVs)')

    add_common_args(parser)

    return parser


def __get_result_output_string(tag: Optional[str], results: Optional[PlanResults], sep: str = ';') -> str:

    """ Get the planning results as a (csv) string.

    Parameters
    ----------
    tag : str, None
        Tag corresponding to the result. If None, the header will be returned and the results will be disregarded.
    results : PlanResults
        Planning results.
    sep : str
        Separator

    Returns
    ----------
    result_str : str
        Result as a string (or header if tag is None)
    """

    if tag is None:
        return f'Scenario{sep}' \
               f'Success{sep}' \
               f'Planning time [s]{sep}' \
               f'Plan duration [s]{sep}' \
               f'Count actions{sep}' \
               f'Count overloads{sep}' \
               f'Overloads distribution{sep}'

    if results.ok:
        overloads_dist = ''
        for o in results.count_overloads_tvs.values():
            overloads_dist += f'{o}:'
        if len(overloads_dist) > 0:
            overloads_dist = overloads_dist[:-1]
        return f'{tag}{sep}' \
               f'OK{sep}' \
               f'{results.planning_time}{sep}' \
               f'{results.plan_duration}{sep}' \
               f'{results.count_actions}{sep}' \
               f'{results.count_overloads_total}{sep}' \
               f'{overloads_dist}{sep}'

    return f'{tag}{sep}FAILED{sep}'


if __name__ == '__main__':

    params = ConfigParams()

    args = __get_argument_parser().parse_args()
    if args.config_file is None or args.config_file == '':
        update_from_args(params, args)
        if params.path is None or params.path == '':
            params.path = f'{pathlib.Path(__file__).parent.parent.parent.resolve()}/test_data/campaigns/campaign_1'
            print(f'Planning default campaign in {params.path}')
    else:
        if not load_object_from_file(args.config_file, params):
            exit(f'Error loading config file')

        if args.path is not None and args.path != '':
            params.path = args.path
        else:
            if params.path.startswith('<>'):
                params.path = params.path.replace('<>', f'{pathlib.Path(__file__).parent.parent.parent.resolve()}', 1)

    do_sim_arolib = params.do_sim_arolib if __with_arolib else False

    FieldState.DEFAULT_AVG_MASS_PER_AREA_T_HA = params.default_yield
    PlanningSettings.DEFAULT_HEADLAND_WIDTH = params.default_headland_width

    planner = None if params.planner == '_auto_' else ConfigParams().planner if params.planner == '' else params.planner

    if params.problem_settings_file is not None and params.problem_settings_file != '':
        if params.problem_settings_file.startswith('<>'):
            params.problem_settings_file = params.problem_settings_file.replace('<>', f'{pathlib.Path(__file__).parent.parent.parent.resolve()}', 1)
        if not load_object_from_file(params.problem_settings_file, params.problem_settings):
            exit(f'Error loading problem settings from file')

    if params.plan_type is not None and params.plan_type != '' and params.plan_type != 'from_problem_settings':
        if params.plan_type.startswith('t'):
            params.problem_settings.planning_type = conf.PlanningType.TEMPORAL
        else:
            params.problem_settings.planning_type = conf.PlanningType.SEQUENTIAL


    fields = list()
    silos = list()
    machines = list()
    harvesters = list()
    tvs = list()
    compactors = list()
    roads = LinestringVector()

    test_results_output = ''

    load_locations(params.path, fields, silos, roads)
    load_machines(params.path, harvesters, tvs, compactors)
    machine_states = load_machine_states(params.path)
    field_states = load_field_states_2(params.path, fields)

    if len(fields) == 0:
        exit("No fields were loaded")
    if len(harvesters) == 0:
        exit("No harvesters were loaded")
    if len(tvs) == 0:
        exit("No transport vehicles were loaded")

    if params.shuffle_fields:
        random.shuffle(fields)
    elif params.reverse_fields:
        fields.reverse()

    if 0 < params.max_fields < len(fields):
        fields = fields[0: params.max_fields]
    if 0 < params.max_harvs < len(harvesters):
        harvesters = harvesters[0: params.max_harvs]
    if 0 < params.max_tvs < len(tvs):
        tvs = tvs[0: params.max_tvs]

    machines.extend(harvesters)
    machines.extend(tvs)

    data_manager = init_data_manager(fields, machines, silos, compactors)
    complete_machine_states_near_silo(machines, silos[0], machine_states, 0.0)

    if params.plot_scene:
        ScenePlotter.plot(data_manager, roads, machine_states)

    out_field_route_planner = SimpleOutFieldRoutePlanner(roads)

    print(f"\nStarting test with loaded data: ({len(fields)}F_{len(harvesters)}H_{len(tvs)}TV_{len(silos)}S)")
    results = plan_and_validate(data_manager, machine_states, field_states,
                                params.problem_settings,
                                out_field_route_planner,
                                get_pre_assigned_fields(params.pre_assign_fields_count,
                                                        params.pre_assign_field_turns_count,
                                                        fields, harvesters,
                                                        field_states, machine_states),
                                get_pre_assigned_tvs(params.pre_assign_harvs_to_tvs_count,
                                                     params.pre_assign_tvs_per_harvester,
                                                     params.pre_assign_assign_tv_turns_count,
                                                     machines, machine_states, silos,
                                                     params.pre_assign_cyclic_tv_turns),
                                planner=planner,
                                use_custom_heuristic=params.use_custom_heuristic,
                                print_problem=True,
                                print_engines_info=False)

    # if results.problem_out is not results.problem_encoder.problem:
    #     with open("/tmp/problem_original.txt", 'w') as file_out:
    #         file_out.write(f'{results.problem_encoder.problem}')
    #         file_out.close()
    #     with open("/tmp/problem_compiled.txt", 'w') as file_out:
    #         file_out.write(f'{results.problem_out}')
    #         file_out.close()

    if results.ok and results.plan is not None:

        plan_decoder = None

        if results.plan.kind is PlanKind.TIME_TRIGGERED_PLAN:
            if params.plot_plan_1:
                TemporalPlanPlotter().plot_plan(results.plan, True)
            if params.plot_plan_2:
                TemporalPlanPlotter().plot_plan_busy_actions(results.plan, False)

        elif results.plan.kind is PlanKind.SEQUENTIAL_PLAN:
            if plan_decoder is None:
                plan_decoder = SequentialPlanDecoder(data_manager, roads, machine_states, field_states,
                                                     out_field_route_planner,
                                                     results.problem_encoder.problem,
                                                     results.plan)

            if params.plot_plan_1:
                SequentialPlanPlotter().plot_plan_busy_actions(plan_decoder, True)
            if params.plot_plan_2:
                SequentialPlanPlotter().plot_plan_busy_actions(plan_decoder, False)

        else:
            warnings.warn(f'[ERROR] Invalid planning kind: {results.plan.kind}')
            results.ok = False

        if results.ok:
            run_sim = params.do_sim or do_sim_arolib
            create_sim = run_sim or len(params.intermediate_states_ts) > 0
            # create_sim = create_sim and results.problem_out is results.problem_encoder.problem

            if create_sim:

                sim = None
                plan_decoder_sim = None

                if do_sim_arolib:
                    try:
                        if plan_decoder is None:
                            if results.plan.kind is PlanKind.TIME_TRIGGERED_PLAN:
                                plan_decoder = TemporalPlanDecoder(data_manager, roads, machine_states, field_states,
                                                                   out_field_route_planner,
                                                                   results.problem_encoder.problem,
                                                                   results.plan)

                            elif results.plan.kind is PlanKind.SEQUENTIAL_PLAN:
                                plan_decoder = SequentialPlanDecoder(data_manager, roads, machine_states, field_states,
                                                                     out_field_route_planner,
                                                                     results.problem_encoder.problem,
                                                                     results.plan)
                            else:
                                raise ValueError(f'Invalid planning kind: {results.plan.kind}')
                        plan_decoder_sim = ArolibPlanGenerator(data_manager, roads, machine_states, field_states,
                                                               out_field_route_planner,
                                                               results.problem_encoder.problem,
                                                               plan_decoder)
                        if not plan_decoder_sim.ok:
                            warnings.warn('Error decoding plan and generating arolib plan')
                            sim = None
                            plan_decoder_sim = None
                    except Exception as e:
                        warnings.warn(f'Error decoding plan and generating arolib plan: {e}')
                        sim = None
                        plan_decoder_sim = None

                sim = PlanSimulator1(data_manager, roads, machine_states, field_states, out_field_route_planner,
                                     results.problem_encoder.problem, results.problem_encoder.problem_settings,
                                     results.plan if plan_decoder_sim is None else plan_decoder_sim)

                for ts in params.intermediate_states_ts:
                    _folder = (f'{params.path_intermediate_states}/'
                               f'{pathlib.Path(params.path).stem}/plan_state__{ts}s')
                    save_problem_state_from_plan(_folder, sim.plan_decoder, ts)
                    sim.plan_decoder.print_states(f'{_folder}/plan_decoder_states.csv')
                    sim.print_states(f'{_folder}/sim_states.csv')

                if run_sim:
                    sim.start()

                plan_decoder = sim.plan_decoder

    print(f'\nFinished test: ({len(fields)}F_{len(harvesters)}H_{len(tvs)}TV_{len(silos)}S)')

    test_results_output = __get_result_output_string(f'Loaded data ({len(fields)}F_'
                                                     f'{len(harvesters)}H_'
                                                     f'{len(tvs)}TV_'
                                                     f'{len(silos)}S)', results)

    print("---")
    print("Results overview:\n")
    print(__get_result_output_string(None, None))
    print(test_results_output)
    print("---")

    if params.results_file is not None and params.results_file != '':
        with open(params.results_file, 'w') as file_out:
            file_out.write(__get_result_output_string(None, None))
            file_out.write('\n')
            file_out.write(test_results_output)
            file_out.close()
