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


class ActionDriveToSilo(DurativeAction):
    """ Durative action related to 'drive transport vehicle to a silo access/unloading point (if needed)' with optional 'do unload at silo access point'. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        DRIVE_TV_FROM_INIT_LOC_TO_SILO = 'drive_tv_from_init_loc_to_silo'
        DRIVE_TV_FROM_INIT_LOC_TO_SILO_AND_UNLOAD = 'drive_tv_from_init_loc_to_silo_and_unload'
        DRIVE_TV_FROM_FAP_TO_SILO = 'drive_tv_from_fap_to_silo'
        DRIVE_TV_FROM_FAP_TO_SILO_AND_UNLOAD = 'drive_tv_from_fap_to_silo_and_unload'
        INIT_TV_AT_SILO_ACCESS = 'init_tv_at_silo_access'
        INIT_TV_AT_SILO_ACCESS_AND_UNLOAD = 'init_tv_at_silo_access_and_unload'

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
            Flag stating whether the 'unload' must be included in the action. The unloaded yield will be added directly to the silo and not to the silo access
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        """

        without_transit = False
        if loc_from_type is upt.MachineInitLoc:
            action_name = ActionDriveToSilo.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_SILO_AND_UNLOAD.value \
                                        if include_unload \
                                        else ActionDriveToSilo.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_SILO.value
        elif loc_from_type is upt.FieldAccess:
            action_name = ActionDriveToSilo.ActionNames.DRIVE_TV_FROM_FAP_TO_SILO_AND_UNLOAD.value \
                                        if include_unload \
                                        else ActionDriveToSilo.ActionNames.DRIVE_TV_FROM_FAP_TO_SILO.value
        elif loc_from_type is upt.SiloAccess:
            without_transit = True
            action_name = ActionDriveToSilo.ActionNames.INIT_TV_AT_SILO_ACCESS_AND_UNLOAD.value \
                if include_unload \
                else ActionDriveToSilo.ActionNames.INIT_TV_AT_SILO_ACCESS.value
        else:
            raise ValueError(f'Invalid loc_from_type')

        params = {ActionDriveToSilo.ParameterNames.TV.value: upt.TransportVehicle,
                  ActionDriveToSilo.ParameterNames.SILO.value: upt.Silo,
                  ActionDriveToSilo.ParameterNames.SILO_ACCESS.value: upt.SiloAccess}

        if not without_transit:
            params[ActionDriveToSilo.ParameterNames.LOC_FROM.value] = loc_from_type

        DurativeAction.__init__(self, action_name, **params)

        # ------------parameters------------

        tv = self.parameter(ActionDriveToSilo.ParameterNames.TV.value)
        silo = self.parameter(ActionDriveToSilo.ParameterNames.SILO.value)
        silo_access = self.parameter(ActionDriveToSilo.ParameterNames.SILO_ACCESS.value)

        loc_from = None
        if not without_transit:
            loc_from = self.parameter(ActionDriveToSilo.ParameterNames.LOC_FROM.value)

        # ------------fluents to be used------------
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

        delta_time_after_unload = 0.0

        if include_unload:
            delta_time_after_unload = max(delta_time_after_unload,
                                          problem_settings.control_windows.enable_driving_tvs_to_field_opening_time)
            delta_time_after_unload = max(delta_time_after_unload,
                                          problem_settings.cost_windows.waiting_drive_from_silo_opening_time)

            unload_duration = Div( tv_bunker_mass(tv), tv_unloading_speed_mass(tv) )
            action_duration = Plus( Plus( transit_duration, unload_duration),
                                    delta_time_after_unload)

            timing_end = get_timing_before_end_timing(action_duration, delay=delta_time_after_unload)
            timing_disable_driving = get_timing_before_end_timing(action_duration,
                                                                  delay=(delta_time_after_unload -
                                                                         max(0.0, problem_settings.control_windows.enable_driving_tvs_to_field_opening_time )))
            timing_enable_waiting_drive = get_timing_before_end_timing(action_duration,
                                                                       delay=(delta_time_after_unload -
                                                                              max(0.0, problem_settings.cost_windows.waiting_drive_from_silo_opening_time)))
        else:
            action_duration = transit_duration
            # timing_end = get_timing_before_end_timing(action_duration, None)
            timing_end = EndTiming() if not without_transit else StartTiming()
            timing_disable_driving = timing_enable_waiting_drive = None

        set_duration_to_action(self, action_duration)

        self.__add_conditions(fluents_manager=fluents_manager,
                              tv_at_from=tv_at_from,
                              transit_distance=transit_distance,
                              no_silo_access_object=no_silo_access_object,
                              no_loc_from_object=no_loc_from_object,
                              without_transit=without_transit)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings,
                           include_unload=include_unload,
                           tv_at_from=tv_at_from,
                           transit_distance=transit_distance,
                           transit_duration=transit_duration,
                           no_loc_from_object=no_loc_from_object,
                           timing_end=timing_end,
                           timing_enable_waiting_drive=timing_enable_waiting_drive,
                           timing_disable_driving=timing_disable_driving,
                           without_transit=without_transit)

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase,
                         tv_at_from,
                         transit_distance,
                         no_silo_access_object,
                         no_loc_from_object,
                         without_transit):

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

        tv_free = fluents_manager.get_fluent(fn.tv_free)
        tv_enabled_to_drive_to_silo = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_silo)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_ready_to_unload = fluents_manager.get_fluent(fn.tv_ready_to_unload)

        tv_can_unload = fluents_manager.get_fluent(fn.tv_can_unload)

        # ------------conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action( self, Not( planning_failed() ), StartTiming() )

        # the objects are valid
        add_precondition_to_action( self, Not( Equals(silo_access, no_silo_access_object) ), StartTiming() )
        if not without_transit:
            add_precondition_to_action( self, Not( Equals(loc_from, no_loc_from_object) ), StartTiming() )

        # check if the access point belongs to the silo
        add_precondition_to_action( self, Equals( silo_access_silo_id(silo_access), silo_id(silo) ), StartTiming() )

        # check if the transport vehicle is available
        add_precondition_to_action( self, tv_free(tv), StartTiming() )
        # add_precondition_to_action( self, tv_free(tv), ClosedTimeInterval(StartTiming(), timing_end) )

        # # the transport vehicle is not currently in a field
        # add_precondition_to_action( self,
        #                             Not( Equals( location_type( tv_at(tv) ), upt.LOC_TYPE_FIELD ) ),
        #                             StartTiming() )

        # the transport vehicle is not currently at a silo ready to unload
        if tv_ready_to_unload is not None:
            add_precondition_to_action( self, Not( tv_ready_to_unload(tv) ), StartTiming() )

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

            if tv_enabled_to_drive_to_silo is not None:
                # the action must be planned while the planning window is open
                add_precondition_to_action( self, tv_enabled_to_drive_to_silo(tv), StartTiming() )

        # the transport vehicle has yield to transport to the silo
        add_precondition_to_action( self, tv_can_unload(tv), StartTiming() )
        add_precondition_to_action( self, GT ( tv_bunker_mass(tv) , get_up_real(0) ), StartTiming() )

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings,
                      include_unload,
                      tv_at_from,
                      transit_distance,
                      transit_duration,
                      no_loc_from_object,
                      timing_end,
                      timing_enable_waiting_drive,
                      timing_disable_driving,
                      without_transit):

        """ Add the effects to the action. """

        effects_option = problem_settings.effects_settings.drive_to_silo

        # ------------parameters------------

        tv = self.parameter(ActionDriveToSilo.ParameterNames.TV.value)
        silo = self.parameter(ActionDriveToSilo.ParameterNames.SILO.value)
        silo_access = self.parameter(ActionDriveToSilo.ParameterNames.SILO_ACCESS.value)
        if not without_transit:
            loc_from = self.parameter(ActionDriveToSilo.ParameterNames.LOC_FROM.value)

        # ------------fluents to be used------------

        silo_available_capacity_mass = fluents_manager.get_fluent(fn.silo_available_capacity_mass)
        total_yield_mass_in_silos = fluents_manager.get_fluent(fn.total_yield_mass_in_silos)
        total_yield_mass_reserved_in_silos = fluents_manager.get_fluent(fn.total_yield_mass_reserved_in_silos)

        tv_free = fluents_manager.get_fluent(fn.tv_free)
        tv_at_silo_access = fluents_manager.get_fluent(fn.tv_at_silo_access)
        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        tv_transit_speed_empty = fluents_manager.get_fluent(fn.tv_transit_speed_empty)
        tv_transit_speed_full = fluents_manager.get_fluent(fn.tv_transit_speed_full)
        tv_enabled_to_drive_to_silo = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_silo)
        tv_enabled_to_drive_to_field = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_field)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_transit_time = fluents_manager.get_fluent(fn.tv_transit_time)
        tv_ready_to_drive = fluents_manager.get_fluent(fn.tv_ready_to_drive)
        tv_waiting_to_drive_id = fluents_manager.get_fluent(fn.tv_waiting_to_drive_id)
        tvs_waiting_to_drive_ref_count = fluents_manager.get_fluent(fn.tvs_waiting_to_drive_ref_count)
        tv_ready_to_unload = fluents_manager.get_fluent(fn.tv_ready_to_unload)
        tv_waiting_to_drive = fluents_manager.get_fluent(fn.tv_waiting_to_drive)

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

            _silo_available_capacity_mass = _total_yield_mass_reserved_in_silos = _total_yield_mass_in_silos = None
            _tv_transit_time = _transit_duration = _tv_ready_to_drive = _tvs_waiting_to_drive_ref_count = None

            if tv_ready_to_drive is not None:
                _tv_ready_to_drive = int(state.get_value(tv_ready_to_drive(_tv)).constant_value())
            if tvs_waiting_to_drive_ref_count is not None:
                _tvs_waiting_to_drive_ref_count = int(state.get_value(tvs_waiting_to_drive_ref_count()).constant_value())

            if not without_transit:
                _transit_distance = float(state.get_value(transit_distance(_loc_from, _silo_access)).constant_value())
                _transit_duration = ( _transit_distance /
                                      ( _tv_transit_speed_empty +
                                        ( _tv_transit_speed_full - _tv_transit_speed_empty )
                                          * _tv_bunker_mass / _tv_total_capacity_mass )
                                      )

            if tv_transit_time(tv) in effects_values.keys():
                _tv_transit_time = float(state.get_value(tv_transit_time(_tv)).constant_value())

            if silo_available_capacity_mass(silo) in effects_values.keys():
                _silo_available_capacity_mass = float(state.get_value(silo_available_capacity_mass(_silo)).constant_value())

            if total_yield_mass_reserved_in_silos() in effects_values.keys():
                _total_yield_mass_reserved_in_silos = float(state.get_value(total_yield_mass_reserved_in_silos()).constant_value())

            if total_yield_mass_in_silos() in effects_values.keys():
                _total_yield_mass_in_silos = float(state.get_value(total_yield_mass_in_silos()).constant_value())

            ret_vals = []

            for fl, val in effects_values.items():
                if val[0] is not None and val[1]:  # give priority to values that were set already
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0] )
                    continue

                if fl is silo_available_capacity_mass(silo):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _silo_available_capacity_mass - _tv_bunker_mass ) )
                elif fl is total_yield_mass_reserved_in_silos():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _total_yield_mass_reserved_in_silos + _tv_bunker_mass) )
                elif tv_at_from is not None and fl is tv_at_from(tv):
                    _no_loc_from_object = ObjectExp(problem.object(no_loc_from_object.name))
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _no_loc_from_object )
                elif fl is tv_at_silo_access(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _silo_access )
                elif fl is tv_transit_time(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _tv_transit_time + _transit_duration ) )
                elif fl is total_yield_mass_in_silos():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _total_yield_mass_in_silos + _tv_bunker_mass )  )

                # end of unload
                elif tv_waiting_to_drive_id is not None and \
                        fl is tv_waiting_to_drive_id(tv) \
                        and timing == timing_enable_waiting_drive:
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_tv_ready_to_drive * _tvs_waiting_to_drive_ref_count))  # tv_waiting_to_drive_id(tv)
                elif tvs_waiting_to_drive_ref_count is not None and \
                        fl is tvs_waiting_to_drive_ref_count() \
                        and timing == timing_enable_waiting_drive:
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_tv_ready_to_drive + _tvs_waiting_to_drive_ref_count))  # tvs_waiting_to_drive_ref_count()

                # unexpected fluent
                else:
                    raise ValueError(f'Unexpected fluent {fl} in simulated effect')

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'------------------- {self.name} sim effect [{timing}] - {_tv} - {_silo} - {_silo_access}')

            return ret_vals

        effects_handler = EffectsHandler()

        effects_handler.add(timing=StartTiming(), fluent=silo_available_capacity_mass(silo), value=Minus(silo_available_capacity_mass(silo), tv_bunker_mass(tv)), value_applies_in_sim_effect=False)

        effects_handler.add(timing=StartTiming(), fluent=total_yield_mass_reserved_in_silos(), value=Plus(total_yield_mass_reserved_in_silos(), tv_bunker_mass(tv)), value_applies_in_sim_effect=False)

        if StartTiming() != timing_end:
            effects_handler.add(timing=StartTiming(), fluent=tv_free(tv), value=Bool(False), value_applies_in_sim_effect=True)
            effects_handler.add(timing=timing_end, fluent=tv_free(tv), value=Bool(True), value_applies_in_sim_effect=True)

        if not without_transit:
            effects_handler.add(timing=StartTiming(), fluent=tv_at_from(tv), value=no_loc_from_object, value_applies_in_sim_effect=False)

            effects_handler.add(timing=StartTiming(), fluent=tv_transit_time(tv), value=Plus(tv_transit_time(tv), transit_duration), value_applies_in_sim_effect=False)

            if tv_waiting_to_drive is not None:  # @todo Remove when the tv_waiting_to_drive_id approach is working
                effects_handler.add(timing=StartTiming(), fluent=tv_waiting_to_drive(tv), value=Bool(False), value_applies_in_sim_effect=True)

            if tv_ready_to_drive is not None and tv_waiting_to_drive_id is not None:
                effects_handler.add(timing=StartTiming(), fluent=tv_ready_to_drive(tv), value=Int(0), value_applies_in_sim_effect=True)
                effects_handler.add(timing=StartTiming(), fluent=tv_waiting_to_drive_id(tv), value=Int(0), value_applies_in_sim_effect=True)

            effects_handler.add(timing=timing_end, fluent=tv_at_silo_access(tv), value=silo_access, value_applies_in_sim_effect=False)

        if not include_unload and tv_ready_to_unload is not None:
            effects_handler.add(timing=timing_end, fluent=tv_ready_to_unload(tv), value=Bool(True), value_applies_in_sim_effect=True)

        effects_handler.add(timing=StartTiming(), fluent=tv_can_unload(tv), value=Bool(False), value_applies_in_sim_effect=True)

        if tv_enabled_to_drive_to_silo is not None:
            effects_handler.add(timing=StartTiming(), fluent=tv_enabled_to_drive_to_silo(tv), value=Bool(False), value_applies_in_sim_effect=True)

        if include_unload:
            effects_handler.add(timing=timing_end, fluent=total_yield_mass_in_silos(), value=Plus(total_yield_mass_in_silos(), tv_bunker_mass(tv)), value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_end, fluent=tv_bunker_mass(tv), value=get_up_real(0), value_applies_in_sim_effect=True)

            if tv_ready_to_unload is not None:
                effects_handler.add(timing=timing_end, fluent=tv_ready_to_unload(tv), value=Bool(False), value_applies_in_sim_effect=True)

            if tv_waiting_to_drive is not None:  # @todo Remove when the tv_waiting_to_drive_id approach is working
                effects_handler.add(timing=timing_enable_waiting_drive, fluent=tv_waiting_to_drive(tv), value=Bool(True), value_applies_in_sim_effect=True)

            if tv_ready_to_drive is not None and tv_waiting_to_drive_id is not None and tvs_waiting_to_drive_ref_count is not None:
                effects_handler.add(timing=timing_end, fluent=tv_ready_to_drive(tv), value=Int(1), value_applies_in_sim_effect=True)

                # @note: if the tv started driving between timing_end_overload/timing_exit_field and timing_enable_waiting_drive, the tv_ready_to_drive(tv) must be 0 at timing_enable_waiting_drive
                effects_handler.add(timing=timing_enable_waiting_drive,
                                    fluent=tv_waiting_to_drive_id(tv),
                                    value=Times(tv_ready_to_drive(tv), tvs_waiting_to_drive_ref_count()),
                                    value_applies_in_sim_effect=False)
                effects_handler.add(timing=timing_enable_waiting_drive,
                                    fluent=tvs_waiting_to_drive_ref_count(),
                                    value=Plus(tvs_waiting_to_drive_ref_count(), tv_ready_to_drive(tv)),
                                    value_applies_in_sim_effect=False)

            if tv_enabled_to_drive_to_field is not None:
                # Enable an x seconds window for the 'drive_tv_to_field' action
                effects_handler.add(timing=timing_end, fluent=tv_enabled_to_drive_to_field(tv), value=Bool(True), value_applies_in_sim_effect=True)
                effects_handler.add(timing=timing_disable_driving, fluent=tv_enabled_to_drive_to_field(tv), value=Bool(False), value_applies_in_sim_effect=True)

            effects_handler.add(timing=timing_end, fluent=tv_can_load(tv), value=Bool(True), value_applies_in_sim_effect=True)

        effects_handler.add_effects_to_action(action=self,
                                              effects_option=effects_option,
                                              sim_effect_cb=sim_effects_cb)


