import sys
import time
import unittest
import logging
import os
from fabric.api import env
from fabric.api import run
from fabric.context_managers import settings
from fabric.operations import get, put
from netaddr import *
import json
import re
import xml.etree.ElementTree as ET
import socket

#import util

# sys.path.insert(0,'/home/stack/stuff/scripts')
from quantumclient.quantum import client
from quantumclient.client import HTTPClient
from quantumclient.common import exceptions
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
from vnc_api.vnc_api import *
from util import *


class ContrailSetup:

    def __init__(self, username, password, provFile, single_node, key, logScenario='Sanity'):
        self.username = username
        self.password = password
        self.provFile = provFile
        self.logScenario = logScenario
        self.single_node = single_node
        self.vn1 = ''
        self.tmpFile = '/tmp/http_data'
        self.quantumPort = 9696
        self.apiPort = '8082'
        self.bgpPort = '8083'
        self.agentPort = '8085'
        self.key = key
        if single_node:
            self.prov_data = self._create_prov_data()
        else:
            self.prov_data = self._read_provFile()
        self.ip = self.cfgmIP
        self.openstack_ip = self.openstackIP
        self.setup()

    def setup(self):
        httpclient = None
        try:
            httpclient = HTTPClient(username='admin',
                                    tenant_name='admin',
                                    password='contrail123',
                                    # region_name=self._region_name,
                                    auth_url='http://' + self.openstack_ip + ':5000/v2.0')
            httpclient.authenticate()
        except exceptions.QuantumClientException:
            logging.exception('Exception while authenticating with %s' %
                              (self.ip))
        #OS_URL = httpclient.endpoint_url
        OS_URL = 'http://%s:%s/' % (self.ip, self.quantumPort)
        OS_TOKEN = httpclient.auth_token
        self._quantum = client.Client(
            '2.0', endpoint_url=OS_URL, token=OS_TOKEN)
        self._nc = mynovaclient.Client(
            '2', username='admin', project_id='admin', api_key='contrail123',
            auth_url='http://' + self.openstack_ip + ':5000/v2.0')
        self._vnc_lib = VncApi('user1', 'password1', 'default-domain',
                               self.ip, self.apiPort, '/')
        self.proj_fq_name = ['default-domain', 'admin']
        self.proj_obj = self._vnc_lib.project_read(fq_name=self.proj_fq_name)
        self.create_keypair(self.key)

    # end setup

    def create_keypair(self, key_name):
        if key_name in [str(key.id) for key in self._nc.keypairs.list()]:
            self._nc.keypairs.delete(key_name)
        rsa_pub_file = os.environ.get('HOME') + '/.ssh/id_rsa.pub'
        rsa_pub_arg = os.environ.get('HOME') + '/.ssh/id_rsa'
        if not os.path.isfile(rsa_pub_file):
            os.system('ssh-keygen -f %s -t rsa -N \'\' -o' % (rsa_pub_arg))
        pub_key = open('/root/.ssh/id_rsa.pub', 'r').read()
        self._nc.keypairs.create(key_name, public_key=pub_key)

    def get_host_ip_of_vm(self, vmUUID):
        for host in self.hostIPs:
            link = 'http://' + host + ':' + \
                self.agentPort + '/Snh_ItfReq?name= '
            output = web_invoke(link)
            if vmUUID in str(output):
                return host
        return None

    # end get_host_of_vm

    def put_key_file_to_host(self, host_ip):
        with settings(host_string='%s@%s' % (self.usernames[host_ip], host_ip),
                      password=self.passwords[host_ip], warn_only=True, abort_on_prompts=False):
            put('~/.ssh/id_rsa', '/tmp/id_rsa')
            run('chmod 600 /tmp/id_rsa')
            self.tmp_key_file = '/tmp/id_rsa'

    def ping_to_ip(self, vmObj, destIP, username, password, size=56, count=5):
        logger = logging.getLogger(self.logScenario)
        output = ''
        try:
            host = self.get_host_ip_of_vm(vmObj.id)
            if host is None:
                logger.error('Cannot get Host IP of VM from agent!')
