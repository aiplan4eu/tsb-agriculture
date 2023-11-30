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


class ActionUnloadAtSilo(DurativeAction):
    """ Durative action related to 'unload at silo'. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        UNLOAD_AT_SILO = 'unload_at_silo'

    @unique
    class ParameterNames(Enum):
        """ Enum with the possible action parameters this action can have. """

        TV = 'tv'
        SILO_ACCESS = 'silo_access'

    def __init__(self,
                 fluents_manager: FluentsManagerBase,
                 problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings):

        """ Creates the action based on the initialization parameters.

        Parameters
        ----------
        fluents_manager : FluentsManagerBase
            Fluents manager used to create the problem
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        """

        params = {self.ParameterNames.TV.value: upt.TransportVehicle,
                  self.ParameterNames.SILO_ACCESS.value: upt.SiloAccess}

        DurativeAction.__init__(self, self.ActionNames.UNLOAD_AT_SILO.value, **params)

        # ------------parameters------------

        tv = self.parameter(self.ParameterNames.TV.value)
        silo_access = self.parameter(self.ParameterNames.SILO_ACCESS.value)

        # ------------fluents to be used------------

        tv_unloading_speed_mass = fluents_manager.get_fluent(fn.tv_unloading_speed_mass)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)

        silo_access_free = fluents_manager.get_fluent(fn.silo_access_free)
        silo_access_available_capacity_mass = fluents_manager.get_fluent(fn.silo_access_available_capacity_mass)

        unload_directly_at_silo = (problem_settings.silo_planning_type is not conf.SiloPlanningType.WITH_SILO_ACCESS_CAPACITY_AND_COMPACTION
                                   and silo_access_available_capacity_mass is not None)
        check_for_sap_availability = (problem_settings.silo_planning_type is not conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY
                                      and silo_access_free is not None)

        # ----------temporal parameters-----------

        delta_time_after_unload = 0.0

        delta_time_after_unload = max( delta_time_after_unload, problem_settings.control_windows.enable_driving_tvs_to_field_opening_time )
        delta_time_after_unload = max( delta_time_after_unload, problem_settings.cost_windows.waiting_drive_from_silo_opening_time)

        action_duration = Plus(
                                Div(tv_bunker_mass(tv), tv_unloading_speed_mass(tv)),
                                delta_time_after_unload
                               )

        timing_end_unload = get_timing_before_end_timing(action_duration,
                                                         delay=delta_time_after_unload)
        timing_disable_driving = get_timing_before_end_timing(action_duration,
                                                              delay=(delta_time_after_unload -
                                                                     max(0.0, problem_settings.control_windows.enable_driving_tvs_to_field_opening_time )))
        timing_enable_waiting_drive = get_timing_before_end_timing(action_duration,
                                                                   delay=(delta_time_after_unload -
                                                                          max(0.0, problem_settings.cost_windows.waiting_drive_from_silo_opening_time)))

        # ------------duration------------#

        set_duration_to_action( self, action_duration )

        self.__add_conditions(fluents_manager=fluents_manager,
                              timing_end_unload=timing_end_unload,
                              unload_directly_at_silo=unload_directly_at_silo,
                              check_for_sap_availability=check_for_sap_availability)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings,
                           timing_end_unload=timing_end_unload,
                           timing_disable_driving=timing_disable_driving,
                           timing_enable_waiting_drive=timing_enable_waiting_drive,
                           unload_directly_at_silo=unload_directly_at_silo,
                           check_for_sap_availability=check_for_sap_availability)

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase,
                         timing_end_unload,
                         unload_directly_at_silo,
                         check_for_sap_availability):

        """ Add the conditions to the action. """

        # ------------parameters------------

        tv = self.parameter(self.ParameterNames.TV.value)
        silo_access = self.parameter(self.ParameterNames.SILO_ACCESS.value)

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)

        silo_access_free = fluents_manager.get_fluent(fn.silo_access_free)
        silo_access_total_capacity_mass = fluents_manager.get_fluent(fn.silo_access_total_capacity_mass)
        silo_access_available_capacity_mass = fluents_manager.get_fluent(fn.silo_access_available_capacity_mass)

        tv_free = fluents_manager.get_fluent(fn.tv_free)
        tv_at_silo_access = fluents_manager.get_fluent(fn.tv_at_silo_access)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_ready_to_unload = fluents_manager.get_fluent(fn.tv_ready_to_unload)

        # ------------conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action( self, Not( planning_failed() ), StartTiming() )

        # check if the transport vehicle is available
        add_precondition_to_action( self, tv_free(tv) , StartTiming() )

        # check if the machine is at the access point
        add_precondition_to_action( self, Equals( tv_at_silo_access(tv), silo_access ), StartTiming() )

        # the transport vehicle is currently at a silo ready to unload
        add_precondition_to_action( self, tv_ready_to_unload(tv) , StartTiming() )

        if check_for_sap_availability:
            # the silo access is free
            add_precondition_to_action( self, silo_access_free(silo_access), StartTiming() )
            # add_precondition_to_action( self, silo_access_free(silo_access), ClosedTimeInterval(StartTiming(), timing_end_unload) )

        if not unload_directly_at_silo:
            # the silo access has enough capacity for the yield
            add_precondition_to_action( self,
                                        GE(silo_access_total_capacity_mass(silo_access),
                                           Plus(silo_access_available_capacity_mass(silo_access), tv_bunker_mass(tv))),
                                        StartTiming() )

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings,
                      timing_end_unload,
                      timing_disable_driving,
                      timing_enable_waiting_drive,
                      unload_directly_at_silo,
                      check_for_sap_availability):

        """ Add the effects to the action. """

        effects_option = problem_settings.effects_settings.general

        # ------------parameters------------

        tv = self.parameter(ActionUnloadAtSilo.ParameterNames.TV.value)
        silo_access = self.parameter(ActionUnloadAtSilo.ParameterNames.SILO_ACCESS.value)

        # ------------fluents to be used------------

        total_yield_mass_in_silos = fluents_manager.get_fluent(fn.total_yield_mass_in_silos)

        silo_access_free = fluents_manager.get_fluent(fn.silo_access_free)
        silo_access_available_capacity_mass = fluents_manager.get_fluent(fn.silo_access_available_capacity_mass)
        silo_access_cleared = fluents_manager.get_fluent(fn.silo_access_cleared)

        tv_free = fluents_manager.get_fluent(fn.tv_free)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_ready_to_unload = fluents_manager.get_fluent(fn.tv_ready_to_unload)
        tv_can_load = fluents_manager.get_fluent(fn.tv_can_load)
        tv_ready_to_drive = fluents_manager.get_fluent(fn.tv_ready_to_drive)
        tv_waiting_to_drive_id = fluents_manager.get_fluent(fn.tv_waiting_to_drive_id)
        tvs_waiting_to_drive_ref_count = fluents_manager.get_fluent(fn.tvs_waiting_to_drive_ref_count)
        tv_waiting_to_drive = fluents_manager.get_fluent(fn.tv_waiting_to_drive)

        tv_enabled_to_drive_to_field = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_field)

        # ------------effects------------#

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
            _silo_access = actual_params.get(silo_access)

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'+++++++++++++++++++ [state {id(state)}] ::  {self.name} sim effect [{timing}] - {_tv} - {_silo_access}')

            _tv_bunker_mass = float(state.get_value(tv_bunker_mass(_tv)).constant_value())

            _tv_ready_to_drive = _tvs_waiting_to_drive_ref_count = None
            if tv_ready_to_drive is not None:
                _tv_ready_to_drive = int(state.get_value(tv_ready_to_drive(_tv)).constant_value())
            if tvs_waiting_to_drive_ref_count is not None:
                _tvs_waiting_to_drive_ref_count = int(state.get_value(tvs_waiting_to_drive_ref_count()).constant_value())

            ret_vals = []

            for fl, val in effects_values.items():
                if val[0] is not None and val[1]: # give priority to values that were set already
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0] )
                    continue

                if fl is silo_access_available_capacity_mass(silo_access):
                    _silo_access_available_capacity_mass = float(state.get_value(silo_access_available_capacity_mass(silo_access)).constant_value())
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _silo_access_available_capacity_mass - _tv_bunker_mass ) )
                elif fl is total_yield_mass_in_silos():
                    _total_yield_mass_in_silos = float(state.get_value(total_yield_mass_in_silos()).constant_value())
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _total_yield_mass_in_silos + _tv_bunker_mass ) )
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
                print(f'------------------- {self.name} sim effect [{timing}] - {_tv} - {_silo_access}')

            return ret_vals

        effects_handler = EffectsHandler()

        if silo_access_free is not None:
            effects_handler.add(timing=StartTiming(), fluent=silo_access_free(silo_access), value=Bool(False), value_applies_in_sim_effect=True)
            effects_handler.add(timing=timing_end_unload, fluent=silo_access_free(silo_access), value=Bool(True), value_applies_in_sim_effect=True)

        effects_handler.add(timing=StartTiming(), fluent=tv_free(tv), value=Bool(False), value_applies_in_sim_effect=True)
        effects_handler.add(timing=timing_end_unload, fluent=tv_free(tv), value=Bool(True), value_applies_in_sim_effect=True)

        effects_handler.add(timing=StartTiming(), fluent=silo_access_cleared(silo_access), value=Bool(False), value_applies_in_sim_effect=True)

        if unload_directly_at_silo:
            effects_handler.add(timing=timing_end_unload, fluent=total_yield_mass_in_silos(), value=Plus(total_yield_mass_in_silos(), tv_bunker_mass(tv)), value_applies_in_sim_effect=False)
        else:
            # @todo check at what timing to decrease the silo_access_available_capacity_mass considering the sweep_silo_access action
            effects_handler.add(timing=timing_end_unload,
                                fluent=silo_access_available_capacity_mass(silo_access),
                                value=Minus(silo_access_available_capacity_mass(silo_access), tv_bunker_mass(tv)),
                                value_applies_in_sim_effect=False)

        effects_handler.add(timing=timing_end_unload, fluent=tv_bunker_mass(tv), value=get_up_real(0), value_applies_in_sim_effect=True)

        effects_handler.add(timing=StartTiming(), fluent=tv_ready_to_unload(tv), value=Bool(False), value_applies_in_sim_effect=True)

        if tv_waiting_to_drive is not None:  # @todo Remove when the tv_waiting_to_drive_id approach is working
            effects_handler.add(timing=timing_enable_waiting_drive, fluent=tv_waiting_to_drive(tv), value=Bool(True), value_applies_in_sim_effect=True)

        if timing_enable_waiting_drive is not None \
                and tv_waiting_to_drive_id is not None \
                and timing_enable_waiting_drive is not None:
            effects_handler.add(timing=timing_end_unload, fluent=tv_ready_to_drive(tv), value=Int(1), value_applies_in_sim_effect=True)

            # @note: if the tv started driving between timing_end_unload and timing_enable_waiting_drive, the tv_ready_to_drive(tv) must be 0 at timing_enable_waiting_drive
            effects_handler.add(timing=timing_enable_waiting_drive,
                                fluent=tv_waiting_to_drive_id(tv),
                                value=Times( tv_ready_to_drive(tv), tvs_waiting_to_drive_ref_count()),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_enable_waiting_drive,
                                fluent=tvs_waiting_to_drive_ref_count(),
                                value=Plus( tvs_waiting_to_drive_ref_count(), tv_ready_to_drive(tv) ),
                                value_applies_in_sim_effect=False)

        if tv_enabled_to_drive_to_field is not None:
            # Enable an x seconds window for the 'drive_tv_to_field' action
            effects_handler.add(timing=timing_end_unload, fluent=tv_enabled_to_drive_to_field(tv), value=Bool(True), value_applies_in_sim_effect=True)
            effects_handler.add(timing=timing_disable_driving, fluent=tv_enabled_to_drive_to_field(tv), value=Bool(False), value_applies_in_sim_effect=True)

        effects_handler.add(timing=timing_end_unload, fluent=tv_can_load(tv), value=Bool(True), value_applies_in_sim_effect=True)

        effects_handler.add_effects_to_action(action=self,
                                              effects_option=effects_option,
                                              sim_effect_cb=sim_effects_cb)


def get_actions_unload_at_silo(fluents_manager: FluentsManagerBase,
                               problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings) \
        -> List[Action]:

    """ Get all actions for 'unload at silo' activities based on the given inputs options and problem settings.

    Parameters
    ----------
    fluents_manager : FluentsManagerBase
        Fluents manager used to create the problem
    problem_settings : conf.GeneralProblemSettings
        Problem settings

    Returns
    -------
    actions : List[Action]
        All actions for 'unload at silo' activities based on the given inputs options and problem settings.

    """
    return [ ActionUnloadAtSilo(fluents_manager, problem_settings ) ]
