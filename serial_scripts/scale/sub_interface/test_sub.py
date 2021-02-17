from common.base import GenericTestBase
from tcutils.wrappers import preposttest_wrapper
import test
from heat_test import HeatStackFixture
from nova_test import *
from vm_test import *
from jinja2 import Environment, FileSystemLoader
import yaml
from port_fixture import PortFixture
from ipaddress import IPv4Network
from multiprocessing import Process
import os


class TestSubInterfaceScale(GenericTestBase):

    @classmethod
    def setUpClass(cls):
        super(TestSubInterfaceScale, cls).setUpClass()
        # Can update deployment path based on variable.
        cls.template_path = os.getenv('DEPLOYMENT_PATH',
                                      'serial_scripts/scale/sub_interface/template')
        cls.env = Environment(loader=FileSystemLoader(cls.template_path))
        cls.num = 4094
        cls.num_per_file = 50
        cls.cidr = "97.27.0.0/16"
        try:
            cls.generate_network_objects()
        except Exception as e:
            cls.logger.error(e)
            cls.vnc_check()
            cls.port_stack.cleanUp()
            cls.vsrx_stack.cleanUp()
            super(TestSubInterfaceScale, cls).tearDownClass()

    @classmethod
    def tearDownClass(cls):
        cls.port_stack.cleanUp()
        cls.vsrx_stack.cleanUp()
        super(TestSubInterfaceScale, cls).tearDownClass()

    @classmethod
    def vnc_check(cls):
        actual_vmis = cls.vnc_lib.virtual_machine_interface_read(
            id=cls.port_uuid).virtual_machine_interface_refs
        assert actual_vmis == cls.num, 'Desired number is not equal to actual number Created'

    @classmethod
    def setup_port(cls):
        cls.port_file = '{}/port.yaml'.format(cls.template_path)
        with open(cls.port_file, 'r') as fd:
            cls.port_template = yaml.load(fd, Loader=yaml.FullLoader)
        cls.port_stack = HeatStackFixture(
            connections=cls.connections,
            stack_name=cls.connections.project_name+'_port_scale',
            template=cls.port_template,
            timeout_mins=15)
        cls.port_stack.setUp()

        op = cls.port_stack.heat_client_obj.stacks.get(
            cls.port_stack.stack_name).outputs
        cls.port_uuid = op[0]['output_value']

    @classmethod
    def setup_vsrx(cls):
        cls.nova_h.get_image('vsrx')
        cls.nova_h.get_flavor('contrail_flavor_2cpu')

        vsrx_temp = cls.env.get_template("vsrx.yaml.j2")
        cls.vsrx_file = '{}/vsrx.yaml'.format(cls.template_path)
        with open(cls.vsrx_file, 'w') as f:
            f.write(vsrx_temp.render(uuid=cls.port_uuid))

        with open(cls.vsrx_file, 'r') as fd:
            cls.vsrx_template = yaml.load(fd, Loader=yaml.FullLoader)
        cls.vsrx_stack = HeatStackFixture(
            connections=cls.connections,
            stack_name=cls.connections.project_name+'_vsrx_scale',
            template=cls.vsrx_template,
            timeout_mins=15)
        cls.vsrx_stack.setUp()

        op = cls.vsrx_stack.heat_client_obj.stacks.get(
            cls.vsrx_stack.stack_name).outputs
        cls.vsrx_id = op[0]['output_value']

        vsrx = VMFixture(connections=cls.connections,
                         uuid=cls.vsrx_id, image_name='vsrx')
        vsrx.read()
        vsrx.verify_on_setup()

    @classmethod
    def call_heat_stack_with_template(cls, sub_intf_file, sub_intf_temp, start_index, end_index):
        with open(sub_intf_file, 'w') as f:
            f.write(sub_intf_temp.render(start_index=start_index, end_index=end_index,
                                         sub_intf_nets=cls.sub_intf_nets, sub_intf_masks=cls.sub_intf_masks, ips=cls.ips, uuid=cls.port_uuid))
        with open(sub_intf_file, 'r') as fd:
            sub_template = yaml.load(fd, Loader=yaml.FullLoader)
        sub_stack = HeatStackFixture(connections=cls.connections, stack_name=cls.connections.project_name +
                                     '_sub_scale{}'.format(start_index), template=sub_template, timeout_mins=120)

        sub_stack.setUp()
        return sub_stack

    @classmethod
    def setup_sub_intfs(cls):

        sub_intf_temp = cls.env.get_template("sub_bgp.yaml.j2")

        # Logic for number of files
        perfect_num = cls.num // cls.num_per_file
        partial_num = cls.num % cls.num_per_file

        def multiple_stacks(i):
            start_index = i * cls.num_per_file
            end_index = (i+1) * cls.num_per_file
            sub_intf_file = '{}/sub_bgp_stack{}.yaml'.format(
                cls.template_path, i)
            sub_intf_stack = cls.call_heat_stack_with_template(
                sub_intf_file, sub_intf_temp, start_index, end_index)

        # Doing multiprocessing here
        procs = []
        for i in range(perfect_num):
            proc = Process(target=multiple_stacks, args=(i,))
            procs.append(proc)
            proc.start()
        for proc in procs:
            proc.join()

        # For the last partial file
        if partial_num != 0:
            start_index = perfect_num * cls.num_per_file
            end_index = start_index + partial_num
            sub_intf_file = '{}/sub_bgp_stack{}.yaml'.format(
                cls.template_path, perfect_num)
            sub_intf_stack = cls.call_heat_stack_with_template(
                sub_intf_file, sub_intf_temp, start_index, end_index)

    @classmethod
    def generate_network_objects(cls):
        cidr = IPv4Network(cls.cidr)
        cls.ips = []
        cls.neighbor1_list = []
        cls.neighbor2_list = []
        cls.sub_intf_nets = []
        cls.sub_intf_masks = []
        cls.sub_mask = 28
        cls.local_as = 64500
        for n, sn in enumerate(cidr.subnets(new_prefix=cls.sub_mask)):
            if n == cls.num:
                break
            sub_intf_cidr = IPv4Network(sn)
            sub_intf_net = str(sub_intf_cidr.network_address)
            sub_intf_mask = sub_intf_cidr.prefixlen
            cls.sub_intf_nets.append(sub_intf_net)
            cls.sub_intf_masks.append(sub_intf_mask)
            for i, ip in enumerate(sub_intf_cidr):
                if i == 0:
                    continue
                elif i == 1:
                    cls.neighbor1_list.append(ip)
                elif i == 2:
                    cls.neighbor2_list.append(ip)
                elif i == 3:
                    cls.ips.append(ip)
                else:
                    break

    @test.attr(type=['sub_intf_scale'])
    @preposttest_wrapper
    def test_sub_interface_scale(self):
        '''
        Description: Test to scale 4094 sub-interfaces and validate it
         Test steps:
                1. Create port
                2. Create sub-interfaces for that port
                3. Attach port to vsrx and validate it
                4. Also validate number of sub-interfaces created through vnc api
         Pass criteria: 4094 sub-interfaces should be present
         Maintainer : nuthanc@juniper.net 
        '''
        self.setup_port()
        self.setup_sub_intfs()
        self.setup_vsrx()
        self.vnc_check()
