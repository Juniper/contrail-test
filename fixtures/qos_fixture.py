import pprint

import vnc_api_test
from vnc_api.vnc_api import QosQueue, ForwardingClass,\
    QosIdForwardingClassPairs, QosIdForwardingClassPair, QosConfig
from cfgm_common.exceptions import NoIdError

from tcutils.util import get_random_name, retry, compare_dict

global_qos_config_fq_str = ('default-global-system-config:'
                            'default-global-qos-config')


class QosBaseFixture(vnc_api_test.VncLibFixture):

    def __init__(self, *args, **kwargs):
        super(QosBaseFixture, self).__init__(self, *args, **kwargs)
        self.agent_inspect = None

    def setUp(self):
        super(QosBaseFixture, self).setUp()
        if self.connections:
            self.agent_inspect = self.connections.agent_inspect

    def cleanUp(self):
        super(QosBaseFixture, self).cleanUp()

    def get_parent_obj(self):
        if getattr(self, 'qos_config_type', None) == 'project':
            if self.connections:
                project_id = self.connections.project_id
            else:
                project_id = self.vnc_api_h.project_read(
                    fq_name_str='default-domain:default-project').uuid
            parent_obj = self.vnc_api_h.project_read(id=project_id)
        else:
            parent_obj = self.vnc_api_h.global_qos_config_read(fq_name_str=
                                                               global_qos_config_fq_str)
        return parent_obj
    # end get_parent_obj


class QosQueueFixture(QosBaseFixture):

    '''
    '''

    def __init__(self, *args, **kwargs):
        super(QosQueueFixture, self).__init__(self, *args, **kwargs)
        self.name = kwargs.get('name', get_random_name('qos_queue'))
        self.min_bandwidth = kwargs.get('min_bandwidth', None)
        self.max_bandwidth = kwargs.get('max_bandwidth', None)

    def setUp(self):
        super(QosQueueFixture, self).setUp()
        self.create()

    def cleanUp(self):
        super(QosQueueFixture, self).cleanUp()
        self.delete()

    def create(self):
        if self.uuid:
            return self.read()
        pass

    def read(self):
        pass

    def delete(self):
        pass


