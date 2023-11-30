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

from unified_planning.shortcuts import Problem
from unified_planning.plans.time_triggered_plan import TimeTriggeredPlan
from unified_planning.plans.sequential_plan import SequentialPlan
from unified_planning.plans.plan import PlanKind

from management.global_data_manager import GlobalDataManager
from route_planning.outfield_route_planning import OutFieldRoutePlanner
from post_processing.sequential_plan_decoder import SequentialPlanDecoder
from post_processing.temporal_plan_decoder import TemporalPlanDecoder
from file_io.json.io_problem_state import *
from file_io.json.io_common import *
from visualization.plan_simulation_1 import PlanSimulator1

try:
    from post_processing.arolib_plan_generator import ArolibPlanGenerator
    __with_arolib = True

except ModuleNotFoundError as err:
    __with_arolib = False


def generate_and_save_states(path_out: str,
                             timestamp: float,
                             data_manager: GlobalDataManager,
                             roads: List[Linestring],
                             machine_initial_states: Dict[int, MachineState],
                             field_initial_states: Dict[int, FieldState],
                             out_field_route_planner: OutFieldRoutePlanner,
                             problem: Problem,
                             problem_settings: GeneralProblemSettings,
                             plan_or_decoder: Union[TimeTriggeredPlan, SequentialPlan, PlanDecoderBase],
                             deviations: Optional[PlanDeviations] = None) -> bool:

    """ Decodes a plan and generate the states for a given timestamp

    Parameters
    ----------
    path_out : str
        Path (folder) where the states will be saved
    timestamp : float
        Cut timestamp to obtain the states
    data_manager : GlobalDataManager
        Data manager
    roads : List[Linestring]
        Roads
    machine_initial_states : Dict[int, MachineState]
        Machine initial states: {machine_id: machine_state}
    field_initial_states : Dict[int, FieldState]
        Field initial states: {field_id: field_state}
    out_field_route_planner : OutFieldRoutePlanner
        Route/path planner for transit outside the fields
    problem : Problem
        UP problem
    problem_settings : GeneralProblemSettings
        Problem settings used to define the problem
    plan_or_decoder : TimeTriggeredPlan, SequentialPlan, PlanDecoderBase
        Temporal/sequential plan or a decoder with a decoded plan
    deviations : PlanDeviations, None
        Deviations to be applied to the state at the given timestamp

    Returns
    ----------
    success : bool
        True on success
    """

    if isinstance(plan_or_decoder, PlanDecoderBase):
        plan_decoder_sim = plan_or_decoder
    else:
        plan = plan_or_decoder
        if plan.kind is PlanKind.TIME_TRIGGERED_PLAN:
            plan_decoder = TemporalPlanDecoder(data_manager, roads,
                                               machine_initial_states, field_initial_states,
                                               out_field_route_planner,
                                               problem,
                                               plan)

        elif plan.kind is PlanKind.SEQUENTIAL_PLAN:
            plan_decoder = SequentialPlanDecoder(data_manager, roads,
                                                 machine_initial_states,
                                                 field_initial_states,
                                                 out_field_route_planner,
                                                 problem,
                                                 plan)
        else:
            warnings.warn(f'[ERROR] Invalid planning kind: {plan.kind}')
            return False

        if not __with_arolib:
            plan_decoder_sim = plan_decoder
        else:
            try:
                plan_decoder_sim = ArolibPlanGenerator(data_manager, roads,
                                                       machine_initial_states,
                                                       field_initial_states,
                                                       out_field_route_planner,
                                                       problem,
                                                       plan_decoder)
                if not plan_decoder_sim.ok:
                    warnings.warn('Error decoding plan and generating arolib plan')
                    plan_decoder_sim = plan_decoder
            except Exception as e:
                warnings.warn(f'Error decoding plan and generating arolib plan: {e}')
                plan_decoder_sim = plan_decoder

    sim = PlanSimulator1(data_manager, roads,
                         machine_initial_states, field_initial_states,
                         out_field_route_planner,
                         problem,
                         problem_settings,
                         plan_decoder_sim)

    return save_problem_state_from_plan(path_out, sim.plan_decoder, timestamp, deviations)
