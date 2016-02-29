import os
from common.openstack_libs import nova_client as mynovaclient
from common.openstack_libs import nova_exception as novaException
from fabric.context_managers import settings, hide, cd, shell_env
from fabric.api import run, local, env
from fabric.operations import get, put
from fabric.contrib.files import exists
from tcutils.util import *
from tcutils.cfgparser import parse_cfg_file
from tcutils.timeout import timeout, TimeoutError
import socket
import time
import re
from common import vcenter_libs

#from contrail_fixtures import contrail_fix_ext

#@contrail_fix_ext (ignore_verify=True, ignore_verify_on_setup=True)


class NovaHelper():

    def __init__(self, inputs,
                 project_name,
                 key='key1',
                 username=None,
                 password=None):
        httpclient = None
        self.inputs = inputs
        self.username = username or inputs.stack_user
        self.password = password or inputs.stack_password
        self.project_name = project_name
        self.cfgm_ip = inputs.cfgm_ip
        self.openstack_ip = inputs.openstack_ip
        # 1265563 keypair name can only be alphanumeric. Fixed in icehouse
        self.key = self.project_name+self.username+key
        self.obj = None
        if not self.inputs.ha_setup:
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                'http://' + self.openstack_ip + ':5000/v2.0'
        else:
            self.auth_url = os.getenv('OS_AUTH_URL') or \
                'http://' + self.inputs.auth_ip + ':5000/v2.0'
        self.logger = inputs.logger
        self.images_info = parse_cfg_file('configs/images.cfg')
        self.flavor_info = parse_cfg_file('configs/flavors.cfg')
        self.endpoint_type = inputs.endpoint_type
        self._connect_to_openstack()
        self.hypervisor_type = os.environ.get('HYPERVISOR_TYPE') \
                                if os.environ.has_key('HYPERVISOR_TYPE') \
                                else None
    # end __init__

    def _connect_to_openstack(self):
        insecure = bool(os.getenv('OS_INSECURE',True))
        self.obj = mynovaclient.Client('2',
                                       username=self.username,
                                       project_id=self.project_name,
                                       api_key=self.password,
                                       auth_url=self.auth_url,
                                       insecure=insecure,
                                       endpoint_type=self.endpoint_type
                      )
        if 'keypair' not in env:
            env.keypair = dict()
        if not env.keypair.get(self.key, False):
            try:
                f = '/tmp/%s'%self.key
                lock = Lock(f)
                lock.acquire()
                env.keypair[self.key] = self._create_keypair(self.key)
            finally:
                lock.release()
        self.compute_nodes = self.get_compute_host()
        self.zones = self._list_zones()
        self.hosts_list = []
        self.hosts_dict = self._list_hosts()
    # end setUp

    def get_hosts(self, zone=None):
        if zone and self.hosts_dict.has_key(zone):
            return self.hosts_dict[zone][:]
        else:
            return self.hosts_list

    def get_zones(self):
        return self.zones[:]

    def _list_hosts(self):
        nova_computes = self.obj.hosts.list()
        nova_computes = filter(lambda x: x.zone != 'internal', nova_computes)
        host_dict = dict()
        for compute in nova_computes:
            self.hosts_list.append(compute.host_name)
            host_list = host_dict.get(compute.zone, None)
            if not host_list: host_list = list()
            host_list += [compute.host_name]
            host_dict[compute.zone] = host_list
        return host_dict

    def _list_zones(self):
        zones = self.obj.availability_zones.list()
        zones = filter(lambda x: x.zoneName != 'internal', zones)
        return map(lambda x: x.zoneName, zones)

    def get_handle(self):
        return self.obj
    # end get_handle

    @retry(delay=5, tries=20)
    def check_if_image_active(self, image_id):
        ''' Check whether the given image id is in 'active' state '''
        self.logger.debug('Check whether image by uuid %s is active'%image_id)
        image = self.obj.images.get(image_id)
        if image.status.lower() == 'active':
            return (True, image)
        self.logger.debug('Image %s is not active.'%image.name)
        return (False, None)

    def find_image(self, image_name):
        got_image = None
        images_list = self.obj.images.list()
        for image in images_list:
            if image.name == image_name:
                (rv, got_image) = self.check_if_image_active(image.id)
                if rv is True:
                   return got_image
        # end for
        if not got_image:
            self.logger.debug('Image by name %s either not found or not active'%
                              (image_name))
        return got_image
    # end find_image

    def get_image(self, image_name='ubuntu'):
        got_image = self.find_image(image_name)
        if not got_image:
            self._install_image(image_name=image_name)
            got_image = self.find_image(image_name)
        return got_image
    # end get_image

    def get_flavor(self, name):
        try:
            flavor = self.obj.flavors.find(name=name)
        except novaException.NotFound:
            self._install_flavor(name=name)
            flavor = self.obj.flavors.find(name=name)
        return flavor
    # end get_flavor

    def get_vm_if_present(self, vm_name=None, project_id=None, vm_id=None):
        try:
            vm_list = self.obj.servers.list(search_opts={"all_tenants": True})
            for vm in vm_list:
                if project_id and vm.tenant_id != self.strip(project_id):
                    continue
                if (vm_name and vm.name == vm_name) or (vm_id and vm.id == vm_id):
                    return vm
        except novaException.NotFound:
            return None
        except Exception:
            self.logger.exception('Exception while finding a VM')
            return None
        return None
    # end get_vm_if_present

    def get_vm_by_id(self, vm_id):
        try:
            vm = self.obj.servers.find(id=vm_id)
            if vm:
                return vm
        except novaException.NotFound:
            return None
        except Exception:
            self.logger.exception('Exception while finding a VM')
            return None
    # end get_vm_by_id

    def _install_flavor(self, name):
        flavor_info = self.flavor_info[name]
        try:
            self.obj.flavors.create(name=name,
                                    vcpus=flavor_info['vcpus'],
                                    ram=flavor_info['ram'],
                                    disk=flavor_info['disk'])
        except Exception, e:
            self.logger.exception('Exception adding flavor %s' % (name))
            raise e
    # end _install_flavor

    def _install_image(self, image_name):
        self.logger.debug('Installing image %s'%image_name)
        image_info = self.images_info[image_name]
        webserver = image_info['webserver'] or \
            os.getenv('IMAGE_WEB_SERVER', '10.204.217.158')
        location = image_info['location']
        params = image_info['params']
        image = image_info['name']
        image_type = image_info['type']
        contrail_test_path = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)),'..'))
        if contrail_test_path and os.path.isfile("%s/images/%s" % (contrail_test_path, image_name)):
            build_path = "file://%s/images/%s" % (contrail_test_path, image_name)
        elif re.match(r'^file://', location):
            build_path = '%s/%s' % (location, image)
        else:
            build_path = 'http://%s/%s/%s' % (webserver, location, image)

        #workaround for bug https://bugs.launchpad.net/juniperopenstack/+bug/1447401 [START]
        #Can remove this when above bug is fixed
        if image_type == 'docker':
            for host in self.hosts_dict['nova/docker']:
                username = self.inputs.host_data[host]['username']
                password = self.inputs.host_data[host]['password']
                ip = self.inputs.host_data[host]['host_ip']
                with settings(
                    host_string='%s@%s' % (username, ip),
                        password=password, warn_only=True, abort_on_prompts=False):
                    self.load_docker_image_on_host(build_path)
        #workaround for bug https://bugs.launchpad.net/juniperopenstack/+bug/1447401 [END]

        username = self.inputs.host_data[self.openstack_ip]['username']
        password = self.inputs.host_data[self.openstack_ip]['password']

        with settings(
            host_string='%s@%s' % (username, self.openstack_ip),
                password=password, warn_only=True, abort_on_prompts=False):
            return self.copy_and_glance(build_path, image_name, image, params, image_type)
    # end _install_image

    def download_image(self, image_url):
        """ Get the image from build path - it download the image  in case of http[s].
        In case of file:// url, copy it to the node.

        Args:
            image_url: Image url - it may be file:// or http:// url

        Returns: Local image filesystem absolute path

        """
        if re.match(r'^file://', image_url):
            abs_path = re.sub('file://','',image_url)
            if not re.match(r'^/', abs_path):
                abs_path = '/' + abs_path
            if os.path.exists(abs_path):
                filename=os.path.basename(abs_path)
                put(abs_path, '/tmp/%s' % filename)
                return '/tmp/%s' % filename
        elif re.match(r'^(http|https)://', image_url):
            filename=os.path.basename(image_url)
            self.execute_cmd_with_proxy("wget %s -O /tmp/%s" % (image_url, filename))
            return '/tmp/%s' % filename

    def load_docker_image_on_host(self, build_path):
        run('pwd')
        image_abs_path = self.download_image(build_path)
        # Add the image to docker
        if '.gz' in image_abs_path:
            image_gz = os.path.basename(image_abs_path)
            image_tar = image_gz.split('.gz')[0]
            self.execute_cmd_with_proxy("gunzip -f /tmp/%s" % image_gz)
        else:
            image_tar = os.path.basename(image_abs_path)

        self.execute_cmd_with_proxy("docker load -i /tmp/%s" % image_tar)

    def get_image_account(self, image_name):
        '''
        Return the username and password considered for the image name
        '''
        return([self.images_info[image_name]['username'],
                self.images_info[image_name]['password']])
    # end get_image_account

    def get_default_image_flavor(self, image_name):
        return self.images_info[image_name]['flavor']

    def execute_cmd_with_proxy(self, cmd):
        if self.inputs.http_proxy:
            with shell_env(http_proxy=self.inputs.http_proxy):
                sudo(cmd)
        else:
            sudo(cmd)

    def copy_and_glance(self, build_path, generic_image_name, image_name, params, image_type):
        """copies the image to the host and glances.
           Requires Image path
        """
        run('pwd')
        image_abs_path = self.download_image(build_path)
        if '.gz' in image_abs_path:
            self.execute_cmd_with_proxy('gunzip -f %s' % image_abs_path)
            image_path_real=image_abs_path.split('.gz')[0]
        else:
            image_path_real=image_abs_path

        cmd = '(source /etc/contrail/openstackrc; glance image-create --name "%s" \
                   --is-public True %s --file %s)' % (generic_image_name, params, image_path_real)

        self.execute_cmd_with_proxy(cmd)
        return True

    def _create_keypair(self, key_name):
        username = self.inputs.host_data[self.cfgm_ip]['username']
        password = self.inputs.host_data[self.cfgm_ip]['password']
        try:
            # Check whether the rsa.pub and keypair matches
            # On pre icehouse novaclient #1223934 observed so get() fails
            # keypair = self.obj.keypairs.get(keypair=key_name)
            keypairs = [x for x in self.obj.keypairs.list() if x.id == key_name]
            if not keypairs:
                raise novaException.NotFound('keypair not found')
            pkey_in_nova = keypairs[0].public_key.strip()
            with settings(hide('everything'), host_string='%s@%s' % (username, self.cfgm_ip),
                    password=password, warn_only=True, abort_on_prompts=True):
                if exists('.ssh/id_rsa.pub'):
                    get('.ssh/id_rsa.pub', '/tmp/')
                    pkey_in_host = open('/tmp/id_rsa.pub', 'r').read().strip()
                    if pkey_in_host == pkey_in_nova:
                        self.logger.debug('Not creating keypair since it exists')
                        return True
            self.logger.error('Keypair and rsa.pub doesnt match.')
            raise Exception('Keypair and rsa.pub doesnt match.'
                            ' Seems rsa keys are updated outside of test env.'
                            ' Delete nova keypair and restart the test')
        except novaException.NotFound:
            pass
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (username, self.cfgm_ip),
                    password=password, warn_only=True, abort_on_prompts=True):
                rsa_pub_arg = '.ssh/id_rsa'
                self.logger.debug('Creating keypair %s' % (key_name)) 
                if exists('.ssh/id_rsa.pub'):  # If file exists on remote m/c
                    self.logger.debug('Public key exists. Getting public key')
                    get('.ssh/id_rsa.pub', '/tmp/')
                else:
                    self.logger.debug('Making .ssh dir')
                    run('mkdir -p .ssh')
                    self.logger.debug('Removing id_rsa*')
                    run('rm -f .ssh/id_rsa*')
                    self.logger.debug('Creating key using : ssh-keygen -f -t rsa -N')
                    run('ssh-keygen -f %s -t rsa -N \'\'' % (rsa_pub_arg))
                    self.logger.debug('Getting the created keypair')
                    get('.ssh/id_rsa.pub', '/tmp/')
                self.logger.debug('Reading publick key')
                pub_key = open('/tmp/id_rsa.pub', 'r').read()
                self.obj.keypairs.create(key_name, public_key=pub_key)
        return True
    # end _create_keypair

    def get_nova_services(self, **kwargs):
        try:
            nova_services = self.obj.services.list(**kwargs)
            nova_services = filter(lambda x: x.state != 'down' and x.status != 'disabled',
                   nova_services)
            self.logger.debug('Services list from nova: %s' %
                             nova_services)
            return nova_services
        except:
            self.logger.debug('Unable to retrieve services from nova obj')
            self.logger.debug('Using \"nova service-list\" to retrieve'
                              ' services info')
            pass

        service_list = []
        username = self.inputs.host_data[self.openstack_ip]['username']
        password = self.inputs.host_data[self.openstack_ip]['password']
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (username, self.openstack_ip),
                    password=password):
                services_info = run(
                    'source /etc/contrail/openstackrc; nova service-list')
        services_info = services_info.split('\r\n')
        get_rows = lambda row: map(str.strip, filter(None, row.split('|')))
        columns = services_info[1].split('|')
        columns = map(str.strip, filter(None, columns))
        columns = map(str.lower, columns)
        columns_no_binary = map(str.lower, columns)
        columns_no_binary.remove('binary')
        rows = map(get_rows, services_info[3:-1])
        nova_class = type('NovaService', (object,), {})
        for row in rows:
            datadict = dict(zip(columns, row))
            for fk, fv in kwargs.items():
                if datadict[fk] != fv:
                    break
                else:
                    if datadict['status'] == 'disabled' and \
                       datadict['state'] == 'down':
                        break
                    service_obj = nova_class()
                    for key, value in datadict.items():
                        setattr(service_obj, key, value)

                    # Append the service into the list.
                    service_list.append(service_obj)
        return service_list

    def create_vm(self, project_uuid, image_name, vm_name, vn_ids,
                  node_name=None, sg_ids=None, count=1, userdata=None,
                  flavor=None, port_ids=None, fixed_ips=None, zone=None):

        if node_name == 'disable':
            zone = None
        elif zone and node_name:
            if zone not in self.zones:
                raise RuntimeError("Zone %s is not available" % zone)
            if node_name not in self.hosts_dict[zone]:
                raise RuntimeError("Zone %s doesn't have compute with name %s"
                                        % (zone, node_name))
        elif node_name:
            nova_services = self.get_nova_services(binary='nova-compute')
            for compute_svc in nova_services:
                if compute_svc.host == node_name:
                    zone = True
                    break
                elif (compute_svc.host in self.inputs.compute_ips and
                      self.inputs.host_data[node_name]['host_ip'] == compute_svc.host):
                    zone = True
                    break
            if not zone:
                raise RuntimeError(
                    "Compute host %s is not listed in nova serivce list" % node_name)

            zone = self.get_compute_node_zone(node_name)
        else:
            zone, node_name = self.lb_node_zone(zone)

        try:
            f = '/tmp/%s'%image_name
            lock = Lock(f)
            lock.acquire()
            image_name = self.get_image_name_for_zone(image_name=image_name, zone=zone)
            image = self.get_image(image_name=image_name)
            if not flavor:
                flavor = self.get_default_image_flavor(image_name=image_name)
            flavor = self.get_flavor(name=flavor)
        finally:
            lock.release()

        if userdata:
            with open(userdata) as f:
                userdata = f.readlines()
            userdata = ''.join(userdata)
        if fixed_ips:
            #ToDo: msenthil - An ugly hack, have to change the logic
            af_list = ['v6' if is_v6(x) else 'v4' for x in fixed_ips]
            if vn_ids:
                nics_list = [{'net-id': x, '%s-fixed-ip'%z: y}
                             for x, y, z in zip(vn_ids, fixed_ips, af_list)]
            elif port_ids:
                nics_list = [{'port-id': x, '%s-fixed-ip'%z: y}
                             for x, y, z in zip(port_ids, fixed_ips, af_list)]
        elif port_ids:
            nics_list = [{'port-id': x} for x in port_ids]
        elif vn_ids:
            nics_list = [{'net-id': x} for x in vn_ids]

        zone = zone + ":" + node_name
        self.obj.servers.create(name=vm_name, image=image,
                                security_groups=sg_ids,
                                flavor=flavor, nics=nics_list,
                                key_name=self.key, availability_zone=zone,
                                min_count=count, max_count=count, userdata=userdata)
        vm_objs = self.get_vm_list(name_pattern=vm_name,
                                   project_id=project_uuid)
        [vm_obj.get() for vm_obj in vm_objs]
        self.logger.info("VM (%s) created on node: (%s), Zone: (%s)" % (
                         str(vm_objs), node_name, zone))
        return vm_objs
    # end create_vm

    def add_security_group(self, vm_id, secgrp):
        self.obj.servers.add_security_group(vm_id, secgrp)

    def remove_security_group(self, vm_id, secgrp):
        self.obj.servers.remove_security_group(vm_id, secgrp)

    def get_vm_obj(self, vm_obj, wait_time=30):
        ''' It has been noticed that sometimes get() takes upto 20-30mins
            in error scenarios
            This method sets a timeout for the same
        '''
        with timeout(seconds=wait_time):
            try:
                vm_obj.get()
            except TimeoutError, e:
                self.logger.error('Timed out while getting VM %s detail' % (
                    vm_obj.name))
    # end get_vm_obj

    @retry(delay=5, tries=5)
    def get_vm_detail(self, vm_obj):
        try:
            self.get_vm_obj(vm_obj)
            if vm_obj.addresses == {} or vm_obj.status == 'BUILD':
                self.logger.debug('VM %s : Status=%s, Addresses : %s' % (
                    vm_obj.name, vm_obj.status, vm_obj.addresses))
                return False
            else:
                return True
        except novaException.ClientException:
            print 'Fatal Nova Exception'
            self.logger.exception('Exception while getting vm detail')
            return False
    # end def

    @retry(tries=1, delay=60)
    def _get_vm_ip(self, vm_obj, vn_name=None):
        ''' Returns a list of IPs for the VM in VN.

        '''
        vm_ip_dict = self.get_vm_ip_dict(vm_obj)
        if not vn_name:
            address = list()
            for ips in vm_ip_dict.itervalues():
                address.extend(ips)
            return (True, address)
        if vn_name in vm_ip_dict.keys() and vm_ip_dict[vn_name]:
            return (True, vm_ip_dict[vn_name])
        self.logger.error('VM does not seem to have got an IP in VN %s' % (vn_name))
        return (False, [])
    # end get_vm_ip

    def get_vm_ip(self, vm_obj, vn_name=None):
        return self._get_vm_ip(vm_obj, vn_name)[1]

    def get_vm_ip_dict(self, vm_obj):
        ''' Returns a dict of all IPs with key being VN name '''
        vm_obj.get()
        ip_dict={}
        for key,value in vm_obj.addresses.iteritems():
            ip_dict[key] = list()
            for dct in value:
                ip_dict[key].append(dct['addr'])
        return ip_dict

    def strip(self, uuid):
        return uuid.replace('-', '')

    def get_vm_list(self, name_pattern='', project_id=None):
        ''' Returns a list of VM objects currently present.

        '''
        final_vm_list = []
        vm_list = self.obj.servers.list(search_opts={"all_tenants": True})
        for vm_obj in vm_list:
            match_obj = re.match(r'%s' %
                                 name_pattern, vm_obj.name, re.M | re.I)
            if project_id:
                if match_obj and vm_obj.tenant_id == self.strip(project_id):
                    final_vm_list.append(vm_obj)
            else:
                if match_obj:
                    final_vm_list.append(vm_obj)
        # end for
        return final_vm_list

    # end get_vm_list

    def get_nova_host_of_vm(self, vm_obj):
        for hypervisor in self.get_nova_hypervisor_list():
            if vm_obj.__dict__['OS-EXT-SRV-ATTR:hypervisor_hostname'] is not None:
                if vm_obj.__dict__['OS-EXT-SRV-ATTR:hypervisor_hostname']\
                    == hypervisor.hypervisor_hostname:
                    if hypervisor.hypervisor_type == 'QEMU' or \
                        hypervisor.hypervisor_type == 'docker':
                        host_name = vm_obj.__dict__['OS-EXT-SRV-ATTR:host']
                        return host_name.split('.')[0]
                    if 'VMware' in hypervisor.hypervisor_type:
                        host_name = vcenter_libs.get_contrail_vm_by_vm_uuid(self.inputs,vm_obj.id)
                        return host_name.split('.')[0]
            else:
                if vm_obj.__dict__['OS-EXT-STS:vm_state'] == "error":
                    self.logger.error('VM %s has failed to come up' %vm_obj.name)
                    self.logger.error('Fault seen in nova show <vm-uuid> is:  %s' %vm_obj.__dict__['fault'])
                else:
                    self.logger.error('VM %s has failed to come up' %vm_obj.name)
                self.logger.error('Nova failed to get host of the VM')
    # end get_nova_host_of_vm

    def get_nova_hypervisor_list(self):
        #return self.obj.hypervisors.find().hypervisor_type
        return self.obj.hypervisors.list()
    #end

    def kill_remove_container(self, compute_host_ip, vm_id):
        get_container_id_cmd = "docker ps -f name=nova-%s | cut -d ' ' -f1"\
                               % vm_id
        with settings(
            host_string='%s@%s' %
                (self.inputs.host_data[compute_host_ip]['username'],
                 compute_host_ip),
            password=self.inputs.host_data[compute_host_ip]['password'],
            warn_only=True, abort_on_prompts=False):
                output = run(get_container_id_cmd)
                container_id = output.split("\n")[-1]
                run("docker kill %s" % container_id)
                run("docker rm -f  %s" % container_id)

    def delete_vm(self, vm_obj):
        compute_host = self.get_nova_host_of_vm(vm_obj)
        if self.get_compute_node_zone(compute_host) == 'nova/docker':
            # Workaround for the bug https://bugs.launchpad.net/nova-docker/+bug/1413371
            self.kill_remove_container(compute_host,
                                       vm_obj.id)
        vm_obj.delete()
    # end _delete_vm

    def get_key_file(self):
        return self.tmp_key_file

    def put_key_file_to_host(self, host_ip):
        username = self.inputs.host_data[self.cfgm_ip]['username']
        password = self.inputs.host_data[self.cfgm_ip]['password']
        with hide('everything'):
            with settings(host_string='%s@%s' % (
                    username, self.cfgm_ip),
                    password=password,
                    warn_only=True, abort_on_prompts=False):
                get('.ssh/id_rsa', '/tmp/')
                get('.ssh/id_rsa.pub', '/tmp/')
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (self.inputs.host_data[host_ip]['username'],
                                       host_ip), password=self.inputs.host_data[
                    host_ip]['password'],
                    warn_only=True, abort_on_prompts=False):
                # Put the key only is the test node and cfgm node in which key
                # is generated is different.
                if self.inputs.cfgm_ips[0] != host_ip:
                    put('/tmp/id_rsa', '/tmp/id_rsa')
                    put('/tmp/id_rsa.pub', '/tmp/id_rsa.pub')
                run('chmod 600 /tmp/id_rsa')
                self.tmp_key_file = '/tmp/id_rsa'
    @threadsafe_generator
    def get_compute_host(self):
        while True:
            nova_services = self.get_nova_services(binary='nova-compute')
            if not nova_services:
                self.logger.error('nova-compute service doesnt exist, check openstack-status')
                raise RuntimeError('nova-compute service doesnt exist')
            for compute_svc in nova_services:
                yield (compute_svc.host, compute_svc.zone)
    # end get_compute_host

    def wait_till_vm_is_active(self, vm_obj):
        return self.wait_till_vm_status(vm_obj, 'ACTIVE')
    # end wait_till_vm_is_active

    @retry(tries=30, delay=5)
    def wait_till_vm_status(self, vm_obj, status='ACTIVE'):
        try:
            vm_obj.get()
            if vm_obj.status == 'ACTIVE' or vm_obj.status == 'ERROR':
                self.logger.debug('VM %s is in %s state now' %
                                 (vm_obj, vm_obj.status))
                return (True,vm_obj.status)
            else:
                self.logger.debug('VM %s is still in %s state' %
                                  (vm_obj, vm_obj.status))
                return False
        except novaException.NotFound:
            self.logger.debug('VM console log not formed yet')
            return False
        except novaException.ClientException:
            self.logger.error('Fatal Nova Exception while getting VM detail')
            return False
    # end wait_till_vm_status

    @retry(tries=40, delay=2)
    def wait_till_vm_is_up(self, vm_obj):
        try:
            vm_obj.get()

            for hyper in self.obj.hypervisors.list():
                if hyper.hypervisor_hostname == getattr(vm_obj,
                     'OS-EXT-SRV-ATTR:hypervisor_hostname') and ((u'VMware' in
                         hyper.hypervisor_type) or (u'docker' in hyper.hypervisor_type)):
                   # can't get console logs for VM in VMware nodes
                   # https://bugs.launchpad.net/nova/+bug/1199754
                   return self.wait_till_vm_is_active(vm_obj)

            if 'login:' in vm_obj.get_console_output():
                self.logger.debug('VM has booted up..')
                return True
            else:
                self.logger.debug('VM not yet booted fully .. ')
                return False
        except novaException.NotFound:
            self.logger.debug('VM console log not formed yet')
            return False
        except novaException.ClientException:
            self.logger.error('Fatal Nova Exception while getting VM detail')
            return False
    # end wait_till_vm_is_up

    def get_vm_console_output(self, vm_obj):
        try:
            vm_obj.get()
            return  vm_obj.get_console_output()
        except novaException.NotFound:
            self.logger.debug('VM console log not formed yet')
            return None
        except novaException.ClientException:
            self.logger.error('Fatal Nova Exception while getting VM detail')
            return None
    # end get_vm_console_output


    def get_vm_in_nova_db(self, vm_obj, node_ip):
        issue_cmd = 'mysql -u root --password=%s -e \'use nova; select vm_state, uuid, task_state from instances where uuid=\"%s\" ; \' ' % (
            self.inputs.get_mysql_token(), vm_obj.id)
        username = self.inputs.host_data[node_ip]['username']
        password = self.inputs.host_data[node_ip]['password']
        output = self.inputs.run_cmd_on_server(
            server_ip=node_ip, issue_cmd=issue_cmd, username=username, password=password)
        return output
    # end get_vm_in_nova_db

    @retry(tries=10, delay=5)
    def is_vm_deleted_in_nova_db(self, vm_obj, node_ip):
        output = self.get_vm_in_nova_db(vm_obj, node_ip)
        if 'deleted' in output and 'NULL' in output:
            self.logger.debug('VM %s is removed in Nova DB' % (vm_obj.name))
            return True
        else:
            self.logger.warn('VM %s is still found in Nova DB : %s' %
                             (vm_obj.name, output))
            return False
    # end is_vm_in_nova_db

    def get_compute_node_zone(self, node_name):
        for zone in self.hosts_dict:
            if node_name in self.hosts_dict[zone]:
                return zone

    def get_image_name_for_zone(self, image_name='ubuntu', zone='nova'):
        image_info = self.images_info[image_name]
        if zone == 'nova/docker':
            return image_info['name_docker']
        else:
            return image_name

    def lb_node_zone(self, zone=None):
        if zone or self.hypervisor_type:
            if (not zone) and self.hypervisor_type:
                if self.hypervisor_type == 'docker':
                    zone = 'nova/docker'
                elif self.hypervisor_type == 'qemu':
                    zone = 'nova'
                else:
                    self.logger.warn("Test on hypervisor type %s not supported yet, \
                                        running test on qemu hypervisor"
                                        % (self.hypervisor_type))
                    zone = 'nova'
            if zone not in self.zones:
                raise RuntimeError("Zone %s is not available" % zone)
            if not len(self.hosts_dict[zone]):
                raise RuntimeError("Zone %s doesnt have any computes" % zone)

            while(True):
                (node, node_zone)  = next(self.compute_nodes)
                if node_zone == zone:
                    node_name = node
                    break
        else:
            (node_name, zone)  = next(self.compute_nodes)

        return (zone, node_name)

# end NovaHelper
