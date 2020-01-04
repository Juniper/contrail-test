import os
import shelve
import filelock

def fqname_to_str(fqname):
    if type(fqname) is list:
        fqname = ':'.join(fqname)
    return fqname

class TestDB(object):
    def __init__(self, filename='/var/tmp/test.db'):
        self.db_file = filename
        if not os.path.exists(self.db_file):
            shelve.open(self.db_file).close()
        self.lock = filelock.FileLock(self.db_file+'.lock')
        self.lock.timeout = 60

    def open(self, mode):
        if mode == 'read':
            self.orig_db = shelve.open(self.db_file, flag='r')
        else:
            self.orig_db = shelve.open(self.db_file)
        self.db = dict(self.orig_db)

    def close(self, mode):
        if mode == 'write':
            self.orig_db['projects'] = self.db.get('projects', {})
            self.orig_db['vdns'] = self.db.get('vdns', {})
            self.orig_db['fip-pool'] = self.db.get('fip-pool', {})
            self.orig_db['logical_router'] = self.db.get('logical_router', {})
            self.orig_db['load_balancer'] = self.db.get('load_balancer', {})
        self.orig_db.close()

    def read(f):
        def wrapper(self, *args, **kwargs):
            self.open(mode='read')
            result = f(self, *args, **kwargs)
            self.close(mode='read')
            return result
        return wrapper

    def write(f):
        def wrapper(self, *args, **kwargs):
            try:
                with self.lock.acquire():
                    self.open(mode='write')
                    result = f(self, *args, **kwargs)
                    self.close(mode='write')
                    return result
            except filelock.Timeout:
                print 'Unable to acquire lock on', self.db_file
                raise
        return wrapper

    def get_vdns_dict(self, fqname):
        if 'vdns' not in self.db:
            self.db['vdns'] = dict()
        if fqname not in self.db['vdns']:
            raise Exception('vDNS %s not found in db'%fqname)
        return self.db['vdns'][fqname]

    @read
    def get_vdns_id(self, fqname):
        vdns = self.get_vdns_dict(fqname_to_str(fqname))
        return vdns['uuid']

    @write
    def set_vdns_id(self, fqname, uuid):
        fqname = fqname_to_str(fqname)
        try:
            self.get_vdns_dict(fqname)
        except:
            self.db['vdns'][fqname] = dict()
        self.db['vdns'][fqname]['uuid'] = uuid

    @write
    def delete_vdns(self, fqname):
        fqname = fqname_to_str(fqname)
        if fqname in self.db['vdns']:
            del self.db['vdns'][fqname]

    @read
    def list_vdns(self):
        return self.db['vdns'].keys()

    @write
    def add_vdns_to_ipam(self, vdns_fqname, ipam_fqname):
        self._add_vdns_to_ipam(self, vdns_fqname, ipam_fqname)

    def _add_vdns_to_ipam(self, vdns_fqname, ipam_fqname):
        vdns = self.get_vdns_dict(fqname_to_str(vdns_fqname))
        if 'ipam_refs' not in vdns:
            vdns['ipam_refs'] = []
        vdns['ipam_refs'].append(fqname_to_str(ipam_fqname))
        vdns['ipam_refs'] = list(set(vdns['ipam_refs']))

    @write
    def delete_vdns_from_ipam(self, vdns_fqname, ipam_fqname):
        self._delete_vdns_from_ipam(self, vdns_fqname, ipam_fqname)

    def _delete_vdns_from_ipam(self, vdns_fqname, ipam_fqname):
        vdns = self.get_vdns_dict(fqname_to_str(vdns_fqname))
        ipam_fqname = fqname_to_str(ipam_fqname)
        if 'ipam_refs' not in vdns or ipam_fqname not in vdns['ipam_refs']:
            return
        vdns['ipam_refs'].remove(ipam_fqname)

    def get_project_dict(self, fqname):
        if 'projects' not in self.db:
            self.db['projects'] = dict()
        if fqname not in self.db['projects']:
            raise Exception('Project %s not found in db'%fqname)
        return self.db['projects'][fqname]

    @read
    def get_project_id(self, fqname):
        proj = self.get_project_dict(fqname_to_str(fqname))
        return proj['uuid']

    @write
    def set_project_id(self, fqname, uuid):
        fqname = fqname_to_str(fqname)
        try:
            self.get_project_dict(fqname)
        except:
            self.db['projects'][fqname] = dict()
        self.db['projects'][fqname]['uuid'] = uuid

    @write
    def delete_project(self, fqname):
        fqname = fqname_to_str(fqname)
        if fqname in self.db['projects']:
            del self.db['projects'][fqname]

    @read
    def list_projects(self):
        return self.db['projects'].keys()

    def get_ipam_dict(self, fqname):
        project_fqname = ':'.join(fqname.split(':')[:-1])
        project = self.get_project_dict(project_fqname)
        if 'ipams' not in project:
            project['ipams'] = dict()
        if fqname not in project['ipams']:
            project['ipams'][fqname] = dict()
        return project['ipams'][fqname]

    @read
    def get_ipam_id(self, fqname):
        ipam = self.get_ipam_dict(fqname_to_str(fqname))
        return ipam['uuid']

    @write
    def add_ipam(self, fqname, uuid, vdns_fqname=None):
        ipam = self.get_ipam_dict(fqname_to_str(fqname))
        ipam['uuid'] = uuid
        self._add_vdns_to_ipam(fqname_to_str(vdns_fqname), fqname)
        ipam['vdns'] = vdns_fqname

    @write
    def delete_ipam(self, fqname):
        fqname = fqname_to_str(fqname)
        ipam = self.get_ipam_dict(fqname)
        if 'vdns' in ipam:
            self._delete_vdns_from_ipam(ipam['vdns'], fqname)
        proj = self.get_project_dict(fqname_to_str(':'.join(fqname.split(':')[:-1])))
        if fqname in proj['ipams']:
            del proj['ipams'][fqname]

    @read
    def list_ipams(self, proj_fqname):
        proj = self.get_project_dict(fqname_to_str(proj_fqname))
        if 'ipams' not in proj:
            return []
        return proj['ipams'].keys()

    def get_vn_dict(self, fqname):
        project_fqname = ':'.join(fqname.split(':')[:-1])
        project = self.get_project_dict(project_fqname)
        if 'virtual-networks' not in project:
            project['virtual-networks'] = dict()
        if fqname not in project['virtual-networks']:
            project['virtual-networks'][fqname] = dict()
        return project['virtual-networks'][fqname]

    @read
    def get_virtual_network_id(self, fqname):
        vn = self.get_vn_dict(fqname_to_str(fqname))
        return vn['uuid']

    @read
    def get_virtual_network(self, fqname):
        vn = self.get_vn_dict(fqname_to_str(fqname))
        return (vn['uuid'], vn['subnets'])

    @write
    def add_virtual_network(self, fqname, uuid, subnets=None):
        vn = self.get_vn_dict(fqname_to_str(fqname))
        vn['uuid'] = uuid
        vn['subnets'] = subnets

    @write
    def delete_virtual_network(self, fqname):
      try:
        fqname = fqname_to_str(fqname)
        proj = self.get_project_dict(fqname_to_str(':'.join(fqname.split(':')[:-1])))
        if fqname in proj['virtual-networks']:
            del proj['virtual-networks'][fqname]
      except:
        pass

    @write
    def add_lr_to_vn(self, fqname, router_id):
        vn = self.get_vn_dict(fqname_to_str(fqname))
        vn['router'] = router_id

    @write
    def delete_lr_from_vn(self, fqname, router_id):
        vn = self.get_vn_dict(fqname_to_str(fqname))
        if 'router' in vn and vn['router'] == router_id:
            del vn['router']

    @read
    def list_virtual_networks(self, proj_fqname):
        proj = self.get_project_dict(fqname_to_str(proj_fqname))
        if 'virtual-networks' not in proj:
            return []
        return proj['virtual-networks'].keys()

    def get_vm_dict(self, name, project_fqname):
        project = self.get_project_dict(project_fqname)
        if 'virtual-machines' not in project:
            project['virtual-machines'] = dict()
        if name not in project['virtual-machines']:
            project['virtual-machines'][name] = dict()
        return project['virtual-machines'][name]

    @write
    def add_virtual_machine(self, name, proj_fqname, uuid, vn_ids, username='ubuntu', password='ubuntu'):
        vm = self.get_vm_dict(fqname_to_str(name), fqname_to_str(proj_fqname))
        vm['uuid'] = uuid
        vm['vns'] = vn_ids
        vm['username'] = username
        vm['password'] = password

    @write
    def associate_fip_to_vm(self, name, proj_fqname, fip_id):
        vm = self.get_vm_dict(fqname_to_str(name), fqname_to_str(proj_fqname))
        if not 'fip_ids' in vm:
            vm['fip_ids'] = list()
        vm['fip_ids'].append(fip_id)
        vm['fip_ids'] = list(set(vm['fip_ids']))

    @write
    def disassociate_fip_from_vm(self, name, proj_fqname, fip_id):
        vm = self.get_vm_dict(fqname_to_str(name), fqname_to_str(proj_fqname))
        if not 'fip_ids' in vm:
            return
        vm['fip_ids'].remove(fip_id)

    @read
    def get_fip_id_assoc(self, name, proj_fqname):
        vm = self.get_vm_dict(fqname_to_str(name), fqname_to_str(proj_fqname))
        return vm.get('fip_ids', [])

    @write
    def delete_virtual_machine(self, name, proj_fqname):
        proj = self.get_project_dict(fqname_to_str(proj_fqname))
        if name in proj['virtual-machines']:
            del proj['virtual-machines'][name]

    @read
    def get_virtual_machine(self, name, proj_fqname):
        vm = self.get_vm_dict(fqname_to_str(name), fqname_to_str(proj_fqname))
        return (vm['uuid'], vm['vns'], vm['username'], vm['password'])

    @read
    def get_creds_of_vm(self, vm_id, proj_fqname):
        proj = self.get_project_dict(fqname_to_str(proj_fqname))
        for vm_name in proj['virtual-machines'].keys():
            vm = self.get_vm_dict(vm_name, fqname_to_str(proj_fqname))
            if vm_id == vm['uuid']:
                return (vm['username'], vm['password'])
        return (None, None)

    @read
    def list_virtual_machines(self, proj_fqname):
        proj = self.get_project_dict(fqname_to_str(proj_fqname))
        if 'virtual-machines' not in proj:
            return []
        return proj['virtual-machines'].keys()

    @read
    def list_vms_in_vn(self, vn_id, proj_fqname):
        vms = list()
        proj = self.get_project_dict(fqname_to_str(proj_fqname))
        if not proj.get('virtual-machines', None):
            return vms
        for vm_name in proj['virtual-machines'].keys():
            if vn_id in proj['virtual-machines'][vm_name]['vns']:
                vm_dict = self.get_vm_dict(vm_name, fqname_to_str(proj_fqname))
                vms.append(vm_dict['uuid'])
        return vms

    def get_fip_pool_dict(self, fqname):
        if 'fip-pool' not in self.db:
            self.db['fip-pool'] = dict()
        if fqname not in self.db['fip-pool']:
            raise Exception('Fip-Pool %s not found in db'%fqname)
        return self.db['fip-pool'][fqname]

    @write
    def add_fip_pool(self, fqname, uuid):
        fqname = fqname_to_str(fqname)
        try:
            self.get_fip_pool_dict(fqname)
        except:
            self.db['fip-pool'][fqname] = dict()
        self.db['fip-pool'][fqname]['uuid'] = uuid

        fip_dict = self.get_fip_pool_dict(fqname_to_str(fqname))
        fip_dict['uuid'] = uuid

    @read
    def get_fip_pool_id(self, fqname):
        fip_dict = self.get_fip_pool_dict(fqname_to_str(fqname))
        return fip_dict['uuid']

    @write
    def delete_fip_pool(self, fqname):
        fqname = fqname_to_str(fqname)
        if fqname in self.db['fip-pool']:
            del self.db['fip-pool'][fqname]

    @read
    def list_fip_pools(self):
        return self.db['fip-pool'].keys()

    @read
    def get_fips(self, fqname):
        fip_dict = self.get_fip_pool_dict(fqname_to_str(fqname))
        return fip_dict.get('fip_ids', [])

    @write
    def add_fip(self, fqname, fip_id):
        fip_dict = self.get_fip_pool_dict(fqname_to_str(fqname))
        if 'fip_ids' not in fip_dict:
            fip_dict['fip_ids'] = list()
        fip_dict['fip_ids'].append(fip_id)
        fip_dict['fip_ids'] = list(set(fip_dict['fip_ids']))

    @write
    def delete_fip(self, fqname, fip_id):
        fip_dict = self.get_fip_pool_dict(fqname_to_str(fqname))
        if 'fip_ids' not in fip_dict:
            return
        fip_dict['fip_ids'].remove(fip_id)

    @read
    def find_fip_pool_id(self, fip_id):
        for fqname, value in self.db['fip-pool'].iteritems():
            if fip_id in value['fip_ids']:
                return value['uuid']

    def get_logical_router_dict(self, fqname):
        if 'logical_router' not in self.db:
            self.db['logical_router'] = dict()
        if fqname not in self.db['logical_router']:
            raise Exception('Logical router %s not found in db'%fqname)
        return self.db['logical_router'][fqname]

    @write
    def add_logical_router(self, fqname, uuid):
        fqname = fqname_to_str(fqname)
        try:
            self.get_logical_router_dict(fqname)
        except:
            self.db['logical_router'][fqname] = dict()
        self.db['logical_router'][fqname]['uuid'] = uuid

        logical_router = self.get_logical_router_dict(fqname_to_str(fqname))
        logical_router['uuid'] = uuid

    @read
    def get_logical_router_id(self, fqname):
        logical_router = self.get_logical_router_dict(fqname_to_str(fqname))
        return logical_router['uuid']

    @write
    def delete_logical_router(self, fqname):
        fqname = fqname_to_str(fqname)
        if fqname in self.db['logical_router']:
            del self.db['logical_router'][fqname]

    @read
    def list_logical_routers(self):
        return self.db['logical_router'].keys()

    @read
    def get_vns_of_lr(self, fqname):
        logical_router = self.get_logical_router_dict(fqname_to_str(fqname))
        return logical_router.get('vns', [])

    @write
    def add_vn_to_lr(self, fqname, vn_id):
        logical_router = self.get_logical_router_dict(fqname_to_str(fqname))
        if 'vns' not in logical_router:
            logical_router['vns'] = list()
        logical_router['vns'].append(vn_id)
        logical_router['vns'] = list(set(logical_router['vns']))

    @write
    def delete_vn_from_lr(self, fqname, vn_id):
        logical_router = self.get_logical_router_dict(fqname_to_str(fqname))
        if 'vns' not in logical_router or vn_id not in logical_router['vns']:
            return
        logical_router['vns'].remove(vn_id)

    @write
    def get_gw_of_lr(self, fqname):
        logical_router = self.get_logical_router_dict(fqname_to_str(fqname))
        return logical_router.get('gw', None)

    @write
    def set_gw_to_lr(self, fqname, vn_id):
        logical_router = self.get_logical_router_dict(fqname_to_str(fqname))
        logical_router['gw'] = vn_id

    @write
    def clear_gw_from_lr(self, fqname):
        logical_router = self.get_logical_router_dict(fqname_to_str(fqname))
        if 'gw' in logical_router:
            del logical_router['gw']

    def get_load_balancer_dict(self, fqname):
        if 'load_balancer' not in self.db:
            self.db['load_balancer'] = dict()
        if fqname not in self.db['load_balancer']:
            raise Exception('Load balancer %s not found in db'%fqname)
        return self.db['load_balancer'][fqname]

    @write
    def add_load_balancer(self, fqname, uuid):
        fqname = fqname_to_str(fqname)
        try:
            self.get_load_balancer_dict(fqname)
        except:
            self.db['load_balancer'][fqname] = dict()
        self.db['load_balancer'][fqname]['uuid'] = uuid

        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        load_balancer['uuid'] = uuid

    @write
    def delete_load_balancer(self, fqname):
        fqname = fqname_to_str(fqname)
        if fqname in self.db['load_balancer']:
            del self.db['load_balancer'][fqname]

    @read
    def get_load_balancer_id(self, fqname):
        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        return load_balancer['uuid']

    @write
    def set_vip_to_lb(self, fqname, vip_id):
        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        load_balancer['vip'] = vip_id

    @write
    def clear_vip_from_lb(self, fqname):
        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        if 'vip' in load_balancer:
            del load_balancer['vip']

    @read
    def get_vip_of_lb(self, fqname):
        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        return load_balancer.get('vip', None)

    @write
    def set_fip_on_vip(self, fqname, fip):
        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        load_balancer['fip'] = fip

    @write
    def clear_fip_on_vip(self, fqname):
        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        if 'fip' in load_balancer:
            del load_balancer['fip']

    @read
    def get_fip_on_vip(self, fqname):
        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        return load_balancer.get('fip', None)

    @write
    def add_member_to_lb(self, fqname, member_id):
        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        if 'members' not in load_balancer:
            load_balancer['members'] = list()
        load_balancer['members'].append(member_id)
        load_balancer['members'] = list(set(load_balancer['members']))

    @write
    def delete_member_from_lb(self, fqname, member_id):
        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        if 'members' not in load_balancer or member_id not in load_balancer['members']:
            return
        load_balancer['members'].remove(member_id)

    @read
    def get_members_of_lb(self, fqname):
        load_balancer = self.get_load_balancer_dict(fqname_to_str(fqname))
        return load_balancer.get('members', [])

    @read
    def list_load_balancer(self):
        return self.db['load_balancer'].keys()

    @read
    def dump(self):
        print self.db

def main():
#    db = TestDB('db.1')
    db = TestDB('/root/test.db.scale.load_balance')
#    db.dump()
#    l = list()
#    for entry in db.list_logical_routers():
#        router_name = entry.split(':')[2]
#        if router_name in l:
#            import pdb; pdb.set_trace()
#        print router_name
#        l.append(router_name)
#        if db.get_logical_router_id(entry) == '22c7f61b-aec3-4787-9dbf-98bee9f030fc':
#            import pdb; pdb.set_trace()
    for entry in db.list_fip_pools():
        print entry
        fips = db.get_fips(entry)
        import pdb; pdb.set_trace()
    exit(0)
    db.delete_project('default-domain:TestProject-LBaas')
    db.set_project_id('default-domain:db-test', 123)
    print db.get_project_id('default-domain:db-test')
    db.add_virtual_network('default-domain:db-test:db-vn', 1234)
    print db.get_virtual_network_id('default-domain:db-test:db-vn')
    print db.list_virtual_networks('default-domain:db-test')

if __name__ == "__main__":
    main()
