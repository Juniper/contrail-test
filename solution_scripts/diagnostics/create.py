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
    logger = ContrailLogger('create')
    logger.setUp()
    mylogger = logger.logger
    inputs = ContrailTestInit(testbed_file, logger=mylogger)
    inputs.setUp()
    connections = ContrailConnections(inputs=inputs, logger=mylogger)
    return connections

class create(object):
    def __init__(self, args):
        self.args = args
        self.connections = setup_test_infra(args.testbed_file)
        project_id = self.connections.get_project_id()
        project_fq_name = self.connections.get_project_fq_name()
        self.db = TestDB(args.db_file)
        self.db.set_project_id(project_fq_name, project_id)
        self.uuid = dict()
        self.vm_connections_map = dict()

    def setup(self):

# Create vDNS
        vdns_id = self.args.vdns
        vdns_obj = vDNS(self.connections)
        vdns_fqname = None
        if self.args.create_vdns:
            vdns_id = vdns_obj.create(random_string('vDNS'))
        if vdns_id:
            vdns_fqname = vdns_obj.fq_name(vdns_id)
            self.db.set_vdns_id(vdns_fqname, vdns_id)

# Create Public Network in case of dNAT or sNAT
        if self.args.n_fips or self.args.create_snat or self.args.router_id:
            name = self.args.public_vn or random_string('Public')
            vn_obj = VN(self.connections)
            self.public_vn_id = vn_obj.create(name, external=True)
            vn_subnets = vn_obj.get_subnets(self.public_vn_id)
            self.db.add_virtual_network(vn_obj.fq_name(), self.public_vn_id, vn_subnets)

# Create Tenant
        for tenant_index in range(int(self.args.n_tenants)):
            self.tenant_name = self.args.tenant or random_string(self.args.tenant_prefix)
            tenant_obj = Project(self.connections)
            tenant_id = tenant_obj.create(self.tenant_name)
            tenant_obj.update_default_sg()
            tenant_connections = tenant_obj.get_connections()
            self.db.set_project_id(tenant_obj.fq_name(), tenant_id)
            self.uuid[self.tenant_name] = UUID()

# Create IPAM
            ipam_id = self.args.ipam
            ipam_obj = IPAM(tenant_connections)
            if self.args.create_ipam:
                ipam_id = ipam_obj.create(self.get_name('ipam'), vdns_id)
            if ipam_id:
                ipam_fqname = ipam_obj.fq_name(ipam_id)
                self.uuid[self.tenant_name].ipam_id = ipam_id
                self.db.add_ipam(ipam_obj.fq_name(), ipam_id, vdns_fqname)

# Create sNAT instance
            self.router_id = self.args.router_id
            router_obj = LogicalRouter(tenant_connections)
            if self.args.create_snat:
                self.router_id = router_obj.create(self.get_name('rtr'), gw=self.public_vn_id)
            if self.router_id:
                router_fqname = router_obj.fq_name(self.router_id)
                self.db.add_logical_router(router_fqname, self.router_id)
                self.db.set_gw_to_lr(router_fqname, self.public_vn_id)
                self.router_fqname = router_fqname

# Create Network
            self.create_vns(tenant_connections)

# Create VMs
            for vn_name,vn_id in self.uuid[self.tenant_name].vn_id.iteritems():
                self.create_vms(tenant_connections, vn_id, vn_name)

