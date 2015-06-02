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
from vm_test import VMFixture
from tcutils.util import *


class VPCVMFixture(fixtures.Fixture):

    '''Fixture to create, verify and delete VM
       Flow: Euca2ools -> Boto -> Nova
       Instance_type is either 'nat' or 'regular'
       If Instance type is nat, also pass public vn fixture object
    '''

    def __init__(self, vpc_vn_fixture,
                 image_name='ubuntu', connections=None, key='key1', sg_ids=[],
                 instance_type='regular',
                 public_vn_fixture=None):
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = self.inputs.logger
        self.vpc_fixture = vpc_vn_fixture.vpc_fixture
        self.vpc_id = self.vpc_fixture.vpc_id
        self.vpc_vn_fixture = vpc_vn_fixture
        self.vpc_id = self.vpc_fixture.vpc_id
        self.project_id = self.vpc_id
        self.image_name = image_name
        self.instance_type = instance_type
        self.vn_obj = vpc_vn_fixture.contrail_vn_fixture.obj
        self.vm_name = None
        self.image_id = None
        self.subnet_id = vpc_vn_fixture.subnet_id

        self.ec2_base = self.vpc_fixture.ec2_base
        self.already_present = False
        self.nova_h = self.connections.nova_h
        self.key = self.inputs.stack_user+key
        self.sg_ids = sg_ids
        self.cfgm_ip = self.inputs.cfgm_ip
        self.instance_id = None
        self.public_vn_fixture = public_vn_fixture
        if public_vn_fixture:
            self.vn_obj = public_vn_fixture.obj

    # end __init__

    def setUp(self):
        super(VPCVMFixture, self).setUp()
        try:
            f = '/tmp/key%s'%self.inputs.stack_user
            lock = Lock(f)
            lock.acquire()
            self._create_keypair(self.key)
        finally:
            lock.release()
        self.create_vm()
        # Build up data structure for std VM verification to happen
        # Note that this Fixture does not create a VM if it is already present
        if self.vm_name:
            self.c_vm_fixture = self.useFixture(VMFixture(
                project_name=self.vpc_id,
                connections=self.connections,
                image_name=self.image_name,
                vn_obj=self.vn_obj,
                vm_name=self.vm_name,
                sg_ids=self.sg_ids))
    # end setUp

    def create_vm(self):
        zone, node_name = self.nova_h.lb_node_zone()
        self.image_name = self.nova_h.get_image_name_for_zone(
                                        image_name=self.image_name,
                                        zone=zone)
        self.nova_h.get_image(self.image_name)
        self.image_id = self._get_image_id()
        cmd_str = 'euca-run-instances %s -s %s -k %s -z %s' % \
            (self.image_id, self.subnet_id, self.key, zone)
        if self.instance_type == 'nat':
            cmd_str = 'euca-run-instances %s' % (self.image_id)
        if self.sg_ids:
            cmd_str += ' -g %s' % (self.sg_ids[0])
        self.logger.debug(cmd_str)
        run_instance_output = self.ec2_base._shell_with_ec2_env(
            cmd_str, True).split('\n')
        self.logger.debug(run_instance_output)
        self.logger.debug('Image name is .%s.' % (self.image_name))
        # TODO WA for Bug 2010
        if self.image_name == 'nat-service':
            time.sleep(10)
            run_instance_output = self.ec2_base._shell_with_ec2_env(
                'euca-describe-instances | grep %s' % (self.image_id),
                True).split('\n')
        self._gather_instance_details(run_instance_output)

        if not self.instance_id:
            self.logger.error(
                'VM Instance ID not found upon doing euca-run-instances')
            return False
        self.logger.info('Instance %s(ID %s) is started with %s image'
                         % (self.instance_name, self.instance_id, self.image_id))
        self.logger.info('VPC VM ID of Instance %s is %s' %
                         (self.instance_name, self.vm_id))
    # end create_vm

    def verify_on_setup(self):
        if not self.verify_instance():
            self.logger.error('Verification of VM %s from euca cmds failed' % (
                self.instance_name))
            return False
        if not self.c_vm_fixture.verify_on_setup():
            self.logger.error('Contrail Fixture verification of VM %s(ID: %s)\
                    failed' % (self.instance_name, self.vm_id))
            return False
        self.logger.info('Euca cmd verification and Contrail fixture \
              verification passed' + ' for VM %s(ID: %s)' %
                         (self.instance_name, self.vm_id))
        return True
    # end verify_on_setup
    
    def wait_till_vm_is_up(self):
        return self.c_vm_fixture.wait_till_vm_is_up()

    @retry(delay=10, tries=30)
    def verify_instance(self):
        self.logger.debug('Waiting for VM %s to be in running state' %
                          (self.instance_id))
        time.sleep(5)
        instances = self.ec2_base._shell_with_ec2_env(
            'euca-describe-instances | grep %s' % (self.instance_id), True).split('\n')
        self.logger.debug(instances)

        foundInstance = False
        for instance in instances:
            instance = [k for k in instance.split('\t')]
            if instance[1] == self.instance_id and instance[5] == 'running':
                foundInstance = True
                self.logger.info('Instance %s verified' % self.instance_id)
                break
            # end if
        return foundInstance
    # end verify_instance

    @retry(delay=5, tries=3)
    def verify_vm_deleted(self):
        instances = self.ec2_base._shell_with_ec2_env(
            'euca-describe-instances | grep %s' % (self.instance_id), True).split('\n')
        result = True
        for instance in instances:
            instance = [k for k in instance.split('\t')]
            try:
                if instance[1] == self.instance_id:
                    result = False
                    self.logger.debug(
                        'Instance %s is still found in Euca cmds' %
                        (self.instance_id))
                    break
                # end if
            except IndexError:
                self.logger.debug(
                    'No instances in euca-describe-instances output')
        self.logger.info('Instance %s is not seen in Euca cmds' %
                         (self.instance_id))
        return result
    # end verify_vm_deleted

    def _get_image_id(self):
        images = self.ec2_base._shell_with_ec2_env(
            'euca-describe-images', True).split('\n')

        for image in images:
            image = [k for k in image.split('\t')]
            if '(%s)' % (self.image_name) in image[2] and image[4] == 'available':
                self.image_id = image[1]
                self.logger.info('Using image %s(%s) to launch VM' %
                                 (self.image_id, image[2]))
                break
        return self.image_id
    # end _get_image_id

    def stop_instance(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-stop-instances %s' % (self.instance_id), True)
        self.logger.debug(out)
        time.sleep(5)
        if 'UnknownError' in out:
            self.logger.error(
                'Some unknown error has happened..pls check system logs')
            return False
        return True
    # end stop_instance

    def start_instance(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-start-instances %s' % (self.instance_id), True)
        self.logger.debug(out)
        time.sleep(2)
        if 'UnknownError' in out:
            self.logger.error(
                'Some unknown error has happened..pls check system logs')
            return False
        return True
    # end start_instance

    def _gather_instance_details(self, instance_output):
        my_instance = None
        for line in instance_output:
            if 'INSTANCE' in line:
                my_instance = line
        if not my_instance:
            self.logger.error('No Instance detail was found!')
            return False
       # instance = [k for k in my_instance.split('\t')]
        # change made for UBUNTU set up as multiple tabs were not getting
        # handled.
        instance = [k for k in re.split("\s+", my_instance)]

        if instance[1].startswith('i-'):
            self.instance_id = instance[1]
            self.instance_name = instance[3]
            self.vm_id = instance[3].replace('server-', '')
            if 'nat' in self.instance_name:
#                self.vm_name = instance[3].replace('server-','')
                self.vm_name = '%s-nat_1' % (self.vpc_id)
            elif 'server-' + self.vm_id != self.instance_name:
                self.logger.error('Unexpected instance name : %s' %
                                  (self.instance_name))
            # self.vm_name would have VM name as required by Nova
            else:
                self.vm_name = 'Server ' + self.vm_id
        else:
            self.logger.error(
                'Unable to gather Instance details of the launched VM')
        return True
    # end _gather_instance_details

    @retry(delay=5, tries=3)
    def verify_on_cleanup(self):
        if not self.verify_vm_deleted():
            self.logger.error('VM %s still present ' % (self.vm_name))
            return False
        else:
            self.logger.info('VM %s is cleaned up as seen by euca cmds ' %
                             (self.instance_id))
        return True
    # end verify_on_cleanup

    def cleanUp(self):
        if self.already_present:
            self.logger.debug(
                'VM was not created by this fixture..Skipping deletion')
            super(VPCVMFixture, self).cleanUp()
        else:
            self.terminate_instance()
            super(VPCVMFixture, self).cleanUp()
            assert self.verify_on_cleanup(), "Euca Verification failed for VM %s cleanup" % (
                self.instance_id)
    # end cleanUp

    def terminate_instance(self):
        self.logger.debug('Terminating instance %s' % (self.instance_id))
        out = self.ec2_base._shell_with_ec2_env(
            'euca-terminate-instances %s' % (self.instance_id), True).split('\t')
        if out[1] == self.instance_id:
            self.logger.info('Instance %s terminated' % self.instance_id)
            return True
        return False
    # end terminate_instance

    def _create_keypair(self, key_name):
        output_lines = self.ec2_base._shell_with_ec2_env(
            'euca-describe-keypairs', True).split('\n')
        for line in output_lines:
            entries = [k for k in line.split('\t')]
            if entries:
                if key_name in entries[0]:
                    return
        username = self.inputs.host_data[self.cfgm_ip]['username']
        password = self.inputs.host_data[self.cfgm_ip]['password']
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (username, self.cfgm_ip),
                    password=password, warn_only=True, abort_on_prompts=True):
                rsa_pub_arg = '.ssh/id_rsa'
                self.logger.debug('Creating keypair')
                if exists('.ssh/id_rsa.pub'):  # If file exists on remote m/c
                    self.logger.debug('Public key exists. Getting public key')
                else:
                    self.logger.debug('Making .ssh dir')
                    run('mkdir -p .ssh')
                    self.logger.debug('Removing id_rsa*')
                    run('rm -f .ssh/id_rsa*')
                    self.logger.debug('Creating key using : ssh-keygen -f -t rsa -N')
                    run('ssh-keygen -f %s -t rsa -N \'\'' % (rsa_pub_arg))
                    self.logger.debug('Getting the created keypair')
                get('.ssh/id_rsa.pub', '/tmp/')
                openstack_host = self.inputs.host_data[self.inputs.openstack_ip]
                copy_file_to_server(openstack_host, '/tmp/id_rsa.pub', '/tmp',
                                    'id_rsa.pub')
                self.ec2_base._shell_with_ec2_env(
                    'euca-import-keypair -f /tmp/id_rsa.pub %s' % (self.key), True)

# end VPCVMFixture
