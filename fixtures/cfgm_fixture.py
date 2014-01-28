
import fixtures
import time 
import uuid

from vnc_api import vnc_api
from cfgm_common import exceptions as ve
from contrail_fixtures import *

class CfgmFixture(fixtures.Fixture):
    def __init__(self, connections, inputs, vn_count, vms_per_vn):
        self._vn_count = vn_count
        self._vms_per_vn = vms_per_vn
        self._vns = []
        self._vms = []
        self._vmi = []
        self.vnc_lib = connections.vnc_lib_fixture.obj
        self.quantum_fixture= connections.quantum_fixture.obj
        self.logger = inputs.logger
        self.inputs = inputs

    def setUp(self):
        super(CfgmFixture, self).setUp()
        for idx in range(self._vn_count):
            vn_obj = vnc_api.VirtualNetwork('vn-%s' % idx)
            vn_obj.add_network_ipam(vnc_api.NetworkIpam(),
                vnc_api.VnSubnetsType([vnc_api.IpamSubnetType(
                    subnet = vnc_api.SubnetType('10.3.0.0', 16))]))
            try:
                vn_id = self.vnc_lib.virtual_network_create(vn_obj)
            except ve.RefsExistError as e:
                self.logger.info(str(e))
            self._vns.append(vn_obj)
            self.logger.info ("Created VN %s" % vn_obj.get_fq_name_str())
            for jdx in range(self._vms_per_vn):
                #import pdb; pdb.set_trace()
                vm_name = 'vmx-%d-%d' % (idx,jdx)
                vm_obj = vnc_api.VirtualMachine(vm_name)
                try:
                    vm_id = self.vnc_lib.virtual_machine_create(vm_obj)
                except ve.RefsExistError as e:
                    self.logger.info(str(e))
                self._vms.append(vm_obj)

                port_name = vm_obj.get_fq_name_str()
                id_perms = vnc_api.IdPermsType(enable=True)
                port_obj = vnc_api.VirtualMachineInterface(port_name, vm_obj,
                                                   id_perms=id_perms)
                port_obj.set_virtual_network(vn_obj)
                self._vmi.append(port_obj)
                try:
                    port_id = self.vnc_lib.virtual_machine_interface_create(port_obj)
                except ve.RefsExistError as e:
                    self.logger.info(str(e))
                #import pdb; pdb.set_trace()
            self.logger.info ("VM count %d , VMI count %d" % (len(self._vms), len(self._vmi)))


    def cleanUp(self):
        super(CfgmFixture, self).cleanUp()
        for idx in self._vmi:
            try:
                self.vnc_lib.virtual_machine_interface_delete(idx.get_fq_name())
            except:
                self.logger.info("Cannot Delete %s" % idx.get_fq_name_str())
        for idx in self._vms:
            try:
                self.vnc_lib.virtual_machine_delete(idx.get_fq_name())
            except:
                self.logger.info("Cannot Delete %s" % idx.get_fq_name_str())
        for idx in self._vns:
            try:
                self.vnc_lib.virtual_network_delete(idx.get_fq_name())
            except:
                self.logger.info("Cannot Delete %s" % idx.get_fq_name_str())


