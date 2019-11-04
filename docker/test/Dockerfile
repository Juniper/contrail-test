ARG REGISTRY_SERVER=localhost:5000
ARG BASE_TAG=latest
FROM $REGISTRY_SERVER/contrail-test-base:$BASE_TAG
ARG SKU=ocata
ARG OPENSTACK_REPO
ARG CONTRAIL_REPO

COPY requirements*.txt *.rpm /

RUN cp -r /etc/yum.repos.d /etc/yum.repos.d.orig
COPY *.repo prepare_repos.sh /etc/yum.repos.d/

RUN /etc/yum.repos.d/prepare_repos.sh && \
    yum install -y \
      python-ceilometerclient python-cinderclient python-barbicanclient \
      python-glanceclient python-heatclient python-novaclient \
      python-ironicclient \
      python-contrail contrail-test python-setuptools && \
    yum --setopt=obsoletes=0 install -y python-neutronclient && \
    yum clean all -y && rm -rf /var/cache/yum && \
    pip install -r /requirements.txt && \
    pip3 install -r  -r /requirements.txt /requirements3.txt && \
    rm -rf /etc/yum.repos.d && \
    mv /etc/yum.repos.d.orig /etc/yum.repos.d && \
    mkdir -p /contrail-test/images

ENTRYPOINT ["/entrypoint.sh"]

LABEL net.juniper.contrail=test
LABEL net.juniper.node=test
