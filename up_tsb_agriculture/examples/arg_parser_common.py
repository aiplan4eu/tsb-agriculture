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

import argparse
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from typing import Dict, Any, Union, List
import tempfile

from route_planning.types import FieldState
from route_planning.field_route_planning import PlanningSettings
from up_interface.config import GeneralProblemSettings


class ConfigParams:

    """ Class holding the common/shard example configuration parameters/arguments """

    def __init__(self):

        """ Class initialization with default parameter/argument values """

        self.planner: str = 'tamer'
        """ Planner (engine) """

        self.use_custom_heuristic: bool = True
        """ Use custom heuristic """

        self.plan_type: str = 'from_problem_settings'
        """ Planning type """

        self.shuffle_fields: bool = False
        """ Revere the order of the fields before creating the problem """

        self.reverse_fields: bool = False
        """ Shuffle the fields before creating the problem """


        self.pre_assign_fields_count: int = 0
        """ Amount of fields to be pre-assigned to harvesters """

        self.pre_assign_field_turns_count: int = 0
        """ Amount of field turns to pre-assign to a harvester """

        self.pre_assign_harvs_to_tvs_count: int = 0
        """ Amount of harvesters to be pre-assigned to transport vehicles """

        self.pre_assign_tvs_per_harvester: int = 0
        """ Amount of transport vehicles to be pre-assigned to a harvester """

        self.pre_assign_assign_tv_turns_count: int = 0
        """ Amount of transport-vehicle turns to pre-assign to a harvester """

        self.pre_assign_cyclic_tv_turns: bool = True
        """ Pre-assign the transport-vehicle turns as cyclic """


        self.default_yield: float = FieldState.DEFAULT_AVG_MASS_PER_AREA_T_HA
        """ Default yield mass per area unit (t/ha) """

        self.default_headland_width: float = PlanningSettings.DEFAULT_HEADLAND_WIDTH
        """ Default headland width (m) """


        self.do_sim: bool = False
        """ Run simulation """

        self.do_sim_arolib: bool = False
        """ Run simulation with arolib (if available, otherwise run normal sim) """


        self.plot_scene: bool = False
        """ Plot the scene before planning """

        self.plot_plan_1: bool = False
        """ Plot the plan (splitting single actions) """

        self.plot_plan_2: bool = False
        """ Plot the plan (without splitting single actions) """

        self.intermediate_states_ts: List = list()
        """ Timestamps of the intermediate states to be generated and saved """

        self.path_intermediate_states: str = f'{tempfile.gettempdir()}/aiplan4eu_agriculture'
        """ Directory where the intermediate states will be saved """


        self.results_file: str = ''
        """ Filename to save the results (CSV) """


        self.problem_settings_file: str = ''
        """ Path to the file holding the problem settings (if given, the problem settings will be loaded from this file 
        and any problem settings loaded directly from the config file will be taken as base) """

        self.problem_settings = GeneralProblemSettings()
        """ Problem settings """


def update_from_args(_obj: Any, _args: Union[Dict, 'argparse.Namespace']):

    """ Updates the properties (variables) of an object from a dictionary/argparse.Namespace holding the argument values

    The name of the object property must be equal to the corresponding key on the input dictionary or the corresponding property in the Namespace.

    Parameters
    ----------
    _obj : Any
        Object to be updated
    _args : Dict, argparse.Namespace
        Dictionary or argparse.Namespace holding the argument values
    """

    c = type(_obj)()
    _atts: Dict = c.__dict__
    if isinstance(_args, Namespace):
        _args_dict = _args.__dict__
    else:
        _args_dict = _args
    for _n, _v in _atts.items():
        if _n in _args_dict.keys():
            _v2 = _args_dict[_n]
            if _v2 is None:  # set default
                setattr(_obj, _n, c.__getattribute__(_n))
            elif type(_v) is type(_v2):
                setattr(_obj, _n, _v2)


def check_arg_positive(value: str) -> int:

    """ Returns the integer corresponding to a given string value iif the value corresponds to a positive integer,
    otherwise raises an error.

    Parameters
    ----------
    value : str
        Value as string

    Returns
    ----------
    value : int
        Value

    Raises
    ------
    ArgumentTypeError
        If the value does not correspond to a positive integer.
    """

    try:
        v = int(value)
        if v > 0:
            return v
    except:
        pass
    raise ArgumentTypeError("This value must be a positive integer (> 0)")


def check_arg_f_positive(value: str) -> float:

    """ Returns the float corresponding to a given string value iif the value corresponds to a positive float,
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
        If the value does not correspond to a positive float.
    """

    try:
        v = float(value)
        if v > 0:
            return v
    except:
        pass
    raise ArgumentTypeError("This value must be a positive float (> 0)")


