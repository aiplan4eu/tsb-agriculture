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

from typing import Dict, List, Callable, Tuple
from functools import partial
import unified_planning.model.expression
from up_interface.config import EffectsOption
from up_interface.types_helper import *

PRINT_ACTION_MESSAGES = False
""" Global variable to enable/control printing messages from action simulated effects (used for debug) """


def print_action_msg(msg: str):
    """ Print messages if enabled (used for debug) """
    if not PRINT_ACTION_MESSAGES:
        return
    print(msg)


def add_precondition_to_action(action: Union[InstantaneousAction, DurativeAction],
                               condition: Union[FNode, Fluent, Parameter, bool],
                               interval: Union[unified_planning.model.expression.TimeExpression , TimeInterval] = StartTiming()):
    """ Add a condition to an action, based on the action type (Instantaneous, Durative),
    at the given timing/interval (disregarded if Instantaneous action)

    Parameters
    ----------
    action : InstantaneousAction, DurativeAction
        Action
    condition : FNode, Fluent, Parameter, bool
        Condition
    interval : unified_planning.model.expression.TimeExpression , TimeInterval
        Interval (for DurativeActions)
    """

    if isinstance(action, InstantaneousAction):
        action.add_precondition(condition)
    elif isinstance(action, DurativeAction):
        action.add_condition(interval, condition)


def add_effect_to_action(action: Union[InstantaneousAction, DurativeAction],
                         fluent: Fluent,
                         value: unified_planning.model.expression.Expression,
                         timing: unified_planning.model.expression.TimeExpression = EndTiming(),
                         condition: Union[unified_planning.model.expression.BoolExpression, None] = None):
    """ Add an effect or conditional effect to an action, based on the action type (Instantaneous, Durative),
    at the given timing (disregarded if Instantaneous action)

    Parameters
    ----------
    action : InstantaneousAction, DurativeAction
        Action
    fluent : Fluent
        Fluent
    value : unified_planning.model.expression.Expression
        Value to be set to the fluent
    timing : unified_planning.model.expression.TimeExpression
        Timing when the effect will be applied (for DurativeActions)
    condition : unified_planning.model.expression.BoolExpression, None
        Condition to apply the effect (disregarded if = None)
    """

    if condition is None:
        if isinstance(action, InstantaneousAction):
            action.add_effect(fluent, value)
        elif isinstance(action, DurativeAction):
            action.add_effect(timing, fluent, value)
    else:
        if isinstance(action, InstantaneousAction):
            action.add_effect(fluent, value, condition)
        elif isinstance(action, DurativeAction):
            action.add_effect(timing, fluent, value, condition)


def add_decrease_effect_to_action(action: Union[InstantaneousAction, DurativeAction],
                                  fluent: Fluent,
                                  delta: unified_planning.model.expression.Expression,
                                  timing: unified_planning.model.expression.TimeExpression = EndTiming(),
                                  condition: Union[unified_planning.model.expression.BoolExpression, None] = None):
    """ Add a decrease effect or conditional effect to an action, based on the action type (Instantaneous, Durative),
    at the given timing (disregarded if Instantaneous action)

    Parameters
    ----------
    action : InstantaneousAction, DurativeAction
        Action
    fluent : Fluent
        Fluent
    delta : unified_planning.model.expression.Expression
        Delta to be applied to the fluent value
    timing : unified_planning.model.expression.TimeExpression
        Timing when the effect will be applied (for DurativeActions)
    condition : unified_planning.model.expression.BoolExpression, None
        Condition to apply the effect (disregarded if = None)
    """

    if condition is None:
        if isinstance(action, InstantaneousAction):
            action.add_decrease_effect(fluent, delta)
        elif isinstance(action, DurativeAction):
            action.add_decrease_effect(timing, fluent, delta)
    else:
        if isinstance(action, InstantaneousAction):
            action.add_decrease_effect(fluent, delta, condition)
        elif isinstance(action, DurativeAction):
            action.add_decrease_effect(timing, fluent, delta, condition)


