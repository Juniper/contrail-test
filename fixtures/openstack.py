import os
from common import log_orig as contrail_logging
from orchestrator import Orchestrator, OrchestratorAuth
from nova_test import NovaHelper
from quantum_test import QuantumHelper
from keystone_tests import KeystoneCommands
from common.openstack_libs import ks_exceptions
from vcenter import VcenterAuth, VcenterOrchestrator

class OpenstackOrchestrator(Orchestrator):

   def __init__(self, inputs, username, password, project_name, project_id,
                 vnclib=None, logger=None, auth_server_ip=None):
       self.logger = logger or contrail_logging.getLogger(__name__)
       super(OpenstackOrchestrator, self).__init__(inputs, vnclib, self.logger)
       self.inputs = inputs
       self.quantum_h = None
       self.nova_h = None
       self.username = username
       self.password = password
       self.project_name = project_name
       self.project_id = project_id 
       self.vnc_lib = vnclib
       self.auth_server_ip = auth_server_ip
       self.region_name = inputs.region_name if inputs else None
       if not auth_server_ip:
           self.auth_server_ip = self.inputs.auth_ip
       #for vcenter as compute
       self.vcntr_handle = self.get_vcenter_handle()

   def get_vcenter_handle(self):
       if self.inputs and self.inputs.vcenter_dc:
           vcntr = VcenterOrchestrator(user=self.inputs.vcenter_username,
                                            pwd=self.inputs.vcenter_password,
                                            host=self.inputs.vcenter_server,
                                            port=self.inputs.vcenter_port,
                                            dc_name=self.inputs.vcenter_dc,
                                            vnc=self.vnc_lib,
                                            inputs=self.inputs,
                                            logger=self.logger)
       else:
           vcntr = None
       return vcntr

   def get_network_handler(self):
       if not self.quantum_h: 
           self.quantum_h = QuantumHelper(username=self.username,
                                          password=self.password,
                                          project_id=self.project_id,
                                          inputs=self.inputs,
                                          auth_server_ip=self.auth_server_ip)
           self.quantum_h.setUp()
       return self.quantum_h

   def get_compute_handler(self):
       if not self.nova_h:
          self.nova_h = NovaHelper(inputs=self.inputs,
                                   project_name=self.project_name,
                                   username=self.username,
                                   password=self.password)
       return self.nova_h

   def get_image_account(self, image_name):
       return self.nova_h.get_image_account(image_name)

   def get_image_name_for_zone(self, image_name='ubuntu', zone='nova'):
       return self.nova_h.get_image_name_for_zone(image_name, zone)

   def get_image(self, image_name):
       return self.nova_h.get_image(image_name)

   def get_default_image_flavor(self, image_name):
       return self.nova_h.get_default_image_flavor(image_name)

   def get_flavor(self, flavor):
       return self.nova_h.get_flavor(flavor)

   def get_hosts(self, zone=None):
       if not zone:
          return self.nova_h.get_hosts()
       else:
          return self.nova_h.get_hosts(zone)

   def get_zones(self):
       return self.nova_h.get_zones()

   def create_vm(self, vm_name, image_name, vn_objs, **kwargs):
       vn_ids = [vn['network']['id'] for vn in vn_objs]
       return self.nova_h.create_vm(vm_name=vm_name, image_name=image_name, vn_ids=vn_ids, **kwargs)

   def delete_vm(self, vm_obj, **kwargs):
       return self.nova_h.delete_vm(vm_obj)

   def is_vm_deleted(self, vm_obj, **kwargs):
       return self.nova_h.is_vm_deleted_in_nova_db(vm_obj, self.inputs.openstack_ip)

   def get_host_of_vm(self, vm_obj, **kwargs):
       return self.nova_h.get_nova_host_of_vm(vm_obj)

   def get_networks_of_vm(self, vm_obj, **kwargs):
       vm_obj.get()
       return vm_obj.networks.keys()

   def wait_till_vm_is_active(self, vm_obj, **kwargs):
       return self.nova_h.wait_till_vm_is_active(vm_obj)

   def wait_till_vm_status(self, vm_obj, status, **kwargs):
       return self.nova_h.wait_till_vm_status(vm_obj, status)

   def get_console_output(self, vm_obj, **kwargs):
       return self.nova_h.get_vm_console_output(vm_obj)

   def get_vm_by_id(self, vm_id, **kwargs):
       return self.nova_h.get_vm_by_id(vm_id)

   def get_vm_if_present(self, vm_name=None, **kwargs):
       return  self.nova_h.get_vm_if_present(vm_name=vm_name, **kwargs)

   def get_vm_list(self, name_pattern='', **kwargs):
       return self.nova_h.get_vm_list(name_pattern=name_pattern, **kwargs)

   def get_vm_detail(self, vm_obj, **kwargs):
       return self.nova_h.get_vm_detail(vm_obj)

   def get_vm_ip(self, vm_obj, vn_name=None, **kwargs):
       return self.nova_h.get_vm_ip(vm_obj, vn_name)

   def get_key_file(self):
       return self.nova_h.get_key_file()

   def put_key_file_to_host(self, host_ip):
       self.nova_h.put_key_file_to_host(host_ip)

   def create_vn(self, name, subnets, option='orch', **kwargs):
       return self.quantum_h.create_network(name, subnets, **kwargs)

   def delete_vn(self, vn_obj, option='orch', **kwargs):
       return self.quantum_h.delete_vn(vn_obj['network']['id'])

   def get_vn_id(self, vn_obj, option='orch', **kwargs):
       return vn_obj['network']['id']

   def get_vn_name(self, vn_obj, option='orch', **kwargs):
       return vn_obj['network']['name']

   def get_vn_obj_if_present(self, vn_name, option='orch', **kwargs):
       return self.quantum_h.get_vn_obj_if_present(vn_name, **kwargs)

   def get_vn_obj_from_id(self, vn_id):
       return self.quantum_h.get_vn_obj_from_id(vn_id)

   def get_vn_list(self, **kwargs):
       return super(OpenstackOrchestrator, self).get_vn_list(**kwargs)

   def get_policy(self, fq_name, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).get_policy(fq_name=fq_name, **kwargs)
       return self.quantum_h.get_policy_if_present(fq_name[1], fq_name[2])

   def get_floating_ip(self, fip_id, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).get_floating_ip(fip_id=fip_id, **kwargs)
       fip = self.quantum_h.get_floatingip(fip_id)
       return fip['floating_ip_address']

   def create_floating_ip(self, pool_vn_id, project_obj, option='orch', **kwargs):
       fip_resp = self.quantum_h.create_floatingip(
                        pool_vn_id, project_obj.uuid)
       return (fip_resp['floatingip']['floating_ip_address'],
                        fip_resp['floatingip']['id'])

   def delete_floating_ip(self, fip_id, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).delete_floating_ip(fip_id=fip_id, **kwargs)
       self.quantum_h.delete_floatingip(fip_id)

   def assoc_floating_ip(self, fip_id, vm_id, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).assoc_floating_ip(fip_id=fip_id, vm_id=vm_id, **kwargs)
       update_dict = {}
       update_dict['port_id'] = self.quantum_h.get_port_id(vm_id)
       self.logger.debug('Associating FIP ID %s with Port ID %s' %(fip_id,
                          update_dict['port_id']))
       if update_dict['port_id']:
           fip_resp = self.quantum_h.update_floatingip(fip_id,
                            {'floatingip': update_dict})
           return fip_resp
       else:
           return None

   def disassoc_floating_ip(self, fip_id, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).disassoc_floating_ip(fip_id=fip_id, **kwargs)
       update_dict = {}
       update_dict['port_id'] = None
       self.logger.debug('Disassociating port from FIP ID : %s' %(fip_id))
       fip_resp = self.quantum_h.update_floatingip(fip_id,
                       {'floatingip': update_dict})
       return fip_resp

   def get_image_name_for_zone(self, image_name='ubuntu', zone='nova'):
       return self.nova_h.get_image_name_for_zone(image_name, zone)

   def get_vm_tap_interface(self,obj):
       return obj['name']

   def add_security_group(self, vm_id, sg_id, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).add_security_group(vm_id=vm_id, sg_id=sg_id, **kwargs)
       return self.nova_h.add_security_group(vm_id, sg_id)

   def remove_security_group(self, vm_id, sg_id, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).remove_security_group(vm_id=vm_id, sg_id=sg_id, **kwargs)
       return self.nova_h.remove_security_group(vm_id, sg_id)

   def create_security_group(self, sg_name, parent_fqname, sg_entries, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).create_security_group(sg_name=sg_name,
                                parent_fqname=parent_fqname, sg_entries=sg_entries, **kwargs)
       sg = self.quantum_h.create_security_group(sg_name)
       if not sg:
           self.logger.error("security group creation failed through quantum")
           return False
       self.quantum_h.delete_default_egress_rule(sg['id'])
       self._create_rules_in_quantum(sg['id'],secgrp_rules=sg_entries)
       return sg['id']

   def delete_security_group(self, sg_id, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).delete_security_group(sg_id=sg_id, **kwargs)
       self.quantum_h.delete_security_group(sg_id)

   def get_security_group_rules(self, sg_id, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).get_security_group_rules(sg_id=sg_id, **kwargs)
       sg_info = self.quantum_h.show_security_group(sg_id)
       return sg_info['security_group']['security_group_rules']

   def delete_security_group_rules(self, sg_id, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).delete_security_group_rules(sg_id=sg_id, **kwargs)
       rules = self.quantum_h.list_security_group_rules(tenant_id=self.quantum_h.project_id)
       for rule in rules['security_group_rules']:
           if rule['security_group_id'] == sg_id:
               self.quantum_h.delete_security_group_rule(rule['id'])

   def set_security_group_rules(self, sg_id, sg_entries, option='orch', **kwargs):
       if option == 'contrail':
           return super(OpenstackOrchestrator, self).set_security_group_rules(sg_id=sg_id, sg_entries=sg_entries, **kwargs)
       self.delete_security_group_rules(sg_id, option=option, **kwargs)
       return self._create_rules_in_quantum(sg_id, sg_entries)

   def _create_rules_in_quantum(self, sg_id, secgrp_rules):
       ret = False
       for rule in secgrp_rules:
           remote_group_id=None;remote_ip_prefix=None
           ethertype = None
           if rule['protocol'] == 'any':
               proto = None
           else:
               proto = rule['protocol']
           if 'ethertype' in rule:
               ethertype = rule['ethertype']
           if rule['src_addresses'][0].has_key('security_group'):
               if rule['src_addresses'][0]['security_group'] == 'local':
                   direction = 'egress'
                   port_range_min = rule['src_ports'][0]['start_port']
                   port_range_max = rule['src_ports'][0]['end_port']
               else:
                   if rule['dst_addresses'][0]['security_group'] != None:
                       remote_group_id = self.get_security_group(sg_id=rule['src_addresses'][0]['security_group'].split(':')).uuid
           if rule['dst_addresses'][0].has_key('security_group'):
               if rule['dst_addresses'][0]['security_group'] == 'local':
                   direction = 'ingress'
                   port_range_min = rule['dst_ports'][0]['start_port']
                   port_range_max = rule['dst_ports'][0]['end_port']
               else:
                   if rule['dst_addresses'][0]['security_group'] != None:
                      remote_group_id = self.get_security_group(sg_id=rule['dst_addresses'][0]['security_group'].split(':')).uuid
           if (port_range_min == 0 and port_range_max == -1) \
                    or (port_range_min == 0 and port_range_max == 65535):
               port_range_min = None;port_range_max = None
           if direction == 'ingress':
               try:
                   for addr in rule['src_addresses']:
                       if addr.has_key('subnet') and  addr['subnet'] != None:
                           remote_ip_prefix = addr['subnet']['ip_prefix'] + '/' + str(addr['subnet']['ip_prefix_len'])
                           ret = self.quantum_h.create_security_group_rule(
                                                sg_id,direction=direction,
                                                port_range_min=port_range_min,
                                                port_range_max=port_range_max,
                                                protocol=proto,
                                                remote_group_id=remote_group_id,
                                                remote_ip_prefix=remote_ip_prefix,
                                                ethertype=ethertype)
               except:
                   self.logger.error("error while creating sg rule through quantum")
                   return False
           if direction == 'egress':
               try:
                   for addr in rule['dst_addresses']:
                       if addr.has_key('subnet') and addr['subnet'] != None:
                           remote_ip_prefix = addr['subnet']['ip_prefix'] + '/' + str(addr['subnet']['ip_prefix_len'])
                           ret = self.quantum_h.create_security_group_rule(
                                                sg_id,direction=direction,
                                                port_range_min=port_range_min,
                                                port_range_max=port_range_max,
                                                protocol=proto,
                                                remote_group_id=remote_group_id,
                                                remote_ip_prefix=remote_ip_prefix,
                                                ethertype=ethertype)
               except:
                   self.logger.error("error while creating sg rule through quantum")
                   return False
           #when remote is security group
           if remote_group_id:
               if not self.quantum_h.create_security_group_rule(
                                           sg_id,direction=direction,
                                           port_range_min=port_range_min,
                                           port_range_max=port_range_max,
                                           protocol=proto,
                                           remote_group_id=remote_group_id,
                                           remote_ip_prefix=remote_ip_prefix,
                                           ethertype=ethertype):
                  return False
       return ret

