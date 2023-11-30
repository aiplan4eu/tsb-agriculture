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


class ActionDriveTvToFieldAndOverload(InstantaneousAction):
    """ Instantaneous action related to 'drive transport vehicle to the field (if needed), harvest and do overload from the harvester in the field to the transport vehicle' """

    EPS_MASS_FIELD_FINISHED = 0.5
    """ If the remaining yield_mass in the field is >= this value, the field will be considered as finished. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_HARV_WAITS = 'drive_tv_from_init_loc_to_field_and_overload_harv_waits'
        DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_TV_WAITS = 'drive_tv_from_init_loc_to_field_and_overload_tv_waits'
        DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED = 'drive_tv_from_init_loc_to_field_and_overload_harv_waits_field_finished'
        DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED = 'drive_tv_from_init_loc_to_field_and_overload_tv_waits_field_finished'
        DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS = 'drive_tv_from_fap_to_field_and_overload_harv_waits'
        DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_TV_WAITS = 'drive_tv_from_fap_to_field_and_overload_tv_waits'
        DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED = 'drive_tv_from_fap_to_field_and_overload_harv_waits_field_finished'
        DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED = 'drive_tv_from_fap_to_field_and_overload_tv_waits_field_finished'
        DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS = 'drive_tv_from_sap_to_field_and_overload_harv_waits'
        DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_TV_WAITS = 'drive_tv_from_sap_to_field_and_overload_tv_waits'
        DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED = 'drive_tv_from_sap_to_field_and_overload_harv_waits_field_finished'
        DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED = 'drive_tv_from_sap_to_field_and_overload_tv_waits_field_finished'
        OVERLOAD_HARV_WAITS = 'overload_harv_waits'
        OVERLOAD_TV_WAITS = 'overload_tv_waits'
        OVERLOAD_HARV_WAITS_FIELD_FINISHED = 'overload_harv_waits_field_finished'
        OVERLOAD_TV_WAITS_FIELD_FINISHED = 'overload_tv_waits_field_finished'

    @unique
    class ParameterNames(Enum):
        """ Enum with the possible action parameters this action can have. """

        FIELD = 'field'
        TV = 'tv'
        HARV = 'harv'
        LOC_FROM = 'loc_from'
        FIELD_ACCESS = 'field_access'
        FIELD_EXIT_TV = 'field_exit_tv'
        FIELD_EXIT_HARV = 'field_exit_harv'

    class ActionCases:
        """ Class holding the specific cases for the action. """

        def __init__(self, field_finished: bool, harv_waits: bool):

            """ Class initialization.

            Parameters
            ----------
            field_finished : bool
                Flag stating whether the field is finished after the overload or not.
            harv_waits : bool
                Flag stating whether the harvester has to wait for the transport vehicle to start the harvesting/overloading or if the transport vehicle has to wait for the harvester.
            """

            self.field_finished: bool = field_finished
            self.harv_waits: bool = harv_waits

    def __init__(self,
                 fluents_manager: FluentsManagerBase,
                 no_harv_object: Object,
                 no_field_object: Object,
                 no_field_access_object: Object,
                 no_silo_access_object: Object,
                 no_init_loc_object: Object,
                 loc_from_type,
                 cyclic_pre_assigned_tv_turns: bool,
                 action_cases: Union[None, 'ActionDriveTvToFieldAndOverload.ActionCases'],  # if None -> General case
                 problem_settings: conf.GeneralProblemSettings):

        """ Creates the action based on the initialization parameters.

        If action_cases is None, a general action for 'harvest/overload' will be created. Otherwise, the 'harvest/overload' will be decomposed into
        'harvest/overload (case: harvester waits for transport vehicle and the field is finished after the overload)',
        'harvest/overload (case: harvester waits for transport vehicle and the field is not finished after the overload)',
        'harvest/overload (case: transport vehicle waits for harvester and the field is finished after the overload)',
        and 'harvest/overload (case: transport vehicle waits for harvester and the field is not finished after the overload)'

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
        action_cases : ActionDriveTvToFieldAndOverload.ActionCases, None
            Holds the action case to create the specific action. If None, the action for the general case will be created.
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        """

        effects_option = problem_settings.effects_settings.reserve_overload

        if effects_option is conf.EffectsOption.WITH_ONLY_NORMAL_EFFECTS and action_cases is None:
            raise ValueError('EffectsOption.WITH_ONLY_NORMAL_EFFECTS can only be achieved with action_cases != None')

        only_overload = ( loc_from_type is upt.Field )

        params = {self.ParameterNames.FIELD.value: upt.Field,
                  self.ParameterNames.TV.value: upt.TransportVehicle,
                  self.ParameterNames.HARV.value: upt.Harvester,
                  self.ParameterNames.FIELD_EXIT_TV.value: upt.FieldAccess}

        if not only_overload:
            params[self.ParameterNames.LOC_FROM.value] = loc_from_type
            params[self.ParameterNames.FIELD_ACCESS.value] = upt.FieldAccess
        if action_cases.field_finished:
            params[self.ParameterNames.FIELD_EXIT_HARV.value] = upt.FieldAccess

        InstantaneousAction.__init__(self, self.__get_action_name(loc_from_type, action_cases), **params)

        # ------------parameters------------

        field = self.parameter(self.ParameterNames.FIELD.value)
        tv = self.parameter(self.ParameterNames.TV.value)
        harv = self.parameter(self.ParameterNames.HARV.value)
        field_exit_tv = self.parameter(self.ParameterNames.FIELD_EXIT_TV.value)
        loc_from = field_access = field_exit_harv = None
        if not only_overload:
            loc_from = self.parameter(self.ParameterNames.LOC_FROM.value)
            field_access = self.parameter(self.ParameterNames.FIELD_ACCESS.value)
        if action_cases.field_finished:
            field_exit_harv = self.parameter(self.ParameterNames.FIELD_EXIT_HARV.value)

        # ------------fluents to be used------------

        field_yield_mass_unharvested = fluents_manager.get_fluent(fn.field_yield_mass_unharvested)

        tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)
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

        infield_transit_duration = max(0.0, problem_settings.infield_transit_duration_to_field_access)  # @todo infield transit to overloading-start (fixed at the moment)

        if only_overload:
            tv_transit_duration = get_up_real(0)
            tv_timestamp_to_field = tv_timestamp(tv)
        else:
            # speed = max_speed_empty + (bunker_mass/bunker_capacity) * (max_speed_full - max_speed_empty)
            tv_transit_duration = Div(  # out-field transit duration
                                      transit_distance(loc_from, field_access),
                                      Plus(
                                          tv_transit_speed_empty(tv),
                                          Times(
                                              Div(tv_bunker_mass(tv), tv_total_capacity_mass(tv)),
                                              Minus(tv_transit_speed_full(tv), tv_transit_speed_empty(tv))
                                          )
                                      )
                                  )
            tv_timestamp_to_field = Plus(tv_timestamp(tv),
                                         Plus(tv_transit_duration,
                                              get_up_real(infield_transit_duration)))

        tv_current_capacity = Minus(tv_total_capacity_mass(tv), tv_bunker_mass(tv))
        condition_finished_field = LT(
                                        field_yield_mass_unharvested(field),
                                        Plus( tv_current_capacity, get_up_real(self.EPS_MASS_FIELD_FINISHED) )
                                    )

        self.__add_conditions(fluents_manager=fluents_manager,
                              action_cases=action_cases,
                              tv_at_from=tv_at_from,
                              transit_distance=transit_distance,
                              tv_timestamp_to_field=tv_timestamp_to_field,
                              no_field_object=no_field_object,
                              no_field_access_object=no_field_access_object,
                              no_loc_from_object=no_loc_from_object,
                              no_harv_object=no_harv_object,
                              condition_finished_field=condition_finished_field,
                              only_overload=only_overload,
                              cyclic_pre_assigned_tv_turns=cyclic_pre_assigned_tv_turns)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings,
                           action_cases=action_cases,
                           tv_at_from=tv_at_from,
                           transit_distance=transit_distance,
                           tv_transit_duration=tv_transit_duration,
                           infield_transit_duration=infield_transit_duration,
                           tv_timestamp_to_field=tv_timestamp_to_field,
                           no_field_object=no_field_object,
                           no_loc_from_object=no_loc_from_object,
                           tv_current_capacity=tv_current_capacity,
                           condition_finished_field=condition_finished_field,
                           only_overload=only_overload,
                           cyclic_pre_assigned_tv_turns=cyclic_pre_assigned_tv_turns)

    @staticmethod
    def __get_action_name(loc_from_type, action_cases) -> str:

        """ Get the action name for the specific case. """

        if loc_from_type is upt.MachineInitLoc:
            if action_cases.harv_waits:
                if action_cases.field_finished:
                    return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value
                return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_HARV_WAITS.value
            else:
                if action_cases.field_finished:
                    return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_INIT_LOC_TO_FIELD_AND_OVERLOAD_TV_WAITS.value
        elif loc_from_type is upt.FieldAccess:
            if action_cases.harv_waits:
                if action_cases.field_finished:
                    return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value
                return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS.value
            else:
                if action_cases.field_finished:
                    return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_FAP_TO_FIELD_AND_OVERLOAD_TV_WAITS.value
        elif loc_from_type is upt.SiloAccess:
            if action_cases.harv_waits:
                if action_cases.field_finished:
                    return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS_FIELD_FINISHED.value
                return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_HARV_WAITS.value
            else:
                if action_cases.field_finished:
                    return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                return ActionDriveTvToFieldAndOverload.ActionNames.DRIVE_TV_FROM_SAP_TO_FIELD_AND_OVERLOAD_TV_WAITS.value
        elif loc_from_type is upt.Field:
            if action_cases.harv_waits:
                if action_cases.field_finished:
                    return ActionDriveTvToFieldAndOverload.ActionNames.OVERLOAD_HARV_WAITS_FIELD_FINISHED.value
                return ActionDriveTvToFieldAndOverload.ActionNames.OVERLOAD_HARV_WAITS.value
            else:
                if action_cases.field_finished:
                    return ActionDriveTvToFieldAndOverload.ActionNames.OVERLOAD_TV_WAITS_FIELD_FINISHED.value
                return ActionDriveTvToFieldAndOverload.ActionNames.OVERLOAD_TV_WAITS.value
        else:
            raise ValueError(f'Invalid loc_from_type')

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase,
                         action_cases,
                         tv_at_from,
                         transit_distance,
                         tv_timestamp_to_field,
                         no_field_object,
                         no_field_access_object,
                         no_loc_from_object,
                         no_harv_object,
                         condition_finished_field,
                         only_overload,
                         cyclic_pre_assigned_tv_turns):

        """ Add the conditions to the action. """

        # ------------parameters------------

        field = self.parameter(self.ParameterNames.FIELD.value)
        tv = self.parameter(self.ParameterNames.TV.value)
        harv = self.parameter(self.ParameterNames.HARV.value)
        field_exit_tv = self.parameter(self.ParameterNames.FIELD_EXIT_TV.value)
        loc_from = field_access = field_exit_harv = None
        if not only_overload:
            loc_from = self.parameter(self.ParameterNames.LOC_FROM.value)
            field_access = self.parameter(self.ParameterNames.FIELD_ACCESS.value)
        if action_cases.field_finished:
            field_exit_harv = self.parameter(self.ParameterNames.FIELD_EXIT_HARV.value)

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)
        field_id = fluents_manager.get_fluent(fn.field_id)
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_access_field_id = fluents_manager.get_fluent(fn.field_access_field_id)

        harv_timestamp = fluents_manager.get_fluent(fn.harv_timestamp)
        harv_at_field = fluents_manager.get_fluent(fn.harv_at_field)
        harv_tv_turn = fluents_manager.get_fluent(fn.harv_tv_turn)
        harv_pre_assigned_tv_turns_left = fluents_manager.get_fluent(fn.harv_pre_assigned_tv_turns_left)

        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_at_field = fluents_manager.get_fluent(fn.tv_at_field)
        tv_pre_assigned_harvester = fluents_manager.get_fluent(fn.tv_pre_assigned_harvester)
        tv_pre_assigned_turn = fluents_manager.get_fluent(fn.tv_pre_assigned_turn)

        tv_can_load = fluents_manager.get_fluent(fn.tv_can_load)

        # ------------pre-conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action( self, Not( planning_failed() ), StartTiming() )

        # the field has not been harvested
        add_precondition_to_action( self, Not( field_harvested(field) ), StartTiming() )

        # the objects are valid
        add_precondition_to_action( self, Not( Equals(field, no_field_object) ), StartTiming() )
        add_precondition_to_action( self, Not( Equals(harv, no_harv_object) ), StartTiming() )
        add_precondition_to_action( self, Not( Equals(field_exit_tv, no_field_access_object) ), StartTiming() )
        if loc_from is not None:
            add_precondition_to_action( self, Not( Equals(loc_from, no_loc_from_object) ), StartTiming() )
        if field_access is not None:
            add_precondition_to_action( self, Not( Equals(field_access, no_field_access_object) ), StartTiming() )
        if field_exit_harv is not None:
            add_precondition_to_action( self, Not( Equals(field_exit_harv, no_field_access_object) ), StartTiming() )

        # check timestamps for case
        if action_cases.harv_waits:
            add_precondition_to_action( self,
                                        LT(harv_timestamp(harv), tv_timestamp_to_field),
                                        StartTiming() )
        else:
            add_precondition_to_action( self,
                                        GE(harv_timestamp(harv), tv_timestamp_to_field),
                                        StartTiming()  )

        # check field state after overload for case
        if action_cases.field_finished:
            add_precondition_to_action( self, condition_finished_field, StartTiming() )
        else:
            add_precondition_to_action( self, Not( condition_finished_field ), StartTiming() )

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
                                        StartTiming()  )

        # the field exit is an access point of the field
        add_precondition_to_action( self, Equals( field_id(field), field_access_field_id(field_exit_tv) ) , StartTiming() )
        if field_exit_harv is not None:
            add_precondition_to_action( self, Equals( field_id(field), field_access_field_id(field_exit_harv) ) , StartTiming() )

        if only_overload:
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

        # the transport vehicle has enough capacity
        add_precondition_to_action( self, tv_can_load( tv ), StartTiming() )

        # _capacity_threshold = 0.8
        # add_precondition_to_action( self,
        #                             LE ( Div( tv_bunker_mass( tv ), tv_total_capacity_mass( tv ) ),
        #                                  get_up_real(_capacity_threshold) ),
        #                             StartTiming() )

        # preconditions at the time the TV arrives at the field

        # the field has a harvester assigned to it
        add_precondition_to_action(self, Equals(field_harvester(field), harv), StartTiming())

        # the harvester is at the field
        add_precondition_to_action(self, Equals(harv_at_field(harv), field), StartTiming())

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings,
                      action_cases,
                      tv_at_from,
                      transit_distance,
                      tv_transit_duration,
                      infield_transit_duration,
                      tv_timestamp_to_field,
                      no_field_object,
                      no_loc_from_object,
                      tv_current_capacity,
                      condition_finished_field,
                      only_overload,
                      cyclic_pre_assigned_tv_turns):

        effects_option = problem_settings.effects_settings.reserve_overload

        # ------------parameters------------

        field = self.parameter(self.ParameterNames.FIELD.value)
        tv = self.parameter(self.ParameterNames.TV.value)
        harv = self.parameter(self.ParameterNames.HARV.value)
        field_exit_tv = self.parameter(self.ParameterNames.FIELD_EXIT_TV.value)
        loc_from = field_access = field_exit_harv = None
        if not only_overload:
            loc_from = self.parameter(self.ParameterNames.LOC_FROM.value)
            field_access = self.parameter(self.ParameterNames.FIELD_ACCESS.value)
        if action_cases.field_finished:
            field_exit_harv = self.parameter(self.ParameterNames.FIELD_EXIT_HARV.value)

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)

        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        field_started_harvest_int = fluents_manager.get_fluent(fn.field_started_harvest_int)
        field_timestamp_harvested = fluents_manager.get_fluent(fn.field_timestamp_harvested)
        field_timestamp_started_harvest = fluents_manager.get_fluent(fn.field_timestamp_started_harvest)
        field_yield_mass_unharvested = fluents_manager.get_fluent(fn.field_yield_mass_unharvested)
        field_area_per_yield_mass = fluents_manager.get_fluent(fn.field_area_per_yield_mass)
        total_yield_mass_in_fields_unharvested = fluents_manager.get_fluent(fn.total_yield_mass_in_fields_unharvested)
        total_harvested_mass = fluents_manager.get_fluent(fn.total_harvested_mass)

        harv_timestamp = fluents_manager.get_fluent(fn.harv_timestamp)
        harv_waiting_time = fluents_manager.get_fluent(fn.harv_waiting_time)
        harv_at_field = fluents_manager.get_fluent(fn.harv_at_field)
        harv_at_field_access = fluents_manager.get_fluent(fn.harv_at_field_access)
        harv_working_time_per_area = fluents_manager.get_fluent(fn.harv_working_time_per_area)
        harv_tv_turn = fluents_manager.get_fluent(fn.harv_tv_turn)
        harv_pre_assigned_tv_turns_left = fluents_manager.get_fluent(fn.harv_pre_assigned_tv_turns_left)

        tv_timestamp = fluents_manager.get_fluent(fn.tv_timestamp)
        tv_waiting_time = fluents_manager.get_fluent(fn.tv_waiting_time)
        tv_at_field_access = fluents_manager.get_fluent(fn.tv_at_field_access)
        tv_at_field = fluents_manager.get_fluent(fn.tv_at_field)
        tv_transit_speed_empty = fluents_manager.get_fluent(fn.tv_transit_speed_empty)
        tv_transit_speed_full = fluents_manager.get_fluent(fn.tv_transit_speed_full)
        tv_total_capacity_mass = fluents_manager.get_fluent(fn.tv_total_capacity_mass)
        tv_bunker_mass = fluents_manager.get_fluent(fn.tv_bunker_mass)
        tv_transit_time = fluents_manager.get_fluent(fn.tv_transit_time)
        tv_pre_assigned_turn = fluents_manager.get_fluent(fn.tv_pre_assigned_turn)

        tv_can_load = fluents_manager.get_fluent(fn.tv_can_load)
        tv_can_unload = fluents_manager.get_fluent(fn.tv_can_unload)


        # ------------effects------------

        _capacity_threshold = 0.8
        _factor_infield_non_working_transit = 1.2  # @todo: to account for non-working transit (temporary)
        mass_to_overload = field_yield_mass_unharvested(field) if action_cases.field_finished else tv_current_capacity
        overload_duration = Times(
                                    get_up_real(_factor_infield_non_working_transit),
                                    Times(  # time needed by the harvester to cover the harvesting area
                                        harv_working_time_per_area(harv),
                                        Times(  # area to cover
                                            mass_to_overload,
                                            field_area_per_yield_mass(field)
                                        )
                                    )
                               )

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
            _field_exit_tv = actual_params.get(field_exit_tv)
            _loc_from = actual_params.get(loc_from) if loc_from is not None else None
            _field_access = actual_params.get(field_access) if field_access is not None else None
            _field_exit_harv = actual_params.get(field_exit_harv) if field_exit_harv is not None else None

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'+++++++++++++++++++ [state {id(state)}] ::  {self.name} sim effect [{timing}] - {_tv} - {_field} - {_harv}')

            _total_harvested_mass = float(state.get_value(total_harvested_mass()).constant_value())
            _total_yield_mass_in_fields_unharvested = float(state.get_value(total_yield_mass_in_fields_unharvested()).constant_value())
            _field_yield_mass_unharvested = float(state.get_value(field_yield_mass_unharvested(_field)).constant_value())
            _field_area_per_yield_mass = float(state.get_value(field_area_per_yield_mass(_field)).constant_value())
            _field_started_harvest_int = int(state.get_value(field_started_harvest_int(_field)).constant_value())
            _field_timestamp_started_harvest = float(state.get_value(field_timestamp_started_harvest(_field)).constant_value())
            _field_timestamp_harvested = float(state.get_value(field_timestamp_harvested(_field)).constant_value())
            _harv_working_time_per_area = float(state.get_value(harv_working_time_per_area(_harv)).constant_value())
            _harv_waiting_time = float(state.get_value(harv_waiting_time(_harv)).constant_value())
            _harv_timestamp = float(state.get_value(harv_timestamp(_harv)).constant_value())
            _tv_timestamp = float(state.get_value(tv_timestamp(_tv)).constant_value())
            _tv_total_capacity_mass = float(state.get_value(tv_total_capacity_mass(_tv)).constant_value())
            _tv_bunker_mass = float(state.get_value(tv_bunker_mass(_tv)).constant_value())
            _tv_waiting_time = float(state.get_value(tv_waiting_time(_tv)).constant_value())

            _tv_current_capacity = _tv_total_capacity_mass - _tv_bunker_mass
            _mass_to_overload = _field_yield_mass_unharvested if action_cases.field_finished else _tv_current_capacity
            _next_field_yield_mass = 0.0 if action_cases.field_finished else _field_yield_mass_unharvested - _mass_to_overload

            _overload_duration = _factor_infield_non_working_transit * _harv_working_time_per_area * _mass_to_overload * _field_area_per_yield_mass

            _tv_transit_duration = 0
            _infield_transit_duration_0 = 0

            _tv_transit_time = None

            if not only_overload:
                _transit_distance = float(state.get_value(transit_distance(_loc_from, _field_access)).constant_value())
                _tv_transit_speed_empty = float(state.get_value(tv_transit_speed_empty(_tv)).constant_value())
                _tv_transit_speed_full = float(state.get_value(tv_transit_speed_full(_tv)).constant_value())
                _tv_transit_duration = (_transit_distance /
                                        ( _tv_transit_speed_empty +
                                          ( _tv_transit_speed_full - _tv_transit_speed_empty)
                                            * _tv_bunker_mass / _tv_total_capacity_mass )
                                        )

                _tv_transit_time = float(state.get_value(tv_transit_time(_tv)).constant_value())
                _infield_transit_duration_0 = infield_transit_duration

            if action_cases.harv_waits:
                _harv_timestamp_new = _tv_timestamp + _tv_transit_duration + _infield_transit_duration_0 + _overload_duration + (infield_transit_duration if action_cases.field_finished else 0)
                _tv_timestamp_new = _tv_timestamp + _tv_transit_duration + _infield_transit_duration_0 + _overload_duration + infield_transit_duration
                _harv_waiting_time_new = _harv_waiting_time + _tv_timestamp + _tv_transit_duration + _infield_transit_duration_0 - _harv_timestamp
                _tv_waiting_time_new = _tv_waiting_time
                _field_timestamp_started_harvest_new = _tv_timestamp + _tv_transit_duration + _infield_transit_duration_0
            else:
                _harv_timestamp_new = _harv_timestamp + _overload_duration + (infield_transit_duration if action_cases.field_finished else 0)
                _tv_timestamp_new = _harv_timestamp + _overload_duration + infield_transit_duration
                _harv_waiting_time_new = _harv_waiting_time
                _tv_waiting_time_new = _tv_waiting_time + _harv_timestamp - ( _tv_timestamp + _tv_transit_duration + _infield_transit_duration_0)
                _field_timestamp_started_harvest_new = _harv_timestamp

            _harv_waiting_time_new = max(0.0, _harv_waiting_time_new)
            _tv_waiting_time_new = max(0.0, _tv_waiting_time_new)

            if _field_started_harvest_int > 0:
                _field_timestamp_started_harvest_new = _field_timestamp_started_harvest
            if action_cases.field_finished:
                _field_timestamp_harvested_new = _harv_timestamp_new - infield_transit_duration
            else:
                _field_timestamp_harvested_new = _field_timestamp_harvested

            ret_vals = []

            for fl, val in effects_values.items():

                # #debug!
                # print(f'   [{self.name}] fluent = {fl} ; value = {val}')

                if val[0] is not None and val[1]:  # give priority to values that were set already
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0] )
                    continue

                if fl is harv_timestamp(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_harv_timestamp_new))  # harv_timestamp(harv)
                elif fl is tv_timestamp(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_tv_timestamp_new))  # tv_timestamp(tv)
                elif fl is field_timestamp_started_harvest(field):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_field_timestamp_started_harvest_new))  # field_timestamp_started_harvest(field)
                elif fl is field_timestamp_harvested(field):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_field_timestamp_harvested))  # field_timestamp_harvested(field)
                elif fl is harv_waiting_time(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_harv_waiting_time_new))  # harv_waiting_time(harv)
                elif fl is tv_waiting_time(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_tv_waiting_time_new))  # tv_waiting_time(tv)
                elif fl is tv_bunker_mass(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_tv_bunker_mass + _mass_to_overload))  # tv_bunker_mass(tv)
                elif fl is total_harvested_mass():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_total_harvested_mass + _mass_to_overload))  # total_harvested_mass()
                elif fl is total_yield_mass_in_fields_unharvested():
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_total_yield_mass_in_fields_unharvested - _mass_to_overload))  # total_yield_mass_in_fields_unharvested()
                elif fl is field_yield_mass_unharvested(field):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_next_field_yield_mass))  # field_yield_mass_unharvested(field)
                elif fl is tv_transit_time(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _tv_transit_time + _tv_transit_duration ))  # tv_transit_time(tv)
                elif fl is harv_at_field(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   ObjectExp(problem.object(no_field_object.name)))  # harv_at_field(harv)
                elif fl is harv_at_field_access(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _field_exit_harv)  # harv_at_field_access(harv)
                elif fl is tv_at_field(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   ObjectExp(problem.object(no_field_object.name)))  # tv_at_field(tv)
                elif fl is tv_at_field_access(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _field_exit_tv)  # tv_at_field_access(tv)
                elif tv_at_from is not None and fl is tv_at_from(tv) and fl is not tv_at_field_access(tv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   ObjectExp(problem.object(no_loc_from_object.name)))  # tv_at_from(tv)
                elif fl is tv_can_load(tv):

                    _tv_can_load = Bool(True) if _tv_bunker_mass / _tv_total_capacity_mass < _capacity_threshold else Bool(False)
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _tv_can_load)  # tv_can_load(tv)
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

        # update machine timestamps
        if action_cases.harv_waits:
            effects_handler.add(timing=StartTiming(),
                                fluent=harv_timestamp(harv),
                                value=Plus( Plus( tv_timestamp_to_field,
                                                  overload_duration ),
                                            get_up_real(infield_transit_duration if action_cases.field_finished else 0) ),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=StartTiming(),
                                fluent=tv_timestamp(tv),
                                value=Plus( Plus( tv_timestamp_to_field,
                                                  overload_duration ),
                                            get_up_real(infield_transit_duration) ),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=StartTiming(),
                                fluent=harv_waiting_time(harv),
                                value=Plus(
                                            harv_waiting_time(harv),
                                            Minus( tv_timestamp_to_field, harv_timestamp(harv)),
                                        ),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=StartTiming(),
                                fluent=field_timestamp_started_harvest(field),
                                value=Plus(
                                            field_timestamp_started_harvest(field),
                                            Times( tv_timestamp_to_field,
                                                   Minus(1, field_started_harvest_int(field))),
                                        ),
                                value_applies_in_sim_effect=False)

            if action_cases.field_finished:
                effects_handler.add(timing=StartTiming(),
                                    fluent=field_timestamp_harvested(field),
                                    value=Plus( tv_timestamp_to_field,
                                                overload_duration ),
                                    value_applies_in_sim_effect=False)

        else:
            effects_handler.add(timing=StartTiming(),
                                fluent=harv_timestamp(harv),
                                value=Plus( Plus( harv_timestamp(harv),
                                                  overload_duration ),
                                            get_up_real(infield_transit_duration if action_cases.field_finished else 0) ),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=StartTiming(),
                                fluent=tv_timestamp(tv),
                                value=Plus( harv_timestamp(harv),
                                            Plus(overload_duration, get_up_real(infield_transit_duration)) ),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=StartTiming(),
                                fluent=tv_waiting_time(tv),
                                value=Plus(
                                            tv_waiting_time(tv),
                                            Minus( harv_timestamp(harv), tv_timestamp_to_field),
                                        ),
                                value_applies_in_sim_effect=False)
            effects_handler.add(timing=StartTiming(),
                                fluent=field_timestamp_started_harvest(field),
                                value=Plus(
                                            field_timestamp_started_harvest(field),
                                            Times( harv_timestamp(harv),
                                                   Minus(1, field_started_harvest_int(field))),
                                        ),
                                value_applies_in_sim_effect=False)

            if action_cases.field_finished:
                effects_handler.add(timing=StartTiming(),
                                    fluent=field_timestamp_harvested(field),
                                    value=Plus( harv_timestamp(harv),
                                                overload_duration ),
                                    value_applies_in_sim_effect=False)

        effects_handler.add(timing=StartTiming(),
                            fluent=field_started_harvest_int(field),
                            value=Int(1),
                            value_applies_in_sim_effect=True)

        # update bunker and field yield mass
        if action_cases.field_finished:
            effects_handler.add(timing=StartTiming(),
                                fluent=field_harvested(field),
                                value=Bool(True),
                                value_applies_in_sim_effect=True)
        effects_handler.add(timing=StartTiming(),
                            fluent=tv_bunker_mass(tv),
                            value=Plus( tv_bunker_mass(tv), mass_to_overload ),
                            value_applies_in_sim_effect=False)
        effects_handler.add(timing=StartTiming(),
                            fluent=total_harvested_mass(),
                            value=Plus( total_harvested_mass(), mass_to_overload ),
                            value_applies_in_sim_effect=False)
        effects_handler.add(timing=StartTiming(),
                            fluent=total_yield_mass_in_fields_unharvested(),
                            value=Minus( total_yield_mass_in_fields_unharvested(), mass_to_overload ),
                            value_applies_in_sim_effect=False)
        effects_handler.add(timing=StartTiming(),
                            fluent=field_yield_mass_unharvested(field),
                            value=Minus( field_yield_mass_unharvested(field), mass_to_overload ),
                            value_applies_in_sim_effect=False)

        if cyclic_pre_assigned_tv_turns is not None:

            effects_handler.add(timing=StartTiming(),
                                fluent=harv_tv_turn(harv),
                                value=Plus(harv_tv_turn(harv), 1),
                                value_applies_in_sim_effect=False)

            if not cyclic_pre_assigned_tv_turns:
                # Note: if not cyclic,
                # - harv_pre_assigned_tv_turns_left decreases by one
                effects_handler.add(timing=StartTiming(),
                                    fluent=harv_pre_assigned_tv_turns_left(harv),
                                    value=Minus(harv_pre_assigned_tv_turns_left(harv), 1),
                                    value_applies_in_sim_effect=False)
            else:
                # Note: if cyclic,
                # - harv_pre_assigned_tv_turns_left remains the same
                # - tv_pre_assigned_turn increases by harv_pre_assigned_tv_turns_left
                effects_handler.add(timing=StartTiming(),
                                    fluent=tv_pre_assigned_turn(tv),
                                    value=Plus(tv_pre_assigned_turn(tv), harv_pre_assigned_tv_turns_left(harv)),
                                    value_applies_in_sim_effect=False)

        effects_handler.add(timing=StartTiming(), fluent=tv_at_field_access(tv), value=field_exit_tv, value_applies_in_sim_effect=False)

        if field_exit_harv is not None:
            effects_handler.add(timing=StartTiming(), fluent=harv_at_field(harv), value=no_field_object, value_applies_in_sim_effect=False)
            effects_handler.add(timing=StartTiming(), fluent=harv_at_field_access(harv), value=field_exit_harv, value_applies_in_sim_effect=False)

        if only_overload:
            effects_handler.add(timing=StartTiming(), fluent=tv_at_field(tv), value=no_field_object, value_applies_in_sim_effect=False)
        else:
            effects_handler.add(timing=StartTiming(), fluent=tv_transit_time(tv), value=Plus(tv_transit_time(tv), tv_transit_duration), value_applies_in_sim_effect=False)
            if tv_at_from is not tv_at_field_access:
                effects_handler.add(timing=StartTiming(), fluent=tv_at_from(tv), value=no_loc_from_object, value_applies_in_sim_effect=False)

        effects_handler.add(timing=StartTiming(), fluent=tv_can_unload(tv), value=Bool(True), value_applies_in_sim_effect=True)

        effects_handler.add(timing=StartTiming(),
                            fluent=tv_can_load(tv),
                            value=LE(Div(tv_bunker_mass(tv), tv_total_capacity_mass(tv)), _capacity_threshold),
                            value_applies_in_sim_effect=False)

        effects_handler.add_effects_to_action(action=self,
                                              effects_option=effects_option,
                                              sim_effect_cb=sim_effects_cb)


def __get_actions_drive_tv_from_loc_to_field_and_overload(fluents_manager: FluentsManagerBase,
                                                          loc_from_type,
                                                          no_harv_object: Object,
                                                          no_field_object: Object,
                                                          no_field_access_object: Object,
                                                          no_silo_access_object: Object,
                                                          no_init_loc_object: Object,
                                                          cyclic_pre_assigned_tv_turns: bool,
                                                          problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings) \
        -> List[Action]:

    """ Get all actions for 'drive transport vehicle from a specific location type to a field, harvest and overload from the harvester to the transport vehicle, and drive the machine(s) to a field exit point' activities based on the given inputs options and problem settings.

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
        All actions for 'drive transport vehicle from a specific location type to a field, harvest and overload from the harvester to the transport vehicle, and drive the machine(s) to a field exit point' activities based on the given inputs options and problem settings.
    """

    actions = list()
    for field_finished in [True, False]:
        for harv_waits in [True, False]:
            action_cases = ActionDriveTvToFieldAndOverload.ActionCases(field_finished, harv_waits)
            actions.append( ActionDriveTvToFieldAndOverload(fluents_manager=fluents_manager,
                                                            no_harv_object=no_harv_object,
                                                            no_field_object=no_field_object,
                                                            no_field_access_object=no_field_access_object,
                                                            no_silo_access_object=no_silo_access_object,
                                                            no_init_loc_object=no_init_loc_object,
                                                            loc_from_type=loc_from_type,
                                                            cyclic_pre_assigned_tv_turns=cyclic_pre_assigned_tv_turns,
                                                            action_cases=action_cases,
                                                            problem_settings=problem_settings) )
    return actions


def get_actions_drive_tv_from_locs_to_field_and_overload(fluents_manager: FluentsManagerBase,
                                                         no_harv_object: Object,
                                                         no_field_object: Object,
                                                         no_field_access_object: Object,
                                                         no_silo_access_object: Object,
                                                         no_init_loc_object: Object,
                                                         cyclic_pre_assigned_tv_turns: bool,
                                                         problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings,
                                                         include_from_init_loc=True,
                                                         include_from_field=True) \
        -> List[Action]:

    """ Get all actions for 'drive transport vehicle from its location to a field (if needed), harvest and overload from the harvester to the transport vehicle, and drive the machine(s) to a field exit point' activities based on the given inputs options and problem settings.

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
        All actions for 'drive transport vehicle from its location to a field (if needed), harvest and overload from the harvester to the transport vehicle, and drive the machine(s) to a field exit point' activities based on the given inputs options and problem settings.

    """

    actions = []
    loc_from_types = [upt.FieldAccess, upt.SiloAccess]
    if include_from_init_loc:
        loc_from_types.append(upt.MachineInitLoc)
    if include_from_field:
        loc_from_types.append(upt.Field)
    for loc_from_type in loc_from_types:
        actions.extend( __get_actions_drive_tv_from_loc_to_field_and_overload(fluents_manager=fluents_manager,
                                                                              loc_from_type=loc_from_type,
                                                                              no_harv_object=no_harv_object,
                                                                              no_field_object=no_field_object,
                                                                              no_field_access_object=no_field_access_object,
                                                                              no_silo_access_object=no_silo_access_object,
                                                                              no_init_loc_object=no_init_loc_object,
                                                                              cyclic_pre_assigned_tv_turns=cyclic_pre_assigned_tv_turns,
                                                                              problem_settings=problem_settings) )
    return actions
