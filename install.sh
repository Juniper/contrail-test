#!/bin/bash -x

BUILD_PLATFORM=$(cat /etc/lsb-release | grep DISTRIB_RELEASE | cut -d '=' -f2)
CONTRAIL_TEST_CI_REPO=https://github.com/juniper/contrail-test-ci
CONTRAIL_TEST_CI_REF=master
CONTRAIL_TEST_REPO=https://github.com/juniper/contrail-test
CONTRAIL_TEST_REF=master
CONTRAIL_FAB_REPO=https://github.com/juniper/contrail-fabric-utils
CONTRAIL_FAB_REF=master
CIRROS_IMAGE_URL=${CIRROS_IMAGE_URL:-http://10.84.5.120/cs-shared/images/converts/cirros-0.3.0-x86_64-disk.vmdk.gz}
SVC_IN_NET_NAT_URL=${SVC_IN_NET_NAT_URL:-http://10.84.5.120/cs-shared/images/tinycore/tinycore-in-network-nat.qcow2.gz}
SVC_IN_NET_URL=${SVC_IN_NET_URL:-http://10.84.5.120/cs-shared/images/tinycore/tinycore-in-network.qcow2.gz}
BASE_DIR=`dirname $(readlink -f $0)`
PACKAGES_REQUIRED_UBUNTU="python-pip ant python-novaclient python-neutronclient python-cinderclient \
    python-contrail python-glanceclient python-heatclient python-ceilometerclient python-setuptools contrail-utils \
    patch git ipmitool python-requests"
PACKAGES_REQUIRED_UBUNTU_DOCKER_BUILD="$PACKAGES_REQUIRED_UBUNTU python-dev libxslt1-dev libz-dev libyaml-dev sshpass"
PACKAGES_REQUIRED_RALLY="libssl-dev libffi-dev python-dev libxml2-dev libxslt1-dev libpq-dev libpq5=9.3.15-0ubuntu0.14.04"
if [ ${BUILD_PLATFORM} = "16.04" ]; then
    PACKAGES_REQUIRED_UBUNTU_DOCKER_BUILD="$PACKAGES_REQUIRED_UBUNTU_DOCKER_BUILD gcc-5-base=5.4.0-6ubuntu1~16.04.4 libgcc-5-dev=5.4.0-6ubuntu1~16.04.4 libstdc++-5-dev=5.4.0-6ubuntu1~16.04.4"
    PACKAGES_REQUIRED_RALLY="libssl-dev libffi-dev python-dev libxml2-dev libxslt1-dev libpq-dev libpq5"
    EXTRAS="libc-dev-bin=2.23-0ubuntu5 libc6-dev=2.23-0ubuntu5 libexpat1-dev libexpat1 libpython2.7-dev python2.7-dev"
else
    EXTRAS="http://10.84.5.120/cs-shared/builder/cache/ubuntu1404/contrail-test/libexpat1-dev_2.1.0-4ubuntu1.3_amd64.deb http://10.84.5.120/cs-shared/builder/cache/ubuntu1404/contrail-test/libexpat1_2.1.0-4ubuntu1.3_amd64.deb http://10.84.5.120/cs-shared/builder/cache/ubuntu1404/contrail-test/libpython2.7-dev_2.7.6-8ubuntu0.2_amd64.deb http://10.84.5.120/cs-shared/builder/cache/ubuntu1404/contrail-test/python2.7-dev_2.7.6-8ubuntu0.2_amd64.deb"
    PACKAGES_REQUIRED_RALLY="libssl-dev libffi-dev python-dev libxml2-dev libxslt1-dev libpq-dev libpq5=9.3.15-0ubuntu0.14.04"
fi

usage () {
    cat <<EOF
Install or do docker build of Contrail-test and contrail-test-ci

Usage: $0 (install|docker-build) [OPTIONS] (contrail-test|contrail-test-ci|rally)

Subcommands:

install         Install contrail-test/contrail-test-ci
docker-build    Build docker container

Run $0 <Subcommand> -h|--help to get subcommand specific help

EOF
}

# Provided Docker image available?
is_image_available () {
    tag=${1:-$pos_arg}
    repo=${tag%:.*}
    version=${tag#*:}
    docker images $repo | grep -q $version
}

function have_command {
    type "$1" >/dev/null 2>/dev/null
}

function fail {
    echo $@
    exit 1
}

function distro {
    if have_command apt-get; then
        DISTRO=ubuntu
        PACKAGES_REQUIRED=$PACKAGES_REQUIRED_UBUNTU
        PACKAGES_REQUIRED_DOCKER_BUILD=$PACKAGES_REQUIRED_UBUNTU_DOCKER_BUILD
#    elif have_command rpm; then
#        DISTRO=redhat
    else
        echo "Unsupported distribution"
        exit 1
    fi
}

function make_entrypoint_rally {
    cat <<'EOT'
#!/bin/bash

sendmail=1

while getopts ":t:p:mu" opt; do
  case $opt in
    t)
        testbed_input=$OPTARG
        ;;
    p)
        contrail_fabpath_input=$OPTARG
        ;;
    s)
        scenarios_list=$OPTARG
        ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done
export ci_image=${CI_IMAGE:-'cirros'}
TESTBED=${testbed_input:-${TESTBED:-'/opt/contrail/utils/fabfile/testbeds/testbed.py'}}
CONTRAIL_FABPATH=${contrail_fabpath_input:-${CONTRAIL_FABPATH:-'/opt/contrail/utils'}}
SCENARIOS=${scenarios_list:-${SCENARIOS:-''}}

if [[ ( ! -f /contrail-test/sanity_params.ini || ! -f /contrail-test/sanity_testbed.json ) && ! -f $TESTBED ]]; then
    echo "ERROR! Either testbed file or sanity_params.ini or sanity_testbed.json under /contrail-test is required.
          you probably forgot to attach them as volumes"
    exit 100
fi

if [ ! $TESTBED -ef ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py ]; then
    mkdir -p ${CONTRAIL_FABPATH}/fabfile/testbeds/
    cp $TESTBED ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py
fi

if [ $sendmail -eq 1 ]; then
    mail_arg='-m'
fi

cd /contrail-test
if [[ $SCENARIOS == "" ]]; then
./run_rally.sh
else
./run_rally.sh -s $SCENARIOS
fi

if [ -d /contrail-test.save ]; then
    cp -f ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py /contrail-test.save/
    rsync -a --exclude logs/ --exclude report/ /contrail-test /contrail-test.save/
fi

EOT
}

function make_entrypoint_contrail_test_ci {
    cat <<'EOT'
#!/bin/bash

sendmail=1

while getopts ":t:p:mu" opt; do
  case $opt in
    t)
        testbed_input=$OPTARG
        ;;
    p)
        contrail_fabpath_input=$OPTARG
        ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done
