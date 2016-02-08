=================
contrail ci tests
=================

This repo contain contrail ci tests and other common tools and libraries to run contrail-test.

Install and use contrail-test or contrail-test-ci
-------------------------------------------------

A script provided (install.sh) to install both contrail-test-ci as well as contrail-test.
::
    $ ./install.sh -h

    Install or do docker build of Contrail-test and contrail-test-ci

    Usage: ./install.sh (install|docker-build) [OPTIONS] (contrail-test|contrail-test-ci)

    Subcommands:

    install         Install contrail-test/contrail-test-ci
    docker-build    Build docker container

    Run ./install.sh <Subcommand> -h|--help to get subcommand specific help

    $ ./install.sh install -h

    Install Contrail-test or contrail-test-ci

    Usage: ./install.sh install [OPTIONS] (contrail-test|contrail-test-ci)

      -h|--help                     Print help message
      --test-repo REPO              Contrail-test git repo, Default: github.com/juniper/contrail-test-ci.git
      --test-ref REF                Contrail-test git reference - commit id, branch, tag, Default: master
      --fab-repo FAB_REPO           Contrail-fabric-utils git repo
      --fab-ref FAB_REF             Contrail-fabric-utils git reference (commit id, branch, or tag), Default: master
      --ci-repo CI_REPO	            Contrail-test-ci git repo, Default: github.com/juniper/contrail-test.git
      --ci-ref CI_REF               Contrail-test-ci reference (commit id, branch, or tag), Default: master
      --test-artifact ARTIFACT      Contrail test tar file - this tar file will be used instead of git source in case provided
      --ci-artifact CI_ARTICACT     Contrail test ci tar file
      --fab-artifact FAB_ARTIFACT   Contrail-fabric-utils tar file
      -u|--package-url PACKAGE_URL  Contrail-install-packages deb package web url, if url is provided, the
                                    package will be installed and setup local repo.

      positional arguments
        What to install             Valid options are contrail-test, contrail-test-ci

     Example:

      ./install.sh install --test-repo https://github.com/hkumarmk/contrail-test --test-ref working --ci-repo https://$GITUSER:$GITPASS@github.com/juniper/contrail-test-ci -e /tmp/export2 -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb contrail-test

    - Install with artifacts

      ./install.sh install --ci-artifact /tmp/contrail-test-ci.tar.gz \
            -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb \
            --fab-artifact /tmp/contrail-fabric-utils.tar.gz contrail-test-ci # Just use contrail-test as last argument to install contrail-test

    - combination of artifacts and git refs

      ./install.sh install --test-ref 1890b36 --ci-artifact /tmp/contrail-test-ci.tar.gz \
            -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb \
            --fab-artifact /tmp/contrail-fabric-utils.tar.gz contrail-test


Once it is installed, one should copy testbed.py to /opt/contrail/utils/fabfile/testbeds (or any custom fab path in which
case, one have to provide --contrail-fab-path while running run_tests.sh). Now just go to /opt/contrail-test
and run run_tests.sh as they have done before.

NOTE: No need to run any fab tasks like setup_testenv or anything. Running run_tests.sh will read testbed.py and build
 required files to run the tests (like sanity_params.ini, sanity_testbed.json).

Here is how I run contrail-test after Install it.

1. Copy testbed.py to /opt/contrail/utils/fabfile/testbeds/
2. cd /opt/contrail-test
3. run ./run_tests.sh with appropriate parameters

