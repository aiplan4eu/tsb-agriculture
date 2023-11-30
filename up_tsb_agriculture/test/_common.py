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

import warnings
from unified_planning.plans.plan import PlanKind


def print_plan_info(plan):
    if plan is None:
        print("ERROR: invalid plan (None)")

    print("Plan: ")
    if plan.kind is PlanKind.TIME_TRIGGERED_PLAN:
        plan_duration = -1
        print(f'# actions = {len(plan.timed_actions)}')
        for start, action, duration in plan.timed_actions:
            if duration is None:
                print("\t%s -> %s: %s [--]" % (float(start), float(start), action))
            else:
                print("\t%s -> %s: %s [%s]" % (float(start), float(start)+float(duration), action, float(duration)))
                plan_duration = max(plan_duration, float(start) + float(duration))
        print(f'plan duration = {plan_duration}')
    elif plan.kind is PlanKind.SEQUENTIAL_PLAN:
        print(f'# actions = {len(plan.actions)}')
        for action in plan.actions:
            print(f'\t{action}')
    else:
        warnings.warn(f'[ERROR]: invalid plan kind: {plan.kind}')
