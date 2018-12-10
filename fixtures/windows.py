import subprocess
import random
from winrm.protocol import Protocol
from orchestrator import Orchestrator, OrchestratorAuth
from vnc_api.vnc_api import VncApi
from tcutils.util import retry

class WindowsOrchestrator(Orchestrator):

    def __init__(self, inputs, vnc=None, logger=None):
		
        super(WindowsOrchestrator, self).__init__(inputs, vnc, logger)
        self._inputs = inputs
        self._vnc = vnc
        self._log = logger

    def _run_docker_cmd_on_remote_windows(self, target_host, command, powershell=False,
    	username='Administrator', password='Contrail123!', transport='ntlm'):

    	self.logger.info("Executing the following docker cmd")
    	self.logger.info(command)
    	p = Protocol(
              endpoint='http://{}:5985/wsman'.format(target_host),
              transport=transport,
              username=username,
              password=password, 
              server_cert_validation='ignore')
        shell_id = p.open_shell()
        if powershell:
        	command = 'powershell.exe ' + str(command)
        if "docker" in command:
            command_id = p.run_command(shell_id, "docker", command.split(" ")[1:])
        else:
        	command_id = p.run_command(shell_id, command)
        std_out, std_err, status_code = p.get_command_output(shell_id, command_id)
        if status_code != 0:
            assert False, ("Error while creating network {} on windows compute {}." 
                    "Error is {}".format(network, target_host, std_err))
        p.cleanup_command(shell_id, command_id)
        print(std_out, status_code)
        p.close_shell(shell_id)
        self.logger.info("Docker cmd successful")
        return std_out, std_err, status_code

    def _create_docker_on_windows(self, network, docker_name, target_host, image, username='Administrator',
    	password='Contrail123!', transport='ntlm'):

    	docker_create_command = "docker run -id --network {} --name {} {} powershell".format(
    		network,
    		docker_name,
    		image)
    	std_out, std_err, status_code = self._run_docker_cmd_on_remote_windows(
    		target_host=target_host,
    		command=docker_create_command,
    		username=username,
    		password=password,
    		transport=transport)
    	return std_out, std_err, status_code, docker_name

    def _create_docker_network(self, network, target_host, username='Administrator',
    	password='Contrail123!', transport='ntlm'):

    	network_create_cmd = "docker network create --ipam-driver windows -d Contrail \
    	    --opt tenant=admin --opt network={} {}".format(network, network)
    	std_out, std_err, status_code = self._run_docker_cmd_on_remote_windows(
    		target_host=target_host,
    		command=network_create_cmd,
    		username=username,
    		password=password,
    		transport=transport)
    	return std_out, std_err, status_code, network

    def create_policy(self, policy_name, rules_list):

    	self.logger.info("Creating new policy")
    	policy_fixture = self.useFixture(PolicyFixture(
            policy_name,
            rules_list,
            self.inputs,
            self.connections,
            api = 'api'))
    	policy_response = policy_fixture.policy_obj.uuid
    	self.logger.debug("Policy Creation Response " + str(policy_response))
    	self.logger.info("policy %s is created with rules using API Server" %
                         policy_name)

    def create_vn(self, vn_name='', vn_subnet=''):
   
        self.logger.info("Creating network in controller")
    	vn_subnet_cidr = get_random_cidr()
        vn_subnet = vn_subnet or [{'cidr': vn_subnet_cidr}]
        vn_name = vn_name or get_random_name(self.project_name)
        vn_obj = self.useFixture(
            VNFixture(
                project_name=self.project_name,
                connections=self.connections,
                vn_name=vn_name,
                subnet=vn_subnet,
                inputs=self.inputs))

    def create_vm(self, vm_name, vn_objs, image_name='microsoft/windowsservercore',
    	target_host_username='Administrator', target_host_transport='ntlm', target_host_password='Contrail123!',
    	count=1, zone=None, node_name=None, **kwargs):
    	
