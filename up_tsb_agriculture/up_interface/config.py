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

from enum import Enum, unique

ENABLE_TAMER_EXCEPTION_PARAM_REF_1 = False  # @todo apparently the exception is fixed, but the planner fails to yield a plan

DEBUG_PRINT_SIM_EFFECTS_IN_OUT = False

@unique
class EffectsOption(Enum):
    """ Enum holding the possible effects' types for a given action. """

    WITH_NORMAL_EFFECTS_AND_SIM_EFFECTS = 'WITH_NORMAL_EFFECTS_AND_SIM_EFFECTS'
    """If a normal effect is given with a proper value, this effect will be used for the respective fluent; otherwise the value for the fluent must be set via simulated effects"""

    WITH_ONLY_SIM_EFFECTS = 'WITH_ONLY_SIM_EFFECTS'
    """All effects are simulated effects"""

    WITH_ONLY_SIM_EFFECTS_WHERE_NEEDED = 'WITH_ONLY_SIM_EFFECTS_WHERE_NEEDED'
    """If all effects at a certain timing can be done without sim. effects or conditional effects, normal effects will be used; otherwise, all effects of that timing will be simulated effects"""

    WITH_ONLY_NORMAL_EFFECTS = 'WITH_ONLY_NORMAL_EFFECTS'
    """Only normal effects will be used"""

    WITH_NORMAL_EFFECTS_AND_CONDITIONAL_EFFECTS = 'WITH_NORMAL_EFFECTS_AND_CONDITIONAL_EFFECTS'
    """Only normal and conditional effects will be used. If a certain timing and fluent has a normal effect and one or more conditional effects, the conditional effects will be used"""

@unique
class PlanningType(Enum):
    """ Enum holding the supported planning types. """

    SEQUENTIAL = 'SEQUENTIAL'
    """Sequential/classical planning"""

    TEMPORAL = 'TEMPORAL'
    """Temporal planning"""

@unique
class SiloPlanningType(Enum):
    """ Enum holding the options for silo-planning. """

    WITHOUT_SILO_ACCESS_AVAILABILITY = 'WITHOUT_SILO_ACCESS_AVAILABILITY'
    """ The planner will not check if a silo access/unloading point is being used by another machine (i.e., more than one transport vehicle may unload simultaneously at the same access point). """

    WITH_SILO_ACCESS_AVAILABILITY = 'WITH_SILO_ACCESS_AVAILABILITY'
    """ The planner will check if a silo access/unloading point is being used by another machine (i.e., only one transport vehicle may unload at at time at an access point). """

    WITH_SILO_ACCESS_CAPACITY_AND_COMPACTION = 'WITH_SILO_ACCESS_CAPACITY_AND_COMPACTION'
    """ The problem will include all silo-planning, including compaction. The planner will check if a silo access/unloading point availability both in terms of it being used by a transport vehicle and the available capacity. """

@unique
class TemporalOptimizationSetting(Enum):
    """ Enum holding the supported optimization options for temporal planning. """

    NONE = 'NONE'
    """No optimization"""

    MAKESPAN = 'MAKESPAN'
    """Makespan (optimize plan duration)"""

@unique
class NumericFluentsBoundsOption(Enum):
    """ Enum holding the possible bound options for the numeric fluents. """

    WITHOUT_BOUNDS = 'WITHOUT_BOUNDS'
    """All numeric fluents will be set without bounds"""

    WITH_DEFAULT_BOUNDS = 'WITH_DEFAULT_BOUNDS'
    """The default/universal fluents bounds will be used (some fluents might have no lower and/or upper bounds)"""

    WITH_PROBLEM_SPECIFIC_BOUNDS = 'WITH_PROBLEM_SPECIFIC_BOUNDS'
    """(most) numeric fluents will be added to the problem with defined lower/upper bounds based on statistics and estimations of the fluent values for the specific problem"""