class OpenstackAuth(OrchestratorAuth):

   def __init__(self, user, passwd, project_name,
                inputs=None, logger=None, auth_url=None, region_name=None):
       self.inputs = inputs
       self.user = user
       self.passwd = passwd
       self.project = project_name
       self.logger = logger or contrail_logging.getLogger(__name__)
       self.insecure = bool(os.getenv('OS_INSECURE',True))
       if inputs:
           self.auth_url = inputs.auth_url
           self.region_name = inputs.region_name
       else:
           self.auth_url = auth_url or os.getenv('OS_AUTH_URL')
           self.region_name = region_name or os.getenv('OS_REGION_NAME')
       self.reauth()

   def reauth(self):
       self.keystone = KeystoneCommands(username=self.user,
                                        password=self.passwd,
                                        tenant=self.project,
                                        auth_url=self.auth_url,
                                        insecure=self.insecure,
                                        region_name=self.region_name,
                                        logger=self.logger)

   def get_project_id(self, name=None):
       if not name or name == self.project:
           return self.keystone.get_id()
       return self.keystone.get_project_id(name)

   def create_project(self, name):
       return self.keystone.create_project(name)

   def delete_project(self, name):
       self.keystone.delete_project(name)

   def delete_user(self, user):
       self.keystone.delete_user(user)

   def create_user(self, user, password):
       try:
           self.keystone.create_user(user,password,email='',
                          tenant_name=self.inputs.stack_tenant,enabled=True)
       except:
           self.logger.info("%s user already present"%(self.user))

   def add_user_to_project(self, user, project, role='admin'):
       try:
           self.keystone.add_user_to_tenant(project, user, role)
       except Exception as e:
           self.logger.info("%s user already added to project"%(user))

   def verify_service_enabled(self, service):
       try:
           for svc in self.keystone.services_list():
               if service in svc.name:
                   return True
               else:
                   continue
           return False
       except Exception as e:
           return False

   def get_auth_h(self):
       return self.keystone
