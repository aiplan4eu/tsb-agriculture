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

from typing import Callable
import matplotlib.pyplot as pyplot
from unified_planning.plans.time_triggered_plan import TimeTriggeredPlan
from matplotlib.ticker import AutoMinorLocator
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as mplPoly
import numpy as np
import random


class TemporalPlanPlotter:

    """ Class used to plot a temporal plan in the agriculture use-case scene """

    class ActionData:

        """ Class holding an action's information """

        def __init__(self):
            action: str = ''
            """ Action name """

            machine: str = ''
            """ Machine name """

            ts_start: float = 0.0
            """ Start-timestamp of the action """

            ts_end: float = 0.0
            """ End-timestamp of the action """

    def __init__(self):
        pass

    def plot_plan(self,
                  plan: TimeTriggeredPlan,
                  split_single_actions: bool = True,
                  exclude_cb: Callable[[str, str], bool] = None):

        """ Plot a plan.

        Parameters
        ----------
        plan : TimeTriggeredPlan
            Temporal UP plan
        split_single_actions : bool
            If false, all actions of the same type will be plotted at the same level; otherwise, the action plotting will change level after every action
        exclude_cb : Callable[[str, str], bool]
            Call-back used to decide if a specific action should be plotted (return = False) or excluded (return = True)
        """

        fig, ax = pyplot.subplots()

        ax.xaxis.set_minor_locator(AutoMinorLocator())

        machine_data = list()
        machine_set = set()
        __actions = set()

        ts_max = 0

        for start, action, duration in plan.timed_actions:
            __actions.add(action.action.name)
            machine_indexes = list()
            for i, param in enumerate(action.action.parameters):
                if param.name == 'tv' or param.name == 'harv':
                    machine_indexes.append( (i, param.name) )
            ts_start = float(start)
            if duration is None:
                ts_end = ts_start
            else:
                ts_end = ts_start + float(duration)

            ts_max = max(ts_max, ts_end)

            for i, name in machine_indexes:
                m = f'{action.actual_parameters[i]}'

                excluded = ( exclude_cb is not None and exclude_cb(action.action.name, m) )
                # if excluded:
                #     continue

                data = dict()
                data["action"] = action.action.name
                data["machine"] = m
                data["ts_start"] = ts_start
                data["ts_end"] = ts_end
                data["excluded"] = excluded
                machine_set.add(m)
                machine_data.append(data)

        sorted_machines = [m for m in machine_set]
        sorted_machines.sort()

        sorted_actions = [a for a in __actions]
        sorted_actions.sort()

        color_ind = 0
        action_colors = dict()
        for action in sorted_actions:
            action_colors[action] = self.get_color(color_ind)
            color_ind += 1

        if split_single_actions:
            delta_y_machine_change = 0.5
            machines_y_base = dict()
            machines_y_delta = dict()
            for m in sorted_machines:
                machines_y_base[m] = len(machines_y_base) + (len(machines_y_base) + 1) * delta_y_machine_change
                machines_y_delta[m] = 0

            added_labels = set()
            for data in machine_data:
                dy = 0.1
                delta_y = machines_y_delta.get( data.get("machine") )
                if delta_y <= 1 - 1e-9:
                    machines_y_delta[ data["machine"] ] = delta_y + dy
                else:
                    machines_y_delta[ data["machine"] ] = 0
                y = machines_y_base[ data["machine"] ] + delta_y

                alpha = 1
                if data["excluded"]:
                    alpha = 0.1

                c = action_colors[ data["action"] ]

                if data["action"] in added_labels or data["excluded"]:
                    ax.plot([ data["ts_start"], data["ts_end"] ], [y, y], c=c, alpha=alpha)
                else:
                    ax.plot([ data["ts_start"], data["ts_end"] ], [y, y], c=c, alpha=alpha, label=data["action"])
                    added_labels.add(data["action"])

                poly_pts = list()
                poly_pts.append([data["ts_start"], y])
                poly_pts.append([data["ts_start"], y+dy])
                poly_pts.append([data["ts_end"], y+dy])
                poly_pts.append([data["ts_end"], y])
                poly_pts.append([data["ts_start"], y])

                polygon = mplPoly( poly_pts, closed=True, color='black', fill=c, alpha=alpha )
                collection = PatchCollection([polygon], color=c, alpha=alpha)
                ax.add_collection(collection)

            for y in machines_y_base.values():
                pyplot.plot([0, ts_max], [y - 0.5 * delta_y_machine_change, y - 0.5 * delta_y_machine_change ], linewidth=2, color='black')

            ax.set_yticks( [*np.arange(delta_y_machine_change, len(machines_y_base)+delta_y_machine_change*(len(machines_y_base)), 1+delta_y_machine_change)] )
            ax.set_yticklabels( sorted_machines )

        else:
            all_machine_actions = dict()
            for data in machine_data:
                m = data["machine"]
                a = data["action"]
                machine_actions = all_machine_actions.get(m)
                if machine_actions is None:
                    machine_actions = dict()
                    all_machine_actions[m] = machine_actions
                machine_actions_2 = machine_actions.get(a)
                if machine_actions_2 is None:
                    machine_actions_2 = list()
                    machine_actions[a] = machine_actions_2
                machine_actions_2.append(data)

            added_labels = set()
            y = 1
            y_ticks = list()
            y_ticks_labels = list()

            pyplot.plot([0, ts_max], [0, 0], linewidth=2, color='black')
            # for machine_name, machine_actions in all_machine_actions.items():
            for machine_name in sorted_machines:
                machine_actions = all_machine_actions.get(machine_name)
                if sorted_machines is None:
                    continue
                y_ticks.append(y)
                y_ticks_labels.append(machine_name)
                for machine_actions_2 in machine_actions.values():
                    for data in machine_actions_2:
                        alpha = 1
                        if data["excluded"]:
                            alpha = 0.1
                        c = action_colors[ data["action"] ]
                        if data["action"] in added_labels or data["excluded"]:
                            ax.plot([ data["ts_start"], data["ts_end"] ], [y, y], c=c, alpha=alpha)
                        else:
                            ax.plot([ data["ts_start"], data["ts_end"] ], [y, y], c=c, alpha=alpha, label=data["action"])
                            added_labels.add(data["action"])

                        poly_pts = list()
                        poly_pts.append([data["ts_start"], y])
                        poly_pts.append([data["ts_start"], y+1])
                        poly_pts.append([data["ts_end"], y+1])
                        poly_pts.append([data["ts_end"], y])
                        poly_pts.append([data["ts_start"], y])

                        polygon = mplPoly( poly_pts, closed=True, color='black', fill=c, alpha=alpha )
                        collection = PatchCollection([polygon], color=c, alpha=alpha)
                        ax.add_collection(collection)

                    y += 1

                pyplot.plot([0, ts_max], [y+1, y+1], linewidth=2, color='black')
                y += 2

            ax.set_yticks( y_ticks )
            ax.set_yticklabels( y_ticks_labels )

        ax.tick_params(which='both', width=2)
        ax.tick_params(which='major', length=7)
        ax.tick_params(which='minor', length=4)

        eps_time = 1000
        x_ticks = int(ts_max / eps_time) + 2
        ax.set_xticks( [*range(0, x_ticks*eps_time, eps_time)] )

        ax.legend()
        ax.grid(axis='x',  which='both', linestyle='--')
        pyplot.show()

    def plot_plan_busy_actions(self, plan: TimeTriggeredPlan, split_single_actions: bool = True):

        """ Plot a plan excluding the actions for a machine where the machine is not really performing an operation.

        For example, a harvester is part of 'reserve overload' actions, but it is neither harvesting/overloading nor
        driving during those actions.

        Parameters
        ----------
        plan : TimeTriggeredPlan
            Temporal UP plan
        split_single_actions : bool
            If false, all actions of the same type will be plotted at the same level; otherwise, the action plotting will change level after every action
        """

        def exclude_cb(action: str, machine: str):
            if machine.find('harv') >= 0 and action.find('drive_tv') >= 0:
                return True
            return False

        self.plot_plan(plan, split_single_actions, exclude_cb)

    @staticmethod
    def get_color(ind: int):

        """ Get a color.

        Parameters
        ----------
        ind : int
            Index
        """

        if ind == 0: return 'blue'
        if ind == 1: return 'green'
        if ind == 2: return 'red'
        if ind == 3: return 'cyan'
        if ind == 4: return 'magenta'
        if ind == 5: return 'orange'
        return "#"+''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