class QosForwardingClassFixture(QosBaseFixture):

    def __init__(self, *args, **kwargs):
        '''
        queue_uuid : UUID of QosQueue object
        '''
        super(QosForwardingClassFixture, self).__init__(self, *args, **kwargs)
        self.name = kwargs.get('name', get_random_name('fc'))
        self.fc_id = kwargs.get('fc_id', None)
        self.dscp = kwargs.get('dscp', None)
        self.dot1p = kwargs.get('dot1p', None)
        self.exp = kwargs.get('exp', None)
        self.uuid = kwargs.get('uuid', None)
        self.queue_uuid = kwargs.get('queue_uuid', None)

        self.is_already_present = False
        self.obj = None
        self.fq_name = None
        self.verify_is_run = False
        self.id = {}
    # end __init__

    def setUp(self):
        super(QosForwardingClassFixture, self).setUp()
        self.create()

    def cleanUp(self):
        super(QosForwardingClassFixture, self).cleanUp()
        self.delete()

    def create(self):
        if self.uuid:
            return self.read()
        fq_name = self.get_parent_obj().fq_name + [self.name]
        try:
            fc_obj = self.vnc_api_h.forwarding_class_read(fq_name=fq_name)
            self.uuid = fc_obj.uuid
            return self.read()
        except NoIdError, e:
            pass

        self.logger.info('Creating FC %s' % (fq_name))
        fc_obj = ForwardingClass(name=self.name,
                                 forwarding_class_id=self.fc_id,
                                 forwarding_class_dscp=self.dscp,
                                 forwarding_class_vlan_priority=self.dot1p,
                                 forwarding_class_mpls_exp=self.exp)

        if self.queue_uuid:
            queue_obj = self.vnc_api_h.qos_queue_read(id=self.queue_uuid)
        else:
            # WA for bug
            queue_obj = self.vnc_api_h.qos_queue_read(
                fq_name_str='%s:default-qos-queue' % (global_qos_config_fq_str))
        fc_obj.add_qos_queue(queue_obj)

        fc_uuid = self.vnc_api_h.forwarding_class_create(fc_obj)
        fc_obj = self.vnc_api_h.forwarding_class_read(id=fc_uuid)
        self._populate_attr(fc_obj)
    # end create

    def verify_on_setup(self):
        if not self.agent_inspect:
            self.logger.warn('Cluster information missing. Cannot proceed')
            return None
        if not self.verify_fc_in_all_agents():
            self.logger.error('Verification of FC %s in agent failed' % (
                self.fq_name))
            return False
        if not self.verify_fc_in_all_vrouters():
            self.logger.error('Verification of FC %s in vrouter failed' % (
                self.fq_name))
            return False
        self.verify_is_run = True
        return True
    # end verify_on_setup

    def verify_on_cleanup(self):
        if not self.verify_is_run:
            return
        msg = 'Cleanup verification of FC %s in agent failed' % (self.fq_name)
        assert self.verify_fc_not_in_all_agents(), msg
        msg = ('Cleanup verification of FC %s in vrouter failed' % (
                self.fq_name))
        assert self.verify_fc_not_in_all_vrouters(), msg
        return True
    # end verify_on_cleanup

    @retry(delay=2, tries=5)
    def verify_fc_in_all_agents(self):
        agent_fcs = {}
        for compute in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute]
            agent_fcs[compute] = inspect_h.get_agent_forwarding_class(
                self.uuid)
            if not agent_fcs[compute]:
                self.logger.warn('Qos FC %s not found in Compute %s' % (
                    self.uuid, compute))
                return False
        agent_fc_reference = agent_fcs[self.inputs.compute_ips[0]]

        # Check that all values are same across all agents
        for compute, agent_fc in agent_fcs.iteritems():
            self.id[compute] = agent_fc['id']
            (result, mismatches) = compare_dict(agent_fc, agent_fc_reference,
                                                ignore_keys=['id'])
            if not result:
                self.logger.warn('On Compute %s, mismatch found in qos fc'
                                 'entries, Unmatched items: %s' % (compute, mismatches))
                return False
        self.logger.info('Validated Qos FC UUID %s in agents of all '
                         ' computes' % (self.uuid))
        return True
    # end verify_fc_in_all_agents

    @retry(delay=2, tries=5)
    def verify_fc_not_in_all_agents(self):
        for compute in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute]
            agent_fc = inspect_h.get_agent_forwarding_class(self.uuid)
            if agent_fc:
                self.logger.warn('Qos FC %s is still in Compute %s' % (
                    self.uuid, compute))
                return False
        self.logger.info('Validated Qos FC UUID %s deleted in agents of all '
                         ' computes' % (self.uuid))
        return True
    # end verify_fc_not_in_all_agents


    @retry(delay=2, tries=5)
    def verify_fc_in_all_vrouters(self):
        vrouter_fcs = {}
        for compute in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute]
            vrouter_fcs[compute] = inspect_h.get_vrouter_forwarding_class(
                self.id[compute])
            if not vrouter_fcs[compute]:
                self.logger.warn('Qos FC %s not found in Compute vrouter %s' % (
                    self.id[compute], compute))
                return False
        vrouter_fc_reference = vrouter_fcs[self.inputs.compute_ips[0]]

        # Check that all values are same across all agents
        for compute, vrouter_fc in vrouter_fcs.iteritems():
            self.id[compute] = vrouter_fc['id']
            (result, mismatches) = compare_dict(vrouter_fc, vrouter_fc_reference,
                                                ignore_keys=['id'])
            if not result:
                self.logger.warn('On Compute %s(vrouter), mismatch found in qos fc'
                                 'entries, Unmatched items: %s' % (compute, mismatches))
                return False
        self.logger.info('Validated Qos FC UUID %s in vrouters of all '
                         'computes' % (self.uuid))
        return True
    # end verify_fc_in_all_vrouters

    @retry(delay=2, tries=5)
    def verify_fc_not_in_all_vrouters(self):
        for compute in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute]
            vrouter_fc = inspect_h.get_vrouter_forwarding_class(
                self.id[compute])
            if vrouter_fc:
                self.logger.warn('Qos FC %s still in Compute vrouter %s' % (
                    self.id[compute], compute))
                return False
        self.logger.info('Validated Qos FC UUID %s s deleted in vrouters '
                         'of all computes' % (self.uuid))
        return True
    # end verify_fc_not_in_all_vrouters

    def _populate_attr(self, fc_obj):
        self.obj = fc_obj
        self.fq_name = fc_obj.fq_name
        self.dscp = fc_obj.forwarding_class_dscp
        self.dot1p = fc_obj.forwarding_class_vlan_priority
        self.exp = fc_obj.forwarding_class_mpls_exp
        self.fc_id = fc_obj.forwarding_class_id
        self.uuid = fc_obj.uuid
        self.queue_uuid = fc_obj.get_qos_queue_refs()[0]['uuid']

    def read(self):
        try:
            fc_obj = self.vnc_api_h.forwarding_class_read(id=self.uuid)
            self.logger.info('Reading existing FC with UUID %s' % (
                             self.uuid))
        except NoIdError, e:
            self.logger.exception('UUID %s not found, unable to read FC' % (
                self.uuid))
            raise e

        self._populate_attr(fc_obj)
        self.is_already_present = True
    # end read

    def update(self, fc_id=None, dscp=None, dot1p=None, exp=None,
               queue_uuid=None):
        self.logger.info('Updating FC : fc_id: %s, dscp: %s, dot1p: %s, exp: %s,'
                         'queue: %s' % (fc_id, dscp, dot1p, exp, queue_uuid))
        fc_obj = self.vnc_api_h.forwarding_class_read(id=self.uuid)
        if fc_id:
            fc_obj.set_forwarding_class_id(fc_id)
        if dscp:
            fc_obj.set_forwarding_class_dscp(dscp)
        if dot1p:
            fc_obj.set_forwarding_class_vlan_priority(dot1p)
        if exp:
            fc_obj.set_forwarding_class_mpls_exp(exp)
        if queue_uuid:
            queue_obj = self.vnc_api_h.qos_queue_read(id=queue_uuid)
            fc_obj.set_qos_queue(queue_obj)
        self.vnc_api_h.forwarding_class_update(fc_obj)
        self._populate_attr(fc_obj)
    # end update

    def delete(self):
        if self.is_already_present:
            self.logger.info('Skipping deletion of FC %s' % (self.fq_name))
            return
        self.logger.info('Deleting FC %s, UUID: %s' %
                         (self.fq_name, self.uuid))
        self.vnc_api_h.forwarding_class_delete(id=self.uuid)
        self.verify_on_cleanup()
    # end delete