def add_increase_effect_to_action(action: Union[InstantaneousAction, DurativeAction],
                                  fluent: Fluent,
                                  delta: unified_planning.model.expression.Expression,
                                  timing: unified_planning.model.expression.TimeExpression = EndTiming(),
                                  condition: Union[unified_planning.model.expression.BoolExpression, None] = None):
    """ Add an increase effect or conditional effect to an action, based on the action type (Instantaneous, Durative),
    at the given timing (disregarded if Instantaneous action)

    Parameters
    ----------
    action : InstantaneousAction, DurativeAction
        Action
    fluent : Fluent
        Fluent
    delta : unified_planning.model.expression.Expression
        Delta to be applied to the fluent value
    timing : unified_planning.model.expression.TimeExpression
        Timing when the effect will be applied (for DurativeActions)
    condition : unified_planning.model.expression.BoolExpression, None
        Condition to apply the effect (disregarded if = None)
    """

    if condition is None:
        if isinstance(action, InstantaneousAction):
            action.add_increase_effect(fluent, delta)
        elif isinstance(action, DurativeAction):
            action.add_increase_effect(timing, fluent, delta)
    else:
        if isinstance(action, InstantaneousAction):
            action.add_increase_effect(fluent, delta, condition)
        elif isinstance(action, DurativeAction):
            action.add_increase_effect(timing, fluent, delta, condition)


def add_simulated_effect_to_action(action: Union[InstantaneousAction, DurativeAction],
                                   effect: SimulatedEffect,
                                   timing: Timing = EndTiming()):
    """ Add a simulated effect to an action, based on the action type (Instantaneous, Durative),
    for a given timing (disregarded if Instantaneous action)

    Parameters
    ----------
    action : InstantaneousAction, DurativeAction
        Action
    effect : SimulatedEffect
        Simulated effect
    timing : Timing
        Timing when the effect will be applied (for DurativeActions)
    """

    if isinstance(action, InstantaneousAction):
        action.set_simulated_effect(effect)
    elif isinstance(action, DurativeAction):
        action.set_simulated_effect(timing, effect)


def set_duration_to_action(action: Union[InstantaneousAction, DurativeAction],
                           duration: up.model.expression.NumericExpression):
    """ Set a duration to an action, if applicable, based on the action type (Instantaneous, Durative).

    Parameters
    ----------
    action : InstantaneousAction, DurativeAction
        Action
    duration : unified_planning.model.expression.NumericExpression
        Action duration (for DurativeActions)
    """

    if isinstance(action, InstantaneousAction):
        return
    elif isinstance(action, DurativeAction):
        action.set_fixed_duration(duration)


def get_timing_before_end_timing(action_duration, delay: Union[float, Timing, None]):
    """ Get the timing corresponding to EndTiming() - delay (i.e., the timing  x seconds before EndTiming).

    Parameters
    ----------
    action_duration : up.model.expression.NumericExpression
        Action duration (for DurativeActions)
    delay : float, None
        delay
    """

    if delay is None or abs(delay) < 1e-12:
        return EndTiming()

    _delay = delay
    # _delay = get_up_fraction(delay)

    # return EndTiming(delay=delay)
    # return StartTiming(delay=Minus(action_duration, delay))
    return EndTiming() - _delay


