#Testcases for disabling policy on VMIs:
#PR https://bugs.launchpad.net/juniperopenstack/+bug/1558920 and PR https://bugs.launchpad.net/juniperopenstack/+bug/1566650
from vn_test import *
from vm_test import *
from tcutils.wrappers import preposttest_wrapper
from common.vrouter.base import BaseVrouterTest
import test

class DisablePolicyEcmp(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(DisablePolicyEcmp, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(DisablePolicyEcmp, cls).tearDownClass()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ecmp_with_static_routes(self):
        """
        Description: Verify disabling policy for ECMP routes with static routes on VM
        Steps:
            1. launch 1 VN and launch 3 VMs in it.
            2. create a static route for a new subnet prefix and add this on 2 VMIs.
               this will create 2 ECMP routes.
            3. Disable the policy on all VMIs.
            4. Now from 3rd VM send traffic to an IP from static route prefix
            5. add new ECMP destinations and verify load is distributed to new destinations too
            6. remove ECMP destinations and verify load is distributed to remaining destinations
        Pass criteria:
            1. traffic should go through fine
            2. flows should not be created
            3. load should be distributed among ecmp routes.
        """

        vn_fixtures = self.create_vn(count=1)
        self.verify_vn(vn_fixtures)
        vn1_fixture = vn_fixtures[0]
        prefix = get_random_cidr()
        assert prefix, "Unable to get a random CIDR"

        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,\
                                    this test needs atleast 2 compute nodes")
            
        #Launch sender on first node and ECMP dest VMs on another node
        vm1_fixture = self.create_vm(vn_fixture= vn1_fixture,count=1,
                                        node_name=compute_hosts[0])
        vm_fixtures = self.create_vm(vn_fixture= vn1_fixture,count=2,
                                        node_name=compute_hosts[1])
        #Launch 1 extra VM, to be used for new ECMP routes later
        vm4_fixture = self.create_vm(vn_fixture= vn1_fixture, count=1,
                                node_name=compute_hosts[0])[0]

        self.verify_vm(vm_fixtures)
        self.verify_vm(vm1_fixture)
        vm1_fixture = vm1_fixture[0]
        vm2_fixture = vm_fixtures[0]
        vm3_fixture = vm_fixtures[1]

        #Add static routes, which will create ECMP routes
        static_ip = self.add_static_routes_on_vm(prefix,
                                [vm2_fixture, vm3_fixture])
        #Disable the policy on all the VMIs
        self.disable_policy_for_vm([vm1_fixture])
        self.disable_policy_for_vm(vm_fixtures)

        assert self.verify_traffic_load_balance(vm1_fixture,
                            [vm2_fixture,vm3_fixture], static_ip)

        self.verify_vm([vm4_fixture])
        self.disable_policy_for_vm([vm4_fixture])

        #Add new ECMP destination and verify load is distributed to new destinations
        static_ip = self.add_static_routes_on_vm(prefix,
                            [vm4_fixture],
                            ip=static_ip)
        self.delete_vm([vm2_fixture])
        assert self.verify_traffic_load_balance(vm1_fixture,
                        [vm3_fixture, vm4_fixture],
                        static_ip)

        return True

    @preposttest_wrapper
    def test_ecmp_with_static_routes_intra_node(self):
        """
        Description: Verify disabling policy for ECMP routes with static routes on VM
        Steps:
            1. launch 1 VN and launch 3 VMs on the same node
            2. create a static route for a new subnet prefix and add this on 2 VMIs.
               this will create 2 ECMP routes.
            3. Disable the policy on all VMIs.
            4. Now from 3rd VM send traffic to an IP from static route prefix
        Pass criteria:
            1. traffic should go through fine
            2. flows should not be created
            3. load should be distributed among ecmp routes.
        """

        vn_fixtures = self.create_vn(count=1)
        self.verify_vn(vn_fixtures)
        vn1_fixture = vn_fixtures[0]

        prefix = get_random_cidr()
        assert prefix, "Unable to get a random CIDR"

        compute_hosts = self.orch.get_hosts()
        #launch all VMs on same node, to test intra node traffic
        vm_fixtures = self.create_vm(vn_fixture= vn1_fixture,count=3, node_name=compute_hosts[0])
        self.verify_vm(vm_fixtures)
        vm1_fixture = vm_fixtures[0]
        vm2_fixture = vm_fixtures[1]
        vm3_fixture = vm_fixtures[2]

        static_ip = self.add_static_routes_on_vm(prefix, [vm2_fixture,vm3_fixture])
        self.disable_policy_for_vm(vm_fixtures)
        assert self.verify_traffic_load_balance(vm1_fixture, [vm2_fixture,vm3_fixture], static_ip)

        return True

