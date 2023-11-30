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

from enum import Enum, auto, unique
import up_interface.types as upt
from up_interface import config as conf
from up_interface.fluents import FluentsManagerBase
from up_interface.fluents import FluentNames as fn
from up_interface.actions.actions_helper import *
from up_interface.types_helper import *


class ActionDoOverload(DurativeAction):
    """ Durative action related to 'harvest and do overload from a harvester to a transport vehicle in a given field' with optional 'drive machine(s) to a field exit point when finished'. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        DO_OVERLOAD_AND_EXIT = 'do_overload_and_exit'
        DO_OVERLOAD_AND_EXIT_FINISHED = 'do_overload_and_exit_finished'
        DO_OVERLOAD = 'do_overload'
        DO_OVERLOAD_FINISHED = 'do_overload_finished'

    @unique
    class ParameterNames(Enum):
        """ Enum with the possible action parameters this action can have. """

        FIELD = 'field'
        TV = 'tv'
        HARV = 'harv'
        FIELD_EXIT_TV = 'field_exit_tv'
        FIELD_EXIT_HARV = 'field_exit_harv'

    class ConditionsOption(Enum):
        """ Enum with the conditions used to create the specific action. """

        GENERAL_CASE = auto()
        """ Do not decompose the 'do overload' action into sub-actions corresponding to 'transport vehicle full/not full' and 'field finished / not finished'. The general action will add the corresponding checks and conditions'. """

        TV_FULL_AND_HARV_FINISHED = auto()
        """ A (sub) action will be created for the specific case where the transport vehicle is full after the overload and the field is finished. """

        TV_FULL_AND_HARV_NOT_FINISHED = auto()
        """ A (sub) action will be created for the specific case where the transport vehicle is full after the overload and the field is not finished. """

        TV_NOT_FULL_AND_HARV_FINISHED = auto()
        """ A (sub) action will be created for the specific case where the transport vehicle is not full after the overload and the field is finished. """

    EPS_MASS_FIELD_FINISHED = 0.5
    """ If the remaining yield_mass in the field is >= this value, the field will be considered as finished. """

    def __init__(self,
                 fluents_manager: FluentsManagerBase,
                 no_harv_object: Object,
                 no_field_object: Object,
                 no_field_access_object: Optional[Object],
                 include_field_exit: bool,
                 case_field_finished: Optional[bool],  # if None -> General case
                 problem_settings: conf.GeneralProblemSettings):

        """ Creates the action based on the initialization parameters.

        If case_field_finished is None, a general action for 'do overload' will be created.
        Otherwise, the 'do overload' will be decomposed into 'do overload (case: field finished after overload) '
        and 'do overload (case: field not finished after overload)'

        Parameters
        ----------
        fluents_manager : FluentsManagerBase
            Fluents manager used to create the problem
        no_harv_object : Object
            Problem object corresponding to 'no harvester'
        no_field_object : Object
            Problem object corresponding to 'no field'
        no_field_access_object : Object
            Problem object corresponding to 'no field access'
        include_field_exit : bool
            Flag stating whether driving of the machine(s) to a field exit after overload must be included in the action.
        case_field_finished : bool, None
            Flag stating whether the action must be created for the specific case that the field will be finished after this overload or for the specific case that the field will not be finished. If None, the action for the general case will be created.
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        """

        effects_option = problem_settings.effects_settings.do_overload

        if effects_option is conf.EffectsOption.WITH_ONLY_NORMAL_EFFECTS \
                and case_field_finished is None:
            raise ValueError(
                'EffectsOption.WITH_ONLY_NORMAL_EFFECTS can only be achieved with case_field_finished != None')

        params = {ActionDoOverload.ParameterNames.FIELD.value: upt.Field,
                  ActionDoOverload.ParameterNames.TV.value: upt.TransportVehicle,
                  ActionDoOverload.ParameterNames.HARV.value: upt.Harvester}

        if include_field_exit:
            params[ActionDoOverload.ParameterNames.FIELD_EXIT_TV.value] = upt.FieldAccess
            params[ActionDoOverload.ParameterNames.FIELD_EXIT_HARV.value] = upt.FieldAccess

            action_name = ActionDoOverload.ActionNames.DO_OVERLOAD_AND_EXIT_FINISHED.value \
                if case_field_finished \
                else ActionDoOverload.ActionNames.DO_OVERLOAD_AND_EXIT.value
        else:
            action_name = ActionDoOverload.ActionNames.DO_OVERLOAD_FINISHED.value \
                                if case_field_finished \
                                else ActionDoOverload.ActionNames.DO_OVERLOAD.value

        DurativeAction.__init__(self, action_name, **params)

        # ------------parameters------------

        field = self.parameter(ActionDoOverload.ParameterNames.FIELD.value)
        tv = self.parameter(ActionDoOverload.ParameterNames.TV.value)
        harv = self.parameter(ActionDoOverload.ParameterNames.HARV.value)

        if include_field_exit:
            field_exit_tv = self.parameter(ActionDoOverload.ParameterNames.FIELD_EXIT_TV.value)
            field_exit_harv = self.parameter(ActionDoOverload.ParameterNames.FIELD_EXIT_HARV.value)

        # ------------fluents to be used------------

        field_area_per_yield_mass = fluents_manager.get_fluent(fn.field_area_per_yield_mass)
        field_yield_mass_after_reserve = fluents_manager.get_fluent(fn.field_yield_mass_after_reserve)
        harv_overload_count = fluents_manager.get_fluent(fn.harv_overload_count)
        harv_overload_id = fluents_manager.get_fluent(fn.harv_overload_id)
        harv_working_time_per_area = fluents_manager.get_fluent(fn.harv_working_time_per_area)

        tv_mass_to_overload = fluents_manager.get_fluent(fn.tv_mass_to_overload)

        # ----------temporal parameters-----------

        delta_time_after_exit = None
        if include_field_exit:
            _duration_to_field_exit = max(0.0,
                                          problem_settings.infield_transit_duration_to_field_access)  # @todo infield transit to field exit (fixed at the moment)
            delta_time_after_exit = 0.0
            delta_time_after_exit = max(delta_time_after_exit, problem_settings.cost_windows.waiting_drive_opening_time)
            delta_time_after_exit = max(delta_time_after_exit,
                                        problem_settings.control_windows.enable_driving_opening_time)
            delta_time_after_exit = max(delta_time_after_exit,
                                        problem_settings.control_windows.enable_driving_tvs_to_field_opening_time)
            delta_time_after_exit = max(delta_time_after_exit,
                                        problem_settings.control_windows.enable_overload_opening_time - _duration_to_field_exit)
            delta_time_after_exit = max(delta_time_after_exit,
                                        problem_settings.control_windows.enable_arriving_tvs_in_field_opening_time - _duration_to_field_exit)

            delta_time_after_overload = delta_time_after_exit + _duration_to_field_exit
        else:
            delta_time_after_overload = 0.0
            delta_time_after_overload = max(delta_time_after_overload,
                                            problem_settings.cost_windows.waiting_drive_opening_time)
            delta_time_after_overload = max(delta_time_after_overload,
                                            problem_settings.control_windows.enable_driving_opening_time)
            delta_time_after_overload = max(delta_time_after_overload,
                                            problem_settings.control_windows.enable_overload_opening_time)
            delta_time_after_overload = max(delta_time_after_overload,
                                            problem_settings.control_windows.enable_arriving_tvs_in_field_opening_time)

        overload_duration = Times(
            Real(Fraction('1.2')),  # @todo: to account for non-working transit (temporary)
            Times(  # time needed by the harvester to cover the harvesting area
                harv_working_time_per_area(harv),
                Times(  # area to cover
                    tv_mass_to_overload(tv),
                    field_area_per_yield_mass(field)
                )
            )
        )
        action_duration = Plus(overload_duration, delta_time_after_overload)

        timing_end_overload = get_timing_before_end_timing(action_duration, delay=delta_time_after_overload)
        timing_disable_overload = get_timing_before_end_timing(action_duration,
                                                               delay=(delta_time_after_overload -
                                                                      max(0.0,
                                                                          problem_settings.control_windows.enable_overload_opening_time)))
        timing_disable_arrival = get_timing_before_end_timing(action_duration,
                                                              delay=(delta_time_after_overload -
                                                                     max(0.0,
                                                                         problem_settings.control_windows.enable_arriving_tvs_in_field_opening_time)))
        if include_field_exit:
            timing_exit_field = get_timing_before_end_timing(action_duration, delay=delta_time_after_exit)
            timing_disable_driving = get_timing_before_end_timing(action_duration,
                                                                  delay=(delta_time_after_exit -
                                                                         max(0.0,
                                                                             problem_settings.control_windows.enable_driving_opening_time)))
            timing_disable_driving_2 = get_timing_before_end_timing(action_duration,
                                                                    delay=(delta_time_after_exit -
                                                                           max(0.0,
                                                                               problem_settings.control_windows.enable_driving_tvs_to_field_opening_time)))
            timing_enable_waiting_drive = get_timing_before_end_timing(action_duration,
                                                                       delay=(delta_time_after_exit -
                                                                              max(0.0,
                                                                                  problem_settings.cost_windows.waiting_drive_opening_time)))
        else:
            timing_exit_field = timing_disable_driving_2 = None
            timing_disable_driving = get_timing_before_end_timing(action_duration,
                                                                  delay=(delta_time_after_overload -
                                                                         max(0.0,
                                                                             problem_settings.control_windows.enable_driving_opening_time)))
            timing_enable_waiting_drive = get_timing_before_end_timing(action_duration,
                                                                       delay=(delta_time_after_overload -
                                                                              max(0.0,
                                                                                  problem_settings.cost_windows.waiting_drive_opening_time)))

        set_duration_to_action(self, action_duration)

        # condition applied at StartTiming!
        condition_finished_field = And(
            LT(
                field_yield_mass_after_reserve(field),
                get_up_real(ActionDoOverload.EPS_MASS_FIELD_FINISHED)
            ),
            Equals(
                Plus(harv_overload_id(harv), 1),
                harv_overload_count(harv)
            )
        )

        self.__add_conditions(fluents_manager=fluents_manager,
                              no_field_object=no_field_object,
                              no_field_access_object=no_field_access_object,
                              no_harv_object=no_harv_object,
                              condition_finished_field=condition_finished_field,
                              include_field_exit=include_field_exit,
                              case_field_finished=case_field_finished)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings,
                           case_field_finished=case_field_finished,
                           include_field_exit=include_field_exit,
                           no_field_object=no_field_object,
                           no_field_access_object=no_field_access_object,
                           condition_finished_field=condition_finished_field,
                           timing_end_overload=timing_end_overload,
                           timing_disable_overload=timing_disable_overload,
                           timing_disable_arrival=timing_disable_arrival,
                           timing_exit_field=timing_exit_field,
                           timing_disable_driving=timing_disable_driving,
                           timing_disable_driving_2=timing_disable_driving_2,
                           timing_enable_waiting_drive=timing_enable_waiting_drive)

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase,
                         no_field_object,
                         no_field_access_object,
                         no_harv_object,
                         condition_finished_field,
                         include_field_exit,
                         case_field_finished):

        """ Add the conditions to the action. """

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)
        field_id = fluents_manager.get_fluent(fn.field_id)
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_access_field_id = fluents_manager.get_fluent(fn.field_access_field_id)

        harv_at_field = fluents_manager.get_fluent(fn.harv_at_field)
        tv_at_field = fluents_manager.get_fluent(fn.tv_at_field)
        harv_enabled_to_overload = fluents_manager.get_fluent(fn.harv_enabled_to_overload)

        harv_free = fluents_manager.get_fluent(fn.harv_free)
        harv_overload_count = fluents_manager.get_fluent(fn.harv_overload_count)
        harv_overload_id = fluents_manager.get_fluent(fn.harv_overload_id)
        harv_overloading = fluents_manager.get_fluent(fn.harv_overloading)

        tv_overload_id = fluents_manager.get_fluent(fn.tv_overload_id)

        # ------------parameters------------

        field = self.parameter(ActionDoOverload.ParameterNames.FIELD.value)
        tv = self.parameter(ActionDoOverload.ParameterNames.TV.value)
        harv = self.parameter(ActionDoOverload.ParameterNames.HARV.value)

        field_exit_tv = field_exit_harv = None
        if include_field_exit:
            field_exit_tv = self.parameter(ActionDoOverload.ParameterNames.FIELD_EXIT_TV.value)
            field_exit_harv = self.parameter(ActionDoOverload.ParameterNames.FIELD_EXIT_HARV.value)

        # ------------conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action(self, Not(planning_failed()), StartTiming())

        # the objects are valid
        add_precondition_to_action(self, Not(Equals(field, no_field_object)), StartTiming())
        add_precondition_to_action(self, Not(Equals(harv, no_harv_object)), StartTiming())
        if include_field_exit:
            add_precondition_to_action(self, Not(Equals(field_exit_tv, no_field_access_object)), StartTiming())
            # add_precondition_to_action(self, Not(Equals(field_exit_harv, no_field_access_object)), StartTiming())
            add_precondition_to_action(self,
                                       Iff(
                                           Equals(field_exit_harv, no_field_access_object),
                                           Not(condition_finished_field)
                                       ),
                                       StartTiming())

        # the field exit is an access point of the field
        if include_field_exit:
            add_precondition_to_action(self, Equals(field_id(field), field_access_field_id(field_exit_tv)),
                                       StartTiming())
            # add_precondition_to_action( self, Equals( field_id(field), field_access_field_id(field_exit_harv) ) , StartTiming() )
            add_precondition_to_action(self,
                                       Iff(
                                           Equals(field_id(field), field_access_field_id(field_exit_harv)),
                                           condition_finished_field
                                       ),
                                       StartTiming())

        # check if the harvester is available
        add_precondition_to_action(self, harv_free(harv), StartTiming())

        # the harvester is not overloading
        add_precondition_to_action(self,
                                   Not(harv_overloading(harv)),
                                   StartTiming())

        # the harvester has a planned overload
        add_precondition_to_action(self,
                                   GT(harv_overload_count(harv), 0),
                                   StartTiming())

        # the planned overload of the TV is the same as the next harv overload
        add_precondition_to_action(self,
                                   Equals(tv_overload_id(tv), Plus(harv_overload_id(harv), 1)),
                                   StartTiming())

        # the field has a harvester assigned to it
        add_precondition_to_action(self, Equals(field_harvester(field), harv), StartTiming())

        # the machines are currently in the field
        add_precondition_to_action(self,
                                   Equals(harv_at_field(harv), field),
                                   StartTiming())
        add_precondition_to_action(self,
                                   Equals(tv_at_field(tv), field),
                                   StartTiming())

        if case_field_finished is not None:
            add_precondition_to_action(self,
                                       condition_finished_field if case_field_finished else Not(
                                           condition_finished_field),
                                       StartTiming())

        if harv_enabled_to_overload is not None:
            # @todo: apparently the SIGSEGV caused when setting gps.control_windows.enable_overload_opening_time is triggered in Plus( harv_enabled_to_overload(harv), 1 )  (if 1 is changed to 0 there is no SIGSEGV)
            add_precondition_to_action(self,
                                       # GE(harv_enabled_to_overload(harv), 0),
                                       And(
                                           GT(harv_enabled_to_overload(harv), 0),
                                           # GE( harv_enabled_to_overload(harv), 0 ),
                                           Equals(tv_overload_id(tv), harv_enabled_to_overload(harv))
                                       ),
                                       StartTiming())

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings: conf.GeneralProblemSettings,
                      case_field_finished,
                      include_field_exit,
                      no_field_object,
                      no_field_access_object,
                      condition_finished_field,
                      timing_end_overload,
                      timing_disable_overload,
                      timing_disable_arrival,
                      timing_exit_field,
                      timing_disable_driving,
                      timing_disable_driving_2,
                      timing_enable_waiting_drive):

        """ Add the effects to the action. """

        effects_option = problem_settings.effects_settings.do_overload

        # ------------parameters------------

        field = self.parameter(ActionDoOverload.ParameterNames.FIELD.value)
        tv = self.parameter(ActionDoOverload.ParameterNames.TV.value)
        harv = self.parameter(ActionDoOverload.ParameterNames.HARV.value)

        field_exit_tv = field_exit_harv = None
        if include_field_exit:
            field_exit_tv = self.parameter(ActionDoOverload.ParameterNames.FIELD_EXIT_TV.value)
            field_exit_harv = self.parameter(ActionDoOverload.ParameterNames.FIELD_EXIT_HARV.value)

        # ------------fluents to be used------------

        total_harvested_mass = fluents_manager.get_fluent(fn.total_harvested_mass)
        total_harvested_mass_planned = fluents_manager.get_fluent(fn.total_harvested_mass_planned)
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        field_yield_mass_unharvested = fluents_manager.get_fluent(fn.field_yield_mass_unharvested)
        field_yield_mass_after_reserve = fluents_manager.get_fluent(fn.field_yield_mass_after_reserve)
        field_yield_mass_minus_planned = fluents_manager.get_fluent(fn.field_yield_mass_minus_planned)

        harv_free = fluents_manager.get_fluent(fn.harv_free)
        tv_free = fluents_manager.get_fluent(fn.tv_free)
        harv_at_field = fluents_manager.get_fluent(fn.harv_at_field)
        harv_at_field_access = fluents_manager.get_fluent(fn.harv_at_field_access)
        tv_at_field = fluents_manager.get_fluent(fn.tv_at_field)
        tv_at_field_access = fluents_manager.get_fluent(fn.tv_at_field_access)
        harv_enabled_to_drive_to_loc = fluents_manager.get_fluent(fn.harv_enabled_to_drive_to_loc)
        tv_enabled_to_drive_to_field = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_field)
        tv_enabled_to_drive_to_silo = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_silo)
        harv_enabled_to_overload = fluents_manager.get_fluent(fn.harv_enabled_to_overload)
        harv_waiting_to_harvest = fluents_manager.get_fluent(fn.harv_waiting_to_harvest)
        harv_enabled_to_drive_to_field_exit = fluents_manager.get_fluent(fn.harv_enabled_to_drive_to_field_exit)
        tv_enabled_to_drive_to_field_exit = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_field_exit)
        tvs_all_enabled_to_arrive_in_field = fluents_manager.get_fluent(fn.tvs_all_enabled_to_arrive_in_field)

        harv_overload_count = fluents_manager.get_fluent(fn.harv_overload_count)
        harv_overload_id = fluents_manager.get_fluent(fn.harv_overload_id)
        harv_overloading = fluents_manager.get_fluent(fn.harv_overloading)

        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_overload_id = fluents_manager.get_fluent(fn.tv_overload_id)
        tv_mass_to_overload = fluents_manager.get_fluent(fn.tv_mass_to_overload)
        tv_ready_to_overload = fluents_manager.get_fluent(fn.tv_ready_to_overload)
        tv_waiting_to_overload_id = fluents_manager.get_fluent(fn.tv_waiting_to_overload_id)
        tv_waiting_to_overload = fluents_manager.get_fluent(fn.tv_waiting_to_overload)
        tv_ready_to_drive = fluents_manager.get_fluent(fn.tv_ready_to_drive)
        tv_waiting_to_drive_id = fluents_manager.get_fluent(fn.tv_waiting_to_drive_id)
        tvs_waiting_to_drive_ref_count = fluents_manager.get_fluent(fn.tvs_waiting_to_drive_ref_count)
        tv_waiting_to_drive = fluents_manager.get_fluent(fn.tv_waiting_to_drive)

        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        tv_can_unload = fluents_manager.get_fluent(fn.tv_can_unload)
        tv_can_load = fluents_manager.get_fluent(fn.tv_can_load)

        # ------------effects------------

        _capacity_threshold = 0.8

        def sim_effects_cb(timing: Timing,
                           effects_values: EffectsHandler.FluentValuesDictType,
                           problem: Problem,
                           state: State,
                           actual_params: Dict[Parameter, FNode]) -> List[FNode]:

            """ Simulated effect callback for the action for the specified timing.

            Parameters
            ----------
            timing : Timing
                Timing of the effect
            effects_values : EffectsHandler.FluentValuesDictType
                Dictionary containing the fluents related to the simulated effect at the given timing and their values (value, value_applies_in_sim_effect)
            problem : Problem
                UP problem
            state : State
                Current UP state
            actual_params : Dict[Parameter, FNode]
                Action actual parameters

            Returns
            -------
            effect_values : List[FNode]
                List with the computed effect values for the given fluents and specific timing.

            """

            _field = actual_params.get(field)
            _harv = actual_params.get(harv)
            _tv = actual_params.get(tv)

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'+++++++++++++++++++ [state {id(state)}] ::  {self.name} sim effect [{timing}] - {_tv} - {_field} - {_harv}')

            _field_yield_mass_unharvested = float(state.get_value(field_yield_mass_unharvested(_field)).constant_value())
            _field_yield_mass_minus_planned = float(state.get_value(field_yield_mass_minus_planned(_field)).constant_value())
            _field_yield_mass_after_reserve = float(state.get_value(field_yield_mass_after_reserve(_field)).constant_value())
            _harv_overload_count = int(state.get_value(harv_overload_count(_harv)).constant_value())
            _harv_overload_id = int(state.get_value(harv_overload_id(_harv)).constant_value())
            _total_harvested_mass = float(state.get_value(total_harvested_mass()).constant_value())
            _total_harvested_mass_planned = float(state.get_value(total_harvested_mass_planned()).constant_value())
            _tv_mass_to_overload = float(state.get_value(tv_mass_to_overload(_tv)).constant_value())
            _tv_bunker_mass = float(state.get_value(tv_bunker_mass(_tv)).constant_value())

            _harv_finished = _field_exit_harv = _field_exit_tv = _no_field_access_object = None
            _tvs_waiting_to_drive_ref_count = _tv_ready_to_drive = None

            if tv_ready_to_drive is not None:
                _tv_ready_to_drive = int(state.get_value(tv_ready_to_drive(_tv)).constant_value())

            if tvs_waiting_to_drive_ref_count is not None:
                _tvs_waiting_to_drive_ref_count = int(
                    state.get_value(tvs_waiting_to_drive_ref_count()).constant_value())

            _no_field_object = ObjectExp(problem.object(no_field_object.name))

            if timing == StartTiming():
                _harv_overload_id = _harv_overload_id + 1

                if _field_yield_mass_after_reserve < ActionDoOverload.EPS_MASS_FIELD_FINISHED and _harv_overload_id == _harv_overload_count:  # last overload
                    _harv_overload_count = -1
                    _harv_overload_id = -1

                _harv_finished = _harv_overload_count < 0

            elif include_field_exit:
                _field_exit_harv = actual_params.get(field_exit_harv)
                _field_exit_tv = actual_params.get(field_exit_tv)

                _no_field_access_object = ObjectExp(problem.object(no_field_access_object.name))

                _harv_finished = _harv_overload_count < 0

            _harv_waiting_to_harvest = (problem_settings.cost_windows.waiting_harvest_opening_time is not None
                                        and problem_settings.cost_windows.waiting_harvest_opening_time > 0.0
                                        and _harv_overload_count >= 0)

            ret_vals = []

            # #debug
            # print(f'... _tv_mass_to_overload [{timing}] = {_tv_mass_to_overload}')

            for fl, val in effects_values.items():
                # #debug
                # print(f'... checking fluent {fl}')

                if val[0] is not None and val[1]:  # give priority to values that were set already
                    # #debug
                    # print(f'... {fl} = {val[0]}')

                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0])
                    continue

                # overload
                if fl is harv_overload_count(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_harv_overload_count))
                elif fl is harv_overload_id(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_harv_overload_id))
                elif fl is tv_bunker_mass(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_tv_bunker_mass + _tv_mass_to_overload))
                elif fl is field_harvested(field):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Bool(_harv_overload_count < 0))
                elif fl is field_yield_mass_unharvested(field):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(max(0.0, _field_yield_mass_unharvested - _tv_mass_to_overload)))
                elif fl is field_yield_mass_minus_planned(field):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(max(0.0, _field_yield_mass_minus_planned - _tv_mass_to_overload)))
                elif harv_waiting_to_harvest is not None and fl is harv_waiting_to_harvest(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Bool(_harv_waiting_to_harvest))
                elif fl is total_harvested_mass():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(
                                                                       _total_harvested_mass + _tv_mass_to_overload))
                elif fl is total_harvested_mass_planned():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(
                                                                       _total_harvested_mass_planned + _tv_mass_to_overload))
                elif harv_enabled_to_overload is not None and fl is harv_enabled_to_overload(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_harv_overload_id + 1))
                elif fl is tv_overload_id(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(-1))
                elif fl is tv_mass_to_overload(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(0))

                elif fl is harv_at_field(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _no_field_object if _harv_finished else _field)
                elif fl is harv_at_field_access(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _field_exit_harv if _harv_finished else _no_field_access_object)
                elif fl is tv_at_field(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _no_field_object)
                elif fl is tv_at_field_access(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _field_exit_tv)
                elif fl is tv_can_load(tv):
                    _tv_bunker_mass = float(state.get_value(tv_bunker_mass(_tv)).constant_value())
                    _tv_total_capacity_mass = float(state.get_value(tv_total_capacity_mass(_tv)).constant_value())
                    _tv_can_load = (_tv_bunker_mass / _tv_total_capacity_mass) < _capacity_threshold
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Bool(_tv_can_load))
                elif harv_enabled_to_drive_to_loc is not None and fl is harv_enabled_to_drive_to_loc(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Bool(_harv_finished))

                # end of overload or field exit
                elif tvs_waiting_to_drive_ref_count is not None and \
                        fl is tv_waiting_to_drive_id(tv) \
                        and timing == timing_enable_waiting_drive:
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_tv_ready_to_drive * _tvs_waiting_to_drive_ref_count))  # tv_waiting_to_drive_id(tv)
                elif tv_waiting_to_drive_id is not None and \
                        fl is tvs_waiting_to_drive_ref_count() \
                        and timing == timing_enable_waiting_drive:
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_tv_ready_to_drive + _tvs_waiting_to_drive_ref_count))  # tvs_waiting_to_drive_ref_count()

                # unexpected fluent
                else:
                    raise ValueError(f'Unexpected fluent {fl} in simulated effect')

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'------------------- {self.name} sim effect [{timing}] - {_tv} - {_field} - {_harv}')

            return ret_vals

        effects_handler = EffectsHandler()

        effects_handler.add(timing=StartTiming(), fluent=harv_overloading(harv), value=Bool(True),
                            value_applies_in_sim_effect=True)
        effects_handler.add(timing=timing_end_overload, fluent=harv_overloading(harv), value=Bool(False),
                            value_applies_in_sim_effect=True)
        effects_handler.add(timing=timing_end_overload, fluent=tv_overload_id(tv), value=Int(-1),
                            value_applies_in_sim_effect=True)
        effects_handler.add(timing=StartTiming(),
                            fluent=field_yield_mass_minus_planned(field),
                            value=Minus(field_yield_mass_minus_planned(field), tv_mass_to_overload(tv)),
                            value_applies_in_sim_effect=False)
        effects_handler.add(timing=timing_end_overload,
                            fluent=field_yield_mass_unharvested(field),
                            value=Minus(field_yield_mass_unharvested(field), tv_mass_to_overload(tv)),
                            value_applies_in_sim_effect=False)

        effects_handler.add(timing=StartTiming(), fluent=harv_free(harv), value=Bool(False),
                            value_applies_in_sim_effect=True)
        effects_handler.add(timing=timing_exit_field if include_field_exit else timing_end_overload,
                            fluent=harv_free(harv), value=Bool(True), value_applies_in_sim_effect=True)

        effects_handler.add(timing=StartTiming(), fluent=tv_free(tv), value=Bool(False),
                            value_applies_in_sim_effect=True)
        effects_handler.add(timing=timing_exit_field if include_field_exit else timing_end_overload,
                            fluent=tv_free(tv), value=Bool(True), value_applies_in_sim_effect=True)

        if harv_enabled_to_overload is not None:
            # enable/disable the overloading window in case there is a tv waiting to overload
            effects_handler.add(timing=timing_end_overload, fluent=harv_enabled_to_overload(harv),
                                value=Plus(harv_overload_id(harv), 1),
                                value_applies_in_sim_effect=False)  # @note: the harv_overload_id was already increased/reset at StartTiming
            effects_handler.add(timing=timing_disable_overload, fluent=harv_enabled_to_overload(harv), value=Int(0),
                                value_applies_in_sim_effect=True)

        if harv_waiting_to_harvest is not None:
            effects_handler.add(timing=StartTiming(), fluent=harv_waiting_to_harvest(harv), value=Bool(False),
                                value_applies_in_sim_effect=True)

        if tvs_all_enabled_to_arrive_in_field is not None:
            effects_handler.add(timing=timing_end_overload, fluent=tvs_all_enabled_to_arrive_in_field(field),
                                value=Bool(True), value_applies_in_sim_effect=True)
            effects_handler.add(timing=timing_disable_arrival, fluent=tvs_all_enabled_to_arrive_in_field(field),
                                value=Bool(False), value_applies_in_sim_effect=True)

        if tv_waiting_to_overload is not None:  # @todo Remove when the tv_waiting_to_overload_id approach is working
            effects_handler.add(timing=StartTiming(), fluent=tv_waiting_to_overload(tv), value=Bool(False),
                                value_applies_in_sim_effect=True)

        if tv_ready_to_overload is not None and tv_waiting_to_overload_id is not None:
            effects_handler.add(timing=StartTiming(), fluent=tv_ready_to_overload(tv), value=Int(0),
                                value_applies_in_sim_effect=True)
            effects_handler.add(timing=StartTiming(), fluent=tv_waiting_to_overload_id(tv), value=Int(0),
                                value_applies_in_sim_effect=True)

        if tv_waiting_to_drive is not None:  # @todo Remove when the tv_waiting_to_drive_id approach is working
            effects_handler.add(timing=timing_enable_waiting_drive, fluent=tv_waiting_to_drive(tv), value=Bool(True),
                                value_applies_in_sim_effect=True)

        if timing_enable_waiting_drive is not None \
                and tv_waiting_to_drive_id is not None \
                and tvs_waiting_to_drive_ref_count is not None:
            effects_handler.add(timing=(timing_exit_field if include_field_exit else timing_end_overload),
                                fluent=tv_ready_to_drive(tv), value=Int(1), value_applies_in_sim_effect=True)

            # @note: if the tv started driving between timing_end_overload/timing_exit_field and timing_enable_waiting_drive, the tv_ready_to_drive(tv) must be 0 at timing_enable_waiting_drive
            effects_handler.add(timing=timing_enable_waiting_drive,
                                fluent=tv_waiting_to_drive_id(tv),
                                value=Times(tv_ready_to_drive(tv), tvs_waiting_to_drive_ref_count()),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_enable_waiting_drive,
                                fluent=tvs_waiting_to_drive_ref_count(),
                                value=Plus(tvs_waiting_to_drive_ref_count(), tv_ready_to_drive(tv)),
                                value_applies_in_sim_effect=False)

        if conf.ENABLE_TAMER_EXCEPTION_PARAM_REF_1 \
                or effects_option is conf.EffectsOption.WITH_ONLY_NORMAL_EFFECTS \
                or effects_option is conf.EffectsOption.WITH_NORMAL_EFFECTS_AND_CONDITIONAL_EFFECTS:
            # @todo the field_harvested(field) effect causes an error in tamer (Found a parameter reference while FTP planning!) --> using sim effects as workaround
            # @todo if the error is fixed, we could remove the sim effects bellow and this condition
            # @todo apparently the exception is fixed, but the planner fails to yield a plan (does not finish)
            effects_handler.add(timing=StartTiming(), fluent=total_harvested_mass_planned(),
                                value=Plus(total_harvested_mass_planned(), tv_mass_to_overload(tv)),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_end_overload, fluent=total_harvested_mass(),
                                value=Plus(total_harvested_mass(), tv_mass_to_overload(tv)),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_end_overload, fluent=tv_bunker_mass(tv),
                                value=Plus(tv_bunker_mass(tv), tv_mass_to_overload(tv)),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_end_overload, fluent=tv_mass_to_overload(tv), value=get_up_real(0),
                                value_applies_in_sim_effect=True)
            # effects_handler.add(timing=timing_end_overload+0.01, fluent=tv_mass_to_overload(tv), value=get_up_real(0), value_applies_in_sim_effect=True)
            effects_handler.add(timing=timing_end_overload, fluent=field_harvested(field),
                                value=LT(harv_overload_count(harv), 0), value_applies_in_sim_effect=False)
            if harv_waiting_to_harvest is not None:
                effects_handler.add(timing=timing_end_overload, fluent=harv_waiting_to_harvest(harv),
                                    value=GE(harv_overload_count(harv), 0), value_applies_in_sim_effect=False)
        else:
            effects_handler.add(timing=StartTiming(), fluent=total_harvested_mass_planned(), value=None,
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_end_overload, fluent=total_harvested_mass(), value=None,
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_end_overload, fluent=tv_bunker_mass(tv), value=None,
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_end_overload, fluent=tv_mass_to_overload(tv), value=None,
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_end_overload, fluent=field_harvested(field), value=None,
                                value_applies_in_sim_effect=False)
            if harv_waiting_to_harvest is not None:
                effects_handler.add(timing=timing_end_overload, fluent=harv_waiting_to_harvest(harv), value=None,
                                    value_applies_in_sim_effect=False)

        # ------------conditional effects------------

        if case_field_finished is None:

            # if field not finished
            effects_handler.add(timing=StartTiming(),
                                fluent=harv_overload_id(harv),
                                value=Plus(harv_overload_id(harv), 1),
                                value_applies_in_sim_effect=False,
                                condition=Not(condition_finished_field))

            # if field finished
            effects_handler.add(timing=StartTiming(),
                                fluent=harv_overload_id(harv),
                                value=Int(-1),
                                value_applies_in_sim_effect=False,
                                condition=condition_finished_field)
            effects_handler.add(timing=StartTiming(),
                                fluent=harv_overload_count(harv),
                                value=Int(-1),
                                value_applies_in_sim_effect=False,
                                condition=condition_finished_field)
        else:
            # if field not finished
            if not case_field_finished:
                effects_handler.add(timing=StartTiming(),
                                    fluent=harv_overload_id(harv),
                                    value=Plus(harv_overload_id(harv), 1),
                                    value_applies_in_sim_effect=False)

            # if field finished
            else:
                effects_handler.add(timing=StartTiming(),
                                    fluent=harv_overload_id(harv),
                                    value=Int(-1),
                                    value_applies_in_sim_effect=True)
                effects_handler.add(timing=StartTiming(),
                                    fluent=harv_overload_count(harv),
                                    value=Int(-1),
                                    value_applies_in_sim_effect=True)

        if not include_field_exit:
            if harv_enabled_to_drive_to_field_exit is not None and tv_enabled_to_drive_to_field_exit is not None:
                # Enable an x seconds window for the 'drive_xx_to_field_exit' action
                effects_handler.add(timing=timing_end_overload, fluent=harv_enabled_to_drive_to_field_exit(harv),
                                    value=Bool(True), value_applies_in_sim_effect=True)
                effects_handler.add(timing=timing_end_overload, fluent=tv_enabled_to_drive_to_field_exit(tv),
                                    value=Bool(True), value_applies_in_sim_effect=True)
                effects_handler.add(timing=timing_disable_driving, fluent=harv_enabled_to_drive_to_field_exit(harv),
                                    value=Bool(False), value_applies_in_sim_effect=True)
                effects_handler.add(timing=timing_disable_driving, fluent=tv_enabled_to_drive_to_field_exit(tv),
                                    value=Bool(False), value_applies_in_sim_effect=True)

        else:
            effects_handler.add(timing=timing_exit_field, fluent=tv_free(tv), value=Bool(True),
                                value_applies_in_sim_effect=True)
            effects_handler.add(timing=StartTiming(), fluent=tv_at_field(tv), value=no_field_object,
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_exit_field, fluent=tv_at_field_access(tv), value=field_exit_tv,
                                value_applies_in_sim_effect=False)

            effects_handler.add(timing=timing_exit_field, fluent=tv_can_unload(tv), value=Bool(True),
                                value_applies_in_sim_effect=True)

            effects_handler.add(timing=timing_exit_field,
                                fluent=tv_can_load(tv),
                                value=LE(Div(tv_bunker_mass(tv), tv_total_capacity_mass(tv)), _capacity_threshold),
                                value_applies_in_sim_effect=False)

            if tv_enabled_to_drive_to_silo is not None and tv_enabled_to_drive_to_silo is not None \
                    and harv_enabled_to_drive_to_loc is not None and harv_enabled_to_drive_to_loc is not None:
                # Enable an x seconds window for the 'drive_to_silo' action
                effects_handler.add(timing=timing_exit_field, fluent=tv_enabled_to_drive_to_silo(tv), value=Bool(True),
                                    value_applies_in_sim_effect=True)
                effects_handler.add(timing=timing_disable_driving, fluent=tv_enabled_to_drive_to_silo(tv),
                                    value=Bool(False), value_applies_in_sim_effect=True)

                # Enable an x seconds window for the 'drive_harv_to_field' action
                # todo: if using harv_finished_condition, this has to be moved to the conditional_effects part (unless the effects_handler adds the conditional effects over the normal effects)
                effects_handler.add(timing=timing_exit_field, fluent=harv_enabled_to_drive_to_loc(harv),
                                    value=Bool(True), value_applies_in_sim_effect=False)
                effects_handler.add(timing=timing_disable_driving, fluent=harv_enabled_to_drive_to_loc(harv),
                                    value=Bool(False), value_applies_in_sim_effect=True)

            if tv_enabled_to_drive_to_field is not None:
                # Enable an x seconds window for the 'drive_tv_to_field' action
                effects_handler.add(timing=timing_exit_field, fluent=tv_enabled_to_drive_to_field(tv), value=Bool(True),
                                    value_applies_in_sim_effect=True)
                effects_handler.add(timing=timing_disable_driving_2, fluent=tv_enabled_to_drive_to_field(tv),
                                    value=Bool(False), value_applies_in_sim_effect=True)

            # ------------conditional effects------------

            if case_field_finished is None:
                harv_finished_condition = LT(harv_overload_count(harv),
                                             0)  # @note the harv_overload_count is reset (if needed) at StartTiming

                effects_handler.add(timing=StartTiming(), fluent=harv_at_field(harv), value=no_field_object,
                                    value_applies_in_sim_effect=False, condition=harv_finished_condition)
                effects_handler.add(timing=timing_exit_field, fluent=harv_at_field_access(harv), value=field_exit_harv,
                                    value_applies_in_sim_effect=False, condition=harv_finished_condition)

            elif case_field_finished:
                effects_handler.add(timing=StartTiming(), fluent=harv_at_field(harv), value=no_field_object,
                                    value_applies_in_sim_effect=False)
                effects_handler.add(timing=timing_exit_field, fluent=harv_at_field_access(harv), value=field_exit_harv,
                                    value_applies_in_sim_effect=False)

        effects_handler.add_effects_to_action(self,
                                              effects_option=effects_option,
                                              sim_effect_cb=sim_effects_cb)


