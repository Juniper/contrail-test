import subprocess
import random
from winrm.protocol import Protocol
from winrm import Session
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
    	username='Administrator', password='Contrail123!', transport='ntlm', ignore_error=False):

	if not isinstance(command, list):
	    cmd_list = [command]
	for command in cmd_list:
   	    s = Session(
                target_host,
                auth=(username, password),
                transport=transport)
	    partial_cmd_list = command.split(' ')
            result = s.run_cmd(partial_cmd_list[0], partial_cmd_list[1:])

            if not ignore_error:
                if result.status_code != 0:
                    assert False, ("Error while executing command {} on windows compute {}."
                        "Error is {}".format(command, target_host, result.std_err))
            print(result.std_out, result.status_code)
	if len(cmd_list) == 1:
            return result.std_out, result.std_err, result.status_code

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

    def _delete_docker_on_windows(self, network, docker_name, target_host, image, username='Administrator',
    	password='Contrail123!', transport='ntlm'):

    	docker_stop_command = "docker container stop {}".format(docker_name)
    	docker_remove_command = "docker container rm {}".format(docker_name)
    	std_out, std_err, status_code = self._run_docker_cmd_on_remote_windows(
    		target_host=target_host,
    		command=docker_stop_command,
    		username=username,
    		password=password,
    		transport=transport)
    	std_out, std_err, status_code = self._run_docker_cmd_on_remote_windows(
    		target_host=target_host,
    		command=docker_remove_command,
    		username=username,
    		password=password,
    		transport=transport)
	
	self.logger.info("Deleting the network associated with this container")
	self._delete_docker_network(
	    network=network,
	    target_host=target_host)

    	return std_out, std_err, status_code, docker_name

    def _create_docker_network(self, network, target_host, username='Administrator',
    	password='Contrail123!', transport='ntlm', ignore_error=False):

    	network_create_cmd = "docker network create --ipam-driver windows -d Contrail \
    	    --opt tenant={} --opt network={} {}".format(self.inputs.project_name,network, network)
    	std_out, std_err, status_code = self._run_docker_cmd_on_remote_windows(
    		target_host=target_host,
    		command=network_create_cmd,
    		username=username,
    		password=password,
    		transport=transport,
		ignore_error=ignore_error)
    	return std_out, std_err, status_code, network

    def _delete_docker_network(self, network, target_host, username='Administrator',
        password='Contrail123!', transport='ntlm'):
	
	network_delete_cmd = "docker network rm {}".format(network)
	std_out, std_err, status_code = self._run_docker_cmd_on_remote_windows(
                target_host=target_host,
                command=network_delete_cmd,
                username=username,
                password=password,
                transport=transport,
		ignore_error=True)
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
        vn_name = vn_name or get_random_name(self.inputs.project_name)
        vn_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn_name,
                subnet=vn_subnet,
                inputs=self.inputs))

    def delete_vn(self, vn_obj, **kwargs):
        
	#Deleting VN from windows machine will be taken care in delete_vm method
	return self.vnc_h.delete_vn_api(vn_obj)

    def delete_vm(self, vm_obj, **kwargs):
	
	self.logger.info("Deleting VM {} on host {}".format(vm_obj.name, vm_obj.host_ip))
	vm_cmd_output = self._delete_docker_on_windows(
                network=vm_obj.network,
                docker_name=vm_obj.name,
                target_host=vm_obj.host_ip,
                image=vm_obj.image,
                username=vm_obj.host_username,
                password=vm_obj.host_password,
                transport=vm_obj.transport)

    def create_vm(self, vm_name, vn_objs, image_name='microsoft/windowsservercore',
    	target_host_username='Administrator', target_host_transport='ntlm', target_host_password='Contrail123!',
    	count=1, zone=None, node_name=None, **kwargs):
 
	#For now, taking the first network from vn_objs. Change this later as required
	network_name = vn_objs[0].name	
	if not node_name:	
	    virtual_routers = self.get_virtual_routers_list()

	    self.logger.info("Selecting a compute node in a random fashion")
	    compute_node = random.choice(virtual_routers)
	    compute_node_data = self.read_virtual_routers_data(
		fq_name=compute_node['fq_name'])
	    node_name = str(compute_node_data._virtual_router_ip_address)

	self.logger.info("Create virtual network on the windows compute node")
    	self._create_docker_network(
    		network=network_name,
    		target_host=node_name,
		ignore_error=True)

    	vm_name = vm_name or get_random_name(self.inputs.project_name)
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
	return [VM(
	    name=vm_name,
	    vm_id=vm_id,
	    host_ip=node_name,
	    network=network_name,
	    image=image_name,
	    host_username=target_host_username,
            host_password=target_host_password,
            transport=target_host_transport,
	    vnc_h=self.vnc_h)]

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
        return image_name

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

	return self._vnc.sub_clusters_list()

    def get_host_of_vm(self, vm_obj, **kwargs):
        '''Returns name of the compute, on which the VM was created.'''
        
	return vm_obj.host_ip

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

	return [str(vm_obj.instance_ip_obj_read._instance_ip_address)]

    def is_vm_deleted(self, vm_obj, **kwargs):
        result_dict = self._vnc.virtual_machines_list(obj_uuids=[vm_obj.id])
	if not result_dict['virtual-machines']:
	    return True
	return False

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
        self.inputs.project_name = project_name
        use_ssl = self.inputs.api_protocol == 'https'
        self.vnc = VncApi(username=user, password=passwd,
                          tenant_name=project_name,
                          api_server_host=self.inputs.cfgm_ip,
                          api_server_port=self.inputs.api_server_port,
                          api_server_use_ssl=use_ssl)

    def get_project_id(self, project_name=None, domain_id=None):
        if not project_name:
            project_name = self.inputs.project_name
        fq_name = [unicode(self.domain), unicode(self.inputs.project_name)]
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

