import sys
import string
import argparse
from tcutils.cfgparser import parse_cfg_file
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
from tcutils.db import TestDB
from config import *

def random_string(prefix):
    return prefix+''.join(random.choice(string.hexdigits) for _ in range(6))

def sig_handler(_signo, _stack_frame):
    raise KeyboardInterrupt

def setup_test_infra(testbed_file):
    import logging
    from common.log_orig import ContrailLogger
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARN)
    logging.getLogger('paramiko.transport').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.session').setLevel(logging.WARN)
    logging.getLogger('keystoneclient.httpclient').setLevel(logging.WARN)
    logging.getLogger('neutronclient.client').setLevel(logging.WARN)
    logger = ContrailLogger('verify')
    logger.setUp()
    mylogger = logger.logger
    inputs = ContrailTestInit(testbed_file, logger=mylogger)
    inputs.setUp()
    connections = ContrailConnections(inputs=inputs, logger=mylogger)
    return connections

class verify(object):
    def __init__(self, args):
        self.args = args
        self.connections = setup_test_infra(args.testbed_file)
        self.db = None
        if args.db_file:
            self.db = TestDB(args.db_file)

    def verify_router(self):
        raise Exception('Not yet implemented')

    def get_vdns_ids(self):
        vdns = []
        if self.db:
            for fqname in self.db.list_vdns():
                vdns.append(self.db.get_vdns_id(fqname))
        return vdns

    def get_fip_pool_ids(self):
        fip_pools = []
        if self.db:
            for fqname in self.db.list_fip_pools():
                fip_pools.append(self.db.get_fip_pool_id(fqname))
        return fip_pools

    def get_tenant_fqnames(self):
        if self.args.tenant:
            return [':'.join([self.connections.inputs.domain_name, self.args.tenant])]
        if self.db:
            return self.db.list_projects()
        return []

    def get_ipam_ids(self, project_fqname):
        ipams = []
        if self.db:
            for fqname in self.db.list_ipams(project_fqname):
                ipams.append(self.db.get_ipam_id(fqname))
        return ipams

    def get_vn_ids(self, project_fqname, connections):
        if self.args.vn_name:
            vn_id = connections.get_network_h().get_vn_id(self.args.vn_name)
            assert vn_id, 'Unable to fetch ID of vn_name '+ self.args.vn_name
            return [vn_id]
        vns = []
        if self.db:
            for fqname in self.db.list_virtual_networks(project_fqname):
                vn_id  = self.db.get_virtual_network_id(fqname)
                vns.append(vn_id)
        return vns

    def get_vm_details(self, vm_name, project_fqname, connections):
        if self.args.vm_id:
            vn_id = connections.get_network_h().get_vn_id(self.args.vn_name)
            return (self.args.vm_id, [vn_id], self.args.username, self.args.password)
        if self.db:
            return self.db.get_virtual_machine(vm_name, project_fqname)
        return None

    def get_vm_names(self, project_fqname):
        if self.args.vm_id:
            return [self.args.vm_id]
        if self.db:
            return self.db.list_virtual_machines(project_fqname)
        return []

    def get_project_id(self, fqname):
        if self.db:
            return self.db.get_project_id(fqname)
        else:
            return self.connections.get_auth_h().get_project_id(fqname[-1])

    def get_fip_ids(self, vm_name, project_fqname):
        if self.db:
            return self.db.get_fip_id_assoc(vm_name, project_fqname)
        return []

    def verify(self):
        vdns_ids = self.args.vdns or self.get_vdns_ids()
        for vdns_id in vdns_ids:
            vDNS(self.connections).verify(vdns_id)

        fip_pool_ids = self.args.fip_pool_id or self.get_fip_pool_ids()
        for fip_pool in fip_pool_ids:
            FloatingIPPool(self.connections).verify(fip_pool)

        for tenant_fqname in self.get_tenant_fqnames():
            project_id = self.get_project_id(tenant_fqname)
            project_obj = Project(self.connections)
            project_obj.verify(project_id)
            connections = project_obj.get_connections()
            ipam_ids = self.args.ipam or self.get_ipam_ids(tenant_fqname)
            for ipam_id in ipam_ids:
                IPAM(connections).verify(ipam_id)

            for vn_id in self.get_vn_ids(tenant_fqname, connections):
                VN(connections).verify(vn_id)

            for vm_name in self.get_vm_names(tenant_fqname):
                (vm_id, vn_ids, username, password) = \
                        self.get_vm_details(vm_name, tenant_fqname, connections)
                vm_obj = VM(connections)
                vm_obj.verify(vm_id, vn_ids, username, password)
                if self.args.vm_id:
                    vm_name = vm_obj.fq_name()
                for fip_id in self.get_fip_ids(vm_name, tenant_fqname):
                    fip_obj = FloatingIPPool(self.connections)
                    fip_pool_id = fip_obj.get_fip_pool_id(fip_id)
                    fip_obj.verify_fip(fip_pool_id, fip_id, vm_id, vn_ids, connections)

