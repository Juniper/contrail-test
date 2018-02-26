import time
import re
import fixtures
from fabric.api import local
from fabric.context_managers import shell_env, settings

from common.connections import ContrailConnections
from vpc_fixture_new import VPCFixture
from ec2_base import EC2Base
from vn_test import VNFixture
from tcutils.util import *


class VPCVNFixture(fixtures.Fixture):

    '''Fixture to create, verify and delete Subnet
       Flow: Euca2ools -> Boto -> Nova
    '''

    def __init__(self, vpc_fixture, subnet_cidr=None, connections=None):
        self.connections = vpc_fixture.get_project_connections()
        #self.connections = connections
        self.inputs = connections.inputs
        self.logger = self.inputs.logger
        self.vpc_id = vpc_fixture.vpc_id
        self.subnet_id = None
        self.vpc_fixture = vpc_fixture

        self.subnet_cidr = subnet_cidr
        self.ec2_base = vpc_fixture.ec2_base
        self.already_present = False
        self.def_acl_id = 'acl-default'

    # end __init__

    def setUp(self):
        super(VPCVNFixture, self).setUp()
        self.create_subnet()
        # Build up data structure for std VN verification to happen
        # Note that this VNFixture does not create a VN if it is already
        # present
        if self.subnet_id:
            self.contrail_vn_fixture = self.useFixture(
                VNFixture(project_name=self.vpc_id,
                          connections=self.connections, inputs=self.inputs,
                          vn_name=self.subnet_id, subnets=[self.subnet_cidr]))
            self.vn_id = self.contrail_vn_fixture.vn_id
    # end setUp

    def verify_on_setup(self):
        if not self.subnet_id:
            self.logger.error(
                'Subnet ID not found...verification failed for %s' %
                self.subnet_cidr)
            return False
        if not self.verify_subnet():
            self.logger.error('Verification failed for Subnet id %s ' %
                              self.subnet_id)
            return False
        else:
            self.logger.info('EC2 Verification for Subnet id %s passed' %
                             self.subnet_id)
        if not self.contrail_vn_fixture.verify_on_setup():
            self.logger.error(
                'Contrail VN verification failed for Subnet %s ' %
                self.subnet_id)
            return False
        return True
    # end verify_on_setup

    def verify_on_cleanup(self):
        if self.verify_subnet_deleted():
            self.logger.info('Subnet %s is removed as per euca cmds' %
                             (self.subnet_id))
            return True
        self.logger.error('Subnet %s still persists as per euca cmds' %
                          (self.subnet_id))
        return False
    # end verify_on_cleanup

    @retry(delay=5, tries=3)
    def verify_subnet(self):
        verify_subnet_output = self.ec2_base._shell_with_ec2_env(
            'euca-describe-subnets', True).split('\n')[2:]
        self.logger.debug(verify_subnet_output)
        foundSubnet = False

        for subnet in verify_subnet_output:
            if subnet.startswith(self.subnet_id):
                subnet_list = subnet.replace('\r', '').split('\t')
                if subnet_list[1] == self.vpc_id and subnet_list[2] == self.subnet_cidr:
                    foundSubnet = True
                    self.logger.info('Subnet %s verified' % self.subnet_id)
                    break

        if not foundSubnet:
            self.logger.warn('Subnet %s not found in euca-describe-subnets' %
                             self.subnet_id)
            return foundSubnet
        return foundSubnet

    # end verify_subnet

    @retry(delay=5, tries=3)
    def verify_subnet_deleted(self):
        verify_subnet_output = self.ec2_base._shell_with_ec2_env(
            'euca-describe-subnets', True).split('\n')[2:]
        foundSubnet = False

        if not self.subnet_id:
            self.logger.warn(
                'Subnet does not seem to be present, nothing to verify in cleanup')
            return True
        for subnet in verify_subnet_output:
            if subnet.startswith(self.subnet_id):
                foundSubnet = True
                break

        if foundSubnet:
            self.logger.warn('Subnet %s still found in euca-describe-subnets' %
                             self.subnet_id)
            return False
        else:
            self.logger.debug(
                'Verified that subnet %s is deleted in euca-describe-subnets' % self.subnet_id)
        return True
    # end verify_subnet_deleted

    def cleanUp(self):
        if self.already_present:
            self.logger.debug(
                'Subnet was not created by this fixture..Skipping deletion')
        else:
            self.delete_subnet()
            self.verify_on_cleanup()
        super(VPCVNFixture, self).cleanUp()
    # end cleanUp

    def delete_vpc(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-delete-vpc %s' % (self.vpc_id), True)
        if len(out) > 0 and out.split(' ')[1] == self.vpc_id:
            self.logger.info('VPC %s deleted' % self.vpc_id)
            return True
        else:
            return False
    # end delete_vpc

    def create_subnet(self):
        create_subnet_output = self.ec2_base._shell_with_ec2_env(
            'euca-create-subnet -c %s %s' %
            (self.subnet_cidr, self.vpc_id), True)
        if create_subnet_output:
            self.subnet_id = create_subnet_output.split(' ')[0].split(':')[1]
            self.logger.info('Create subnet with CIDR %s' % self.subnet_cidr)
            return True
        else:
            return False
    # end create_subnet

    def delete_subnet(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-delete-subnet %s' % (self.subnet_id), True)
        if len(out) > 0 and out.split(' ')[1] == self.subnet_id:
            self.logger.info('Subnet %s deleted' % self.subnet_id)
            return True
        else:
            return False
    # end delete_subnet

    def _get_acl_association_id(self):
        subnet_id = self.subnet_id
        out = self.ec2_base._shell_with_ec2_env(
            'euca-describe-network-acls', True).split('\n')
        assoc_id = None

        for entry in out:
            idx = out.index(entry)
            entry.replace(' ', '')
            if not entry.startswith('acl-'):
                continue

            vpc_id = out[idx + 1].replace(' ', '')

            for entry in out:
                assoc_str = re.sub(' +', ' ', entry).replace(' ', '', 1)
                assoc = assoc_str.split(' ')
                if not assoc[0].startswith('aclassoc-'):
                    continue
                if assoc[1] == subnet_id:
                    assoc_id = assoc[0]

        return assoc_id
    # end _get_acl_association_id

    def associate_acl(self, acl_id=None):
        subnet_id = self.subnet_id
        acl_assoc_id = self._get_acl_association_id()
        # if acl = default then associate subnet to default ACL for VPC
        # else associate subnet with ACL created using euca2ools
        if not acl_assoc_id:
            self.logger.error('Cannot get ACL association id')
        if not acl_id:
            aclId = self.def_acl_id

        out = self.ec2_base._shell_with_ec2_env(
            'euca-replace-network-acl-association %s -a %s' % (acl_id, acl_assoc_id), True)
        self.logger.debug(out)
        self.contrail_vn_fixture.update_vn_object()
        if out:
            self.logger.info('Associate ACL %s to subnet %s' %
                             (acl_id, subnet_id))
            if acl_id == 'default':
                self.acl_association = False
            else:
                self.acl_association = True
            return True

        return False
    # end associate_acl

    def verify_acl_binding(self, acl_id):
        subnet_id = self.subnet_id
        acl_assoc_id = self._get_acl_association_id()
        out = self.ec2_base._shell_with_ec2_env(
            'euca-describe-network-acls %s' % acl_id, True).split('\n')
        self.logger.debug(out)
        foundAcl = False

        if len(out) <= 0:
            return foundAcl

        got_acl_id = out[2].replace(' ', '')
        vpc_id = out[3].replace(' ', '').replace('\r', '')
        if acl_id in got_acl_id and vpc_id == self.vpc_id:
            self.logger.info('ACL %s verified' % acl_id)

            # check if acl associated or not
            if not self.acl_association:
                self.logger.info('ACL %s not associated with any subnet' %
                                 acl_id)
                foundAcl = True

            # check if acl associated with subnet or not
            else:
                for entry in out:
                    assoc_str = re.sub(' +', ' ', entry).replace(' ', '', 1)
                    assoc = assoc_str.split(' ')
                    if not assoc[0].startswith('aclassoc-'):
                        continue
                    if assoc[0] == acl_assoc_id and assoc[1] == self.subnet_id:
                        self.logger.info(
                            'ACL %s associated with subnet %s verified' %
                            (acl_id, self.subnet_id))
                        if self.acl_association:
                            foundAcl = True
                            break
            return foundAcl

        else:
            return False
    # end verify_acl_binding


# end VPCVNFixture
