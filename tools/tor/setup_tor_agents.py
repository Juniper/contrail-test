#
# Copy certs to tor-agents and restart tor-agent services
#
#import os
import sys
#import json
#import ConfigParser
import logging
from fabric.context_managers import settings
from fabric.operations import put

from common.contrail_test_init import ContrailTestInit

logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
logging.getLogger('paramiko.transport').setLevel(logging.WARN)

CONTRAIL_CONF_PATH = '/etc/contrail'

if __name__ == "__main__":
    init_obj = ContrailTestInit(sys.argv[1])
    init_obj.read_prov_file()
    if init_obj.tor_agent_data:
        print 'Configuring any cert files required for tor-agents'
    else:
        print 'No tor-agents in the setup, no cert files will be configured'
        sys.exit(0)

    for ta_host_string, ta_list in init_obj.tor_agent_data.iteritems():
        (user, ip) = ta_host_string.split('@')
        password = init_obj.host_data[ip]['password']
        with settings(host_string=ta_host_string, password=password):
            # Copy cacert.pem
            cacert_file = '%s/ssl/certs/cacert.pem' % (CONTRAIL_CONF_PATH)
            put('tools/tor/cacert.pem', cacert_file)
            for tor_agent in ta_list:
                if tor_agent.get('tor_ovs_protocol') != 'pssl':
                    print 'ToR ovs protocol %s is not pssl' % (
                        tor_agent.get('tor_ovs_protocol'))
                    continue
                tor_agent_id = tor_agent.get('tor_agent_id')

                # Copy sc-cert.pem and sc-privkey.pem
                ta_cert_file = '%s/ssl/certs/tor.%s.cert.pem' % (
                    CONTRAIL_CONF_PATH, tor_agent_id)
                ta_priv_file = '%s/ssl/private/tor.%s.privkey.pem' % (
                    CONTRAIL_CONF_PATH, tor_agent_id)
                put('tools/tor/sc-cert.pem', ta_cert_file)
                put('tools/tor/sc-privkey.pem', ta_priv_file)

                # Restart tor-agent
                init_obj.restart_service('contrail-tor-agent-%s' % (tor_agent_id),
                                         [ip])
        # end for tor_agent
    # end for
