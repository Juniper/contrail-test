
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

### contrail-test docker container

This repository contain Dockerfile, and docker_entrypoint.sh to support building docker container for contrail-test.

All installation of packages, building contrail-test will be done on docker build time, so you may have different docker images
one of juno, one for kilo etc.

You can build docker container using below steps

1. Install docker on the build node where docker image will be built (https://docs.docker.com/engine/installation/ubuntulinux/)
2. Get Dockerfile and docker_entrypoint.sh to a directory (build directory).
2. Copy appropriate contrail-packages deb file (e.g contrail-install-packages_3.0-2687~juno_all.deb) to same directory
3. Run the command "docker build -t contrail-test-juno:latest ." from the build directory

NOTE:
* You may use appropriate tag while building image and you may push the image using command "docker push" to the registry.
* docker build expect appropriate contrail-packages deb file in the build directory.

How you start contrail-test container

contrail-test container expect sanity_params.ini and sanity_testbed.json to be there under /contrail-test in the container. So you will need to
attach those files as volumes on "docker run". Once the above files are available, it run appropriate feature tests according to the parameter passed
 to the container with default of sanity.

Docker run will automatically start running contrail test and log the results to container console log which can be shown by using ```docker logs <container id>```.
In case /contrail-test/logs volume is mounted from docker host, all logs will be saved under that directory.

e.g

The contrail-test docker image tag used here in this example is hkumar/contrail-test-juno:latest, you may use appropriate image.

1. Running container without volumes attached for sanity_params.ini and sanity_testbed.json will fail
```
$ docker run -it hkumar/contrail-test-juno
ERROR! sanity_params.ini or sanity_testbed.json not found under /contrail-test,
          you probably forgot to attach them as volumes
```
2. Run container to run sanity test

```
$ docker run -v ~/contrail-test-3/sanity_params.ini:/contrail-test/sanity_params.ini -v ~/contrail-test-3/sanity_testbed.json:/contrail-test/sanity_testbed.json -it hkumar/contrail-test-juno
Python 2.7.6
no match
Applied patch
patching file __init__.py
+ echo 'Validating if test discovery passes in scripts/ and serial_scripts'
Validating if test discovery passes in scripts/ and serial_scripts
+ echo ''

+ GIVEN_TEST_PATH=
+ export PYTHONPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/contrail-test/scripts:/contrail-test/fixtures
+ PYTHONPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/contrail-test/scripts:/contrail-test/fixtures
+ export OS_TEST_PATH=./scripts
+ OS_TEST_PATH=./scripts
+ testr list-tests
running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-6000} \
${PYTHON:-python} -m subunit.run discover -t ./ ${OS_TEST_PATH:-./scripts} --list
scripts.analytics.test_analytics.AnalyticsTestSanity.test_bgprouter_uve_for_xmpp_and_bgp_peer_count
scripts.analytics.test_analytics.AnalyticsTestSanity.test_colector_uve_module_sates
scripts.analytics.test_analytics.AnalyticsTestSanity.test_config_node_uve_states
scripts.analytics.test_analytics.AnalyticsTestSanity.test_contrail_alarms[sanity,vcenter]
scripts.analytics.test_analytics.AnalyticsTestSanity.test_contrail_status[sanity,vcenter]
scripts.analytics.test_analytics.AnalyticsTestSanity.test_message_table
scripts.analytics.test_analytics.AnalyticsTestSanity.test_verify_hrefs
scripts.analytics.test_analytics.AnalyticsTestSanity.test_verify_object_logs[ci_sanity,sanity,vcenter]
scripts.analytics.test_analytics.AnalyticsTestSanity1.test_stats_tables
scripts.analytics.test_analytics.AnalyticsTestSanity1.test_verify__bgp_router_uve_up_xmpp_and_bgp_count
scripts.analytics.test_analytics.AnalyticsTestSanity1.test_verify_bgp_peer_uve
scripts.analytics.test_analytics.AnalyticsTestSanity2.runTest
.................
................
................
```
3. Run container with logs directory attached

After test run, all logs will be saved under ~/contrail-test-4/logs directory.

```
$ docker run -v ~/contrail-test-4/sanity_params.ini:/contrail-test/sanity_params.ini -v ~/contrail-test-4/sanity_testbed.json:/contrail-test/sanity_testbed.json \
   -v ~/contrail-test-4/logs/:/contrail-test/logs -it hkumar/contrail-test-juno

Python 2.7.6
no match
Applied patch
patching file __init__.py
+ echo 'Validating if test discovery passes in scripts/ and serial_scripts'
Validating if test discovery passes in scripts/ and serial_scripts
+ echo ''

+ GIVEN_TEST_PATH=
+ export PYTHONPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/contrail-test/scripts:/contrail-test/fixtures
+ PYTHONPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/contrail-test/scripts:/contrail-test/fixtures
+ export OS_TEST_PATH=./scripts
+ OS_TEST_PATH=./scripts
+ testr list-tests
running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-6000} \
${PYTHON:-python} -m subunit.run discover -t ./ ${OS_TEST_PATH:-./scripts} --list
scripts.analytics.test_analytics.AnalyticsTestSanity.test_bgprouter_uve_for_xmpp_and_bgp_peer_count
scripts.analytics.test_analytics.AnalyticsTestSanity.test_colector_uve_module_sates
scripts.analytics.test_analytics.AnalyticsTestSanity.test_config_node_uve_states
scripts.analytics.test_analytics.AnalyticsTestSanity.test_contrail_alarms[sanity,vcenter]
scripts.analytics.test_analytics.AnalyticsTestSanity.test_contrail_status[sanity,vcenter]
scripts.analytics.test_analytics.AnalyticsTestSanity.test_message_table
scripts.analytics.test_analytics.AnalyticsTestSanity.test_verify_hrefs
scripts.analytics.test_analytics.AnalyticsTestSanity.test_verify_object_logs[ci_sanity,sanity,vcenter]
scripts.analytics.test_analytics.AnalyticsTestSanity1.test_stats_tables
scripts.analytics.test_analytics.AnalyticsTestSanity1.test_verify__bgp_router_uve_up_xmpp_and_bgp_count
scripts.analytics.test_analytics.AnalyticsTestSanity1.test_verify_bgp_peer_uve
scripts.analytics.test_analytics.AnalyticsTestSanity2.runTest
.................
................
................

$ ls ~/contrail-test-4/logs/
analyticstestsanity3.log  analyticstestsanity.log  keystone_tests.log .....

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
