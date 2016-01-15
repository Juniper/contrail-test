from tcutils.util import *
from vnc_api.vnc_api import *
from orchestrator import Orchestrator

class ContrailApi(Orchestrator):

    def __init__(self, inputs, vnc, logger):
        self._inputs = inputs
        self._vnc = vnc
        self._log = logger

    def get_policy(self, fq_name, **kwargs):
        return self._vnc.network_policy_read(fq_name=fq_name)

    def get_floating_ip(self, fip_id, **kwargs):
        fip_obj = self._vnc.floating_ip_read(id=fip_id)
        return fip_obj.get_floating_ip_address()

    def create_floating_ip(self, pool_obj, project_obj, **kwargs):
        fip_obj = FloatingIp(get_random_name('fip'), pool_obj)
        fip_obj.set_project(project_obj)
        self._vnc.floating_ip_create(fip_obj)
        fip_obj = self._vnc.floating_ip_read(fq_name=fip_obj.fq_name)
        return (fip_obj.get_floating_ip_address(), fip_obj.uuid)

    def delete_floating_ip(self, fip_id, **kwargs):
        self._vnc.floating_ip_delete(id=fip_id)

    def assoc_floating_ip(self, fip_id, vm_id, **kwargs):
        fip_obj = self._vnc.floating_ip_read(id=fip_id)
        vm_obj = self._vnc.virtual_machine_read(id=vm_id)
        vmi = vm_obj.get_virtual_machine_interface_back_refs()[0]['uuid']
        vmintf = self._vnc.virtual_machine_interface_read(id=vmi)
        fip_obj.set_virtual_machine_interface(vmintf)
        self._log.debug('Associating FIP:%s with VMI:%s' % (fip_id, vm_id))
        self._vnc.floating_ip_update(fip_obj)
        return fip_obj

    def disassoc_floating_ip(self, fip_id, **kwargs):
        self._log.debug('Disassociating FIP %s' % fip_id)
        fip_obj = self._vnc.floating_ip_read(id=fip_id)
        fip_obj.virtual_machine_interface_refs=None
        self._vnc.floating_ip_update(fip_obj)
        return fip_obj

    def add_security_group(self, vm_id, sg_id, **kwargs):
        sg = self.get_security_group(sg_id)
        vnc_vm = self._vnc.virtual_machine_read(id=vm_id)
        vmis = [vmi['uuid'] for vmi in vnc_vm.get_virtual_machine_interface_back_refs()]
        vmis = [self._vnc.virtual_machine_interface_read(id=vmi) for vmi in vmis]
        for vmi in vmis:
            sg_lst = vmi.get_security_group_refs()
            if not sg_lst:
                sg_lst = []
            sg_lst.append({'uuid': sg.uuid, 'to':sg.fq_name})
            vmi.set_security_group_list(sg_lst)
            self._vnc.virtual_machine_interface_update(vmi)

    def remove_security_group(self, vm_id, sg_id, **kwargs):
        sg = self.get_security_group(sg_id)
        vnc_vm = self._vnc.virtual_machine_read(id=vm_id)
        vmis = [vmi['uuid'] for vmi in vnc_vm.get_virtual_machine_interface_back_refs()]
        vmis = [self._vnc.virtual_machine_interface_read(id=vmi) for vmi in vmis]
        for vmi in vmis:
            sg_lst = vmi.get_security_group_refs()
            if not sg_lst:
                return
            for i, sg_ref in enumerate(sg_lst):
                if sg_ref['uuid'] == sg.uuid:
                     break
            else:
                return
            sg_lst.pop(i)
            vmi.set_security_group_list(sg_lst)
            self._vnc.virtual_machine_interface_update(vmi)

    def create_security_group(self, sg_name, parent_fqname, sg_entries, **kwargs):
        sg = SecurityGroup(sg_name, parent_type='project',
                           fq_name=parent_fqname+[sg_name])
        sg.security_group_entries = PolicyEntriesType(sg_entries)
        self._vnc.security_group_create(sg)
        sg = self._vnc.security_group_read(fq_name=sg.get_fq_name())
        return sg.uuid

    def delete_security_group(self, sg_id, **kwargs):
        self._vnc.security_group_delete(id=sg_id)

    def get_security_group(self, sg_id, **kwargs):
        try:
            return self._vnc.security_group_read(id=sg_id)
        except:
            try:
                return self._vnc.security_group_read(fq_name=sg_id)
            except:
                return None

    def get_security_group_rules(self, sg_id, **kwargs):
        sg_info = self._vnc.security_group_read(id=sg_id)
        return sg_info.get_security_group_entries().exportDict()['PolicyEntriesType']['policy_rule']

    def delete_security_group_rules(self, sg_id, **kwargs):
        sg = self._vnc.security_group_read(id=sg_id)
        sg.set_security_group_entries(None)
        self._vnc.security_group_update(sg)

    def set_security_group_rules(self, sg_id, sg_entries, **kwargs):
        sg = self._vnc.security_group_read(id=sg_id)
        sg.set_security_group_entries(PolicyEntriesType(sg_entries))
        return self._vnc.security_group_update(sg)

    def get_vn_list(self, **kwargs):
       return self._vnc.virtual_networks_list(kwargs['parent_id'])['virtual-networks'] 

    def get_health_check(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        try:
             return self._vnc.service_health_check_read(**kwargs)
        except NoIdError:
             return None

    def create_health_check(self, fq_name, parent_type, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param parent_type : parents type 'project' or 'domain'
            Optional:
            :param enabled : Health check status (True, False)
            :param monitor_type : Health check probe type (PING, HTTP)
            :param delay : delay in secs between probes
            :param timeout : timeout for each probe, must be < delay
            :param max_retries : max no of retries
            :param http_method : One of GET/PUT/PUSH default:GET
            :param url_path : HTTP URL Path
            :param expected_codes : HTTP reply codes
        '''
        name = fq_name[-1]
        prop = ServiceHealthCheckType(**kwargs)
        obj = ServiceHealthCheck(name, parent_type=parent_type, fq_name=fq_name,
                                 service_health_check_properties=prop)
        return self._vnc.service_health_check_create(obj)

    def update_health_check_properties(self, hc_uuid, **kwargs):
        prop = ServiceHealthCheckType(**kwargs)
        hc_obj = self._vnc.service_health_check_read(id=hc_uuid)
        hc_obj.set_service_health_check_properties(prop)
        return self._vnc.service_health_check_update(hc_obj)

    def delete_health_check(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        return self._vnc.service_health_check_delete(**kwargs)

    def assoc_health_check_to_vmi(self, vmi_id, hc_uuid):
        '''
            :param vmi_id : UUID of the VMI object
            :param hc_uuid : UUID of HealthCheck object
        '''
        hc_obj = self._vnc.service_health_check_read(id=hc_uuid)
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        vmi_obj.add_service_health_check(hc_obj)
        return self._vnc.virtual_machine_interface_update(vmi_obj)

    def disassoc_health_check_from_vmi(self, vmi_id, hc_uuid):
        '''
            :param vmi_id : UUID of the VMI object
            :param hc_uuid : UUID of HealthCheck object
        '''
        hc_obj = self._vnc.service_health_check_read(id=hc_uuid)
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        vmi_obj.del_service_health_check(hc_obj)
        return self._vnc.virtual_machine_interface_update(vmi_obj)
