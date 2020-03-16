from common.dp_encryption.base import BaseDataPathEncryption
from builtins import range
from tcutils.wrappers import preposttest_wrapper
from common.firewall.base import BaseFirewallTest
from tcutils.util import get_an_ip
from port_fixture import PortFixture
from vn_test import VNFixture
from tcutils.tcpdump_utils import start_tcpdump_for_vm_intf,\
                                  stop_tcpdump_for_vm_intf

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
        assert cls.check_vms_active(iter(cls.vms.values()), do_assert=False)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'vms', None):
            for obj in cls.vms.values():
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
        self.check_vms_booted(iter(self.vms.values()))

        src_vm = self.vms[self.inputs.compute_names[0]]
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            traffic_objs[compute] = self.start_traffic(src_vm, vm, 'tcp', '8000', '9000')
            self.verify_encrypt_traffic(src_vm, vm)
        for compute, traffic_obj in traffic_objs.items():
            self.poll_traffic(traffic_obj)

        self.disable_encryption()
        self.validate_tunnels()
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            self.verify_encrypt_traffic(src_vm, vm, encrypt=False)
        for compute, traffic_obj in traffic_objs.items():
            self.stop_traffic(traffic_obj)

        if len(self.inputs.compute_names) < 3:
            self.logger.info('Cluster has less than 3 computes so skipping the rest of the testcase')
            return
        computes = self.inputs.compute_names[:3]
        self.add_vrouter_to_encryption(computes)
        self.validate_tunnels(vrouters=computes, endpoints=computes)
        self.validate_tunnels(vrouters=self.inputs.compute_names[3:])
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            traffic_objs[compute] = self.start_traffic(src_vm, vm, 'tcp', '8000', '9000')
            encrypt = True if compute in computes else False
            self.verify_encrypt_traffic(src_vm, vm, encrypt=encrypt)
        for compute, traffic_obj in traffic_objs.items():
            self.poll_traffic(traffic_obj)

        self.delete_vrouter_from_encryption(computes[1:2])
        computes.pop(1)
        self.validate_tunnels(vrouters=computes, endpoints=computes)
        self.validate_tunnels(vrouters=list(set(self.inputs.compute_names)
                                          - set(computes)))
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            encrypt = True if compute in computes else False
            self.verify_encrypt_traffic(src_vm, vm, encrypt=encrypt)
        for compute, traffic_obj in traffic_objs.items():
            self.poll_traffic(traffic_obj)

        self.add_vrouter_to_encryption(list(set(self.inputs.compute_names) - set(computes)))
        self.validate_tunnels(endpoints=self.inputs.compute_names)
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            self.verify_encrypt_traffic(src_vm, vm, encrypt=True)
        for compute, traffic_obj in traffic_objs.items():
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
        self.check_vms_booted(iter(self.vms.values()))

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

        self.enable_encryption()
        self.check_vms_booted(iter(self.vms.values()))

        # Set encap mode as MPLSoUDP
        self.set_encap_priority(['MPLSoUDP'])
        self.validate_tunnels(endpoints=self.inputs.compute_names)
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
        self.check_vms_booted(iter(self.vms.values()))
        self.validate_linklocal_service(src_vm)