def get_actions_do_overload(fluents_manager: FluentsManagerBase,
                            no_harv_object: Object,
                            no_field_object: Object,
                            problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings) \
        -> List[Action]:

    """ Get all actions for 'harvest and do overload from the harvester to the transport vehicle' activities based on the given inputs options and problem settings.

    This action will not include the transit to the field exit after overload disregarding the corresponding setting in problem_settings.

    Parameters
    ----------
    fluents_manager : FluentsManagerBase
        Fluents manager used to create the problem
    no_harv_object : Object
        Problem object corresponding to 'no harvester'
    no_field_object : Object
        Problem object corresponding to 'no field'
    problem_settings : conf.GeneralProblemSettings
        Problem settings

    Returns
    -------
    actions : List[Action]
        All actions for 'harvest and do overload from the harvester to the transport vehicle and drive machine(s) to the field exit' activities based on the given inputs options and problem settings.

    """

    if problem_settings.effects_settings.do_overload is conf.EffectsOption.WITH_ONLY_NORMAL_EFFECTS \
            or problem_settings.action_decomposition_settings.do_overload:
        return [ ActionDoOverload(fluents_manager, no_harv_object, no_field_object, None, False, False, problem_settings),
                 ActionDoOverload(fluents_manager, no_harv_object, no_field_object, None, False, True, problem_settings)
                 ]
    else:
        return [ ActionDoOverload(fluents_manager, no_harv_object, no_field_object, None, False, None, problem_settings) ]


