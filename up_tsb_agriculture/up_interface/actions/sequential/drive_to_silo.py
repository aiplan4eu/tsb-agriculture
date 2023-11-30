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


class ActionDriveToSilo(InstantaneousAction):
    """ Instantaneous action related to 'drive transport vehicle to a silo access/unloading point (if needed)' with optional 'do unload at silo access point'. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        DRIVE_TV_FROM_INIT_LOC_TO_SILO = 'drive_tv_from_init_loc_to_silo'
        DRIVE_TV_FROM_INIT_LOC_TO_SILO_AND_UNLOAD = 'drive_tv_from_init_loc_to_silo_and_unload'
        DRIVE_TV_FROM_INIT_LOC_TO_SILO_AND_UNLOAD_TV_WAITS = 'drive_tv_from_init_loc_to_silo_and_unload_tv_waits'
        DRIVE_TV_FROM_FAP_TO_SILO = 'drive_tv_from_fap_to_silo'
        DRIVE_TV_FROM_FAP_TO_SILO_AND_UNLOAD = 'drive_tv_from_fap_to_silo_and_unload'
        DRIVE_TV_FROM_FAP_TO_SILO_AND_UNLOAD_TV_WAITS = 'drive_tv_from_fap_to_silo_and_unload_tv_waits'
        INIT_TV_AT_SILO_ACCESS = 'init_tv_at_silo_access'
        INIT_TV_AT_SILO_ACCESS_AND_UNLOAD = 'init_tv_at_silo_access_and_unload'
        INIT_TV_AT_SILO_ACCESS_AND_UNLOAD_TV_WAITS = 'init_tv_at_silo_access_and_unload_tv_waits'

    @unique
    class ParameterNames(Enum):
        """ Enum with the possible action parameters this action can have. """

        TV = 'tv'
        SILO = 'silo'
        SILO_ACCESS = 'silo_access'
        LOC_FROM = 'loc_from'

    def __init__(self,
                 fluents_manager: FluentsManagerBase,
                 no_field_access_object: Object,
                 no_silo_access_object: Object,
                 no_init_loc_object: Object,
                 loc_from_type,
                 include_unload: bool,
                 tv_waits_for_unload: Optional[bool],
                 problem_settings: conf.GeneralProblemSettings):

        """ Creates the action based on the initialization parameters.

        Parameters
        ----------
        fluents_manager : FluentsManagerBase
            Fluents manager used to create the problem
        no_field_access_object : Object
            Problem object corresponding to 'no field access'
        no_silo_access_object : Object
            Problem object corresponding to 'no silo access'
        no_init_loc_object : Object
            Problem object corresponding to 'no machine initial location'
        loc_from_type : Type
            Type of the parameter 'loc_from', i.e., the type of the current location of the transport vehicle (MachineInitLoc, FieldAccess)
        include_unload : bool
            Flag stating whether the 'unload' must be included in the action.
        tv_waits_for_unload : bool, None
            Flag stating whether the action must be created for the specific case that the transport vehicle has to wait at the silo access to unload or for the specific case that it does not wait to unload. If None, the action for the general case will be created. Only relevant if include_unload==True.
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        """

        without_transit = (loc_from_type is upt.SiloAccess)
        action_name = self.__get_action_name(loc_from_type, include_unload, tv_waits_for_unload)

        params = {ActionDriveToSilo.ParameterNames.TV.value: upt.TransportVehicle,
                  ActionDriveToSilo.ParameterNames.SILO.value: upt.Silo,
                  ActionDriveToSilo.ParameterNames.SILO_ACCESS.value: upt.SiloAccess}

        if not without_transit:
            params[ActionDriveToSilo.ParameterNames.LOC_FROM.value] = loc_from_type

        InstantaneousAction.__init__(self, action_name, **params)

        # ------------parameters------------

        tv = self.parameter(ActionDriveToSilo.ParameterNames.TV.value)
        silo = self.parameter(ActionDriveToSilo.ParameterNames.SILO.value)
        silo_access = self.parameter(ActionDriveToSilo.ParameterNames.SILO_ACCESS.value)
        loc_from = None
        if not without_transit:
            loc_from = self.parameter(ActionDriveToSilo.ParameterNames.LOC_FROM.value)

        # ------------fluents to be used------------

        silo_access_timestamp = fluents_manager.get_fluent(fn.silo_access_timestamp)

        tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)
        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        tv_transit_speed_empty = fluents_manager.get_fluent(fn.tv_transit_speed_empty)
        tv_transit_speed_full = fluents_manager.get_fluent(fn.tv_transit_speed_full)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_unloading_speed_mass = fluents_manager.get_fluent(fn.tv_unloading_speed_mass)

        tv_at_from = transit_distance = no_loc_from_object = None
        if loc_from_type is upt.MachineInitLoc:
            tv_at_from = fluents_manager.get_fluent(fn.tv_at_init_loc)
            transit_distance = fluents_manager.get_fluent(fn.transit_distance_init_sap)
            no_loc_from_object = no_init_loc_object
        elif loc_from_type is upt.FieldAccess:
            tv_at_from = fluents_manager.get_fluent(fn.tv_at_field_access)
            transit_distance = fluents_manager.get_fluent(fn.transit_distance_fap_sap)
            no_loc_from_object = no_field_access_object
        elif loc_from_type is upt.SiloAccess:
            tv_at_from = fluents_manager.get_fluent(fn.tv_at_silo_access)

        # ----------temporal parameters-----------

        if without_transit:
            transit_duration = get_up_real(0)
        else:
            # speed = max_speed_empty + (bunker_mass/bunker_capacity) * (max_speed_full - max_speed_empty)
            transit_duration = Div(
                                    transit_distance( loc_from , silo_access ),
                                    Plus(
                                        tv_transit_speed_empty(tv),
                                        Times(
                                            Div(tv_bunker_mass(tv), tv_total_capacity_mass(tv)),
                                            Minus(tv_transit_speed_full(tv), tv_transit_speed_empty(tv))
                                        )
                                    )
                               )

        if include_unload:
            unload_duration = Div( tv_bunker_mass(tv), tv_unloading_speed_mass(tv) )
        else:
            unload_duration = get_up_real(0)

        transit_finish_timestamp = Plus(tv_timestamp(tv), transit_duration)
        unload_start_timestamp = None
        if include_unload:
            if tv_waits_for_unload is None or not tv_waits_for_unload:
                unload_start_timestamp = transit_finish_timestamp
            else:
                if silo_access_timestamp is None:
                    raise ValueError('Option-case tv_waits not supported by current configuration')
                unload_start_timestamp = silo_access_timestamp(silo_access)
            action_finish_timestamp = Plus(unload_start_timestamp, unload_duration)
        else:
            action_finish_timestamp = transit_finish_timestamp

        self.__add_conditions(fluents_manager=fluents_manager,
                              tv_at_from=tv_at_from,
                              transit_distance=transit_distance,
                              transit_duration=transit_duration,
                              transit_finish_timestamp=transit_finish_timestamp,
                              unload_start_timestamp=unload_start_timestamp,
                              action_finish_timestamp=action_finish_timestamp,
                              no_silo_access_object=no_silo_access_object,
                              no_loc_from_object=no_loc_from_object,
                              without_transit=without_transit,
                              tv_waits_for_unload=tv_waits_for_unload)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings,
                           include_unload=include_unload,
                           tv_at_from=tv_at_from,
                           transit_distance=transit_distance,
                           transit_duration=transit_duration,
                           unload_duration=unload_duration,
                           transit_finish_timestamp=transit_finish_timestamp,
                           unload_start_timestamp=unload_start_timestamp,
                           action_finish_timestamp=action_finish_timestamp,
                           no_loc_from_object=no_loc_from_object,
                           without_transit=without_transit,
                           tv_waits_for_unload=tv_waits_for_unload)

    @staticmethod
    def __get_action_name(loc_from_type,
                          include_unload: bool,
                          tv_waits_for_unload: Optional[bool]) -> str:

        """ Get the action name for the specific case. """

        if loc_from_type is upt.MachineInitLoc:
            if include_unload:
                if tv_waits_for_unload is None or not tv_waits_for_unload:
                    return ActionDriveToSilo.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_SILO_AND_UNLOAD.value
                return ActionDriveToSilo.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_SILO_AND_UNLOAD_TV_WAITS.value
            return ActionDriveToSilo.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_SILO.value
        elif loc_from_type is upt.FieldAccess:
            if include_unload:
                if tv_waits_for_unload is None or not tv_waits_for_unload:
                    return ActionDriveToSilo.ActionNames.DRIVE_TV_FROM_FAP_TO_SILO_AND_UNLOAD.value
                return ActionDriveToSilo.ActionNames.DRIVE_TV_FROM_FAP_TO_SILO_AND_UNLOAD_TV_WAITS.value
            return ActionDriveToSilo.ActionNames.DRIVE_TV_FROM_FAP_TO_SILO.value
        elif loc_from_type is upt.SiloAccess:
            if include_unload:
                if tv_waits_for_unload is None or not tv_waits_for_unload:
                    return ActionDriveToSilo.ActionNames.INIT_TV_AT_SILO_ACCESS_AND_UNLOAD.value
                return ActionDriveToSilo.ActionNames.INIT_TV_AT_SILO_ACCESS_AND_UNLOAD_TV_WAITS.value
            return ActionDriveToSilo.ActionNames.INIT_TV_AT_SILO_ACCESS.value
        else:
            raise ValueError(f'Invalid loc_from_type')

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase,
                         tv_at_from,
                         transit_distance,
                         transit_duration,
                         transit_finish_timestamp,
                         unload_start_timestamp,
                         action_finish_timestamp,
                         no_silo_access_object,
                         no_loc_from_object,
                         without_transit,
                         tv_waits_for_unload):

        """ Add the conditions to the action. """

        # ------------parameters------------

        tv = self.parameter(ActionDriveToSilo.ParameterNames.TV.value)
        silo = self.parameter(ActionDriveToSilo.ParameterNames.SILO.value)
        silo_access = self.parameter(ActionDriveToSilo.ParameterNames.SILO_ACCESS.value)
        loc_from = None
        if not without_transit:
            loc_from = self.parameter(ActionDriveToSilo.ParameterNames.LOC_FROM.value)

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)
        silo_id = fluents_manager.get_fluent(fn.silo_id)
        silo_available_capacity_mass = fluents_manager.get_fluent(fn.silo_available_capacity_mass)
        silo_access_silo_id = fluents_manager.get_fluent(fn.silo_access_silo_id)
        silo_access_timestamp = fluents_manager.get_fluent(fn.silo_access_timestamp)

        tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_can_unload = fluents_manager.get_fluent(fn.tv_can_unload)

        # ------------pre-conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action( self, Not( planning_failed() ), StartTiming() )

        # the objects are valid
        add_precondition_to_action( self, Not( Equals(silo_access, no_silo_access_object) ), StartTiming() )
        if not without_transit:
            add_precondition_to_action( self, Not( Equals(loc_from, no_loc_from_object) ), StartTiming() )

        # check if the access point belongs to the silo
        add_precondition_to_action( self, Equals( silo_access_silo_id(silo_access), silo_id(silo) ), StartTiming() )

        # the silo has enough capacity for the yield
        add_precondition_to_action( self,
                                    GE ( silo_available_capacity_mass(silo), tv_bunker_mass(tv) ),
                                    StartTiming()  # ClosedTimeInterval(StartTiming(), timing_end)
                                    )

        if without_transit:
            # the machine is at the silo access
            add_precondition_to_action( self, Equals( tv_at_from(tv), silo_access ) , StartTiming() )

        else:
            # the machine is at loc_from
            add_precondition_to_action( self, Equals( tv_at_from(tv), loc_from ) , StartTiming() )

            # there is a valid connection between the machine location and the silo_access
            add_precondition_to_action( self,
                                        GE ( transit_distance( loc_from , silo_access), 0 ),
                                        StartTiming() )

        # the transport vehicle has yield to transport to the silo
        add_precondition_to_action( self, tv_can_unload(tv), StartTiming() )
        add_precondition_to_action( self, GT ( tv_bunker_mass(tv) , get_up_real(0) ), StartTiming() )

        # check the tv and sap timestamps for silo access availability
        if tv_waits_for_unload is not None:
            if silo_access_timestamp is None:
                raise ValueError('Option-case tv_waits not supported by current configuration')
            if tv_waits_for_unload:
                add_precondition_to_action( self, LT ( transit_finish_timestamp, silo_access_timestamp(silo_access) ), StartTiming() )
            else:
                add_precondition_to_action( self, GE ( transit_finish_timestamp, silo_access_timestamp(silo_access) ), StartTiming() )

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings,
                      include_unload,
                      tv_at_from,
                      transit_distance,
                      transit_duration,
                      unload_duration,
                      transit_finish_timestamp,
                      unload_start_timestamp,
                      action_finish_timestamp,
                      no_loc_from_object,
                      without_transit,
                      tv_waits_for_unload):

        """ Add the effects to the action. """

        effects_option = problem_settings.effects_settings.drive_to_silo

        # ------------parameters------------

        tv = self.parameter(ActionDriveToSilo.ParameterNames.TV.value)
        silo = self.parameter(ActionDriveToSilo.ParameterNames.SILO.value)
        silo_access = self.parameter(ActionDriveToSilo.ParameterNames.SILO_ACCESS.value)
        loc_from = None
        if not without_transit:
            loc_from = self.parameter(ActionDriveToSilo.ParameterNames.LOC_FROM.value)

        # ------------fluents to be used------------

        silo_available_capacity_mass = fluents_manager.get_fluent(fn.silo_available_capacity_mass)
        total_yield_mass_in_silos = fluents_manager.get_fluent(fn.total_yield_mass_in_silos)
        silo_access_timestamp = fluents_manager.get_fluent(fn.silo_access_timestamp)

        tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)
        tv_at_silo_access = fluents_manager.get_fluent(fn.tv_at_silo_access)
        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        tv_transit_speed_empty = fluents_manager.get_fluent(fn.tv_transit_speed_empty)
        tv_transit_speed_full = fluents_manager.get_fluent(fn.tv_transit_speed_full)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_transit_time = fluents_manager.get_fluent(fn.tv_transit_time)
        tv_waiting_time = fluents_manager.get_fluent(fn.tv_waiting_time)
        tv_unloading_speed_mass = fluents_manager.get_fluent(fn.tv_unloading_speed_mass)
        tv_ready_to_unload = fluents_manager.get_fluent(fn.tv_ready_to_unload)
        tv_can_unload = fluents_manager.get_fluent(fn.tv_can_unload)
        tv_can_load = fluents_manager.get_fluent(fn.tv_can_load)

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
            _silo = actual_params.get(silo)
            _silo_access = actual_params.get(silo_access)
            _loc_from = None
            if not without_transit:
                _loc_from = actual_params.get(loc_from)

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'+++++++++++++++++++ [state {id(state)}] ::  {self.name} sim effect [{timing}] - {_tv} - {_silo} - {_silo_access}')

            _tv_bunker_mass = float(state.get_value(tv_bunker_mass(_tv)).constant_value())
            _tv_total_capacity_mass = float(state.get_value(tv_total_capacity_mass(_tv)).constant_value())
            _tv_transit_speed_full = float(state.get_value(tv_transit_speed_full(_tv)).constant_value())
            _tv_transit_speed_empty = float(state.get_value(tv_transit_speed_empty(_tv)).constant_value())
            _tv_timestamp = float(state.get_value(tv_timestamp(_tv)).constant_value())
            _tv_waiting_time = float(state.get_value(tv_waiting_time(_tv)).constant_value())
            _tv_unloading_speed_mass = float(state.get_value(tv_unloading_speed_mass(_tv)).constant_value())
            _tv_transit_time = float(state.get_value(tv_transit_time(_tv)).constant_value())
            _silo_available_capacity_mass = float(state.get_value(silo_available_capacity_mass(_silo)).constant_value())
            _total_yield_mass_in_silos = float(state.get_value(total_yield_mass_in_silos()).constant_value())

            _transit_duration = 0
            if not without_transit:
                _transit_distance = float(state.get_value(transit_distance(_loc_from, _silo_access)).constant_value())
                _transit_duration = ( _transit_distance /
                                      ( _tv_transit_speed_empty +
                                        ( _tv_transit_speed_full - _tv_transit_speed_empty )
                                          * _tv_bunker_mass / _tv_total_capacity_mass )
                                      )
            _unload_duration = 0
            if include_unload:
                _unload_duration = _tv_bunker_mass / _tv_unloading_speed_mass

            _transit_finish_timestamp = _tv_timestamp + _transit_duration
            if tv_waits_for_unload is not None:
                _silo_access_timestamp = float(state.get_value(silo_access_timestamp(_silo_access)).constant_value())
                _unload_start_timestamp = _silo_access_timestamp if tv_waits_for_unload else _transit_finish_timestamp
                _action_finish_timestamp = _unload_start_timestamp + _unload_duration
                if tv_waits_for_unload:
                    _tv_waiting_time += max(0.0, _unload_start_timestamp - _transit_finish_timestamp )
            else:
                _action_finish_timestamp = _transit_finish_timestamp + _unload_duration

            ret_vals = []

            for fl, val in effects_values.items():
                if val[0] is not None and val[1]:  # give priority to values that were set already
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0] )
                    continue

                if fl is silo_available_capacity_mass(silo):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _silo_available_capacity_mass - _tv_bunker_mass ) )
                elif silo_access_timestamp is not None and fl is silo_access_timestamp(silo_access):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _action_finish_timestamp ) )
                elif fl is tv_timestamp(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _action_finish_timestamp ) )
                elif fl is tv_waiting_time(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _tv_waiting_time ) )
                elif tv_at_from is not None and fl is tv_at_from(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   ObjectExp(problem.object(no_loc_from_object.name)) )
                elif fl is tv_at_silo_access(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _silo_access )
                elif fl is tv_transit_time(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _tv_transit_time + _transit_duration ) )
                elif fl is total_yield_mass_in_silos():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _total_yield_mass_in_silos + _tv_bunker_mass )  )

                # unexpected fluent
                else:
                    raise ValueError(f'Unexpected fluent {fl} in simulated effect')

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'------------------- {self.name} sim effect [{timing}] - {_tv} - {_silo} - {_silo_access}')

            return ret_vals

        effects_handler = EffectsHandler()

        effects_handler.add(timing=StartTiming(), fluent=silo_available_capacity_mass(silo), value=Minus(silo_available_capacity_mass(silo), tv_bunker_mass(tv)), value_applies_in_sim_effect=False)
        effects_handler.add(timing=StartTiming(), fluent=tv_can_unload(tv), value=Bool(False), value_applies_in_sim_effect=True)

        effects_handler.add(timing=StartTiming(), fluent=tv_timestamp(tv),
                            value=action_finish_timestamp,
                            value_applies_in_sim_effect=False)
        if tv_waits_for_unload is not None:
            effects_handler.add(timing=StartTiming(), fluent=silo_access_timestamp(silo_access),
                                value=action_finish_timestamp,
                                value_applies_in_sim_effect=False)
            if tv_waits_for_unload:
                effects_handler.add(timing=StartTiming(), fluent=tv_waiting_time(tv),
                                    value=Minus(unload_start_timestamp, transit_finish_timestamp),
                                    value_applies_in_sim_effect=False)

        if not without_transit:
            effects_handler.add(timing=StartTiming(), fluent=tv_at_from(tv), value=no_loc_from_object, value_applies_in_sim_effect=False)

            effects_handler.add(timing=StartTiming(), fluent=tv_transit_time(tv), value=Plus(tv_transit_time(tv), transit_duration), value_applies_in_sim_effect=False)

            effects_handler.add(timing=StartTiming(), fluent=tv_at_silo_access(tv), value=silo_access, value_applies_in_sim_effect=False)

        if include_unload:
            effects_handler.add(timing=StartTiming(), fluent=total_yield_mass_in_silos(), value=Plus(total_yield_mass_in_silos(), tv_bunker_mass(tv)), value_applies_in_sim_effect=False)
            effects_handler.add(timing=StartTiming(), fluent=tv_bunker_mass(tv), value=get_up_real(0), value_applies_in_sim_effect=True)
            effects_handler.add(timing=StartTiming(), fluent=tv_can_load(tv), value=Bool(True), value_applies_in_sim_effect=True)
        else:
            effects_handler.add(timing=StartTiming(), fluent=tv_ready_to_unload(tv), value=Bool(True), value_applies_in_sim_effect=True)

        effects_handler.add_effects_to_action(action=self,
                                              effects_option=effects_option,
                                              sim_effect_cb=sim_effects_cb)


def get_actions_drive_tv_from_loc_to_silo(fluents_manager: FluentsManagerBase,
                                          no_field_access_object: Object,
                                          no_silo_access_object: Object,
                                          no_init_loc_object: Object,
                                          problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings,
                                          include_from_init_loc = True
                                          ) \
        -> List[Action]:

    actions = []
    loc_from_types = [upt.FieldAccess]
    if include_from_init_loc:
        loc_from_types.append(upt.MachineInitLoc)

    for loc_from_type in loc_from_types:
        actions.append( ActionDriveToSilo(fluents_manager=fluents_manager,
                                          no_field_access_object=no_field_access_object,
                                          no_silo_access_object=no_silo_access_object,
                                          no_init_loc_object=no_init_loc_object,
                                          loc_from_type=loc_from_type,
                                          include_unload=False,
                                          tv_waits_for_unload=None,
                                          problem_settings=problem_settings) )
    return actions


def get_actions_drive_tv_from_loc_to_silo_and_unload(fluents_manager: FluentsManagerBase,
                                                     no_field_access_object: Object,
                                                     no_silo_access_object: Object,
                                                     no_init_loc_object: Object,
                                                     problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings,
                                                     include_from_init_loc = True,
                                                     include_from_silo_access = True
                                                     ) \
        -> List[Action]:

    """ Get all actions for 'drive transport vehicle to a silo access/unloading point (if needed) and unload' activities based on the given inputs options and problem settings.

    This action will include unload disregarding the corresponding setting in problem_settings.

    Parameters
    ----------
    fluents_manager : FluentsManagerBase
        Fluents manager used to create the problem
    no_field_access_object : Object
        Problem object corresponding to 'no field access'
    no_silo_access_object : Object
        Problem object corresponding to 'no silo access'
    no_init_loc_object : Object
        Problem object corresponding to 'no machine initial location'
    problem_settings : conf.GeneralProblemSettings
        Problem settings
    include_from_init_loc : bool
        Flag stating if actions corresponding to 'drive transport vehicle from initial location to a silo access' must be included or not (if no transport vehicles are located at MachineInitLoc, it is not necessary to add these actions)
    include_from_silo_access : bool
        Flag stating if actions corresponding to 'unload transport vehicle at the silo access it in currently' must be included or not (if no transport vehicles are located at SiloAccess, it is not necessary to add these actions)

    Returns
    -------
    actions : List[Action]
        All actions for 'drive transport vehicle to a silo access/unloading point (if needed) and unload' activities based on the given inputs options and problem settings.

    """

    actions = []
    loc_from_types = [upt.FieldAccess]
    if include_from_init_loc:
        loc_from_types.append(upt.MachineInitLoc)
    if include_from_silo_access:
        loc_from_types.append(upt.SiloAccess)

    tv_waits_for_unload_options = [None] if problem_settings.silo_planning_type is conf.SiloPlanningType.WITHOUT_SILO_ACCESS_AVAILABILITY else [True, False]

    for loc_from_type in loc_from_types:
        for tv_waits_for_unload in tv_waits_for_unload_options:
            actions.append( ActionDriveToSilo(fluents_manager=fluents_manager,
                                              no_field_access_object=no_field_access_object,
                                              no_silo_access_object=no_silo_access_object,
                                              no_init_loc_object=no_init_loc_object,
                                              loc_from_type=loc_from_type,
                                              include_unload=True,
                                              tv_waits_for_unload=tv_waits_for_unload,
                                              problem_settings=problem_settings) )
    return actions
