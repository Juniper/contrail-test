=================
contrail ci tests
=================

Docker build
------------
There is a Docker build script (docker/build.sh) which build docker containers for both contrail-test-ci as well as contrail-test.
::

  Usage: ./build.sh [OPTIONS] (contrail-test|contrail-test-ci)
  Build Contrail-test ci container
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

    ./build.sh --test-repo https://github.com/hkumarmk/contrail-test --test-ref working --ci-repo https://$GITUSER:$GITPASS@github.com/juniper/contrail-test-ci -e /tmp/export2 -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb contrail-test


- Docker build with artifacts

  ``./build.sh -c --ci-artifact /tmp/contrail-test-ci.tar.gz -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb --fab-artifact /tmp/contrail-fabric-utils.tar.gz contrail-test-ci``

- Docker build with combination of artifacts and git refs

  ``./build.sh -c --test-ref 1890b36 --ci-artifact /tmp/contrail-test-ci.tar.gz -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb --fab-artifact /tmp/contrail-fabric-utils.tar.gz contrail-test-ci``

- Build and export to /export/docker/contrail-test-ci/

  ``./build.sh -c --test-ref 1890b36 --ci-artifact /tmp/contrail-test-ci.tar.gz -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb --fab-artifact /tmp/contrail-fabric-utils.tar.gz contrail-test-ci -e /export/docker/contrail-test-ci/``

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