#	vn_list = self.get_vn_list()
	#For now, taking the first network from vn_objs. Change this later as required
	network_name = vn_objs[0].name	
	if not node_name:	
	    #Taking first compute node for now. Change this later
	    virtual_routers = self.get_virtual_routers_list()

	    self.logger.info("Selecting a compute node in a random fashion")
	    compute_node = random.choice(virtual_routers)
	    compute_node_data = self.read_virtual_routers_data(
		fq_name=compute_node['fq_name'])
	    node_name = compute_node_data._virtual_router_ip_address
	self.logger.info("Create virtual network on the windows compute node")
    	self._create_docker_network(
    		network=network_name,
    		target_host=node_name)

    	vm_name = vm_name or get_random_name(self.project_name)
    	vm_cmd_output = self._create_docker_on_windows(
        	network=network_name,
        	docker_name=vm_name,
        	target_host=node_name,
        	image=image_name,
        	username=target_host_username,
        	password=target_host_password,
        	transport=target_host_transport)
	vm_name = vm_cmd_output[3]
	vm_id = vm_cmd_output[0].strip()
	return [VM(name=vm_name, vm_id=vm_id)]

    def _is_process_running_on_host(self, process_name, target_host,
    	target_host_username='Administrator', target_host_transport='ntlm', target_host_password='Contrail123!'):

    	command = 'Get-Service '+str(process_name)
    	std_out, std_err, status_code = self._run_docker_cmd_on_remote_windows(
    		target_host=target_host,
    		command=command,
    		username=username,
    		password=password,
    		transport=transport,
    		powershell=True)
    	if 'Running' in std_out:
    		return True
    	return False

    def get_image_account(self, image_name):
        '''Returns username, password for the image.'''
	#returning None ince this username password is not required for windows containers
        return None,None

    def get_image_name_for_zone(self, image_name='ubuntu', zone='nova'):
        '''Get image name compatible with zone '''
        pass

    def get_flavor(self, flavor):
        '''Installs and Returns Flavor ID.'''
        pass

    def get_default_image_flavor(self, image_name):
        '''Returns Flavor ID for an image.'''
        pass

    def get_image(self, image):
        '''Installs and Returns Image ID.'''
        pass

    def get_hosts(self, zone=None):
        '''Returns a list of computes.'''
        pass

    def get_zones(self):
        '''Returns a list of zones/clusters into which computes are grouped.'''
        pass

    def delete_vm(self, vm_obj, **kwargs):
	pass

    def get_host_of_vm(self, vm_obj, **kwargs):
        '''Returns name of the compute, on which the VM was created.'''
        pass

    def get_networks_of_vm(self, vm_obj, **kwargs):
        '''Returns names of the networks, associated with the VM.'''
        pass

    def get_vm_if_present(self, vm_name, **kwargs):
        pass

    def get_vm_by_id(self, vm_id, **kwargs):
        pass
 
    def get_vm_list(self, name_pattern='', **kwargs):
        '''Returns a list of VM object matching pattern.'''
        return None
   
    def get_vm_detail(self, vm_obj, **kwargs):
        '''Refreshes VM object.'''
        return True

    def get_vm_ip(self, vm_obj, vn_name, **kwargs):
        '''Returns a list of IP of VM in VN.'''
        pass

    def is_vm_deleted(self, vm_obj, **kwargs):
        pass

    def wait_till_vm_is_active(self, vm_obj, **kwargs):
        return self.wait_till_vm_status(vm_obj, 'ACTIVE')

    @retry(tries=60, delay=5)
    def wait_till_vm_status(self, vm_obj, status, **kwargs):
        try:
            vm_obj.get()
            if vm_obj.status == status or vm_obj.status == 'ERROR':
                self.logger.debug('VM %s is in %s state now' %
                                 (vm_obj, vm_obj.status))
                return (True,vm_obj.status)
            else:
                self.logger.debug('VM %s is still in %s state, Expected: %s' %
                                  (vm_obj, vm_obj.status, status))
                return False
        except novaException.NotFound:
            self.logger.debug('VM console log not formed yet')
            return False
        except novaException.ClientException:
            self.logger.error('Fatal Nova Exception while getting VM detail')
            return False

    def get_console_output(self, vm_obj, **kwargs):
        pass

    def get_key_file(self):
        '''Returns the key file path.'''
        pass

    def put_key_file_to_host(self, host_ip):
        '''Copy RSA key to host.'''
        pass

    def create_vn(self, vn_name, subnets, **kwargs):
        
	pass

    def delete_vn(self, vn_obj, **kwargs):
        
	return self.vnc_h.delete_vn_api(vn_obj)

    def get_vn_obj_if_present(self, vn_name, **kwargs):
        
	for network in self._vnc.virtual_networks_list()['virtual-networks']:
	    if vn_name in network['fq_name']:
		pass
	self._vnc.virtual_networks_list()

    def get_vn_name(self, vn_obj, **kwargs):

        return vn_obj.name

    def get_vn_id(self, vn_obj, **kwargs):
        
	if not vn_obj.uuid:
            vn_obj.get()
        return vn_obj.uuid

    def get_vn_obj_from_id(self, vn_id):

	obj = self._vnc.virtual_network_read(id=vn_id)
	return obj
        #return self.get_vn_obj_if_present(obj.name)

    def get_vn_list(self):

	return self._vnc.virtual_networks_list()['virtual-networks']

    def get_virtual_routers_list(self):

	return self._vnc.virtual_routers_list()['virtual-routers']

    def read_virtual_routers_data(self, fq_name):

	return self._vnc.virtual_router_read(fq_name=fq_name)

 
class WindowsAuth(OrchestratorAuth):

    def __init__(self, user, passwd, project_name, inputs, domain='default-domain'):
        self.inputs = inputs
        self.user = user
        self.passwd = passwd
        self.domain = domain
        self.project_name = project_name
        use_ssl = self.inputs.api_protocol == 'https'
        self.vnc = VncApi(username=user, password=passwd,
                          tenant_name=project_name,
                          api_server_host=self.inputs.cfgm_ip,
                          api_server_port=self.inputs.api_server_port,
                          api_server_use_ssl=use_ssl)

    def get_project_id(self, project_name=None, domain_id=None):
       if not project_name:
           project_name = self.project_name
       fq_name = [unicode(self.domain), unicode(self.project_name)]
       obj = self.vnc.project_read(fq_name=fq_name)
       if obj:
           return obj.get_uuid()
       return None

    def reauth(self):
        raise Exception('Unimplemented interface')

    def create_project(self, name):
        raise Exception('Unimplemented interface')

    def delete_project(self, name):
        raise Exception('Unimplemented interface')

    def create_user(self, user, passwd):
        raise Exception('Unimplemented interface')

    def delete_user(self, user):
        raise Exception('Unimplemented interface')

    def add_user_to_project(self, user, project):
        raise Exception('Unimplemented interface')

class VM(object):

    def __init__(self, name, vm_id):
	self.name = name
	self.id = vm_id
	self.status = 'ACTIVE'

    def get(self):
	pass	
