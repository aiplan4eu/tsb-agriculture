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

from setuptools import setup, find_packages  # type: ignore

long_description = \
'''
 ============================================================
    UP Use-case Agriculture
 ============================================================

    This use-case deals with the planning of silage-maize harvesting campaigns. During silage-maize harvest, 
    a non-capacitated harvester harvests the yield from a field. Because these machines have no bunker, one 
    or more transport vehicles are used to receive the harvested yield from the harvester while the harvester 
    is working (i.e., 'on the run' yield overload). The harvested yield is later transported to a silo for storage. 
    In a day campaign, n fields (n>0) must be harvested by m harvesters (n>=m>0) being assisted by k transport 
    vehicles (k>0). 
    
    This package offers the tools to (a.o.):
        - load and manage the campaign data
        - define the problem as a temporal or sequential planning problem
        - solve the problem using the available engines in UP.
        - inspect and plot the plans
'''

setup(
    name="up_tsb_agriculture",
    version="1.0.0",
    description="Unified Planning Framework - Use Case - Agriculture (Silage Maize Harvesting)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DFKI (Santiago Focke)",
    author_email="santiago.focke@dfki.de",
    url="https://www.ai4europe.eu/business-and-industry/case-studies/campaign-planning-silage-maize-harvesting",
    packages=["up_tsb_agriculture"],
    python_requires=">=3.8",
    install_requires=["unified_planning", "matplotlib", "Shapely", "Pillow", "pyproj"],
    license="APACHE",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