#                return 0
            host_username = self.usernames[host]
            host_password = self.passwords[host]
            local_ip = self.get_local_ip_of_vm(host, vmObj.id)
            vmPassword = 'cubswin:)'
            logger.info('Pinging from ' + str(vmObj) + ' to ' +
                        destIP + ' with size(bytes)' + str(size) + '..... ')
            env.disable_known_hosts = True
            # Copy id file from cfgm-ip to compute node
            self.put_key_file_to_host(host)
            with settings(host_string='%s@%s' % (host_username, host), password=host_password, warn_only=True, abort_on_prompts=False):
#                env.shell='/bin/sh -l -c '
#                with settings(host_string='cirros@%s' %( local_ip ), password='cubswin:)', warn_only=True, abort_on_prompts=False ):
#                    output=run('ping -s '+ str(size)+ ' -c '+ str(count)+' '+destIP)
                output = run('ssh -o StrictHostKeyChecking=no -i ' + self.tmp_key_file + ' root@' +
                             local_ip + ' \"ping -s ' + str(size) + ' -c ' + str(count) + ' ' + destIP + '\"')

                logger.info(output)
        except Exception, e:
            logger.exception('Error occured during ping operation ' + str(e))
            return 0

        expected_result = ' 0% packet loss'
        if expected_result in output:
            return 1
        else:
            return 0
    # end ping_to_ip

    # return a tuple similar to (enabled, active, running)
    def get_service_status(self, server_ip, service_name, username='root',
                           password='contrail123'):
        logger = logging.getLogger(self.logScenario)
        state = None
        active_str1 = None
        active_str2 = None
        with settings(
            host_string=server_ip, username=username, password=password,
                warn_only=True, abort_on_prompts=False):
            output = run('systemctl status %s.service | head ' %
                         (service_name))
            logger.debug(output)
            if service_name not in output:
                return (None, None, None)
            match_obj1 = re.search(
                r'Active: (.*) \((.*)\)', output, re.M | re.I)
            match_obj2 = re.search(r'Loaded.* (.*)\)', output, re.M | re.I)
            if match_obj1:
                active_str1 = match_obj1.group(1)
                active_str2 = match_obj1.group(2)
            if match_obj2:
                state = match_obj2.group(1)
        return (state, active_str1, active_str2)
    # end get_service_status

    def get_local_ip_of_vm(self, hostIP, vmUUID):
        logger = logging.getLogger(self.logScenario)
        try:
            output = os.system('wget http://' + hostIP +
                               ':8085/Snh_ItfReq?name= -O ' + self.tmpFile)
            xml_tree = ET.parse(self.tmpFile)
            xml_root = xml_tree.getroot()
            xml_elem = xml_root.find('itf_list')
            for row in xml_elem.getiterator('ItfSandeshData'):
                vm_id = row.find('vm_uuid')
                if vm_id is not None and vm_id.text == vmUUID:
                    return row.find('mdata_ip_addr').text
        except Exception, e:
            logger.exception('Error while getting local 169.x IP of VM')
            return ''
    # end get_local_ip_of_vm

    def _read_provFile(self):
        prov_file = open(self.provFile, 'r')
        prov_data = prov_file.read()
        json_data = json.loads(prov_data)
        self.openstackIP = ''
        self.cfgmIP = ''
        self.computeIPs = []
        self.bgpIPs = []
        self.hostIPs = []
        self.usernames = {}
        self.passwords = {}
        for host in json_data['hosts']:
            hostIP = str(IPNetwork(host['ip']).ip)
            self.hostIPs.append(hostIP)
            roles = host["roles"]
            self.usernames[hostIP] = host['username']
            self.passwords[hostIP] = host['password']
            for role in roles:
                if role['type'] == 'openstack':
                    self.openstackIP = hostIP
                    self.hostname = host['name']
                if role['type'] == 'cfgm':
                    self.cfgmIP = hostIP
                    self.masterhost = self.cfgmIP
                    self.hostname = host['name']
                if role['type'] == 'compute':
                    self.computeIPs.append(hostIP)
                if role['type'] == 'bgp':
                    self.bgpIPs.append(hostIP)
                if role['type'] == 'collector':
                    self.collectorIP = hostIP
                if role['type'] == 'webui':
                    self.webuiIP = hostIP
            # end for
        # end for
        return json.loads(prov_data)
    # end _read_provision_data

    def _create_prov_data(self):
        ''' Creates json data for a single node only.

        '''
        single_node = self.single_node
        self.cfgmIP = single_node
        self.bgpIPs = [single_node, single_node]
        self.computeIPs = [single_node]
        self.hostIPs = [single_node]
        self.collectorIP = single_node
        self.webuiIP = single_node
        self.usernames = {single_node: self.username}
        self.passwords = {single_node:  self.password}
        json_data = {}
        hostname = socket.gethostbyaddr(single_node)[0]
        self.hostname = hostname
        json_data['hosts'] = [{
            'ip': single_node,
            'name': hostname,
            'username': self.username,
            'password': self.password,
            'roles': [
                {"params": {"collector": hostname, "cfgm": hostname},
                 "type": "bgp"},
                {"params": {"bgp": [hostname, hostname], "cfgm":
                            hostname, "collector": hostname}, "type": "compute"},
                {"params": {"collector": hostname}, "type": "cfgm"},
                {"params": {"cfgm": hostname}, "type": "webui"},
                {"type": "collector"}
            ]
        }]
        return json_data
    # end _create_prov_data

    def is_vn_in_quantum(self, vn):
        logger = logging.getLogger(self.logScenario)
        is_present = 0
        try:
            net_rsp = self._quantum.show_network(vn['network']['id'])
            if net_rsp['network']['name']:
                is_present = 1
                logging.debug(str(vn) + ' is seen in Quantum')
            else:
                is_present = 0
        except exceptions.QuantumClientException:
            is_present = 0
            logging.exception('Exception while viewing quantum VN detail')
            return is_present
        # end try
        return is_present

    def is_subnet_present(self, vn, subnetUUID):
        is_present = 0
        try:
            net_rsp = self._quantum.show_network(vn['network']['id'])
            if subnetUUID in net_rsp['network']['subnets']:
                is_present = 1
            else:
                is_subnet = 0
        except exceptions.QuantumClientException:
            is_present = 0
        return is_present

    def is_server_present(self, vmName):
        logger = logging.getLogger(self.logScenario)
        is_present = 0
        try:
            vm = self._nc.servers.find(name=vmName)
            if vm in self._nc.servers.list():
                is_present = 1
            else:
                is_present = 0
        except Exception:
            logging.exception(
                'Exception occured while checking if server is present')
            is_present = 0
        return is_present
    # end is_server_present

    def create_vn(self, vnName, vnSubnet):
        logger = logging.getLogger(self.logScenario)
        try:
            logger.debug('VN to be created : ' +
                         vnName + ', Subnet ' + vnSubnet)
            net_req = {'name': vnName}
            net_rsp = self._quantum.create_network({'network': net_req})
            logger.debug('Response for create_network : ' + repr(net_rsp))
            vn = net_rsp
            net_id = net_rsp['network']['id']
            net1_fq_name = net_rsp['network']['contrail:fq_name']
            net_fq_name_str = ':'.join(net1_fq_name)
    #        self.vn1=VirtualNetwork(vnName,net_id)
    #        self.vn1.fqName=net_fq_name_str

    #        self.vn1.subnet=vnSubnet
            subnet = unicode(vnSubnet)
            net_rsp = self._create_subnet(unicode(vnSubnet), net_id)

            return self._quantum.show_network(network=net_id)
        except exceptions.QuantumClientException:
            logger.exception(
                'Some Exception occured while creating Virtual Network')
            return None
    # end create_vn

    def delete_vn(self, vnName):
        logger = logging.getLogger(self.logScenario)
        result = 1
        try:
            net_rsp = self._quantum.list_networks()
            logger.debug('Response for listing VNs :' + repr(net_rsp))
            for (x, y) in [(network['name'], network['id']) for network in net_rsp['networks']]:
                if vnName == x:
                    net_id = y
                    break
            net_rsp = self._quantum.delete_network(net_id)
            logger.debug('Response for deleting vn ' +
                         vnName + ' : ' + net_rsp)
        except exceptions.QuantumClientException, e:
            logger.exception(
                'Some Quantum Exception Occured while deleting Virtual Network')
            if "internal server error" in str(e):
                return 0
        return result
    # end delete_vn

    def create_policy(self, policy_dict):
        logger = logging.getLogger(self.logScenario)

        source_port = policy_dict['source_port']
        dest_port = policy_dict['dest_port']
        if policy_dict['source_port'] == 'any':
            source_port = [PortType(-1, -1)]
        if policy_dict['dest_port'] == 'any':
            dest_port = [PortType(-1, -1)]

