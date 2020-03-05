from common.vrouter.base import BaseVrouterTest
import unittest
from tcutils.wrappers import preposttest_wrapper
import os
import sys
from tcutils.tcpdump_utils import *
from tcutils.util import get_random_string
import math
from random import randint

PKG_DIR = 'common/vrouter/ip_fragment'
VM_DIR = '/tmp'

class IPFragments(BaseVrouterTest):

    @classmethod
    def setUpClass(cls):
        super(IPFragments, cls).setUpClass()
        cls.create_test_resources()

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_test_resources()
        super(IPFragments, cls).tearDownClass()

    @classmethod
    def create_test_resources(cls):
        cls.vn1_fixture = cls.create_only_vn()
        cls.vn1_fixture.verify_on_setup()

        cls.vm1_fixture = cls.create_only_vm(vn_fixture=cls.vn1_fixture,
            image_name='ubuntu-traffic')
        cls.vm2_fixture = cls.create_only_vm(vn_fixture=cls.vn1_fixture,
            image_name='ubuntu-traffic')

        assert cls.vm1_fixture.verify_on_setup()
        assert cls.vm2_fixture.verify_on_setup()
        assert cls.vm1_fixture.wait_till_vm_is_up()
        assert cls.vm2_fixture.wait_till_vm_is_up()

    @classmethod
    def cleanup_test_resources(cls):
        cls.vm1_fixture.cleanUp()
        cls.vm2_fixture.cleanUp()
        cls.vn1_fixture.cleanUp()

    @preposttest_wrapper
    def test_ip_fragment_in_order(self):
        '''
            Test IP fragments sent in order
        '''
        vn1_fixture = self.vn1_fixture
        vm1_fixture = self.vm1_fixture
        vm2_fixture = self.vm2_fixture

        proto = 'udp'
        vn_fq_name = vm2_fixture.vn_fq_name
        order = '0123'
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        #Start tcpdump on recvr VM
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -p %s -o %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, proto, order, log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=4, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_in_order

    @preposttest_wrapper
    def test_ip_fragment_out_of_order_inter_node(self):
        '''
            Test IP fragments sent out of order and inter node
        '''
        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,\
                                    this test needs atleast 2 compute nodes")

        vn1_fixture = self.vn1_fixture

        image = 'ubuntu-traffic'
        vm1_fixture = self.create_vms(vn_fixture=vn1_fixture, count=1,
            node_name=compute_hosts[0], image_name=image)[0]
        vm2_fixture = self.create_vms(vn_fixture=vn1_fixture, count=1,
            node_name=compute_hosts[1], image_name=image)[0]
        self.verify_vms([vm1_fixture, vm2_fixture])

        proto = 'udp'
        vn_fq_name = vm2_fixture.vn_fq_name
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        #Start tcpdump on recvr VM
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -p %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, proto, log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=4, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_out_of_order_inter_node

    @preposttest_wrapper
    def test_ip_fragment_out_of_order_intra_node(self):
        '''
            Test IP fragments sent out of order and intra node
        '''
        compute_hosts = self.orch.get_hosts()

        vn1_fixture = self.vn1_fixture
        image = 'ubuntu-traffic'
        vm_fixtures = self.create_vms(vn_fixture=vn1_fixture, count=2,
            node_name=compute_hosts[0], image_name=image)
        self.verify_vms(vm_fixtures)
        vm1_fixture = vm_fixtures[0]
        vm2_fixture = vm_fixtures[1]

        proto = 'udp'
        vn_fq_name = vm2_fixture.vn_fq_name
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        #Start tcpdump on recvr VM
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -p %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, proto, log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=4, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_out_of_order_intra_node

    @preposttest_wrapper
    def test_ip_fragment_out_of_order1(self):
        '''
            Test IP fragments sent in below orders:
                1. f1,f2,f0
                2. f1,f0,f2
                3. f0,f2,f1
                4. f2,f1,f0
                5. f2,f0,f1
        '''
        vn1_fixture = self.vn1_fixture
        vm1_fixture = self.vm1_fixture
        vm2_fixture = self.vm2_fixture

        proto = 'udp'
        vn_fq_name = vm2_fixture.vn_fq_name
        data = "Z"*30
        fragsize = 16
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        order_list = ['120', '102', '021', '210', '201']
        frags_count = int(math.ceil((8 + len(data))/float(fragsize)))#8 is udp header size
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)

        for order in order_list:
            #Start tcpdump on recvr VM
            session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
                vn_fq_name, filters = filters)
            #Start traffic
            pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
            log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
            cmd1 = 'chmod +x %s;%s %s %s -p %s -o %s -d %s -f %s 2>%s 1>%s' % (
                        pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                        vm1_fixture.vm_ip, proto, order, data, fragsize,
                        log_file, log_file)
            output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1],
                as_sudo=True)
            self.logger.info(output_cmd_dict)

            #Verify packet count and stop tcpdump
            assert verify_tcpdump_count(self, session, pcap,
                exp_count=frags_count,
                grep_string=vm1_fixture.vm_ip), ("Could not get expected no. of"
                " fragments for order %s" % (order))
    #end test_ip_fragment_out_of_order1

    @preposttest_wrapper
    def test_ip_fragment_out_of_order_icmp(self):
        '''
            Test IP fragments sent out of order for icmp
        '''
        vn1_fixture = self.vn1_fixture
        vm1_fixture = self.vm1_fixture
        vm2_fixture = self.vm2_fixture

        proto = 'icmp'
        vn_fq_name = vm2_fixture.vn_fq_name
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        #Start tcpdump on recvr VM
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -p %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, proto, log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=4, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_out_of_order_icmp

    @preposttest_wrapper
    def test_ip_fragment_out_of_order_tcp(self):
        '''
            Test IP fragments sent out of order for tcp
        '''
        vn1_fixture = self.vn1_fixture
        vm1_fixture = self.vm1_fixture
        vm2_fixture = self.vm2_fixture

        proto = 'tcp'
        vn_fq_name = vm2_fixture.vn_fq_name
        fragsize = 20
        order = 10
        data = "Z"*20
        frags_count = int(math.ceil((20 + len(data))/float(fragsize)))#20 is tcp header size
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        #Start tcpdump on recvr VM
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -p %s -f %s -o %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, proto, fragsize, order,
                    log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=frags_count, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_out_of_order_tcp

    @preposttest_wrapper
    def test_ip_fragment_out_of_order_syn(self):
        '''
            Test IP fragments sent out of order for tcp syn
        '''
        vn1_fixture = self.vn1_fixture
        vm1_fixture = self.vm1_fixture
        vm2_fixture = self.vm2_fixture

        proto = 'tcp'
        vn_fq_name = vm2_fixture.vn_fq_name
        fragsize = 20
        order = 10
        data = "Z"*20
        frags_count = int(math.ceil((20 + len(data))/float(fragsize)))#20 is tcp header size
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        #Start tcpdump on recvr VM
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -p %s -f %s -o %s -t 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, proto, fragsize, order,
                    log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=frags_count, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_out_of_order_syn

    @preposttest_wrapper
    def test_ip_fragment_out_of_order_big_payload(self):
        '''
            Test IP fragments sent out of order with large packets
        '''
        vn1_fixture = self.vn1_fixture
        vm1_fixture = self.vm1_fixture
        vm2_fixture = self.vm2_fixture

        proto = 'udp'
        vn_fq_name = vm2_fixture.vn_fq_name
        size = 60000
        fragsize = 1300
        frags_count = int(math.ceil((8 + size)/float(fragsize)))#8 is udp header size
        order = 1023
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        #Start tcpdump on recvr VM
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -p %s -o %s -f %s -s %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, proto, order, fragsize, size,
                    log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=frags_count, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_out_of_order_big_payload

    @preposttest_wrapper
    def test_ip_fragment_multi_sender(self):
        '''
         Test IP fragments with multiple sender
        '''
        vn1_fixture = self.vn1_fixture
        vm1_fixture = self.vm1_fixture
        vm2_fixture = self.vm2_fixture

        image = 'ubuntu-traffic'
        vm_fixtures = self.create_vms(vn_fixture=vn1_fixture, count=1,
            image_name=image)
        self.verify_vms(vm_fixtures)
        vm3_fixture = vm_fixtures[0]

        proto = 'icmp'
        vn_fq_name = vm3_fixture.vn_fq_name
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)
        self.logger.info("copying %s to VM %s" % (pkg, vm2_fixture.vm_name))
        vm2_fixture.copy_file_to_vm(path, VM_DIR)

        #start tcpdump on recvr VM
        filters = '\'(%s and (src %s or %s) and dst %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip, vm3_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm3_fixture,
            vn_fq_name, filters=filters)

        #Start traffic from VM1
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd = 'chmod +x %s;%s %s %s -p %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm3_fixture.vm_ip,
                    vm1_fixture.vm_ip, proto, log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Start traffic from VM2
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd = 'chmod +x %s;%s %s %s -p %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm3_fixture.vm_ip,
                    vm2_fixture.vm_ip, proto, log_file, log_file)
        output_cmd_dict = vm2_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=8, grep_string=vm3_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_multi_sender

    @preposttest_wrapper
    def test_ip_fragment_overlapping(self):
        '''
            Test overlapping fragments
        '''
        vn1_fixture = self.vn1_fixture
        vm1_fixture = self.vm1_fixture
        vm2_fixture = self.vm2_fixture

        proto = 'icmp'
        vn_fq_name = vm2_fixture.vn_fq_name
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        #Start tcpdump on recvr VM
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -l 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=3, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_overlapping

    @preposttest_wrapper
    def test_ip_fragment_duplicate_frags(self):
        '''
            Test with duplicate IP fragments
        '''
        vn1_fixture = self.vn1_fixture
        vm1_fixture = self.vm1_fixture
        vm2_fixture = self.vm2_fixture

        proto = 'tcp'
        vn_fq_name = vm2_fixture.vn_fq_name
        fragsize = 20
        order = 10
        data = "Z"*20
        duplicate_count = 10
        frags_count = int(math.ceil((20 + len(data))/float(fragsize)))#20 is tcp header size
        pkg = 'sender.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        #Start tcpdump on recvr VM
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -p %s -f %s -o %s -c %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, proto, fragsize, order, duplicate_count,
                    log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=frags_count, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"

        #Send duplicate fragment head followed by rest of the fragments
        #Receiver VM should receive all the fragments including all the duplicate heads
        order = '01'
        #Start tcpdump on recvr VM
        filters = '\'(%s and src host %s and dst host %s)\'' % (proto,
            vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session, pcap = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -p %s -f %s -o %s -c %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, proto, fragsize, order, duplicate_count,
                    log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session, pcap,
            exp_count=frags_count+duplicate_count, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_duplicate_frags

    @preposttest_wrapper
    def test_ip_fragment_mixed(self):
        '''
            Test with mixed fragments with different IP id
        '''
        vn1_fixture = self.vn1_fixture
        vm1_fixture = self.vm1_fixture
        vm2_fixture = self.vm2_fixture

        proto = 'icmp'
        ip_id = randint(0, 65535)
        vn_fq_name = vm2_fixture.vn_fq_name
        pkg = 'mixed.py'
        path = os.getcwd() + '/' + PKG_DIR + '/' + pkg
        self.logger.info("copying %s to VM %s" % (pkg, vm1_fixture.vm_name))
        vm1_fixture.copy_file_to_vm(path, VM_DIR)

        #Start tcpdump on recvr VM
        filters = '-v \'(ip[4:2]==%s and %s and src host %s and dst host %s)\'' % (
            ip_id, proto, vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session1, pcap1 = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)
        filters = '-v \'(ip[4:2]==%s and %s and src host %s and dst host %s)\'' % (
            ip_id+1, proto, vm1_fixture.vm_ip, vm2_fixture.vm_ip)
        session2, pcap2 = start_tcpdump_for_vm_intf(self, vm2_fixture,
            vn_fq_name, filters = filters)

        #Start traffic
        pkg_absolute_path = '%s/%s' % (VM_DIR, pkg)
        log_file = pkg_absolute_path + '-' + get_random_string() + '.log'
        cmd1 = 'chmod +x %s;%s %s %s -i %s 2>%s 1>%s' % (
                    pkg_absolute_path, pkg_absolute_path, vm2_fixture.vm_ip,
                    vm1_fixture.vm_ip, ip_id, log_file, log_file)
        output_cmd_dict = vm1_fixture.run_cmd_on_vm(cmds=[cmd1], as_sudo=True)
        self.logger.info(output_cmd_dict)

        #Verify packet count and stop tcpdump
        assert verify_tcpdump_count(self, session1, pcap1,
            exp_count=4, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
        assert verify_tcpdump_count(self, session2, pcap2,
            exp_count=4, grep_string=vm1_fixture.vm_ip
            ), "Could not get expected no. of fragments"
    #end test_ip_fragment_mixed
