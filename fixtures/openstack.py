import os
from common import log_orig as contrail_logging
from orchestrator import Orchestrator, OrchestratorAuth
import nova_test
import quantum_test
from keystone_tests import KeystoneCommands
from common.openstack_libs import ks_exceptions
from vcenter import VcenterAuth, VcenterOrchestrator

class OpenstackOrchestrator(Orchestrator):

   def __init__(self, inputs, auth_h, region_name=None, vnclib=None, logger=None):
       self.logger = logger or contrail_logging.getLogger(__name__)
       super(OpenstackOrchestrator, self).__init__(inputs, vnclib, self.logger)
       self.auth_h = auth_h
       self.inputs = inputs
       self.quantum_h = None
       self.nova_h = None
       self.vnc_lib = vnclib
       self.region_name = region_name or inputs.region_name if inputs else None
       #for vcenter as compute
       self.vcntr_handle = self.get_vcenter_handle()

   def is_feature_supported(self, feature):
        if self.inputs.vcenter_compute:
            unsupported_features = ['ipv6', 'trans_svc', 'lbaasv1', 'ceilometer']
            return feature not in unsupported_features
        return True

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
           self.quantum_h = quantum_test.QuantumHelper(auth_h=self.auth_h,
                                          region_name=self.region_name,
                                          inputs=self.inputs)
           self.quantum_h.setUp()
       return self.quantum_h

   def get_compute_handler(self):
       if not self.nova_h:
          self.nova_h = nova_test.NovaHelper(inputs=self.inputs,
                                   auth_h=self.auth_h,
                                   region_name=self.region_name)
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

   def __init__(self, username, password, project_name,
                inputs=None, logger=None, auth_url=None, region_name=None,
                certfile=None, keyfile=None, cacert=None, insecure=True, domain_name=None):
       self.inputs = inputs
       self.user = username
       self.passwd = password
       self.project = project_name
       self.logger = logger or contrail_logging.getLogger(__name__)
       if inputs:
           self.auth_url = inputs.auth_url
           self.region_name = inputs.region_name
           if self.inputs.domain_isolation:
               self.domain_name = domain_name or self.inputs.domain_name
           else:
               self.domain_name = domain_name or self.inputs.admin_domain
           self.keystone_certfile = self.inputs.keystonecertfile
           self.keystone_keyfile = self.inputs.keystonekeyfile
           self.certbundle = self.inputs.certbundle
           self.insecure = self.inputs.insecure
       else:
           self.auth_url = auth_url or os.getenv('OS_AUTH_URL')
           self.region_name = region_name or os.getenv('OS_REGION_NAME')
           self.domain_name = domain_name or os.getenv('OS_DOMAIN_NAME')
           self.keystone_certfile = certfile
           self.keystone_keyfile = keyfile
           self.insecure = insecure
           self.certbundle = cacert
       self.reauth()

   def reauth(self):
       self.keystone = KeystoneCommands(username=self.user,
                                        password=self.passwd,
                                        tenant=self.project,
                                        domain_name=self.domain_name,
                                        auth_url=self.auth_url,
                                        insecure=self.insecure,
                                        region_name=self.region_name,
                                        cert=self.keystone_certfile,
                                        key=self.keystone_keyfile,
                                        cacert=self.certbundle,
                                        logger=self.logger)
   def get_domain_id(self, name='Default'):
        return self.keystone.get_domain_id(name)

   def get_project_id(self, name=None, domain_id=None):
       if not name:
           return self.keystone.get_id()
       return self.keystone.get_project_id(name, domain_id)

   def get_session(self):
       return self.keystone.get_session()

   def get_endpoint(self, service, interface='public'):
       return self.keystone.get_endpoint(service, interface)

   def get_token(self):
       return self.keystone.get_token()

   def create_domain(self,domain_name):
       return self.keystone.create_domain(domain_name)
        
   def delete_domain(self, domain_name):
       self.keystone.delete_domain(domain_name)
   
   def update_domain(self,domain_id, domain_name, description, enabled):
       return self.keystone.update_domain(domain_id=domain_id, domain_name=domain_name,
                                    description=description,enabled=enabled)
   
   def get_domain(self,domain_id):
       return self.keystone.get_domain(domain_id=domain_id) 

   def create_project(self, name, domain_name=None):
       return self.keystone.create_project(name, domain_name)

   def delete_project(self, name):
       self.keystone.delete_project(name)

   def delete_user(self, user):
       self.keystone.delete_user(user)

   def create_user(self, user, password, tenant_name=None, domain_name=None):
       try:
           self.keystone.create_user(user,password,email='',
                          tenant_name=tenant_name or self.inputs.stack_tenant,enabled=True,
                          domain_name=domain_name)
       except:
           self.logger.info("%s user already present"%(self.user))

   def create_role(self, role):
       self.keystone.create_role(role)

   def delete_role(self, role):
       self.keystone.delete_role(role)

   def add_user_to_project(self, user, project, role='admin', domain=None):
       try:
           self.keystone.add_user_to_tenant(project, user, role, domain)
       except Exception as e:
           self.logger.info("%s user already added to project"%(user))

   def remove_user_from_project(self, user, role, project):
       try:
           self.keystone.remove_user_role(user, role, project)
       except Exception as e:
           self.logger.exception("%s user already removed from project"%(user))

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
 
   def create_user_group(self,group,domain_name):
       try:
           self.keystone.create_group(group,domain_name)
       except Exception as e:
           self.logger.info("%s user already present"%(group))

   def delete_group(self,name):
        return self.keystone.delete_group(name=name)

   def add_user_to_group(self,user,group):
       try:
           self.keystone.add_user_to_group(user, group)
       except Exception as e:
           self.logger.info("%s user already added to group %s"%(user, group))

   def add_user_group_to_tenant(self, project, group, role='admin', domain=None):
       try:
           self.keystone.add_group_to_tenant(project, group, role='admin', domain=domain)
       except Exception as e:
           self.logger.info("%s group already added to project"%(group,project))