# Create FIP Pool and associate fips to VMs
        if self.args.n_fips:
            fip_pool_obj = FloatingIPPool(self.connections)
            self.fip_pool_id = fip_pool_obj.create(self.public_vn_id)
            self.fip_pool_fqname = fip_pool_obj.fq_name()
            self.db.add_fip_pool(self.fip_pool_fqname, self.fip_pool_id)
            self.associate_fips()

    def create_vns(self, connections):
        for index in range(int(self.args.n_vns)):
            name = self.args.vn_name or self.get_name('VN', index)
            ipam_id = self.uuid[self.tenant_name].ipam_id
            vn_obj = VN(connections)
            self.uuid[self.tenant_name].vn_id[name] = vn_obj.create(name,
                                    ipam_id=ipam_id)
            vn_fqname = vn_obj.fq_name()
            vn_subnets = vn_obj.get_subnets(self.uuid[self.tenant_name].vn_id[name])
            self.db.add_virtual_network(vn_fqname, self.uuid[self.tenant_name].vn_id[name], vn_subnets)
            if self.router_id:
                LogicalRouter(connections).attach_vn(self.router_id, self.uuid[self.tenant_name].vn_id[name])
                self.db.add_vn_to_lr(self.router_fqname, self.uuid[self.tenant_name].vn_id[name])
                self.db.add_lr_to_vn(vn_fqname, self.router_id)

    def create_vms(self, connections, vn_id, vn_name):
        for index in range(int(self.args.n_vms)):
            name = random_string(vn_name+'-VM%s'%index)
            vm_obj = VM(connections)
            self.uuid[self.tenant_name].vm_id[name] = vm_obj.create(name, [vn_id], self.args.image)
            vm_fqname = vm_obj.fq_name()
            (self.username, self.password) = vm_obj.get_vm_creds()
            self.db.add_virtual_machine(name, connections.get_project_fq_name(),
                                        self.uuid[self.tenant_name].vm_id[name],
                                        [vn_id], self.username, self.password)
            self.vm_connections_map[name] = connections

    def associate_fips(self):
        vm_names = list(); vm_ids = list()
        for uuid in self.uuid.itervalues():
            (names, ids) = (uuid.vm_id.keys(), uuid.vm_id.values())
            vm_names.extend(names)
            vm_ids.extend(ids)

        for index in range(int(self.args.n_fips)):
            connections = self.vm_connections_map[vm_names[index]]
            fip_id = FloatingIPPool(self.connections).associate_fip(
                                                      self.fip_pool_id,
                                                      vm_ids[index],
                                                      connections,
                                                      self.username,
                                                      self.password)
            self.db.associate_fip_to_vm(vm_names[index],
                                        connections.get_project_fq_name(),
                                        fip_id)
            self.db.add_fip(self.fip_pool_fqname, fip_id)

    def get_name(self, prefix, index=''):
        return random_string(self.tenant_name + '-' + str(prefix) + str(index))

class UUID(object):
    def __init__(self):
        self.ipam_id = None
        self.vn_id = dict()
        self.vm_id = dict()

def validate_args(args):
    for key, value in args.__dict__.iteritems():
        if value == 'None':
            args.__dict__[key] = None
        if value == 'False':
            args.__dict__[key] = False
        if value == 'True':
            args.__dict__[key] = True

    if args.vn_name and not args.tenant:
        raise Exception('Need tenant name too. use --tenant <tenant_name>')

    if not args.testbed_file:
        args.testbed_file = os.path.join(os.path.abspath(
                                         os.path.dirname(__file__)),
                                         '../', 'sanity_params.ini')
    if not args.db_file:
        args.db_file = os.path.join('/var/tmp/', 'test.db')

    if args.tenant:
        args.n_tenants = 1
    if args.vn_name:
        args.n_vns = 1
    if not args.n_tenants and \
       (args.n_vns or args.n_vms or args.n_fips):
        args.n_tenants = 1
    if not args.n_vns and args.n_vms:
        args.n_vns = 1
    if int(args.n_fips) > (int(args.n_tenants) * int(args.n_vms) * int(args.n_vns)):
        raise Exception('n_fips cant be greater than (n_tenants * n_vms * n_vns)')
    if args.n_vms and not args.image:
        raise Exception('n_vms needs image name, please specify --image <image_name>')
    if not args.tenant_prefix:
        args.tenant_prefix = 'TestProject'

def parse_cli(args):
    '''Define and Parse arguments for the script'''
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tenant_prefix', default=None,
                        help='tenant prefix for auto generated tenants [TestProject]')
    parser.add_argument('--image', default=None,
                        help='Image Name [None]')
    parser.add_argument('--n_tenants', default=0, type=int,
                        help='No of tenants to create [0]')
    parser.add_argument('--n_vns', default=0, type=int,
                        help='No of Vns to create per tenant [0]')
    parser.add_argument('--n_vms', default=0, type=int,
                        help='No of VMs to create per VN [0]')
    parser.add_argument('--n_fips', default=0, type=int,
                        help='No of Floating-IPs to create [0]')
    parser.add_argument('--create_vdns', action='store_true',
                        help='Knob to create and associate vdns')
    parser.add_argument('--create_ipam', action='store_true',
                        help='Knob to create and associate ipam')
    parser.add_argument('--create_snat', action='store_true',
                        help='Knob to create and associate Logical Router')

    parser.add_argument('--testbed_file', default=None,
                        help='Specify testbed ini file', metavar="FILE")
    parser.add_argument('--db_file', default=None,
                        help='Specify database file', metavar="FILE")

    parser.add_argument('--tenant', default=None,
                        help='Tenant name []')
    parser.add_argument('--public_vn', default=None,
                        help='Name of public network')
    parser.add_argument('--vn_name', default=None,
                        help='Name of virtual network')
    parser.add_argument('--vdns', default=None,
                        help='UUID of virtual DNS')
    parser.add_argument('--ipam', default=None,
                        help='IPAM UUID')
    parser.add_argument('--router_id', default=None,
                        help='UUID of Logical Router(snat)')

    return dict(parser.parse_known_args(args)[0]._get_kwargs())

# CLI params override params defined in ini file
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
    obj = create(args)
    obj.setup()

if __name__ == "__main__":
    main()