export ci_image=${CI_IMAGE:-'cirros'}
TESTBED=${testbed_input:-${TESTBED:-'/opt/contrail/utils/fabfile/testbeds/testbed.py'}}
CONTRAIL_FABPATH=${contrail_fabpath_input:-${CONTRAIL_FABPATH:-'/opt/contrail/utils'}}

if [[ ( ! -f /contrail-test/sanity_params.ini || ! -f /contrail-test/sanity_testbed.json ) && ! -f $TESTBED ]]; then
    echo "ERROR! Either testbed file or sanity_params.ini or sanity_testbed.json under /contrail-test is required.
          you probably forgot to attach them as volumes"
    exit 100
fi

if [ ! $TESTBED -ef ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py ]; then
    mkdir -p ${CONTRAIL_FABPATH}/fabfile/testbeds/
    cp $TESTBED ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py
fi

if [ $sendmail -eq 1 ]; then
    mail_arg='-m'
fi

cd /contrail-test
./run_ci.sh $mail_arg --contrail-fab-path $CONTRAIL_FABPATH $EXTRA_RUN_TEST_ARGS

if [ -d /contrail-test.save ]; then
    cp -f ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py /contrail-test.save/
    rsync -a --exclude logs/ --exclude report/ /contrail-test /contrail-test.save/
fi

EOT
}

function make_entrypoint_contrail_test {
    cat <<'EOT'
#!/bin/bash -x

function usage {
    cat <<EOF
Usage: $0 [OPTIONS]

Run contrail-test in container

  -h  Print help
  -t  Testbed file, Default: /opt/contrail/utils/fabfile/testbeds/testbed.py
  -p  contrail fab utils path. Default: /opt/contrail/utils
  -f  features to test. Default: sanity
      Valid options:
        sanity, quick_sanity, ci_sanity, ci_sanity_WIP, ci_svc_sanity,
        upgrade, webui_sanity, ci_webui_sanity, devstack_sanity, upgrade_only
  -T  test tags to run tests. If not provided, try $TEST_TAGS variable

EOF
}

while getopts ":T:t:p:f:h" opt; do
  case $opt in
    h)
      usage
      exit
      ;;
    t)
      testbed_input=$OPTARG
      ;;
    p)
      contrail_fabpath_input=$OPTARG
      ;;
    f)
      feature_input=$OPTARG
      ;;
    T)
      test_tags=$OPTARG
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

TESTBED=${testbed_input:-${TESTBED:-'/opt/contrail/utils/fabfile/testbeds/testbed.py'}}
CONTRAIL_FABPATH=${contrail_fabpath_input:-${CONTRAIL_FABPATH:-'/opt/contrail/utils'}}
FEATURE=${feature_input:-${FEATURE:-'sanity'}}
TEST_TAGS=${test_tags:-$TEST_TAGS}

