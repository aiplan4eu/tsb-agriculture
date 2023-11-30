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

""" Script to run examples on automatically generated (fake) campaign data """

import pathlib
import random
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, ArgumentTypeError

from unified_planning.plans.plan import PlanKind
from up_interface import config as conf
from examples.arg_parser_common import add_common_args, check_arg_non_negative, update_from_args
from examples.arg_parser_common import ConfigParams as CommonConfigParams
from examples.common import init_data_manager
from examples.plan_and_validate import plan_and_validate, PlanResults
from examples.common import complete_machine_states_near_silo
from examples.location_data_gen_1 import *
from examples.machine_data_gen_1 import *
from route_planning.outfield_route_planning import SimpleOutFieldRoutePlanner
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
        self.fields: int = 4
        """ Amount of fields """

        self.harvs: int = 2
        """ Amount of harvesters """

        self.tvs: int = 4
        """ Amount of transport vehicles """

        self.silos: int = 1
        """ Amount of silos """

        self.access_points_per_field: int = 1
        """ Amount of access points per field """

        self.access_points_per_silo: int = 1
        """ Amount of access points per silo """

        self.compactors_per_silo: int = 1
        """ Amount of compactors per silo """


        self.fields_harv_percent: List = []
        """ Harvested percentages of the fields [0,100], applied in order to the generated fields """

        self.tvs_filling_percent: List = []
        """ Filling percentages of the transport vehicles [0,100], applied in order to the generated TVs """


def check_arg_percentage(value):

    """ Returns the float corresponding to a given string value iif the value corresponds to a float in the range [0.0, 100.0],
    otherwise raises an error.

    Parameters
    ----------
    value : str
        Value as string

    Returns
    ----------
    value : float
        Value

    Raises
    ------
    ArgumentTypeError
        If the value does not correspond to a float in the range [0.0, 100.0].
    """

    try:
        v = float(value)
        if 0 <= v <= 100:
            return v
    except:
        pass
    raise ArgumentTypeError("This values must be numbers in the range [0.0, 100.0]")


def __get_argument_parser():

    """ Get the ArgumentParser for the example.

    Returns
    ----------
    parser : ArgumentParser
        Argument-parser
    """

    c = ConfigParams()

    parser = ArgumentParser(prog='plan_fake_campaign',
                            description='Generate a (fake) campaign and plan',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--fields', '-f', type=check_arg_non_negative, default=c.fields,
                        help='Amount of fields')
    parser.add_argument('--harvs', '-hv', type=check_arg_non_negative, default=c.harvs,
                        help='Amount of harvesters')
    parser.add_argument('--tvs', '-tvs', type=check_arg_non_negative, default=c.tvs,
                        help='Amount of transport vehicles')
    parser.add_argument('--silos', '-s', type=int, default=c.silos,
                        choices=[1, 2],
                        help='Amount of silos')
    parser.add_argument('--access_points_per_field', '-appf', type=check_arg_non_negative,
                        default=c.access_points_per_field,
                        help='Amount of access points per field')
    parser.add_argument('--access_points_per_silo', '-apps', type=check_arg_non_negative,
                        default=c.access_points_per_silo,
                        help='Amount of access points per silo')
    parser.add_argument('--compactors_per_silo', '-cps', type=check_arg_non_negative,
                        default=c.compactors_per_silo,
                        help='Amount of compactors per silo')

    parser.add_argument('--fields_harv_percent', '-fhp', type=check_arg_percentage, nargs='*',
                        help='Harvested percentages of the fields [0,100], applied in order to the generated fields')
    parser.add_argument('--tvs_filling_percent', '-tfp', type=check_arg_percentage, nargs='*',
                        help='Filling percentages of the transport vehicles [0,100], applied in order to the generated TVs')

    add_common_args(parser)

    return parser


def __get_result_output_string(tag: Optional[str], results: Optional[PlanResults], sep: str = ';'):

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
    else:
        if not load_object_from_file(args.config_file, params):
            exit(f'Error loading config file')

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
    compactors = list()
    roads = LinestringVector()
    machine_states = dict()
    field_states = dict()

    test_results_output = ''

    _description = f'{params.fields}F_{params.harvs}H_{params.tvs}TV_{params.silos}S'

    print(f'\nStarting test: ({_description})')

    get_test_location_data_1(params.fields, params.access_points_per_field,
                             params.access_points_per_silo, params.compactors_per_silo,
                             fields, silos, compactors, roads)
    if params.silos % 2 == 1:
        silos = [silos[0]]
        compactors = [compactors[0]]
    machines = generate_working_group(params.harvs, params.tvs)
    data_manager = init_data_manager(fields, machines, silos, compactors)
    machine_states: Dict[int, MachineState] = dict()
    complete_machine_states_near_silo(machines, silos[0], machine_states, 0.0)

    if params.shuffle_fields:
        random.shuffle(fields)
    elif params.reverse_fields:
        fields.reverse()

    if params.fields_harv_percent is not None:
        for i, pc in enumerate(params.fields_harv_percent):
            if i >= len(fields):
                break
            field_state = FieldState()
            field_state.harvested_percentage = pc
            field_states[fields[i].id] = field_state

    if params.tvs_filling_percent is not None:
        tvs = list()
        for m in machines:
            if m.machinetype is MachineType.OLV:
                tvs.append(m)
        for i, pc in enumerate(params.tvs_filling_percent):
            if i >= len(tvs):
                break
            machine_states[tvs[i].id].bunker_mass = tvs[i].bunker_mass * 0.01 * pc

    data_manager = init_data_manager(fields, machines, silos, compactors)
    complete_machine_states_near_silo(machines, silos[0], machine_states, 0.0)

    if params.plot_scene:
        ScenePlotter.plot(data_manager, roads, machine_states)

    out_field_route_planner = SimpleOutFieldRoutePlanner(roads)

    print(f"\nStarting test with generated data")
    results = plan_and_validate(data_manager, machine_states, field_states,
                                params.problem_settings,
                                out_field_route_planner,
                                get_pre_assigned_fields(params.pre_assign_fields_count,
                                                        params.pre_assign_field_turns_count,
                                                        fields, machines,
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
                               f'{_description}/plan_state__{ts}s')
                    save_problem_state_from_plan(_folder, sim.plan_decoder, ts)
                    sim.plan_decoder.print_states(f'{_folder}/plan_decoder_states.csv')
                    sim.print_states(f'{_folder}/sim_states.csv')

                if run_sim:
                    sim.start()

                plan_decoder = sim.plan_decoder

    print(f'\nFinished test: ({params.fields}F_{params.harvs}H_{params.tvs}TV_{params.silos}S)')

    test_results_output = __get_result_output_string(f'Generated data ({_description})', results)

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
