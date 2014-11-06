import test
import pytun
import platform
#from common import isolated_creds

from fabric.context_managers import settings
from fabric.api import local, run
from tcutils.util import *
from common.connections import ContrailConnections

class BaseScaleTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseScaleTest, cls).setUpClass()
        ScaleTestConfig(cls.inputs).fixup_conf_and_restart_services()
        cls.connections= ContrailConnections(inputs= cls.inputs,
                                             logger= cls.logger)
        cls.vnc_lib= cls.connections.vnc_lib
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseScaleTest, cls).tearDownClass()
    #end tearDownClass 

    def get_role_dict(self, role_name='Member'):
        all_roles = self.keystone.roles.list()
        for x in all_roles:
            if (x.name == role_name):
                return x
        return None

    def get_user_dict(self, user_name=None):
        if not user_name:
            user_name=self.inputs.stack_user
        all_users = self.keystone.users.list()
        for x in all_users:
            if (x.name == user_name):
                return x
        return None

    def get_tenant_dict(self, project):
        return project.tenant_dict[project.project_name]

    def add_user_to_tenant(self, project):
        tenant = self.get_tenant_dict(project)
        self.keystone.tenants.add_user(tenant, self.user, self.role)

    def cleanup_before_test (self):
        cmd1 = 'python /opt/contrail/utils/del_projects.py --ip %s --port %s'%(
                                             '127.0.0.1', '8082')
        cmd2 = 'source /etc/contrail/openstackrc && keystone tenant-delete'
        for i in range(1, self.n_tenants + 1):
            with settings(warn_only=True):
                local('%s --proj project%s'%(cmd1, i))
                local('%s project%s'%(cmd2, i), shell='/bin/bash')
    #end cleanup_before_test

    @retry(delay=1, tries=10)
    def get_tap_intf(self, vm_fixture):
        for compute_ip in self.inputs.compute_ips:
            nova_host = self.inputs.host_data[compute_ip]
            vm_node_ip = nova_host['host_ip']
            inspect_h = vm_fixture.agent_inspect[vm_node_ip]
            vm_id = vm_fixture.vm_obj.id
            tap_intf_list = inspect_h.get_vna_tap_interface_by_vm(vm_id=vm_id)
            if tap_intf_list:
                tap_intf = tap_intf_list[0]['name']
            else:
                tap_intf = None
            if tap_intf:
                vm_fixture.vm_obj.__dict__['OS-EXT-SRV-ATTR:host'] = compute_ip
                return (True, tap_intf)
        else:
            return (False, None)

    def enable_tap_interface(self, vm_fixture):
        (status, tap_intf) = self.get_tap_intf(vm_fixture)
        if not status:
            raise Exception("Unable to find the tap interface")
        self.dummy_tap_open[tap_intf] = pytun.TapTunnel(pattern=tap_intf)

class ScaleTestConfig(object):
    def __init__(self, inputs):
        self.inputs = inputs

    def get_dist(self):
        return platform.linux_distribution()[0].lower()

    def get_python_path(self):
        dist = self.get_dist()   
        if dist in ['centos', 'fedora', 'redhat']:
            pythonpath = '/usr/lib/python2.6/site-packages'
        else:
            pythonpath = '/usr/lib/python2.7/dist-packages'
        return pythonpath

    def fixup_nova_config_file(self):
        pythonpath = self.get_python_path()
        with settings(warn_only=True):
            local("cp ./fakeTest.py %s/nova/virt/"%pythonpath)
            replace_string="scheduler_default_filters=RetryFilter,AvailabilityZoneFilter,ComputeFilter,ComputeCapabilitiesFilter,ImagePropertiesFilter"
            local("sed -i -e 's/connection_type.*$/connection_type=fakeTest/g' \
                                                       /etc/nova/nova.conf")
            local("sed -i -e 's/connection_type.*$/connection_type=fakeTest/g' \
                                               /etc/nova/nova-compute.conf")
            local("sed -i -e 's/compute_driver.*$/compute_driver=fakeTest.FakeTestDriver/g'\
                                                       /etc/nova/nova.conf")
            local("sed -i -e 's/compute_driver.*$/compute_driver=fakeTest.FakeTestDriver/g'\
                                               /etc/nova/nova-compute.conf")
            local("sed -i -e '/compute_driver.*$/a %s' \
                                       /etc/nova/nova.conf" %replace_string)

    def fixup_supervisor_openstack_files(self):
        with settings(warn_only=True):
            local("sed -i -e 's/minfds.*/minfds=65535/g' \
                  /etc/contrail/supervisord_openstack.conf")

    def fixup_keystone_files(self):
        pythonpath = self.get_python_path()
        with settings(warn_only=True):
            local("sed -i -e 's/threads=1000)/threads=65535)/g' \
                %s/keystone/common/environment/eventlet_server.py"%pythonpath)

    def fixup_memcached_config_file(self):
        with settings(warn_only=True):
            local("sed -i -e 's/-I.*m/-I 50m/g' /etc/memcached.conf")

    def fixup_config_files(self):
        self.fixup_nova_config_file()
        self.fixup_supervisor_openstack_files()
        self.fixup_keystone_files()
        self.fixup_memcached_config_file()

    def restart_services(self):
        self.inputs.restart_service('keystone')
        self.inputs.restart_service('memcached')
        self.inputs.restart_service('supervisor-openstack')
        self.inputs.restart_service('nova-compute')
        self.inputs.restart_service('nova-scheduler')
        time.sleep(15)

    def fixup_conf_and_restart_services(self):
        self.fixup_config_files()
        self.restart_services()
