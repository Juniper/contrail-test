from fabric_test import FabricFixture
from physical_device_fixture import PhysicalDeviceFixture
from pif_fixture import PhysicalInterfaceFixture
from lif_fixture import LogicalInterfaceFixture
from tcutils.util import retry
from lxml import etree
from tcutils.verification_util import elem2dict

class FabricUtils(object):
    @classmethod
    def create_only_fabric(cls, namespaces=None, creds=None):
        '''
        :param namespaces : namespaces in below format
                        eg: {'management': [{'cidr': '1.1.1.0/24',
                                             'gateway': '1.1.1.254'}],
                             'loopback': ['10.1.1.0/25'],
                             'peer': ['172.16.0.0/16'],
                             'asn': [{'max': 64512, 'min': 64512}],
                             'ebgp_asn': [{'max': 64512, 'min': 64512}]}
        :param creds : list of creds in the below format
                   eg: [{'username': 'root', 'password': 'c0ntrail123',
                         'vendor': 'Juniper', 'device_family': 'qfx'}]
        '''
        fabric = FabricFixture(connections=cls.connections,
                               namespaces=namespaces,
                               creds=creds)
        fabric.setUp()
        return fabric

    def create_fabric(self, namespaces=None, creds=None):
        fabric = self.create_only_fabric(namespaces=namespaces,
                                         creds=creds)
        self.logger.info('Created fabric %s'%fabric.name)
        self.addCleanup(self.cleanup_fabric, fabric)
        return fabric

    def cleanup_fabric(self, fabric, wait_for_finish=False):
        fq_name = ['default-global-system-config', 'fabric_deletion_template']
        payload = {'fabric_fq_name': fabric.fq_name}
        execution_id = self.vnc_h.execute_job(fq_name, payload)
        self.logger.info('Started cleanup of fabric %s'%(fabric.name))
        if wait_for_finish:
            status = self.wait_for_job_to_finish(':'.join(fq_name), execution_id)
            assert status, 'job %s to cleanup fabric failed'%execution_id
            assert fabric.verify_on_cleanup()
        return execution_id

    def discover(self, fabric, wait_for_finish=True):
        devices = list()
        fq_name = ['default-global-system-config', 'discover_device_template']
        payload = {'fabric_uuid': fabric.uuid}
        execution_id = self.vnc_h.execute_job(fq_name, payload)
        self.logger.info('Started device discovery for fabric %s'%(
                         fabric.name))
        self.addCleanup(self.cleanup_discover, fabric, devices)
        if wait_for_finish:
            status = self.wait_for_job_to_finish(':'.join(fq_name), execution_id)
            assert status, 'job %s to discover devices failed'%execution_id
            for device in fabric.fetch_associated_devices() or []:
                device_fixture = PhysicalDeviceFixture(connections=self.connections,
                                                       name=device)
                device_fixture.read()
                device_fixture.add_csn()
                devices.append(device_fixture)
            self.logger.info('discovered devices %s for fabric %s'%(
                             devices, fabric.name))
        return execution_id, devices

    def cleanup_discover(self, fabric, devices=None, wait_for_finish=True):
        device_list = [device.uuid for device in devices or []]
        self.logger.info('Cleanup discovered devices %s for fabric %s'%(
                         device_list, fabric.name))
