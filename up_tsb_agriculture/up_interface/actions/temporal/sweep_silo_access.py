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


class ActionSweepSiloAccess(DurativeAction):
    """ Durative action related to 'sweep silo access/unloading point'. """

    @unique
    class ActionNames(Enum):
        """ Enum with the possible action names this action can have. """

        SWEEP_SILO_ACCESS = 'sweep_silo_access'

    @unique
    class ParameterNames(Enum):
        """ Enum with the possible action parameters this action can have. """

        COMPACTOR = 'comp'
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

        params = {ActionSweepSiloAccess.ParameterNames.COMPACTOR.value: upt.Compactor,
                  ActionSweepSiloAccess.ParameterNames.SILO_ACCESS.value: upt.SiloAccess}

        DurativeAction.__init__(self, ActionSweepSiloAccess.ActionNames.SWEEP_SILO_ACCESS.value, **params)

        # ------------parameters------------

        comp = self.parameter(ActionSweepSiloAccess.ParameterNames.COMPACTOR.value)
        silo_access = self.parameter(ActionSweepSiloAccess.ParameterNames.SILO_ACCESS.value)

        # ------------fluents to be used------------

        silo_access_sweep_duration = fluents_manager.get_fluent(fn.silo_access_sweep_duration)

        # ------------duration------------#

        set_duration_to_action( self, silo_access_sweep_duration(silo_access) )


        self.__add_conditions(fluents_manager=fluents_manager)

        self.__add_effects(fluents_manager=fluents_manager,
                           problem_settings=problem_settings)

    def __add_conditions(self,
                         fluents_manager: FluentsManagerBase):

        """ Add the conditions to the action. """

        # ------------parameters------------

        comp = self.parameter(ActionSweepSiloAccess.ParameterNames.COMPACTOR.value)
        silo_access = self.parameter(ActionSweepSiloAccess.ParameterNames.SILO_ACCESS.value)

        # ------------fluents to be used------------

        planning_failed = fluents_manager.get_fluent(fn.planning_failed)
        silo_access_silo_id = fluents_manager.get_fluent(fn.silo_access_silo_id)
        silo_access_cleared = fluents_manager.get_fluent(fn.silo_access_cleared)
        compactor_silo_id = fluents_manager.get_fluent(fn.compactor_silo_id)
        compactor_free = fluents_manager.get_fluent(fn.compactor_free)

        # ------------conditions------------

        # planning has not failed (@todo temporary workaround)
        add_precondition_to_action( self, Not( planning_failed() ) , StartTiming() )

        # the compactor is available
        add_precondition_to_action( self, compactor_free(comp), StartTiming() )

        # the silo access has yield to be collected
        add_precondition_to_action( self, Not( silo_access_cleared(silo_access) ), StartTiming() )

        # check if the machine and the silo access belong to the same silo
        add_precondition_to_action( self,
                                    Equals( compactor_silo_id(comp), silo_access_silo_id(silo_access) ),
                                    StartTiming() )

    def __add_effects(self,
                      fluents_manager: FluentsManagerBase,
                      problem_settings):

        """ Add the effects to the action. """

        effects_option = problem_settings.effects_settings.general

        # ------------parameters------------

        comp = self.parameter(ActionSweepSiloAccess.ParameterNames.COMPACTOR.value)
        silo_access = self.parameter(ActionSweepSiloAccess.ParameterNames.SILO_ACCESS.value)

        # ------------fluents to be used------------

        silo_access_total_capacity_mass = fluents_manager.get_fluent(fn.silo_access_total_capacity_mass)
        silo_access_available_capacity_mass = fluents_manager.get_fluent(fn.silo_access_available_capacity_mass)
        silo_access_cleared = fluents_manager.get_fluent(fn.silo_access_cleared)
        compactor_free = fluents_manager.get_fluent(fn.compactor_free)
        compactor_mass_per_sweep = fluents_manager.get_fluent(fn.compactor_mass_per_sweep)

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

            _comp = actual_params.get(comp)
            _silo_access = actual_params.get(silo_access)

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'+++++++++++++++++++ [state {id(state)}] ::  {self.name} sim effect [{timing}] - {_comp} - {_silo_access}')

            _silo_access_total_capacity_mass = \
                float( state.get_value( silo_access_total_capacity_mass( _silo_access ) ).constant_value() )
            _silo_access_available_capacity_mass = \
                float( state.get_value( silo_access_available_capacity_mass( _silo_access ) ).constant_value() )
            _compactor_mass_per_sweep = float( state.get_value( compactor_mass_per_sweep( _comp ) ).constant_value() )

            _mass_to_sweep = min( _compactor_mass_per_sweep,
                                  _silo_access_total_capacity_mass - _silo_access_available_capacity_mass )

            _silo_access_available_capacity_mass_new = float( _silo_access_available_capacity_mass + _mass_to_sweep )

            _cleared = abs(_silo_access_total_capacity_mass - _silo_access_available_capacity_mass_new) < 0.1

            ret_vals = []

            for fl, val in effects_values.items():
                if val[0] is not None and val[1]: # give priority to values that were set already
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl, val[0] )
                    continue

                if fl is silo_access_cleared(silo_access):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   Bool(_cleared) )
                elif fl is silo_access_available_capacity_mass(silo_access):
                    EffectsHandler.append_value_to_callback_return(ret_vals, effects_values, fl,
                                                                   get_up_real( _silo_access_available_capacity_mass_new ) )

                # unexpected fluent
                else:
                    raise ValueError(f'Unexpected fluent {fl} in simulated effect')

            if conf.DEBUG_PRINT_SIM_EFFECTS_IN_OUT:
                print(f'------------------- {self.name} sim effect [{timing}] - {_comp} - {_silo_access}')

            return ret_vals

        effects_handler = EffectsHandler()

        effects_handler.add(timing=StartTiming(), fluent=compactor_free(comp), value=Bool(False), value_applies_in_sim_effect=True)
        effects_handler.add(timing=EndTiming(), fluent=compactor_free(comp), value=Bool(True), value_applies_in_sim_effect=True)

        # conditional effects

        # @note condition_cleared != condition_all_removed because condition_cleared lets a little amount of yield to be left in the sap
        mass_in_sap = Minus(silo_access_total_capacity_mass(silo_access),
                            silo_access_available_capacity_mass(silo_access))
        condition_cleared = LT( Minus( mass_in_sap, compactor_mass_per_sweep(comp) ), 0.1 )
        condition_all_removed = LE( mass_in_sap, compactor_mass_per_sweep(comp) )

        # condition silo access considered to be cleared or not
        effects_handler.add(timing=EndTiming(), fluent=silo_access_cleared(silo_access),
                            value=Bool(True),
                            value_applies_in_sim_effect=False,
                            condition=condition_cleared)
        effects_handler.add(timing=EndTiming(),
                            fluent=silo_access_cleared(silo_access),
                            value=Bool(False),
                            value_applies_in_sim_effect=False,
                            condition=Not(condition_cleared))

        # condition silo access has yield left or not
        effects_handler.add(timing=EndTiming(),
                            fluent=silo_access_available_capacity_mass(silo_access),
                            value=silo_access_total_capacity_mass(silo_access),
                            value_applies_in_sim_effect=False,
                            condition=condition_all_removed)
        effects_handler.add(timing=EndTiming(),
                            fluent=silo_access_available_capacity_mass(silo_access),
                            value=Plus( silo_access_available_capacity_mass(silo_access), compactor_mass_per_sweep(comp) ),
                            value_applies_in_sim_effect=False,
                            condition=Not(condition_all_removed))

        effects_handler.add_effects_to_action(action=self,
                                              effects_option=effects_option,
                                              sim_effect_cb=sim_effects_cb)


def get_actions_sweep_silo_access(fluents_manager: FluentsManagerBase,
                                  problem_settings: conf.GeneralProblemSettings = conf.default_problem_settings) \
        -> List[Action]:

    """ Get all actions for 'sweep silo access/unloading point' activities based on the given inputs options and problem settings.

    Parameters
    ----------
    fluents_manager : FluentsManagerBase
        Fluents manager used to create the problem
    problem_settings : conf.GeneralProblemSettings
        Problem settings

    Returns
    -------
    actions : List[Action]
        All actions for 'sweep silo access/unloading point' activities based on the given inputs options and problem settings.

    """

    return [ ActionSweepSiloAccess(fluents_manager, problem_settings ) ]