class VM(WindowsOrchestrator):

    def __init__(self, name, vm_id, host_ip, network, image='microsoft/windowsservercore',
        host_username='Administrator', transport='ntlm', host_password='Contrail123!',vnc_h=None):
	
	self.name = name
	self.status = 'ACTIVE'
	self.host_ip = str(host_ip)
	self.network = network
	self.image = image
	self.host_username = host_username
	self.host_password = host_password
	self.transport = transport
	self.vm_id = vm_id
	self.vnc_h = vnc_h
	self.get()

    def _read_vm_fq_name_str(self):
        ''' Runs docker inspect on windows host to find VM fq_name_str'''

        docker_inspect_cmd = "docker inspect --format=\"{{{{range .NetworkSettings.Networks}}}}{{{{.EndpointID}}}}{{{{end}}}}\" {}".format(self.vm_id)
        std_out, std_err, status_code = self._run_docker_cmd_on_remote_windows(
                target_host=self.host_ip,
                command=docker_inspect_cmd,
                username=self.host_username,
                password=self.host_password,
                transport=self.transport)
        self.fq_name_str = std_out.strip()

    def _read_uuid(self):

        virtual_machine_obj = self.vnc_h.virtual_machine_read(
            fq_name_str=self.fq_name_str)

        self.vmi_obj = virtual_machine_obj.get_virtual_machine_interface_back_refs()[0]

        self.vmi_obj_uuid = self.vmi_obj["uuid"]
	self.id = str(self.vmi_obj["uuid"])
        self.vmi_obj_read = self.vnc_h.virtual_machine_interface_read(id=self.vmi_obj_uuid)

        self.instance_ip_obj = self.vmi_obj_read.get_instance_ip_back_refs()
        self.instance_ip_obj_uuid = self.instance_ip_obj[0]["uuid"]
        self.instance_ip_obj_read = self.vnc_h.instance_ip_read(id=self.instance_ip_obj_uuid)

    def get(self):
	self._read_vm_fq_name_str()
	self._read_uuid()
	
    def _run_docker_cmd_on_remote_windows(self, target_host, command, powershell=False,
    	username='Administrator', password='Contrail123!', transport='ntlm', ignore_error=False):

	s = Session(
	        target_host,
		auth=(username, password),
		transport=transport)
	cmd_list = command.split(' ')
        result = s.run_cmd(cmd_list[0], cmd_list[1:])
	
	if not ignore_error:
            if result.status_code != 0:
                assert False, ("Error while executing command {} on windows compute {}." 
                    "Error is {}".format(cmd_list, target_host, result.std_err))
        print(result.std_out, result.status_code)
        return result.std_out, result.std_err, result.status_code
