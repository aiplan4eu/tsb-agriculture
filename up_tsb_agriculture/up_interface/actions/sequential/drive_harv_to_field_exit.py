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


class ActionDriveHarvToFieldExit(InstantaneousAction):
    """ Instantaneous action related to 'drive harvester to a field exit point'. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        DRIVE_HARV_TO_FIELD_EXIT = 'drive_harv_to_field_exit'

    @unique
    class ParameterNames(Enum):
        """ Enum with the possible action parameters this action can have. """

        FIELD = 'field'
        FIELD_ACCESS = 'field_access'
        HARV = 'harv'

    def __init__(self,
                 fluents_manager: FluentsManagerBase,
                 no_harv_object: Object,
                 no_field_object: Object,
                 no_field_access_object: Object,
                 problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings):

        """ Creates the action based on the initialization parameters.

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
        """

        params = {self.ParameterNames.FIELD.value: upt.Field,
                  self.ParameterNames.FIELD_ACCESS.value: upt.FieldAccess,
                  self.ParameterNames.HARV.value: upt.Harvester}

        InstantaneousAction.__init__(self, self.ActionNames.DRIVE_HARV_TO_FIELD_EXIT.value, **params)

        infield_transit_duration = max(0.0, problem_settings.infield_transit_duration_to_field_access)  # @todo infield transit to field exit (fixed at the moment)

        self.__add_conditions(fluents_manager=fluents_manager,
                              no_field_object=no_field_object,
                              no_field_access_object=no_field_access_object,
                              no_harv_object=no_harv_object)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings,
                           no_field_object=no_field_object,
                           infield_transit_duration=infield_transit_duration)

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase,
                         no_field_object,
                         no_field_access_object,
                         no_harv_object):

        """ Add the conditions to the action. """

        # ------------parameters------------

        field = self.parameter(ActionDriveHarvToFieldExit.ParameterNames.FIELD.value)
        field_access = self.parameter(ActionDriveHarvToFieldExit.ParameterNames.FIELD_ACCESS.value)
        harv = self.parameter(ActionDriveHarvToFieldExit.ParameterNames.HARV.value)

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)
        field_id = fluents_manager.get_fluent(fn.field_id)
        field_harvested = fluents_manager.get_fluent(fn.field_harvested)
        field_access_field_id = fluents_manager.get_fluent(fn.field_access_field_id)

        harv_at_field = fluents_manager.get_fluent(fn.harv_at_field)

        # ------------pre-conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action( self, Not( planning_failed() ) , StartTiming() )

        # the objects are valid
        add_precondition_to_action( self, Not( Equals(field, no_field_object) ), StartTiming() )
        add_precondition_to_action( self, Not( Equals(field_access, no_field_access_object) ), StartTiming() )
        add_precondition_to_action( self, Not( Equals(harv, no_harv_object) ), StartTiming() )

        # the field access is an access point of the field
        add_precondition_to_action( self, Equals( field_id(field), field_access_field_id(field_access) ) , StartTiming() )

        # the field is harvested
        add_precondition_to_action( self, field_harvested(field) , StartTiming() )

        # the harvester is currently in the field
        add_precondition_to_action( self, Equals( harv_at_field(harv), field ), StartTiming() )

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings,
                      no_field_object,
                      infield_transit_duration):

        """ Add the effects to the action. """

        effects_option = problem_settings.effects_settings.general

        # ------------parameters------------

        field_access = self.parameter(ActionDriveHarvToFieldExit.ParameterNames.FIELD_ACCESS.value)
        harv = self.parameter(ActionDriveHarvToFieldExit.ParameterNames.HARV.value)

        # ------------fluents to be used------------

        harv_timestamp = fluents_manager.get_fluent(fn.harv_timestamp)
        harv_at_field = fluents_manager.get_fluent(fn.harv_at_field)
        harv_at_field_access = fluents_manager.get_fluent(fn.harv_at_field_access)

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

            _harv = actual_params.get(harv)

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'+++++++++++++++++++ [state {id(state)}] ::  {self.name} sim effect [{timing}] - {_harv}')

            _harv_timestamp = float(state.get_value(harv_timestamp(_harv)).constant_value())

            ret_vals = []

            for fl, val in effects_values.items():
                if val[0] is not None and val[1]:  # give priority to values that were set already
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0] )
                    continue

                if fl is harv_at_field(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   ObjectExp(problem.object( no_field_object.name) ) )
                elif fl is harv_at_field_access(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   actual_params.get(field_access) )
                elif fl is harv_timestamp(harv):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real(_harv_timestamp + infield_transit_duration))

                # unexpected fluent
                else:
                    raise ValueError(f'Unexpected fluent {fl} in simulated effect')

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'------------------- {self.name} sim effect [{timing}] - {_harv}')

            return ret_vals

        effects_handler = EffectsHandler()

        effects_handler.add(timing=StartTiming(), fluent=harv_timestamp(harv),
                            value=Plus(harv_timestamp(harv), get_up_real(infield_transit_duration)),
                            value_applies_in_sim_effect=False)
        effects_handler.add(timing=StartTiming(), fluent=harv_at_field(harv), value=no_field_object, value_applies_in_sim_effect=False)
        effects_handler.add(timing=StartTiming(), fluent=harv_at_field_access(harv), value=field_access, value_applies_in_sim_effect=False)

        effects_handler.add_effects_to_action(action=self,
                                              effects_option=effects_option,
                                              sim_effect_cb=sim_effects_cb)


def get_actions_drive_harv_to_field_exit(fluents_manager: FluentsManagerBase,
                                         no_harv_object: Object,
                                         no_field_object: Object,
                                         no_field_access_object: Object,
                                         problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings) \
        -> List[Action]:

    """ Get all actions for 'drive harvester to a field exit point' activities based on the given inputs options and problem settings.

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
        All actions for 'drive harvester to a field exit point' activities based on the given inputs options and problem settings.
    """

    return [ ActionDriveHarvToFieldExit(fluents_manager, no_harv_object, no_field_object, no_field_access_object, problem_settings ) ]
