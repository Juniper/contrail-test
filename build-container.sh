#!/bin/bash

REPO_TEMPLATE_FILE="docker/test/contrail.repo.template"
REPO_FILE="docker/test/contrail.repo"
declare -A SUBVERSIONS=([newton]=5 [ocata]=3 [pike]=1)
REGISTRY_SERVER="docker.io/opencontrail"
SKU=""
INSTALL_PKG=""
CONTRAIL_REPO=""
TAG=""

create_repo () {
    local tmpl=$1
    local repo=$2
    template=$(cat $tmpl)
    content=$(eval "echo \"$template\"")
    echo "$content" > $repo
}

download_pkg () {
    local pkg=$1
    local dir=$2
    if [[ $pkg =~ ^http[s]*:// ]]; then
        wget --spider $pkg
        wget $pkg -O $dir
    elif [[ $pkg =~ ^ssh[s]*:// ]]; then
        server=$(echo $pkg | sed 's=scp://==;s|\/.*||')
        path=$(echo $pkg |sed -r 's#scp://[a-zA-Z0-9_\.\-]+##')
        yum install -y sshpass
        sshpass -e scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${sshuser_sub}${server}:${path} $dir
    else
        echo "ERROR, Unknown url format, only http[s], ssh supported" >&2
        exit 1
    fi
}

docker_build () {
  local dir=${1%/}
  local name=$2
  local tag=$3
  local build_arg_opts=''
  local dockerfile=${dir}'/Dockerfile'
  docker_ver=$(docker -v | awk -F' ' '{print $3}' | sed 's/,//g')
  if [[ "$docker_ver" < '17.06' ]] ; then
    cat $dockerfile | sed \
      -e 's/\(^ARG REGISTRY_SERVER=.*\)/#\1/' \
      -e "s/\$REGISTRY_SERVER/$REGISTRY_SERVER/g" \
      -e 's/\(^ARG BASE_TAG=.*\)/#\1/' \
      -e "s/\$BASE_TAG/$BASE_TAG/g" \
      > ${dockerfile}.nofromargs
    dockerfile="${dockerfile}.nofromargs"
  else
    build_arg_opts+=" --build-arg REGISTRY_SERVER=${REGISTRY_SERVER}"
  fi
  build_arg_opts+=" --build-arg BASE_TAG=${BASE_TAG}"
  build_arg_opts+=" --build-arg OPENSTACK_VERSION=${OPENSTACK_VERSION}"
  build_arg_opts+=" --build-arg OPENSTACK_SUBVERSION=${OPENSTACK_SUBVERSION}"
  build_arg_opts+=" --build-arg INSTALL_PACKAGE=${INSTALL_PACKAGE}"
  build_arg_opts+=" --build-arg REPO_FILE=contrail.repo"

  echo "Building test container ${name}:${tag} with opts ${build_arg_opts}"
  docker build -t ${name}:${tag} ${build_arg_opts} -f $dockerfile $dir || exit
  echo "Built test container ${name}:${tag}"
}

docker_build_test () {
    usage () {
    cat <<EOF
Build test container

Usage: $0 test [OPTIONS]

  -h|--help                     Print help message
  --tag           TAG           Docker container tag, default to sku
  --base-tag      BASE_TAG      Specify contrail-base-test container tag to use. Defaults to 'latest'.
  --sku           SKU           Openstack version. Defaults to ocata
  --contrail-repo CONTRAIL_REPO Contrail Repository, optional, if unspecified specify --package-url.
  --package-url   INSTALL_PKG   Contrail-install-packages package url (scp:// or http:// or https://)
                                Optional, if unspecified specify --package-url
                                Local repo will be setup based on install package.
                                In case of scp, specify the below env variables
                                SSHUSER - user name to be used during scp, Default: current user
                                SSHPASS - user password to be used during scp
  --registry-server REGISTRY_SERVER Docker registry hosting the base test container, Defaults to docker.io/opencontrail
  --post          POST          Upload the test container to the registy-server, if specified
EOF
    }
    if ! options=$(getopt -o h -l help,tag:,sku:,contrail-repo:,package-url:,registry-server:,post -- "$@"); then
        usage
        exit 1
    fi
    eval set -- "$options"

    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) usage; exit;;
            --base-tag) BASE_TAG=$2; shift;;
            --tag) TAG=$2; shift;;
            --sku) SKU=$2; shift;;
            --contrail-repo) CONTRAIL_REPO=$2; shift;;
            --package-url) INSTALL_PKG=$2; shift;;
            --registry-server) REGISTRY_SERVER=$2; shift;;
            --post) POST=1; shift;;
	esac
	shift
    done

    if [[ -z $INSTALL_PKG && -z $CONTRAIL_REPO ]]; then
        echo "Need to specify either --package-url or --contrail-repo"; echo
        usage
        exit 1
    fi
    if [[ -z $REGISTRY_SERVER ]]; then
        echo "--registry-server is unspecified, using docker.io/opencontrail"; echo
    fi
    if [[ -z $SKU ]]; then
        echo "SKU(--sku) is unspecified. Assuming ocata"; echo
        SKU=ocata
    fi
    if [[ -z $TAG ]]; then
        echo "TAG(--tag) is unspecified. using $SKU"; echo
        TAG=$SKU
    fi
    if [[ -z $BASE_TAG ]]; then
        echo "BASE_TAG(--base-tag) is unspecified, using 'latest'."; echo
        BASE_TAG='latest'
    fi
    if [[ -n $CONTRAIL_REPO ]]; then
        create_repo $REPO_TEMPLATE_FILE $REPO_FILE
        INSTALL_PACKAGE=""
    else
        download_pkg $INSTALL_PKG docker/test/
        INSTALL_PACKAGE="${INSTALL_PKG##*/}"
    fi
    OPENSTACK_VERSION=$SKU
    OPENSTACK_SUBVERSION="${SUBVERSIONS[$OPENSTACK_VERSION]}"

    docker_build "docker/test" "contrail-test-test" "$TAG"
    if [[ -n $POST ]]; then
        docker tag contrail-test-test:$TAG $REGISTRY_SERVER/contrail-test-test:$TAG
        docker push $REGISTRY_SERVER/contrail-test-test:$TAG
    fi
}

