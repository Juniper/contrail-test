import test_v1
from common import isolated_creds
from common import create_public_vn
from vn_test import *
from vm_test import *
import fixtures


class FloatingIpBaseTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(FloatingIpBaseTest, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.orch = cls.connections.orch
        if cls.inputs.admin_username:
            public_creds = cls.admin_isolated_creds
        else:
            public_creds = cls.isolated_creds
        cls.public_vn_obj = create_public_vn.PublicVn(
            connections=cls.connections,
            isolated_creds_obj=public_creds,
            logger=cls.logger)
        cls.public_vn_obj.configure_control_nodes()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(FloatingIpBaseTest, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(FloatingIpBaseTest, self).setUp()
        '''self.inputs = inputs
        self.connections = connections
        self.setup_common_objects()'''

    def cleanUp(self):
        super(FloatingIpBaseTest, self).cleanUp()

    def scp_files_to_vm(self, src_vm, dst_vm):
        result = True
        src_vm.put_pub_key_to_vm()
        dst_vm.put_pub_key_to_vm()
        dest_vm_ip = dst_vm.vm_ip
        file_sizes = ['1000', '1101', '1202']
        for size in file_sizes:
            self.logger.debug("-" * 80)
            self.logger.debug("FILE SIZE = %sB" % size)
            self.logger.debug("-" * 80)

            self.logger.debug('Transferring the file from %s to %s using scp' %
                             (src_vm.vm_name, dst_vm.vm_name))
            filename = 'testfile'

            # Create file
            cmd = 'dd bs=%s count=1 if=/dev/zero of=%s' % (size, filename)
            src_vm.run_cmd_on_vm(cmds=[cmd])

            # Copy key
            dst_vm.run_cmd_on_vm(
                cmds=['cp -f ~root/.ssh/authorized_keys ~/.ssh/'],
                as_sudo=True)
            # Scp file from EVPN_VN_L2_VM1 to EVPN_VN_L2_VM2 using
            # EVPN_VN_L2_VM2 vm's eth1 interface ip
            src_vm.scp_file_to_vm(filename, vm_ip=dst_vm.vm_ip)
            src_vm.run_cmd_on_vm(cmds=['sync'])
            # Verify if file size is same in destination vm
            out_dict = dst_vm.run_cmd_on_vm(
                cmds=['ls -l %s' % (filename)])
            if size in out_dict.values()[0]:
                self.logger.info('File of size %s is trasferred successfully to \
                    %s by scp ' % (size, dest_vm_ip))
            else:
                self.logger.warn('File of size %s is not trasferred fine to %s \
                    by scp !! Pls check logs' % (size, dest_vm_ip))
                result = result and False
        return result

    def get_two_different_compute_hosts(self):
        host_list = self.connections.orch.get_hosts()
        self.compute_1 = host_list[0]
        self.compute_2 = host_list[0]
        if len(host_list) > 1:
            self.compute_1 = host_list[0]
            self.compute_2 = host_list[1]
        

class CreateAssociateFip(fixtures.Fixture):

    """Create and associate a floating IP to the Virtual Machine."""

    def __init__(self, inputs, fip_fixture, vn_id, vm_id):
        self.inputs = inputs
        self.logger = self.inputs.logger
        self.fip_fixture = fip_fixture
        self.vn_id = vn_id
        self.vm_id = vm_id

    def setUp(self):
        self.logger.info("Create associate FIP")
        super(CreateAssociateFip, self).setUp()
        self.fip_id = self.fip_fixture.create_and_assoc_fip(
            self.vn_id, self.vm_id)

    def cleanUp(self):
        self.logger.info("Disassociationg FIP")
        super(CreateAssociateFip, self).cleanUp()
        self.fip_fixture.disassoc_and_delete_fip(self.fip_id)
