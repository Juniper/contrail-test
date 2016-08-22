FROM hkumar/ubuntu-14.04.2:latest
MAINTAINER Harish Kumar <hkumar@d4devops.org>

ARG http_proxy
ARG DEBIAN_FRONTEND=noninteractive
ARG RALLYRUNNER_REPO=https://github.com/hkumarmk/rallyrunner.git
ARG RALLYRUNNER_REF=master

# install prereqs
RUN apt-get update && apt-get install --yes wget python

# ubuntu's pip is too old to work with the version of requests we
# require, so get pip with get-pip.py
RUN wget https://bootstrap.pypa.io/get-pip.py && \
  python get-pip.py && \
  rm -f get-pip.py

# create rally user
RUN useradd -u 65500 -m rally
#  ln -s /usr/share/doc/rally /home/rally/rally-docs

# install rally. the COPY command below frequently invalidates
# subsequent cache

RUN wget -q -O- https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh -O /tmp/install_rally.sh && \
 bash /tmp/install_rally.sh --system --verbose --yes \
    --db-name /home/rally/.rally.sqlite && \
  rm -rf /tmp/* && \
  apt-get -y remove \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    python3 \
  && \
  apt-get -y autoremove && \
  apt-get clean

RUN git clone $RALLYRUNNER_REPO /opt/rally; \
    cd /opt/rally ; \
    git checkout $RALLYRUNNER_REF; \
    git reset --hard; \
    rm -fr .git

COPY docker_entrypoint.sh /entrypoint.sh
RUN chmod a+x /entrypoint.sh

VOLUME ["/home/rally"]

WORKDIR /home/rally
USER rally
ENV HOME /home/rally
ENTRYPOINT ["/entrypoint.sh"]