class TestDataPathEncryption2(BaseDataPathEncryption, BaseFirewallTest):
    @classmethod
    def setUpClass(cls):
        super(TestDataPathEncryption2, cls).setUpClass()
        cls.disable_encryption()
        cls.vnc_h = cls.connections.orch.vnc_h

    def setup_firewall_policy(self, vn, source, destination):
        hr_app_tag = self.tags['global']['application']['hr']
        self.set_tag(vn, hr_app_tag)
        self.set_tag(source, self.tags['global']['tier']['web'])
        self.set_tag(destination, self.tags['global']['tier']['db'])
        hr_web_ep = {'tags': ['global:tier=web']}
        hr_db_ep = {'tags': ['global:tier=db']}
        self.fwr = self.create_fw_rule(scope='global', protocol='icmp',
            source=hr_web_ep, destination=hr_db_ep, match='None')
        rules = [{'uuid': self.fwr.uuid, 'seq_no': 20}]
        self.fwp = self.create_fw_policy(scope='global', rules=rules)
        policies = [{'uuid': self.fwp.uuid, 'seq_no': 30}]
        self.aps_hr = self.create_aps('global', policies=policies,
                                      application=hr_app_tag)

    @preposttest_wrapper
    def test_fwp_on_workload(self):
        image_name = 'cirros'
        src_node = self.inputs.compute_names[0]
        dst_node = self.inputs.compute_names[1]
        encrypt_nodes = self.inputs.compute_names[:2]
        vn = self.create_vn()
        src_vm = self.create_vm(vn_fixture=vn, node_name=src_node,
                                image_name=image_name)
        dst_vm = self.create_vm(vn_fixture=vn, node_name=dst_node,
                                image_name=image_name)
        self.enable_encryption(encrypt_nodes)
        self.validate_tunnels(encrypt_nodes, encrypt_nodes)
        self.setup_firewall_policy(vn, src_vm, dst_vm)
        self.check_vms_booted([src_vm, dst_vm])
        self.verify_encrypt_traffic(src_vm, dst_vm)
        self.fwr.update(action='deny')
        before_src, before_dst = self.get_crypt_stats(src_node, dst_node)
        self.verify_traffic(src_vm, dst_vm, 'icmp', expectation=False)
        after_src, after_dst = self.get_crypt_stats(src_node, dst_node)
        assert before_dst == after_dst, 'Pkts are not dropped at src vrouter'
        self.disable_encryption()
        self.validate_tunnels()
        self.verify_encrypt_traffic(src_vm, dst_vm, encrypt=False, expectation=False)
        self.fwr.update(action='pass', match='None')
        self.verify_encrypt_traffic(src_vm, dst_vm, encrypt=False, expectation=True)

    @preposttest_wrapper
    def test_fwp_on_vhost0(self):
        src_node = self.inputs.compute_names[0]
        dst_node = self.inputs.compute_names[1]
        encrypt_nodes = self.inputs.compute_names[:2]
        self.enable_encryption(encrypt_nodes)
        self.validate_tunnels(encrypt_nodes, encrypt_nodes)
        src_vhost0_fqname = ['default-global-system-config',
                             src_node, 'vhost0']
        src_vhost0_uuid = self.vnc_h.virtual_machine_interface_read(
                          fq_name=src_vhost0_fqname).uuid
        src_vhost0 = PortFixture(connections=self.connections,
                                 uuid=src_vhost0_uuid)
        src_vhost0.setUp()
        src_vhost0.enable_policy()
        self.addCleanup(src_vhost0.disable_policy)
        dst_vhost0_fqname = ['default-global-system-config',
                             dst_node, 'vhost0']
        dst_vhost0_uuid = self.vnc_h.virtual_machine_interface_read(
                          fq_name=dst_vhost0_fqname).uuid
        dst_vhost0 = PortFixture(connections=self.connections,
                                 uuid=dst_vhost0_uuid)
        dst_vhost0.setUp()
        dst_vhost0.enable_policy()
        self.addCleanup(dst_vhost0.disable_policy)
        vn_fqname = ["default-domain", "default-project", "ip-fabric"]
        fab_vn_uuid = self.vnc_h.virtual_network_read(fq_name=vn_fqname).uuid
        fab_vn = VNFixture(connections=self.connections, uuid=fab_vn_uuid)
        fab_vn.setUp()
        self.setup_firewall_policy(fab_vn, src_vhost0, dst_vhost0)
        self.fwr.update(protocol='tcp', dports=(7777, 7777))
        self.verify_encrypt_traffic_bw_hosts(src_node, dst_node, '7777')
        self.fwr.update(action='deny', match='None')
        self.verify_encrypt_traffic_bw_hosts(src_node, dst_node, '7777',
                                             expectation=False)

