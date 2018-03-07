ARG REGISTRY_SERVER=localhost:5000
ARG FROM_TAG=latest
FROM $REGISTRY_SERVER/contrail-test-base:$FROM_TAG
ARG INSTALL_PACKAGE=""
ARG REPO_FILE="contrail.repo"
ARG OPENSTACK_VERSION=ocata
ARG OPENSTACK_SUBVERSION=3

COPY requirements.txt *.rpm *.repo /

RUN if [ ! -z "$INSTALL_PACKAGE" ]; then yum localinstall /$INSTALL_PACKAGE; \
    cd /opt/contrail/contrail_packages; ./setup.sh; fi
RUN if [ -f "/$REPO_FILE" ]; then cp /$REPO_FILE /etc/yum.repos.d/; fi
RUN yum install -y \
      https://repos.fedorapeople.org/repos/openstack/openstack-$OPENSTACK_VERSION/rdo-release-$OPENSTACK_VERSION-$OPENSTACK_SUBVERSION.noarch.rpm ; \
    yum install -y \
      python-ceilometerclient python-cinderclient python-barbicanclient \
      python-glanceclient python-heatclient python-novaclient \
      python-selenium python-kubernetes python-contrail contrail-test contrail-fabric-utils && \
    yum --setopt=obsoletes=0 install -y python-neutronclient && \
    yum clean all -y && rm -rf /var/cache/yum

RUN pip install -r /requirements.txt

RUN mkdir -p /contrail-test/images
ENTRYPOINT ["/entrypoint.sh"]

LABEL net.juniper.contrail=test
LABEL net.juniper.node=test