def validate_args(args):
    for key, value in args.__dict__.iteritems():
        if value == 'None':
            args.__dict__[key] = None
        if value == 'False':
            args.__dict__[key] = False
        if value == 'True':
            args.__dict__[key] = True

    if (args.vm_id or args.vn_name) and not args.tenant:
        raise Exception('Need tenant name too. use --tenant <tenant_name>')
                
    if not args.testbed_file:
        args.testbed_file = os.path.join(os.path.abspath(
                                         os.path.dirname(__file__)),
                                         '../', 'sanity_params.ini')
    if not args.db_file:
        args.db_file = os.path.join('/var/tmp/', 'test.db')

    if args.vm_id and not (args.username and args.password):
        raise Exception('Need VM username and password')

    if type(args.vdns) is str:
       args.vdns = [args.vdns]
    if type(args.ipam) is str:
       args.ipam = [args.ipam]
    if type(args.fip_pool_id) is str:
       args.fip_pool_id = [args.fip_pool_id]

def parse_cli(args):
    '''Define and Parse arguments for the script'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--testbed_file', default=None,
                        help='Specify testbed ini file', metavar="FILE")
    parser.add_argument('--db_file', default=None,
                        help='Specify database file', metavar="FILE")
                        
    parser.add_argument('--tenant', default=None,
                        help='Tenant name []')
    parser.add_argument('--vn_name', default=None,
                        help='Name of virtual network')
    parser.add_argument('--vdns', default=None,
                        help='UUID of virtual DNS')
    parser.add_argument('--ipam', default=None,
                        help='IPAM UUID')
    parser.add_argument('--vm_id', default=None,
                        help='UUID of Virtual Machine')
    parser.add_argument('--fip_pool_id', default=None,
                        help='UUID of Floating IP Pool')
    parser.add_argument('--username', default=None,
                        help='VM username - required if vm_id is specified')
    parser.add_argument('--password', default=None,
                        help='VM password - required if vm_id is specified')
                        
    return dict(parser.parse_known_args(args)[0]._get_kwargs())

def update_args(ini_args, cli_args):
    for key in cli_args.keys():
        if cli_args[key]:
            ini_args[key] = cli_args[key]
    return ini_args

class Struct(object):
    def __init__(self, entries): 
        self.__dict__.update(entries)

def main():
    signal.signal(signal.SIGTERM, sig_handler)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-i", "--ini_file", help="Specify conf file", metavar="FILE")
    args, remaining_argv = parser.parse_known_args(sys.argv[1:])
    cli_args = parse_cli(remaining_argv)
    if args.ini_file:
        ini_args = parse_cfg_file(args.ini_file)
        args = update_args(ini_args['TEST'], cli_args)
        args.update(update_args(ini_args['DEFAULTS'], cli_args))
    else:
        args = cli_args
    args = Struct(args)
    validate_args(args)
    obj = verify(args)
    obj.verify()

if __name__ == "__main__":
    main()