#        np_rules = [PolicyRuleType(None, '<>', policy_dict['action'] , policy_dict['protocol'],
#            [AddressType(virtual_network = 'local')], source_port, policy_dict['source_subnet'],
#            [AddressType(virtual_network = policy_dict['dest_vn'])], dest_port, policy_dict['dest_subnet'])]

        net1_fq_name = 'default-domain:admin:' + policy_dict['source_vn']
        net2_fq_name = 'default-domain:admin:' + policy_dict['dest_vn']
        np_rules = [PolicyRuleType(
            direction='<>', simple_action='pass', protocol='any',
            src_addresses=[AddressType(virtual_network=net1_fq_name)], src_ports=[PortType(-1, -1)],
            dst_addresses=[AddressType(virtual_network=net2_fq_name)], dst_ports=[PortType(-1, -1)])]

        logger.debug("Policy dict is " + str(policy_dict))
        pol_entries = PolicyEntriesType(np_rules)
        pol_entries_dict = \
            json.loads(json.dumps(pol_entries,
                                  default=lambda o: {k: v for k, v in o.__dict__.iteritems()}))
        policy_req = {'name': policy_dict['name'],
                      'entries': pol_entries_dict}

        try:
            policy_rsp = self._quantum.create_policy({'policy': policy_req})
            logger.debug("Policy Response " + str(policy_rsp))
            return policy_rsp
        except exceptions.QuantumClientException:
            logger.exception('Exception occured while creating a policy')
            return None
    # end create_policy

    def delete_policy(self, policy_name):
        logger = logging.getLogger(self.logScenario)
        try:
            pol_list = self._quantum.list_policys()
            for policy in pol_list['policys']:
                if policy['name'] == policy_name:
                    self._quantum.delete_policy(policy['id'])
                    break
        except exceptions.QuantumClientException:
            logger.exception(
                'Some Quantum Exception Occured while deleting Virtual Network')

    # end delete_policy

    def bind_policy(self, vn_id, policy_fq_name):
        logger = logging.getLogger(self.logScenario)
        net_req = {'contrail:policys': [policy_fq_name]}
        net_rsp = self._quantum.update_network(vn_id, {'network': net_req})
        logger.debug('Response for mapping policy with vn ' + str(net_rsp))
        return net_rsp
    # end bind_policy

    def create_and_bind_policy(self, vn_id, policy_dict):
        logger = logging.getLogger(self.logScenario)
        if policy_dict['source_port'] == 'any':
            source_port = [PortType(-1, -1)]
        if policy_dict['dest_port'] == 'any':
            dest_port = [PortType(-1, -1)]
        policy = self.create_policy(policy_dict)
        if policy is None:
            return None
        policy_fq_name = policy['policy']['fq_name']
        resp = self.bind_policy(vn_id, policy_fq_name)
        return resp
    # end create_and_bind_policy

    def get_vn_id(self, vnName):
        logger = logging.getLogger(self.logScenario)
        net_id = ''
        net_rsp = self._quantum.list_networks()
        logger.debug('Response for quantum list_networks: ' + repr(net_rsp))
        for (x, y) in [(network['name'], network['id']) for network in net_rsp['networks']]:
            if vnName == x:
                net_id = y
                break
        return net_id
    # end get_vn_id

    def create_vm(self, vmName, vnName, image_name='cirros-0.3.0-x86_64-uec'):
        logger = logging.getLogger(self.logScenario)
        flavor = self._nc.flavors.find(ram=512)
        image = ''
        try:
            image = self._nc.images.find(name=image_name)
        except novaException.NotFound:
            self.get_image(image_name=image_name)
            image = self._nc.images.find(name=image_name)
        networkId = self.get_vn_id(vnName)