if [[ ( ! -f /contrail-test/sanity_params.ini || ! -f /contrail-test/sanity_testbed.json ) && ! -f $TESTBED ]]; then
    echo "ERROR! Either testbed file or sanity_params.ini or sanity_testbed.json under /contrail-test is required.
          you probably forgot to attach them as volumes"
    exit 100
fi

if [ ! $TESTBED -ef ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py ]; then
    mkdir -p ${CONTRAIL_FABPATH}/fabfile/testbeds/
    cp $TESTBED ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py
fi

cd /contrail-test
run_tests="./run_tests.sh --contrail-fab-path $CONTRAIL_FABPATH "
if [[ -n $TEST_RUN_CMD ]]; then
    $TEST_RUN_CMD $EXTRA_RUN_TEST_ARGS
    rv_run_test=$?
elif [[ -n $TEST_TAGS ]]; then
    $run_tests -T $TEST_TAGS $EXTRA_RUN_TEST_ARGS
    rv_run_test=$?
else
    case $FEATURE in
        sanity)
            $run_tests --sanity --send-mail -U $EXTRA_RUN_TEST_ARGS
            rv_run_test=$?
            ;;
        quick_sanity)
            $run_tests -T quick_sanity --send-mail -t $EXTRA_RUN_TEST_ARGS
            rv_run_test=$?
            ;;
        ci_sanity)
            $run_tests -T ci_sanity --send-mail -U $EXTRA_RUN_TEST_ARGS
            rv_run_test=$?
            ;;
        ci_sanity_WIP)
            $run_tests -T ci_sanity_WIP --send-mail -U $EXTRA_RUN_TEST_ARGS
            rv_run_test=$?
            ;;
        ci_svc_sanity)
            python ci_svc_sanity_suite.py
            rv_run_test=$?
            ;;
        upgrade)
            $run_tests -T upgrade --send-mail -U $EXTRA_RUN_TEST_ARGS
            rv_run_test=$?
            ;;
        webui_sanity)
            python webui_tests_suite.py
            rv_run_test=$?
            ;;
        ci_webui_sanity)
            python ci_webui_sanity.py
            rv_run_test=$?
            ;;
        devstack_sanity)
            python devstack_sanity_tests_with_setup.py
            rv_run_test=$?
            ;;
        upgrade_only)
            python upgrade/upgrade_only.py
            rv_run_test=$?
            ;;
        *)
            echo "Unknown FEATURE - ${FEATURE}"
            exit 1
            ;;
    esac
fi


if [ -d /contrail-test.save ]; then
    cp -f ${CONTRAIL_FABPATH}/fabfile/testbeds/testbed.py /contrail-test.save/
    rsync -a --exclude logs/ --exclude report/ /contrail-test /contrail-test.save/
fi

exit $rv_run_test

EOT
}

