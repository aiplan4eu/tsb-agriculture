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
from unified_planning.engines.results import *
from functools import partial
from management.global_data_manager import GlobalDataManager
from management.field_partial_plan_manager import FieldPartialPlanManager
from management.pre_assignments import *
from up_interface.problem_encoder.problem_encoder import ProblemEncoder
from up_interface.heuristics.heuristics_factory import TemporalHeuristicsFactory, SequentialHeuristicsFactory
from up_interface.heuristics.heuristics_base import HeuristicBase
import up_interface.config as conf
from route_planning.types import MachineState, FieldState
from route_planning.outfield_route_planning import OutFieldRoutePlanner


class Orchestrator:

    """ Class used to create the problem encoder and use it to plan """

    class PlanningSettings:
        """ Class holding the planning configuration settings """

        def __init__(self):
            self.planner_name = 'tamer'
            """ UP-planner name """

            self.heuristic: Union[str, List[str], HeuristicBase, None] = None
            """ Heuristic name/names (built-in heuristic of the selected planner), or custom heuristic (HeuristicBase), or no heuristic (None) """

            self.weight: float = 0.8
            """ Heuristic weight """

    def __init__(self,
                 data_manager: GlobalDataManager,
                 machine_states: Dict[int, MachineState],
                 field_states: Dict[int, FieldState],
                 out_field_route_planner: OutFieldRoutePlanner,
                 problem_settings: Optional[conf.GeneralProblemSettings] = conf.default_problem_settings,
                 pre_assigned_fields: Optional[FieldPreAssignments] = None,
                 pre_assigned_tvs: Optional[TVPreAssignments] = None):

        """ Orchestrator initialization (incl. creation of the problem encoder and corresponding problem)

        Parameters
        ----------
        data_manager : GlobalDataManager
            Data manager
        out_field_route_planner : OutFieldRoutePlanner
            Route/path planner for transit outside the fields
        machine_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        field_states : Dict[int, FieldState]
            Field initial states: {field_id: field_state}
        problem_settings : config.GeneralProblemSettings
            Problem configuration settings
        pre_assigned_fields : FieldPreAssignments
            Field pre-assignments (disregarded if None)
        pre_assigned_tvs : TVPreAssignments
            Transport vehicle pre-assignments (disregarded if None)
        """

        field_plan_manager = FieldPartialPlanManager()

        self.__problem_encoder = ProblemEncoder(data_manager=data_manager,
                                                  field_plan_manager=field_plan_manager,
                                                  out_field_route_planner=out_field_route_planner,
                                                  machine_initial_states=machine_states,
                                                  field_initial_states=field_states,
                                                  problem_settings=problem_settings,
                                                  pre_assigned_fields=pre_assigned_fields,
                                                  pre_assigned_tvs=pre_assigned_tvs)

    @property
    def problem_encoder(self) -> ProblemEncoder:
        """ Get the problem encoder

        Returns
        ----------
        problem_encoder : ProblemEncoder
            Problem encoder
        """
        return self.__problem_encoder

    def plan(self,
             settings: Optional[Union[PlanningSettings, List[PlanningSettings]]] = None,
             base_plan_final_state: Optional[State] = None,
             timeout: Optional[float] = None,
             compilation_types: Optional[List[CompilationKind]] = None) \
            -> Tuple[Optional[PlanGenerationResult], Problem]:

        """ Get a plan for the generated problem using the given planning settings

        Parameters
        ----------
        settings : PlanningSettings | List[PlanningSettings]
            Planning configuration settings
        base_plan_final_state : State
            Final state for a valid base plan
        timeout : float
            Planning timeout
        compilation_types : List[CompilationKind]
            The problem will be compiled following these compilation types in order (only for non-custom heuristics)

        Returns
        ----------
        results : PlanGenerationResult
            Planning results
        """

        do_not_compile = False
        __problem = None

        def get_problem(problem: Problem) -> Problem:
            if compilation_types is None or len(compilation_types) == 0:
                return problem
            if do_not_compile:
                warnings.warn(f'The given settings do not allow problem compilation. Using original problem')
                return problem
            for ct in compilation_types:
                print(f'Compiling problem with {ct}...')
                with Compiler(
                    problem_kind=problem.kind,
                    compilation_kind=ct,
                ) as utfr:
                    res = utfr.compile(problem)
                    assert res is not None and res.problem is not None, f'Error compiling problem with compilation_type = {ct}'
                    problem = res.problem
            return problem

        try:

            if settings is None:
                settings = Orchestrator.PlanningSettings()
                settings.weight = 1.0
                settings.planner_name = 'tamer'
                if self.__problem_encoder.problem_settings.planning_type is conf.PlanningType.TEMPORAL:
                    settings.heuristic = TemporalHeuristicsFactory(problem=self.__problem_encoder.problem,
                                                                   fluents_manager=self.__problem_encoder.fluents_manager,
                                                                   objects=self.__problem_encoder.problem_objects,
                                                                   problem_stats=self.__problem_encoder.problem_stats,
                                                                   problem_settings=self.__problem_encoder.problem_settings) \
                        .get_heuristics(heuristic_type=TemporalHeuristicsFactory.HType.DEFAULT)
                else:
                    settings.heuristic = SequentialHeuristicsFactory(problem=self.__problem_encoder.problem,
                                                                     fluents_manager=self.__problem_encoder.fluents_manager,
                                                                     objects=self.__problem_encoder.problem_objects,
                                                                     problem_stats=self.__problem_encoder.problem_stats,
                                                                     base_plan_final_state=base_plan_final_state) \
                        .get_heuristics(heuristic_type=SequentialHeuristicsFactory.HType.DEFAULT)

            if isinstance(settings, list):
                def heuristic_cb(heuristic: HeuristicBase, state: State):
                    return heuristic.get_cost(self.__problem_encoder.problem, self.__problem_encoder.fluents_manager, self.__problem_encoder.problem_objects, state)

                planner_names = [s.planner_name for s in settings]
                planner_params = list()
                for i, s in enumerate(settings):
                    if s.planner_name == 'tamer':
                        if isinstance(s.heuristic, HeuristicBase):
                            do_not_compile = True

                            print(f'Planning with Tamer (custom heuristic - weight = {settings.weight}) [{i}]')
                            planner_params.append({'weight': s.weight,
                                                   'heuristic': partial(heuristic_cb, s.heuristic)})
                        else:
                            if settings.heuristic is None:
                                print(f'Planning with Tamer ( default heuristic - weight = {settings.weight} ) [{i}]')
                                planner_params.append({'weight': s.weight})
                            else:
                                print(f'Planning with Tamer ( heuristic: {settings.heuristic} - weight = {settings.weight} ) [{i}]')
                                planner_params.append({'weight': s.weight,
                                                       'heuristic': settings.heuristic})

                    else:
                        print(f'Planning with {s.planner_name} ( default params ) [{i}]')
                        planner_params.append({})

                planner = OneshotPlanner(names=planner_names, params=planner_params)
                # file_out = f = open('/tmp/up_agri_test_case', 'w')
                # return planner.solve(get_problem(self.__problem_encoder.problem), output_stream=file_out)
                __problem = get_problem(self.__problem_encoder.problem)
                return planner.solve(__problem, timeout=timeout), __problem

            elif settings.planner_name is not None:
                __problem = get_problem(self.__problem_encoder.problem)
                _params = dict()
                _params_str = ''
                if settings.weight is not None:
                    _params['weight'] = settings.weight
                    _params_str += f'- weight = {settings.weight} '

                if isinstance(settings.heuristic, HeuristicBase):
                    do_not_compile = True
                    print(f'Planning with {settings.planner_name} ( custom heuristic {_params_str})')

                    def heuristic_cb(state: State):
                        return settings.heuristic.get_cost(self.__problem_encoder.problem, self.__problem_encoder.fluents_manager, self.__problem_encoder.problem_objects, state)

                    if len(_params) > 0:
                        planner = OneshotPlanner(name=settings.planner_name, params=_params)
                    else:
                        planner = OneshotPlanner(name=settings.planner_name)

                    # file_out = f = open('/tmp/up_agri_test_case', 'w')
                    # return planner.solve(__problem, heuristic=heuristic_cb, output_stream=file_out), __problem
                    return planner.solve(__problem, heuristic=heuristic_cb, timeout=timeout), __problem

                if settings.heuristic is not None:
                    _params['heuristic'] = settings.heuristic
                    _params_str += f'- heuristic = {settings.heuristic} '

                if len(_params) > 0:
                    planner = OneshotPlanner(name=settings.planner_name, params=_params)
                else:
                    planner = OneshotPlanner(name=settings.planner_name)

                # file_out = f = open('/tmp/up_agri_test_case', 'w')
                # return planner.solve(__problem, output_stream=file_out), __problem
                return planner.solve(__problem, timeout=timeout), __problem

            else:

                planner_name = None

                #debug!
                # planner_name = 'tamer'
                # planner_name = 'pyperplan'
                # planner_name = 'cpor'
                # planner_name = 'enhsp'
                # planner_name = 'aries'
                # planner_name = 'fast-downward'
                # planner_name = 'lpg'
                # planner_name = 'skdecide'
                # planner_name = 'spiderplan'
                # planner_name = 'fmap'
                # planner_name = 'poc'

                __problem = get_problem(self.__problem_encoder.problem)
                if planner_name is None:
                    planner = OneshotPlanner(problem_kind=__problem.kind)
                else:
                    planner = OneshotPlanner(name=planner_name)

                print(f'Planning with {planner.name}')
                return planner.solve(__problem, timeout=timeout), __problem
        except Exception as e:
            warnings.warn(f'ERROR - PLANNING EXCEPTION: {e}')
            return None, __problem
