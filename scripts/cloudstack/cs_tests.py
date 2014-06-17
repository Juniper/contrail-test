# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import signal
import re
import unittest
import fixtures
import testtools
import cloudclient
from contrail_test_init import *
from vn_test import *
from vnc_api_test import *
from vm_test import *
from connections import ContrailConnections
from cs_floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile,StandardProfile, BurstProfile,ContinuousSportRange
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
#from analytics_tests import *
from cs_vpc import *
from fabric.state import connections

class TestCSSanity(testtools.TestCase, fixtures.TestWithFixtures):

    @retry(delay=30, tries=20)
    def isSystemVmUp(self):
        client = self.connections.cstack_handle.client
        result = client.request('listSystemVms')
        self.logger.info( str(result) )
        response = result['listsystemvmsresponse']
        count = response['count']
        if response['count'] == 2:
            for systemvm in response['systemvm']:
                if systemvm['state'] != "Running":
                    self.logger.info( "System VM %s is not running. Current state %s" %(systemvm['systemvmtype'], systemvm['state']))
                    return False
            return True
        print response
        return False

    def setUp(self):
        super(TestCSSanity, self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'
        self.inputs=self.useFixture(ContrailTestInit(self.ini_file, environ= 'cstack'))
        self.connections= ContrailConnections(self.inputs)
        self.network_handle= self.connections.network_handle
        self.vnc_lib= self.connections.vnc_lib
        self.logger= self.inputs.logger
        self.agent_inspect= self.connections.agent_inspect
        self.cn_inspect= self.connections.cn_inspect
        self.analytics_obj=self.connections.analytics_obj
        #isSystemVmUp(self)
    #end setUpClass

    def cleanUp(self):
        super(TestCSSanity, self).cleanUp()
    #end cleanUp

    def runTest(self):
        pass
    #end runTest

    @preposttest_wrapper
    def test_vn_add_delete(self):
        '''Test to validate VN creation and deletion.
        '''
        vn_obj=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name='vn22', inputs= self.inputs, subnets=['10.1.1.0/24'] ))
        assert vn_obj.verify_on_setup()
        return True
    #end

    @preposttest_wrapper
    def test_vm_add_delete(self):
        ''' Test to validate that a VM creation and deletion passes.
        '''
        vm1_name='vm-mine2'
        vn_name='vn229'
        vn_subnets=['10.3.9.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        return True
    #end test_vm_add_delete

    @preposttest_wrapper
    def test_ping_within_vn(self):
        ''' Validate Ping between two VMs within a VN.

        '''
        vn1_name='vn31'
        vn1_subnets=['10.1.1.0/24']
        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, flavor= "medium", vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, flavor= "small", vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )
        return True
    #end test_ping_within_vn

    @preposttest_wrapper
    def test_vms_in_project(self):
        ''' Validate that VMs can be created in a new project
        '''
        project_name= 'custom_project'
        vn1_name='custom-vn32'
        vn1_subnets=['10.1.2.0/24']
        vn1_vm1_name = vn1_name+'-vn1-vm1'
        vn1_vm2_name = vn1_name+'-vn1-vm2'
        project_fixture= self.useFixture(ProjectFixture( connections= self.connections, vnc_lib_h = self.vnc_lib, project_name = project_name ) )
        vn1_fixture= self.useFixture(VNFixture(project_name= project_fixture.project_name, connections= self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        vm1_fixture= self.useFixture(VMFixture(project_name= project_fixture.project_name, connections= self.connections,  vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= project_fixture.project_name, connections= self.connections,  vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        assert vm1_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn1_vm1_name)
        assert vm2_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn1_vm2_name)
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip ), "Ping between VMs in a new project failed!"
        return True
    #end test_vms_in_project

    @preposttest_wrapper
    def test_vsrx_guest_vm_with_ping(self):
        '''Validate creating vSRX instance in custom project, create VM and reach outside world
        '''

        def createVSRXOffering(client):
            result = client.request('listServiceOfferings',
                                    {'name': 'System Offering for vSRX',
                                     'isSystem': 'True'})
            response = result['listserviceofferingsresponse']
            if 'serviceoffering' in response:
                return response['serviceoffering'][0]['id']

            params = {
                'name': 'System Offering for vSRX',
                'displaytext': "System Offering for vSRX",
                'cpunumber': 2,
                'memory': 2048,
                'systemvmtype': 'domainrouter',
                'cpuspeed': 500,
                'issystem': True
             }

            result = client.request('createServiceOffering', params)
            return result['createserviceofferingresponse']['serviceoffering']['id']

        #end createVSRXOffering

        def getSystemNetwork(client, traffictype):
            params = {
                'traffictype': traffictype,
                'issystem': True,
            }
            result = client.request('listNetworks', params)
            return result['listnetworksresponse']['network'][0]['id']

        #end getSystemNetwork

        def getZone(client, name):
            result = client.request('listZones', {'name': name})
            return result['listzonesresponse']['zone'][0]['id']

        #end getZone

        def getTemplate(client, tmpl_name):
            result = client.request('listTemplates',
                                    {'templatefilter': 'executable',
                                     'name': tmpl_name})
            return result['listtemplatesresponse']['template'][0]['id']

        #end getTemplate

        def createVSRX(client, zoneid, project_id, networks, tmpl_vsrx, offer_id):
            self.instance_handle = self.connections.instance_handle
            params = {
                'zoneid': zoneid,
                'projectid': project_id,
                'name': 'vSRX appliance',
                'leftnetworkid': networks[0],
                'rightnetworkid': networks[1],
                'templateid': tmpl_vsrx,
                'serviceofferingid': offer_id,
                'displayname': 'vSRX appliance',
            }
            result = client.request('createServiceInstance', params)
            print result
            return result
        #end createVSRX

        client = self.connections.cstack_handle.client
        project_name = 'a_new_proj_' ##WA for a bug in CS
        vn1_name='__service__'
        vn1_subnets=['10.254.254.0/24']
        project_fixture = self.useFixture(ProjectFixture(connections = self.connections, vnc_lib_h = self.vnc_lib,
        project_name = project_name))
        project_id = project_fixture.cs_project_obj['id']
        vn1_fixture= self.useFixture(VNFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))

        offer_id = createVSRXOffering(client)
        projectnetwork = vn1_fixture.vn_id
        systemnetwork = getSystemNetwork(client, 'Public')
        networks = [projectnetwork, systemnetwork]
        zoneid = getZone(client, 'default')
        tmpl_vsrx = getTemplate(client, 'Juniper vSRX')
        result_vsrx = createVSRX(client, zoneid, project_id, networks, tmpl_vsrx, offer_id)
        if not result_vsrx['queryasyncjobresultresponse'].has_key('created'):
            self.logger.error( 'creation of vSRX VM failed' )
            assert False, "Creation of vSRX VM failed"
        vsrx_vm_id = result_vsrx['queryasyncjobresultresponse']['jobresult']['serviceinstance']['id']

        #self.addCleanup(self.instance_handle.delete_vm_by_id, vsrx_vm_id)

        vn1_vm1_name = 'vn1-guest-vm'
        vm1_fixture= self.useFixture(VMFixture(project_name= project_fixture.project_name, connections= self.connections, vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))

        #verify_on_setup need to work for VM created in custom project, right now it looks in default project
        assert vm1_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn1_vm1_name)
        assert vm1_fixture.ping_with_certainty('yahoo.com'), "Ping to website name failed!"
        return True

    #end test_vsrx_guest_vm_with_ping

    @preposttest_wrapper
    def test_vm_with_fip(self):
        ''' Test to validate that Floating IP tests on VM passes
        '''
        result = True
        vm1_name='vn1-vm1'
        vm2_name='vn2-vm1'
        vn1_name='vn229'
        vn2_name='vn230'
        vn1_subnets=['10.3.9.0/24']
        vn2_subnets=['10.3.10.0/24']
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj= vn1_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn1_obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        #Second VM
        vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn2_name, inputs= self.inputs, subnets= vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vn2_obj= vn2_fixture.obj
        vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn2_obj, vm_name= vm2_name, project_name= self.inputs.project_name))
        assert vm2_fixture.verify_on_setup(), "VM %s verification failed" %(vm2_fixture.vm_id)

        #Assign FIP to the first VM
        fip_test_obj = self.useFixture(CSFloatingIPFixture(connections= self.connections, project_name=self.inputs.project_name))
        cs_fip_obj = fip_test_obj.create_and_assoc_fip(vn1_fixture.vn_id, vm1_fixture.vm_id)

        fip_test_obj.verify_fip(cs_fip_obj, vm1_fixture, vn1_fixture )

        #Ping and initiate TCP traffic to public address from VM now
        if not vm1_fixture.ping_with_certainty('8.8.8.8'):
            self.logger.error('Ping to public IP 8.8.8.8 from VM failed')
            result = result and False
        if not vm1_fixture.ping_with_certainty('www.yahoo.com'):
            self.logger.error('Ping to yahoo.com from VM failed')
            result = result and False

        urls=['www.google.com',
              'www-int.juniper.net']
        for url in urls:
            cmd = 'wget %s --timeout 100 --tries 2' %(url)
            output = vm1_fixture.run_cmd_on_vm(cmds=[cmd])[cmd]
            if not 'saved' in output:
                self.logger.error("TCP transfer tests on VM %s with URL %s failed"
                    %(vm1_fixture.vm_name, url))
                result = result and False
            else:
                self.logger.info("TCP transfer test from VM %s with URL %s passed "
                    %(vm1_fixture.vm_name, url ))
        #end for url

        #Give Public IP to second VM and check if these two VMs can talk to each other
        cs_fip_obj1 = fip_test_obj.create_and_assoc_fip(vn2_fixture.vn_id, vm2_fixture.vm_id)
        if not vm2_fixture.ping_with_certainty(cs_fip_obj['ipaddress']):
            self.logger.error('Ping between two VMs via the public network failed')
            result = result and False
        else:
            self.logger.info('Ping between two VMs via the public network passed')

        fip_test_obj.disassoc_and_delete_fip(cs_fip_obj1['id'])
        fip_test_obj.disassoc_and_delete_fip(cs_fip_obj['id'])
        if not fip_test_obj.verify_no_fip(cs_fip_obj):
            self.logger.error('Verification of FIP ID %s removal failed' %( cs_fip_obj['id']) )
            result = result and False
        if not fip_test_obj.verify_no_fip(cs_fip_obj1):
            self.logger.error('Verification of FIP ID %s removal failed' %( cs_fip_obj['id']) )
            result = result and False

        assert result , "One or more tests with FIP failed..Please check logs"

        return result
    #end test_vm_with_fip

    @preposttest_wrapper
    def test_multiple_networks_per_project(self):
        '''Validate creating multiple networks inside project, create VM in each and verify delete
        '''
        project_name = 'custom_new_proj'
        project_fixture = self.useFixture(ProjectFixture(connections = self.connections, vnc_lib_h = self.vnc_lib,
        project_name = project_name))
        if not project_fixture:
            self.logger.error('creation of project: %s failed') %project_name
            assert False, 'creation of project failed'
        project_id = project_fixture.cs_project_obj['id']
        (vn1_name, vn2_name) = ('guestVN1', 'guestVN2')
        (vn1_subnets, vn2_subnets) = (['10.25.25.0/24'], ['10.20.20.0/24'])
        vn1_fixture = self.useFixture(VNFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        vn1_fixture.verify_is_run = True
        vn1_fixture.verify_on_setup()
        vn2_fixture = self.useFixture(VNFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_name=vn2_name, inputs= self.inputs, subnets= vn2_subnets))
        (vn1_vm1_name, vn1_vm2_name, vn2_vm1_name, vn2_vm2_name)  = ('vn1-guest-vm1', 'vn1-guest-vm2', 'vn2-guest-vm1',
                                                                     'vn2-guest-vm2')
        vn1_vm1_fixture = self.useFixture(VMFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vn1_vm2_fixture = self.useFixture(VMFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        vn2_vm1_fixture = self.useFixture(VMFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_obj= vn2_fixture.obj, vm_name= vn2_vm1_name))
        vn2_vm2_fixture = self.useFixture(VMFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_obj= vn2_fixture.obj, vm_name= vn2_vm2_name))
        assert vn1_vm1_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn1_vm1_name)
        assert vn1_vm2_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn1_vm2_name)
        assert vn2_vm1_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn2_vm1_name)
        assert vn2_vm2_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn2_vm2_name)

        assert vn1_vm1_fixture.ping_with_certainty( vn1_vm2_fixture.vm_ip ), "Ping between VMs in same network failed!"
        #assert vn1_vm1_fixture.ping_to_ip( vn2_vm1_fixture.vm_ip ), "Ping between VMs in different networks failed!"
        #assert vn1_vm2_fixture.ping_to_ip( vn2_vm2_fixture.vm_ip ), "Ping between VMs in different networks failed!"
        return True
    #end test_multiple_networks_per_project

    @preposttest_wrapper
    def test_mgmt_server_restart(self):
        ''' validate creation and delete works after management server restart
        '''
        project_name = 'custom_new_proj'
        project_fixture = self.useFixture(ProjectFixture(connections = self.connections, vnc_lib_h = self.vnc_lib,
        project_name = project_name))
        if not project_fixture:
            self.logger.error('creation of project: %s failed') %project_name
            assert False, 'creation of project failed'
        project_id = project_fixture.cs_project_obj['id']
        (vn1_name, vn2_name) = ('guestVN1', 'guestVN2')
        (vn1_subnets, vn2_subnets) = (['10.25.25.0/24'], ['10.20.20.0/24'])
        vn1_fixture = self.useFixture(VNFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        vn1_fixture.verify_is_run = True
        vn1_fixture.verify_on_setup()
        vn2_fixture = self.useFixture(VNFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_name=vn2_name, inputs= self.inputs, subnets= vn2_subnets))
        (vn1_vm1_name, vn1_vm2_name, vn2_vm1_name, vn2_vm2_name)  = ('vn1-guest-vm1', 'vn1-guest-vm2', 'vn2-guest-vm1',
                                                                     'vn2-guest-vm2')
        vn1_vm1_fixture = self.useFixture(VMFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vn1_vm2_fixture = self.useFixture(VMFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        vn2_vm1_fixture = self.useFixture(VMFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_obj= vn2_fixture.obj, vm_name= vn2_vm1_name))
        vn2_vm2_fixture = self.useFixture(VMFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_obj= vn2_fixture.obj, vm_name= vn2_vm2_name))
        assert vn1_vm1_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn1_vm1_name)
        assert vn1_vm2_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn1_vm2_name)
        assert vn2_vm1_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn2_vm1_name)
        assert vn2_vm2_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn2_vm2_name)

        assert vn1_vm1_fixture.ping_with_certainty( vn1_vm2_fixture.vm_ip ), "Ping between VMs in same network failed!"
        self.inputs.restart_service('cloudstack-management', [self.inputs.cfgm_ip]), "service did not come up"
        sleep(60)

        vn3_name = 'guestVN3'
        vn3_subnets = ['10.30.30.0/24']
        vn3_vm1_name = 'vn3-guest-vm1'
        vn3_fixture = self.useFixture(VNFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_name=vn3_name, inputs= self.inputs, subnets= vn3_subnets))
        vn3_fixture.verify_is_run = True
        assert vn3_fixture.verify_on_setup(), "VN verification failed!!"
        vn3_vm1_fixture = self.useFixture(VMFixture(project_name= project_fixture.project_name, connections=
        self.connections, vn_obj= vn3_fixture.obj, vm_name= vn3_vm1_name))

        assert vn3_vm1_fixture.verify_on_setup(), "VM %s verification failed" %vn3_vm1_name
        assert vn1_vm1_fixture.ping_with_certainty( vn1_vm2_fixture.vm_ip ), "Ping between VMs in same network failed!"
        return True
    #end test_mgmt_server_restart

    @preposttest_wrapper
    def test_disassociate_vn_from_vm(self):
        ''' Test to validate that disassociating a VN from a VM fails.
        '''
        self.inputs.negative_tc = True
        vm1_name='vm222'
        vn_name='vn222'
        vn_subnets=['10.1.1.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        try:
            self.logger.info(' Will try deleting the VN now')
            self.network_handle.delete_vn(vn_obj['id'])
            assert vn_fixture.verify_on_setup()
            assert vm1_fixture.verify_on_setup()
        except RefsExistError as e:
            self.logger.info( 'RefsExistError:Check passed that the VN cannot be disassociated/deleted when the VM exists')

        return True
    #end test_disassociate_vn_from_vm

    @preposttest_wrapper
    def test_vm_stop_start(self):
        ''' Validate that VM IP is reserved for the VM even while it is shut. A second VM should not get the same IP at this state

        '''
        result = True
        vn1_name='vn31'
        vn1_subnets=['10.2.1.0/24']
        vn1_vm1_name= 'vn31vm1'
        vn1_vm2_name= 'vn31vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup(), "VN1 %s verification failed..Pls check logs" %(vn1_name)
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,  vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        assert vm1_fixture.verify_on_setup(), "VM1 %s verification failed! Please check logs" %(vn1_vm1_name)
        vm1_fixture.stop_vm()
        #Validate that the a new VM does not get the same IP as VM1
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,  vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        assert vm2_fixture.verify_on_setup(), "VM2 %s verification failed! Pls check logs" %(vn1_vm2_name)
        if vm2_fixture.vm_ip == vm1_fixture.vm_ip:
            self.logger.error('VM2 IP %s is same as VM1(stopped) IP : %s' %(vm2_fixture.vm_ip,vm1_fixture.vm_ip))
            result = result and False
        else:
            self.logger.info('VM2 has got a different IP compared to VM1s(stopped) IP')

        #Bring up VM1 again and check if VM1 verification passes
        vm1_fixture.start_vm()
        assert vm1_fixture.verify_on_setup(), "VM1 %s verification failed after restarting it! Please check logs" %(vn1_vm1_name)
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip), "Ping between VM1 and VM2 failed!"
        return True
    #end test_vm_stop_start

    @preposttest_wrapper
    def test_vm_vn_block_exhaustion(self):
        ''' Test to validate that a VMs verification fails after the IP-Block is exhausted.
        '''
        #self.inputs.negative_tc = True
        vn_name='vn-block-exhaustion'
        vn_subnets=['10.1.1.0/29']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
            vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
        self.logger.info('out of /29 block, we can have 5 usable addresses. Only 5 VMs should get launched properly.')

        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
            vn_obj=vn_obj, vm_name= vn_name+'-vm1', project_name= self.inputs.project_name))

        vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
            vn_obj=vn_obj, vm_name= vn_name+'-vm2', project_name= self.inputs.project_name))

        vm3_fixture= self.useFixture(VMFixture(connections= self.connections,
            vn_obj=vn_obj, vm_name= vn_name+'-vm3', project_name= self.inputs.project_name))

        vm4_fixture= self.useFixture(VMFixture(connections= self.connections,
            vn_obj=vn_obj, vm_name= vn_name+'-vm4', project_name= self.inputs.project_name))

        vm5_fixture= self.useFixture(VMFixture(connections= self.connections,
            vn_obj=vn_obj, vm_name= vn_name+'-vm5', project_name= self.inputs.project_name))

        self.logger.info('The 6th VM verification should fail as it is unable to get any ip. The ip-block is exhausted')

        vm6_fixture= self.useFixture(VMFixture(connections= self.connections,
            vn_obj=vn_obj, vm_name= vn_name+'-vm6', project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        assert vm5_fixture.verify_on_setup()
        try:
            self.connections.instance_handle.get_vm_ip(vm6_fixture.vm_obj, vn_name)
            assert False, "VM seems to have got an ip"
        except KeyError:
            msg="VM didn't get ip as expected"
            self.inputs.logger.info(msg)

        vm1_fixture.cleanUp(), "Unable to delete the VM after VN exhaustion"
        vm7_fixture= self.useFixture(VMFixture(connections= self.connections,
            vn_obj=vn_obj, vm_name= vn_name+'-vm7', project_name= self.inputs.project_name))
        assert vm7_fixture.verify_on_setup()
        return True

    #end test_vm_vn_block_exhaustion

    @preposttest_wrapper
    def test_vn_connectivity_thru_policy(self):
        ''' Validate creation of policy to connect two VNs and deletion of VPC.
        '''
        vpc_name = 'testVPC'
        cidr = '10.5.0.0/16'
        vn1_name = 'vpcnet1'
        vn2_name = 'vpcnet2'
        vn1_subnets = ['10.5.100.0/24']
        vn2_subnets = ['10.5.101.0/24']
        vn1_vm1_name = 'vn1testVM1'
        vn2_vm1_name = 'vn2testVM1'

        vpc_fixture = self.useFixture(CSVPCFixture(vpc_name, cidr, connections = self.connections, vnc_lib_h = self.vnc_lib,
                                                    project_name= self.inputs.project_name))
        if not vpc_fixture:
            self.logger.error('VPC create fialed')
            return False
        vn1_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn1_name,
                                                inputs= self.inputs, subnets= vn1_subnets, vpc_id = vpc_fixture.vpc_id))
        vn2_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn2_name,
                                                inputs= self.inputs, subnets= vn2_subnets, vpc_id = vpc_fixture.vpc_id))
        vm1_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vn2_fixture.obj, vm_name= vn2_vm1_name))
        assert vm1_fixture.verify_on_setup(), "VM verification failed - %s" %vn1_vm1_name
        assert vm2_fixture.verify_on_setup(), "VM verification failed - %s" %vn2_vm1_name
        vn1_acllist_id = vpc_fixture.create_acllist(vpc_fixture.vpc_id, 'vn1_acllist')
        vn2_acllist_id = vpc_fixture.create_acllist(vpc_fixture.vpc_id, 'vn2_acllist')
        if not vn1_acllist_id or not vn2_acllist_id:
            self.logger.error('acl list creation failed')
            return False
        assert vpc_fixture.create_aclrule('1', 'all', vn1_acllist_id, vn2_subnets[0], 'egress', 'allow'), "Create ACL Rule failed"
        assert vpc_fixture.create_aclrule('2', 'all', vn1_acllist_id, vn2_subnets[0], 'ingress', 'allow'), "Create ACL Rule failed"
        assert vpc_fixture.create_aclrule('1', 'all', vn2_acllist_id, vn1_subnets[0], 'egress', 'allow'), "Create ACL Rule failed"
        assert vpc_fixture.create_aclrule('2', 'all', vn2_acllist_id, vn1_subnets[0], 'ingress', 'allow'), "Create ACL Rule failed"
        #associate the aclid to the network
        assert vpc_fixture.bind_acl_nw(vn1_acllist_id, vn1_fixture.vn_id), "binding acl to network failed"
        assert vpc_fixture.bind_acl_nw(vn2_acllist_id, vn2_fixture.vn_id), "binding acl to network failed"
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip), "Ping VMs across networks failed!"
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip), "Ping VMs across networks failed!"
        return True
    #end test_vpc

    @preposttest_wrapper
    def test_vn_name_with_spl_characters(self):
        '''Test to validate VN name with special characters is allowed.
        '''
        vn1_obj=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
            vn_name='vn.1', inputs= self.inputs, subnets=['10.1.1.0/29'] ))
        assert vn1_obj.verify_on_setup()
        assert vn1_obj

        vn2_obj=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
            vn_name='vn,2', inputs= self.inputs, subnets=['10.2.1.0/29'] ))
        assert vn2_obj.verify_on_setup()
        assert vn2_obj

        vn4_obj=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
            vn_name='vn_4', inputs= self.inputs, subnets=['10.3.1.0/29'] ))
        assert vn4_obj.verify_on_setup()
        assert vn4_obj

        return True
    #end test_vn_name_with_spl_characters

    @preposttest_wrapper
    def test_vm_intf_tests(self):
        ''' Test to validate Loopback and eth0 intfs up/down events.
        '''
        vm1_name='vmmine'
        vn_name='vn222'
        vn_subnets=['10.1.1.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        self.logger.info('Shutting down Loopback intf')
        cmd_to_intf_down=['ifdown lo ']
        vm1_fixture.run_cmd_on_vm( cmds= cmd_to_intf_down);
        assert vm1_fixture.verify_on_setup()
        self.logger.info('Bringing up Loopback intf')
        cmd_to_intf_up=['ifup lo']
        vm1_fixture.run_cmd_on_vm( cmds= cmd_to_intf_up);
        assert vm1_fixture.verify_on_setup()
        cmd_to_create_file=['touch batchfile']
        vm1_fixture.run_cmd_on_vm( cmds= cmd_to_create_file);
        cmd_to_add_cmd_to_file=["echo 'ifconfig; route; ifdown eth0; ifconfig; route; sleep 10; ifup eth0;  ifconfig; route ' > batchfile"]
        vm1_fixture.run_cmd_on_vm( cmds= cmd_to_add_cmd_to_file);
        cmd_to_exec_file=['sh batchfile | tee > out.log']
        vm1_fixture.run_cmd_on_vm( cmds= cmd_to_exec_file);
        assert vm1_fixture.verify_on_setup()
        return True
    #end test_vm_intf_tests

    @preposttest_wrapper
    def test_shutdown_vm(self):
        ''' Test to validate that VN is unaffected after VM launched in it is shutdown.
        '''
        vn_name='vn-shutdown-vm'
        vm1_name=vn_name+'-vm1'
        vn_subnets=['10.10.10.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        cmd_to_shutdown_vm=['shutdown -h now']
        vm1_fixture.run_cmd_on_vm( cmds= cmd_to_shutdown_vm);
        assert vn_fixture.verify_on_setup()
        return True
    #end test_shutdown_vm

    @preposttest_wrapper
    def test_duplicate_vn_add(self):
        '''Test to validate adding a Duplicate VN creation and deletion.
        '''
        vn_obj1=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name='vn_1', inputs= self.inputs, subnets=['10.255.255.0/29'] ))
        assert vn_obj1
        assert vn_obj1.verify_on_setup()
        vn_obj2=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name='vn_1', inputs= self.inputs, subnets=['10.255.255.0/29'] ))
        assert vn_obj2, 'Duplicate VN cannot be created'
        assert vn_obj2.verify_on_setup()
        if (vn_obj1.vn_id == vn_obj2.vn_id):
            self.logger.info('Same obj created')
        else:
            self.logger.error('Different objs created.')
        return True
    #end test_duplicate_vn_add

    @preposttest_wrapper
    def test_ping_on_broadcast_multicast(self):
        ''' Validate Ping on subnet broadcast, link local multicast, network broadcast.
        '''
        ping_count='5'
        vn_name='vn-bcast-mcast'
        vn_subnets=['10.2.2.0/24']
        list_of_ip_to_ping=['10.2.2.255', '224.0.0.1', '255.255.255.255']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                                              vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()

        vm_fixture={}; vm_ips=[]
        vm_list=[vn_name+'-vm1', vn_name+'-vm2', vn_name+'-vm3', vn_name+'-vm4']
        for vm in vm_list:
            vm_fixture[vm]= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
                                                      vn_obj= vn_fixture.obj, vm_name= vm))
        for vm in vm_list:
            assert vm_fixture[vm].verify_on_setup(), "VM %s is not UP" %vm
            vm_ips.append(vm_fixture[vm].vm_ip)

        # Enabling Broadcast and multicast echo reply in the VM
        cmd=['echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']
        for vm in vm_list:
            vm_fixture[vm].run_cmd_on_vm(cmds= cmd)

        for dst_ip in list_of_ip_to_ping:
            self.logger.info('pinging from %s to %s'%(vm_ips[0],dst_ip))
            ping_output= vm_fixture[vm_list[0]].ping_to_ip( dst_ip, return_output= True, count=ping_count, other_opt='-b' )
            expected_result=' 0% packet loss'
            assert (expected_result in ping_output)
            #getting count of ping response from each vm
            string_count_dict=get_string_match_count(vm_ips, ping_output)
            print string_count_dict
            for k in vm_ips:
                assert (string_count_dict[k] >= (int(ping_count)-1))#this is a workaround : ping utility exist as soon as it gets one response


        for dst_ip in list_of_ip_to_ping:
            self.logger.info('pinging from %s to %s with jumbo frames and MTU of 1500'%(vm_ips[0],dst_ip))
            ping_output= vm_fixture[vm_list[0]].ping_to_ip( dst_ip, return_output= True, count=ping_count,  size= '3000', other_opt='-b' )
            self.logger.info('The packet is not fragmanted because of the smaller MTU')
            expected_result='Message too long'
            assert (expected_result in ping_output)

        self.logger.info('Will change the MTU of the VMs and try again')
        cmd_to_increase_mtu=['ifconfig eth0 mtu 9000']
        for vm in vm_list:
            vm_fixture[vm].run_cmd_on_vm(cmds= cmd_to_increase_mtu)

        for dst_ip in list_of_ip_to_ping:
            self.logger.info('pinging from %s to %s with jumbo frames and MTU of 9000'%(vm_ips[0],dst_ip))
            ping_output= vm_fixture[vm_list[0]].ping_to_ip( dst_ip, return_output= True, count=ping_count,  size= '3000', other_opt='-b' )
            expected_result='Message too long'
            assert (expected_result not in ping_output)
            #getting count of ping response from each vm
            string_count_dict={}
            string_count_dict=get_string_match_count(vm_ips,ping_output)
            print string_count_dict
            for k in vm_ips:
                assert (string_count_dict[k] >= (int(ping_count)-1))#this is a workaround : ping utility exist as soon as it gets one response
        return True

    #end test_ping_on_broadcast_multicast

    @preposttest_wrapper
    def test_multistep_vm_add_delete_with_stop_start_service(self):
        ''' Test to validate VMs addition deletion after service restarts.
        '''
        vn_name='vn-11'
        vn_subnets=['10.1.1.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
            vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()

        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
            vn_obj=vn_fixture.obj, vm_name= 'vm-11', project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup(), "VM 'vm1' is not UP"
        self.logger.info('vm1 launched successfully.Stopping vrouter service')

        for compute_ip in self.inputs.compute_ips:
            self.inputs.stop_service('contrail-vrouter',[compute_ip])
            self.addCleanup( self.inputs.start_service, 'contrail-vrouter', [compute_ip] )

        assert not vm1_fixture.cleanUp(), "Though vrouter is down we are able to destroy the VM"
        self.logger.info('vm1 is not deleted as expected when vrouter is down. Launch a new VM vm2')

        try:
            vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_fixture.obj, vm_name= 'vm-12', project_name= self.inputs.project_name))
        except:
            print "Unexpected error:", sys.exc_info()[0]
            assert not vm2_fixture.verify_vm_launched(), "VM is UP eventhough vrouter is down"
            self.logger.info('vm2 has not booted up as expected. Starting vrouter service')

        for compute_ip in self.inputs.compute_ips:
            self.inputs.start_service('contrail-vrouter',[compute_ip])

        assert vm2_fixture.verify_on_setup(), "VM vm2 is not up even after bringing up contrail-vrouter service"
        self.logger.info('vm2 is up now as expected')

        assert vm1_fixture.verify_vm_not_in_api_server()
        assert vm1_fixture.verify_vm_not_in_agent()
        assert vm1_fixture.verify_vm_not_in_control_nodes()
        self.logger.info('vm1 is deleted as expected')

        return True

    #end test_multistep_vm_add_delete_with_stop_start_service


    @preposttest_wrapper
    def test_process_restart_with_multiple_vn_vm(self):
        ''' Test to validate that multiple VM creation and deletion passes.
        '''
        vm1_name='vm1'
        vn_name='multivn-vm'
        vn_subnets=['192.168.1.0/24']
        vn_count_for_test=4
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test = 4
        vm_fixture= self.useFixture(create_multiple_vn_and_multiple_vm_fixture(connections= self.connections,
                     vn_name=vn_name, vm_name=vm1_name, inputs= self.inputs, project_name= self.inputs.project_name,
                      subnets= vn_subnets, vn_count=vn_count_for_test, vm_count=1, subnet_count=1))
        time.sleep(300)
        assert vm_fixture.verify_vns_on_setup()
        for i in range (0, 5):
            try:
                for vmobj in vm_fixture.vm_obj_dict.values():
                    assert vmobj.verify_on_setup()
                break
            except Exception as e:
                self.logger.exception("Got exception as %s" %(e))
                self.logger.info("retry verifying vm on setup")
        else:
            return False

        compute_ip=[]
        for vmobj in vm_fixture.vm_obj_dict.values():
            vm_host_ip=vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        try:
            self.inputs.restart_service('contrail-vrouter', compute_ip)
            sleep(60)
            for vmobj in vm_fixture.vm_obj_dict.values():
                assert vmobj.verify_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s" %(e))
            return False
        return True
    #end test_process_restart_with_multiple_vn_vm

    @preposttest_wrapper
    def test_vm_add_delete_in_2_vns(self):
        ''' Test to validate that a VM can be associated to more than one VN.
        '''
        vm1_name='vm1'; vm2_name='vm2'; vm3_name='vm3'
        vn1_name='vn1'; vn1_subnets=['10.1.1.0/24']
        vn2_name='vn2'; vn2_subnets=['10.1.2.0/24']
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn2_name, inputs= self.inputs, subnets= vn2_subnets))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_objs=[ vn1_fixture.obj, vn2_fixture.obj ], vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        cmd = 'ifconfig -a'
        vm1_fixture.run_cmd_on_vm( cmds= [cmd])
        output = vm1_fixture.return_output_cmd_dict[cmd]
        print output
        for ips in vm1_fixture.vm_ips:
            if ips not in output:
                self.logger.error("IP %s not assigned to any eth intf of %s"%(ips,vm1_fixture.vm_name))
                assert False, "PR 1018"
            else:
                self.logger.info("IP %s is assigned to eth intf of %s"%(ips,vm1_fixture.vm_name))

        vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn1_fixture.obj, vm_name= vm2_name, project_name= self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()
        vm3_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn2_fixture.obj, vm_name= vm3_name, project_name= self.inputs.project_name))
        assert vm3_fixture.verify_on_setup()

        if not vm1_fixture.ping_to_ip( vm2_fixture.vm_ip ):
            assert False, "Ping to %s Fail"%vm2_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass'%vm2_fixture.vm_ip)
        if not vm1_fixture.ping_to_ip( vm3_fixture.vm_ip ):
            assert False, "Ping to %s Fail"%vm3_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass'%vm3_fixture.vm_ip)

        self.logger.info('Deleting vm1')
        vm1_fixture.cleanUp()
        self.logger.info('Checking if vn is still present in agent')
        assert not vn1_fixture.verify_vn_not_in_agent()
        self.logger.info('VN is present in agent as expected.Now deleting vm2')
        vm2_fixture.cleanUp()
        self.logger.info('Checking if VN is removed from agent')

        assert vn1_fixture.verify_vn_not_in_agent()
        self.logger.info('VN is not present in agent as expected')

        return True

    #end test_vm_add_delete_in_2_vns

    @preposttest_wrapper
    def test_vm_arp(self):
        ''' Test to validate that the fool-proof way is to not answer
        for arp request from the guest for the address the tap i/f is
        "configured" for.
        '''
        vn_name='arp-vn'
        vm1_name=vn_name+'-vm1'
        vm2_name=vn_name+'-vm2'
        vn_subnets=['10.11.1.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm2_name, project_name= self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        i= 'arping -c 5 %s'%vm1_fixture.vm_ip
        cmd_to_output=[i]
        vm1_fixture.run_cmd_on_vm( cmds= cmd_to_output)
        output = vm1_fixture.return_output_cmd_dict[i]
        result= True
        if not 'Received 0 response' in output:
            self.logger.error('Arping to the VMs own address should have failed')
            result= False
        else:
            self.logger.info('Arping to the VMs own address fails')

        j= 'arping -c 5 %s'%vm2_fixture.vm_ip
        cmd_to_output=[j]
        vm1_fixture.run_cmd_on_vm( cmds= cmd_to_output)
        output1 = vm1_fixture.return_output_cmd_dict[j]
        if not 'Received 5 response' in output1:
            self.logger.error('Arping to the other VMs address should have passed')
            result= False
        else:
            self.logger.info('Arping to the other VMs address passes')

        assert result, "ARPing Failure"
        return True
    #end test_vm_arp

    # TODO: Dont make it part of sanity. Wait till we have 2 node setup
    @preposttest_wrapper
    def test_fip_with_traffic (self):
        '''Testtraffic accross borrower and giving VN.
        '''
        result= True
        (vn1_name, vn1_subnets)= ("vn1", ["11.1.1.0/24"])
        (vn2_name, vn2_subnets)= ("vn2", ["22.1.1.0/24"])
        (vm1_name, vm2_name)= ("vm1", "vm2")
        fip_pool_name1= 'fip1'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                                       inputs= self.inputs, vn_name= self.vn1_name, subnets= self.vn1_subnets))
        vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                                       inputs= self.inputs, vn_name= self.vn2_name, subnets= self.vn2_subnets))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_traffic_fixture= self.useFixture(VMFixture(connections= self.connections,
                             vn_obj=vn1_fixture, vm_name= vm1_name, project_name= self.inputs.project_name))
        vm2_traffic_fixture= self.useFixture(VMFixture(connections= self.connections,
                             vn_obj=vn1_fixture, vm_name= vm2_name, project_name= self.inputs.project_name))
        assert vm1_traffic_fixture.verify_on_setup()
        assert vm2_traffic_fixture.verify_on_setup()

        fip_fixture1= self.useFixture(CSFloatingIPFixture( project_name= self.inputs.project_name, connections= self.connections ))
        assert fip_fixture1.verify_on_setup()

        fip_id1= fip_fixture1.create_and_assoc_fip(vn1_fixture.vn_id, vm2_traffic_fixture.vm_id)
        self.addCleanup( fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip( fip_id1, vm2_traffic_fixture, vn1_fixture)
        if not vm2_traffic_fixture.ping_with_certainty(vm1_traffic_fixture.vm_ip):
            result = result and False

        # Verify Traffic ---
        # Start Traffic
        traffic_obj= {}; startStatus= {}; stopStatus= {}
        traffic_proto_l= ['udp']
        total_streams= {}; total_streams['udp']= 1; dpi= 9100; proto= 'udp'
        for proto in traffic_proto_l:
            traffic_obj[proto]= {}; startStatus[proto]= {}
            traffic_obj[proto]= self.useFixture(traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000, total_single_instance_streams= 20):
            startStatus[proto]= traffic_obj[proto].startTraffic(num_streams=total_streams[proto], start_port=dpi, \
                tx_vm_fixture=vn1_vm1_traffic_fixture, rx_vm_fixture=fvn1_vm1_traffic_fixture, stream_proto=proto)
            self.logger.info ("Status of start traffic : %s, %s, %s" %(proto, vn1_vm1_traffic_fixture.vm_ip, startStatus[proto]))
            if startStatus[proto]['status'] != True:  result= False
        self.logger.info ("-"*80)

        # Poll live traffic
        traffic_stats= {}
        self.logger.info ("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats= traffic_obj[proto].getLiveTrafficStats()
            err_msg= "Traffic disruption is seen: details: "
        #self.assertEqual(traffic_stats['status'], True, err_msg)
        assert(traffic_stats['status']== True), err_msg
        self.logger.info ("-"*80)

        # Verify Flow records here
        inspect_h1= self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        inspect_h2= self.agent_inspect[fvn1_vm1_traffic_fixture.vm_node_ip]
        flow_rec1= None
        udp_src=unicode(8000)
        dpi=unicode(dpi)

        # Verify Ingress Traffic
        self.logger.info('Verifying Ingress Flow Record')
        flow_rec1= inspect_h1.get_vna_fetchflowrecord(vrf=vn1_vm1_traffic_fixture.agent_vrf_objs['vrf_list'][0]['ucindex'],sip=vn1_vm1_traffic_fixture.vm_ip,dip=fvn1_vm1_traffic_fixture.vm_ip,sport=udp_src,dport=dpi,protocol='17')

        if flow_rec1 is not None:
            self.logger.info('Verifying NAT in flow records')
            match = inspect_h1.match_item_in_flowrecord (flow_rec1,'nat','enabled')
            if match is False :
                self.logger.error('Test Failed. NAT is not enabled in given flow. Flow details %s' %(flow_rec1))
                result = result and False
            self.logger.info('Verifying traffic direction in flow records')
            match = inspect_h1.match_item_in_flowrecord (flow_rec1,'direction','ingress')
            if match is False :
                self.logger.error('Test Failed. Traffic direction is wrong should be ingress. Flow details %s' %(flow_rec1))
                result = result and False
        else:
            self.logger.error('Test Failed. Required ingress Traffic flow not found')
            result = result and False

        # Verify Egress Traffic
        # Check VMs are in same agent or not. Need to compute source vrf accordingly
        if vn1_vm1_traffic_fixture.vm_node_ip != fvn1_vm1_traffic_fixture.vm_node_ip:
            source_vrf = vn1_vm1_traffic_fixture.agent_vrf_objs['vrf_list'][0]['ucindex']
        else:
            vrf_list= inspect_h1.get_vna_vrf_objs(vn_name=fvn1_vm1_traffic_fixture.vn_name)
            source_vrf = vrf_list['vrf_list'][0]['ucindex']
        self.logger.info('Verifying Egress Flow Records')
        flow_rec2= inspect_h1.get_vna_fetchflowrecord(vrf=source_vrf,sip=fvn1_vm1_traffic_fixture.vm_ip,dip=fip_fixture1.fip[fip_id1],sport=dpi,dport=udp_src,protocol='17')
        if flow_rec2 is not None:
            self.logger.info('Verifying NAT in flow records')
            match = inspect_h1.match_item_in_flowrecord (flow_rec2,'nat','enabled')
            if match is False :
                self.logger.error('Test Failed. NAT is not enabled in given flow. Flow details %s' %(flow_rec2))
                result = result and False
            self.logger.info('Verifying traffic direction in flow records')
            match = inspect_h1.match_item_in_flowrecord (flow_rec2,'direction','egress')
            if match is False :
                self.logger.error('Test Failed. Traffic direction is wrong should be Egress. Flow details %s' %(flow_rec1))
                result = result and False
        else:
            self.logger.error('Test Failed. Required Egress Traffic flow not found')
            result = result and False

        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-"*80)
        for proto in traffic_proto_l:
            stopStatus[proto]= {}
            stopStatus[proto]= traffic_obj[proto].stopTraffic()
            #if stopStatus[proto] != []: msg.append(stopStatus[proto]); result= False
            if stopStatus[proto] != []: result= False
            self.logger.info ("Status of stop traffic for proto %s is %s" %(proto, stopStatus[proto]))
        self.logger.info ("-"*80)
        if not result :
            self.logger.error('Test Failed. Floating IP test with traffic failed')
            assert result
        return result
    # end test_fip_with_traffic

    @preposttest_wrapper
    def test_vpc_aclrules(self):
        def check_all_connectivity():
            cmd = 'service iptables stop'
            vm1_fixture.run_cmd_on_vm( cmds= [cmd])
            vm2_fixture.run_cmd_on_vm( cmds= [cmd])

            self.logger.info("Check ICMP, TCP and UDP Traffic between VNs")
            output = vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
            result = {'icmp': output}

            for port in range (startport, endport+1):
                for protocol in ['tcp', 'udp']:
                    if protocol == 'tcp':
                        cmd = 'traceroute -T -p %d %s -n -N 1 -q 1 -m 1' %(port, vm2_fixture.vm_ip)
                    else:
                        cmd = 'traceroute -U -p %d %s -N 1 -q 1 -m 1' %(port, vm2_fixture.vm_ip)
                    vm1_fixture.run_cmd_on_vm( cmds= [cmd])
                    output = vm1_fixture.return_output_cmd_dict[cmd]
                    m = re.search("1\s+%s"%vm2_fixture.vm_ip, output)
                    if m:
                        result.update({'%s%d'%(protocol,port): True})
                    else:
                        self.logger.info("%s traffic test for port %d failed"%(protocol,port))
                        result.update({'%s%d'%(protocol,port): False})
            return result

        (vpc_name, cidr) = ('vpc1b', '10.2.0.0/16')
        (vn1_name, vn1_subnets) = ('vpcnet1b', ['10.2.100.0/24'])
        (vn2_name, vn2_subnets) = ('vpcnet2b', ['10.2.101.0/24'])
        vn1_vm1_name = 'vn1testVM1b'
        vn2_vm1_name = 'vn2testVM1b'
        startport = 9999; endport = startport + 2

        self.logger.info("Create VPC...")
        vpc_fixture = self.useFixture(CSVPCFixture(vpc_name, cidr, connections = self.connections, vnc_lib_h = self.vnc_lib,
                                                    project_name= self.inputs.project_name))
        vn1_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn1_name,
                                                inputs= self.inputs, subnets= vn1_subnets, vpc_id = vpc_fixture.vpc_id))
        vn2_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn2_name,
                                                inputs= self.inputs, subnets= vn2_subnets, vpc_id = vpc_fixture.vpc_id))
        vm1_fixture = self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture = self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vn2_fixture.obj, vm_name= vn2_vm1_name))
        assert vm1_fixture.verify_on_setup(), "VM verification failed - %s" %vn1_vm1_name
        assert vm2_fixture.verify_on_setup(), "VM verification failed - %s" %vn2_vm1_name

        self.logger.info("Create ACL List")
        vn1_acllist_id = vpc_fixture.create_acllist(vpc_fixture.vpc_id, 'vn1_acllist')
        vn2_acllist_id = vpc_fixture.create_acllist(vpc_fixture.vpc_id, 'vn2_acllist')
        assert vn1_acllist_id, "Unable to create acl list"
        assert vn2_acllist_id, "Unable to create acl list"

        #associate the aclid to the network
        self.logger.info("Bind the ACL list to VN1 before creating any rules")
        assert vpc_fixture.bind_acl_nw(vn1_acllist_id, vn1_fixture.vn_id), "binding acl to network failed"

        self.logger.info("Create egress ACL rules")
        vn1_acl_icmprule_id = vpc_fixture.create_aclrule('5', 'icmp', vn1_acllist_id,
                                  vn2_subnets[0], 'egress', 'allow', icmptype=8, icmpcode=0)
        vn1_acl_tcprule_id = vpc_fixture.create_aclrule('6', 'tcp', vn1_acllist_id, vn2_subnets[0],
                                  'egress', 'allow', startport=startport, endport=endport)
        vn1_acl_udprule_id = vpc_fixture.create_aclrule('7', 'udp', vn1_acllist_id, vn2_subnets[0],
                                  'egress', 'allow', startport=startport, endport=endport)

        self.logger.info("Create ingress ACL rules")
        vn2_acl_icmprule_id = vpc_fixture.create_aclrule('5', 'icmp', vn2_acllist_id, vn1_subnets[0],
                                  'ingress', 'allow', icmptype=8, icmpcode=0)
        vn2_acl_tcprule_id = vpc_fixture.create_aclrule('6', 'tcp', vn2_acllist_id, vn1_subnets[0], 'ingress',
                                  'allow', startport=startport, endport=endport)
        vn2_acl_udprule_id = vpc_fixture.create_aclrule('7', 'udp', vn2_acllist_id, vn1_subnets[0], 'ingress',
                                  'allow', startport=startport, endport=endport)
        self.logger.info("Bind the ACL list to VN1 after creating the rules")
        assert vpc_fixture.bind_acl_nw(vn2_acllist_id, vn2_fixture.vn_id), "binding acl to network failed"

        result = check_all_connectivity()
        if result['icmp'] != True:
           assert False, "ICMP rule test failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if result['%s%d'%(protocol,port)] != True:
                    assert False, "%s test for port %d failed"%(protocol,port)

        # Change the rule from allow to deny
        self.logger.info("Modify the ICMP rule from allow to deny on ingress VN")
        vn2_acl_icmprule_id = vpc_fixture.modify_aclrule('5', 'icmp', vn2_acl_icmprule_id, vn1_subnets[0],
                                                         'ingress', 'deny', icmptype=8, icmpcode=0)
        result = check_all_connectivity()
        if result['icmp'] != False:
           assert False, "After changing the rule to deny icmp, certain flows are not as expected"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if protocol == "udp":
                    exp_result = False
                else:
                    exp_result = True
                if result['%s%d'%(protocol,port)] != exp_result:
                    assert False, "%s test for port %d failed after changing rule to deny icmp"%(protocol,port)

        # Add allow all icmp before deny echo
        self.logger.info("Add allow all icmp types before deny echo")
        vn2_acl_new_rule_id = vpc_fixture.create_aclrule('1', 'icmp', vn2_acllist_id, vn1_subnets[0],
                                                         'ingress', 'allow', icmptype=-1, icmpcode=-1)
        result = check_all_connectivity()
        if result['icmp'] != True:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if result['%s%d'%(protocol,port)] != True:
                    assert False, "%s test for port %d failed after adding allow all icmp"%(protocol,port)

        # Delete a specific acl rule - allow all icmp rule
        self.logger.info("Delete the allow all icmp types rule")
        assert vpc_fixture.delete_aclrule(vn2_acl_new_rule_id), "Unable to delete acl rule"
        result = check_all_connectivity()
        if result['icmp'] != False:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if protocol == "udp":
                    exp_result = False
                else:
                    exp_result = True
                if result['%s%d'%(protocol,port)] != exp_result:
                    assert False, "%s test for port %d failed after changing rule to deny icmp"%(protocol,port)

        # Add allow specific host icmp echo after deny network icmp
        self.logger.info("Add allow icmp after deny icmp echo")
        vn2_acl_new_rule_id = vpc_fixture.create_aclrule('9', 'icmp', vn2_acllist_id, vn1_subnets[0],
                                                         'ingress', 'allow', icmptype=8, icmpcode=0)
        result = check_all_connectivity()
        if result['icmp'] != False:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if protocol == "udp":
                    exp_result = False
                else:
                    exp_result = True
                if result['%s%d'%(protocol,port)] != exp_result:
                    assert False, "%s test for port %d failed after changing rule to deny icmp"%(protocol,port)

        # delete the ICMP deny rule from ingress
        self.logger.info("Delete the icmp rule added at the end")
        assert vpc_fixture.delete_aclrule(vn2_acl_icmprule_id), "Failed to delete icmp rule"
        vn2_acl_icmprule_id = vn2_acl_new_rule_id

        # Add overlapping rules
        self.logger.info("Add overlapping tcp rule")
        vn2_acl_new_rule_id = vpc_fixture.create_aclrule('1', 'tcp', vn2_acllist_id, vn1_subnets[0],
                                                         'ingress', 'deny', startport=startport+1, endport=startport+1)
        result = check_all_connectivity()
        if result['icmp'] != True:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if port == startport+1 and protocol == 'tcp':
                    exp_result = False
                else:
                    exp_result = True
                if result['%s%d'%(protocol,port)] != exp_result:
                    assert False, "%s test for port %d failed after adding overlapping rule"%(protocol,port)

        assert vpc_fixture.delete_aclrule(vn2_acl_new_rule_id), "Failed to delete tcp rule"

        # Change the rule from allow to deny
        self.logger.info("Testing on engress acl list. Changing the tcp,udp rules from allow to deny")
        vn1_acl_tcprule_id = vpc_fixture.modify_aclrule('6', 'tcp', vn1_acl_tcprule_id, vn2_subnets[0],
                                                         'egress', 'deny', startport=startport, endport=endport)
        vn1_acl_udprule_id = vpc_fixture.modify_aclrule('7', 'udp', vn1_acl_udprule_id, vn2_subnets[0],
                                                         'egress', 'deny', startport=startport, endport=endport)
        result = check_all_connectivity()
        if result['icmp'] != True:
           assert False, "After changing the rule to deny tcp/udp, ping fails"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if result['%s%d'%(protocol,port)] != False:
                    assert False, "%s test for port %d is fine even after changing rule to deny"%(protocol,port)
                    self.logger.info("Traffic should have been dropped for port %d" %port)

        # Add allow all before deny
        self.logger.info("Add allow all before all the rules")
        vn1_acl_new_rule_id = vpc_fixture.create_aclrule('1', 'all', vn1_acllist_id, vn2_subnets[0],
                                                         'egress', 'allow')
        result = check_all_connectivity()
        if result['icmp'] != True:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if result['%s%d'%(protocol,port)] != True:
                    assert False, "%s test for port %d failed"%(protocol,port)

        # Delete a specific acl rule - allow all icmp rule
        self.logger.info("Delete the allow all rule")
        assert vpc_fixture.delete_aclrule(vn1_acl_new_rule_id), "Unable to delete acl rule"
        result = check_all_connectivity()
        if result['icmp'] != True:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if result['%s%d'%(protocol,port)] != False:
                    assert False, "%s test for port %d fine, shouldnt be"%(protocol,port)
                    self.logger.info("Traffic should have been dropped for port %d" %port)

        # Add allow after deny network
        self.logger.info("Add allow all at the tail")
        vn1_acl_new_rule_id = vpc_fixture.create_aclrule('10', 'all', vn1_acllist_id, vn2_subnets[0],
                                                          'egress', 'allow')
        result = check_all_connectivity()
        if result['icmp'] != True:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if result['%s%d'%(protocol,port)] != False:
                    assert False, "%s test for port %d fine, shouldnt be"%(protocol,port)
                    self.logger.info("Traffic should have been dropped for port %d" %port)

        # delete the rule from ingress
        assert vpc_fixture.delete_aclrule(vn1_acl_new_rule_id), "Failed to delete allow all rule"

        # Add overlapping rules
        self.logger.info("Add overlapping tcp and udp rules at the head")
        vn1_acl_new_rule_id = vpc_fixture.create_aclrule('1', 'tcp', vn1_acllist_id, vn2_subnets[0],
                                                         'egress', 'allow', startport=startport+1, endport=startport+1)
        vn1_acl_new_rule_id_2 = vpc_fixture.create_aclrule('2', 'udp', vn1_acllist_id, vn2_subnets[0],
                                                           'egress', 'allow', startport=startport+1, endport=startport+1)
        result = check_all_connectivity()
        if result['icmp'] != True:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if port == startport+1:
                    exp_result = True
                else:
                    exp_result = False
                if result['%s%d'%(protocol,port)] != exp_result:
                    self.logger.info("Traffic should have been dropped for port %d" %port)
                    assert False, "%s test for port %d is not as expected"%(protocol,port)

        # add new rule but different action
        self.logger.info("Add a new rule with the different action")
        vn1_acl_icmprule_id_2 = vpc_fixture.create_aclrule('3', 'icmp', vn1_acllist_id,
                                  vn2_subnets[0], 'egress', 'deny', icmptype=8, icmpcode=0)
        result = check_all_connectivity()
        if result['icmp'] != False:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if protocol == "udp" or port != startport+1:
                    exp_result = False
                else:
                    exp_result = True
                if result['%s%d'%(protocol,port)] != exp_result:
                    assert False, "%s test for port %d is not OK"%(protocol,port)
                    self.logger.info("Traffic should have been dropped for port %d" %port)

        assert vpc_fixture.delete_aclrule(vn1_acl_new_rule_id), "Failed to delete tcp rule"
        assert vpc_fixture.delete_aclrule(vn1_acl_new_rule_id_2), "Failed to delete udp rule"
        assert vpc_fixture.delete_aclrule(vn1_acl_icmprule_id_2), "Failed to delete icmp rule"

        # Add to any network egress rule
        #vn1_acl_new_rule_id = vpc_fixture.create_aclrule('1', 'tcp', vn1_acllist_id,
        #                          "0.0.0.0/0", 'egress', 'allow', startport=startport, endport=endport)
        #result = check_all_connectivity()
        #if result['icmp'] != True:
        #   assert False, "Traffic verification failed"
        #for port in range (startport, endport+1):
        #    for protocol in ['tcp', 'udp']:
        #        if protocol == 'tcp':
        #            exp_result = True
        #        else:
        #            exp_result = False
        #        if result['%s%d'%(protocol,port)] != exp_result:
        #            self.logger.info("Traffic should have been dropped for port %d" %port)
        #            assert False, "%s test for port %d is not as expected"%(protocol,port)
        #assert vpc_fixture.delete_aclrule(vn1_acl_new_rule_id), "Failed to delete tcp rule"

        self.logger.info("Modify the TCP rule to be a UDP rule")
        vn1_acl_tcprule_id = vpc_fixture.modify_aclrule('6', 'udp', vn1_acl_tcprule_id, vn2_subnets[0],
                                                        'egress', 'allow', startport=startport, endport=endport)
        result = check_all_connectivity()
        if result['icmp'] != True:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if protocol == "tcp":
                    exp_result = False
                else:
                    exp_result = True
                if result['%s%d'%(protocol,port)] != exp_result:
                    assert False, "%s test for port %d is not OK"%(protocol,port)
                    self.logger.info("Traffic should have been dropped for port %d" %port)

        self.logger.info("Modify the UDP rule to be an all rule")

        # TODO: MSENTHIL change assert not to assert once PR is fixed
        assert vpc_fixture.modify_aclrule('7', 'all', vn1_acl_udprule_id, vn2_subnets[0],
                                               'egress', 'allow')
        result = check_all_connectivity()
        if result['icmp'] != True:
           assert False, "Traffic verification failed"
        for port in range (startport, endport+1):
            for protocol in ['tcp', 'udp']:
                if result['%s%d'%(protocol,port)] != True:
                    assert False, "%s test for port %d is not OK"%(protocol,port)
                    self.logger.info("Traffic should have been dropped for port %d" %port)

        # Misc testing... readding the same rule
        self.logger.info("Readd the same rule with same action and different action")
        assert not vpc_fixture.create_aclrule('6', 'udp', vn1_acllist_id, vn2_subnets[0],
                                              'egress', 'allow', startport=startport+1, endport=startport+1)
        assert not vpc_fixture.create_aclrule('6', 'udp', vn1_acllist_id, vn2_subnets[0],
                                              'egress', 'deny', startport=startport+1, endport=startport+1)
        return True

    @preposttest_wrapper
    def test_vpc_acllists(self):
        def check_all_connectivity():
            result = {}
            cmd = 'service iptables stop'
            vm1_fixture.run_cmd_on_vm( cmds= [cmd])
            vm2_fixture.run_cmd_on_vm( cmds= [cmd])
            vm3_fixture.run_cmd_on_vm( cmds= [cmd])

            for port in range (startport, endport+1):
                cmd1 = 'traceroute -T -p %d %s -n -N 1 -q 1 -m 1' %(port, vm2_fixture.vm_ip)
                cmd2 = 'traceroute -T -p %d %s -n -N 1 -q 1 -m 1' %(port, vm3_fixture.vm_ip)
                vm1_fixture.run_cmd_on_vm( cmds= [cmd1, cmd2])
                output = vm1_fixture.return_output_cmd_dict[cmd1]
                m = re.search("1\s+%s"%vm2_fixture.vm_ip, output)
                if m:
                    result.update({'vm2%d'%port: True})
                else:
                    self.logger.info("tcp traffic test for port %d failed for vm2"%port)
                    result.update({'vm2%d'%port: False})
                output = vm1_fixture.return_output_cmd_dict[cmd2]
                m = re.search("1\s+%s"%vm3_fixture.vm_ip, output)
                if m:
                    result.update({'vm3%d'%port: True})
                else:
                    self.logger.info("tcp traffic test for port %d failed for vm3"%port)
                    result.update({'vm3%d'%port: False})
            return result

        (vpc_name, cidr) = ('vpc1', '10.2.0.0/16')
        (vn1_name, vn1_subnets) = ('vpcnet1', ['10.2.100.0/24'])
        (vn2_name, vn2_subnets) = ('vpcnet2', ['10.2.101.0/24'])
        (vn3_name, vn3_subnets) = ('vpcnet3', ['10.2.102.0/24'])
        vn1_vm1_name = 'vn1testVM1'
        vn2_vm1_name = 'vn2testVM1'
        vn3_vm1_name = 'vn3testVM1'
        startport = 9999; endport = startport + 2
        vpc_fixture = self.useFixture(CSVPCFixture(vpc_name, cidr, connections = self.connections, vnc_lib_h = self.vnc_lib,
                                                    project_name= self.inputs.project_name))
        vn1_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn1_name,
                                                inputs= self.inputs, subnets= vn1_subnets, vpc_id = vpc_fixture.vpc_id))
        vn2_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn2_name,
                                                inputs= self.inputs, subnets= vn2_subnets, vpc_id = vpc_fixture.vpc_id))
        vn3_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn3_name,
                                                inputs= self.inputs, subnets= vn3_subnets, vpc_id = vpc_fixture.vpc_id))
        vm1_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vn2_fixture.obj, vm_name= vn2_vm1_name))
        vm3_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vn3_fixture.obj, vm_name= vn3_vm1_name))
        assert vm1_fixture.verify_on_setup(), "VM verification failed - %s" %vn1_vm1_name
        assert vm2_fixture.verify_on_setup(), "VM verification failed - %s" %vn2_vm1_name
        assert vm3_fixture.verify_on_setup(), "VM verification failed - %s" %vn3_vm1_name

        vn1_acllist_id = vpc_fixture.create_acllist(vpc_fixture.vpc_id, 'vn1_acllist')
        vn2_acllist_id = vpc_fixture.create_acllist(vpc_fixture.vpc_id, 'vn2_acllist')
        vn3_acllist_id = vpc_fixture.create_acllist(vpc_fixture.vpc_id, 'vn3_acllist')

        #associate the aclid to the network
        assert vpc_fixture.bind_acl_nw(vn1_acllist_id, vn1_fixture.vn_id), "binding acl to network failed"

        vn1_acl_tcprule_id_1 = vpc_fixture.create_aclrule('6', 'tcp', vn1_acllist_id, vn2_subnets[0],
                                  'egress', 'allow', startport=startport, endport=endport)
        vn1_acl_tcprule_id_2 = vpc_fixture.create_aclrule('7', 'tcp', vn1_acllist_id, vn3_subnets[0],
                                  'egress', 'allow', startport=startport, endport=endport)

        vn2_acl_tcprule_id = vpc_fixture.create_aclrule('6', 'tcp', vn2_acllist_id, vn1_subnets[0], 'ingress',
                                  'allow', startport=startport, endport=endport)
        vn3_acl_tcprule_id = vpc_fixture.create_aclrule('6', 'tcp', vn3_acllist_id, vn1_subnets[0], 'ingress',
                                  'allow', startport=startport, endport=endport)
        assert vpc_fixture.bind_acl_nw(vn2_acllist_id, vn2_fixture.vn_id), "binding acl to network failed"

        result = check_all_connectivity()
        for port in range (startport, endport+1):
            for vm in ['vm2', 'vm3']:
                if vm == 'vm3':
                   exp_result = False
                else:
                   exp_result = True
                if result['%s%d'%(vm, port)] != exp_result:
                    assert False, "tcp test for port %d is not as expected for vm %s"%(port,vm)

        assert vpc_fixture.bind_acl_nw(vn3_acllist_id, vn3_fixture.vn_id), "binding acl to network failed"

        result = check_all_connectivity()
        for port in range (startport, endport+1):
            for vm in ['vm2', 'vm3']:
                if result['%s%d'%(vm, port)] != True:
                    assert False, "tcp test for port %d is not as expected for vm %s"%(port,vm)

        # Add deny tcp rule for CIDR and try deleting the same TODO Uncomment the set once the PR is fixed
        #vn1_acl_anyrule_id = vpc_fixture.create_aclrule('1', 'tcp', vn1_acllist_id, cidr,
        #                         'egress', 'deny', startport=startport, endport=endport)
        #assert vn1_acl_anyrule_id, "Unable to create a network rule with vpc CIDR"
        #result = check_all_connectivity()
        #for port in range (startport, endport+1):
        #    for vm in ['vm2', 'vm3']:
        #        if result['%s%d'%(vm, port)] != False:
        #            assert False, "tcp test for port %d is not as expected for vm %s"%(port,vm)

        # Delete rule TODO
        #assert vpc_fixture.delete_aclrule(vn1_acl_anyrule_id), "Unable to delete acl rule"

        # Unbinding a list from a network
        #assert vpc_fixture.bind_acl_nw(vn3_acllist_id), "unbinding acl from network failed"
        #result = check_all_connectivity()
        #for port in range (startport, endport+1):
        #    for vm in ['vm2', 'vm3']:
        #        if vm == 'vm3':
        #            exp_result = False
        #        else:
        #            exp_result = True
        #        if result['%s%d'%(vm, port)] != exp_result:
        #            assert False, "tcp test for port %d is not as expected for vm %s"%(port,vm)

        # Create a new list and bind it to the VN
        vn3_acllist_id_2 = vpc_fixture.create_acllist(vpc_fixture.vpc_id, 'vn3_acllist_2')
        vn3_acl_tcprule_id2_1 = vpc_fixture.create_aclrule('6', 'tcp', vn3_acllist_id_2, vn1_subnets[0], 'ingress',
                                  'allow', startport=startport+1, endport=startport+1)
        assert vpc_fixture.bind_acl_nw(vn3_acllist_id_2, vn3_fixture.vn_id), "binding acl from network failed"

        result = check_all_connectivity()
        for port in range (startport, endport+1):
            for vm in ['vm2', 'vm3']:
                if vm == 'vm3' and port != startport+1:
                    exp_result = False
                else:
                    exp_result = True
                if result['%s%d'%(vm, port)] != exp_result:
                    assert False, "tcp test for port %d is not as expected for vm %s"%(port,vm)

        # Add back the old list too. Testing multiple list attached to a VN
        vn3_acl_tcprule_id_2 = vpc_fixture.create_aclrule('1', 'tcp', vn3_acllist_id, vn1_subnets[0], 'ingress',
                                  'deny', startport=startport, endport=startport)
        assert vpc_fixture.bind_acl_nw(vn3_acllist_id, vn3_fixture.vn_id), "binding acl from network failed"
        result = check_all_connectivity()
        for port in range (startport, endport+1):
            for vm in ['vm2', 'vm3']:
                if vm == 'vm3' and port == startport:
                    exp_result = False
                else:
                    exp_result = True
                if result['%s%d'%(vm, port)] != exp_result:
                    assert False, "tcp test for port %d is not as expected for vm %s"%(port,vm)

        # ToDo TODO uncomment Delete the old list
        assert vpc_fixture.delete_acllist(vn3_acllist_id_2), "Deleting the unbound acl list failed"
        result = check_all_connectivity()
        for port in range (startport, endport+1):
            for vm in ['vm2', 'vm3']:
                if vm == 'vm3' and port == startport:
                    exp_result = False
                else:
                    exp_result = True
                if result['%s%d'%(vm, port)] != exp_result:
                    assert False, "tcp test for port %d is not as expected for vm %s"%(port,vm)

        # Attach one list to multiple VNs
        vn2_acl_tcprule_id_2 = vpc_fixture.create_aclrule('7', 'tcp', vn2_acllist_id, vn1_subnets[0], 'ingress',
                                                          'allow', startport=startport, endport=endport)
        assert vpc_fixture.bind_acl_nw(vn2_acllist_id, vn3_fixture.vn_id), "binding acl from network failed"
        result = check_all_connectivity()
        for port in range (startport, endport+1):
            for vm in ['vm2', 'vm3']:
                if result['%s%d'%(vm, port)] != True:
                    assert False, "tcp test for port %d is not as expected for vm %s"%(port,vm)

        return True

    @preposttest_wrapper
    def test_multiple_vpc(self):
        def check_all_connectivity(cross_vpc=None):
            result = {}
            cmd = 'service iptables stop'
            vpc1_vm1_fixture.run_cmd_on_vm( cmds= [cmd])
            vpc1_vm2_fixture.run_cmd_on_vm( cmds= [cmd])
            vpc2_vm1_fixture.run_cmd_on_vm( cmds= [cmd])
            vpc2_vm2_fixture.run_cmd_on_vm( cmds= [cmd])

            for port in range (startport, endport+1):
                if cross_vpc and cross_vpc == True:
                    vm_ip = vpc2_vm1_fixture.vm_ip
                else:
                    vm_ip = vpc1_vm2_fixture.vm_ip
                cmd = 'traceroute -T -p %d %s -n -N 1 -q 1 -m 1' %(port, vm_ip)
                vpc1_vm1_fixture.run_cmd_on_vm( cmds= [cmd])
                output = vpc1_vm1_fixture.return_output_cmd_dict[cmd]
                m = re.search("1\s+%s"%vm_ip, output)
                if m:
                    result.update({'vpc1%d'%port: True})
                else:
                    self.logger.info("tcp traffic test for port %d failed for vpc1"%port)
                    result.update({'vpc1%d'%port: False})
                if cross_vpc and cross_vpc == True:
                    vm_fixture = vpc1_vm1_fixture
                else:
                    vm_fixture = vpc2_vm1_fixture
                cmd = 'traceroute -T -p %d %s -n -N 1 -q 1 -m 1' %(port, vpc2_vm2_fixture.vm_ip)
                vm_fixture.run_cmd_on_vm( cmds= [cmd])
                output = vm_fixture.return_output_cmd_dict[cmd]
                m = re.search("1\s+%s"%vpc2_vm2_fixture.vm_ip, output)
                if m:
                    result.update({'vpc2%d'%port: True})
                else:
                    self.logger.info("tcp traffic test for port %d failed for vpc2"%port)
                    result.update({'vpc2%d'%port: False})
            return result

        (vpc1_name, cidr1) = ('vpc1', '10.1.0.0/16')
        (vpc2_name, cidr2) = ('vpc2', '10.2.0.0/16')
        (vpc1_vn1_name, vpc1_vn1_subnets) = ('vpc1_vpcnet1', ['10.1.101.0/24'])
        (vpc1_vn2_name, vpc1_vn2_subnets) = ('vpc1_vpcnet2', ['10.1.102.0/24'])
        (vpc2_vn1_name, vpc2_vn1_subnets) = ('vpc2_vpcnet1', ['10.2.101.0/24'])
        (vpc2_vn2_name, vpc2_vn2_subnets) = ('vpc2_vpcnet2', ['10.2.102.0/24'])
        vpc1_vn1_vm1_name = 'vpc1vn1testVM1'
        vpc1_vn2_vm1_name = 'vpc1vn2testVM1'
        vpc2_vn1_vm1_name = 'vpc2vn1testVM1'
        vpc2_vn2_vm1_name = 'vpc2vn2testVM1'
        startport = 9999; endport = startport + 2
        vpc1_fixture = self.useFixture(CSVPCFixture(vpc1_name, cidr1, connections = self.connections, vnc_lib_h = self.vnc_lib,
                                                    project_name= self.inputs.project_name))
        vpc2_fixture = self.useFixture(CSVPCFixture(vpc2_name, cidr2, connections = self.connections, vnc_lib_h = self.vnc_lib,
                                                    project_name= self.inputs.project_name))
        vpc1_vn1_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vpc1_vn1_name,
                                                inputs= self.inputs, subnets= vpc1_vn1_subnets, vpc_id = vpc1_fixture.vpc_id))
        vpc2_vn1_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vpc2_vn1_name,
                                                inputs= self.inputs, subnets= vpc2_vn1_subnets, vpc_id = vpc2_fixture.vpc_id))
        vpc1_vn2_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vpc1_vn2_name,
                                                inputs= self.inputs, subnets= vpc1_vn2_subnets, vpc_id = vpc1_fixture.vpc_id))
        vpc2_vn2_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vpc2_vn2_name,
                                                inputs= self.inputs, subnets= vpc2_vn2_subnets, vpc_id = vpc2_fixture.vpc_id))
        vpc1_vm1_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vpc1_vn1_fixture.obj, vm_name= vpc1_vn1_vm1_name))
        vpc1_vm2_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vpc1_vn2_fixture.obj, vm_name= vpc1_vn2_vm1_name))
        vpc2_vm1_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vpc2_vn1_fixture.obj, vm_name= vpc2_vn1_vm1_name))
        vpc2_vm2_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vpc2_vn2_fixture.obj, vm_name= vpc2_vn2_vm1_name))
        assert vpc1_vm1_fixture.verify_on_setup(), "VM verification failed - %s" %vpc1_vn1_vm1_name
        assert vpc1_vm2_fixture.verify_on_setup(), "VM verification failed - %s" %vpc1_vn2_vm1_name
        assert vpc2_vm1_fixture.verify_on_setup(), "VM verification failed - %s" %vpc2_vn1_vm1_name
        assert vpc2_vm2_fixture.verify_on_setup(), "VM verification failed - %s" %vpc2_vn2_vm1_name

        vpc1_vn1_acllist_id = vpc1_fixture.create_acllist(vpc1_fixture.vpc_id, 'vpc1_vn1_acllist')
        vpc1_vn2_acllist_id = vpc1_fixture.create_acllist(vpc1_fixture.vpc_id, 'vpc1_vn2_acllist')
        vpc2_vn1_acllist_id = vpc2_fixture.create_acllist(vpc2_fixture.vpc_id, 'vpc2_vn1_acllist')
        vpc2_vn2_acllist_id = vpc2_fixture.create_acllist(vpc2_fixture.vpc_id, 'vpc2_vn2_acllist')

        #associate the aclid to the network
        assert vpc1_fixture.bind_acl_nw(vpc1_vn1_acllist_id, vpc1_vn1_fixture.vn_id), "binding acl to network failed"
        assert vpc2_fixture.bind_acl_nw(vpc2_vn1_acllist_id, vpc2_vn1_fixture.vn_id), "binding acl to network failed"

        vpc1_vn1_acl_tcprule_id = vpc1_fixture.create_aclrule('6', 'tcp', vpc1_vn1_acllist_id, vpc1_vn2_subnets[0],
                                  'egress', 'allow', startport=startport, endport=endport)
        vpc2_vn1_acl_tcprule_id = vpc2_fixture.create_aclrule('6', 'tcp', vpc2_vn1_acllist_id, vpc2_vn2_subnets[0],
                                  'egress', 'allow', startport=startport, endport=endport)

        # TODO: Workaround of setting the ingress acl address set to vn2_subnets it should be set to vn1_subnets once the issue is resolved
        vpc1_vn2_acl_tcprule_id = vpc1_fixture.create_aclrule('6', 'tcp', vpc1_vn2_acllist_id, vpc1_vn1_subnets[0], 'ingress',
                                  'allow', startport=startport, endport=endport)
        vpc2_vn2_acl_tcprule_id = vpc2_fixture.create_aclrule('6', 'tcp', vpc2_vn2_acllist_id, vpc2_vn1_subnets[0], 'ingress',
                                  'allow', startport=startport, endport=endport)
        assert vpc1_fixture.bind_acl_nw(vpc1_vn2_acllist_id, vpc1_vn2_fixture.vn_id), "binding acl to network failed"
        assert vpc2_fixture.bind_acl_nw(vpc2_vn2_acllist_id, vpc2_vn2_fixture.vn_id), "binding acl to network failed"

        result = check_all_connectivity()
        for port in range (startport, endport+1):
            for vpc in ['vpc1', 'vpc2']:
                if result['%s%d'%(vpc, port)] != True:
                    assert False, "tcp test for port %d is not as expected for vpc %s"%(port,vpc)

        # Cross VPC traffic test
        vpc1_vn1_acl_tcprule_id_2 = vpc1_fixture.create_aclrule('7', 'tcp', vpc1_vn1_acllist_id, vpc2_vn1_subnets[0],
                                  'egress', 'allow', startport=startport, endport=endport)
        vpc2_vn1_acl_tcprule_id_2 = vpc2_fixture.create_aclrule('7', 'tcp', vpc2_vn1_acllist_id, vpc1_vn1_subnets[0], 'ingress',
                                  'allow', startport=startport, endport=endport)

        result = check_all_connectivity(cross_vpc=True)
        for port in range (startport, endport+1):
            for vpc in ['vpc1', 'vpc2']:
                if vpc == 'vpc1':
                    exp_result = True
                else:
                    exp_result = False
                if result['%s%d'%(vpc, port)] != exp_result:
                    assert False, "tcp test for port %d is not as expected"%port
        result = check_all_connectivity()
        for port in range (startport, endport+1):
            for vpc in ['vpc1', 'vpc2']:
                if result['%s%d'%(vpc, port)] != True:
                    assert False, "tcp test for port %d is not as expected"%(port)

        # Restart a VPC
        assert vpc1_fixture.restart_vpc(), "Restart VPC failed"
        result = check_all_connectivity(cross_vpc=True)
        for port in range (startport, endport+1):
            for vpc in ['vpc1', 'vpc2']:
                if vpc == 'vpc1':
                    exp_result = True
                else:
                    exp_result = False
                if result['%s%d'%(vpc, port)] != exp_result:
                    assert False, "tcp test for port %d is not as expected"%port
        result = check_all_connectivity()
        for port in range (startport, endport+1):
            for vpc in ['vpc1', 'vpc2']:
                if result['%s%d'%(vpc, port)] != True:
                    assert False, "tcp test for port %d is not as expected"%(port)

        return True

    @preposttest_wrapper
    def test_xen_host_reboot(self):
        ''' Check Systems VMs and User VMs status after reboot
        '''
        def get_pool_master():
            cmd = "xe host-param-get uuid=$(xe pool-param-get uuid=$(xe pool-list --minimal) param-name=master) param-name=address"
            self.master = self.inputs.run_cmd_on_server(self.inputs.compute_ips[0], cmd,
                          username=self.inputs.host_data[self.inputs.compute_ips[0]]['username'],
                          password=self.inputs.host_data[self.inputs.compute_ips[0]]['password'])
            self.logger.info("Pool master is %s"%self.master)

        def enable_maintenance_mode(host_name):
            host_id = self.connections.instance_handle.get_node_id_from_name(host_name)
            self.logger.info("Preparing maintenance mode on host %s"%host_name)
            response = self.connections.cstack_handle.client.request('prepareHostForMaintenance', {'id': host_id })
            if response['queryasyncjobresultresponse']['jobprocstatus'] != 0:
                self.logger.error('Unable to put host %s on maintenance mode' %host_name)
                return False
            result = response['queryasyncjobresultresponse']
            return result

        def cancel_maintenance_mode(host_name):
            host_id = self.connections.instance_handle.get_node_id_from_name(host_name)
            self.logger.info("Canceling maintenance mode on host %s"%host_name)
            response = self.connections.cstack_handle.client.request('cancelHostMaintenance', {'id': host_id })
            if response['queryasyncjobresultresponse']['jobprocstatus'] != 0:
                self.logger.error('Unable to put host %s on maintenance mode' %host_name)
                return False
            result = response['queryasyncjobresultresponse']
            return result

        get_pool_master()
        master = self.inputs.host_data[self.master]['name']

        vn1_name='vn-xen-reboot'; vn1_subnets=['172.16.17.0/24']
        vm1_name= vn1_name+'-vm1'; vm2_name= vn1_name+'-vm2'; vm3_name= vn1_name+'-vm3'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()

        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, flavor= "small", vn_obj= vn1_fixture.obj, vm_name= vm1_name, node_name= master))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, flavor= "small", vn_obj= vn1_fixture.obj, vm_name= vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )

        if self.inputs.host_data[vm1_fixture.vm_node_ip]['name'] != master:
            self.logger.error('VM %s is not launched on host %s' %(vm1_name, master))
            return False

        self.logger.info("Master node %s will be prepared for maintenace" %master)

        # Reboot Xen Host
        assert enable_maintenance_mode( master )
        try:
            if len(self.inputs.compute_ips) > 1:
                sleep(120)
                for i in range (0, 10):
                    sleep(30)
                    vm1_fixture.update_vm_obj()
                    if self.inputs.host_data[vm2_fixture.vm_node_ip]['name'] == master:
                        vm2_fixture.update_vm_obj()
                    if vm1_fixture.vm_node_ip and self.inputs.host_data[vm1_fixture.vm_node_ip]['name'] != master and \
                       vm2_fixture.vm_node_ip and self.inputs.host_data[vm2_fixture.vm_node_ip]['name'] != master:
                        break
                else:
                    self.logger.error('VM didnt migrate to the other host')
                    raise
            self.inputs.run_cmd_on_server(self.master, 'reboot',
                        username=self.inputs.host_data[self.master]['username'],
                        password=self.inputs.host_data[self.master]['password'])
        except:
            cancel_maintenance_mode(master)
            raise
        sleep(300)
        cancel_maintenance_mode(master)
        connections.clear()
        assert self.isSystemVmUp(), "System Vms are not up after reboot and a wait of 10 mins"

        if len(self.inputs.compute_ips) > 1:

            domain_id= self.connections.instance_handle.get_domain_id_of_vm( vm1_fixture.vm_node_ip, vm1_fixture.vm_obj )
            self.connections.instance_handle.stop_vncterm( vm1_fixture.vm_node_ip, domain_id )
            domain_id= self.connections.instance_handle.get_domain_id_of_vm( vm2_fixture.vm_node_ip, vm2_fixture.vm_obj )
            self.connections.instance_handle.stop_vncterm( vm2_fixture.vm_node_ip, domain_id )

            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()
            assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
            assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )

            if self.inputs.host_data[vm1_fixture.vm_node_ip]['name'] == master:
                self.logger.error('VM didnt migrate to the other host on enabling maintenance mode')
                return False

            old_master = self.master
            get_pool_master()
            if master == self.inputs.host_data[self.master]['name']:
                self.logger.error('Master should have been re-elected when master is put into maintenance mode')
                return False
            slave = master
            master = self.inputs.host_data[self.master]['name']

            vm3_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, flavor= "small", vn_obj= vn1_fixture.obj, vm_name= vm3_name, node_name= slave))
            assert vm3_fixture.verify_on_setup()
            assert vm3_fixture.ping_to_ip( vm2_fixture.vm_ip )
            assert vm3_fixture.ping_to_ip( vm1_fixture.vm_ip )
            self.logger.info("Slave node %s will be prepared for maintenace" %slave)
            assert enable_maintenance_mode( slave )
            try:
                sleep(120)
                for i in range (0, 10):
                    sleep(30)
                    vm3_fixture.update_vm_obj()
                    if vm3_fixture.vm_node_ip and self.inputs.host_data[vm3_fixture.vm_node_ip]['name'] != slave:
                        break
                else:
                    self.logger.error('VM didnt migrate to the other host')
                    raise
                self.inputs.run_cmd_on_server(old_master, 'reboot',
                            username=self.inputs.host_data[old_master]['username'],
                            password=self.inputs.host_data[old_master]['password'])
            except:
                cancel_maintenance_mode(slave)
                raise
            sleep(300)
            cancel_maintenance_mode(slave)
            connections.clear()
            assert self.isSystemVmUp(), "System Vms are not up after reboot and a wait of 10 mins"

            vm1_fixture.update_vm_obj()
            if self.inputs.host_data[vm1_fixture.vm_node_ip]['name'] != master:
                self.logger.error('VM %s got migrated to the other host. It shouldnt have' %vm1_name)
                return False
            get_pool_master()
            if master != self.inputs.host_data[self.master]['name']:
                self.logger.error('Master shouldnt have been re-elected when slave is put into maintenance mode')
                return False
            domain_id= self.connections.instance_handle.get_domain_id_of_vm( vm3_fixture.vm_node_ip, vm3_fixture.vm_obj )
            self.connections.instance_handle.stop_vncterm( vm3_fixture.vm_node_ip, domain_id )
            assert vm3_fixture.verify_on_setup()
            assert vm3_fixture.ping_to_ip( vm2_fixture.vm_ip )
            assert vm3_fixture.ping_to_ip( vm1_fixture.vm_ip )
        else:
            vm1_fixture.start_vm()
            vm2_fixture.start_vm()

        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )

        return True
    #end test_xen_host_reboot

    @preposttest_wrapper
    def test_migrate_vm(self):
        ''' Test migrate of User VMs '''

        if len(self.inputs.compute_ips) < 2:
            self.logger.info("\nWARNING: This test is specific to multi node.\n\t Bailing Out\n")
            print "This test is specific to multi node"
            return False

        vn1_name='vn-migrate-vm'; vn1_subnets=['172.18.19.0/24']
        vm1_name= vn1_name+'-vm1'; vm2_name= vn1_name+'-vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()

        first_host = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        second_host = self.inputs.host_data[self.inputs.compute_ips[1]]['name']
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, flavor= "small", vn_obj= vn1_fixture.obj, vm_name= vm1_name, node_name= first_host))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, flavor= "small", vn_obj= vn1_fixture.obj, vm_name= vm2_name, node_name= second_host))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        if self.inputs.host_data[vm1_fixture.vm_node_ip]['name'] != first_host:
            self.logger.error('VM %s is not launched on host %s' %(vm1_name, first_host))
            return False
        if self.inputs.host_data[vm2_fixture.vm_node_ip]['name'] != second_host:
            self.logger.error('VM %s is not launched on host %s' %(vm2_name, second_host))
            return False

        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )

        # Migrate VM1 to Host2 and VM2 to Host1
        vm1_fixture.migrate_vm( second_host )
        vm2_fixture.migrate_vm( first_host )

        '''
        sleep(120)
        for i in range (0, 10):
            sleep(30)
            vm1_fixture.update_vm_obj()
            if self.inputs.host_data[vm2_fixture.vm_node_ip]['name'] == master:
                vm2_fixture.update_vm_obj()
            if vm1_fixture.vm_node_ip and self.inputs.host_data[vm1_fixture.vm_node_ip]['name'] != master and \
               vm2_fixture.vm_node_ip and self.inputs.host_data[vm2_fixture.vm_node_ip]['name'] != master:
                break
        else:
            self.logger.error('VM didnt migrate to the other host')
            raise
        '''

        if self.inputs.host_data[vm1_fixture.vm_node_ip]['name'] != second_host:
            self.logger.error('VM %s didnt migrate to host %s' %(vm1_name, second_host))
            return False
        if self.inputs.host_data[vm2_fixture.vm_node_ip]['name'] != first_host:
            self.logger.error('VM %s didnt migrate to host %s' %(vm2_name, first_host))
            return False

        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )

        return True


    @preposttest_wrapper
    def test_dedicated_host(self):
        ''' Check Systems VMs and User VMs status after reboot
        '''
        def dedicate_host(host_name):
            host_id = self.connections.instance_handle.get_node_id_from_name(host_name)
            domain_response = self.connections.cstack_handle.client.request('listDomains', {'name': 'ROOT'})
            domain_id= domain_response['listdomainsresponse']['domain'][0]['id']
            params = { 'domainid': domain_id, 'hostid': host_id }
            response = self.connections.cstack_handle.client.request('dedicateHost', params)
            if response['queryasyncjobresultresponse']['jobprocstatus'] != 0 :
                self.logger.error('Unable to put host %s on dedicated mode' %host_name)
                return False
            aff_group_response = self.connections.cstack_handle.client.request('listAffinityGroups')
            aff_group_id = aff_group_response['listaffinitygroupsresponse']['affinitygroup'][0]['id']
            return aff_group_id

        def release_dedicate_host(host_name):
            host_id = self.connections.instance_handle.get_node_id_from_name(host_name)
            response = self.connections.cstack_handle.client.request('releaseDedicatedHost', { 'hostid': host_id })
            if response['queryasyncjobresultresponse']['jobresult']['success'] != True:
                self.logger.error('Unable to release host %s from dedicated mode' %host_name)
                return False
            return True

        if len(self.inputs.compute_ips) < 2:
            self.logger.error("\nWARNING: This test is specific to multi node.\n\t Bailing Out\n")
            print "This test is specific to multi node"
            return False

        vn1_name='vn-dedicated-host'; vn1_subnets=['172.17.18.0/24']
        vm1_name= vn1_name+'-vm1'; vm2_name= vn1_name+'-vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        first_host = self.inputs.host_data[self.inputs.compute_ips[0]]['name']
        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, flavor= "small", vn_obj= vn1_fixture.obj, vm_name= vm1_name, node_name= first_host))
        assert vm1_fixture.verify_on_setup()
        if vm1_fixture.vm_node_ip != self.inputs.compute_ips[0]:
            assert False, "VM got launched on a different host than requested"

        # Put the other node on dedicated mode and start the other VM on that node
        dedicated_node = self.inputs.host_data[self.inputs.compute_ips[1]]['name']
        try:
            affinity_groupid = dedicate_host(dedicated_node)
        except:
            self.logger.error('Unable to put host %s on dedicated mode' %dedicated_node)
            return False
        vm2_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections, flavor= "small", vn_obj= vn1_fixture.obj, vm_name= vm2_name, affinity_group_ids= affinity_groupid))
        if vm2_fixture.vm_node_ip != self.inputs.compute_ips[1]:
            assert False, "VM got launched on a different host than requested"

        assert vm2_fixture.verify_on_setup()

        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )

        assert release_dedicate_host(dedicated_node), "Unable to release the dedicated host"
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )

        return True
    #end test_dedicated_host

    @preposttest_wrapper
    def test_deploy_vsrx(self):
        '''Validate creating vSRX instance in custom project, create VM and reach outside world
        '''
        result = True
        project_name = 'vsrx_proj2' 
        vn1_name='__service2__'
        vn1_subnets=['10.254.42.0/24']
        vsrx_instance_name = 'vSRX_appliance'
        project_fixture = self.useFixture(ProjectFixture(connections = self.connections, vnc_lib_h = self.vnc_lib,
                                          project_name = project_name))
        vn1_fixture = self.useFixture(VNFixture(project_name= project_name, connections=
                                     self.connections, vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        vn1_vm1_name = 'vn1-guest-vm'
        vsrx_fixture = self.useFixture(vSRXFixture(project_name = project_name, connections = self.connections,
                                                   vn_fixture = vn1_fixture.obj, instance_name = vsrx_instance_name))
        print vsrx_fixture.vsrxinstance_obj
        vsrx_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup(), "VM %s verification failed in a new project" %(vn1_vm1_name)
        vm1_fixture.verify_on_setup()
        assert vm1_fixture.ping_with_certainty('yahoo.com'), "Ping to website name failed!"
        vm1_fixture.ping_with_certainty('yahoo.com')
        return True
    #end test_deploy_vsrx

    @preposttest_wrapper
    def test_analytics(self):
        project_name = 'project01'
        (vn1_name, vn1_subnets)= ("vn1", ["192.168.1.0/24"])
        (vn2_name, vn2_subnets)= ("vn2", ["192.168.2.0/24"])
        (vn1_vm1_name, vn1_vm2_name)=( 'vn1-vm1', 'vn1-vm2')
        (vn2_vm1_name, vn2_vm2_name)=( 'vn2-vm1', 'vn2-vm2')

        project_fixture = self.useFixture(ProjectFixture(connections= self.connections, vnc_lib_h= self.vnc_lib, project_name= project_name))
        vn1_fixture=self.useFixture( VNFixture(project_name= project_name, connections= self.connections, inputs= self.inputs, vn_name= vn1_name, subnets= vn1_subnets))
        vn2_fixture=self.useFixture( VNFixture(project_name= project_name, connections= self.connections, inputs= self.inputs, vn_name= vn2_name, subnets= vn2_subnets))
        vn1_vm1_fixture=self.useFixture(VMFixture(project_name= project_name, connections= self.connections, vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))
        vn1_vm2_fixture=self.useFixture(VMFixture(project_name= project_name, connections= self.connections, vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))
        vn2_vm1_fixture=self.useFixture(VMFixture(project_name= project_name, connections= self.connections, vn_obj= vn2_fixture.obj, vm_name= vn2_vm1_name))
        vn2_vm2_fixture=self.useFixture(VMFixture(project_name= project_name, connections= self.connections, vn_obj= vn2_fixture.obj, vm_name= vn2_vm2_name))

        vn_list=[vn1_fixture.vn_fq_name,vn2_fixture.vn_fq_name]
        vm_fixture_list=[vn1_vm1_fixture,vn1_vm2_fixture,vn2_vm1_fixture,vn2_vm2_fixture]

        '''Verify all hyperlinks under uves
        '''
        assert self.analytics_obj.verify_all_uves()

        '''Test to validate vn uve receives uve message from api-server and Agent.
        '''
        for vn in vn_list:
            assert self.analytics_obj.verify_vn_uve_tiers(vn_fq_name=vn)

        '''Test to validate routing instance in vn uve.
        '''
        for vn in vn_list:
            assert self.analytics_obj.verify_vn_uve_ri(vn_fq_name=vn)

        '''Test to validate vm list,connected networks and tap interfaces in vrouter uve.
        '''
        for vm_fixture in vm_fixture_list:
            assert vm_fixture.verify_on_setup()
            vm_uuid=vm_fixture.vm_id
            vm_node_ip= vm_fixture.vm_node_ip
            vn_of_vm= vm_fixture.vn_fq_name
            vm_host=self.inputs.host_data[vm_node_ip]['name']
            interface_name=vm_fixture.agent_inspect[vm_node_ip].get_vna_tap_interface_by_vm(vm_id= vm_uuid)[0]['config_name']
            self.logger.info("expected tap interface of vm uuid %s is %s"%(vm_uuid,interface_name))
            self.logger.info("expected virtual netowrk  of vm uuid %s is %s"%(vm_uuid,vn_of_vm))
            assert self.analytics_obj.verify_vm_list_in_vrouter_uve(vm_uuid=vm_uuid,vn_fq_name=vn_of_vm,vrouter=vm_host,tap=interface_name)

        '''Test to validate virtual machine uve tiers - should be UveVirtualMachineAgent.
        '''
        vm_id_list=[vn1_vm1_fixture.vm_instance_name, vn1_vm2_fixture.vm_instance_name, vn2_vm1_fixture.vm_instance_name, vn2_vm2_fixture.vm_instance_name]
        for id in vm_id_list:
            assert self.analytics_obj.verify_vm_uve_tiers(uuid=id)

        ''' Test bgp-router uve for active xmpp/bgp connections count
        '''
        assert self.analytics_obj.verify_bgp_router_uve_xmpp_and_bgp_count()
        assert self.analytics_obj.verify_bgp_router_uve_up_xmpp_and_bgp_count()
        assert self.analytics_obj.get_peer_stats_info_tx_proto_stats(self.inputs.collector_ips[0], self.inputs.bgp_names[0])

        ''' Test all hrefs for collector/agents/bgp-routers etc
        '''
        assert self.analytics_obj.verify_hrefs_to_all_uves_of_a_given_uve_type()

        '''Test to validate collector uve process states.
        '''
        process_list = ['redis-query', 'contrail-qe','contrail-collector','contrail-analytics-nodemgr','redis-uve','contrail-opserver']
        for process in process_list:
            assert self.analytics_obj.verify_collector_uve_module_state(self.inputs.collector_names[0],self.inputs.collector_names[0],process)

        '''Test to validate config node uve process states.
        '''
        process_list = ['contrail-discovery:0', 'contrail-config-nodemgr','ifmap','contrail-api:0','contrail-schema']
        for process in process_list:
            assert self.analytics_obj.verify_cfgm_uve_module_state(self.inputs.collector_names[0],self.inputs.cfgm_names[0],process)

        """
        '''Test object tables.
        '''
        start_time=self.analytics_obj.get_time_since_uptime(self.inputs.cfgm_ip)
        assert self.analytics_obj.verify_object_tables(start_time= start_time, skip_tables = [u'MessageTable', \
                                                            u'ObjectDns', u'ObjectVMTable', \
                                                            u'ConfigObjectTable', u'ObjectQueryTable', \
                                                            u'ObjectBgpPeer', u'ObjectBgpRouter', u'ObjectXmppConnection',\
                                                             u'ObjectVNTable', u'ObjectGeneratorInfo', u'ObjectRoutingInstance', \
                                                            u'ObjectVRouter', u'ObjectConfigNode', u'ObjectXmppPeerInfo', \
                                                            u'ObjectCollectorInfo'])

        '''Test Message tables.
        '''
        assert self.analytics_obj.verify_message_table(start_time= start_time)

        '''Test stats tables.
        '''
        assert self.analytics_obj.verify_stats_tables(start_time= start_time,skip_tables = [u'StatTable.ConfigCpuState.\
                                    cpu_info', u'StatTable.AnalyticsCpuState.cpu_info', u'StatTable.ControlCpuState.cpu_info',\
                                     u'StatTable.QueryPerfInfo.query_stats', u'StatTable.UveVirtualNetworkAgent.vn_stats', \
                                    u'StatTable.SandeshMessageStat.msg_info'])
        """

        return True

    #end test_analytics

    @preposttest_wrapper
    def test_analytics_flows(self):

        result = True
        (vpc_name, cidr) = ('AnalyticsVPC', '10.11.0.0/16')
        (vn1_name, vn1_subnets) = ('AnalyticsVN10', ['10.11.100.0/24'])
        (vn2_name, vn2_subnets) = ('AnalyticsVN20', ['10.11.101.0/24'])
        vn1_vm1_name = 'AnalyticsVM1'
        vn2_vm1_name = 'AnalyticsVM2'
        vpc_fixture = self.useFixture(CSVPCFixture(vpc_name, cidr, connections = self.connections, vnc_lib_h = self.vnc_lib,
                                                    project_name= self.inputs.project_name))
        vn1_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn1_name,
                                                inputs= self.inputs, subnets= vn1_subnets, vpc_id = vpc_fixture.vpc_id))
        vn2_fixture = self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections, vn_name=vn2_name,
                                                inputs= self.inputs, subnets= vn2_subnets, vpc_id = vpc_fixture.vpc_id))
        vm1_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vn1_fixture.obj, vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name = self.inputs.project_name, connections = self.connections, vn_obj=
                                                vn2_fixture.obj, vm_name= vn2_vm1_name))
        assert vm1_fixture.verify_on_setup(), "VM verification failed - %s" %vn1_vm1_name
        assert vm2_fixture.verify_on_setup(), "VM verification failed - %s" %vn2_vm1_name

        vn1_acllist_id = vpc_fixture.create_acllist(vpc_fixture.vpc_id, 'vn1_acllist')
        vn2_acllist_id = vpc_fixture.create_acllist(vpc_fixture.vpc_id, 'vn2_acllist')

        #associate the aclid to the network
        startport = 8000; endport = startport+1000
        assert vpc_fixture.bind_acl_nw(vn1_acllist_id, vn1_fixture.vn_id), "binding acl to network failed"
        assert vpc_fixture.bind_acl_nw(vn2_acllist_id, vn2_fixture.vn_id), "binding acl to network failed"
        vn1_acl_tcprule_id = vpc_fixture.create_aclrule('1', 'udp', vn1_acllist_id, vn2_subnets[0], 'egress',
                                  'allow', startport=startport, endport=endport)
        vn2_acl_tcprule_id = vpc_fixture.create_aclrule('1', 'udp', vn2_acllist_id, vn1_subnets[0], 'ingress',
                                  'allow', startport=startport, endport=endport)

        self.tx_vm_node_ip= vm1_fixture.vm_node_ip
        self.rx_vm_node_ip= vm2_fixture.vm_node_ip
        self.tx_local_host = Host(self.tx_vm_node_ip, self.inputs.username, self.inputs.password)
        self.rx_local_host = Host(self.rx_vm_node_ip, self.inputs.username, self.inputs.password)
        vn1_fq_name = '%s:%s:%s'%(self.inputs.project_fq_name[0],self.inputs.project_fq_name[1],vn1_name)
        vn2_fq_name = '%s:%s:%s'%(self.inputs.project_fq_name[0],self.inputs.project_fq_name[1],vn2_name)

        ''' Test to validate attached policy in the virtual-networks uve '''
        assert self.analytics_obj.verify_connected_networks_in_vn_uve(vn1_fq_name,vn2_fq_name)
        assert self.analytics_obj.verify_connected_networks_in_vn_uve(vn2_fq_name,vn1_fq_name)

        pkts_before_traffic = self.analytics_obj.get_inter_vn_stats(self.inputs.collector_ips[0], src_vn=vn1_fq_name, other_vn=vn2_fq_name, direction='in')
        if not pkts_before_traffic:
            pkts_before_traffic = 0
        #Create traffic stream
        self.logger.info("Creating streams...")
        stream = Stream(protocol="ip", proto="udp", src=vm1_fixture.vm_ip,
                        dst=vm2_fixture.vm_ip, dport=startport+1)

        profile = StandardProfile(stream=stream, size=100,count=10,listener=vm2_fixture.vm_ip)
        sender = Sender("sendudp", profile, self.tx_local_host, vm1_fixture, self.inputs.logger)
        receiver = Receiver("recvudp", profile, self.rx_local_host, vm2_fixture, self.inputs.logger)
        start_time=self.analytics_obj.getstarttime(self.tx_vm_node_ip)
        self.logger.info("start time= %s"%(start_time))
        receiver.start()
        sender.start()
        time.sleep(10)
        #Poll to make sure traffic flows, optional
        #sender.poll()
        #receiver.poll()
        sender.stop()
        receiver.stop()
        print sender.sent, receiver.recv
        assert (sender.sent == receiver.recv), "UDP traffic to ip:%s failed" % self.res.vn2_vm2_fixture.vm_ip

        #Verifying the vrouter uve for the active flow
        vm_node_ip= vm1_fixture.vm_node_ip
        vm_host= self.inputs.host_data[vm_node_ip]['name']
        self.logger.info("Waiting for the %s vrouter uve to be updated with active flows"%(vm_host))
        time.sleep(60)
        self.flow_record= self.analytics_obj.get_flows_vrouter_uve(vrouter=vm_host)
        self.logger.info("Active flow in vrouter uve = %s"%(self.flow_record))
        if (self.flow_record > 0):
            self.logger.info("Flow records updated")
        else:
            self.logger.warn("Flow records NOT updated")
            result= result and False

        pkts_after_traffic = self.analytics_obj.get_inter_vn_stats(self.inputs.collector_ips[0], src_vn=vn1_fq_name, other_vn=vn2_fq_name, direction='in')
        if not pkts_after_traffic:
            pkts_after_traffic = 0
        self.logger.info("Verifying that the inter-vn stats updated")
        self.logger.info("Inter vn stats before traffic %s"%(pkts_before_traffic))
        self.logger.info("Inter vn stats after traffic %s"%(pkts_after_traffic))
        if ((pkts_after_traffic - pkts_before_traffic) >= 10):
            self.logger.info("Inter vn stats updated")
        else:
            self.logger.warn("Inter vn stats NOT updated")
            result= result and False

        self.logger.info("Waiting for flow records to be expired...")
        time.sleep(224)
        self.flow_record=self.analytics_obj.get_flows_vrouter_uve(vrouter=vm_host)
        self.logger.debug("Active flow in vrouter uve = %s"%(self.flow_record))

        #Verifying flow series table
        #src_vn='default-domain'+':'+self.inputs.project_name+':'+vn1_name
        #dst_vn='default-domain'+':'+self.inputs.project_name+':'+vn2_name
        query='('+'sourcevn='+vn1_fq_name+') AND (destvn='+vn2_fq_name+')'
        for ip in self.inputs.collector_ips:
            self.logger.info("Verifying flowRecordTable through opserver %s.."%(ip))
            output= self.analytics_obj.ops_inspect[ip].post_query('FlowRecordTable',start_time=start_time,end_time='now',
                                                                  select_fields=['sourcevn', 'sourceip', 'destvn', 'destip',
                                                                                 'setup_time','teardown_time','agg-packets'],
                                                                  where_clause=query)
            self.logger.info("Query output: %s"%output)
            assert output
            if output:
                r=output[0]
                s_time=r['setup_time']
                e_time=r['teardown_time']
                agg_pkts=r['agg-packets']
                assert (agg_pkts == sender.sent)
            self.logger.info( 'setup_time= %s,teardown_time= %s'%(s_time,e_time))
            self.logger.info("Records=\n%s"%output)
            #Quering flow sreies table
            self.logger.info("Verifying flowSeriesTable through opserver %s"%(ip))
            output=self.analytics_obj.ops_inspect[ip].post_query('FlowSeriesTable',start_time=str(s_time),
                                                                    end_time=str(e_time),select_fields=['sourcevn',
                                                                    'sourceip', 'destvn', 'destip','sum(packets)'],
                                                                    where_clause=query)
            self.logger.info("Query output: %s"%output)
            assert output
            if output:
                r1=output[0]
                sum_pkts=r1['sum(packets)']
                assert (sum_pkts == sender.sent)
            self.logger.info("Flow series Records=\n%s"%(output))
            assert (sum_pkts==agg_pkts)

        start_time=self.analytics_obj.getstarttime(self.tx_vm_node_ip)
        for i in range(10):
            count=100; dport=startport+100
            count=count* (i+1); dport=dport+i
            print 'count=%s'%(count)
            print 'dport=%s'%(dport)

            self.logger.info("Creating streams...")
            stream = Stream(protocol="ip", proto="udp", src=vm1_fixture.vm_ip,
                        dst=vm2_fixture.vm_ip, dport=dport)

            profile = StandardProfile(stream=stream, size=100, count=count, listener=vm2_fixture.vm_ip)
            sender = Sender("sendudp", profile, self.tx_local_host, vm1_fixture, self.inputs.logger)
            receiver = Receiver("recvudp", profile, self.rx_local_host, vm2_fixture, self.inputs.logger)
            receiver.start()
            sender.start()
            sender.stop()
            receiver.stop()
            print sender.sent, receiver.recv
            time.sleep(1)
        time.sleep(300)
        #Verifying flow series table
        query='('+'sourcevn='+vn1_fq_name+') AND (destvn='+vn2_fq_name+')'
        for ip in self.inputs.collector_ips:
            self.logger.info( 'setup_time= %s'%(start_time))
            #Quering flow sreies table
            self.logger.info("Verifying flowSeriesTable through opserver %s"%(ip))
            self.res1=self.analytics_obj.ops_inspect[ip].post_query('FlowSeriesTable',start_time=start_time,end_time='now'
                                               ,select_fields=['sourcevn', 'sourceip', 'destvn', 'destip','sum(packets)','sport','dport','T=1'],
                                                where_clause=query,sort=2,limit=5,sort_fields=['sum(packets)'])
            #assert self.res1
            self.logger.info("Top 5 flows %s"%(self.res1))

        #Create traffic stream
        start_time=self.analytics_obj.getstarttime(self.tx_vm_node_ip)
        self.logger.info("start time= %s"%(start_time))

        self.logger.info("Creating streams...")
        stream = Stream(protocol="ip", proto="udp", src=vm1_fixture.vm_ip, dst=vm2_fixture.vm_ip, dport=endport)
        profile = ContinuousSportRange(stream=stream, listener=vm2_fixture.vm_ip, startport= startport, endport= endport, pps= 100)
        sender = Sender('sname', profile, self.tx_local_host, vm1_fixture, self.inputs.logger)
        receiver = Receiver('rname', profile, self.rx_local_host, vm2_fixture, self.inputs.logger)
        receiver.start()
        sender.start()
        time.sleep(30)
        sender.stop()
        receiver.stop()
        print sender.sent, receiver.recv
        time.sleep(30)
        query= '(sourcevn=%s) AND (destvn=%s) AND protocol= 17 AND (sport = %s < %s)'%(vn1_fq_name, vn2_fq_name, startport+50, endport-50)
        for ip in self.inputs.collector_ips:
            self.logger.info( 'setup_time= %s'%(start_time))

            self.logger.info("Verifying flowSeriesTable through opserver %s"%(ip))
            self.res1=self.analytics_obj.ops_inspect[ip].post_query('FlowSeriesTable',start_time=start_time,end_time='now',
                                                                    select_fields=['sourcevn', 'sourceip', 'destvn', 'destip',
                                                                                   'sum(packets)','sport','dport','T=1'],
                                                                    where_clause=query)
            assert self.res1
            for elem in self.res1:
                if ((elem['sport'] < startport+50) or (elem['sport'] > endport-50)):
                    self.logger.warn("Out of range element (range:sport > 8050 and sport < 9950):%s"%(elem))
                    self.logger.warn("Test Failed")
                    result = False
                    assert result

        return result

    #end test_analytics_flows

    @preposttest_wrapper
    def test_analytics_query_logs(self):
        '''
          Description: Test to validate object logs
        '''
        vn_name='AnalyticsVN'; vn_subnets=['10.18.18.0/24']; vm1_name='AnalyticsVM'
        start_time=self.analytics_obj.getstarttime(self.inputs.cfgm_ip)
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                                              vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_fixture.obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        self.logger.info("Waiting for logs to be updated in the database...")
        time.sleep(10)
        query='('+'ObjectId=default-domain:default-project:'+vn_name+')'
        self.logger.info("Verifying ObjectVNTable through opserver %s.."%(self.inputs.collector_ips[0]))
        result=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectVNTable',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
        self.logger.info("query output : %s"%(result))
        if not result:
            st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].send_trace_to_database(node= self.inputs.collector_names[0],
                                                                            module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
            self.logger.info("status: %s"%(st))
        assert result

        self.logger.info("Getting object logs for ObjectRoutingInstance table")
        object_id='%s:%s:%s:%s'%(self.inputs.project_fq_name[0],self.inputs.project_fq_name[1],vn_name,vn_name)
        query='(ObjectId=%s)'%(object_id)
        self.logger.info("Verifying ObjectRoutingInstance through opserver %s.."%(self.inputs.collector_ips[0]))
        result=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectRoutingInstance',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
        self.logger.info("query output : %s"%(result))
        if not result:
            self.logger.warn("ObjectRoutingInstance  query did not return any output")
            st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].send_trace_to_database(node= self.inputs.collector_names[0],
                                                                            module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
            self.logger.info("status: %s"%(st))
        assert result

        self.logger.info("Getting object logs for vm")
        query='('+'ObjectId='+ vm1_fixture.vm_id +')'
        self.logger.info("Verifying ObjectVMTable through opserver %s.."%(self.inputs.collector_ips[0]))
        result=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectVMTable',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
        self.logger.info("query output : %s"%(result))
        if not result:
            st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].send_trace_to_database(node= self.inputs.collector_names[0],
                                                                            module= 'QueryEngine', trace_buffer_name= 'QeTraceBuf')
            self.logger.info("status: %s"%(st))
        assert result

        ''' Test to validate xmpp peer object logs '''
        result = True
        try:
            start_time=self.analytics_obj.getstarttime(self.inputs.compute_ips[0])
            object_id= self.inputs.bgp_names[0]+':'+self.inputs.compute_ips[0]
            query='('+'ObjectId='+ object_id +')'
            self.logger.info("Stopping the xmpp node in %s"%(self.inputs.compute_ips[0]))
            self.inputs.stop_service('contrail-vrouter',[self.inputs.compute_ips[0]])
            self.logger.info("Waiting for the logs to be updated in database..")
            time.sleep(120)
            self.logger.info("Verifying ObjectXmppPeerInfo Table through opserver %s.."%(self.inputs.collector_ips[0]))
            self.res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectXmppPeerInfo',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
            if not self.res1:
                self.logger.info("query output : %s"%(self.res1))
                st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].send_trace_to_database (node= self.inputs.collector_names[0], module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
                self.logger.info("status: %s"%(st))
                result = result and False
            start_time=self.analytics_obj.getstarttime(self.inputs.compute_ips[0])
            time.sleep(2)
            self.inputs.start_service('contrail-vrouter',[self.inputs.compute_ips[0]])
            self.logger.info("Waiting for the logs to be updated in database..")
            time.sleep(60)
            self.logger.info("Verifying ObjectXmppPeerInfo Table through opserver %s.."%(self.inputs.collector_ips[0]))
            self.res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectXmppPeerInfo',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
            if not self.res1:
                self.logger.info("query output : %s"%(self.res1))
                st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].send_trace_to_database (node= self.inputs.collector_names[0], module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
                self.logger.info("status: %s"%(st))
                result = result and False
        except Exception as e:
            print e
            result=result and False
        finally:
            self.inputs.start_service('contrail-vrouter',[self.inputs.compute_ips[0]])
            import pdb; pdb.set_trace()
            time.sleep(20)
            self.logger.info("Verifying ObjectVRouter Table through opserver %s.."%(self.inputs.collector_ips[0]))
            object_id= self.inputs.compute_names[0]
            query='('+'ObjectId='+ object_id +')'
            self.res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectVRouter',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
            if (self.res1):
                self.logger.info("ObjectVRouter table query passed")
                result = result and True
            else:
                self.logger.warn("ObjectVRouter table query failed")
                result = result and False
            assert result
            return True