class SequentialOptimizationSettings:
    """ Class holding the optimization options for sequential planning (to be used with MinimizeExpressionOnFinalState metrics). """

    def __init__(self):
        self.k_harv_waiting_time: float = 0.0
        """ Factor applied to the sum of harvester waiting times. """

        self.k_tv_waiting_time: float = 0.0
        """ Factor applied to the sum of transport vehicle waiting times. """

    def has_optimization(self):
        """ Check if there is any optimization to be made. """

        return self.k_harv_waiting_time > 1e-9 \
            or self.k_tv_waiting_time > 1e-9


class EffectsSettings:
    """ Class holding the effect-settings for the different problem actions. """

    # def __init__(self, default: EffectsOption = EffectsOption.WITH_NORMAL_EFFECTS_AND_SIM_EFFECTS):
    def __init__(self, default: EffectsOption = EffectsOption.WITH_ONLY_SIM_EFFECTS):

        # self.do_overload = default
        self.do_overload = default if default is not EffectsOption.WITH_ONLY_NORMAL_EFFECTS or ENABLE_TAMER_EXCEPTION_PARAM_REF_1 \
            else EffectsOption.WITH_NORMAL_EFFECTS_AND_SIM_EFFECTS  # @todo because of ENABLE_TAMER_EXCEPTION_PARAM_REF_1, the planner fails to yield a plan
        """ Effect-settings for the 'do_overload' actions in temporal planning. """

        self.drive_harv_to_field = default
        """ Effect-settings for the 'drive_harv_from_xxx_to_field' actions. """

        self.reserve_overload = default
        """ Effect-settings for the 'reserve_overload' actions in temporal planning and the 'overload' actions in sequential planning. """

        self.drive_to_silo = default
        """ Effect-settings for the 'drive_tv_from_xxx_to_silo' actions. """

        self.general = default
        """ Effect-settings for the actions which have no specific effect-settings. """


class ActionsDecompositionSettings:
    """ Class holding the options to decompose some of the problem actions.

    If a decomposition-setting for a given action is set to True, the action might be decomposed into 2 or more 'more specific' actions.
    For example, an action 'do_overload' could be decomposed into 'do_overload_field_finished' and 'do_overload_field_not_finished'.
    This decomposition allows the problem encoder to generate actions that use only normal (non-simulated, non-conditional) effects.
    For some actions, it is not possible to have EffectsOption.WITH_ONLY_NORMAL_EFFECTS without setting the corresponding decomposition-setting to True
    """

    def __init__(self, default: bool = False):

        self.do_overload = default
        """ Decomposition-settings for the 'do_overload' actions in temporal planning."""

        # For reserve_overload actions
        self.reserve_overload = default
        """ Decomposition-settings for the 'reserve_overload' actions in temporal planning."""

        self.general = default
        """ Decomposition-settings for the actions which have no specific decomposition-settings (if applicable). """


class ControlWindowsSettings:
    """ Class holding the options for control time-windows in temporal planning.

    The control windows are used to enable some actions for a shot time and then disable them, forcing the planner to plan an action within this time-frame
    The control windows are given in seconds, and are disregarded if they are <= 0
    """

    def __init__(self):
        self.enable_driving_opening_time: float = 1.0  # 0.05
        """ Enable the start of driving of a machine ('drive_tv_to_field' and 'drive_to_silo' actions) for a given time-window (in seconds, disregarded if <= 0). """

        self.enable_driving_tvs_to_field_opening_time: float = 1.0  # 0.05
        """ Enable the start of driving of a transport vehicle to a field ('drive_tv_to_field' actions) for a given time-window (in seconds, disregarded if <= 0). """

        self.enable_arriving_tvs_in_field_opening_time: float = -1.0  # 0.05
        """ Enable the arriving of a transport vehicle to a field ('drive_tv_to_field' actions) for a given time-window (in seconds, disregarded if <= 0). """

        self.enable_overload_opening_time: float = -0.05
        """ Enable the starting of overload ('do_overload' actions) for a given harvester for a given time-window (in seconds, disregarded if <= 0). """

    def disable_all(self):
        """ Disable all control windows """

        self.enable_driving_opening_time = -1
        self.enable_driving_tvs_to_field_opening_time = -1
        self.enable_arriving_tvs_in_field_opening_time = -1
        self.enable_overload_opening_time = -1