def get_actions_drive_tv_from_loc_to_silo(fluents_manager: FluentsManagerBase,
                                          no_field_access_object: Object,
                                          no_silo_access_object: Object,
                                          no_init_loc_object: Object,
                                          problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings,
                                          include_from_init_loc=True
                                          ) \
        -> List[Action]:

    """ Get all actions for 'drive transport vehicle to a silo access/unloading point' activities based on the given inputs options and problem settings.

    This action will not include unload disregarding the corresponding setting in problem_settings.

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

    Returns
    -------
    actions : List[Action]
        All actions for 'drive transport vehicle to a silo access/unloading point (if needed) and unload' activities based on the given inputs options and problem settings.

    """

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
                                          problem_settings=problem_settings) )
    return actions


def get_actions_drive_tv_from_loc_to_silo_and_unload(fluents_manager: FluentsManagerBase,
                                                     no_field_access_object: Object,
                                                     no_silo_access_object: Object,
                                                     no_init_loc_object: Object,
                                                     problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings,
                                                     include_from_init_loc=True,
                                                     include_from_silo_access=True
                                                     ) \
        -> List[Action]:

    """ Get all actions for 'drive transport vehicle to a silo access/unloading point (if needed) and unload' activities based on the given inputs options and problem settings.

    This action will include unload right after reaching the silo access point disregarding the corresponding setting in problem_settings.
    The unloaded yield will be added directly to the silo and not to the silo access.
    No checks for silo access availability are included.

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

    for loc_from_type in loc_from_types:
        actions.append( ActionDriveToSilo(fluents_manager=fluents_manager,
                                          no_field_access_object=no_field_access_object,
                                          no_silo_access_object=no_silo_access_object,
                                          no_init_loc_object=no_init_loc_object,
                                          loc_from_type=loc_from_type,
                                          include_unload=True,
                                          problem_settings=problem_settings) )
    return actions