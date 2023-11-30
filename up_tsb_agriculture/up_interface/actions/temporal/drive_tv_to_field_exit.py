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
import up_interface.types as upt
from up_interface import config as conf
from up_interface.fluents import FluentsManagerBase
from up_interface.fluents import FluentNames as fn
from up_interface.actions.actions_helper import *
from up_interface.types_helper import *


class ActionDriveTvToFieldExit(DurativeAction):
    """ Durative action related to 'drive transport vehicle to a field exit point'. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        DRIVE_TV_TO_FIELD_EXIT = 'drive_tv_to_field_exit'

    @unique
    class ParameterNames(Enum):
        """ Enum with the possible action parameters this action can have. """

        FIELD = 'field'
        FIELD_ACCESS = 'field_access'
        TV = 'tv'

    def __init__(self,
                 fluents_manager: FluentsManagerBase,
                 no_field_object: Object,
                 no_field_access_object: Object,
                 problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings):

        """ Creates the action based on the initialization parameters.

        Parameters
        ----------
        fluents_manager : FluentsManagerBase
            Fluents manager used to create the problem
        no_field_object : Object
            Problem object corresponding to 'no field'
        no_field_access_object : Object
            Problem object corresponding to 'no field access'
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        """

        params = {ActionDriveTvToFieldExit.ParameterNames.FIELD.value: upt.Field,
                  ActionDriveTvToFieldExit.ParameterNames.FIELD_ACCESS.value: upt.FieldAccess,
                  ActionDriveTvToFieldExit.ParameterNames.TV.value: upt.TransportVehicle}

        DurativeAction.__init__(self, ActionDriveTvToFieldExit.ActionNames.DRIVE_TV_TO_FIELD_EXIT.value, **params)

        # ----------temporal parameters-----------

        delta_time_after_exit = 0.0
        delta_time_after_exit = max(delta_time_after_exit, problem_settings.control_windows.enable_driving_opening_time)
        delta_time_after_exit = max(delta_time_after_exit, problem_settings.control_windows.enable_driving_tvs_to_field_opening_time )
        delta_time_after_exit = max(delta_time_after_exit, problem_settings.cost_windows.waiting_drive_opening_time)

        action_duration = Plus(30,  # @todo infield transit to field exit (fixed at the moment)
                               delta_time_after_exit)

        timing_end_exit = get_timing_before_end_timing(action_duration, delay=delta_time_after_exit)
        timing_disable_driving = get_timing_before_end_timing(action_duration,
                                                              delay=(delta_time_after_exit -
                                                                     max(0.0, problem_settings.control_windows.enable_driving_opening_time)))
        timing_disable_driving_2 = get_timing_before_end_timing(action_duration,
                                                                delay=(delta_time_after_exit -
                                                                       max(0.0, problem_settings.control_windows.enable_driving_tvs_to_field_opening_time )))
        timing_enable_waiting_drive = get_timing_before_end_timing(action_duration,
                                                                   delay=(delta_time_after_exit -
                                                                          max(0.0, problem_settings.cost_windows.waiting_drive_opening_time)))

        set_duration_to_action(self, action_duration)

        self.__add_conditions(fluents_manager=fluents_manager,
                              no_field_object=no_field_object,
                              no_field_access_object=no_field_access_object)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings,
                           no_field_object=no_field_object,
                           timing_end_exit=timing_end_exit,
                           timing_disable_driving=timing_disable_driving,
                           timing_disable_driving_2=timing_disable_driving_2,
                           timing_enable_waiting_drive=timing_enable_waiting_drive)

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase,
                         no_field_object,
                         no_field_access_object):

        """ Add the conditions to the action. """

        # ------------parameters------------

        field = self.parameter(ActionDriveTvToFieldExit.ParameterNames.FIELD.value)
        field_access = self.parameter(ActionDriveTvToFieldExit.ParameterNames.FIELD_ACCESS.value)
        tv = self.parameter(ActionDriveTvToFieldExit.ParameterNames.TV.value)

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)
        field_id = fluents_manager.get_fluent(fn.field_id)
        field_access_field_id = fluents_manager.get_fluent(fn.field_access_field_id)

        tv_free = fluents_manager.get_fluent(fn.tv_free)
        tv_at_field = fluents_manager.get_fluent(fn.tv_at_field)
        tv_enabled_to_drive_to_field_exit = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_field_exit)
        tv_overload_id = fluents_manager.get_fluent(fn.tv_overload_id)

        # ------------conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action( self, Not( planning_failed() ) , StartTiming() )

        # the objects are valid
        add_precondition_to_action( self, Not( Equals(field, no_field_object) ), StartTiming() )
        add_precondition_to_action( self, Not( Equals(field_access, no_field_access_object) ), StartTiming() )

        # the field access is an access point of the field
        add_precondition_to_action( self, Equals( field_id(field), field_access_field_id(field_access) ) , StartTiming() )

        # check if the machines are available
        add_precondition_to_action( self, tv_free(tv), StartTiming() )

        # check if the machine has no pending overloads
        add_precondition_to_action( self, LT( tv_overload_id(tv), 0 ) , StartTiming() )

        # the machine is currently in the field
        add_precondition_to_action( self, Equals( tv_at_field(tv), field ), StartTiming() )

        if tv_enabled_to_drive_to_field_exit is not None:
            # the action must be planned while the planning window is open
            add_precondition_to_action( self, tv_enabled_to_drive_to_field_exit(tv), StartTiming() )

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings,
                      no_field_object,
                      timing_end_exit,
                      timing_disable_driving,
                      timing_disable_driving_2,
                      timing_enable_waiting_drive):

        """ Add the effects to the action. """
    
        effects_option = problem_settings.effects_settings.general

        # ------------parameters------------

        field_access = self.parameter(ActionDriveTvToFieldExit.ParameterNames.FIELD_ACCESS.value)
        tv = self.parameter(ActionDriveTvToFieldExit.ParameterNames.TV.value)

        # ------------fluents to be used------------

        tv_free = fluents_manager.get_fluent(fn.tv_free)
        tv_at_field = fluents_manager.get_fluent(fn.tv_at_field)
        tv_at_field_access = fluents_manager.get_fluent(fn.tv_at_field_access)
        tv_enabled_to_drive_to_field_exit = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_field_exit)
        tv_enabled_to_drive_to_field = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_field)
        tv_enabled_to_drive_to_silo = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_silo)
        tv_ready_to_drive = fluents_manager.get_fluent(fn.tv_ready_to_drive)
        tv_waiting_to_drive_id = fluents_manager.get_fluent(fn.tv_waiting_to_drive_id)
        tvs_waiting_to_drive_ref_count = fluents_manager.get_fluent(fn.tvs_waiting_to_drive_ref_count)
        tv_waiting_to_drive = fluents_manager.get_fluent(fn.tv_waiting_to_drive)

        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
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

            _tv = actual_params.get(tv)
            _field_access = actual_params.get(field_access)

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'+++++++++++++++++++ [state {id(state)}] ::  {self.name} sim effect [{timing}] - {_tv}')

            _tv_ready_to_drive = _tvs_waiting_to_drive_ref_count = None
            if tv_ready_to_drive is not None:
                _tv_ready_to_drive = int(state.get_value(tv_ready_to_drive(_tv)).constant_value())
            if tvs_waiting_to_drive_ref_count is not None:
                _tvs_waiting_to_drive_ref_count = int(state.get_value(tvs_waiting_to_drive_ref_count()).constant_value())

            ret_vals = []

            for fl, val in effects_values.items():
                if val[0] is not None and val[1]:  # give priority to values that were set already
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0] )
                    continue

                if fl is tv_at_field(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   ObjectExp(problem.object(no_field_object.name)) )
                elif fl is tv_at_field_access(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _field_access )
                elif fl is tv_can_load(tv):
                    _tv_bunker_mass = float( state.get_value( tv_bunker_mass( _tv) ).constant_value() )
                    _tv_total_capacity_mass = float( state.get_value( tv_total_capacity_mass( _tv) ).constant_value() )
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Bool( _tv_bunker_mass / _tv_total_capacity_mass <= _capacity_threshold ) )
                elif fl is tv_can_unload(tv):
                    _tv_bunker_mass = float( state.get_value( tv_bunker_mass( _tv) ).constant_value() )
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Bool( _tv_bunker_mass > 1e-9 ) )
                elif tv_waiting_to_drive_id is not None \
                        and fl is tv_waiting_to_drive_id(tv) \
                        and timing == timing_enable_waiting_drive:
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_tv_ready_to_drive * _tvs_waiting_to_drive_ref_count))  # tv_waiting_to_drive_id(tv)
                elif tvs_waiting_to_drive_ref_count is not None \
                        and fl is tvs_waiting_to_drive_ref_count() \
                        and timing == timing_enable_waiting_drive:
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_tv_ready_to_drive + _tvs_waiting_to_drive_ref_count))  # tvs_waiting_to_drive_ref_count()

                # unexpected fluent
                else:
                    raise ValueError(f'Unexpected fluent {fl} in simulated effect')

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'------------------- {self.name} sim effect [{timing}] - {_tv}')

            return ret_vals

        effects_handler = EffectsHandler()

        effects_handler.add(timing=StartTiming(), fluent=tv_free(tv), value=Bool(False), value_applies_in_sim_effect=True)
        effects_handler.add(timing=timing_end_exit, fluent=tv_free(tv), value=Bool(True), value_applies_in_sim_effect=True)
        effects_handler.add(timing=StartTiming(), fluent=tv_at_field(tv), value=no_field_object, value_applies_in_sim_effect=False)
        effects_handler.add(timing=timing_end_exit, fluent=tv_at_field_access(tv), value=field_access, value_applies_in_sim_effect=False)

        if tv_waiting_to_drive is not None:  # @todo Remove when the tv_waiting_to_drive_id approach is working
            effects_handler.add(timing=StartTiming(), fluent=tv_waiting_to_drive(tv), value=Bool(False), value_applies_in_sim_effect=True)
            effects_handler.add(timing=timing_enable_waiting_drive, fluent=tv_waiting_to_drive(tv), value=Bool(True), value_applies_in_sim_effect=True)

        if tv_ready_to_drive is not None \
                and tv_waiting_to_drive_id is not None \
                and tvs_waiting_to_drive_ref_count is not None:
            effects_handler.add(timing=StartTiming(), fluent=tv_ready_to_drive(tv), value=Int(0), value_applies_in_sim_effect=True)
            effects_handler.add(timing=StartTiming(), fluent=tv_waiting_to_drive_id(tv), value=Int(0), value_applies_in_sim_effect=True)

            effects_handler.add(timing=timing_end_exit, fluent=tv_ready_to_drive(tv), value=Int(1), value_applies_in_sim_effect=True)

            # @note: if the tv started driving between timing_end_exit and timing_enable_waiting_drive, the tv_ready_to_drive(tv) must be 0 at timing_enable_waiting_drive
            effects_handler.add(timing=timing_enable_waiting_drive,
                                fluent=tv_waiting_to_drive_id(tv),
                                value=Times( tv_ready_to_drive(tv), tvs_waiting_to_drive_ref_count()),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_enable_waiting_drive,
                                fluent=tvs_waiting_to_drive_ref_count(),
                                value=Plus( tvs_waiting_to_drive_ref_count(), tv_ready_to_drive(tv) ),
                                value_applies_in_sim_effect=False)

        # effects_handler.add(timing=timing_end_exit, fluent=tv_can_unload(tv), value=Bool(True), value_applies_in_sim_effect=True)
        effects_handler.add(timing=timing_end_exit,
                            fluent=tv_can_unload(tv),
                            value=GT ( tv_bunker_mass(tv) , get_up_real(0) ),
                            value_applies_in_sim_effect=False)

        effects_handler.add(timing=timing_end_exit,
                            fluent=tv_can_load(tv),
                            value=LE ( Div( tv_bunker_mass( tv ), tv_total_capacity_mass( tv ) ),
                                       _capacity_threshold ),
                            value_applies_in_sim_effect=False)

        if tv_enabled_to_drive_to_field_exit is not None and tv_enabled_to_drive_to_silo is not None:
            effects_handler.add(timing=StartTiming(), fluent=tv_enabled_to_drive_to_field_exit(tv), value=Bool(False), value_applies_in_sim_effect=True)

            # Enable an x seconds window for the 'drive_harv_to_field' action
            effects_handler.add(timing=timing_end_exit, fluent=tv_enabled_to_drive_to_silo(tv), value=Bool(True), value_applies_in_sim_effect=True)
            effects_handler.add(timing=timing_disable_driving, fluent=tv_enabled_to_drive_to_silo(tv), value=Bool(False), value_applies_in_sim_effect=True)

        if tv_enabled_to_drive_to_field is not None:
            # Enable an x seconds window for the 'drive_harv_to_field' action
            effects_handler.add(timing=timing_end_exit, fluent=tv_enabled_to_drive_to_field(tv), value=Bool(True), value_applies_in_sim_effect=True)
            effects_handler.add(timing=timing_disable_driving_2, fluent=tv_enabled_to_drive_to_field(tv), value=Bool(False), value_applies_in_sim_effect=True)

        effects_handler.add_effects_to_action(action=self,
                                              effects_option=effects_option,
                                              sim_effect_cb=sim_effects_cb)
        

def get_actions_drive_tv_to_field_exit(fluents_manager: FluentsManagerBase,
                                       no_field_object: Object,
                                       no_field_access_object: Object,
                                       problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings) \
        -> List[Action]:

    """ Get all actions for 'drive transport vehicle to a field exit point' activities based on the given inputs options and problem settings.

    Parameters
    ----------
    fluents_manager : FluentsManagerBase
        Fluents manager used to create the problem
    no_field_object : Object
        Problem object corresponding to 'no field'
    no_field_access_object : Object
        Problem object corresponding to 'no field access'
    problem_settings : conf.GeneralProblemSettings
        Problem settings

    Returns
    -------
    actions : List[Action]
        All actions for 'drive transport vehicle to a field exit point' activities based on the given inputs options and problem settings.

    """

    return [ ActionDriveTvToFieldExit(fluents_manager, no_field_object, no_field_access_object, problem_settings ) ]
