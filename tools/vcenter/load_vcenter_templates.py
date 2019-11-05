from builtins import object
import argparse
import os
import sys
import logging

from common.contrail_test_init import ContrailTestInit
from vcenter import VcenterOrchestrator 

log = logging.getLogger(__name__)

logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
logging.getLogger('paramiko.transport').setLevel(logging.WARN)

class VcenterInfo(object):
    def __init__(self, d):
        self.__dict__ = d

def get_vcenter_server_details(inputs):
    vcenter = {}
    vcenter['server'] = inputs.vcenter_server
    vcenter['port'] = inputs.vcenter_port
    vcenter['user'] = inputs.vcenter_username
    vcenter['password'] = inputs.vcenter_password
    return VcenterInfo(vcenter) 

def main():
    init_obj = ContrailTestInit(sys.argv[1])
    if init_obj.inputs.vcenter_gw_setup or (init_obj.inputs.orchestrator == 'vcenter'):
        vcenter=get_vcenter_server_details(init_obj.inputs)
        vcenter_orch = VcenterOrchestrator(init_obj.inputs, vcenter.server, 
                                           vcenter.port, vcenter.user, 
                                           vcenter.password, 
                                           init_obj.inputs.vcenter_dc,
                                           logger = log 
                                           )
        images = ['ubuntu', 'ubuntu-traffic', 'vcenter_tiny_vm', 'tiny_nat_fw',
                  'tiny_in_net']
        for image in images:
            try:
                vcenter_orch.load_and_register_template(image)
            except:
                log.info('Not able to load template %s' %image)


if __name__ == "__main__":
    main()