::

    $ cd /opt/contrail-test
    $ ./run_tests.sh -h
    Usage: ./run_tests.sh [OPTION]...
    Run Contrail test suite

      -V, --virtual-env        Always use virtualenv.  Install automatically if not present
      -N, --no-virtual-env     Don't use virtualenv.  Run tests in local environment
      -n, --no-site-packages   Isolate the virtualenv from the global Python environment
      -f, --force              Force a clean re-build of the virtual environment. Useful when dependencies have been added.
      -u, --update             Update the virtual environment with any newer package versions
      -U, --upload             Upload test logs
      -s, --sanity             Only run sanity tests
      -t, --parallel           Run testr in parallel
      -C, --config             Config file location
      -h, --help               Print this usage message
      -d, --debug              Run tests with testtools instead of testr. This allows you to use PDB
      -l, --logging            Enable logging
      -L, --logging-config     Logging config file location.  Default is logging.conf
      -m, --send-mail          Send the report at the end
      -F, --features           Only run tests from features listed
      -T, --tags               Only run tests taged with tags
      -c, --concurrency        Number of threads to be spawned
      --contrail-fab-path      Contrail fab path, default to /opt/contrail/utils
      -- [TESTROPTIONS]        After the first '--' you can pass arbitrary arguments to testr

    $ ./run_tests.sh
    [localhost] local: git branch
    fatal: Not a git repository (or any of the parent directories): .git

    2016-02-09 10:25:35:568148: Warning: local() encountered an error (return code 128) while executing 'git branch'
    2016-02-09 10:25:35:568148:
    2016-02-09 10:25:35:568148: 2016-02-09 10:25:35:561571: [root@10.204.217.88] run: cat /opt/contrail/contrail_packages/VERSION
    2016-02-09 10:25:35:568437: [root@10.204.217.88] out: BUILDID=2709
    2016-02-09 10:25:36:714451: [root@10.204.217.88] out:
    2016-02-09 10:25:36:714859:
    2016-02-09 10:25:36:719259: [localhost] local: git branch
    fatal: Not a git repository (or any of the parent directories): .git

    2016-02-09 10:25:36:726339: Warning: local() encountered an error (return code 128) while executing 'git branch'
    2016-02-09 10:25:36:726339:
    2016-02-09 10:25:36:726339: 2016-02-09 10:25:36:719675: [root@10.204.217.88] run: cat /opt/contrail/contrail_packages/VERSION
    2016-02-09 10:25:36:726615: [root@10.204.217.88] out: BUILDID=2709
    2016-02-09 10:25:36:777523: [root@10.204.217.88] out:
    2016-02-09 10:25:36:777781:
    2016-02-09 10:25:36:778033: [root@10.204.217.88] run: hostname
    2016-02-09 10:25:36:778463: [root@10.204.217.88] out: harishku-vm1
    2016-02-09 10:25:36:832563: [root@10.204.217.88] out:
    2016-02-09 10:25:36:832820:
    2016-02-09 10:25:36:833036: [root@10.204.217.88] run: hostname
    2016-02-09 10:25:36:833272: [root@10.204.217.88] out: harishku-vm1
    2016-02-09 10:25:36:884548: [root@10.204.217.88] out:
    2016-02-09 10:25:36:884789:
    2016-02-09 10:25:36:885041: [root@10.204.217.88] run: hostname
    2016-02-09 10:25:36:885263: [root@10.204.217.88] out: harishku-vm1
    2016-02-09 10:25:36:969527: [root@10.204.217.88] out:
    2016-02-09 10:25:36:969768:
    2016-02-09 10:25:36:974452: [root@10.204.217.90] run: hostname
    2016-02-09 10:25:36:974680: [root@10.204.217.90] out: harishku-vm3
    2016-02-09 10:25:37:708216: [root@10.204.217.90] out:
    2016-02-09 10:25:37:708449:
    2016-02-09 10:25:37:708709: [root@10.204.217.88] run: hostname
    2016-02-09 10:25:37:708983: [root@10.204.217.88] out: harishku-vm1
    2016-02-09 10:25:37:729606: [root@10.204.217.88] out:
    2016-02-09 10:25:37:729832:
    2016-02-09 10:25:37:730082: [root@10.204.217.89] run: hostname
    2016-02-09 10:25:37:730289: [root@10.204.217.89] out: localhost
    2016-02-09 10:25:38:520887: [root@10.204.217.89] out:
    2016-02-09 10:25:38:521179:
    2016-02-09 10:25:38:521440: [root@10.204.217.90] run: hostname
    2016-02-09 10:25:38:521712: [root@10.204.217.90] out: harishku-vm3
    2016-02-09 10:25:38:542269: [root@10.204.217.90] out:
    2016-02-09 10:25:38:542559:
    2016-02-09 10:25:38:542855: [root@10.204.217.88] run: hostname
    2016-02-09 10:25:38:543112: [root@10.204.217.88] out: harishku-vm1
    2016-02-09 10:25:38:589205: [root@10.204.217.88] out:
    2016-02-09 10:25:38:589499:
    2016-02-09 10:25:38:589721: [root@10.204.217.89] run: hostname
    2016-02-09 10:25:38:590029: [root@10.204.217.89] out: localhost
    2016-02-09 10:25:38:611151: [root@10.204.217.89] out:
    2016-02-09 10:25:38:611428:
    2016-02-09 10:25:38:616572: [root@10.204.217.90] run: hostname
    2016-02-09 10:25:38:616852: [root@10.204.217.90] out: harishku-vm3
    2016-02-09 10:25:38:639135: [root@10.204.217.90] out:
    2016-02-09 10:25:38:639500:
    2016-02-09 10:25:38:639774: [root@10.204.217.129] run: hostname
    2016-02-09 10:25:38:640058: [root@10.204.217.129] out: nodei17
    2016-02-09 10:25:38:965649: [root@10.204.217.129] out:
    2016-02-09 10:25:38:965880:
    2016-02-09 10:25:38:968799: Python 2.7.6
    no match
    Reversed (or previously applied) patch detected!  Skipping patch.
    1 out of 1 hunk ignored
    + echo 'Validating if test discovery passes in scripts/ and serial_scripts'
    Validating if test discovery passes in scripts/ and serial_scripts
    + echo ''

    + GIVEN_TEST_PATH=
    + export PYTHONPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/opt/contrail-test/scripts:/opt/contrail-test/fixtures
    + PYTHONPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/opt/contrail-test/scripts:/opt/contrail-test/fixtures
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
    scripts.analytics.test_analytics.AnalyticsTestSanity1.test_stats_tables
    scripts.analytics.test_analytics.AnalyticsTestSanity1.test_verify__bgp_router_uve_up_xmpp_and_bgp_count
    scripts.analytics.test_analytics.AnalyticsTestSanity1.test_verify_bgp_peer_uve
    scripts.analytics.test_analytics.AnalyticsTestSanity2.runTest
    scripts.analytics.test_analytics.AnalyticsTestSanity3.test_contrail_database_status[sanity,vcenter]
    scripts.analytics.test_analytics.AnalyticsTestSanity3.test_db_nodemgr_status[sanity,vcenter]
    scripts.analytics.test_analytics.AnalyticsTestSanity3.test_db_purge[sanity,vcenter]
    scripts.analytics.test_analytics.AnalyticsTestSanity3.test_verify_generator_collector_connections[sanity,vcenter]
    scripts.analytics.test_analytics.AnalyticsTestSanity3.test_verify_generator_connections_to_collector_node[sanity,vcenter]
    scripts.analytics.test_analytics.AnalyticsTestSanity3.test_verify_process_status_agent[sanity,vcenter]
    scripts.analytics.test_analytics.AnalyticsTestSanity3.test_verify_process_status_analytics_node[sanity,vcenter]
    scripts.analytics.test_analytics.AnalyticsTestSanity3.test_verify_process_status_config[sanity,vcenter]
    scripts.analytics.test_analytics.AnalyticsTestSanity3.test_verify_process_status_control_node[sanity,vcenter]
    scripts.analytics.test_analytics_basic.AnalyticsBasicTestSanity.test_verify_object_logs[ci_sanity,sanity,vcenter]
    scripts.ceilometer_tests.test_ceilometer.CeilometerTest.test_resources_by_admin_tenant
    scripts.ceilometer_tests.test_ceilometer.CeilometerTest.test_resources_by_user_tenant
    scripts.ceilometer_tests.test_ceilometer.CeilometerTest.test_sample_floating_ip_transmit_packets[sanity]
    scripts.discovery_regression.test_discovery.TestDiscovery.test_ApiServer_subscribed_to_collector_service
    scripts.discovery_regression.test_discovery.TestDiscovery.test_Schema_subscribed_to_collector_service
    scripts.discovery_regression.test_discovery.TestDiscovery.test_ServiceMonitor_subscribed_to_collector_service
    scripts.discovery_regression.test_discovery.TestDiscovery.test_agents_connected_to_collector_service[sanity,vcenter]
    scripts.discovery_regression.test_discovery.TestDiscovery.test_agents_connected_to_dns_service
    scripts.discovery_regression.test_discovery.TestDiscovery.test_cleanup
    scripts.discovery_regression.test_discovery.TestDiscovery.test_control_nodes_connected_to_collector_service



