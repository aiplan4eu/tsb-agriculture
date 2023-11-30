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

from typing import Dict, List, Union, Optional
import shapely.geometry as sg
import matplotlib.pyplot as pyplot

from util_arolib.types import Point, Polygon, Linestring
from management.global_data_manager import GlobalDataManager
from route_planning.types import MachineState


class ScenePlotter:

    """ Class used to plot the agriculture use-case scene """

    class SubfieldFigures:

        """ Class holding the subfield pyplot geometries (figures) to be plotted """

        def __init__(self):
            self.boundary_inner: Optional[pyplot.Polygon] = None
            self.boundary_outer: Optional[pyplot.Polygon] = None
            self.reference_lines: List[pyplot.Line2D] = list()
            self.access_points: List[pyplot.Line2D] = list()

    class FieldFigures:

        """ Class holding the field pyplot geometries (figures) to be plotted """

        def __init__(self):
            self.boundary: Optional[pyplot.Polygon] = None
            self.subfields: List[ScenePlotter.SubfieldFigures] = list()
            self.external_roads: List[pyplot.Polygon] = list()

    class SiloFigures:

        """ Class holding the silo pyplot geometries (figures) to be plotted """

        def __init__(self):
            self.boundary: Optional[pyplot.Polygon] = None
            self.access_points: List[pyplot.Line2D] = list()

    def __init__(self, ax: pyplot.Axes, data_manager: GlobalDataManager, roads: List[Linestring]):

        """ Class initialization.

        Parameters
        ----------
        ax : pyplot.Axes
            Axes where the scene will be plotted
        data_manager : GlobalDataManager
            Data manager holding the problem data (fields, machines, etc.)
        roads : List[Linestring]
            Roads (as linestrings) for transit outside the fields
        """

        self.__ax = ax
        self.__field_figures: Dict[int, ScenePlotter.FieldFigures] = dict()
        self.__silo_figures: Dict[int, ScenePlotter.SiloFigures] = dict()
        self.__road_figures: List[pyplot.Line2D] = list()

        self.__plot_fields(ax, data_manager)
        self.__plot_silos(ax, data_manager)
        self.__plot_roads(ax, roads)

    @property
    def field_figures(self) -> Dict[int, FieldFigures]:

        """ Get all the field pyplot geometries (figures) in the scene plot.

        Returns
        ----------
        figures : Dict[int, FieldFigures]
            Field pyplot geometries (figures) in the scene plot: {field_id: figures}
        """

        return self.__field_figures

    @property
    def silo_figures(self) -> Dict[int, SiloFigures]:

        """ Get all the silo pyplot geometries (figures) in the scene plot.

        Returns
        ----------
        figures : Dict[int, FieldFigures]
            Subfield silo geometries (figures) in the scene plot: {silo_id: figures}.
        """

        return self.__silo_figures

    @property
    def roads_figures(self) -> List[pyplot.Line2D]:

        """ Get all the external roads' pyplot geometries (figures) in the scene plot.

        Returns
        ----------
        figures : List[pyplot.Line2D]
            External roads' pyplot geometries (figures) in the scene plot.
        """

        return self.__road_figures

    @staticmethod
    def plot(data_manager: GlobalDataManager, roads: List[Linestring], machine_initial_states: Dict[int, MachineState]):

        """ Plot the scene.

        Parameters
        ----------
        data_manager : GlobalDataManager
            Data manager holding the problem data (fields, machines, etc.)
        roads : List[Linestring]
            Roads (as linestrings) for transit outside the fields
        machine_initial_states : Dict[int, MachineState]
            Machines' initial states: {machine_id: machine_state}
        """

        pyplot.rcParams["figure.figsize"] = [7.0, 7.0]
        pyplot.rcParams["figure.autolayout"] = True
        fig, ax = pyplot.subplots()

        sp = ScenePlotter(ax, data_manager=data_manager, roads=roads)

        for field_id, figs in sp.field_figures.items():
            figs.boundary.set_color('red')

        for ms in machine_initial_states.values():
            ScenePlotter.__plot_machine_position(ax, ms.position)

        pyplot.gca().set_aspect('equal', adjustable='box')
        pyplot.show()

    @staticmethod
    def __plot_poly(ax: pyplot.Axes, poly: Polygon, color="black", ls='-', fill_color='#FF000000') \
            -> Optional[pyplot.Polygon]:

        """ Plot a polygon.

        Parameters
        ----------
        ax : pyplot.Axes
            Axes where the polygon will be plotted
        poly : Polygon
            Polygon to be plotted
        color : Any
            Color of the polygon boundary-line
        ls : str
            Style of the polygon boundary-line
        fill_color : Any
            Fill-color of the polygon

        Returns
        ----------
        pyplot_polygon : pytplotlib.patches.Polygon
            Plotted pyplot polygon
        """

        if len(poly.points) < 3:
            return None
        x = [p.x for p in poly.points]
        y = [p.y for p in poly.points]
        f, = ax.fill(x, y, c=fill_color, ec=color, animated=False)
        return f

    @staticmethod
    def __plot_linestring(ax: pyplot.Axes, points: List[Point], color="black", ls='-', width: float = -1.) \
            -> Union[pyplot.Polygon, pyplot.Line2D, None]:

        """ Plot a linestring as a line (width == 0) or a polygon (width > 0).

        Parameters
        ----------
        ax : pyplot.Axes
            Axes where the polygon will be plotted
        points : List[Point]
            Linestring points
        color : Any
            Color of the polygon boundary-line
        ls : str
            Style of the polygon boundary-line
        width : float
            If >0, the linestring will be buffered the given width and the resulting polygon will be plotted; otherwise, a line will be plotted.

        Returns
        ----------
        pyplot_polygon : Union[pyplot.Polygon, pyplot.Line2D]
            Plotted pyplot line or polygon
        """

        if len(points) == 0:
            return None
        if width > 0:
            ls = sg.LineString([ (p.x, p.y) for p in points ])
            x, y = ls.buffer(width, cap_style=2).exterior.xy
            poly = Polygon()
            for i in range(len(x)):
                poly.points.append(Point(x[i],y[i]))
            return ScenePlotter.__plot_poly(ax, poly, color=(0,0,0,0), fill_color=color)

        x = [p.x for p in points]
        y = [p.y for p in points]
        f, = ax.plot(x, y, c=color, linestyle=ls, animated=False)
        return f

    @staticmethod
    def __plot_access_point(ax: pyplot.Axes, pt: Point, markersize=5) -> pyplot.Line2D:

        """ Plot an access point as a marker.

        Parameters
        ----------
        ax : pyplot.Axes
            Axes where the polygon will be plotted
        pt : Point
            Access point position
        markersize : int
            Marker size

        Returns
        ----------
        pyplot_polygon : pyplot.Line2D
            Access point pyplot marker
        """

        # x = [pt.x, pt.x-0.5, pt.x-0.25, pt.x-0.25, pt.x+0.25, pt.x+0.25, pt.x+0.5, pt.x]
        # y = [pt.y, pt.y+0.25, pt.y+0.25, pt.y+0.5, pt.y+0.5, pt.y+0.25, pt.y+0.25, pt.y]
        # ax.fill(x, y, c="yellow", animated=False)
        f, = ax.plot(pt.x, pt.y, marker='v', c="yellow", markersize=5, animated=False)
        return f

    def __plot_fields(self, ax: pyplot.Axes, data_manager: GlobalDataManager):

        """ Plot all fields in the scene.

        Parameters
        ----------
        ax : pyplot.Axes
            Axes where the polygon will be plotted
        data_manager : GlobalDataManager
            Data manager holding the problem data (fields, machines, etc)
        """

        for f in data_manager.fields.values():
            fig = ScenePlotter.FieldFigures()
            self.__field_figures[f.id] = fig
            fig.boundary = self.__plot_poly(ax, f.outer_boundary)
            for r in f.external_roads:
                fig.external_roads.append( self.__plot_linestring(ax, r.points, "grey", width=1) )
            for sf in f.subfields:
                fig2 = ScenePlotter.SubfieldFigures()
                fig.subfields.append(fig2)
                fig2.boundary_outer = self.__plot_poly(ax, sf.boundary_outer, fill_color=(0, 1, 0, 0.5))
                fig2.boundary_inner = self.__plot_poly(ax, sf.boundary_inner, "grey")
                for ap in sf.access_points:
                    fig2.access_points.append( self.__plot_access_point(ax, ap) )

    def __plot_silos(self, ax: pyplot.Axes, data_manager: GlobalDataManager):

        """ Plot all silos in the scene.

        Parameters
        ----------
        ax : pyplot.Axes
            Axes where the polygon will be plotted
        data_manager : GlobalDataManager
            Data manager holding the problem data (fields, machines, etc.)
        """

        for s in data_manager.silos.values():
            fig = ScenePlotter.SiloFigures()
            self.__silo_figures[s.id] = fig
            fig.boundary = self.__plot_poly(ax, s.geometry, fill_color=(0.5, 0.25, 0, 0.5))
            for ap in s.access_points:
                fig.access_points.append( self.__plot_access_point(ax, ap) )

    def __plot_roads(self, ax: pyplot.Axes, roads: List[Linestring]):

        """ Plot all machines in the scene.

        Parameters
        ----------
        ax : pyplot.Axes
            Axes where the polygon will be plotted
        roads : List[Linestring]
            Roads (as linestrings) for transit outside the fields
        """

        for r in roads:
            self.__road_figures.append( self.__plot_linestring(ax, r.points, "grey", width=2) )

    @staticmethod
    def __plot_machine_position(ax: pyplot.Axes, pt: Point, markersize=5) -> pyplot.Line2D:

        """ Plot all machines in the scene.

        Parameters
        ----------
        ax : pyplot.Axes
            Axes where the polygon will be plotted
        markersize : int
            Marker size
        """

        # x = [pt.x, pt.x-0.5, pt.x-0.25, pt.x-0.25, pt.x+0.25, pt.x+0.25, pt.x+0.5, pt.x]
        # y = [pt.y, pt.y+0.25, pt.y+0.25, pt.y+0.5, pt.y+0.5, pt.y+0.25, pt.y+0.25, pt.y]
        # ax.fill(x, y, c="yellow")
        f, = ax.plot(pt.x, pt.y, marker='o', c="orange", markersize=markersize)
        return f
