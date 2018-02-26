FROM 10.84.34.155:5000/ubuntu:16.04
MAINTAINER Contrail Builder <contrail-builder@juniper.net>
ENTRYPOINT ["/bin/bash"]
ENV DEBIAN_FRONTEND=noninteractive
ENV apt_quiet=${apt_quiet:--quiet}
ENV wget=${wget:-wget --quiet}
ENV apt_get="apt-get $apt_quiet --assume-yes "
ENV EXTRAS="libc-dev-bin libc6-dev libexpat1-dev libexpat1 libpython2.7-dev python2.7-dev"
ENV MORE_EXTRAS="vim tcpdump strace"
ENV PACKAGES_REQUIRED_UBUNTU="ant git ipmitool patch python-pip python-requests python-setuptools"
ENV PACKAGES_REQUIRED_UBUNTU_DOCKER_BUILD="python-dev sshpass libyaml-dev libz-dev libxslt1-dev gcc-5-base libgcc-5-dev libstdc++-5-dev"
ENV CIRROS_IMAGE_URL=${CIRROS_IMAGE_URL:-http://10.84.5.120/cs-shared/images/converts/cirros-0.3.0-x86_64-disk.vmdk.gz}
ENV SVC_IN_NET_NAT_URL=${SVC_IN_NET_NAT_URL:-http://10.84.5.120/cs-shared/images/tinycore/tinycore-in-network-nat.qcow2.gz}
ENV SVC_IN_NET_URL=${SVC_IN_NET_URL:-http://10.84.5.120/cs-shared/images/tinycore/tinycore-in-network.qcow2.gz}

RUN $apt_get update ; $apt_get install bzip2 wget sudo perl-modules-5.22
RUN $apt_get install $EXTRAS $MORE_EXTRAS
RUN $apt_get install $PACKAGES_REQUIRED_UBUNTU_DOCKER_BUILD
RUN $apt_get install $PACKAGES_REQUIRED_UBUNTU
RUN $wget --spider $CIRROS_IMAGE_URL
RUN mkdir -p /images && $wget $CIRROS_IMAGE_URL -O /images/cirros-0.3.0-x86_64-disk.vmdk.gz
RUN $wget $SVC_IN_NET_NAT_URL -O /images/tinycore-in-network-nat.qcow2.gz
RUN $wget $SVC_IN_NET_URL -O /images/tinycore-in-network.qcow2.gz
RUN sudo pip install -U pip