Docker build
------------
There is a script (install.sh) which build docker containers for both contrail-test-ci as well as contrail-test.
::
    $ ./install.sh docker-build -h

    Build Contrail-test and contrail-test-ci docker container

    Usage: ./install.sh docker-build [OPTIONS] (contrail-test|contrail-test-ci)

      -h|--help                     Print help message
      --test-repo REPO                Contrail-test git repo, Default: github.com/juniper/contrail-test-ci.git
      --test-ref REF                  Contrail-test git reference - commit id, branch, tag, Default: master
      --fab-repo FAB_REPO           Contrail-fabric-utils git repo
      --fab-ref FAB_REF             Contrail-fabric-utils git reference (commit id, branch, or tag), Default: master
      --ci-repo CI_REPO	            Contrail-test-ci git repo, Default: github.com/juniper/contrail-test.git
      --ci-ref CI_REF               Contrail-test-ci reference (commit id, branch, or tag), Default: master
      --container-tag CONTAINER_TAG Docker container tag, default to contrail-test-ci-<openstack-release>:<contrail-version>
                                        openstack-release and contrail-version is extracted from contrail-install-package name
                                        e.g contrail-test-ci-juno:2.21-105
      --test-artifact ARTIFACT        Contrail test tar file - this tar file will be used instead of git source in case provided
      --ci-artifact CI_ARTICACT     Contrail test ci tar file
      --fab-artifact FAB_ARTIFACT   Contrail-fabric-utils tar file
      -u|--package-url PACKAGE_URL  Contrail-install-packages deb package web url
      -c|--use-cache                Use docker cache for the build
      -e|--export EXPORT_PATH       Export Container image to the path provided

      positional arguments
        Type of build               What to build, valid options are contrail-test, contrail-test-ci

     Example:

      ./install.sh docker-build --test-repo https://github.com/hkumarmk/contrail-test --test-ref working --ci-repo \
        https://$GITUSER:$GITPASS@github.com/juniper/contrail-test-ci -e /tmp/export2 \
        -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb contrail-test

