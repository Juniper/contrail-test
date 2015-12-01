
# Contrail Test Scripts

This software is licensed under the Apache License, Version 2.0 (the "License");
you may not use this software except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Overview

The Contrail Test repository contains the test code for validating the Contrail infrastructure
The code is organized into ``fixtures`` , ``scripts`` and ``serial_scripts``

Testcases under ``scripts`` folder are independent of each other and can be run in parallel
Testcases under ``serial_scripts`` can have cluster-wide impact and MUST be run only one at a time

``run_tests.sh`` lets you run these tests as well. Take a look at [ this ] (https://github.com/Juniper/contrail-test/wiki/Running-Tests)

### fixtures

Contains high level fixtures for creating projects, virtual networks, virtual machines, floating ips, policies, security-groups, service instances, VPCs, VDNS etc. and validate these objects against Contrail components like Contrail API Server, Control nodes, Virtual Routers. 
The fixtures provide ``verify_on_setup()`` and ``verify_on_cleanup()`` methods to achieve this. They also provide some commonly used methods to work with these objects. 
Examples include:
- To run commands on a VM and verify connectivity to it
- Traffic send/receive methods using tools like scapy/netperf 
- Policy rules validation with traffic 
- Perform tcp/icmp/ssh/scp/tftp validations on the VM
- Flow verification for traffic
- Analytics data validation

### scripts, serial_scripts

Test scripts at a per-feature level. Sub-folders are created for the features. 
The test scripts can be run on any of the config nodes in the Contrail cluster.  

## Initialization
Install git on the node
```
    $> apt-get install git 
or ::
    $> yum install git
```
Checkout the corresponding branch that the cluster is running ("master","R1.05", "R1.04" etc.)
```
    $> git clone git@github.com:Juniper/contrail-test.git
    $> cd contrail-test
    $> git checkout R1.05
```
Populate the path of this test repo in ``env.test_repo_dir`` in testbed.py (typically /opt/contrail/utils/fabfile/testbeds/testbed.py) 
Refer to ``sanity_params.ini.sample`` for more options. 
Populate the path to the images in ``configs/images.cfg`` 

##Running Tests
Run the 'run_sanity' task in fab 
```
    $> cd /opt/contrail/utils
    $> # Run Sanity test
    $> fab run_sanity
    $> # Run CI Sanity
    $> fab run_sanity:ci_sanity

```
Run ``fab run_sanity:help`` to view help on running individual tests and other regressions

The run_sanity task installs the python modules required for running tests, autogenerates sanity_params.ini and sanity_testbed.json and sources them for the tests. 
``sanity_testbed.json`` contails the Contrail cluster topology information

To setup fab and learn about testbed.py, please refer to [Contrail Documentation ] (https://www.juniper.net/techpubs/en_US/contrail1.0/topics/task/installation/testbed-file-vnc.html)

The log files and any html report of the entire run will be created in contrail-test/logs folder

For more , refer [ here ] (https://github.com/Juniper/contrail-test/wiki/Running-Tests)

### Usage:
```
  fab run_sanity
  fab run_sanity:ci_sanity
```
### Filing Bugs
Use http://bugs.launchpad.net/juniperopenstack
It will be useful to include the test run log file. 
For post-analysis of a cluster, a fab task ``attach_logs_cores`` can collect the logs and cassandra logs 
### Queries
Mail to
dev@lists.opencontrail.org
users@lists.opencontrail.org
### IRC 
opencontrail on freenode.net
