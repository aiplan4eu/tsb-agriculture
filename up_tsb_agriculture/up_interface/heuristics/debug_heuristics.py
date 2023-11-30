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
from typing import Set, Tuple

from unified_planning.shortcuts import *
import up_interface.types as upt
from up_interface.fluents import FluentsManagerBase
from up_interface.fluents import FluentNames as fn
from up_interface.problem_encoder.problem_objects import ProblemObjects
from up_interface.problem_encoder.problem_stats import *
from up_interface.heuristics.heuristics_base import HeuristicBase


class HeuristicDebugFluents(HeuristicBase):

    """ Special heuristic calculator used solely to save in a file specific fluent values for a given state """

    def __init__(self, fluents_to_print: Union[Sequence[Union[fn, Fluent, str]], Set[Union[fn, Fluent, str]]] = None,
                 file_name: str = "/tmp/heuristic_debug_fluents.txt"):

        """ Class initialization

        Parameters
        ----------
        fluents_to_print : Sequence[Union[fn, Fluent]]
            Set of fluents to be saved. If None, all non-static fluents will be printed. If empty, no fluents will be saved.
        file_name : str
            Output file name/path
        """

        self.__file_name = file_name
        self.__fluents_to_print = fluents_to_print

        if self.__fluents_to_print is not None and len(self.__fluents_to_print) == 0:
            return

        open(file_name, 'w').close()

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Returns 0

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        state : State
            State

        Returns
        ----------
        cost : float
            Cost = 0
        """

        if self.__fluents_to_print is not None and len(self.__fluents_to_print) == 0:
            return 0

        fluents_by_type: Dict[Type, List[Fluent]] = dict()
        process_fluents = list()

        def sort_fluent(fluent: Fluent):
            if fluent is None:
                return
            if len(fluent.signature) > 1:
                return
            if len(fluent.signature) == 0:
                process_fluents.append(fluent)
                return

            _type = fluent.signature[0].type
            type_fls = fluents_by_type.get(_type)
            if type_fls is None:
                fluents_by_type[_type] = [fluent]
            else:
                type_fls.append(fluent)

        if self.__fluents_to_print is None:
            __fluents_to_print = list()
            problem_fluents = problem.fluents
            problem_fluents_static = problem.get_static_fluents()
            for problem_fluent in problem_fluents:
                if problem_fluent not in problem_fluents_static:
                    sort_fluent(problem_fluent)

        else:
            for fluent_to_print in self.__fluents_to_print:
                try:
                    if isinstance(fluent_to_print, str):
                        sort_fluent(problem.fluent(fluent_to_print))
                    elif isinstance(fluent_to_print, fn):
                        sort_fluent(problem.fluent(f'{fluent_to_print.value}'))
                    else:
                        sort_fluent(fluent_to_print)
                except Exception as e:
                    continue

        try:
            f = open(self.__file_name, "a")

            def print_value(fl: Fluent, *args, tabs_count: int = 1, print_params=True):

                tabs = '\t'*tabs_count

                if len(fl.signature) == 0:
                    params = ''
                    val = state.get_value(fl()).constant_value()
                else:
                    if print_params:
                        params = f'{args}'
                    else:
                        params = ''
                    val = state.get_value(fl(*args)).constant_value()

                if isinstance(val, Fraction):
                    val = float(val)
                f.write(f'{tabs}{fl.name}{params} = {val}\n')

            def print_for_objects(fluents, objs, no_obj=None):
                sorted_objs = list(objs)
                sorted_objs.sort(key=lambda x: x.name)
                for obj in sorted_objs:
                    if obj is no_obj:
                        continue
                    _obj = problem.object(obj.name)
                    f.write(f'\t{obj.name}:\n')
                    for fl in fluents:
                        print_value(fl, _obj, tabs_count=2, print_params=True)

            f.write(f'\n\n------- STATE: {id(state)} --------\n\n')

            if len(process_fluents) > 0:
                f.write(f'Process fluents:\n')
                for fl in process_fluents:
                    print_value(fl)

            for _type, fluents in fluents_by_type.items():
                f.write(f'{_type} fluents:\n')
                print_for_objects(fluents,
                                  problem.objects(_type),
                                  objects.get_no_object_by_type(_type))

            f.write(f'---------------\n\n')
            f.close()
            return 0
        except OSError:
            return 0

    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> float:

        """ Returns 0

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects

        Returns
        ----------
        max_cost : float
            Maximum cost = 0
        """

        return 0


class HeuristicDebugActionConditions(HeuristicBase):

    """ Special heuristic calculator used solely to save in a file specific fluent values for a given state """

    def __init__(self, actions_to_print: Sequence[Union[Action, str]] = None, file_name: str = "/tmp/heuristic_debug_action_conditions.txt"):

        """ Class initialization

        Parameters
        ----------
        actions_to_print : Set[FluentNames]
            Set of fluents to be saved. If None, the default set of fluents will be used. If empty, no fluents will be saved.
        file_name : str
            Output file name/path
        """

        self.__file_name = file_name
        self.__actions_to_print = actions_to_print

        if self.__actions_to_print is not None and len(self.__actions_to_print) == 0:
            return

        open(file_name, 'w').close()

    def get_cost(self,
                 problem: Problem,
                 fluents_manager: FluentsManagerBase,
                 objects: ProblemObjects,
                 state: State) -> Union[float, None]:

        """ Returns 0

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects
        state : State
            State

        Returns
        ----------
        cost : float
            Cost = 0
        """

        if self.__actions_to_print is not None and len(self.__actions_to_print) == 0:
            return 0

        if self.__actions_to_print is None:
            __actions_to_print = problem.actions
        else:
            __actions_to_print = self.__actions_to_print

        try:
            f = open(self.__file_name, "a")

            def get_arg_objects(arg: FNode) -> List[FNode]:
                objs = None
                no_obj = None
                if arg.type is upt.Field:
                    objs = problem.objects(upt.Field)
                    no_obj = objects.no_field
                elif arg.type is upt.FieldAccess:
                    objs = problem.objects(upt.FieldAccess)
                    no_obj = objects.no_field_access
                elif arg.type is upt.Silo:
                    objs = problem.objects(upt.Silo)
                elif arg.type is upt.SiloAccess:
                    objs = problem.objects(upt.SiloAccess)
                    no_obj = objects.no_silo_access
                elif arg.type is upt.Harvester:
                    objs = problem.objects(upt.Harvester)
                    no_obj = objects.no_harvester
                elif arg.type is upt.TransportVehicle:
                    objs = problem.objects(upt.TransportVehicle)
                elif arg.type is upt.Compactor:
                    objs = problem.objects(upt.Compactor)
                    no_obj = objects.no_compactor
                if objs is None:
                    return list()
                ret = list()
                for obj in objs:
                    if no_obj is None or obj.name != no_obj.name:
                        ret.append(ObjectExp(obj))
                return ret

            def get_arg_values(args_objs: List[Tuple[FNode, List[FNode]]],
                               values_dicts: List[List[FNode]],
                               current_values: List[FNode] = [],
                               ind=0):
                if ind >= len(args_objs):
                    return
                arg, objs = args_objs[ind]
                for obj in objs:
                    _current_values = current_values.copy()
                    _current_values.append(obj)
                    if ind == len(args_objs) - 1:
                        values_dicts.append(_current_values)
                    else:
                        get_arg_values(args_objs, values_dicts, _current_values, ind+1)

            def get_fluents_values(node: FNode) -> Dict[str, str]:
                if node.is_constant():
                    return {}
                elif node.is_fluent_exp():
                    fl_args_str = f'{node}'
                    ind_args = fl_args_str.find('(')
                    if ind_args >= 0:
                        fluent_name = fl_args_str[:ind_args]
                    else:
                        fluent_name = fl_args_str

                    if len(node.args) == 0:
                        fluent_exp = FluentExp( problem.fluent(f'{fluent_name}'), [] )
                        return {f'{fluent_name}': f'{state.get_value(fluent_exp).constant_value()}'}

                    args = list()
                    for arg in node.args:
                        args.append( ( arg, get_arg_objects(arg) ) )

                    ret = dict()
                    values_dicts = list()
                    get_arg_values(args, values_dicts )
                    for arg_values in values_dicts:
                        fluent_exp = FluentExp( problem.fluent(f'{fluent_name}'), arg_values )
                        ret[f'{fluent_name}{arg_values}'] = f'{state.get_value(fluent_exp).constant_value()}'
                    return ret
                else:
                    ret = dict()
                    for arg in node.args:
                        fv = get_fluents_values(arg)
                        for k, v in fv.items():
                            ret[k] = v
                    return ret

            f.write(f'\n------- STATE: {id(state)} --------\n')
            for _action in __actions_to_print:
                if isinstance(_action, str):
                    action: Action = problem.action(_action)
                else:
                    action: Action = problem.action(_action.name)
                if action is None:
                    continue

                if isinstance(action, InstantaneousAction):
                    conditions = action.preconditions

                    f.write(f'\n---------------\n')
                    f.write(f'ACTION: {action.name}{action.parameters}\n')
                    for condition in conditions:
                        fluent_values = get_fluents_values(condition)
                        f.write(f'\t{condition}:\n')
                        for fl, v in fluent_values.items():
                            f.write(f'\t\t{fl} = {v}\n')
                    f.write(f'\n---------------\n')
                    f.write('')

                elif isinstance(action, DurativeAction):
                    conditions = action.conditions

                    f.write(f'\n---------------\n')
                    f.write(f'ACTION: {action.name}{action.parameters}\n')
                    for timing, conditions_timing in conditions.items():
                        f.write(f'\t[{timing}]\n')
                        for condition in conditions_timing:
                            fluent_values = get_fluents_values(condition)
                            f.write(f'\t\t{condition}:\n')
                            for fl, v in fluent_values.items():
                                f.write(f'\t\t\t{fl} = {v}\n')
                    f.write(f'\n---------------\n')
            f.write(f'\n\n------------------------------\n\n')
        except Exception as e:
            pass

        return 0

    def get_max_cost(self,
                     problem: Problem,
                     fluents_manager: FluentsManagerBase,
                     objects: ProblemObjects) -> float:

        """ Returns 0

        Parameters
        ----------
        problem : Problem
            Problem
        fluents_manager : FluentsManagerBase
            Fluents manager holding the problem fluents
        objects : ProblemObjects
            Holds all the problem objects

        Returns
        ----------
        max_cost : float
            Maximum cost = 0
        """

        return 0
