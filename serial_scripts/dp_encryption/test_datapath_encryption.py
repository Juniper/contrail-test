from tcutils.wrappers import preposttest_wrapper
from common.dp_encryption.base import BaseDataPathEncryption

class TestDataPathEncryption(BaseDataPathEncryption):
    @classmethod
    def setUpClass(cls):
        super(TestDataPathEncryption, cls).setUpClass()
        cls.disable_encryption()
        try:
            cls.create_objects()
        except:
            cls.tearDownClass()
            raise

    @classmethod
    def create_objects(cls):
        ''' Create class specific objects
            1) Create VN
            2) Create VMs on all computes
        '''
        cls.vms = dict()
        cls.vn = cls.create_only_vn()
        for compute in cls.inputs.compute_names:
            cls.vms[compute] = cls.create_only_vm(vn_fixture=cls.vn, node_name=compute)
        assert cls.check_vms_active(cls.vms.itervalues(), do_assert=False)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'vms', None):
            for obj in cls.vms.itervalues():
                obj.cleanUp()
        if getattr(cls, 'vn', None):
            cls.vn.cleanUp()
        super(TestDataPathEncryption, cls).tearDownClass()

    @preposttest_wrapper
    def test_encryption_enable_disable(self):
        '''
           Toggle encryption enabled nodes and check the tunnel status
           and make sure there is no traffic disruption
        '''
        traffic_objs = dict()
        self.enable_encryption()
        self.validate_tunnels(endpoints=self.inputs.compute_names)

        # Wait till VMs are booted up
        self.check_vms_booted(self.vms.itervalues())

        src_vm = self.vms[self.inputs.compute_names[0]]
        for compute, vm in self.vms.iteritems():
            if vm.uuid == src_vm.uuid:
                continue
            traffic_objs[compute] = self.start_traffic(src_vm, vm, 'tcp', '8000', '9000')
            self.verify_encrypt_traffic(src_vm, vm)
        for compute, traffic_obj in traffic_objs.iteritems():
            self.poll_traffic(traffic_obj)

        self.disable_encryption()
        self.validate_tunnels()
        for compute, vm in self.vms.iteritems():
            if vm.uuid == src_vm.uuid:
                continue
            self.verify_encrypt_traffic(src_vm, vm, encrypt=False)
        for compute, traffic_obj in traffic_objs.iteritems():
            self.stop_traffic(traffic_obj)

        if len(self.inputs.compute_names) < 3:
            self.logger.info('Cluster has less than 3 computes so skipping the rest of the testcase')
            return
        computes = self.inputs.compute_names[:3]
        self.add_vrouter_to_encryption(computes)
        self.validate_tunnels(vrouters=computes, endpoints=computes)
        self.validate_tunnels(vrouters=self.inputs.compute_names[3:])
        for compute, vm in self.vms.iteritems():
            if vm.uuid == src_vm.uuid:
                continue
            traffic_objs[compute] = self.start_traffic(src_vm, vm, 'tcp', '8000', '9000')
            encrypt = True if compute in computes else False
            self.verify_encrypt_traffic(src_vm, vm, encrypt=encrypt)
        for compute, traffic_obj in traffic_objs.iteritems():
            self.poll_traffic(traffic_obj)

        self.delete_vrouter_from_encryption(computes[1:2])
        computes.pop(1)
        self.validate_tunnels(vrouters=computes, endpoints=computes)
        self.validate_tunnels(vrouters=list(set(self.inputs.compute_names)
                                          - set(computes)))
        for compute, vm in self.vms.iteritems():
            if vm.uuid == src_vm.uuid:
                continue
            encrypt = True if compute in computes else False
            self.verify_encrypt_traffic(src_vm, vm, encrypt=encrypt)
        for compute, traffic_obj in traffic_objs.iteritems():
            self.poll_traffic(traffic_obj)

        self.add_vrouter_to_encryption(list(set(self.inputs.compute_names) - set(computes)))
        self.validate_tunnels(endpoints=self.inputs.compute_names)
        for compute, vm in self.vms.iteritems():
            if vm.uuid == src_vm.uuid:
                continue
            self.verify_encrypt_traffic(src_vm, vm, encrypt=True)
        for compute, traffic_obj in traffic_objs.iteritems():
            self.stop_traffic(traffic_obj)

    @preposttest_wrapper
    def test_diff_pkt_sizes(self):
        '''
           icmp pkt sizes: 1350, 1400, 2000, 8850, 8900, 9500
           scp transfer file
        '''
        payloads = [1350, 1400, 2000, 8850, 8900, 9500]
        self.enable_encryption()
        self.validate_tunnels(endpoints=self.inputs.compute_names)

        # Wait till VMs are booted up
        self.check_vms_booted(self.vms.itervalues())

        src_vm = self.vms[self.inputs.compute_names[0]]
        dst_vm = self.vms[self.inputs.compute_names[1]]
        for payload in payloads:
            self.verify_encrypt_traffic(src_vm, dst_vm, size=payload)
        for payload in payloads:
            assert vm1_fixture.check_file_transfer(vm2_fixture, size=payload)


    @preposttest_wrapper
    def test_change_encap_mode(self):
        src_vm = self.vms[self.inputs.compute_names[0]]
        dst_vm = self.vms[self.inputs.compute_names[1]]
        curr_encap = self.get_encap_priority()
        self.addCleanup(self.set_encap_priority, curr_encap)

        # Set encap mode as MPLSoUDP
        self.set_encap_priority(['MPLSoUDP'])
        self.enable_encryption()
        self.validate_tunnels(endpoints=self.inputs.compute_names)

        # Wait till VMs are booted up
        self.check_vms_booted(self.vms.itervalues())
        self.verify_encrypt_traffic(src_vm, dst_vm)

        # Set encap mode as MPLSoGRE
        self.set_encap_priority(['MPLSoGRE'])
        self.validate_tunnels(endpoints=self.inputs.compute_names)
        self.verify_encrypt_traffic(src_vm, dst_vm)

        # Set encap mode as VXLAN
        self.set_encap_priority(['VXLAN'])
        self.validate_tunnels(endpoints=self.inputs.compute_names)
        self.verify_encrypt_traffic(src_vm, dst_vm)

    @preposttest_wrapper
    def test_link_local_service(self):
        src_vm = self.vms[self.inputs.compute_names[0]]
        fabric_ip = self.vms[self.inputs.compute_names[1]].vm_node_data_ip
        self.enable_encryption()
        self.validate_tunnels(endpoints=self.inputs.compute_names)
        self.add_linklocal_service(ipfabric_ip=fabric_ip, ipfabric_port='8085')
        # Wait till VMs are booted up
        self.check_vms_booted(self.vms.itervalues())
        self.validate_linklocal_service(src_vm)

