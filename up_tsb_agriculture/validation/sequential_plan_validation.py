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

from unified_planning.shortcuts import SequentialSimulator, State, FluentExp, Object, UserType
from unified_planning.plans.sequential_plan import SequentialPlan
import up_interface.types as upt
from up_interface.fluents import FluentNames as fn
from up_interface.problem_encoder.names_helper import *
from up_interface.problem_encoder.problem_encoder import ProblemEncoder


def __count_locations(machine: Object, machine_type: UserType, problem_encoder: ProblemEncoder, state: State) -> bool:

    """ Checks that a machine is not assigned to more than one location at a given state

    Parameters
    ----------
    machine : Object
        Machine object
    machine_type : UserType
        Machine type (Harvester, TransportVehicle)
    problem_encoder : ProblemEncoder
        Problem encoder
    state : State
        State

    Returns
    ----------
    valid : bool
        True if the state is valid
    """

    problem = problem_encoder.problem
    objects = problem_encoder.problem_objects

    if machine_type is upt.Harvester:
        fls = {fn.harv_at_init_loc: objects.no_init_loc,
               fn.harv_at_field: objects.no_field,
               fn.harv_at_field_access: objects.no_field_access}
    else:
        fls = {fn.tv_at_init_loc: objects.no_init_loc,
               fn.tv_at_field: objects.no_field,
               fn.tv_at_field_access: objects.no_field_access,
               fn.tv_at_silo_access: objects.no_silo_access}

    count = 0
    for f, no_loc in fls.items():
        loc = FluentExp(problem.fluent(f.value), machine)
        _loc = state.get_value(loc).constant_value()
        if _loc.name != no_loc.name:
            count += 1
    if count > 1:
        print(f'Invalid state [{machine}]: the machine is at more than one location')
        return False

    return True


def __check_state_fields(problem_encoder: ProblemEncoder, state: State, prev_state: State):

    """ Checks the validity of the fluent values of all fields for a given state

    Parameters
    ----------
    problem_encoder : ProblemEncoder
        Problem encoder
    state : State
        State
    prev_state : State
        Previous state

    Returns
    ----------
    valid : bool
        True if the state is valid
    """

    problem = problem_encoder.problem

    print(f'\nChecking states of the fields ...')
    for field in problem.objects(upt.Field):
        if field.name == problem_encoder.problem_objects.no_field.name:
            continue
        print(f'... Checking states of field {field} ...')

        field_yield_mass_total = FluentExp(problem.fluent(fn.field_yield_mass_total.value), field)
        _field_yield_mass_total = float(state.get_value(field_yield_mass_total).constant_value())

        field_yield_mass_unharvested = FluentExp(problem.fluent(fn.field_yield_mass_unharvested.value), field)
        _field_yield_mass_unharvested = float(state.get_value(field_yield_mass_unharvested).constant_value())
        _field_yield_mass_unharvested_prev = float(prev_state.get_value(field_yield_mass_unharvested).constant_value())

        print(f'... Checking that field_yield_mass_unharvested of field {field} is in the valid range [0, field_yield_mass_total] ...')

        if _field_yield_mass_unharvested > _field_yield_mass_total + 0.1:
            print(
                f'Invalid state [{field}]: field_yield_mass_unharvested ({_field_yield_mass_unharvested}) > field_yield_mass_total ({_field_yield_mass_total})')
            return False

        if _field_yield_mass_unharvested < -0.1:
            print(
                f'Invalid state [{field}]: field_yield_mass_unharvested ({_field_yield_mass_unharvested}) < 0')
            return False

        print(f'... Checking that field_yield_mass_unharvested of field {field} does not increase with with time ...')

        if _field_yield_mass_unharvested > _field_yield_mass_unharvested_prev + 0.1:
            print(
                f'Invalid state [{field}]: current_field_yield_mass_unharvested ({_field_yield_mass_unharvested}) > prev_field_yield_mass_unharvested ({_field_yield_mass_unharvested_prev})')
            return False

        print(f'... State of field {field} is VALID')

    return True


def __check_state_harvs(problem_encoder: ProblemEncoder, state: State):

    """ Checks the validity of the fluent values of all harvesters for a given state

    Parameters
    ----------
    problem_encoder : ProblemEncoder
        Problem encoder
    state : State
        State

    Returns
    ----------
    valid : bool
        True if the state is valid
    """

    problem = problem_encoder.problem

    print(f'\nChecking states of the harvesters ...')
    for machine in problem.objects(upt.Harvester):
        if machine.name == problem_encoder.problem_objects.no_harvester.name:
            continue

        print(f'... Checking states of machine {machine} ...')
        print(f'... ... Checking that the machine {machine} is not assigned to more than one location ...')
        if not __count_locations(machine, upt.Harvester, problem_encoder, state):
            return False
        print(f'... State of machine {machine} is VALID')
    return True