class QosConfigFixture(QosBaseFixture):

    ''' Fixture for QoSConfig
    dscp_mapping , dot1p_mapping and exp_mapping is a
    dict of code_points as key and ForwardingClass id as value

    qos_config_type: One of vhost/fabric/project, Default is project
    '''

    def __init__(self, *args, **kwargs):
        super(QosConfigFixture, self).__init__(self, *args, **kwargs)
        self.name = kwargs.get('name') or get_random_name('qos_config')
        self.qos_config_type = kwargs.get('qos_config_type') or 'project'
        self.uuid = kwargs.get('uuid', None)
        self.dscp_mapping = kwargs.get('dscp_mapping', {})
        self.dot1p_mapping = kwargs.get('dot1p_mapping', {})
        self.exp_mapping = kwargs.get('exp_mapping', {})
        self.vmi_uuid = kwargs.get('vmi_uuid', None)
        self.vn_uuid = kwargs.get('vn_uuid', None)

        self.is_already_present = False
        self.parent_obj = None
        self.id = {}

    def setUp(self):
        super(QosConfigFixture, self).setUp()
        self.create()

    def cleanUp(self):
        super(QosConfigFixture, self).cleanUp()
        self.delete()

    def _get_code_point_to_fc_map(self, mapping_dict=None):
        if not mapping_dict:
            return None
        new_map = QosIdForwardingClassPairs()
        for k, v in mapping_dict.iteritems():
            pair = QosIdForwardingClassPair(k, v)
            new_map.add_qos_id_forwarding_class_pair(pair)
        return new_map
    # end _get_code_point_to_fc_map

    def create(self):
        if self.uuid:
            return self.read()
        fq_name = self.get_parent_obj().fq_name + [self.name]
        try:
            qos_config_obj = self.vnc_api_h.qos_config_read(fq_name=fq_name)
            self.uuid = qos_config_obj.uuid
            return self.read()
        except NoIdError, e:
            pass

        self.logger.info('Creating QosConfig %s' % (fq_name))
        if self.qos_config_type == 'project':
            if self.connections:
                project_id = self.connections.project_id
            else:
                project_id = self.vnc_api_h.project_read(
                    fq_name_str='default-domain:default-project').uuid
            parent_obj = self.vnc_api_h.project_read(id=project_id)
        else:
            parent_obj = self.vnc_api_h.global_qos_config_read(fq_name_str=
                                                               global_qos_config_fq_str)
        self.parent_obj = parent_obj

        dscp_entries = self._get_code_point_to_fc_map(self.dscp_mapping)
        dot1p_entries = self._get_code_point_to_fc_map(self.dot1p_mapping)
        exp_entries = self._get_code_point_to_fc_map(self.exp_mapping)

        qos_config_obj = QosConfig(name=self.name,
                                   parent_obj=self.parent_obj,
                                   dscp_entries=dscp_entries,
                                   vlan_priority_entries=dot1p_entries,
                                   mpls_exp_entries=exp_entries,
                                   qos_config_type=self.qos_config_type)
        self.uuid = self.vnc_api_h.qos_config_create(qos_config_obj)
        self.qos_config_obj = self.vnc_api_h.qos_config_read(id=self.uuid)
        self._populate_attr()
    # end create

    def set_entries(self, dscp_mapping=None, dot1p_mapping=None, exp_mapping=None):
        ''' If the user wants to clear the entries, {} needs to be passed
        '''
        self.logger.info('Updating qos-config: dscp_mapping: %s,'
                         'dot1p_mapping: %s, exp_mapping: %s' % (dscp_mapping,
                                                                 dot1p_mapping, exp_mapping))
        self.qos_config_obj = self.vnc_api_h.qos_config_read(id=self.uuid)
        if dscp_mapping is not None:
            dscp_entries = self._get_code_point_to_fc_map(dscp_mapping)
            self.qos_config_obj.set_dscp_entries(dscp_entries)
        if dot1p_mapping is not None:
            dot1p_entries = self._get_code_point_to_fc_map(dot1p_mapping)
            self.qos_config_obj.set_vlan_priority_entries(dot1p_entries)
        if exp_mapping is not None:
            exp_entries = self._get_code_point_to_fc_map(exp_mapping)
            self.qos_config_obj.set_mpls_exp_entries(exp_entries)
        self.vnc_api_h.qos_config_update(self.qos_config_obj)
        self._populate_attr()
    # end set_entries

    def _add_to_entries(self, dscp_mapping=None, dot1p_mapping=None, exp_mapping=None):
        self.logger.debug('Adding FC entries, dscp:%s, dot1p: %s, exp: %s' % (
            dscp_mapping, dot1p_mapping, exp_mapping))
        if dscp_mapping:
            for k, v in dscp_mapping.iteritems():
                entry = QosIdForwardingClassPair(k, v)
                self.qos_config_obj.dscp_entries.add_qos_id_forwarding_class_pair(
                    entry)
                self.qos_config_obj.set_dscp_entries(
                    self.qos_config_obj.dscp_entries)
        if dot1p_mapping:
            for k, v in dot1p_mapping.iteritems():
                entry = QosIdForwardingClassPair(k, v)
                self.qos_config_obj.vlan_priority_entries.add_qos_id_forwarding_class_pair(
                    entry)
                self.qos_config_obj.set_vlan_priority_entries(
                    self.qos_config_obj.vlan_priority_entries)
        if exp_mapping:
            for k, v in exp_mapping.iteritems():
                entry = QosIdForwardingClassPair(k, v)
                self.qos_config_obj.mpls_exp_entries.add_qos_id_forwarding_class_pair(
                    entry)
                self.qos_config_obj.set_mpls_exp_entries(
                    self.qos_config_obj.mpls_exp_entries)
        self.vnc_api_h.qos_config_update(self.qos_config_obj)
    # end _add_to_entries

    def add_entries(self, dscp_mapping=None, dot1p_mapping=None, exp_mapping=None):
        ''' Add one or more code-point to fc mappings to existing qos-config entries
        '''
        self.qos_config_obj = self.vnc_api_h.qos_config_read(id=self.uuid)
        if dscp_mapping:
            self._add_to_entries(dscp_mapping=dscp_mapping)
        if dot1p_mapping:
            self._add_to_entries(dot1p_mapping=dot1p_mapping)
        if exp_mapping:
            self._add_to_entries(exp_mapping=exp_mapping)
        self._populate_attr()
    # end add_entries

    def get_code_point_entry(self, dscp=None, dot1p=None, exp=None):
        ''' Return QosIdForwardingClassPair object for the argument
        '''
        entries = None
        value = dscp or dot1p or exp
        if dscp:
            entries = self.qos_config_obj.dscp_entries
        if dot1p:
            entries = self.qos_config_obj.vlan_priority_entries
        if exp:
            entries = self.qos_config_obj.mpls_exp_entries

        if entries:
            pairs = entries.get_qos_id_forwarding_class_pair()
            entry = [x for x in pairs if x.key == value]
            if entry:
                return entry[0]
    # end get_code_point_entry

    def del_entry(self, dscp=None, dot1p=None, exp=None):
        ''' Remove the entry from qos config which has the code-point
        '''
        self.qos_config_obj = self.vnc_api_h.qos_config_read(id=self.uuid)
        self.logger.info('Removing entry for key dscp:%s, dot1p:%s, exp:%s' % (
            dscp, dot1p, exp))

        dscp_entry = self.get_code_point_entry(dscp=dscp)
        if dscp_entry:
            self.qos_config_obj.dscp_entries.delete_qos_id_forwarding_class_pair(
                dscp_entry)
            self.qos_config_obj.set_dscp_entries(
                self.qos_config_obj.dscp_entries)
        dot1p_entry = self.get_code_point_entry(dot1p=dot1p)
        if dot1p_entry:
            self.qos_config_obj.dscp_entries.delete_qos_id_forwarding_class_pair(
                dot1p_entry)
            self.qos_config_obj.set_vlan_priority_entries(
                self.qos_config_obj.vlan_priority_entries)
        exp_entry = self.get_code_point_entry(exp=exp)
        if exp_entry:
            self.qos_config_obj.dscp_entries.delete_qos_id_forwarding_class_pair(
                exp_entry)
            self.qos_config_obj.set_mpls_exp_entries(
                self.qos_config_obj.mpls_exp_entries)
        self.vnc_api_h.qos_config_update(self.qos_config_obj)
        self._populate_attr()
    # end del_entry

    def _populate_attr(self, qos_config_obj=None):
        if not qos_config_obj:
            qos_config_obj = self.qos_config_obj
        self.uuid = qos_config_obj.uuid
        self.fq_name = qos_config_obj.fq_name
        self.qos_config_type = qos_config_obj.get_qos_config_type()
        self.dscp_entries = qos_config_obj.dscp_entries
        self.dot1p_entries = qos_config_obj.vlan_priority_entries
        self.mpls_exp_entries = qos_config_obj.mpls_exp_entries

    def read(self):
        try:
            self.qos_config_obj = self.vnc_api_h.qos_config_read(id=self.uuid)
            self.logger.info('Reading existing qos-config with UUID %s' % (
                             self.uuid))
        except NoIdError, e:
            self.logger.exception('UUID %s not found, cant read qos config' % (
                self.uuid))
            raise e

        if self.qos_config_type == 'project':
            self.parent_obj = self.vnc_api_h.project_read(
                id=self.qos_config_obj.parent_uuid)
        else:
            self.parent_obj = self.vnc_api_h.global_qos_config_read(fq_name_str=
                                                                    global_qos_config_fq_str)
        self._populate_attr()
        self.is_already_present = True
    # end read

    def delete(self):
        if self.is_already_present:
            self.logger.info('Skipping deletion of qos config %s' %
                             (self.fq_name))
            return
        self.logger.info('Deleting Qos config %s, UUID: %s' % (self.fq_name,
                                                               self.uuid))
        self.vnc_api_h.qos_config_delete(id=self.uuid)
        self.verify_on_cleanup()
    # end delete

    def apply_to_vmi(self, vmi_uuid):
        self.logger.info('Applying qos-config on VM %s' % (vmi_uuid))
        vmi_obj = self.vnc_api_h.virtual_machine_interface_read(id=vmi_uuid)
        vmi_obj.add_qos_config(self.qos_config_obj)
        self.vnc_api_h.virtual_machine_interface_update(vmi_obj)
    # end apply_to_vmi

    def remove_from_vmi(self, vmi_uuid):
        self.logger.info('Removing qos-config on VM %s' % (vmi_uuid))
        vmi_obj = self.vnc_api_h.virtual_machine_interface_read(id=vmi_uuid)
        vmi_obj.del_qos_config(self.qos_config_obj)
        self.vnc_api_h.virtual_machine_interface_update(vmi_obj)
    # end remove_from_vmi

    def apply_to_vn(self, vn_uuid):
        self.logger.info('Applying qos-config on VN %s' % (vn_uuid))
        vn_obj = self.vnc_api_h.virtual_network_read(id=vn_uuid)
        vn_obj.add_qos_config(self.qos_config_obj)
        self.vnc_api_h.virtual_network_update(vn_obj)
    # end apply_to_vn

    def remove_from_vn(self, vn_uuid):
        self.logger.info('Removing qos-config on VN %s' % (vn_uuid))
        vn_obj = self.vnc_api_h.virtual_network_read(id=vn_uuid)
        vn_obj.del_qos_config(self.qos_config_obj)
        self.vnc_api_h.virtual_network_update(vn_obj)
    # end remove_from_vn

    def verify(self):
        return self.verify_on_setup(self)

    def verify_on_setup(self):
        if not self.agent_inspect:
            self.logger.warn('Cluster information missing. Cannot proceed')
            return None
        if not self.verify_qos_config_in_all_agents():
            self.logger.error('Verification of Qos config %s in agent failed' % (
                self.fq_name))
            return False
        if not self.verify_qos_config_in_all_vrouters():
            self.logger.error('Verification of Qos config %s in vrouter failed' % (
                self.fq_name))
            return False
        # TODO
        # Check if any vmi mappings and validate the same
        # Do it for both agent and vrouter
        self.verify_is_run = True
        return True
    # end verify_on_setup

    def verify_on_cleanup(self):
        if not self.verify_is_run:
            return
        msg = ('Cleanup verification of Qos config %s in '
                 ' agent failed' % (self.fq_name))
        assert self.verify_qos_config_not_in_all_agents(), msg
        msg = ('Cleanup verification of Qos config %s in '
                ' vrouter failed' % (self.fq_name))
        assert self.verify_qos_config_not_in_all_vrouters(), msg
        return True
    # end verify_on_cleanup


    @retry(delay=2, tries=5)
    def verify_qos_config_in_all_agents(self):
        agent_qcs = {}
        for compute in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute]
            agent_qcs[compute] = inspect_h.get_agent_qos_config(self.uuid)
            if not agent_qcs[compute]:
                self.logger.warn('Qos Config %s not found in Compute %s' % (
                    self.uuid, compute))
                return False
        agent_qc_reference = agent_qcs[self.inputs.compute_ips[0]]

        # Check that all values are same across all agents
        for (compute, agent_qc) in agent_qcs.iteritems():
            self.id[compute] = agent_qc['id']
            (result, mismatches) = compare_dict(agent_qc, agent_qc_reference,
                                                ignore_keys=['id'])
            if not result:
                self.logger.warn('On Compute %s, mismatch found in qos config'
                                 'entries, Unmatched items: %s' % (compute, mismatches))
                return False
        self.logger.info('Validated Qos Config UUID %s in agents of all '
                         ' computes' % (self.uuid))
        return True
    # end verify_qos_config_in_all_agents

    @retry(delay=2, tries=5)
    def verify_qos_config_in_all_vrouters(self):
        vrouter_qcs = {}
        for compute in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute]
            vrouter_qcs[compute] = inspect_h.get_vrouter_qos_config(
                self.id[compute])
            if not vrouter_qcs[compute]:
                self.logger.warn('Qos config %s not found in Compute vrouter %s' % (
                    self.id[compute], compute))
                return False
        vrouter_qc_reference = vrouter_qcs[self.inputs.compute_ips[0]]

        # Check that all values are same across all agents
        for compute, vrouter_qc in vrouter_qcs.iteritems():
            self.id[compute] = vrouter_qc['id']
            (result, mismatches) = compare_dict(vrouter_qc, vrouter_qc_reference,
                                                ignore_keys=['id'])
            if not result:
                self.logger.warn('On Compute %s(vrouter), mismatch in qos config'
                                 ' entries, Mismatched items: %s' % (compute, mismatches))
                return False
        self.logger.info('Validated Qos Config UUID %s in vrouter of all computes' % (
                         self.uuid))
        return True
    # end verify_qos_config_in_all_vrouters

    @retry(delay=2, tries=5)
    def verify_qos_config_not_in_all_agents(self):
        for compute in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute]
            agent_qc = inspect_h.get_agent_qos_config(self.uuid)
            if agent_qc:
                self.logger.warn('Qos Config is in %s Compute %s' % (
                    self.uuid, compute))
                return False
        self.logger.info('Validated Qos Config UUID %s is deleted in agents '
                         ' of all computes' % (self.uuid))
        return True
    # end verify_qos_config_not_in_all_agents

    @retry(delay=2, tries=5)
    def verify_qos_config_not_in_all_vrouters(self):
        for compute in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute]
            vrouter_qc = inspect_h.get_vrouter_qos_config(self.id[compute])
            if vrouter_qc:
                self.logger.warn('Qos config %s is still in Compute vrouter %s' % (
                    self.id[compute], compute))
                return False
        self.logger.info('Validated Qos Config UUID %s is deleted in  vrouter '
                         'of all computes' % (self.uuid))
        return True
    # end verify_qos_config_not_in_all_vrouters

# end QosConfigFixture


if __name__ == "__main__":
    fc_fixture = QosForwardingClassFixture(
        name='fc0', dscp=10, dot1p=2, exp=2, fc_id=0, auth_server_ip='192.168.192.251', cfgm_ip='192.168.192.6')
    fc_fixture.setUp()
    import pdb
    pdb.set_trace()
    dscp_map = {1: fc_fixture.fc_id}
    dscp_map1 = {2: fc_fixture.fc_id}
    qos_config_fixture = QosConfigFixture(
        name='qos_config1', dscp_mapping=dscp_map, auth_server_ip='192.168.192.251', cfgm_ip='192.168.192.6')
    qos_config_fixture.setUp()
    import pdb
    pdb.set_trace()
    qos_config_fixture.add_entries(dscp_mapping=dscp_map1)
    qos_config_fixture.del_entry(dscp=2)
    qos_config_fixture.add_entries(dscp_mapping=dscp_map1)
    qos_config_fixture.del_entry(dscp=1)
    qos_config_fixture.cleanUp()
    fc_fixture.cleanUp()