function make_dockerfile {
    type=$1
    if [[ ${BUILD_PLATFORM} == "16.04" ]]; then
        base_image=${2:-hkumar/ubuntu:16.04}
    else
        base_image=${2:-hkumar/ubuntu-14.04.2}
    fi
    cat <<EOF
FROM $base_image
MAINTAINER Juniper Contrail <contrail@juniper.net>
ARG http_proxy
ARG https_proxy
ARG CONTRAIL_INSTALL_PACKAGE_URL
ARG ENTRY_POINT=docker_entrypoint.sh
ARG SSHPASS
ENV DEBIAN_FRONTEND=noninteractive
ENV SKU=$openstack_release
EOF
    if [[ ${BUILD_PLATFORM} == "16.04" ]]; then
        cat <<EOF
RUN apt-get update; apt-get install -y bzip2 wget sudo perl-modules-5.22
RUN apt-get install -y $EXTRAS
EOF
    fi
    if [[ $type == 'prep' ]]; then
        if [[ $CONTRAIL_INSTALL_PACKAGE_URL =~ ^http[s]*:// ]]; then
            cat <<EOF
# Just check if $CONTRAIL_INSTALL_PACKAGE_URL is there, if not valid, build will fail
RUN wget -q --spider $CONTRAIL_INSTALL_PACKAGE_URL

# setup contrail-install-packages
RUN wget $CONTRAIL_INSTALL_PACKAGE_URL -O /contrail-install-packages.deb && \
    dpkg -i /contrail-install-packages.deb && \
    rm -f /contrail-install-packages.deb && \
    cd /opt/contrail/contrail_packages/ && ./setup.sh;
EOF
            if [[ ${BUILD_PLATFORM} == "16.04" ]]; then
                cat <<EOF
RUN cd /opt/contrail/contrail_install_repo/ && apt-get install -y $EXTRAS;
EOF
            else
RUN cd /opt/contrail/contrail_install_repo/ && wget $EXTRAS && \
    cd /opt/contrail/contrail_install_repo/ && dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz && apt-get update;
EOF
            fi
            cat <<EOF
RUN apt-get install -y $PACKAGES_REQUIRED_DOCKER_BUILD && \
    sed -i '/file:\/opt\/contrail\/contrail_install_repo/d' /etc/apt/sources.list ; \
    rm -fr /opt/contrail/* ; apt-get -y autoremove && apt-get -y clean;
EOF
        elif [[ $CONTRAIL_INSTALL_PACKAGE_URL =~ ^ssh[s]*:// ]]; then
            scp_package=1
            server=` echo $CONTRAIL_INSTALL_PACKAGE_URL | sed 's/ssh:\/\///;s|\/.*||'`
            path=`echo $CONTRAIL_INSTALL_PACKAGE_URL |sed -r 's#ssh://[a-zA-Z0-9_\.\-]+##'`
            cat << EOF

RUN apt-get install -y sshpass && \
    sshpass -e scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${sshuser_sub}${server}:${path} /contrail-install-packages.deb && \
    dpkg -i /contrail-install-packages.deb && \
    rm -f /contrail-install-packages.deb && \
    cd /opt/contrail/contrail_packages/ && ./setup.sh; 
EOF
            if [[ ${BUILD_PLATFORM} == "16.04" ]]; then
                cat <<EOF
RUN cd /opt/contrail/contrail_install_repo/ && apt-get install -y $EXTRAS;
EOF
            else
                cat <<EOF
RUN cd /opt/contrail/contrail_install_repo/ && wget $EXTRAS && \
    cd /opt/contrail/contrail_install_repo/ && dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz && apt-get update;
EOF
            fi
            cat <<EOF
RUN apt-get install -y $PACKAGES_REQUIRED_DOCKER_BUILD && \
    sed -i '/file:\/opt\/contrail\/contrail_install_repo/d' /etc/apt/sources.list ; \
    rm -fr /opt/contrail/* ; apt-get -y autoremove; apt-get -y clean
EOF
        else
            echo "ERROR, Unknown url format, only http[s], ssh supported" >&2
            exit 1
        fi

        cat <<EOF
    RUN wget -q --spider $CIRROS_IMAGE_URL
    RUN mkdir -p /images && wget $CIRROS_IMAGE_URL -O /images/cirros-0.3.0-x86_64-disk.vmdk.gz
    RUN wget $SVC_IN_NET_NAT_URL -O /images/tinycore-in-network-nat.qcow2.gz
    RUN wget $SVC_IN_NET_URL -O /images/tinycore-in-network.qcow2.gz
EOF
    #Finished dockerfile for prep image
    else
        # In case of contrail-test, ci should be added in /contrail-test-ci and later merge both
        # /contrail-test-ci and /contrail-test together
        ci_dir='/contrail-test'

        if [[ $build_type == 'contrail-test' ]]; then
            ci_dir='/contrail-test-ci'
            merge_code='cp -RTf /contrail-test-ci /contrail-test; '
            if [[ -f $CONTRAIL_TEST_ARTIFACT ]]; then
                echo -e "ADD $(basename $CONTRAIL_TEST_ARTIFACT) /"
            else
                cat <<EOF
RUN echo 'deb http://dl.google.com/linux/chrome/deb/ stable main' > /etc/apt/sources.list.d/chrome.list; \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -; \
    apt-get -q -y update; apt-get -qy install unzip firefox xvfb; \
    wget -c http://chromedriver.storage.googleapis.com/2.10/chromedriver_linux64.zip; \
    unzip chromedriver_linux64.zip; cp ./chromedriver /usr/bin/; chmod ugo+rx /usr/bin/chromedriver; \
    apt-get -qy install libxpm4 libxrender1 libgtk2.0-0 libnss3 libgconf-2-4 google-chrome-stable; \
    apt-get remove -y firefox; \
    wget https://ftp.mozilla.org/pub/mozilla.org/firefox/releases/31.0/linux-x86_64/en-US/firefox-31.0.tar.bz2 -O /tmp/firefox.tar.bz2; \
    cd /opt; tar xjf /tmp/firefox.tar.bz2; ln -sf /opt/firefox/firefox /usr/bin/firefox;

RUN git clone $CONTRAIL_TEST_REPO /contrail-test; \
    cd /contrail-test ; \
    git checkout $CONTRAIL_TEST_REF; \
    git reset --hard; \
    rm -fr .git
EOF
            fi
        elif [[ ($build_type == 'contrail-test-ci' || $build_type == 'rally') && -f $CONTRAIL_TEST_CI_ARTIFACT ]] ; then
            merge_code='mv /contrail-test-ci /contrail-test; '
        fi

        if [[ -f $CONTRAIL_TEST_CI_ARTIFACT ]]; then
            echo -e "ADD $(basename $CONTRAIL_TEST_CI_ARTIFACT) /"
        else
            cat <<EOF
RUN git clone $CONTRAIL_TEST_CI_REPO $ci_dir; \
    cd $ci_dir ; \
    git checkout $CONTRAIL_TEST_CI_REF; \
    git reset --hard; \
    rm -fr .git
EOF
         fi

        if [[ ! -z $RALLY_REPO ]]; then
            cat <<EOF
RUN cd contrail-test-ci ; \
    apt-get install -y $PACKAGES_REQUIRED_RALLY ; \
    ./install_rally.sh $RALLY_REPO
EOF
        fi

        if [[ -f $CONTRAIL_FAB_ARTIFACT ]]; then
            echo -e "ADD $(basename $CONTRAIL_FAB_ARTIFACT) /opt/contrail/"
            fab_utils_mv="mv /opt/contrail/fabric-utils /opt/contrail/utils; "
        else
            cat <<EOF
RUN git clone $CONTRAIL_FAB_REPO /opt/contrail/utils; \
    cd /opt/contrail/utils ; \
    git checkout $CONTRAIL_FAB_REF; \
    git reset --hard;
EOF
        fi

        cat <<EOF
RUN sudo pip install -U pip
RUN $merge_code $fab_utils_mv cd /contrail-test && pip install -r requirements.txt
RUN mv /images /contrail-test/images
COPY \$ENTRY_POINT /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
EOF
    fi
}

docker_build () {
    usage () {
    cat <<EOF
Build Contrail-test and contrail-test-ci docker container

Usage: $0 docker-build [OPTIONS] (contrail-test|contrail-test-ci)

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
  -u|--package-url PACKAGE_URL  Contrail-install-packages deb package web url (http:// or https://) or scp path
                                (ssh://<server ip/name/< package path>), if url is provided, the
                                package will be installed and setup local repo.
                                In case of scp, user name and password will be read from environment variables
                                SSHUSER - user name to be used during scp, Default: current user
                                SSHPASS - user password to be used during scp

  -c|--use-cache                Use docker cache for the build
  -e|--export EXPORT_PATH       Export Container image to the path provided
  -f|--force                    Build the "prep" containers even though they are exist. Prep containers are the intermediate
                                containers which has all contrail packages installed, and ready to setup contrail-test-ci/contrail-test

  positional arguments
    Type of build               What to build, valid options are contrail-test, contrail-test-ci

 Example:

  $ $0 docker-build --test-repo https://github.com/hkumarmk/contrail-test --test-ref working
        --ci-repo https://\$GITUSER:\$GITPASS@github.com/juniper/contrail-test-ci -e /tmp/export2
        -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb contrail-test

  $ export SSHUSER=user1 SSHPASS=password
  $ $0 docker-build --test-repo https://github.com/hkumarmk/contrail-test --test-ref working
        --ci-repo https://\$GITUSER:\$GITPASS@github.com/juniper/contrail-test-ci -e /tmp/export2
        -u ssh://nodei16/var/cache/artifacts/contrail-install-packages_2.21-105~juno_all.deb contrail-test


EOF
    }

    build_prep () {
        image_tag=${1:-$PREP_IMAGE}
        BUILD_DIR=`mktemp -d`
        if [ ${BUILD_PLATFORM} = "16.04" ]; then
            make_dockerfile prep 'hkumar/ubuntu:16.04' > $BUILD_DIR/Dockerfile
        else
            make_dockerfile prep 'hkumar/ubuntu-14.04.2' > $BUILD_DIR/Dockerfile
        fi

        if [[ -n $scp_package ]]; then
            # Disabling xtrace to avoid printing SSHPASS
            if xtrace_status; then
                set +x
                xtrace=1
            fi
            ssh_build_arg="--build-arg SSHPASS=$SSHPASS"
        fi
        docker build ${cache_opt} ${proxy_args} -t $image_tag \
            --build-arg CONTRAIL_INSTALL_PACKAGE_URL=$CONTRAIL_INSTALL_PACKAGE_URL \
            ${ssh_build_arg} $BUILD_DIR; rv=$?
        [[ -n $xtrace ]] && set -x

        rm -rf $BUILD_DIR
        return $rv
    }

    build_final () {
        base_image=${1:-$PREP_IMAGE}
        BUILD_DIR=`mktemp -d`
        make_dockerfile final $base_image > $BUILD_DIR/Dockerfile

        if [[ -f $CONTRAIL_TEST_ARTIFACT ]]; then
            cp $CONTRAIL_TEST_ARTIFACT $BUILD_DIR/
        fi

        if [[ -f $CONTRAIL_TEST_CI_ARTIFACT ]]; then
            cp $CONTRAIL_TEST_CI_ARTIFACT $BUILD_DIR
        fi

        if [[ -f $CONTRAIL_FAB_ARTIFACT ]]; then
            cp $CONTRAIL_FAB_ARTIFACT $BUILD_DIR
        fi


        if [[ $build_type == 'contrail-test' ]]; then
            make_entrypoint_contrail_test > ${BUILD_DIR}/docker_entrypoint.sh
        elif [[ $build_type == 'contrail-test-ci' ]]; then
            make_entrypoint_contrail_test_ci > ${BUILD_DIR}/docker_entrypoint.sh
        elif [[ $build_type == 'rally' ]]; then
            make_entrypoint_rally > ${BUILD_DIR}/docker_entrypoint.sh
        else
            echo "ERROR! Unknown build_type: $build_type"
            exit 1
        fi

        docker build ${proxy_args} ${cache_opt} -t $CONTAINER_TAG $BUILD_DIR; rv=$?
        rm -rf $BUILD_DIR
        return $rv
    }

    save () {
        if [[ -n $EXPORT_PATH ]]; then
            echo "Exporting the image to $EXPORT_PATH"
            mkdir -p $EXPORT_PATH
            docker save $CONTAINER_TAG | gzip -c > ${EXPORT_PATH}/docker-image-${CONTAINER_TAG/:/-}.tar.gz; rv=$?
            if [ $rv -eq 0 ]; then
                echo "Successfully exported the image to ${EXPORT_PATH}/docker-image-${CONTAINER_TAG/:/-}.tar.gz"
                docker rmi -f $CONTAINER_TAG; rv=$?
                if [ $rv -eq 0 ]; then
                    echo "Cleaned up the image $CONTAINER_TAG from build environment"
                else
                    echo "Failed to cleanup the image $CONTAINER_TAG from the build environment, please cleanup manually"
                    exit 1
                fi
            else
                echo "Failed to export the image $CONTAINER_TAG"
                exit 2
            fi
        fi
    }

    if ! options=$(getopt -o hcu:t:e:f -l help,force,test-artifact:,ci-artifact:,rally-repo:,fab-artifact:,use-cache,ci-repo:,ci-ref:,export:,test-repo:,test-ref:,contrail-install-package-url:,fab-repo:,fab-ref:,container-tag: -- "$@"); then
# parse error
        usage
        exit 1
    fi
    eval set -- "$options"

    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) usage; exit;;
            --test-repo) CONTRAIL_TEST_REPO=$2; shift;;
            --test-ref) CONTRAIL_TEST_REF=$2; shift;;
            -u|--package-url) CONTRAIL_INSTALL_PACKAGE_URL=$2; shift;;
            --fab-repo) CONTRAIL_FAB_REPO=$2; shift;;
            --fab-ref) CONTRAIL_FAB_REF=$2; shift;;
            --ci-repo) CONTRAIL_TEST_CI_REPO=$2; shift;;
            --rally-repo) RALLY_REPO=$2; shift;;
            --ci-ref) CONTRAIL_TEST_CI_REF=$2; shift;;
            --test-artifact) CONTRAIL_TEST_ARTIFACT=$2; shift;;
            --ci-artifact) CONTRAIL_TEST_CI_ARTIFACT=$2; shift;;
            --fab-artifact) CONTRAIL_FAB_ARTIFACT=$2; shift;;
            -t|--container-tag) CONTAINER_TAG=$2; shift;;
            -c|--use-cache) CACHE=1;;
            -e|--export) EXPORT_PATH=$2; shift;;
            -f|--force) FORCE_BUILD=1;;
            --) :;;
            *) build_type=$1;;
	    esac
	    shift
    done

    if [[ -z $CONTRAIL_INSTALL_PACKAGE_URL ]]; then
        echo "No contrail package url provided"; echo
        usage
        exit 1
    fi

    if [[ $CONTRAIL_INSTALL_PACKAGE_URL =~ (ssh|http|https)*://.*/contrail-install-packages_[0-9\.\-]+~[a-zA-Z]+_all.deb ]]; then
        contrail_version=`echo ${CONTRAIL_INSTALL_PACKAGE_URL##*/} | sed 's/contrail-install-packages_\([0-9\.\-]*\).*/\1/'`
        openstack_release=`echo ${CONTRAIL_INSTALL_PACKAGE_URL##*/} | sed 's/contrail-install-packages_[0-9\.\-]*~\([a-zA-Z]*\).*/\1/'`
    else
        echo -e "Not able to extract contrail-version and SKU from contrail package url\nBad contrail package url, it should match regex http[s]*://.*/contrail-install-packages_[0-9\.\-]+~[a-zA-Z]+_all.deb"
        exit 1
    fi

    if [[ -z $CONTAINER_TAG ]]; then
        CONTAINER_TAG=${build_type}-${openstack_release}:${contrail_version}
    fi

    # IS docker runnable?
    docker  -v &> /dev/null ; rv=$?

    if [ $rv -ne 0 ]; then
      echo "docker is not installed, please install docker-engine (https://docs.docker.com/engine/installation/)"
      exit 1
    fi

    if [[ -z $CACHE ]]; then
      cache_opt='--no-cache'
    fi

    if [[ -n $http_proxy ]]; then
        proxy_args="--build-arg http_proxy=$http_proxy "
    fi

    if [[ -n $https_proxy ]]; then
        proxy_args="$proxy_args --build-arg https_proxy=$https_proxy "
    fi

    PREP_IMAGE="prep-${openstack_release}:${contrail_version}"
    if ! is_image_available "$PREP_IMAGE" || [[ -n $FORCE_BUILD ]]; then
        echo "Building prep image - $PREP_IMAGE"
        build_prep; rv=$?
        if [ $rv -eq 0 ]; then
            echo "Successfully built prep image"
        else
            fail "ERROR!! Failed to build prep image"
        fi
    fi
    echo "Building final image - $CONTAINER_TAG"
    build_final; rv=$?
    if [ $rv -eq 0 ]; then
        echo "Successfully built the container image - $CONTAINER_TAG"
        save
    else
        fail "ERROR! Failed to build the container image - $CONTAINER_TAG"
    fi
}

