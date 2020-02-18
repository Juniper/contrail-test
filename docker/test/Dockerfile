ARG REGISTRY_SERVER=localhost:5000
ARG BASE_TAG=latest
FROM $REGISTRY_SERVER/contrail-test-base:$BASE_TAG
ARG SKU=ocata
ARG OPENSTACK_REPO
ARG CONTRAIL_REPO
ARG CONTRAIL_BUILD_FROM_SOURCE

COPY requirements*.txt *.rpm /

RUN cp -r /etc/yum.repos.d /etc/yum.repos.d.orig
COPY *.repo prepare_repos.sh /etc/yum.repos.d/

RUN /etc/yum.repos.d/prepare_repos.sh && \
    yum install -y \
      python-ceilometerclient python-cinderclient python-barbicanclient \
      python-glanceclient python-heatclient python-novaclient \
      python-ironicclient \
      python-contrail contrail-test python-setuptools  && \
    if [[ "${CONTRAIL_BUILD_FROM_SOURCE}" == 'true' ]] ; then \
      yum install -y yum-utils && \
      for package in python-contrail python3-contrail contrail-test ; do \
        rpm -Uvh --nodeps $(repoquery --location "${package}"); \
      done; \
    else \
      yum install -y python-contrail python3-contrail contrail-test; \
    fi && \
    yum --setopt=obsoletes=0 install -y python-neutronclient && \
    yum clean all -y && rm -rf /var/cache/yum && \
    pip install -r /requirements.txt && \
    pip3 install -r /requirements.txt -r /requirements3.txt && \
    rm -rf /etc/yum.repos.d && \
    mv /etc/yum.repos.d.orig /etc/yum.repos.d && \
    mkdir -p /contrail-test/images

ENTRYPOINT ["/entrypoint.sh"]

LABEL net.juniper.contrail=test
LABEL net.juniper.node=test
