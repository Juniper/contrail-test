import subprocess
from winrm.protocol import Protocol

class WindowsOrchestrator(Orchestrator):

    def __init__(self, inputs, host, port, user, pwd, dc_name, vnc=None, logger=None):
		
        super(VcenterOrchestrator, self).__init__(inputs, vnc, logger)
        self._inputs = inputs
        self._host = host
        self._port = port
        self._user = user
        self._passwd = pwd
        self._dc_name = dc_name
        self._vnc = vnc
        self._log = logger
        self._images_info = parse_cfg_file('configs/images.cfg')
        self._connect_to_windows()
        self._create_keypair()
        self._nfs_ds = NFSDatastore(self._inputs, self)
        self.migration = False

    def _run_docker_cmd_on_remote_windows(self, target_host, command, powershell=False,
    	username='Administrator', password='Contrail123!', transport='ntlm'):

    	self.logger.info("Executing the following docker cmd")
    	self.logger.info(docker_cmd)
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
            command_id = p.run_command(shell_id, "docker", docker_cmd.split(" ")[1:])
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

    def _create_docker_windows(self, network, docker_name, target_host, image, username='Administrator',
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

    	network_create_cmd = "docker network create --ipam-driver windows -d Contrail "
    	    "--opt tenant=admin --opt network={} {}".format(network, network)
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

    def create_vm(self, target_host, network_name, image_name='microsoft/windowsservercore',
    	target_host_username='Administrator', target_host_transport='ntlm', target_host_password='Contrail123!',
    	vm_name='', count=1, zone=None, node_name=None, **kwargs):
    	
    	vm_name = vm_name or get_random_name(self.project_name)    		
    	vm_cmd_output = self._create_docker_in_windows(
        	network=network_name,
        	docker_name=vm_name,
        	target_host=target_host,
        	image=image_name,
        	username=target_host_username,
        	password=target_host_password,
        	transport=target_host_transport)

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