xtrace_status() {
  set | grep -q SHELLOPTS=.*:xtrace
  return $?
}

try_wget () {
    wget -q --spider $1;
    return $?
}

install_req_apt () {
    DEBIAN_FRONTEND=noninteractive
    apt-get install -y --force-yes $PACKAGES_REQUIRED
}

install () {
    usage () {
    cat <<EOF
Install Contrail-test or contrail-test-ci

Usage: $0 install [OPTIONS] (contrail-test|contrail-test-ci)

  -h|--help                     Print help message
  --test-repo REPO              Contrail-test git repo, Default: github.com/juniper/contrail-test-ci.git
  --test-ref REF                Contrail-test git reference - commit id, branch, tag, Default: master
  --fab-repo FAB_REPO           Contrail-fabric-utils git repo
  --fab-ref FAB_REF             Contrail-fabric-utils git reference (commit id, branch, or tag), Default: master
  --ci-repo CI_REPO                 Contrail-test-ci git repo, Default: github.com/juniper/contrail-test.git
  --ci-ref CI_REF               Contrail-test-ci reference (commit id, branch, or tag), Default: master
  --test-artifact ARTIFACT      Contrail test tar file - this tar file will be used instead of git source in case provided
  --ci-artifact CI_ARTICACT     Contrail test ci tar file
  --fab-artifact FAB_ARTIFACT   Contrail-fabric-utils tar file
  -i|--install-dir INSTALL_DIR  Install directory, Default: /opt/contrail-test
  -u|--package-url PACKAGE_URL  Contrail-install-packages deb package web url (http:// or https://) or scp path
                                (ssh://<server ip/name/< package path>), if url is provided, the
                                package will be installed and setup local repo.
                                In case of scp, user name and password will be read from environment variables
                                SSHUSER - user name to be used during scp, Default: current user
                                SSHPASS - user password to be used during scp

  positional arguments
    What to install             Valid options are contrail-test, contrail-test-ci

 Example:

  # Install contrail-test on a node which doesnt have contrail-install-packages setup (-u is required in this case)

  $ $0 install --test-repo https://github.com/hkumarmk/contrail-test --test-ref working
        --ci-repo https://\$GITUSER:\$GITPASS@github.com/juniper/contrail-test-ci
        -u http://nodei16/contrail-install-packages_2.21-105~juno_all.deb contrail-test

  # Install contrail-test-ci
  $ export SSHUSER=user1 SSHPASS=password
  $ $0 install --test-repo https://github.com/hkumarmk/contrail-test --test-ref working
     --ci-repo https://\$GITUSER:\$GITPASS@github.com/juniper/contrail-test-ci
     -u ssh://nodei16/var/cache/artifacts/contrail-install-packages_2.21-105~juno_all.deb contrail-test-ci

  # Install contrail-test under custom install directory and the machine already have contrail-install-packages setup.

  $ $0 install -i /root/contrail-test contrail-test

EOF
    }

    if ! options=$(getopt -o hi:u: -l install-dir:,help,test-artifact:,ci-artifact:,fab-artifact:,ci-repo:,ci-ref:,test-repo:,test-ref:,contrail-install-package-url:,fab-repo:,fab-ref: -- "$@"); then
# parse error
        usage
        exit 1
    fi
    eval set -- "$options"

    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) usage; exit;;
            --test-repo) CONTRAIL_TEST_REPO=$2; shift;;
            --test-ref) CONTRAIL_TEST_REF=$2; shift;;
            -u|--package-url) CONTRAIL_INSTALL_PACKAGE_URL=$2; shift;;
            --fab-repo) CONTRAIL_FAB_REPO=$2; shift;;
            --fab-ref) CONTRAIL_FAB_REF=$2; shift;;
            --ci-repo) CONTRAIL_TEST_CI_REPO=$2; shift;;
            --ci-ref) CONTRAIL_TEST_CI_REF=$2; shift;;
            --test-artifact) CONTRAIL_TEST_ARTIFACT=$2; shift;;
            --ci-artifact) CONTRAIL_TEST_CI_ARTIFACT=$2; shift;;
            --fab-artifact) CONTRAIL_FAB_ARTIFACT=$2; shift;;
            -i|--install-dir) install_dir=$2; shift;;
            --) :;;
            *) build_type=$1;;
	    esac
	    shift
    done

    install_req_apt

    if [[ -n $CONTRAIL_INSTALL_PACKAGE_URL ]]; then
        if [[ $CONTRAIL_INSTALL_PACKAGE_URL =~ ^http[s]*:// ]]; then
            if try_wget $CONTRAIL_INSTALL_PACKAGE_URL; then
               wget $CONTRAIL_INSTALL_PACKAGE_URL -O /tmp/contrail-install-packages.deb
            else
                echo "ERROR! $CONTRAIL_INSTALL_PACKAGE_URL is not accessible"
                exit 1
            fi
        elif [[ $CONTRAIL_INSTALL_PACKAGE_URL =~ ^ssh:// ]]; then
            server=` echo $CONTRAIL_INSTALL_PACKAGE_URL | sed 's/ssh:\/\///;s|\/.*||'`
            path=`echo $CONTRAIL_INSTALL_PACKAGE_URL |sed -r 's#ssh://[a-zA-Z0-9_\.\-]+##'`
            sshpass -e scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${sshuser_sub}${server}:${path} /tmp/contrail-install-packages.deb
        else
            echo "ERROR, Unknown url format, only http[s], ssh supported"
            exit 1
        fi

        dpkg -i /tmp/contrail-install-packages.deb
        rm -f /tmp/contrail-install-packages.deb
        cd /opt/contrail/contrail_packages/ && ./setup.sh
    fi

    test_dir=${install_dir:-'/opt/contrail-test'}
    if [[ $build_type == 'contrail-test' ]]; then
        ci_dir='/tmp/contrail-test-ci'
        dir=`dirname $test_dir`
        mkdir -p $dir
        if [[ -f $CONTRAIL_TEST_ARTIFACT ]]; then
            tar -C $dir zxf $CONTRAIL_TEST_ARTIFACT
        else
            git clone $CONTRAIL_TEST_REPO $test_dir
            cd $test_dir
            git checkout $CONTRAIL_TEST_REF;
            git reset --hard;
            rm -fr .git
        fi
    elif [[ $build_type == 'contrail-test-ci' ]]; then
        ci_dir=${install_dir:-'/opt/contrail-test'}
    fi

    dir=`dirname $ci_dir`
    mkdir -p $dir
    if [[ -f $CONTRAIL_TEST_CI_ARTIFACT ]]; then
        tar -C $dir zxf $CONTRAIL_TEST_CI_ARTIFACT
    else
        git clone $CONTRAIL_TEST_CI_REPO $ci_dir;
        cd $ci_dir
        git checkout $CONTRAIL_TEST_CI_REF;
        git reset --hard;
        rm -fr .git
    fi

    # Assuming contrail-fabric-utils are isntalled in case /opt/contrail/utils exists
    if [ ! -e /opt/contrail/utils ]; then
        mkdir -p /opt/contrail
        if [[ -f $CONTRAIL_FAB_ARTIFACT ]]; then
            cd /opt/contrail
            tar zxf $CONTRAIL_FAB_ARTIFACT
            mv /opt/contrail/fabric-utils /opt/contrail/utils
        else
            git clone $CONTRAIL_FAB_REPO /opt/contrail/utils
            cd /opt/contrail/utils;
            git checkout $CONTRAIL_FAB_REF;
            git reset --hard;
        fi
    fi

    if [[ ! $test_dir -ef $ci_dir ]]; then
        cp -RTf $ci_dir $test_dir
    fi
    cd $test_dir
    pip install -r requirements.txt
}

## Main starts here

#Distro specific variables
distro

if [[ -n $SSHUSER ]]; then
   sshuser_sub="${SSHUSER}@"
fi
subcommand=$1; shift;
if [[ $subcommand == '-h' || $subcommand == '' ]]; then
    usage
    exit
elif [[ $subcommand == 'docker-build' ]]; then
    docker_build $@
elif [[ $subcommand == 'install' ]]; then
    install $@
else
    echo "Error: '$subcommand' is not a known subcommand." >&2
    echo "       Run '$0 --help' for a list of known subcommands." >&2
    exit 1
fi
