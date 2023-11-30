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
from management.field_partial_plan_manager import *


class ActionDriveHarvToFieldAndInit(InstantaneousAction):
    """ Instantaneous action related to 'drive harvester to a field (if needed) and initialize the harvesting process'. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        DRIVE_HARV_FROM_INIT_LOC_TO_FIELD_AND_INIT = 'drive_harv_from_init_loc_to_field_and_init'
        DRIVE_HARV_FROM_FAP_TO_FIELD_AND_INIT = 'drive_harv_from_fap_to_field_and_init'
        INIT_HARV_IN_FIELD = 'init_harv_in_field'

    @unique
    class ParameterNames(Enum):
        """ Enum with the possible action parameters this action can have. """

        FIELD = 'field'
        HARV = 'harv'
        LOC_FROM = 'loc_from'
        FIELD_ACCESS = 'field_access'

    def __init__(self,
                 fluents_manager: FluentsManagerBase,
                 infield_planner: FieldPartialPlanManager,
                 no_harv_object: Object,
                 no_field_object: Object,
                 no_field_access_object: Object,
                 no_init_loc_object: Object,
                 loc_from_type,
                 problem_settings: conf.GeneralProblemSettings):

        """ Creates the action based on the initialization parameters.

        Parameters
        ----------
        fluents_manager : FluentsManagerBase
            Fluents manager used to create the problem
        infield_planner : FieldPartialPlanManager
            Infield route planning manager (not used at the moment)
        no_harv_object : Object
            Problem object corresponding to 'no harvester'
        no_field_object : Object
            Problem object corresponding to 'no field'
        no_field_access_object : Object
            Problem object corresponding to 'no field access'
        no_init_loc_object : Object
            Problem object corresponding to 'no machine initial location'
        loc_from_type : Type
            Type of the parameter 'loc_from', i.e., the type of the current location of the transport vehicle (MachineInitLoc, FieldAccess, Field)
        problem_settings : conf.GeneralProblemSettings
            Problem settings
        """

        only_init = False
        if loc_from_type is upt.MachineInitLoc:
            action_name = ActionDriveHarvToFieldAndInit.ActionNames.DRIVE_HARV_FROM_INIT_LOC_TO_FIELD_AND_INIT.value
        elif loc_from_type is upt.FieldAccess:
            action_name = ActionDriveHarvToFieldAndInit.ActionNames.DRIVE_HARV_FROM_FAP_TO_FIELD_AND_INIT.value
        elif loc_from_type is upt.Field:
            only_init = True
            action_name = ActionDriveHarvToFieldAndInit.ActionNames.INIT_HARV_IN_FIELD.value
        else:
            raise ValueError(f'Invalid loc_from_type')

        params = {ActionDriveHarvToFieldAndInit.ParameterNames.FIELD.value: upt.Field,
                  ActionDriveHarvToFieldAndInit.ParameterNames.HARV.value: upt.Harvester}

        if not only_init:
            params[ActionDriveHarvToFieldAndInit.ParameterNames.LOC_FROM.value] = loc_from_type
            params[ActionDriveHarvToFieldAndInit.ParameterNames.FIELD_ACCESS.value] = upt.FieldAccess

        InstantaneousAction.__init__(self, action_name, **params)

        # ------------parameters------------

        field = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.FIELD.value)
        harv = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.HARV.value)

        loc_from = field_access = None
        if not only_init:
            loc_from = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.LOC_FROM.value)
            field_access = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.FIELD_ACCESS.value)

        # ------------fluents to be used------------

        harv_transit_speed_empty = fluents_manager.get_fluent(fn.harv_transit_speed_empty)

        harv_at_from = None
        transit_distance = None
        no_loc_from_object = None
        if loc_from_type is upt.MachineInitLoc:
            harv_at_from = fluents_manager.get_fluent(fn.harv_at_init_loc)
            transit_distance = fluents_manager.get_fluent(fn.transit_distance_init_fap)
            no_loc_from_object = no_init_loc_object
        elif loc_from_type is upt.FieldAccess:
            harv_at_from = fluents_manager.get_fluent(fn.harv_at_field_access)
            transit_distance = fluents_manager.get_fluent(fn.transit_distance_fap_fap)
            no_loc_from_object = no_field_access_object

        # ----------temporal parameters-----------

        if only_init:
            transit_duration = get_up_real(0)
        else:
            transit_duration = Div( transit_distance( loc_from , field_access ),
                                    harv_transit_speed_empty(harv)
                               )

        self.__add_conditions(fluents_manager=fluents_manager,
                              harv_at_from=harv_at_from,
                              transit_distance=transit_distance,
                              no_loc_from_object=no_loc_from_object,
                              no_field_object=no_field_object,
                              no_field_access_object=no_field_access_object,
                              no_harv_object=no_harv_object,
                              only_init=only_init)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings,
                           harv_at_from=harv_at_from,
                           transit_distance=transit_distance,
                           transit_duration=transit_duration,
                           no_loc_from_object=no_loc_from_object,
                           only_init=only_init)

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase,
                         harv_at_from,
                         transit_distance,
                         no_loc_from_object,
                         no_field_object,
                         no_field_access_object,
                         no_harv_object,
                         only_init):

        """ Add the conditions to the action. """

        # ------------parameters------------

        field = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.FIELD.value)
        harv = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.HARV.value)
        loc_from = field_access = None
        if not only_init:
            loc_from = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.LOC_FROM.value)
            field_access = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.FIELD_ACCESS.value)

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)
        field_id = fluents_manager.get_fluent(fn.field_id)
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_pre_assigned_harvester = fluents_manager.get_fluent(fn.field_pre_assigned_harvester)
        field_pre_assigned_turn = fluents_manager.get_fluent(fn.field_pre_assigned_turn)
        field_access_field_id = fluents_manager.get_fluent(fn.field_access_field_id)

        harv_at_field = fluents_manager.get_fluent(fn.harv_at_field)
        harv_field_turn = fluents_manager.get_fluent(fn.harv_field_turn)
        harv_count_pre_assigned_field_turns = fluents_manager.get_fluent(fn.harv_count_pre_assigned_field_turns)

        # ------------pre-conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action( self, Not( planning_failed() ) , StartTiming() )

        # the objects are valid
        add_precondition_to_action( self, Not( Equals(field, no_field_object) ), StartTiming() )
        add_precondition_to_action( self, Not( Equals(harv, no_harv_object) ), StartTiming() )
        if not only_init:
            add_precondition_to_action( self, Not( Equals(loc_from, no_loc_from_object) ), StartTiming() )
            add_precondition_to_action( self, Not( Equals(field_access, no_field_access_object) ), StartTiming() )

        # the field has no pre_assigned harvester or the harvester is the pre_assigned harvester
        add_precondition_to_action( self,
                                    Or( Equals( field_pre_assigned_harvester(field), no_harv_object ),
                                        Equals( field_pre_assigned_harvester(field), harv ) ) ,
                                    StartTiming() )

        # the field has no pre_assigned harvester or the field has no pre_assigned turn or the field turn is next
        # or the harvester has no pending pre-assigned fields
        add_precondition_to_action( self,
                                    Or(
                                        And(
                                            Or(
                                                Equals(field_pre_assigned_harvester(field), no_harv_object),
                                                Equals(field_pre_assigned_turn(field), 0)
                                            ),
                                            Or(
                                                Equals(harv_count_pre_assigned_field_turns(harv), 0),
                                                GE(
                                                    harv_field_turn(harv),
                                                    harv_count_pre_assigned_field_turns(harv)
                                                )
                                            )
                                        ),
                                        And(
                                            Equals(field_pre_assigned_harvester(field), harv),
                                            And(GT(field_pre_assigned_turn(field), 0),
                                                Equals(field_pre_assigned_turn(field), Plus(harv_field_turn(harv), 1)))
                                        )
                                    ),
                                    StartTiming() )

        # the field has not been harvested
        add_precondition_to_action( self, Not( field_harvested(field) ) , StartTiming() )

        # the field has no harvester assigned
        add_precondition_to_action( self, Equals( field_harvester(field), no_harv_object ) , StartTiming() )

        if only_init:
            # the machine is at a field
            add_precondition_to_action( self, Equals( harv_at_field(harv), field ) , StartTiming() )


        else:
            # the field access is an access point of the field
            add_precondition_to_action( self, Equals( field_id(field), field_access_field_id(field_access) ) , StartTiming() )

            # the machine is at loc_from
            add_precondition_to_action( self, Equals( harv_at_from(harv), loc_from ) , StartTiming() )

            # the machine is not at a field
            add_precondition_to_action( self, Equals( harv_at_field(harv), no_field_object ) , StartTiming() )

            # there is a valid connection between the machine location and the field_access
            add_precondition_to_action( self,
                                        GE ( transit_distance( loc_from , field_access), 0 ),
                                        StartTiming() )

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings,
                      harv_at_from,
                      transit_distance,
                      transit_duration,
                      no_loc_from_object,
                      only_init):

        """ Add the effects to the action. """

        effects_option = problem_settings.effects_settings.drive_harv_to_field

        # ------------parameters------------

        field = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.FIELD.value)
        harv = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.HARV.value)
        loc_from = field_access = None
        if not only_init:
            loc_from = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.LOC_FROM.value)
            field_access = self.parameter(ActionDriveHarvToFieldAndInit.ParameterNames.FIELD_ACCESS.value)

        # ------------fluents to be used------------
        field_harvester = fluents_manager.get_fluent(fn.field_harvester)
        field_timestamp_assigned = fluents_manager.get_fluent(fn.field_timestamp_assigned)

        harv_timestamp = fluents_manager.get_fluent(fn.harv_timestamp)
        harv_at_field = fluents_manager.get_fluent(fn.harv_at_field)
        harv_transit_speed_empty = fluents_manager.get_fluent(fn.harv_transit_speed_empty)
        harv_transit_time = fluents_manager.get_fluent(fn.harv_transit_time)
        harv_field_turn = fluents_manager.get_fluent(fn.harv_field_turn)

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
            _loc_from = actual_params.get(loc_from) if loc_from is not None else None
            _field_access = actual_params.get(field_access) if field_access is not None else None

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'+++++++++++++++++++ [state {id(state)}] ::  {self.name} sim effect [{timing}] - {_harv} - {_field}')

            _harv_timestamp = float(state.get_value(harv_timestamp(_harv)).constant_value())
            _harv_transit_time = float(state.get_value(harv_transit_time(_harv)).constant_value())
            if only_init:
                _transit_duration = 0
            else:
                _transit_distance = float(state.get_value(transit_distance(_loc_from, _field_access)).constant_value())
                _harv_transit_speed_empty = float(state.get_value(harv_transit_speed_empty(_harv)).constant_value())

                _transit_duration = (_transit_distance / _harv_transit_speed_empty)

            ret_vals = []

            for fl, val in effects_values.items():

                # #debug!
                # print(f'   [{self.name}] fluent = {fl} ; value = {val}')

                if val[0] is not None and val[1]:  # give priority to values that were set already
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0] )
                    continue

                if fl is field_harvester(field):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _harv)  # field_harvester(field)
                elif fl is field_timestamp_assigned(field):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_harv_timestamp))  # field_timestamp_assigned(field)
                elif fl is harv_timestamp(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_harv_timestamp + _transit_duration))  # harv_timestamp(harv)
                elif fl is harv_at_field(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   _field)  # harv_at_field(harv)
                elif harv_at_from is not None and fl is harv_at_from(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   ObjectExp(problem.object(no_loc_from_object.name)))  # harv_at_from(harv)
                elif fl is harv_transit_time(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_harv_transit_time + _transit_duration))  # harv_transit_time(harv)
                elif fl is harv_field_turn(harv):
                    _harv_field_turn = int(state.get_value(harv_field_turn(_harv)).constant_value())
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Int(_harv_field_turn + 1))  # harv_field_turn(harv)

                # unexpected fluent
                else:
                    raise ValueError(f'Unexpected fluent {fl} in simulated effect')

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'------------------- {self.name} sim effect [{timing}] - {_harv} - {_field}')

            return ret_vals

        effects_handler = EffectsHandler()

        effects_handler.add(timing=StartTiming(), fluent=field_harvester(field), value=harv,
                            value_applies_in_sim_effect=False)
        effects_handler.add(timing=StartTiming(), fluent=field_timestamp_assigned(field),
                            value=harv_timestamp(harv),
                            value_applies_in_sim_effect=False)
        effects_handler.add(timing=StartTiming(), fluent=harv_timestamp(harv),
                            value=Plus(harv_timestamp(harv), transit_duration),
                            value_applies_in_sim_effect=False)
        effects_handler.add(timing=StartTiming(), fluent=harv_field_turn(harv), value=Plus(harv_field_turn(harv), 1),
                            value_applies_in_sim_effect=False)

        if not only_init:
            effects_handler.add(timing=StartTiming(), fluent=harv_at_from(harv), value=no_loc_from_object,
                                value_applies_in_sim_effect=False)

            effects_handler.add(timing=StartTiming(), fluent=harv_at_field(harv), value=field,
                                value_applies_in_sim_effect=False)

            effects_handler.add(timing=StartTiming(), fluent=harv_transit_time(harv),
                                value=Plus(harv_transit_time(harv), transit_duration), value_applies_in_sim_effect=False)

        effects_handler.add_effects_to_action(action=self,
                                              effects_option=effects_option,
                                              sim_effect_cb=sim_effects_cb)


def get_actions_drive_harv_from_loc_to_field_and_init(fluents_manager: FluentsManagerBase,
                                                      infield_planner: FieldPartialPlanManager,
                                                      no_harv_object: Object,
                                                      no_field_object: Object,
                                                      no_field_access_object: Object,
                                                      no_init_loc_object: Object,
                                                      problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings,
                                                      include_from_init_loc=True,
                                                      include_from_field=True
                                                      ) \
        -> List[Action]:

    """ Get all actions for 'drive harvester to a field (if needed) and initialize harvesting process' activities based on the given inputs options and problem settings.

    Parameters
    ----------
    fluents_manager : FluentsManagerBase
        Fluents manager used to create the problem
    infield_planner : FieldPartialPlanManager
        Infield route planning manager (not used at the moment)
    no_harv_object : Object
        Problem object corresponding to 'no harvester'
    no_field_object : Object
        Problem object corresponding to 'no field'
    no_field_access_object : Object
        Problem object corresponding to 'no field access'
    no_init_loc_object : Object
        Problem object corresponding to 'no machine initial location'
    problem_settings : conf.GeneralProblemSettings
        Problem settings
    include_from_init_loc : bool
        Flag stating if actions corresponding to 'drive harvester from initial location to field' must be included or not (if no harvesters are located at MachineInitLoc, it is not necessary to add these actions)
    include_from_field : bool
        Flag stating if actions corresponding to 'initialize harvesting process at the field where the harvester is currently located' must be included or not (if no harvesters are located at a Field, it is not necessary to add these actions)

    Returns
    -------
    actions : List[Action]
        All actions for 'drive harvester to a field (if needed) and initialize harvesting process' activities based on the given inputs options and problem settings.
    """

    actions = []
    loc_from_types = [upt.FieldAccess]
    if include_from_init_loc:
        loc_from_types.append(upt.MachineInitLoc)
    if include_from_field:
        loc_from_types.append(upt.Field)

    for loc_from_type in loc_from_types:
        actions.append( ActionDriveHarvToFieldAndInit(fluents_manager=fluents_manager,
                                                      infield_planner=infield_planner,
                                                      no_harv_object=no_harv_object,
                                                      no_field_object=no_field_object,
                                                      no_field_access_object=no_field_access_object,
                                                      no_init_loc_object=no_init_loc_object,
                                                      loc_from_type=loc_from_type,
                                                      problem_settings=problem_settings) )

    return actions
