import time
import re
import fixtures
from fabric.api import local
from fabric.context_managers import shell_env, settings, hide
from fabric.contrib.files import exists
from fabric.operations import get, put

from common.connections import ContrailConnections
from vpc_fixture_new import VPCFixture
from ec2_base import EC2Base
from floating_ip import FloatingIPFixture
from tcutils.util import *


class VPCFIPFixture(fixtures.Fixture):

    '''Fixture to create, verify and delete FIP
       Flow: Euca2ools -> Boto -> Nova
    '''

    def __init__(self, public_vn_obj, ec2_base=None, connections=None):
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = self.inputs.logger

        self.ec2_base = ec2_base
        self.already_present = False
        self.fip_vn_fixture = public_vn_obj.public_vn_fixture
        self.pool_name = public_vn_obj.fip_fixture.pool_name
        self.public_vn_obj = public_vn_obj
        self.vn_obj = self.fip_vn_fixture.obj
    # end __init__

    def setUp(self):
        super(VPCFIPFixture, self).setUp()
        self.c_fip_fixture = self.public_vn_obj.fip_fixture
    # end setUp

    def allocate_floating_ip(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-allocate-address -d vpc', True).split('\t')
        if out:
            floating_ip = out[1]
            fip_allocation_id = out[2]
            self.logger.info('Allocated a Floating IP %s from Floating Ip pool fpool. ID : %s'
                             % (floating_ip, fip_allocation_id))
            return (floating_ip, fip_allocation_id)
        else:
            return (None, None)
    # end allocate_floating_ip

    def associate_floating_ip(self, fip_allocation_id, instance_id):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-associate-address -a %s %s' % (fip_allocation_id,
                                                 instance_id), True).split('\t')
        if out:
            fip_allocation_id = out[1]
            self.logger.info(
                'Associated Floating IP (Assoc ID : %s) to Instance %s' % (fip_allocation_id,
                                                                           instance_id))
            return True
        else:
            return False
    # end associate_floating_ip

    def create_and_assoc_fip(self, instance_id):
        (fip, fip_alloc_id) = self.allocate_floating_ip()
        if not self.associate_floating_ip(fip_alloc_id, instance_id):
            self.logger.error('Error while applying FIP to instance %s' %
                              (instance_id))
            return (None, None)
        return (fip, fip_alloc_id)
    # end create_and_assoc_fip

    def disassociate_floating_ip(self, fip_allocation_id, fip):
        out = self.ec2_base._shell_with_ec2_env('euca-disassociate-address %s' % (
            fip_allocation_id), True)
        if out == 'True':
            fip_allocation_id.replace('eipassoc', 'eipalloc')
            self.logger.info('Floating IP %s disassociated ' % (fip))
            return True
        else:
            return False
    # end disassociate_floating_ip

    def release_floating_ip(self, fip_allocation_id, fip):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-release-address %s' % fip_allocation_id, True)
        if out:
            self.logger.info('Floating IP (Alloc ID %s) %s released' %
                             (fip, fip_allocation_id))
            return True
        else:
            return False
    # end release_floating_ip

    def disassoc_and_delete_fip(self, fip_allocation_id, fip):
        if not self.disassociate_floating_ip(fip_allocation_id, fip):
            self.logger.error('Disassociation of FIP %s failed' % fip)
        if not self.release_floating_ip(fip_allocation_id, fip):
            self.logger.error('Unable to deallocate FIP %s ' % (fip))
    # end disassoc_and_delete_fip

    def verify_fip(self, floating_ip):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-describe-addresses --filter domain=vpc| grep %s' % (floating_ip), True).split('\n')
        self.logger.debug(out)
        foundIp = False

        for ip in out:
            ip = filter(None, ip.split(' '))
            if len(ip) == 0:
                continue
            if ip[0] == floating_ip:
                fip_allocation_id = ip[2]
                foundIp = True

                # looger info for allocation or association verification
                if ip[2].split('-')[0] == 'eipalloc':
                    self.logger.info('Floating IP %s verified. No instance associated'
                                     % floating_ip)
                elif ip[2].split('-')[0] == 'eipassoc':
                    self.logger.info(
                        'Floating IP %s associated with instance %s verified' %
                        (floating_ip, ip[3]))
                else:
                    self.logger.warn(
                        'Floating IP allocation or association id problem')
                break

        if not foundIp:
            self.logger.warn(
                'Floating IP allocation or association id verification failed')
        return foundIp
    # end verify_fip

    def verify_on_setup(self):
        if not self.c_fip_fixture.verify_on_setup():
            self.logger.error('Contrail Fixture verification of FIP Pool %s failed'
                              % (self.pool_name))
            return False
        return True
    # end verify_on_setup

    @retry(delay=5, tries=3)
    def verify_on_cleanup(self):
        return True
    # end verify_on_cleanup

    def cleanUp(self):
        if self.already_present:
            self.logger.debug(
                'VM was not created by this fixture..Skipping deletion')
            super(VPCFIPFixture, self).cleanUp()
        else:
            super(VPCFIPFixture, self).cleanUp()
            assert self.verify_on_cleanup(), "Euca Verification failed for FIP Pool %s cleanup" \
                % (self.pool_name)
    # end cleanUp

# end VPCFIPFixture
