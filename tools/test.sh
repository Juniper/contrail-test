#!/usr/bin/env bash

TESTBED=${TESTBED:-/opt/contrail/utils/fabfile/testbeds/testbed.py}
CI_REPO=${CI_REPO:-https://github.com/Juniper/contrail-test-ci.git}
CI_REF=${CI_REF:-master}
FAB_REPO=${FAB_REPO:-https://github.com/Juniper/contrail-fabric-utils.git}
FAB_REF=${FAB_REF:-master}

# NOTE: only https urls supported for CI_REPO
# Below variabls also being used
#FAB_ARTIFACT=$FAB_ARTIFACT
#$CONTRAIL_INSTALL_PACKAGE_URL

usage () {
    cat <<EOF
To test contrail-test-ci quickly by creating the container and runnning it against testbed (already provisioned testbed.
EOF

}

if ! options=$(getopt -o ht:u: -l help,testbed:, ci-repo:, ci-ref:, fab-repo:, fab-ref:, package-url:, fab-artifact: -- "$@"); then
# parse error
    usage
    exit 1
fi
eval set -- "$options"

while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit;;
        --ci-repo) CI_REPO=$2; shift;;
        --ci-ref) CI_REF=$2; shift;;
        -u|--package-url) CONTRAIL_INSTALL_PACKAGE_URL=$2; shift;;
        --fab-repo) FAB_REPO=$2; shift;;
        --fab-ref) FAB_REF=$2; shift;;
        --fab-artifact) FAB_ARTIFACT=$2; shift;;
        -t|--testbed) TESTBED=$2; shift;;
        --) :;;
        *) build_type=$1;;
    esac
    shift
done


arr=(`echo $CI_REPO | sed -e 's#http[s]://\(.*\)/\(.*\)/\(.*\)#\1 \2 \3#' -e 's/.git$//'`)

if [[ -n $FAB_ARTIFACT ]]; then
    fab_opt=" --fab-artifact $FAB_ARTIFACT "
else
    fab_opt=" --fab-repo $FAB_REPO --fab-ref $FAB_REF "
fi

if [[ $CONTRAIL_INSTALL_PACKAGE_URL =~ (ssh|http|https)*://.*/contrail-install-packages_[0-9\.\-]+~[a-zA-Z]+_all.deb ]]; then
    contrail_version=`echo ${CONTRAIL_INSTALL_PACKAGE_URL##*/} | sed 's/contrail-install-packages_\([0-9\.\-]*\).*/\1/'`
    openstack_release=`echo ${CONTRAIL_INSTALL_PACKAGE_URL##*/} | sed 's/contrail-install-packages_[0-9\.\-]*~\([a-zA-Z]*\).*/\1/'`
    CONTAINER_TAG=contrail-test-ci-${openstack_release}:${contrail_version}
else
    echo "Bad contrail package url, it should match regex (ssh|http[s])*://.*/contrail-install-packages_[0-9\.\-]+~[a-zA-Z]+_all.deb"
    exit 1
fi

echo "Building the container"
wget https://raw.githubusercontent.com/${arr[1]}/${arr[2]}/${CI_REF}/install.sh -O /tmp/install.sh
bash -x /tmp/install.sh docker-build --fab-artifact $FAB_ARTIFACT $fab_opt --ci-repo $CI_REPO  --ci-ref $CI_REF -u $CONTRAIL_INSTALL_PACKAGE_URL contrail-test-ci; rv=$?
if [ $rv -eq 0 ]; then
    echo "Successfully built the container - $CONTAINER_TAG"
    rm -f /tmp/install.sh
fi

echo "Running the container against testbed - $TESTBED"

wget https://raw.githubusercontent.com/${arr[1]}/${arr[2]}/${CI_REF}/testrunner.sh -O /tmp/testrunner.sh
bash -x /tmp/testrunner.sh run -t $TESTBED $CONTAINER_TAG
rm -f /tmp/testrunner.sh