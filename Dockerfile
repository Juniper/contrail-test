FROM hkumar/ubuntu-14.04.2
MAINTAINER Juniper Contrail <contrail@juniper.net>
ARG CONTRAIL_TEST_CI_REPO=https://github.com/juniper/contrail-test-ci
ARG CONTRAIL_TEST_CI_BRANCH=master
ARG CONTRAIL_INSTALL_PACKAGE_URL
ARG ENTRY_POINT=docker_entrypoint_ci.sh
ARG CONTRAIL_FAB_REPO=https://github.com/juniper/contrail-fabric-utils
ARG CONTRAIL_FAB_BRANCH=master

ENV DEBIAN_FRONTEND=noninteractive

# Just check if $CONTRAIL_INSTALL_PACKAGE_URL is there, if not valid, build will fail
RUN wget -q --spider $CONTRAIL_INSTALL_PACKAGE_URL

# setup contrail-install-packages
RUN wget $CONTRAIL_INSTALL_PACKAGE_URL -O /contrail-install-packages.deb && \
    dpkg -i /contrail-install-packages.deb && \
    rm -f /contrail-install-packages.deb && \
    cd /opt/contrail/contrail_packages/ && ./setup.sh && \
    apt-get install -y python-pip ant python-dev python-novaclient python-neutronclient python-cinderclient \
                    python-contrail patch python-heatclient python-ceilometerclient python-setuptools \
                    libxslt1-dev libz-dev libyaml-dev git python-glanceclient && \
                    rm -fr /opt/contrail/* ; apt-get -y autoremove && apt-get -y clean
RUN git clone $CONTRAIL_TEST_CI_REPO -b $CONTRAIL_TEST_CI_BRANCH /contrail-test
RUN cd /contrail-test && pip install --upgrade -r requirements.txt
RUN git clone $CONTRAIL_FAB_REPO -b $CONTRAIL_FAB_BRANCH /opt/contrail/utils
COPY $ENTRY_POINT /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