docker_build_base () {
    REGISTRY_SERVER=""
    usage () {
    cat <<EOF
Build base container

Usage: $0 base
  -h|--help                     Print help message
  --registry-server REGISTRY_SERVER Docker registry hosting the base test container, specify if the image needs to be pushed
  --tag             TAG           Docker container tag, default to sku
EOF
    }
    if ! options=$(getopt -o h -l help,registry-server:,tag: -- "$@"); then
        usage
        exit 1
    fi
    eval set -- "$options"
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) usage; exit;;
            --tag) TAG=$2; shift;;
            --registry-server) REGISTRY_SERVER=$2; shift;;
	esac
	shift
    done
    if [[ -z $TAG ]]; then
        echo "TAG(--tag) is unspecified. using latest"; echo
        TAG=latest
    fi
    echo "Building base container"
    docker build -t contrail-test-base:$TAG docker/base || exit
    if [[ -n $REGISTRY_SERVER ]]; then
        docker tag contrail-test-base:$TAG $REGISTRY_SERVER/contrail-test-base:$TAG
        docker push $REGISTRY_SERVER/contrail-test-base:$TAG
    fi
    echo "Built base container contrail-test-base:$TAG"
}

usage () {
    cat <<EOF
Build of contrail test container

Usage: $0 (base|test) [OPTIONS]

Subcommands:

base   Build base test container which is openstack/contrail version agnostic
test   Build contrail test container openstack/contrail version specific

Run $0 <Subcommand> -h|--help to get subcommand specific help

EOF
}

if [[ -n $SSHUSER ]]; then
   sshuser_sub="${SSHUSER}@"
fi
subcommand=$1; shift;
if [[ $subcommand == '-h' || $subcommand == '' ]]; then
    usage
    exit
elif [[ $subcommand == 'test' ]]; then
    docker_build_test $@
elif [[ $subcommand == 'base' ]]; then
    docker_build_base $@
else
    echo "Error: '$subcommand' is not a known subcommand." >&2
    echo "       Run '$0 --help' for a list of known subcommands." >&2
    exit 1
fi