#        fabric.disassociate_devices()
#        for device in devices or []:
#            device.cleanUp(force=True)
        fq_name = ['default-global-system-config', 'device_deletion_template']
        payload = {'fabric_fq_name': fabric.fq_name}
        execution_id = self.vnc_h.execute_job(fq_name, payload, device_list)
        if wait_for_finish:
            status = self.wait_for_job_to_finish(':'.join(fq_name), execution_id)
            assert status, 'job %s to delete devices %s failed'%(
                   execution_id, device_list)
            for device in devices or []:
                assert device.verify_on_cleanup()
        return execution_id

    def get_filters(self, filters):
        filters = filters if filters is not None else ['^ge', '^xe', '^ae', '^em', '^lo']
        if not filters:
             return {}
        filter_dict = {'interface_filters': []}
        for fltr in filters or []:
            dct = {'op': 'regex', 'expr': fltr}
            filter_dict['interface_filters'].append(dct)
        return filter_dict

    def onboard(self, devices, filters=None, wait_for_finish=True):
        interfaces = {'physical': [], 'logical': []}
        fq_name = ['default-global-system-config', 'device_import_template']
        payload = self.get_filters(filters)
        device_list = [device.uuid for device in devices]
        execution_id = self.vnc_h.execute_job(fq_name, payload, device_list)
        self.logger.info('Started onboarding devices %s'%devices)
        self.addCleanup(self.cleanup_onboard, devices, interfaces)
        if wait_for_finish:
            status = self.wait_for_job_to_finish(':'.join(fq_name), execution_id)
            assert status, 'job %s to onboard devices failed'%execution_id
            for device in devices:
                for port in device.get_physical_ports():
                    pif = PhysicalInterfaceFixture(uuid=port, connections=self.connections)
                    pif._clear_cleanups()
                    pif.read()
                    interfaces['physical'].append(pif)
            for pif in interfaces['physical']:
                for port in pif.get_logical_ports():
                    lif = LogicalInterfaceFixture(uuid=port, connections=self.connections)
                    lif._clear_cleanups()
                    lif.read()
                    interfaces['logical'].append(lif)
            return execution_id, interfaces
        return execution_id, None

    def cleanup_onboard(self, devices, interfaces):
        self.logger.info('Cleaning up onboarded devices %s'%devices)
        for lif in interfaces['logical']:
            lif.cleanUp(force=True)
            #assert lif.verify_on_cleanup()
        for pif in interfaces['physical']:
            pif.cleanUp(force=True)
            #assert pif.verify_on_cleanup()

    def configure_underlay(self, devices, payload=None, wait_for_finish=True):
        payload = payload or dict()
        payload.update({'enable_lldp': 'true'})
        fq_name = ['default-global-system-config', 'generate_underlay_template']
        device_list = [device.uuid for device in devices]
        execution_id = self.vnc_h.execute_job(fq_name, payload, device_list)
        self.logger.info('Started configuring devices %s'%devices)
        if wait_for_finish:
            status = self.wait_for_job_to_finish(':'.join(fq_name), execution_id)
            assert status, 'job %s to configure underlay failed'%execution_id
            return execution_id, status
        return execution_id, None

    def get_role_from_inputs(self, device_name):
        for device in self.inputs.physical_routers_data.itervalues():
            if device['name'] == device_name:
                return device['role']

    def assign_roles(self, devices):
        ''' eg: {device1Fixture: 'spine', device2Fixture: 'leaf'}'''
        roles_dict = dict()
        for device in devices:
            roles_dict.update({device: self.get_role_from_inputs(device.name)})
        for device, role in roles_dict.iteritems():
            device.assign_role(role)
        '''
        fq_name = ['default-global-system-config', 'role_assignment_template']
        payload = {'role_assignments': list()}
        for device, role in device_role_dict.iteritems():
            dev_role_dict = {'device_fq_name': ['default-global-system-config',
                                                device.name],
                             'physical_role': role}
            payload['role_assignments'].append(dev_role_dict)
        execution_id = self.vnc_h.execute_job(fq_name, payload)
        self.logger.info('Started configuring devices %s'%devices)
        if wait_for_finish:
            status = self.wait_for_job_to_finish(':'.join(fq_name), execution_id)
            assert status, 'job %s to configure underlay failed'%execution_id
            return execution_id, status
        return execution_id, None
        '''

    @retry(delay=10, tries=60)
    def wait_for_job_to_finish(self, job_name, execution_id, start_time='now-10m'):
        ops_h = self.connections.ops_inspects[self.inputs.collector_ips[0]]
        table = 'ObjectJobExecutionTable'
        query = '(Messagetype=JobLog)'
        response = ops_h.post_query(table, start_time=start_time,
                                    end_time='now',
                                    select_fields=['MessageTS', 'Messagetype', 'ObjectLog'],
                                    where_clause=query)
        if response:
            for resp in response:
#                try:
                    dct = elem2dict(etree.fromstring(resp['ObjectLog']))
                    log = dct['log_entry']['JobLogEntry']
                    if log['name'] == job_name and \
                       log['execution_id'] == execution_id:
                       if log['status'].upper() == 'SUCCESS':
                           self.logger.debug('job %s with exec id %s finished'%(job_name, execution_id))
                           return True
                       elif log['status'].upper() == 'FAILURE':
                           raise Exception('job %s with exec id %s failed'%(job_name, execution_id))
#                except Exception as e:
#                    self.logger.debug('Wait for job finish raised %s'%e)
            else:
                self.logger.warn('job %s with exec id %s hasnt completed'%(job_name, execution_id))
        else:
            self.logger.warn('Query failed for table ObjectJobExecutionTable. Will retry...')
        return False
