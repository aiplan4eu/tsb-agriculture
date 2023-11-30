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
import math
from enum import auto
from typing import Dict, List, Union, Tuple
import numpy as np
from functools import partial
import matplotlib
import matplotlib.pyplot as pyplot
import time
from threading import Lock
from tkinter import TclError

from util_arolib.types import *
from util_arolib.geometry import getCentroid2, getPointAtRelativeDist
from route_planning.types import MachineState, FieldState
from route_planning.outfield_route_planning import OutFieldRoutePlanner
from post_processing.plan_decoder_base import PlanDecoderBase
from post_processing.temporal_plan_decoder import TemporalPlanDecoder
from post_processing.sequential_plan_decoder import SequentialPlanDecoder
from visualization.scene_plotter import ScenePlotter
from up_interface.problem_encoder.names_helper import *
import up_interface.config as conf

from unified_planning.plans.sequential_plan import SequentialPlan
from unified_planning.plans.time_triggered_plan import TimeTriggeredPlan
from unified_planning.shortcuts import *

from util_arolib.types import Point, Linestring
from management.global_data_manager import GlobalDataManager


class PlanSimulator1:

    """ Simple spatio/temporal graphical plan simulator for sequential and temporal plans of the agriculture use-case """

    __FieldHarvestingState_Type = None

    class SimMachineState:

        """ Machine state """

        def __init__(self):
            self.ts_start: float = 0.0
            """ Timestamp - start """

            self.ts_end: Optional[float] = None
            """ Timestamp - end """

            self.loc_name: Optional[str] = None
            """ Location name """

            self.pt_start: Optional[Point] = None
            """ Location point - start """

            self.pt_end: Optional[Point] = None
            """ Location point - end """

            self.mass_start: Optional[float] = None
            """ Mass in the bunker - start """

            self.mass_end: Optional[float] = None
            """ Mass in the bunker - end """

    class SimFieldState:

        """ Field state """

        def __init__(self):
            self.ts_start = 0.0
            """ Timestamp - start """

            self.ts_end = None
            """ Timestamp - end """

            self.state = PlanSimulator1.__FieldHarvestingState_Type.UNRESERVED
            """ State """

    class PlotType(Enum):

        """ Enum for plot types """

        SCENE = auto()
        FIELDS_HARV_AREA_PERCENTAGE = auto()
        TVS_BUNKER_MASS_PERCENTAGE = auto()
        SILOS_UNLOADED_MASS = auto()
        PROCESS_TIME = auto()


    def __init__(self,
                 data_manager: GlobalDataManager,
                 roads: List[Linestring],
                 machine_initial_states: Dict[int, MachineState],
                 field_initial_states: Dict[int, FieldState],
                 out_field_route_planner: OutFieldRoutePlanner,
                 problem: Problem,
                 problem_settings: conf.GeneralProblemSettings,
                 plan_or_decoder: Union[SequentialPlan, TimeTriggeredPlan, PlanDecoderBase]):

        """ Class initialization.

        Parameters
        ----------
        data_manager : GlobalDataManager
            Data manager holding the problem data (fields, machines, etc)
        roads : List[Linestring]
            Roads (as linestrings) for transit outside the fields
        machine_initial_states : Dict[int, MachineState]
            Machines' initial states: {machine_id: machine_state}
        field_initial_states : Dict[int, FieldState]
            Fields' initial states: {field_id: field_state}
        out_field_route_planner : OutFieldRoutePlanner
            Planner used to plan the transit of the machines outside the fields
        problem : Problem
            UP problem
        problem_settings : config.GeneralProblemSettings
            Problem settings used to define the problem
        plan_or_decoder : SequentialPlan, TimeTriggeredPlan, PlanDecoderBase
            Plan to be simulated or a plan decoder
        """

        if isinstance(plan_or_decoder, TimeTriggeredPlan):
            self.__plan_decoder = TemporalPlanDecoder(data_manager, roads,
                                                      machine_initial_states, field_initial_states,
                                                      out_field_route_planner,
                                                      problem, plan_or_decoder)
        elif isinstance(plan_or_decoder, SequentialPlan):
            self.__plan_decoder = SequentialPlanDecoder(data_manager, roads,
                                                        machine_initial_states, field_initial_states,
                                                        out_field_route_planner,
                                                        problem, plan_or_decoder)
        else:
            self.__plan_decoder = plan_or_decoder

        PlanSimulator1.__FieldHarvestingState_Type = self.__plan_decoder.FieldHarvestingState

        self.__data_manager = data_manager
        self.__roads = roads
        self.__out_field_route_planner = out_field_route_planner
        self.__scene_plotter: Optional[ScenePlotter] = None
        self.__period = 0.1
        self.__speed_factor = 50
        self.__stop: bool = True
        self.__machine_spots_at_location: Dict[str, Dict[str, Point]] = dict()

        self.__machine_states: Dict[str, List[PlanSimulator1.SimMachineState]] = dict()

        self.__last_timestamp = 0.0

        self.__init_states()
        self.__init_machine_spots_at_location()

    @property
    def plan_decoder(self) -> Union[TemporalPlanDecoder, SequentialPlanDecoder]:

        """ Get the plan decoder used by the simulator.

        Returns
        ----------
        decoder : TemporalPlanDecoder, SequentialPlanDecoder
            Plan decoder used by the simulator
        """

        return self.__plan_decoder

    @property
    def last_timestamp(self) -> float:

        """ Get the last timestamp before the simulator was closed.

        Returns
        ----------
        last_timestamp : float
            Last timestamp before the simulator was closed
        """

        return self.__last_timestamp

    def __init_states(self):

        """ Initialize the machines' and fields' states """

        for machine_name, plan_states in self.__plan_decoder.machine_states.items():
            states = list()
            self.__machine_states[machine_name] = states
            for i, plan_state in enumerate(plan_states):
                machine_state = PlanSimulator1.SimMachineState()
                states.append(machine_state)
                machine_state.ts_start = plan_state.ts_start
                machine_state.ts_end = plan_state.ts_end
                if plan_state.loc_start is not None and \
                    ( plan_state.loc_start in self.__plan_decoder.field_names_map.keys()
                      or plan_state.loc_start in self.__plan_decoder.silo_names_map.keys() ):
                    machine_state.loc_name = plan_state.loc_start
                else:
                    machine_state.pt_start = self.__plan_decoder.harvester_init_locations_names_map.get(plan_state.loc_start)
                    if machine_state.pt_start is None:
                        machine_state.pt_start = self.__plan_decoder.tv_init_locations_names_map.get(plan_state.loc_start)
                    if machine_state.pt_start is None:
                        machine_state.pt_start = self.__plan_decoder.field_access_names_map.get(plan_state.loc_start)
                    if machine_state.pt_start is None:
                        machine_state.pt_start = self.__plan_decoder.silo_access_names_map.get(plan_state.loc_start)
                    if machine_state.pt_start is None:
                        raise ValueError(f'Invalid machines state loc_start {plan_state.loc_start}')

                if plan_state.loc_end is not None and \
                    ( plan_state.loc_end in self.__plan_decoder.field_names_map.keys()
                      or plan_state.loc_end in self.__plan_decoder.silo_names_map.keys() ):
                    machine_state.loc_name = plan_state.loc_end
                else:
                    if plan_state.loc_end is not None:
                        machine_state.pt_end = self.__plan_decoder.harvester_init_locations_names_map.get(plan_state.loc_end)
                        if machine_state.pt_end is None:
                            machine_state.pt_end = self.__plan_decoder.tv_init_locations_names_map.get(plan_state.loc_end)
                        if machine_state.pt_end is None:
                            machine_state.pt_end = self.__plan_decoder.field_access_names_map.get(plan_state.loc_end)
                        if machine_state.pt_end is None:
                            machine_state.pt_end = self.__plan_decoder.silo_access_names_map.get(plan_state.loc_end)
                        if machine_state.pt_end is None:
                            raise ValueError(f'Invalid machines state loc_end {plan_state.loc_end}')

    def __init_machine_spots_at_location(self):

        """ Initialize the machines' spots at the problem locations (for display) """

        delta_machine_pos = 20.0
        for i in range(2):
            loc_states = self.__plan_decoder.field_names_map
            if i != 0:
                loc_states = self.__plan_decoder.silo_names_map
            for loc_name, loc in loc_states.items():
                self.__machine_spots_at_location[loc_name] = dict()
                centroid = getCentroid2(loc.outer_boundary) if i == 0 else getCentroid2(loc.geometry)
                ref_point = Point(centroid.x, centroid.y)
                ref_point.y += 0.5 * delta_machine_pos
                ref_point.x -= ( 0.5 * (len(self.__plan_decoder.harvester_names_map.keys())-1) * delta_machine_pos )
                for machine_name, m in self.__plan_decoder.harvester_names_map.items():
                    self.__machine_spots_at_location[loc_name][machine_name] = Point(ref_point.x, ref_point.y)
                    ref_point.x += delta_machine_pos
                ref_point = Point(centroid.x, centroid.y)
                ref_point.y -= 0.5 * delta_machine_pos
                ref_point.x -= ( 0.5 * (len(self.__plan_decoder.tv_names_map.keys())-1) * delta_machine_pos )
                for machine_name, m in self.__plan_decoder.tv_names_map.items():
                    self.__machine_spots_at_location[loc_name][machine_name] = Point(ref_point.x, ref_point.y)
                    ref_point.x += delta_machine_pos

    @staticmethod
    def __get_state_at(states: List[Union[SimMachineState, SimFieldState]], timestamp:float, ind_start: int = 0) \
        -> Optional[Tuple[Union[SimMachineState, SimFieldState], int]]:

        """ Get the last state before the given timestamp from the given list of states.

        Parameters
        ----------
        states : List[Union[SimMachineState, SimFieldState]]
            Input list of states used for the search, sorted by timestamp (start)
        timestamp : float
            Timestamp [s]
        ind_start : int
            Index of the state (in the list of states) where the search will start. If not known, set 0.

        Returns
        ----------
        state : SimMachineState, SimFieldState
            Last state before the given timestamp
        index: int
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

    def print_states(self, filename: str):

        """ Save the decoded field and machine states in a file.

        Parameters
        ----------
        filename : str
            Output file name/path
        """

        f = open(filename, 'w')
        for field_name, states in self.__plan_decoder.field_states.items():
            f.write(f'{field_name.upper()}\n')
            f.write(f'ts_start;ts_end;harv_state\n')
            for state in states:
                f.write(f'{state.ts_start};{state.ts_end};{state.state}\n')
            f.write(f'\n')
        f.write(f'\n')
        for machine_name, states in self.__machine_states.items():
            f.write(f'{machine_name.upper()}\n')
            f.write(f'ts_start;ts_end;loc_name;pt_start;pt_end\n')
            for state in states:
                pt_start = f'{state.pt_start}'
                if state.pt_start is not None:
                    pt_start = f'({state.pt_start.x},{state.pt_start.y})'
                pt_end = f'{state.pt_end}'
                if state.pt_end is not None:
                    pt_end = f'({state.pt_end.x},{state.pt_end.y})'
                f.write(f'{state.ts_start};{state.ts_end};{state.loc_name};'
                        f'{pt_start};{pt_end};\n')
            f.write(f'\n')
        f.close()

    def set_sample_period(self, per: float):

        """ Set the simulation sample period.

        Parameters
        ----------
        per : float
            Sample period [s]
        """

        self.__period = per

    def set_speed_factor(self, speed_factor: float):

        """ Set the simulation speed factor.

        Parameters
        ----------
        speed_factor : float
            Simulation speed factor
        """

        self.__speed_factor = speed_factor

    def stop(self):

        """ Stop the simulation and close."""

        self.__stop = True


    def start(self, ts_start: float = 0.0, period: float = None, speed_factor: float = None, plot_in_separate_windows = False):

        """ Start simulation with the given parameters.

        Parameters
        ----------
        ts_start : float
            Timestamp [s] from when to start the simulation.
        period : float, None
            Simulation sample period [s] (optional)
        speed_factor : float, None
            Simulation speed factor (optional)
        plot_in_separate_windows : bool
            Display the plots in separate windows (True) or in one window (False)
        """

        self.__stop = False

        if period is not None:
            self.set_sample_period(period)
        if speed_factor is not None:
            self.set_speed_factor(speed_factor)

        field_inds = {field_name: 0 for field_name in self.__plan_decoder.field_states.keys()}
        field_inds_2 = {field_name: 0 for field_name in self.__plan_decoder.field_states.keys()}
        machine_inds = {field_name: 0 for field_name in self.__machine_states.keys()}
        machine_inds_2 = {field_name: 0 for field_name in self.__machine_states.keys()}
        silo_inds = {silo_name: 0 for silo_name in self.__plan_decoder.silo_states.keys()}
        silo_inds_2 = {silo_name: 0 for silo_name in self.__plan_decoder.silo_states.keys()}

        pyplot.rcParams["figure.autolayout"] = True
        pyplot.ion()

        if plot_in_separate_windows:
            pyfig_scene = pyplot.figure(layout="constrained", figsize=[10, 10])
            pyfig_plots_all = pyplot.figure(layout="constrained", figsize=[7, 5])
            (pyfig_plots, pyfig_time) = pyfig_plots_all.subfigures(1, 2, width_ratios=[5, 2])
            try:
                pyfig_scene_pos = pyfig_scene.canvas.manager.window.pos()
                pyfig_scene_size_x = pyfig_scene.canvas.manager.window.size().width()
                pyfig_plots_all.canvas.manager.window.move(pyfig_scene_pos.x() + pyfig_scene_size_x, pyfig_scene_pos.y())
            except:
                pass
        else:
            pyfig = pyplot.figure(layout="constrained", figsize=[15, 10])
            (pyfig_scene, pyfig_plots, pyfig_time) = pyfig.subfigures(1, 3, width_ratios=[10, 6, 2])
            pyfig_plots_all = (pyfig_plots, pyfig_time)

        axes = self._create_axes(pyfig_scene, pyfig_plots, pyfig_time)
        ax_scene = axes.get(PlanSimulator1.PlotType.SCENE)

        scene_plotter = ScenePlotter(ax_scene, data_manager=self.__data_manager, roads=self.__roads)

        field_boundary_polys = self._get_field_boundary_polys(scene_plotter)
        machine_markers = self._create_machine_markers(ax_scene)
        max_timestamp = self._get_max_timestamp()
        bars = self._init_axes(axes, max_timestamp)

        pyplot.show()
        pyplot.pause(0.1)

        bgs = dict()
        locks = dict()
        resize_times = dict()

        def on_resize(fig, event):
            with locks.get(fig):
                resize_times[fig] = time.time()

        if plot_in_separate_windows:
            bgs[pyfig_scene] = pyfig_scene.canvas.copy_from_bbox(pyfig_scene.bbox)
            bgs[pyfig_plots_all] = pyfig_plots_all.canvas.copy_from_bbox(pyfig_plots_all.bbox)

            locks[pyfig_scene] = Lock()
            locks[pyfig_plots_all] = Lock()

            resize_times[pyfig_scene] = None
            resize_times[pyfig_plots_all] = None

            pyfig_scene.canvas.mpl_connect('resize_event', partial(on_resize, pyfig_scene))
            pyfig_plots_all.canvas.mpl_connect('resize_event', partial(on_resize, pyfig_plots_all))
        else:
            bgs[pyfig] = pyfig.canvas.copy_from_bbox(pyfig.bbox)
            locks[pyfig] = Lock()
            resize_times[pyfig] = None
            pyfig.canvas.mpl_connect('resize_event', partial(on_resize, pyfig))

        def redraw(fig):
            with locks.get(fig):
                if resize_times.get(fig) is None or time.time() - resize_times.get(fig) < 0.1:
                    return
                fig.canvas.draw()
                pyplot.pause(0.1)
                bgs[fig] = fig.canvas.copy_from_bbox(fig.bbox)
                resize_times[fig] = None

        self.__last_timestamp = max(0, ts_start)

        ts_samples = list()

        start_time = time.time()

        while not self.__stop:
            elapsed_time = time.time()- start_time
            self.__last_timestamp += elapsed_time * self.__speed_factor
            ts = self.__last_timestamp

            start_time = time.time()

            ts_samples.append(ts)

            try:

                if plot_in_separate_windows:

                    with locks.get(pyfig_plots_all):
                        blitters_plots_all = self._update_bars(ts, axes, bars, max_timestamp, field_inds_2, machine_inds_2, silo_inds_2)

                    with locks.get(pyfig_scene):
                        blitters_scene = self._update_scene(ts, axes, field_boundary_polys, machine_markers, field_inds, machine_inds)

                    if not pyplot.fignum_exists(pyfig_scene.number) and not pyplot.fignum_exists(pyfig_plots_all.number):
                        # pyplot.close(pyfig_scene)
                        # pyplot.close(pyfig_plots_all)
                        break
                    if pyplot.fignum_exists(pyfig_scene.number):
                        pyfig_scene.canvas.flush_events()
                        redraw(pyfig_scene)
                        with locks.get(pyfig_scene):
                            pyfig_scene.canvas.restore_region(bgs.get(pyfig_scene))
                            for (blitter, _ax) in blitters_scene:
                                _ax.draw_artist(blitter)
                            if pyplot.fignum_exists(pyfig_scene.number):
                                pyfig_scene.canvas.blit(pyfig_scene.bbox)
                        pyfig_scene.canvas.flush_events()
                    if pyplot.fignum_exists(pyfig_plots_all.number):
                        pyfig_plots_all.canvas.flush_events()
                        redraw(pyfig_plots_all)
                        with locks.get(pyfig_plots_all):
                            pyfig_plots_all.canvas.restore_region(bgs.get(pyfig_plots_all))
                            for (blitter, _ax) in blitters_plots_all:
                                _ax.draw_artist(blitter)
                            if pyplot.fignum_exists(pyfig_plots_all.number):
                                pyfig_plots_all.canvas.blit(pyfig_plots_all.bbox)
                        pyfig_plots_all.canvas.flush_events()
                else:

                    with locks.get(pyfig):
                        blitters_plots_all = self._update_bars(ts, axes, bars, max_timestamp, field_inds_2, machine_inds_2, silo_inds_2)
                        blitters_scene = self._update_scene(ts, axes, field_boundary_polys, machine_markers, field_inds, machine_inds)

                    if not pyplot.fignum_exists(pyfig.number):
                        break
                    pyfig.canvas.flush_events()
                    redraw(pyfig)
                    with locks.get(pyfig):
                        pyfig.canvas.restore_region(bgs.get(pyfig))
                        for (blitter, _ax) in blitters_scene:
                            ax_scene.draw_artist(blitter)
                        for (blitter, _ax) in blitters_plots_all:
                            ax_scene.draw_artist(blitter)
                        if pyplot.fignum_exists(pyfig.number):
                            pyfig.canvas.blit(pyfig.bbox)
                    pyfig.canvas.flush_events()

            except TclError as e:
                print(f'WARN: {e}')

            elapsed_time = time.time()- start_time
            if elapsed_time < self.__period:
                time.sleep(self.__period - elapsed_time)
            else:
                pass
                print(f'WARN: update_time = {elapsed_time}   ;   period = {self.__period}')

        pyplot.ioff()

    def _create_axes(self, pyfig_scene: pyplot.Figure, pyfig_plots: pyplot.Figure, pyfig_time: pyplot.Figure) \
            -> Dict['PlanSimulator1.PlotType', pyplot.Axes]:

        """ Create the plots' axes

        Parameters
        ----------
        pyfig_scene : float
            Figure of the scene
        pyfig_scene : float
            Figure containing the plots of machine, field and silo states
        pyfig_scene : float
            Figure containing the time bar

        Returns
        ----------
        axes_dict : Dict['PlanSimulator1.PlotType', pyplot.Axes]
            Axes: {axes_type: axes}
        """

        axes = dict()

        ax_scene = pyfig_scene.subplots()
        axes[PlanSimulator1.PlotType.SCENE] = ax_scene

        num_tvs = len(self.__plan_decoder.tv_names_map.keys())
        num_fields = len(self.__plan_decoder.field_names_map.keys())
        num_silos = len(self.__plan_decoder.silo_names_map.keys())
        (ax_tvs_bunker_mass, ax_fields_harvested_percentage, ax_silo_mass) = \
            pyfig_plots.subplots(3, 1, height_ratios=[num_tvs, num_fields, num_silos])
        axes[PlanSimulator1.PlotType.TVS_BUNKER_MASS_PERCENTAGE] = ax_tvs_bunker_mass
        axes[PlanSimulator1.PlotType.FIELDS_HARV_AREA_PERCENTAGE] = ax_fields_harvested_percentage
        axes[PlanSimulator1.PlotType.SILOS_UNLOADED_MASS] = ax_silo_mass

        ax_time = pyfig_time.subplots()
        axes[PlanSimulator1.PlotType.PROCESS_TIME] = ax_time

        return axes

    @staticmethod
    def _get_field_boundary_polys(scene_plotter: ScenePlotter) -> Dict[str, pyplot.Polygon]:

        """ Obtain and adjust the field boundary (pyplot) polygons from the scene plotter and
        remove all field geometries from the scene plotter that we don't want to display

        Parameters
        ----------
        scene_plotter : ScenePlotter
            Scene plotter

        Returns
        ----------
        field_polygons : Dict[str, pyplot.Polygon]
            Fields' boundary (pyplot) polygons: {field_location_name: boundary (pyplot) polygon}
        """

        field_boundary_polys = dict()
        for field_id, f_figs in scene_plotter.field_figures.items():
            f_figs.boundary.set(animated=True)
            field_boundary_polys[ get_field_location_name(field_id) ] = f_figs.boundary
            for sf_figs in f_figs.subfields:  # remove other polygons to avoid overlap
                if sf_figs.boundary_outer is not None:
                    sf_figs.boundary_outer.remove()
                if sf_figs.boundary_inner is not None:
                    sf_figs.boundary_inner.remove()
        return field_boundary_polys

    def _create_machine_markers(self, ax: pyplot.Axes) -> Dict[str, pyplot.Line2D]:

        """ Create the machines' markers

        Parameters
        ----------
        ax : pyplot.Axes
            Axes

        Returns
        ----------
        machine_markers_dict : Dict[str, pyplot.Line2D]
            Machines' markers: {machine_name: marker}
        """

        machine_markers: Dict[str, pyplot.Line2D] = dict()
        marker_size = 10
        ref_field_name = next(iter(self.__machine_spots_at_location.items()))[0]
        for machine_name, m in self.__plan_decoder.harvester_names_map.items():
            pos = self.__machine_spots_at_location.get(ref_field_name).get(machine_name)
            machine_markers[machine_name] = \
            ax.plot(pos.x, pos.y,  # initialize in a random field (only for visualization)
                    marker='s',
                    c=tuple(np.random.choice(range(256), size=3) / 256.0),
                    markersize=marker_size,
                    label=machine_name,
                    animated=True)[0]
        for machine_name, m in self.__plan_decoder.tv_names_map.items():
            pos = self.__machine_spots_at_location.get(ref_field_name).get(machine_name)
            machine_markers[machine_name] = \
            ax.plot(pos.x, pos.y,  # initialize in a random field (only for visualization)
                    marker='o',
                    c=tuple(np.random.choice(range(256), size=3) / 256.0),
                    markersize=marker_size,
                    label=machine_name,
                    animated=True)[0]
        return machine_markers

    def _get_max_timestamp(self) -> float:

        """ Compute the maximum timestamp of the given plan (i.e., plan duration)

        Returns
        ----------
        timestamp : float
            Maximum timestamp of the given plan (i.e., plan duration)
        """

        max_timestamp = 0
        for states in [self.__plan_decoder.field_states, self.__plan_decoder.machine_states,
                       self.__plan_decoder.silo_states]:
            for name, states_2 in states.items():
                last_state = states_2[-1]
                ts = last_state.ts_start if last_state.ts_end is None else last_state.ts_end
                max_timestamp = max(max_timestamp, ts)
        return max_timestamp


    def _init_axes(self, axes: Dict['PlanSimulator1.PlotType', pyplot.Axes], max_timestamp: float) \
            -> Dict[
                    'PlanSimulator1.PlotType',
                    Union[
                        Tuple[matplotlib.container.BarContainer, pyplot.Text],
                        Dict[str, matplotlib.container.BarContainer]
                    ]
               ]:

        """ Initialize the axes of all plots and get the bars of all plots

        Parameters
        ----------
        axes : Dict['PlanSimulator1.PlotType', pyplot.Axes]
            Axes dictionary: {plot_type: axes}
        max_timestamp : float
            Maximum timestamp of the given plan (i.e., plan duration)

        Returns
        ----------
        bars : Dict[PlanSimulator1.PlotType, Any]
            Bars of all figures: { plot_type: (bar, plot_text) | {object_name, bar} }
        """

        ax_scene = axes.get(PlanSimulator1.PlotType.SCENE)
        ax_time = axes.get(PlanSimulator1.PlotType.PROCESS_TIME)
        ax_fields_harvested_percentage = axes.get(PlanSimulator1.PlotType.FIELDS_HARV_AREA_PERCENTAGE)
        ax_tvs_bunker_mass = axes.get(PlanSimulator1.PlotType.TVS_BUNKER_MASS_PERCENTAGE)
        ax_silo_mass = axes.get(PlanSimulator1.PlotType.SILOS_UNLOADED_MASS)

        bars = dict()

        ax_scene.set_aspect('equal', adjustable='box')
        ax_scene.legend()

        ax_time.set_ylim([0, math.ceil(max_timestamp)])
        bar_time = ax_time.bar('Time[s]', 0)
        bar_time_text = [ ax_time.text(x=bar_time[0].get_x() + bar_time[0].get_width() / 2, y=0.5*max_timestamp, s='0', ha='center', animated=True) ]
        # ax_time.bar_label(bar_time, label_type='center')
        bars[PlanSimulator1.PlotType.PROCESS_TIME] = (bar_time, bar_time_text)

        ax_fields_harvested_percentage.set_xlabel('Field harvested area (%)')
        ax_fields_harvested_percentage.set_xlim([0, 105])
        ax_fields_harvested_percentage.grid(visible=True, which='major', axis='x', linestyle='--')
        bars_fields_harvested_percentage = dict()
        for name in self.__plan_decoder.field_names_map.keys():
            bars_fields_harvested_percentage[name] = ax_fields_harvested_percentage.barh(name, width=-1, color='blue', animated=True)[0]
        bars[PlanSimulator1.PlotType.FIELDS_HARV_AREA_PERCENTAGE] = bars_fields_harvested_percentage

        ax_tvs_bunker_mass.set_xlabel('TV bunker filling level (%)')
        ax_tvs_bunker_mass.set_xlim([0, 105])
        ax_tvs_bunker_mass.grid(visible=True, which='major', axis='x', linestyle='--')
        bars_tvs_bunker_mass = dict()
        for name in self.__plan_decoder.tv_names_map.keys():
            bars_tvs_bunker_mass[name] = ax_tvs_bunker_mass.barh(name, width=-1, color='blue', animated=True)[0]
        bars[PlanSimulator1.PlotType.TVS_BUNKER_MASS_PERCENTAGE] = bars_tvs_bunker_mass

        ax_silo_mass.set_xlabel('Yield-mass unloaded at silo (t)')
        ax_silo_mass.grid(visible=True, which='major', axis='x', linestyle='--')
        bars_silo_mass = dict()
        max_silo_mass = 0
        for name in self.__plan_decoder.silo_names_map.keys():
            bars_silo_mass[name] = ax_silo_mass.barh(name, width=0, color='blue', animated=True)[0]
            last_state = self.__plan_decoder.silo_states.get(name)[-1]
            max_silo_mass = max( max_silo_mass, last_state.yield_mass_start
                                                    if last_state.yield_mass_end is None
                                                    else last_state.yield_mass_end)
        ax_silo_mass.set_xlim([0, math.ceil(max_silo_mass/1000)])
        bars[PlanSimulator1.PlotType.SILOS_UNLOADED_MASS] = bars_silo_mass

        return bars


    @staticmethod
    def __adjust_field_boundary_poly(poly: pyplot.Polygon, state: SimFieldState):

        """ Adjust the field boundary (pyplot) polygon based on the field state

        Parameters
        ----------
        poly : pyplot.Polygon
            Field boundary (pyplot) polygon
        state : SimFieldState
            Field state
        """

        if state.state is PlanSimulator1.__FieldHarvestingState_Type.UNRESERVED:
            poly.set_color('red')
            poly.set_edgecolor('black')
            poly.set_linewidth(1)
        elif state.state is PlanSimulator1.__FieldHarvestingState_Type.RESERVED:
            poly.set_color('#FF000000')
            poly.set_edgecolor('orange')
            poly.set_linewidth(2)
        elif state.state is PlanSimulator1.__FieldHarvestingState_Type.BEING_HARVESTED:
            poly.set_color('lightgreen')
            poly.set_edgecolor('green')
            poly.set_linewidth(2)
        elif state.state is PlanSimulator1.__FieldHarvestingState_Type.BEING_HARVESTED_WAITING:
            poly.set_color('lightyellow')
            poly.set_edgecolor('yellow')
            poly.set_linewidth(2)
        elif state.state is PlanSimulator1.__FieldHarvestingState_Type.HARVESTED:
            poly.set_color('green')
            poly.set_edgecolor('black')
            poly.set_linewidth(1)

    def __get_machine_position(self, state: SimMachineState, timestamp: float, machine_name: str) -> Point:

        """ Get the machine (interpolated) position for a given timestamp

        Parameters
        ----------
        state : SimMachineState
            Machine state corresponding to the given timestamp
        timestamp : float
            Timestamp [s]
        machine_name : str
            Machine name

        Returns
        ----------
        position : Point
            Machine (interpolated) position for the given timestamp
        """

        pos = None
        machine = self.__plan_decoder.harvester_names_map.get(machine_name)
        if machine is None:
            machine = self.__plan_decoder.tv_names_map.get(machine_name)
        if state.loc_name is not None:
            pos = self.__machine_spots_at_location.get(state.loc_name).get(machine_name)
            if state.pt_end is not None and pos != state.pt_end:
                pos = getPointAtRelativeDist([pos, state.pt_end], (timestamp-state.ts_start)/(state.ts_end-state.ts_start))[0]
        elif state.pt_start is not None:
            if state.pt_end is None or state.pt_start == state.pt_end:
                pos = state.pt_start
            else:
                path = self.__out_field_route_planner.get_path(state.pt_start, state.pt_end, machine)
                pos = getPointAtRelativeDist(path, (timestamp-state.ts_start)/(state.ts_end-state.ts_start))[0]
        return pos

    def __adjust_machine_marker(self, marker: pyplot.Line2D,
                                state: Union[SimMachineState, Point],
                                timestamp: float,
                                machine_name: str):

        """ Adjust a machine marker based on the machine state at a given timestamp

        Parameters
        ----------
        marker : pyplot.Line2D
            Machine marker
        state : SimMachineState, Point
            Machine state corresponding to the given timestamp OR position
        timestamp : float
            Timestamp [s]
        machine_name : str
            Machine name
        """

        if isinstance(state, Point):
            pos = state
        else:
            pos = self.__get_machine_position(state, timestamp, machine_name)
        if pos is None:
            marker.set_alpha(0)
        else:
            marker.set_alpha(1)
            marker.set_xdata([pos.x])
            marker.set_ydata([pos.y])

    def _update_bars(self,
                     ts: float,
                     axes: Dict['PlanSimulator1.PlotType', pyplot.Axes],
                     bars: Dict['PlanSimulator1.PlotType', Union[Tuple, Dict]],
                     max_timestamp: float,
                     field_inds_2: Dict[str, int],
                     machine_inds_2: Dict[str, int],
                     silo_inds_2: Dict[str, int]):

        """ Update the bars based on the objects (fields, machines, silos) states at a given timestamp

        Parameters
        ----------
        ts : float
            Timestamp [s]
        axes : pyplot.Axes
            Simulator axes
        bars : Dict['PlanSimulator1.PlotType', Union[Tuple, Dict]]
            Simulator bars
        max_timestamp : float
            Maximum timestamp of the given plan (i.e., plan duration)
        field_inds_2 : Dict[str: int]
            [in, out] Dictionary holding the state indexes of the current fields' states (for quicker search)
        machine_inds_2 : Dict[str: int]
            [in, out] Dictionary holding the state indexes of the current machines' states (for quicker search)
        silo_inds_2 : Dict[str: int]
            [in, out] Dictionary holding the state indexes of the current silos' states (for quicker search)

        Returns
        ----------
        blitters : List[Tuple[Any, pyplot.Axes]]
            Objects' states bars blitters (plot objects that change dynamically, e.g., bar-rectangles and and bar-texts) with the respective axis
        """

        blitters_plots_all = list()

        ax_time = axes.get(PlanSimulator1.PlotType.PROCESS_TIME)
        ax_fields_harvested_percentage = axes.get(PlanSimulator1.PlotType.FIELDS_HARV_AREA_PERCENTAGE)
        ax_tvs_bunker_mass = axes.get(PlanSimulator1.PlotType.TVS_BUNKER_MASS_PERCENTAGE)
        ax_silo_mass = axes.get(PlanSimulator1.PlotType.SILOS_UNLOADED_MASS)

        (bar_time, bar_time_text) = bars.get(PlanSimulator1.PlotType.PROCESS_TIME)
        bars_fields_harvested_percentage = bars.get(PlanSimulator1.PlotType.FIELDS_HARV_AREA_PERCENTAGE)
        bars_tvs_bunker_mass = bars.get(PlanSimulator1.PlotType.TVS_BUNKER_MASS_PERCENTAGE)
        bars_silo_mass = bars.get(PlanSimulator1.PlotType.SILOS_UNLOADED_MASS)

        bar_time[0].set_height(ts)
        bar_time_text[0].remove()
        bar_time_text[0] = ax_time.text(x=bar_time[0].get_x() + bar_time[0].get_width() / 2, y=0.5 * max_timestamp,
                                        s=f'{math.ceil(ts)}\n / {math.ceil(max_timestamp)}\n\n[x{self.__speed_factor}]',
                                        ha='center', weight='bold',
                                        animated=True)
        blitters_plots_all.append((bar_time[0], ax_time))
        blitters_plots_all.append((bar_time_text[0], ax_time))

        cmap = matplotlib.cm.get_cmap('winter')
        for name in self.__plan_decoder.field_names_map.keys():
            state2, ind = self.__plan_decoder.get_field_state_at(name, ts, field_inds_2.get(name))
            field_inds_2[name] = ind

            bars_fields_harvested_percentage.get(name).set_width(state2.harvested_percentage)
            bars_fields_harvested_percentage.get(name).set_color(cmap(state2.harvested_percentage / 100))
            blitters_plots_all.append((bars_fields_harvested_percentage.get(name), ax_fields_harvested_percentage))

        cmap = matplotlib.cm.get_cmap('turbo')
        for name in self.__plan_decoder.tv_names_map.keys():
            state2, ind = self.__plan_decoder.get_machine_state_at(name, ts, machine_inds_2.get(name))
            if state2 is None:
                continue

            machine_inds_2[name] = ind

            mass_percentage = 100 * state2.bunker_mass / self.__plan_decoder.tv_names_map.get(name).bunker_mass
            bars_tvs_bunker_mass.get(name).set_width(mass_percentage)
            bars_tvs_bunker_mass.get(name).set_color(cmap(mass_percentage / 100))
            blitters_plots_all.append((bars_tvs_bunker_mass.get(name), ax_tvs_bunker_mass))

        for name, states in self.__plan_decoder.silo_states.items():
            state2, ind = self.__plan_decoder.get_silo_state_at(name, ts, silo_inds_2.get(name))
            if state2 is None:
                continue
            silo_inds_2[name] = ind
            bars_silo_mass.get(name).set_width(state2.yield_mass / 1000)
            blitters_plots_all.append((bars_silo_mass.get(name), ax_silo_mass))

        return blitters_plots_all

    def _update_scene(self, ts, axes, field_boundary_polys, machine_markers, field_inds, machine_inds):

        """ Update the scene plot based on the objects (fields, machines, silos) states at a given timestamp

        Parameters
        ----------
        ts : float
            Timestamp [s]
        axes : pyplot.Axes
            Simulator axes
        field_boundary_polys : Dict[str, pyplot.Polygon]
            Fields' boundary (pyplot) polygons
        machine_markers : Dict[str, pyplot.Line2D]
            Machines' markers
        field_inds : Dict[str: int]
            [in, out] Dictionary holding the state indexes of the current fields' states (for quicker search)
        machine_inds : Dict[str: int]
            [in, out] Dictionary holding the state indexes of the current machines' states (for quicker search)

        Returns
        ----------
        blitters : List[Tuple[Any, pyplot.Axes]]
            Scene blitters (plot objects that change dynamically, e.g., field polygons, machine markers) with the respective axis
        """

        blitters_scene = list()
        ax_scene = axes.get(PlanSimulator1.PlotType.SCENE)
        for name, states in self.__plan_decoder.field_states.items():
            state, ind = self.__get_state_at(states, ts, field_inds.get(name))
            if state is None:
                continue
            self.__adjust_field_boundary_poly(field_boundary_polys.get(name), state)
            field_inds[name] = ind
            blitters_scene.append((field_boundary_polys.get(name), ax_scene))

        if self.__plan_decoder.gives_precise_machine_positions():
            for name, marker in machine_markers.items():
                state, ind = self.__plan_decoder.get_machine_state_at(name, ts, machine_inds.get(name))
                if state is None:
                    continue
                self.__adjust_machine_marker(marker, state.position, ts, name)
                machine_inds[name] = ind
                blitters_scene.append((machine_markers.get(name), ax_scene))
        else:
            for name, states in self.__machine_states.items():
                state, ind = self.__get_state_at(states, ts, machine_inds.get(name))
                if state is None:
                    continue
                self.__adjust_machine_marker(machine_markers.get(name), state, ts, name)
                machine_inds[name] = ind
                blitters_scene.append((machine_markers.get(name), ax_scene))
        return blitters_scene



