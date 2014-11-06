from fabric.api import local, run
from fabric.context_managers import shell_env, settings
import time


class EC2Base(object):

    def __init__(self, tenant=None, logger=None, inputs=None):
        self.inputs = inputs
        if not tenant:
            tenant = self.inputs.stack_tenant
        self.tenant = tenant
        self.logger = logger
        self.openstack_ip = self.inputs.openstack_ip
        self.os_username = self.inputs.host_data[self.openstack_ip]['username']
        self.os_password = self.inputs.host_data[self.openstack_ip]['password']
        if not self._set_ec2_keys(tenant):
            if not self.create_ec2_keys(tenant):
                self.logger.error('ec2-key create failed for vpc tenant')
        self.tenant_id = None

    def run_cmd_on_os_node(self, cmd):
        ''' 
        Run cmd on openstack node
        '''
        with settings(
            host_string='%s@%s' % (self.os_username, self.openstack_ip), password=self.os_password,
                warn_only=True, abort_on_prompts=False):
            output = run(cmd)
            return output
    # end run_cmd_on_os_node

    def _set_ec2_keys(self, tenant):
        # export ec2 secret key and access key for admin or VPC
        keys = self.run_cmd_on_os_node('(source /etc/contrail/openstackrc; keystone ec2-credentials-list)'
                                       ).split('\n')[3:]
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

    def _shell_with_ec2_env(self, command, ret):
        # shell to run Euca commands on machine with ec2 credentials
        with settings(
            host_string='%s@%s' % (self.os_username, self.openstack_ip), password=self.os_password,
                warn_only=True, abort_on_prompts=False):
            with shell_env(EC2_ACCESS_KEY=self.access_key,
                           EC2_SECRET_KEY=self.secret_key,
                           EC2_URL='http://%s:8773/services/Cloud' % self.openstack_ip):
                out = run(command)
                self.logger.debug('Command : %s' % (command))
                self.logger.debug('Output : %s' % (out))
                if 'Unauthorized' in out or 'Not Authorized' in out:
                    # A bad WA for bugs 1890 and 1984
                    self.inputs.restart_service(
                        'memcached', [self.inputs.openstack_ip])
                    self.inputs.restart_service(
                        'openstack-nova-api', [self.inputs.openstack_ip])
                    # If openstack is not built by us
                    self.inputs.restart_service(
                        'nova-api', [self.inputs.openstack_ip])
                    time.sleep(5)
                    self.logger.debug('Trying the command again')
                    out = run(command)
                    self.logger.debug('Command : %s' % (command))
                    self.logger.debug('Output : %s' % (out))
            if ret:
                return out
    # end _shell_with_ec2_env

    def create_ec2_keys(self, tenant_name):
        key_data = {}
        # create ec2 credentials for VPC
        tenantId = self._get_tenant_id(tenant_name)
        output = self.run_cmd_on_os_node('(source /etc/contrail/openstackrc; keystone ec2-credentials-create \
                               --tenant-id %s)' % tenantId, ).split('\n')
        self.logger.info('EC2 keys created for %s' % tenant_name)
        for row in output:
            if row[0] == '+':
                continue
            items = [k for k in filter(None, row.split(' ')) if k != '|']
            key_data[items[0]] = items[1]
        self.logger.info('Exported ec2 keys for %s' % tenant_name)
        self.access_key = key_data['access']
        self.secret_key = key_data['secret']
        self.logger.debug(key_data)
        return key_data
    # end create_ec2_keys

    def delete_ec2_keys(self, accessKey):
        self.run_cmd_on_os_node('(source /etc/contrail/openstackrc; keystone ec2-credentials-delete \
                                                         --access %s)' % accessKey)
        self.logger.info('EC2 keys deleted for VPC')
    # end delete_ec2_keys

    def _get_tenant_id(self, tenantName):
        tenants = self.run_cmd_on_os_node('(source /etc/contrail/openstackrc; keystone tenant-get %s)'
                                          % tenantName, ).split('\n')

        for tenant in tenants:
            tenant = [k for k in filter(None, tenant.split(' ')) if k != '|']
            if tenant[0] == 'id':
                self.tenant_id = tenant[1]
                break

        return self.tenant_id
    # end _get_tenant_id
# end class EC2Base