def check_arg_non_negative(value: str) -> int:

    """ Returns the integer corresponding to a given string value iif the value corresponds to a non-negative integer,
    otherwise raises an error.

    Parameters
    ----------
    value : str
        Value as string

    Returns
    ----------
    value : int
        Value

    Raises
    ------
    ArgumentTypeError
        If the value does not correspond to a non-negative integer.
    """

    try:
        v = int(value)
        if v >= 0:
            return v
    except:
        pass
    raise ArgumentTypeError("This value must be a non-negative integer (>= 0)")


def add_common_args(parser: ArgumentParser):

    """ Add the common/shared example arguments to an ArgumentParser.

    Parameters
    ----------
    parser : ArgumentParser
        Argument-parser to be updated
    """

    c = ConfigParams()

    parser.add_argument('--planner', '-pn', default=c.planner,
                        help='Planner (engine). If "_auto_" -> lets UP select ')

    parser.add_argument('--use_custom_heuristic', '-uch',
                        action='store_false' if c.use_custom_heuristic else 'store_true',
                        help='Use custom heuristic')

    parser.add_argument('--config_file', '-cf', default=None,
                        help='Path of the file from which the configuration parameters will be loaded. '
                             'Other given parameters will be disregarded unless explicitly stated')

    parser.add_argument('--plan_type', '-pt', default=c.plan_type,
                        choices=['from_problem_settings', 'temporal', 'temp', 't', 'sequential', 'seq', 's'],
                        help='Planning type. '
                             'Will overwrite the type given in the config_file and problem_settings_file if loaded!')

    parser.add_argument('--shuffle_fields', '-shf',
                        action='store_false' if c.shuffle_fields else 'store_true',
                        help='Shuffle the fields before creating the problem')
    parser.add_argument('--reverse_fields', '-rvf',
                        action='store_false' if c.reverse_fields else 'store_true',
                        help='Revere the order of the fields before creating the problem')

    parser.add_argument('--pre_assign_fields_count', '-paf', type=check_arg_non_negative,
                        default=c.pre_assign_fields_count,
                        help='Amount of fields to be pre-assigned to harvesters')
    parser.add_argument('--pre_assign_field_turns_count', '-paft', type=check_arg_non_negative,
                        default=c.pre_assign_field_turns_count,
                        help='Amount of field turns to pre-assign to a harvester')
    parser.add_argument('--pre_assign_harvs_to_tvs_count', '-pahtt', type=check_arg_non_negative,
                        default=c.pre_assign_harvs_to_tvs_count,
                        help='Amount of harvesters to be pre-assigned to transport vehicles')
    parser.add_argument('--pre_assign_tvs_per_harvester', '-patph', type=check_arg_non_negative,
                        default=c.pre_assign_tvs_per_harvester,
                        help='Amount of transport vehicles to be pre-assigned to a harvester')
    parser.add_argument('--pre_assign_assign_tv_turns_count', '-patt', type=check_arg_non_negative,
                        default=c.pre_assign_assign_tv_turns_count,
                        help='Amount of transport-vehicle turns to pre-assign to a harvester')
    parser.add_argument('--pre_assign_cyclic_tv_turns', '-pactt',
                        action='store_false' if c.pre_assign_cyclic_tv_turns else 'store_true',
                        help='Pre-assign the transport-vehicle turns as cyclic')

    parser.add_argument('--default_yield', '-defy', type=check_arg_f_positive,
                        default=c.default_yield,
                        help='Default yield mass per area unit (t/ha)')

    parser.add_argument('--default_headland_width', '-defhw', type=check_arg_f_positive,
                        default=c.default_headland_width,
                        help='Default headland width (m)')


    parser.add_argument('--do_sim', '-sim',
                        action='store_false' if c.do_sim else 'store_true',
                        help='Run simulation')
    parser.add_argument('--do_sim_arolib', '-sima',
                        action='store_false' if c.do_sim_arolib else 'store_true',
                        help='Run simulation with arolib (if available, otherwise run normal sim)')

    parser.add_argument('--plot_scene', '-ps',
                        action='store_false' if c.plot_scene else 'store_true',
                        help='Plot the scene before planning')
    parser.add_argument('--plot_plan_1', '-pp1',
                        action='store_false' if c.plot_plan_1 else 'store_true',
                        help='Plot the plan (splitting single actions)')
    parser.add_argument('--plot_plan_2', '-pp2',
                        action='store_false' if c.plot_plan_2 else 'store_true',
                        help='Plot the plan (without splitting single actions)')

    parser.add_argument('--intermediate_states_ts', '-ists', type=check_arg_f_positive, nargs='*',
                        help='Timestamps of the intermediate states to be generated and saved')
    parser.add_argument('--path_intermediate_states', '-pis',
                        default=c.path_intermediate_states,
                        help='Directory where the intermediate states will be saved')

    parser.add_argument('--results_file', '-rf',
                        default=c.results_file,
                        help='Filename to save the results (CSV)')

    parser.add_argument('--problem_settings_file', '-psf',
                        default=None,
                        help='Path to the file holding the problem settings. '
                             'Will overwrite the settings from the config_file if loaded')
