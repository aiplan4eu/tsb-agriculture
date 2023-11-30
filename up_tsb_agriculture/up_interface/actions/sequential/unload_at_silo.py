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


class ActionUnloadAtSilo(InstantaneousAction):
    """ Instantaneous action related to 'unload at silo'. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        UNLOAD_AT_SILO = 'unload_at_silo'
        UNLOAD_AT_SILO_TV_WAITS = 'unload_at_silo_tv_waits'

    @unique
    class ParameterNames(Enum):
        """ Enum with the possible action parameters this action can have. """

        TV = 'tv'
        SILO_ACCESS = 'silo_access'

    def __init__(self,
                 fluents_manager: FluentsManagerBase,
                 tv_waits_for_unload: Union[bool, None],
                 problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings):

        """ Creates the action based on the initialization parameters.

        Parameters
        ----------
        fluents_manager : FluentsManagerBase
            Fluents manager used to create the problem
        tv_waits_for_unload : bool, None
            Flag stating whether the action must be created for the specific case that the transport vehicle has to wait at the silo access to unload or for the specific case that it does not wait to unload. If None, the action for the general case will be created.
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        """

        params = {ActionUnloadAtSilo.ParameterNames.TV.value: upt.TransportVehicle,
                  ActionUnloadAtSilo.ParameterNames.SILO_ACCESS.value: upt.SiloAccess}

        if tv_waits_for_unload is None or not tv_waits_for_unload:
            action_name = ActionUnloadAtSilo.ActionNames.UNLOAD_AT_SILO.value
        else:
            action_name = ActionUnloadAtSilo.ActionNames.UNLOAD_AT_SILO_TV_WAITS.value
        InstantaneousAction.__init__(self, action_name, **params)

        # ------------parameters------------

        tv = self.parameter(ActionUnloadAtSilo.ParameterNames.TV.value)
        silo_access = self.parameter(ActionUnloadAtSilo.ParameterNames.SILO_ACCESS.value)

        # ------------fluents to be used------------

        silo_access_timestamp = fluents_manager.get_fluent(fn.silo_access_timestamp)

        tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)
        tv_unloading_speed_mass = fluents_manager.get_fluent(fn.tv_unloading_speed_mass)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)

        # ----------temporal parameters-----------

        unload_duration = Div( tv_bunker_mass(tv), tv_unloading_speed_mass(tv) )

        if tv_waits_for_unload is None or not tv_waits_for_unload:
            unload_start_timestamp = tv_timestamp(tv)
        else:
            if silo_access_timestamp is None:
                raise ValueError('Option-case tv_waits not supported by current configuration')
            unload_start_timestamp = silo_access_timestamp(silo_access)
        action_finish_timestamp = Plus(unload_start_timestamp, unload_duration)

        self.__add_conditions(fluents_manager=fluents_manager,
                              unload_start_timestamp=unload_start_timestamp,
                              tv_waits_for_unload=tv_waits_for_unload)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings,
                           unload_start_timestamp=unload_start_timestamp,
                           action_finish_timestamp=action_finish_timestamp,
                           tv_waits_for_unload=tv_waits_for_unload)

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase,
                         unload_start_timestamp,
                         tv_waits_for_unload):

        """ Add the conditions to the action. """

        # ------------parameters------------

        tv = self.parameter(ActionUnloadAtSilo.ParameterNames.TV.value)
        silo_access = self.parameter(ActionUnloadAtSilo.ParameterNames.SILO_ACCESS.value)

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)

        silo_access_timestamp = fluents_manager.get_fluent(fn.silo_access_timestamp)
        silo_access_total_capacity_mass = fluents_manager.get_fluent(fn.silo_access_total_capacity_mass)
        silo_access_available_capacity_mass = fluents_manager.get_fluent(fn.silo_access_available_capacity_mass)

        tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)
        tv_at_silo_access = fluents_manager.get_fluent(fn.tv_at_silo_access)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_ready_to_unload = fluents_manager.get_fluent(fn.tv_ready_to_unload)

        # ------------pre-conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action( self, Not( planning_failed() ), StartTiming() )

        # check if the machine is at the access point
        add_precondition_to_action( self, Equals( tv_at_silo_access(tv), silo_access ), StartTiming() )

        # the transport vehicle is currently at a silo ready to unload
        add_precondition_to_action( self, tv_ready_to_unload(tv) , StartTiming() )

        # the silo access has enough capacity for the yield
        add_precondition_to_action( self,
                                    GE(silo_access_total_capacity_mass(silo_access),
                                       Plus(silo_access_available_capacity_mass(silo_access), tv_bunker_mass(tv))),
                                    StartTiming() )

        # check the tv and sap timestamps for silo access availability
        if tv_waits_for_unload is not None:
            if silo_access_timestamp is None:
                raise ValueError('Option-case tv_waits not supported by current configuration')
            if tv_waits_for_unload:
                add_precondition_to_action( self, LT ( tv_timestamp(tv), silo_access_timestamp(silo_access) ), StartTiming() )
            else:
                add_precondition_to_action( self, GE ( tv_timestamp(tv), silo_access_timestamp(silo_access) ), StartTiming() )

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings,
                      unload_start_timestamp,
                      action_finish_timestamp,
                      tv_waits_for_unload):

        """ Add the effects to the action. """

        effects_option = problem_settings.effects_settings.general

        # ------------parameters------------

        tv = self.parameter(ActionUnloadAtSilo.ParameterNames.TV.value)
        silo_access = self.parameter(ActionUnloadAtSilo.ParameterNames.SILO_ACCESS.value)

        # ------------fluents to be used------------

        total_yield_mass_in_silos = fluents_manager.get_fluent(fn.total_yield_mass_in_silos)  # @todo in the future it might be needed to differentiate between mass_in_silos (incl. unloading points) and mass_in_silos (in main storage)

        silo_access_available_capacity_mass = fluents_manager.get_fluent(fn.silo_access_available_capacity_mass)
        silo_access_cleared = fluents_manager.get_fluent(fn.silo_access_cleared)
        silo_access_timestamp = fluents_manager.get_fluent(fn.silo_access_timestamp)

        tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)
        tv_waiting_time = fluents_manager.get_fluent(fn.tv_waiting_time)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_unloading_speed_mass = fluents_manager.get_fluent(fn.tv_unloading_speed_mass)
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

            _tv_timestamp = float(state.get_value(tv_timestamp(_tv)).constant_value())
            _tv_waiting_time = float(state.get_value(tv_waiting_time(_tv)).constant_value())
            _tv_bunker_mass = float(state.get_value(tv_bunker_mass(_tv)).constant_value())
            _tv_ready_to_drive = int(state.get_value(tv_ready_to_drive(_tv)).constant_value())
            _tvs_waiting_to_drive_ref_count = int(state.get_value(tvs_waiting_to_drive_ref_count()).constant_value())
            _tv_unloading_speed_mass = float(state.get_value(tv_unloading_speed_mass(_tv)).constant_value())

            _unload_duration = _tv_bunker_mass / _tv_unloading_speed_mass
            if tv_waits_for_unload is not None:
                _silo_access_timestamp = float(state.get_value(silo_access_timestamp(_silo_access)).constant_value())
                _unload_start_timestamp = _silo_access_timestamp if tv_waits_for_unload else _tv_timestamp
                _action_finish_timestamp = _unload_start_timestamp + _unload_duration
                if tv_waits_for_unload:
                    _tv_waiting_time += max(0.0, _unload_start_timestamp - _tv_timestamp )
            else:
                _action_finish_timestamp = _tv_timestamp + _unload_duration

            ret_vals = []

            for fl, val in effects_values.items():
                if val[0] is not None and val[1]:  # give priority to values that were set already
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0] )
                    continue

                if fl is total_yield_mass_in_silos():
                    _total_yield_mass_in_silos = float(state.get_value(total_yield_mass_in_silos()).constant_value())
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _total_yield_mass_in_silos + _tv_bunker_mass ) )
                elif fl is silo_access_timestamp(silo_access):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _action_finish_timestamp ) )
                elif fl is tv_timestamp(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _action_finish_timestamp ) )
                elif fl is tv_waiting_time(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _tv_waiting_time ) )

                # unexpected fluent
                else:
                    raise ValueError(f'Unexpected fluent {fl} in simulated effect')

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'------------------- {self.name} sim effect [{timing}] - {_tv} - {_silo_access}')

            return ret_vals

        effects_handler = EffectsHandler()

        effects_handler.add(timing=StartTiming(), fluent=total_yield_mass_in_silos(), value=Plus(total_yield_mass_in_silos(), tv_bunker_mass(tv)), value_applies_in_sim_effect=False)
        effects_handler.add(timing=StartTiming(), fluent=tv_bunker_mass(tv), value=get_up_real(0), value_applies_in_sim_effect=True)
        effects_handler.add(timing=StartTiming(), fluent=tv_can_load(tv), value=Bool(True), value_applies_in_sim_effect=True)
        effects_handler.add(timing=StartTiming(), fluent=tv_ready_to_unload(tv), value=Bool(False), value_applies_in_sim_effect=True)

        effects_handler.add(timing=StartTiming(), fluent=tv_timestamp(tv),
                            value=action_finish_timestamp,
                            value_applies_in_sim_effect=False)
        if tv_waits_for_unload is not None:
            effects_handler.add(timing=StartTiming(), fluent=silo_access_timestamp(silo_access),
                                value=action_finish_timestamp,
                                value_applies_in_sim_effect=False)
            if tv_waits_for_unload:
                effects_handler.add(timing=StartTiming(), fluent=tv_waiting_time(tv),
                                    value=Minus(silo_access_timestamp(silo_access), tv_timestamp(tv)),
                                    value_applies_in_sim_effect=False)


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

    actions = []
    tv_waits_for_unload_options = [None] if problem_settings.silo_planning_type is conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY else [True, False]

    for tv_waits_for_unload in tv_waits_for_unload_options:
        actions.append( ActionUnloadAtSilo(fluents_manager=fluents_manager,
                                           tv_waits_for_unload=tv_waits_for_unload,
                                           problem_settings=problem_settings) )
    return actions
