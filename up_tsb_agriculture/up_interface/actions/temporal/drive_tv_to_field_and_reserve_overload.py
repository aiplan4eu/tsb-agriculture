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


class ActionDriveTvToFieldAndReserveOverload(DurativeAction):
    """ Durative action related to 'drive transport vehicle to a field (if needed) and reserve the next overload in the field'. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_RESERVE_OVERLOAD = 'drive_tv_from_init_loc_to_field_and_reserve_overload'
        DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_RESERVE_OVERLOAD_TV_FULL = 'drive_tv_from_init_loc_to_field_and_reserve_overload_tv_full'
        DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_RESERVE_OVERLOAD_TV_NOT_FULL = 'drive_tv_from_init_loc_to_field_and_reserve_overload_tv_not_full'
        DRIVE_TV_FROM_FAP_TO_FIELD_AND_RESERVE_OVERLOAD = 'drive_tv_from_fap_to_field_and_reserve_overload'
        DRIVE_TV_FROM_FAP_TO_FIELD_AND_RESERVE_OVERLOAD_TV_FULL = 'drive_tv_from_fap_to_field_and_reserve_overload_tv_full'
        DRIVE_TV_FROM_FAP_TO_FIELD_AND_RESERVE_OVERLOAD_TV_NOT_FULL = 'drive_tv_from_fap_to_field_and_reserve_overload_tv_not_full'
        DRIVE_TV_FROM_SAP_TO_FIELD_AND_RESERVE_OVERLOAD = 'drive_tv_from_sap_to_field_and_reserve_overload'
        DRIVE_TV_FROM_SAP_TO_FIELD_AND_RESERVE_OVERLOAD_TV_FULL = 'drive_tv_from_sap_to_field_and_reserve_overload_tv_full'
        DRIVE_TV_FROM_SAP_TO_FIELD_AND_RESERVE_OVERLOAD_TV_NOT_FULL = 'drive_tv_from_sap_to_field_and_reserve_overload_tv_not_full'
        RESERVE_OVERLOAD = 'reserve_overload'
        RESERVE_OVERLOAD_TV_FULL = 'reserve_overload_tv_full'
        RESERVE_OVERLOAD_TV_NOT_FULL = 'reserve_overload_tv_not_full'

    @unique
    class ParameterNames(Enum):
        """ Enum with the possible action parameters this action can have. """

        FIELD = 'field'
        TV = 'tv'
        HARV = 'harv'
        LOC_FROM = 'loc_from'
        FIELD_ACCESS = 'field_access'

    def __init__(self,
                 fluents_manager: FluentsManagerBase,
                 no_harv_object: Object,
                 no_field_object: Object,
                 no_field_access_object: Object,
                 no_silo_access_object: Object,
                 no_init_loc_object: Object,
                 loc_from_type: Type,
                 cyclic_pre_assigned_tv_turns: [bool, None],
                 case_bunker_full: Union[bool, None],  # if None -> General case
                 problem_settings: conf.GeneralProblemSettings):

        """ Creates the action based on the initialization parameters.

        If case_bunker_full is None, a general action for 'reserve overload' will be created. Otherwise,
        the 'reserve overload' will be decomposed into 'reserve overload (case: transport vehicle full after overload) '
        and 'reserve overload (case: transport vehicle not full after overload)'

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
        no_silo_access_object : Object
            Problem object corresponding to 'no silo access'
        no_init_loc_object : Object
            Problem object corresponding to 'no machine initial location'
        loc_from_type : Type
            Type of the parameter 'loc_from', i.e., the type of the current location of the transport vehicle (MachineInitLoc, FieldAccess, SiloAccess, Field)
        cyclic_pre_assigned_tv_turns : bool, None
            Flag stating whether the tv turns were pre-assigned cyclical or not. If None, no tv turns were pre-assigned.
        case_bunker_full : bool, None
            Flag stating whether the action must be created for the specific case that the transport vehicle will finish with the bunker full after the reserved overload or for the specific case that the bunker is not full. If None, the action for the general case will be created.
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        """

        effects_option = problem_settings.effects_settings.reserve_overload

        if effects_option is conf.EffectsOption.WITH_ONLY_NORMAL_EFFECTS and case_bunker_full is None:
            raise ValueError('EffectsOption.WITH_ONLY_NORMAL_EFFECTS can only be achieved with case_bunker_full != None')

        only_reserve_overload = (loc_from_type is upt.Field)

        params = {ActionDriveTvToFieldAndReserveOverload.ParameterNames.FIELD.value: upt.Field,
                  ActionDriveTvToFieldAndReserveOverload.ParameterNames.TV.value: upt.TransportVehicle,
                  ActionDriveTvToFieldAndReserveOverload.ParameterNames.HARV.value: upt.Harvester}

        if not only_reserve_overload:
            params[ActionDriveTvToFieldAndReserveOverload.ParameterNames.LOC_FROM.value] = loc_from_type
            params[ActionDriveTvToFieldAndReserveOverload.ParameterNames.FIELD_ACCESS.value] = upt.FieldAccess

        DurativeAction.__init__(self, self.__get_action_name(loc_from_type, case_bunker_full), **params)

        # ------------parameters------------

        field = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.FIELD.value)
        tv = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.TV.value)
        harv = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.HARV.value)

        loc_from = field_access = None
        if not only_reserve_overload:
            loc_from = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.LOC_FROM.value)
            field_access = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.FIELD_ACCESS.value)

        # ------------fluents to be used------------

        field_yield_mass_after_reserve = fluents_manager.get_fluent(fn.field_yield_mass_after_reserve)

        tv_transit_speed_empty = fluents_manager.get_fluent(fn.tv_transit_speed_empty)
        tv_transit_speed_full = fluents_manager.get_fluent(fn.tv_transit_speed_full)
        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)

        tv_at_from = transit_distance = no_loc_from_object = None
        if loc_from_type is upt.MachineInitLoc:
            tv_at_from = fluents_manager.get_fluent(fn.tv_at_init_loc)
            transit_distance = fluents_manager.get_fluent(fn.transit_distance_init_fap)
            no_loc_from_object = no_init_loc_object
        elif loc_from_type is upt.FieldAccess:
            tv_at_from = fluents_manager.get_fluent(fn.tv_at_field_access)
            transit_distance = fluents_manager.get_fluent(fn.transit_distance_fap_fap)
            no_loc_from_object = no_field_access_object
        elif loc_from_type is upt.SiloAccess:
            tv_at_from = fluents_manager.get_fluent(fn.tv_at_silo_access)
            transit_distance = fluents_manager.get_fluent(fn.transit_distance_sap_fap)
            no_loc_from_object = no_silo_access_object

        # ----------temporal parameters-----------

        delta_time_after_transit = 0.0
        delta_time_after_transit = max(delta_time_after_transit, problem_settings.control_windows.enable_overload_opening_time)
        delta_time_after_transit = max(delta_time_after_transit, problem_settings.cost_windows.waiting_overload_opening_time)

        infield_transit_duration = max(0.0, problem_settings.infield_transit_duration_to_field_access)  # @todo infield transit to overloading-start (fixed at the moment)

        if only_reserve_overload:
            transit_duration = get_up_real(0)
            # action_duration = infield_transit_duration + delta_time_after_transit
            action_duration = get_up_real(delta_time_after_transit)

            timing_end_transit = StartTiming()

        else:
            # speed = max_speed_empty + (bunker_mass/bunker_capacity) * (max_speed_full - max_speed_empty)
            transit_duration = Div(  # out-field transit duration
                transit_distance(loc_from, field_access),
                Plus(
                    tv_transit_speed_empty(tv),
                    Times(
                        Div(tv_bunker_mass(tv), tv_total_capacity_mass(tv)),
                        Minus(tv_transit_speed_full(tv), tv_transit_speed_empty(tv))
                    )
                )
            )

            action_duration = Plus(
                Plus(transit_duration,
                     infield_transit_duration),
                delta_time_after_transit
            )

            timing_end_transit = get_timing_before_end_timing(action_duration, delay=delta_time_after_transit)

        timing_disable_overload = get_timing_before_end_timing(action_duration,
                                                               delay=(delta_time_after_transit -
                                                                      max(0.0, problem_settings.control_windows.enable_overload_opening_time)))
        timing_enable_waiting_overload = get_timing_before_end_timing(action_duration,
                                                                      delay=(delta_time_after_transit -
                                                                             max(0.0, problem_settings.cost_windows.waiting_overload_opening_time)))

        if problem_settings.with_harv_conditions_and_effects_at_tv_arrival:
            timing_harv_preconditions_and_effects = timing_end_transit  # low planner performance and (with the current heuristics) the tvs wait until the previous overload finishes to drive&reserve
        else:
            timing_harv_preconditions_and_effects = StartTiming()  # at StartTiming the TV has to wait until the harvester is assigned to a field to start driving, even when it could have started driving to the field before

        reserved_mass_preconditions_and_effects_at_start = True
        timing_reserved_mass_preconditions_and_effects = StartTiming() if reserved_mass_preconditions_and_effects_at_start else timing_end_transit

        # ------------duration------------#

        set_duration_to_action(self, action_duration)

        tv_current_capacity = Minus(tv_total_capacity_mass(tv), tv_bunker_mass(tv))
        condition_full_capacity = LE(tv_current_capacity, field_yield_mass_after_reserve(field))

        self.__add_conditions(fluents_manager=fluents_manager,
                              case_bunker_full=case_bunker_full,
                              tv_at_from=tv_at_from,
                              transit_distance=transit_distance,
                              no_loc_from_object=no_loc_from_object,
                              no_field_object=no_field_object,
                              no_field_access_object=no_field_access_object,
                              no_harv_object=no_harv_object,
                              timing_end_transit=timing_end_transit,
                              timing_harv_preconditions_and_effects=timing_harv_preconditions_and_effects,
                              timing_reserved_mass_preconditions_and_effects=timing_reserved_mass_preconditions_and_effects,
                              condition_full_capacity=condition_full_capacity,
                              only_reserve_overload=only_reserve_overload,
                              cyclic_pre_assigned_tv_turns=cyclic_pre_assigned_tv_turns)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings,
                           case_bunker_full=case_bunker_full,
                           tv_at_from=tv_at_from,
                           transit_distance=transit_distance,
                           transit_duration=transit_duration,
                           no_loc_from_object=no_loc_from_object,
                           timing_end_transit=timing_end_transit,
                           timing_enable_waiting_overload=timing_enable_waiting_overload,
                           timing_disable_overload=timing_disable_overload,
                           timing_harv_preconditions_and_effects=timing_harv_preconditions_and_effects,
                           timing_reserved_mass_preconditions_and_effects=timing_reserved_mass_preconditions_and_effects,
                           tv_current_capacity=tv_current_capacity,
                           condition_full_capacity=condition_full_capacity,
                           only_reserve_overload=only_reserve_overload,
                           cyclic_pre_assigned_tv_turns=cyclic_pre_assigned_tv_turns)

    @staticmethod
    def __get_action_name(loc_from_type, case_bunker_full) -> str:

        """ Get the action name for the specific case. """

        if loc_from_type is upt.MachineInitLoc:
            if case_bunker_full is None:
                return ActionDriveTvToFieldAndReserveOverload.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_RESERVE_OVERLOAD.value
            elif case_bunker_full:
                return ActionDriveTvToFieldAndReserveOverload.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_RESERVE_OVERLOAD_TV_FULL.value
            return ActionDriveTvToFieldAndReserveOverload.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_RESERVE_OVERLOAD_TV_NOT_FULL.value
        elif loc_from_type is upt.FieldAccess:
            if case_bunker_full is None:
                return ActionDriveTvToFieldAndReserveOverload.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_RESERVE_OVERLOAD.value
            elif case_bunker_full:
                return ActionDriveTvToFieldAndReserveOverload.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_RESERVE_OVERLOAD_TV_FULL.value
            return ActionDriveTvToFieldAndReserveOverload.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_RESERVE_OVERLOAD_TV_NOT_FULL.value
        elif loc_from_type is upt.SiloAccess:
            if case_bunker_full is None:
                return ActionDriveTvToFieldAndReserveOverload.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_RESERVE_OVERLOAD.value
            elif case_bunker_full:
                return ActionDriveTvToFieldAndReserveOverload.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_RESERVE_OVERLOAD_TV_FULL.value
            return ActionDriveTvToFieldAndReserveOverload.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_RESERVE_OVERLOAD_TV_NOT_FULL.value
        elif loc_from_type is upt.Field:
            if case_bunker_full is None:
                return ActionDriveTvToFieldAndReserveOverload.ActionNames.RESERVE_OVERLOAD.value
            elif case_bunker_full:
                return ActionDriveTvToFieldAndReserveOverload.ActionNames.RESERVE_OVERLOAD_TV_FULL.value
            return ActionDriveTvToFieldAndReserveOverload.ActionNames.RESERVE_OVERLOAD_TV_NOT_FULL.value
        else:
            raise ValueError(f'Invalid loc_from_type')

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase,
                         case_bunker_full,
                         tv_at_from,
                         transit_distance,
                         no_loc_from_object,
                         no_field_object,
                         no_field_access_object,
                         no_harv_object,
                         timing_end_transit,
                         timing_harv_preconditions_and_effects,
                         timing_reserved_mass_preconditions_and_effects,
                         condition_full_capacity,
                         only_reserve_overload,
                         cyclic_pre_assigned_tv_turns):

        """ Add the conditions to the action. """

        # ------------parameters------------

        field = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.FIELD.value)
        tv = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.TV.value)
        harv = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.HARV.value)

        loc_from = field_access = None
        if not only_reserve_overload:
            loc_from = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.LOC_FROM.value)
            field_access = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.FIELD_ACCESS.value)

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)
        field_id = fluents_manager.get_fluent(fn.field_id)
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_yield_mass_after_reserve = fluents_manager.get_fluent(fn.field_yield_mass_after_reserve)
        field_access_field_id = fluents_manager.get_fluent(fn.field_access_field_id)

        harv_overload_count = fluents_manager.get_fluent(fn.harv_overload_count)
        harv_tv_turn = fluents_manager.get_fluent(fn.harv_tv_turn)
        harv_pre_assigned_tv_turns_left = fluents_manager.get_fluent(fn.harv_pre_assigned_tv_turns_left)

        tv_free = fluents_manager.get_fluent(fn.tv_free)
        tv_overload_id = fluents_manager.get_fluent(fn.tv_overload_id)
        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_ready_to_unload = fluents_manager.get_fluent(fn.tv_ready_to_unload)
        tv_enabled_to_drive_to_field = fluents_manager.get_fluent(fn.tv_enabled_to_drive_to_field)
        tvs_all_enabled_to_drive_to_field = fluents_manager.get_fluent(fn.tvs_all_enabled_to_drive_to_field)
        tvs_all_enabled_to_arrive_in_field = fluents_manager.get_fluent(fn.tvs_all_enabled_to_arrive_in_field)
        tv_at_field = fluents_manager.get_fluent(fn.tv_at_field)
        tv_pre_assigned_harvester = fluents_manager.get_fluent(fn.tv_pre_assigned_harvester)
        tv_pre_assigned_turn = fluents_manager.get_fluent(fn.tv_pre_assigned_turn)

        tv_can_load = fluents_manager.get_fluent(fn.tv_can_load)

        # ------------conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action( self, Not( planning_failed() ), StartTiming() )

        # the field has not been harvested
        add_precondition_to_action( self, Not( field_harvested(field) ), StartTiming() )

        # the objects are valid
        add_precondition_to_action( self, Not( Equals(field, no_field_object) ), StartTiming() )
        add_precondition_to_action( self, Not( Equals(harv, no_harv_object) ), StartTiming() )
        if not only_reserve_overload:
            add_precondition_to_action( self, Not( Equals(loc_from, no_loc_from_object) ), StartTiming() )
            add_precondition_to_action( self, Not( Equals(field_access, no_field_access_object) ), StartTiming() )

        # check if the machines are available
        add_precondition_to_action( self, tv_free(tv), StartTiming() )

        # the transport vehicle is not currently at a silo ready to unload
        if tv_ready_to_unload is not None:
            add_precondition_to_action( self, Not( tv_ready_to_unload(tv) ), StartTiming() )

        # the transport vehicle is not currently at a silo ready to unload
        add_precondition_to_action( self, LT( tv_overload_id(tv), 0 ), StartTiming() )

        # the tv has no pre_assigned harvester or the harvester is the pre_assigned harvester
        add_precondition_to_action( self,
                                    Or( Equals( tv_pre_assigned_harvester(tv), no_harv_object ),
                                        Equals( tv_pre_assigned_harvester(tv), harv ) ) ,
                                    StartTiming() )

        if cyclic_pre_assigned_tv_turns is not None:
            # the harvester has no pre-assigned turns (left) or tv pre-assigned turn is the next harvester turn
            # Note: if cyclic,
            # - harv_pre_assigned_tv_turns_left remains the same
            # - tv_pre_assigned_turn increases by harv_pre_assigned_tv_turns_left
            # Note: if not cyclic,
            # - harv_pre_assigned_tv_turns_left decreases by one
            add_precondition_to_action( self,
                                        Or(
                                            LT(harv_pre_assigned_tv_turns_left(harv), 1),   # the harvester has no pre-assigned turns left
                                            Equals(
                                                tv_pre_assigned_turn(tv),
                                                Plus(harv_tv_turn(harv), 1)
                                            )  # tv pre-assigned turn is the next harvester turn
                                        ),
                                        timing_harv_preconditions_and_effects )

        if only_reserve_overload:
            # the machine is at loc_from
            add_precondition_to_action( self, Equals( tv_at_field(tv), field ) , StartTiming() )
        else:
            # the field access is an access point of the field
            add_precondition_to_action( self, Equals( field_id(field), field_access_field_id(field_access) ) , StartTiming() )

            # the machine is at loc_from
            add_precondition_to_action( self, Equals( tv_at_from(tv), loc_from ) , StartTiming() )

            # # the transport vehicle is not currently in a field
            # add_precondition_to_action( self,
            #                             Not( Equals( location_type( machine_at(tv) ), upt.LOC_TYPE_FIELD ) ),
            #                             StartTiming() )

            # there is a valid connection between the machine location and the field_access
            add_precondition_to_action( self,
                                        GE ( transit_distance( loc_from , field_access), 0 ),
                                        StartTiming() )

            if tv_enabled_to_drive_to_field is not None and tvs_all_enabled_to_drive_to_field is not None:
                # The window to drive to a field is enabled
                add_precondition_to_action(self,
                                           Or(tv_enabled_to_drive_to_field(tv), tvs_all_enabled_to_drive_to_field()),
                                           StartTiming())

            if tvs_all_enabled_to_arrive_in_field is not None:
                # The window to arrive in a field is enabled
                add_precondition_to_action(self,
                                           tvs_all_enabled_to_arrive_in_field(field),
                                           timing_end_transit)

        # the transport vehicle has enough capacity
        add_precondition_to_action( self, tv_can_load( tv ), StartTiming() )

        # _capacity_threshold = 0.8
        # add_precondition_to_action( self,
        #                             LE ( Div( tv_bunker_mass( tv ), tv_total_capacity_mass( tv ) ),
        #                                  get_up_real(_capacity_threshold) ),
        #                             StartTiming() )

        if case_bunker_full is not None:  # check the specific conditions for the given bunker state after reserve
            add_precondition_to_action( self,
                                        condition_full_capacity if case_bunker_full else Not(condition_full_capacity),
                                        timing_reserved_mass_preconditions_and_effects )
            condition_full_capacity = None

        # preconditions at the time the TV arrives at the field

        # the field has a harvester assigned to it
        add_precondition_to_action(self,
                                   GE(harv_overload_count(harv), 0),
                                   timing_harv_preconditions_and_effects)

        # the field has a harvester assigned to it
        add_precondition_to_action(self, Equals(field_harvester(field), harv), timing_harv_preconditions_and_effects)

        # # allow the TV only to arrive when it is its turn to overload  #@todo does not work when the reservation is done for a harvester that is not in the field
        # # add_precondition_to_action(self, Not(harv_overloading(harv)), timing_end_transit)
        # if timing_harv_preconditions_and_effects == timing_end_transit:  # tv_overload_id(tv) and harv_overload_count(harv) have not been set
        #     add_precondition_to_action(self,
        #                                And(
        #                                    GE( harv_overload_count(harv), 0 ),
        #                                    Equals( harv_overload_count(harv), harv_overload_id(harv) )
        #                                ),
        #                                timing_end_transit)
        # else: # tv_overload_id(tv) and harv_overload_count(harv) were set at StartTiming
        #     add_precondition_to_action(self, Equals(tv_overload_id(tv), Plus( harv_overload_id(harv), 1)), timing_end_transit)


        # the field has yield to be overloaded (after all currently planned overloads)
        add_precondition_to_action(self, GT(field_yield_mass_after_reserve(field), get_up_real(0)), timing_reserved_mass_preconditions_and_effects)

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings,
                      case_bunker_full,
                      tv_at_from,
                      transit_distance,
                      transit_duration,
                      no_loc_from_object,
                      timing_end_transit,
                      timing_enable_waiting_overload,
                      timing_disable_overload,
                      timing_harv_preconditions_and_effects,
                      timing_reserved_mass_preconditions_and_effects,
                      tv_current_capacity,
                      condition_full_capacity,
                      only_reserve_overload,
                      cyclic_pre_assigned_tv_turns
    ):

        """ Add the effects to the action. """

        effects_option = problem_settings.effects_settings.reserve_overload

        # ------------parameters------------

        field = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.FIELD.value)
        tv = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.TV.value)
        harv = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.HARV.value)
        if not only_reserve_overload:
            loc_from = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.LOC_FROM.value)
            field_access = self.parameter(ActionDriveTvToFieldAndReserveOverload.ParameterNames.FIELD_ACCESS.value)

        # ------------fluents to be used------------

        field_yield_mass_after_reserve = fluents_manager.get_fluent(fn.field_yield_mass_after_reserve)
        total_yield_mass_in_fields_unreserved = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unreserved)
        total_yield_mass_reserved = fluents_manager.get_fluent(fn.total_yield_mass_reserved)
        total_yield_mass_potentially_reserved = fluents_manager.get_fluent(fn.total_yield_mass_potentially_reserved)

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)
        harv_overload_count = fluents_manager.get_fluent(fn.harv_overload_count)
        harv_overload_id = fluents_manager.get_fluent(fn.harv_overload_id)
        harv_overloading = fluents_manager.get_fluent(fn.harv_overloading)
        harv_enabled_to_overload = fluents_manager.get_fluent(fn.harv_enabled_to_overload)
        harv_tv_turn = fluents_manager.get_fluent(fn.harv_tv_turn)
        harv_pre_assigned_tv_turns_left = fluents_manager.get_fluent(fn.harv_pre_assigned_tv_turns_left)

        tv_free = fluents_manager.get_fluent(fn.tv_free)
        tv_at_field = fluents_manager.get_fluent(fn.tv_at_field)
        tv_transit_speed_empty = fluents_manager.get_fluent(fn.tv_transit_speed_empty)
        tv_transit_speed_full = fluents_manager.get_fluent(fn.tv_transit_speed_full)
        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_overload_id = fluents_manager.get_fluent(fn.tv_overload_id)
        tv_mass_to_overload = fluents_manager.get_fluent(fn.tv_mass_to_overload)
        tv_transit_time = fluents_manager.get_fluent(fn.tv_transit_time)
        tvs_waiting_to_overload_ref_count = fluents_manager.get_fluent(fn.tvs_waiting_to_overload_ref_count)
        tv_ready_to_overload = fluents_manager.get_fluent(fn.tv_ready_to_overload)
        tv_waiting_to_overload_id = fluents_manager.get_fluent(fn.tv_waiting_to_overload_id)
        tv_waiting_to_overload = fluents_manager.get_fluent(fn.tv_waiting_to_overload)
        tv_ready_to_drive = fluents_manager.get_fluent(fn.tv_ready_to_drive)
        tv_waiting_to_drive_id = fluents_manager.get_fluent(fn.tv_waiting_to_drive_id)
        tv_waiting_to_drive = fluents_manager.get_fluent(fn.tv_waiting_to_drive)
        tv_pre_assigned_turn = fluents_manager.get_fluent(fn.tv_pre_assigned_turn)

        tv_can_load = fluents_manager.get_fluent(fn.tv_can_load)

        # ------------effects------------

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
            _tv = actual_params.get(tv)
            _harv = actual_params.get(harv)

            _loc_from = _field_access = None
            if not only_reserve_overload:
                _loc_from = actual_params.get(loc_from)
                _field_access = actual_params.get(field_access)

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'+++++++++++++++++++ [state {id(state)}] ::  {self.name} sim effect [{timing}] - {_tv} - {_field} - {_harv}')

            _total_yield_mass_in_fields_unreserved = float(state.get_value(total_yield_mass_in_fields_unreserved()).constant_value())
            _total_yield_mass_reserved = float(state.get_value(total_yield_mass_reserved()).constant_value())
            _total_yield_mass_potentially_reserved = float(state.get_value(total_yield_mass_potentially_reserved()).constant_value())
            _field_yield_mass = float(state.get_value(field_yield_mass_after_reserve(_field)).constant_value())

            _harv_overload_count = int(state.get_value(harv_overload_count(_harv)).constant_value())

            _tv_total_capacity_mass = float(state.get_value(tv_total_capacity_mass(_tv)).constant_value())
            _tv_bunker_mass = float(state.get_value(tv_bunker_mass(_tv)).constant_value())
            _tv_overload_id = int(state.get_value(tv_overload_id(_tv)).constant_value())

            _tv_transit_time = _transit_duration = _tv_ready_to_overload = _tvs_waiting_to_overload_ref_count = None

            if tv_ready_to_overload is not None:
                _tv_ready_to_overload = int(state.get_value(tv_ready_to_overload(_tv)).constant_value())
            if tvs_waiting_to_overload_ref_count is not None:
                _tvs_waiting_to_overload_ref_count = int(state.get_value(tvs_waiting_to_overload_ref_count()).constant_value())

            _tv_current_capacity = _tv_total_capacity_mass - _tv_bunker_mass
            mass_to_overload = min(_tv_current_capacity, _field_yield_mass)
            next_field_yield_mass = max(0.0, _field_yield_mass - _tv_current_capacity)

            if not only_reserve_overload:
                _transit_distance = float(state.get_value(transit_distance(_loc_from, _field_access)).constant_value())
                _tv_transit_speed_empty = float(state.get_value(tv_transit_speed_empty(_tv)).constant_value())
                _tv_transit_speed_full = float(state.get_value(tv_transit_speed_full(_tv)).constant_value())
                _transit_duration = (_transit_distance /
                                     ( _tv_transit_speed_empty +
                                       ( _tv_transit_speed_full - _tv_transit_speed_empty)
                                         * _tv_bunker_mass / _tv_total_capacity_mass
                                       )
                                     )

                _tv_transit_time = float(state.get_value(tv_transit_time(_tv)).constant_value())

            ret_vals = []

            for fl, val in effects_values.items():
                if val[0] is not None and val[1]:  # give priority to values that were set already
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0] )
                    continue

                if fl is tv_mass_to_overload(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(mass_to_overload))  # tv_mass_to_overload(tv)
                elif fl is field_yield_mass_after_reserve(field):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(next_field_yield_mass))  # field_yield_mass_after_reserve(field)
                elif fl is total_yield_mass_in_fields_unreserved():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_total_yield_mass_in_fields_unreserved - mass_to_overload))  # total_yield_mass_in_fields_unreserved()
                elif fl is total_yield_mass_reserved():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_total_yield_mass_reserved + mass_to_overload))  # total_yield_mass_reserved()
                elif fl is total_yield_mass_potentially_reserved():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_total_yield_mass_potentially_reserved + mass_to_overload))  # total_yield_mass_potentially_reserved()
                elif fl is harv_overload_count(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_harv_overload_count + 1))  # harv_overload_count(harv)
                elif fl is tv_overload_id(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_harv_overload_count + 1))  # tv_overload_id(tv)
                elif fl is tv_transit_time(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _tv_transit_time + _transit_duration ))  # tv_transit_time(tv)
                elif tv_at_from is not None and fl is tv_at_from(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   ObjectExp(problem.object(no_loc_from_object.name)))  # tv_at_from(tv)
                elif fl is tv_at_field(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _field)  # tv_at_field(tv)
                elif tv_waiting_to_overload_id is not None and fl is tv_waiting_to_overload_id(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_tv_ready_to_overload * _tvs_waiting_to_overload_ref_count) )  # tv_waiting_to_overload_id(tv)
                elif tvs_waiting_to_overload_ref_count is not None and fl is tvs_waiting_to_overload_ref_count():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_tv_ready_to_overload + _tvs_waiting_to_overload_ref_count) )  # tvs_waiting_to_overload_ref_count()
                elif harv_enabled_to_overload is not None \
                        and fl is harv_enabled_to_overload(harv) \
                        and timing == timing_end_transit:

                    _harv_enabled_to_overload = int(state.get_value(harv_enabled_to_overload(_harv)).constant_value())
                    _harv_overloading = state.get_value(harv_overloading(_harv)).bool_constant_value()
                    _harv_overload_id = int(state.get_value(harv_overload_id(_harv)).constant_value())

                    if timing_harv_preconditions_and_effects == timing_end_transit:  # tv_overload_id(tv) and harv_overload_count(harv) have not been set
                        _val = _harv_overload_count + 1 \
                            if ( not _harv_overloading and _harv_overload_count == _harv_overload_id ) \
                            else _harv_enabled_to_overload
                    else:  # tv_overload_id(tv) and harv_overload_count(harv) were set at StartTiming
                        _val = _tv_overload_id \
                            if ( not _harv_overloading and (_harv_overload_id + 1) == _tv_overload_id ) \
                            else _harv_enabled_to_overload

                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, Int( _val ))  # harv_enabled_to_overload(harv)

                elif harv_enabled_to_overload is not None \
                        and fl is harv_enabled_to_overload(harv) \
                        and timing == timing_disable_overload:
                    _harv_enabled_to_overload = int(state.get_value(harv_enabled_to_overload(_harv)).constant_value())
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int( -1
                                                                        if ( _harv_enabled_to_overload == _tv_overload_id )
                                                                        else _harv_enabled_to_overload ) )  # harv_enabled_to_overload(harv)
                elif fl is harv_pre_assigned_tv_turns_left(harv):
                    _harv_pre_assigned_tv_turns_left = int(state.get_value(harv_pre_assigned_tv_turns_left(_harv)).constant_value())
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_harv_pre_assigned_tv_turns_left - 1))  # harv_pre_assigned_tv_turns_left(harv)
                elif fl is harv_tv_turn(harv):
                    _harv_tv_turn = int(state.get_value(harv_tv_turn(_harv)).constant_value())
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_harv_tv_turn+1))  # harv_tv_turn(harv)
                elif fl is tv_pre_assigned_turn(tv):
                    _harv_pre_assigned_tv_turns_left = int(state.get_value(harv_pre_assigned_tv_turns_left(_harv)).constant_value())
                    _tv_pre_assigned_turn = int(state.get_value(tv_pre_assigned_turn(_tv)).constant_value())
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_tv_pre_assigned_turn + _harv_pre_assigned_tv_turns_left))  # tv_pre_assigned_turn(tv)

                # unexpected fluent
                else:
                    raise ValueError(f'Unexpected fluent {fl} in simulated effect')

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'------------------- {self.name} sim effect [{timing}] - {_tv} - {_field} - {_harv}')

            return ret_vals

        effects_handler = EffectsHandler()

        effects_handler.add(timing=StartTiming(), fluent=tv_free(tv), value=Bool(False), value_applies_in_sim_effect=True)
        effects_handler.add(timing=timing_end_transit, fluent=tv_free(tv), value=Bool(True), value_applies_in_sim_effect=True)

        if cyclic_pre_assigned_tv_turns is not None:

            effects_handler.add(timing=timing_harv_preconditions_and_effects,
                                fluent=harv_tv_turn(harv),
                                value=Plus(harv_tv_turn(harv), 1),
                                value_applies_in_sim_effect=False)

            if not cyclic_pre_assigned_tv_turns:
                # Note: if not cyclic,
                # - harv_pre_assigned_tv_turns_left decreases by one
                effects_handler.add(timing=timing_harv_preconditions_and_effects,
                                    fluent=harv_pre_assigned_tv_turns_left(harv),
                                    value=Minus(harv_pre_assigned_tv_turns_left(harv), 1),
                                    value_applies_in_sim_effect=False)
            else:
                # Note: if cyclic,
                # - harv_pre_assigned_tv_turns_left remains the same
                # - tv_pre_assigned_turn increases by harv_pre_assigned_tv_turns_left
                effects_handler.add(timing=timing_harv_preconditions_and_effects,
                                    fluent=tv_pre_assigned_turn(tv),
                                    value=Plus(tv_pre_assigned_turn(tv), harv_pre_assigned_tv_turns_left(harv)),
                                    value_applies_in_sim_effect=False)

        if not only_reserve_overload:
            effects_handler.add(timing=StartTiming(), fluent=tv_at_from(tv), value=no_loc_from_object, value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_end_transit, fluent=tv_at_field(tv), value=field, value_applies_in_sim_effect=False)
            effects_handler.add(timing=StartTiming(), fluent=tv_transit_time(tv), value=Plus(tv_transit_time(tv), transit_duration), value_applies_in_sim_effect=False)

            if tv_waiting_to_drive is not None:  # @todo Remove when the tv_waiting_to_drive_id approach is working
                effects_handler.add(timing=StartTiming(), fluent=tv_waiting_to_drive(tv), value=Bool(False), value_applies_in_sim_effect=True)

            if tv_ready_to_drive is not None and tv_waiting_to_drive_id is not None:
                effects_handler.add(timing=StartTiming(), fluent=tv_ready_to_drive(tv), value=Int(0), value_applies_in_sim_effect=True)
                effects_handler.add(timing=StartTiming(), fluent=tv_waiting_to_drive_id(tv), value=Int(0), value_applies_in_sim_effect=True)

        if tv_waiting_to_overload is not None:  # @todo Remove when the tv_waiting_to_overload_id approach is working
            effects_handler.add(timing=timing_enable_waiting_overload, fluent=tv_waiting_to_overload(tv), value=Bool(True), value_applies_in_sim_effect=True)

        if tv_ready_to_overload is not None \
                and tv_waiting_to_overload_id is not None \
                and tvs_waiting_to_overload_ref_count is not None:
            effects_handler.add(timing=StartTiming(), fluent=tv_ready_to_overload(tv), value=Int(1), value_applies_in_sim_effect=True)

            # @note: if the tv started overloading between StartTiming and timing_enable_waiting_overload, the tv_ready_to_overload(tv) must be 0 at timing_enable_waiting_overload
            effects_handler.add(timing=timing_enable_waiting_overload,
                                fluent=tv_waiting_to_overload_id(tv),
                                value=Times( tv_ready_to_overload(tv), tvs_waiting_to_overload_ref_count()),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=timing_enable_waiting_overload,
                                fluent=tvs_waiting_to_overload_ref_count(),
                                value=Plus( tvs_waiting_to_overload_ref_count(), tv_ready_to_overload(tv) ),
                                value_applies_in_sim_effect=False)

        effects_handler.add(timing=timing_harv_preconditions_and_effects, fluent=harv_overload_count(harv), value=Plus( harv_overload_count(harv), 1 ), value_applies_in_sim_effect=False)
        effects_handler.add(timing=timing_harv_preconditions_and_effects, fluent=tv_overload_id(tv), value=Plus( harv_overload_count(harv), 1 ), value_applies_in_sim_effect=False)

        if harv_enabled_to_overload is not None:

            if effects_option == conf.EffectsOption.WITH_ONLY_NORMAL_EFFECTS:
                raise NotImplementedError(f'enable_overload_opening_time is only implemented when using simulated effects or conditional effects')

            if timing_harv_preconditions_and_effects == timing_end_transit:  # tv_overload_id(tv) and harv_overload_count(harv) have not been set
                effects_handler.add(timing=timing_end_transit,  # == timing_harv_preconditions_and_effects
                                    fluent=harv_enabled_to_overload(harv),
                                    value=Plus( harv_overload_count(harv), 1 ),
                                    value_applies_in_sim_effect=False,
                                    condition=And(
                                                Not( harv_overloading(harv) ),
                                                Equals( harv_overload_count(harv), harv_overload_id(harv) )
                                              )  # only set it when the harvester is not overloading and the next TV to overload is this one
                                    )
            else:
                effects_handler.add(timing=timing_end_transit,  # tv_overload_id(tv) and harv_overload_count(harv) were set at StartTiming
                                    fluent=harv_enabled_to_overload(harv),
                                    value=tv_overload_id(tv),
                                    value_applies_in_sim_effect=False,
                                    condition=And(
                                                Not( harv_overloading(harv) ),
                                                Equals( Plus( harv_overload_id(harv), 1), tv_overload_id(tv) )
                                              )  # only set it when the harvester is not overloading and the next TV to overload is this one
                                    )

            effects_handler.add(timing=timing_disable_overload,
                                fluent=harv_enabled_to_overload(harv),
                                value=Int(-1),
                                value_applies_in_sim_effect=False,
                                condition=Equals( harv_enabled_to_overload(harv), tv_overload_id(tv) ) )

        # ------------conditional effects------------

        # if condition_full_capacity
        if case_bunker_full is None or case_bunker_full:
            effects_handler.add(timing=timing_reserved_mass_preconditions_and_effects,
                                fluent=tv_mass_to_overload(tv),
                                value=tv_current_capacity,
                                value_applies_in_sim_effect=False,
                                condition=condition_full_capacity if case_bunker_full is None else None)
            effects_handler.add(timing=timing_reserved_mass_preconditions_and_effects,
                                fluent=field_yield_mass_after_reserve(field),
                                value=Minus( field_yield_mass_after_reserve(field), tv_current_capacity ),
                                value_applies_in_sim_effect=False,
                                condition=condition_full_capacity if case_bunker_full is None else None)
            effects_handler.add(timing=timing_reserved_mass_preconditions_and_effects,
                                fluent=total_yield_mass_in_fields_unreserved(),
                                value=Minus( total_yield_mass_in_fields_unreserved(), tv_current_capacity ),
                                value_applies_in_sim_effect=False,
                                condition=condition_full_capacity if case_bunker_full is None else None)
            effects_handler.add(timing=timing_reserved_mass_preconditions_and_effects,
                                fluent=total_yield_mass_reserved(),
                                value=Plus( total_yield_mass_reserved(), tv_current_capacity ),
                                value_applies_in_sim_effect=False,
                                condition=condition_full_capacity if case_bunker_full is None else None)

            effects_handler.add(timing=StartTiming(),
                                fluent=total_yield_mass_potentially_reserved(),
                                value=Plus( total_yield_mass_potentially_reserved(), tv_current_capacity ),
                                value_applies_in_sim_effect=False,
                                condition=condition_full_capacity if case_bunker_full is None else None)

        # if not condition_full_capacity
        if case_bunker_full is None or not case_bunker_full:
            condition_not_full_capacity = None if condition_full_capacity is None else Not(condition_full_capacity)
            effects_handler.add(timing=timing_reserved_mass_preconditions_and_effects,
                                fluent=tv_mass_to_overload(tv),
                                value=field_yield_mass_after_reserve(field),
                                value_applies_in_sim_effect=False,
                                condition=condition_not_full_capacity if case_bunker_full is None else None)
            effects_handler.add(timing=timing_reserved_mass_preconditions_and_effects,
                                fluent=field_yield_mass_after_reserve(field),
                                value=get_up_real(0),
                                value_applies_in_sim_effect=(case_bunker_full is not None),
                                condition=condition_not_full_capacity if case_bunker_full is None else None)
            effects_handler.add(timing=timing_reserved_mass_preconditions_and_effects,
                                fluent=total_yield_mass_in_fields_unreserved(),
                                value=Minus( total_yield_mass_in_fields_unreserved(), field_yield_mass_after_reserve(field) ),
                                value_applies_in_sim_effect=False,
                                condition=condition_not_full_capacity if case_bunker_full is None else None)
            effects_handler.add(timing=timing_reserved_mass_preconditions_and_effects,
                                fluent=total_yield_mass_reserved(),
                                value=Plus( total_yield_mass_reserved(), field_yield_mass_after_reserve(field) ),
                                value_applies_in_sim_effect=False,
                                condition=condition_not_full_capacity if case_bunker_full is None else None)

            effects_handler.add(timing=StartTiming(),
                                fluent=total_yield_mass_potentially_reserved(),
                                value=Plus( total_yield_mass_potentially_reserved(), field_yield_mass_after_reserve(field) ),
                                value_applies_in_sim_effect=False,
                                condition=condition_not_full_capacity if case_bunker_full is None else None)

        effects_handler.add_effects_to_action(action=self,
                                              effects_option=effects_option,
                                              sim_effect_cb=sim_effects_cb)


def __get_actions_drive_tv_from_loc_to_field_and_reserve_overload(fluents_manager: FluentsManagerBase,
                                                                  loc_from_type,
                                                                  no_harv_object: Object,
                                                                  no_field_object: Object,
                                                                  no_field_access_object: Object,
                                                                  no_silo_access_object: Object,
                                                                  no_init_loc_object: Object,
                                                                  cyclic_pre_assigned_tv_turns: bool,
                                                                  problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings) \
        -> List[Action]:

    """ Get all actions for 'drive transport vehicle from a specific location type to a field and reserve the next overload' activities based on the given inputs options and problem settings.

    Parameters
    ----------
    fluents_manager : FluentsManagerBase
        Fluents manager used to create the problem
    loc_from_type : Type
        Type of the parameter 'loc_from', i.e., the type of the current location of the transport vehicle (MachineInitLoc, FieldAccess, SiloAccess, Field)
    no_harv_object : Object
        Problem object corresponding to 'no harvester'
    no_field_object : Object
        Problem object corresponding to 'no field'
    no_field_access_object : Object
        Problem object corresponding to 'no field access'
    no_silo_access_object : Object
        Problem object corresponding to 'no silo access'
    no_init_loc_object : Object
        Problem object corresponding to 'no machine initial location'
    cyclic_pre_assigned_tv_turns : bool, None
        Flag stating whether the tv turns were pre-assigned cyclical or not. If None, no tv turns were pre-assigned.
    problem_settings : conf.GeneralProblemSettings
        Problem settings

    Returns
    -------
    actions : List[Action]
        All actions for 'drive transport vehicle from a specific location type to a field and reserve the next overload' activities based on the given inputs options and problem settings.
    """

    if problem_settings.effects_settings.do_overload is conf.EffectsOption.WITH_ONLY_NORMAL_EFFECTS \
            or problem_settings.action_decomposition_settings.reserve_overload:
        return [
                ActionDriveTvToFieldAndReserveOverload(fluents_manager=fluents_manager,
                                                       no_harv_object=no_harv_object,
                                                       no_field_object=no_field_object,
                                                       no_field_access_object=no_field_access_object,
                                                       no_silo_access_object=no_silo_access_object,
                                                       no_init_loc_object=no_init_loc_object,
                                                       loc_from_type=loc_from_type,
                                                       cyclic_pre_assigned_tv_turns= cyclic_pre_assigned_tv_turns,
                                                       case_bunker_full=True,
                                                       problem_settings=problem_settings),
                ActionDriveTvToFieldAndReserveOverload(fluents_manager=fluents_manager,
                                                       no_harv_object=no_harv_object,
                                                       no_field_object=no_field_object,
                                                       no_field_access_object=no_field_access_object,
                                                       no_silo_access_object=no_silo_access_object,
                                                       no_init_loc_object=no_init_loc_object,
                                                       loc_from_type=loc_from_type,
                                                       cyclic_pre_assigned_tv_turns= cyclic_pre_assigned_tv_turns,
                                                       case_bunker_full=False,
                                                       problem_settings=problem_settings)
                ]
    return [ ActionDriveTvToFieldAndReserveOverload(fluents_manager=fluents_manager,
                                                    no_harv_object=no_harv_object,
                                                    no_field_object=no_field_object,
                                                    no_field_access_object=no_field_access_object,
                                                    no_silo_access_object=no_silo_access_object,
                                                    no_init_loc_object=no_init_loc_object,
                                                    loc_from_type=loc_from_type,
                                                    cyclic_pre_assigned_tv_turns= cyclic_pre_assigned_tv_turns,
                                                    case_bunker_full=None,
                                                    problem_settings=problem_settings) ]

def get_actions_drive_tv_from_locs_to_field_and_reserve_overload(fluents_manager: FluentsManagerBase,
                                                                 no_harv_object: Object,
                                                                 no_field_object: Object,
                                                                 no_field_access_object: Object,
                                                                 no_silo_access_object: Object,
                                                                 no_init_loc_object: Object,
                                                                 cyclic_pre_assigned_tv_turns: Union[bool, None],
                                                                 problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings,
                                                                 include_from_init_loc = True,
                                                                 include_from_field = True) \
        -> List[Action]:

    """ Get all actions for 'drive transport vehicle from its location to a field (if needed) and reserve the next overload' activities based on the given inputs options and problem settings.

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
    no_silo_access_object : Object
        Problem object corresponding to 'no silo access'
    no_init_loc_object : Object
        Problem object corresponding to 'no machine initial location'
    cyclic_pre_assigned_tv_turns : bool, None
        Flag stating whether the tv turns were pre-assigned cyclical or not. If None, no tv turns were pre-assigned.
    include_from_init_loc : bool
        Flag stating if actions corresponding to 'drive transport vehicle from initial location to field' must be included or not (if no transport vehicles are located at MachineInitLoc, it is not necessary to add these actions)
    include_from_field : bool
        Flag stating if actions corresponding to 'reserve overload for transport vehicles already at the field' must be included or not (if no transport vehicles are located at a Field, it is not necessary to add these actions)
    problem_settings : conf.GeneralProblemSettings
        Problem settings

    Returns
    -------
    actions : List[Action]
        All actions for 'drive transport vehicle from its location to a field (if needed) and reserve the next overload' activities based on the given inputs options and problem settings.

    """

    actions = []
    loc_from_types = [upt.FieldAccess, upt.SiloAccess]
    if include_from_init_loc:
        loc_from_types.append(upt.MachineInitLoc)
    if include_from_field:
        loc_from_types.append(upt.Field)
    for loc_from_type in loc_from_types:
        actions.extend( __get_actions_drive_tv_from_loc_to_field_and_reserve_overload(fluents_manager=fluents_manager,
                                                                                      loc_from_type=loc_from_type,
                                                                                      no_harv_object=no_harv_object,
                                                                                      no_field_object=no_field_object,
                                                                                      no_field_access_object=no_field_access_object,
                                                                                      no_silo_access_object=no_silo_access_object,
                                                                                      no_init_loc_object=no_init_loc_object,
                                                                                      cyclic_pre_assigned_tv_turns=cyclic_pre_assigned_tv_turns,
                                                                                      problem_settings=problem_settings) )
    return actions