def __check_state_tvs(problem_encoder: ProblemEncoder, state: State):

    """ Checks the validity of the fluent values of all transport vehicles for a given state

    Parameters
    ----------
    problem_encoder : ProblemEncoder
        Problem encoder
    state : State
        State

    Returns
    ----------
    valid : bool
        True if the state is valid
    """

    problem = problem_encoder.problem
    data_manager = problem_encoder.data_manager

    print(f'\nChecking states of the transport vehicles ...')
    for machine in problem.objects(upt.TransportVehicle):
        print(f'... Checking states of machine {machine} ...')

        machine_id = get_tv_id_from_name(machine.name)
        m = data_manager.get_machine(machine_id)

        tv_total_capacity_mass = FluentExp(problem.fluent(fn.tv_total_capacity_mass.value), machine)
        _tv_total_capacity_mass = float(state.get_value(tv_total_capacity_mass).constant_value())

        tv_bunker_mass = FluentExp(problem.fluent(fn.tv_bunker_mass.value), machine)
        _tv_bunker_mass = float(state.get_value(tv_bunker_mass).constant_value())

        print(f'... ... Checking capacity constraints of machine {machine} ...')

        if _tv_bunker_mass > _tv_total_capacity_mass + 0.1:
            print(
                f'Invalid state [{machine}]: tv_bunker_mass ({_tv_bunker_mass}) > tv_total_capacity_mass ({_tv_total_capacity_mass})')
            return False

        if _tv_bunker_mass > m.bunker_mass + 0.1:
            print(
                f'Invalid state [{machine}]: tv_bunker_mass ({_tv_bunker_mass}) > machine.bunker_mass ({m.bunker_mass})')
            return False

        print(f'... ... Checking that the machine {machine} is not assigned to more than one location ...')
        if not __count_locations(machine, upt.TransportVehicle, problem_encoder, state):
            return False

        print(f'... State of machine {machine} is VALID')

    return True


def __check_state_silos(problem_encoder: ProblemEncoder, state: State, prev_state: State):

    """ Checks the validity of the fluent values of all silos for a given state

    Parameters
    ----------
    problem_encoder : ProblemEncoder
        Problem encoder
    state : State
        State
    prev_state : State
        Previous state

    Returns
    ----------
    valid : bool
        True if the state is valid
    """

    problem = problem_encoder.problem

    print(f'\nChecking states of the silos ...')
    for silo in problem.objects(upt.Silo):
        print(f'... Checking states of silo {silo} ...')

        silo_available_capacity_mass = FluentExp(problem.fluent(fn.silo_available_capacity_mass.value), silo)
        _silo_available_capacity_mass = float(state.get_value(silo_available_capacity_mass).constant_value())
        _silo_available_capacity_mass_prev = float(prev_state.get_value(silo_available_capacity_mass).constant_value())

        print(f'... Checking that silo_available_capacity_mass of silo {silo} is not negative ...')
        if _silo_available_capacity_mass < -0.1:
            print(
                f'Invalid state [{silo}]: silo_available_capacity_mass ({_silo_available_capacity_mass}) < 0')
            return False

        print(f'... Checking that silo_available_capacity_mass of silo {silo} does increase with with time ...')
        if _silo_available_capacity_mass > _silo_available_capacity_mass_prev + 0.1:
            print(
                f'Invalid state [{silo}]: silo_available_capacity_mass ({_silo_available_capacity_mass}) > silo_available_capacity_mass_prev ({_silo_available_capacity_mass_prev})')
            return False

        print(f'... State of silo {silo} is VALID')
    return True


def __check_state(problem_encoder: ProblemEncoder, state: State, prev_state: State):

    """ Checks the validity of a given state

    Parameters
    ----------
    problem_encoder : ProblemEncoder
        Problem encoder
    state : State
        State
    prev_state : State
        Previous state

    Returns
    ----------
    valid : bool
        True if the state is valid
    """

    return (__check_state_fields(problem_encoder, state, prev_state)
            and __check_state_harvs(problem_encoder, state)
            and __check_state_tvs(problem_encoder, state)
            and __check_state_silos(problem_encoder, state, prev_state))


def validate_sequential_plan(problem_encoder: ProblemEncoder, plan: SequentialPlan) -> bool:

    """ Checks the validity of a given plan

    Only checks some important fluents, i.e., does not make a complete validation of the plan.

    Parameters
    ----------
    problem_encoder : ProblemEncoder
        Problem encoder
    plan : SequentialPlan
        Plan

    Returns
    ----------
    valid : bool
        True if the plan is valid
    """

    print(f'Validating states...')
    simulator = SequentialSimulator(problem_encoder.problem)
    state_prev: State = simulator.get_initial_state()
    for i, action in enumerate(plan.actions):
        state_new = simulator.apply(state_prev, action)
        if not __check_state(problem_encoder, state_new, state_prev):
            print(f'Action {i} generated an invalid state!!!!!')
            print(f'Action: {action}')
            return False
        state_prev = state_new
    print(f'Validation OK')
    return True
