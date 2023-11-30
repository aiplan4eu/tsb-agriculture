#!/usr/bin/env python3

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

import sys
import os
import pathlib
import subprocess
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, ArgumentTypeError

def __get_argument_parser():

    parser = ArgumentParser(prog='run_example',
                            description='Run a given example',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--example', '-ex', default='real_campaign',
                        choices=['real_campaign', 'fake_campaign'],
                        help='Type of example to be run')

    parser.add_argument('--config_file', '-cf', default=None,
                        help=f'Path to the example configuration file')

    return parser


if __name__ == '__main__':

    parser = __get_argument_parser()
    args = parser.parse_args()

    try:
        if args.example == 'real_campaign':
            _pyfile = f'{pathlib.Path(__file__).parent.resolve()}/examples/plan_campaign.py'
        else:
            _pyfile = f'{pathlib.Path(__file__).parent.resolve()}/examples/plan_fake_campaign.py'
        if args.config_file is None:
            sys.exit( subprocess.check_call(f'python3 {_pyfile}', shell=True) )
        sys.exit( subprocess.check_call(f'python3 {_pyfile} -cf {args.config_file}', shell=True) )

    except OSError as e:
        print("Execution failed:", e, file=sys.stderr)

