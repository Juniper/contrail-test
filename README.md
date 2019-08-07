
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

The Contrail Test repository contains the test code for validating the Contrail infrastructure.
The code is organized into ``fixtures`` , ``scripts`` and ``serial_scripts``.

Testcases under ``scripts`` folder are independent of each other and can be run in parallel.
Testcases under ``serial_scripts`` can have cluster-wide impact and MUST be run only one at a time.

``run_tests.sh`` lets you run these tests as well. Take a look at [ this ](https://github.com/Juniper/contrail-test/wiki/Running-Tests).

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

## Test container

The scripts can be executed from a containerized environment.
As part of the contrail software the test containers are also being built and posted @ https://hub.docker.com/r/opencontrailnightly/contrail-test-test/

### Build test container
Test container is split into base and test containers where in base has sku and
orchestrator independent packages like testr, chrome, wget, git etal and
test container has orchestrator and sku specific packages on top of base.

One can also custom build base and test containers
#### To build base test container
```
    $> ./build-container.sh base -h
       Build base container

       Usage: ./build-container.sh base
         -h|--help                     Print help message
         --registry-server REGISTRY_SERVER Docker registry hosting the base test container, specify if the image needs to be pushed
         --tag             TAG           Docker container tag, default to sku
    $> ./build-container.sh base --registry-server opencontrailnightly/ --tag ocata-bld-1
```
#### To build test container
```
    $> ./build-container.sh test -h
       Build test container

       Usage: ./build-container.sh test [OPTIONS]

         -h|--help                     Print help message
         --tag           TAG           Docker container tag, default to sku
         --base-tag      BASE_TAG      Specify contrail-base-test container tag to use. Defaults to 'latest'.
         --sku           SKU           Openstack version. Defaults to ocata
         --contrail-repo CONTRAIL_REPO Contrail Repository, mandatory.
         --registry-server REGISTRY_SERVER Docker registry hosting the base test container, Defaults to docker.io/opencontrail
         --post          POST          Upload the test container to the registy-server, if specified
    $> ./build-container.sh test --tag ocata-bld-1 --base-tag ocata-bld-1 --sku ocata --package-url http://path/to/contrail-install-packages.rpm --contrail-repo http://path/to/contrail/repo/bld-1 --registry-server opencontrailnightly
```

## Running Tests
* Create a test input file as per https://github.com/Juniper/contrail-test/blob/master/contrail_test_input.yaml.sample
* Download testrunner.sh script to the host where the test container will run
* Pull the test container image from dockerhub
* Execute the testrunner.sh script
```
    $> wget https://github.com/Juniper/contrail-test/raw/master/testrunner.sh
    $> docker pull opencontrailnightly/contrail-test-test:ocata-bld-1
    $> ./testrunner.sh run -P /path/to/contrail_test_input.yaml contrail-test-test:ocata-bld-1
```
You can find more detailed information about running tests @ (https://github.com/Juniper/contrail-test/wiki/How-to-use-contrail-test-container#sample-testrunnersh-commands)

### Filing Bugs
Use launchpad [http://bugs.launchpad.net/juniperopenstack](http://bugs.launchpad.net/juniperopenstack) to describe new bugs.

It will be useful to include the test run log file. 

For post-analysis of a cluster, a fab task ``attach_logs_cores`` can collect the logs and cassandra logs.

### Queries
Mail to
dev@lists.opencontrail.org and
users@lists.opencontrail.org.
### IRC 
\#opencontrail on freenode.net