class TestDataPathEncryption3(BaseDataPathEncryption):
    @classmethod
    def setUpClass(cls):
        super(TestDataPathEncryption3, cls).setUpClass()
        cls.disable_encryption()
        cls.vnc_h = cls.connections.orch.vnc_h

    def is_test_applicable(self):
        if len(self.inputs.compute_names) < 3:
            return (False, 'Need atleast 3 compute nodes')
        return super(TestDataPathEncryption3, self).is_test_applicable()

    @preposttest_wrapper
    def test_ecmp_active_active_aap(self):
        image_name = 'ubuntu'
        src_node = self.inputs.compute_names[0]
        dst_node1 = self.inputs.compute_names[1]
        dst_node2 = self.inputs.compute_names[2]
        encrypt_nodes = self.inputs.compute_names[:2]
        non_encrypt_nodes = self.inputs.compute_names[2:]

        vn = self.create_vn()
        src_vm = self.create_vm(vn_fixture=vn, node_name=src_node,
                                image_name=image_name)
        dst_vm1 = self.create_vm(vn_fixture=vn, node_name=dst_node1,
                                image_name=image_name)
        dst_vm2 = self.create_vm(vn_fixture=vn, node_name=dst_node2,
                                image_name=image_name)
        self.enable_encryption(encrypt_nodes)
        self.validate_tunnels(encrypt_nodes, encrypt_nodes)
        self.validate_tunnels(vrouters=non_encrypt_nodes)

        self.check_vms_booted([src_vm, dst_vm1, dst_vm2])

        vIP = get_an_ip(vn.get_cidrs()[0], offset=10)
        for vm in [dst_vm1, dst_vm2]:
            port = vm.get_vmi_obj_from_api_server()[1][0]
            self.config_aap(port.uuid, vIP, mac=port.mac_addr,
                aap_mode='active-active', contrail_api=True)
            cmd = 'ip addr add %s/24 dev eth0'%vIP
            vm.run_cmd_on_vm([cmd], as_sudo=True)
            vm.start_webserver()

        b_src_dst1, b_dst1_src = self.get_crypt_stats(src_node, dst_node1)
        b_src_dst2, b_dst2_src = self.get_crypt_stats(src_node, dst_node2)
        exp_output = set([dst_vm1.vm_name, dst_vm2.vm_name])
        for retry in range(1, 15):
            cmd = "curl %s:8000"%vIP
            result = src_vm.run_cmd_on_vm(cmds=[cmd])[cmd].strip()
            assert result in [dst_vm1.vm_name, dst_vm2.vm_name]
            exp_output.discard(result)
            if not exp_output:
                break
        assert not exp_output, 'active-active aap doesnt seem to work'
        a_src_dst1, a_dst1_src = self.get_crypt_stats(src_node, dst_node1)
        a_src_dst2, a_dst2_src = self.get_crypt_stats(src_node, dst_node2)
        assert (b_src_dst1 != a_src_dst1) and (b_dst1_src != a_dst1_src)
        assert (b_src_dst2 == a_src_dst2) and (b_dst2_src == a_dst2_src)

    @preposttest_wrapper
    def test_interface_mirroring(self):
        image_name = 'ubuntu'
        src_node = dst_node = self.inputs.compute_names[0]
        if len(self.inputs.compute_names) > 3:
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

        # Wait till VMs are booted up
        self.check_vms_booted([src_vm, dst_vm, mirror1_vm, mirror2_vm])

        self.setup_policy_between_vns(vn, mirror_vn)
        vIP = get_an_ip(mirror_vn.get_cidrs()[0], offset=10)
        for vm in [mirror1_vm, mirror2_vm]:
            port = vm.get_vmi_obj_from_api_server()[1][0]
            self.config_aap(port.uuid, vIP, mac=port.mac_addr,
                aap_mode='active-active', contrail_api=True)
            cmd = 'ip addr add %s/24 dev eth0'%vIP
            vm.run_cmd_on_vm([cmd], as_sudo=True)

        src_vmi = src_vm.get_vmi_obj_from_api_server()[1][0].uuid
        self.vnc_h.enable_intf_mirroring(src_vmi, vIP)
        self.addCleanup(self.vnc_h.disable_intf_mirroring, src_vmi)
        b_src_dst1, b_dst1_src = self.get_crypt_stats(src_node, mirror_node1)
        b_src_dst2, b_dst2_src = self.get_crypt_stats(src_node, mirror_node2)
        exp_vms = set([mirror1_vm, mirror2_vm])
        for retry in range(1, 15):
            pcap_ids = list()
            for mirror_vm in exp_vms:
                pcap_id = start_tcpdump_for_vm_intf(None, [mirror_vm],
                          None, filters='udp port 8099', pcap_on_vm=True)
                pcap_ids.append(pcap_id)
            result = src_vm.ping_to_ip(dst_vm.vm_ip, size=1200)
            filters = '| grep \"length [1-9][2-9][0-9][0-9][0-9]*\"'
            for pcap_id in pcap_ids:
                ignore, count = stop_tcpdump_for_vm_intf(None, None, None,
                    vm_fix_pcap_pid_files=pcap_id, filters=filters,
                    verify_on_all=True)
                if count and count[0]:
                    exp_vms.discard(pcap_id[0][0])
            if not exp_vms:
                break
        assert not exp_vms, '%s'%exp_vms
        a_src_dst1, a_dst1_src = self.get_crypt_stats(src_node, mirror_node1)
        a_src_dst2, a_dst2_src = self.get_crypt_stats(src_node, mirror_node2)
        assert (b_src_dst2 == a_src_dst2) and (b_dst2_src == a_dst2_src)
        assert (b_src_dst1 != a_src_dst1) and (b_dst1_src != a_dst1_src)