- Docker build with artifacts

  ``./install.sh docker-build -c --ci-artifact /tmp/contrail-test-ci.tar.gz \
        -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb \
        --fab-artifact /tmp/contrail-fabric-utils.tar.gz contrail-test-ci``

- Docker build with combination of artifacts and git refs

  ``./install.sh docker-build --test-ref 1890b36 --ci-artifact /tmp/contrail-test-ci.tar.gz \
        -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb \
        --fab-artifact /tmp/contrail-fabric-utils.tar.gz contrail-test-ci``

- Build and export to /export/docker/contrail-test-ci/

  ``./install.sh docker-build --test-ref 1890b36 --ci-artifact /tmp/contrail-test-ci.tar.gz \
        -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb \
        --fab-artifact /tmp/contrail-fabric-utils.tar.gz contrail-test-ci -e /export/docker/contrail-test-ci/``

Docker Container Execution
--------------------------

- Load docker image from /export/docker/contrail-test-ci/contrail-test-ci-juno-2.21-105.tar.gz

$ docker load < /export/docker/contrail-test-ci/contrail-test-ci-juno-2.21-105.tar.gz

- Execute docker container
  
  it run contrail-test ci tests and log the console. The console output may be captured at later point by running "docker logs [-f] <container id>".

$ docker run -v /opt/contrail/utils/fabfile/testbeds/testbed.py:/opt/contrail/utils/fabfile/testbeds/testbed.py -t contrail-test-ci-juno:2.21-105

- Execute the container with logs saved in specific location

  The logs will be saved under /export/logs/contrail-test-ci/ on docker host.

  $ docker run -v /opt/contrail/utils/fabfile/testbeds/testbed.py:/opt/contrail/utils/fabfile/testbeds/testbed.py -v /export/logs/contrail-test-ci/:/contrail-test/logs -t contrail-test-ci-juno:2.21-105

contrail-test.sh
----------------

This is a helper script to manage (run/rebuild/list) contrail-test/contrail-test-ci container.