def get_actions_do_overload_and_exit(fluents_manager: FluentsManagerBase,
                                     no_harv_object: Object,
                                     no_field_object: Object,
                                     no_field_access_object: Object,
                                     problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings) \
        -> List[Action]:

    """ Get all actions for 'harvest and do overload from the harvester to the transport vehicle and drive machine(s) to the field exit' activities based on the given inputs options and problem settings.

    This action will include the transit to the field exit after overload disregarding the corresponding setting in problem_settings.

    Parameters
    ----------
    fluents_manager : FluentsManagerBase
        Fluents manager used to create the problem
    no_harv_object : Object
        Problem object corresponding to 'no harvester'
    no_field_object : Object
        Problem object corresponding to 'no field'
    no_field_access_object : Object
        Problem object corresponding to 'no field access'
    problem_settings : conf.GeneralProblemSettings
        Problem settings

    Returns
    -------
    actions : List[Action]
        All actions for 'harvest and do overload from the harvester to the transport vehicle and drive machine(s) to the field exit' activities based on the given inputs options and problem settings.

    """

    if problem_settings.effects_settings.do_overload is conf.EffectsOption.WITH_ONLY_NORMAL_EFFECTS \
            or problem_settings.action_decomposition_settings.do_overload:
        return [ ActionDoOverload(fluents_manager, no_harv_object, no_field_object, no_field_access_object, True, False, problem_settings),
                 ActionDoOverload(fluents_manager, no_harv_object, no_field_object, no_field_access_object, True, True, problem_settings)
                 ]
    return [ ActionDoOverload(fluents_manager, no_harv_object, no_field_object, no_field_access_object, True, None, problem_settings ) ]
