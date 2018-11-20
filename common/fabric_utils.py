from fabric_test import FabricFixture
from physical_device_fixture import PhysicalDeviceFixture
from pif_fixture import PhysicalInterfaceFixture
from lif_fixture import LogicalInterfaceFixture
from bms_fixture import BMSFixture
from tcutils.util import retry, get_random_name
from lxml import etree
from tcutils.verification_util import elem2dict
import time

NODE_PROFILES = ['juniper-mx', 'juniper-qfx10k', 'juniper-qfx5k', 'juniper-qfx5k-lean']

class FabricUtils(object):
    def __init__(self, connections):
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = connections.logger
        self.vnc_h = connections.orch.vnc_h

    @retry(delay=10, tries=12)
    def _get_fabric_fixture(self, name):
        fabric = FabricFixture(connections=self.connections,
                               name=name)
        fabric.read()
        if not fabric.uuid:
            return (False, None)
        return (True, fabric)

    def onboard_existing_fabric(self, fabric_dict, wait_for_finish=True,
                                name=None, cleanup=False):
        interfaces = {'physical': [], 'logical': []}
        devices = list()
        
        name = get_random_name(name) if name else get_random_name('fabric')

        fq_name = ['default-global-system-config',
                   'existing_fabric_onboard_template']
        payload = {'fabric_fq_name': ["default-global-system-config", name],
                   'node_profiles': [{"node_profile_name": profile}
                       for profile in fabric_dict.get('node_profiles')\
                                      or NODE_PROFILES],
                   'device_auth': [{"username": cred['username'],
                                    "password": cred['password']}
                       for cred in fabric_dict['credentials']],
                   'overlay_ibgp_asn': fabric_dict['namespaces']['asn'][0]['min'],
                   'management_subnets': [{"cidr": mgmt["cidr"]}
                       for mgmt in fabric_dict['namespaces']['management']]
                  }
        self.logger.info('Onboarding existing fabric %s %s'%(name, payload))
        execution_id = self.vnc_h.execute_job(fq_name, payload)
        status, fabric = self._get_fabric_fixture(name)
        assert fabric, 'Create fabric seems to have failed'
        if cleanup:
            self.addCleanup(self.cleanup_fabric, fabric, devices, interfaces)
        if wait_for_finish:
            status = self.wait_for_job_to_finish(':'.join(fq_name), execution_id)
 
            assert status, 'job %s to create fabric failed'%execution_id
            for device in fabric.fetch_associated_devices() or []:
                device_fixture = PhysicalDeviceFixture(connections=self.connections,
                                                       name=device)
                device_fixture.read()
                device_fixture.add_csn()
                devices.append(device_fixture)
            for device in devices:
                for port in device.get_physical_ports():
                    pif = PhysicalInterfaceFixture(uuid=port, connections=self.connections)
                    pif.read()
                    interfaces['physical'].append(pif)
            for pif in interfaces['physical']:
                for port in pif.get_logical_ports():
                    lif = LogicalInterfaceFixture(uuid=port, connections=self.connections)
                    lif.read()
                    interfaces['logical'].append(lif)
        return (fabric, devices, interfaces)

    def cleanup_fabric(self, fabric, devices=None, interfaces=None,
                       verify=True, wait_for_finish=True):
        fq_name = ['default-global-system-config', 'fabric_deletion_template']
        payload = {'fabric_fq_name': fabric.fq_name}
        execution_id = self.vnc_h.execute_job(fq_name, payload)
        self.logger.info('Started cleanup of fabric %s'%(fabric.name))
        if wait_for_finish:
            status = self.wait_for_job_to_finish(':'.join(fq_name), execution_id)
            assert status, 'job %s to cleanup fabric failed'%execution_id
            if verify:
                for lif in interfaces['logical']:
                    assert lif.verify_on_cleanup()
                for pif in interfaces['physical']:
                    assert pif.verify_on_cleanup()
                for device in devices or []:
                    assert device.verify_on_cleanup()
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
            self.logger.info('cleanup discover status after wait_for_job_to_finish : %s' % status)
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

    def assign_roles(self, fabric, devices, rb_roles=None, wait_for_finish=True):
        ''' eg: rb_roles = {device1: ['CRB-Access'], device2: ['CRB-Gateway', 'DC-Gateway']}'''
        rb_roles = rb_roles or dict()
        roles_dict = dict()
        for device in devices:
            roles_dict.update({device: self.get_role_from_inputs(device.name)})
        fq_name = ['default-global-system-config', 'role_assignment_template']
        payload = {'fabric_fq_name': fabric.fq_name, 'role_assignments': list()}
        for device, role in roles_dict.iteritems():
            # ToDo: Need to revisit this post R5.0.1
            if role == 'leaf':
                routing_bridging_role = rb_roles.get(device.name, ['CRB-Access'])
            elif role == 'spine':
                routing_bridging_role = rb_roles.get(device.name, ['CRB-Gateway', 'Route-Reflector'])
            dev_role_dict = {'device_fq_name': ['default-global-system-config',
                                                device.name],
                             'physical_role': role,
                             'routing_bridging_roles': routing_bridging_role}
            payload['role_assignments'].append(dev_role_dict)
        execution_id = self.vnc_h.execute_job(fq_name, payload)
        self.logger.info('Started assigning roles for %s'%devices)
        if wait_for_finish:
            status = self.wait_for_job_to_finish(':'.join(fq_name), execution_id)
            assert status, 'job %s to assign roles failed'%execution_id
            #ToDo: Adding sleep since assign roles triggers internal playbook
            #which we are not able to track till completion
            time.sleep(120)
            return execution_id, status
        return execution_id, None

    @retry(delay=30, tries=90)
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
                dct = elem2dict(etree.fromstring(resp['ObjectLog']))
                log = dct['log_entry']['JobLogEntry']
                if log['name'] == job_name and \
                    log['execution_id'] == execution_id:
                    if log['status'].upper() == 'SUCCESS':
                        self.logger.debug('job %s with exec id %s finished'%(job_name, execution_id))
                        return True
                    elif log['status'].upper() == 'FAILURE':
                        raise Exception('job %s with exec id %s failed'%(job_name, execution_id))
            else:
                self.logger.warn('job %s with exec id %s hasnt completed'%(job_name, execution_id))
        else:
            self.logger.warn('Query failed for table ObjectJobExecutionTable. Will retry...')
        return False

    def create_bms(self, bms_name, **kwargs):
        self.logger.info('Creating bms %s'%bms_name)
        bms = self.useFixture(BMSFixture(
                              connections=self.connections,
                              name=bms_name,
                              **kwargs))
        if not kwargs.get('static_ip', False):
            status, msg = bms.run_dhclient()
            assert status, 'DHCP failed to fetch address'
        bms.verify_on_setup()
        return bms
