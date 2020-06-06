from __future__ import print_function
from builtins import str
from builtins import object
import uuid
import logging

from tcutils.util import *
from vnc_api.vnc_api import *
from loadbalancer_vnc_api import *
from future.utils import with_metaclass


class ContrailVncApi(object):

    def __init__(self, vnc, _log=None):
        self._vnc = vnc
        self._log = _log or logging.getLogger(__name__)

    def __getattr__(self, name):
        # Call self._vnc method if no matching method exists
        if hasattr(self._vnc, name):
            return getattr(self._vnc, name)
        else:
            raise AttributeError('%s object has no attribute %s' % (
                                 self.__class__.__name__, name))

    def get_policy(self, fq_name, **kwargs):
        return self._vnc.network_policy_read(fq_name=fq_name)

    def create_project(self, project_name):
        return self._vnc.project_create(project_name)

    def delete_project(self, project_name):
        return self._vnc.project_delete(project_name)

    def read_project_obj(self, project_fq_name=None, project_id=None):
        if project_fq_name:
            return self._vnc.project_read(project_fq_name)
        if project_id:
            return self._vnc.project_read(id=project_id)
    
    def create_multicast_policy(self, name, policyList):

        multicast_policy = MulticastPolicy(name,self.vnc_project)
        add_source_groups = MulticastSourceGroups()

        for policy in policyList:
            add_source_group = MulticastSourceGroup(source_address=policy['source'], group_address=policy['group'], action=policy['action'])
            add_source_groups.add_multicast_source_group(add_source_group)

        multicast_policy.set_multicast_source_groups(add_source_groups)
        uuid = self._vnc.multicast_policy_create(multicast_policy)
        return uuid


    def delete_multicast_policy(self,uuid):
        self._vnc.multicast_policy_delete(id=uuid)

    def create_dci(self, name, lr1_uuid, lr2_uuid):
        dci = DataCenterInterconnect(name)
        lr1_obj = self._vnc.logical_router_read(id=lr1_uuid)
        lr2_obj = self._vnc.logical_router_read(id=lr2_uuid)
        dci.add_logical_router(lr1_obj)
        dci.add_logical_router(lr2_obj)
        return self._vnc.data_center_interconnect_create(dci)

    def delete_dci(self, name=None, **kwargs):
        '''
            :param name : name of the object
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        if name:
            kwargs['fq_name'] = ['default-global-system-config', name]
        self._log.debug('Deleting dci %s' % kwargs)
        return self._vnc.data_center_interconnect_delete(**kwargs)

    @property
    def vnc_project(self):
        '''This method returns the project object
           for this vnc_api object
        '''
        project = self._vnc._tenant_name
        # This may fail for non-default domain
        domain = 'default-domain' if self._vnc._domain_name == 'Default' \
            else self._vnc._domain_name
        fq_name = [domain, project]
        # WA for vcenter/vcenter-gw
        return self.read_project_obj(project_fq_name=fq_name)

    def get_floating_ip(self, fip_id, **kwargs):
        fip_obj = self._vnc.floating_ip_read(id=fip_id)
        return fip_obj.get_floating_ip_address()

    def create_floating_ip(self, pool_obj, project_obj, **kwargs):
        owner = kwargs.get('owner')

        if not pool_obj:
            # Create FIP Poola
            vn_obj = kwargs.get('vn_obj', None)
            fip_pool_name = 'fip_pool'
            pool_obj = FloatingIpPool(fip_pool_name, vn_obj)
            self._vnc.floating_ip_pool_create(pool_obj)

        fip_obj = FloatingIp(get_random_name('fip'), pool_obj)
        fip_obj.set_project(project_obj)
        if owner:
            project_id = owner.replace('-', '')
            fip_obj.set_perms2(PermType2(owner=project_id, owner_access=7))
        self._vnc.floating_ip_create(fip_obj)
        fip_obj = self._vnc.floating_ip_read(fq_name=fip_obj.fq_name)
        return (fip_obj.get_floating_ip_address(), fip_obj.uuid)

    def delete_floating_ip(self, fip_id, **kwargs):
        self._vnc.floating_ip_delete(id=fip_id)

    def assoc_fixed_ip_to_floating_ip(self, fip_id, fixed_ip):
        fip_obj = self._vnc.floating_ip_read(id=fip_id)
        self._log.debug('Associating fixed IP:%s to FIP:%s' %
                        (fixed_ip, fip_id))
        fip_obj.set_floating_ip_fixed_ip_address(fixed_ip)
        self._vnc.floating_ip_update(fip_obj)
        return fip_obj

    def assoc_floating_ip(self, fip_id, vm_id, **kwargs):
        fip_obj = self._vnc.floating_ip_read(id=fip_id)
        try:
          if vm_id:
            vm_obj = self._vnc.virtual_machine_read(id=vm_id)
        except Exception as e:
            self._log.debug(
                "Got exception as %s while reading the vm obj" %
                (e))
        if kwargs.get('vmi_id'):
            vmi = kwargs['vmi_id']
        else:
            vmi = vm_obj.get_virtual_machine_interface_back_refs()[0]['uuid']
        vmintf = self._vnc.virtual_machine_interface_read(id=vmi)
        fip_obj.add_virtual_machine_interface(vmintf)
        self._log.debug('Associating FIP:%s with VMI:%s' % (fip_id, vm_id))
        self._vnc.floating_ip_update(fip_obj)
        return fip_obj

    def disassoc_floating_ip(self, fip_id, **kwargs):
        self._log.debug('Disassociating FIP %s' % fip_id)
        fip_obj = self._vnc.floating_ip_read(id=fip_id)
        fip_obj.virtual_machine_interface_refs = None
        self._vnc.floating_ip_update(fip_obj)
        return fip_obj

    def add_allowed_address_pair(self, prefix, vmi_id=None, si_fq_name=None, left_vn_name=None, prefix_len=32, mac='', mode='active-standby'):
        if si_fq_name is not None:
            si_obj = self._vnc.service_instance_read(fq_name=si_fq_name)
            si_props = si_obj.get_service_instance_properties()
            intf_list = si_props.get_interface_list()
            ip = SubnetType(ip_prefix=prefix, ip_prefix_len=prefix_len)
            aap = AllowedAddressPair(ip=ip, mac=mac)
            aap.set_address_mode(mode)
            aaps = AllowedAddressPairs(allowed_address_pair=[aap])
            for intf in intf_list:
                if intf.virtual_network == left_vn_name:
                    intf.allowed_address_pairs = aaps
                    si_props.set_interface_list(intf_list)
                    si_obj.set_service_instance_properties(si_props)
                    self._vnc.service_instance_update(si_obj)
        else:
            vmi = self._vnc.virtual_machine_interface_read(id=vmi_id)
            ip = SubnetType(ip_prefix=prefix, ip_prefix_len=prefix_len)
            aap = AllowedAddressPair(ip=ip, mac=mac)
            aap.set_address_mode(mode)
            aaps = AllowedAddressPairs(allowed_address_pair=[aap])
            vmi.set_virtual_machine_interface_allowed_address_pairs(aaps)
            self._vnc.virtual_machine_interface_update(vmi)

        # end add_allowed_address_pair


    def get_allowed_address_pair(self, vmi_id):
        vmi = self._vnc.virtual_machine_interface_read(id=vmi_id)
        return vmi.get_virtual_machine_interface_allowed_address_pairs()

    def add_security_group(self, vm_id=None, sg_id=None, **kwargs):
        sg = self.get_security_group(sg_id)
        vmi_id = kwargs.get('vmi_id')
        if vmi_id:
            vmis = [vmi_id]
        else:
            vnc_vm = self._vnc.virtual_machine_read(id=vm_id)
            vmis = [vmi['uuid']
                        for vmi in vnc_vm.get_virtual_machine_interface_back_refs()]
        vmis = [
            self._vnc.virtual_machine_interface_read(
                id=vmi) for vmi in vmis]
        for vmi in vmis:
            sg_lst = vmi.get_security_group_refs()
            if not sg_lst:
                sg_lst = []
            sg_lst.append({'uuid': sg.uuid, 'to': sg.fq_name})
            vmi.set_security_group_list(sg_lst)
            self._vnc.virtual_machine_interface_update(vmi)

    def set_security_group(self, vm_id, sg_ids, **kwargs):
        sgs = [self.get_security_group(sg_id) for sg_id in sg_ids]
        vnc_vm = self._vnc.virtual_machine_read(id=vm_id)
        vmis = [vmi['uuid']
                    for vmi in vnc_vm.get_virtual_machine_interface_back_refs()]
        vmis = [
            self._vnc.virtual_machine_interface_read(
                id=vmi) for vmi in vmis]
        for vmi in vmis:
            sg_lst = []
            for sg in sgs:
                sg_lst.append({'uuid': sg.uuid, 'to': sg.fq_name})
            vmi.set_security_group_list(sg_lst)
            self._vnc.virtual_machine_interface_update(vmi)

    def remove_security_group(self, vm_id=None, sg_id=None, **kwargs):
        sg = self.get_security_group(sg_id)
        vmi_id = kwargs.get('vmi_id')
        if vmi_id:
            vmis = [vmi_id]
        else:
            vnc_vm = self._vnc.virtual_machine_read(id=vm_id)
            vmis = [vmi['uuid']
                        for vmi in vnc_vm.get_virtual_machine_interface_back_refs()]
        vmis = [
            self._vnc.virtual_machine_interface_read(
                id=vmi) for vmi in vmis]
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

    def create_security_group(
            self,
            sg_name,
            parent_fqname,
            sg_entries,
            **kwargs):
        sg = SecurityGroup(sg_name, parent_type='project',
                           fq_name=parent_fqname + [sg_name])
        sg.security_group_entries = PolicyEntriesType(sg_entries)
        self._vnc.security_group_create(sg)
        sg = self._vnc.security_group_read(fq_name=sg.get_fq_name())
        return sg.uuid

    def delete_security_group(self, sg_id, **kwargs):
        self._vnc.security_group_delete(id=sg_id)

    def get_security_group(self, sg_id, **kwargs):
        try:
            return self._vnc.security_group_read(id=sg_id)
        except BaseException:
            try:
                return self._vnc.security_group_read(fq_name=sg_id)
            except BaseException:
                return None

    def get_security_group_rules(self, sg_id, **kwargs):
        sg_info = self._vnc.security_group_read(id=sg_id)
        return sg_info.get_security_group_entries().exportDict()[
            'PolicyEntriesType']['policy_rule']

    def delete_security_group_rules(self, sg_id, **kwargs):
        sg = self._vnc.security_group_read(id=sg_id)
        sg.set_security_group_entries(None)
        self._vnc.security_group_update(sg)

    def set_security_group_rules(self, sg_id, sg_entries, **kwargs):
        sg = self._vnc.security_group_read(id=sg_id)
        sg.set_security_group_entries(PolicyEntriesType(sg_entries))
        return self._vnc.security_group_update(sg)

    def get_vn_list(self, **kwargs):
        return self._vnc.virtual_networks_list(kwargs['parent_id'])[
            'virtual-networks']

    def create_queue(self, name, queue_id, parent_obj=None):
        queue_obj = QosQueue(name=name,
                             qos_queue_identifier=queue_id,
                             parent_obj=parent_obj)
        queue_uuid = self._vnc.qos_queue_create(queue_obj)
        self._log.info('Created Queue %s, UUID %s' %
                       (self._vnc.id_to_fq_name(queue_uuid), queue_uuid))
        return queue_uuid
    # end create_queue

    def delete_queue(self, uuid):
        fq_name = self._vnc.id_to_fq_name(uuid)
        self._log.info('Deleting Queue %s, UUID: %s' % (fq_name, uuid))
        return self._vnc.qos_queue_delete(id=uuid)
    # end delete_queue

    def create_forwarding_class(
            self,
            name,
            fc_id,
            parent_obj=None,
            dscp=None,
            dot1p=None,
            exp=None,
            queue_uuid=None):
        fc_obj = ForwardingClass(name=name,
                                 parent_obj=parent_obj,
                                 forwarding_class_id=fc_id,
                                 forwarding_class_dscp=dscp,
                                 forwarding_class_vlan_priority=dot1p,
                                 forwarding_class_mpls_exp=exp)
        if queue_uuid:
            queue_obj = self._vnc.qos_queue_read(id=queue_uuid)
            fc_obj.add_qos_queue(queue_obj)
        fc_uuid = self._vnc.forwarding_class_create(fc_obj)
        self._log.info('Created FC %s, UUID %s' %
                       (self._vnc.id_to_fq_name(fc_uuid), fc_uuid))
        return fc_uuid
    # end create_forwarding_class

    def update_forwarding_class(self, uuid, fc_id=None, dscp=None, dot1p=None,
                                exp=None, queue_uuid=None):
        self._log.info(
            'Updating FC %s: fc_id: %s, dscp: %s, dot1p: %s, exp: %s,'
            'queue: %s' %
            (uuid, fc_id, dscp, dot1p, exp, queue_uuid))
        fc_obj = self._vnc.forwarding_class_read(id=uuid)
        if fc_id:
            fc_obj.set_forwarding_class_id(fc_id)
        if dscp:
            fc_obj.set_forwarding_class_dscp(dscp)
        if dot1p:
            fc_obj.set_forwarding_class_vlan_priority(dot1p)
        if exp:
            fc_obj.set_forwarding_class_mpls_exp(exp)
        if queue_uuid:
            queue_obj = self._vnc.qos_queue_read(id=queue_uuid)
            fc_obj.set_qos_queue(queue_obj)
        self._vnc.forwarding_class_update(fc_obj)
        return fc_obj
    # end update_forwarding_class

    def delete_forwarding_class(self, uuid):
        fq_name = self._vnc.id_to_fq_name(uuid)
        self._log.info('Deleting FC %s, UUID: %s' % (fq_name, uuid))
        return self._vnc.forwarding_class_delete(id=uuid)
    # end delete_forwarding_class

    def create_qos_config(self, name,
                          parent_obj=None,
                          dscp_mapping=None,
                          dot1p_mapping=None,
                          exp_mapping=None,
                          qos_config_type=None,
                          default_fc_id=0):
        '''
            dscp_mapping , dot1p_mapping and exp_mapping is a
            dict of code_points as key and ForwardingClass id as value

            qos_config_type: One of vhost/fabric/project
        '''

        dscp_entries = self._get_code_point_to_fc_map(dscp_mapping)
        dot1p_entries = self._get_code_point_to_fc_map(dot1p_mapping)
        exp_entries = self._get_code_point_to_fc_map(exp_mapping)

        qos_config_obj = QosConfig(name=name,
                                   parent_obj=parent_obj,
                                   dscp_entries=dscp_entries,
                                   vlan_priority_entries=dot1p_entries,
                                   mpls_exp_entries=exp_entries,
                                   qos_config_type=qos_config_type,
                                   default_forwarding_class_id=default_fc_id)
        uuid = self._vnc.qos_config_create(qos_config_obj)
        self._log.info('Created QosConfig %s, UUID: %s' % (
            self._vnc.id_to_fq_name(uuid), uuid))
        return uuid
    # end create_qos_config

    def set_qos_config_entries(
            self,
            uuid,
            dscp_mapping=None,
            dot1p_mapping=None,
            exp_mapping=None):
        ''' If the user wants to clear the entries, {} needs to be passed
        '''
        self._log.info('Updating qos-config:%s, dscp_mapping: %s,'
                       'dot1p_mapping: %s, exp_mapping: %s' % (
                           uuid, dscp_mapping, dot1p_mapping, exp_mapping))
        qos_config_obj = self._vnc.qos_config_read(id=uuid)
        if dscp_mapping is not None:
            dscp_entries = self._get_code_point_to_fc_map(dscp_mapping)
            qos_config_obj.set_dscp_entries(dscp_entries)
        if dot1p_mapping is not None:
            dot1p_entries = self._get_code_point_to_fc_map(dot1p_mapping)
            qos_config_obj.set_vlan_priority_entries(dot1p_entries)
        if exp_mapping is not None:
            exp_entries = self._get_code_point_to_fc_map(exp_mapping)
            qos_config_obj.set_mpls_exp_entries(exp_entries)
        self._vnc.qos_config_update(qos_config_obj)
        return qos_config_obj
    # end set_qos_config_entries

    def set_default_fc_id(self, uuid, default_fc_id=0):
        ''' Updates the default FC ID associated with this qos config
        '''
        self._log.info('Updating qos-config: Default_FC_Id: %d,'
                       % (default_fc_id))
        qos_config_obj = self._vnc.qos_config_read(id=uuid)
        qos_config_obj.set_default_forwarding_class_id(default_fc_id)
        self._vnc.qos_config_update(qos_config_obj)

    def _get_code_point_to_fc_map(self, mapping_dict=None):
        if not mapping_dict:
            return None
        new_map = QosIdForwardingClassPairs()
        for k, v in mapping_dict.items():
            pair = QosIdForwardingClassPair(k, v)
            new_map.add_qos_id_forwarding_class_pair(pair)
        return new_map
    # end _get_code_point_to_fc_map

    def _add_to_entries(self, qos_config_obj, dscp_mapping=None,
                        dot1p_mapping=None, exp_mapping=None):
        self._log.debug(
            'Adding FC entries to Qos Config %s, dscp:%s, '
            'dot1p: %s, exp: %s' %
            (qos_config_obj.uuid, dscp_mapping, dot1p_mapping, exp_mapping))
        if dscp_mapping:
            for k, v in dscp_mapping.items():
                entry = QosIdForwardingClassPair(k, v)
                qos_config_obj.dscp_entries.add_qos_id_forwarding_class_pair(
                    entry)
                qos_config_obj.set_dscp_entries(qos_config_obj.dscp_entries)
        if dot1p_mapping:
            for k, v in dot1p_mapping.items():
                entry = QosIdForwardingClassPair(k, v)
                qos_config_obj.vlan_priority_entries.add_qos_id_forwarding_class_pair(
                    entry)
                qos_config_obj.set_vlan_priority_entries(
                    qos_config_obj.vlan_priority_entries)
        if exp_mapping:
            for k, v in exp_mapping.items():
                entry = QosIdForwardingClassPair(k, v)
                qos_config_obj.mpls_exp_entries.add_qos_id_forwarding_class_pair(
                    entry)
                qos_config_obj.set_mpls_exp_entries(
                    qos_config_obj.mpls_exp_entries)
        self._vnc.qos_config_update(qos_config_obj)
        return qos_config_obj
    # end _add_to_entries

    def add_qos_config_entries(self, uuid, dscp_mapping=None,
                               dot1p_mapping=None,
                               exp_mapping=None):
        ''' Add one or more code-point to fc mappings to existing qos-config entries
        '''
        qos_config_obj = self._vnc.qos_config_read(id=uuid)
        if dscp_mapping:
            self._add_to_entries(qos_config_obj, dscp_mapping=dscp_mapping)
        if dot1p_mapping:
            self._add_to_entries(qos_config_obj, dot1p_mapping=dot1p_mapping)
        if exp_mapping:
            self._add_to_entries(qos_config_obj, exp_mapping=exp_mapping)
        return qos_config_obj
    # end add_qos_config_entries

    def get_code_point_entry(self, qos_config_obj, dscp=None, dot1p=None,
                             exp=None):
        ''' Return QosIdForwardingClassPair object for the argument
        '''
        entries = None
        value = dscp or dot1p or exp
        if dscp:
            entries = qos_config_obj.dscp_entries
        if dot1p:
            entries = qos_config_obj.vlan_priority_entries
        if exp:
            entries = qos_config_obj.mpls_exp_entries

        if entries:
            pairs = entries.get_qos_id_forwarding_class_pair()
            entry = [x for x in pairs if x.key == value]
            if entry:
                return entry[0]
    # end get_code_point_entry

    def del_qos_config_entry(self, uuid, dscp=None, dot1p=None, exp=None):
        ''' Remove the entry from qos config which has the code-point
        '''
        qos_config_obj = self._vnc.qos_config_read(id=uuid)
        self._log.info('In Qos config %s, Removing entry for key dscp:%s, '
                       'dot1p:%s, exp:%s' % (uuid, dscp, dot1p, exp))

        dscp_entry = self.get_code_point_entry(qos_config_obj, dscp=dscp)
        if dscp_entry:
            qos_config_obj.dscp_entries.delete_qos_id_forwarding_class_pair(
                dscp_entry)
            qos_config_obj.set_dscp_entries(
                self.qos_config_obj.dscp_entries)
        dot1p_entry = get_code_point_entry(qos_config_obj, dot1p=dot1p)
        if dot1p_entry:
            qos_config_obj.dscp_entries.delete_qos_id_forwarding_class_pair(
                dot1p_entry)
            qos_config_obj.set_vlan_priority_entries(
                qos_config_obj.vlan_priority_entries)
        exp_entry = self.get_code_point_entry(qos_config_obj, exp=exp)
        if exp_entry:
            qos_config_obj.dscp_entries.delete_qos_id_forwarding_class_pair(
                exp_entry)
            qos_config_obj.set_mpls_exp_entries(
                qos_config_obj.mpls_exp_entries)
        self._vnc.qos_config_update(qos_config_obj)
        return qos_config_obj
    # end del_qos_config_entry

    def _get_rbac_prop(self, rule_object=None, rule_field=None, perms=None):
        rule_perms = []
        for perm in perms or []:
            role = perm.get('role', '*')
            crud = perm.get('crud', 'CRUD')
            rule_perms.append(RbacPermType(role_name=role, role_crud=crud))
        return RbacRuleType(
            rule_object=rule_object,
            rule_field=rule_field,
            rule_perms=rule_perms)

    def update_api_access_list(self, uuid, rules, delete=False):
        '''
            :param uuid : fqname of the object (list)
            :param rules : dictionary of rule_object, rule_field, list of perms dict('role', 'crud')
                           eg: [{'rule_object': 'virtual_network',
                                 'rule_field': 'route_target_list',
                                 'perms': [{'role': 'admin', 'crud': 'CRUD'},
                                           {'role': '_member_', 'crud': 'R'}]
                                 },
                                 {'rule_object': '*',
                                  'rule_field': '*',
                                  'perms': [{'role': '*', 'crud': 'R'}]
                                 }
                                ]
        '''
        obj = self.get_api_access_list(id=uuid)
        current_prop = obj.get_api_access_list_entries()
        if delete is True:
            # Convert existing rules to dict
            current_rules = list()
            for rule in current_prop.get_rbac_rule() or []:
                perms = list()
                for perm in rule.get_rule_perms() or []:
                    perms.append({'role': perm.get_role_name(),
                                  'crud': perm.get_role_crud()})
                current_rules.append({'rule_object': rule.get_rule_object(),
                                      'rule_field': rule.get_rule_field(),
                                      'perms': perms})
            # Remove the to be removed from the list
            for rule in rules or []:
                current_rules.remove(rule)
            # Readd the rules
            to_add_rules = list()
            for rule in current_rules:
                to_add_rules.append(self._get_rbac_prop(**rule))
            current_prop.set_rbac_rule(to_add_rules)
        else:
            for rule in rules or []:
                current_prop.add_rbac_rule(self._get_rbac_prop(**rule))
        obj.set_api_access_list_entries(current_prop)
        return self._vnc.api_access_list_update(obj)

    def create_api_access_list(self, fq_name, parent_type, rules=None):
        '''
            :param fq_name : fqname of the object (list)
            :param parent_type : parents type 'project' or 'domain'
            Optional:
               :param rules : list of dictionary of rule_object, rule_field, list of perms dict('role', 'crud')
                              eg: [{'rule_object': 'virtual_network',
                                   'rule_field': 'route_target_list',
                                   'perms': [{'role': 'admin', 'crud': 'CRUD'},
                                             {'role': '_member_', 'crud': 'R'}]
                                   },
                                   {'rule_object': '*',
                                    'rule_field': '*',
                                    'perms': [{'role': '*', 'crud': 'R'}]
                                   }
                                  ]
        '''
        name = fq_name[-1]
        prop = list()
        for rule in rules or []:
            prop.append(self._get_rbac_prop(**rule))
        obj = ApiAccessList(
            name,
            parent_type=parent_type,
            fq_name=fq_name,
            api_access_list_entries=RbacRuleEntriesType(
                rbac_rule=prop))
        return self._vnc.api_access_list_create(obj)

    def delete_api_access_list(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        return self._vnc.api_access_list_delete(**kwargs)

    def get_api_access_list(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        return self._vnc.api_access_list_read(**kwargs)

    def _get_obj(self, object_type, uuid):
        api = ('self._vnc.' + object_type + '_read').replace('-', '_')
        return eval(api)(id=uuid)

    def update_obj(self, obj):
        object_type = obj.object_type
        api = 'self._vnc.' + object_type + '_update'
        eval(api)(obj)

    def get_perms2(self, obj):
        '''
            :param object_type : for eg: virtual_network, virtual_machine, etal
            :param obj : object itself
        '''
        perms2 = obj.get_perms2()
        if not perms2:
            obj = self._get_obj(object_type=obj.object_type, uuid=obj.uuid)
            perms2 = obj.get_perms2()
        return perms2

    def set_perms2(self, perms2, obj):
        obj.set_perms2(perms2)
        self.update_obj(obj)

    def set_global_access(self, rwx=7, obj=None, object_type=None, uuid=None):
        if not obj:
            obj = self._get_obj(object_type, uuid)
        perms2 = self.get_perms2(obj)
        perms2.set_global_access(rwx)
        self.set_perms2(perms2, obj)

    def set_share_tenants(
            self,
            tenant,
            tenant_access,
            obj=None,
            object_type=None,
            uuid=None):
        if not obj:
            obj = self._get_obj(object_type, uuid)
        perms2 = self.get_perms2(obj)
        share = ShareType(tenant=tenant, tenant_access=tenant_access)
        perms2.add_share(share)
        self.set_perms2(perms2, obj)

    def set_owner(self, tenant, obj=None, object_type=None, uuid=None):
        if not obj:
            obj = self._get_obj(object_type, uuid)
        perms2 = self.get_perms2(obj)
        perms2.set_owner(tenant)
        self.set_perms2(perms2, obj)

    def update_virtual_router_type(self, name, vrouter_type):
        vr_fq_name = ['default-global-system-config', name]
        vr = self._vnc.virtual_router_read(
            fq_name=vr_fq_name)
        vr.set_virtual_router_type(vrouter_type)
        self._vnc.virtual_router_update(vr)

    def create_virtual_machine(self, vm_uuid=None):
        vm = VirtualMachine()
        if vm_uuid:
            vm.set_uuid(vm_uuid)
        self._vnc.virtual_machine_create(vm)
        return vm
    # end create_virtual_machine

    def delete_virtual_machine(self, vm_uuid):
        self._vnc.virtual_machine_delete(id=vm_uuid)
    # end delete_virtual_machine

    def disable_policy_on_vmi(self, vmi_id, disable=True):
        '''
        Disables the policy on the VMI vmi_id
        '''

        log_str = 'DISABLED' if disable else 'ENABLED'

        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        vmi_obj.set_virtual_machine_interface_disable_policy(disable)
        self._vnc.virtual_machine_interface_update(vmi_obj)
        self._log.info("Policy %s on VMI %s" % (log_str, vmi_id))

        return True
    # end disable_policy_on_vmi

    def add_fat_flow_to_vmi(self, vmi_id, fat_flow_config):
        '''vmi_id: vmi id where Fat flow config is to be added
           fat_flow_config: dictionary of format {'proto':<string>,'port':<int>,
            'ignore_address': <string, source/destination>}
        '''
        source_subnet = None
        destination_subnet = None
        ignore_address = fat_flow_config.get('ignore_address', None)
        source_prefix = fat_flow_config.get('source_prefix', None)
        destination_prefix = fat_flow_config.get('destination_prefix', None)
        source_aggregate_prefix_length = fat_flow_config.get('source_aggregate_prefix_length', None)
        destination_aggregate_prefix_length = fat_flow_config.get('destination_aggregate_prefix_length', None)

        if source_prefix:
            source_subnet = SubnetType(source_prefix[0], source_prefix[1])
        if destination_prefix:
            destination_subnet = SubnetType(destination_prefix[0], destination_prefix[1])
        proto_type = ProtocolType(
            protocol=fat_flow_config['proto'],
            port=fat_flow_config['port'],
            ignore_address=ignore_address,
            source_prefix=source_subnet,
            destination_prefix=destination_subnet,
            destination_aggregate_prefix_length=destination_aggregate_prefix_length,
            source_aggregate_prefix_length=source_aggregate_prefix_length)

        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        fat_config = vmi_obj.get_virtual_machine_interface_fat_flow_protocols()
        if fat_config:
            fat_config.fat_flow_protocol.append(proto_type)
        else:
            fat_config = FatFlowProtocols(fat_flow_protocol=[proto_type])
        vmi_obj.set_virtual_machine_interface_fat_flow_protocols(
            fat_config)
        self._vnc.virtual_machine_interface_update(vmi_obj)
        self._log.info("Fat flow added on VMI %s: %s" % (
            vmi_id, fat_flow_config))

        return True
    # end add_fat_flow_to_vmi

    def delete_all_fat_flow_config_from_vmi(self, vmi_id):
        '''
        Removes the first matching Fat flow configuration
        vmi_id: vmi id
        fat_flow_config: dictionary of format {'proto':<string>,'port':<int>}
        '''
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        fat_config_get = vmi_obj.get_virtual_machine_interface_fat_flow_protocols()
        if fat_config_get:
            for config in fat_config_get.fat_flow_protocol:
                    fat_config_get.fat_flow_protocol.remove(config)
                    vmi_obj.set_virtual_machine_interface_fat_flow_protocols(
                        fat_config_get)
                    self._vnc.virtual_machine_interface_update(vmi_obj)
                    self._log.info(
                        "Fat flow config removed from VMI %s: %s" %
                        (vmi_id, vars(config)))
                    break

        return True
    # delete_all_fat_flow_config_from_vmi

    def remove_fat_flow_on_vmi(self, vmi_id, fat_flow_config):
        '''
        Removes the first matching Fat flow configuration
        vmi_id: vmi id
        fat_flow_config: dictionary of format {'proto':<string>,'port':<int>}
        '''
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        fat_config_get = vmi_obj.get_virtual_machine_interface_fat_flow_protocols()
        if fat_config_get:
            for config in fat_config_get.fat_flow_protocol:
                if config.protocol == fat_flow_config['proto'] and \
                        config.port == fat_flow_config['port'] and \
                        config.ignore_address == fat_flow_config.get('ignore_address'):
                    fat_config_get.fat_flow_protocol.remove(config)
                    vmi_obj.set_virtual_machine_interface_fat_flow_protocols(
                        fat_config_get)
                    self._vnc.virtual_machine_interface_update(vmi_obj)
                    self._log.info(
                        "Fat flow config removed from VMI %s: %s" %
                        (vmi_id, vars(config)))
                    break

        return True
    # end remove_fat_flow_on_vmi

    def add_proto_based_flow_aging_time(self, proto, port=0, timeout=180):
        '''
        Adds protocol based flow aging timeout value.
        proto: <string>, port: <int>, timeout: <int-in-seconds>
        '''

        fq_name = ['default-global-system-config',
                   'default-global-vrouter-config']
        gv_obj = self._vnc.global_vrouter_config_read(fq_name=fq_name)
        flow_aging = gv_obj.get_flow_aging_timeout_list()

        flow_aging_add = FlowAgingTimeout(
            protocol=proto, port=port, timeout_in_seconds=timeout)
        if flow_aging:
            flow_aging.flow_aging_timeout.append(flow_aging_add)
        else:
            flow_aging = FlowAgingTimeoutList([flow_aging_add])
        gv_obj.set_flow_aging_timeout_list(flow_aging)
        self._vnc.global_vrouter_config_update(gv_obj)

        self._log.info(
            'Added global flow aging configuration: %s' %
            (vars(flow_aging_add)))

        return True
    # end add_proto_based_flow_aging_time

    def delete_proto_based_flow_aging_time(self, proto, port=0, timeout=180):
        '''
        Remove protocol based flow aging timeout value.
        proto: <string>, port: <int>, timeout: <int-in-seconds>
        '''

        fq_name = ['default-global-system-config',
                   'default-global-vrouter-config']
        gv_obj = self._vnc.global_vrouter_config_read(fq_name=fq_name)
        flow_aging = gv_obj.get_flow_aging_timeout_list()

        if not flow_aging:
            return
        for aging in flow_aging.flow_aging_timeout:
            values = vars(aging)
            if values['timeout_in_seconds'] == timeout and \
                    values['protocol'] == proto and values['port'] == port:
                flow_aging.flow_aging_timeout.remove(aging)

                gv_obj.set_flow_aging_timeout_list(flow_aging)
                self._vnc.global_vrouter_config_update(gv_obj)

                self._log.info(
                    'Deleted the flow aging configuration: %s' %
                    (vars(aging)))

                return True
    # end delete_proto_based_flow_aging_time

    def create_interface_route_table(self, name, parent_obj=None, prefixes=[]):
        '''
        Create and return InterfaceRouteTable object

        Args:
            prefixes : list of x.y.z.a/mask entries
        '''
        route_table = RouteTableType(name)
        nw_prefixes = [IPNetwork(x) for x in prefixes]
        route_table.set_route([])
        intf_route_table = InterfaceRouteTable(
            interface_route_table_routes=route_table,
            parent_obj=parent_obj,
            name=name)
        if prefixes:
            rt_routes = intf_route_table.get_interface_route_table_routes()
            routes = rt_routes.get_route()
            for prefix in prefixes:
                rt1 = RouteType(prefix=prefix)
                routes.append(rt1)
            intf_route_table.set_interface_route_table_routes(rt_routes)
        uuid = self._vnc.interface_route_table_create(intf_route_table)
        intf_route_table_obj = self._vnc.interface_route_table_read(id=uuid)
        self._log.info(
            'Created InterfaceRouteTable %s(UUID %s), prefixes : %s' %
            (intf_route_table_obj.fq_name, intf_route_table_obj.uuid, prefixes))
        return intf_route_table_obj
    # end create_interface_route_table

    def add_interface_route_table_routes(self, uuid, prefixes=[]):
        '''
        Add prefixes to an existing InterfaceRouteTable object
        Args:
            uuid     : uuid of InterfaceRouteTable
            prefixes : list of x.y.z.a/mask entries
        '''
        intf_route_table = self._vnc.interface_route_table_read(id=uuid)
        nw_prefixes = [IPNetwork(x) for x in prefixes]
        intf_route_table = self._vnc.interface_route_table_read(id=uuid)
        if nw_prefixes:
            rt_routes = intf_route_table.get_interface_route_table_routes()
            routes = rt_routes.get_route()
            for prefix in prefixes:
                rt1 = RouteType(prefix=prefix)
                routes.append(rt1)
                self._log.info('Adding prefix %s to intf route table'
                               '%s' % str((prefix)))
            intf_route_table.set_interface_route_table_routes(rt_routes)
        self._vnc.interface_route_table_update(intf_route_table)
        return intf_route_table
    # end add_interface_route_table_routes

    def delete_interface_route_table_routes(self, uuid, prefixes):
        '''
        Delete prefixes from an existing InterfaceRouteTable object

        Args:
        uuid     : uuid of InterfaceRouteTabl
        prefixes : list of x.y.z.a/mask entries
        '''
        intf_rtb_obj = self._vnc.interface_route_table_read(id=uuid)
        rt_routes = intf_rtb_obj.get_interface_route_table_routes()
        routes = rt_routes.get_route()
        for prefix in prefixes:
            prefix_found = False
            for route in routes:
                if route.prefix == prefix:
                    prefix_found = True
                    routes.remove(route)
                if not prefix_found:
                    self._log.warn('Prefix %s not found in intf route table'
                                   ' %s' % (prefix, self.name))
                else:
                    self._log.info('Prefix %s deleted from intf route table'
                                   ' %s' % (prefix, self.name))
        intf_route_table.set_interface_route_table_routes(rt_routes)
        self._vnc.interface_route_table_update(intf_route_table)
    # end delete_interface_route_table_routes

    def delete_interface_route_table(self, uuid):
        '''
        Delete InterfaceRouteTable object

        Args:
            uuid : UUID of InterfaceRouteTable object
        '''
        self._vnc.interface_route_table_delete(id=uuid)
        self._log.info('Deleted Interface route table %s' % (uuid))
    # end delete_interface_route_table

    def bind_vmi_to_interface_route_table(self, vmi_uuid, intf_rtb):
        '''
        Bind interface route table to a VMI

        intf_rtb : either UUID or InterfaceRouteTable object

        Returns None
        '''
        # TODO
        # Start making different modules for each object and rename methods
        # accordingly
        if is_uuid(intf_rtb):
            intf_rtb_obj = self._vnc.interface_route_table_read(id=intf_rtb)
        elif isinstance(intf_rtb, InterfaceRouteTable):
            intf_rtb_obj = intf_rtb
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_uuid)
        vmi_obj.add_interface_route_table(intf_rtb_obj)
        self._vnc.virtual_machine_interface_update(vmi_obj)
        self._log.info('Added intf route table %s to port %s' % (
            intf_rtb_obj.uuid, vmi_uuid))
    # end bind_vmi_to_interface_route_table

    def unbind_vmi_from_interface_route_table(self, vmi_uuid, intf_rtb):
        '''
        Unbind interface route table from a VMI

        intf_rtb : either UUID or InterfaceRouteTable object

        Returns None
        '''
        if is_uuid(intf_rtb):
            intf_rtb_obj = self._vnc.interface_route_table_read(id=intf_rtb)
        elif isinstance(intf_rtb, InterfaceRouteTable):
            intf_rtb_obj = intf_rtb
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_uuid)
        vmi_obj.del_interface_route_table(intf_rtb_obj)
        self._vnc.virtual_machine_interface_update(vmi_obj)
        self._log.info('Removed intf route table %s from port %s' % (
            intf_rtb_obj.uuid, vmi_uuid))
    # end unbind_vmi_from_interface_route_table

    def create_route_table(
            self,
            name,
            route_table_type='interface',
            parent_obj=None,
            prefixes=[],
            next_hop='',
            next_hop_type='ip-address'):
        '''
        Create and return InterfaceRouteTable or RouteTable object
        Args:
            For interface route table:
            prefixes : list of x.y.z.a/mask entries for Interface route table

            For network route table:
            route_table_type : type of static table, Either interface table or network table
                               This also determines the parameters to be passed.
                               Interface table only needs prefix.
                               Network table would need atleast next-hop ip with prefix
            prefixes : list of x.y.z.a/mask entries for Interface route table
            next_hop_type : Either 'ip-address' or 'service-chain' for Interface route table
            next-hop value : next-hop ip for route table

        '''
        route_table = RouteTableType(name)
        if route_table_type == 'interface':
            nw_prefixes = [IPNetwork(x) for x in prefixes]
            route_table.set_route([])
            intf_route_table = InterfaceRouteTable(
                interface_route_table_routes=route_table,
                parent_obj=parent_obj,
                name=name)
            if prefixes:
                rt_routes = intf_route_table.get_interface_route_table_routes()
                routes = rt_routes.get_route()
                for prefix in prefixes:
                    rt1 = RouteType(prefix=prefix)
                    routes.append(rt1)
                intf_route_table.set_interface_route_table_routes(rt_routes)
            uuid = self._vnc.interface_route_table_create(intf_route_table)
            intf_route_table_obj = self._vnc.interface_route_table_read(
                id=uuid)
            self._log.info(
                'Created InterfaceRouteTable %s(UUID %s), prefixes : %s' %
                (intf_route_table_obj.fq_name, intf_route_table_obj.uuid, prefixes))
            return intf_route_table_obj
        else:
            nw_route_table = RouteTable(name, parent_obj)
            if prefixes:
                for prefix in prefixes:
                    rt1 = RouteType(
                        prefix=prefix,
                        next_hop=next_hop,
                        next_hop_type=next_hop_type)
                    route_table.set_route([rt1])
            nw_route_table.set_routes(route_table)
            uuid = self._vnc.route_table_create(nw_route_table)
            network_route_table_obj = self._vnc.route_table_read(id=uuid)
            self._log.info('Created NetworkRouteTable %s(UUID %s), prefixes : %s' % (
                network_route_table_obj.fq_name, network_route_table_obj.uuid, prefixes))
            return network_route_table_obj

    def bind_network_route_table_to_vn(self, vn_uuid, nw_route_table_obj):
        '''
        Bind network route table to a VN

        nw_route_table_obj : either UUID or RouteTable object

        Returns None
        '''

        if is_uuid(nw_route_table_obj):
            network_route_table_obj = self._vnc.route_table_read(
                id=nw_route_table_obj)
        elif isinstance(nw_route_table_obj, RouteTable):
            network_route_table_obj = nw_route_table_obj

        vn_rt_obj = self._vnc.virtual_network_read(id=vn_uuid)
        vn_rt_obj.add_route_table(network_route_table_obj)
        self._vnc.virtual_network_update(vn_rt_obj)

    # end create_route_table

    def unbind_vn_from_network_route_table(self, vn_uuid, nw_route_table_obj):
        '''
        Unbind network route table from a VN

        nw_route_table_obj : either UUID or RouteTable object

        Returns None
        '''

        if is_uuid(nw_route_table_obj):
            network_route_table_obj = self._vnc.route_table_read(
                id=nw_route_table_obj)
        elif isinstance(nw_route_table_obj, RouteTable):
            network_route_table_obj = nw_route_table_obj
        vn_obj = self._vnc.virtual_network_read(id=vn_uuid)
        vn_obj.del_route_table(network_route_table_obj)
        self._vnc.virtual_network_update(vn_obj)
        self._log.info('Removed network route table %s from network %s' % (
            network_route_table_obj.uuid, vn_uuid))
    # end unbind_vn_from_network_route_table

    def delete_network_route_table(self, uuid):
        '''
        Delete NetworkRouteTable object

        Args:
            uuid : UUID of NetworkRouteTable object
        '''
        self._vnc.route_table_delete(id=uuid)
        self._log.info('Deleted Network route table %s' % (uuid))
    # end delete_network_route_table

    def get_alarm(self, alarm_id):
        try:
            return self._vnc.alarm_read(id=alarm_id)
        except BaseException:
            try:
                return self._vnc.alarm_read(fq_name=alarm_id)
            except BaseException:
                return None
    # end get_alarm

    def create_alarm(
            self,
            name,
            parent_obj,
            alarm_rules,
            alarm_severity,
            uve_keys):
        alarm_obj = Alarm(
            name=name,
            parent_obj=parent_obj,
            alarm_rules=alarm_rules,
            alarm_severity=alarm_severity,
            uve_keys=uve_keys)
        return self._vnc.alarm_create(alarm_obj)
    # end create_alarm

    def update_alarm(self, alarm_obj):
        return self._vnc.alarm_update(alarm_obj)
    # end update_alarm

    def delete_alarm(self, alarm_id):
        self._vnc.alarm_delete(id=alarm_id)
    # end delete_alarm

    def get_global_config_obj(self):
        gsc_id = self._vnc.get_default_global_system_config_id()
        gsc_obj = self._vnc.global_system_config_read(id=gsc_id)
        return gsc_obj
    # end get_global_config_obj

    def get_bgpaas(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        return self._vnc.bgp_as_a_service_read(**kwargs)

    def create_bgpaas(self, fq_name, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
        '''
        name = fq_name[-1]
        kwargs['address_families'] = AddressFamilies(
            kwargs['address_families'])
        autonomous_system = kwargs['autonomous_system']
        bgpaas_ip_address = kwargs['bgpaas_ip_address']
        bgpaas_shared = kwargs['bgpaas_shared']
        local_autonomous_system = kwargs['local_autonomous_system']
        session_attributes = BgpSessionAttributes(**kwargs)
        obj = BgpAsAService(
            name,
            parent_type='project',
            fq_name=fq_name,
            bgpaas_session_attributes=session_attributes,
            autonomous_system=autonomous_system,
            bgpaas_shared=bgpaas_shared,
            bgpaas_ip_address=bgpaas_ip_address,
            local_autonomous_system=local_autonomous_system)
        return self._vnc.bgp_as_a_service_create(obj)

    def update_bgpaas(self, bgpaas_uuid, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
        '''
        bgpaas_obj = self._vnc.bgp_as_a_service_read(id=bgpaas_uuid)
        # Todo: Make a list of all parameters.
        return self._vnc.bgp_as_a_service_update(bgpaas_obj)

    def delete_bgpaas(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        return self._vnc.bgp_as_a_service_delete(**kwargs)

    def attach_shc_to_vmi(self, vmi_uuid, shc_id):
        self._log.info('Attaching HC %s to VMI %s' % (shc_id, vmi_uuid))
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_uuid)
        ref_obj = self._vnc.service_health_check_read(id=shc_id)
        vmi_obj.add_service_health_check(ref_obj)
        return self._vnc.virtual_machine_interface_update(vmi_obj)

    def detach_shc_from_vmi(self, vmi_uuid, shc_id):
        self._log.info(
            'Detaching HC %s from VMI %s' %
            (shc_id, vmi_uuid))
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_uuid)
        ref_obj = self._vnc.service_health_check_read(id=shc_id)
        vmi_obj.del_service_health_check(ref_obj)
        return self._vnc.virtual_machine_interface_update(vmi_obj)

    def attach_vmi_to_bgpaas(self, bgpaas_uuid, vmi_id):
        self._log.info('Attaching VMI %s to BGPaaS %s' % (vmi_id, bgpaas_uuid))
        bgpaas_obj = self._vnc.bgp_as_a_service_read(id=bgpaas_uuid)
        ref_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        bgpaas_obj.add_virtual_machine_interface(ref_obj)
        return self._vnc.bgp_as_a_service_update(bgpaas_obj)

    def detach_vmi_from_bgpaas(self, bgpaas_uuid, vmi_id):
        self._log.info(
            'Detaching VMI %s from BGPaaS %s' %
            (vmi_id, bgpaas_uuid))
        bgpaas_obj = self._vnc.bgp_as_a_service_read(id=bgpaas_uuid)
        ref_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        bgpaas_obj.del_virtual_machine_interface(ref_obj)
        return self._vnc.bgp_as_a_service_update(bgpaas_obj)

    def attach_shc_to_bgpaas(self, bgpaas_uuid, shc_id):
        self._log.info('Attaching HC %s to BGPaaS %s' % (shc_id, bgpaas_uuid))
        bgpaas_obj = self._vnc.bgp_as_a_service_read(id=bgpaas_uuid)
        ref_obj = self._vnc.service_health_check_read(id=shc_id)
        bgpaas_obj.add_service_health_check(ref_obj)
        return self._vnc.bgp_as_a_service_update(bgpaas_obj)

    def detach_shc_from_bgpaas(self, bgpaas_uuid, shc_id):
        self._log.info(
            'Detaching HC %s from BGPaaS %s' %
            (shc_id, bgpaas_uuid))
        bgpaas_obj = self._vnc.bgp_as_a_service_read(id=bgpaas_uuid)
        ref_obj = self._vnc.service_health_check_read(id=shc_id)
        bgpaas_obj.del_service_health_check(ref_obj)
        return self._vnc.bgp_as_a_service_update(bgpaas_obj)

    def get_health_check(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        return self._vnc.service_health_check_read(**kwargs)

    def create_health_check(self, fq_name, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            Optional:
            :param health_check_type : 'link-local' or 'end-to-end'
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
        obj = ServiceHealthCheck(name, parent_type='project', fq_name=fq_name,
                                 service_health_check_properties=prop)
        return self._vnc.service_health_check_create(obj)

    def update_health_check_properties(self, hc_uuid, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            Optional:
            :param health_check_type : 'link-local' or 'end-to-end'
            :param enabled : Health check status (True, False)
            :param monitor_type : Health check probe type (PING, HTTP)
            :param delay : delay in secs between probes
            :param timeout : timeout for each probe, must be < delay
            :param max_retries : max no of retries
            :param http_method : One of GET/PUT/PUSH default:GET
            :param url_path : HTTP URL Path
            :param expected_codes : HTTP reply codes
        '''
        hc_obj = self._vnc.service_health_check_read(id=hc_uuid)
        curr_prop = hc_obj.get_service_health_check_properties()
        for k, v in kwargs.items():
            setattr(curr_prop, k, v)
        hc_obj.set_service_health_check_properties(curr_prop)
        return self._vnc.service_health_check_update(hc_obj)

    def delete_health_check(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        return self._vnc.service_health_check_delete(**kwargs)

    def _update_security_draft_mode(self, flag, project_fqname=None):
        if project_fqname:
            fq_name = project_fqname if isinstance(project_fqname, list)\
                else project_fqname.split(':')
            obj = self._vnc.project_read(fq_name=fq_name)
        else:
            obj = self.read_global_system_config()
        obj.set_enable_security_policy_draft(flag)
        self.update_obj(obj)

    def enable_security_draft_mode(self, project_fqname=None):
        self._update_security_draft_mode(True, project_fqname)

    def disable_security_draft_mode(self, project_fqname=None):
        self._update_security_draft_mode(False, project_fqname)

    def _security_draft_action(self, action, project_fqname=None):
        if project_fqname:
            fqname = project_fqname if isinstance(project_fqname, list)\
                else project_fqname.split(':')
            obj = self._vnc.project_read(fq_name=fqname)
        else:
            obj = self.read_global_system_config()
        if action == 'commit':
            self._vnc.commit_security(obj)
        elif action == 'discard':
            self._vnc.discard_security(obj)
        else:
            raise Exception('action %s not allowed' % action)

    def commit_security_draft(self, project_fqname=None):
        self._security_draft_action('commit', project_fqname)

    def discard_security_draft(self, project_fqname=None):
        self._security_draft_action('discard', project_fqname)

    def list_security_drafts(self, project_fqname=None):
        fq_name = ['draft-policy-management']
        if project_fqname:
            fq_name = list(project_fqname) if isinstance(project_fqname, list)\
                else project_fqname.split(':')
            fq_name.append('draft-policy-management')
        return self._vnc.policy_management_read(
            fq_name=fq_name,
            fields=[
                "application_policy_sets",
                "firewall_policys",
                "firewall_rules",
                "service_groups",
                "address_groups"])

    def create_tag_type(self, name):
        ''' Create a Tag Type
            :param name : name of the tag type
        '''
        self._log.debug('Creating tag type %s' % name)
        obj = TagType(name)
        return self._vnc.tag_type_create(obj)

    def delete_tag_type(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting tag type %s' % kwargs)
        return self._vnc.tag_type_delete(**kwargs)

    def read_tag_type(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading tag type %s' % kwargs)
        return self._vnc.tag_type_read(**kwargs)

    def create_application_policy_set(
            self,
            fq_name,
            parent_type,
            policies=None,
            **kwargs):
        ''' Create a firewall policy
            :param fq_name : name of the APS
            :param parent_type : parent type ('project' or 'policy-management')
            :param policies : Ordered list of dict of firewall policies and seq no
                [{'uuid': uuid, 'seq_no': <int>}]
        '''
        obj = ApplicationPolicySet(
            fq_name[-1], fq_name=fq_name, parent_type=parent_type)
        for policy in policies or []:
            policy_obj = self.read_firewall_policy(id=policy['uuid'])
            seq = FirewallSequence(str(policy['seq_no']))
            obj.add_firewall_policy(policy_obj, seq)
        self._log.debug('Creating application policy set %s' % fq_name)
        return self._vnc.application_policy_set_create(obj)

    def add_firewall_policies(self, uuid, policies):
        obj = self.read_application_policy_set(id=uuid)
        for policy in policies or []:
            seq = FirewallSequence(str(policy['seq_no']))
            policy_obj = self.read_firewall_policy(id=policy['uuid'])
            obj.add_firewall_policy(policy_obj, seq)
            self._log.debug('Adding firewall policy %s to APS %s' % (
                policy_obj.name, obj.name))
        return self._vnc.application_policy_set_update(obj)

    def remove_firewall_policies(self, uuid, policies):
        obj = self.read_application_policy_set(id=uuid)
        for policy in policies or []:
            policy_obj = self.read_firewall_policy(id=policy['uuid'])
            obj.del_firewall_policy(policy_obj)
            self._log.debug('Removing firewall policy %s from APS %s' % (
                policy_obj.name, obj.name))
        return self._vnc.application_policy_set_update(obj)

    def delete_application_policy_set(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting application policy set %s' % kwargs)
        return self._vnc.application_policy_set_delete(**kwargs)

    def read_application_policy_set(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading application policy set %s' % kwargs)
        draft = kwargs.pop('draft', False)
        if draft:
            return self._vnc.application_policy_set_read_draft(**kwargs)
        return self._vnc.application_policy_set_read(**kwargs)

    def create_firewall_policy(
            self,
            fq_name,
            parent_type=None,
            rules=None,
            **kwargs):
        ''' Create a firewall policy
            :param fq_name : name of the FWP
            :param parent_type : one of 'project' or 'policy-management'
            :param rules : Ordered list of dict of firewall rules and seq no
                [{'uuid': rule_uuid, 'seq_no': <int>}]
            :param slo: {'slo_obj': slo obj, 'rate_obj':rate obj}
        '''
        obj = FirewallPolicy(
            fq_name[-1], fq_name=fq_name, parent_type=parent_type)
        for rule in rules or []:
            seq = FirewallSequence(str(rule['seq_no']))
            rule_obj = self.read_firewall_rule(id=rule['uuid'])
            obj.add_firewall_rule(rule_obj, seq)

        slo = kwargs.get('slo') or None
        if slo is not None:
            obj.add_security_logging_object(slo['slo_obj'], slo['rate_obj'])
        self._log.debug('creating firewall policy %s' % fq_name)
        return self._vnc.firewall_policy_create(obj)

    def add_firewall_rules(self, uuid, rules):
        obj = self.read_firewall_policy(id=uuid)
        for rule in rules or []:
            seq = FirewallSequence(str(rule['seq_no']))
            rule_obj = self.read_firewall_rule(id=rule['uuid'])
            self._log.debug('Adding rule %s to policy %s' % (
                rule_obj.name, obj.name))
            obj.add_firewall_rule(rule_obj, seq)
        return self._vnc.firewall_policy_update(obj)

    def remove_firewall_rules(self, uuid, rules):
        obj = self.read_firewall_policy(id=uuid)
        for rule in rules or []:
            rule_obj = self.read_firewall_rule(id=rule['uuid'])
            self._log.debug('Removing rule %s from policy %s' % (
                rule_obj.name, obj.name))
            obj.del_firewall_rule(rule_obj)
        return self._vnc.firewall_policy_update(obj)

    def delete_firewall_policy(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting firewall policy %s' % kwargs)
        return self._vnc.firewall_policy_delete(**kwargs)

    def read_firewall_policy(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading firewall policy %s' % kwargs)
        draft = kwargs.pop('draft', False)
        if draft:
            return self._vnc.firewall_policy_read_draft(**kwargs)
        return self._vnc.firewall_policy_read(**kwargs)

    def _get_fw_endpoint_obj(self, endpoint):
        if not endpoint:
            return None
        subnet = None
        if endpoint.get('subnet'):
            subnet = SubnetType(*endpoint['subnet'].split('/'))
        vn = endpoint.get('virtual_network')
        ag = endpoint.get('address_group')
        tags = endpoint.get('tags', [])
        any = endpoint.get('any', False)
        return FirewallRuleEndpointType(subnet=subnet, virtual_network=vn,
                                        address_group=ag, tags=tags, any=any)

    def update_firewall_rule(
            self,
            uuid,
            action=None,
            direction=None,
            protocol=None,
            sports=None,
            dports=None,
            log=False,
            source=None,
            destination=None,
            match=None,
            service_groups=None,
            **kwargs):
        ''' Update a firewall policy rule
            :param uuid : uuid of the policy rule
            :param action : pass or deny
            :param direction : <> or < or >
            :param protocol : protocol to filter (int or one of icmp/tcp/udp/any)
            :param sports : tuple of start,end port
            :param dports : tuple of start,end port
            :param log : to log flow to analytics
            :param match : list of match tag-types ['deployment', 'site']
            :param source : dict for endpoint
            :param destination : dict for endpoint
            eg: endpoint dict
                {'subnet': '1.1.1.0/24', 'virtual_network': vn_fq_name, 'any': False,
                 'address_group': ag_fq_name,
                 'tags': ['deployment=prod', 'global:site=us'],
                }
        '''
        sg_list = []
        obj = self.read_firewall_rule(id=uuid)
        action_list = obj.get_action_list() or ActionListType()
        if log:
            action_list.log = log
        if action:
            action_list.simple_action = action
        obj.set_action_list(action_list)
        if direction:
            obj.set_direction(direction)
        if protocol or sports or dports:
            service = obj.get_service() or FirewallServiceType()
            if protocol:
                service.protocol = protocol
            if sports:
                service.src_ports = PortType(*sports)
            if dports:
                service.dst_ports = PortType(*dports)
            obj.set_service(service)
        if match:
            match = [] if match == 'None' else match
            obj.set_match_tags(FirewallRuleMatchTagsType(tag_list=match))
        if source:
            obj.set_endpoint_1(self._get_fw_endpoint_obj(source))
        if destination:
            obj.set_endpoint_2(self._get_fw_endpoint_obj(destination))
        for uuid in service_groups or []:
            sg = self.read_service_group(id=uuid)
            sg_list.append({'to': sg.get_fq_name(), 'uuid': sg.uuid})
        if sg_list:
            obj.set_service(None)
        if service_groups is not None:
            obj.set_service_group_list(sg_list)
        self._log.debug('Updating firewall rule %s' % obj.name)
        return self._vnc.firewall_rule_update(obj)

    def create_firewall_rule(
            self,
            fq_name,
            parent_type,
            action=None,
            direction=None,
            service_groups=None,
            protocol=None,
            sports=None,
            dports=None,
            log=False,
            source=None,
            destination=None,
            match=None,
            **kwargs):
        ''' Create a firewall policy rule
            :param fq_name : name of the policy rule
            :param parent_type : parent type ('project' or 'policy-management')
            :param action : pass or deny
            :param direction : <> or < or >
            :param service_groups : list of service_group uuids
            :param protocol : protocol to filter (int or one of icmp/tcp/udp/any)
            :param sports : tuple of start,end port
            :param dports : tuple of start,end port
            :param log : to log flow to analytics
            :param match : list of match tag-types ['deployment', 'site']
            :param source : dict for endpoint
            :param destination : dict for endpoint
            eg: endpoint dict
                {'subnet': '1.1.1.0/24', 'virtual_network': vn_fq_name, 'any': False,
                 'address_group': ag_fq_name,
                 'tags': ['deployment=prod', 'global:site=us'],
                }
        '''
        service = None
        if protocol or sports or dports:
            sports = sports if sports else (0, 65535)
            dports = dports if dports else (0, 65535)
            service = FirewallServiceType(protocol=protocol or 'any',
                                          src_ports=PortType(*sports),
                                          dst_ports=PortType(*dports))
        if match:
            match = [] if match == 'None' else match
            match = FirewallRuleMatchTagsType(tag_list=match)
        obj = FirewallRule(fq_name[-1],
                           fq_name=fq_name,
                           parent_type=parent_type,
                           action_list=ActionListType(simple_action=action,
                                                      log=log),
                           direction=direction,
                           service=service,
                           endpoint_1=self._get_fw_endpoint_obj(source),
                           endpoint_2=self._get_fw_endpoint_obj(destination),
                           match_tags=match)
        for uuid in service_groups:
            obj.add_service_group(self.read_service_group(id=uuid))
        self._log.debug('Creating firewall rule %s' % fq_name)
        return self._vnc.firewall_rule_create(obj)

    def add_service_group(self, uuid, service_groups):
        obj = self.read_firewall_rule(id=uuid)
        for uuid in service_groups:
            sg_obj = self.read_service_group(id=uuid)
            obj.add_service_group(sg_obj)
            self._log.debug(
                'Add Service Group %s to Rule %s' %
                (sg_obj.name, obj.name))
        return self._vnc.firewall_rule_update(obj)

    def remove_service_group(self, uuid, service_groups):
        obj = self.read_firewall_rule(id=uuid)
        for uuid in service_groups:
            sg_obj = self.read_service_group(id=uuid)
            obj.del_service_group(sg_obj)
            self._log.debug(
                'Remove Service Group %s from Rule %s' %
                (sg_obj.name, obj.name))
        return self._vnc.firewall_rule_update(obj)

    def delete_firewall_rule(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting firewall rule %s' % kwargs)
        return self._vnc.firewall_rule_delete(**kwargs)

    def read_firewall_rule(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading firewall rule %s' % kwargs)
        draft = kwargs.pop('draft', False)
        if draft:
            return self._vnc.firewall_rule_read_draft(**kwargs)
        return self._vnc.firewall_rule_read(**kwargs)

    def create_service_group(self, fq_name, parent_type, services, **kwargs):
        ''' Create a service group
            :param fq_name : name of the SG
            :param parent_type : parent type ('project' or 'policy-management')
            :param services : List of services tuple
                eg: [(<protocol>, (<sp_start, sp_end>), (<dp_start, dp_end>))]
        '''
        services_list = list()
        for service in services or []:
            sports = PortType(*service[1])
            dports = PortType(*service[2])
            services_list.append(
                FirewallServiceType(
                    protocol=service[0],
                    src_ports=sports,
                    dst_ports=dports))
        services = FirewallServiceGroupType(firewall_service=services_list)
        obj = ServiceGroup(fq_name[-1],
                           fq_name=fq_name,
                           parent_type=parent_type,
                           service_group_firewall_service_list=services,
                           **kwargs)
        self._log.debug('Creating service group %s' % fq_name)
        return self._vnc.service_group_create(obj)

    def update_service_group(self, uuid, services, delete=False):
        ''' Update a service group
            :param uuid : uuid of the service group
            :param services : List of services tuple
                eg: [(<protocol>, (<sp_start, sp_end>), (<dp_start, dp_end>))]
        '''
        sg = self.read_service_group(id=uuid)
        curr_services = list()
        svcs = sg.get_service_group_firewall_service_list() or FirewallServiceGroupType()
        for service in svcs.firewall_service or []:
            sports = (service.src_ports.start_port, service.src_ports.end_port)
            dports = (service.dst_ports.start_port, service.dst_ports.end_port)
            curr_services.append((service.protocol, sports, dports))
        if delete:
            services = set(curr_services) - set(services)
        else:
            services = set(curr_services).union(services)
        services_list = list()
        for service in services or []:
            sports = PortType(*service[1])
            dports = PortType(*service[2])
            services_list.append(FirewallServiceType(
                protocol=service[0], src_ports=sports, dst_ports=dports))
        sg.set_service_group_firewall_service_list(
            FirewallServiceGroupType(services_list))
        self._log.debug('Updating service group %s' % sg.name)
        return self._vnc.service_group_update(sg)

    def delete_service_group(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting service group %s' % kwargs)
        return self._vnc.service_group_delete(**kwargs)

    def read_service_group(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading service group %s' % kwargs)
        draft = kwargs.pop('draft', False)
        if draft:
            return self._vnc.service_group_read_draft(**kwargs)
        return self._vnc.service_group_read(**kwargs)

    def create_address_group(self, fq_name, parent_type, subnets, **kwargs):
        ''' Create a address group
            :param fq_name : name of the AG
            :param parent_type : parent type ('project' or 'policy-management')
            :param subnets : List of Subnets (in IPAddress/Prefix format)
        '''
        subnets = [SubnetType(ip_prefix=subnet.split('/')[0],
                              ip_prefix_len=int(subnet.split('/')[1]))
                   for subnet in subnets]
        obj = AddressGroup(fq_name[-1],
                           fq_name=fq_name,
                           parent_type=parent_type,
                           address_group_prefix=SubnetListType(subnet=subnets),
                           **kwargs)
        self._log.debug('Creating address group %s' % fq_name)
        return self._vnc.address_group_create(obj)

    def update_address_group(self, uuid, subnets, delete=False):
        '''
            :param uuid : uuid of the object
            :param subnets : List of Subnets (in IPAddress/Prefix format)
        '''
        obj = self.read_address_group(id=uuid)
        prefixes = obj.get_address_group_prefix() or SubnetListType()
        curr_subnet = ['%s/%s' % (subnet.ip_prefix, subnet.ip_prefix_len)
                       for subnet in prefixes.subnet or []]
        if delete:
            subnets = set(curr_subnet) - set(subnets)
        else:
            subnets = set(curr_subnet).union(subnets)
        to_update_subnets = [
            SubnetType(
                ip_prefix=subnet.split('/')[0],
                ip_prefix_len=int(
                    subnet.split('/')[1])) for subnet in subnets]
        obj.set_address_group_prefix(SubnetListType(subnet=to_update_subnets))
        self._log.debug('Updating address group %s' % obj.name)
        return self._vnc.address_group_update(obj)

    def delete_address_group(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting address group %s' % kwargs)
        return self._vnc.address_group_delete(**kwargs)

    def read_address_group(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading address group %s' % kwargs)
        draft = kwargs.pop('draft', False)
        if draft:
            return self._vnc.address_group_read_draft(**kwargs)
        return self._vnc.address_group_read(**kwargs)

    def check_and_create_tag(self, fq_name, tag_type,
                             tag_value, parent_type=None, **kwargs):
        try:
            return self.create_tag(fq_name, tag_type, tag_value,
                                   parent_type, **kwargs)
        except RefsExistError:
            fqname = ['%s=%s' % (tag_type, tag_value)]
            if parent_type == 'project':
                fqname = fq_name[:-1] + fqname
            return self.read_tag(fq_name=fqname).uuid

    def create_tag(
            self,
            fq_name,
            tag_type,
            tag_value,
            parent_type=None,
            **kwargs):
        ''' Create a Tag
            :param fq_name : fqname of the Tag
            :param parent_type : parent type ('project' or None for global tag)
            :param tag_type : tag_type (Application/Tier/Site etal)
            :param tag_value : string representing the tag
        '''
        obj = Tag(fq_name[-1], tag_type_name=tag_type, tag_value=tag_value,
                  parent_type=parent_type, fq_name=fq_name, **kwargs)
        self._log.debug('Creating tag %s' % fq_name)
        return self._vnc.tag_create(obj)

    def delete_tag(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting tag %s' % kwargs)
        return self._vnc.tag_delete(**kwargs)

    def read_tag(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading tag %s' % kwargs)
        return self._vnc.tag_read(**kwargs)

    def add_tag(self, tag, obj=None, object_type=None, uuid=None):
        ''' add tag to an object
            :param tag : uuid of the tag
            :param obj : object to which tag has to be set (optional)
            :param object_type : object_type to which tag has to be set (optional)
            :param uuid : uuid of object to which tag has to be set (optional)
             either of obj or (object_type and uuid) has to be specified
        '''
        tag = self.read_tag(id=tag)
        if not obj:
            obj = self._get_obj(object_type, uuid)
        obj.add_tag(tag)
        self._log.debug('Adding tag %s to obj %s' % (tag.get_fq_name_str(),
                                                     obj.get_fq_name_str()))
        self.update_obj(obj)

    def add_labels(self, tags, is_global=False, obj=None,
                   object_type=None, uuid=None):
        ''' add labels to an object
            :param tags : list of tags
            :param obj : object to which tag has to be set (optional)
            :param object_type : object_type to which tag has to be set (optional)
            :param uuid : uuid of object to which tag has to be set (optional)
             either of obj or (object_type and uuid) has to be specified
        '''
        if not obj:
            obj = self._get_obj(object_type, uuid)
        tags_dict = dict()
        tags_dict['label'] = {'is_global': is_global, 'add_values': tags}
        self._log.debug('Adding labels %s to obj %s' % (tags,
                                                        obj.get_fq_name_str()))
        return self._vnc.set_tags(obj, tags_dict)

    def delete_labels(self, tags, is_global=False,
                      obj=None, object_type=None, uuid=None):
        ''' delete labels from an object
            :param tags : list of tags
            :param obj : object to which tag has to be set (optional)
            :param object_type : object_type to which tag has to be set (optional)
            :param uuid : uuid of object to which tag has to be set (optional)
             either of obj or (object_type and uuid) has to be specified
        '''
        if not obj:
            obj = self._get_obj(object_type, uuid)
        tags_dict = dict()
        tags_dict['label'] = {'is_global': is_global, 'delete_values': tags}
        self._log.debug(
            'Deleting labels %s from obj %s' %
            (tags, obj.get_fq_name_str()))
        return self._vnc.set_tags(obj, tags_dict)

    def set_tag(self, tag_type, tag_value, is_global=False,
                obj=None, object_type=None, uuid=None):
        ''' set tag to an object
            :param tag_type : tag_type (Application/Tier/Site etal)
            :param tag_value : string representing the tag
            :param obj : object to which tag has to be set (optional)
            :param object_type : object_type to which tag has to be set (optional)
            :param uuid : uuid of object to which tag has to be set (optional)
             either of obj or (object_type and uuid) has to be specified
        '''
        if not obj:
            obj = self._get_obj(object_type, uuid)
        self._log.debug(
            'Adding %s tag %s:%s to obj %s' %
            ('global' if is_global else 'local', tag_type, tag_value, obj.name))
        return self._vnc.set_tag(obj, tag_type, tag_value, is_global)

    def unset_tag(self, tag_type, obj=None, object_type=None, uuid=None):
        ''' unset tag of an object
            :param tag_type : tag_type (Application/Tier/Site etal)
            :param obj : object to which tag has to be set (optional)
            :param object_type : object_type to which tag has to be set (optional)
            :param uuid : uuid of object to which tag has to be set (optional)
             either of obj or (object_type and uuid) has to be specified
        '''
        if not obj:
            obj = self._get_obj(object_type, uuid)
        self._log.debug(
            'Deleting tag-type %s from obj %s' %
            (tag_type, obj.name))
        return self._vnc.unset_tag(obj, tag_type)

    def get_tags(self, obj=None, object_type=None, uuid=None):
        ''' get tags associated to an object
            :param obj : object to which tag has to be set (optional)
            :param object_type : object_type to which tag has to be set (optional)
            :param uuid : uuid of object to which tag has to be set (optional)
             either of obj or (object_type and uuid) has to be specified
        '''
        if not obj:
            obj = self._get_obj(object_type, uuid)
        self._log.debug('fetching tags for obj %s' % obj.name)
        tag_refs = obj.get_tag_refs()
        if tag_refs:
            return [self._vnc.tag_read(id=tag['uuid']) for tag in tag_refs]
        else:
            return []

    def read_virtual_router(self, compute_name):
        fq_name = ['default-global-system-config', compute_name]
        return self._vnc.virtual_router_read(fq_name=fq_name)

    def enable_datapath_encryption(self, vrouters=None):
        gr_obj = self.read_global_vrouter_config()
        gr_obj.encryption_mode = 'all'
        vr_endpoints = gr_obj.get_encryption_tunnel_endpoints() or \
            EncryptionTunnelEndpointList()
        for vrouter in vrouters or list():
            vr_endpoints.add_endpoint(EncryptionTunnelEndpoint(vrouter))
        gr_obj.set_encryption_tunnel_endpoints(vr_endpoints)
        self._vnc.global_vrouter_config_update(gr_obj)

    def disable_datapath_encryption(self):
        gr_obj = self.read_global_vrouter_config()
        gr_obj.encryption_mode = None
        gr_obj.set_encryption_tunnel_endpoints(list())
        self._vnc.global_vrouter_config_update(gr_obj)

    def add_vrouter_to_encryption(self, vrouters):
        self.enable_datapath_encryption(vrouters)

    def delete_vrouter_from_encryption(self, vrouters):
        gr_obj = self.read_global_vrouter_config()
        vr_endpoints = gr_obj.get_encryption_tunnel_endpoints()
        for vrouter in vrouters:
            vr_endpoints.delete_endpoint(EncryptionTunnelEndpoint(vrouter))
        gr_obj.set_encryption_tunnel_endpoints(vr_endpoints)
        self._vnc.global_vrouter_config_update(gr_obj)

    def get_encap_priority(self):
        gr_obj = self.read_global_vrouter_config()
        encap = gr_obj.get_encapsulation_priorities() or EncapsulationPrioritiesType()
        return encap.get_encapsulation()

    def set_encap_priority(self, encaps):
        gr_obj = self.read_global_vrouter_config()
        encap = EncapsulationPrioritiesType(encapsulation=encaps)
        gr_obj.set_encapsulation_priorities(encap)
        self._vnc.global_vrouter_config_update(gr_obj)

    def delete_encap_priority(self):
        self.set_encap_priority(list())

    def assoc_intf_rt_table_to_si(
            self,
            si_fq_name,
            intf_rt_table_uuid,
            intf_type):
        '''
            :param si_uuid : UUID of the Service Instance object
            :param intf_table_uuid : UUID of Interface Route Table object
        '''
        intf_rt_table_obj = self._vnc.interface_route_table_read(
            id=intf_rt_table_uuid)
        si_obj = self._vnc.service_instance_read(fq_name=si_fq_name)
        intf_rt_table_obj.add_service_instance(
            si_obj, ServiceInterfaceTag(interface_type=intf_type))
        return self._vnc.interface_route_table_update(intf_rt_table_obj)

    def disassoc_intf_rt_table_from_si(self, si_fq_name, intf_rt_table_uuid):
        '''
            :param si_uuid : UUID of the Service Instance object
            :param intf_table_uuid : UUID of Interface Route Table object
        '''
        intf_rt_table_obj = self._vnc.interface_route_table_read(
            id=intf_rt_table_uuid)
        si_obj = self._vnc.service_instance_read(fq_name=si_fq_name)
        intf_rt_table_obj.del_service_instance(si_obj)
        return self._vnc.interface_route_table_update(intf_rt_table_obj)

    def assoc_health_check_to_si(self, si_fq_name, hc_uuid, intf_type):
        '''
            :param si_uuid : UUID of the Service Instance object
            :param hc_uuid : UUID of HealthCheck object
        '''
        hc_obj = self._vnc.service_health_check_read(id=hc_uuid)
        si_obj = self._vnc.service_instance_read(fq_name=si_fq_name)
        hc_obj.add_service_instance(
            si_obj, ServiceInterfaceTag(interface_type=intf_type))
        return self._vnc.service_health_check_update(hc_obj)

    def disassoc_health_check_from_si(self, si_fq_name, hc_uuid):
        '''
            :param si_uuid : UUID of the Service Instance object
            :param hc_uuid : UUID of HealthCheck object
        '''
        hc_obj = self._vnc.service_health_check_read(id=hc_uuid)
        si_obj = self._vnc.service_instance_read(fq_name=si_fq_name)
        hc_obj.del_service_instance(si_obj)
        return self._vnc.service_health_check_update(hc_obj)

    def create_bd(self, bd_name=None, parent_obj=None, cleanup=True, **kwargs):
        '''
            Creates a bridge domain
        '''
        if not bd_name:
            bd_name = get_random_name('bd')
        mac_learning_enabled = kwargs.get('mac_learning_enabled', None)
        mac_limit_control = kwargs.get('mac_limit_control', None)
        mac_move_control = kwargs.get('mac_move_control', None)
        mac_aging_time = kwargs.get('mac_aging_time', 300)
        isid = kwargs.get('isid', None)

        bd_obj = BridgeDomain(name=bd_name,
                              parent_obj=parent_obj,
                              mac_learning_enabled=mac_learning_enabled,
                              mac_limit_control=mac_limit_control,
                              mac_move_control=mac_move_control,
                              mac_aging_time=mac_aging_time,
                              isid=isid)
        uuid = self._vnc.bridge_domain_create(bd_obj)
        self._log.info('Created Bridge Domain %s, UUID: %s' % (
            self._vnc.id_to_fq_name(uuid), uuid))
        return bd_obj
    # end create_bd

    def update_bd(self, uuid=None, **kwargs):
        '''
            Updates bridge domain
        '''
        mac_learning_enabled = kwargs.get('mac_learning_enabled', None)
        mac_limit_control = kwargs.get('mac_limit_control', None)
        mac_move_control = kwargs.get('mac_move_control', None)
        mac_aging_time = kwargs.get('mac_aging_time', None)
        isid = kwargs.get('isid', None)
        bd_obj = self._vnc.bridge_domain_read(id=uuid)
        if mac_learning_enabled:
            bd_obj.set_mac_learning_enabled(mac_learning_enabled)
        if mac_limit_control:
            bd_obj.set_mac_limit_control(mac_limit_control)
        if mac_move_control:
            bd_obj.set_mac_move_control(mac_move_control)
        if mac_aging_time:
            bd_obj.set_mac_aging_time(mac_aging_time)
        if isid:
            bd_obj.set_isid(isid)

        self._vnc.bridge_domain_update(bd_obj)
        self._log.info('Updated Bridge Domain %s, UUID: %s' % (
            self._vnc.id_to_fq_name(uuid), uuid))
        return uuid
    # end update_bd

    def delete_bd(self, uuid=None):
        '''
        Delete Bridge Domain object

        Args:
            uuid : UUID of BridgeDomain object
        '''
        self._vnc.bridge_domain_delete(id=uuid)
        self._log.info('Deleted Bridge Domain %s' % (uuid))
    # end delete_bd

    def read_bd(self, uuid=None):
        '''
        Read Bridge Domain object

        Args:
            uuid : UUID of BridgeDomain object
        '''
        bd_obj = self._vnc.bridge_domain_read(id=uuid)
        self._log.info('Bridge Domain %s info' % (uuid, bd_obj))
    # end read_bd

    def get_bd(self, uuid=None):
        '''
        Get Bridge Domain object

        Args:
            uuid : UUID of BridgeDomain object
        '''
        bd_obj = self._vnc.bridge_domain_read(id=uuid)
        self._log.info('Bridge Domain %s info' % (uuid, bd_obj))
        bd_obj.dump()
    # end get_bd

    def add_bd_to_vmi(self, bd_id, vmi_id, vlan_tag):
        '''
        Adding Bridge Domain to VMI

        Args:
            bd_id: ID of BridgeDomain
            vmi_id: ID of VMI
            vlan_tag: vlan tag
        '''
        self._log.info('Adding Bridge Domain %s to VMI %s' % (bd_id, vmi_id))
        vmi = self._vnc.virtual_machine_interface_read(id=vmi_id)
        bd_obj = self._vnc.bridge_domain_read(id=bd_id)
        bmeb = BridgeDomainMembershipType()
        bmeb.set_vlan_tag(vlan_tag)
        vmi.add_bridge_domain(bd_obj, bmeb)
        self._vnc.virtual_machine_interface_update(vmi)

    def enable_vlan_tag_based_bridge_domain(
            self, vmi_id, vlan_tag_based_bridge_domain):
        '''
        Enabling vlan tag based bridge domain

        Args:
            vmi_id: ID of VMI
            vlan_tag_based_bridge_domain: vlan tag based bridge domain
        '''
        self._log.info(
            'Enabling vlan tag based bridge domain %s on  VMI %s' %
            (vlan_tag_based_bridge_domain, vmi_id))
        vmi = self._vnc.virtual_machine_interface_read(id=vmi_id)
        vmi.set_vlan_tag_based_bridge_domain(vlan_tag_based_bridge_domain)
        self._vnc.virtual_machine_interface_update(vmi)

    def get_vmi_host_name(self, vmi_id):
        '''
        Gets VMIs compute node name
        '''

        vmi_host = None
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        vmi_bindings = vmi_obj.get_virtual_machine_interface_bindings()
        # Sub-interface case, get the host of parent VMI
        if not vmi_bindings:
            parent_vmi_id = vmi_obj.get_virtual_machine_interface_refs()[
                0]['uuid']
            vmi_obj = self._vnc.virtual_machine_interface_read(
                id=parent_vmi_id)
            vmi_bindings = vmi_obj.get_virtual_machine_interface_bindings()
        if not vmi_bindings:
            self._log.error('Could not get VMI bindings for VMI %s' % (vmi_id))
            return False
        kv_list = vmi_bindings.key_value_pair
        for kv in kv_list:
            if kv.key == 'host_id':
                vmi_host = kv.value
                return vmi_host

    def get_vn_obj_from_id(self, uuid):
        return self._vnc.virtual_network_read(id=uuid)

    def connect_gateway_with_router(self, router_obj, public_network_obj):

        # Add public network to router as external_gateway
        if type(public_network_obj).__name__ is 'VirtualNetwork':
            router_obj.add_virtual_network(public_network_obj)
        else:
            router_obj.add_virtual_network(
                self.get_vn_obj_from_id(
                    public_network_obj['network']['id']))

        # Update logical router object
        self._vnc.logical_router_update(router_obj)
        return router_obj

    def update_bgp_router_af(self, name, af):
        '''
            Update bgp router address family
            Param:
               name - bgp router name
               af - address family to add
        '''
        bgp_fq_name = ['default-domain', 'default-project',
                           'ip-fabric', '__default__']
        bgp_fq_name.append(name)
        bgp_router_obj = self._vnc.bgp_router_read(fq_name=bgp_fq_name)
        params = bgp_router_obj.get_bgp_router_parameters()
        address_families = params.get_address_families()
        address_families.add_family(af)
        params.set_address_families(address_families)
        bgp_router_obj.set_bgp_router_parameters(params)
        self._vnc.bgp_router_update(bgp_router_obj)

    def provision_bgp_router(self, name, ip, asn, af):
        '''Provision Fabric Gateway.
           Input is: name, ip, asn and address families of bgp router
        '''
        router_name = name
        router_ip = ip
        router_type = 'router'
        vendor = 'mx'
        router_asn = asn
        address_families = af

        rt_inst_obj = self._vnc.routing_instance_read(
            fq_name=['default-domain', 'default-project',
                     'ip-fabric', '__default__'])
        bgp_router = BgpRouter(router_name, rt_inst_obj)
        params = BgpRouterParams()
        params.address = router_ip
        params.router_type = router_type
        params.vendor = vendor
        params.address_families = AddressFamilies(
            address_families)
        params.autonomous_system = router_asn
        params.identifier = router_ip
        bgp_router.set_bgp_router_parameters(params)

        try:
            bgp_router_id = self._vnc.bgp_router_create(bgp_router)
            bgp_router_obj = self._vnc.bgp_router_read(
                id=bgp_router_id)
            self._log.info('Created BGP router: %s' % (router_name))
            return bgp_router_obj

        except RefsExistError:
            self._log.info("BGP router: %s is already present, "
                           "continuing the test" % (router_name))
            bgp_fq_name = ['default-domain', 'default-project',
                           'ip-fabric', '__default__']
            bgp_fq_name.append(router_name)
            bgp_router_obj = self._vnc.bgp_router_read(fq_name=bgp_fq_name)
            return bgp_router_obj
        except BaseException:
            self._log.error("Error in configuring BGP router: %s" % (
                router_name))
            return False

    # end provision_bgp_router

    def add_bgp_router(self, router_type, router_name, router_ip,
                       router_asn, address_families=[], md5=None,
                       local_asn=None, port=179, sub_cluster_name=None):
        if not address_families:
            address_families = ['route-target', 'inet-vpn', 'e-vpn', 'erm-vpn',
                                'inet6-vpn']
            if router_type != 'control-node':
                address_families.remove('erm-vpn')

        if router_type != 'control-node':
            if 'erm-vpn' in address_families:
                raise RuntimeError("Only contrail bgp routers can support "
                                   "family 'erm-vpn'")

        bgp_addr_fams = AddressFamilies(address_families)

        bgp_sess_attrs = [
            BgpSessionAttributes(address_families=bgp_addr_fams)]
        bgp_sessions = [BgpSession(attributes=bgp_sess_attrs)]
        bgp_peering_attrs = BgpPeeringAttributes(session=bgp_sessions)

        rt_inst_obj = self._vnc.routing_instance_read(
            fq_name=['default-domain', 'default-project',
                     'ip-fabric', '__default__'])
        if router_type == 'control-node':
            vendor = 'contrail'
        elif router_type == 'router':
            vendor = 'mx'
        else:
            vendor = 'unknown'

        router_params = BgpRouterParams(
            router_type=router_type,
            vendor=vendor,
            autonomous_system=int(router_asn),
            identifier=self.get_ip(router_ip),
            address=self.get_ip(router_ip),
            port=port,
            address_families=bgp_addr_fams)

        bgp_router_obj = BgpRouter(router_name, rt_inst_obj,
                                   bgp_router_parameters=router_params)
        bgp_router_fq_name = bgp_router_obj.get_fq_name()
        try:
            # full-mesh with existing bgp routers
            if not sub_cluster_name:
                fq_name = rt_inst_obj.get_fq_name()
                bgp_other_objs = self._vnc.bgp_routers_list(
                    parent_fq_name=fq_name,
                    detail=True)
                bgp_router_names = [bgp_obj.fq_name
                                    for bgp_obj in bgp_other_objs
                                    if bgp_obj.get_sub_cluster_refs() is None]
                bgp_router_obj.set_bgp_router_list(
                    bgp_router_names, [bgp_peering_attrs] * len(bgp_router_names))
            else:
                sub_cluster_obj = SubCluster(sub_cluster_name)
                try:
                    sub_cluster_obj = self._vnc.sub_cluster_read(
                        fq_name=sub_cluster_obj.get_fq_name())
                except NoIdError:
                    raise RuntimeError("Sub cluster to be provisioned first")
                bgp_router_obj.add_sub_cluster(sub_cluster_obj)
                refs = sub_cluster_obj.get_bgp_router_back_refs()
                if refs:
                    bgp_router_names = [
                        ref['to'] for ref in refs if ref['uuid'] != bgp_router_obj.uuid]
                    bgp_router_obj.set_bgp_router_list(
                        bgp_router_names, [bgp_peering_attrs] * len(bgp_router_names))
            self._vnc.bgp_router_create(bgp_router_obj)
        except RefsExistError as e:
            print ("BGP Router " + pformat(bgp_router_fq_name) +
                   " already exists " + str(e))
        if md5 or local_asn:
            cur_obj = self._vnc.bgp_router_read(fq_name=bgp_router_fq_name)
        changed = False
        if md5:
            changed = True
            md5 = {'key_items': [{'key': md5, "key_id": 0}], "key_type": "md5"}
            rparams = cur_obj.bgp_router_parameters
            rparams.set_auth_data(md5)
            cur_obj.set_bgp_router_parameters(rparams)

        if local_asn:
            changed = True
            local_asn = int(local_asn)
            if local_asn <= 0 or local_asn > 65535:
                raise argparse.ArgumentTypeError(
                    "local_asn %s must be in range (1..65535)" % local_asn)
            rparams = cur_obj.bgp_router_parameters
            rparams.set_local_autonomous_system(local_asn)
            cur_obj.set_bgp_router_parameters(rparams)

        if changed:
            self._vnc.bgp_router_update(cur_obj)

    # end add_bgp_router

    def delete_bgp_router(self, name):
        '''Delete Fabric Gateway.
           Input is: name of fabric gateway

        '''
        router_name = name

        bgp_fq_name = ['default-domain', 'default-project', 'ip-fabric',
                       '__default__']
        bgp_fq_name.append(router_name)

        try:
            self._vnc.bgp_router_delete(fq_name=bgp_fq_name)
            self._log.info(
                "Deleted BGP router %s successfully" %
                (router_name))
            return True

        except BaseException:
            self._log.error("%s Error in Deleting BGP router " % (router_name))
            return False

    # end delete_bgp_router

    def read_global_system_config(self):
        fq_name = ['default-global-system-config']
        return self._vnc.global_system_config_read(fq_name=fq_name)

    def read_global_vrouter_config(self):
        fq_name = ['default-global-system-config',
                   'default-global-vrouter-config']
        return self._vnc.global_vrouter_config_read(fq_name=fq_name)

    def get_flow_export_rate(self):
        gv_obj = self.read_global_vrouter_config()
        return gv_obj.get_flow_export_rate()

    def set_flow_export_rate(self, rate):
        gv_obj = self.read_global_vrouter_config()
        gv_obj.set_flow_export_rate(rate)
        self._vnc.global_vrouter_config_update(gv_obj)

    def add_link_local_service(self, name, ip, port, ipfabric_service_port,
                               ipfabric_service_ip=None,
                               ipfabric_service_dns_name=None):
        if not isinstance(ipfabric_service_ip, list):
            ipfabric_service_ip = [ipfabric_service_ip]
        linklocal_obj = LinklocalServiceEntryType(
            linklocal_service_name=name,
            linklocal_service_ip=ip,
            linklocal_service_port=int(port),
            ip_fabric_DNS_service_name=ipfabric_service_dns_name,
            ip_fabric_service_port=int(ipfabric_service_port),
            ip_fabric_service_ip=ipfabric_service_ip)
        gv_obj = self.read_global_vrouter_config()
        services = gv_obj.get_linklocal_services() or LinklocalServicesTypes()
        lls_entries = services.get_linklocal_service_entry()
        for entry in lls_entries:
            if entry.get_linklocal_service_name() == name:
                self._log.info("Link local service %s already there" % name)
                return
        lls_entries.append(linklocal_obj)
        services.set_linklocal_service_entry(lls_entries)
        gv_obj.set_linklocal_services(services)
        self._vnc.global_vrouter_config_update(gv_obj)
        self._log.debug("Link local service %s added" % name)

    def delete_link_local_service(self, name):
        gv_obj = self.read_global_vrouter_config()
        services = gv_obj.get_linklocal_services() or LinklocalServicesTypes()
        lls_entries = services.get_linklocal_service_entry()
        for entry in lls_entries:
            if entry.get_linklocal_service_name() == name:
                break
        else:
            self._log.info("Link local service %s not found" % name)
            return
        lls_entries.remove(entry)
        services.set_linklocal_service_entry(lls_entries)
        gv_obj.set_linklocal_services(services)
        self._vnc.global_vrouter_config_update(gv_obj)
        self._log.debug("Link local service %s removed" % name)

    # Lbaasv2 functions
    def get_loadbalancer(self, lb_uuid):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        return self.lb_feature_handles.lb_mgr.read(id=lb_uuid)
    # End get_loadbalancer

    def list_floatingips(self, tenant_id=None, port_id=None):
        if port_id:
            port_obj = self._vnc.virtual_machine_interface_read(id=port_id)
            fip_refs = port_obj.get_floating_ip_back_refs()
            if fip_refs:
                fip_ids = [ref['uuid'] for ref in fip_refs]
                if fip_ids:
                    fip_dict = self._vnc.floating_ips_list(
                        obj_uuids=fip_ids, fields=[
                            'parent_uuid', 'floating_ip_fixed_ip_address'], detail=False)
                    fip_list = fip_dict.get('floating-ips')
                return fip_list
        return []
    # End list_floatingips

    def list_loadbalancers(self, **kwargs):
        lb_name = kwargs.get('name', None)
        if lb_name:
            self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
            lb_objects = self.lb_feature_handles.lb_mgr.lb_list()
            return lb_objects['loadbalancers']
    # End list_loadbalancers

    def create_loadbalancer(self, name=None, network_id=None,
                            subnet_id=None, address=None, project=None):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        #proj_obj = self.read_project_obj(project_fq_name=project)
        proj_obj = self.vnc_project
        vn_obj = self.get_vn_obj_from_id(network_id)
        lb_obj = self.lb_feature_handles.lb_mgr.create(
            name, proj_obj, vn_obj, vip_address=address, subnet_uuid=subnet_id)
        return lb_obj
    # End create_loadbalancer

    def delete_loadbalancer(self, lb_id):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        self.lb_feature_handles.lb_mgr.delete(lb_id)
    # End delete_loadbalancer

    def assoc_floatingip(self, fip_id, port_id):
        return self.assoc_floating_ip(fip_id, port_id, vmi_id=port_id)
    # End assoc_floatingip

    def create_floatingip(self, fip_pool_vn_id,
                          project_id=None, port_id=None,
                          project_fq_name=None):
        pool_obj = self.get_vn_obj_from_id(fip_pool_vn_id)
        proj_obj = self.vnc_project
        (fip, fip_id) = self.create_floating_ip(
            None, proj_obj, vn_obj=pool_obj)
        if port_id:
            self.assoc_floating_ip(fip_id, port_id, vmi_id=port_id)
        fip_obj = self._vnc.floating_ip_read(id=fip_id)
        return fip_obj
    # End create_floatingip

    def delete_floatingip(self, fip_id):
        self.delete_floating_ip(fip_id)
    # End delete_floatingip

    def apply_sg_to_port(self, port_id, sg_list):
        return self.set_security_group(port_id, sg_list)
    # End apply_sg_to_port

    def get_listener(self, listener_id, **kwargs):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        return self.lb_feature_handles.ll_mgr.read(id=listener_id)
    # End get_listener

    def list_lbaas_pools(self, **kwargs):
        ll_id = kwargs.get('listener', '')
        parent_obj = self.vnc_project
        parent_id = parent_obj.uuid
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        ll_list = self.lb_feature_handles.lb_pool_mgr.resource_list(
            tenant_id=parent_id)
        return ll_list['loadbalancer-pools']
    # End list_lbaas_pools

    def get_lbaas_member(self, member_id, pool_id, **kwargs):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        return self.lb_feature_handles.lb_member_mgr.read(id=member_id)
    # End get_lbaas_member

    def get_lbaas_healthmonitor(self, hm_id, **kwargs):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        return self.lb_feature_handles.lb_hm_mgr.read(id=hm_id)
    # End get_lbaas_healthmonitor

    def list_listeners(self, **kwargs):
        parent = kwargs.get('parent_fq_name', None)
        if parent:
            parent_obj = self.vnc_project
            parent_id = parent_obj.id
        else:
            parent_id = None
        lb_listeners = self._vnc.loadbalancer_listeners_list(
            parent_id=parent_id)
        return lb_listeners['loadbalancer-listeners']
    # End list_listeners

    def create_listener(
            self,
            lb_id,
            protocol,
            port,
            default_tls_container=None,
            name=None,
            connection_limit=-1,
            **kwargs):
        sni_containers = kwargs.get('sni_containers', None)
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        lb_obj = self._vnc.loadbalancer_read(id=lb_id)
        proj_fq_name = kwargs.get('projetc_fq_name', None)
        proj_obj = self.vnc_project
        return self.lb_feature_handles.ll_mgr.create(
            lb_obj,
            proj_obj,
            name=name,
            protocol=protocol,
            protocol_port=port,
            connection_limit=connection_limit,
            default_tls_container=default_tls_container,
            sni_containers=sni_containers)
    # End create_listener

    def create_lbaas_pool(self, listener_id, protocol, lb_algorithm,
                          name=None, session_persistence=None, **kwargs):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        ll_obj = self._vnc.loadbalancer_listener_read(id=listener_id)
        proj_fq_name = kwargs.get('projetc_fq_name', None)
        proj_obj = self.vnc_project
        return self.lb_feature_handles.lb_pool_mgr.create(
            ll_obj,
            proj_obj,
            protocol,
            name=name,
            session_persistence=session_persistence,
            lb_algorithm=lb_algorithm)
    # End create_lbaas_pool

    def delete_lbaas_pool(self, pool_id):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        self.lb_feature_handles.lb_pool_mgr.delete(id=pool_id)
    # End delete_lbaas_pool

    def get_port_ips(self, port_id):
        vmi_obj=self._vnc.virtual_machine_interface_read(id=port_id)
    #End get_port_ips

    def get_subnet_id_from_network(self, vn_id):
        vn_obj = self._vnc.virtual_network_read(id=vn_id)

    def create_lbaas_member(self, address, port, pool_id, weight=1,
                            subnet_id=None, network_id=None):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        pool_obj = self._vnc.loadbalancer_pool_read(id=pool_id)
        if network_id and not subnet_id:
            subnet_id = self.get_subnet_id_from_network(network_id)
        return self.lb_feature_handles.lb_member_mgr.create(
            pool_obj,
            address=address,
            protocol_port=port,
            weight=weight,
            subnet_id=subnet_id)
    # End create_lbaas_member

    def list_lbaas_members(self, pool_id, **kwargs):
        return self._vnc.loadbalancer_members_list(
            parent_id=pool_id)
    # End list_lbaas_members

    def delete_lbaas_member(self, member_id, pool_id):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        self.lb_feature_handles.lb_member_mgr.delete(id=member_id)
    # End delete_lbaas_member

    def update_lbaas_member(self, member_id, pool_id, port=None,
                            weight=None, admin_state=None,
                            status=None, address=None):
        '''
        'admin_state': 'admin_state_up',
        'status': 'status',
        'protocol_port': 'protocol_port',
        'weight': 'weight',
        'address': 'address',
        'subnet_id': 'subnet_id',
        '''

        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        return self.lb_feature_handles.lb_member_mgr.update(
            member_id,
            admin_state=admin_state,
            status=status,
            port=port,
            weight=weight,
            address=address)
    # End update_lbaas_member

    def create_lbaas_healthmonitor(self, pool_id, delay, max_retries,
                                   probe_type, timeout, http_method=None,
                                   http_codes=None, http_url=None):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        proj_obj = self.vnc_project
        return self.lb_feature_handles.lb_hm_mgr.create(
            pool_id,
            delay,
            max_retries,
            probe_type,
            timeout,
            http_method=http_method,
            http_codes=http_codes,
            http_url=http_url,
            proj_obj=proj_obj)

    # End create_lbaas_healthmonitor

    def delete_lbaas_healthmonitor(self, hm_id):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        return self.lb_feature_handles.lb_hm_mgr.delete(id=hm_id)
    # End delete_lbaas_healthmonitor

    def update_lbaas_healthmonitor(self, hm_id, delay=None, max_retries=None,
                                   timeout=None, http_method=None,
                                   http_codes=None, http_url=None,
                                   project_fq_name=None):

        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        proj_obj = self.vnc_project
        return self.lb_feature_handles.lb_hm_mgr.update(
            hm_id=hm_id,
            proj_obj=proj_obj,
            delay=delay,
            max_retries=max_retries,
            timeout=timeout,
            http_method=http_method,
            http_codes=http_codes,
            http_url=http_url)
    # End update_lbaas_healthmonitor

    def delete_listener(self, listener_id):
        self.lb_feature_handles = LBFeatureHandles(self._vnc, self._log)
        self.lb_feature_handles.ll_mgr.delete(id=listener_id)
    # End delete_listener
    # End Lbaasv2 functions

    def get_vn_of_subnet(self, subnet_id):
        return get_subnet_network_id(self._vnc, subnet_id)

    def delete_fip_on_vip(self):
        # This function is needed to meet the expectation
        # of lbaasV2 fixture.The intent is achieved
        # in delete of pool.Hence keeping is empty
        pass

    def port_translation_pool(
            self,
            protocol,
            port_count,
            start_port=0,
            end_port=0):
        port_range = PortType(start_port=start_port, end_port=end_port)
        pp = PortTranslationPool(
            protocol=protocol,
            port_count=str(port_count),
            port_range=port_range)
        return pp

    def get_port_translation_pools(self):
        gv_obj = self.read_global_vrouter_config()
        return gv_obj.get_port_translation_pools()
    # end get_port_translation_pool_global_config

    def set_port_translation_pool(self, pp=None):
        pp = pp or []
        gv_obj = self.read_global_vrouter_config()
        ppp = PortTranslationPools()
        ppp.set_port_translation_pool(pp)
        gv_obj.set_port_translation_pools(ppp)
        self._vnc.global_vrouter_config_update(gv_obj)
        return True
    # end set_port_translation_pool

    def delete_port_translation_pool(self, pp):
        gv_obj = self.read_global_vrouter_config()
        port_tr_pools = gv_obj.get_port_translation_pools()
        port_tr_pools.delete_port_translation_pool(pp)
        gv_obj.set_port_translation_pools(port_tr_pools)
        self._vnc.global_vrouter_config_update(gv_obj)
        return port_tr_pools

    def insert_port_translation_pool(self, pp, index=-1):
        gv_obj = self.read_global_vrouter_config()
        port_tr_pools = gv_obj.get_port_translation_pools()
        port_tr_pools.insert_port_translation_pool(index, pp)
        gv_obj.set_port_translation_pools(port_tr_pools)
        self._vnc.global_vrouter_config_update(gv_obj)
        return port_tr_pools

    def get_fabric_snat(self, vn_id):
        vn_obj = self._vnc.virtual_network_read(id=vn_id)
        return vn_obj.get_fabric_snat()

    def set_fabric_snat(self, vn_id, enable=True):
        vn_obj = self._vnc.virtual_network_read(id=vn_id)
        vn_obj.set_fabric_snat(enable)
        self._vnc.virtual_network_update(vn_obj)

    def get_ip(self, ip_w_pfx):
        return str(IPNetwork(ip_w_pfx).ip)

    def create_vn_api(self, vn_name, project, subnets, ipam, **kwargs):
        project_obj = self.read_project_obj(project_fq_name=project)
        ipam_obj = self._vnc.network_ipam_read(
            fq_name=ipam)
        vn_obj = VirtualNetwork(vn_name, parent_obj=project_obj)
        for pfx in subnets:
            px = pfx['cidr'].split('/')[0]
            pfx_len = int(pfx['cidr'].split('/')[1])
            subnet_vnc = IpamSubnetType(subnet=SubnetType(px, pfx_len))
            vnsn_data = VnSubnetsType([subnet_vnc])
            vn_obj.add_network_ipam(ipam_obj, vnsn_data)
        try:
            vn_uuid = self._vnc.virtual_network_create(vn_obj)
            if not kwargs.get('enable_dhcp', None):
                vn_obj.external_ipam = True
                self._vnc.virtual_network_update(vn_obj)
            return vn_uuid
        except RefsExistError:
            project_fq_name.append(vn_name)
            return self._vnc.virtual_network_read(vn_fq_name=project_fq_name)

    def delete_vn_api(self, vn_obj):
        try:
            self._vnc.virtual_network_delete(id=vn_obj.uuid)
            return True
        except RefsExistError as e:
            self._log.debug(
                'RefsExistError %s while deleting VN %s..%(e, vn_obj.name)')
            return False

    def get_vmi_by_vm(self, vm_id, **kwargs):
        try:
            vm_obj = self._vnc.virtual_machine_read(id=vm_id)
        except Exception as e:
            self._log.debug(
                "Got exception as %s while reading the vm obj" %
                (e))
        vmis = vm_obj.get_virtual_machine_interface_back_refs()
        return [
            self._vnc.virtual_machine_interface_read(
                id=vmi['uuid']) for vmi in vmis]

    def create_virtual_port_group(self, fq_name):
        obj = VirtualPortGroup(fq_name[-1], fq_name=fq_name,
                               parent_type='fabric')
        self._log.debug('Creating VPG %s'%fq_name)
        return self._vnc.virtual_port_group_create(obj)

    def read_virtual_port_group(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading VPG %s' % kwargs)
        return self._vnc.virtual_port_group_read(**kwargs)

    def delete_virtual_port_group(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting VPG %s' % kwargs)
        return self._vnc.virtual_port_group_delete(**kwargs)

    def associate_physical_interface(self, vpg_uuid, pif_obj):
        self._log.debug('Associate VPG %s and PIF %s'%(vpg_uuid, pif_obj.uuid))
        obj = self.read_virtual_port_group(id=vpg_uuid)
        obj.add_physical_interface(pif_obj)
        return self._vnc.virtual_port_group_update(obj)

    def disassociate_physical_interface(self, vpg_uuid, pif_obj):
        self._log.debug('Disassoc VPG %s and PIF %s'%(vpg_uuid, pif_obj.uuid))
        obj = self.read_virtual_port_group(id=vpg_uuid)
        obj.del_physical_interface(pif_obj)
        return self._vnc.virtual_port_group_update(obj)

    def create_fabric(self, name, creds=None):
        fqname = ['default-global-system-config', name]
        parent_type = 'global-system-config'
        credentials = DeviceCredentialList()
        for cred in creds or list():
            user_creds = UserCredentials(username=cred['username'],
                                         password=cred['password'])
            credential = DeviceCredential(vendor=cred['vendor'],
                                          device_family=cred['device_family'],
                                          credential=user_creds)
            credentials.add_device_credential(credential)
        obj = Fabric(name, fq_name=fqname, parent_type=parent_type,
                     fabric_credentials=credentials)
        self._log.debug('Creating fabric %s' % fqname)
        return self._vnc.fabric_create(obj)

    def add_creds_to_fabric(self, name, creds):
        obj = self.read_fabric(name)
        credentials = obj.get_fabric_credentials()
        for cred in creds:
            user_creds = UserCredentials(username=cred['username'],
                                         password=cred['password'])
            credential = DeviceCredential(vendor=cred['vendor'],
                                          device_family=cred['device_family'],
                                          credential=user_creds)
            credentials.add_device_credential(credential)
        obj.set_fabric_credentials(credentials)
        return self._vnc.fabric_update(obj)

    def delete_creds_from_fabric(self, name, creds):
        obj = self.read_fabric(name)
        credentials = obj.get_fabric_credentials()
        for cred in creds:
            for curr_cred in credentials.get_device_credential() or list():
                user_creds = curr_cred.get_credential()
                if cred['username'] == user_creds.get_username() and \
                   cred['password'] == user_creds.get_password() and \
                   cred['vendor'] == curr_cred.get_vendor() and \
                   cred['device_family'] == curr_cred.get_device_family():
                    credentials.delete_device_credential(curr_cred)
                    break

    def read_fabric(self, name=None, **kwargs):
        '''
            :param name : name of the object
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        if name:
            kwargs['fq_name'] = ['default-global-system-config', name]
        self._log.debug('Reading fabric %s' % kwargs)
        return self._vnc.fabric_read(**kwargs)

    def delete_fabric(self, name=None, **kwargs):
        '''
            :param name : name of the object
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        if name:
            kwargs['fq_name'] = ['default-global-system-config', name]
        self._log.debug('Deleting fabric %s' % kwargs)
        return self._vnc.fabric_delete(**kwargs)

    def get_fabric_namespace_value(self, **kwargs):
        obj = self.read_fabric_namespace(**kwargs)
        value = obj.fabric_namespace_value
        if obj.fabric_namespace_type == 'IPV4-CIDR':
            v4_cidr = value.get_ipv4_cidr()
            subnet = v4_cidr.get_subnet()[0]
            return '%s/%s' % (subnet.ip_prefix, subnet.ip_prefix_len)
        elif obj.fabric_namespace_type == 'ASN':
            asn = value.get_asn()
            return asn.get_asn()[0]
        elif obj.fabric_namespace_type == 'MAC_ADDR':
            mac = value.get_mac_addr()
            return mac.get_mac_address()[0]

    def create_fabric_namespace(self, fq_name, ns_type, ns_value):
        ns_value_obj = NamespaceValue()
        if ns_type == 'IPV4-CIDR':
            cidrs = ns_value if isinstance(ns_value, list) else [ns_value]
            subnets = SubnetListType()
            for cidr in cidrs:
                subnets.add_subnet(SubnetType(
                                   ip_prefix=cidr.split('/')[0],
                                   ip_prefix_len=cidr.split('/')[1]))
            ns_value_obj.set_ipv4_cidr(subnets)
        elif ns_type == 'ASN':
            asns = ns_value if isinstance(ns_value, list) else [ns_value]
            ns_value_obj.set_asn(AutonomousSystemsType(asn=asns))
        elif ns_type == 'MAC_ADDR':
            macs = ns_value if isinstance(ns_value, list) else [ns_value]
            ns_value_obj.set_mac_addr(MacAddressesType(mac_address=macs))
        else:
            raise Exception('unsupported namespace type')
        obj = FabricNamespace(fq_name[-1], fq_name=fq_name,
                              parent_type='fabric',
                              fabric_namespace_type=ns_type,
                              fabric_namespace_value=ns_value_obj)
        return self._vnc.fabric_namespace_create(obj)

    def read_fabric_namespace(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading fabric namespace %s' % kwargs)
        return self._vnc.fabric_namespace_read(**kwargs)

    def delete_fabric_namespace(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting fabric namespace %s' % kwargs)
        return self._vnc.fabric_namespace_delete(**kwargs)

    def add_device_to_fabric(self, fabric, device):
        '''
           :param fabric: uuid or name of the fabric
           :param device: uuid or name of the device
        '''
        kwargs = dict()
        if is_uuid(device):
            kwargs['id'] = device
        else:
            kwargs['name'] = device
        device_obj = self.read_physical_router(**kwargs)
        kwargs = dict()
        if is_uuid(fabric):
            kwargs['id'] = fabric
        else:
            kwargs['name'] = fabric
        fabric_obj = self.read_fabric(**kwargs)
        fabric_obj.add_physical_router(device_obj)
        return self._vnc.fabric_update(fabric_obj)

    def delete_device_from_fabric(self, fabric, device):
        kwargs = dict()
        if is_uuid(device):
            kwargs['id'] = device
        else:
            kwargs['name'] = device
        device_obj = self.read_physical_router(**kwargs)
        kwargs = dict()
        if is_uuid(fabric):
            kwargs['id'] = fabric
        else:
            kwargs['name'] = fabric
        fabric_obj = self.read_fabric(**kwargs)
        fabric_obj.del_physical_router(device_obj)
        return self._vnc.fabric_update(fabric_obj)

    def delete_logical_interface(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting logical interface %s' % kwargs)
        return self._vnc.logical_interface_delete(**kwargs)

    def read_logical_interface(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading logical interface %s' % kwargs)
        return self._vnc.logical_interface_read(**kwargs)

    def create_logical_interface(self, name, pif_fqname, vlan=None,
                                 interface_type=None):
        fq_name = pif_fqname + [name.replace(':', '__')]
        obj = LogicalInterface(name=fq_name[-1],
                               parent_type='physical-interface',
                               fq_name=fq_name,
                               display_name=name)
        if vlan is not None:
            obj.set_logical_interface_vlan_tag(vlan)
        if interface_type:
            obj.set_logical_interface_type(interface_type)
        return self._vnc.logical_interface_create(obj)

    def update_logical_interface(
            self,
            vlan=None,
            interface_type=None,
            **kwargs):
        obj = self.read_logical_interface(**kwargs)
        if vlan is not None:
            obj.set_logical_interface_vlan_tag(vlan_id)
        if interface_type:
            obj.set_logical_interface_type(interface_type)
        self._vnc.logical_interface_update(obj)

    def add_vmi_to_lif(self, vmi_id, lif_id):
        lif_obj = self.read_logical_interface(id=lif_id)
        vmi_obj = self.read_virtual_machine_interface(id=vmi_id)
        lif_obj.add_virtual_machine_interface(vmi_obj)
        self._vnc.logical_interface_update(lif_obj)

    def delete_vmi_from_lif(self, vmi_id, lif_id):
        lif_obj = self.read_logical_interface(id=lif_id)
        vmi_obj = self.read_virtual_machine_interface(id=vmi_id)
        lif_obj.del_virtual_machine_interface(vmi_obj)
        self._vnc.logical_interface_update(lif_obj)

    def delete_physical_interface(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting physical interface %s' % kwargs)
        return self._vnc.physical_interface_delete(**kwargs)

    def read_physical_interface(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading physical interface %s' % kwargs)
        return self._vnc.physical_interface_read(**kwargs)

    def create_physical_interface(self, name, device_name, mac=None,
                                  interface_type=None):
        fq_name = ['default-global-system-config', device_name,
                   name.replace(':', '__')]
        obj = PhysicalInterface(name=fq_name[-1],
                                parent_type='physical-router',
                                fq_name=fq_name,
                                display_name=name)
        if mac:
            macs = mac if isinstance(mac, list) else [mac]
            mac_addr = MacAddressesType(mac_address=macs)
            obj.set_physical_interface_mac_addresses(mac_addr)
        if interface_type:
            obj.set_physical_interface_type(interface_type)
        return self._vnc.physical_interface_create(obj)

    def update_physical_router(self, role=None, **kwargs):
        obj = self.read_physical_router(**kwargs)
        obj.set_physical_router_role(role)
        self._vnc.physical_router_update(obj)

    def create_physical_router(self, name, mgmt_ip, loopback_ip, peer_ip=None,
                               dm_managed=True, username=None, password=None,
                               lldp=True, vendor='Juniper', family='junos',
                               role=None, model=None):
        peer_ip = peer_ip or loopback_ip
        creds = UserCredentials(username=username, password=password)
        obj = PhysicalRouter(name, physical_router_management_ip=mgmt_ip,
                             physical_router_loopback_ip=loopback_ip,
                             physical_router_dataplane_ip=peer_ip,
                             physical_router_vnc_managed=dm_managed,
                             physical_router_user_credentials=creds,
                             physical_router_lldp=lldp,
                             physical_router_vendor_name=vendor,
                             physical_router_device_family=family,
                             physical_router_role=role,
                             physical_router_product_name=model)
        return self._vnc.physical_router_create(obj)

    def read_physical_router(self, name=None, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading physical router %s' % kwargs)
        if name:
            kwargs['fq_name'] = ['default-global-system-config', name]
        return self._vnc.physical_router_read(**kwargs)

    def delete_physical_router(self, name=None, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting physical router %s' % kwargs)
        if name:
            kwargs['fq_name'] = ['default-global-system-config', name]
        return self._vnc.physical_router_delete(**kwargs)

    def read_virtual_machine_interface(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Read virtual machine interface %s' % kwargs)
        return self._vnc.virtual_machine_interface_read(**kwargs)

    def read_virtual_network(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Read virtual network %s' % kwargs)
        return self._vnc.virtual_network_read(**kwargs)

    def read_virtual_router(self, name=None, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Read virtual router %s' % kwargs)
        if name:
            kwargs['fq_name'] = ['default-global-system-config', name]
        return self._vnc.virtual_router_read(**kwargs)

    def delete_vn_from_physical_router(self, device, vn_id):
        kwargs = dict()
        if is_uuid(device):
            kwargs['id'] = device
        else:
            kwargs['name'] = device
        device_obj = self.read_physical_router(**kwargs)
        vn_obj = self.read_virtual_network(id=vn_id)
        device_obj.del_virtual_network(vn_obj)
        self._vnc.physical_router_update(device_obj)

    def add_vn_to_physical_router(self, device, vn_id):
        kwargs = dict()
        if is_uuid(device):
            kwargs['id'] = device
        else:
            kwargs['name'] = device
        device_obj = self.read_physical_router(**kwargs)
        vn_obj = self.read_virtual_network(id=vn_id)
        device_obj.add_virtual_network(vn_obj)
        self._vnc.physical_router_update(device_obj)

    def delete_csn_from_physical_router(self, device, csn):
        '''
           :param device: uuid or name of the device
           :param csn: uuid or name of the contrail service node
        '''
        kwargs = dict()
        if is_uuid(device):
            kwargs['id'] = device
        else:
            kwargs['name'] = device
        device_obj = self.read_physical_router(**kwargs)
        kwargs = dict()
        if is_uuid(csn):
            kwargs['id'] = csn
        else:
            kwargs['name'] = csn
        vr_obj = self.read_virtual_router(**kwargs)
        device_obj.del_virtual_router(vr_obj)
        return self._vnc.physical_router_update(device_obj)

    def add_csn_to_physical_router(self, device, csn):
        '''
           :param device: uuid or name of the device
           :param csn: uuid or name of the contrail service node
        '''
        kwargs = dict()
        if is_uuid(device):
            kwargs['id'] = device
        else:
            kwargs['name'] = device
        device_obj = self.read_physical_router(**kwargs)
        kwargs = dict()
        if is_uuid(csn):
            kwargs['id'] = csn
        else:
            kwargs['name'] = csn
        vr_obj = self.read_virtual_router(**kwargs)
        device_obj.add_virtual_router(vr_obj)
        return self._vnc.physical_router_update(device_obj)

    def add_si_to_prouter(self, device, service_port):
        kwargs = dict()
        if is_uuid(device):
            kwargs['id'] = device
        else:
            kwargs['name'] = device
        device_obj = self.read_physical_router(**kwargs)
        service_ports = device_obj.get_physical_router_junos_service_ports() \
                        or JunosServicePorts()
        service_ports.add_service_port(service_port)
        device_obj.set_physical_router_junos_service_ports(service_ports)
        self._vnc.physical_router_update(device_obj)

    def execute_job(self, template_fqname, payload_dict, devices=None):
        '''
            :param template_fqname : fqname of Job template
            :param payload : input for the job in json format
        '''
        device_str = '' if not devices else ' on devices %s'
        self._log.debug('Executing job %s with %s payload%s' % (
                        template_fqname, payload_dict, device_str))
        #payload = json.dumps(payload_dict)
        kwargs = {'job_template_fq_name': template_fqname,
                  'job_input': payload_dict}
        if devices:
            kwargs['device_list'] = devices
        resp = self._vnc.execute_job(**kwargs)
        self._log.debug('Execution id %s' % resp['job_execution_id'])
        return resp['job_execution_id']

    def enable_intf_mirroring(self, vmi_uuid, analyzer_ip, analyzer_name=None,
                             analyzer_mac=None, routing_instance=None,
                             direction='both', udp_port=8099, encapsulation=None,
                             nic_assisted_mirroring=False, nh_mode='dynamic',
                             nic_assisted_mirroring_vlan=None, header=True,
                             vn_uuid=None, vtep_ip=None):
        analyzer_name = analyzer_name or get_random_name('mirror')
        vmi = self._vnc.virtual_machine_interface_read(id=vmi_uuid)
        prop_obj = vmi.get_virtual_machine_interface_properties() or \
                   VirtualMachineInterfacePropertiesType()
        interface_mirror = prop_obj.get_interface_mirror()
        if nh_mode == 'static':
            vn = self._vnc.virtual_network_read(id=vn_uuid)
            vni = vn.get_virtual_network_network_id()
            static_nh = StaticMirrorNhType(vtep_dst_ip_address=vtep_ip, vni=vni)
            mirror_to = MirrorActionType(analyzer_name=analyzer_name,
                                         encapsulation=encapsulation,
                                         analyzer_ip_address=analyzer_ip,
                                         juniper_header=header,
                                         nh_mode=nh_mode,
                                         static_nh_header=static_nh,
                                         routing_instance=routing_instance,
                                         udp_port=udp_port,
                                         analyzer_mac_address=analyzer_mac)
        else:
            mirror_to = MirrorActionType(analyzer_name=analyzer_name,
                                         analyzer_ip_address=analyzer_ip,
                                         juniper_header=header,
                                         nh_mode=nh_mode,
                                         udp_port=udp_port,
                                         nic_assisted_mirroring=nic_assisted_mirroring,
                                         nic_assisted_mirroring_vlan=nic_assisted_mirroring_vlan,
                                         analyzer_mac_address=analyzer_mac)
            if routing_instance:
                mirror_to.set_routing_instance(routing_instance)
            if encapsulation:
                mirror_to.set_encapsulation(encapsulation)
        interface_mirror = InterfaceMirrorType(direction, mirror_to)
        prop_obj.set_interface_mirror(interface_mirror)
        vmi.set_virtual_machine_interface_properties(prop_obj)
        self._vnc.virtual_machine_interface_update(vmi)

    def disable_intf_mirroring(self, vmi_uuid):
        vmi = self._vnc.virtual_machine_interface_read(id=vmi_uuid)
        prop_obj = vmi.get_virtual_machine_interface_properties() or \
                   VirtualMachineInterfacePropertiesType()
        prop_obj.set_interface_mirror(None)
        vmi.set_virtual_machine_interface_properties(prop_obj)
        self._vnc.virtual_machine_interface_update(vmi)

    def read_logical_router(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading logical router %s' % kwargs)
        return self._vnc.logical_router_read(**kwargs)

    def create_router(self, name, project_obj=None, vni=None,
                      is_public=False, parent_fq_name=None,
                      vxlan_enabled=False, relay_servers=None):
        vni = str(vni) if vni else None
        parent_fq_name = project_obj.fq_name if project_obj else parent_fq_name
        fq_name = parent_fq_name + [name]
        lr_type = 'vxlan-routing' if vxlan_enabled else 'snat-routing'
        relay_servers = IpAddressesType(relay_servers)
        obj = LogicalRouter(name=name, parent_type='project',
                            fq_name=fq_name,
                            logical_router_gateway_external=is_public,
                            logical_router_type=lr_type,
                            logical_router_dhcp_relay_server=relay_servers,
                            vxlan_network_identifier=vni)
        self._vnc.logical_router_create(obj)
        return obj

    def update_logical_router(self, uuid=None, fq_name=None, vni=0,
                              is_public=None, relay_servers=None):
        obj = self.read_logical_router(id=uuid, fq_name=fq_name)
        if vni != 0:
            vni = str(vni) if vni else None
            obj.set_vxlan_network_identifier(vni)
        if relay_servers is not None:
            obj.set_logical_router_dhcp_relay_server(
                IpAddressesType(relay_servers))
        if is_public is not None:
            obj.set_logical_router_gateway_external(is_public)
        self._vnc.logical_router_update(obj)

    def delete_router(self, router_obj=None, **kwargs):
        if router_obj:
            self._vnc.logical_router_delete(id=router_obj.uuid)
        else:
            self._vnc.logical_router_delete(**kwargs)

    def enable_vxlan_routing(self, project_name=None):
        '''Used to change the existing encapsulation priorities to new values'''
        if project_name:
            project_obj = self._vnc.project_read(fq_name=['default-domain',
                                                          project_name])
        else:
            project_obj =  self.vnc_project

        self._log.info('Enabling VxLAN Routing for the project: %s' %(project_name))
        project_obj.set_vxlan_routing(True)
        return self._vnc.project_update(project_obj)

    def disable_vxlan_routing(self, project_name=None):
        '''Used to change the existing encapsulation priorities to new values'''
        if project_name:
            project_obj = self._vnc.project_read(fq_name=['default-domain',
                                                          project_name])
        else:
            project_obj =  self.vnc_project

        self._log.info('Disabling VxLAN Routing for the project: %s' %(project_name))
        project_obj.set_vxlan_routing(False)
        return self._vnc.project_update(project_obj)

    def set_logical_router_vni(self, lr_id, vni):
        ''' Used to configure VxLAN Network Identifier on logical router'''
        lr_obj = self._vnc.logical_router_read(id=lr_id)
        lr_obj.set_vxlan_network_identifier(str(vni))
        return self._vnc.logical_router_update(lr_obj)

    def delete_logical_router_vni(self, lr_id):
        ''' Used to delete VxLAN Network Identifier on logical router'''
        lr_obj = self._vnc.logical_router_read(id=lr_id)
        lr_obj.set_vxlan_network_identifier(None)
        return self._vnc.logical_router_update(lr_obj)

    def create_rt(self, rt_name):
        ''' Used to create route target and returns rt object '''
        rt_obj = RouteTarget(name=rt_name)
        self._vnc.route_target_create(rt_obj)
        return rt_obj

    def extend_lr_to_physical_router(self, lr_id, router):
        ''' Logical router extended to given physical router'''
        lr_obj = self._vnc.logical_router_read(id=lr_id)
        phy_router_obj = self.read_physical_router(id=router)
        lr_obj.add_physical_router(phy_router_obj)
        return self._vnc.logical_router_update(lr_obj)

    def remove_physical_router_from_lr(self, lr_id, router):
        ''' Given physical router is removed from logical router'''
        lr_obj = self._vnc.logical_router_read(id=lr_id)
        phy_router_obj = self.read_physical_router(id=router)
        lr_obj.del_physical_router(phy_router_obj)
        return self._vnc.logical_router_update(lr_obj)

    def add_route_target_to_lr(self, lr_id, rt):
        lr_obj = self._vnc.logical_router_read(id=lr_id)
        rt_obj = self._vnc.route_target_read(fq_name=[rt])
        lr_obj.add_route_target(rt_obj)
        return self._vnc.logical_router_update(lr_obj)

    def remove_route_target_from_lr(self, lr_id, rt):
        rt_obj = self._vnc.route_target_read(fq_name=[rt])
        lr_obj = self._vnc.logical_router_read(id=lr_id)
        lr_obj.del_route_target(rt_obj)
        return self._vnc.logical_router_update(lr_obj)

    def set_lr_configured_rt_list(self, lr_id,  rt_list):
        lr_obj = self._vnc.logical_router_read(id=lr_id)
        rt_obj_list = []
        for each_rt in rt_list:
            rt_obj = self._vnc.route_target_read(fq_name=[each_rt])
            rt_obj_list.append(rt_obj)

        lr_obj.set_configured_route_target_list(rt_obj_list)
        return self._vnc.logical_router_update(lr_obj)

    def create_virtual_machine_interface(self, vn_id, name=None, device_owner=None):
        vmi_name = name if name else get_random_name('vmi')
        if device_owner:
            vmi_obj = VirtualMachineInterface(name=vmi_name, parent_obj=self.vnc_project,
                               virtual_machine_interface_device_owner=device_owner)
        else:
            vmi_obj = VirtualMachineInterface(name=vmi_name, parent_obj=self.vnc_project)

        vn_obj = self._vnc.virtual_network_read(id=vn_id)
        vmi_obj.add_virtual_network(vn_obj)
        self._vnc.virtual_machine_interface_create(vmi_obj)
        return vmi_obj

    def delete_virtual_machine_interface(self, id):
        return self._vnc.virtual_machine_interface_delete(id=id)

    def create_instance_ip(self, vn_id, vmi_id, name=None):
        vn_obj = self._vnc.virtual_network_read(id=vn_id)
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        ip_name = name if name else get_random_name('vmi')
        ip_obj = InstanceIp(name=ip_name)
        ip_obj.add_virtual_network(vn_obj)
        ip_obj.add_virtual_machine_interface(vmi_obj)
        self._vnc.instance_ip_create(ip_obj)
        return ip_obj

    def delete_instance_ip(self, id):
        return self._vnc.instance_ip_delete(id=id)

    def add_interface_to_lr(self, lr_id, vmi_id):
        lr_obj = self._vnc.logical_router_read(id=lr_id)
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        lr_obj.add_virtual_machine_interface(vmi_obj)
        return self._vnc.logical_router_update(lr_obj)

    def remove_interface_from_lr(self, lr_id, vmi_id):
        lr_obj = self._vnc.logical_router_read(id=lr_id)
        vmi_obj = self._vnc.virtual_machine_interface_read(id=vmi_id)
        lr_obj.del_virtual_machine_interface(vmi_obj)
        return self._vnc.logical_router_update(lr_obj)

    def read_overlay_role(self, role):
        return self._vnc.overlay_role_read(
            fq_name=['default-global-system-config', role])

    def read_physical_role(self, role):
        return self._vnc.physical_role_read(
            fq_name=['default-global-system-config', role])

    def associate_rb_role(self, prouter, rb_role):
        prouter_obj = self.read_physical_router(fq_name=prouter)
        role_obj = self.read_overlay_role(rb_role)
        prouter_obj.add_overlay_role(role_obj)
        self._vnc.physical_router_update(prouter_obj)

    def associate_physical_role(self, prouter, role):
        prouter_obj = self.read_physical_router(fq_name=prouter)
        role_obj = self.read_physical_role(role)
        prouter_obj.add_physical_role(role_obj)
        self._vnc.physical_router_update(prouter_obj)

    def create_service_appliance_set(self, sas_name=None,
            virtualization_type='physical-device'):
        gsc_obj = self._vnc.global_system_config_read(
            fq_name=['default-global-system-config'])
        sas_name = get_random_name('sas')
        sas_fq_name = ['default-global-system-config', sas_name]
        sas_obj = ServiceApplianceSet(sas_name, gsc_obj)
        sas_obj.set_service_appliance_set_virtualization_type(
            virtualization_type)
        sas_uuid = self._vnc.service_appliance_set_create(sas_obj)
        return sas_uuid

    def delete_service_appliance_set(self, sas_uuid):
        return self._vnc.service_appliance_set_delete(id=sas_uuid)

    def create_service_appliance_pnf(self, sas_id, pnf_device,
            local_left_intf, local_right_intf, left_qfx, left_qfx_intf,
            right_qfx, right_qfx_intf, virtualization_type='physical-device'):
        default_gsc_name = 'default-global-system-config'
        sa_name = get_random_name('pnf_sa')
        sas_obj = self._vnc.service_appliance_set_read(id=sas_id)
        sa_obj = ServiceAppliance(sa_name, sas_obj)
        kvp_array = []
        kvp = KeyValuePair("left-attachment-point",
            ':'.join([default_gsc_name, left_qfx, left_qfx_intf]))
        kvp_array.append(kvp)
        kvp = KeyValuePair("right-attachment-point",
            ':'.join([default_gsc_name, right_qfx, right_qfx_intf]))
        kvp_array.append(kvp)
        kvps = KeyValuePairs()
        kvps.set_key_value_pair(kvp_array)
        sa_obj.set_service_appliance_properties(kvps)
        sa_obj.set_service_appliance_virtualization_type(
            virtualization_type)
        pnf_left_intf_obj = self._vnc.physical_interface_read(
            fq_name=[default_gsc_name, pnf_device, local_left_intf])
        attr = ServiceApplianceInterfaceType(interface_type='left')
        sa_obj.add_physical_interface(pnf_left_intf_obj, attr)
        pnf_right_intf_obj = self._vnc.physical_interface_read(
            fq_name=[default_gsc_name, pnf_device, local_right_intf])
        attr = ServiceApplianceInterfaceType(interface_type='right')
        sa_obj.add_physical_interface(pnf_right_intf_obj, attr)
        sa_uuid = self._vnc.service_appliance_create(sa_obj)
        return sa_uuid

    def delete_service_appliance(self, sa_uuid):
        return self._vnc.service_appliance_delete(id=sa_uuid)

    def create_port_tuple_pnf(self, si_id, left_lr, right_lr):
        pt_name = get_random_name('pnf_pt')
        si_obj = self._vnc.service_instance_read(id=si_id)
        pt_obj = PortTuple(pt_name, parent_obj=si_obj)
        left_lr_obj = self._vnc.logical_router_read(id=left_lr.uuid)
        right_lr_obj = self._vnc.logical_router_read(id=right_lr.uuid)
        pt_obj.add_logical_router(left_lr_obj)
        pt_obj.add_logical_router(right_lr_obj)
        kvp_array = []
        kvp = KeyValuePair("left-lr", left_lr.uuid)
        kvp_array.append(kvp)
        kvp = KeyValuePair("right-lr", right_lr.uuid)
        kvp_array.append(kvp)
        kvps = KeyValuePairs()
        kvps.set_key_value_pair(kvp_array)
        pt_obj.set_annotations(kvps)
        pt_uuid = self._vnc.port_tuple_create(pt_obj)
        return pt_uuid


    def delete_port_tuple(self, pt_uuid):
        try:
            self._vnc.port_tuple_delete(id=pt_uuid)
        except NoIdError:
            self._log.debug('Port tuple is deleted already.')

    def delete_hardware_inventory(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting hardware inventory %s' % kwargs)
        return self._vnc.hardware_inventory_delete(**kwargs)

    def update_storm_control_profile(self, uuid=None, fq_name=None, **kwargs):
        obj = self.read_storm_control_profile(id=uuid, fq_name=fq_name)
        params = obj.get_storm_control_parameters() or StormControlParameters()
        if 'action' in kwargs:
            params.set_storm_control_actions(kwargs['action'])
        if 'recovery_timeout' in kwargs:
            params.set_recovery_timeout(kwargs['recovery_timeout'])
        if 'bandwidth' in kwargs:
            params.set_bandwidth_percent(kwargs['bandwidth'])
        if 'no_broadcast' in kwargs:
            params.set_no_broadcast(kwargs['no_broadcast'])
        if 'no_unknown_unicast' in kwargs:
            params.set_no_unknown_unicast(kwargs['no_unknown_unicast'])
        if 'no_multicast' in kwargs:
            params.set_no_multicast(kwargs['no_multicast'])
        if 'no_registered_multicast' in kwargs:
            params.set_no_registered_multicast(kwargs['no_registered_multicast'])
        if 'no_unregistered_multicast' in kwargs:
            params.set_no_unregistered_multicast(kwargs['no_unregistered_multicast'])
        obj.set_storm_control_parameters(params)
        self._vnc.storm_control_profile_update(obj)

    def create_storm_control_profile(self, fq_name, action=None,
        recovery_timeout=None, bandwidth=None, no_broadcast=False,
        no_unknown_unicast=False, no_multicast=False,
        no_registered_multicast=False, no_unregistered_multicast=False):
        params = StormControlParameters()
        if action:
            params.set_storm_control_actions([action])
        if recovery_timeout:
            params.set_recovery_timeout(int(recovery_timeout))
        if bandwidth:
            params.set_bandwidth_percent(int(bandwidth))
        params.set_no_broadcast(no_broadcast)
        params.set_no_unknown_unicast(no_unknown_unicast)
        params.set_no_multicast(no_multicast)
        params.set_no_registered_multicast(no_registered_multicast)
        params.set_no_unregistered_multicast(no_unregistered_multicast)
        obj = StormControlProfile(name=fq_name[-1], parent_type='project',
                                  fq_name=fq_name,
                                  storm_control_parameters=params)
        uuid = self._vnc.storm_control_profile_create(obj)
        return uuid

    def delete_storm_control_profile(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting storm control profile %s' % kwargs)
        return self._vnc.storm_control_profile_delete(**kwargs)

    def read_storm_control_profile(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Reading storm control profile %s' % kwargs)
        return self._vnc.storm_control_profile_read(**kwargs)

    def create_port_profile(self, fq_name):
        obj = PortProfile(name=fq_name[-1], parent_type='project',
                          fq_name=fq_name)
        return self._vnc.port_profile_create(obj)

    def delete_port_profile(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting port profile %s' % kwargs)
        return self._vnc.port_profile_delete(**kwargs)

    def read_port_profile(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting port profile %s' % kwargs)
        return self._vnc.port_profile_read(**kwargs)

    def read_security_group(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting port profile %s' % kwargs)
        return self._vnc.security_group_read(**kwargs)

    def assoc_sc_to_port_profile(self, pp_uuid, sc_uuid):
        sc_obj = self.read_storm_control_profile(id=sc_uuid)
        obj = self.read_port_profile(id=pp_uuid)
        obj.add_storm_control_profile(sc_obj)
        return self._vnc.port_profile_update(obj)

    def disassoc_sc_from_port_profile(self, pp_uuid, sc_uuid):
        sc_obj = self.read_storm_control_profile(id=sc_uuid)
        obj = self.read_port_profile(id=pp_uuid)
        obj.del_storm_control_profile(sc_obj)
        return self._vnc.port_profile_update(obj)

    def assoc_security_group_to_vpg(self, sg_uuid, vpg_id):
        sg_obj = self.read_security_group(id=sg_uuid)
        obj = self.read_virtual_port_group(id=vpg_id)
        obj.add_security_group(sg_obj)
        return self._vnc.virtual_port_group_update(obj)

    def disassoc_security_group_from_vpg(self, sg_uuid, vpg_id):
        sg_obj = self.read_security_group(id=sg_uuid)
        obj = self.read_virtual_port_group(id=vpg_id)
        obj.del_security_group(sg_obj)
        return self._vnc.virtual_port_group_update(obj)

    def assoc_port_profile_to_vpg(self, pp_uuid, vpg_id):
        pp_obj = self.read_port_profile(id=pp_uuid)
        obj = self.read_virtual_port_group(id=vpg_id)
        obj.add_port_profile(pp_obj)
        return self._vnc.virtual_port_group_update(obj)

    def disassoc_port_profile_from_vpg(self, pp_uuid, vpg_id):
        pp_obj = self.read_port_profile(id=pp_uuid)
        obj = self.read_virtual_port_group(id=vpg_id)
        obj.del_port_profile(pp_obj)
        return self._vnc.virtual_port_group_update(obj)

    def assoc_port_profile_to_vmi(self, pp_uuid, vmi_id):
        pp_obj = self.read_port_profile(id=pp_uuid)
        obj = self.read_virtual_machine_interface(id=vmi_id)
        obj.add_port_profile(pp_obj)
        return self._vnc.virtual_machine_interface_update(obj)

    def disassoc_port_profile_from_vmi(self, pp_uuid, vmi_id):
        pp_obj = self.read_port_profile(id=pp_uuid)
        obj = self.read_virtual_machine_interface(id=vmi_id)
        obj.del_port_profile(pp_obj)
        return self._vnc.virtual_machine_interface_update(obj)

    def create_port(self, name, server, mac_address, tor_port, tor, switch_id):
        ll_info = LocalLinkConnection(port_id=tor_port,
                                      switch_id=switch_id,
                                      switch_info=tor)
        bms_port_info = BaremetalPortInfo(pxe_enabled=False,
                                          address=mac_address,
                                          local_link_connection=ll_info)
        obj = Port(name, parent_type='node',
                   fq_name=['default-global-system-config', server, name],
                   bms_port_info=bms_port_info)
        return self._vnc.port_create(obj)

    def delete_port(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting port %s' % kwargs)
        port_obj = self._vnc.port_read(**kwargs)
        pifs = port_obj.get_physical_interface_back_refs() or []
        for pif in pifs:
            pif_obj = self.read_physical_interface(id=pif['uuid'])
            pif_obj.del_port(port_obj)
            self._vnc.physical_interface_update(pif_obj)
        return self._vnc.port_delete(**kwargs)

    def create_node(self, name):
        bms_info = BaremetalServerInfo(network_interface='neutron',
            driver='pxe_ipmitool', name=name, type='baremetal')
        obj = Node(name, parent_type='global-system-config',
                   fq_name=['default-global-system-config', name],
                   node_type='baremetal', bms_info=bms_info,
                   hostname=name)
        return self._vnc.node_create(obj)

    def delete_node(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting node %s' % kwargs)
        return self._vnc.node_delete(**kwargs)

    def add_node_profile(self, node_name, node_profile_name):
        node_obj = self._vnc.node_read(fq_name=['default-global-system-config',
                                                node_name])
        np_fqname = ['default-global-system-config', node_profile_name]
        np_obj = self._vnc.node_profile_read(fq_name=np_fqname)
        node_obj.add_node_profile(np_obj)
        self._vnc.node_update(node_obj)

    def create_card(self, name, label, interfaces):
        ports = [PortInfoType(name=interface, labels=[label])
                 for interface in interfaces]
        obj = Card(name=name, interface_map=InterfaceMapType(port_info=ports))
        return self._vnc.card_create(obj)

    def create_hardware(self, name):
        obj = Hardware(name=name)
        return self._vnc.hardware_create(obj)

    def add_card(self, card_name, hardware_name):
        card_obj = self._vnc.card_read(fq_name=[card_name])
        hw_obj = self._vnc.hardware_read(fq_name=[hardware_name])
        hw_obj.add_card(card_obj)
        self._vnc.hardware_update(hw_obj)

    def create_node_profile(self, name, vendor, np_type):
        obj = NodeProfile(name=name, node_profile_type=np_type,
                          node_profile_vendor=vendor)
        return self._vnc.node_profile_create(obj)

    def add_hardware(self, hardware_name, node_profile_name):
        hw_obj = self._vnc.hardware_read(fq_name=[hardware_name])
        np_fqname = ['default-global-system-config', node_profile_name]
        np_obj = self._vnc.node_profile_read(fq_name=np_fqname)
        np_obj.add_hardware(hw_obj)
        self._vnc.node_profile_update(np_obj)

    def delete_node_profile(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting node profile %s' % kwargs)
        return self._vnc.node_profile_delete(**kwargs)

    def delete_hardware(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting hardware %s' % kwargs)
        return self._vnc.hardware_delete(**kwargs)

    def delete_card(self, **kwargs):
        '''
            :param fq_name : fqname of the object (list)
            :param fq_name_str : fqname of the object in string notation
            :param id : uuid of the object
        '''
        self._log.debug('Deleting card %s' % kwargs)
        return self._vnc.card_delete(**kwargs)

class LBFeatureHandles(with_metaclass(Singleton, object)):
    def __init__(self, vnc, log):
        self._vnc = vnc
        self._log = log
        self.get_lb_feature_handles()

    def get_lb_feature_handles(self):
        self.lb_mgr = ServiceLbManager(self._vnc, self._log)
        self.ll_mgr = ServiceLbListenerManager(self._vnc, self._log)
        self.lb_pool_mgr = ServiceLbPoolManager(self._vnc, self._log)
        self.lb_member_mgr = ServiceLbMemberManager(self._vnc, self._log)
        self.lb_hm_mgr = ServiceLbHealthMonitorManager(self._vnc, self._log)

# vn.get_floating_ip_pools()
# floating_ip_pool_delete
