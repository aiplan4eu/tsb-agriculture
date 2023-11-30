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

from abc import ABC, abstractmethod
from typing import TypeVar

import up_interface.types as upt
from silo_planning.types import SiloExtended, SiloAccessPoint
from util_arolib.types import *
from util_arolib.geometry import getCentroid2, getPointAtRelativeDist
from route_planning.types import MachineState, FieldState, SiloState
from route_planning.outfield_route_planning import OutFieldRoutePlanner
from up_interface.problem_encoder.names_helper import *
from up_interface.fluents import FluentNames as fn

from unified_planning.shortcuts import *

from util_arolib.types import Point, Linestring, Field
from management.global_data_manager import GlobalDataManager


class PlanDecoderBase(ABC):

    """ Base class for UP-plan decoders """

    class PlanStateBase:
        def __init__(self):
            self.ts_start: float = 0.0
            """ State start timestamp [s] """

            self.ts_end: Optional[float] = None
            """ State end timestamp [s] (None if unknown) """

    class MachineActivity(Enum):

        """ Enum for machine activity types """

        WAITING_TO_DRIVE = 'WAITING_TO_DRIVE'
        WAITING_TO_OVERLOAD = 'WAITING_TO_OVERLOAD'
        OVERLOADING = 'OVERLOADING'
        TRANSIT_IN_FIELD = 'TRANSIT_IN_FIELD'
        TRANSIT_OFF_FIELD = 'TRANSIT_OFF_FIELD'
        WAITING_TO_UNLOAD = 'WAITING_TO_UNLOAD'
        UNLOADING = 'UNLOADING'

    class PlanMachineState(PlanStateBase):

        """ Class holding information about the state of a machine """

        def __init__(self):
            super(PlanDecoderBase.PlanMachineState, self).__init__()

            self.ts_start: float = 0.0
            """ State start timestamp [s] """

            self.ts_end: Optional[float] = None
            """ State end timestamp [s] (None if unknown) """

            self.loc_start: Optional[str] = None
            """ Machine location at ts_start """

            self.loc_end: Optional[str] = None
            """ Machine location at ts_end (None if unknown) """

            self.pt_start: Optional[Point] = None
            """ Machine position at ts_start (None if unknown) """

            self.pt_end: Optional[Point] = None
            """ Machine position at ts_end (None if unknown) """

            self.bunker_mass_start: float = 0.0
            """ Mass [kg] in the machine's bunker at ts_start """

            self.bunker_mass_end: float = 0.0
            """ Mass [kg] in the machine's bunker at ts_end (None if unknown) """

            self.transit_time_start: float = 0.0
            """ Machine transit time [s] until ts_start """

            self.transit_time_end: Optional[float] = None
            """ Machine transit time [s] until ts_end (None if unknown) """

            self.waiting_time_start: float = 0.0
            """ Machine waiting time [s] until ts_start """

            self.waiting_time_end: Optional[float] = None
            """ Machine waiting time [s] until (None if unknown) """

            self.action: Optional[str] = None
            """ Name of the action that caused the state """

            self.activity: PlanDecoderBase.MachineActivity = PlanDecoderBase.MachineActivity.WAITING_TO_DRIVE
            """ Machine activity starting from ts_start """

            self.overloading_machine_name: Optional[str] = None
            """ Name of the machine participating in the overload activity (None if not overloading) """

    class FieldHarvestingState(Enum):

        """ Enum for the harvesting states of a field """

        UNRESERVED = 'UNRESERVED'
        RESERVED = 'RESERVED'
        BEING_HARVESTED = 'BEING_HARVESTED'
        BEING_HARVESTED_WAITING = 'BEING_HARVESTED_WAITING'
        HARVESTED = 'HARVESTED'

    class PlanFieldState(PlanStateBase):

        """ Class holding information about the state of a field """

        def __init__(self):
            super(PlanDecoderBase.PlanFieldState, self).__init__()

            self.ts_start: float = 0.0
            """ State start timestamp [s] """

            self.ts_end: Optional[float] = None
            """ State end timestamp [s] (None if unknown) """

            self.harvested_percentage_start: float = 0.0
            """ Percentage [0, 100] of the field that has been harvested at ts_start """

            self.harvested_percentage_end: Optional[float] = None
            """ Percentage [0, 100] of the field that has been harvested at ts_end (None if unknown) """

            self.harvested_yield_mass_start: float = 0.0
            """ Amount of yield mass [kg] that has been harvested from the field at ts_start """

            self.harvested_yield_mass_end: Optional[float] = None
            """ Amount of yield mass [kg] that has been harvested from the field at ts_end (None if unknown) """

            self.state: PlanDecoderBase.FieldHarvestingState = PlanDecoderBase.FieldHarvestingState.UNRESERVED
            """ Field state starting from ts_start """

            self.harvester: Optional[str] = None
            """ Name of the harvester assigned to the field from ts_start (None if unassigned) """

            self.tv: Optional[str] = None
            """ Name of the transport vehicle overloading at the field from ts_start (None if no overloading is being performed) """

    class PlanSiloState(PlanStateBase):

        """ Class holding information about the state of a silo """

        def __init__(self):
            super(PlanDecoderBase.PlanSiloState, self).__init__()

            self.ts_start: float = 0.0
            """ State start timestamp [s] """

            self.ts_end: float = 0.0
            """ State end timestamp [s] (None if unknown) """

            self.yield_mass_start: float = 0.0
            """ Amount of yield mass [kg] in the silo at ts_start """

            self.yield_mass_end: float = 0.0
            """ Amount of yield mass [kg] in the silo at ts_end (None if unknown) """

    class FieldOverloadInfo(PlanStateBase):

        """ Class holding information about the state of an overload activity """

        def __init__(self):
            super(PlanDecoderBase.FieldOverloadInfo, self).__init__()

            self.ts_start: float = 0.0
            """ State start timestamp [s] """

            self.ts_end: Optional[float] = None
            """ State end timestamp [s] (None if unknown) """

            self.tv: Optional[str] = None
            """ Name of the transport vehicle participating in the overload """

    class FieldOverloads:

        """ Class holding information about the overload activities of a field """

        def __init__(self):
            self.harv = None
            """ Name of the harvester harvesting the field """

            self.entry_point = None
            """ Name of the field access point used by the harvester """

            self.overloads: List[PlanDecoderBase.FieldOverloadInfo] = list()
            """ Overloads' information """

    class TVOverloadInfo(PlanStateBase):

        """ Class holding information about the overload activities of a transport vehicle """

        def __init__(self):
            super(PlanDecoderBase.TVOverloadInfo, self).__init__()

            self.ts_start: float = 0.0
            """ State start timestamp [s] """

            self.ts_end: float = 0.0
            """ State end timestamp [s] (None if unknown) """

            self.field: Optional[str] = None
            """ Name of the field being harvested during the overload """

            self.harv: Optional[str] = None
            """ Name of the harvester participating in the overload """

            self.silo_access: Optional[str] = None
            """ Name of the silo access where the transport vehicle unloaded (if None, there was another overload before unloading) """

    class TVUnloadInfo(PlanStateBase):

        """ Class holding information about the unload activities of a transport vehicle """

        def __init__(self):
            super(PlanDecoderBase.TVUnloadInfo, self).__init__()

            self.ts_start: float = 0.0
            """ State start timestamp [s] """

            self.ts_end: float = 0.0
            """ State end timestamp [s] (None if unknown) """

            self.silo_access: Optional[str] = None
            """ Silo access where the transport vehicle unloaded """

            self.overload_info: Optional[PlanDecoderBase.TVOverloadInfo ]= None
            """ Info about the last overload done before unloading """

    class SiloUnloadInfo(PlanStateBase):

        """ Class holding information about the unload activities at a silo """

        def __init__(self):
            super(PlanDecoderBase.SiloUnloadInfo, self).__init__()

            self.ts_start: float = 0.0
            """ State start timestamp [s] """

            self.ts_end: float = 0.0
            """ State end timestamp [s] (None if unknown) """

            self.silo_access: Optional[str] = None
            """ Silo access where the transport vehicle unloaded """

            self.tv: Optional[str] = None
            """ Transport vehicle unloading """

            self.unloaded_mass: float = 0.0
            """ Unloaded yield mass [kg] """

    def __init__(self,
                 data_manager: GlobalDataManager,
                 roads: List[Linestring],
                 machine_initial_states: Dict[int, MachineState],
                 field_initial_states: Dict[int, FieldState],
                 out_field_route_planner: OutFieldRoutePlanner,
                 problem: Problem):

        """ Decoder initialization

        Parameters
        ----------
        data_manager : GlobalDataManager
            Data manager
        roads : List[Linestring]
            Roads
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        field_initial_states : Dict[int, FieldState]
            Field initial states: {field_id: field_state}
        out_field_route_planner : OutFieldRoutePlanner
            Route/path planner for transit outside the fields
        problem : Problem
            UP problem
        """

        self._ok = False

        self._data_manager = data_manager
        self._roads = roads
        self._out_field_route_planner = out_field_route_planner

        self._field_names_map: Dict[str, Field] = dict()
        self._field_access_names_map: Dict[str, FieldAccessPoint] = dict()
        self._harvester_names_map: Dict[str, Machine] = dict()
        self._tv_names_map: Dict[str, Machine] = dict()
        self._silo_names_map: Dict[str, SiloExtended] = dict()
        self._silo_access_names_map: Dict[str, SiloAccessPoint] = dict()
        self._harvester_init_locations_names_map: Dict[str, Point] = dict()
        self._tv_init_locations_names_map: Dict[str, Point] = dict()
        self._fields_yield_mass: Dict[str, float] = dict()
        self._fields_mass_per_area: Dict[str, float] = dict()

        self._machine_states: Dict[str, List[PlanDecoderBase.PlanMachineState]] = dict()
        self._field_states: Dict[str, List[PlanDecoderBase.PlanFieldState]] = dict()
        self._field_overloads: Dict[str, PlanDecoderBase.FieldOverloads] = dict()
        self._tv_overloads: Dict[str, List[PlanDecoderBase.TVOverloadInfo]] = dict()
        self._tv_unloads: Dict[str, List[PlanDecoderBase.TVUnloadInfo]] = dict()
        self._tv_overloads_all: List[PlanDecoderBase.TVOverloadInfo] = list()
        self._silo_unloads: Dict[str, List[PlanDecoderBase.SiloUnloadInfo]] = dict()
        self._silo_states: Dict[str, List[PlanDecoderBase.PlanSiloState]] = dict()

        self.__init_names_maps(data_manager, machine_initial_states)
        self.__init_field_yield_masses(problem, field_initial_states)

    @property
    def ok(self) -> bool:
        """ Get the data manager

        Returns
        ----------
        ok : bool
            True on success
        """
        return self._ok

    @abstractmethod
    def gives_precise_machine_positions(self) -> bool:
        """ Check if the get_machine_state_at returns precise machine positions

        Returns
        ----------
        ok : bool
            True if the get_machine_state_at returns precise machine positions
        """
        pass

    @property
    def data_manager(self) -> GlobalDataManager:
        """ Get the data manager

        Returns
        ----------
        data_manager : GlobalDataManager
            Data manager
        """
        return self._data_manager

    @property
    def roads(self) -> List[Linestring]:
        """ Get the roads

        Returns
        ----------
        roads : List[Linestring]
            Roads
        """
        return self._roads

    @property
    def field_names_map(self) -> Dict[str, Field]:
        """ Get the map/dictionary of field object name -> field

        Returns
        ----------
        field_names_map : Dict[str, Field]
            Field object-names map: {field_object_name: field}
        """
        return self._field_names_map

    @property
    def field_access_names_map(self) -> Dict[str, FieldAccessPoint]:
        """ Get the map/dictionary of field-access object name -> field access point

        Returns
        ----------
        field_access_names_map : Dict[str, FieldAccessPoint]
            Field-access object-names map: {field_access_object_name: field_access_point}
        """
        return self._field_access_names_map

    @property
    def harvester_names_map(self) -> Dict[str, Machine]:
        """ Get the map/dictionary of harvester object name -> harvester

        Returns
        ----------
        harvester_names_map : Dict[str, Machine]
            Harvester object-names map: {harvester_object_name: harvester}
        """
        return self._harvester_names_map

    @property
    def tv_names_map(self) -> Dict[str, Machine]:
        """ Get the map/dictionary of transport vehicle object name -> transport vehicle

        Returns
        ----------
        tv_names_map : Dict[str, Machine]
            Transport vehicle object-names map: {transport_vehicle_object_name: transport_vehicle}
        """
        return self._tv_names_map

    @property
    def silo_names_map(self) -> Dict[str, SiloExtended]:
        """ Get the map/dictionary of silo object name -> silo

        Returns
        ----------
        silo_names_map : Dict[str, SiloExtended]
            Silo object-names map: {silo_object_name: silo}
        """
        return self._silo_names_map

    @property
    def silo_access_names_map(self) -> Dict[str, SiloAccessPoint]:
        """ Get the map/dictionary of silo-access object name -> silo access point

        Returns
        ----------
        silo_access_names_map : Dict[str, SiloAccessPoint]
            Silo-access object-names map: {silo_access_object_name: silo_access_point}
        """
        return self._silo_access_names_map

    @property
    def harvester_init_locations_names_map(self) -> Dict[str, Point]:
        """ Get the map/dictionary of harvester initial location's object name -> location/position

        Returns
        ----------
        harvester_names_map : Dict[str, Point]
            Harvester initial location object-names map: {harvester_initial_location_object_name: position}
        """
        return self._harvester_init_locations_names_map

    @property
    def tv_init_locations_names_map(self) -> Dict[str, Point]:
        """ Get the map/dictionary of transport vehicle initial location's object name -> location/position

        Returns
        ----------
        tv_init_locations_names_map : Dict[str, Point]
            transport vehicle initial location object-names map: {transport_vehicle_initial_location_object_name: position}
        """
        return self._tv_init_locations_names_map

    @property
    def fields_yield_mass(self) -> Dict[str, float]:
        """ Get the map/dictionary of field object name -> yield mass in field

        Returns
        ----------
        fields_yield_mass_map : Dict[str, float]
            Field yield-mass map: {field_object_name: yield_mass[kg]}
        """
        return self._fields_yield_mass

    @property
    def fields_mass_per_area(self) -> Dict[str, float]:
        """ Get the map/dictionary of field object name -> yield mass / area unit in field

        Returns
        ----------
        fields_mass_per_area_map : Dict[str, float]
            Field yield-mass-per-area-unit map: {field_object_name: yield_mass_per_area_unit[kg/m²]}
        """
        return self._fields_mass_per_area

    @property
    def machine_states(self) -> Dict[str, List[PlanMachineState]]:
        """ Get the decoded machines' (harvesters, transport vehicles) states (ordered by start-timestamp for each machine)

        Returns
        ----------
        machine_states : Dict[str, List[PlanMachineState]]
            Machine states: {machine_object_name: [machine_states_sorted_by_ts_start]}
        """
        return self._machine_states

    @property
    def field_states(self) -> Dict[str, List[PlanFieldState]]:
        """ Get the decoded fields' states (ordered by start-timestamp for each field)

        Returns
        ----------
        field_states : Dict[str, List[PlanFieldState]]
            Field states: {field_object_name: [field_states_sorted_by_ts_start]}
        """
        return self._field_states

    @property
    def silo_states(self) -> Dict[str, List[PlanSiloState]]:
        """ Get the decoded silos' states (ordered by start-timestamp for each silo)

        Returns
        ----------
        silo_states : Dict[str, List[PlanSiloState]]
            Silo states: {silo_object_name: [silo_states_sorted_by_ts_start]}
        """
        return self._silo_states

    @property
    def field_overloads(self) -> Dict[str, FieldOverloads]:
        """ Get the decoded fields' overloads (ordered by start-timestamp for each field)

        Returns
        ----------
        field_overloads : Dict[str, FieldOverloads]
            Field overloads: {field_object_name: [field_overloads_sorted_by_ts_start]}
        """
        return self._field_overloads

    @property
    def tv_overloads(self) -> Dict[str, List[TVOverloadInfo]]:
        """ Get the decoded transport vehicles' overloads (ordered by start-timestamp for each machine)

        Returns
        ----------
        tv_overloads : Dict[str, TVOverloadInfo]
            Transport vehicles overloads: {transport_vehicle_object_name: [transport_vehicle_overloads_sorted_by_ts_start]}
        """
        return self._tv_overloads

    @property
    def tv_unloads(self) -> Dict[str, List[TVUnloadInfo]]:
        """ Get the decoded transport vehicles' unloads (ordered by start-timestamp for each machine)

        Returns
        ----------
        tv_unloads : Dict[str, TVUnloadInfo]
            Transport vehicles unloads: {transport_vehicle_object_name: [transport_vehicle_unloads_sorted_by_ts_start]}
        """
        return self._tv_unloads

    @property
    def silo_unloads(self) -> Dict[str, List[SiloUnloadInfo]]:
        """ Get the decoded silos' unloads (ordered by start-timestamp for each silo)

        Returns
        ----------
        silo_unloads : Dict[str, SiloUnloadInfo]
            Silos unloads: {transport_vehicle_object_name: [silo_unloads_sorted_by_ts_start]}
        """
        return self._silo_unloads

    @property
    def tv_overloads_all(self) -> List[TVOverloadInfo]:
        """ Get all the decoded transport vehicles' overloads (ordered by start-timestamp)

        Returns
        ----------
        tv_overloads : Dict[str, TVOverloadInfo]
            Transport vehicles overloads: [transport_vehicle_overloads_sorted_by_ts_start]
        """
        return self._tv_overloads_all

    def get_machine_plan_state_at(self, machine_name: str, timestamp: float, ind_start: int = 0) \
            -> Union[Tuple[PlanMachineState, int], None]:
        """ Get the decoded state of a machine corresponding to a given timestamp (i.e., the last state before the given timestamp)

        Parameters
        ----------
        machine_name : str
            Machine object name
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state where the search will start. If not known, set 0.

        Returns
        ----------
        machine_state : PlanMachineState
            Machine decoded state (None on error)
        ind : int
            Index of the last state before the given timestamp (for future search)
        """

        states = self._machine_states.get(machine_name)
        if states is None:
            return None
        state_ind = self._get_state_at(states, timestamp, ind_start)
        if state_ind is None:
            return None
        (state, ind) = state_ind
        if state.activity is not self.MachineActivity.OVERLOADING or state.overloading_machine_name is None:
            state.overloading_machine_name = None
            return state, ind

        field_state_ind = self.get_field_plan_state_at(state.loc_start, timestamp)
        assert field_state_ind is not None, f'Machine {machine_name} is overloading, but loc_start ({state.loc_start}) is not a field with a valid state at the given timestamp'
        (field_state, _) = field_state_ind
        if machine_name in self.harvester_names_map.keys():
            state.overloading_machine_name = field_state.tv
        elif machine_name in self.tv_names_map.keys():
            if field_state.tv != machine_name:
                state.activity = self.MachineActivity.TRANSIT_IN_FIELD
                state.overloading_machine_name = None
        return state, ind

    def get_field_plan_state_at(self, field_name: str, timestamp: float, ind_start: int = 0) \
            -> Optional[Tuple[PlanFieldState, int]]:
        """ Get the decoded state of a field corresponding to a given timestamp (i.e., the last state before the given timestamp)

        Parameters
        ----------
        field_name : str
            Field object name
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state where the search will start. If not known, set 0.

        Returns
        ----------
        field_state : PlanFieldState
            Field decoded state (None on error)
        ind : int
            Index of the last state before the given timestamp (for future search)
        """
        states = self._field_states.get(field_name)
        if states is None:
            return None
        return self._get_state_at(states, timestamp, ind_start)

    def get_silo_plan_state_at(self, silo_name: str, timestamp: float, ind_start: int = 0) \
            -> Optional[Tuple[PlanSiloState, int]]:
        """ Get the decoded state of a silo corresponding to a given timestamp (i.e., the last state before the given timestamp)

        Parameters
        ----------
        silo_name : str
            Silo object name
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state where the search will start. If not known, set 0.

        Returns
        ----------
        silo_state : PlanSiloState
            Silo decoded state (None on error)
        ind : int
            Index of the last state before the given timestamp (for future search)
        """
        states = self._silo_states.get(silo_name)
        if states is None:
            return None
        return self._get_state_at(states, timestamp, ind_start)

    def get_tv_overload_at(self, machine_name: str, timestamp: float, ind_start: int = 0) \
            -> Union[Tuple[TVOverloadInfo, int], None]:
        """ Get the decoded transport vehicle' overload corresponding to a given timestamp (i.e., the overload that 'includes' the timestamp)

        Parameters
        ----------
        machine_name : str
            Machine object name
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state where the search will start. If not known, set 0.

        Returns
        ----------
        overload_info : TVOverloadInfo
            Transport vehicle' overload (None on error or if no overload was done at the given timestamp)
        ind : int
            Index of the last state before the given timestamp (for future search)
        """

        states = self._tv_overloads.get(machine_name)
        if states is None:
            return None
        state_ind = self._get_state_at(states, timestamp, ind_start)
        if state_ind is None:
            return None
        (state, ind) = state_ind
        if state.ts_end > timestamp + 1e-6:
            return None
        return state, ind

    def get_tv_unload_at(self, machine_name: str, timestamp: float, ind_start: int = 0) \
            -> Optional[Tuple[TVUnloadInfo, int]]:
        """ Get the decoded transport vehicle' unload corresponding to a given timestamp (i.e., the unload that 'includes' the timestamp)

        Parameters
        ----------
        machine_name : str
            Machine object name
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state where the search will start. If not known, set 0.

        Returns
        ----------
        overload_info : TVUnloadInfo
            Transport vehicle' unload (None on error or if no overload was done at the given timestamp)
        ind : int
            Index of the last state before the given timestamp (for future search)
        """

        states = self._tv_unloads.get(machine_name)
        if states is None:
            return None
        state_ind = self._get_state_at(states, timestamp, ind_start)
        if state_ind is None:
            return None
        (state, ind) = state_ind
        if state.ts_end > timestamp + 1e-6:
            return None
        return state, ind

    def __init_names_maps(self,
                          data_manager: GlobalDataManager,
                          machine_initial_states: Dict[int, MachineState]):
        """ Initialize the internal object-names maps

        Parameters
        ----------
        data_manager : GlobalDataManager
            Data manager
        machine_initial_states : Dict[int, MachineState]
            Machine initial states: {machine_id: machine_state}
        """

        for f in data_manager.fields.values():
            self._field_names_map[get_field_location_name(f.id)] = f
            if len(f.subfields) > 0:
                for i, ap in enumerate(f.subfields[0].access_points):
                    self._field_access_names_map[get_field_access_location_name(f.id, i)] = ap
        for s in data_manager.silos.values():
            self._silo_names_map[get_silo_location_name(s.id)] = s
            for i, ap in enumerate(s.access_points):
                self._silo_access_names_map[get_silo_access_location_name(s.id, i)] = ap
        for m in data_manager.machines.values():
            state = machine_initial_states.get(m.id)
            if m.machinetype == MachineType.HARVESTER:
                map1 = self._harvester_names_map
                map2 = self._harvester_init_locations_names_map
                name = get_harvester_name(m.id)
            elif m.machinetype == MachineType.OLV:
                name = get_tv_name(m.id)
                map1 = self._tv_names_map
                map2 = self._tv_init_locations_names_map
            else:
                continue
            map1[name] = m
            if state is not None:
                map2[ get_machine_initial_location_name(name) ] = state.position

    def __init_field_yield_masses(self,
                                  problem: Problem,
                                  field_initial_states: Dict[int, FieldState]):
        """ Initialize the internal field yield-masses maps

        Parameters
        ----------
        problem : Problem
            UP problem
        field_initial_states : Dict[int, FieldState]
            Field initial states: {field_id: field_state}
        """

        field_objects = problem.objects(upt.Field)
        for field_object in field_objects:
            field_name = f'{field_object}'
            field_id = get_field_id_from_location_name(field_name)
            if field_id is None:
                continue

            init_state: FieldState = field_initial_states.get(field_id)

            mass_per_area = FieldState.DEFAULT_AVG_MASS_PER_AREA_T_HA
            harvested_percentage_start = 0.0
            if init_state is not None:
                harvested_percentage_start = max(0.0, min(100.0, init_state.harvested_percentage))
                mass_per_area = init_state.avg_mass_per_area_t_ha

            field_yield_mass_total = problem.fluent(fn.field_yield_mass_total.value)
            _field_yield_mass = float(problem.initial_value(field_yield_mass_total(field_object)).constant_value())
            _field_yield_mass_total = 100 * _field_yield_mass / (100.0-harvested_percentage_start)

            self._fields_mass_per_area[field_name] = mass_per_area
            self._fields_yield_mass[field_name] = _field_yield_mass_total

    @staticmethod
    def _add_state(states_list: List[PlanStateBase],
                    state: PlanStateBase,
                    remove_future_states: bool = True):

        """ Add a (machine, field, silo, overload) state to a given list of states (sorting by the states' start timestamp ts_start)

        Parameters
        ----------
        states_list : List[PlanStateBase]
            [in, out] List of states where th state will de added
        state : PlanStateBase
            State to be added
        remove_future_states : bool
            If True, all states in the list that have a start timestamp (ts_start) higher than the start timestamp of the new state will be removed
        """

        i = len(states_list) - 1
        while i >= 0:
            if state.ts_start >= states_list[i].ts_start:
                break
            if remove_future_states:
                states_list.pop()
            i -= 1
        states_list.insert(i + 1, state)

    _StateType = TypeVar('_StateType', bound=PlanStateBase)

    @staticmethod
    def _get_state_at(states: List[_StateType], timestamp: float, ind_start: int = 0) \
            -> Union[Tuple[_StateType, int], None]:

        """ Get the decoded state from a given list of states (sorted by ts_start) corresponding to a given timestamp (i.e., the last state before the given timestamp)

        Parameters
        ----------
        states : List[PlanStateBase]
            List of states
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state where the search will start. If not known, set 0.

        Returns
        ----------
        machine_state : PlanStateBase | None
            Decoded state (None on error)
        ind : int
            Index of the last state before the given timestamp (for future search)
        """

        if len(states) == 0:
            return None
        if ind_start >= len(states)-1:
            return states[-1], len(states)-1
        ind_start = max(0, ind_start)
        for i in range(len(states) - ind_start -1):
            if timestamp < states[ind_start+i+1].ts_start :
                return states[ind_start+i], i
        return states[-1], len(states)-1

    def _get_point_from_machine_location(self, loc_name: str) -> Tuple[Union[Point, None], bool]:

        """ Get the point/position of a given machine location

        In the case of fields and silos, the position corresponds to the centroid of the field/silo boundary

        Parameters
        ----------
        loc_name : str
            Location object name

        Returns
        ----------
        point : Point | None
            Position/point (None on error)
        out_of_location : bool
            True if the machine location corresponds to 'outside' of a location (i.e., not inside a field or silo)
        """

        out_of_location = True
        pt = self._harvester_init_locations_names_map.get(loc_name)
        if pt is None:
            pt = self._tv_init_locations_names_map.get(loc_name)
        if pt is None:
            pt = self._field_access_names_map.get(loc_name)
        if pt is None:
            pt = self._silo_access_names_map.get(loc_name)
        if pt is None:
            out_of_location = False
            field = self._field_names_map.get(loc_name)
            if field is not None:
                pt = getCentroid2(field.subfields[0].boundary_outer)
        if pt is None:
            silo = self._silo_names_map.get(loc_name)
            if silo is not None:
                if len(silo.geometry.points > 3):
                    pt = getCentroid2(silo.geometry)
                else:
                    pt = silo
        return pt, out_of_location

    def _generate_silo_states_from_unloads(self):
        self._silo_states = dict()
        for silo, _unloads in self._silo_unloads.items():
            silo_state = PlanDecoderBase.PlanSiloState()
            silo_state.ts_start = 0.0
            silo_state.ts_end = None
            silo_state.yield_mass_start = silo_state.yield_mass_end = 0.0
            silo_states = [silo_state]
            self._silo_states[silo] = silo_states

            ts_cuts = list()

            for unload in _unloads:
                ts_cuts.append(unload.ts_start)
                ts_cuts.append(unload.ts_end)

            ts_cuts.sort()
            unloads = _unloads.copy()
            for i, ts_cut in enumerate(ts_cuts):
                if i+1 >= len(ts_cuts):
                    break
                ts_cut_next = ts_cuts[i+1]
                unloaded_mass = 0.0
                unloads_to_remove = list()
                for unload in unloads:
                    if unload.ts_end < ts_cut:
                        unloads_to_remove.append(unload)
                        continue
                    if unload.ts_start > ts_cut_next:
                        break
                    unloaded_mass += max(0.0, unload.unloaded_mass * min( 1.0,
                                                                          (ts_cut_next - ts_cut) / (unload.ts_end - unload.ts_start)))

                silo_state_prev = silo_states[-1]
                silo_state_prev.ts_end = ts_cut
                silo_state = PlanDecoderBase.PlanSiloState()
                silo_state.ts_start = ts_cut
                silo_state.ts_end = ts_cut_next
                silo_state.yield_mass_start = silo_state_prev.yield_mass_end
                silo_state.yield_mass_end = silo_state_prev.yield_mass_end + unloaded_mass
                silo_states.append(silo_state)

                for unload in unloads_to_remove:
                    unloads.remove(unload)

    def get_machine_state_at(self, machine_name: str, timestamp: float, ind_start: int = 0) \
            -> Union[Tuple[MachineState, int], Tuple[None, None]]:
        """ Get the interpolated state of a machine corresponding at a given timestamp

        The state values (position, bunker_mass, etc.) of the machine will be computed (interpolated) based on the known plan states of the machine before and after the given timestamp

        Parameters
        ----------
        machine_name : str
            Machine object name
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state where the search will start. If not known, set 0.

        Returns
        ----------
        machine_state : MachineState
            Machine state (None on error)
        ind : int
            Index of the last state before the given timestamp (for future search)
        """

        plan_state_ind = self.get_machine_plan_state_at(machine_name, timestamp, ind_start)
        if plan_state_ind is None:
            return None, None
        (plan_state, ind_ret) = plan_state_ind

        pt_from, out_of_location_from = self._get_point_from_machine_location(plan_state.loc_start)
        if pt_from is None:
            raise ValueError(f'Invalid loc_start = {plan_state.loc_start}')

        if plan_state.ts_end is None or plan_state.ts_start >= plan_state.ts_end:
            timestamp_rel = 0.0
        else:
            timestamp_rel = min(1.0, max(0.0, (timestamp - plan_state.ts_start) / (plan_state.ts_end - plan_state.ts_start) ) )

        state = MachineState()
        state.timestamp = timestamp
        state.timestamp_free = timestamp
        state.location_name = plan_state.loc_start
        state.bunker_mass = 0.0
        state.bunker_volume = 0.0

        if machine_name in self.harvester_names_map.keys():
            state.overloading_machine_id = get_tv_id_from_name(plan_state.overloading_machine_name)
        else:
            state.overloading_machine_id = get_harvester_id_from_name(plan_state.overloading_machine_name)

        if plan_state.bunker_mass_start is not None:
            if plan_state.bunker_mass_end is not None:
                state.bunker_mass = (1-timestamp_rel) * plan_state.bunker_mass_start + \
                                    timestamp_rel * plan_state.bunker_mass_end
            else:
                state.bunker_mass = plan_state.bunker_mass_start

        if plan_state.loc_end is None or plan_state.ts_end is None or plan_state.ts_start >= plan_state.ts_end:
            state.position = get_copy_aro(point_ref(pt_from))
            return state, ind_ret

        pt_to, out_of_location_to = self._get_point_from_machine_location(plan_state.loc_end)
        if pt_to is None:
            raise ValueError(f'Invalid loc_end = {plan_state.loc_end}')

        if timestamp >= plan_state.ts_end:
            state.location_name = plan_state.loc_end
            state.position = get_copy_aro(point_ref(pt_from))
            return state, ind_ret

        if not out_of_location_from:
            state.location_name = plan_state.loc_start
        elif not out_of_location_to:
            state.location_name = plan_state.loc_end
        else:
            state.location_name = None

        machine = self._harvester_names_map.get(machine_name)
        if machine is None:
            machine = self._tv_names_map.get(machine_name)

        if out_of_location_from and out_of_location_to:
            path = self._out_field_route_planner.get_path(pt_from, pt_to, machine)
        else:
            path = [pt_from, pt_to]
        state.position = getPointAtRelativeDist(path, timestamp_rel)[0]

        return state, ind_ret


    def get_field_state_at(self, field_name: str, timestamp: float, ind_start: int = 0) \
            -> Union[Tuple[FieldState, int], Tuple[None, None]]:

        """ Get the interpolated state of a field corresponding at a given timestamp

        The state values (harvested_percentage, etc.) of the field will be computed (interpolated) based on the known plan states of the field before and after the given timestamp

        Parameters
        ----------
        field_name : str
            Field object name
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state where the search will start. If not known, set 0.

        Returns
        ----------
        field_state : FieldState
            Field state (None on error)
        ind : int
            Index of the last state before the given timestamp (for future search)
        """

        plan_state_ind = self.get_field_plan_state_at(field_name, timestamp, ind_start)
        if plan_state_ind is None:
            return None, None
        (plan_state, ind_ret) = plan_state_ind

        state = FieldState()
        state.avg_mass_per_area_t_ha = self._fields_mass_per_area.get(field_name)
        if plan_state.harvested_percentage_end is None or plan_state.ts_end is None:
            state.harvested_percentage = plan_state.harvested_percentage_start
        elif timestamp >= plan_state.ts_end or plan_state.ts_end <= plan_state.ts_start:
            state.harvested_percentage = plan_state.harvested_percentage_end
        else:
            dt = plan_state.ts_end - plan_state.ts_start
            dpc = plan_state.harvested_percentage_end - plan_state.harvested_percentage_start
            state.harvested_percentage = (plan_state.harvested_percentage_start
                                          + dpc * (timestamp - plan_state.ts_start) / dt)

        return state, ind_ret

    def get_silo_state_at(self, silo_name: str, timestamp: float, ind_start: int = 0) \
            -> Union[Tuple[SiloState, int], Tuple[None, None]]:

        """ Get the interpolated state of a silo corresponding at a given timestamp

        The state values (harvested_percentage, etc.) of the silo will be computed (interpolated) based on the known plan states of the silo before and after the given timestamp

        Parameters
        ----------
        silo_name : str
            Silo object name
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state where the search will start. If not known, set 0.

        Returns
        ----------
        silo_state : SiloState
            Silo state (None on error)
        ind : int
            Index of the last state before the given timestamp (for future search)
        """

        plan_state_ind = self.get_silo_plan_state_at(silo_name, timestamp, ind_start)
        if plan_state_ind is None:
            return None, None
        (plan_state, ind_ret) = plan_state_ind

        state = SiloState()
        if plan_state.yield_mass_end is None or plan_state.ts_end is None:
            state.yield_mass = plan_state.yield_mass_start
        elif timestamp >= plan_state.ts_end or plan_state.ts_end <= plan_state.ts_start:
            state.yield_mass = plan_state.yield_mass_end
        else:
            dt = plan_state.ts_end - plan_state.ts_start
            dpc = plan_state.yield_mass_end - plan_state.yield_mass_start
            state.yield_mass = (plan_state.yield_mass_start
                                + dpc * (timestamp - plan_state.ts_start) / dt)

        return state, ind_ret

    def print_states(self, filename: str,
                     include_field_states: bool = True,
                     include_machine_states: bool = True,
                     include_silo_states: bool = True,
                     include_field_overloads: bool = True,
                     include_tv_overloads: bool = True,
                     include_tv_unloads: bool = True,
                     include_tv_overloads_all: bool = True):

        """ Save the decoded states in a file

        The state values (harvested_percentage, etc.) of the silo will be computed (interpolated) based on the known plan states of the silo before and after the given timestamp

        Parameters
        ----------
        filename : str
            Output file name/path
        include_field_states : bool
            Include field states?
        include_machine_states : bool
            Include machine (harvesters, transport vehicles) states?
        include_silo_states : bool
            Include silo states?
        include_field_overloads : bool
            Include field overloads?
        include_tv_overloads : bool
            Include transport vehicle overloads (divided by machine)?
        include_tv_unloads : bool
            Include transport vehicle unloads (divided by machine)?
        include_tv_overloads_all : bool
            Include transport vehicle overloads (all)?
        """

        f = open(filename, 'w')
        if include_field_states:
            f.write('*** FIELD STATES *** \n\n')
            for field_name, states in self._field_states.items():
                f.write(f'{field_name.upper()}\n')
                f.write(f'ts_start;ts_end;harv_state;'
                        f'harvested_percentage_start;harvested_percentage_end;'
                        f'harvested_yield_mass_start;harvested_yield_mass_end;'
                        f'harvester;tv;'
                        f'\n')
                for state in states:
                    f.write(f'{state.ts_start};{state.ts_end};{state.state};'
                            f'{state.harvested_percentage_start};{state.harvested_percentage_end};'
                            f'{state.harvested_yield_mass_start};{state.harvested_yield_mass_end};'
                            f'{state.harvester};{state.tv}\n')
                f.write(f'\n')
            f.write(f'\n')

        if include_field_overloads:
            f.write('*** FIELD OVERLOADS *** \n\n')
            for field_name, overloads in self._field_overloads.items():
                f.write(f'{field_name.upper()}\n')
                f.write(f'ts_start;ts_end;tv;harvester\n')
                for overload in overloads.overloads:
                    f.write(f'{overload.ts_start};{overload.ts_end};'
                            f'{overload.tv};{overloads.harv}\n')
                f.write(f'\n')
            f.write(f'\n')

        if include_machine_states:
            f.write('*** MACHINE STATES *** \n\n')
            for machine_name, states in self._machine_states.items():
                f.write(f'{machine_name.upper()}\n')
                f.write(f'ts_start;ts_end;'
                        f'loc_start;loc_end;'
                        f'pt_start;pt_end;'
                        f'bunker_mass_start;bunker_mass_end;'
                        f'transit_time_start;transit_time_end;'
                        f'action;activity;'
                        f'overloading_machine\n')
                for state in states:
                    pt_start = pt_end = ''
                    if state.pt_start is not None:
                        pt_start =  f'({state.pt_start.x},{state.pt_start.y})'
                    if state.pt_end is not None:
                        pt_end = f'({state.pt_end.x},{state.pt_end.y})'
                    f.write(f'{state.ts_start};{state.ts_end};'
                            f'{state.loc_start};{state.loc_end};'
                            f'{pt_start};{pt_end};'
                            f'{state.bunker_mass_start};{state.bunker_mass_end};'
                            f'{state.transit_time_start};{state.transit_time_end};'
                            f'{state.action};{state.activity};'
                            f'{state.overloading_machine_name};'
                            f'\n')
                f.write(f'\n')
            f.write(f'\n')

        if include_tv_overloads:
            f.write('*** TV OVERLOADS *** \n\n')
            for tv_name, overloads in self._tv_overloads.items():
                f.write(f'{tv_name.upper()}\n')
                f.write(f'ts_start;ts_end;field;harvester\n')
                for overload in overloads:
                    f.write(f'{overload.ts_start};{overload.ts_end};'
                            f'{overload.field};{overload.harv}\n')
                f.write(f'\n')
            f.write(f'\n')

        if include_tv_unloads:
            f.write('*** TV UNLOADS *** \n\n')
            for tv_name, unloads in self._tv_unloads.items():
                f.write(f'{tv_name.upper()}\n')
                f.write(f'ts_start;ts_end;field_overload;harvester_overload\n')
                for unload in unloads:
                    if unload.overload_info is not None:
                        f.write(f'{unload.ts_start};{unload.ts_end};'
                                f'{unload.overload_info.field};{unload.overload_info.harv}\n')
                    else:
                        f.write(f'{unload.ts_start};{unload.ts_end};'
                                f'{unload.overload_info};{unload.overload_info}\n')
                f.write(f'\n')
            f.write(f'\n')

        if include_tv_overloads_all:
            f.write('*** TV OVERLOADS (ALL) *** \n\n')
            f.write(f'ts_start;ts_end;field;harvester\n')
            for overload in self._tv_overloads_all:
                f.write(f'{overload.ts_start};{overload.ts_end};'
                        f'{overload.field};{overload.harv}\n')
            f.write(f'\n')

        if include_silo_states:
            f.write('*** SILO STATES *** \n\n')
            for field_name, states in self._silo_states.items():
                f.write(f'{field_name.upper()}\n')
                f.write(f'ts_start;ts_end;'
                        f'yield_mass_start;yield_mass_end'
                        f'\n')
                for state in states:
                    f.write(f'{state.ts_start};{state.ts_end};'
                            f'{state.yield_mass_start};{state.yield_mass_end}\n')
                f.write(f'\n')
            f.write(f'\n')

        f.close()