class EffectsHandler:

    """ Class used to handle/manage an action's effects based on the problem effect settings."""

    FluentValuesDictType = Dict[Fluent, Tuple[Union[unified_planning.model.expression.Expression, None], bool]]
    """ Fluent values dictionary type: {fluent, (value, value_applies_in_sim_effect)} """

    SimEffectCallbackType = Callable[[Timing, FluentValuesDictType, Problem, State, Dict[Parameter, FNode]], List[FNode]]
    """ Callback type for simulated effects. Parameters: timing, {fluent, (value, value_applies_in_sim_effect)}, problem, state, parameters: Returns: List of fluent computed values in order. """

    def __init__(self):
        self.__values: Dict[Timing, EffectsHandler.FluentValuesDictType] = dict()
        self.__values_cond: Dict[Timing, Dict[unified_planning.model.expression.BoolExpression, EffectsHandler.FluentValuesDictType]] = dict()

    def add(self,
            timing: Timing,
            fluent: FNode,
            value: Union[unified_planning.model.expression.Expression, None],
            value_applies_in_sim_effect: bool,
            condition: Union[unified_planning.model.expression.BoolExpression, None] = None):
        """Add/register an effect with its respective timing, fluent, value and condition.

        Parameters
        ----------
        timing : Timing
            Timing of the effect
        fluent : FNode
            Fluent (with parameters) affected by the effect
        value : unified_planning.model.expression.Expression, None
            Value to be set to the fluent. If None or condition!=None or value_applies_in_sim_effect==False, the fluent value must be set via simulated effects.
        value_applies_in_sim_effect : bool
            If false, the fluent value must be set via simulated effects, no matter what the input <value> is.
            If true, the given value will be used by the simulated effects (disregarding any value set inside the simulated effect). Only constant boolean and numeric values can be given (e.g., Bool(b), Int(n), Real(Fraction(f))
        condition : unified_planning.model.expression.BoolExpression, None
            If None, only one effect must be added for a given timing and fluent
            If not None, this means this is a conditional effect. More than one conditional effect can be added to a given timing and fluent. Also, if no conditional effects are being used, the fluent value must be set via simulated effects.
        """

        # #debug
        # print(f'Adding effect to fluent {fluent} at timing ({timing})')

        f_type = get_up_type_as_str(fluent)
        if value is not None:
            if not isinstance(value, (FNode, Parameter, Object)):
                if is_up_type_bool(f_type):
                    if not isinstance(value, bool):
                        raise ValueError(f'Missmatch in value and fluent ({f_type}) types')
                    _value = Bool(value)
                elif is_up_type_int(f_type):
                    if not isinstance(value, int):
                        raise ValueError(f'Missmatch in value and fluent ({f_type}) types')
                    _value = Int(value)
                elif is_up_type_real(f_type):
                    if not isinstance(value, (float, int)):
                        raise ValueError(f'Missmatch in value and fluent ({f_type}) types')
                    _value = get_up_real(value)
                else:
                    raise ValueError(f'Unexpected value type (value = {value})')
            else:
                _value = value

            v_type = get_up_type_as_str(_value)
            if value_applies_in_sim_effect and not _value.is_constant():
                raise ValueError(f'Only constant values can apply for simulated effects')
            if v_type != f_type:
                raise ValueError(f'Missmatch in value ({v_type}) and fluent ({f_type}) types')
        else:
            _value = value

        if timing not in self.__values.keys():
            self.__values[timing] = dict()
            self.__values_cond[timing] = dict()
        if condition is None:
            self.__values[timing][fluent] = (_value, value_applies_in_sim_effect)
        else:
            self.__values[timing][fluent] = (None, False)  # the there is a condition, the values must be set in Sim Effects callback when no conditional effects are used
            if condition not in self.__values_cond[timing].keys():
                self.__values_cond[timing][condition] = dict()
            self.__values_cond[timing][condition][fluent] = (_value, value_applies_in_sim_effect)

    def add_effects_to_action(self,
                              action: Union[InstantaneousAction, DurativeAction],
                              effects_option: EffectsOption,
                              sim_effect_cb: Union['EffectsHandler.SimEffectCallbackType', None] = None):

        """Add all registered effects to an action based on the problem effects option/setting

        Parameters
        ----------
        action : InstantaneousAction, DurativeAction
            Action
        effects_option : EffectsOption
            Problem effects option/setting
        sim_effect_cb : EffectsHandler.SimEffectCallbackType, None
            Simulated effect callback (None if not applicable, i.e., not simulated effects are needed for the given problem and problem settings).
        """

        if effects_option is EffectsOption.WITH_ONLY_SIM_EFFECTS:
            for timing, fls in self.__values.items():
                assert sim_effect_cb is not None
                if len(fls) == 0:
                    continue
                add_simulated_effect_to_action(action,
                                               SimulatedEffect(list(fls.keys()),
                                                               partial(sim_effect_cb, timing, fls)),
                                               timing)

        elif effects_option is EffectsOption.WITH_ONLY_SIM_EFFECTS_WHERE_NEEDED:
            for timing, fls in self.__values.items():
                if len(fls) == 0:
                    continue
                has_sim_effect = False
                for fl, val in fls.items():
                    if val[0] is None:
                        has_sim_effect = True
                        break
                if has_sim_effect:
                    assert sim_effect_cb is not None
                    add_simulated_effect_to_action(action,
                                                   SimulatedEffect(list(fls.keys()),
                                                                   partial(sim_effect_cb, timing, fls)),
                                                   timing)
                else:
                    added_fluents = set()
                    for cond, fls2 in self.__values_cond[timing].items():  # give priority to conditional effects
                        for fl, val in fls2.items():
                            add_effect_to_action(action, fl, val[0], timing, cond)
                            added_fluents.add(fl)
                    for fl, val in fls.items():
                        if fl not in added_fluents:
                            add_effect_to_action(action, fl, val[0], timing)

        elif effects_option is EffectsOption.WITH_NORMAL_EFFECTS_AND_SIM_EFFECTS:
            for timing, fls in self.__values.items():
                _fluents_sim_effect = list()
                _vals_sim_effect = dict()
                for fl, val in fls.items():
                    if val[0] is None:
                        _fluents_sim_effect.append(fl)
                        _vals_sim_effect[fl] = val
                    else:
                        add_effect_to_action(action, fl, val[0], timing)
                if len(_vals_sim_effect) > 0:
                    assert sim_effect_cb is not None
                    add_simulated_effect_to_action(action,
                                                   SimulatedEffect(list(_vals_sim_effect.keys()),
                                                                   partial(sim_effect_cb, timing, _vals_sim_effect)),
                                                   timing)

        elif effects_option is EffectsOption.WITH_NORMAL_EFFECTS_AND_CONDITIONAL_EFFECTS:
            for timing, fls in self.__values.items():
                added_fluents = set()
                for cond, fls2 in self.__values_cond[timing].items():
                    for fl, val in fls2.items():
                        assert(val[0] is not None)
                        add_effect_to_action(action, fl, val[0], timing, cond)
                        added_fluents.add(fl)
                for fl, val in fls.items():
                    if fl not in added_fluents:
                        assert(val[0] is not None)
                        add_effect_to_action(action, fl, val[0], timing)

        elif effects_option is EffectsOption.WITH_ONLY_NORMAL_EFFECTS:
            for timing, fls in self.__values.items():
                for fl, val in fls.items():

                    # #debug!
                    # print(f'Fluent: {fl} ; val: {val[0]} ; timing: {timing}')

                    assert (val[0] is not None)
                    add_effect_to_action(action, fl, val[0], timing)
        else:
            raise NotImplementedError()

    @staticmethod
    def append_value_to_callback_return(cb_return_values: List[FNode],
                                        sim_effect_values: Dict,
                                        fluent: FNode,
                                        value: FNode):

        """Function used to add a fluent value, if applicable,  to the list of values to be returned from a simulated effect callback

        Parameters
        ----------
        cb_return_values : List[FNode]
            Current list of values to be returned by the simulated effect callback
        sim_effect_values : Dict
            Dictionary holding the values (and value_applies_in_sim_effect) for the simulated effects
        fluent : FNode
            Fluent (with parameters) affected by the effect
        value : FNode
            Value to be added to cb_return_values.
            If the fluent value obtained from sim_effect_values is not None (i.e., the value was set when the effect was registered)
            and value_applies_in_sim_effect==True, this value will be disregarded and the initially registered value will be added instead.
        """

        if fluent not in sim_effect_values.keys():
            return
        val, value_applies_in_sim_effect = sim_effect_values.get(fluent)
        if val is None or not value_applies_in_sim_effect:
            val = value
        cb_return_values.append( val )

        # #debug!
        # print(f'Added value = {val} to fluent = {fluent}')