class CostWindowsSettings:
    """ Class holding the options for cost time-windows in temporal planning.

    The cost windows are used to handle/activate heuristic costs within the give time-frame, e.g., only generating a cost if an action was not planned withing the given window.
    The cost windows are given in seconds, and are disregarded if they are <= 0
    """

    def __init__(self):
        self.waiting_overload_opening_time: float = 0.1
        """ The cost corresponding to a transport vehicle waiting to overload will be 'activated' if a corresponding overload action is not planned within this time-frame (in seconds, disregarded if <= 0) """

        self.waiting_drive_opening_time: float = 0.1
        """ The cost corresponding to a machine waiting to drive will be 'activated' if a corresponding 'drive' action is not planned within this time-frame (in seconds, disregarded if <= 0) """

        self.waiting_drive_from_silo_opening_time: float = -1
        """ The cost corresponding to a transport vehicle waiting to drive from a silo will be 'activated' if a corresponding 'drive_tv_to_field' action is not planned within this time-frame (in seconds, disregarded if <= 0) """

        self.waiting_harvest_opening_time: float = 0.1
        """ The cost corresponding to a harvester waiting to harvest/overload will be 'activated' if a corresponding overload action is not planned within this time-frame (in seconds, disregarded if <= 0) """

        self.use_old_implementation_waiting_overload = False #@todo Remove when the tv_waiting_to_overload_id approach is working
        self.use_old_implementation_waiting_drive = True #@todo Remove when the tv_waiting_to_drive_id approach is working

    def disable_all(self):
        """ Disable all cost windows """

        self.waiting_overload_opening_time = -1
        self.waiting_drive_opening_time = -1
        self.waiting_drive_from_silo_opening_time = -1
        self.waiting_harvest_opening_time = -1


class GeneralProblemSettings:
    """ Class holding the problem settings. """

    def __init__(self):
        self.id_undef: int = -12345
        """ Default value for undefined ids """

        self.planning_type = PlanningType.TEMPORAL
        """ Planning type """

        self.with_harv_conditions_and_effects_at_tv_arrival = False  # True   # currently with True the planner/heuristics are not working well
        """ If set to True, the conditions and effects corresponding to 'reserve_overload' actions in temporal planning 
        will be set so that they are checked/applied at the time the transport vehicle arrives to the field; 
        otherwise they will be checked/applied at the time the transport vehicle starts driving to the field.
        The correct setting is True, to allow the planning of transport vehicles to start driving to a field 
        before the harvester is assigned to that field, with the condition that, by the time the transport vehicle 
        arrives to the field, the harvester has been already assigned to the field """

        self.with_drive_to_field_exit = False
        """ If set to False, the transport vehicle and the harvester (if it is the last overload) will be sent 
        to a field exit within the 'do_overload' actions; otherwise, the 'do_overload' actions will not include
        the transit to a field exit and 'drive_xxx_to_field_exit' actions will be used to plan those transits """

        self.silo_planning_type = SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY
        """ Type of silo-planning """

        self.numeric_fluent_bounds_option = NumericFluentsBoundsOption.WITHOUT_BOUNDS
        """ Option to set the bounds of the numeric fluents """

        self.infield_transit_duration_to_field_access = 30
        """ Default duration of in-field transit (from a field access point to an overload-start point, 
        and from an overload-end point to a field exit point) """

        self.effects_settings = EffectsSettings()
        """ Effect-settings for the problem actions """

        self.action_decomposition_settings = ActionsDecompositionSettings()
        """ Decomposition-settings for the problem actions """

        self.control_windows = ControlWindowsSettings()
        """ Control-windows' settings for the problem """

        self.cost_windows = CostWindowsSettings()
        """ Cost-windows' settings for the problem """

        self.temporal_optimization_setting = TemporalOptimizationSetting.NONE
        """ Optimization settings for temporal planning """

        self.sequential_optimization_settings = SequentialOptimizationSettings()
        """ Optimization settings for sequential/classical planning """


default_problem_settings = GeneralProblemSettings()
""" Default problem settings """

gps = default_problem_settings # alias
""" Default problem settings (alias) """

