# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# n specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
from time import sleep

from common.openstack_libs import nova_client as mynovaclient
from common.openstack_libs import nova_exception as novaException
import fixtures
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from tcutils.util import *
import threading
import Queue


class create_multiple_vn_and_multiple_vm_fixture(fixtures.Fixture):

#    @classmethod
    def __init__(self, connections, inputs, policy_objs=[], subnets=[], project_name=None, image_name='ubuntu', flavor='contrail_flavor_tiny', vn_name='vn', vm_name='vm', vn_count=1, vm_count=2, subnet_count=2, af=None, userdata=None):
        """ 
        creates a dict of the format: {vn_name:{vm_name:vm_obj,...}}
        """
        self.connections = connections
        self.inputs = inputs
        if not project_name:
            project_name = self.inputs.project_name
        self.project_name = project_name
        self.vn_name = vn_name
        self.vn_count = vn_count
        self.stack = af or self.inputs.get_af()
        self.subnet_count = subnet_count
        self.vm_name = vm_name
        self.vm_count = vm_count
        self.image_name = image_name
        self.flavor = flavor
        self.nova_h = self.connections.nova_h
        self.q = Queue.Queue()
        self.vn_threads = []
        self.vm_threads = []
        self.userdata = userdata
        self.nova_h.get_image(self.image_name)
        self.random_subnets = []

    def calculateSubnetAF(self, af):
        while True:
            network=get_random_cidr(af=af, mask=SUBNET_MASK[af]['min'])
            for rand_net in self.random_subnets:
                if not cidr_exclude(network, rand_net):
                   break
            else:
                break
        net, plen = network.split('/')
        plen = int(plen)
        max_plen = SUBNET_MASK[af]['max']
        reqd_plen = max_plen - (int(self.subnet_count) - 1).bit_length()
        if plen > reqd_plen:
            max_subnets = 2 ** (max_plen - plen)
            raise Exception("Network prefix %s can be subnetted "
                  "only to maximum of %s subnets" % (network, max_subnets))

        subnets = list(IPNetwork(network).subnet(plen))
        return map(lambda subnet: subnet.__str__(), subnets[:])

    def calculateSubnet(self):
        self.subnet_list = []
        if 'v4' in self.stack or 'dual' in self.stack:
            self.subnet_list.extend(self.calculateSubnetAF(af='v4'))
        if 'v6' in self.stack or 'dual' in self.stack:
            self.subnet_list.extend(self.calculateSubnetAF(af='v6'))
        self.random_subnets.extend(self.subnet_list)

    def createMultipleVN(self):

        self.vn_obj_dict = {}
        self.vn_keylist = []
        self.vn_valuelist = []
        for x in range(self.vn_count):
            try:
                vn_name = self.vn_name
                vn_name = vn_name + str(x)
                self.calculateSubnet()
                vn_obj = VNFixture(
                    project_name=self.project_name, connections=self.connections,
                    vn_name=vn_name, inputs=self.inputs, subnets=self.subnet_list, af=self.stack)
                vn_obj.setUp()
                self.vn_keylist.append(vn_name)
                self.vn_valuelist.append(vn_obj)
            except Exception as e:
                print e
                raise
        count = 0

        self.vn_obj_dict = dict(zip(self.vn_keylist, self.vn_valuelist))

    def createMultipleVM(self):

        self.vm_obj_dict = {}
        self.vm_keylist = []
        self.vm_valuelist = []

        self.vm_per_vn_dict = {}
        self.vm_per_vn_list = []
        # for each vn, creating the number of vms
        start = 0
        count = 0
        try:
            for k in self.vn_keylist:
                self.vn_obj = self.vn_obj_dict[k].obj
                for c in range(self.vm_count):
                    vm_name = '%s_%s_%s' % (k, self.vm_name, c)
                    vm_fixture = VMFixture(connections=self.connections,
                                           vn_obj=self.vn_obj, vm_name=vm_name, project_name=self.inputs.project_name,
                                           userdata=self.userdata, image_name=self.image_name, flavor=self.flavor)
                    t = threading.Thread(target=vm_fixture.setUp, args=())
                    self.vm_threads.append(t)
                    count += 1
                    self.vm_keylist.append(vm_name)
                    self.vm_valuelist.append(vm_fixture)
                self.vm_obj_dict = dict(
                    zip(self.vm_keylist, self.vm_valuelist))
                self.vm_per_vn_list.append(self.vm_obj_dict)
            self.vm_per_vn_dict = dict(
                zip(self.vn_keylist, self.vm_per_vn_list))
        except Exception as e:
            print e
        for thread in self.vm_threads:
            time.sleep(3)
            thread.start()

        for thread in self.vm_threads:
            thread.join(5)

    def verify_vns_on_setup(self):
        try:
            result = True
            verify_threads = []
            for vn_name, vn_obj in self.vn_obj_dict.items():
                t = threading.Thread(target=vn_obj.verify_on_setup, args=())
                verify_threads.append(t)
            for thread in verify_threads:
                time.sleep(0.5)
                thread.daemon = True
                thread.start()
            for thread in verify_threads:
                thread.join(10)
            for vn_name, vn_obj in self.vn_obj_dict.items():
                if not vn_obj.verify_result:
                    result = result and False
        except Exception as e:
            print e
            result = result and False
        finally:
            return result

    def verify_vms_on_setup(self):
        try:
            result = True
            verify_threads = []
            for vm_fix in self.vm_valuelist:
                t = threading.Thread(target=vm_fix.verify_on_setup, args=())
                verify_threads.append(t)
            for thread in verify_threads:
                time.sleep(0.5)
              #  thread.daemon = True
                thread.start()
            for thread in verify_threads:
                thread.join(60)
            for vm_fix in self.vm_valuelist:
                if not vm_fix.verify_vm_flag:
                    result = result and False
        except Exception as e:
            print e
            result = result and False
        finally:
            return result

    def wait_till_vms_are_up(self):
        try:
            result = True
            verify_threads = []
            for vm_fix in self.vm_valuelist:
                t = threading.Thread(target=vm_fix.wait_till_vm_is_up, args=())
                verify_threads.append(t)
            for thread in verify_threads:
                time.sleep(0.5)
              #  thread.daemon = True
                thread.start()
            for thread in verify_threads:
                thread.join(20)
            for vm_fix in self.vm_valuelist:
                if not vm_fix.verify_vm_flag:
                    result = result and False
        except Exception as e:
            print e
            result = result and False
        finally:
            return result

    def setUp(self):
        super(create_multiple_vn_and_multiple_vm_fixture, self).setUp()
        self.createMultipleVN()
        time.sleep(5)
        self.createMultipleVM()
        time.sleep(5)

    def cleanUp(self):
        super(create_multiple_vn_and_multiple_vm_fixture, self).cleanUp()
        vm_thread_to_delete = []
        vn_thread_to_delete = []
        try:
            for vm_fix in self.vm_valuelist:
                print 'deleteing vm'
                t = threading.Thread(target=vm_fix.cleanUp, args=())
                vm_thread_to_delete.append(t)
            if vm_thread_to_delete:
                for vm_thread in vm_thread_to_delete:
                    time.sleep(3)
                    vm_thread.start()
            for vm_thread in vm_thread_to_delete:
                vm_thread.join()
        except Exception as e:
            print e
        time.sleep(10)

        try:
            for vn_name, vn_obj in self.vn_obj_dict.items():
                vn_obj.cleanUp()
        except Exception as e:
            print e
        try:
            for vn_name, vn_obj in self.vn_obj_dict.items():
                assert vn_obj.verify_not_in_result
        except Exception as e:
            print e
