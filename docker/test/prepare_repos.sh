#!/bin/bash -e

cat >/etc/yum.repos.d/contrail.repo <<EOF
[contrail]
name = Contrail repo
baseurl = ${CONTRAIL_REPO}
enabled = 1
gpgcheck = 0
EOF

cat >/etc/yum.repos.d/openstack.repo <<EOF
[centos-openstack-${SKU}]
name = Centos Openstack repo
baseurl = ${OPENSTACK_REPO}
enabled = 1
gpgcheck = 0
EOF
