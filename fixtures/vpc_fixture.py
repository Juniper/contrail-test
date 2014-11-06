import time
import re
import fixtures
from fabric.api import local
from fabric.context_managers import shell_env, settings

from common.connections import ContrailConnections

from floating_ip import *


class VPCFixture(fixtures.Fixture):

    '''Fixture to create, verify and delete VPC, Subnet, Instance, 
       Floating IP allocation and association
       Flow: Euca2ools -> Boto -> Nova
    '''

    def __init__(
        self, inputs, cidr, subnet_cidr=None, floating_net_id=None, connections=None,
        doSubnet=False, doInstance=False, doFloating=True,
            doAcl=False, doSg=False, sgName=None):
        self.inputs = inputs
        self.logger = inputs.logger
        self.cidr = cidr
        self.vpc_id = None
        self.subnet_id = None
        self.do_subnet_test = doSubnet
        self.instance_id = None
        self.do_instance_test = doInstance
        self.do_floating_ip = doFloating
        self.floating_ip = None
        self.floating_ip_association = False
        self.floating_ip_allocation = False
        self.floating_net_id = floating_net_id
        self.def_acl_id = None
        self.do_acl = doAcl
        self.acl_association = False
        self.acl_association_id = None
        self.sg_id = None
        self.do_security_group = doSg
        self.sg_name = sgName

        if subnet_cidr and doSubnet:
            self.subnet_cidr = subnet_cidr
        else:
            self.subnet_cidr = cidr.split('/')[0] + '/' + '30'

        if doFloating and floating_net_id:
            self.fpool = 'fpool'
            self.connections = connections
    # end __init__

    def setUp(self):
        super(VPCFixture, self).setUp()
    # end setUp

    def cleanUp(self):
        # delete security group
        if self.do_security_group and self.sg_id:
            self.delete_security_group()

        # delete ACL
        if self.do_acl and not self.acl_association:
            self.delete_acl()

        # release floating IP and delete floating IP pool
        if self.do_floating_ip and self.floating_ip:
            self.release_floating_ip()
            self.fip_fixture.cleanUp()

        # terminate instance
        if self.instance_id and self.do_instance_test:
            self.terminate_instance()
            print('Waiting for VM to terminate')
            time.sleep(7)

        # delete subnet
        if self.do_subnet_test and self.subnet_id:
            self.delete_subnet()

        # delete VPC and its ec2 aceess key, ec2 secret key
        if self.vpc_id:
            self.delete_vpc()
            self.delete_ec2_keys(self.access_key)

        super(VPCFixture, self).cleanUp()
    # end cleanUp

    # EC2 Secret key and Access key setup functions

    def _set_ec2_keys(self, tenant):
        # export ec2 secret key and access key for admin or VPC
        keys = local(
            '(source /etc/contrail/openstackrc; keystone ec2-credentials-list)',
            capture=True).split('\n')[3:]
        found = False

        for key in keys:
            key = [k for k in filter(None, key.split(' ')) if k != '|']
            if key[0] == tenant:
                found = True
                self.logger.info('Exported ec2 keys for %s' % tenant)
                self.access_key = key[1]
                self.secret_key = key[2]
                break
        return found
    # end set_ec2_keys

    def _create_ec2_keys(self, tenant_name):
        # create ec2 credentials for VPC
        tenantId = self._get_tenant_id(tenant_name)
        local('(source /etc/contrail/openstackrc; keystone ec2-credentials-create \
                                                       --tenant-id %s)' % tenantId)
        self.logger.info('EC2 keys created for %s' % tenant_name)
        return True
    # end create_ec2_keys

    def delete_ec2_keys(self, accessKey):
        local('(source /etc/contrail/openstackrc; keystone ec2-credentials-delete \
                                                         --access %s)' % accessKey)
        self.logger.info('EC2 keys deleted for VPC')
    # end delete_ec2_keys

    def _get_admin_user_id(self):
        users = local(
            '(source /etc/contrail/keystonerc; keystone user-get admin)',
            capture=True).split('\n')

        for user in users:
            user = [k for k in filter(None, user.split(' ')) if k != '|']
            if user[0] == 'id':
                self.user_id = user[1]
                break

        return self.user_id
    # end _get_admin_user_id

    def _get_admin_role_id(self):
        roles = local(
            '(source /etc/contrail/keystonerc; keystone role-get admin)',
            capture=True).split('\n')

        for role in roles:
            role = [k for k in filter(None, role.split(' ')) if k != '|']
            if role[0] == 'id':
                self.role_id = role[1]
                break

        return self.role_id
    # end _get_admin_role_id

    def _get_tenant_id(self, tenantName):
        tenants = local('(source /etc/contrail/openstackrc; keystone tenant-get %s)'
                        % tenantName, capture=True).split('\n')

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
        local('(source /etc/contrail/keystonerc ; keystone user-role-add --user %s\
                              --role %s --tenant %s)' % (userId, roleId, tenantId))
        self.logger.info('Admin user with admin role added to VPC %s' %
                         self.vpc_id)
    # end _add_admin_role_to_tenant

    def _shell_with_ec2_env(self, command, ret):
        # shell to run Euca commands on machine with ec2 credentials
        first_cfgm = self.inputs.cfgm_ips[0]
        with settings(warn_only=True):
            with shell_env(EC2_ACCESS_KEY=self.access_key,
                           EC2_SECRET_KEY=self.secret_key,
                           EC2_URL='http://%s:8773/services/Cloud' % first_cfgm):
                out = local(command, capture=True)
            if ret:
                return out
    # end _shell_with_ec2_env

    # VPC Functions

    def create_vpc(self):
        if not self._set_ec2_keys(self.inputs.stack_tenant):
            self.logger.error('set ec2-key failed for admin')
            return False

        create_vpc_output = self._shell_with_ec2_env(
            'euca-create-vpc %s' % (self.cidr), True)
        self.logger.info('Create vpc with CIDR %s' % self.cidr)

        # get vpcid and setup ec2 environment
        if create_vpc_output:
            self.vpc_id = create_vpc_output.split(' ')[1][4:]
            self._add_admin_role_to_tenant()

            if not self._create_ec2_keys(self.vpc_id):
                self.logger.error('ec2-key create failed for vpc tenant')

            if not self._set_ec2_keys(self.vpc_id):
                self.logger.error('set ec2-key failed for vpc tenant')

            local('service openstack-nova-api restart')
            return True

        else:
            return False
    # end create_vpc

    def verify_vpc(self):
        verify_vpc_output = self._shell_with_ec2_env(
            'euca-describe-vpcs %s' % (self.vpc_id), True).split('\n')[2].split(' ')
        verify_vpc_output = filter(None, verify_vpc_output)

        if verify_vpc_output[1] == self.cidr and verify_vpc_output[0] == self.vpc_id:
            self.logger.info('VPC %s verified' % self.vpc_id)
            return True

        else:
            return False
    # end verify_vpc

    def delete_vpc(self):
        out = self._shell_with_ec2_env(
            'euca-delete-vpc %s' % (self.vpc_id), True)
        if len(out) > 0 and out.split(' ')[1] == self.vpc_id:
            self.logger.info('VPC %s deleted' % self.vpc_id)
            return True
        else:
            return False
    # end delete_vpc

    # Subnet Functions

    def create_subnet(self):
        create_subnet_output = self._shell_with_ec2_env(
            'euca-create-subnet -c %s %s' %
            (self.subnet_cidr, self.vpc_id), True)
        if create_subnet_output:
            self.subnet_id = create_subnet_output.split(' ')[0].split(':')[1]
            self.logger.info('Create subnet with CIDR %s' % self.subnet_cidr)
            return True
        else:
            return False
    # end create_subnet

    def verify_subnet(self):
        verify_subnet_output = self._shell_with_ec2_env(
            'euca-describe-subnets', True).split('\n')[2:]
        foundSubnet = False

        for subnet in verify_subnet_output:
            if subnet.startswith(self.subnet_id):
                foundSubnet = True
                break

        if not foundSubnet:
            return False

        subnet = subnet.split('\t')
        if subnet[1] == self.vpc_id and subnet[2] == self.subnet_cidr:
            self.logger.info('Subnet %s verified' % self.subnet_id)
            return True

        else:
            return False
    # end verify_subnet

    def delete_subnet(self):
        out = self._shell_with_ec2_env(
            'euca-delete-subnet %s' % (self.subnet_id), True)
        if len(out) > 0 and out.split(' ')[1] == self.subnet_id:
            self.logger.info('Subnet %s deleted' % self.subnet_id)
            return True
        else:
            return False
    # end delete_subnet

    # Instance Functions

    def _get_image_id(self):
        images = self._shell_with_ec2_env(
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

    def _get_instance_id(self, instances):
        instance = [k for k in instances[1].split('\t')]

        if instance[1].startswith('i-'):
            self.instance_id = instance[1]
            self.instance_name = instance[3]

        else:
            self.logger.error('create instance failed')

        return self.instance_id
    # end _get_instance_id

    def run_instance(self):
        imageId = self._get_image_id()

        run_instance_output = self._shell_with_ec2_env(
            'euca-run-instances %s -s %s' %
            (imageId, self.subnet_id), True).split('\n')
        instanceId = self._get_instance_id(run_instance_output)

        if not instanceId:
            return False
        self.logger.info(
            'Run Instance in subnet %s with %s image' % (self.subnet_id,
                                                         self.image_id))
        return True
    # end run_instance

    @retry(delay=1, tries=3)
    def verify_instance(self):
        print('Waiting for VM to be in running state  ...')
        time.sleep(7)
        instances = self._shell_with_ec2_env(
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
        out = self._shell_with_ec2_env(
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
            project_name='admin', inputs=self.inputs,
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

        out = self._shell_with_ec2_env(
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
        out = self._shell_with_ec2_env(
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
        out = self._shell_with_ec2_env(
            'euca-describe-addresses', True).split('\n')
        foundIp = False

        for ip in out:
            ip = filter(None, ip.split(' '))
            if ip[0] == self.floating_ip:
                self.fip_allcation_id = ip[2]
                foundIp = True

                # looger info for allocation or association verification
                if ip[2].split('-')[0] == 'eipalloc' and self.floating_ip_allocation:
                    self.logger.info('Floating IP %s verified. No instance associated'
                                     % self.floating_ip)
                elif ip[2].split('-')[0] == 'eipassoc' and self.floating_ip_association:
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
        out = self._shell_with_ec2_env(
            'euca-associate-address -a %s %s' % (self.fip_allcation_id,
                                                 self.instance_id), True).split('\t')
        if out:
            self.floating_ip_association = True
            self.fip_allcation_id = out[1]
            self.logger.info(
                'Associate Floating IP %s to Instance %s' % (self.floating_ip,
                                                             self.instance_id))
            return True

        else:
            return False
    # end associate_floating_ip

    def disassociate_floating_ip(self):
        out = self._shell_with_ec2_env('euca-disassociate-address %s' % (
            self.fip_allcation_id), True)
        if out == 'True':
            self.floating_ip_association = False
            self.fip_allcation_id.replace('eipassoc', 'eipalloc')
            self.logger.info(
                'Floating IP %s disassociated from instance %s' % (self.floating_ip,
                                                                   self.instance_id))
            return True
        else:
            return False
    # end disassociate_floating_ip

    # ACL

    def create_acl(self):
        out = self._shell_with_ec2_env(
            'euca-create-network-acl %s' % self.vpc_id, True)
        if len(out) > 0 and out.startswith('acl-'):
            self.acl_id = out
            self.logger.info('Create ACL in vpc %s' % self.vpc_id)
            return True

        else:
            return False
    # end create_acl

    def verify_acl(self):
        out = self._shell_with_ec2_env(
            'euca-describe-network-acls %s' % self.acl_id, True).split('\n')
        foundAcl = False

        if len(out) <= 0:
            return foundAcl

        acl_id = out[2].replace(' ', '')
        vpc_id = out[3].replace(' ', '')
        if acl_id == self.acl_id and vpc_id == self.vpc_id:
            self.logger.info('ACL %s verified' % self.acl_id)

            # check if acl associated or not
            if not self.acl_association:
                self.logger.info('ACL %s not associated with any subnet' %
                                 self.acl_id)
                foundAcl = True

            # check if acl associated with subnet or not
            else:
                for entry in out:
                    assoc_str = re.sub(' +', ' ', entry).replace(' ', '', 1)
                    assoc = assoc_str.split(' ')
                    if not assoc[0].startswith('aclassoc-'):
                        continue
                    if assoc[0] == self.acl_association_id and assoc[1] == self.subnet_id:
                        self.logger.info(
                            'ACL %s associated with subnet %s verified' %
                            (self.acl_id, self.subnet_id))
                        if self.acl_association:
                            foundAcl = True
                            break
            return foundAcl

        else:
            return False

    def delete_acl(self):
        out = self._shell_with_ec2_env(
            'euca-delete-network-acl %s' % self.acl_id, True)
        if out == 'True':
            self.logger.info('ACL %s deleted' % self.acl_id)
            return True
        else:
            return False
    # end delete_acl

    def associate_acl(self, acl=None):
        # if acl = default then associate subnet to default ACL for VPC
        # else associate subnet with ACL created using euca2ools
        if not acl:
            aclId = self.acl_id
            self.acl_association_id = self._get_acl_association_id()
            if not self.acl_association_id:
                self.logger.debug('Cannot get ACL association id')
        else:
            aclId = self.def_acl_id

        out = self._shell_with_ec2_env(
            'euca-replace-network-acl-association %s -a %s' % (aclId,
                                                               self.acl_association_id), True)
        if out:
            self.logger.info('Associate ACL %s to subnet %s' %
                             (aclId, self.subnet_id))
            if acl == 'default':
                self.acl_association = False
            else:
                self.acl_association = True
            return True

        return False
    # end associate_acl

    def _get_acl_association_id(self):
        out = self._shell_with_ec2_env(
            'euca-describe-network-acls', True).split('\n')
        assoc_id = None

        for entry in out:
            idx = out.index(entry)
            entry.replace(' ', '')
            if not entry.startswith('acl-'):
                continue

            vpc_id = out[idx + 1].replace(' ', '')
            if entry.startswith('acl-default'):
                self.def_acl_id = 'acl-default'

            for entry in out:
                assoc_str = re.sub(' +', ' ', entry).replace(' ', '', 1)
                assoc = assoc_str.split(' ')
                if not assoc[0].startswith('aclassoc-'):
                    continue
                if assoc[1] == self.subnet_id:
                    assoc_id = assoc[0]

        return assoc_id
    # end _get_acl_association_id

    def create_acl_rule(self, rule):
        out = self._shell_with_ec2_env('euca-create-network-acl-entry %s -r %s -p %s -a %s -n %s -f %s -t %s -d %s'
                                       % (self.acl_id, rule['number'],
                                           rule['protocol'], rule['action'],
                                           rule['cidr'], rule['fromPort'],
                                           rule['toPort'], rule['direction']), True)
        if out == 'True':
            self.logger.info('Rule %s added in ACL %s' %
                             (rule['number'], self.acl_id))
            return True
        else:
            return False
    # end create_acl_rule

    def replace_acl_rule(self, rule):
        out = self._shell_with_ec2_env('euca-replace-network-acl-entry %s -r %s -p %s -a %s -n %s -f %s -t %s -d %s'
                                       % (self.acl_id, rule['number'],
                                           rule['protocol'], rule['action'],
                                           rule['cidr'], rule['fromPort'],
                                           rule['toPort'], rule['direction']), True)
        if out == 'True':
            self.logger.info('Rule %s replaced in ACL %s' %
                             (rule['number'], self.acl_id))
            return True
        else:
            return False
    # end replace_acl_rule

    def delete_acl_rule(self, rule):
        out = self._shell_with_ec2_env('euca-delete-network-acl-entry %s -r %s -d %s'
                                       % (self.acl_id, rule['number'],
                                           rule['direction']), True)
        if out == 'True':
            self.logger.info('Rule %s deleted in ACL %s' %
                             (rule['number'], self.acl_id))
            return True
        else:
            return False
    # end delete_acl_rule

    # Security Group

    def create_security_group(self):
        out = self._shell_with_ec2_env(
            'euca-create-security-group -d sanity_test_group -v %s %s' %
            (self.vpc_id, self.sg_name), True).split('\t')
        if len(out) > 3 and out[2] == self.sg_name and out[3] == 'sanity_test_group':
            self.logger.info('Create security group %s' % self.sg_name)
            self.sg_id = out[1]
            return True
        else:
            return False
    # end create_security_group

    def verify_security_group(self):
        out = self._shell_with_ec2_env('euca-describe-group', True).split('\n')
        foundGroup = False

        for group in out:
            group = group.split('\t')
            if len(group) > 3 and group[2] == self.sg_name and group[3] == 'sanity_test_group':
                foundGroup = True
                self.logger.info('Security Group %s (%s) verified' %
                                 (self.sg_name, self.sg_id))
                break
        return foundGroup
    # end verify_security_group

    def delete_security_group(self):
        out = self._shell_with_ec2_env(
            'euca-delete-security-group %s' % self.sg_id, True)
        if out == 'Group %s deleted' % self.sg_id:
            self.logger.info('Security Group %s (%s) deleted' %
                             (self.sg_name, self.sg_id))
            return True
        else:
            return False
    # end delete_security_group

    def create_security_group_rule(self, rule):
        if rule.has_key('group_id'):
            cidr_group = rule['group_id']
            ruletail = '-o %s' % rule['group_id']
        else:
            cidr_group = rule['cidr']
            ruletail = '-s %s' % rule['cidr']

        out = self._shell_with_ec2_env('euca-authorize-security-group-%s -P %s -p %s %s %s'
                                       % (rule[
                                           'direction'], rule['protocol'],
                                          rule['port'], ruletail,
                                          self.sg_id), True).split('\n')
        if len(out) > 1:
            ruleList = out[1].split('\t')
            if self.sg_id in ruleList and rule['protocol'] in ruleList and cidr_group in ruleList:
                self.logger.info('Rule added successfuly')
                return True

        else:
            return False
    # end add_security_group_rule

    def delete_security_group_rule(self, rule):
        if rule.has_key('group_id'):
            cidr_group = rule['group_id']
            ruletail = '-o %s' % rule['group_id']
        else:
            cidr_group = rule['cidr']
            ruletail = '-s %s' % rule['cidr']

        out = self._shell_with_ec2_env('euca-revoke-security-group-%s -P %s -p %s %s %s'
                                       % (rule[
                                           'direction'], rule['protocol'],
                                          rule['port'], ruletail,
                                          self.sg_id), True).split('\n')
        if len(out) > 1:
            ruleList = out[1].split('\t')
            if self.sg_id in ruleList and rule['protocol'] in ruleList and cidr_group in ruleList:
                self.logger.info('Rule deleted successfuly')
                return True

        else:
            return False
    # end delete_security_group_rule

# end VPCFixture
