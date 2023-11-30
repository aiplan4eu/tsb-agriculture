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

from copy import deepcopy
from typing import Dict, Optional
from util_arolib.types import Point, MachineDynamicInfo, MachineId2DynamicInfoMap, get_copy_aro


class MachineState:

    """ Machine state (for harvesters and transport vehicles) """

    def __init__(self):
        self.timestamp: float = 0.0
        """ Timestamp of the state """

        self.timestamp_free: float = 0.0
        """ Timestamp in which the machine is free for planning """

        self.position: Point = Point()
        """ Position """

        self.bunker_mass: float = 0.0
        """ Yield mass [kg] in the bunker """

        self.bunker_volume: float = 0.0
        """ Yield volume [m³] in the bunker """

        self.location_name: Optional[str] = None
        """ Name of the location of the machine """

        self.overloading_machine_id: Optional[int] = None
        """ If the machine is overloading, this is the id of the other machine participating in the overload """

    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls)
        result.__dict__.update(self.__dict__)
        return result

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == 'position':
                setattr(result, k, get_copy_aro(v))
            else:
                setattr(result, k, deepcopy(v, memo))
        return result


    def to_aro_machine_state(self) -> MachineDynamicInfo:

        """ Parce to arolib type 'MachineDynamicInfo'


        Returns
        ----------
        arolib_state : MachineDynamicInfo
            Arolib machine state
        """

        mdi = MachineDynamicInfo()
        mdi.position = Point(self.position)
        mdi.bunkerMass = self.bunker_mass
        mdi.bunkerVolume = self.bunker_volume
        mdi.timestamp = self.timestamp
        return mdi

    def from_aro_machine_state(self, mdi: MachineDynamicInfo):

        """ Parce from arolib type 'MachineDynamicInfo'


        Parameters
        ----------
        mdi : MachineDynamicInfo
            Arolib machine state
        """

        self.position = Point(mdi.position)
        self.bunker_mass = mdi.bunkerMass
        self.bunker_volume = mdi.bunkerVolume
        self.timestamp = mdi.timestamp

    @staticmethod
    def to_aro_machine_states_map(machines_states: Dict[int, 'MachineState']) -> MachineId2DynamicInfoMap:

        """ Parce a machines' states map (dictionary) to the corresponding map of arolib machine states

        Parameters
        ----------
        machines_states : Dict[int, 'MachineState']
            Input machine states map: {machine_id, machine_state}

        Returns
        ----------
        arolib_machines_states : MachineId2DynamicInfoMap
            Arolib machine states map: {machine_id, arolib_machine_state}
        """

        mdi = MachineId2DynamicInfoMap()
        for m_id, state in machines_states.items():
            mdi[m_id] = state.to_aro_machine_state()
        return mdi

    @staticmethod
    def to_aro_machine_states_dict(machines_states: Dict[int, 'MachineState']) -> Dict[int, MachineDynamicInfo]:

        """ Parce a machines' states map (dictionary) to the corresponding dictionary of arolib machine states

        Parameters
        ----------
        machines_states : Dict[int, 'MachineState']
            Input machine states map: {machine_id, machine_state}

        Returns
        ----------
        arolib_machines_states : Dict[int, MachineDynamicInfo]
            Arolib machine states map: {machine_id, arolib_machine_state}
        """

        mdi: Dict[int, MachineDynamicInfo] = dict()
        for m_id, state in machines_states.items():
            mdi[m_id] = state.to_aro_machine_state()
        return mdi


class FieldState:

    """ Field state """

    DEFAULT_AVG_MASS_PER_AREA_T_HA: float = 50.0
    """ Default average yield mass per area [t/ha] """

    def __init__(self):
        self.avg_mass_per_area_t_ha: float = FieldState.DEFAULT_AVG_MASS_PER_AREA_T_HA
        """ Average yield mass per area [t/ha] in the field """

        self.harvested_percentage: float = 0.0  # [0, 100]
        """ Percentage [0-100 %] of the field that is harvested """

class SiloState:

    """ Silo state """

    def __init__(self):
        self.yield_mass: float = 0.0
        """ Amount of yield-mass [kg] stored at the silo """