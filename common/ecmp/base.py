import os
from tcutils.util import get_random_name, get_random_cidr
from common.base import GenericTestBase

class ECMPTestBase(GenericTestBase):

    @classmethod
    def setUpClass(cls):
        super(ECMPTestBase, cls).setUpClass()
        cls.inputs.set_af(cls.get_af())

        # Mgmt VN
        cls.mgmt_vn_name = get_random_name('mgmt_%s' % (
                                            cls.inputs.project_name))
        cls.mgmt_vn_subnets = [get_random_cidr(af=cls.inputs.get_af())]
        cls.mgmt_vn_fixture = cls.create_only_vn(
                cls.mgmt_vn_name, cls.mgmt_vn_subnets)

        # Left VN
        cls.left_vn_name = get_random_name('left_%s' % (
                                          cls.inputs.project_name))
        cls.left_vn_subnets = [get_random_cidr(af=cls.inputs.get_af())]
        cls.left_vn_fixture = cls.create_only_vn(cls.left_vn_name,
                                                 cls.left_vn_subnets)

        # Right VN
        cls.right_vn_name = get_random_name('right_%s' % (
                                             cls.inputs.project_name))
        cls.right_vn_subnets = [get_random_cidr(af=cls.inputs.get_af())]
        cls.right_vn_fixture = cls.create_only_vn(cls.right_vn_name,
                                                  cls.right_vn_subnets)
        #if cls.inputs.get_af() == 'v6':
        #    cls.left_vn_subnets += [get_random_cidr()]
        #    cls.right_vn_subnets += [get_random_cidr()]

        ci = os.environ.has_key('ci_image')
        if ci and cls.inputs.get_af() == 'v4':
            cls.image_name = 'cirros-0.3.0-x86_64-uec'
        else:
            cls.image_name = 'ubuntu-traffic'

        # End Vms
        cls.left_vm_name = get_random_name('left_vm_%s' % (
                                            cls.inputs.project_name))
        cls.left_vm_fixture = cls.create_only_vm(cls.left_vn_fixture,
                                                 vm_name=cls.left_vm_name,
                                                 image_name=cls.image_name)
        cls.right_vm_name = get_random_name('right_vm_%s' % (
                                             cls.inputs.project_name))
        cls.right_vm_fixture = cls.create_only_vm(cls.right_vn_fixture,
                                                  vm_name=cls.right_vm_name,
                                                  image_name=cls.image_name)
        cls.check_vms_booted([cls.left_vm_fixture, cls.right_vm_fixture])

        cls.common_args = { 'mgmt_vn_name' : cls.mgmt_vn_name,
                            'mgmt_vn_subnets' : cls.mgmt_vn_subnets,
                            'mgmt_vn_fixture' : cls.mgmt_vn_fixture,
                            'left_vn_name' : cls.left_vn_name,
                            'left_vn_subnets' : cls.left_vn_subnets,
                            'left_vn_fixture' : cls.left_vn_fixture,
                            'left_vm_name' : cls.left_vm_name,
                            'left_vm_fixture' : cls.left_vm_fixture,
                            'right_vn_name' : cls.right_vn_name,
                            'right_vn_subnets' : cls.right_vn_subnets,
                            'right_vn_fixture' : cls.right_vn_fixture,
                            'right_vm_name' : cls.right_vm_name,
                            'right_vm_fixture' : cls.right_vm_fixture,
                            'image_name' : cls.image_name }
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.safe_cleanup('right_vm_fixture')
        cls.safe_cleanup('left_vm_fixture')
        cls.safe_cleanup('left_vn_fixture')
        cls.safe_cleanup('right_vn_fixture')
        cls.safe_cleanup('mgmt_vn_fixture')
        super(ECMPTestBase, cls).tearDownClass()
    # end tearDownClass

