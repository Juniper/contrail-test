
import time
import re
import fixtures
from project_test import *
from tcutils.util import *
from vnc_api.vnc_api import *
from contrail_fixtures import *
import inspect
import threading
import sys

class BGPaasFixture(fixtures.Fixture):
    def __init__(self, connections, inputs=None, service_name=None,project_name=None, asn='64512', cleanup=True, project_obj= None, uuid=None,option="api"):
     
        self.connections = connections
        self.inputs = connections.inputs
        #self.orch = self.connections.get_orch_h()
        self.orch = self.connections.orch #vageesant
        #self.quantum_h = self.connections.get_network_h()
        self.quantum_h = self.connections.quantum_h
        #self.vnc_lib_h = self.connections.get_vnc_lib_h().get_handle()
        self.vnc_lib_h = self.connections.vnc_lib
        if not project_name:
            project_name = self.inputs.project_name
        if not service_name:
            service_name = get_random_name(project_name)
        self.domain_name = self.inputs.domain_name
        self.project_name = project_name
        self.service_name = service_name
        self.asn          = asn
        self.cleanup      = cleanup
        self.option       = option
        self.project_obj  = project_obj
        self.uuid         = uuid
        self.fq_name = [self.domain_name, self.project_name, self.service_name]
        self.service_fq_name = ":".join(self.fq_name)
        self.project_id = self.connections.get_project_id()
        self.logger = self.inputs.logger
        self.already_present = False
        self.lock = threading.Lock()
        self.verify_result = True
        self.verify_not_in_result = True
        self.api_verification_flag = True

    def cleanUp(self):
        super(BGPaasFixture, self).cleanUp()
        self.delete()

    def delete(self):
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
           self.logger.info("Deleting the BGPaas %s" % (self.service_fq_name))
           vmi_refs = self.api_bgpaas_obj.virtual_machine_interface_refs
           for vmi in vmi_refs:
               vmi_obj = self.vnc_lib_h.virtual_machine_interface_read(id=vmi['uuid'])
               self.api_bgpaas_obj.del_virtual_machine_interface(vmi_obj)
           self.vnc_lib_h.bgp_as_a_service_update(self.api_bgpaas_obj)
           self.vnc_lib_h.bgp_as_a_service_delete(id=self.api_bgpaas_obj.get_uuid())
           time.sleep(10)
        else:
           self.logger.info("Skipping Deletion of the BGPaas %s" % (self.service_fq_name))
        
    def verify_if_bgpaas_already_present(self,obj):
        return False

    def get_bgpaas_uuid(self,obj,proj_uuid):
        return 

    def _create_bgpaas_api(self,service_name):

           self.api_bgpaas_obj = BgpAsAService(name=service_name,parent_type='project',fq_name=self.fq_name)
           if not self.verify_if_bgpaas_already_present(self.api_bgpaas_obj):
              self.bgpaas_id = self.vnc_lib_h.bgp_as_a_service_create(self.api_bgpaas_obj)
           else:
              with self.lock:
                   self.logger.info("BGPaas %s already present"%self.service_name)
              self.bgpaas_id = self.get_bgpaas_uuid(self.api_bgpaas_obj,project.project_obj.uuid)
           #self.connections.orch = self.connections.get_orch_h() #vageesant
           self.connections.orch = self.orch
           proj_obj = self.vnc_lib_h.project_read(fq_name=[u'default-domain', u'%s'%self.project_name])
           tenant_id = proj_obj.uuid
           vms_all = self.connections.orch.get_vm_list(project_id=tenant_id) or []
           vmis = []
           for vm in vms_all:
              if re.search('srx.bgp.vm',vm.name):
                 vm_obj = self.vnc_lib_h.virtual_machine_read(id=vm.id)
                 vmis   = vm_obj.get_virtual_machine_interface_back_refs()
                 break
           
           for vmi in vmis:
               vmi_obj  = self.vnc_lib_h.virtual_machine_interface_read(id=vmi['uuid'])
               networks = vmi_obj.get_virtual_network_refs()[0]['to']
               def_dom,t_name,netname = networks
               if re.search('bgp_vn2',netname):
                  inst_ips = vmi_obj.get_instance_ip_back_refs()
                  ip_obj = self.vnc_lib_h.instance_ip_read(id=inst_ips[0]['uuid'])
                  self.api_bgpaas_obj.add_virtual_machine_interface(vmi_obj) # vSRX VMI
                  self.api_bgpaas_obj.set_bgpaas_ip_address(ip_obj.get_instance_ip_address()) # get instance IP attached to vmi.
           self.api_bgpaas_obj.set_autonomous_system(self.asn)
           self.api_bgpaas_obj.set_display_name(self.service_name)
           bgp_addr_fams  = AddressFamilies(['inet','inet6'])
           bgp_sess_attrs = BgpSessionAttributes(address_families=bgp_addr_fams,hold_time=300)
           self.api_bgpaas_obj.set_bgpaas_session_attributes(bgp_sess_attrs)
           self.vnc_lib_h.bgp_as_a_service_update(self.api_bgpaas_obj)

    def setUp(self):
        super(BGPaasFixture,self).setUp()
        with self.lock:
            self.logger.info("Creating bgpaas %s.." % (self.service_name))
        if self.inputs.is_gui_based_config():
           raise Exception('BGPaas: no support for bgpaas creation thru GUI')
        elif (self.option == 'api'):
            self._create_bgpaas_api(self.service_name)
        else:
            self._create_bgpaas_orch()
