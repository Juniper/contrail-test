ARG REGISTRY_SERVER=localhost:5000
ARG BASE_TAG=latest
FROM $REGISTRY_SERVER/contrail-test-base:$BASE_TAG
ARG REPO_FILE="contrail.repo"
ARG OPENSTACK_VERSION=ocata

COPY requirements.txt *.rpm /

RUN cp -r /etc/yum.repos.d /etc/yum.repos.d.orig
# in case we don't have any repo files, copy Dockerfile too so it won't fail
# yum will ignore Dockerfile during the build
COPY *.repo Dockerfile /etc/yum.repos.d/

RUN yum install -y \
      python-ceilometerclient python-cinderclient python-barbicanclient \
      python-glanceclient python-heatclient python-novaclient \
      python-ironicclient \
      python-contrail contrail-test python-setuptools && \
    yum --setopt=obsoletes=0 install -y python-neutronclient && \
    yum clean all -y && rm -rf /var/cache/yum && \
    pip install -r /requirements.txt && \
    rm -rf /etc/yum.repos.d && \
    mv /etc/yum.repos.d.orig /etc/yum.repos.d && \
    mkdir -p /contrail-test/images

ENTRYPOINT ["/entrypoint.sh"]

LABEL net.juniper.contrail=test
LABEL net.juniper.node=test
