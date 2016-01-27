import time
import re
import fixtures
from fabric.api import local, run
from fabric.context_managers import shell_env, settings

from common.connections import ContrailConnections
from ec2_base import EC2Base

from floating_ip import *


class VPCFixture(fixtures.Fixture):

    '''Fixture to create, verify and delete VPC
       Flow: Euca2ools -> Boto -> Nova
    '''

    def __init__(self, cidr, connections=None):
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = self.inputs.logger
        self.cidr = cidr
        self.vpc_id = None
        self.ec2_base = EC2Base(
            logger=self.logger,
            inputs=self.inputs)
        self.openstack_ip = self.inputs.openstack_ip
        self.os_username = self.inputs.host_data[self.openstack_ip]['username']
        self.os_password = self.inputs.host_data[self.openstack_ip]['password']
        self.acl_association = False
        self.acl_association_id = None
        self.tenant_id = None
        self.project_connections = None
    # end __init__

    def setUp(self):
        super(VPCFixture, self).setUp()
        self.create_vpc()
    # end setUp

    def create_vpc(self):
        create_vpc_output = self.ec2_base._shell_with_ec2_env(
            'euca-create-vpc %s' % (self.cidr), True)
        self.logger.info('Create vpc with CIDR %s' % self.cidr)

        # get vpcid and setup ec2 environment
        if 'EC2APIError' in create_vpc_output or create_vpc_output.failed:
            self.logger.warn('Unable to create VPC : %s' % (create_vpc_output))
            return False
        if create_vpc_output:
            self.vpc_id = create_vpc_output.split(' ')[1][4:]
            self._add_admin_role_to_tenant()

            key_data = self.ec2_base.create_ec2_keys(self.vpc_id)
            if key_data:
                self.addCleanup(self.ec2_base.delete_ec2_keys,
                                key_data['access'])
            else:
                self.logger.error('ec2-key create failed for vpc tenant')

            if not self.ec2_base._set_ec2_keys(self.vpc_id):
                self.logger.error('set ec2-key failed for vpc tenant')

            return True
        else:
            return False
    # end create_vpc

    def verify_on_setup(self):
        if not self.vpc_id:
            self.logger.warn('VPC ID is not set, VPC Verification failed')
            return False
        if not self.verify_vpc():
            self.logger.error('VPC %s verification failed' % (self.vpc_id))
            return False
        return True
    # end verify_on_setup

    def cleanUp(self):
        # delete VPC and its ec2 aceess key, ec2 secret key
        if self.vpc_id:
            self.delete_vpc()

        super(VPCFixture, self).cleanUp()
    # end cleanUp

    def run_cmd_on_os_node(self, cmd):
        '''
        Run cmd on openstack node
        '''
        with settings(host_string='%s@%s' % (self.os_username,
                                             self.openstack_ip), password=self.os_password,
                      warn_only=True, abort_on_prompts=False):
            output = run(cmd)
            return output
    # end run_cmd_on_os_node

    def _get_admin_user_id(self):
        users = self.run_cmd_on_os_node(
            '(source /etc/contrail/keystonerc; keystone user-get admin)',
        ).split('\n')

        for user in users:
            user = [k for k in filter(None, user.split(' ')) if k != '|']
            if user[0] == 'id':
                user_id = user[1]
                break

        return user_id
    # end _get_admin_user_id

    def _get_admin_role_id(self):
        roles = self.run_cmd_on_os_node(
            '(source /etc/contrail/keystonerc; keystone role-get admin)',
        ).split('\n')

        for role in roles:
            role = [k for k in filter(None, role.split(' ')) if k != '|']
            if role[0] == 'id':
                role_id = role[1]
                break

        return role_id
    # end _get_admin_role_id

    def _get_tenant_id(self, tenantName):
        tenants = self.run_cmd_on_os_node(
            '(source /etc/contrail/openstackrc; keystone tenant-get %s)' % tenantName, ).split('\n')

        for tenant in tenants:
            tenant = [k for k in filter(None, tenant.split(' ')) if k != '|']
            if tenant[0] == 'id':
                self.tenant_id = tenant[1]
                break

        return self.tenant_id
    # end _get_tenant_id

    def _add_admin_role_to_tenant(self):
        # add 'admin' user to VPC with 'admin' role
        userId = self._get_admin_user_id()
        roleId = self._get_admin_role_id()
        tenantId = self._get_tenant_id(self.vpc_id)
        if not tenantId:
            self.logger.warn('Tenant id not found for VPC %s' % (self.vpc_id))
            return False
        self.run_cmd_on_os_node(
            '(source /etc/contrail/keystonerc ; keystone user-role-add --user %s --role %s --tenant %s)' %
            (userId, roleId, tenantId))
        self.logger.info('Admin user with admin role added to VPC %s' %
                         self.vpc_id)
    # end _add_admin_role_to_tenant

    @retry(delay=5, tries=3)
    def verify_vpc(self):
        if not self.vpc_id:
            self.logger.warn(
                'VPC ID is not set, VPC may not be created at all')
            return False
        verify_vpc_output = self.ec2_base._shell_with_ec2_env(
            'euca-describe-vpcs |grep %s' % (self.vpc_id), True).split('\n')[0].split(' ')
        verify_vpc_output = filter(None, verify_vpc_output)

        if verify_vpc_output[1] == self.cidr and \
                verify_vpc_output[0] == self.vpc_id:
            self.logger.info('VPC %s verified' % self.vpc_id)
            return True

        else:
            return False
    # end verify_vpc
    # vaildation of a partiular vpcs entry

    def verify_vpc_entry(self, vpc_id):

        if not vpc_id:
            self.logger.warn(
                'VPC ID is not set, VPC may not be created at all')
            return False

        verify_vpc_output = self.ec2_base._shell_with_ec2_env(
            'euca-describe-vpcs %s | grep vpc- | wc -l' % (vpc_id), True)

        if verify_vpc_output != '1':

            found_vpc = False
            self.logger.debug(
                'euca-describe-vpcs <vpcs-Id> returns Multiple Entries')

        else:
            self.logger.info('Single vpcs entry  %s verified' % (vpc_id))
            found_vpc = True
        return found_vpc

    # end verify_vpc

    def delete_vpc(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-delete-vpc %s' % (self.vpc_id), True)
        if len(out) > 0 and out.split(' ')[1] == self.vpc_id:
            self.logger.info('VPC %s deleted' % self.vpc_id)
            return True
        else:
            return False
    # end delete_vpc

    # Instance Functions

    def _get_image_id(self):
        images = self.ec2_base._shell_with_ec2_env(
            'euca-describe-images', True).split('\n')

        for image in images:
            image = [k for k in image.split('\t')]
            if image[4] == 'available':
                self.image_id = image[1]
                self.logger.info('Using image %s(%s) to launch VM' %
                                 (self.image_id, image[2]))
                break

        return self.image_id
    # end _get_image_id

    def _get_nat_image_id(self):
        images = self.ec2_base._shell_with_ec2_env(
            'euca-describe-images', True).split('\n')

        for image in images:
            image = [k for k in image.split('\t')]
            if image[4] == 'available' and image[2] == 'None (nat-service)':
                image_id = image[1]
                self.logger.info('Using image %s(%s) to launch VM' %
                                 (image_id, image[2]))
                break

        return image_id
    # end _get_nat_image_id

    def _get_instance_id(self, instances):
        instance = [k for k in instances[1].split('\t')]

        if instance[1].startswith('i-'):
            self.instance_id = instance[1]
            self.instance_name = instance[3]

        else:
            self.logger.error('create instance failed')

        return self.instance_id
    # end _get_instance_id

    @retry(delay=1, tries=3)
    def verify_instance(self):
        self.logger.debug('Waiting for VM to be in running state  ...')
        time.sleep(7)
        instances = self.ec2_base._shell_with_ec2_env(
            'euca-describe-instances', True).split('\n')

        foundInstance = False
        for instance in instances:
            instance = [k for k in instance.split('\t')]
            if instance[1] == self.instance_id and instance[5] == 'running':
                foundInstance = True
                self.logger.info('Instance %s verified' % self.instance_id)
                break

        return foundInstance
    # end verify_instance

    def terminate_instance(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-terminate-instances %s' % (self.instance_id), True).split('\t')
        if out[1] == self.instance_id:
            self.logger.info('Instance %s terminated' % self.instance_id)
            return True
        return False
    # end terminate_instance

    # Floating IP

    def _create_floating_ip_pool(self):
        # create flaoting ip pool
        self.fip_fixture = FloatingIPFixture(
            inputs=self.inputs,
            connections=self.connections, pool_name=self.fpool,
            vn_id=self.floating_net_id)
        self.fip_fixture.setUp()

        if self.fip_fixture.verify_on_setup():
            return True
        else:
            self.logger.error('FIP pool create error')

        return False
    # end _create_floating_ip_pool

    def allocate_floating_ip(self):
        if not self._create_floating_ip_pool():
            return False

        out = self.ec2_base._shell_with_ec2_env(
            'euca-allocate-address -d vpc', True).split('\t')
        if out:
            self.floating_ip = out[1]
            self.fip_allcation_id = out[2]
            self.floating_ip_allocation = True
            self.logger.info(
                'Allocate a Floating IP from Floating Ip pool fpool')
            return True

        else:
            return False
    # end allocate_floating_ip

    def release_floating_ip(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-release-address %s' % self.fip_allcation_id, True)
        if out:
            self.logger.info('Floating IP %s released' % self.floating_ip)
            # TODO enable verify_floating ip after describe_address
            #     has been fixed in cloud.py
            # return not self.verify_floating_ip()
            return True
        else:
            return False
    # end release_floating_ip

    def verify_floating_ip(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-describe-addresses', True).split('\n')
        foundIp = False

        for ip in out:
            ip = filter(None, ip.split(' '))
            if ip[0] == self.floating_ip:
                self.fip_allcation_id = ip[2]
                foundIp = True

                # looger info for allocation or association verification
                if ip[2].split('-')[0] == 'eipalloc' \
                        and self.floating_ip_allocation:
                    self.logger.info(
                        'Floating IP %s verified. No instance associated'
                        % self.floating_ip)
                elif ip[2].split('-')[0] == 'eipassoc' and  \
                        self.floating_ip_association:
                    self.logger.info(
                        'Floating IP %s associated with instance %s verified' %
                        (self.floating_ip, ip[3]))
                else:
                    self.logger.debug(
                        'Floating IP allocation or association id problem')
                break

        return foundIp
    # end verify_floating_ip

    def associate_floating_ip(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-associate-address -a %s %s' % (self.fip_allcation_id, self.instance_id), True).split('\t')
        if out:
            self.floating_ip_association = True
            self.fip_allcation_id = out[1]
            self.logger.info('Associate Floating IP %s to Instance %s' %
                             (self.floating_ip, self.instance_id))
            return True

        else:
            return False
    # end associate_floating_ip

    def disassociate_floating_ip(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-disassociate-address %s' % (self.fip_allcation_id), True)
        if out == 'True':
            self.floating_ip_association = False
            self.fip_allcation_id.replace('eipassoc', 'eipalloc')
            self.logger.info('Floating IP %s disassociated from instance %s' %
                             (self.floating_ip, self.instance_id))
            return True
        else:
            return False
    # end disassociate_floating_ip

    # ACL

    def create_acl(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-create-network-acl %s' % self.vpc_id, True)
        if len(out) > 0 and out.startswith('acl-'):
            acl_id = out
            self.logger.info('Create ACL in vpc %s' % self.vpc_id)
            return acl_id

        else:
            return None
    # end create_acl

    def delete_acl(self, acl_id):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-delete-network-acl %s' % acl_id, True)
        if out == 'True':
            self.logger.info('ACL %s deleted' % acl_id)
            return True
        else:
            self.logger.error('Unable to delete ACL %s' % (acl_id))
            return False
    # end delete_acl

    def create_acl_rule(self, acl_id, rule):
        cmd = 'euca-create-network-acl-entry %s ' % (acl_id)
        acl_keys = ['protocol', 'action', 'cidr',
                    'fromPort', 'toPort', 'direction']
        acl_key_prefix = ['-p', '-a', '-n', '-f', '-t', '-d']
        acl_strings = {
            'number': '-r',
            'protocol': '-p',
            'action': '-a',
            'cidr': '-n',
            'fromPort': '-f',
            'toPort': '-t',
            'direction': '-d',
        }
        for key in rule.keys():
            cmd += ' %s %s ' % (acl_strings[key], rule[key])

        out = self.ec2_base._shell_with_ec2_env(cmd, True)

        if out == 'True':
            self.logger.info(
                'Rule %s added in ACL %s' % (rule['number'], acl_id))
            return True
        else:
            return False
    # end create_acl_rule

    def replace_acl_rule(self, acl_id, rule):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-replace-network-acl-entry %s -r %s -p %s -a %s -n %s -f %s -t %s -d %s'
            % (acl_id, rule['number'],
               rule['protocol'], rule['action'],
               rule['cidr'], rule['fromPort'],
               rule['toPort'], rule['direction']), True)
        if out == 'True':
            self.logger.info(
                'Rule %s replaced in ACL %s' % (rule['number'], acl_id))
            return True
        else:
            return False
    # end replace_acl_rule

    def delete_acl_rule(self, acl_id, rule):
        out = self.ec2_base._shell_with_ec2_env('euca-delete-network-acl-entry %s -r %s -d %s'
                                                % (acl_id, rule['number'],
                                                   rule['direction']), True)
        if out == 'True':
            self.logger.info(
                'Rule %s deleted in ACL %s' % (rule['number'], acl_id))
            return True
        else:
            return False
    # end delete_acl_rule

    # Route Table
    def create_route_table(self, vpc_id=None):
        '''
        Create route table in VPC
        [root@nodec22 0000_]# euca-create-route-table vpc-96d08029
        rtb-2e799f33    vpc-96d08029    10.1.1.0/24     local   active
        [root@nodec22 0000_]#
        '''
        if not vpc_id:
            vpc_id = self.vpc_id
        out = self.ec2_base._shell_with_ec2_env('euca-create-route-table %s' %
                                                (vpc_id), True).split('\t')
        if out[1] == vpc_id:
            rtb_id = out[0]
            self.logger.info(
                'Created Route table %s in VPC %s' % (rtb_id, vpc_id))
            return rtb_id
        else:
            return None
    # end create_route_table

    def verify_route_table(self, rtb_id):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-describe-route-tables %s' % (rtb_id), True).split('\n')
        found_rtb = False

        for line in out:
            if rtb_id in line:
                found_rtb = True
                self.logger.info('Route table %s verified' % (rtb_id))
                break

        # validation for Bug [1904]
        out = self.ec2_base._shell_with_ec2_env(
            'euca-describe-route-tables %s | grep rtb- | wc -l' % (rtb_id), True)
        if out != '1':
            found_rtb = False
            self.logger.debug(
                'euca-describe-route-tables <rt-Id> returns Multiple Entries')
        else:
            self.logger.info('Single Route table %s verified' % (rtb_id))

        return found_rtb
    # end verify_route_table

    def delete_route_table(self, rtb_id):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-delete-route-table %s' % rtb_id, True)
        if 'True' in out:
            self.logger.info('Route Table %s deleted' % (rtb_id))
            return True
        else:
            return False
    # end delete_route_table

    def associate_route_table(self, rtb_id, subnet_id):
        '''
        Associate subnet with route_table
        [root@nodec22 ~]# euca-associate-route-table -s subnet-4dad7f88 rtb-9bb0e59f
ASSOCIATION     rtbassoc-2f162321       rtb-9bb0e59f    subnet-4dad7f88
[root@nodec22 ~]#
        '''
        out = self.ec2_base._shell_with_ec2_env(
            'euca-associate-route-table -s %s %s' % (subnet_id, rtb_id), True).split('\n')
        line = filter(None, out[0].split('\t'))
        if line[2] == rtb_id:
            assoc_id = line[1]
            self.logger.info('Route table %s is associated with Subnet %s \
                     with association id %s' % (rtb_id, subnet_id, assoc_id))
            return assoc_id
        else:
            return None
    # end associate_route_table

    def disassociate_route_table(self, rtb_assoc_id):
        '''
        Disassociate a subnet from this route table
        '''
        out = self.ec2_base._shell_with_ec2_env(
            'euca-disassociate-route-table %s' % (rtb_assoc_id), True)
        if out == 'True':
            self.logger.info('Association id %s removed' % (rtb_assoc_id))
            return True
        else:
            return False
    # end disassociate_route_table

    def create_route(self, prefix, rtb_id, instance_id=None, gw_id=None):
        '''
        Create a route entry in a route table
        '''
        cmd = 'euca-create-route '
        if instance_id:
            cmd += '-i %s ' % instance_id
        if gw_id:
            cmd += '-g %s ' % gw_id
        out = self.ec2_base._shell_with_ec2_env(cmd + '-r %s %s' % (prefix,
                                                                    rtb_id), True).split('\n')
        line = filter(None, out[0].split('\t'))
        if line[2] == prefix:
            self.logger.info('Created Route with prefix %s in %s' % (prefix,
                                                                     rtb_id))
            return True
        # endif
        return False
    # end create_route

    def delete_route(self, rtb_id, prefix):
        '''
        Delete route from route table
        Ex:
        [root@nodec22 ~]# euca-delete-route -r 0.0.0.0/0 rtb-9bb0e59f
True
        '''
        out = self.ec2_base._shell_with_ec2_env('euca-delete-route -r %s %s'
                                                % (prefix, rtb_id), True)
        if out == 'True':
            self.logger.info('Route with prefix %s removed from Route table %s'
                             % (prefix, rtb_id))
            return True
        else:
            return False
    # end delete_route

    # Security Group

    def create_security_group(self, sg_name):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-create-security-group -d sanity_test_group -v %s %s' % (self.vpc_id, sg_name), True).split('\t')
        if len(out) > 3 and out[2] == sg_name and out[3] == 'sanity_test_group':
            self.logger.info('Create security group %s' % sg_name)
            sg_id = out[1]
            return sg_id
        else:
            return None
    # end create_security_group

    def verify_security_group(self, sg_name):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-describe-group', True).split('\n')
        foundGroup = False

        for group in out:
            group = group.split('\t')
            if len(group) > 3 and group[2] == sg_name and \
                    group[3] == 'sanity_test_group':
                foundGroup = True
                self.logger.info('Security Group %s verified' % (sg_name))
                break
        return foundGroup
    # end verify_security_group

    def get_security_group_id(self, sg_name):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-describe-security-groups --filter vpc-id=%s' % (self.vpc_id), True).split('\n')
        sg_id = None
        for group in out:
            group = group.split()
            if len(group) >= 3 and group[2] == sg_name:
                sg_id = group[0]
                break
        return sg_id
    # end get_security_group_id

    def delete_security_group(self, sg_id):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-delete-security-group %s' % sg_id, True)
        if out == 'Group %s deleted' % sg_id:
            self.logger.info('Security Group %s deleted' % (sg_id))
            return True
        else:
            return False
    # end delete_security_group

    def create_security_group_rule(self, sg_id, rule):
        if rule.has_key('source-group'):
            cidr_group = rule['source-group']
        else:
            cidr_group = rule['cidr']
        cmd = 'euca-authorize-security-group-%s ' % (rule['direction'])
        sg_keys = ['protocol', 'port', 'cidr', 'source-group']
        acl_strings = {
            'protocol': '-P',
            'cidr': '-s',
            'port': '-p',
            'source-group': '-o',
        }
        for key in rule.keys():
            if not key == 'direction':
                cmd += ' %s %s ' % (acl_strings[key], rule[key])
        cmd += sg_id

        out = self.ec2_base._shell_with_ec2_env(cmd, True).split('\n')
        if len(out) > 1:
            ruleList = out[1].split('\t')
            if sg_id in ruleList and \
                    rule['protocol'] in ruleList and cidr_group in ruleList:
                self.logger.info('Rule added successfuly')
                return True

        else:
            return False
    # end add_security_group_rule

    def delete_security_group_rule(self, sg_id, rule):
        if rule.has_key('source-group'):
            cidr_group = rule['source-group']
        else:
            cidr_group = rule['cidr']
        cmd = 'euca-revoke-security-group-%s ' % (rule['direction'])
        sg_keys = ['protocol', 'port', 'cidr', 'source-group']
        acl_strings = {
            'protocol': '-P',
            'cidr': '-s',
            'port': '-p',
            'source-group': '-o',
        }
        for key in rule.keys():
            if not key == 'direction':
                cmd += ' %s %s ' % (acl_strings[key], rule[key])
        cmd += sg_id

        out = self.ec2_base._shell_with_ec2_env(cmd, True).split('\n')
        if len(out) > 1:
            ruleList = out[1].split('\t')
            if sg_id in ruleList and rule['protocol'] in ruleList and \
                    cidr_group in ruleList:
                self.logger.info('Rule deleted successfuly')
                return True

        else:
            return False
    # end delete_security_group_rule

    # Internet Gateway
    def create_gateway(self):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-create-internet-gateway', True)
        if len(out) > 0 and 'igw-default' in out:
            gw_id = 'igw-default'
            self.logger.info('Created Gateway %s in vpc %s' %
                            (gw_id, self.vpc_id))
            return gw_id
        else:
            return None
    # end create_gateway

    def delete_gateway(self, gw_id):
        out = self.ec2_base._shell_with_ec2_env(
            'euca-delete-internet-gateway %s' % (gw_id), True)
        if 'True' in out:
            self.logger.info('Deleted Gateway %s in vpc %s' %
                            (gw_id, self.vpc_id))
            return gw_id
        else:
            return None
    # end delete_gateway

    def get_project_connections(self, username=None, password=None):
        if not username:
            username = 'admin'
        if not password:
            password = 'contrail123'
        if not self.project_connections:
            self.project_connections = ContrailConnections(
                inputs=self.inputs,
                logger=self.logger,
                project_name=self.vpc_id,
                username=username,
                password=password)
        return self.project_connections
    # end get_project_connections



# end VPCFixture