class TestDataPathEncryptionRestart(BaseDataPathEncryption):
    @classmethod
    def setUpClass(cls):
        super(TestDataPathEncryptionRestart, cls).setUpClass()
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
        for compute in cls.inputs.compute_names[:3]:
            cls.vms[compute] = cls.create_only_vm(vn_fixture=cls.vn, node_name=compute)
        assert cls.check_vms_booted(iter(cls.vms.values()), do_assert=False)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'vms', None):
            for obj in cls.vms.values():
                obj.cleanUp()
        if getattr(cls, 'vn', None):
            cls.vn.cleanUp()
        super(TestDataPathEncryptionRestart, cls).tearDownClass()

    def setup_testcase(self):
        self.enable_encryption()
        self.validate_tunnels(endpoints=self.inputs.compute_names)
        src_vm = self.vms[self.inputs.compute_names[0]]
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            self.verify_encrypt_traffic(src_vm, vm)

    @preposttest_wrapper
    def test_restart_vrouter_agent(self):
        self.setup_testcase()
        src_vm = self.vms[self.inputs.compute_names[0]]
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            self.inputs.restart_container([compute], 'agent')
            self.verify_encrypt_traffic(src_vm, vm)

        if self.inputs.deployer != 'contrail-ansible-deployer':
            return
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            self.inputs.relaunch_container([compute], 'vrouter')
            self.verify_encrypt_traffic(src_vm, vm)

    @preposttest_wrapper
    def test_restart_strongswan(self):
        self.setup_testcase()
        src_vm = self.vms[self.inputs.compute_names[0]]
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            self.inputs.restart_container([compute], 'strongswan')
            self.verify_encrypt_traffic(src_vm, vm)

        if self.inputs.deployer != 'contrail-ansible-deployer':
            return
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            self.inputs.relaunch_container([compute], 'strongswan')
            self.verify_encrypt_traffic(src_vm, vm)

    @preposttest_wrapper
    def test_restart_config_service(self):
        self.setup_testcase()
        src_vm = self.vms[self.inputs.compute_names[0]]
        self.inputs.restart_container([self.inputs.cfgm_ip], 'api-server')
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            self.verify_encrypt_traffic(src_vm, vm)

        if self.inputs.deployer != 'contrail-ansible-deployer':
            return
        self.inputs.relaunch_container([self.inputs.cfgm_ip], 'config')
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            self.verify_encrypt_traffic(src_vm, vm)

    @preposttest_wrapper
    def test_interface_up_down(self):
        self.setup_testcase()
        src_vm = self.vms[self.inputs.compute_names[0]]
        crypt_up_cmd = 'ifconfig crypt0 up'
        decrypt_up_cmd = 'ifconfig decrypt0 up'
        crypt_down_cmd = 'ifconfig crypt0 down'
        decrypt_down_cmd = 'ifconfig decrypt0 down'
        for compute, vm in self.vms.items():
            if vm.uuid == src_vm.uuid:
                continue
            self.addCleanup(self.inputs.run_cmd_on_server,
                compute, crypt_up_cmd, pty=True, as_sudo=True)
            self.addCleanup(self.inputs.run_cmd_on_server,
                compute, decrypt_up_cmd, pty=True, as_sudo=True)
            self.inputs.run_cmd_on_server(compute, crypt_down_cmd,
                                          pty=True, as_sudo=True)
            self.verify_traffic(src_vm, vm, 'icmp', expectation=False)
            self.inputs.run_cmd_on_server(compute, crypt_up_cmd,
                                          pty=True, as_sudo=True)
            self.verify_encrypt_traffic(src_vm, vm)
            self.inputs.run_cmd_on_server(compute, decrypt_down_cmd,
                                          pty=True, as_sudo=True)
            self.verify_traffic(src_vm, vm, 'icmp', expectation=False)
            self.inputs.run_cmd_on_server(compute, decrypt_up_cmd,
                                          pty=True, as_sudo=True)
            self.verify_encrypt_traffic(src_vm, vm)