class TestDataPathEncryption2(BaseDataPathEncryption):
    @classmethod
    def setUpClass(cls):
        super(TestDataPathEncryption, cls).setUpClass()
        cls.disable_encryption()

    def is_test_applicable(self):
        if len(self.inputs.compute_ips) < 3:
            return (False, 'Need atleast 3 compute nodes')
        return (True, None)

    @preposttest_wrapper
    def test_interface_mirroring(self):
        image_name = 'ubuntu'
        src_node = dst_node = self.inputs.compute_names[0]
        if len(self.inputs.compute_name) > 3:
            dst_node = self.inputs.compute_names[-1]
        mirror_node1 = self.inputs.compute_names[1]
        mirror_node2 = self.inputs.compute_names[2]
        encrypt_nodes = self.inputs.compute_names[:2]
        non_encrypt_nodes = self.inputs.compute_names[2:]
        if src_node != dst_node:
            encrypt_nodes.append(dst_node)
            non_encrypt_nodes.remove(dst_node)
        vn = self.create_vn()
        mirror_vn = self.create_vn()
        src_vm = self.create_vm(vn_fixture=vn, node_name=src_node,
                                image_name=image_name)
        dst_vm = self.create_vm(vn_fixture=vn, node_name=dst_node,
                                image_name=image_name)
        mirror1_vm = self.create_vm(vn_fixture=mirror_vn,
            node_name=mirror_node1, image_name=image_name)
        mirror2_vm = self.create_vm(vn_fixture=mirror_vn,
            node_name=mirror_node2, image_name=image_name)

        self.enable_encryption(encrypt_nodes)
        self.validate_tunnels(encrypt_nodes, encrypt_nodes)
        self.validate_tunnels(vrouters=non_encrypt_nodes)

        self.setup_policy_between_vns(vn, mirror_vn)
        # Wait till VMs are booted up
        self.check_vms_booted([src_vm, dst_vm, mirror1_vm, mirror2_vm])