#        server = self._nc.servers.create(name=vmName, image=image, flavor=flavor,
#                                              nics=[{'net-id':networkId}])
        server = self._nc.servers.create(
            name=vmName, image=image, flavor=flavor,
            nics=[{'net-id': networkId}], key_name=self.key)
        server.get()
#        import pdb; pdb.set_trace()
        logger.debug('Created VM : ' + str(server))
        return server
    # end create_vm

    @retry(delay=10)
    def get_vm_detail(self, vm_obj):
        try:
            vm_obj.get()
            if vm_obj.addresses == {}:
                return False
            else:
                return True
        except novaException.ClientException:
            logger.debug('Fatal Nova Exception')
            return False
    # end def

    @retry(tries=7, delay=30)
    def wait_till_vm_up(self, vm_obj):
        logger = logging.getLogger(self.logScenario)
        try:
            time.sleep(5)
            vm_obj.get()
            if vm_obj.get_console_output().endswith('login: '):
                logger.debug('VM has booted up..')
                return True
            else:
                logger.debug('VM not yet up..')
                return False
        except novaException.NotFound:
            logger.debug('VM console log not formed yet')
            return False
        except novaException.ClientException:
            logger.debug('Fatal Nova Exception')
            return False

    def _create_subnet(self, cidr, net_id, ipam_fq_name=None):
        logger = logging.getLogger(self.logScenario)
        if not ipam_fq_name:
            ipam_fq_name = NetworkIpam().get_fq_name()

        subnet_req = {'network_id': net_id,
                      'cidr': cidr,
                      'ip_version': 4,
                      'contrail:ipam_fq_name': ipam_fq_name}
        subnet_rsp = self._quantum.create_subnet({'subnet': subnet_req})
        logger.debug('Response for create_subnet : ' + repr(subnet_rsp))
    # end _create_subnet

    def create_floatingip_pool(self, fip_pool_name, net_id):
        logger = logging.getLogger(self.logScenario)
        logger.debug('Creating Floating IP pool in API Server')

        # create floating ip pool from public network
        pub_vn_obj = self._vnc_lib.virtual_network_read(id=net_id)
        fip_pool_obj = FloatingIpPool(fip_pool_name, pub_vn_obj)
        self._vnc_lib.floating_ip_pool_create(fip_pool_obj)

        # allow current project to pick from pool
        self.proj_obj.add_floating_ip_pool(fip_pool_obj)
        self._vnc_lib.project_update(self.proj_obj)
        return fip_pool_obj

    # end create_floatingip_pool

    def delete_floatingip_pool(self, fip_pool_id):
        logger = logging.getLogger(self.logScenario)
        logger.debug('Deleting Floating IP pool in API Server')
        fip_pool_obj = self._vnc_lib.floating_ip_pool_read(id=fip_pool_id)
        self.proj_obj.del_floating_ip_pool(fip_pool_obj)
        self._vnc_lib.project_update(self.proj_obj)
        self._vnc_lib.floating_ip_pool_delete(id=fip_pool_id)
    # end delete_floatingip_pool

    def create_floatingip(self, count=1):
        logger = logging.getLogger(self.logScenario)
        logger.debug('Creating floating IP in quantum')

        # list pools available for current project
        fip_pool_nets = self._quantum.list_networks(external=True)
        fip_pool_net_id = fip_pool_nets['networks'][0]['id']

        # allocate 'count' number of floating ips
        fip_dicts = []
        for i in range(count):
            fip_req = {'floatingip': {'floating_network_id': fip_pool_net_id,
                                      'tenant_id': self.proj_obj.uuid}}
            fip_resp = self._quantum.create_floatingip(fip_req)
            fip_dicts.append(fip_resp['floatingip'])

        # list floating ips available for current project
        fip_resp = self._quantum.list_floatingips(
            tenant_id=self.proj_obj.uuid)
        logger.debug("Floating IP list: " + str(fip_resp))
        return fip_resp
    # end create_floatingip

    def delete_floatingip(self, fip_obj_list):
        logger = logging.getLogger(self.logScenario)
        logger.debug('Deleting floating IP in quantum')

        fip_pool_nets = self._quantum.list_networks(external=True)
        fip_pool_net_id = fip_pool_nets['networks'][0]['id']
        for i in fip_obj_list['floatingips']:
            index = fip_obj_list['floatingips'].index(i)
            self._quantum.delete_floatingip(
                fip_obj_list['floatingips'][index]['id'])

    # end delete_floatingip

    def get_port_id(self, vm_id):
        logger = logging.getLogger(self.logScenario)
        try:
            port_rsp = self._quantum.list_ports(device_id=[vm_id])
            port_id = port_rsp['ports'][0]['id']
            return port_id
        except Exception, e:
            logger.exception('Error occured while getting port-id of a VM ')
            return None
    # end

    def assoc_floatingip(self, fip_id, vm_id):
        update_dict = {}
        update_dict['port_id'] = self.get_port_id(vm_id)
        if update_dict['port_id']:
            fip_resp = self._quantum.update_floatingip(
                fip_id, {'floatingip': update_dict})
            return fip_resp
        else:
            return None
    # end

    def disassoc_floatingip(self, fip_id):
        update_dict = {}
        update_dict['port_id'] = None
        fip_resp = self._quantum.update_floatingip(
            fip_id, {'floatingip': update_dict})
        return fip_resp
    # end

    def is_vn_in_bgp(self, vn_name):
        logger = logging.getLogger(self.logScenario)
        vn_fqdn = self.get_fqdn(vn_name)
        for host in self.bgpIPs:
            link = 'http://' + host + ':' + self.bgpPort + \
                '/Snh_ShowRoutingInstanceReq?name='
            output = web_invoke(link)
            if output and vn_fqdn in output:
                logger.debug('VN ' + vn_fqdn +
                             ' found in control-node of ' + host)
                return 1
        logger.debug('VN ' + vn_fqdn + ' is not found in any control-nodes')
        return 0
    # end is_vn_in_bgp

    def is_vn_in_agent(self, vn_name):
        logger = logging.getLogger(self.logScenario)
        vn_fqdn = self.get_fqdn(vn_name)
        vrf = vn_fqdn + ':' + vn_name
        for host in self.hostIPs:
            link = 'http://' + host + ':' + self.agentPort + \
                '/Snh_VrfListReq?name=' + vn_fqdn
            output = web_invoke(link)
            if output and vn_fqdn in output:
                logger.debug('VN ' + vn_fqdn + ' found in agent of ' + host)
                return 1
        logger.debug('VN ' + vn_fqdn + ' is not found in any agents')
        return 0
    # end is_vn_in_bgp

    def get_fqdn(self, name):
        return 'default-domain:admin:' + name
    # end get_fqdn

    def get_image(self, image_name):
        with settings(
            host_string=self.ip, username=self.username, password=self.password,
                warn_only=True, abort_on_prompts=False):
            if image_name == 'cirros-0.3.0-x86_64-uec':
                run('source /etc/contrail/openstackrc')
                run('cd /tmp ; sudo rm -f /tmp/cirros-0.3.0-x86_64* ; \
			wget http://launchpad.net/cirros/trunk/0.3.0/+download/cirros-0.3.0-x86_64-uec.tar.gz')
                run('tar xvzf /tmp/cirros-0.3.0-x86_64-uec.tar.gz -C /tmp/')
                run('source /etc/contrail/openstackrc && glance add name=cirros-0.3.0-x86_64-kernel is_public=true ' +
                    'container_format=aki disk_format=aki < /tmp/cirros-0.3.0-x86_64-vmlinuz')
                run('source /etc/contrail/openstackrc && glance add name=cirros-0.3.0-x86_64-ramdisk is_public=true ' +
                    ' container_format=ari disk_format=ari < /tmp/cirros-0.3.0-x86_64-initrd')
                run('source /etc/contrail/openstackrc && glance add name=' + image_name + ' is_public=true ' +
                    'container_format=ami disk_format=ami ' +
                    '\"kernel_id=$(glance index | awk \'/cirros-0.3.0-x86_64-kernel/ {print $1}\')\" ' +
                    '\"ramdisk_id=$(glance index | awk \'/cirros-0.3.0-x86_64-ramdisk/ {print $1}\')\" ' +
                    ' < <(zcat --force /tmp/cirros-0.3.0-x86_64-blank.img)')
    # end get_image

    def get_cfgm_hostname(self):
        return self.hostname
    # end def

    def get_compute_host(self):
        while(1):
            for i in self.computeIPs:
                yield socket.gethostbyaddr(i)[0]
    # end get_next_compute_host
# end class ContrailSetup
